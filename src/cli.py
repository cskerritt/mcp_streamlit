import click
import json
import sys
from pathlib import Path
from typing import Optional
from .models import LifeCarePlan, Evaluee, ProjectionSettings, ServiceTable, Service, LCPConfigModel
from .calculator import CostCalculator
from .exporters import ExcelExporter, WordExporter, PDFExporter


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Life Care Plan Table Generator - Economic Analysis Tool
    
    A comprehensive tool for creating, calculating, and exporting life care plan
    cost projections with inflation adjustments and present value calculations.
    """
    pass


@cli.command()
@click.option('--name', '-n', required=True, help='Evaluee name')
@click.option('--age', '-a', required=True, type=int, help='Current age')
@click.option('--base-year', '-y', default=2025, type=int, help='Base year for projections')
@click.option('--projection-years', '-p', default=30, type=int, help='Number of years to project')
@click.option('--discount-rate', '-d', default=0.03, type=float, help='Discount rate (decimal)')
@click.option('--output', '-o', default='lcp_example.json', help='Output configuration file')
def create(name: str, age: int, base_year: int, projection_years: int, discount_rate: float, output: str):
    """Create a new life care plan configuration file with example data."""
    
    # Create example configuration
    config_data = {
        "evaluee_name": name,
        "current_age": age,
        "base_year": base_year,
        "projection_years": projection_years,
        "discount_rate": discount_rate,
        "tables": {
            "Physician Evaluation": [
                {
                    "name": "Initial Neuro Eval",
                    "inflation_rate": 0.027,
                    "unit_cost": 500.00,
                    "frequency_per_year": 1,
                    "start_year": base_year,
                    "end_year": base_year
                },
                {
                    "name": "Annual Follow-up",
                    "inflation_rate": 0.027,
                    "unit_cost": 300.00,
                    "frequency_per_year": 1,
                    "start_year": base_year + 1,
                    "end_year": base_year + projection_years - 1
                }
            ],
            "Medications": [
                {
                    "name": "Anti-Spasticity Drug",
                    "inflation_rate": 0.05,
                    "unit_cost": 300.00,
                    "frequency_per_year": 12,
                    "start_year": base_year,
                    "end_year": base_year + projection_years - 1
                }
            ],
            "Surgeries": [
                {
                    "name": "Spinal Fusion Surgery",
                    "inflation_rate": 0.05,
                    "unit_cost": 75000.00,
                    "frequency_per_year": 1,
                    "occurrence_years": [base_year + 2, base_year + 20]
                }
            ]
        }
    }
    
    # Validate configuration
    try:
        config_model = LCPConfigModel(**config_data)
        
        # Save to file
        with open(output, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        click.echo(f"✓ Created life care plan configuration: {output}")
        click.echo(f"  Evaluee: {name} (age {age})")
        click.echo(f"  Projection: {projection_years} years ({base_year}-{base_year + projection_years - 1})")
        click.echo(f"  Discount rate: {discount_rate:.1%}")
        
    except Exception as e:
        click.echo(f"✗ Error creating configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--excel', '-e', help='Export to Excel file')
@click.option('--word', '-w', help='Export to Word document')
@click.option('--pdf', '-p', help='Export to PDF file')
@click.option('--all', '-a', is_flag=True, help='Export to all formats using config filename as base')
@click.option('--show-summary', '-s', is_flag=True, help='Show summary statistics in terminal')
def calculate(config_file: str, excel: Optional[str], word: Optional[str], pdf: Optional[str], 
              all: bool, show_summary: bool):
    """Calculate costs from a configuration file and export results."""
    
    try:
        # Load configuration
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        config_model = LCPConfigModel(**config_data)
        lcp = config_model.to_life_care_plan()
        
        # Create calculator
        calculator = CostCalculator(lcp)
        
        # Show summary if requested
        if show_summary:
            summary = calculator.calculate_summary_statistics()
            click.echo(f"\n📊 Life Care Plan Summary for {lcp.evaluee.name}")
            click.echo("=" * 50)
            click.echo(f"Total Nominal Cost:    ${summary['total_nominal_cost']:,.2f}")
            click.echo(f"Total Present Value:   ${summary['total_present_value']:,.2f}")
            click.echo(f"Average Annual Cost:   ${summary['average_annual_cost']:,.2f}")
            click.echo(f"Projection Period:     {summary['projection_period']}")
            click.echo(f"Discount Rate:         {summary['discount_rate']:.1f}%")
            
            # Category breakdown
            click.echo(f"\n📋 Cost Breakdown by Category:")
            category_costs = calculator.get_cost_by_category()
            for table_name, data in category_costs.items():
                click.echo(f"  {table_name}:")
                click.echo(f"    Present Value: ${data['table_present_value_total']:,.2f}")
                click.echo(f"    Services: {len(data['services'])}")
        
        # Export files
        config_path = Path(config_file)
        base_name = config_path.stem
        
        exports_completed = []
        
        if all or excel:
            excel_file = excel or f"{base_name}_lcp.xlsx"
            ExcelExporter(calculator).export(excel_file)
            exports_completed.append(f"Excel: {excel_file}")
        
        if all or word:
            word_file = word or f"{base_name}_lcp.docx"
            WordExporter(calculator).export(word_file)
            exports_completed.append(f"Word: {word_file}")
        
        if all or pdf:
            pdf_file = pdf or f"{base_name}_lcp.pdf"
            PDFExporter(calculator).export(pdf_file)
            exports_completed.append(f"PDF: {pdf_file}")
        
        if exports_completed:
            click.echo(f"\n✓ Exports completed:")
            for export in exports_completed:
                click.echo(f"  {export}")
        
        if not (show_summary or exports_completed):
            click.echo("No output options specified. Use --show-summary, --excel, --word, --pdf, or --all")
        
    except FileNotFoundError:
        click.echo(f"✗ Configuration file not found: {config_file}", err=True)
        sys.exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"✗ Invalid JSON in configuration file: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Error processing life care plan: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
def validate(config_file: str):
    """Validate a life care plan configuration file."""
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        config_model = LCPConfigModel(**config_data)
        lcp = config_model.to_life_care_plan()
        
        click.echo(f"✓ Configuration is valid")
        click.echo(f"  Evaluee: {lcp.evaluee.name} (age {lcp.evaluee.current_age})")
        click.echo(f"  Tables: {len(lcp.tables)}")
        
        total_services = sum(len(table.services) for table in lcp.tables.values())
        click.echo(f"  Total services: {total_services}")
        
        # Show table details
        for table_name, table in lcp.tables.items():
            click.echo(f"    {table_name}: {len(table.services)} services")
        
    except FileNotFoundError:
        click.echo(f"✗ Configuration file not found: {config_file}", err=True)
        sys.exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"✗ Invalid JSON in configuration file: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Configuration validation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
def examples():
    """Show example configuration formats and usage."""
    
    example_config = {
        "evaluee_name": "John Smith",
        "current_age": 35,
        "base_year": 2025,
        "projection_years": 30,
        "discount_rate": 0.03,
        "tables": {
            "Medical Equipment": [
                {
                    "name": "Wheelchair",
                    "inflation_rate": 0.03,
                    "unit_cost": 2500.00,
                    "frequency_per_year": 1,
                    "occurrence_years": [2025, 2035, 2045]
                }
            ],
            "Therapy Services": [
                {
                    "name": "Physical Therapy",
                    "inflation_rate": 0.04,
                    "unit_cost": 150.00,
                    "frequency_per_year": 52,
                    "start_year": 2025,
                    "end_year": 2054
                }
            ]
        }
    }
    
    click.echo("📋 Example Life Care Plan Configuration:")
    click.echo("=" * 50)
    click.echo(json.dumps(example_config, indent=2))
    
    click.echo(f"\n💡 Usage Examples:")
    click.echo("=" * 20)
    click.echo("# Create a new configuration file:")
    click.echo("lcp create --name 'Jane Doe' --age 30 --output my_plan.json")
    click.echo()
    click.echo("# Validate configuration:")
    click.echo("lcp validate my_plan.json")
    click.echo()
    click.echo("# Calculate and show summary:")
    click.echo("lcp calculate my_plan.json --show-summary")
    click.echo()
    click.echo("# Export to all formats:")
    click.echo("lcp calculate my_plan.json --all")
    click.echo()
    click.echo("# Export to specific format:")
    click.echo("lcp calculate my_plan.json --excel output.xlsx --word report.docx")


if __name__ == '__main__':
    cli()