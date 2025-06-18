import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple
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
                inflation_factor = Decimal(str(1 + service.inflation_rate)) ** years_to_occurrence
                return (base_cost * inflation_factor).quantize(self.precision, rounding=ROUND_HALF_UP)
            else:
                return Decimal('0')
        
        # Handle recurring and discrete services (existing logic)
        # Calculate inflation adjustment from base year
        inflation_factor = Decimal(str(1 + service.inflation_rate / 100)) ** int(years_from_base)
        
        # Check if service applies to this year
        if service.occurrence_years:
            # Discrete occurrence service
            if year in service.occurrence_years:
                return (base_cost * inflation_factor).quantize(self.precision, rounding=ROUND_HALF_UP)
            else:
                return Decimal('0')
        else:
            # Recurring service - handle None values
            start_year = service.start_year if service.start_year is not None else self.lcp.settings.base_year
            end_year = service.end_year if service.end_year is not None else self.lcp.settings.base_year + int(self.lcp.settings.projection_years) - 1
            
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
        projection_years = int(self.lcp.settings.projection_years)
        end_year = base_year + projection_years
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
                    else:
                        # Handle None values for start_year and end_year
                        start_year = service.start_year if service.start_year is not None else self.lcp.settings.base_year
                        end_year = service.end_year if service.end_year is not None else self.lcp.settings.base_year + int(self.lcp.settings.projection_years) - 1
                        duration = end_year - start_year + 1
                        col_name = f'{table_name}: {service.name}\n({duration} yrs @ {service.inflation_rate*100:.1f}%)'
                    
                    row[col_name] = float(cost)
                    total_nominal += cost
            
            row["Total Nominal"] = float(total_nominal)
            
            # Only include present value if discount calculations are enabled
            if self.lcp.evaluee.discount_calculations:
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
                    if self.lcp.evaluee.discount_calculations:
                        table_pv += self.calculate_present_value(cost, years_from_base)
            
            table_stats[table_name] = {
                "nominal_total": float(table_nominal),
                "present_value_total": float(table_pv) if self.lcp.evaluee.discount_calculations else 0
            }
        
        return {
            "total_nominal_cost": total_nominal,
            "total_present_value": total_present_value,
            "average_annual_cost": total_nominal / self.lcp.settings.projection_years,
            "table_statistics": table_stats,
            "projection_period": f"{self.lcp.settings.base_year}-{self.lcp.settings.base_year + int(self.lcp.settings.projection_years) - 1}",
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
                    if self.lcp.evaluee.discount_calculations:
                        service_pv += self.calculate_present_value(cost, years_from_base)
                
                table_nominal += service_nominal
                if self.lcp.evaluee.discount_calculations:
                    table_pv += service_pv
                
                service_details.append({
                    "name": service.name,
                    "nominal_total": float(service_nominal),
                    "present_value_total": float(service_pv) if self.lcp.evaluee.discount_calculations else 0,
                    "unit_cost": service.unit_cost,
                    "frequency_per_year": service.frequency_per_year,
                    "inflation_rate": service.inflation_rate * 100,
                    "start_year": service.start_year,
                    "end_year": service.end_year,
                    "occurrence_years": service.occurrence_years,
                    "is_one_time_cost": service.is_one_time_cost,
                    "one_time_cost_year": service.one_time_cost_year
                })
            
            category_costs[table_name] = {
                "table_nominal_total": float(table_nominal),
                "table_present_value_total": float(table_pv) if self.lcp.evaluee.discount_calculations else 0,
                "services": service_details
            }
        
        return category_costs