#!/usr/bin/env python3

import pandas as pd
from src.models import LifeCarePlan, Evaluee, ProjectionSettings, ServiceTable, Service
from src.calculator import CostCalculator
from decimal import Decimal

def manual_fractional_calculation():
    """Calculate the impact of fractional years manually for accurate error analysis."""
    
    print('=== FRACTIONAL YEAR ERROR ANALYSIS ===')
    print()
    
    # Test scenarios based on your CSV data
    scenarios = [
        {'name': 'Physician Evaluation: Neurology', 'cost': 444.33, 'inflation': 0.032, 'freq': 1},
        {'name': 'Diagnostics: MRI Head', 'cost': 1852.03, 'inflation': 0.030, 'freq': 1},
        {'name': 'Therapies: Physical Therapy', 'cost': 17908.88, 'inflation': 0.028, 'freq': 1},
        {'name': 'Medications: Gabapentin', 'cost': 277.40, 'inflation': 0.016, 'freq': 12},
        {'name': 'Surgeries: Shoulder Arthroscopy', 'cost': 130600.45, 'inflation': 0.035, 'freq': 1}
    ]
    
    base_year = 2025
    current_age = 37.8
    
    results = []
    
    for scenario in scenarios:
        print(f"Analyzing: {scenario['name']}")
        print(f"Base cost: ${scenario['cost']:,.2f}, Inflation: {scenario['inflation']:.1%}")
        
        # Calculate for different projection periods
        periods = [39.0, 39.4, 40.0]
        scenario_results = {'Service': scenario['name']}
        
        for period in periods:
            total_cost = 0
            
            # Calculate year by year
            for year_offset in range(int(period)):
                years_from_base = year_offset
                inflation_factor = (1 + scenario['inflation']) ** years_from_base
                annual_cost = scenario['cost'] * scenario['freq'] * inflation_factor
                total_cost += annual_cost
            
            # Add fractional year if applicable
            fractional_part = period - int(period)
            if fractional_part > 0:
                years_from_base = int(period)
                inflation_factor = (1 + scenario['inflation']) ** years_from_base
                fractional_cost = scenario['cost'] * scenario['freq'] * inflation_factor * fractional_part
                total_cost += fractional_cost
                
                print(f"  Fractional year ({fractional_part:.1f}): ${fractional_cost:,.2f}")
            
            scenario_results[f'{period} years'] = total_cost
            print(f"  {period:4.1f} years total: ${total_cost:,.2f}")
        
        # Calculate error rates
        total_39 = scenario_results['39.0 years']
        total_394 = scenario_results['39.4 years']
        total_40 = scenario_results['40.0 years']
        
        error_39_vs_394 = ((total_394 - total_39) / total_39) * 100
        error_39_vs_40 = ((total_40 - total_39) / total_39) * 100
        
        scenario_results['Error 39 vs 39.4'] = error_39_vs_394
        scenario_results['Error 39 vs 40'] = error_39_vs_40
        
        print(f"  Error 39.0 vs 39.4: {error_39_vs_394:+.3f}%")
        print(f"  Error 39.0 vs 40.0: {error_39_vs_40:+.3f}%")
        print()
        
        results.append(scenario_results)
    
    # Summary analysis
    print('=== SUMMARY ANALYSIS ===')
    
    total_39_all = sum(r['39.0 years'] for r in results)
    total_394_all = sum(r['39.4 years'] for r in results)
    total_40_all = sum(r['40.0 years'] for r in results)
    
    overall_error_394 = ((total_394_all - total_39_all) / total_39_all) * 100
    overall_error_40 = ((total_40_all - total_39_all) / total_39_all) * 100
    
    print(f"Combined totals:")
    print(f"  39.0 years: ${total_39_all:,.2f}")
    print(f"  39.4 years: ${total_394_all:,.2f}")
    print(f"  40.0 years: ${total_40_all:,.2f}")
    print()
    
    print(f"Error Analysis:")
    print(f"  Using 39.0 instead of 39.4: {overall_error_394:+.3f}% underestimation")
    print(f"  Using 39.0 instead of 40.0: {overall_error_40:+.3f}% underestimation")
    print()
    
    print(f"Dollar Impact:")
    print(f"  39.0 vs 39.4 difference: ${total_394_all - total_39_all:,.2f}")
    print(f"  39.0 vs 40.0 difference: ${total_40_all - total_39_all:,.2f}")
    print()
    
    # Per service breakdown
    print("Per Service Error Rates (39.0 vs 39.4):")
    for result in results:
        service = result['Service'].split(':')[0]  # Shorten name
        error = result['Error 39 vs 39.4']
        if abs(error) > 0.001:
            print(f"  {service}: {error:+.3f}%")
        else:
            print(f"  {service}: {error:+.3f}% (minimal)")
    
    # Calculate theoretical impact
    print(f"\nTheoretical Analysis:")
    print(f"  0.4 years represents {0.4/39.4*100:.2f}% of the total projection period")
    print(f"  For high-inflation items, this compounds significantly over time")
    
    return results

if __name__ == '__main__':
    results = manual_fractional_calculation()