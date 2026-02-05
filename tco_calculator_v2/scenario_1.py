"""
TCO Calculator V2 - Scenario 1: Purchase Upfront
Faithful replication of Excel formulas for purchase scenario
Matches Excel rows 3-13 (Years 0-7 + Salvage)
"""

from dataclasses import dataclass
from typing import List
from .parameters import TCOParameters


@dataclass
class YearCosts:
    """All cost components for a single year"""
    year: int  # 0-7, or 8 for salvage year
    
    # ICE costs
    ice_purchase: float
    ice_fuel: float
    ice_carbon_tax: float
    ice_maintenance: float
    ice_salvage: float
    ice_insurance: float
    ice_depreciation: float
    
    # EV costs
    ev_purchase: float
    ev_rebates: float
    ev_cfr_lcfs_credits: float
    ev_charging: float
    ev_maintenance: float
    ev_charger_cost: float
    ev_charger_maintenance: float
    ev_vehicle_salvage: float
    ev_charger_salvage: float
    ev_insurance: float
    ev_vehicle_depreciation: float
    ev_charger_depreciation: float
    
    # Computed totals
    ice_total: float
    ice_cumulative: float
    ev_total: float
    ev_cumulative: float
    
    # Analysis
    discount_factor: float
    cumulative_savings: float
    ice_discounted: float
    ev_discounted: float


