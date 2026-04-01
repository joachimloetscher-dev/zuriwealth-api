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
        
        # Inflate living expenses and salaries to maintain real purchasing power
        if age > state.personal.current_age:
            state.financial.monthly_living_expenses *= (1.0 + inflation)
            if not is_retired:
                state.financial.gross_income_primary *= (1.0 + inflation)
                state.financial.gross_income_spouse *= (1.0 + inflation)
            
        net_wealth = state.financial.cash_assets + state.financial.invested_assets

        # ---- TRANSITION YEAR (Capital Withdrawal Tax) ----
        if age == state.personal.target_retirement_age and state.pension.pillar_3a_capital > 0:
            lump_sum = state.pension.pillar_3a_capital
            if state.pension.stagger_3a_withdrawals and state.pension.pillar_3a_accounts_count > 1:
                chunks = state.pension.pillar_3a_accounts_count
                tax_per_chunk = tax_zh.calculate_capital_withdrawal_tax(lump_sum / chunks, state.personal.civil_status, config)
                withdrawal_tax = tax_per_chunk * chunks
            else:
                withdrawal_tax = tax_zh.calculate_capital_withdrawal_tax(lump_sum, state.personal.civil_status, config)
                
            annual_tax += withdrawal_tax
            state.financial.invested_assets += (lump_sum - withdrawal_tax)
            state.pension.pillar_3a_capital = 0.0 

        if not is_retired:
            # --- STRICT CASHFLOW ACCOUNTING (Accumulation) ---
            gross_income = state.financial.gross_income_primary + state.financial.gross_income_spouse
            taxable_income = gross_income - state.pension.annual_3a_contribution
            
            # BVG Buy-In Logic (Safeguarded against running out of cash)
            safe_cash_buffer = state.financial.monthly_living_expenses * 3
            actual_bvg_buyin = 0.0
            if state.pension.annual_bvg_buyin > 0 and state.pension.bvg_buy_in_potential > 0 and age < (state.personal.target_retirement_age - 3):
                excess_cash = max(0.0, state.financial.cash_assets - safe_cash_buffer)
                actual_bvg_buyin = min(state.pension.annual_bvg_buyin, state.pension.bvg_buy_in_potential, excess_cash)
                taxable_income -= actual_bvg_buyin
                state.pension.bvg_buy_in_potential -= actual_bvg_buyin
                state.pension.bvg_capital += actual_bvg_buyin

            # Real Estate Math
            mortgage_interest = 0.0
            amortization_cash_out = 0.0
            if state.real_estate and state.real_estate.is_owner:
                mortgage_interest = real_estate.calculate_mortgage_interest(state.real_estate.mortgage_debt, state.real_estate.mortgage_interest_rate)
                taxable_income += real_estate.calculate_eigenmietwert(state.real_estate.market_value)
                taxable_income -= mortgage_interest
                net_wealth += (state.real_estate.market_value - state.real_estate.mortgage_debt)
                
                amortization_cash_out = state.real_estate.annual_amortization_amount
                if state.real_estate.amortization_type == "direct":
                    state.real_estate.mortgage_debt -= amortization_cash_out
                else:
                    state.financial.invested_assets += amortization_cash_out

            # Taxes
            income_tax = tax_zh.calculate_income_tax(taxable_income, state.personal.civil_status, config)
            wealth_tax = tax_zh.calculate_wealth_tax_zh(net_wealth, state.personal.civil_status, config)
            annual_tax += (income_tax + wealth_tax)
            
            # Actual Bank Account Cashflow
            cash_in = gross_income
            cash_out = (state.financial.monthly_living_expenses * 12) + annual_tax + state.pension.annual_3a_contribution + actual_bvg_buyin + mortgage_interest + amortization_cash_out
            savings = cash_in - cash_out
            
            if savings > 0:
                state.financial.invested_assets += savings
            else:
                state.financial.cash_assets += savings 
                
            # Pension Standard Compounding
            state.pension.bvg_capital += state.pension.bvg_annual_savings
            state.pension.bvg_capital *= 1.01 # 1% BVG statutory minimum
            state.pension.pillar_3a_capital += state.pension.annual_3a_contribution
            state.pension.pillar_3a_capital *= 1.015 # 1.5% 3a standard yield

        else:
            # --- STRICT CASHFLOW ACCOUNTING (Decumulation) ---
            ahv_pension = pension_ahv_bvg.calculate_ahv_pension(state.personal.civil_status == "married", state.personal.missing_ahv_years, state.personal.target_retirement_age, config)
            bvg_pension = state.pension.bvg_capital * 0.05 
            taxable_income = ahv_pension + bvg_pension
            
            if age < 65:
                annual_tax += pension_ahv_bvg.calculate_ahv_nichterwerbstaetige(net_wealth, taxable_income, config)
                
            annual_tax += tax_zh.calculate_income_tax(taxable_income, state.personal.civil_status, config)
            
            cash_in = ahv_pension + bvg_pension
            cash_out = (state.financial.monthly_living_expenses * 12) + annual_tax
            gap = cash_out - cash_in
            
            if gap > 0:
                if state.financial.cash_assets >= gap:
                    state.financial.cash_assets -= gap
                else:
                    remaining_gap = gap - state.financial.cash_assets
                    state.financial.cash_assets = 0
                    state.financial.invested_assets -= remaining_gap
                    if state.financial.invested_assets < 0:
                        state.financial.invested_assets = 0 # Out of money
            elif gap < 0:
                state.financial.cash_assets += abs(gap) # Save the surplus

        # Free Wealth Compounding
        state.financial.invested_assets *= (1.0 + cap_growth)
        state.financial.invested_assets += (state.financial.invested_assets * yield_rate) 
        
        total_tax_paid += annual_tax
        timeline.append({"age": age, "year": current_year, "wealth": max(0.0, state.financial.cash_assets + state.financial.invested_assets), "tax": annual_tax})
        current_year += 1

    return timeline, total_tax_paid
