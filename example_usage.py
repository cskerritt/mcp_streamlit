#!/usr/bin/env python3
"""
Example Usage of Life Care Plan Table Generator

This script demonstrates how to use the LCP Table Generator programmatically
to create life care plans, calculate costs, and export results.
"""

from src.models import LifeCarePlan, Evaluee, ProjectionSettings, ServiceTable, Service
from src.calculator import CostCalculator
from src.exporters import ExcelExporter, WordExporter, PDFExporter
import json


def create_comprehensive_example():
    """Create a comprehensive life care plan example."""
    
    print("Creating comprehensive life care plan example...")
    
    # Create evaluee - a 30-year-old individual
    evaluee = Evaluee(name="Alex Johnson", current_age=30)
    
    # Set projection parameters - 35 years with 3.5% discount rate
    settings = ProjectionSettings(
        base_year=2025,
        projection_years=35,
        discount_rate=0.035
    )
    
    # Create life care plan
    lcp = LifeCarePlan(evaluee=evaluee, settings=settings)
    
    # 1. Medical Evaluations and Consultations
    medical_eval_table = ServiceTable(name="Medical Evaluations")
    
    # Initial comprehensive evaluation
    medical_eval_table.add_service(Service(
        name="Initial Comprehensive Evaluation",
        inflation_rate=0.035,
        unit_cost=1200.00,
        frequency_per_year=1,
        start_year=2025,
        end_year=2025
    ))
    
    # Annual neurological evaluations
    medical_eval_table.add_service(Service(
        name="Annual Neurological Evaluation",
        inflation_rate=0.035,
        unit_cost=650.00,
        frequency_per_year=1,
        start_year=2026,
        end_year=2059
    ))
    
    # Specialist consultations (quarterly)
    medical_eval_table.add_service(Service(
        name="Specialist Consultation",
        inflation_rate=0.04,
        unit_cost=300.00,
        frequency_per_year=4,
        start_year=2025,
        end_year=2059
    ))
    
    lcp.add_table(medical_eval_table)
    
    # 2. Medications
    medication_table = ServiceTable(name="Medications")
    
    # Primary medication (monthly)
    medication_table.add_service(Service(
        name="Primary Medication",
        inflation_rate=0.06,  # Higher inflation for pharmaceuticals
        unit_cost=450.00,
        frequency_per_year=12,
        start_year=2025,
        end_year=2059
    ))
    
    # Secondary medication (as needed, estimated 8 times per year)
    medication_table.add_service(Service(
        name="Secondary Medication",
        inflation_rate=0.055,
        unit_cost=120.00,
        frequency_per_year=8,
        start_year=2025,
        end_year=2059
    ))
    
    lcp.add_table(medication_table)
    
    # 3. Therapy Services
    therapy_table = ServiceTable(name="Therapy Services")
    
    # Physical therapy (twice weekly)
    therapy_table.add_service(Service(
        name="Physical Therapy",
        inflation_rate=0.045,
        unit_cost=125.00,
        frequency_per_year=104,  # 2x per week
        start_year=2025,
        end_year=2059
    ))
    
    # Occupational therapy (weekly)
    therapy_table.add_service(Service(
        name="Occupational Therapy",
        inflation_rate=0.045,
        unit_cost=130.00,
        frequency_per_year=52,  # 1x per week
        start_year=2025,
        end_year=2050  # May not need full duration
    ))
    
    # Speech therapy (twice monthly)
    therapy_table.add_service(Service(
        name="Speech Therapy",
        inflation_rate=0.04,
        unit_cost=115.00,
        frequency_per_year=24,  # 2x per month
        start_year=2025,
        end_year=2040  # Limited duration
    ))
    
    lcp.add_table(therapy_table)
    
    # 4. Medical Equipment
    equipment_table = ServiceTable(name="Medical Equipment")
    
    # Wheelchair replacements (every 5 years)
    equipment_table.add_service(Service(
        name="Power Wheelchair",
        inflation_rate=0.035,
        unit_cost=8500.00,
        frequency_per_year=1,
        occurrence_years=[2025, 2030, 2035, 2040, 2045, 2050, 2055]
    ))
    
    # Home modifications (one-time major, then periodic updates)
    equipment_table.add_service(Service(
        name="Home Accessibility Modifications",
        inflation_rate=0.04,
        unit_cost=25000.00,
        frequency_per_year=1,
        occurrence_years=[2025, 2040]  # Initial and major update
    ))
    
    # Assistive technology updates (every 3 years)
    equipment_table.add_service(Service(
        name="Assistive Technology Package",
        inflation_rate=0.05,  # Technology inflates faster
        unit_cost=3500.00,
        frequency_per_year=1,
        occurrence_years=[2025, 2028, 2031, 2034, 2037, 2040, 2043, 2046, 2049, 2052, 2055, 2058]
    ))
    
    lcp.add_table(equipment_table)
    
    # 5. Surgical Procedures
    surgery_table = ServiceTable(name="Surgical Procedures")
    
    # Planned surgical interventions
    surgery_table.add_service(Service(
        name="Orthopedic Surgery",
        inflation_rate=0.055,
        unit_cost=45000.00,
        frequency_per_year=1,
        occurrence_years=[2027, 2042]  # Two major procedures expected
    ))
    
    # Potential emergency procedures (estimated)
    surgery_table.add_service(Service(
        name="Emergency Surgical Procedures",
        inflation_rate=0.055,
        unit_cost=25000.00,
        frequency_per_year=1,
        occurrence_years=[2032, 2048]  # Estimated emergency needs
    ))
    
    lcp.add_table(surgery_table)
    
    # 6. Personal Care Services
    care_table = ServiceTable(name="Personal Care Services")
    
    # Daily care assistance (increasing over time)
    care_table.add_service(Service(
        name="Personal Care Assistant (4 hrs/day)",
        inflation_rate=0.05,  # Service wages inflate faster
        unit_cost=25.00 * 4 * 365,  # $25/hr * 4 hrs/day * 365 days
        frequency_per_year=1,
        start_year=2025,
        end_year=2039
    ))
    
    # Increased care needs (6 hrs/day for later years)
    care_table.add_service(Service(
        name="Personal Care Assistant (6 hrs/day)",
        inflation_rate=0.05,
        unit_cost=25.00 * 6 * 365,  # $25/hr * 6 hrs/day * 365 days
        frequency_per_year=1,
        start_year=2040,
        end_year=2059
    ))
    
    lcp.add_table(care_table)
    
    return lcp


