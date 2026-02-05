"""
TCO Calculator V2 - Scenario 2: Finance Vehicles
Vehicles are financed with down payments and monthly payments over 7 years.
Chargers are purchased upfront (same as Scenario 1).
"""

from dataclasses import dataclass
from typing import List

try:
    from .parameters import TCOParameters
    from .scenario_1 import YearCosts
except ImportError:
    from parameters import TCOParameters
    from scenario_1 import YearCosts


def calculate_monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """Calculate monthly loan payment using PMT formula.
    
    PMT = PV × (r × (1+r)^n) / ((1+r)^n - 1)
    where:
        PV = principal (loan amount)
        r = monthly interest rate
        n = number of monthly payments
    """
    if annual_rate == 0:
        return principal / (years * 12)
    
    monthly_rate = annual_rate / 12
    num_payments = years * 12
    
    payment = principal * (monthly_rate * (1 + monthly_rate)**num_payments) / \
              ((1 + monthly_rate)**num_payments - 1)
    
    return payment


def _declining_balance_residual(cost: float, rate: float, years: int) -> float:
    """Compute residual using declining balance with half-year rule in year 1."""
    residual = cost
    if years <= 0:
        return residual
    # Half-year rule in first year
    residual -= residual * rate * 0.5
    years -= 1
    # Full rate for remaining years
    for _ in range(years):
        residual -= residual * rate
    return residual