class Scenario1Calculator:
    """Calculate TCO for Scenario 1: Purchase Upfront
    
    Excel Structure (matches rows 3-13 in calculation sheet):
    - Row 3 (Year 0): Empty - no costs, present day baseline
    - Row 4 (Year 1): Vehicle purchases + Year 1 operational costs
    - Rows 5-10 (Years 2-7): Operational costs only
    - Row 11 (Salvage Year): Residual values
    
    Key insight: Purchases happen in Year 1, not Year 0
    """
    
    def __init__(self, params: TCOParameters):
        self.params = params
        self.years: List[YearCosts] = []
        self._ice_cumulative_depreciation = 0.0
        self._ev_cumulative_depreciation = 0.0
        self._charger_cumulative_depreciation = 0.0
        self._charger_cost_year1 = 0.0  # Track for maintenance calculations
        self._prev_cfr_lcfs_credit = 0.0  # Track for declining CFR/LCFS
    
    def calculate(self) -> List[YearCosts]:
        """
        Calculate all years (1-7 + salvage + total)
        Returns list of YearCosts with 9 entries (Excel rows 4-12)
        
        Excel Row 4: Year 1 with purchases
        Excel Row 5: Year 2
        ...
        Excel Row 10: Year 7
        Excel Row 11: Salvage year (residual values, negative)
        Excel Row 12: Total (sum of rows 4-11)
        """
        self.years = []
        ice_cumulative = 0.0
        ev_cumulative = 0.0
        
        # Years 1-7: Calculate all operational years
        for year in range(1, 8):
            year_costs = self._calculate_year(year, ice_cumulative, ev_cumulative)
            self.years.append(year_costs)
            ice_cumulative = year_costs.ice_cumulative
            ev_cumulative = year_costs.ev_cumulative
        
        # Year 8: Salvage year (Row 11 in Excel) - residual values
        salvage = self._calculate_salvage_year(ice_cumulative, ev_cumulative)
        self.years.append(salvage)
        
        # Year 9: Total row (Row 12 in Excel) - sum of all previous rows
        total = self._calculate_total_row()
        self.years.append(total)
        
        return self.years
    
    def _calculate_year(self, year: int, prev_ice_cum: float, prev_ev_cum: float) -> YearCosts:
        """Calculate costs for years 1-7
        
        Year 1: Vehicle purchases + operational costs
        Years 2-7: Operational costs only
        """
        p = self.params
        
        # === ICE COSTS ===
        ice_purchase = p.ice_msrp if year == 1 else 0.0
        
        # Fuel: uses (year-1) as exponent for escalation
        ice_fuel = (p.ice_efficiency_l_per_km * p.annual_km) * (
            p.gasoline_price_per_l * ((1 + p.fuel_price_escalation) ** (year - 1))
        )
        
        # Carbon tax: uses (year-1) as exponent
        ice_carbon_tax = (p.ice_efficiency_l_per_km * p.annual_km) * (
            p.carbon_tax_per_l * ((1 + p.fuel_price_escalation) ** (year - 1))
        )
        
        # Maintenance: uses (year-1) as exponent
        ice_maintenance = (p.ice_maintenance_per_km * p.annual_km) * (
            (1 + p.maintenance_escalation) ** (year - 1)
        )
        
        # Insurance: constant % of MSRP each year
        ice_insurance = p.ice_insurance_rate * p.ice_msrp
        
        # Depreciation: declining balance on remaining book value
        # Formula: (purchase - cumulative_depreciation) * rate
        ice_remaining_value = p.ice_msrp - self._ice_cumulative_depreciation
        ice_depreciation = ice_remaining_value * p.ice_depreciation_rate
        self._ice_cumulative_depreciation += ice_depreciation
        
        # === EV COSTS ===
        ev_purchase = p.ev_msrp if year == 1 else 0.0
        
        # Rebates and incentives: only in Year 1
        ev_rebates = -(p.ev_federal_rebate + p.charger_incentives) if year == 1 else 0.0
        
        # CFR/LCFS credits: decline annually (each year = previous * (1 - decline_rate)), stop after credit_end_year
        if year < (p.credit_end_year - 2024):  # Strictly less than (not <=)
            if year == 1:
                # Year 1: =-B41-B43
                ev_cfr_lcfs_credits = -(p.cfr_credit_annual + p.lcfs_credit_annual)
                self._prev_cfr_lcfs_credit = ev_cfr_lcfs_credits
            else:
                # Year N>1: =previous * (1 - decline_rate) = previous - (previous * decline_rate)
                ev_cfr_lcfs_credits = self._prev_cfr_lcfs_credit * (1 - p.lcfs_decline_rate)
                self._prev_cfr_lcfs_credit = ev_cfr_lcfs_credits
        else:
            ev_cfr_lcfs_credits = 0.0
        
        # Charging: uses (year-1) as exponent for escalation
        ev_charging = (p.ev_efficiency_kwh_per_km * p.electricity_price_per_kwh) * (
            p.annual_km * ((1 + p.electricity_price_escalation) ** (year - 1))
        )
        
        # Maintenance: uses (year-1) as exponent
        ev_maintenance = (p.ev_maintenance_per_km * p.annual_km) * (
            (1 + p.maintenance_escalation) ** (year - 1)
        )
        
        # Charger cost: only in Year 1
        ev_charger_cost = (p.charger_cost * p.charger_cost_per_vehicle) if year == 1 else 0.0
        if year == 1:
            self._charger_cost_year1 = ev_charger_cost
        
        # Charger maintenance: Y4=X4*B17, then Y5=Y4+1.02, Y6=Y5+1.02 (additive escalation!)
        if year == 1:
            ev_charger_maintenance = self._charger_cost_year1 * p.charger_maintenance_rate
        elif year > 1 and len(self.years) > 0:
            # Get previous year's maintenance and add 1.02 (not multiply!)
            prev_maintenance = self.years[-1].ev_charger_maintenance
            ev_charger_maintenance = prev_maintenance + 1.02
        else:
            ev_charger_maintenance = 0.0
        
        # Insurance: constant % of MSRP each year
        ev_insurance = p.ev_msrp * p.ev_insurance_rate
        
        # EV vehicle depreciation: declining balance
        # AE4 = S4*B26, AE5+ = (S4-SUM(AE4:AEn-1))*B26
        if year == 1:
            ev_vehicle_depreciation = p.ev_msrp * p.ev_depreciation_rate
        else:
            ev_remaining_value = p.ev_msrp - self._ev_cumulative_depreciation
            ev_vehicle_depreciation = ev_remaining_value * p.ev_depreciation_rate
        
        self._ev_cumulative_depreciation += ev_vehicle_depreciation
        
        # Charger depreciation: CCA declining balance with half-year rule
        # AF4 = 0.5*B37*rate, AF5+ = (B37-SUM(AF4:AFn-1))*rate
        # Rate is B28 (Class 43.2 = 0.5) or B27 (Class 43.1 = 0.3)
        # For now, assume B28 is always used (matches L2 7.2kW charger)
        charger_depreciation_rate = p.charger_depreciation_rate  # This is B28 = 0.5
        
        if year == 1:
            ev_charger_depreciation = (
                0.5 * self._charger_cost_year1 * charger_depreciation_rate
            )
            self._charger_cumulative_depreciation += ev_charger_depreciation
        elif year > 1:
            remaining_value = self._charger_cost_year1 - self._charger_cumulative_depreciation
            ev_charger_depreciation = remaining_value * charger_depreciation_rate
            self._charger_cumulative_depreciation += ev_charger_depreciation
        else:
            ev_charger_depreciation = 0.0
        
        # === TOTALS ===
        ice_total = ice_purchase + ice_fuel + ice_carbon_tax + ice_maintenance + ice_insurance
        ice_cumulative = prev_ice_cum + ice_total
        
        ev_total = (
            ev_purchase + ev_rebates + ev_cfr_lcfs_credits + ev_charging + ev_maintenance +
            ev_charger_cost + ev_charger_maintenance + ev_insurance
        )
        ev_cumulative = prev_ev_cum + ev_total
        
        # Discount factor: 1/(1+rate)^year, starts at 0.9615 for year 1
        discount_factor = 1.0 / ((1 + p.discount_rate) ** year)
        
        # Cumulative savings
        cumulative_savings = max(ice_cumulative - ev_cumulative, 0)
        
        # Discounted costs
        ice_discounted = discount_factor * ice_total
        ev_discounted = discount_factor * ev_total
        
        return YearCosts(
            year=year,
            ice_purchase=ice_purchase, ice_fuel=ice_fuel, ice_carbon_tax=ice_carbon_tax,
            ice_maintenance=ice_maintenance, ice_salvage=0.0, ice_insurance=ice_insurance,
            ice_depreciation=ice_depreciation,
            ev_purchase=ev_purchase, ev_rebates=ev_rebates, ev_cfr_lcfs_credits=ev_cfr_lcfs_credits,
            ev_charging=ev_charging, ev_maintenance=ev_maintenance, ev_charger_cost=ev_charger_cost,
            ev_charger_maintenance=ev_charger_maintenance, ev_vehicle_salvage=0.0,
            ev_charger_salvage=0.0, ev_insurance=ev_insurance,
            ev_vehicle_depreciation=ev_vehicle_depreciation, ev_charger_depreciation=ev_charger_depreciation,
            ice_total=ice_total, ice_cumulative=ice_cumulative, ev_total=ev_total, ev_cumulative=ev_cumulative,
            discount_factor=discount_factor, cumulative_savings=cumulative_savings,
            ice_discounted=ice_discounted, ev_discounted=ev_discounted
        )
    
    def _calculate_salvage_year(self, prev_ice_cum: float, prev_ev_cum: float) -> YearCosts:
        """Calculate salvage year (Year 8, Row 11 in Excel)
        
        This row contains ONLY the residual/salvage values, NOT annual costs.
        Salvage values are negative (credits).
        
        After 7 years of declining depreciation, calculate what's left.
        """
        p = self.params
        
        # ICE residual value after 7 years of depreciation
        # Depreciation formula: each year depreciates the remaining value by the depreciation rate
        # After 7 years: remaining = MSRP * (1 - rate)^7
        ice_residual = p.ice_msrp * ((1 - p.ice_depreciation_rate) ** 7)
        ice_salvage = -ice_residual  # Negative = credit
        
        # EV vehicle residual value after 7 years
        ev_vehicle_residual = p.ev_msrp * ((1 - p.ev_depreciation_rate) ** 7)
        ev_vehicle_salvage = -ev_vehicle_residual
        
        # Charger residual value: first year deduction + remaining years
        # Year 1 depreciation: 0.5 * charger_cost * rate
        # Remaining: charger_cost * (1 - 0.5*rate) * (1 - rate)^6
        charger_cost = p.charger_cost * p.charger_cost_per_vehicle
        charger_residual = charger_cost * (1 - 0.5 * p.charger_depreciation_rate) * ((1 - p.charger_depreciation_rate) ** 6)
        ev_charger_salvage = -charger_residual
        
        # Salvage year totals (only salvage values, no other costs)
        ice_total = ice_salvage
        ice_cumulative = prev_ice_cum + ice_total
        
        ev_total = ev_vehicle_salvage + ev_charger_salvage
        ev_cumulative = prev_ev_cum + ev_total
        
        # Discount factor for salvage year (Year 8 in Excel = row 11)
        discount_factor = 1.0 / ((1 + p.discount_rate) ** 8)
        
        # Final savings
        cumulative_savings = max(ice_cumulative - ev_cumulative, 0)
        
        # Discounted values
        ice_discounted = discount_factor * ice_total
        ev_discounted = discount_factor * ev_total
        
        return YearCosts(
            year=8,
            ice_purchase=0.0, ice_fuel=0.0, ice_carbon_tax=0.0, ice_maintenance=0.0,
            ice_salvage=ice_salvage, ice_insurance=0.0, ice_depreciation=0.0,
            ev_purchase=0.0, ev_rebates=0.0, ev_cfr_lcfs_credits=0.0, ev_charging=0.0,
            ev_maintenance=0.0, ev_charger_cost=0.0, ev_charger_maintenance=0.0,
            ev_vehicle_salvage=ev_vehicle_salvage, ev_charger_salvage=ev_charger_salvage,
            ev_insurance=0.0, ev_vehicle_depreciation=0.0, ev_charger_depreciation=0.0,
            ice_total=ice_total, ice_cumulative=ice_cumulative, ev_total=ev_total,
            ev_cumulative=ev_cumulative, discount_factor=discount_factor,
            cumulative_savings=cumulative_savings, ice_discounted=ice_discounted,
            ev_discounted=ev_discounted
        )
    
    def _calculate_total_row(self) -> YearCosts:
        """Calculate total row (Row 12 in Excel)
        
        This is the SUM of rows 4-11 (Years 1-7 + Salvage)
        """
        if len(self.years) < 8:
            raise ValueError("Must have at least 8 years calculated")
        
        p = self.params
        
        # Sum all years (1-7) plus salvage
        ice_total = sum(y.ice_total for y in self.years)
        ev_total = sum(y.ev_total for y in self.years)
        ice_cumulative = ice_total  # Total is the final cumulative
        ev_cumulative = ev_total
        
        # Discount factor for total row
        discount_factor = 0.0  # No discount for total
        
        # Final savings
        cumulative_savings = max(ice_cumulative - ev_cumulative, 0)
        
        # Discounted values
        ice_discounted = sum(y.ice_discounted for y in self.years)
        ev_discounted = sum(y.ev_discounted for y in self.years)
        
        return YearCosts(
            year=9,  # Special value for total row
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
            discount_factor=discount_factor, cumulative_savings=cumulative_savings,
            ice_discounted=ice_discounted, ev_discounted=ev_discounted
        )
    
    def get_totals(self) -> YearCosts:
        """Calculate total row (sum of all years)"""
        if not self.years:
            raise ValueError("Must call calculate() first")
        
        # Sum all years (Rows 3-11 in Excel)
        totals = YearCosts(
            year=-1,  # Special value for totals row
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
            ice_total=sum(y.ice_total for y in self.years),
            ice_cumulative=self.years[-1].ice_cumulative,  # Final cumulative
            ev_total=sum(y.ev_total for y in self.years),
            ev_cumulative=self.years[-1].ev_cumulative,  # Final cumulative
            discount_factor=0.0,  # N/A for totals
            cumulative_savings=self.years[-1].cumulative_savings,  # Final savings
            ice_discounted=sum(y.ice_discounted for y in self.years),
            ev_discounted=sum(y.ev_discounted for y in self.years)
        )
        
        return totals