def demonstrate_calculations(lcp: LifeCarePlan):
    """Demonstrate cost calculations and analysis."""
    
    print(f"\nCalculating costs for {lcp.evaluee.name}...")
    
    # Create calculator
    calculator = CostCalculator(lcp)
    
    # Get summary statistics
    summary = calculator.calculate_summary_statistics()
    
    print(f"\n📊 LIFE CARE PLAN SUMMARY")
    print("=" * 50)
    print(f"Evaluee: {lcp.evaluee.name} (Current Age: {lcp.evaluee.current_age})")
    print(f"Projection Period: {summary['projection_period']}")
    print(f"Discount Rate: {summary['discount_rate']:.1f}%")
    print(f"\nTotal Nominal Cost:    ${summary['total_nominal_cost']:,.2f}")
    print(f"Total Present Value:   ${summary['total_present_value']:,.2f}")
    print(f"Average Annual Cost:   ${summary['average_annual_cost']:,.2f}")
    
    # Category breakdown
    print(f"\n📋 COST BREAKDOWN BY CATEGORY")
    print("=" * 50)
    category_costs = calculator.get_cost_by_category()
    
    for table_name, data in category_costs.items():
        print(f"\n{table_name}:")
        print(f"  Present Value Total: ${data['table_present_value_total']:,.2f}")
        print(f"  Nominal Total:       ${data['table_nominal_total']:,.2f}")
        print(f"  Services:")
        for service in data['services']:
            print(f"    • {service['name']}")
            print(f"      Cost: ${service['unit_cost']:,.2f} ({service['frequency_per_year']}x/year)")
            print(f"      Inflation: {service['inflation_rate']:.1f}%")
            print(f"      PV Total: ${service['present_value_total']:,.2f}")
    
    return calculator


