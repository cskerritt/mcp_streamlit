"""
Scenario Management Page for Streamlit Life Care Plan Application
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from src.models import Scenario
from src.database import db

def show_scenario_management_page():
    """Display the scenario management page."""
    st.title("🎭 Scenario Management")
    
    # Check if we have a life care plan
    if not st.session_state.lcp_data:
        st.warning("⚠️ Please create an evaluee first before managing scenarios.")
        if st.button("👤 Go to Create Evaluee"):
            st.session_state.page = "👤 Create/Edit Evaluee"
            st.rerun()
        return
    
    st.markdown(f"Managing scenarios for: **{st.session_state.lcp_data.evaluee.name}**")
    
    # Ensure baseline scenario exists
    if not st.session_state.lcp_data.scenarios:
        st.session_state.lcp_data.__post_init__()
    
    # Current scenario selection
    st.subheader("Current Scenario")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        scenario_names = list(st.session_state.lcp_data.scenarios.keys())
        current_index = 0
        if st.session_state.lcp_data.active_scenario in scenario_names:
            current_index = scenario_names.index(st.session_state.lcp_data.active_scenario)
        
        selected_scenario = st.selectbox(
            "Active Scenario",
            scenario_names,
            index=current_index,
            help="Select the scenario to view and edit"
        )
        
        if selected_scenario != st.session_state.lcp_data.active_scenario:
            st.session_state.lcp_data.set_active_scenario(selected_scenario)
            st.success(f"Switched to scenario: {selected_scenario}")
            st.rerun()
    
    with col2:
        if st.button("🔄 Refresh", help="Refresh scenario list"):
            st.rerun()
    
    # Display current scenario info
    current_scenario = st.session_state.lcp_data.get_current_scenario()
    if current_scenario:
        st.info(f"**Current:** {current_scenario.name}")
        if current_scenario.description:
            st.caption(current_scenario.description)
        
        # Show scenario stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Tables", len(current_scenario.tables))
        with col2:
            total_services = sum(len(table.services) for table in current_scenario.tables.values())
            st.metric("Services", total_services)
        with col3:
            st.metric("Base Year", current_scenario.settings.base_year if current_scenario.settings else "N/A")
        with col4:
            discount_rate = current_scenario.settings.discount_rate if current_scenario.settings else 0
            st.metric("Discount Rate", f"{discount_rate:.1%}")
    
    # Tabs for different operations
    tab1, tab2, tab3, tab4 = st.tabs(["📋 View All Scenarios", "➕ Create Scenario", "📊 Scenario Comparison", "⚙️ Scenario Settings"])
    
    with tab1:
        show_scenarios_overview()
    
    with tab2:
        show_create_scenario_form()
    
    with tab3:
        show_scenario_comparison()
    
    with tab4:
        show_scenario_settings()

def show_scenarios_overview():
    """Show overview of all scenarios."""
    st.subheader("All Scenarios")
    
    if not st.session_state.lcp_data.scenarios:
        st.info("No scenarios created yet.")
        return
    
    # Create scenario summary table
    scenario_data = []
    for name, scenario in st.session_state.lcp_data.scenarios.items():
        tables_count = len(scenario.tables)
        services_count = sum(len(table.services) for table in scenario.tables.values())
        base_year = scenario.settings.base_year if scenario.settings else "N/A"
        discount_rate = f"{scenario.settings.discount_rate:.1%}" if scenario.settings else "N/A"
        is_active = "✅" if name == st.session_state.lcp_data.active_scenario else ""
        is_baseline = "🏠" if scenario.is_baseline else ""
        
        scenario_data.append({
            "Scenario": name,
            "Description": scenario.description[:50] + "..." if len(scenario.description) > 50 else scenario.description,
            "Tables": tables_count,
            "Services": services_count,
            "Base Year": base_year,
            "Discount Rate": discount_rate,
            "Active": is_active,
            "Baseline": is_baseline,
            "Created": scenario.created_at.strftime("%Y-%m-%d %H:%M") if scenario.created_at else "N/A"
        })
    
    df = pd.DataFrame(scenario_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Scenario actions
    st.subheader("Scenario Actions")
    
    scenario_names = [name for name in st.session_state.lcp_data.scenarios.keys()]
    selected_for_action = st.selectbox("Select scenario for actions", scenario_names, key="action_scenario")
    
    if selected_for_action:
        scenario = st.session_state.lcp_data.scenarios[selected_for_action]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📋 Copy Scenario"):
                st.session_state.show_copy_form = selected_for_action
                st.rerun()
        
        with col2:
            if not scenario.is_baseline and st.button("✏️ Rename"):
                st.session_state.show_rename_form = selected_for_action
                st.rerun()
        
        with col3:
            if st.button("🎯 Set as Active"):
                st.session_state.lcp_data.set_active_scenario(selected_for_action)
                st.success(f"Set {selected_for_action} as active scenario")
                st.rerun()
        
        with col4:
            if not scenario.is_baseline and st.button("🗑️ Delete", type="secondary"):
                if st.session_state.get(f"confirm_delete_{selected_for_action}", False):
                    st.session_state.lcp_data.remove_scenario(selected_for_action)
                    st.success(f"Deleted scenario: {selected_for_action}")
                    if f"confirm_delete_{selected_for_action}" in st.session_state:
                        del st.session_state[f"confirm_delete_{selected_for_action}"]
                    st.rerun()
                else:
                    st.session_state[f"confirm_delete_{selected_for_action}"] = True
                    st.warning("Click delete again to confirm")
    
    # Show copy form
    if st.session_state.get("show_copy_form"):
        source_name = st.session_state.show_copy_form
        with st.expander(f"📋 Copy Scenario: {source_name}", expanded=True):
            with st.form("copy_scenario_form"):
                new_name = st.text_input("New Scenario Name", value=f"{source_name} Copy")
                new_description = st.text_area("Description", value=f"Copy of {source_name}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Create Copy"):
                        if st.session_state.lcp_data.copy_scenario(source_name, new_name, new_description):
                            st.success(f"Created copy: {new_name}")
                            del st.session_state.show_copy_form
                            st.rerun()
                        else:
                            st.error("Failed to copy scenario. Name may already exist.")
                
                with col2:
                    if st.form_submit_button("❌ Cancel"):
                        del st.session_state.show_copy_form
                        st.rerun()
    
    # Show rename form
    if st.session_state.get("show_rename_form"):
        old_name = st.session_state.show_rename_form
        with st.expander(f"✏️ Rename Scenario: {old_name}", expanded=True):
            with st.form("rename_scenario_form"):
                new_name = st.text_input("New Scenario Name", value=old_name)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Rename"):
                        if st.session_state.lcp_data.rename_scenario(old_name, new_name):
                            st.success(f"Renamed to: {new_name}")
                            del st.session_state.show_rename_form
                            st.rerun()
                        else:
                            st.error("Failed to rename scenario. Name may already exist.")
                
                with col2:
                    if st.form_submit_button("❌ Cancel"):
                        del st.session_state.show_rename_form
                        st.rerun()

def show_create_scenario_form():
    """Show form to create a new scenario."""
    st.subheader("Create New Scenario")
    
    # Option to create from scratch or copy from existing
    creation_mode = st.radio(
        "Creation Mode",
        ["Create from Current Scenario", "Create Empty Scenario", "Copy from Another Scenario"],
        help="Choose how to create the new scenario"
    )
    
    with st.form("create_scenario_form"):
        scenario_name = st.text_input(
            "Scenario Name *",
            placeholder="e.g., Conservative, Optimistic, High-Care"
        )
        
        scenario_description = st.text_area(
            "Description",
            placeholder="Brief description of this scenario's assumptions",
            help="Describe what makes this scenario different"
        )
        
        if creation_mode == "Copy from Another Scenario":
            source_scenarios = list(st.session_state.lcp_data.scenarios.keys())
            source_scenario = st.selectbox("Copy from Scenario", source_scenarios)
        else:
            source_scenario = None
        
        # Settings for new scenario
        st.subheader("Scenario Settings")
        
        if creation_mode == "Create Empty Scenario":
            col1, col2 = st.columns(2)
            with col1:
                base_year = st.number_input(
                    "Base Year",
                    value=st.session_state.lcp_data.settings.base_year,
                    step=1
                )
                projection_years = st.number_input(
                    "Projection Years",
                    value=float(st.session_state.lcp_data.settings.projection_years),
                    min_value=1.0,
                    step=1.0
                )
            with col2:
                discount_rate = st.number_input(
                    "Discount Rate (%)",
                    value=st.session_state.lcp_data.settings.discount_rate * 100,
                    min_value=0.0,
                    max_value=20.0,
                    step=0.1
                )
        else:
            st.info("Settings will be copied from the source scenario and can be modified later.")
        
        submitted = st.form_submit_button("➕ Create Scenario", use_container_width=True)
        
        if submitted:
            if not scenario_name.strip():
                st.error("Please enter a scenario name.")
                return
            
            if scenario_name in st.session_state.lcp_data.scenarios:
                st.error(f"Scenario '{scenario_name}' already exists.")
                return
            
            try:
                if creation_mode == "Copy from Another Scenario" and source_scenario:
                    # Copy from existing scenario
                    success = st.session_state.lcp_data.copy_scenario(
                        source_scenario, 
                        scenario_name, 
                        scenario_description
                    )
                    if success:
                        st.success(f"✅ Created scenario '{scenario_name}' from '{source_scenario}'")
                    else:
                        st.error("Failed to copy scenario")
                        return
                
                elif creation_mode == "Create from Current Scenario":
                    # Copy from current scenario
                    current_name = st.session_state.lcp_data.active_scenario
                    success = st.session_state.lcp_data.copy_scenario(
                        current_name,
                        scenario_name,
                        scenario_description
                    )
                    if success:
                        st.success(f"✅ Created scenario '{scenario_name}' from '{current_name}'")
                    else:
                        st.error("Failed to copy current scenario")
                        return
                
                else:  # Create empty scenario
                    from src.models import ProjectionSettings
                    new_settings = ProjectionSettings(
                        base_year=base_year,
                        projection_years=projection_years,
                        discount_rate=discount_rate / 100
                    )
                    
                    new_scenario = Scenario(
                        name=scenario_name,
                        description=scenario_description,
                        settings=new_settings,
                        is_baseline=False
                    )
                    
                    st.session_state.lcp_data.add_scenario(new_scenario)
                    st.success(f"✅ Created empty scenario '{scenario_name}'")
                
                # Auto-save to database if enabled
                if st.session_state.get('auto_save', True):
                    try:
                        db.save_life_care_plan(st.session_state.lcp_data)
                        st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
                    except Exception as e:
                        st.warning(f"Auto-save failed: {str(e)}")
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Error creating scenario: {str(e)}")

def show_scenario_comparison():
    """Show scenario comparison interface."""
    st.subheader("📊 Scenario Comparison")
    
    if len(st.session_state.lcp_data.scenarios) < 2:
        st.info("Create at least 2 scenarios to enable comparison.")
        return
    
    st.write("Compare key metrics across different scenarios:")
    
    # Select scenarios to compare
    scenario_names = list(st.session_state.lcp_data.scenarios.keys())
    selected_scenarios = st.multiselect(
        "Select scenarios to compare",
        scenario_names,
        default=scenario_names[:3] if len(scenario_names) >= 3 else scenario_names,
        help="Choose 2 or more scenarios to compare"
    )
    
    if len(selected_scenarios) < 2:
        st.warning("Please select at least 2 scenarios to compare.")
        return
    
    # Create comparison table
    comparison_data = []
    for scenario_name in selected_scenarios:
        scenario = st.session_state.lcp_data.scenarios[scenario_name]
        tables_count = len(scenario.tables)
        services_count = sum(len(table.services) for table in scenario.tables.values())
        
        # Calculate total estimated cost (simplified)
        total_cost = 0
        if scenario.settings:
            for table in scenario.tables.values():
                for service in table.services:
                    # Simple estimation: unit_cost * frequency * projection_years
                    annual_cost = service.unit_cost * service.frequency_per_year
                    total_cost += annual_cost * scenario.settings.projection_years
        
        comparison_data.append({
            "Scenario": scenario_name,
            "Description": scenario.description[:30] + "..." if len(scenario.description) > 30 else scenario.description,
            "Tables": tables_count,
            "Services": services_count,
            "Base Year": scenario.settings.base_year if scenario.settings else "N/A",
            "Projection Years": f"{scenario.settings.projection_years:.1f}" if scenario.settings else "N/A",
            "Discount Rate": f"{scenario.settings.discount_rate:.1%}" if scenario.settings else "N/A",
            "Est. Total Cost": f"${total_cost:,.0f}" if total_cost > 0 else "N/A"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    # Quick switch between scenarios
    st.subheader("Quick Scenario Switch")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        quick_switch = st.selectbox(
            "Switch to scenario for detailed view",
            selected_scenarios,
            key="quick_switch"
        )
    
    with col2:
        if st.button("🎯 Switch & Go to Tables"):
            st.session_state.lcp_data.set_active_scenario(quick_switch)
            st.session_state.page = "📋 Manage Service Tables"
            st.rerun()

def show_scenario_settings():
    """Show settings for the current scenario."""
    st.subheader("⚙️ Current Scenario Settings")
    
    current_scenario = st.session_state.lcp_data.get_current_scenario()
    if not current_scenario:
        st.error("No active scenario found.")
        return
    
    st.markdown(f"**Editing settings for:** {current_scenario.name}")
    
    if not current_scenario.settings:
        st.warning("This scenario has no settings. Creating default settings.")
        from src.models import ProjectionSettings
        current_scenario.settings = ProjectionSettings(
            base_year=st.session_state.lcp_data.settings.base_year,
            projection_years=st.session_state.lcp_data.settings.projection_years,
            discount_rate=st.session_state.lcp_data.settings.discount_rate
        )
    
    with st.form("scenario_settings_form"):
        st.subheader("Basic Information")
        
        # Scenario name and description (can't edit baseline name)
        if current_scenario.is_baseline:
            st.text_input("Scenario Name", value=current_scenario.name, disabled=True, help="Cannot rename baseline scenario")
        else:
            new_name = st.text_input("Scenario Name", value=current_scenario.name)
        
        new_description = st.text_area("Description", value=current_scenario.description)
        
        st.subheader("Projection Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            new_base_year = st.number_input(
                "Base Year",
                value=current_scenario.settings.base_year,
                step=1,
                help="The starting year for projections"
            )
            
            new_projection_years = st.number_input(
                "Projection Years",
                value=float(current_scenario.settings.projection_years),
                min_value=1.0,
                step=1.0,
                help="Number of years to project costs"
            )
        
        with col2:
            new_discount_rate = st.number_input(
                "Discount Rate (%)",
                value=current_scenario.settings.discount_rate * 100,
                min_value=0.0,
                max_value=20.0,
                step=0.1,
                help="Annual discount rate for present value calculations"
            )
        
        # Show impact of changes
        if (new_base_year != current_scenario.settings.base_year or 
            new_projection_years != current_scenario.settings.projection_years or
            new_discount_rate/100 != current_scenario.settings.discount_rate):
            st.info("⚠️ Changing these settings will affect all cost calculations for this scenario.")
        
        submitted = st.form_submit_button("💾 Save Settings", use_container_width=True)
        
        if submitted:
            try:
                # Update scenario info
                if not current_scenario.is_baseline and 'new_name' in locals():
                    if new_name != current_scenario.name:
                        old_name = current_scenario.name
                        if st.session_state.lcp_data.rename_scenario(old_name, new_name):
                            st.success(f"Renamed scenario to: {new_name}")
                        else:
                            st.error("Failed to rename scenario. Name may already exist.")
                            return
                
                current_scenario.description = new_description
                
                # Update settings
                current_scenario.settings.base_year = new_base_year
                current_scenario.settings.projection_years = new_projection_years
                current_scenario.settings.discount_rate = new_discount_rate / 100
                
                # Auto-save to database if enabled
                if st.session_state.get('auto_save', True):
                    try:
                        db.save_life_care_plan(st.session_state.lcp_data)
                        st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
                    except Exception as e:
                        st.warning(f"Auto-save failed: {str(e)}")
                
                st.success("✅ Settings updated successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error updating settings: {str(e)}")