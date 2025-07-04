"""
Manage Service Tables Page for Streamlit Life Care Plan Application
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from src.models import ServiceTable, Service
from src.database import db

def calculate_age_for_year(base_year: int, current_age: float, target_year: int) -> float:
    """Calculate the age of the evaluee in a given year."""
    return current_age + (target_year - base_year)

def display_age_info(years, evaluee_current_age: float, base_year: int):
    """Display age information for given years."""
    if isinstance(years, (list, tuple)) and len(years) > 0:
        if len(years) == 1:
            age = calculate_age_for_year(base_year, evaluee_current_age, years[0])
            st.caption(f"📅 Age in {years[0]}: **{age:.1f} years old**")
        else:
            ages_info = []
            for year in sorted(years):
                age = calculate_age_for_year(base_year, evaluee_current_age, year)
                ages_info.append(f"{year} (age {age:.1f})")
            st.caption(f"📅 Ages: {', '.join(ages_info)}")
    elif isinstance(years, int):
        age = calculate_age_for_year(base_year, evaluee_current_age, years)
        st.caption(f"📅 Age in {years}: **{age:.1f} years old**")

def get_service_years(service):
    """Get all years when a service occurs."""
    years = set()
    
    if service.is_one_time_cost and service.one_time_cost_year:
        years.add(service.one_time_cost_year)
    elif hasattr(service, 'is_interval_based') and service.is_interval_based:
        if service.interval_start_year and service.interval_years:
            # Calculate all interval occurrences within projection period
            # We need to get the end year from session state
            if hasattr(st.session_state, 'lcp_data') and st.session_state.lcp_data:
                base_year = st.session_state.lcp_data.settings.base_year
                projection_years = st.session_state.lcp_data.settings.projection_years
                end_year = base_year + int(projection_years)
                
                # For decimal intervals, calculate the fractional year positions and round to nearest year
                current_fractional_year = float(service.interval_start_year)
                while current_fractional_year <= end_year:
                    # Round to nearest integer year
                    occurrence_year = round(current_fractional_year)
                    if occurrence_year <= end_year:
                        years.add(occurrence_year)
                    current_fractional_year += service.interval_years
    elif service.occurrence_years:
        years.update(service.occurrence_years)
    elif service.start_year and service.end_year:
        years.update(range(service.start_year, service.end_year + 1))
    elif hasattr(service, 'is_distributed_instances') and service.is_distributed_instances:
        if service.start_year and service.distribution_period_years:
            end_year = int(service.start_year + service.distribution_period_years)
            years.update(range(service.start_year, end_year + 1))
    
    return sorted(years)

def check_service_overlaps(new_service_data, table_name, exclude_service_index=None):
    """Check for overlaps between a new/edited service and existing services in the same table."""
    overlaps = []
    
    if table_name not in st.session_state.lcp_data.tables:
        return overlaps
    
    table = st.session_state.lcp_data.tables[table_name]
    
    # Get years for the new/edited service
    new_years = set()
    
    if new_service_data.get('is_one_time_cost') and new_service_data.get('one_time_cost_year'):
        new_years.add(new_service_data['one_time_cost_year'])
    elif new_service_data.get('is_interval_based'):
        if new_service_data.get('interval_start_year') and new_service_data.get('interval_years'):
            # Calculate all interval occurrences within projection period
            base_year = st.session_state.lcp_data.settings.base_year
            projection_years = st.session_state.lcp_data.settings.projection_years
            end_year = base_year + int(projection_years)
            
            # For decimal intervals, calculate the fractional year positions and round to nearest year
            current_fractional_year = float(new_service_data['interval_start_year'])
            while current_fractional_year <= end_year:
                # Round to nearest integer year
                occurrence_year = round(current_fractional_year)
                if occurrence_year <= end_year:
                    new_years.add(occurrence_year)
                current_fractional_year += new_service_data['interval_years']
    elif new_service_data.get('occurrence_years'):
        new_years.update(new_service_data['occurrence_years'])
    elif new_service_data.get('start_year') and new_service_data.get('end_year'):
        new_years.update(range(new_service_data['start_year'], new_service_data['end_year'] + 1))
    elif new_service_data.get('is_distributed_instances'):
        if new_service_data.get('start_year') and new_service_data.get('distribution_period_years'):
            end_year = int(new_service_data['start_year'] + new_service_data['distribution_period_years'])
            new_years.update(range(new_service_data['start_year'], end_year + 1))
    
    # Check against existing services
    for i, existing_service in enumerate(table.services):
        if exclude_service_index is not None and i == exclude_service_index:
            continue  # Skip the service being edited
            
        existing_years = set(get_service_years(existing_service))
        overlap_years = new_years.intersection(existing_years)
        
        if overlap_years:
            overlaps.append({
                'service_name': existing_service.name,
                'service_index': i,
                'overlap_years': sorted(overlap_years)
            })
    
    return overlaps

def display_overlap_warnings(overlaps, new_service_name):
    """Display warnings for overlapping services."""
    if overlaps:
        st.warning("⚠️ **Service Overlap Detected!**")
        st.markdown("The following existing services overlap with your new service:")
        
        for overlap in overlaps:
            years_str = ', '.join(map(str, overlap['overlap_years']))
            if len(overlap['overlap_years']) > 5:  # Truncate if too many years
                years_str = ', '.join(map(str, overlap['overlap_years'][:5])) + f"... ({len(overlap['overlap_years'])} total years)"
            
            st.error(f"🔴 **{overlap['service_name']}** overlaps in years: {years_str}")
        
        st.markdown("**Recommendations:**")
        st.markdown("- Adjust the years for one of the services")
        st.markdown("- Consider if both services are truly needed simultaneously")
        st.markdown("- Review if this overlap is intentional (e.g., multiple therapy types)")
        
        return True
    return False

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
    tab1, tab2, tab3, tab4 = st.tabs(["📋 View Tables", "➕ Add Table", "🔧 Add/Edit Services", "🌐 Unified View"])
    
    with tab1:
        show_tables_overview()
    
    with tab2:
        show_add_table_form()
    
    with tab3:
        show_service_management()
    
    with tab4:
        show_unified_view_edit()

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
                    if service.is_one_time_cost:
                        service_type = "One-time"
                        timing = f"Year {service.one_time_cost_year}"
                    elif hasattr(service, 'is_interval_based') and service.is_interval_based:
                        if service.interval_years == int(service.interval_years):
                            service_type = f"Every {int(service.interval_years)} years"
                            timing = f"Starting {service.interval_start_year}, every {int(service.interval_years)} years"
                        else:
                            service_type = f"Every {service.interval_years:.1f} years"
                            timing = f"Starting {service.interval_start_year}, every {service.interval_years:.1f} years"
                    elif service.occurrence_years:
                        service_type = "Discrete"
                        timing = f"Years: {', '.join(map(str, service.occurrence_years))}"
                    else:
                        service_type = "Recurring"
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

                    # Display frequency information
                    if hasattr(service, 'is_distributed_instances') and service.is_distributed_instances:
                        st.write(f"**Frequency:** {service.frequency_per_year:.2f}/year ({service.total_instances}x total)")
                    else:
                        st.write(f"**Frequency:** {service.frequency_per_year:.1f}/year")
                    st.write(f"**Inflation:** {service.inflation_rate:.1%}")

                    # Display service type information
                    if service.is_one_time_cost:
                        st.write(f"**Type:** One-time cost in {service.one_time_cost_year}")
                    elif service.occurrence_years:
                        years_display = ', '.join(map(str, service.occurrence_years))
                        if len(years_display) > 50:  # Truncate if too long
                            years_display = years_display[:47] + "..."
                        st.write(f"**Type:** Specific years: {years_display}")
                    elif hasattr(service, 'is_distributed_instances') and service.is_distributed_instances:
                        st.write(f"**Type:** {service.total_instances} instances over {service.distribution_period_years:.1f} years")
                        st.write(f"**Period:** {service.start_year} to {service.start_year + service.distribution_period_years:.0f}")
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
                help="How many times per year this service occurs. Examples:\n• 1.0 = Once per year\n• 0.5 = Every 2 years\n• 1.5 = Every 1.5 years\n• 0.33 = Every 3 years\n• 0.25 = Every 4 years\n\nNote: For 'Distributed Instances' this will be calculated automatically."
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
            ["Recurring", "Discrete Occurrences", "One-time Cost", "Specific Years", "Distributed Instances", "Interval Based (Every X Years)"],
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
                # Display age for start year
                start_age = calculate_age_for_year(
                    st.session_state.lcp_data.settings.base_year,
                    st.session_state.lcp_data.evaluee.current_age,
                    start_year
                )
                st.caption(f"📅 Starting age: **{start_age:.1f} years old**")
                
            with col2:
                end_year = st.number_input(
                    "End Year",
                    min_value=start_year,
                    value=int(st.session_state.lcp_data.settings.base_year + st.session_state.lcp_data.settings.projection_years) - 1,
                    step=1
                )
                # Display age for end year
                end_age = calculate_age_for_year(
                    st.session_state.lcp_data.settings.base_year,
                    st.session_state.lcp_data.evaluee.current_age,
                    end_year
                )
                st.caption(f"📅 Ending age: **{end_age:.1f} years old**")
            
            # Display service duration
            if end_year > start_year:
                duration = end_year - start_year + 1
                st.info(f"⏱️ Service duration: **{duration} years** (age {start_age:.1f} to {end_age:.1f})")

        elif service_type == "Discrete Occurrences":
            occurrence_years_str = st.text_input(
                "Occurrence Years",
                placeholder="e.g., 2025, 2030, 2035",
                help="Comma-separated list of years when this service occurs"
            )
            
            # Display ages for entered years
            if occurrence_years_str:
                try:
                    occurrence_years = [int(year.strip()) for year in occurrence_years_str.split(',')]
                    display_age_info(
                        occurrence_years,
                        st.session_state.lcp_data.evaluee.current_age,
                        st.session_state.lcp_data.settings.base_year
                    )
                except ValueError:
                    st.warning("Please enter valid years separated by commas")

        elif service_type == "Specific Years":
            st.markdown("**Select Specific Years:**")
            st.caption("Choose individual years from the projection period when this service will occur")

            # Create year range for selection
            base_year = st.session_state.lcp_data.settings.base_year
            end_year = base_year + int(st.session_state.lcp_data.settings.projection_years)
            if st.session_state.lcp_data.settings.projection_years % 1 != 0:
                end_year += 1
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
                # Display ages for selected years
                display_age_info(
                    selected_years,
                    st.session_state.lcp_data.evaluee.current_age,
                    st.session_state.lcp_data.settings.base_year
                )

        elif service_type == "Distributed Instances":
            st.markdown("**Total Instances Spread Over Period:**")
            st.caption("Enter the total number of times this service will occur, spread evenly over a specified period")
            
            col1, col2 = st.columns(2)
            with col1:
                total_instances = st.number_input(
                    "Total Number of Instances *",
                    min_value=1,
                    value=75,
                    step=1,
                    help="Total number of times this service will occur (e.g., 75 therapy sessions)"
                )
            with col2:
                distribution_period = st.number_input(
                    "Distribution Period (Years) *",
                    min_value=0.1,
                    value=5.0,
                    step=0.1,
                    format="%.1f",
                    help="Period over which instances are spread (e.g., 5 years)"
                )
            
            # Calculate and show effective frequency
            if distribution_period > 0:
                effective_frequency = total_instances / distribution_period
                st.info(f"💡 Effective Frequency: {effective_frequency:.2f} instances per year")
                if effective_frequency < 1:
                    years_per_instance = 1 / effective_frequency
                    st.caption(f"   (Approximately 1 instance every {years_per_instance:.1f} years)")
                else:
                    st.caption(f"   (Approximately {effective_frequency:.1f} instances per year)")
            
            # Start year for distribution
            distribution_start_year = st.number_input(
                "Start Year for Distribution",
                min_value=st.session_state.lcp_data.settings.base_year,
                value=st.session_state.lcp_data.settings.base_year,
                step=1,
                help="Year when the distributed instances begin"
            )
            
            # Display age information for distribution period
            distribution_end_year = distribution_start_year + distribution_period
            start_age = calculate_age_for_year(
                st.session_state.lcp_data.settings.base_year,
                st.session_state.lcp_data.evaluee.current_age,
                distribution_start_year
            )
            end_age = calculate_age_for_year(
                st.session_state.lcp_data.settings.base_year,
                st.session_state.lcp_data.evaluee.current_age,
                int(distribution_end_year)
            )
            st.caption(f"📅 Distribution period: Age {start_age:.1f} to {end_age:.1f} ({distribution_start_year} to {distribution_end_year:.1f})")
            
        elif service_type == "Interval Based (Every X Years)":
            st.markdown("**Interval-Based Service Configuration:**")
            st.caption("Service occurs at regular intervals (e.g., every 5-7 years)")
            
            col1, col2 = st.columns(2)
            with col1:
                interval_years = st.number_input(
                    "Interval (Years) *",
                    min_value=0.1,
                    max_value=20.0,
                    value=6.0,
                    step=0.1,
                    format="%.1f",
                    help="How often the service occurs (e.g., 3.5 means every 3.5 years, 6.0 means every 6 years)"
                )
            with col2:
                interval_start_year = st.number_input(
                    "First Occurrence Year *",
                    min_value=st.session_state.lcp_data.settings.base_year,
                    value=st.session_state.lcp_data.settings.base_year,
                    step=1,
                    help="Year of the first occurrence"
                )
            
            # Calculate and display all occurrences within projection period
            base_year = st.session_state.lcp_data.settings.base_year
            projection_years = st.session_state.lcp_data.settings.projection_years
            end_year = base_year + int(projection_years)
            
            occurrence_years_preview = []
            current_fractional_year = float(interval_start_year)
            while current_fractional_year <= end_year:
                # Round to nearest integer year for display
                occurrence_year = round(current_fractional_year)
                if occurrence_year <= end_year and occurrence_year not in occurrence_years_preview:
                    occurrence_years_preview.append(occurrence_year)
                current_fractional_year += interval_years
            
            # Sort the years
            occurrence_years_preview.sort()
            
            if occurrence_years_preview:
                st.info(f"🗓️ Service will occur in {len(occurrence_years_preview)} years: {', '.join(map(str, occurrence_years_preview))}")
                
                # Display ages for interval occurrences
                display_age_info(
                    occurrence_years_preview,
                    st.session_state.lcp_data.evaluee.current_age,
                    st.session_state.lcp_data.settings.base_year
                )
                
                # Show frequency info
                if len(occurrence_years_preview) > 1:
                    avg_frequency = len(occurrence_years_preview) / (occurrence_years_preview[-1] - occurrence_years_preview[0] + 1)
                    st.caption(f"💡 Average frequency: {avg_frequency:.3f} occurrences per year")
            
        else:  # One-time cost
            one_time_year = st.number_input(
                "Year of Occurrence",
                min_value=st.session_state.lcp_data.settings.base_year,
                value=st.session_state.lcp_data.settings.base_year,
                step=1
            )
            # Display age for one-time cost year
            display_age_info(
                one_time_year,
                st.session_state.lcp_data.evaluee.current_age,
                st.session_state.lcp_data.settings.base_year
            )
        
        submitted = st.form_submit_button("➕ Add Service", use_container_width=True)
        
        if submitted:
            if not service_name.strip():
                st.error("Please enter a service name.")
                return
            
            # Prepare service data for overlap checking
            overlap_check_data = {
                "name": service_name.strip(),
                "start_year": None,
                "end_year": None,
                "occurrence_years": None,
                "is_one_time_cost": False,
                "one_time_cost_year": None,
                "is_distributed_instances": False,
                "distribution_period_years": None,
                "is_interval_based": False,
                "interval_years": None,
                "interval_start_year": None
            }
            
            # Set timing data based on service type
            if service_type == "Recurring":
                overlap_check_data["start_year"] = start_year
                overlap_check_data["end_year"] = end_year
            elif service_type == "Discrete Occurrences":
                if occurrence_years_str:
                    try:
                        overlap_check_data["occurrence_years"] = [int(year.strip()) for year in occurrence_years_str.split(',')]
                    except ValueError:
                        st.error("Please enter valid years separated by commas.")
                        return
            elif service_type == "Specific Years":
                overlap_check_data["occurrence_years"] = selected_years
            elif service_type == "Distributed Instances":
                overlap_check_data["is_distributed_instances"] = True
                overlap_check_data["start_year"] = distribution_start_year
                overlap_check_data["distribution_period_years"] = distribution_period
            elif service_type == "Interval Based (Every X Years)":
                overlap_check_data["is_interval_based"] = True
                overlap_check_data["interval_years"] = interval_years
                overlap_check_data["interval_start_year"] = interval_start_year
            else:  # One-time cost
                overlap_check_data["is_one_time_cost"] = True
                overlap_check_data["one_time_cost_year"] = one_time_year
            
            # Check for overlaps
            overlaps = check_service_overlaps(overlap_check_data, table.name)
            
            # Display overlap warnings but allow user to proceed
            if overlaps:
                display_overlap_warnings(overlaps, service_name.strip())
                st.info("ℹ️ You can still add this service if the overlap is intentional.")
            
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
                elif service_type == "Distributed Instances":
                    if total_instances <= 0:
                        st.error("Total instances must be greater than zero.")
                        return
                    if distribution_period <= 0:
                        st.error("Distribution period must be greater than zero.")
                        return
                    
                    # Set up distributed instance parameters
                    service_params.update({
                        "is_distributed_instances": True,
                        "total_instances": total_instances,
                        "distribution_period_years": distribution_period,
                        "start_year": distribution_start_year,
                        "end_year": int(distribution_start_year + distribution_period),
                        "frequency_per_year": total_instances / distribution_period  # This will be calculated in __post_init__
                    })
                elif service_type == "Interval Based (Every X Years)":
                    if interval_years <= 0:
                        st.error("Interval years must be greater than zero.")
                        return
                    if interval_start_year < st.session_state.lcp_data.settings.base_year:
                        st.error("Start year cannot be before the base year.")
                        return
                    
                    # Set up interval-based service parameters
                    service_params.update({
                        "is_interval_based": True,
                        "interval_years": interval_years,
                        "interval_start_year": interval_start_year,
                        "frequency_per_year": 1.0 / interval_years  # This will be calculated in __post_init__
                    })
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
            # Display age for one-time cost year
            display_age_info(
                one_time_year,
                st.session_state.lcp_data.evaluee.current_age,
                st.session_state.lcp_data.settings.base_year
            )
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
                # Display ages for entered years
                if occurrence_years_str:
                    try:
                        occurrence_years = [int(year.strip()) for year in occurrence_years_str.split(',')]
                        display_age_info(
                            occurrence_years,
                            st.session_state.lcp_data.evaluee.current_age,
                            st.session_state.lcp_data.settings.base_year
                        )
                    except ValueError:
                        st.warning("Please enter valid years separated by commas")
            else:
                # Multi-select for years
                base_year = st.session_state.lcp_data.settings.base_year
                end_year = base_year + int(st.session_state.lcp_data.settings.projection_years)
                if st.session_state.lcp_data.settings.projection_years % 1 != 0:
                    end_year += 1
                available_years = list(range(base_year, end_year))

                selected_years = st.multiselect(
                    "Select Years",
                    options=available_years,
                    default=service.occurrence_years,
                    help="Select all years when this service will occur"
                )
                # Display ages for selected years
                if selected_years:
                    display_age_info(
                        selected_years,
                        st.session_state.lcp_data.evaluee.current_age,
                        st.session_state.lcp_data.settings.base_year
                    )
        else:
            st.write("**Current Type:** Recurring")
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.number_input("Start Year", value=int(service.start_year) if service.start_year else 2025, step=1)
                # Display age for start year
                start_age = calculate_age_for_year(
                    st.session_state.lcp_data.settings.base_year,
                    st.session_state.lcp_data.evaluee.current_age,
                    start_year
                )
                st.caption(f"📅 Starting age: **{start_age:.1f} years old**")
            with col2:
                end_year = st.number_input("End Year", value=int(service.end_year) if service.end_year else 2030, step=1)
                # Display age for end year
                end_age = calculate_age_for_year(
                    st.session_state.lcp_data.settings.base_year,
                    st.session_state.lcp_data.evaluee.current_age,
                    end_year
                )
                st.caption(f"📅 Ending age: **{end_age:.1f} years old**")
            
            # Display service duration
            if end_year > start_year:
                duration = end_year - start_year + 1
                st.info(f"⏱️ Service duration: **{duration} years** (age {start_age:.1f} to {end_age:.1f})")
        
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

def show_unified_view_edit():
    """Show unified view of all tables and services with inline editing capabilities."""
    st.subheader("🌐 Unified View - All Tables & Services")
    st.markdown("View and edit all your service tables and services from one comprehensive interface.")
    
    # Multi-scenario support
    has_multiple_scenarios = len(st.session_state.lcp_data.scenarios) > 1
    
    if has_multiple_scenarios:
        st.markdown("#### 🎭 Scenario Selection")
        
        # View mode selection
        view_mode = st.radio(
            "View Mode:",
            ["Current Scenario Only", "Selected Scenarios", "All Scenarios Combined"],
            help="Choose which scenarios to view and edit"
        )
        
        selected_scenarios = []
        
        if view_mode == "Current Scenario Only":
            current_scenario = st.session_state.lcp_data.get_current_scenario()
            st.info(f"**Viewing:** {current_scenario.name if current_scenario else 'Unknown'}")
        elif view_mode == "Selected Scenarios":
            st.markdown("#### 📋 Select Scenarios to View")
            st.caption("💡 Choose which scenarios to include in the unified view. You can edit services from any selected scenario.")
            
            # Add Select All / Deselect All buttons
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button("✅ Select All", key="select_all_scenarios"):
                    for scenario_key in st.session_state.lcp_data.scenarios.keys():
                        st.session_state[f"scenario_select_{scenario_key}"] = True
                    st.rerun()
            with col2:
                if st.button("❌ Deselect All", key="deselect_all_scenarios"):
                    for scenario_key in st.session_state.lcp_data.scenarios.keys():
                        st.session_state[f"scenario_select_{scenario_key}"] = False
                    st.rerun()
            
            # Create checkboxes for each scenario
            scenario_options = {}
            col_count = min(3, len(st.session_state.lcp_data.scenarios))  # Max 3 columns
            cols = st.columns(col_count)
            
            for idx, (scenario_key, scenario) in enumerate(st.session_state.lcp_data.scenarios.items()):
                col_idx = idx % col_count
                with cols[col_idx]:
                    baseline_text = " (Baseline)" if scenario.is_baseline else ""
                    is_current = scenario_key == st.session_state.lcp_data.active_scenario
                    current_text = " 🟢" if is_current else ""
                    
                    # Default to selecting current scenario
                    default_value = is_current
                    
                    checkbox_key = f"scenario_select_{scenario_key}"
                    selected = st.checkbox(
                        f"{scenario.name}{baseline_text}{current_text}",
                        value=default_value,
                        key=checkbox_key,
                        help=f"Include '{scenario.name}' in the unified view"
                    )
                    
                    if selected:
                        selected_scenarios.append(scenario_key)
            
            if selected_scenarios:
                scenario_names = [st.session_state.lcp_data.scenarios[key].name for key in selected_scenarios]
                st.info(f"**Selected:** {', '.join(scenario_names)} ({len(selected_scenarios)} scenarios)")
            else:
                st.warning("⚠️ No scenarios selected. Please select at least one scenario to view.")
                return
        else:  # All Scenarios Combined
            selected_scenarios = list(st.session_state.lcp_data.scenarios.keys())
            scenario_count = len(st.session_state.lcp_data.scenarios)
            st.info(f"**Viewing:** All {scenario_count} scenarios combined")
        
        st.markdown("---")
        
        # If viewing multiple scenarios, use the multi-scenario view with selected scenarios
        if view_mode in ["Selected Scenarios", "All Scenarios Combined"]:
            show_multi_scenario_unified_view(selected_scenarios)
            return
    else:
        view_mode = "Current Scenario Only"
    
    # Check if we have any tables
    if not st.session_state.lcp_data.tables:
        st.info("No service tables created yet. Use the 'Add Table' tab to create your first table.")
        return
    
    # Get all services from current scenario (original functionality preserved)
    all_services = []
    for table_name, table in st.session_state.lcp_data.tables.items():
        for i, service in enumerate(table.services):
            service_years = get_service_years(service)
            all_services.append({
                'table_name': table_name,
                'service_name': service.name,
                'service_index': i,
                'service_obj': service,
                'unit_cost': service.unit_cost,
                'frequency': service.frequency_per_year,
                'inflation_rate': service.inflation_rate * 100,
                'years': service_years,
                'year_range': f"{min(service_years)}-{max(service_years)}" if service_years else "None",
                'total_years': len(service_years),
                'service_type': "One-time" if service.is_one_time_cost else ("Distributed" if hasattr(service, 'is_distributed_instances') and service.is_distributed_instances else ("Discrete" if service.occurrence_years else "Recurring"))
            })
    
    if not all_services:
        st.info("No services found. Add services to your tables using the 'Add/Edit Services' tab.")
        return
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tables", len(st.session_state.lcp_data.tables))
    with col2:
        st.metric("Total Services", len(all_services))
    with col3:
        total_cost = sum(s['unit_cost'] * s['frequency'] for s in all_services)
        st.metric("Total Annual Cost", f"${total_cost:,.0f}")
    with col4:
        avg_inflation = sum(s['inflation_rate'] for s in all_services) / len(all_services)
        st.metric("Avg Inflation", f"{avg_inflation:.1f}%")
    
    st.markdown("---")
    
    # Filters and search
    if view_mode == "All Scenarios Combined":
        col1, col2, col3, col4, col5 = st.columns(5)
        with col4:
            # Get unique scenarios for filter
            unique_scenarios = list(set(s['scenario_name'] for s in all_services))
            filter_scenario = st.selectbox("Filter by scenario:", ["All Scenarios"] + unique_scenarios)
        with col5:
            # Age range filtering
            age_filter_mode = st.selectbox("Age filter:", ["All Ages", "By Age Range", "Active at Age"])
    else:
        col1, col2, col3, col4 = st.columns(4)
        filter_scenario = None
        with col4:
            # Age range filtering
            age_filter_mode = st.selectbox("Age filter:", ["All Ages", "By Age Range", "Active at Age"])
    
    with col1:
        search_term = st.text_input("🔍 Search services:", placeholder="Enter service or table name")
    with col2:
        # Get unique tables for filter based on view mode
        if view_mode == "All Scenarios Combined":
            unique_tables = list(set(s['table_name'] for s in all_services))
        else:
            unique_tables = list(st.session_state.lcp_data.tables.keys())
        filter_table = st.selectbox("Filter by table:", ["All Tables"] + unique_tables)
    with col3:
        filter_type = st.selectbox("Filter by type:", ["All Types", "Recurring", "One-time", "Discrete", "Distributed"])
    
    # Age filtering inputs
    age_filter_min = None
    age_filter_max = None
    age_filter_specific = None
    
    if age_filter_mode == "By Age Range":
        col1, col2 = st.columns(2)
        with col1:
            age_filter_min = st.number_input("Min age:", min_value=0.0, max_value=120.0, value=st.session_state.lcp_data.evaluee.current_age, step=1.0)
        with col2:
            age_filter_max = st.number_input("Max age:", min_value=age_filter_min if age_filter_min else 0.0, max_value=120.0, value=st.session_state.lcp_data.evaluee.current_age + 10, step=1.0)
        st.info(f"💡 Showing services active between ages {age_filter_min:.0f} and {age_filter_max:.0f}")
    elif age_filter_mode == "Active at Age":
        age_filter_specific = st.number_input("Show services active at age:", min_value=0.0, max_value=120.0, value=st.session_state.lcp_data.evaluee.current_age, step=1.0)
        st.info(f"💡 Showing services active at age {age_filter_specific:.0f}")
    
    # Apply filters
    filtered_services = all_services
    if search_term:
        filtered_services = [s for s in filtered_services if 
                           search_term.lower() in s['service_name'].lower() or 
                           search_term.lower() in s['table_name'].lower() or
                           (view_mode == "All Scenarios Combined" and search_term.lower() in s['scenario_name'].lower())]
    if filter_table != "All Tables":
        filtered_services = [s for s in filtered_services if s['table_name'] == filter_table]
    if filter_type != "All Types":
        filtered_services = [s for s in filtered_services if s['service_type'] == filter_type]
    if filter_scenario and filter_scenario != "All Scenarios":
        filtered_services = [s for s in filtered_services if s['scenario_name'] == filter_scenario]
    
    # Apply age filtering
    if age_filter_mode != "All Ages":
        age_filtered_services = []
        base_year = st.session_state.lcp_data.settings.base_year
        current_age = st.session_state.lcp_data.evaluee.current_age
        
        for service_data in filtered_services:
            service_years = service_data['years']
            if not service_years:
                continue
                
            # Convert years to ages
            service_ages = [calculate_age_for_year(base_year, current_age, year) for year in service_years]
            
            include_service = False
            if age_filter_mode == "By Age Range":
                # Check if service is active during any part of the age range
                min_service_age = min(service_ages)
                max_service_age = max(service_ages)
                if (min_service_age <= age_filter_max and max_service_age >= age_filter_min):
                    include_service = True
            elif age_filter_mode == "Active at Age":
                # Check if service is active at the specific age
                if age_filter_specific >= min(service_ages) and age_filter_specific <= max(service_ages):
                    include_service = True
            
            if include_service:
                age_filtered_services.append(service_data)
        
        filtered_services = age_filtered_services
    
    st.markdown(f"### Found {len(filtered_services)} services")
    
    if not filtered_services:
        st.warning("No services match your filters.")
        return
    
    # Quick edit options
    st.markdown("#### Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📈 Bulk Inflation Update", use_container_width=True):
            st.session_state.show_bulk_inflation = True
    with col2:
        if st.button("📅 Detect All Overlaps", use_container_width=True):
            show_all_overlaps()
    with col3:
        if st.button("💾 Export Service List", use_container_width=True):
            show_export_service_list(filtered_services)
    
    # Bulk inflation update
    if st.session_state.get('show_bulk_inflation', False):
        st.markdown("#### 📈 Bulk Inflation Rate Update")
        with st.form("bulk_inflation_form"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                new_inflation = st.number_input("New inflation rate (%):", value=3.5, min_value=0.0, max_value=20.0, step=0.1)
            with col2:
                apply_to = st.selectbox("Apply to:", ["All Services", "Selected Table Only"])
            with col3:
                target_table = st.selectbox("Target table:", list(st.session_state.lcp_data.tables.keys())) if apply_to == "Selected Table Only" else None
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Update Inflation", use_container_width=True):
                    update_count = 0
                    for service_data in filtered_services:
                        if apply_to == "All Services" or service_data['table_name'] == target_table:
                            service_data['service_obj'].inflation_rate = new_inflation / 100
                            update_count += 1
                    
                    # Auto-save if enabled
                    if st.session_state.get('auto_save', True):
                        try:
                            db.save_life_care_plan(st.session_state.lcp_data)
                            st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
                        except Exception as e:
                            st.warning(f"Auto-save failed: {str(e)}")
                    
                    st.success(f"✅ Updated inflation rate for {update_count} services to {new_inflation}%")
                    st.session_state.show_bulk_inflation = False
                    st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.show_bulk_inflation = False
                    st.rerun()
    
    st.markdown("---")
    
    # Detailed service list with inline editing
    st.markdown("#### 📋 Service Details")
    
    # Group services by scenario and table for better organization
    if view_mode == "All Scenarios Combined":
        services_by_scenario_table = {}
        for service in filtered_services:
            key = f"{service['scenario_name']} / {service['table_name']}"
            if key not in services_by_scenario_table:
                services_by_scenario_table[key] = []
            services_by_scenario_table[key].append(service)
        
        for scenario_table_key, table_services in services_by_scenario_table.items():
            with st.expander(f"🎭 {scenario_table_key} ({len(table_services)} services)", expanded=True):
                _display_service_list(table_services, view_mode)
    else:
        services_by_table = {}
        for service in filtered_services:
            table_name = service['table_name']
            if table_name not in services_by_table:
                services_by_table[table_name] = []
            services_by_table[table_name].append(service)
        
        for table_name, table_services in services_by_table.items():
            with st.expander(f"📋 {table_name} ({len(table_services)} services)", expanded=True):
                _display_service_list(table_services, view_mode)

def _display_service_list(table_services, view_mode):
    """Helper function to display a list of services with editing capabilities."""
    for service_data in table_services:
        service = service_data['service_obj']
        service_index = service_data['service_index']
        table_name = service_data['table_name']
        
        # Create columns for service display
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
        
        with col1:
            st.markdown(f"**{service.name}**")
            # Show age information for service years
            if service_data['years']:
                if len(service_data['years']) <= 3:
                    ages = [calculate_age_for_year(st.session_state.lcp_data.settings.base_year, 
                                                 st.session_state.lcp_data.evaluee.current_age, year) 
                           for year in service_data['years']]
                    age_str = ', '.join([f"Age {age:.1f}" for age in ages])
                    st.caption(f"📅 {service_data['year_range']} ({age_str})")
                else:
                    start_age = calculate_age_for_year(st.session_state.lcp_data.settings.base_year, 
                                                     st.session_state.lcp_data.evaluee.current_age, 
                                                     min(service_data['years']))
                    end_age = calculate_age_for_year(st.session_state.lcp_data.settings.base_year, 
                                                   st.session_state.lcp_data.evaluee.current_age, 
                                                   max(service_data['years']))
                    st.caption(f"📅 {service_data['year_range']} (Age {start_age:.1f} to {end_age:.1f})")
        
        with col2:
            st.write(f"**${service.unit_cost:,.2f}**")
            st.caption(f"{service.frequency_per_year:.1f}/year")
        
        with col3:
            st.write(f"**{service.inflation_rate*100:.1f}%**")
            st.caption(f"{service_data['service_type']}")
        
        with col4:
            annual_cost = service.unit_cost * service.frequency_per_year
            st.write(f"**${annual_cost:,.0f}**/year")
            st.caption(f"{service_data['total_years']} years")
        
        with col5:
            # Create unique key based on view mode to avoid duplicates
            view_prefix = "multi" if view_mode == "All Scenarios Combined" else "single"
            scenario_id = service_data.get('scenario_key', 'current') if view_mode == "All Scenarios Combined" else 'current'
            edit_key = f"edit_unified_{view_prefix}_{scenario_id}_{table_name}_{service_index}"
            edit_state_key = f"editing_unified_{view_prefix}_{scenario_id}_{table_name}_{service_index}"
            
            if st.button("✏️", key=edit_key, help="Quick edit"):
                st.session_state[edit_state_key] = True
                st.rerun()
        
        # Simplified quick edit form with basic cost/frequency editing only
        if st.session_state.get(edit_state_key, False):
            with st.form(f"quick_edit_{view_prefix}_{scenario_id}_{table_name}_{service_index}"):
                st.markdown(f"**Quick Edit: {service.name}**")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_cost = st.number_input("Unit Cost ($):", value=float(service.unit_cost), min_value=0.0)
                with col2:
                    new_freq = st.number_input("Frequency/Year:", value=float(service.frequency_per_year), min_value=0.1)
                with col3:
                    new_inflation = st.number_input("Inflation (%):", value=float(service.inflation_rate * 100), min_value=0.0, max_value=20.0)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Save", use_container_width=True):
                        # For multi-scenario view, we may need to switch scenarios
                        if view_mode == "All Scenarios Combined" and scenario_id != 'current':
                            # Switch to the correct scenario for editing
                            original_scenario = st.session_state.lcp_data.active_scenario
                            st.session_state.lcp_data.set_active_scenario(scenario_id)
                            
                            # Update the service in the correct scenario
                            target_table = st.session_state.lcp_data.tables[table_name]
                            target_service = target_table.services[service_index]
                            target_service.unit_cost = new_cost
                            target_service.frequency_per_year = new_freq
                            target_service.inflation_rate = new_inflation / 100
                            
                            # Switch back to original scenario
                            st.session_state.lcp_data.set_active_scenario(original_scenario)
                        else:
                            # Update cost and frequency information in current scenario
                            service.unit_cost = new_cost
                            service.frequency_per_year = new_freq
                            service.inflation_rate = new_inflation / 100
                        
                        # Auto-save if enabled
                        if st.session_state.get('auto_save', True):
                            try:
                                db.save_life_care_plan(st.session_state.lcp_data)
                                st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
                            except Exception as e:
                                st.warning(f"Auto-save failed: {str(e)}")
                        
                        st.success("✅ Service updated!")
                        del st.session_state[edit_state_key]
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        del st.session_state[edit_state_key]
                        st.rerun()
        
        st.markdown("---")

def show_all_overlaps():
    """Detect and display all service overlaps across all tables."""
    st.markdown("#### 🔍 Service Overlap Analysis")
    
    overlaps_found = []
    
    # Check each table for internal overlaps
    for table_name, table in st.session_state.lcp_data.tables.items():
        for i, service1 in enumerate(table.services):
            years1 = set(get_service_years(service1))
            
            for j, service2 in enumerate(table.services[i+1:], i+1):
                years2 = set(get_service_years(service2))
                overlap_years = years1.intersection(years2)
                
                if overlap_years:
                    overlaps_found.append({
                        'table': table_name,
                        'service1': service1.name,
                        'service2': service2.name,
                        'overlap_years': sorted(overlap_years)
                    })
    
    if overlaps_found:
        st.warning(f"⚠️ Found {len(overlaps_found)} service overlaps:")
        
        for overlap in overlaps_found:
            years_str = ', '.join(map(str, overlap['overlap_years'][:5]))
            if len(overlap['overlap_years']) > 5:
                years_str += f"... ({len(overlap['overlap_years'])} total years)"
            
            st.error(f"**{overlap['table']}**: {overlap['service1']} ↔ {overlap['service2']} (Years: {years_str})")
    else:
        st.success("✅ No service overlaps detected!")

def show_export_service_list(services):
    """Show export options for the service list."""
    st.markdown("#### 💾 Export Service List")
    
    # Create DataFrame for export
    export_data = []
    for service in services:
        export_data.append({
            'Table': service['table_name'],
            'Service': service['service_name'],
            'Type': service['service_type'],
            'Unit Cost': service['unit_cost'],
            'Frequency/Year': service['frequency'],
            'Inflation Rate (%)': service['inflation_rate'],
            'Year Range': service['year_range'],
            'Total Years': service['total_years'],
            'Annual Cost': service['unit_cost'] * service['frequency']
        })
    
    df = pd.DataFrame(export_data)
    
    # Display as CSV
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name=f"service_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # Show preview
    st.dataframe(df, use_container_width=True)

def show_multi_scenario_unified_view(selected_scenario_keys=None):
    """Show unified view across selected scenarios with editing capabilities.
    
    Args:
        selected_scenario_keys: List of scenario keys to include. If None, includes all scenarios.
    """
    # Default to all scenarios if none specified
    if selected_scenario_keys is None:
        selected_scenario_keys = list(st.session_state.lcp_data.scenarios.keys())
    
    st.markdown("### 🎭 Multi-Scenario Unified View")
    
    # Show which scenarios are being viewed
    if len(selected_scenario_keys) == len(st.session_state.lcp_data.scenarios):
        st.markdown("View and edit services across **all scenarios**. **Note:** Editing services will modify them in their respective scenarios.")
    else:
        scenario_names = [st.session_state.lcp_data.scenarios[key].name for key in selected_scenario_keys]
        st.markdown(f"View and edit services from **{len(selected_scenario_keys)} selected scenarios**: {', '.join(scenario_names)}. **Note:** Editing services will modify them in their respective scenarios.")
    
    # Check if selected scenarios have tables
    has_tables = any(st.session_state.lcp_data.scenarios[key].tables for key in selected_scenario_keys if key in st.session_state.lcp_data.scenarios)
    if not has_tables:
        st.info("No service tables found in the selected scenarios. Create tables and services first.")
        return
    
    # Collect services from selected scenarios only
    all_services = []
    for scenario_key in selected_scenario_keys:
        if scenario_key not in st.session_state.lcp_data.scenarios:
            continue  # Skip if scenario doesn't exist
            
        scenario = st.session_state.lcp_data.scenarios[scenario_key]
        for table_name, table in scenario.tables.items():
            for i, service in enumerate(table.services):
                service_years = get_service_years(service)
                baseline_text = " (Baseline)" if scenario.is_baseline else ""
                all_services.append({
                    'scenario_name': f"{scenario.name}{baseline_text}",
                    'scenario_key': scenario_key,
                    'table_name': table_name,
                    'service_name': service.name,
                    'service_index': i,
                    'service_obj': service,
                    'unit_cost': service.unit_cost,
                    'frequency': service.frequency_per_year,
                    'inflation_rate': service.inflation_rate * 100,
                    'years': service_years,
                    'year_range': f"{min(service_years)}-{max(service_years)}" if service_years else "None",
                    'total_years': len(service_years),
                    'service_type': "One-time" if service.is_one_time_cost else ("Distributed" if hasattr(service, 'is_distributed_instances') and service.is_distributed_instances else ("Discrete" if service.occurrence_years else "Recurring"))
                })
    
    if not all_services:
        st.info("No services found in the selected scenarios.")
        return
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Selected Scenarios", len(selected_scenario_keys))
    with col2:
        table_count = len(set(s['table_name'] for s in all_services))
        st.metric("Unique Tables", table_count)
    with col3:
        st.metric("Total Services", len(all_services))
    with col4:
        total_cost = sum(s['unit_cost'] * s['frequency'] for s in all_services)
        st.metric("Total Annual Cost", f"${total_cost:,.0f}")
    
    st.markdown("---")
    
    # Filters and search
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        search_term = st.text_input("🔍 Search:", placeholder="Service, table, or scenario")
    with col2:
        unique_scenarios = list(set(s['scenario_name'] for s in all_services))
        filter_scenario = st.selectbox("Filter by scenario:", ["All Scenarios"] + unique_scenarios)
    with col3:
        unique_tables = list(set(s['table_name'] for s in all_services))
        filter_table = st.selectbox("Filter by table:", ["All Tables"] + unique_tables)
    with col4:
        filter_type = st.selectbox("Filter by type:", ["All Types", "Recurring", "One-time", "Discrete", "Distributed"])
    with col5:
        # Age range filtering
        age_filter_mode = st.selectbox("Age filter:", ["All Ages", "By Age Range", "Active at Age"])
    
    # Age filtering inputs for multi-scenario view
    age_filter_min = None
    age_filter_max = None
    age_filter_specific = None
    
    if age_filter_mode == "By Age Range":
        col1, col2 = st.columns(2)
        with col1:
            age_filter_min = st.number_input("Min age:", min_value=0.0, max_value=120.0, value=st.session_state.lcp_data.evaluee.current_age, step=1.0, key="multi_age_min")
        with col2:
            age_filter_max = st.number_input("Max age:", min_value=age_filter_min if age_filter_min else 0.0, max_value=120.0, value=st.session_state.lcp_data.evaluee.current_age + 10, step=1.0, key="multi_age_max")
        st.info(f"💡 Showing services active between ages {age_filter_min:.0f} and {age_filter_max:.0f} across all scenarios")
    elif age_filter_mode == "Active at Age":
        age_filter_specific = st.number_input("Show services active at age:", min_value=0.0, max_value=120.0, value=st.session_state.lcp_data.evaluee.current_age, step=1.0, key="multi_age_specific")
        st.info(f"💡 Showing services active at age {age_filter_specific:.0f} across all scenarios")
    
    # Apply filters
    filtered_services = all_services
    if search_term:
        filtered_services = [s for s in filtered_services if 
                           search_term.lower() in s['service_name'].lower() or 
                           search_term.lower() in s['table_name'].lower() or
                           search_term.lower() in s['scenario_name'].lower()]
    if filter_scenario != "All Scenarios":
        filtered_services = [s for s in filtered_services if s['scenario_name'] == filter_scenario]
    if filter_table != "All Tables":
        filtered_services = [s for s in filtered_services if s['table_name'] == filter_table]
    if filter_type != "All Types":
        filtered_services = [s for s in filtered_services if s['service_type'] == filter_type]
    
    # Apply age filtering for multi-scenario view
    if age_filter_mode != "All Ages":
        age_filtered_services = []
        base_year = st.session_state.lcp_data.settings.base_year
        current_age = st.session_state.lcp_data.evaluee.current_age
        
        for service_data in filtered_services:
            service_years = service_data['years']
            if not service_years:
                continue
                
            # Convert years to ages
            service_ages = [calculate_age_for_year(base_year, current_age, year) for year in service_years]
            
            include_service = False
            if age_filter_mode == "By Age Range":
                # Check if service is active during any part of the age range
                min_service_age = min(service_ages)
                max_service_age = max(service_ages)
                if (min_service_age <= age_filter_max and max_service_age >= age_filter_min):
                    include_service = True
            elif age_filter_mode == "Active at Age":
                # Check if service is active at the specific age
                if age_filter_specific >= min(service_ages) and age_filter_specific <= max(service_ages):
                    include_service = True
            
            if include_service:
                age_filtered_services.append(service_data)
        
        filtered_services = age_filtered_services
    
    scenario_text = "selected scenarios" if len(selected_scenario_keys) < len(st.session_state.lcp_data.scenarios) else "all scenarios"
    st.markdown(f"### Found {len(filtered_services)} services across {scenario_text}")
    
    if not filtered_services:
        st.info("No services match your filters.")
        return
    
    # Group by scenario and table
    services_by_scenario_table = {}
    for service in filtered_services:
        key = f"{service['scenario_name']} / {service['table_name']}"
        if key not in services_by_scenario_table:
            services_by_scenario_table[key] = []
        services_by_scenario_table[key].append(service)
    
    # Display services grouped by scenario/table
    for scenario_table_key, table_services in services_by_scenario_table.items():
        with st.expander(f"🎭 {scenario_table_key} ({len(table_services)} services)", expanded=True):
            
            for service_data in table_services:
                service = service_data['service_obj']
                service_index = service_data['service_index']
                table_name = service_data['table_name']
                scenario_key = service_data['scenario_key']
                
                # Create unique key for multi-scenario editing
                edit_key = f"multi_scenario_{scenario_key}_{table_name}_{service_index}"
                
                # Create columns for service display
                col1, col2, col3, col4, col5, col6 = st.columns([3, 1.5, 1.5, 1.5, 1, 1])
                
                with col1:
                    st.markdown(f"**{service.name}**")
                    # Show age information for service years
                    if service_data['years']:
                        if len(service_data['years']) <= 3:
                            ages = [calculate_age_for_year(st.session_state.lcp_data.settings.base_year, 
                                                         st.session_state.lcp_data.evaluee.current_age, year) 
                                   for year in service_data['years']]
                            age_str = ', '.join([f"Age {age:.1f}" for age in ages])
                            st.caption(f"📅 {service_data['year_range']} ({age_str})")
                        else:
                            start_age = calculate_age_for_year(st.session_state.lcp_data.settings.base_year, 
                                                             st.session_state.lcp_data.evaluee.current_age, 
                                                             min(service_data['years']))
                            end_age = calculate_age_for_year(st.session_state.lcp_data.settings.base_year, 
                                                           st.session_state.lcp_data.evaluee.current_age, 
                                                           max(service_data['years']))
                            st.caption(f"📅 {service_data['year_range']} (Age {start_age:.1f} to {end_age:.1f})")
                
                with col2:
                    st.write(f"**${service.unit_cost:,.2f}**")
                    st.caption(f"{service.frequency_per_year:.1f}/year")
                
                with col3:
                    st.write(f"**{service.inflation_rate*100:.1f}%**")
                    st.caption(f"{service_data['service_type']}")
                
                with col4:
                    annual_cost = service.unit_cost * service.frequency_per_year
                    st.write(f"**${annual_cost:,.0f}**/year")
                    st.caption(f"{service_data['total_years']} years")
                
                with col5:
                    scenario_parts = service_data['scenario_name'].split(' (')[0]  # Remove "(Baseline)" for display
                    st.caption(f"**Scenario:**")
                    st.caption(f"{scenario_parts}")
                
                with col6:
                    if st.button("✏️", key=f"edit_{edit_key}", help="Edit service"):
                        st.session_state[f"editing_{edit_key}"] = True
                        st.rerun()
                
                # Quick edit form for cross-scenario editing
                if st.session_state.get(f"editing_{edit_key}", False):
                    with st.form(f"edit_form_{edit_key}"):
                        st.markdown(f"**Editing: {service.name}** (in {service_data['scenario_name']})")
                        st.warning("⚠️ **Multi-Scenario Edit**: Changes will be applied to this service in its original scenario.")
                        
                        # Cost and frequency section
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            new_cost = st.number_input("Unit Cost ($):", value=float(service.unit_cost), min_value=0.0, key=f"cost_{edit_key}")
                        with col2:
                            new_freq = st.number_input("Frequency/Year:", value=float(service.frequency_per_year), min_value=0.1, key=f"freq_{edit_key}")
                        with col3:
                            new_inflation = st.number_input("Inflation (%):", value=float(service.inflation_rate * 100), min_value=0.0, max_value=20.0, key=f"infl_{edit_key}")
                        
                        # Save/Cancel buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                                # Switch to the correct scenario for editing
                                original_scenario = st.session_state.lcp_data.active_scenario
                                st.session_state.lcp_data.set_active_scenario(scenario_key)
                                
                                # Update the service
                                target_table = st.session_state.lcp_data.tables[table_name]
                                target_service = target_table.services[service_index]
                                target_service.unit_cost = new_cost
                                target_service.frequency_per_year = new_freq
                                target_service.inflation_rate = new_inflation / 100
                                
                                # Switch back to original scenario
                                st.session_state.lcp_data.set_active_scenario(original_scenario)
                                
                                # Auto-save if enabled
                                if st.session_state.get('auto_save', True):
                                    try:
                                        db.save_life_care_plan(st.session_state.lcp_data)
                                        st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
                                    except Exception as e:
                                        st.warning(f"Auto-save failed: {str(e)}")
                                
                                st.success(f"✅ Updated {service.name} in {service_data['scenario_name']}!")
                                del st.session_state[f"editing_{edit_key}"]
                                st.rerun()
                        
                        with col2:
                            if st.form_submit_button("❌ Cancel", use_container_width=True):
                                del st.session_state[f"editing_{edit_key}"]
                                st.rerun()
                
                st.markdown("---")
