from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import json
import os
import tempfile
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.utils

from src.models import LifeCarePlan, Evaluee, ProjectionSettings, ServiceTable, Service, LCPConfigModel
from src.calculator import CostCalculator
from src.exporters import ExcelExporter, WordExporter, PDFExporter
from src.database import db

app = FastAPI(title="Life Care Plan Table Generator", description="Interactive Economic Analysis Tool")

# Create directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("temp_files", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global variables to store current LCP data and table templates
current_lcp_data = None

# No more pre-built templates - users create their own tables


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/create_evaluee")
async def create_evaluee(
    name: str = Form(...),
    age: float = Form(...),
    base_year: int = Form(2025),
    projection_years: float = Form(30),
    discount_rate: float = Form(0.03),
    discount_calculations: bool = Form(True)
):
    """Create a new evaluee and projection settings."""
    global current_lcp_data
    
    try:
        evaluee = Evaluee(name=name, current_age=age, discount_calculations=discount_calculations)
        settings = ProjectionSettings(
            base_year=base_year,
            projection_years=projection_years,
            discount_rate=discount_rate
        )
        
        current_lcp_data = LifeCarePlan(evaluee=evaluee, settings=settings)
        
        # Auto-save to database
        try:
            db.save_life_care_plan(current_lcp_data)
        except Exception as e:
            print(f"Warning: Could not save to database: {e}")
        
        return {
            "success": True,
            "message": f"Created life care plan for {name}",
            "evaluee": {
                "name": name,
                "age": age,
                "base_year": base_year,
                "projection_years": projection_years,
                "discount_rate": discount_rate,
                "discount_calculations": discount_calculations
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/delete_evaluee")
async def delete_evaluee():
    """Delete the current evaluee and all associated data."""
    global current_lcp_data
    
    if not current_lcp_data:
        return {
            "success": False,
            "message": "No life care plan exists to delete"
        }
    
    try:
        evaluee_name = current_lcp_data.evaluee.name if current_lcp_data.evaluee else "Unknown"
        current_lcp_data = None
        
        return {
            "success": True,
            "message": f"Deleted life care plan for {evaluee_name}"
        }
        
    except Exception as e:
        print(f"Error deleting evaluee: {str(e)}")
        return {
            "success": False,
            "message": f"Error deleting evaluee: {str(e)}"
        }


@app.post("/api/add_service_table")
async def add_service_table(
    table_name: str = Form(...),
    default_inflation_rate: float = Form(3.5)
):
    """Add a new user-created service table."""
    global current_lcp_data
    
    if not current_lcp_data:
        raise HTTPException(status_code=400, detail="No life care plan created yet")
    
    if table_name in current_lcp_data.tables:
        raise HTTPException(status_code=400, detail="Table already exists")
    
    table = ServiceTable(name=table_name)
    # Store the default inflation rate as a table attribute
    table.default_inflation_rate = default_inflation_rate
    current_lcp_data.add_table(table)
    
    # Auto-save to database
    try:
        db.save_life_care_plan(current_lcp_data)
    except Exception as e:
        print(f"Warning: Could not save to database: {e}")
    
    return {
        "success": True, 
        "message": f"Added table: {table_name} with {default_inflation_rate}% default inflation rate"
    }


@app.post("/api/add_service")
async def add_service(
    table_name: str = Form(...),
    service_name: str = Form(...),
    unit_cost: Optional[float] = Form(None),
    frequency_per_year: float = Form(...),
    inflation_rate: float = Form(...),
    service_type: Optional[str] = Form(None),  # "recurring" or "discrete" 
    start_year: Optional[int] = Form(None),
    end_year: Optional[int] = Form(None),
    occurrence_years: Optional[str] = Form(None),  # Comma-separated years
    
    # Cost range fields
    use_cost_range: bool = Form(False),
    cost_range_low: Optional[float] = Form(None),
    cost_range_high: Optional[float] = Form(None),
    
    # One-time cost fields
    is_one_time_cost: bool = Form(False),
    one_time_cost_year: Optional[int] = Form(None)
):
    """Add a service to a table."""
    global current_lcp_data
    
    if not current_lcp_data:
        raise HTTPException(status_code=400, detail="No life care plan created yet")
    
    table = current_lcp_data.get_table(table_name)
    if not table:
        raise HTTPException(status_code=400, detail=f"Table '{table_name}' not found")
    
    try:
        # Debug logging - comprehensive form data inspection
        print(f"\n=== DEBUG: Adding service ===")
        print(f"Service name: '{service_name}'")
        print(f"Table name: '{table_name}'") 
        print(f"Unit cost: {unit_cost}")
        print(f"Frequency per year: {frequency_per_year}")
        print(f"Inflation rate: {inflation_rate}")
        print(f"Service type: '{service_type}'")
        print(f"Start year: {start_year}")
        print(f"End year: {end_year}")
        print(f"Occurrence years: '{occurrence_years}'")
        print(f"Use cost range: {use_cost_range}")
        print(f"Cost range low: {cost_range_low}")
        print(f"Cost range high: {cost_range_high}")
        print(f"Is one-time cost: {is_one_time_cost}")
        print(f"One-time cost year: {one_time_cost_year}")
        print("=== End DEBUG ===\n")
        
        # Prepare service parameters
        service_params = {
            "name": service_name,
            "inflation_rate": inflation_rate / 100,  # Convert percentage to decimal
            "frequency_per_year": frequency_per_year,
            "use_cost_range": use_cost_range,
            "is_one_time_cost": is_one_time_cost
        }
        
        # Handle cost inputs
        if use_cost_range:
            if cost_range_low is None or cost_range_high is None:
                raise ValueError("Cost range requires both low and high values")
            service_params.update({
                "cost_range_low": cost_range_low,
                "cost_range_high": cost_range_high,
                "unit_cost": 0  # Will be calculated in model
            })
        else:
            if unit_cost is None:
                raise ValueError("Unit cost is required when not using cost range")
            service_params["unit_cost"] = unit_cost
        
        # Handle service timing
        if is_one_time_cost:
            if one_time_cost_year is None:
                raise ValueError("One-time cost year is required for one-time costs")
            service_params["one_time_cost_year"] = one_time_cost_year
        else:
            if service_type == "recurring":
                if start_year is None or end_year is None:
                    raise ValueError("Start year and end year required for recurring services")
                service_params.update({
                    "start_year": start_year,
                    "end_year": end_year
                })
            elif service_type == "discrete":
                if not occurrence_years or occurrence_years.strip() == "":
                    raise ValueError("Occurrence years required for discrete services")
                
                # Parse occurrence years
                try:
                    years_list = [int(year.strip()) for year in occurrence_years.split(",") if year.strip()]
                    if not years_list:
                        raise ValueError("No valid years found in occurrence years")
                except ValueError as ve:
                    raise ValueError(f"Invalid occurrence years format: {occurrence_years}")
                
                service_params["occurrence_years"] = years_list
            else:
                raise ValueError("Service type is required for non-one-time costs")
        
        service = Service(**service_params)
        
        table.add_service(service)
        
        # Auto-save to database
        try:
            db.save_life_care_plan(current_lcp_data)
        except Exception as e:
            print(f"Warning: Could not save to database: {e}")
        
        return {
            "success": True,
            "message": f"Added service: {service_name} to {table_name}"
        }
        
    except ValueError as ve:
        print(f"ValueError adding service: {str(ve)}")
        return {
            "success": False,
            "message": str(ve)
        }
    except Exception as e:
        print(f"Unexpected error adding service: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}"
        }


@app.post("/api/edit_service")
async def edit_service(
    table_name: str = Form(...),
    service_index: int = Form(...),
    service_name: str = Form(...),
    unit_cost: float = Form(...),
    frequency_per_year: float = Form(...),
    inflation_rate: float = Form(...),
    service_type: str = Form(...),  # "recurring" or "discrete"
    start_year: Optional[int] = Form(None),
    end_year: Optional[int] = Form(None),
    occurrence_years: Optional[str] = Form(None)  # Comma-separated years
):
    """Edit an existing service in a table."""
    global current_lcp_data
    
    if not current_lcp_data:
        raise HTTPException(status_code=400, detail="No life care plan created yet")
    
    table = current_lcp_data.get_table(table_name)
    if not table:
        raise HTTPException(status_code=400, detail=f"Table '{table_name}' not found")
    
    if service_index < 0 or service_index >= len(table.services):
        raise HTTPException(status_code=400, detail="Service index out of range")
    
    try:
        print(f"DEBUG: Editing service {service_index} in table: {table_name}")
        print(f"DEBUG: New data - Name: {service_name}, Cost: {unit_cost}, Frequency: {frequency_per_year}")
        print(f"DEBUG: Inflation: {inflation_rate}, Type: {service_type}")
        
        if service_type == "recurring":
            if start_year is None or end_year is None:
                raise ValueError("Start year and end year required for recurring services")
            
            new_service = Service(
                name=service_name,
                inflation_rate=inflation_rate / 100,  # Convert percentage to decimal
                unit_cost=unit_cost,
                frequency_per_year=frequency_per_year,
                start_year=start_year,
                end_year=end_year
            )
        elif service_type == "discrete":
            if not occurrence_years or occurrence_years.strip() == "":
                raise ValueError("Occurrence years required for discrete services")
            
            try:
                years_list = [int(year.strip()) for year in occurrence_years.split(",") if year.strip()]
                if not years_list:
                    raise ValueError("No valid years found in occurrence years")
            except ValueError as ve:
                raise ValueError(f"Invalid occurrence years format: {occurrence_years}. Please use comma-separated years.")
            
            new_service = Service(
                name=service_name,
                inflation_rate=inflation_rate / 100,  # Convert percentage to decimal
                unit_cost=unit_cost,
                frequency_per_year=frequency_per_year,
                occurrence_years=years_list
            )
        else:
            raise ValueError(f"Invalid service type: {service_type}")
        
        # Replace the service
        table.services[service_index] = new_service
        
        return {
            "success": True,
            "message": f"Updated service: {service_name} in {table_name}"
        }
        
    except Exception as e:
        print(f"Error editing service: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/delete_service")
async def delete_service(
    table_name: str = Form(...),
    service_index: int = Form(...)
):
    """Delete a service from a table."""
    global current_lcp_data
    
    if not current_lcp_data:
        return {
            "success": False,
            "message": "No life care plan created yet"
        }
    
    table = current_lcp_data.get_table(table_name)
    if not table:
        return {
            "success": False,
            "message": f"Table '{table_name}' not found"
        }
    
    if service_index < 0 or service_index >= len(table.services):
        return {
            "success": False,
            "message": "Service index out of range"
        }
    
    try:
        service_name = table.services[service_index].name
        del table.services[service_index]
        
        return {
            "success": True,
            "message": f"Deleted service: {service_name} from {table_name}"
        }
        
    except Exception as e:
        print(f"Error deleting service: {str(e)}")
        return {
            "success": False,
            "message": f"Error deleting service: {str(e)}"
        }


# Template endpoints removed - users create their own tables


@app.post("/api/load_sample_data")
async def load_sample_data():
    """Load sample evaluee data for testing."""
    global current_lcp_data
    
    try:
        # Create sample evaluee
        evaluee = Evaluee(name="Jane Doe Sample", current_age=35, discount_calculations=True)
        settings = ProjectionSettings(
            base_year=2025,
            projection_years=30,
            discount_rate=0.035
        )
        
        current_lcp_data = LifeCarePlan(evaluee=evaluee, settings=settings)
        
        # No pre-built tables - user will create their own
        
        return {
            "success": True,
            "message": "Sample evaluee loaded - create your own tables and services",
            "evaluee": {
                "name": "Jane Doe Sample",
                "age": 35,
                "base_year": 2025,
                "projection_years": 30,
                "discount_rate": 0.035,
                "discount_calculations": True
            },
            "tables_count": 0,
            "total_services": 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading sample data: {str(e)}")


# All template endpoints removed - users create tables directly


@app.get("/api/table_growth_rates")
async def get_table_growth_rates():
    """Get current inflation/growth rates for all tables."""
    global current_lcp_data
    
    if not current_lcp_data:
        return {"success": False, "message": "No life care plan created yet"}
    
    growth_rates = {}
    
    for table_name, table in current_lcp_data.tables.items():
        services_rates = []
        for service in table.services:
            services_rates.append({
                "name": service.name,
                "inflation_rate": service.inflation_rate * 100,
                "unit_cost": service.unit_cost,
                "frequency_per_year": service.frequency_per_year
            })
        
        # Calculate average inflation rate for the table
        if services_rates:
            avg_inflation = sum(s["inflation_rate"] for s in services_rates) / len(services_rates)
        else:
            avg_inflation = 0
        
        growth_rates[table_name] = {
            "average_inflation_rate": round(avg_inflation, 2),
            "service_count": len(services_rates),
            "services": services_rates,
            "table_default": getattr(table, 'default_inflation_rate', 0)
        }
    
    return {
        "success": True,
        "growth_rates": growth_rates
    }


@app.post("/api/update_table_inflation")
async def update_table_inflation(
    table_name: str = Form(...),
    new_inflation_rate: float = Form(...)
):
    """Update inflation rate for all services in a table."""
    global current_lcp_data
    
    if not current_lcp_data:
        raise HTTPException(status_code=400, detail="No life care plan created yet")
    
    table = current_lcp_data.get_table(table_name)
    if not table:
        raise HTTPException(status_code=400, detail="Table not found")
    
    try:
        services_updated = 0
        for service in table.services:
            service.inflation_rate = new_inflation_rate / 100
            services_updated += 1
        
        return {
            "success": True,
            "message": f"Updated inflation rate to {new_inflation_rate}% for {services_updated} services in '{table_name}'",
            "services_updated": services_updated,
            "new_rate": new_inflation_rate
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/calculate")
async def calculate_costs():
    """Calculate costs and return results."""
    global current_lcp_data
    
    if not current_lcp_data:
        return {
            "success": False,
            "message": "Please create an evaluee first, then add service tables with services before calculating costs. Use 'Load Sample Data' for a quick start."
        }
    
    try:
        calculator = CostCalculator(current_lcp_data)
        
        # Get cost schedule
        df = calculator.build_cost_schedule()
        
        # Get summary statistics
        summary = calculator.calculate_summary_statistics()
        
        # Get category costs
        category_costs = calculator.get_cost_by_category()
        
        # Create chart data
        chart_data = create_chart_data(df)
        
        return {
            "success": True,
            "summary": summary,
            "category_costs": category_costs,
            "cost_schedule": df.to_dict('records'),
            "chart_data": chart_data
        }
        
    except Exception as e:
        print(f"Error calculating costs: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "message": f"Calculation error: {str(e)}"
        }


def create_chart_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Create chart data for visualization."""
    
    has_present_value = "Present Value" in df.columns
    
    if has_present_value:
        # Present Value by Year Chart
        pv_chart = go.Figure()
        pv_chart.add_trace(go.Bar(
            x=df["Year"],
            y=df["Present Value"],
            name="Present Value",
            marker_color="steelblue"
        ))
        pv_chart.update_layout(
            title="Present Value of Medical Costs by Year",
            xaxis_title="Year",
            yaxis_title="Present Value ($)",
            template="plotly_white"
        )
        
        # Nominal vs Present Value Comparison
        comparison_chart = go.Figure()
        comparison_chart.add_trace(go.Scatter(
            x=df["Year"],
            y=df["Total Nominal"],
            mode='lines+markers',
            name="Nominal Cost",
            line=dict(color="red")
        ))
        comparison_chart.add_trace(go.Scatter(
            x=df["Year"],
            y=df["Present Value"],
            mode='lines+markers',
            name="Present Value",
            line=dict(color="blue")
        ))
        comparison_chart.update_layout(
            title="Nominal Cost vs Present Value Over Time",
            xaxis_title="Year",
            yaxis_title="Cost ($)",
            template="plotly_white"
        )
        
        return {
            "present_value_chart": json.dumps(pv_chart, cls=plotly.utils.PlotlyJSONEncoder),
            "comparison_chart": json.dumps(comparison_chart, cls=plotly.utils.PlotlyJSONEncoder)
        }
    else:
        # Only show nominal cost chart when PV calculations are disabled
        nominal_chart = go.Figure()
        nominal_chart.add_trace(go.Bar(
            x=df["Year"],
            y=df["Total Nominal"],
            name="Nominal Cost",
            marker_color="green"
        ))
        nominal_chart.update_layout(
            title="Nominal Medical Costs by Year",
            xaxis_title="Year",
            yaxis_title="Nominal Cost ($)",
            template="plotly_white"
        )
        
        return {
            "nominal_chart": json.dumps(nominal_chart, cls=plotly.utils.PlotlyJSONEncoder)
        }


@app.get("/api/export/{format}")
async def export_results(format: str):
    """Export results in specified format."""
    global current_lcp_data
    
    if not current_lcp_data:
        raise HTTPException(status_code=400, detail="No life care plan created yet")
    
    if format not in ["excel", "word", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format")
    
    try:
        calculator = CostCalculator(current_lcp_data)
        
        # Create temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        evaluee_name = current_lcp_data.evaluee.name.replace(" ", "_")
        
        if format == "excel":
            filename = f"{evaluee_name}_LCP_{timestamp}.xlsx"
            filepath = f"temp_files/{filename}"
            ExcelExporter(calculator).export(filepath)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        elif format == "word":
            filename = f"{evaluee_name}_LCP_{timestamp}.docx"
            filepath = f"temp_files/{filename}"
            WordExporter(calculator).export(filepath)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
        elif format == "pdf":
            filename = f"{evaluee_name}_LCP_{timestamp}.pdf"
            filepath = f"temp_files/{filename}"
            PDFExporter(calculator).export(filepath)
            media_type = "application/pdf"
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type=media_type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload_config")
async def upload_config(file: UploadFile = File(...)):
    """Upload and load a configuration file."""
    global current_lcp_data
    
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")
    
    try:
        content = await file.read()
        config_data = json.loads(content)
        
        config_model = LCPConfigModel(**config_data)
        current_lcp_data = config_model.to_life_care_plan()
        
        return {
            "success": True,
            "message": f"Loaded configuration for {current_lcp_data.evaluee.name}",
            "evaluee": {
                "name": current_lcp_data.evaluee.name,
                "age": current_lcp_data.evaluee.current_age,
                "base_year": current_lcp_data.settings.base_year,
                "projection_years": current_lcp_data.settings.projection_years,
                "discount_rate": current_lcp_data.settings.discount_rate
            },
            "tables": list(current_lcp_data.tables.keys())
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/download_config")
async def download_config():
    """Download current configuration as JSON."""
    global current_lcp_data
    
    if not current_lcp_data:
        raise HTTPException(status_code=400, detail="No life care plan created yet")
    
    try:
        # Convert to configuration format
        config_data = {
            "evaluee_name": current_lcp_data.evaluee.name,
            "current_age": current_lcp_data.evaluee.current_age,
            "base_year": current_lcp_data.settings.base_year,
            "projection_years": current_lcp_data.settings.projection_years,
            "discount_rate": current_lcp_data.settings.discount_rate,
            "tables": {}
        }
        
        for table_name, table in current_lcp_data.tables.items():
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
        
        # Save to temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        evaluee_name = current_lcp_data.evaluee.name.replace(" ", "_")
        filename = f"{evaluee_name}_config_{timestamp}.json"
        filepath = f"temp_files/{filename}"
        
        with open(filepath, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/json"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/current_data")
async def get_current_data():
    """Get current life care plan data."""
    global current_lcp_data
    
    if not current_lcp_data:
        return {"success": False, "message": "No life care plan created yet"}
    
    tables_data = {}
    for table_name, table in current_lcp_data.tables.items():
        tables_data[table_name] = []
        for service in table.services:
            # Determine service type
            if service.is_one_time_cost:
                service_type = "one_time"
            elif service.occurrence_years:
                service_type = "discrete"
            else:
                service_type = "recurring"
            
            service_data = {
                "name": service.name,
                "unit_cost": service.unit_cost,
                "frequency_per_year": service.frequency_per_year,
                "inflation_rate": service.inflation_rate * 100,  # Convert to percentage
                "type": service_type,
                "use_cost_range": service.use_cost_range,
                "is_one_time_cost": service.is_one_time_cost
            }
            
            # Add cost range info if applicable
            if service.use_cost_range:
                service_data.update({
                    "cost_range_low": service.cost_range_low,
                    "cost_range_high": service.cost_range_high
                })
            
            # Add timing info based on type
            if service.is_one_time_cost:
                service_data["one_time_cost_year"] = service.one_time_cost_year
            elif service.occurrence_years:
                service_data["occurrence_years"] = service.occurrence_years
            else:
                service_data["start_year"] = service.start_year
                service_data["end_year"] = service.end_year
            
            tables_data[table_name].append(service_data)
    
    return {
        "success": True,
        "evaluee": {
            "name": current_lcp_data.evaluee.name,
            "age": current_lcp_data.evaluee.current_age,
            "base_year": current_lcp_data.settings.base_year,
            "projection_years": current_lcp_data.settings.projection_years,
            "discount_rate": current_lcp_data.settings.discount_rate,
            "discount_calculations": current_lcp_data.evaluee.discount_calculations
        },
        "tables": tables_data
    }


@app.get("/api/list_evaluees")
async def list_evaluees():
    """Get a list of all saved evaluees from database."""
    try:
        evaluees = db.list_evaluees()
        return {
            "success": True,
            "evaluees": evaluees
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error loading evaluees: {str(e)}"
        }


@app.post("/api/load_evaluee")
async def load_evaluee(evaluee_name: str = Form(...)):
    """Load an evaluee from the database."""
    global current_lcp_data
    
    try:
        lcp = db.load_life_care_plan(evaluee_name)
        
        if not lcp:
            return {
                "success": False,
                "message": f"Evaluee '{evaluee_name}' not found in database"
            }
        
        current_lcp_data = lcp
        
        # Build response data
        evaluee_data = {
            "name": lcp.evaluee.name,
            "age": lcp.evaluee.current_age,
            "base_year": lcp.settings.base_year,
            "projection_years": lcp.settings.projection_years,
            "discount_rate": lcp.settings.discount_rate,
            "discount_calculations": lcp.evaluee.discount_calculations
        }
        
        tables_data = {}
        for table_name, table in lcp.tables.items():
            services_data = []
            for service in table.services:
                service_data = {
                    "name": service.name,
                    "inflation_rate": service.inflation_rate,
                    "unit_cost": service.unit_cost,
                    "frequency_per_year": service.frequency_per_year,
                    "start_year": service.start_year,
                    "end_year": service.end_year,
                    "occurrence_years": service.occurrence_years,
                    "use_cost_range": service.use_cost_range,
                    "cost_range_low": service.cost_range_low,
                    "cost_range_high": service.cost_range_high,
                    "is_one_time_cost": service.is_one_time_cost,
                    "one_time_cost_year": service.one_time_cost_year
                }
                services_data.append(service_data)
            tables_data[table_name] = services_data
        
        return {
            "success": True,
            "message": f"Loaded evaluee: {evaluee_name}",
            "evaluee": evaluee_data,
            "tables": tables_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error loading evaluee: {str(e)}"
        }


@app.delete("/api/delete_evaluee_db/{evaluee_name}")
async def delete_evaluee_from_db(evaluee_name: str):
    """Delete an evaluee from the database."""
    try:
        success = db.delete_evaluee(evaluee_name)
        
        if success:
            return {
                "success": True,
                "message": f"Deleted evaluee: {evaluee_name}"
            }
        else:
            return {
                "success": False,
                "message": f"Evaluee '{evaluee_name}' not found"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error deleting evaluee: {str(e)}"
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)