"""
Calculate & View Results Page for Streamlit Life Care Plan Application
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.calculator import CostCalculator

def show_calculate_results_page():
    """Display the calculate and view results page."""
    st.title("🧮 Calculate & View Results")
    
    # Check if we have a life care plan with services
    if not st.session_state.lcp_data:
        st.warning("⚠️ Please create an evaluee first.")
        if st.button("👤 Go to Create Evaluee"):
            st.session_state.page = "👤 Create/Edit Evaluee"
            st.rerun()
        return
    
    if not st.session_state.lcp_data.tables:
        st.warning("⚠️ Please add service tables first.")
        if st.button("📋 Go to Manage Services"):
            st.session_state.page = "📋 Manage Service Tables"
            st.rerun()
        return
    
    # Check if there are any services
    total_services = sum(len(table.services) for table in st.session_state.lcp_data.tables.values())
    if total_services == 0:
        st.warning("⚠️ Please add services to your tables first.")
        if st.button("📋 Go to Manage Services"):
            st.session_state.page = "📋 Manage Service Tables"
            st.rerun()
        return
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"Calculating costs for: **{st.session_state.lcp_data.evaluee.name}**")
    with col2:
        if st.button("🔄 Refresh Calculations", key="refresh_calc"):
            st.rerun()
    
    try:
        # Create calculator
        calculator = CostCalculator(st.session_state.lcp_data)
        
        # Calculate results
        with st.spinner("Calculating costs..."):
            cost_schedule = calculator.build_cost_schedule()
            summary_stats = calculator.calculate_summary_statistics()
            category_costs = calculator.get_cost_by_category()
        
        # Display results in tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary", "📈 Charts", "📋 Cost Schedule", "🏷️ By Category"])
        
        with tab1:
            show_summary_tab(summary_stats, cost_schedule)
        
        with tab2:
            show_charts_tab(cost_schedule)
        
        with tab3:
            show_cost_schedule_tab(cost_schedule)
        
        with tab4:
            show_category_tab(category_costs)
            
    except Exception as e:
        st.error(f"Error calculating costs: {str(e)}")
        with st.expander("📋 Error Details", expanded=False):
            st.exception(e)
        
        # Provide helpful suggestions
        st.markdown("### Possible Solutions:")
        st.markdown("- Check that all services have valid cost and frequency values")
        st.markdown("- Ensure projection settings are properly configured")
        st.markdown("- Try refreshing the page or reloading the evaluee data")
        
        if st.button("🏠 Return to Home", key="error_home"):
            st.session_state.page = "🏠 Home"
            st.rerun()

def show_summary_tab(summary_stats, cost_schedule):
    """Show summary statistics."""
    st.subheader("📊 Executive Summary")
    
    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Nominal Cost",
            f"${summary_stats['total_nominal_cost']:,.0f}",
            help="Total cost over the projection period without discounting"
        )
    
    with col2:
        st.metric(
            "Average Annual Cost",
            f"${summary_stats['average_annual_cost']:,.0f}",
            help="Average cost per year over the projection period"
        )
    
    with col3:
        if st.session_state.lcp_data.evaluee.discount_calculations:
            st.metric(
                "Total Present Value",
                f"${summary_stats['total_present_value']:,.0f}",
                help="Total cost discounted to present value"
            )
        else:
            st.metric(
                "Present Value", 
                "Disabled", 
                help="Present value calculations are disabled for this evaluee. Enable them in the evaluee settings."
            )
            st.warning("⚠️ Present value calculations are disabled. Enable them in the Create/Edit Evaluee page to see discounted costs.")
            if st.button("🔧 Enable Present Value Calculations", key="enable_pv_calc"):
                st.session_state.page = "👤 Create/Edit Evaluee"
                st.rerun()
    
    with col4:
        st.metric(
            "Projection Period",
            f"{st.session_state.lcp_data.settings.projection_years:.0f} years",
            help=f"From {st.session_state.lcp_data.settings.base_year} to {st.session_state.lcp_data.settings.base_year + int(st.session_state.lcp_data.settings.projection_years)}"
        )
    
    # Additional details
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Plan Details")
        st.write(f"**Evaluee:** {st.session_state.lcp_data.evaluee.name}")
        st.write(f"**Current Age:** {st.session_state.lcp_data.evaluee.current_age} years")
        st.write(f"**Base Year:** {st.session_state.lcp_data.settings.base_year}")
        st.write(f"**Discount Rate:** {st.session_state.lcp_data.settings.discount_rate:.1%}")
        
        # Calculate final age
        final_age = st.session_state.lcp_data.evaluee.current_age + st.session_state.lcp_data.settings.projection_years
        st.write(f"**Age at End:** {final_age:.1f} years")
    
    with col2:
        st.markdown("### Service Summary")
        total_tables = len(st.session_state.lcp_data.tables)
        total_services = sum(len(table.services) for table in st.session_state.lcp_data.tables.values())
        
        st.write(f"**Service Tables:** {total_tables}")
        st.write(f"**Total Services:** {total_services}")
        
        # Show table breakdown
        for table_name, table in st.session_state.lcp_data.tables.items():
            st.write(f"• {table_name}: {len(table.services)} services")
    
    # Cost breakdown by year ranges
    if len(cost_schedule) > 0:
        st.markdown("---")
        st.markdown("### Cost Distribution by Period")
        
        # Split into periods (e.g., 5-year chunks)
        years_per_period = 5
        periods = []
        
        for i in range(0, len(cost_schedule), years_per_period):
            period_data = cost_schedule.iloc[i:i+years_per_period]
            start_year = period_data['Year'].min()
            end_year = period_data['Year'].max()
            
            period_nominal = period_data['Total Nominal'].sum()
            period_pv = period_data['Present Value'].sum() if 'Present Value' in period_data.columns else 0
            
            periods.append({
                'Period': f"{start_year}-{end_year}",
                'Nominal Cost': period_nominal,
                'Present Value': period_pv if st.session_state.lcp_data.evaluee.discount_calculations else None
            })
        
        periods_df = pd.DataFrame(periods)
        
        # Format for display
        periods_df['Nominal Cost'] = periods_df['Nominal Cost'].apply(lambda x: f"${x:,.0f}")
        if st.session_state.lcp_data.evaluee.discount_calculations:
            periods_df['Present Value'] = periods_df['Present Value'].apply(lambda x: f"${x:,.0f}")
        else:
            periods_df = periods_df.drop('Present Value', axis=1)
        
        st.dataframe(periods_df, use_container_width=True, hide_index=True)

def show_charts_tab(cost_schedule):
    """Show interactive charts."""
    st.subheader("📈 Cost Projections")
    
    if len(cost_schedule) == 0:
        st.warning("No cost data to display.")
        return
    
    # Chart selection
    chart_type = st.selectbox(
        "Select Chart Type",
        ["Annual Costs", "Cumulative Costs", "Cost Comparison"]
    )
    
    if chart_type == "Annual Costs":
        show_annual_costs_chart(cost_schedule)
    elif chart_type == "Cumulative Costs":
        show_cumulative_costs_chart(cost_schedule)
    else:
        show_cost_comparison_chart(cost_schedule)

def show_annual_costs_chart(cost_schedule):
    """Show annual costs chart."""
    fig = go.Figure()
    
    # Add nominal costs
    fig.add_trace(go.Bar(
        x=cost_schedule['Year'],
        y=cost_schedule['Total Nominal'],
        name='Nominal Cost',
        marker_color='lightblue',
        hovertemplate='<b>Year %{x}</b><br>Nominal Cost: $%{y:,.0f}<extra></extra>'
    ))
    
    # Add present value if available
    if 'Present Value' in cost_schedule.columns and st.session_state.lcp_data.evaluee.discount_calculations:
        fig.add_trace(go.Bar(
            x=cost_schedule['Year'],
            y=cost_schedule['Present Value'],
            name='Present Value',
            marker_color='darkblue',
            hovertemplate='<b>Year %{x}</b><br>Present Value: $%{y:,.0f}<extra></extra>'
        ))
    
    fig.update_layout(
        title='Annual Medical Costs by Year',
        xaxis_title='Year',
        yaxis_title='Cost ($)',
        template='plotly_white',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_cumulative_costs_chart(cost_schedule):
    """Show cumulative costs chart."""
    # Calculate cumulative costs
    cost_schedule_copy = cost_schedule.copy()
    cost_schedule_copy['Cumulative Nominal'] = cost_schedule_copy['Total Nominal'].cumsum()
    
    if 'Present Value' in cost_schedule_copy.columns:
        cost_schedule_copy['Cumulative PV'] = cost_schedule_copy['Present Value'].cumsum()
    
    fig = go.Figure()
    
    # Add cumulative nominal
    fig.add_trace(go.Scatter(
        x=cost_schedule_copy['Year'],
        y=cost_schedule_copy['Cumulative Nominal'],
        mode='lines+markers',
        name='Cumulative Nominal',
        line=dict(color='red', width=3),
        hovertemplate='<b>Year %{x}</b><br>Cumulative Nominal: $%{y:,.0f}<extra></extra>'
    ))
    
    # Add cumulative present value if available
    if 'Cumulative PV' in cost_schedule_copy.columns and st.session_state.lcp_data.evaluee.discount_calculations:
        fig.add_trace(go.Scatter(
            x=cost_schedule_copy['Year'],
            y=cost_schedule_copy['Cumulative PV'],
            mode='lines+markers',
            name='Cumulative Present Value',
            line=dict(color='blue', width=3),
            hovertemplate='<b>Year %{x}</b><br>Cumulative PV: $%{y:,.0f}<extra></extra>'
        ))
    
    fig.update_layout(
        title='Cumulative Medical Costs Over Time',
        xaxis_title='Year',
        yaxis_title='Cumulative Cost ($)',
        template='plotly_white',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_cost_comparison_chart(cost_schedule):
    """Show nominal vs present value comparison."""
    if not st.session_state.lcp_data.evaluee.discount_calculations or 'Present Value' not in cost_schedule.columns:
        st.warning("Present value calculations are disabled. Enable them in the evaluee settings to see this comparison.")
        return
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=cost_schedule['Year'],
        y=cost_schedule['Total Nominal'],
        mode='lines+markers',
        name='Nominal Cost',
        line=dict(color='red', width=2),
        hovertemplate='<b>Year %{x}</b><br>Nominal: $%{y:,.0f}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=cost_schedule['Year'],
        y=cost_schedule['Present Value'],
        mode='lines+markers',
        name='Present Value',
        line=dict(color='blue', width=2),
        hovertemplate='<b>Year %{x}</b><br>Present Value: $%{y:,.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        title='Nominal Cost vs Present Value Comparison',
        xaxis_title='Year',
        yaxis_title='Cost ($)',
        template='plotly_white',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_cost_schedule_tab(cost_schedule):
    """Show detailed cost schedule table."""
    st.subheader("📋 Detailed Cost Schedule")
    
    if len(cost_schedule) == 0:
        st.warning("No cost data to display.")
        return
    
    # Format the dataframe for display
    display_df = cost_schedule.copy()
    
    # Format monetary columns
    monetary_columns = [col for col in display_df.columns if col not in ['Year', 'Age']]
    for col in monetary_columns:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
    
    # Format age
    if 'Age' in display_df.columns:
        display_df['Age'] = display_df['Age'].apply(lambda x: f"{x:.1f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Download button
    csv = cost_schedule.to_csv(index=False)
    st.download_button(
        label="📥 Download Cost Schedule (CSV)",
        data=csv,
        file_name=f"{st.session_state.lcp_data.evaluee.name.replace(' ', '_')}_cost_schedule.csv",
        mime="text/csv"
    )

def show_category_tab(category_costs):
    """Show costs broken down by category."""
    st.subheader("🏷️ Costs by Service Category")
    
    if not category_costs:
        st.warning("No category data to display.")
        return
    
    # Create DataFrame from category costs
    category_data = []
    for category, costs in category_costs.items():
        row = {
            'Category': category,
            'Nominal Total': costs['table_nominal_total'],
            'Services Count': len(costs.get('services', []))
        }

        if st.session_state.lcp_data.evaluee.discount_calculations:
            row['Present Value Total'] = costs['table_present_value_total']

        category_data.append(row)
    
    category_df = pd.DataFrame(category_data)
    
    # Sort by nominal total
    category_df = category_df.sort_values('Nominal Total', ascending=False)
    
    # Display metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Category Breakdown")
        for _, row in category_df.iterrows():
            st.metric(
                row['Category'],
                f"${row['Nominal Total']:,.0f}",
                delta=f"{row['Services Count']} services"
            )
    
    with col2:
        # Pie chart
        fig = px.pie(
            category_df,
            values='Nominal Total',
            names='Category',
            title='Cost Distribution by Category'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table
    st.markdown("### Detailed Category Costs")
    
    # Format for display
    display_category_df = category_df.copy()
    display_category_df['Nominal Total'] = display_category_df['Nominal Total'].apply(lambda x: f"${x:,.2f}")
    
    if 'Present Value Total' in display_category_df.columns:
        display_category_df['Present Value Total'] = display_category_df['Present Value Total'].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(display_category_df, use_container_width=True, hide_index=True)
