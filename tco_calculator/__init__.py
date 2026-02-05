"""
TCO Calculator - Total Cost of Ownership analysis for vehicles.

A Python package for calculating and analyzing the total cost of ownership
for electric vehicles vs internal combustion engine vehicles.
"""

from .calculator import TCOCalculator
from .loader import DataLoader
from .models import VehicleScenario, TCOResult

__version__ = "0.1.0"
__all__ = ["TCOCalculator", "DataLoader", "VehicleScenario", "TCOResult"]
