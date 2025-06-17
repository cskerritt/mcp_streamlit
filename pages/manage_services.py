"""
Manage Service Tables Page for Streamlit Life Care Plan Application
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from src.models import ServiceTable, Service
from src.database import db

def show_manage_services_page():
    """Display the manage service tables page."""
    st.title("📋 Manage Service Tables")
    
    # Check if we have a life care plan
    if not st.session_state.lcp_data:
        st.warning("⚠️ Please create an evaluee first before managing services.")
        if st.button("👤 Go to Create Evaluee"):
            st.session_state.page = "👤 Create/Edit Evaluee"
            st.rerun()
        return
    
    st.markdown(f"Managing services for: **{st.session_state.lcp_data.evaluee.name}**")
    
    # Tabs for different operations
    tab1, tab2, tab3 = st.tabs(["📋 View Tables", "➕ Add Table", "🔧 Add/Edit Services"])
    
    with tab1:
        show_tables_overview()
    
    with tab2:
        show_add_table_form()
    
    with tab3:
        show_service_management()

def show_tables_overview():
    """Show overview of all service tables."""
    st.subheader("Service Tables Overview")
    
    if not st.session_state.lcp_data.tables:
        st.info("No service tables created yet. Use the 'Add Table' tab to create your first table.")
        return
    
    # Display tables in a nice format
    for table_name, table in st.session_state.lcp_data.tables.items():
        with st.expander(f"📋 {table_name} ({len(table.services)} services)", expanded=True):
            if table.services:
                # Create DataFrame for display
                services_data = []
                for i, service in enumerate(table.services):
                    service_type = "One-time" if service.is_one_time_cost else ("Discrete" if service.occurrence_years else "Recurring")

                    if service.is_one_time_cost:
                        timing = f"Year {service.one_time_cost_year}"
                    elif service.occurrence_years:
                        timing = f"Years: {', '.join(map(str, service.occurrence_years))}"
                    else:
                        timing = f"{service.start_year} - {service.end_year}"

                    # Handle cost display
                    if service.use_cost_range:
                        cost_display = f"${service.unit_cost:,.2f} (Range: ${service.cost_range_low:,.2f} - ${service.cost_range_high:,.2f})"
                    else:
                        cost_display = f"${service.unit_cost:,.2f}"

                    services_data.append({
                        "Service": service.name,
                        "Type": service_type,
                        "Cost": cost_display,
                        "Frequency/Year": f"{service.frequency_per_year:.1f}",
                        "Inflation Rate": f"{service.inflation_rate:.1%}",
                        "Timing": timing
                    })
                
                df = pd.DataFrame(services_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Delete table button
                if st.button(f"🗑️ Delete {table_name} Table", key=f"delete_table_{table_name}"):
                    if st.session_state.get(f"confirm_delete_{table_name}", False):
                        del st.session_state.lcp_data.tables[table_name]
                        st.success(f"Deleted table: {table_name}")
                        st.rerun()
                    else:
                        st.session_state[f"confirm_delete_{table_name}"] = True
                        st.warning("Click again to confirm deletion")
            else:
                st.info("No services in this table yet.")

def show_add_table_form():
    """Show form to add a new service table."""
    st.subheader("Add New Service Table")
    
    with st.form("add_table_form"):
        table_name = st.text_input(
            "Table Name *",
            placeholder="e.g., Physician Evaluation, Medications, Equipment",
            help="Name for the service category (e.g., 'Medications', 'Physical Therapy')"
        )
        
        default_inflation_rate = st.number_input(
            "Default Inflation Rate (%)",
            min_value=0.0,
            max_value=20.0,
            value=3.5,
            step=0.1,
            help="Default inflation rate for services in this table (can be overridden per service)"
        )
        
        submitted = st.form_submit_button("➕ Create Table", use_container_width=True)
        
        if submitted:
            if not table_name.strip():
                st.error("Please enter a table name.")
                return
            
            if table_name in st.session_state.lcp_data.tables:
                st.error(f"Table '{table_name}' already exists.")
                return
            
            try:
                table = ServiceTable(name=table_name.strip())
                table.default_inflation_rate = default_inflation_rate / 100  # Store as decimal
                st.session_state.lcp_data.add_table(table)

                # Auto-save to database if enabled
                if st.session_state.get('auto_save', True):
                    try:
                        db.save_life_care_plan(st.session_state.lcp_data)
                        st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
                    except Exception as e:
                        st.warning(f"Auto-save failed: {str(e)}")

                st.success(f"✅ Created table: {table_name}")
                st.rerun()

            except Exception as e:
                st.error(f"Error creating table: {str(e)}")

def show_service_management():
    """Show service management interface."""
    st.subheader("Add/Edit Services")
    
    if not st.session_state.lcp_data.tables:
        st.warning("Please create at least one service table first.")
        return
    
    # Select table
    table_names = list(st.session_state.lcp_data.tables.keys())
    selected_table = st.selectbox("Select Table", table_names)
    
    if not selected_table:
        return
    
    table = st.session_state.lcp_data.tables[selected_table]
    
    # Show existing services with edit/delete options
    if table.services:
        st.markdown("### Existing Services")
        for i, service in enumerate(table.services):
            with st.expander(f"🔧 {service.name}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Display cost information
                    if service.use_cost_range:
                        st.write(f"**Cost:** ${service.unit_cost:,.2f} (avg)")
                        st.write(f"**Range:** ${service.cost_range_low:,.2f} - ${service.cost_range_high:,.2f}")
                    else:
                        st.write(f"**Cost:** ${service.unit_cost:,.2f}")

                    st.write(f"**Frequency:** {service.frequency_per_year:.1f}/year")
                    st.write(f"**Inflation:** {service.inflation_rate:.1%}")

                    if service.is_one_time_cost:
                        st.write(f"**Type:** One-time cost in {service.one_time_cost_year}")
                    elif service.occurrence_years:
                        years_display = ', '.join(map(str, service.occurrence_years))
                        if len(years_display) > 50:  # Truncate if too long
                            years_display = years_display[:47] + "..."
                        st.write(f"**Type:** Specific years: {years_display}")
                    else:
                        st.write(f"**Type:** Recurring from {service.start_year} to {service.end_year}")
                
                with col2:
                    if st.button("✏️ Edit", key=f"edit_{i}"):
                        st.session_state[f"editing_service_{i}"] = True
                        st.rerun()
                    
                    if st.button("🗑️ Delete", key=f"delete_{i}"):
                        if st.session_state.get(f"confirm_delete_service_{i}", False):
                            table.services.pop(i)
                            st.success(f"Deleted service: {service.name}")
                            st.rerun()
                        else:
                            st.session_state[f"confirm_delete_service_{i}"] = True
                            st.warning("Click again to confirm")
                
                # Show edit form if editing
                if st.session_state.get(f"editing_service_{i}", False):
                    show_edit_service_form(table, i, service)
    
    # Add new service form
    st.markdown("### Add New Service")
    show_add_service_form(table)

def show_add_service_form(table: ServiceTable):
    """Show form to add a new service."""
    with st.form(f"add_service_form_{table.name}"):
        service_name = st.text_input(
            "Service Name *",
            placeholder="e.g., Annual Neurological Exam, Wheelchair Replacement"
        )

        # Cost input options
        st.subheader("Cost Information")
        use_cost_range = st.checkbox(
            "Use Cost Range (High/Low)",
            help="Enter a high and low cost estimate - the average will be used as the unit cost"
        )

        col1, col2 = st.columns(2)

        if use_cost_range:
            with col1:
                cost_range_low = st.number_input(
                    "Low End Cost ($) *",
                    min_value=0.0,
                    value=50.0,
                    step=1.0,
                    help="Lower estimate of the cost"
                )

            with col2:
                cost_range_high = st.number_input(
                    "High End Cost ($) *",
                    min_value=0.0,
                    value=150.0,
                    step=1.0,
                    help="Higher estimate of the cost"
                )

            # Show calculated average
            if cost_range_high > 0 and cost_range_low > 0:
                average_cost = (cost_range_low + cost_range_high) / 2
                st.info(f"💡 Average Cost: ${average_cost:,.2f}")

            unit_cost = None  # Will be calculated from range
        else:
            with col1:
                unit_cost = st.number_input(
                    "Unit Cost ($) *",
                    min_value=0.0,
                    value=100.0,
                    step=1.0,
                    help="Cost per unit of service"
                )
            cost_range_low = None
            cost_range_high = None

        col3, col4 = st.columns(2)

        with col3:
            frequency_per_year = st.number_input(
                "Frequency per Year *",
                min_value=0.1,
                value=1.0,
                step=0.1,
                format="%.2f",
                help="How many times per year this service occurs. Examples:\n• 1.0 = Once per year\n• 0.5 = Every 2 years\n• 1.5 = Every 1.5 years\n• 0.33 = Every 3 years\n• 0.25 = Every 4 years"
            )

            # Show frequency interpretation
            if frequency_per_year < 1.0:
                years_between = 1.0 / frequency_per_year
                st.caption(f"💡 This means every {years_between:.1f} years")
            elif frequency_per_year > 1.0:
                st.caption(f"💡 This means {frequency_per_year:.1f} times per year")
            else:
                st.caption("💡 This means once per year")

        with col4:
            # Handle default inflation rate - check if it's already in percentage format
            # Handle inflation rate conversion safely
            default_inflation = getattr(table, 'default_inflation_rate', 0.035)
            try:
                default_inflation = float(default_inflation)
                if default_inflation <= 1.0:  # Likely stored as decimal (0.035 = 3.5%)
                    default_inflation = default_inflation * 100
                # Ensure it's within reasonable bounds
                default_inflation = max(0.0, min(default_inflation, 20.0))
            except (ValueError, TypeError):
                default_inflation = 3.5  # Fallback to 3.5%

            inflation_rate = st.number_input(
                "Inflation Rate (%) *",
                min_value=0.0,
                max_value=20.0,
                value=min(default_inflation, 20.0),  # Cap at 20% to avoid validation error
                step=0.1,
                help="Annual inflation rate for this service"
            )

        # Service timing
        st.subheader("Service Timing")
        service_type = st.radio(
            "Service Type",
            ["Recurring", "Discrete Occurrences", "One-time Cost", "Specific Years"],
            help="How often this service occurs"
        )
        
        if service_type == "Recurring":
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.number_input(
                    "Start Year",
                    min_value=st.session_state.lcp_data.settings.base_year,
                    value=st.session_state.lcp_data.settings.base_year,
                    step=1
                )
            with col2:
                end_year = st.number_input(
                    "End Year",
                    min_value=start_year,
                    value=st.session_state.lcp_data.settings.base_year + int(st.session_state.lcp_data.settings.projection_years) - 1,
                    step=1
                )

        elif service_type == "Discrete Occurrences":
            occurrence_years_str = st.text_input(
                "Occurrence Years",
                placeholder="e.g., 2025, 2030, 2035",
                help="Comma-separated list of years when this service occurs"
            )

        elif service_type == "Specific Years":
            st.markdown("**Select Specific Years:**")
            st.caption("Choose individual years from the projection period when this service will occur")

            # Create year range for selection
            base_year = st.session_state.lcp_data.settings.base_year
            end_year = base_year + int(st.session_state.lcp_data.settings.projection_years)
            available_years = list(range(base_year, end_year))

            # Multi-select for years
            selected_years = st.multiselect(
                "Select Years",
                options=available_years,
                default=[base_year],
                help="Select all years when this service will occur"
            )

            if selected_years:
                st.info(f"Selected {len(selected_years)} years: {', '.join(map(str, sorted(selected_years)))}")

        else:  # One-time cost
            one_time_year = st.number_input(
                "Year of Occurrence",
                min_value=st.session_state.lcp_data.settings.base_year,
                value=st.session_state.lcp_data.settings.base_year,
                step=1
            )
        
        submitted = st.form_submit_button("➕ Add Service", use_container_width=True)
        
        if submitted:
            if not service_name.strip():
                st.error("Please enter a service name.")
                return
            
            try:
                # Base service parameters
                service_params = {
                    "name": service_name.strip(),
                    "frequency_per_year": frequency_per_year,
                    "inflation_rate": inflation_rate / 100,  # Convert to decimal
                    "use_cost_range": use_cost_range
                }

                # Handle cost inputs
                if use_cost_range:
                    if cost_range_low is None or cost_range_high is None:
                        st.error("Cost range requires both low and high values.")
                        return
                    if cost_range_low >= cost_range_high:
                        st.error("High end cost must be greater than low end cost.")
                        return

                    # Calculate average cost
                    average_cost = (cost_range_low + cost_range_high) / 2
                    service_params.update({
                        "cost_range_low": cost_range_low,
                        "cost_range_high": cost_range_high,
                        "unit_cost": average_cost
                    })
                else:
                    if unit_cost is None or unit_cost <= 0:
                        st.error("Unit cost is required and must be greater than zero.")
                        return
                    service_params["unit_cost"] = unit_cost

                # Handle service timing
                if service_type == "Recurring":
                    service_params.update({
                        "start_year": start_year,
                        "end_year": end_year
                    })
                elif service_type == "Discrete Occurrences":
                    if not occurrence_years_str.strip():
                        st.error("Please enter occurrence years.")
                        return

                    try:
                        occurrence_years = [int(year.strip()) for year in occurrence_years_str.split(",")]
                        if not occurrence_years:
                            st.error("No valid years found in occurrence years.")
                            return
                        service_params["occurrence_years"] = occurrence_years
                    except ValueError:
                        st.error("Invalid occurrence years format. Use comma-separated years (e.g., 2025, 2030, 2035)")
                        return
                elif service_type == "Specific Years":
                    if not selected_years:
                        st.error("Please select at least one year.")
                        return
                    service_params["occurrence_years"] = sorted(selected_years)
                else:  # One-time cost
                    service_params.update({
                        "is_one_time_cost": True,
                        "one_time_cost_year": one_time_year
                    })
                
                service = Service(**service_params)
                table.add_service(service)

                # Auto-save to database if enabled
                if st.session_state.get('auto_save', True):
                    try:
                        db.save_life_care_plan(st.session_state.lcp_data)
                        st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
                    except Exception as e:
                        st.warning(f"Auto-save failed: {str(e)}")

                st.success(f"✅ Added service: {service_name}")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error adding service: {str(e)}")

def show_edit_service_form(table: ServiceTable, service_index: int, service: Service):
    """Show form to edit an existing service."""
    st.markdown("#### Edit Service")

    with st.form(f"edit_service_form_{service_index}"):
        # Pre-fill with existing values
        service_name = st.text_input("Service Name *", value=service.name)

        # Cost information
        st.subheader("Cost Information")
        use_cost_range = st.checkbox(
            "Use Cost Range (High/Low)",
            value=service.use_cost_range,
            help="Enter a high and low cost estimate - the average will be used as the unit cost"
        )

        col1, col2 = st.columns(2)

        if use_cost_range:
            with col1:
                cost_range_low = st.number_input(
                    "Low End Cost ($) *",
                    value=float(service.cost_range_low if service.cost_range_low else float(service.unit_cost) * 0.8),
                    min_value=0.0,
                    step=1.0
                )

            with col2:
                cost_range_high = st.number_input(
                    "High End Cost ($) *",
                    value=float(service.cost_range_high if service.cost_range_high else float(service.unit_cost) * 1.2),
                    min_value=0.0,
                    step=1.0
                )

            # Show calculated average
            if cost_range_high > 0 and cost_range_low > 0:
                average_cost = (cost_range_low + cost_range_high) / 2
                st.info(f"💡 Average Cost: ${average_cost:,.2f}")
        else:
            with col1:
                unit_cost = st.number_input("Unit Cost ($) *", value=service.unit_cost, min_value=0.0, step=1.0)

        col3, col4 = st.columns(2)

        with col3:
            frequency_per_year = st.number_input(
                "Frequency per Year *",
                value=float(service.frequency_per_year),
                min_value=0.1,
                step=0.1,
                format="%.2f",
                help="How many times per year this service occurs. Examples:\n• 1.0 = Once per year\n• 0.5 = Every 2 years\n• 1.5 = Every 1.5 years\n• 0.33 = Every 3 years\n• 0.25 = Every 4 years"
            )

            # Show frequency interpretation
            if frequency_per_year < 1.0:
                years_between = 1.0 / frequency_per_year
                st.caption(f"💡 This means every {years_between:.1f} years")
            elif frequency_per_year > 1.0:
                st.caption(f"💡 This means {frequency_per_year:.1f} times per year")
            else:
                st.caption("💡 This means once per year")

        with col4:
            # Handle inflation rate - check if it's already in percentage format
            display_inflation = service.inflation_rate
            if display_inflation <= 1.0:  # Likely stored as decimal (0.035 = 3.5%)
                display_inflation = display_inflation * 100
            # If it's > 1.0, assume it's already in percentage format

            inflation_rate = st.number_input(
                "Inflation Rate (%) *",
                value=float(min(display_inflation, 20.0)),  # Cap at 20% to avoid validation error
                min_value=0.0,
                max_value=20.0,
                step=0.1
            )
        
        # Service timing
        st.subheader("Service Timing")

        if service.is_one_time_cost:
            st.write("**Current Type:** One-time Cost")
            one_time_year = st.number_input("Year of Occurrence", value=int(service.one_time_cost_year) if service.one_time_cost_year else 2025, step=1)
        elif service.occurrence_years:
            st.write("**Current Type:** Discrete Occurrences / Specific Years")

            # Option to edit as text or use multiselect
            edit_mode = st.radio(
                "Edit Mode",
                ["Text Input", "Year Selector"],
                horizontal=True,
                help="Choose how to edit the occurrence years"
            )

            if edit_mode == "Text Input":
                occurrence_years_str = st.text_input(
                    "Occurrence Years",
                    value=", ".join(map(str, service.occurrence_years)),
                    help="Comma-separated list of years"
                )
            else:
                # Multi-select for years
                base_year = st.session_state.lcp_data.settings.base_year
                end_year = base_year + int(st.session_state.lcp_data.settings.projection_years)
                available_years = list(range(base_year, end_year))

                selected_years = st.multiselect(
                    "Select Years",
                    options=available_years,
                    default=service.occurrence_years,
                    help="Select all years when this service will occur"
                )
        else:
            st.write("**Current Type:** Recurring")
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.number_input("Start Year", value=int(service.start_year) if service.start_year else 2025, step=1)
            with col2:
                end_year = st.number_input("End Year", value=int(service.end_year) if service.end_year else 2030, step=1)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                try:
                    # Update basic service info
                    service.name = service_name.strip()
                    service.frequency_per_year = frequency_per_year
                    service.inflation_rate = inflation_rate / 100
                    service.use_cost_range = use_cost_range

                    # Update cost information
                    if use_cost_range:
                        if cost_range_low >= cost_range_high:
                            st.error("High end cost must be greater than low end cost.")
                            return
                        service.cost_range_low = cost_range_low
                        service.cost_range_high = cost_range_high
                        service.unit_cost = (cost_range_low + cost_range_high) / 2
                    else:
                        service.unit_cost = unit_cost
                        service.cost_range_low = None
                        service.cost_range_high = None

                    # Update timing information
                    if service.is_one_time_cost:
                        service.one_time_cost_year = one_time_year
                    elif service.occurrence_years:
                        if edit_mode == "Text Input":
                            occurrence_years = [int(year.strip()) for year in occurrence_years_str.split(",")]
                            service.occurrence_years = occurrence_years
                        else:
                            service.occurrence_years = sorted(selected_years)
                    else:
                        service.start_year = start_year
                        service.end_year = end_year

                    # Auto-save to database if enabled
                    if st.session_state.get('auto_save', True):
                        try:
                            db.save_life_care_plan(st.session_state.lcp_data)
                            st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
                        except Exception as e:
                            st.warning(f"Auto-save failed: {str(e)}")

                    st.success("✅ Service updated successfully!")
                    del st.session_state[f"editing_service_{service_index}"]
                    st.rerun()

                except Exception as e:
                    st.error(f"Error updating service: {str(e)}")
        
        with col2:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                del st.session_state[f"editing_service_{service_index}"]
                st.rerun()
