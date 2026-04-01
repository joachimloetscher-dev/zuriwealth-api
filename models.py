from pydantic import BaseModel, Field
from typing import List, Optional

class PersonalData(BaseModel):
    current_age: int
    spouse_age: Optional[int] = None
    target_retirement_age: int = Field(..., le=70, ge=58)
    civil_status: str # "single" or "married"
    children: int = 0
    religion: str = "none"
    permit_type: str # "C", "B", "Swiss"
    missing_ahv_years: int = 0

class FinancialData(BaseModel):
    gross_income_primary: float
    gross_income_spouse: float = 0.0
    monthly_living_expenses: float
    cash_assets: float
    invested_assets: float
    risk_profile: str # "conservative", "balanced", "growth"

class PensionData(BaseModel):
    bvg_capital: float = 0.0
    bvg_annual_savings: float = 0.0
    bvg_buy_in_potential: float = 0.0
    pillar_3a_capital: float = 0.0
    pillar_3a_accounts_count: int = 1
    annual_3a_contribution: float = 0.0
    stagger_3a_withdrawals: bool = False

class RealEstateData(BaseModel):
    is_owner: bool
    market_value: float = 0.0
    mortgage_debt: float = 0.0
    mortgage_interest_rate: float = 0.0
    amortization_type: str = "direct" # "direct" or "indirect"
    annual_amortization_amount: float = 0.0

class SimulationRequest(BaseModel):
    personal: PersonalData
    financial: FinancialData
    pension: PensionData
    real_estate: Optional[RealEstateData] = None

class TimeSeriesPoint(BaseModel):
    age: int
    year: int
    wealth_status_quo: float
    wealth_optimized: float
    tax_paid_status_quo: float
    tax_paid_optimized: float

class ActionPlanItem(BaseModel):
    trigger_age: int
    trigger_year: int
    category: str
    action_title: str
    action_description: str
    financial_impact_chf: float

class MetaData(BaseModel):
    marginal_tax_rate: float
    pension_gap_monthly: float
    tragbarkeit_status: str
    requires_nov_filing: bool
    total_tax_saved_lifetime: float

class SimulationResponse(BaseModel):
    meta_data: MetaData
    time_series: List[TimeSeriesPoint]
    action_plan: List[ActionPlanItem]
