"""
TCO Calculator - Core calculation engine.
Implements the financial model for TCO analysis.
"""

import numpy as np
from typing import Optional
from .models import VehicleScenario, VehicleResults, AnnualCosts, TCOResult
from .loader import DataLoader


class TCOCalculator:
    """Calculate total cost of ownership for vehicles."""
    
    def __init__(self, excel_path: str):
        """
        Initialize calculator with data.
        
        Args:
            excel_path: Path to Excel workbook with vehicle and cost data
        """
        self.loader = DataLoader(excel_path)
    
    def calculate(self, scenario: VehicleScenario) -> TCOResult:
        """
        Calculate TCO for EV vs ICE comparison.
        
        Args:
            scenario: VehicleScenario with calculation parameters
            
        Returns:
            TCOResult with complete comparison
        """
        # Get vehicle data
        ev_data = self._get_vehicle_data(scenario.ev_vehicle_name, 'EV')
        ice_data = self._get_vehicle_data(scenario.ice_vehicle_name, 'ICE')
        
        # Get fuel and cost parameters
        electricity_cost, gasoline_cost, diesel_cost = self.loader.get_fuel_costs(
            scenario.province
        )
        
        # Calculate annual distances
        annual_distance_km = scenario.daily_distance_km * 365
        
        # Calculate EV results
        ev_results = self._calculate_vehicle_tco(
            vehicle_name=scenario.ev_vehicle_name,
            vehicle_data=ev_data,
            vehicle_type='EV',
            scenario=scenario,
            annual_distance_km=annual_distance_km,
            fuel_cost_rate=electricity_cost,
        )
        
        # Calculate ICE results
        fuel_type = ice_data.get('fuel type', 'Gasoline')
        ice_fuel_cost = gasoline_cost if fuel_type == 'Gasoline' else diesel_cost
        
        ice_results = self._calculate_vehicle_tco(
            vehicle_name=scenario.ice_vehicle_name,
            vehicle_data=ice_data,
            vehicle_type='ICE',
            scenario=scenario,
            annual_distance_km=annual_distance_km,
            fuel_cost_rate=ice_fuel_cost,
        )
        
        return TCOResult(
            scenario=scenario,
            ev_results=ev_results,
            ice_results=ice_results,
        )
    
    def _get_vehicle_data(self, vehicle_name: str, vehicle_type: str) -> dict:
        """Get vehicle data from loader."""
        if vehicle_type == 'EV':
            data = self.loader.get_ev_vehicle(vehicle_name)
        else:
            data = self.loader.get_ice_vehicle(vehicle_name)
        
        if data is None:
            raise ValueError(f"{vehicle_type} vehicle '{vehicle_name}' not found")
        
        return data
    
    def _calculate_vehicle_tco(
        self,
        vehicle_name: str,
        vehicle_data: dict,
        vehicle_type: str,
        scenario: VehicleScenario,
        annual_distance_km: float,
        fuel_cost_rate: float,
    ) -> VehicleResults:
        """
        Calculate TCO for a single vehicle.
        
        Args:
            vehicle_name: Vehicle name
            vehicle_data: Vehicle specifications
            vehicle_type: 'EV' or 'ICE'
            scenario: Calculation scenario
            annual_distance_km: Annual distance driven
            fuel_cost_rate: Fuel or electricity cost per unit
            
        Returns:
            VehicleResults with annual breakdown and totals
        """
        results = VehicleResults(
            vehicle_name=vehicle_name,
            vehicle_type=vehicle_type,
        )
        
        # Get key vehicle specs
        purchase_price = (scenario.ev_custom_price if vehicle_type == 'EV' and scenario.ev_custom_price
                         else scenario.ice_custom_price if vehicle_type == 'ICE' and scenario.ice_custom_price
                         else vehicle_data.get('cost, $msrp\ncad') or 
                              vehicle_data.get('purchase price ($ cad)', 0))
        
        efficiency = (scenario.ev_custom_efficiency if vehicle_type == 'EV' and scenario.ev_custom_efficiency
                     else scenario.ice_custom_efficiency if vehicle_type == 'ICE' and scenario.ice_custom_efficiency
                     else vehicle_data.get('efficiency (kwh/km)') or 
                          vehicle_data.get('efficiency (l/km)', 0.1))
        
        fhwa_class = vehicle_data.get('fhwa class (2b - 8)', '2B')
        battery_size = vehicle_data.get('battery size, kwh', 0)
        insurance_rate = 0.015  # 1.5% of vehicle value per year
        
        # Get maintenance cost
        duty_class = scenario.category
        maintenance_cost_per_km = self.loader.get_maintenance_cost(vehicle_type, duty_class)
        
        # Get rebates (EV only)
        total_rebate = 0.0
        if vehicle_type == 'EV':
            federal_rebate = self.loader.get_imhzev_rebate(fhwa_class, battery_size)
            provincial_rebate = self.loader.get_clean_bc_rebate(fhwa_class) if scenario.province == 'BC' else 0.0
            total_rebate = min(federal_rebate + provincial_rebate, purchase_price * 0.75)
        
        # Get CFR value
        cfr_value_per_kwh = 0.0
        if vehicle_type == 'EV':
            vehicle_class = 'Light + medium duty' if duty_class in ['Light Duty', 'Medium Duty'] else 'Heavy duty'
            cfr_value_per_kwh = self.loader.get_cfr_value(vehicle_class, scenario.province)
        
        # Calculate annual costs
        cumulative_cost = 0.0
        for year in range(scenario.years):
            annual_cost = AnnualCosts(year=year)
            
            # Purchase cost (year 0 only)
            if year == 0:
                annual_cost.purchase_cost = purchase_price
            
            # Fuel/electricity cost
            annual_fuel_cost = annual_distance_km * efficiency * fuel_cost_rate
            annual_cost.fuel_cost = annual_fuel_cost
            
            # Carbon tax (ICE only, 5% annual escalation)
            if vehicle_type == 'ICE':
                carbon_tax_rate = 0.03 + 0.02  # From Excel
                annual_cost.carbon_tax = annual_fuel_cost * carbon_tax_rate * ((1 + carbon_tax_rate) ** year)
            
            # Maintenance cost
            annual_cost.maintenance_cost = annual_distance_km * maintenance_cost_per_km
            
            # Insurance (1.5% of vehicle value, adjusted for depreciation)
            depreciation_rate = 0.15  # 15% per year
            remaining_value = purchase_price * ((1 - depreciation_rate) ** year)
            annual_cost.insurance_cost = remaining_value * insurance_rate
            
            # Charger costs (EV only, year 0)
            if vehicle_type == 'EV' and year == 0:
                # Assume L2 charger installation
                annual_cost.charger_cost = 15214.0716  # From charger database
            
            # Charger maintenance (EV only, 2% annual escalation)
            if vehicle_type == 'EV' and year > 0:
                annual_cost.charger_maintenance = annual_cost.charger_cost * 0.02 * year
            
            # Rebates (year 0 only)
            if year == 0:
                annual_cost.rebates = total_rebate
            
            # CFR value (EV only)
            if vehicle_type == 'EV':
                annual_cost.cfr_value = annual_distance_km * efficiency * cfr_value_per_kwh
            
            # Salvage value (final year)
            if year == scenario.years - 1:
                salvage_rate = 0.3  # 30% residual value
                annual_cost.salvage_value = purchase_price * salvage_rate
            
            results.annual_costs.append(annual_cost)
            cumulative_cost += annual_cost.total_cost
            results.cumulative_costs.append(cumulative_cost)
        
        # Calculate totals
        results.total_cost = sum(ac.total_cost for ac in results.annual_costs)
        
        # Calculate present value cost
        discount_factors = [(1 / (1 + scenario.discount_rate) ** year) 
                           for year in range(scenario.years)]
        results.present_value_cost = sum(
            ac.total_cost * df 
            for ac, df in zip(results.annual_costs, discount_factors)
        )
        
        return results