class Scenario2Calculator:
    """Calculate TCO for Scenario 2: Finance Vehicles + Purchase Chargers Upfront
    
    Key differences from Scenario 1:
    - Vehicles financed with down payment + monthly payments
    - EV rebate reduces the financed amount (not Year 1 credit)
    - Chargers purchased upfront (same as Scenario 1)
    """
    
    def __init__(self, params: TCOParameters):
        self.params = params
        self.years: List[YearCosts] = []
        
        # Cumulative depreciation tracking (same as Scenario 1)
        self._ice_cumulative_depreciation = 0.0
        self._ev_cumulative_depreciation = 0.0
        self._charger_cumulative_depreciation = 0.0
        self._charger_cost_year1 = 0.0
        self._prev_cfr_lcfs_credit = 0.0
        
        # Financing calculations
        self._ice_down_payment = params.ice_msrp * params.ice_down_payment_pct
        self._ice_financed = params.ice_msrp - self._ice_down_payment
        self._ice_monthly_payment = calculate_monthly_payment(
            self._ice_financed, params.ice_interest_rate, params.ice_loan_term_years
        )
        
        # EV: Rebate reduces financed amount (NOT a Year 1 credit in Scenario 2)
        self._ev_down_payment = params.ev_msrp * params.ev_down_payment_pct
        self._ev_financed = (params.ev_msrp - params.ev_federal_rebate) - self._ev_down_payment
        self._ev_monthly_payment = calculate_monthly_payment(
            self._ev_financed, params.ev_interest_rate, params.ev_loan_term_years
        )
    
    def calculate(self) -> List[YearCosts]:
        """Calculate all years (1-7 + salvage + total)
        
        Returns 9 YearCosts entries matching Excel structure.
        """
        self.years = []
        ice_cumulative = 0.0
        ev_cumulative = 0.0
        
        # Years 1-7
        for year in range(1, 8):
            year_costs = self._calculate_year(year, ice_cumulative, ev_cumulative)
            self.years.append(year_costs)
            ice_cumulative = year_costs.ice_cumulative
            ev_cumulative = year_costs.ev_cumulative
        
        # Year 8: Salvage
        salvage = self._calculate_salvage_year(ice_cumulative, ev_cumulative)
        self.years.append(salvage)
        
        # Year 9: Total
        total = self._calculate_total_row()
        self.years.append(total)
        
        return self.years
    
    def _calculate_year(self, year: int, prev_ice_cum: float, prev_ev_cum: float) -> YearCosts:
        """Calculate costs for years 1-7 with financing."""
        p = self.params
        
        # === ICE COSTS ===
        # No upfront purchase - replaced by down payment + monthly payments
        ice_purchase = 0.0  # Handled via financing
        
        # Down payment in Year 1
        ice_down_payment = self._ice_down_payment if year == 1 else 0.0
        
        # Monthly payments every year
        ice_annual_payments = self._ice_monthly_payment * 12
        
        # Fuel (same as Scenario 1)
        ice_fuel = (p.ice_efficiency_l_per_km * p.annual_km) * \
                   (p.gasoline_price_per_l * ((1 + p.fuel_price_escalation) ** (year - 1)))
        
        # Carbon tax (same as Scenario 1)
        ice_carbon_tax = (p.ice_efficiency_l_per_km * p.annual_km) * \
                        (p.carbon_tax_per_l * ((1 + p.fuel_price_escalation) ** (year - 1)))
        
        # Maintenance (same as Scenario 1)
        ice_maintenance = (p.ice_maintenance_per_km * p.annual_km) * \
                         ((1 + p.maintenance_escalation) ** (year - 1))
        
        # Insurance (same as Scenario 1)
        ice_insurance = p.ice_insurance_rate * p.ice_msrp
        
        # Depreciation (same as Scenario 1)
        ice_remaining_value = p.ice_msrp - self._ice_cumulative_depreciation
        ice_depreciation = ice_remaining_value * p.ice_depreciation_rate
        self._ice_cumulative_depreciation += ice_depreciation
        
        # === EV COSTS ===
        # No upfront purchase - replaced by down payment + monthly payments
        ev_purchase = 0.0  # Handled via financing
        
        # Down payment in Year 1
        ev_down_payment = self._ev_down_payment if year == 1 else 0.0
        
        # Monthly payments every year
        ev_annual_payments = self._ev_monthly_payment * 12
        
        # Rebates: NOT applied as Year 1 credit in financing scenario
        # (Rebate reduces financed amount, handled in __init__)
        ev_rebates = 0.0
        
        # CFR/LCFS credits (same declining logic as Scenario 1)
        if year < (p.credit_end_year - 2024):
            if year == 1:
                ev_cfr_lcfs_credits = -(p.cfr_credit_annual + p.lcfs_credit_annual)
                self._prev_cfr_lcfs_credit = ev_cfr_lcfs_credits
            else:
                ev_cfr_lcfs_credits = self._prev_cfr_lcfs_credit * (1 - p.lcfs_decline_rate)
                self._prev_cfr_lcfs_credit = ev_cfr_lcfs_credits
        else:
            ev_cfr_lcfs_credits = 0.0
        
        # Charging (same as Scenario 1)
        ev_charging = (p.ev_efficiency_kwh_per_km * p.electricity_price_per_kwh) * \
                      (p.annual_km * ((1 + p.electricity_price_escalation) ** (year - 1)))
        
        # Maintenance (same as Scenario 1)
        ev_maintenance = (p.ev_maintenance_per_km * p.annual_km) * \
                        ((1 + p.maintenance_escalation) ** (year - 1))
        
        # Charger (same as Scenario 1 - purchased upfront)
        ev_charger_cost = (p.charger_cost * p.charger_cost_per_vehicle) if year == 1 else 0.0
        if year == 1:
            self._charger_cost_year1 = ev_charger_cost
        
        # Charger maintenance (same as Scenario 1)
        if year == 1:
            ev_charger_maintenance = self._charger_cost_year1 * p.charger_maintenance_rate
        elif year > 1 and len(self.years) > 0:
            prev_maintenance = self.years[-1].ev_charger_maintenance
            ev_charger_maintenance = prev_maintenance + 1.02
        else:
            ev_charger_maintenance = 0.0
        
        # Insurance (same as Scenario 1)
        ev_insurance = p.ev_msrp * p.ev_insurance_rate
        
        # Vehicle depreciation (same as Scenario 1)
        if year == 1:
            ev_vehicle_depreciation = p.ev_msrp * p.ev_depreciation_rate
        else:
            ev_remaining_value = p.ev_msrp - self._ev_cumulative_depreciation
            ev_vehicle_depreciation = ev_remaining_value * p.ev_depreciation_rate
        self._ev_cumulative_depreciation += ev_vehicle_depreciation
        
        # Charger depreciation (same as Scenario 1)
        if year == 1:
            ev_charger_depreciation = 0.5 * self._charger_cost_year1 * p.charger_depreciation_rate
            self._charger_cumulative_depreciation += ev_charger_depreciation
        elif year > 1:
            remaining_value = self._charger_cost_year1 - self._charger_cumulative_depreciation
            ev_charger_depreciation = remaining_value * p.charger_depreciation_rate
            self._charger_cumulative_depreciation += ev_charger_depreciation
        else:
            ev_charger_depreciation = 0.0
        
        # === TOTALS ===
        ice_total = (ice_down_payment + ice_annual_payments + ice_fuel + ice_carbon_tax +
                    ice_maintenance + ice_insurance)
        ice_cumulative = prev_ice_cum + ice_total
        
        ev_total = (ev_down_payment + ev_annual_payments + ev_cfr_lcfs_credits +
                   ev_charging + ev_maintenance + ev_charger_cost + ev_charger_maintenance +
                   ev_insurance)
        ev_cumulative = prev_ev_cum + ev_total
        
        # Discount factor
        discount_factor = 1.0 / ((1 + p.discount_rate) ** year)
        cumulative_savings = max(ice_cumulative - ev_cumulative, 0)
        ice_discounted = discount_factor * ice_total
        ev_discounted = discount_factor * ev_total
        
        return YearCosts(
            year=year,
            ice_purchase=ice_down_payment + ice_annual_payments,  # Combined financing costs
            ice_fuel=ice_fuel, ice_carbon_tax=ice_carbon_tax, ice_maintenance=ice_maintenance,
            ice_salvage=0.0, ice_insurance=ice_insurance, ice_depreciation=ice_depreciation,
            ev_purchase=ev_down_payment + ev_annual_payments,  # Combined financing costs
            ev_rebates=ev_rebates, ev_cfr_lcfs_credits=ev_cfr_lcfs_credits,
            ev_charging=ev_charging, ev_maintenance=ev_maintenance,
            ev_charger_cost=ev_charger_cost, ev_charger_maintenance=ev_charger_maintenance,
            ev_vehicle_salvage=0.0, ev_charger_salvage=0.0, ev_insurance=ev_insurance,
            ev_vehicle_depreciation=ev_vehicle_depreciation,
            ev_charger_depreciation=ev_charger_depreciation,
            ice_total=ice_total, ice_cumulative=ice_cumulative,
            ev_total=ev_total, ev_cumulative=ev_cumulative,
            discount_factor=discount_factor, cumulative_savings=cumulative_savings,
            ice_discounted=ice_discounted, ev_discounted=ev_discounted
        )
    
    def _calculate_salvage_year(self, prev_ice_cum: float, prev_ev_cum: float) -> YearCosts:
        """Calculate salvage year using traditional residual values.
        
        For Scenario 2 (Finance vehicles + Purchase chargers):
        - ICE: Residual value based on depreciation (includes charger salvage since fleet owns it)
        - EV: Residual value based on depreciation (vehicle only)
        - Chargers: Residual value is added to ICE column (they're owned by the fleet)
        
        Note: In Excel, charger salvage (AD column) is included in the ICE total (Q column),
        not in the EV total (AF column), because the fleet OWNS the chargers.
        """
        p = self.params
        
        # Vehicle residual values (declining balance with half-year rule to mirror Excel)
        ice_residual = _declining_balance_residual(p.ice_msrp, p.ice_depreciation_rate, 7)
        ice_vehicle_salvage = -ice_residual
        
        ev_vehicle_residual = _declining_balance_residual(p.ev_msrp, p.ev_depreciation_rate, 7)
        ev_vehicle_salvage = -ev_vehicle_residual
        
        # Charger residual (purchased upfront in Scenario 2, so salvage benefits both)
        charger_cost = p.charger_cost * p.charger_cost_per_vehicle
        charger_residual = _declining_balance_residual(charger_cost, p.charger_depreciation_rate, 7)
        charger_salvage = -charger_residual
        
        # Excel places charger salvage in AD (EV side) and sums into AF.
        # ICE salvage (Q column) reflects vehicle only.
        ice_total = ice_vehicle_salvage
        ice_cumulative = prev_ice_cum + ice_total
        
        # EV includes both vehicle and charger salvage (fleet owns chargers)
        ev_total = ev_vehicle_salvage + charger_salvage
        ev_cumulative = prev_ev_cum + ev_total
        
        discount_factor = 1.0 / ((1 + p.discount_rate) ** 8)
        cumulative_savings = max(ice_cumulative - ev_cumulative, 0)
        ice_discounted = discount_factor * ice_total
        ev_discounted = discount_factor * ev_total
        
        return YearCosts(
            year=8,
            ice_purchase=0.0, ice_fuel=0.0, ice_carbon_tax=0.0, ice_maintenance=0.0,
            ice_salvage=ice_vehicle_salvage, ice_insurance=0.0, ice_depreciation=0.0,
            ev_purchase=0.0, ev_rebates=0.0, ev_cfr_lcfs_credits=0.0,
            ev_charging=0.0, ev_maintenance=0.0, ev_charger_cost=0.0,
            ev_charger_maintenance=0.0, ev_vehicle_salvage=ev_vehicle_salvage,
            ev_charger_salvage=charger_salvage, ev_insurance=0.0,
            ev_vehicle_depreciation=0.0, ev_charger_depreciation=0.0,
            ice_total=ice_total, ice_cumulative=ice_cumulative,
            ev_total=ev_total, ev_cumulative=ev_cumulative,
            discount_factor=discount_factor, cumulative_savings=cumulative_savings,
            ice_discounted=ice_discounted, ev_discounted=ev_discounted
        )
    
    def _calculate_total_row(self) -> YearCosts:
        """Calculate total row (sum of all years)."""
        if len(self.years) < 8:
            raise ValueError("Must have at least 8 years calculated")
        
        if len(self.years) < 8:
            raise ValueError("Must have at least 8 years calculated")
        
        # Sum all years to get nominal totals
        ice_total = sum(y.ice_total for y in self.years)
        ev_total = sum(y.ev_total for y in self.years)
        ice_cumulative = ice_total
        ev_cumulative = ev_total
        cumulative_savings = max(ice_cumulative - ev_cumulative, 0)
        ice_discounted = sum(y.ice_discounted for y in self.years)
        ev_discounted = sum(y.ev_discounted for y in self.years)
        
        return YearCosts(
            year=9,
            ice_purchase=sum(y.ice_purchase for y in self.years),
            ice_fuel=sum(y.ice_fuel for y in self.years),
            ice_carbon_tax=sum(y.ice_carbon_tax for y in self.years),
            ice_maintenance=sum(y.ice_maintenance for y in self.years),
            ice_salvage=sum(y.ice_salvage for y in self.years),
            ice_insurance=sum(y.ice_insurance for y in self.years),
            ice_depreciation=sum(y.ice_depreciation for y in self.years),
            ev_purchase=sum(y.ev_purchase for y in self.years),
            ev_rebates=sum(y.ev_rebates for y in self.years),
            ev_cfr_lcfs_credits=sum(y.ev_cfr_lcfs_credits for y in self.years),
            ev_charging=sum(y.ev_charging for y in self.years),
            ev_maintenance=sum(y.ev_maintenance for y in self.years),
            ev_charger_cost=sum(y.ev_charger_cost for y in self.years),
            ev_charger_maintenance=sum(y.ev_charger_maintenance for y in self.years),
            ev_vehicle_salvage=sum(y.ev_vehicle_salvage for y in self.years),
            ev_charger_salvage=sum(y.ev_charger_salvage for y in self.years),
            ev_insurance=sum(y.ev_insurance for y in self.years),
            ev_vehicle_depreciation=sum(y.ev_vehicle_depreciation for y in self.years),
            ev_charger_depreciation=sum(y.ev_charger_depreciation for y in self.years),
            ice_total=ice_total, ice_cumulative=ice_cumulative,
            ev_total=ev_total, ev_cumulative=ev_cumulative,
            discount_factor=0.0, cumulative_savings=cumulative_savings,
            ice_discounted=ice_discounted, ev_discounted=ev_discounted
        )


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tco_calculator_v2.parameters import load_parameters_from_excel
    
    excel_path = Path("/Users/danikae/Git/tco_model/excel_tool/7_year_TCO_Canada.xlsx")
    params = load_parameters_from_excel(excel_path, scenario=2)
    
    print("=" * 100)
    print("SCENARIO 2: FINANCE VEHICLES + PURCHASE CHARGERS UPFRONT")
    print("=" * 100)
    
    calculator = Scenario2Calculator(params)
    
    print(f"\nFinancing Details:")
    print(f"  ICE Down Payment: ${calculator._ice_down_payment:,.2f}")
    print(f"  ICE Financed: ${calculator._ice_financed:,.2f}")
    print(f"  ICE Monthly Payment: ${calculator._ice_monthly_payment:,.2f}")
    print(f"  EV Down Payment: ${calculator._ev_down_payment:,.2f}")
    print(f"  EV Financed (after rebate): ${calculator._ev_financed:,.2f}")
    print(f"  EV Monthly Payment: ${calculator._ev_monthly_payment:,.2f}")
    
    years = calculator.calculate()
    totals = years[-1]
    
    print(f"\n{'Year':<6} {'ICE Total':>12} {'EV Total':>12} {'ICE Cum':>12} {'EV Cum':>12} {'Savings':>12}")
    print("-" * 72)
    
    for year_costs in years:
        year_label = str(year_costs.year) if year_costs.year <= 7 else ("Salvage" if year_costs.year == 8 else "TOTAL")
        print(f"{year_label:<6} ${year_costs.ice_total:>11,.0f} ${year_costs.ev_total:>11,.0f} " +
              f"${year_costs.ice_cumulative:>11,.0f} ${year_costs.ev_cumulative:>11,.0f} " +
              f"${year_costs.cumulative_savings:>11,.0f}")
    
    print(f"\n{'=' * 100}")
    print("VALIDATION AGAINST EXCEL:")
    print(f"{'=' * 100}")
    print(f"ICE Total:    Python=${totals.ice_total:,.2f}    Excel=$180,707.44")
    print(f"EV Total:     Python=${totals.ev_total:,.2f}     Excel=$163,928.01")
    print(f"Savings:      Python=${totals.cumulative_savings:,.2f}    Excel=$16,779.44")
    
    ice_diff = abs(totals.ice_total - 180707.44)
    ev_diff = abs(totals.ev_total - 163928.01)
    savings_diff = abs(totals.cumulative_savings - 16779.44)
    
    print(f"\nDifferences:")
    print(f"  ICE:     ${ice_diff:,.2f} {'✅' if ice_diff < 1.0 else '❌'}")
    print(f"  EV:      ${ev_diff:,.2f} {'✅' if ev_diff < 1.0 else '❌'}")
    print(f"  Savings: ${savings_diff:,.2f} {'✅' if savings_diff < 1.0 else '❌'}")
