# Life Care Plan Table Generator - Economic Analysis Tool

A comprehensive Python application for creating, calculating, and exporting life care plan cost projections with inflation adjustments and present value calculations.

## Features

- **Flexible Service Modeling**: Support for both recurring services (with start/end years) and discrete occurrence services
- **Economic Calculations**: Built-in inflation adjustment and present value calculations
- **Multiple Export Formats**: Export to Excel, Word, and PDF formats
- **Command-Line Interface**: Easy-to-use CLI for creating and processing life care plans
- **Configuration-Based**: JSON configuration files for easy plan management and version control
- **Professional Reports**: Automatically generated reports with summary statistics and detailed breakdowns

## Installation

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Create a New Life Care Plan

```bash
python main.py create --name "Jane Doe" --age 35 --output my_plan.json
```

### 2. Calculate and Export Results

```bash
# Show summary in terminal
python main.py calculate my_plan.json --show-summary

# Export to all formats
python main.py calculate my_plan.json --all

# Export to specific formats
python main.py calculate my_plan.json --excel report.xlsx --word report.docx
```

### 3. Validate Configuration

```bash
python main.py validate my_plan.json
```

## Configuration Format

Life care plans are defined in JSON configuration files:

```json
{
  "evaluee_name": "Jane Doe",
  "current_age": 35,
  "base_year": 2025,
  "projection_years": 30,
  "discount_rate": 0.03,
  "tables": {
    "Physician Evaluation": [
      {
        "name": "Initial Neuro Eval",
        "inflation_rate": 0.027,
        "unit_cost": 500.00,
        "frequency_per_year": 1,
        "start_year": 2025,
        "end_year": 2025
      }
    ],
    "Medications": [
      {
        "name": "Anti-Spasticity Drug",
        "inflation_rate": 0.05,
        "unit_cost": 300.00,
        "frequency_per_year": 12,
        "start_year": 2025,
        "end_year": 2054
      }
    ],
    "Surgeries": [
      {
        "name": "Spinal Fusion Surgery",
        "inflation_rate": 0.05,
        "unit_cost": 75000.00,
        "frequency_per_year": 1,
        "occurrence_years": [2027, 2045]
      }
    ]
  }
}
```

## Service Types

### Recurring Services
Services that occur regularly within a date range:
- Use `start_year` and `end_year` parameters
- Calculated for each year in the range
- Example: Annual medical appointments, monthly medications

### Discrete Occurrence Services
Services that occur only in specific years:
- Use `occurrence_years` parameter (list of years)
- Calculated only for specified years
- Example: Surgeries, equipment replacements

## CLI Commands

### `create`
Create a new life care plan configuration file with example data.

```bash
python main.py create [OPTIONS]

Options:
  -n, --name TEXT              Evaluee name [required]
  -a, --age INTEGER           Current age [required]
  -y, --base-year INTEGER     Base year for projections [default: 2025]
  -p, --projection-years INTEGER  Number of years to project [default: 30]
  -d, --discount-rate FLOAT   Discount rate (decimal) [default: 0.03]
  -o, --output TEXT           Output configuration file [default: lcp_example.json]
```

### `calculate`
Calculate costs from a configuration file and export results.

```bash
python main.py calculate [OPTIONS] CONFIG_FILE

Options:
  -e, --excel TEXT    Export to Excel file
  -w, --word TEXT     Export to Word document
  -p, --pdf TEXT      Export to PDF file
  -a, --all           Export to all formats using config filename as base
  -s, --show-summary  Show summary statistics in terminal
```

### `validate`
Validate a life care plan configuration file.

```bash
python main.py validate CONFIG_FILE
```

### `examples`
Show example configuration formats and usage.

```bash
python main.py examples
```

## Using as a Python Library

```python
from src.models import LifeCarePlan, Evaluee, ProjectionSettings, ServiceTable, Service
from src.calculator import CostCalculator
from src.exporters import ExcelExporter, WordExporter, PDFExporter

# Create life care plan programmatically
evaluee = Evaluee(name="John Smith", current_age=40)
settings = ProjectionSettings(base_year=2025, projection_years=25, discount_rate=0.035)
lcp = LifeCarePlan(evaluee=evaluee, settings=settings)

# Add services
table = ServiceTable(name="Medical Equipment")
table.add_service(Service(
    name="Wheelchair",
    inflation_rate=0.03,
    unit_cost=2500.00,
    frequency_per_year=1,
    occurrence_years=[2025, 2035, 2045]
))
lcp.add_table(table)

# Calculate costs
calculator = CostCalculator(lcp)
cost_schedule = calculator.build_cost_schedule()
summary_stats = calculator.calculate_summary_statistics()

# Export results
ExcelExporter(calculator).export("output.xlsx")
WordExporter(calculator).export("report.docx")
```

## Output Files

### Excel Export
- **Cost Schedule**: Year-by-year breakdown with all services
- **Summary**: Key statistics and totals
- **Category Summary**: Costs broken down by service category

### Word Export
- Executive summary with key metrics
- Cost breakdown by category
- Detailed cost schedule table
- Optional present value chart

### PDF Export
- Professional report format
- Summary statistics table
- Category breakdown
- Detailed cost schedule

## Economic Calculations

### Inflation Adjustment
Each service cost is adjusted for inflation using:
```
Adjusted Cost = Base Cost × (1 + Inflation Rate)^(Year - Base Year)
```

### Present Value Calculation
Future costs are discounted to present value using:
```
Present Value = Future Value ÷ (1 + Discount Rate)^(Year - Base Year)
```

## Dependencies

- pandas: Data manipulation and analysis
- matplotlib: Chart generation
- python-docx: Word document generation
- openpyxl: Excel file handling
- reportlab: PDF generation
- click: Command-line interface
- pydantic: Data validation

## File Structure

```
LCP_Table_Generator_Econ/
├── src/
│   ├── __init__.py
│   ├── models.py          # Data models and validation
│   ├── calculator.py      # Cost calculation engine
│   ├── exporters.py       # Export functionality
│   └── cli.py            # Command-line interface
├── main.py               # Main application entry point
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## License

This project is provided as-is for educational and professional use in life care planning and economic analysis.