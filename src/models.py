from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, field_validator


@dataclass
class Service:
    """Represents a medical service or treatment in a life care plan."""
    name: str
    inflation_rate: float
    unit_cost: float
    frequency_per_year: int
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    occurrence_years: Optional[List[int]] = None
    
    # Cost range support
    cost_range_low: Optional[float] = None
    cost_range_high: Optional[float] = None
    use_cost_range: bool = False
    
    # One-time cost support
    is_one_time_cost: bool = False
    one_time_cost_year: Optional[int] = None
    
    def __post_init__(self):
        """Validate service data after initialization."""
        if not self.is_one_time_cost:
            if self.occurrence_years is None and (self.start_year is None or self.end_year is None):
                # For now, log the warning but don't fail - let calculator handle gracefully
                print(f"Warning: Service '{self.name}' missing timing information - calculator will use defaults")
        else:
            if self.one_time_cost_year is None:
                raise ValueError("One-time cost must have a specified year")
        
        if self.inflation_rate < 0:
            raise ValueError("Inflation rate cannot be negative")
        
        # Calculate average cost if using range
        if self.use_cost_range:
            if self.cost_range_low is None or self.cost_range_high is None:
                raise ValueError("Cost range requires both low and high values")
            if self.cost_range_low < 0 or self.cost_range_high < 0:
                raise ValueError("Cost range values cannot be negative")
            if self.cost_range_low > self.cost_range_high:
                raise ValueError("Cost range low value cannot be greater than high value")
            # Calculate average for unit_cost
            self.unit_cost = (self.cost_range_low + self.cost_range_high) / 2
        else:
            if self.unit_cost < 0:
                raise ValueError("Unit cost cannot be negative")
        
        if self.frequency_per_year < 0:
            raise ValueError("Frequency per year cannot be negative")
        
        # One-time costs should have frequency of 1
        if self.is_one_time_cost and self.frequency_per_year != 1:
            self.frequency_per_year = 1


@dataclass
class ServiceTable:
    """Represents a category of medical services."""
    name: str
    services: List[Service] = field(default_factory=list)
    
    def add_service(self, service: Service) -> None:
        """Add a service to this table."""
        self.services.append(service)
    
    def remove_service(self, service_name: str) -> bool:
        """Remove a service by name. Returns True if found and removed."""
        for i, service in enumerate(self.services):
            if service.name == service_name:
                self.services.pop(i)
                return True
        return False
    
    def get_service(self, service_name: str) -> Optional[Service]:
        """Get a service by name."""
        for service in self.services:
            if service.name == service_name:
                return service
        return None


@dataclass
class Evaluee:
    """Represents the person for whom the life care plan is being created."""
    name: str
    current_age: float
    birth_year: Optional[int] = None
    discount_calculations: bool = True  # Toggle for present value calculations
    
    def __post_init__(self):
        if self.birth_year is None:
            self.birth_year = datetime.now().year - int(self.current_age)


@dataclass
class ProjectionSettings:
    """Settings for the cost projection calculation."""
    base_year: int
    projection_years: float
    discount_rate: float
    
    def __post_init__(self):
        if self.projection_years <= 0:
            raise ValueError("Projection years must be positive")
        
        if self.discount_rate < 0:
            raise ValueError("Discount rate cannot be negative")


@dataclass
class LifeCarePlan:
    """Main life care plan containing all data and settings."""
    evaluee: Evaluee
    settings: ProjectionSettings
    tables: Dict[str, ServiceTable] = field(default_factory=dict)
    
    def add_table(self, table: ServiceTable) -> None:
        """Add a service table to the plan."""
        self.tables[table.name] = table
    
    def remove_table(self, table_name: str) -> bool:
        """Remove a table by name. Returns True if found and removed."""
        if table_name in self.tables:
            del self.tables[table_name]
            return True
        return False
    
    def get_table(self, table_name: str) -> Optional[ServiceTable]:
        """Get a table by name."""
        return self.tables.get(table_name)
    
    def get_all_services(self) -> List[tuple[str, Service]]:
        """Get all services with their table names."""
        services = []
        for table_name, table in self.tables.items():
            for service in table.services:
                services.append((table_name, service))
        return services


class LCPConfigModel(BaseModel):
    """Pydantic model for validating LCP configuration from JSON/YAML."""
    evaluee_name: str
    current_age: float
    base_year: int
    projection_years: float
    discount_rate: float
    tables: Dict[str, List[Dict[str, Any]]]
    
    @field_validator('current_age')
    @classmethod
    def validate_age(cls, v):
        if v <= 0 or v > 120:
            raise ValueError('Age must be between 0.1 and 120')
        return v
    
    @field_validator('discount_rate')
    @classmethod
    def validate_discount_rate(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Discount rate must be between 0 and 1')
        return v
    
    def to_life_care_plan(self) -> LifeCarePlan:
        """Convert this config model to a LifeCarePlan object."""
        evaluee = Evaluee(name=self.evaluee_name, current_age=self.current_age)
        settings = ProjectionSettings(
            base_year=self.base_year,
            projection_years=self.projection_years,
            discount_rate=self.discount_rate
        )
        
        lcp = LifeCarePlan(evaluee=evaluee, settings=settings)
        
        for table_name, services_data in self.tables.items():
            table = ServiceTable(name=table_name)
            for service_data in services_data:
                service = Service(**service_data)
                table.add_service(service)
            lcp.add_table(table)
        
        return lcp