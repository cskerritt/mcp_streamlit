#!/usr/bin/env python3
"""
Life Care Plan Table Generator - Main Application Entry Point

This module serves as the main entry point for the Life Care Plan economic analysis tool.
It can be used to run the CLI interface or import the core functionality for use in
other applications.
"""

from src.cli import cli
from src.models import LifeCarePlan, Evaluee, ProjectionSettings, ServiceTable, Service
from src.calculator import CostCalculator
from src.exporters import ExcelExporter, WordExporter, PDFExporter


def create_example_plan() -> LifeCarePlan:
    """Create an example life care plan for demonstration purposes."""
    
    # Create evaluee
    evaluee = Evaluee(name="Jane Doe", current_age=35)
    
    # Create projection settings
    settings = ProjectionSettings(base_year=2025, projection_years=30, discount_rate=0.03)
    
    # Create life care plan
    lcp = LifeCarePlan(evaluee=evaluee, settings=settings)
    
    # Add Physician Evaluation table
    physician_table = ServiceTable(name="Physician Evaluation")
    physician_table.add_service(Service(
        name="Initial Neuro Eval",
        inflation_rate=0.027,
        unit_cost=500.00,
        frequency_per_year=1,
        start_year=2025,
        end_year=2025
    ))
    physician_table.add_service(Service(
        name="Annual Follow-up",
        inflation_rate=0.027,
        unit_cost=300.00,
        frequency_per_year=1,
        start_year=2026,
        end_year=2054
    ))
    lcp.add_table(physician_table)
    
    # Add Medications table
    medication_table = ServiceTable(name="Medications")
    medication_table.add_service(Service(
        name="Anti-Spasticity Drug",
        inflation_rate=0.05,
        unit_cost=300.00,
        frequency_per_year=12,
        start_year=2025,
        end_year=2054
    ))
    lcp.add_table(medication_table)
    
    # Add Surgeries table
    surgery_table = ServiceTable(name="Surgeries")
    surgery_table.add_service(Service(
        name="Spinal Fusion Surgery",
        inflation_rate=0.05,
        unit_cost=75000.00,
        frequency_per_year=1,
        occurrence_years=[2027, 2045]
    ))
    lcp.add_table(surgery_table)
    
    return lcp


def main():
    """Main function - runs the CLI interface."""
    cli()


if __name__ == "__main__":
    main()