"""
Data loader for TCO calculations.
Loads vehicle databases and cost tables from Excel workbook.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional


class DataLoader:
    """Load and manage TCO data from Excel workbook."""
    
    def __init__(self, excel_path: str):
        """
        Initialize data loader with Excel file.
        
        Args:
            excel_path: Path to Excel TCO workbook
        """
        self.excel_path = Path(excel_path)
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
        
        self._load_all_data()
    
    def _load_all_data(self):
        """Load all required sheets from Excel."""
        self.ev_database = pd.read_excel(self.excel_path, sheet_name='EV database')
        self.ice_database = pd.read_excel(self.excel_path, sheet_name='ICE database')
        self.fuel_costs = pd.read_excel(self.excel_path, sheet_name='Fuel & Electricity Costs table')
        
        # Maintenance costs has headers in row 2, skip row 1
        self.maintenance_costs = pd.read_excel(
            self.excel_path, sheet_name='Maintenance costs table', skiprows=1
        )
        
        self.charger_database = pd.read_excel(self.excel_path, sheet_name='Charger database')
        self.cfr_values = pd.read_excel(self.excel_path, sheet_name='New CFR marginal value')
        self.clean_bc_rebates = pd.read_excel(self.excel_path, sheet_name='Clean BC values table')
        
        # iMHZEV table has headers in row 2, skip row 1
        self.imhzev_rebates = pd.read_excel(
            self.excel_path, sheet_name='iMHZEV table', skiprows=1
        )
        
        # Clean up column names
        self._clean_column_names()
    
    def _clean_column_names(self):
        """Standardize column names across dataframes."""
        for df in [self.ev_database, self.ice_database, self.fuel_costs, 
                   self.maintenance_costs, self.charger_database, self.cfr_values]:
            df.columns = df.columns.str.strip().str.lower()
    
    def get_ev_vehicle(self, vehicle_name: str) -> Optional[Dict]:
        """
        Get EV vehicle specifications by name.
        
        Args:
            vehicle_name: Name of EV vehicle
            
        Returns:
            Dictionary of vehicle specs, or None if not found
        """
        ev = self.ev_database[
            self.ev_database['make & model'].str.contains(vehicle_name, case=False, na=False)
        ]
        if ev.empty:
            return None
        return ev.iloc[0].to_dict()
    
    def get_ice_vehicle(self, vehicle_name: str) -> Optional[Dict]:
        """
        Get ICE vehicle specifications by name.
        
        Args:
            vehicle_name: Name of ICE vehicle
            
        Returns:
            Dictionary of vehicle specs, or None if not found
        """
        ice = self.ice_database[
            self.ice_database['make + model'].str.contains(vehicle_name, case=False, na=False)
        ]
        if ice.empty:
            return None
        return ice.iloc[0].to_dict()
    
    def get_fuel_costs(self, province: str) -> Tuple[float, float, float]:
        """
        Get fuel costs for a province.
        
        Args:
            province: Province code (e.g., 'BC', 'ON')
            
        Returns:
            Tuple of (electricity_cost_per_kwh, gasoline_cost_per_L, diesel_cost_per_L)
        """
        costs = self.fuel_costs[self.fuel_costs['province'] == province]
        if costs.empty:
            raise ValueError(f"Province {province} not found in fuel costs table")
        
        row = costs.iloc[0]
        electricity = row.get('cost of electricity ($/kwh)', 0.15)
        gasoline = row.get('gasoline cost ($/l)', 1.50)
        diesel = row.get('diesel cost ($/l)', 1.60)
        
        return electricity, gasoline, diesel
    
    def get_maintenance_cost(self, vehicle_type: str, duty_class: str) -> float:
        """
        Get maintenance cost per km for a vehicle.
        
        Args:
            vehicle_type: 'EV' or 'ICE'
            duty_class: 'Light Duty', 'Medium Duty', or 'Heavy Duty'
            
        Returns:
            Maintenance cost in $/km
        """
        # Convert duty class to match Excel format (Light Duty -> Light-Duty)
        duty_class_formatted = duty_class.replace(' ', '-')
        label = f"{duty_class_formatted} {vehicle_type}s"
        
        # Try to find matching row
        maint = self.maintenance_costs[
            self.maintenance_costs.iloc[:, 0].str.contains(label, case=False, na=False)
        ]
        
        if maint.empty:
            # Try without 's' at the end for ICE
            label_alt = f"{duty_class_formatted} {vehicle_type}"
            maint = self.maintenance_costs[
                self.maintenance_costs.iloc[:, 0].str.contains(label_alt, case=False, na=False)
            ]
        
        if maint.empty:
            raise ValueError(f"Maintenance cost not found for {label}")
        
        # Total cost is in the 4th column (index 3)
        return maint.iloc[0, 3]
    
    def get_cfr_value(self, vehicle_type: str, province: str) -> float:
        """
        Get CFR (Clean Fuel Requirement) marginal value.
        
        Args:
            vehicle_type: 'Light + medium duty' or 'Heavy duty'
            province: Province code
            
        Returns:
            CFR value in $ per kWh
        """
        cfr = self.cfr_values[
            (self.cfr_values['vehicle type'] == vehicle_type) &
            (self.cfr_values['province'] == province)
        ]
        
        if cfr.empty:
            return 0.0
        
        return cfr.iloc[0]['marginal cfr $ value per kwh dispensed']
    
    def get_clean_bc_rebate(self, fhwa_class: str) -> float:
        """
        Get Clean BC vehicle rebate amount.
        
        Args:
            fhwa_class: FHWA vehicle class (e.g., '2B', '3')
            
        Returns:
            Rebate amount in $
        """
        rebate = self.clean_bc_rebates[
            self.clean_bc_rebates.iloc[:, 0] == fhwa_class
        ]
        
        if rebate.empty:
            return 0.0
        
        return float(rebate.iloc[0, 1])
    
    def get_imhzev_rebate(self, fhwa_class: str, battery_size: Optional[float] = None) -> float:
        """
        Get iMHZEV federal incentive amount.
        
        Args:
            fhwa_class: FHWA vehicle class
            battery_size: Battery size in kWh (optional, for class 8 vehicles)
            
        Returns:
            Incentive amount in $
        """
        # Convert class to string and clean it
        fhwa_class_str = str(fhwa_class).strip()
        
        rebates = self.imhzev_rebates[
            self.imhzev_rebates.iloc[:, 0].astype(str).str.strip() == fhwa_class_str
        ]
        
        if rebates.empty:
            return 0.0
        
        # For class 8, check battery size if provided
        if fhwa_class_str == '8' and battery_size:
            if battery_size > 350:
                battery_rebates = rebates[
                    rebates.iloc[:, 1].astype(str).str.contains('Over 350', na=False)
                ]
                if len(battery_rebates) > 0:
                    return float(battery_rebates.iloc[0, 3])
            else:
                battery_rebates = rebates[
                    rebates.iloc[:, 1].astype(str).str.contains('Under 350', na=False)
                ]
                if len(battery_rebates) > 0:
                    return float(battery_rebates.iloc[0, 3])
        
        return float(rebates.iloc[0, 3])
    
    def list_ev_vehicles(self) -> list:
        """Get list of available EV vehicles."""
        return self.ev_database['make & model'].dropna().unique().tolist()
    
    def list_ice_vehicles(self) -> list:
        """Get list of available ICE vehicles."""
        return self.ice_database['make + model'].dropna().unique().tolist()
