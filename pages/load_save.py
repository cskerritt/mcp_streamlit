"""
Load/Save Configurations Page for Streamlit Life Care Plan Application
"""

import streamlit as st
import json
import tempfile
import os
from datetime import datetime
from src.models import LCPConfigModel

def show_load_save_page():
    """Display the load/save configurations page."""
    st.title("💾 Load/Save Configurations")
    st.markdown("Save your life care plan as a JSON configuration file or load an existing configuration.")
    
    # Tabs for different operations
    tab1, tab2, tab3 = st.tabs(["📁 Load Configuration", "💾 Save Configuration", "📋 Configuration Format"])
    
    with tab1:
        show_load_tab()
    
    with tab2:
        show_save_tab()
    
    with tab3:
        show_format_tab()

def show_load_tab():
    """Show the load configuration tab."""
    st.subheader("📁 Load Configuration")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a JSON configuration file",
        type=['json'],
        help="Upload a previously saved life care plan configuration file"
    )
    
    if uploaded_file is not None:
        try:
            # Read and parse the JSON file
            content = uploaded_file.read()
            config_data = json.loads(content)
            
            # Show preview of the configuration
            st.markdown("### Configuration Preview")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Evaluee Name:** {config_data.get('evaluee_name', 'N/A')}")
                st.write(f"**Current Age:** {config_data.get('current_age', 'N/A')}")
                st.write(f"**Base Year:** {config_data.get('base_year', 'N/A')}")
                st.write(f"**Projection Years:** {config_data.get('projection_years', 'N/A')}")
                st.write(f"**Discount Rate:** {config_data.get('discount_rate', 'N/A')}")
            
            with col2:
                tables = config_data.get('tables', {})
                st.write(f"**Service Tables:** {len(tables)}")
                
                total_services = sum(len(services) for services in tables.values())
                st.write(f"**Total Services:** {total_services}")
                
                # Show table breakdown
                for table_name, services in tables.items():
                    st.write(f"• {table_name}: {len(services)} services")
            
            # Load button
            if st.button("📥 Load This Configuration", use_container_width=True):
                load_configuration(config_data)
            
            # Show detailed preview
            with st.expander("View Detailed Configuration", expanded=False):
                st.json(config_data)
                
        except json.JSONDecodeError:
            st.error("Invalid JSON file. Please upload a valid configuration file.")
        except Exception as e:
            st.error(f"Error reading configuration file: {str(e)}")
    
    # Sample configurations
    st.markdown("---")
    st.subheader("📋 Sample Configurations")
    st.markdown("Load pre-built sample configurations to get started quickly.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👩‍⚕️ Basic Medical Plan", use_container_width=True):
            load_sample_basic_plan()
    
    with col2:
        if st.button("🏥 Comprehensive Plan", use_container_width=True):
            load_sample_comprehensive_plan()

def show_save_tab():
    """Show the save configuration tab."""
    st.subheader("💾 Save Configuration")
    
    if not st.session_state.lcp_data:
        st.warning("⚠️ No life care plan to save. Please create an evaluee and add services first.")
        return
    
    # Show current plan summary
    st.markdown("### Current Plan Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Evaluee:** {st.session_state.lcp_data.evaluee.name}")
        st.write(f"**Age:** {st.session_state.lcp_data.evaluee.current_age}")
        st.write(f"**Base Year:** {st.session_state.lcp_data.settings.base_year}")
        st.write(f"**Projection Years:** {st.session_state.lcp_data.settings.projection_years}")
        st.write(f"**Discount Rate:** {st.session_state.lcp_data.settings.discount_rate:.1%}")
    
    with col2:
        st.write(f"**Service Tables:** {len(st.session_state.lcp_data.tables)}")
        total_services = sum(len(table.services) for table in st.session_state.lcp_data.tables.values())
        st.write(f"**Total Services:** {total_services}")
        
        for table_name, table in st.session_state.lcp_data.tables.items():
            st.write(f"• {table_name}: {len(table.services)} services")
    
    # Save options
    st.markdown("### Save Options")
    
    # Multi-scenario export option
    has_multiple_scenarios = len(st.session_state.lcp_data.scenarios) > 1
    if has_multiple_scenarios:
        st.markdown("#### 🎭 Scenario Export Options")
        include_all_scenarios = st.checkbox(
            "Include All Scenarios",
            value=True,
            help="When checked, exports all scenarios to prevent data loss. When unchecked, only exports the current active scenario."
        )
        
        if include_all_scenarios:
            st.info(f"✅ Will export all {len(st.session_state.lcp_data.scenarios)} scenarios")
            scenarios_to_export = list(st.session_state.lcp_data.scenarios.keys())
            for scenario_name in scenarios_to_export:
                scenario = st.session_state.lcp_data.scenarios[scenario_name]
                baseline_text = " (Baseline)" if scenario.is_baseline else ""
                st.write(f"  • **{scenario_name}**{baseline_text}")
        else:
            current_scenario = st.session_state.lcp_data.get_current_scenario()
            st.warning(f"⚠️ Only exporting current scenario: **{current_scenario.name if current_scenario else 'Unknown'}**")
    else:
        include_all_scenarios = False
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    evaluee_name = st.session_state.lcp_data.evaluee.name.replace(" ", "_")
    if has_multiple_scenarios and include_all_scenarios:
        default_filename = f"{evaluee_name}_complete_config_{timestamp}.json"
    else:
        default_filename = f"{evaluee_name}_config_{timestamp}.json"
    
    filename = st.text_input(
        "Configuration Filename",
        value=default_filename,
        help="Name for the configuration file (will be saved as JSON)"
    )
    
    if st.button("💾 Save Configuration", use_container_width=True):
        save_configuration(filename, include_all_scenarios)
    
    # Preview configuration
    with st.expander("Preview Configuration JSON", expanded=False):
        preview_include_all = include_all_scenarios if has_multiple_scenarios else False
        config_data = create_config_data(preview_include_all)
        st.json(config_data)

