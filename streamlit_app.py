#!/usr/bin/env python3
"""
Life Care Plan Table Generator - Streamlit Web Application

This is the main Streamlit application for the Life Care Plan economic analysis tool.
It provides an interactive web interface for creating, managing, and exporting 
life care plan cost projections.
"""

import streamlit as st
from datetime import datetime

# Import core modules
from src.models import LifeCarePlan, Evaluee, ProjectionSettings, ServiceTable, Service
from src.database import db
from src.auth import auth

# Configure Streamlit page
st.set_page_config(
    page_title="Life Care Plan Table Generator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
def initialize_session_state():
    """Initialize session state variables."""
    if 'lcp_data' not in st.session_state:
        st.session_state.lcp_data = None
    if 'current_table' not in st.session_state:
        st.session_state.current_table = None
    if 'show_calculations' not in st.session_state:
        st.session_state.show_calculations = False
    if 'auto_save' not in st.session_state:
        st.session_state.auto_save = True
    if 'last_saved' not in st.session_state:
        st.session_state.last_saved = None

def create_sidebar():
    """Create the sidebar navigation."""
    st.sidebar.title("🏥 Life Care Plan Generator")

    # Show user info and logout button
    current_user = auth.get_current_user()
    if current_user:
        st.sidebar.success(f"👤 **Welcome, {current_user.get('full_name', current_user['username'])}**")

        col1, col2 = st.sidebar.columns([2, 1])
        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                auth.logout()
                st.rerun()

    st.sidebar.markdown("---")

    # Auto-save toggle
    st.session_state.auto_save = st.sidebar.checkbox(
        "🔄 Auto-save to Database",
        value=st.session_state.auto_save,
        help="Automatically save changes to the database"
    )

    # Show current evaluee info if available
    if st.session_state.lcp_data:
        st.sidebar.success(f"**Current Plan:** {st.session_state.lcp_data.evaluee.name}")
        st.sidebar.info(f"Age: {st.session_state.lcp_data.evaluee.current_age}")
        st.sidebar.info(f"Tables: {len(st.session_state.lcp_data.tables)}")

        # Show last saved time
        if st.session_state.last_saved:
            st.sidebar.caption(f"Last saved: {st.session_state.last_saved}")

        # Manual save button
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("💾 Save", help="Save current plan to database"):
                save_to_database()

        with col2:
            if st.button("🗑️ Clear", help="Clear current plan from memory"):
                st.session_state.lcp_data = None
                st.session_state.current_table = None
                st.session_state.show_calculations = False
                st.session_state.last_saved = None
                st.rerun()
    else:
        st.sidebar.warning("No life care plan loaded")
    
    st.sidebar.markdown("---")

    # Database section
    st.sidebar.subheader("📂 Database")

    # Load from database
    try:
        current_user = auth.get_current_user()
        user_id = current_user['id'] if current_user else None
        evaluees = db.list_evaluees(user_id)
        if evaluees:
            evaluee_names = [e['name'] for e in evaluees]
            selected_evaluee = st.sidebar.selectbox(
                "Load from Database:",
                [""] + evaluee_names,
                help="Select an evaluee to load from database"
            )

            if selected_evaluee and selected_evaluee != "":
                if st.sidebar.button(f"📂 Load {selected_evaluee}"):
                    load_from_database(selected_evaluee)
        else:
            st.sidebar.info("No saved plans in database")
    except Exception as e:
        st.sidebar.error(f"Database error: {str(e)}")

    st.sidebar.markdown("---")

    # Navigation menu
    page_options = [
        "🏠 Home",
        "👤 Create/Edit Evaluee",
        "📋 Manage Service Tables",
        "🧮 Calculate & View Results",
        "📊 Export Reports",
        "💾 Load/Save Configurations"
    ]

    return st.sidebar.selectbox("Navigate to:", page_options)

def show_home_page():
    """Display the home page."""
    st.title("🏥 Life Care Plan Table Generator")
    st.markdown("### Interactive Economic Analysis Tool")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        Welcome to the Life Care Plan Table Generator! This tool helps you create comprehensive 
        economic projections for medical care costs over time.
        
        **Key Features:**
        - 📊 **Flexible Service Modeling**: Support for recurring and discrete occurrence services
        - 💰 **Economic Calculations**: Built-in inflation adjustment and present value calculations
        - 📄 **Multiple Export Formats**: Export to Excel, Word, and PDF formats
        - 🔧 **Interactive Interface**: Easy-to-use web interface for all operations
        - 💾 **Configuration Management**: Save and load life care plan configurations
        
        **Getting Started:**
        1. Create a new evaluee (person receiving care)
        2. Add service tables and medical services
        3. Calculate costs and view projections
        4. Export professional reports
        """)
        
        # Quick start buttons
        st.markdown("### Quick Start")
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            if st.button("🆕 Create New Plan", use_container_width=True):
                st.session_state.page = "👤 Create/Edit Evaluee"
                st.rerun()
        
        with col_b:
            if st.button("📂 Load Sample Data", use_container_width=True):
                load_sample_data()
                st.rerun()
        
        with col_c:
            if st.button("📁 Load Configuration", use_container_width=True):
                st.session_state.page = "💾 Load/Save Configurations"
                st.rerun()
    
    with col2:
        st.markdown("### Current Status")
        if st.session_state.lcp_data:
            st.success("✅ Life Care Plan Loaded")
            st.info(f"**Evaluee:** {st.session_state.lcp_data.evaluee.name}")
            st.info(f"**Age:** {st.session_state.lcp_data.evaluee.current_age}")
            st.info(f"**Base Year:** {st.session_state.lcp_data.settings.base_year}")
            st.info(f"**Projection Years:** {st.session_state.lcp_data.settings.projection_years}")
            st.info(f"**Service Tables:** {len(st.session_state.lcp_data.tables)}")

            total_services = sum(len(table.services) for table in st.session_state.lcp_data.tables.values())
            st.info(f"**Total Services:** {total_services}")

            # Show last saved status
            if st.session_state.get('last_saved'):
                st.info(f"**Last Saved:** {st.session_state.last_saved}")

            if total_services > 0:
                if st.button("🧮 Calculate Costs", use_container_width=True):
                    st.session_state.page = "🧮 Calculate & View Results"
                    st.rerun()
        else:
            st.warning("⚠️ No Plan Loaded")
            st.markdown("Create a new plan or load an existing configuration to get started.")

        # Database status
        st.markdown("### Database Status")
        try:
            current_user = auth.get_current_user()
            user_id = current_user['id'] if current_user else None
            evaluees = db.list_evaluees(user_id)
            st.info(f"**Your Saved Plans:** {len(evaluees)}")
            if st.session_state.get('auto_save', True):
                st.success("🔄 Auto-save: ON")
            else:
                st.warning("🔄 Auto-save: OFF")
        except Exception as e:
            st.error(f"Database Error: {str(e)}")

def save_to_database():
    """Save current life care plan to database."""
    if not st.session_state.lcp_data:
        st.error("No life care plan to save")
        return

    try:
        current_user = auth.get_current_user()
        user_id = current_user['id'] if current_user else None
        db.save_life_care_plan(st.session_state.lcp_data, user_id)
        st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
        st.success(f"✅ Saved {st.session_state.lcp_data.evaluee.name} to database")
    except Exception as e:
        st.error(f"Error saving to database: {str(e)}")

def auto_save_if_enabled():
    """Auto-save to database if enabled."""
    if st.session_state.auto_save and st.session_state.lcp_data:
        try:
            current_user = auth.get_current_user()
            user_id = current_user['id'] if current_user else None
            db.save_life_care_plan(st.session_state.lcp_data, user_id)
            st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            st.error(f"Auto-save failed: {str(e)}")

def load_from_database(evaluee_name):
    """Load a life care plan from database."""
    try:
        lcp = db.load_life_care_plan(evaluee_name)
        if lcp:
            st.session_state.lcp_data = lcp
            st.session_state.last_saved = datetime.now().strftime("%H:%M:%S")
            st.success(f"✅ Loaded {evaluee_name} from database")
            st.rerun()
        else:
            st.error(f"Could not load {evaluee_name} from database")
    except Exception as e:
        st.error(f"Error loading from database: {str(e)}")

def load_sample_data():
    """Load sample data for demonstration."""
    try:
        # Create sample evaluee
        evaluee = Evaluee(name="Jane Doe (Sample)", current_age=35, discount_calculations=True)
        settings = ProjectionSettings(base_year=2025, projection_years=30, discount_rate=0.035)
        lcp = LifeCarePlan(evaluee=evaluee, settings=settings)
        
        # Add sample physician evaluation table
        physician_table = ServiceTable(name="Physician Evaluation")
        physician_table.add_service(Service(
            name="Initial Neurological Evaluation",
            inflation_rate=0.027,
            unit_cost=500.00,
            frequency_per_year=1,
            start_year=2025,
            end_year=2025
        ))
        physician_table.add_service(Service(
            name="Annual Follow-up Visits",
            inflation_rate=0.027,
            unit_cost=300.00,
            frequency_per_year=2,
            start_year=2026,
            end_year=2054
        ))
        lcp.add_table(physician_table)
        
        # Add sample medications table
        medication_table = ServiceTable(name="Medications")
        medication_table.add_service(Service(
            name="Anti-Spasticity Medication",
            inflation_rate=0.05,
            unit_cost=300.00,
            frequency_per_year=12,
            start_year=2025,
            end_year=2054
        ))
        lcp.add_table(medication_table)
        
        # Add sample surgery table
        surgery_table = ServiceTable(name="Surgeries")
        surgery_table.add_service(Service(
            name="Spinal Fusion Surgery",
            inflation_rate=0.05,
            unit_cost=75000.00,
            frequency_per_year=1,
            occurrence_years=[2027, 2045]
        ))
        lcp.add_table(surgery_table)
        
        st.session_state.lcp_data = lcp

        # Auto-save if enabled
        auto_save_if_enabled()

        st.success("✅ Sample data loaded successfully!")

    except Exception as e:
        st.error(f"Error loading sample data: {str(e)}")

def main():
    """Main application function."""
    # Check authentication first
    if not auth.is_authenticated():
        auth.show_login_page()
        return

    # Validate session
    if not auth.validate_session():
        return

    initialize_session_state()

    # Create sidebar and get selected page
    if 'page' not in st.session_state:
        st.session_state.page = "🏠 Home"

    selected_page = create_sidebar()
    if selected_page != st.session_state.page:
        st.session_state.page = selected_page
        st.rerun()

    # Display selected page
    if st.session_state.page == "🏠 Home":
        show_home_page()
    elif st.session_state.page == "👤 Create/Edit Evaluee":
        from pages.create_plan import show_create_plan_page
        show_create_plan_page()
    elif st.session_state.page == "📋 Manage Service Tables":
        from pages.manage_services import show_manage_services_page
        show_manage_services_page()
    elif st.session_state.page == "🧮 Calculate & View Results":
        from pages.calculate_results import show_calculate_results_page
        show_calculate_results_page()
    elif st.session_state.page == "📊 Export Reports":
        from pages.export_reports import show_export_reports_page
        show_export_reports_page()
    elif st.session_state.page == "💾 Load/Save Configurations":
        from pages.load_save import show_load_save_page
        show_load_save_page()

if __name__ == "__main__":
    main()