def demonstrate_exports(calculator: CostCalculator, base_filename: str = "comprehensive_lcp"):
    """Demonstrate all export formats."""
    
    print(f"\n📁 EXPORTING RESULTS")
    print("=" * 30)
    
    try:
        # Excel export
        excel_file = f"{base_filename}.xlsx"
        ExcelExporter(calculator).export(excel_file)
        print(f"✓ Excel export completed: {excel_file}")
        
        # Word export
        word_file = f"{base_filename}.docx"
        WordExporter(calculator).export(word_file, include_chart=True)
        print(f"✓ Word export completed: {word_file}")
        
        # PDF export
        pdf_file = f"{base_filename}.pdf"
        PDFExporter(calculator).export(pdf_file)
        print(f"✓ PDF export completed: {pdf_file}")
        
        print(f"\n✅ All exports completed successfully!")
        
    except Exception as e:
        print(f"❌ Export error: {e}")


def save_configuration(lcp: LifeCarePlan, filename: str = "comprehensive_example.json"):
    """Save the life care plan as a JSON configuration file."""
    
    print(f"\n💾 SAVING CONFIGURATION")
    print("=" * 30)
    
    # Convert to configuration format
    config_data = {
        "evaluee_name": lcp.evaluee.name,
        "current_age": lcp.evaluee.current_age,
        "base_year": lcp.settings.base_year,
        "projection_years": lcp.settings.projection_years,
        "discount_rate": lcp.settings.discount_rate,
        "tables": {}
    }
    
    # Add all tables and services
    for table_name, table in lcp.tables.items():
        config_data["tables"][table_name] = []
        for service in table.services:
            service_data = {
                "name": service.name,
                "inflation_rate": service.inflation_rate,
                "unit_cost": service.unit_cost,
                "frequency_per_year": service.frequency_per_year
            }
            
            if service.occurrence_years:
                service_data["occurrence_years"] = service.occurrence_years
            else:
                service_data["start_year"] = service.start_year
                service_data["end_year"] = service.end_year
            
            config_data["tables"][table_name].append(service_data)
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"✓ Configuration saved: {filename}")
    print(f"  Use with CLI: python main.py calculate {filename} --all")


def main():
    """Main demonstration function."""
    
    print("🏥 LIFE CARE PLAN TABLE GENERATOR - COMPREHENSIVE EXAMPLE")
    print("=" * 60)
    
    # Create comprehensive example
    lcp = create_comprehensive_example()
    
    # Demonstrate calculations
    calculator = demonstrate_calculations(lcp)
    
    # Save configuration for CLI use
    save_configuration(lcp, "comprehensive_example.json")
    
    # Demonstrate exports
    demonstrate_exports(calculator, "comprehensive_lcp_example")
    
    print(f"\n🎉 DEMONSTRATION COMPLETE!")
    print("=" * 40)
    print("Files created:")
    print("  • comprehensive_example.json (configuration)")
    print("  • comprehensive_lcp_example.xlsx (Excel report)")
    print("  • comprehensive_lcp_example.docx (Word report)")
    print("  • comprehensive_lcp_example.pdf (PDF report)")
    print("\nTry the CLI:")
    print("  python main.py validate comprehensive_example.json")
    print("  python main.py calculate comprehensive_example.json --show-summary")


if __name__ == "__main__":
    main()