#!/usr/bin/env python3
"""
Demo script to showcase the Streamlit Life Care Plan application.

This script demonstrates how to programmatically create a life care plan
and then shows how to run the Streamlit application to interact with it.
"""

import json
import os
from datetime import datetime
from src.models import LifeCarePlan, Evaluee, ProjectionSettings, ServiceTable, Service

def create_demo_configuration():
    """Create a demonstration life care plan configuration."""
    
    print("🏥 Creating Demo Life Care Plan Configuration...")
    
    # Create evaluee
    evaluee = Evaluee(name="Demo Patient", current_age=42, discount_calculations=True)
    
    # Create projection settings
    settings = ProjectionSettings(base_year=2025, projection_years=25, discount_rate=0.035)
    
    # Create life care plan
    lcp = LifeCarePlan(evaluee=evaluee, settings=settings)
    
    # Add Physician Evaluation table
    physician_table = ServiceTable(name="Physician Evaluation")
    physician_table.add_service(Service(
        name="Initial Comprehensive Evaluation",
        inflation_rate=0.027,
        unit_cost=750.00,
        frequency_per_year=1,
        start_year=2025,
        end_year=2025
    ))
    physician_table.add_service(Service(
        name="Quarterly Follow-up Visits",
        inflation_rate=0.027,
        unit_cost=350.00,
        frequency_per_year=4,
        start_year=2026,
        end_year=2049
    ))
    physician_table.add_service(Service(
        name="Annual Comprehensive Review",
        inflation_rate=0.027,
        unit_cost=500.00,
        frequency_per_year=1,
        start_year=2026,
        end_year=2049
    ))
    lcp.add_table(physician_table)
    
    # Add Medications table
    medication_table = ServiceTable(name="Medications")
    medication_table.add_service(Service(
        name="Primary Medication",
        inflation_rate=0.055,
        unit_cost=0,  # Will be calculated from range
        frequency_per_year=12,
        start_year=2025,
        end_year=2049,
        use_cost_range=True,
        cost_range_low=400.00,
        cost_range_high=500.00
    ))
    medication_table.add_service(Service(
        name="Supplemental Medication",
        inflation_rate=0.045,
        unit_cost=125.00,
        frequency_per_year=12,
        start_year=2025,
        end_year=2049
    ))
    lcp.add_table(medication_table)
    
    # Add Therapy Services table
    therapy_table = ServiceTable(name="Therapy Services")
    therapy_table.add_service(Service(
        name="Physical Therapy",
        inflation_rate=0.032,
        unit_cost=120.00,
        frequency_per_year=24,
        start_year=2025,
        end_year=2049
    ))
    therapy_table.add_service(Service(
        name="Occupational Therapy",
        inflation_rate=0.032,
        unit_cost=115.00,
        frequency_per_year=12,
        start_year=2025,
        end_year=2035
    ))
    lcp.add_table(therapy_table)
    
    # Add Equipment table
    equipment_table = ServiceTable(name="Medical Equipment")
    equipment_table.add_service(Service(
        name="Wheelchair Replacement",
        inflation_rate=0.028,
        unit_cost=0,  # Will be calculated from range
        frequency_per_year=1,
        occurrence_years=[2025, 2030, 2035, 2040, 2045],
        use_cost_range=True,
        cost_range_low=3000.00,
        cost_range_high=4000.00
    ))
    equipment_table.add_service(Service(
        name="Home Modifications",
        inflation_rate=0.025,
        unit_cost=0,  # Will be calculated from range
        frequency_per_year=1,
        is_one_time_cost=True,
        one_time_cost_year=2026,
        use_cost_range=True,
        cost_range_low=12000.00,
        cost_range_high=18000.00
    ))
    # Add a service with specific years (different from discrete occurrences)
    equipment_table.add_service(Service(
        name="Assistive Technology Updates",
        inflation_rate=0.035,
        unit_cost=1500.00,
        frequency_per_year=1,
        occurrence_years=[2025, 2027, 2031, 2034, 2038, 2042, 2046]
    ))
    lcp.add_table(equipment_table)
    
    # Add Surgical Procedures table
    surgery_table = ServiceTable(name="Surgical Procedures")
    surgery_table.add_service(Service(
        name="Corrective Surgery",
        inflation_rate=0.048,
        unit_cost=85000.00,
        frequency_per_year=1,
        occurrence_years=[2028, 2040]
    ))
    lcp.add_table(surgery_table)
    
    return lcp

