def calculate_eigenmietwert(market_value: float) -> float:
    return market_value * 0.04 * 0.70

def calculate_mortgage_interest(debt: float, rate: float) -> float:
    return debt * rate

def check_tragbarkeit(market_value: float, mortgage_debt: float, retirement_income_annual: float) -> bool:
    imputed_costs = (mortgage_debt * 0.05) + (market_value * 0.01)
    max_allowed = retirement_income_annual * 0.33
    return imputed_costs <= max_allowed