def show_format_tab():
    """Show the configuration format documentation."""
    st.subheader("📋 Configuration Format")
    st.markdown("Learn about the JSON configuration file format used by the Life Care Plan Generator.")
    
    # Format explanation
    st.markdown("""
    ### Configuration Structure
    
    The configuration file is a JSON document with the following structure:
    
    ```json
    {
      "evaluee_name": "Person's Name",
      "current_age": 35.0,
      "base_year": 2025,
      "projection_years": 30.0,
      "discount_rate": 0.035,
      "tables": {
        "Table Name": [
          {
            "name": "Service Name",
            "inflation_rate": 0.027,
            "unit_cost": 500.00,
            "frequency_per_year": 1,
            "start_year": 2025,
            "end_year": 2025
          }
        ]
      }
    }
    ```
    """)
    
    # Field descriptions
    st.markdown("### Field Descriptions")
    
    field_descriptions = {
        "evaluee_name": "Full name of the person receiving care",
        "current_age": "Current age in years (can include decimals)",
        "base_year": "Starting year for cost projections",
        "projection_years": "Number of years to project into the future",
        "discount_rate": "Annual discount rate for present value calculations (as decimal)",
        "tables": "Dictionary of service tables, each containing a list of services"
    }
    
    for field, description in field_descriptions.items():
        st.write(f"• **{field}**: {description}")
    
    # Service types
    st.markdown("### Service Types")
    
    st.markdown("""
    **Recurring Services** (occur regularly within a date range):
    ```json
    {
      "name": "Annual Check-up",
      "inflation_rate": 0.027,
      "unit_cost": 300.00,
      "frequency_per_year": 1,
      "start_year": 2025,
      "end_year": 2054
    }
    ```
    
    **Discrete Occurrence Services** (occur only in specific years):
    ```json
    {
      "name": "Surgery",
      "inflation_rate": 0.05,
      "unit_cost": 75000.00,
      "frequency_per_year": 1,
      "occurrence_years": [2027, 2045]
    }
    ```
    
    **One-time Costs** (occur once in a specific year):
    ```json
    {
      "name": "Equipment Purchase",
      "inflation_rate": 0.03,
      "unit_cost": 5000.00,
      "frequency_per_year": 1,
      "is_one_time_cost": true,
      "one_time_cost_year": 2026
    }
    ```
    """)

def load_configuration(config_data):
    """Load a configuration into the session state."""
    try:
        # Validate and convert to LifeCarePlan
        config_model = LCPConfigModel(**config_data)
        lcp = config_model.to_life_care_plan()
        
        # Store in session state
        st.session_state.lcp_data = lcp
        
        st.success(f"✅ Configuration loaded successfully for {lcp.evaluee.name}!")
        st.info("You can now view calculations or make modifications to the plan.")
        
    except Exception as e:
        st.error(f"Error loading configuration: {str(e)}")

def save_configuration(filename, include_all_scenarios=False):
    """Save the current configuration to a file."""
    try:
        config_data = create_config_data(include_all_scenarios)
        
        # Create JSON string
        json_str = json.dumps(config_data, indent=2)
        
        # Provide download
        st.download_button(
            label="📥 Download Configuration File",
            data=json_str,
            file_name=filename,
            mime="application/json"
        )
        
        if include_all_scenarios:
            st.success("✅ Complete configuration with all scenarios ready for download!")
        else:
            st.success("✅ Configuration ready for download!")
        
    except Exception as e:
        st.error(f"Error saving configuration: {str(e)}")