def save_demo_config(lcp):
    """Save the demo configuration to a JSON file."""
    
    config_data = {
        "evaluee_name": lcp.evaluee.name,
        "current_age": lcp.evaluee.current_age,
        "base_year": lcp.settings.base_year,
        "projection_years": lcp.settings.projection_years,
        "discount_rate": lcp.settings.discount_rate,
        "tables": {}
    }
    
    for table_name, table in lcp.tables.items():
        config_data["tables"][table_name] = []
        for service in table.services:
            service_data = {
                "name": service.name,
                "inflation_rate": service.inflation_rate,
                "unit_cost": service.unit_cost,
                "frequency_per_year": service.frequency_per_year
            }
            
            if service.is_one_time_cost:
                service_data.update({
                    "is_one_time_cost": True,
                    "one_time_cost_year": service.one_time_cost_year
                })
            elif service.occurrence_years:
                service_data["occurrence_years"] = service.occurrence_years
            else:
                service_data.update({
                    "start_year": service.start_year,
                    "end_year": service.end_year
                })
            
            config_data["tables"][table_name].append(service_data)
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"demo_config_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"💾 Demo configuration saved to: {filename}")
    return filename

def show_demo_summary(lcp):
    """Show a summary of the demo configuration."""
    
    print("\n📋 Demo Life Care Plan Summary")
    print("=" * 50)
    print(f"Evaluee: {lcp.evaluee.name}")
    print(f"Current Age: {lcp.evaluee.current_age} years")
    print(f"Base Year: {lcp.settings.base_year}")
    print(f"Projection Period: {lcp.settings.projection_years} years")
    print(f"Discount Rate: {lcp.settings.discount_rate:.1%}")
    print(f"Present Value Calculations: {'Enabled' if lcp.evaluee.discount_calculations else 'Disabled'}")
    
    print(f"\nService Tables: {len(lcp.tables)}")
    total_services = 0
    
    for table_name, table in lcp.tables.items():
        print(f"  • {table_name}: {len(table.services)} services")
        total_services += len(table.services)
    
    print(f"\nTotal Services: {total_services}")
    
    # Quick calculation preview
    from src.calculator import CostCalculator
    calculator = CostCalculator(lcp)
    summary_stats = calculator.calculate_summary_statistics()
    
    print(f"\n💰 Cost Summary:")
    print(f"  • Total Nominal Cost: ${summary_stats['total_nominal_cost']:,.0f}")
    print(f"  • Total Present Value: ${summary_stats['total_present_value']:,.0f}")
    print(f"  • Average Annual Cost: ${summary_stats['average_annual_cost']:,.0f}")

def main():
    """Main demo function."""
    
    print("🎯 Life Care Plan Streamlit Application Demo")
    print("=" * 60)
    
    # Create demo configuration
    demo_lcp = create_demo_configuration()
    
    # Show summary
    show_demo_summary(demo_lcp)
    
    # Save configuration
    config_file = save_demo_config(demo_lcp)
    
    print("\n🚀 How to Use the Streamlit Application:")
    print("=" * 60)
    print("1. Start the application:")
    print("   python run_streamlit.py")
    print("   OR")
    print("   streamlit run streamlit_app.py")
    print()
    print("2. In the application:")
    print("   • Go to 'Load/Save Configurations'")
    print(f"   • Upload the file: {config_file}")
    print("   • Explore the loaded data")
    print("   • Calculate costs and view charts")
    print("   • Export reports")
    print()
    print("3. Or create your own plan:")
    print("   • Start with 'Create/Edit Evaluee'")
    print("   • Add service tables and services")
    print("   • Calculate and export results")
    print()
    print("📱 The application will open in your web browser at:")
    print("   http://localhost:8501")
    print()
    print("💡 Features to try:")
    print("   • Interactive cost calculations")
    print("   • Dynamic charts and visualizations")
    print("   • Export to Excel, Word, and PDF")
    print("   • Save and load configurations")
    print("   • Sample data for quick testing")

if __name__ == "__main__":
    main()
