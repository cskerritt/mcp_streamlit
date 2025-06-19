import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Any
from .models import LifeCarePlan, Service


class CostCalculator:
    """Handles all cost calculations for life care plan projections."""
    
    def __init__(self, life_care_plan: LifeCarePlan):
        self.lcp = life_care_plan
        self.precision = Decimal('0.01')
    
    def calculate_service_cost(self, service: Service, year: int) -> Decimal:
        """Calculate the cost of a service for a specific year."""
        try:
            years_from_base = year - self.lcp.settings.base_year
            
            if years_from_base < 0:
                return Decimal('0')
            
            # Validate service data
            if service.unit_cost is None or service.frequency_per_year is None:
                return Decimal('0')
            
            base_cost = Decimal(str(service.unit_cost)) * Decimal(str(service.frequency_per_year))
        except (ValueError, TypeError, AttributeError):
            return Decimal('0')
        
        # Handle one-time costs
        if service.is_one_time_cost:
            if year == service.one_time_cost_year:
                # For one-time costs, grow from base year to the occurrence year
                years_to_occurrence = service.one_time_cost_year - self.lcp.settings.base_year
                if years_to_occurrence < 0:
                    years_to_occurrence = 0
                # FIX: Treat inflation_rate as decimal consistently with recurring costs
                inflation_factor = Decimal(str(1 + service.inflation_rate)) ** years_to_occurrence
                return (base_cost * inflation_factor).quantize(self.precision, rounding=ROUND_HALF_UP)
            else:
                return Decimal('0')
        
        # Handle recurring and discrete services (existing logic)
        # Calculate inflation adjustment from base year
        inflation_factor = Decimal(str(1 + service.inflation_rate)) ** int(years_from_base)
        
        # Check if service applies to this year
        if service.occurrence_years:
            # Discrete occurrence service
            if year in service.occurrence_years:
                return (base_cost * inflation_factor).quantize(self.precision, rounding=ROUND_HALF_UP)
            else:
                return Decimal('0')
        else:
            # Recurring service or distributed instances - handle None values
            start_year = service.start_year if service.start_year is not None else self.lcp.settings.base_year
            end_year = service.end_year if service.end_year is not None else self.lcp.settings.base_year + int(self.lcp.settings.projection_years) - 1
            
            # Handle distributed instances differently
            if hasattr(service, 'is_distributed_instances') and service.is_distributed_instances:
                # For distributed instances, check if we're within the distribution period
                distribution_end_year = service.start_year + service.distribution_period_years
                if start_year <= year < distribution_end_year:
                    # Calculate cost using the calculated frequency per year
                    return (base_cost * inflation_factor).quantize(self.precision, rounding=ROUND_HALF_UP)
                else:
                    return Decimal('0')
            else:
                # Regular recurring service
                if start_year <= year <= end_year:
                    return (base_cost * inflation_factor).quantize(self.precision, rounding=ROUND_HALF_UP)
                else:
                    return Decimal('0')
    
    def calculate_present_value(self, future_value: Decimal, years_from_base: int) -> Decimal:
        """Calculate present value of a future cost."""
        # If discount calculations are disabled, return the nominal value
        if not self.lcp.evaluee.discount_calculations:
            return future_value
            
        if years_from_base == 0:
            return future_value
        
        discount_factor = Decimal(str(1 + self.lcp.settings.discount_rate)) ** years_from_base
        return (future_value / discount_factor).quantize(self.precision, rounding=ROUND_HALF_UP)
    
    def build_cost_schedule(self) -> pd.DataFrame:
        """Build comprehensive year-by-year cost schedule."""
        base_year = int(self.lcp.settings.base_year)
        projection_years = self.lcp.settings.projection_years
        end_year = base_year + int(projection_years)
        
        # Handle fractional years by including partial year if needed
        if projection_years % 1 != 0:
            end_year += 1
        
        year_range = range(base_year, end_year)
        
        rows = []
        
        for year in year_range:
            age = self.lcp.evaluee.current_age + (year - base_year)
            row = {"Year": year, "Age": age}
            
            total_nominal = Decimal('0')
            
            # Calculate costs for each service
            for table_name, table in self.lcp.tables.items():
                for service in table.services:
                    cost = self.calculate_service_cost(service, year)
                    
                    # Create descriptive column name
                    if service.occurrence_years:
                        occurrences = len(service.occurrence_years)
                        col_name = f'{table_name}: {service.name}\n({occurrences} occ. @ {service.inflation_rate*100:.1f}%)'
                    elif hasattr(service, 'is_distributed_instances') and service.is_distributed_instances:
                        # Distributed instances - show total instances over period
                        col_name = f'{table_name}: {service.name}\n({service.total_instances}x over {service.distribution_period_years:.1f} yrs @ {service.inflation_rate*100:.1f}%)'
                    else:
                        # Handle None values for start_year and end_year
                        start_year = service.start_year if service.start_year is not None else self.lcp.settings.base_year
                        end_year = service.end_year if service.end_year is not None else self.lcp.settings.base_year + self.lcp.settings.projection_years - 1
                        duration = self.lcp.settings.projection_years if service.end_year is None else end_year - start_year + 1
                        col_name = f'{table_name}: {service.name}\n({duration} yrs @ {service.inflation_rate*100:.1f}%)'
                    
                    row[col_name] = float(cost)
                    total_nominal += cost
            
            row["Total Nominal"] = float(total_nominal)
            
            # Only include present value if discount calculations are enabled AND discount rate > 0
            if self.lcp.evaluee.discount_calculations and self.lcp.settings.discount_rate > 0:
                years_from_base = year - base_year
                present_value = self.calculate_present_value(total_nominal, years_from_base)
                row["Present Value"] = float(present_value)
            
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def calculate_summary_statistics(self) -> Dict[str, float]:
        """Calculate summary statistics for the life care plan."""
        df = self.build_cost_schedule()
        
        total_nominal = df["Total Nominal"].sum()
        total_present_value = df["Present Value"].sum() if self.lcp.evaluee.discount_calculations and "Present Value" in df.columns else 0
        
        # Calculate statistics by table
        table_stats = {}
        for table_name, table in self.lcp.tables.items():
            table_nominal = Decimal('0')
            table_pv = Decimal('0')
            
            for year in range(self.lcp.settings.base_year, 
                            self.lcp.settings.base_year + int(self.lcp.settings.projection_years)):
                years_from_base = year - self.lcp.settings.base_year
                
                for service in table.services:
                    cost = self.calculate_service_cost(service, year)
                    table_nominal += cost
                    if self.lcp.evaluee.discount_calculations and self.lcp.settings.discount_rate > 0:
                        table_pv += self.calculate_present_value(cost, years_from_base)
            
            table_stats[table_name] = {
                "nominal_total": float(table_nominal),
                "present_value_total": float(table_pv) if self.lcp.evaluee.discount_calculations and self.lcp.settings.discount_rate > 0 else 0
            }
        
        # Calculate correct average using actual number of years with costs
        actual_years_with_costs = len(df[df["Total Nominal"] > 0]) if len(df) > 0 else int(self.lcp.settings.projection_years)
        average_annual_cost = total_nominal / actual_years_with_costs if actual_years_with_costs > 0 else 0
        
        return {
            "total_nominal_cost": total_nominal,
            "total_present_value": total_present_value,
            "average_annual_cost": average_annual_cost,
            "actual_years_with_costs": actual_years_with_costs,
            "table_statistics": table_stats,
            "projection_period": f"{self.lcp.settings.base_year}-{self.lcp.settings.base_year + self.lcp.settings.projection_years - 1:.1f}",
            "discount_rate": self.lcp.settings.discount_rate * 100
        }
    
    def get_cost_by_category(self) -> Dict[str, Dict[str, float]]:
        """Get costs broken down by service category."""
        category_costs = {}
        
        for table_name, table in self.lcp.tables.items():
            table_nominal = Decimal('0')
            table_pv = Decimal('0')
            service_details = []
            
            for service in table.services:
                service_nominal = Decimal('0')
                service_pv = Decimal('0')
                
                for year in range(self.lcp.settings.base_year, 
                                self.lcp.settings.base_year + int(self.lcp.settings.projection_years)):
                    years_from_base = year - self.lcp.settings.base_year
                    cost = self.calculate_service_cost(service, year)
                    service_nominal += cost
                    if self.lcp.evaluee.discount_calculations and self.lcp.settings.discount_rate > 0:
                        service_pv += self.calculate_present_value(cost, years_from_base)
                
                table_nominal += service_nominal
                if self.lcp.evaluee.discount_calculations and self.lcp.settings.discount_rate > 0:
                    table_pv += service_pv
                
                service_details.append({
                    "name": service.name,
                    "nominal_total": float(service_nominal),
                    "present_value_total": float(service_pv) if self.lcp.evaluee.discount_calculations and self.lcp.settings.discount_rate > 0 else 0,
                    "unit_cost": service.unit_cost,
                    "frequency_per_year": service.frequency_per_year,
                    "inflation_rate": service.inflation_rate * 100,
                    "start_year": service.start_year,
                    "end_year": service.end_year,
                    "occurrence_years": service.occurrence_years,
                    "is_one_time_cost": service.is_one_time_cost,
                    "one_time_cost_year": service.one_time_cost_year,
                    "is_distributed_instances": getattr(service, 'is_distributed_instances', False),
                    "total_instances": getattr(service, 'total_instances', None),
                    "distribution_period_years": getattr(service, 'distribution_period_years', None)
                })
            
            category_costs[table_name] = {
                "table_nominal_total": float(table_nominal),
                "table_present_value_total": float(table_pv) if self.lcp.evaluee.discount_calculations and self.lcp.settings.discount_rate > 0 else 0,
                "services": service_details
            }
        
        return category_costs
    
    def quality_control_validation(self) -> Dict[str, Any]:
        """
        Implement quality control matrix validation as suggested in audit:
        1. Extract service master table
        2. Generate yearly matrices: Cost_year[i,j] = UnitCost_j × Freq_j × (1 + infl_j)^(i)
        3. Row-sum → AnnualSchedule[i]; Column-sum → LifetimeCost[j]
        4. Assert: abs(Σ LifetimeCost[j] – Σ AnnualSchedule[i]) < $1
        """
        base_year = int(self.lcp.settings.base_year)
        projection_years = int(self.lcp.settings.projection_years)
        end_year = base_year + projection_years
        years = list(range(base_year, end_year))
        
        # Step 1: Extract service master table
        all_services = []
        for table_name, table in self.lcp.tables.items():
            for service in table.services:
                all_services.append({
                    'table_name': table_name,
                    'service': service,
                    'unit_cost': service.unit_cost,
                    'frequency': service.frequency_per_year,
                    'inflation_rate': service.inflation_rate
                })
        
        # Step 2: Generate yearly cost matrix
        cost_matrix = {}  # cost_matrix[year][service_index] = cost
        annual_schedule = {}  # annual_schedule[year] = total_cost
        lifetime_costs = {}  # lifetime_costs[service_index] = total_lifetime_cost
        
        for year in years:
            cost_matrix[year] = {}
            annual_total = Decimal('0')
            
            for service_idx, service_data in enumerate(all_services):
                service = service_data['service']
                cost = self.calculate_service_cost(service, year)
                cost_matrix[year][service_idx] = cost
                annual_total += cost
                
                # Accumulate lifetime cost for this service
                if service_idx not in lifetime_costs:
                    lifetime_costs[service_idx] = Decimal('0')
                lifetime_costs[service_idx] += cost
            
            annual_schedule[year] = annual_total
        
        # Step 3: Calculate sums
        sum_lifetime_costs = sum(lifetime_costs.values())
        sum_annual_schedule = sum(annual_schedule.values())
        
        # Step 4: Assert reconciliation within $1
        discrepancy = abs(sum_lifetime_costs - sum_annual_schedule)
        reconciliation_passes = discrepancy < 1.0
        
        return {
            'reconciliation_passes': reconciliation_passes,
            'discrepancy': float(discrepancy),
            'sum_lifetime_costs': float(sum_lifetime_costs),
            'sum_annual_schedule': float(sum_annual_schedule),
            'annual_schedule': {year: float(total) for year, total in annual_schedule.items()},
            'lifetime_costs': {idx: float(cost) for idx, cost in lifetime_costs.items()},
            'service_master': [
                {
                    'index': idx,
                    'table_name': s['table_name'],
                    'service_name': s['service'].name,
                    'unit_cost': s['unit_cost'],
                    'frequency': s['frequency'],
                    'inflation_rate': s['inflation_rate'],
                    'lifetime_cost': float(lifetime_costs[idx])
                } for idx, s in enumerate(all_services)
            ]
        }

    def perform_variance_analysis(self) -> Dict[str, Any]:
        """Perform comprehensive variance analysis and error detection."""
        
        # Get baseline calculations
        schedule = self.build_cost_schedule()
        summary = self.calculate_summary_statistics()
        category_costs = self.get_cost_by_category()
        qc_validation = self.quality_control_validation()
        
        analysis_results = {
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_integrity_checks': self._check_data_integrity(),
            'calculation_consistency': self._check_calculation_consistency(schedule, summary, category_costs),
            'reasonableness_checks': self._check_reasonableness(summary, schedule),
            'trend_analysis': self._analyze_trends(schedule),
            'error_flags': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Compile error flags and warnings
        if not qc_validation['reconciliation_passes']:
            analysis_results['error_flags'].append(f"Quality control reconciliation failed: ${qc_validation['discrepancy']:.2f} discrepancy")
        
        # Add recommendations based on analysis
        analysis_results['recommendations'] = self._generate_recommendations(analysis_results)
        
        return analysis_results

    def _check_data_integrity(self) -> Dict[str, Any]:
        """Check data integrity and completeness."""
        checks = {
            'missing_data': [],
            'invalid_values': [],
            'data_consistency': True
        }
        
        # Check for missing or invalid service data
        for table_name, table in self.lcp.tables.items():
            for service in table.services:
                if service.unit_cost <= 0:
                    checks['invalid_values'].append(f"{table_name}.{service.name}: Invalid unit cost (${service.unit_cost})")
                
                if service.frequency_per_year <= 0:
                    checks['invalid_values'].append(f"{table_name}.{service.name}: Invalid frequency ({service.frequency_per_year})")
                
                if service.inflation_rate < -0.1 or service.inflation_rate > 0.5:
                    checks['invalid_values'].append(f"{table_name}.{service.name}: Unusual inflation rate ({service.inflation_rate:.1%})")
                
                if not service.occurrence_years and not service.start_year and not service.end_year:
                    checks['missing_data'].append(f"{table_name}.{service.name}: Missing timing information")
        
        # Check projection settings
        if self.lcp.settings.projection_years <= 0 or self.lcp.settings.projection_years > 100:
            checks['invalid_values'].append(f"Unusual projection period: {self.lcp.settings.projection_years} years")
        
        if self.lcp.settings.discount_rate < 0 or self.lcp.settings.discount_rate > 0.2:
            checks['invalid_values'].append(f"Unusual discount rate: {self.lcp.settings.discount_rate:.1%}")
        
        checks['data_consistency'] = len(checks['missing_data']) == 0 and len(checks['invalid_values']) == 0
        
        return checks

    def _check_calculation_consistency(self, schedule: pd.DataFrame, summary: Dict, category_costs: Dict) -> Dict[str, Any]:
        """Check consistency across different calculation methods."""
        checks = {
            'schedule_vs_summary': {},
            'category_reconciliation': {},
            'present_value_consistency': {},
            'tolerance_met': True
        }
        
        # Schedule vs Summary consistency
        schedule_total = schedule['Total Nominal'].sum()
        summary_total = summary['total_nominal_cost']
        schedule_diff = abs(schedule_total - summary_total)
        
        checks['schedule_vs_summary'] = {
            'schedule_total': schedule_total,
            'summary_total': summary_total,
            'difference': schedule_diff,
            'passes': schedule_diff < 1.0
        }
        
        # Category reconciliation
        category_total = sum(data['table_nominal_total'] for data in category_costs.values())
        category_diff = abs(category_total - summary_total)
        
        checks['category_reconciliation'] = {
            'category_total': category_total,
            'summary_total': summary_total,
            'difference': category_diff,
            'passes': category_diff < 1.0
        }
        
        # Present value consistency (if enabled)
        if self.lcp.evaluee.discount_calculations and 'Present Value' in schedule.columns:
            schedule_pv = schedule['Present Value'].sum()
            summary_pv = summary['total_present_value']
            pv_diff = abs(schedule_pv - summary_pv)
            
            checks['present_value_consistency'] = {
                'schedule_pv': schedule_pv,
                'summary_pv': summary_pv,
                'difference': pv_diff,
                'passes': pv_diff < 1.0
            }
        
        checks['tolerance_met'] = all(
            check.get('passes', True) for check in checks.values() 
            if isinstance(check, dict) and 'passes' in check
        )
        
        return checks

    def _check_reasonableness(self, summary: Dict, schedule: pd.DataFrame) -> Dict[str, Any]:
        """Perform reasonableness checks on calculated values."""
        checks = {
            'cost_distribution': {},
            'growth_patterns': {},
            'outlier_detection': {},
            'age_progression': {}
        }
        
        # Cost distribution analysis
        annual_costs = schedule['Total Nominal'].values
        checks['cost_distribution'] = {
            'min_annual': float(annual_costs.min()),
            'max_annual': float(annual_costs.max()),
            'mean_annual': float(annual_costs.mean()),
            'std_annual': float(annual_costs.std()),
            'coefficient_of_variation': float(annual_costs.std() / annual_costs.mean()) if annual_costs.mean() > 0 else 0
        }
        
        # Growth pattern analysis
        if len(annual_costs) > 1:
            year_over_year_growth = [(annual_costs[i] - annual_costs[i-1]) / annual_costs[i-1] for i in range(1, len(annual_costs)) if annual_costs[i-1] > 0]
            if year_over_year_growth:
                checks['growth_patterns'] = {
                    'avg_growth_rate': float(sum(year_over_year_growth) / len(year_over_year_growth)),
                    'growth_volatility': float(pd.Series(year_over_year_growth).std()),
                    'extreme_growth_years': sum(1 for g in year_over_year_growth if abs(g) > 0.5)
                }
        
        # Outlier detection (costs >3 standard deviations from mean)
        if annual_costs.std() > 0:
            mean_cost = annual_costs.mean()
            std_cost = annual_costs.std()
            outliers = [i for i, cost in enumerate(annual_costs) if abs(cost - mean_cost) > 3 * std_cost]
            checks['outlier_detection'] = {
                'outlier_years': [int(schedule.iloc[i]['Year']) for i in outliers],
                'outlier_count': len(outliers)
            }
        
        # Age progression check
        ages = schedule['Age'].values
        expected_progression = [self.lcp.evaluee.current_age + i for i in range(len(ages))]
        age_errors = [abs(ages[i] - expected_progression[i]) for i in range(len(ages))]
        checks['age_progression'] = {
            'max_age_error': float(max(age_errors)) if age_errors else 0,
            'age_progression_correct': max(age_errors) < 0.1 if age_errors else True
        }
        
        return checks

    def _analyze_trends(self, schedule: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trends in cost projections."""
        annual_costs = schedule['Total Nominal'].values
        years = schedule['Year'].values
        
        trends = {
            'overall_trend': 'stable',
            'early_years_avg': 0,
            'middle_years_avg': 0,
            'late_years_avg': 0,
            'peak_cost_year': int(years[annual_costs.argmax()]),
            'peak_cost_amount': float(annual_costs.max())
        }
        
        # Divide into thirds for trend analysis
        third = len(annual_costs) // 3
        if third > 0:
            trends['early_years_avg'] = float(annual_costs[:third].mean())
            trends['middle_years_avg'] = float(annual_costs[third:2*third].mean())
            trends['late_years_avg'] = float(annual_costs[2*third:].mean())
            
            # Determine overall trend
            if trends['late_years_avg'] > trends['early_years_avg'] * 1.5:
                trends['overall_trend'] = 'increasing'
            elif trends['late_years_avg'] < trends['early_years_avg'] * 0.67:
                trends['overall_trend'] = 'decreasing'
            else:
                trends['overall_trend'] = 'stable'
        
        return trends

    def _generate_recommendations(self, analysis: Dict) -> list:
        """Generate recommendations based on analysis results."""
        recommendations = []
        
        # Data integrity recommendations
        if analysis['data_integrity_checks']['invalid_values']:
            recommendations.append("Review and correct invalid service values identified in data integrity checks")
        
        if analysis['data_integrity_checks']['missing_data']:
            recommendations.append("Complete missing service timing information for accurate projections")
        
        # Calculation consistency recommendations
        if not analysis['calculation_consistency']['tolerance_met']:
            recommendations.append("Investigate calculation discrepancies exceeding $1.00 tolerance")
        
        # Reasonableness recommendations
        reasonableness = analysis['reasonableness_checks']
        if reasonableness.get('cost_distribution', {}).get('coefficient_of_variation', 0) > 2.0:
            recommendations.append("High cost variability detected - review service distribution for potential outliers")
        
        if reasonableness.get('outlier_detection', {}).get('outlier_count', 0) > 0:
            outlier_years = reasonableness['outlier_detection']['outlier_years']
            recommendations.append(f"Unusual cost patterns in years: {', '.join(map(str, outlier_years))} - verify service assumptions")
        
        # Trend recommendations
        trends = analysis['trend_analysis']
        if trends['overall_trend'] == 'increasing':
            recommendations.append("Costs show strong upward trend - consider impact of inflation assumptions")
        elif trends['overall_trend'] == 'decreasing':
            recommendations.append("Costs show downward trend - verify service end dates and assumptions")
        
        if not recommendations:
            recommendations.append("All validation checks passed - calculations appear accurate and reasonable")
        
        return recommendations