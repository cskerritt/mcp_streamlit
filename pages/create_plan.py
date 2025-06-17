"""
Create/Edit Evaluee Page for Streamlit Life Care Plan Application
"""

import streamlit as st
from datetime import datetime
from src.models import LifeCarePlan, Evaluee, ProjectionSettings
from src.database import db
from src.auth import auth

def show_create_plan_page():
    """Display the create/edit evaluee page."""
    st.title("👤 Create/Edit Evaluee")
    st.markdown("Create a new life care plan or edit the current evaluee information.")
    
    # Check if we have existing data
    has_existing_data = st.session_state.lcp_data is not None
    
    if has_existing_data:
        st.info(f"Currently editing: **{st.session_state.lcp_data.evaluee.name}**")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🆕 Create New Plan Instead", use_container_width=True):
                st.session_state.lcp_data = None
                st.rerun()
    
    # Form for evaluee information
    with st.form("evaluee_form"):
        st.subheader("Evaluee Information")
        
        # Pre-fill with existing data if available
        default_name = st.session_state.lcp_data.evaluee.name if has_existing_data else ""
        default_age = st.session_state.lcp_data.evaluee.current_age if has_existing_data else 35.0
        default_discount = st.session_state.lcp_data.evaluee.discount_calculations if has_existing_data else True
        
        name = st.text_input(
            "Evaluee Name *",
            value=default_name,
            placeholder="Enter the full name of the person receiving care",
            help="This is the person for whom the life care plan is being created."
        )
        
        age = st.number_input(
            "Current Age *",
            min_value=0.1,
            max_value=120.0,
            value=default_age,
            step=0.1,
            help="Current age of the evaluee in years (can include decimals for months)."
        )
        
        discount_calculations = st.checkbox(
            "Enable Present Value Calculations",
            value=default_discount,
            help="When enabled, costs will be discounted to present value using the discount rate."
        )
        
        st.subheader("Projection Settings")
        
        # Pre-fill projection settings if available
        default_base_year = st.session_state.lcp_data.settings.base_year if has_existing_data else datetime.now().year
        default_projection_years = st.session_state.lcp_data.settings.projection_years if has_existing_data else 30.0
        default_discount_rate = st.session_state.lcp_data.settings.discount_rate if has_existing_data else 0.035
        
        col1, col2 = st.columns(2)
        
        with col1:
            base_year = st.number_input(
                "Base Year *",
                min_value=2020,
                max_value=2050,
                value=default_base_year,
                step=1,
                help="The starting year for cost projections."
            )
            
            projection_years = st.number_input(
                "Projection Period (Years) *",
                min_value=1.0,
                max_value=100.0,
                value=default_projection_years,
                step=1.0,
                help="Number of years to project costs into the future."
            )
        
        with col2:
            discount_rate = st.number_input(
                "Discount Rate *",
                min_value=0.0,
                max_value=0.20,
                value=default_discount_rate,
                step=0.001,
                format="%.3f",
                help="Annual discount rate for present value calculations (as decimal, e.g., 0.035 = 3.5%)."
            )
            
            # Show discount rate as percentage
            st.caption(f"Discount Rate: {discount_rate:.1%}")
        
        # Form submission
        submitted = st.form_submit_button("💾 Save Evaluee Information", use_container_width=True)
        
        if submitted:
            if not name.strip():
                st.error("Please enter the evaluee's name.")
                return
            
            try:
                # Create evaluee and settings
                evaluee = Evaluee(
                    name=name.strip(),
                    current_age=age,
                    discount_calculations=discount_calculations
                )
                
                settings = ProjectionSettings(
                    base_year=base_year,
                    projection_years=projection_years,
                    discount_rate=discount_rate
                )
                
                # Create or update life care plan
                if has_existing_data:
                    # Update existing plan
                    st.session_state.lcp_data.evaluee = evaluee
                    st.session_state.lcp_data.settings = settings
                    st.success(f"✅ Updated evaluee information for {name}")
                else:
                    # Create new plan
                    st.session_state.lcp_data = LifeCarePlan(evaluee=evaluee, settings=settings)
                    st.success(f"✅ Created new life care plan for {name}")

                # Auto-save to database if enabled
                if st.session_state.get('auto_save', True):
                    try:
                        current_user = auth.get_current_user()
                        user_id = current_user['id'] if current_user else None
                        db.save_life_care_plan(st.session_state.lcp_data, user_id)
                        st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
                        st.info("💾 Auto-saved to database")
                    except Exception as e:
                        st.warning(f"Auto-save failed: {str(e)}")

                # Show next steps
                st.info("**Next Steps:** Go to 'Manage Service Tables' to add medical services and costs.")
                
            except ValueError as e:
                st.error(f"Validation error: {str(e)}")
            except Exception as e:
                st.error(f"Error creating evaluee: {str(e)}")
    
    # Show current plan summary if available
    if st.session_state.lcp_data:
        st.markdown("---")
        st.subheader("📋 Current Plan Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Evaluee", st.session_state.lcp_data.evaluee.name)
            st.metric("Current Age", f"{st.session_state.lcp_data.evaluee.current_age} years")
        
        with col2:
            st.metric("Base Year", st.session_state.lcp_data.settings.base_year)
            st.metric("Projection Period", f"{st.session_state.lcp_data.settings.projection_years} years")
        
        with col3:
            st.metric("Discount Rate", f"{st.session_state.lcp_data.settings.discount_rate:.1%}")
            st.metric("Present Value Calcs", "Enabled" if st.session_state.lcp_data.evaluee.discount_calculations else "Disabled")
        
        # Show projection period details
        end_year = st.session_state.lcp_data.settings.base_year + int(st.session_state.lcp_data.settings.projection_years)
        final_age = st.session_state.lcp_data.evaluee.current_age + st.session_state.lcp_data.settings.projection_years
        
        st.info(f"**Projection Period:** {st.session_state.lcp_data.settings.base_year} - {end_year} (Age {st.session_state.lcp_data.evaluee.current_age} - {final_age:.1f})")
        
        # Show service tables summary
        if st.session_state.lcp_data.tables:
            st.markdown("### Service Tables")
            for table_name, table in st.session_state.lcp_data.tables.items():
                st.write(f"• **{table_name}**: {len(table.services)} services")
        else:
            st.warning("No service tables created yet. Go to 'Manage Service Tables' to add services.")
    
    # Help section
    with st.expander("ℹ️ Help & Guidelines"):
        st.markdown("""
        **Evaluee Information:**
        - **Name**: Full name of the person receiving care
        - **Age**: Current age (can include decimals for precise age in months)
        - **Present Value Calculations**: Enable to discount future costs to present value
        
        **Projection Settings:**
        - **Base Year**: Starting year for projections (usually current year)
        - **Projection Period**: How many years into the future to project costs
        - **Discount Rate**: Annual rate for present value calculations (typically 2-5%)
        
        **Common Discount Rates:**
        - Conservative: 2.0% - 3.0%
        - Moderate: 3.0% - 4.0%
        - Aggressive: 4.0% - 5.0%
        """)
