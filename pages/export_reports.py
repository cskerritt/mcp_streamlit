"""
Export Reports Page for Streamlit Life Care Plan Application
"""

import streamlit as st
import tempfile
import os
from datetime import datetime
from src.calculator import CostCalculator
from src.exporters import ExcelExporter, WordExporter, PDFExporter
from src.database import db

def show_export_reports_page():
    """Display the export reports page."""
    st.title("📊 Export Reports")
    
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
    
    st.markdown(f"Export reports for: **{st.session_state.lcp_data.evaluee.name}**")
    
    # Show scenario information
    has_multiple_scenarios = len(st.session_state.lcp_data.scenarios) > 1
    if has_multiple_scenarios:
        current_scenario = st.session_state.lcp_data.get_current_scenario()
        st.info(f"📋 **Current Scenario:** {current_scenario.name if current_scenario else 'None'} | **Total Scenarios:** {len(st.session_state.lcp_data.scenarios)}")
    
    # Create calculator for exports
    try:
        calculator = CostCalculator(st.session_state.lcp_data)
        
        # Multi-scenario export options
        if has_multiple_scenarios:
            st.subheader("🎭 Multi-Scenario Export Options")
            
            # Initialize export mode if not set
            if 'export_mode' not in st.session_state:
                st.session_state.export_mode = "single"
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📊 Single Scenario Mode", 
                           disabled=(st.session_state.export_mode == "single"),
                           key="single_mode", 
                           use_container_width=True):
                    st.session_state.export_mode = "single"
                    st.rerun()
                
                if st.session_state.export_mode == "single":
                    st.success(f"✅ Exporting: **{current_scenario.name if current_scenario else 'Unknown'}**")
                else:
                    st.markdown(f"Export current scenario: **{current_scenario.name if current_scenario else 'Unknown'}**")
                
            with col2:
                if st.button("🔄 Multi-Scenario Mode", 
                           disabled=(st.session_state.export_mode == "multi"),
                           key="multi_mode", 
                           use_container_width=True):
                    st.session_state.export_mode = "multi"
                    st.rerun()
                
                if st.session_state.export_mode == "multi":
                    st.success(f"✅ Exporting: **All {len(st.session_state.lcp_data.scenarios)} scenarios**")
                else:
                    st.markdown(f"Export all {len(st.session_state.lcp_data.scenarios)} scenarios with comparison tables")
            
            st.markdown("---")
        else:
            st.session_state.export_mode = "single"
        
        # Plan protection section
        st.subheader("🛡️ Plan Protection")
        st.markdown("Before exporting, you can create a copy of this plan to prevent accidental modifications.")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            copy_name = st.text_input(
                "Create a copy with name:",
                value=f"{st.session_state.lcp_data.evaluee.name} - Export Copy",
                help="Create a copy of the current plan before making changes"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Add spacing to align button
            if st.button("📋 Create Copy", use_container_width=True):
                if copy_name and copy_name.strip():
                    try:
                        from src.auth import auth
                        current_user = auth.get_current_user()
                        user_id = current_user['id'] if current_user else None
                        
                        # Create copy using the database method
                        if db.copy_life_care_plan(st.session_state.lcp_data.evaluee.name, copy_name.strip(), user_id):
                            st.success(f"✅ Created copy: {copy_name}")
                        else:
                            st.error(f"Failed to copy plan. Name '{copy_name}' may already exist.")
                    except Exception as e:
                        st.error(f"Error copying plan: {str(e)}")
                else:
                    st.error("Please enter a valid name for the copy")
        
        st.markdown("---")
        
        # Export options
        st.subheader("📄 Available Export Formats")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 📊 Excel Export")
            st.markdown("""
            **Includes:**
            - Cost schedule by year
            - Summary statistics
            - Service details
            - Category breakdown
            """)
            
            include_all_scenarios = has_multiple_scenarios and st.session_state.get('export_mode') == 'multi'
            if st.button("📊 Export to Excel", use_container_width=True):
                export_to_excel(calculator, include_all_scenarios)
        
        with col2:
            st.markdown("### 📝 Word Document")
            st.markdown("""
            **Includes:**
            - Executive summary
            - Cost breakdown by category
            - Detailed cost schedule
            - Professional formatting
            """)
            
            if st.button("📝 Export to Word", use_container_width=True):
                export_to_word(calculator, include_all_scenarios)
        
        with col3:
            st.markdown("### 📄 PDF Report")
            st.markdown("""
            **Includes:**
            - Professional report format
            - Summary statistics
            - Category breakdown
            - Detailed cost schedule
            """)
            
            if st.button("📄 Export to PDF", use_container_width=True):
                export_to_pdf(calculator)
        
        # Bulk export option
        st.markdown("---")
        st.subheader("📦 Bulk Export")
        st.markdown("Export all formats at once as a ZIP file.")
        
        if st.button("📦 Export All Formats", use_container_width=True):
            export_all_formats(calculator)
        
        # Preview section
        st.markdown("---")
        st.subheader("👁️ Report Preview")
        
        with st.expander("Preview Report Content", expanded=False):
            show_report_preview(calculator)
            
    except Exception as e:
        st.error(f"Error preparing exports: {str(e)}")
        st.exception(e)

def export_to_excel(calculator, include_all_scenarios=False):
    """Export to Excel format."""
    try:
        with st.spinner("Generating Excel report..."):
            # Create temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            evaluee_name = st.session_state.lcp_data.evaluee.name.replace(" ", "_")
            
            if include_all_scenarios:
                filename = f"{evaluee_name}_LCP_MultiScenario_{timestamp}.xlsx"
                export_label = "📥 Download Multi-Scenario Excel Report"
                success_msg = "✅ Multi-scenario Excel report generated successfully!"
            else:
                filename = f"{evaluee_name}_LCP_{timestamp}.xlsx"
                export_label = "📥 Download Excel Report"
                success_msg = "✅ Excel report generated successfully!"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                # Export to temporary file
                ExcelExporter(calculator).export(tmp_file.name, include_all_scenarios=include_all_scenarios)
                
                # Read file for download
                with open(tmp_file.name, 'rb') as f:
                    file_data = f.read()
                
                # Clean up
                os.unlink(tmp_file.name)
                
                # Provide download
                st.download_button(
                    label=export_label,
                    data=file_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.success(success_msg)
                
    except Exception as e:
        st.error(f"Error generating Excel report: {str(e)}")

def export_to_word(calculator, include_all_scenarios=False):
    """Export to Word format."""
    try:
        with st.spinner("Generating Word document..."):
            # Create temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            evaluee_name = st.session_state.lcp_data.evaluee.name.replace(" ", "_")
            
            if include_all_scenarios:
                filename = f"{evaluee_name}_LCP_MultiScenario_{timestamp}.docx"
                export_label = "📥 Download Multi-Scenario Word Document"
                success_msg = "✅ Multi-scenario Word document generated successfully!"
            else:
                filename = f"{evaluee_name}_LCP_{timestamp}.docx"
                export_label = "📥 Download Word Document"
                success_msg = "✅ Word document generated successfully!"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                # Export to temporary file
                WordExporter(calculator).export(tmp_file.name, include_all_scenarios=include_all_scenarios)
                
                # Read file for download
                with open(tmp_file.name, 'rb') as f:
                    file_data = f.read()
                
                # Clean up
                os.unlink(tmp_file.name)
                
                # Provide download
                st.download_button(
                    label=export_label,
                    data=file_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
                st.success(success_msg)
                
    except Exception as e:
        st.error(f"Error generating Word document: {str(e)}")

def export_to_pdf(calculator):
    """Export to PDF format."""
    try:
        with st.spinner("Generating PDF report..."):
            # Create temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            evaluee_name = st.session_state.lcp_data.evaluee.name.replace(" ", "_")
            filename = f"{evaluee_name}_LCP_{timestamp}.pdf"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                # Export to temporary file
                PDFExporter(calculator).export(tmp_file.name)
                
                # Read file for download
                with open(tmp_file.name, 'rb') as f:
                    file_data = f.read()
                
                # Clean up
                os.unlink(tmp_file.name)
                
                # Provide download
                st.download_button(
                    label="📥 Download PDF Report",
                    data=file_data,
                    file_name=filename,
                    mime="application/pdf"
                )
                
                st.success("✅ PDF report generated successfully!")
                
    except Exception as e:
        st.error(f"Error generating PDF report: {str(e)}")

def export_all_formats(calculator):
    """Export all formats as a ZIP file."""
    try:
        import zipfile
        
        with st.spinner("Generating all reports..."):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            evaluee_name = st.session_state.lcp_data.evaluee.name.replace(" ", "_")
            
            # Create temporary files for each format
            temp_files = {}
            
            # Excel
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                ExcelExporter(calculator).export(tmp_file.name)
                temp_files['excel'] = (tmp_file.name, f"{evaluee_name}_LCP_{timestamp}.xlsx")
            
            # Word
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                WordExporter(calculator).export(tmp_file.name)
                temp_files['word'] = (tmp_file.name, f"{evaluee_name}_LCP_{timestamp}.docx")
            
            # PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                PDFExporter(calculator).export(tmp_file.name)
                temp_files['pdf'] = (tmp_file.name, f"{evaluee_name}_LCP_{timestamp}.pdf")
            
            # Create ZIP file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as zip_file:
                with zipfile.ZipFile(zip_file.name, 'w') as zf:
                    for format_name, (temp_path, final_name) in temp_files.items():
                        zf.write(temp_path, final_name)
                
                # Read ZIP file for download
                with open(zip_file.name, 'rb') as f:
                    zip_data = f.read()
                
                # Clean up temporary files
                for temp_path, _ in temp_files.values():
                    os.unlink(temp_path)
                os.unlink(zip_file.name)
                
                # Provide download
                zip_filename = f"{evaluee_name}_LCP_Reports_{timestamp}.zip"
                st.download_button(
                    label="📥 Download All Reports (ZIP)",
                    data=zip_data,
                    file_name=zip_filename,
                    mime="application/zip"
                )
                
                st.success("✅ All reports generated successfully!")
                
    except Exception as e:
        st.error(f"Error generating reports: {str(e)}")

def show_report_preview(calculator):
    """Show a preview of what will be included in the reports."""
    try:
        # Get summary statistics
        summary_stats = calculator.calculate_summary_statistics()
        cost_schedule = calculator.build_cost_schedule()
        category_costs = calculator.get_cost_by_category()
        
        st.markdown("### Report Contents Preview")
        
        # Summary section
        st.markdown("#### Executive Summary")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Evaluee:** {st.session_state.lcp_data.evaluee.name}")
            st.write(f"**Current Age:** {st.session_state.lcp_data.evaluee.current_age} years")
            st.write(f"**Base Year:** {st.session_state.lcp_data.settings.base_year}")
            st.write(f"**Projection Period:** {st.session_state.lcp_data.settings.projection_years} years")
        
        with col2:
            st.write(f"**Total Nominal Cost:** ${summary_stats['total_nominal_cost']:,.2f}")
            st.write(f"**Average Annual Cost:** ${summary_stats['average_annual_cost']:,.2f}")
            if st.session_state.lcp_data.evaluee.discount_calculations:
                st.write(f"**Total Present Value:** ${summary_stats['total_present_value']:,.2f}")
            st.write(f"**Discount Rate:** {st.session_state.lcp_data.settings.discount_rate:.1%}")
        
        # Service tables summary
        st.markdown("#### Service Categories")
        for table_name, table in st.session_state.lcp_data.tables.items():
            st.write(f"• **{table_name}**: {len(table.services)} services")
        
        # Category costs preview
        if category_costs:
            st.markdown("#### Cost by Category")
            for category, costs in category_costs.items():
                pv_text = f" (PV: ${costs['present_value_total']:,.0f})" if st.session_state.lcp_data.evaluee.discount_calculations else ""
                st.write(f"• **{category}**: ${costs['nominal_total']:,.0f}{pv_text}")
        
        # Cost schedule preview (first 5 years)
        if len(cost_schedule) > 0:
            st.markdown("#### Cost Schedule Preview (First 5 Years)")
            preview_df = cost_schedule.head(5).copy()
            
            # Format for display
            monetary_columns = [col for col in preview_df.columns if col not in ['Year', 'Age']]
            for col in monetary_columns:
                if col in preview_df.columns:
                    preview_df[col] = preview_df[col].apply(lambda x: f"${x:,.0f}")
            
            if 'Age' in preview_df.columns:
                preview_df['Age'] = preview_df['Age'].apply(lambda x: f"{x:.1f}")
            
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
            
            if len(cost_schedule) > 5:
                st.caption(f"... and {len(cost_schedule) - 5} more years")
        
    except Exception as e:
        st.error(f"Error generating preview: {str(e)}")
