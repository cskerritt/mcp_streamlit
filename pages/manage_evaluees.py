#!/usr/bin/env python3
"""
Manage Evaluees Page - View and Delete Evaluees

This page provides functionality to view all evaluees in the database,
see their details, and delete them if needed.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from src.database import db
from src.auth import auth

def show_manage_evaluees_page():
    """Display the manage evaluees page."""
    st.title("👥 Manage Evaluees")
    st.markdown("View, edit, and delete evaluees from your database.")
    
    current_user = auth.get_current_user()
    if not current_user:
        st.error("Please log in to manage evaluees.")
        return
    
    user_id = current_user['id']
    
    try:
        # Get all evaluees for the current user
        evaluees = db.list_evaluees(user_id)
        
        if not evaluees:
            st.info("No evaluees found in your database.")
            st.markdown("👆 Use **Create/Edit Evaluee** to create your first evaluee.")
            return
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(evaluees)
        
        # Format dates for better display
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        if 'updated_at' in df.columns:
            df['updated_at'] = pd.to_datetime(df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Rename columns for better display
        display_columns = {
            'name': 'Evaluee Name',
            'current_age': 'Current Age',
            'birth_year': 'Birth Year',
            'table_count': 'Tables',
            'service_count': 'Services',
            'created_at': 'Created',
            'updated_at': 'Last Updated'
        }
        
        df_display = df.rename(columns=display_columns)
        
        # Display summary stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Evaluees", len(evaluees))
        with col2:
            total_tables = sum(e.get('table_count', 0) for e in evaluees)
            st.metric("Total Tables", total_tables)
        with col3:
            total_services = sum(e.get('service_count', 0) for e in evaluees)
            st.metric("Total Services", total_services)
        with col4:
            avg_age = sum(e.get('current_age', 0) for e in evaluees) / len(evaluees) if evaluees else 0
            st.metric("Average Age", f"{avg_age:.1f}")
        
        st.markdown("---")
        
        # Search and filter
        col1, col2 = st.columns([2, 1])
        with col1:
            search_term = st.text_input("🔍 Search evaluees by name:", "")
        with col2:
            sort_by = st.selectbox("Sort by:", ["Last Updated", "Name", "Age", "Created"])
        
        # Filter evaluees based on search
        filtered_evaluees = evaluees
        if search_term:
            filtered_evaluees = [e for e in evaluees if search_term.lower() in e['name'].lower()]
        
        # Sort evaluees
        sort_mapping = {
            "Last Updated": "updated_at",
            "Name": "name", 
            "Age": "current_age",
            "Created": "created_at"
        }
        sort_key = sort_mapping[sort_by]
        
        if sort_key in ["updated_at", "created_at"]:
            filtered_evaluees.sort(key=lambda x: x.get(sort_key, ""), reverse=True)
        elif sort_key == "name":
            filtered_evaluees.sort(key=lambda x: x.get(sort_key, "").lower())
        else:
            filtered_evaluees.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
        
        if not filtered_evaluees:
            st.warning(f"No evaluees found matching '{search_term}'")
            return
        
        st.markdown(f"### Found {len(filtered_evaluees)} evaluee(s)")
        
        # Display evaluees in expandable cards
        for i, evaluee in enumerate(filtered_evaluees):
            with st.expander(f"👤 {evaluee['name']} (Age: {evaluee['current_age']})", expanded=(i < 3)):
                
                # Create columns for info and actions
                info_col, action_col = st.columns([3, 1])
                
                with info_col:
                    # Basic info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Current Age", evaluee['current_age'])
                        if evaluee.get('birth_year'):
                            st.caption(f"Born: {evaluee['birth_year']}")
                    
                    with col2:
                        st.metric("Service Tables", evaluee.get('table_count', 0))
                        st.metric("Total Services", evaluee.get('service_count', 0))
                    
                    with col3:
                        if evaluee.get('created_at'):
                            created_date = pd.to_datetime(evaluee['created_at']).strftime('%Y-%m-%d %H:%M')
                            st.caption(f"Created: {created_date}")
                        if evaluee.get('updated_at'):
                            updated_date = pd.to_datetime(evaluee['updated_at']).strftime('%Y-%m-%d %H:%M')
                            st.caption(f"Updated: {updated_date}")
                
                with action_col:
                    st.markdown("**Actions:**")
                    
                    # Load button
                    if st.button(f"📂 Load", key=f"load_{evaluee['name']}_{i}", use_container_width=True):
                        try:
                            lcp_data = db.load_life_care_plan(evaluee['name'])
                            if lcp_data:
                                st.session_state.lcp_data = lcp_data
                                st.session_state.last_saved = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                st.success(f"✅ Loaded {evaluee['name']}")
                                st.rerun()
                            else:
                                st.error(f"Failed to load {evaluee['name']}")
                        except Exception as e:
                            st.error(f"Error loading {evaluee['name']}: {str(e)}")
                    
                    # Edit button (navigates to Create/Edit page)
                    if st.button(f"✏️ Edit", key=f"edit_{evaluee['name']}_{i}", use_container_width=True):
                        try:
                            lcp_data = db.load_life_care_plan(evaluee['name'])
                            if lcp_data:
                                st.session_state.lcp_data = lcp_data
                                st.session_state.last_saved = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                st.session_state.navigate_to = "👤 Create/Edit Evaluee"
                                st.rerun()
                            else:
                                st.error(f"Failed to load {evaluee['name']} for editing")
                        except Exception as e:
                            st.error(f"Error loading {evaluee['name']}: {str(e)}")
                    
                    # Copy button
                    copy_key = f"copy_{evaluee['name']}_{i}"
                    copy_name_key = f"copy_name_{evaluee['name']}_{i}"
                    copy_confirm_key = f"copy_confirm_{evaluee['name']}_{i}"
                    
                    if st.button(f"📋 Copy", key=copy_key, use_container_width=True):
                        st.session_state[copy_confirm_key] = True
                    
                    # Show copy dialog if copy was clicked
                    if st.session_state.get(copy_confirm_key, False):
                        st.markdown("**📋 Copy Life Care Plan**")
                        new_name = st.text_input(
                            "New name for copy:",
                            value=f"{evaluee['name']} - Copy",
                            key=copy_name_key
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Create Copy", key=f"confirm_copy_{evaluee['name']}_{i}", use_container_width=True):
                                if new_name and new_name.strip():
                                    try:
                                        current_user = auth.get_current_user()
                                        user_id = current_user['id'] if current_user else None
                                        
                                        if db.copy_life_care_plan(evaluee['name'], new_name.strip(), user_id):
                                            st.success(f"✅ Created copy: {new_name}")
                                            st.session_state[copy_confirm_key] = False
                                            st.rerun()
                                        else:
                                            st.error(f"Failed to copy plan. Name '{new_name}' may already exist.")
                                    except Exception as e:
                                        st.error(f"Error copying plan: {str(e)}")
                                else:
                                    st.error("Please enter a valid name for the copy")
                        
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_copy_{evaluee['name']}_{i}", use_container_width=True):
                                st.session_state[copy_confirm_key] = False
                                st.rerun()
                    
                    st.markdown("---")
                    
                    # Delete button with confirmation
                    delete_key = f"delete_{evaluee['name']}_{i}"
                    confirm_key = f"confirm_delete_{evaluee['name']}_{i}"
                    
                    if st.button(f"🗑️ Delete", key=delete_key, use_container_width=True, type="secondary"):
                        st.session_state[confirm_key] = True
                    
                    # Show confirmation if delete was clicked
                    if st.session_state.get(confirm_key, False):
                        st.warning(f"⚠️ Delete {evaluee['name']}?")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✅ Yes", key=f"yes_{evaluee['name']}_{i}", use_container_width=True):
                                try:
                                    db.delete_evaluee(evaluee['name'])
                                    
                                    # Clear from session if it's the current evaluee
                                    if (st.session_state.get('lcp_data') and 
                                        st.session_state.lcp_data.evaluee.name == evaluee['name']):
                                        keys_to_clear = ['lcp_data', 'current_table', 'show_calculations', 'last_saved']
                                        for key in keys_to_clear:
                                            if key in st.session_state:
                                                st.session_state[key] = None
                                    
                                    st.success(f"✅ Deleted {evaluee['name']}")
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting {evaluee['name']}: {str(e)}")
                        
                        with col2:
                            if st.button("❌ No", key=f"no_{evaluee['name']}_{i}", use_container_width=True):
                                st.session_state[confirm_key] = False
                                st.rerun()
        
        # Bulk actions
        st.markdown("---")
        st.markdown("### 🔧 Bulk Actions")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Delete All My Evaluees", type="secondary"):
                st.session_state.show_bulk_delete_confirm = True
        
        with col2:
            if st.button("📊 Export Evaluee List", type="secondary"):
                # Create CSV export of evaluee list
                export_df = pd.DataFrame(filtered_evaluees)
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"evaluees_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        # Bulk delete confirmation
        if st.session_state.get('show_bulk_delete_confirm', False):
            st.error("⚠️ **WARNING**: This will permanently delete ALL your evaluees and their data!")
            st.markdown("This action cannot be undone. Type 'DELETE ALL' to confirm:")
            
            confirm_text = st.text_input("Confirmation:", "")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Confirm Delete All") and confirm_text == "DELETE ALL":
                    try:
                        # Delete all evaluees for this user
                        for evaluee in evaluees:
                            db.delete_evaluee(evaluee['name'])
                        
                        # Clear session state safely
                        keys_to_clear = ['lcp_data', 'current_table', 'show_calculations', 'last_saved']
                        for key in keys_to_clear:
                            if key in st.session_state:
                                st.session_state[key] = None
                        st.session_state.show_bulk_delete_confirm = False
                        
                        st.success("✅ All evaluees deleted successfully")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during bulk delete: {str(e)}")
            
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.show_bulk_delete_confirm = False
                    st.rerun()
    
    except Exception as e:
        st.error(f"Error loading evaluees: {str(e)}")
        st.info("Please try refreshing the page or contact support if the issue persists.")

if __name__ == "__main__":
    show_manage_evaluees_page()