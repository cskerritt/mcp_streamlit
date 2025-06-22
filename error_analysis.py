#!/usr/bin/env python3

import pandas as pd
from src.models import LifeCarePlan, Evaluee, ProjectionSettings, ServiceTable, Service
from src.calculator import CostCalculator

def detailed_error_analysis():
    print('=== DETAILED PROJECTION YEARS IMPACT ANALYSIS ===')
    print()
    
    # Test with services that span different periods to show the impact
    test_scenarios = [
        {'name': 'High-Cost Surgery', 'cost': 100000, 'inflation': 0.035, 'frequency': 1},
        {'name': 'Daily Medication', 'cost': 50, 'inflation': 0.06, 'frequency': 365},
        {'name': 'Weekly Therapy', 'cost': 150, 'inflation': 0.032, 'frequency': 52},
        {'name': 'Monthly Evaluation', 'cost': 500, 'inflation': 0.028, 'frequency': 12}
    ]
    
    print('Comparing different projection periods:')
    projection_periods = [39.0, 39.2, 39.4, 39.6, 39.8, 40.0]
    
    results = []
    
    for scenario in test_scenarios:
        print(f'\nService: {scenario["name"]} (${scenario["cost"]}/unit, {scenario["frequency"]}x/year)')
        scenario_results = {'Service': scenario['name']}
        
        baseline_total = None
        
        for years in projection_periods:
            evaluee = Evaluee(name='Test', current_age=37.8)
            settings = ProjectionSettings(base_year=2025, projection_years=years, discount_rate=0.035)
            lcp = LifeCarePlan(evaluee=evaluee, settings=settings)
            
            table = ServiceTable(name='Test')
            table.add_service(Service(
                name=scenario['name'],
                inflation_rate=scenario['inflation'],
                unit_cost=scenario['cost'],
                frequency_per_year=scenario['frequency'],
                start_year=2025,
                end_year=None
            ))
            lcp.add_table(table)
            
            calc = CostCalculator(lcp)
            schedule = calc.build_cost_schedule()
            total = schedule['Total Nominal'].sum()
            
            if baseline_total is None:
                baseline_total = total
            
            scenario_results[f'{years} yrs'] = total
            
            # Calculate percentage difference from baseline
            pct_diff = ((total - baseline_total) / baseline_total) * 100
            
            print(f'  {years:4.1f} years: ${total:12,.2f} ({pct_diff:+6.3f}%)')
        
        results.append(scenario_results)
    
    # Show the specific impact of 39.0 vs 39.4
    print('\n=== SPECIFIC 39.0 vs 39.4 COMPARISON ===')
    
    total_39 = 0
    total_394 = 0
    
    for result in results:
        service = result['Service']
        val_39 = result['39.0 yrs']
        val_394 = result['39.4 yrs']
        diff = val_394 - val_39
        pct_diff = ((val_394 - val_39) / val_39) * 100
        
        total_39 += val_39
        total_394 += val_394
        
        print(f'{service}:')
        print(f'  39.0 years: ${val_39:12,.2f}')
        print(f'  39.4 years: ${val_394:12,.2f}')
        print(f'  Difference: ${diff:12,.2f} ({pct_diff:+.3f}%)')
        print()
    
    overall_diff = total_394 - total_39
    overall_pct = ((total_394 - total_39) / total_39) * 100
    
    print('OVERALL IMPACT:')
    print(f'Total 39.0 years: ${total_39:12,.2f}')
    print(f'Total 39.4 years: ${total_394:12,.2f}')
    print(f'Overall difference: ${overall_diff:12,.2f} ({overall_pct:+.3f}%)')
    
    # Calculate error magnitude
    print(f'\nERROR ANALYSIS:')
    print(f'Using 39.0 instead of 39.4 years results in:')
    print(f'- Absolute underestimation: ${overall_diff:,.2f}')
    print(f'- Relative error rate: {overall_pct:.3f}%')
    
    # Show compound effect over time
    if overall_pct > 0:
        print(f'- This represents missing {0.4/39.4*100:.1f}% of the projection period')
        print(f'- Per $1M in total costs, error = ${overall_pct/100 * 1000000:,.2f}')
    
    return results

if __name__ == '__main__':
    results = detailed_error_analysis()