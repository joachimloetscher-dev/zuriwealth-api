import copy
from typing import Dict
from models import SimulationRequest, ActionPlanItem, MetaData, SimulationResponse, TimeSeriesPoint
from engine import simulation
from calculators import tax_zh, real_estate, pension_ahv_bvg

def run_optimization(req: SimulationRequest, config: Dict) -> SimulationResponse:
    # 1. Run Status Quo
    timeline_sq, tax_sq = simulation.run_simulation(req, config)
    
    # 2. Apply Rule Engine
    opt_req = copy.deepcopy(req)
    action_plan = []
    current_year = config["meta"]["year"]
    
    if opt_req.personal.permit_type in ["B", "L"] and opt_req.financial.gross_income_primary < 120000:
        action_plan.append(ActionPlanItem(
            trigger_age=opt_req.personal.current_age, trigger_year=current_year, category="tax",
            action_title="File NOV (Tarifkorrektur)", action_description="File a tax return to claim deductions.",
            financial_impact_chf=0.0
        ))

    if opt_req.real_estate and opt_req.real_estate.is_owner and opt_req.real_estate.amortization_type == "direct":
        opt_req.real_estate.amortization_type = "indirect"
        action_plan.append(ActionPlanItem(
            trigger_age=opt_req.personal.current_age, trigger_year=current_year, category="real_estate",
            action_title="Switch to Indirect Amortization", action_description="Pledge Pillar 3a instead of direct paydown.",
            financial_impact_chf=1500.0
        ))

    safe_buffer = opt_req.financial.monthly_living_expenses * 3
    max_3a = config["meta"]["max_3a_contribution"]
    
    if opt_req.financial.cash_assets > safe_buffer and opt_req.pension.annual_3a_contribution < max_3a:
        opt_req.pension.annual_3a_contribution = max_3a
        opt_req.financial.cash_assets -= max_3a
        action_plan.append(ActionPlanItem(
            trigger_age=opt_req.personal.current_age, trigger_year=current_year, category="tax",
            action_title="Max out Pillar 3a", action_description=f"Invest CHF {max_3a} into Pillar 3a.",
            financial_impact_chf=2000.0
        ))

    if opt_req.pension.pillar_3a_accounts_count > 1:
        opt_req.pension.stagger_3a_withdrawals = True
        action_plan.append(ActionPlanItem(
            trigger_age=opt_req.personal.target_retirement_age - 2, 
            trigger_year=current_year + (opt_req.personal.target_retirement_age - 2 - opt_req.personal.current_age),
            category="retirement", action_title="Staggered 3a Withdrawal", 
            action_description="Withdraw 3a accounts across different years to break tax progression.",
            financial_impact_chf=3500.0
        ))

    # 3. Run Optimized Simulation
    timeline_opt, tax_opt = simulation.run_simulation(opt_req, config)
    
    # 4. Compile MetaData
    marginal_rate = tax_zh.calculate_marginal_tax_rate(req.financial.gross_income_primary, req.personal.civil_status, config)
    ahv = pension_ahv_bvg.calculate_ahv_pension(req.personal.civil_status=="married", req.personal.missing_ahv_years, req.personal.target_retirement_age, config)
    bvg = req.pension.bvg_capital * 0.05
    gap = req.financial.monthly_living_expenses - ((ahv + bvg)/12)
    
    tragbarkeit = "N/A"
    if req.real_estate and req.real_estate.is_owner:
        is_afford = real_estate.check_tragbarkeit(req.real_estate.market_value, req.real_estate.mortgage_debt, ahv+bvg)
        tragbarkeit = "Pass" if is_afford else "Fail"

    meta = MetaData(
        marginal_tax_rate=marginal_rate,
        pension_gap_monthly=max(0.0, gap),
        tragbarkeit_status=tragbarkeit,
        requires_nov_filing=(opt_req.personal.permit_type in ["B", "L"]),
        total_tax_saved_lifetime=tax_sq - tax_opt
    )

    # 5. Merge Timelines
    merged_timeline = [TimeSeriesPoint(
        age=sq["age"], year=sq["year"],
        wealth_status_quo=sq["wealth"], wealth_optimized=opt["wealth"],
        tax_paid_status_quo=sq["tax"], tax_paid_optimized=opt["tax"]
    ) for sq, opt in zip(timeline_sq, timeline_opt)]

    return SimulationResponse(meta_data=meta, time_series=merged_timeline, action_plan=action_plan)