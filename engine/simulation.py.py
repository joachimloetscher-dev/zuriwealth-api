import copy
from typing import Dict, List, Tuple
from models import SimulationRequest
from calculators import tax_zh, real_estate, pension_ahv_bvg

def run_simulation(req: SimulationRequest, config: Dict) -> Tuple[List[Dict], float]:
    state = copy.deepcopy(req)
    timeline = []
    total_tax_paid = 0.0
    current_year = config["meta"]["year"]
    inflation = config["meta"]["inflation_rate"]
    
    returns = {"conservative": (0.01, 0.01), "balanced": (0.03, 0.015), "growth": (0.05, 0.02)}
    cap_growth, yield_rate = returns.get(state.financial.risk_profile, (0.03, 0.015))

    for age in range(state.personal.current_age, 96):
        is_retired = age >= state.personal.target_retirement_age
        annual_tax = 0.0
        
        # Inflation applied year over year
        if age > state.personal.current_age:
            state.financial.monthly_living_expenses *= (1.0 + inflation)
            
        taxable_income = 0.0
        net_wealth = state.financial.cash_assets + state.financial.invested_assets

        # Transition Year (Capital Withdrawal Tax)
        if age == state.personal.target_retirement_age and state.pension.pillar_3a_capital > 0:
            lump_sum = state.pension.pillar_3a_capital
            
            if state.pension.stagger_3a_withdrawals and state.pension.pillar_3a_accounts_count > 1:
                chunks = state.pension.pillar_3a_accounts_count
                tax_per_chunk = tax_zh.calculate_capital_withdrawal_tax(lump_sum / chunks, state.personal.civil_status, config)
                withdrawal_tax = tax_per_chunk * chunks
            else:
                withdrawal_tax = tax_zh.calculate_capital_withdrawal_tax(lump_sum, state.personal.civil_status, config)
                
            annual_tax += withdrawal_tax
            net_lump_sum = lump_sum - withdrawal_tax
            state.financial.invested_assets += net_lump_sum 
            state.pension.pillar_3a_capital = 0.0 

        if not is_retired:
            # Accumulation
            taxable_income = state.financial.gross_income_primary + state.financial.gross_income_spouse
            taxable_income -= state.pension.annual_3a_contribution
            
            if state.real_estate and state.real_estate.is_owner:
                taxable_income += real_estate.calculate_eigenmietwert(state.real_estate.market_value)
                interest = real_estate.calculate_mortgage_interest(state.real_estate.mortgage_debt, state.real_estate.mortgage_interest_rate)
                taxable_income -= interest
                net_wealth += (state.real_estate.market_value - state.real_estate.mortgage_debt)
                
                if state.real_estate.amortization_type == "direct":
                    state.real_estate.mortgage_debt -= state.real_estate.annual_amortization_amount
                else:
                    state.financial.invested_assets += state.real_estate.annual_amortization_amount

            income_tax = tax_zh.calculate_income_tax(taxable_income, state.personal.civil_status, config)
            wealth_tax = tax_zh.calculate_wealth_tax_zh(net_wealth, state.personal.civil_status, config)
            annual_tax += (income_tax + wealth_tax)
            
            savings = taxable_income - (state.financial.monthly_living_expenses * 12) - annual_tax
            
            if savings > 0:
                state.financial.invested_assets += savings
            else:
                state.financial.cash_assets += savings 
                
            state.pension.bvg_capital += state.pension.bvg_annual_savings
            state.pension.pillar_3a_capital += state.pension.annual_3a_contribution

        else:
            # Decumulation
            ahv_pension = pension_ahv_bvg.calculate_ahv_pension(
                state.personal.civil_status == "married", 
                state.personal.missing_ahv_years, 
                state.personal.target_retirement_age, 
                config
            )
            bvg_pension = state.pension.bvg_capital * 0.05 
            taxable_income = ahv_pension + bvg_pension
            
            if age < 65:
                ne_tax = pension_ahv_bvg.calculate_ahv_nichterwerbstaetige(net_wealth, taxable_income, config)
                annual_tax += ne_tax
                
            income_tax = tax_zh.calculate_income_tax(taxable_income, state.personal.civil_status, config)
            annual_tax += income_tax
            
            expenses = state.financial.monthly_living_expenses * 12
            gap = expenses + annual_tax - taxable_income
            
            # Correct Waterfall: Drain Cash -> Invested
            if gap > 0:
                if state.financial.cash_assets >= gap:
                    state.financial.cash_assets -= gap
                else:
                    remaining_gap = gap - state.financial.cash_assets
                    state.financial.cash_assets = 0
                    state.financial.invested_assets -= remaining_gap
                    if state.financial.invested_assets < 0:
                        state.financial.invested_assets = 0

        # Growth
        state.financial.invested_assets *= (1.0 + cap_growth)
        taxable_yield_amount = state.financial.invested_assets * yield_rate
        state.financial.invested_assets += taxable_yield_amount 
        
        total_tax_paid += annual_tax
        timeline.append({
            "age": age,
            "year": current_year,
            "wealth": max(0.0, state.financial.cash_assets + state.financial.invested_assets),
            "tax": annual_tax
        })
        current_year += 1

    return timeline, total_tax_paid