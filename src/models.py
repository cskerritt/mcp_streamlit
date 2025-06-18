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
    frequency_per_year: float
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
    
    # Distributed instances support
    is_distributed_instances: bool = False
    total_instances: Optional[int] = None
    distribution_period_years: Optional[float] = None
    
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
        
        if self.frequency_per_year <= 0:
            raise ValueError("Frequency per year must be greater than zero")

        # One-time costs should have frequency of 1
        if self.is_one_time_cost and self.frequency_per_year != 1:
            self.frequency_per_year = 1
        
        # Validate distributed instances
        if self.is_distributed_instances:
            if self.total_instances is None or self.total_instances <= 0:
                raise ValueError("Distributed instances must have a positive total instance count")
            if self.distribution_period_years is None or self.distribution_period_years <= 0:
                raise ValueError("Distributed instances must have a positive distribution period")
            # Calculate effective frequency per year based on distribution
            self.frequency_per_year = self.total_instances / self.distribution_period_years


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
class Scenario:
    """Represents a specific scenario for analysis within a life care plan."""
    name: str
    description: str = ""
    settings: ProjectionSettings = None
    tables: Dict[str, ServiceTable] = field(default_factory=dict)
    is_baseline: bool = False
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def add_table(self, table: ServiceTable) -> None:
        """Add a service table to this scenario."""
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
    
    def copy(self, new_name: str, new_description: str = "") -> 'Scenario':
        """Create a copy of this scenario with a new name."""
        import copy
        new_scenario = Scenario(
            name=new_name,
            description=new_description,
            settings=copy.deepcopy(self.settings),
            tables=copy.deepcopy(self.tables),
            is_baseline=False,
            created_at=datetime.now()
        )
        return new_scenario


@dataclass
class LifeCarePlan:
    """Main life care plan containing all data and settings."""
    evaluee: Evaluee
    settings: ProjectionSettings  # Default settings (used for baseline scenario)
    _tables: Dict[str, ServiceTable] = field(default_factory=dict)  # Default tables (baseline scenario)
    scenarios: Dict[str, Scenario] = field(default_factory=dict)
    active_scenario: Optional[str] = None  # Name of currently active scenario
    
    def __post_init__(self):
        """Initialize the baseline scenario if no scenarios exist."""
        if not self.scenarios:
            # Create baseline scenario from default tables and settings
            baseline_scenario = Scenario(
                name="Baseline",
                description="Default baseline scenario",
                settings=self.settings,
                tables=self._tables,
                is_baseline=True,
                created_at=datetime.now()
            )
            self.scenarios["Baseline"] = baseline_scenario
            self.active_scenario = "Baseline"
    
    def get_current_scenario(self) -> Scenario:
        """Get the currently active scenario."""
        if self.active_scenario and self.active_scenario in self.scenarios:
            return self.scenarios[self.active_scenario]
        else:
            # Fallback to baseline if available
            baseline = self.get_baseline_scenario()
            if baseline:
                self.active_scenario = baseline.name
                return baseline
            else:
                # Create baseline if none exists
                self.__post_init__()
                return self.scenarios["Baseline"]
    
    def get_baseline_scenario(self) -> Optional[Scenario]:
        """Get the baseline scenario."""
        for scenario in self.scenarios.values():
            if scenario.is_baseline:
                return scenario
        # If no baseline found, return the first scenario
        if self.scenarios:
            return list(self.scenarios.values())[0]
        return None
    
    def add_scenario(self, scenario: Scenario) -> None:
        """Add a new scenario to the plan."""
        self.scenarios[scenario.name] = scenario
    
    def remove_scenario(self, scenario_name: str) -> bool:
        """Remove a scenario by name. Cannot remove baseline scenario."""
        if scenario_name in self.scenarios:
            scenario = self.scenarios[scenario_name]
            if scenario.is_baseline:
                return False  # Cannot remove baseline
            del self.scenarios[scenario_name]
            # If we deleted the active scenario, switch to baseline
            if self.active_scenario == scenario_name:
                baseline = self.get_baseline_scenario()
                self.active_scenario = baseline.name if baseline else None
            return True
        return False
    
    def copy_scenario(self, source_name: str, new_name: str, new_description: str = "") -> bool:
        """Copy a scenario with a new name."""
        if source_name in self.scenarios and new_name not in self.scenarios:
            source_scenario = self.scenarios[source_name]
            new_scenario = source_scenario.copy(new_name, new_description)
            self.scenarios[new_name] = new_scenario
            return True
        return False
    
    def rename_scenario(self, old_name: str, new_name: str) -> bool:
        """Rename a scenario. Cannot rename baseline scenario."""
        if old_name in self.scenarios and new_name not in self.scenarios:
            scenario = self.scenarios[old_name]
            if scenario.is_baseline:
                return False  # Cannot rename baseline
            scenario.name = new_name
            self.scenarios[new_name] = scenario
            del self.scenarios[old_name]
            # Update active scenario if it was the renamed one
            if self.active_scenario == old_name:
                self.active_scenario = new_name
            return True
        return False
    
    def set_active_scenario(self, scenario_name: str) -> bool:
        """Set the active scenario."""
        if scenario_name in self.scenarios:
            self.active_scenario = scenario_name
            return True
        return False
    
    # Legacy methods that work with current scenario for backward compatibility
    def add_table(self, table: ServiceTable) -> None:
        """Add a service table to the current scenario."""
        current_scenario = self.get_current_scenario()
        current_scenario.add_table(table)
    
    def remove_table(self, table_name: str) -> bool:
        """Remove a table by name from current scenario."""
        current_scenario = self.get_current_scenario()
        return current_scenario.remove_table(table_name)
    
    def get_table(self, table_name: str) -> Optional[ServiceTable]:
        """Get a table by name from current scenario."""
        current_scenario = self.get_current_scenario()
        return current_scenario.get_table(table_name)
    
    def get_all_services(self) -> List[tuple[str, Service]]:
        """Get all services with their table names from current scenario."""
        current_scenario = self.get_current_scenario()
        return current_scenario.get_all_services()
    
    @property
    def tables(self) -> Dict[str, ServiceTable]:
        """Get tables from current scenario (for backward compatibility)."""
        current_scenario = self.get_current_scenario()
        return current_scenario.tables
    
    @tables.setter
    def tables(self, value: Dict[str, ServiceTable]):
        """Set tables in current scenario (for backward compatibility)."""
        current_scenario = self.get_current_scenario()
        current_scenario.tables = value


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