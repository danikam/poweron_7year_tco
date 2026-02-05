"""
Data models for TCO calculations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd


@dataclass
class VehicleScenario:
    """Configuration for a TCO calculation scenario."""
    
    # Duty cycle inputs
    daily_distance_km: float
    max_payload_lbs: float
    category: str  # Light Duty, Medium Duty, Heavy Duty
    refrigeration_required: bool = False
    
    # Vehicle selections
    ev_vehicle_name: str = ""
    ice_vehicle_name: str = ""
    
    # Province for incentives and fuel costs
    province: str = "BC"
    
    # Analysis parameters
    years: int = 7
    discount_rate: float = 0.04
    
    # Optional: manual overrides for vehicle specs
    ev_custom_price: Optional[float] = None
    ice_custom_price: Optional[float] = None
    ev_custom_efficiency: Optional[float] = None
    ice_custom_efficiency: Optional[float] = None


@dataclass
class AnnualCosts:
    """Annual cost breakdown for a vehicle."""
    
    year: int
    purchase_cost: float = 0.0
    fuel_cost: float = 0.0
    carbon_tax: float = 0.0
    maintenance_cost: float = 0.0
    insurance_cost: float = 0.0
    charger_cost: float = 0.0
    charger_maintenance: float = 0.0
    rebates: float = 0.0
    cfr_value: float = 0.0
    salvage_value: float = 0.0
    
    @property
    def total_cost(self) -> float:
        """Calculate total annual cost."""
        return (self.purchase_cost + self.fuel_cost + self.carbon_tax + 
                self.maintenance_cost + self.insurance_cost + 
                self.charger_cost + self.charger_maintenance - 
                self.rebates - self.cfr_value - self.salvage_value)


@dataclass
class VehicleResults:
    """Results for a single vehicle analysis."""
    
    vehicle_name: str
    vehicle_type: str  # "EV" or "ICE"
    annual_costs: List[AnnualCosts] = field(default_factory=list)
    total_cost: float = 0.0
    present_value_cost: float = 0.0
    cumulative_costs: List[float] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame."""
        data = []
        for ac in self.annual_costs:
            data.append({
                'Year': ac.year,
                'Purchase Cost': ac.purchase_cost,
                'Fuel Cost': ac.fuel_cost,
                'Carbon Tax': ac.carbon_tax,
                'Maintenance': ac.maintenance_cost,
                'Insurance': ac.insurance_cost,
                'Charger Cost': ac.charger_cost,
                'Charger Maintenance': ac.charger_maintenance,
                'Rebates': ac.rebates,
                'CFR Value': ac.cfr_value,
                'Salvage Value': ac.salvage_value,
                'Total Cost': ac.total_cost,
            })
        return pd.DataFrame(data)


@dataclass
class TCOResult:
    """Complete TCO comparison results."""
    
    scenario: VehicleScenario
    ev_results: VehicleResults
    ice_results: VehicleResults
    total_savings: float = 0.0
    pv_savings: float = 0.0
    breakeven_year: Optional[int] = None
    
    def __post_init__(self):
        """Calculate derived metrics."""
        self.total_savings = self.ice_results.total_cost - self.ev_results.total_cost
        self.pv_savings = self.ice_results.present_value_cost - self.ev_results.present_value_cost
        
        # Find breakeven year (where cumulative EV cost < ICE cost)
        for year in range(len(self.ev_results.cumulative_costs)):
            if (self.ev_results.cumulative_costs[year] < 
                self.ice_results.cumulative_costs[year]):
                self.breakeven_year = year
                break
    
    def summary(self) -> Dict:
        """Return summary of TCO comparison."""
        return {
            'EV Total Cost': self.ev_results.total_cost,
            'ICE Total Cost': self.ice_results.total_cost,
            'Total Savings': self.total_savings,
            'EV PV Cost': self.ev_results.present_value_cost,
            'ICE PV Cost': self.ice_results.present_value_cost,
            'PV Savings': self.pv_savings,
            'Breakeven Year': self.breakeven_year,
        }
