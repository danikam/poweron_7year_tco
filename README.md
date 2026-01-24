# TCO Calculator

A Python package for calculating and analyzing the Total Cost of Ownership (TCO) for electric vehicles vs internal combustion engine vehicles.

## Features

- **Comprehensive TCO Analysis**: Calculates purchase price, fuel costs, maintenance, insurance, rebates, and salvage value
- **Multi-Year Projections**: Full 7-year analysis with cost escalation modeling
- **Discount Rate Analysis**: Present value calculations with configurable discount rates
- **Vehicle Databases**: Pre-loaded EV and ICE vehicle specifications
- **Provincial Support**: Regional fuel costs, taxes, and rebate programs for all Canadian provinces
- **Validation Suite**: Automated tests to ensure calculations match Excel implementation
- **Visualization**: Built-in plotting for cost comparisons, breakdowns, and trends

## Installation

### From Source

```bash
git clone https://github.com/yourusername/tco_model.git
cd tco_model
pip install -r requirements.txt
pip install -e .
```

## Quick Start

```python
from tco_calculator import TCOCalculator, VehicleScenario

# Initialize calculator
calculator = TCOCalculator("excel_tool/7_year_TCO_Canada.xlsx")

# Define a scenario
scenario = VehicleScenario(
    daily_distance_km=200,
    max_payload_lbs=1500,
    category="Light Duty",
    ev_vehicle_name="GMC Sierra EV Denali Edition 1",
    ice_vehicle_name="Ford Transit",
    province="BC",
    years=7,
    discount_rate=0.04,
)

# Calculate TCO
result = calculator.calculate(scenario)

# View results
print(f"EV Total Cost: ${result.ev_results.total_cost:,.2f}")
print(f"ICE Total Cost: ${result.ice_results.total_cost:,.2f}")
print(f"Savings: ${result.total_savings:,.2f}")
```

## Module Structure

```
tco_calculator/
├── __init__.py           # Package initialization
├── models.py             # Data models (VehicleScenario, TCOResult, etc.)
├── loader.py             # Excel data loader
├── calculator.py         # Core TCO calculation engine
└── visualizer.py         # Visualization utilities

tests/
└── validation.py         # Validation tests against Excel

examples.py              # Example usage scenarios
setup.py                 # Package setup
requirements.txt         # Dependencies
```

## Usage Examples

### Basic Comparison
```python
from tco_calculator import TCOCalculator, VehicleScenario

calculator = TCOCalculator("path/to/excel.xlsx")
scenario = VehicleScenario(...)
result = calculator.calculate(scenario)
print(result.summary())
```

### Multiple Scenarios
```python
scenarios = [
    VehicleScenario(..., daily_distance_km=100),
    VehicleScenario(..., daily_distance_km=200),
    VehicleScenario(..., daily_distance_km=300),
]

for scenario in scenarios:
    result = calculator.calculate(scenario)
    print(f"Distance: {scenario.daily_distance_km}km, Savings: ${result.total_savings:,.2f}")
```

### Visualization
```python
from tco_calculator.visualizer import TCOVisualizer

result = calculator.calculate(scenario)
visualizer = TCOVisualizer()
visualizer.plot_comparison(result)
visualizer.plot_annual_costs(result)
```

## Validation

The package includes comprehensive validation tests to ensure Python calculations match the Excel implementation:

```bash
cd tests
python validation.py
```

Tests include:
- Data loading verification
- Fuel cost lookups
- Vehicle database queries
- TCO calculation logic
- Discount factor calculations
- Cost escalation modeling

## Cost Components

### EV Costs
- Purchase price (with rebates)
- Charging electricity costs
- Maintenance and tires
- Insurance
- Charger infrastructure (purchase and maintenance)
- CFR/LCFS credit value

### ICE Costs
- Purchase price
- Fuel costs (gasoline/diesel)
- Carbon tax
- Maintenance and tires
- Insurance
- Salvage value

## Rebate Programs Supported

- **iMHZEV**: Federal incentive program (class-based)
- **Clean BC**: Provincial rebates for BC
- **PlugIn BC**: Charger installation rebates for BC

## Configuration Options

`VehicleScenario` parameters:
- `daily_distance_km`: Daily distance driven
- `max_payload_lbs`: Maximum payload requirement
- `category`: Vehicle category (Light/Medium/Heavy Duty)
- `refrigeration_required`: Whether refrigeration unit is needed
- `ev_vehicle_name`: EV model name
- `ice_vehicle_name`: ICE model name
- `province`: Province for costs and rebates
- `years`: Analysis period (default: 7)
- `discount_rate`: Discount rate for present value (default: 0.04)

## Future Enhancements

- [ ] Sensitivity analysis for key parameters
- [ ] Monte Carlo simulations
- [ ] Fleet-level analysis
- [ ] Export to Excel/PDF reports
- [ ] Web API interface
- [ ] Interactive dashboard

## Testing

Run the validation suite:
```bash
python tests/validation.py
```

Run examples:
```bash
python examples.py
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues or questions, please open an issue on GitHub.