if __name__ == "__main__":
    from pathlib import Path
    from parameters import load_parameters_from_excel
    
    # Load parameters and calculate
    excel_path = Path("/Users/danikae/Git/tco_model/excel_tool/7_year_TCO_Canada.xlsx")
    params = load_parameters_from_excel(excel_path, scenario=1)
    
    print("="*100)
    print("SCENARIO 1: PURCHASE UPFRONT - TCO CALCULATION")
    print("="*100)
    
    calculator = Scenario1Calculator(params)
    years = calculator.calculate()
    totals = calculator.get_totals()
    
    # Display year-by-year results
    print(f"\n{'Year':<6} {'ICE Total':>12} {'EV Total':>12} {'ICE Cum':>12} {'EV Cum':>12} {'Savings':>12}")
    print("-"*72)
    
    for year_costs in years:
        year_label = str(year_costs.year) if year_costs.year < 8 else "Salvage"
        print(f"{year_label:<6} ${year_costs.ice_total:>11,.0f} ${year_costs.ev_total:>11,.0f} " +
              f"${year_costs.ice_cumulative:>11,.0f} ${year_costs.ev_cumulative:>11,.0f} " +
              f"${year_costs.cumulative_savings:>11,.0f}")
    
    print("-"*72)
    print(f"{'TOTALS':<6} ${totals.ice_total:>11,.0f} ${totals.ev_total:>11,.0f} " +
          f"${totals.ice_cumulative:>11,.0f} ${totals.ev_cumulative:>11,.0f} " +
          f"${totals.cumulative_savings:>11,.0f}")
    
    # Validation against Excel
    print(f"\n{'='*100}")
    print("VALIDATION AGAINST EXCEL:")
    print(f"{'='*100}")
    print(f"ICE Total:    Python=${totals.ice_total:,.2f}    Excel=$168,497.52")
    print(f"EV Total:     Python=${totals.ev_total:,.2f}     Excel=$144,937.09")
    print(f"Savings:      Python=${totals.cumulative_savings:,.2f}    Excel=$23,560.43")
    
    # Check if within $1
    ice_diff = abs(totals.ice_total - 168497.52)
    ev_diff = abs(totals.ev_total - 144937.09)
    savings_diff = abs(totals.cumulative_savings - 23560.43)
    
    print(f"\nDifferences:")
    print(f"  ICE:    ${ice_diff:,.2f} {'✅' if ice_diff < 1.0 else '❌'}")
    print(f"  EV:     ${ev_diff:,.2f} {'✅' if ev_diff < 1.0 else '❌'}")
    print(f"  Savings: ${savings_diff:,.2f} {'✅' if savings_diff < 1.0 else '❌'}")