def create_config_data(include_all_scenarios=False):
    """Create configuration data from current session state."""
    config_data = {
        "evaluee_name": st.session_state.lcp_data.evaluee.name,
        "current_age": st.session_state.lcp_data.evaluee.current_age,
        "base_year": st.session_state.lcp_data.settings.base_year,
        "projection_years": st.session_state.lcp_data.settings.projection_years,
        "discount_rate": st.session_state.lcp_data.settings.discount_rate,
        "discount_calculations": st.session_state.lcp_data.evaluee.discount_calculations
    }
    
    # Single scenario mode (backwards compatibility)
    if not include_all_scenarios or len(st.session_state.lcp_data.scenarios) == 1:
        config_data["tables"] = {}
        
        for table_name, table in st.session_state.lcp_data.tables.items():
            config_data["tables"][table_name] = []
            for service in table.services:
                service_data = create_service_data(service)
                config_data["tables"][table_name].append(service_data)
    
    # Multi-scenario mode 
    else:
        config_data["scenarios"] = {}
        config_data["active_scenario"] = st.session_state.lcp_data.active_scenario
        
        for scenario_name, scenario in st.session_state.lcp_data.scenarios.items():
            scenario_data = {
                "name": scenario.name,
                "description": scenario.description,
                "is_baseline": scenario.is_baseline,
                "tables": {}
            }
            
            for table_name, table in scenario.tables.items():
                scenario_data["tables"][table_name] = []
                for service in table.services:
                    service_data = create_service_data(service)
                    scenario_data["tables"][table_name].append(service_data)
            
            config_data["scenarios"][scenario_name] = scenario_data
    
    return config_data

def create_service_data(service):
    """Create service data dictionary from a service object."""
    service_data = {
        "name": service.name,
        "inflation_rate": service.inflation_rate,
        "unit_cost": service.unit_cost,
        "frequency_per_year": service.frequency_per_year
    }
    
    # Handle distributed instances
    if hasattr(service, 'is_distributed_instances') and service.is_distributed_instances:
        service_data.update({
            "is_distributed_instances": True,
            "total_instances": service.total_instances,
            "distribution_period_years": service.distribution_period_years,
            "start_year": service.start_year,
            "end_year": service.end_year
        })
    # Handle one-time costs
    elif service.is_one_time_cost:
        service_data.update({
            "is_one_time_cost": True,
            "one_time_cost_year": service.one_time_cost_year
        })
    # Handle discrete occurrences
    elif service.occurrence_years:
        service_data["occurrence_years"] = service.occurrence_years
    # Handle recurring services
    else:
        service_data.update({
            "start_year": service.start_year,
            "end_year": service.end_year
        })
    
    return service_data

def load_sample_basic_plan():
    """Load a basic sample plan."""
    sample_config = {
        "evaluee_name": "Sample Patient - Basic Plan",
        "current_age": 35.0,
        "base_year": 2025,
        "projection_years": 25.0,
        "discount_rate": 0.035,
        "tables": {
            "Medical Visits": [
                {
                    "name": "Annual Physical Exam",
                    "inflation_rate": 0.027,
                    "unit_cost": 250.00,
                    "frequency_per_year": 1,
                    "start_year": 2025,
                    "end_year": 2049
                }
            ],
            "Medications": [
                {
                    "name": "Daily Medication",
                    "inflation_rate": 0.05,
                    "unit_cost": 150.00,
                    "frequency_per_year": 12,
                    "start_year": 2025,
                    "end_year": 2049
                }
            ]
        }
    }
    
    load_configuration(sample_config)

def load_sample_comprehensive_plan():
    """Load a comprehensive sample plan."""
    sample_config = {
        "evaluee_name": "Sample Patient - Comprehensive Plan",
        "current_age": 40.0,
        "base_year": 2025,
        "projection_years": 30.0,
        "discount_rate": 0.035,
        "tables": {
            "Physician Evaluation": [
                {
                    "name": "Initial Neurological Evaluation",
                    "inflation_rate": 0.027,
                    "unit_cost": 500.00,
                    "frequency_per_year": 1,
                    "start_year": 2025,
                    "end_year": 2025
                },
                {
                    "name": "Annual Follow-up Visits",
                    "inflation_rate": 0.027,
                    "unit_cost": 300.00,
                    "frequency_per_year": 2,
                    "start_year": 2026,
                    "end_year": 2054
                }
            ],
            "Medications": [
                {
                    "name": "Anti-Spasticity Medication",
                    "inflation_rate": 0.05,
                    "unit_cost": 300.00,
                    "frequency_per_year": 12,
                    "start_year": 2025,
                    "end_year": 2054
                }
            ],
            "Surgeries": [
                {
                    "name": "Spinal Fusion Surgery",
                    "inflation_rate": 0.05,
                    "unit_cost": 75000.00,
                    "frequency_per_year": 1,
                    "occurrence_years": [2027, 2045]
                }
            ],
            "Equipment": [
                {
                    "name": "Wheelchair Replacement",
                    "inflation_rate": 0.03,
                    "unit_cost": 2500.00,
                    "frequency_per_year": 1,
                    "occurrence_years": [2025, 2030, 2035, 2040, 2045, 2050]
                }
            ]
        }
    }
    
    load_configuration(sample_config)
