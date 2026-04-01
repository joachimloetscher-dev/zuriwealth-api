from typing import Dict

def calculate_income_tax(taxable_income: float, civil_status: str, config: Dict) -> float:
    if taxable_income <= 0:
        return 0.0

    tariff_type = "married" if civil_status.lower() in ["married", "registered_partnership"] else "single"
    brackets = config["income_tax_brackets"][tariff_type]

    base_tax = 0.0
    for bracket in reversed(brackets):
        if taxable_income > bracket["threshold"]:
            excess_amount = taxable_income - bracket["threshold"]
            marginal_tax = excess_amount * bracket["marginal_rate"]
            base_tax = bracket["base_amount"] + marginal_tax
            break
            
    total_multiplier = config["meta"]["cantonal_steuerfuss"] + config["meta"]["municipal_steuerfuss"]
    return base_tax * total_multiplier

def calculate_wealth_tax_zh(net_wealth: float, civil_status: str, config: Dict) -> float:
    is_married = civil_status.lower() in ["married", "registered_partnership"]
    freibetrag = config["wealth_tax"]["freibetrag_married"] if is_married else config["wealth_tax"]["freibetrag_single"]
    
    taxable_wealth = max(0.0, net_wealth - freibetrag)
    if taxable_wealth == 0.0:
        return 0.0
        
    base_tax = 0.0
    brackets = config["wealth_tax"]["brackets"]
    
    for i in range(len(brackets)):
        current_threshold = brackets[i]["threshold"]
        rate = brackets[i]["rate"]
        next_threshold = brackets[i+1]["threshold"] if i + 1 < len(brackets) else float('inf')
        
        wealth_in_bracket = max(0.0, min(taxable_wealth, next_threshold) - current_threshold)
        base_tax += wealth_in_bracket * rate
        
        if taxable_wealth <= next_threshold:
            break
            
    total_multiplier = config["meta"]["cantonal_steuerfuss"] + config["meta"]["municipal_steuerfuss"]
    return base_tax * total_multiplier

def calculate_marginal_tax_rate(taxable_income: float, civil_status: str, config: Dict) -> float:
    tax_base = calculate_income_tax(taxable_income, civil_status, config)
    tax_plus_1000 = calculate_income_tax(taxable_income + 1000, civil_status, config)
    return (tax_plus_1000 - tax_base) / 1000.0

def calculate_capital_withdrawal_tax(amount: float, civil_status: str, config: Dict) -> float:
    if amount <= 0:
        return 0.0
    
    brackets = config["capital_withdrawal_tax_brackets"]
    base_tax = 0.0
    
    for bracket in reversed(brackets):
        if amount > bracket["threshold"]:
            excess = amount - bracket["threshold"]
            base_tax += excess * bracket["rate"]
            amount = bracket["threshold"]
            
    total_multiplier = config["meta"]["cantonal_steuerfuss"] + config["meta"]["municipal_steuerfuss"]
    return base_tax * total_multiplier