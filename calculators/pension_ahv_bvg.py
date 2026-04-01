from typing import Dict

def calculate_ahv_nichterwerbstaetige(wealth: float, pension_income: float, config: Dict) -> float:
    basis = wealth + (pension_income * 20)
    brackets = config["ahv_early_retirement_brackets"]
    for bracket in reversed(brackets):
        if basis >= bracket["threshold"]:
            return bracket["contribution"]
    return 514.00

def calculate_ahv_pension(is_married: bool, missing_years: int, retirement_age: int, config: Dict) -> float:
    max_pension = config["meta"]["max_ahv_pension_married"] if is_married else config["meta"]["max_ahv_pension_single"]
    gap_penalty = max(0.0, 1.0 - (missing_years / 44.0))
    pension = max_pension * gap_penalty
    
    if retirement_age < 65:
        years_early = 65 - retirement_age
        pension *= (1.0 - (0.068 * years_early))
    elif retirement_age > 65:
        years_late = min(5, retirement_age - 65)
        pension *= (1.0 + (0.052 * years_late))
        
    return pension
