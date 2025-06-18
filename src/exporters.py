import pandas as pd
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import os
from .calculator import CostCalculator
from .models import LifeCarePlan


class ExcelExporter:
    """Export life care plan data to Excel format."""
    
    def __init__(self, calculator: CostCalculator):
        self.calculator = calculator
        self.lcp = calculator.lcp
    
    def export(self, file_path: str) -> None:
        """Export the life care plan to Excel file with improved formatting."""
        df = self.calculator.build_cost_schedule()
        summary_stats = self.calculator.calculate_summary_statistics()
        category_costs = self.calculator.get_cost_by_category()

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Main cost schedule with better column headers
            df_formatted = df.copy()
            df_formatted.columns = [
                'Year',
                'Evaluee Age',
                'Total Annual Cost (Nominal)',
                'Total Annual Cost (Present Value)' if 'Present Value' in df.columns else 'Total Annual Cost',
                'Cumulative Cost (Nominal)',
                'Cumulative Cost (Present Value)' if 'Cumulative PV' in df.columns else 'Cumulative Cost'
            ][:len(df.columns)]

            df_formatted.to_excel(writer, sheet_name='Annual Cost Schedule', index=False)

            # Enhanced Summary statistics with clearer descriptions
            summary_data = [
                ['Life Care Plan Summary', ''],
                ['Evaluee Name', self.lcp.evaluee.name],
                ['Current Age at Base Year', f"{self.lcp.evaluee.current_age} years old"],
                ['Base Year (Analysis Start)', str(self.lcp.settings.base_year)],
                ['Projection Period', f"{self.lcp.settings.projection_years} years ({summary_stats['projection_period']})"],
                ['Discount Rate Applied', f"{self.lcp.settings.discount_rate:.1%}" if self.lcp.evaluee.discount_calculations else "Not Applied"],
                ['', ''],
                ['Financial Summary', ''],
                ['Total Lifetime Cost (Nominal)', f"${summary_stats['total_nominal_cost']:,.2f}"],
                ['Average Annual Cost', f"${summary_stats['average_annual_cost']:,.2f}"],
            ]
            
            # Only include discount rate info if calculations are enabled
            if self.lcp.evaluee.discount_calculations:
                summary_data.extend([
                    ['Total Lifetime Cost (Present Value)', f"${summary_stats['total_present_value']:,.2f}"],
                    ['Present Value Savings vs Nominal', f"${summary_stats['total_nominal_cost'] - summary_stats['total_present_value']:,.2f}"],
                ])

            summary_data.extend([
                ['', ''],
                ['Analysis Details', ''],
                ['Service Categories Included', str(len(self.lcp.tables))],
                ['Total Individual Services', str(sum(len(table.services) for table in self.lcp.tables.values()))],
                ['Report Generated', datetime.now().strftime('%Y-%m-%d at %H:%M:%S')],
            ])

            summary_df = pd.DataFrame(summary_data, columns=['Description', 'Value'])
            summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
            
            # Enhanced Category breakdown with clearer headers
            category_rows = []
            if self.lcp.evaluee.discount_calculations:
                category_columns = [
                    'Service Category',
                    'Total Lifetime Cost (Nominal)',
                    'Total Lifetime Cost (Present Value)',
                    'Number of Services'
                ]
                for table_name, data in category_costs.items():
                    category_rows.append([
                        table_name,
                        f"${data['table_nominal_total']:,.2f}",
                        f"${data['table_present_value_total']:,.2f}",
                        len(data['services'])
                    ])
            else:
                category_columns = [
                    'Service Category',
                    'Total Lifetime Cost (Nominal)',
                    'Number of Services'
                ]
                for table_name, data in category_costs.items():
                    category_rows.append([
                        table_name,
                        f"${data['table_nominal_total']:,.2f}",
                        len(data['services'])
                    ])

            category_df = pd.DataFrame(category_rows, columns=category_columns)
            category_df.to_excel(writer, sheet_name='Cost by Category', index=False)
            
            # Detailed Service Information with clearer headers
            service_rows = []
            service_columns = [
                'Service Category',
                'Service Name',
                'Unit Cost ($)',
                'Frequency per Year',
                'Annual Inflation Rate (%)',
                'Service Type',
                'Start Year',
                'End Year',
                'Total Lifetime Cost (Nominal)'
            ]

            if self.lcp.evaluee.discount_calculations:
                service_columns.append('Total Lifetime Cost (Present Value)')
            
            for table_name, data in category_costs.items():
                for service in data['services']:
                    service_type = 'One-time' if service['is_one_time_cost'] else \
                                  'Discrete' if service['occurrence_years'] else 'Recurring'
                    
                    start_year = service['one_time_cost_year'] if service['is_one_time_cost'] else \
                                service['start_year'] if service['start_year'] else 'N/A'
                    end_year = service['one_time_cost_year'] if service['is_one_time_cost'] else \
                              service['end_year'] if service['end_year'] else 'N/A'
                    
                    if service['occurrence_years']:
                        start_year = min(service['occurrence_years'])
                        end_year = max(service['occurrence_years'])
                        service_type += f" ({len(service['occurrence_years'])} occurrences)"
                    
                    service_row = [
                        table_name,
                        service['name'],
                        f"${service['unit_cost']:,.2f}",
                        f"{service['frequency_per_year']:.1f}x per year",
                        f"{service['inflation_rate']:.1f}%",
                        service_type,
                        start_year,
                        end_year,
                        f"${service['nominal_total']:,.2f}"
                    ]
                    
                    if self.lcp.evaluee.discount_calculations:
                        service_row.append(f"${service['present_value_total']:,.2f}")
                    
                    service_rows.append(service_row)
            
            service_df = pd.DataFrame(service_rows, columns=service_columns)
            service_df.to_excel(writer, sheet_name='Service Details', index=False)


class WordExporter:
    """Export life care plan data to Word document format."""
    
    def __init__(self, calculator: CostCalculator):
        self.calculator = calculator
        self.lcp = calculator.lcp
    
    def export(self, file_path: str, include_chart: bool = True) -> None:
        """Export the life care plan to Word document in landscape mode."""
        doc = Document()

        # Set document to landscape orientation
        section = doc.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        # Swap width and height for landscape
        new_width, new_height = section.page_height, section.page_width
        section.page_width = new_width
        section.page_height = new_height

        # Adjust margins for better table fit
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)

        # Title and header information
        title = doc.add_heading(f"Life Care Plan Economic Projection", level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Subtitle with evaluee name
        subtitle = doc.add_heading(f"Evaluee: {self.lcp.evaluee.name}", level=2)
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Enhanced Document metadata in a more professional format
        metadata_para = doc.add_paragraph()
        metadata_para.add_run("Report Generated: ").bold = True
        metadata_para.add_run(f"{datetime.now().strftime('%B %d, %Y at %H:%M:%S')}\n")

        metadata_para.add_run("Evaluee Age at Analysis Start: ").bold = True
        metadata_para.add_run(f"{self.lcp.evaluee.current_age} years old (in {self.lcp.settings.base_year})\n")

        metadata_para.add_run("Analysis Period: ").bold = True
        end_year = int(self.lcp.settings.base_year) + int(self.lcp.settings.projection_years) - 1
        metadata_para.add_run(f"{int(self.lcp.settings.projection_years)} years ({int(self.lcp.settings.base_year)} to {end_year})\n")

        if self.lcp.evaluee.discount_calculations:
            metadata_para.add_run("Discount Rate Applied: ").bold = True
            metadata_para.add_run(f"{self.lcp.settings.discount_rate:.1%} annually\n")
            metadata_para.add_run("Present Value Calculations: ").bold = True
            metadata_para.add_run("Enabled\n")
        else:
            metadata_para.add_run("Present Value Calculations: ").bold = True
            metadata_para.add_run("Not Applied\n")

        metadata_para.add_run("Service Categories Analyzed: ").bold = True
        metadata_para.add_run(f"{len(self.lcp.tables)}\n")

        metadata_para.add_run("Total Individual Services: ").bold = True
        metadata_para.add_run(f"{sum(len(table.services) for table in self.lcp.tables.values())}")
        
        # Add spacing after metadata
        doc.add_paragraph()
        doc.add_paragraph()
        
        # DAUBERT/FRYE COMPLIANCE DOCUMENTATION
        doc.add_heading("Expert Methodology and Scientific Reliability Documentation", level=2)
        
        # Methodology Section
        methodology_para = doc.add_paragraph()
        methodology_para.add_run("Methodology and Scientific Basis: ").bold = True
        methodology_para.add_run("This life care plan economic projection employs established econometric principles and medical cost forecasting methodologies ")
        methodology_para.add_run("consistent with peer-reviewed literature in health economics and actuarial science. The analytical framework incorporates ")
        methodology_para.add_run("inflation modeling using compound annual growth rates, present value calculations using established discount rate theory, ")
        methodology_para.add_run("and frequency-based cost projections grounded in medical utilization standards.")
        
        doc.add_paragraph()
        
        # Reliability and Error Rate Section
        reliability_para = doc.add_paragraph()
        reliability_para.add_run("Reliability and Potential Error Rates: ").bold = True
        reliability_para.add_run("Economic projections are subject to inherent uncertainties in inflation rates, discount rates, and medical cost trends. ")
        reliability_para.add_run("Historical medical inflation rates typically range from 2-6% annually (Bureau of Labor Statistics, 2010-2024). ")
        reliability_para.add_run("Discount rate assumptions follow federal guidelines and economic standards (OMB Circular A-4, Federal Reserve data). ")
        reliability_para.add_run("Service frequency estimates are based on medical literature and clinical guidelines where available.")
        
        doc.add_paragraph()
        
        # Scientific Acceptance Section
        acceptance_para = doc.add_paragraph()
        acceptance_para.add_run("General Acceptance in Relevant Scientific Community: ").bold = True
        acceptance_para.add_run("Life care plan economic analysis methodologies are widely accepted in forensic economics, ")
        acceptance_para.add_run("rehabilitation counseling, and medical-legal communities. Standards are established by: ")
        acceptance_para.add_run("International Association of Rehabilitation Professionals (IARP), ")
        acceptance_para.add_run("Commission on Health Care Certification (CHCC), ")
        acceptance_para.add_run("National Association of Forensic Economics (NAFE), ")
        acceptance_para.add_run("and peer-reviewed publications in Journal of Forensic Economics, ")
        acceptance_para.add_run("Topics in Spinal Cord Injury Rehabilitation, and similar professional journals.")
        
        doc.add_paragraph()
        
        # Testing and Peer Review Section
        testing_para = doc.add_paragraph()
        testing_para.add_run("Testing and Peer Review: ").bold = True
        testing_para.add_run("The economic modeling techniques used in this analysis have been subject to extensive peer review ")
        testing_para.add_run("through professional literature and court proceedings. Mathematical calculations follow established ")
        testing_para.add_run("financial formulas for present value analysis (PV = FV / (1 + r)^n) and compound growth modeling ")
        testing_para.add_run("(FV = PV × (1 + g)^n). All computational methods are reproducible and verifiable.")
        
        doc.add_paragraph()
        
        # Data Sources and Standards Section
        standards_para = doc.add_paragraph()
        standards_para.add_run("Data Sources and Professional Standards: ").bold = True
        standards_para.add_run("Cost estimates should be derived from reliable sources including: ")
        standards_para.add_run("Medicare fee schedules, private insurance reimbursement rates, ")
        standards_para.add_run("durable medical equipment vendor quotes, pharmaceutical pricing databases, ")
        standards_para.add_run("and published medical literature. Service frequencies should reference ")
        standards_para.add_run("evidence-based treatment protocols, clinical practice guidelines, ")
        standards_para.add_run("and medical professional recommendations specific to the individual's condition.")
        
        doc.add_paragraph()
        
        # Expert Qualifications Required Section
        qualifications_para = doc.add_paragraph()
        qualifications_para.add_run("Expert Qualifications Framework: ").bold = True
        qualifications_para.add_run("Life care plan economic analysis should be conducted by qualified professionals with: ")
        qualifications_para.add_run("(1) Advanced education in economics, healthcare administration, or rehabilitation counseling; ")
        qualifications_para.add_run("(2) Specialized training in life care planning methodology; ")
        qualifications_para.add_run("(3) Professional certification (CRC, CLCP, CVE, or equivalent); ")
        qualifications_para.add_run("(4) Experience with economic analysis and present value calculations; ")
        qualifications_para.add_run("(5) Knowledge of relevant medical conditions and treatment standards.")
        
        doc.add_paragraph()
        
        # Limitations and Assumptions Section
        limitations_para = doc.add_paragraph()
        limitations_para.add_run("Limitations and Key Assumptions: ").bold = True
        limitations_para.add_run("This economic projection is based on current medical knowledge and economic conditions. ")
        limitations_para.add_run("Actual costs may vary due to: changes in medical technology, treatment protocols, ")
        limitations_para.add_run("economic conditions, geographic variations, insurance coverage changes, ")
        limitations_para.add_run("and individual medical developments. Inflation and discount rate assumptions ")
        limitations_para.add_run("represent reasonable estimates but are subject to economic volatility. ")
        limitations_para.add_run("Service frequencies assume stable medical condition and standard care protocols.")
        
        doc.add_paragraph()
        
        # Calculation Transparency Section
        transparency_para = doc.add_paragraph()
        transparency_para.add_run("Calculation Transparency and Reproducibility: ").bold = True
        transparency_para.add_run("All calculations in this report are fully documented and reproducible. ")
        transparency_para.add_run("Mathematical formulas, inflation rates, discount rates, and service frequencies ")
        transparency_para.add_run("are explicitly stated. Raw data inputs and computational methods are available ")
        transparency_para.add_run("for independent verification and cross-examination. Alternative scenarios ")
        transparency_para.add_run("and sensitivity analyses can be performed using different assumption sets.")
        
        # Add legal disclaimer
        doc.add_paragraph()
        disclaimer_para = doc.add_paragraph()
        disclaimer_para.add_run("Legal and Professional Disclaimer: ").bold = True
        disclaimer_para.add_run("This economic analysis is prepared for legal proceedings and expert testimony purposes. ")
        disclaimer_para.add_run("The methodology and conclusions are offered to assist the trier of fact in understanding ")
        disclaimer_para.add_run("future medical care costs. All opinions are expressed within reasonable degree of ")
        disclaimer_para.add_run("professional certainty based on available data and established methodologies.")
        
        # Mathematical Methodology Documentation
        doc.add_heading("Mathematical Formulas and Calculation Methods", level=2)
        
        # Formula documentation
        formula_para = doc.add_paragraph()
        formula_para.add_run("Inflation Adjustment Formula: ").bold = True
        formula_para.add_run("Future Cost = Present Cost × (1 + inflation_rate)^years_from_base")
        
        doc.add_paragraph()
        pv_para = doc.add_paragraph()
        pv_para.add_run("Present Value Formula: ").bold = True
        pv_para.add_run("Present Value = Future Value ÷ (1 + discount_rate)^years_from_base")
        
        doc.add_paragraph()
        annual_para = doc.add_paragraph()
        annual_para.add_run("Annual Service Cost: ").bold = True
        annual_para.add_run("Annual Cost = Unit Cost × Frequency per Year × Inflation Adjustment")
        
        doc.add_paragraph()
        lifetime_para = doc.add_paragraph()
        lifetime_para.add_run("Lifetime Service Cost: ").bold = True
        lifetime_para.add_run("Sum of all annual costs over the service period, with inflation applied to each year")
        
        doc.add_paragraph()
        
        # Economic Assumptions Documentation
        economic_para = doc.add_paragraph()
        economic_para.add_run("Economic Assumptions Used: ").bold = True
        if self.lcp.evaluee.discount_calculations:
            economic_para.add_run(f"Discount Rate: {self.lcp.settings.discount_rate:.1%} annually. ")
        economic_para.add_run(f"Analysis Period: {int(self.lcp.settings.projection_years)} years ")
        economic_para.add_run(f"({int(self.lcp.settings.base_year)} through {int(self.lcp.settings.base_year) + int(self.lcp.settings.projection_years) - 1}). ")
        economic_para.add_run("Individual service inflation rates as specified in service details. ")
        economic_para.add_run("All calculations assume consistent annual application of stated rates.")
        
        doc.add_paragraph()
        
        # Quality Control Documentation
        qc_para = doc.add_paragraph()
        qc_para.add_run("Quality Control and Verification: ").bold = True
        qc_para.add_run("All calculations are performed using established financial mathematics. ")
        qc_para.add_run("Results are subject to mathematical verification and cross-checking. ")
        qc_para.add_run("Alternative calculation methods may be applied for confirmation. ")
        qc_para.add_run("Sensitivity analysis can be performed using different assumption sets ")
        qc_para.add_run("to test the robustness of projections under varying economic conditions.")
        
        doc.add_page_break()
        
        # Summary statistics
        doc.add_heading("Executive Summary", level=2)
        summary_stats = self.calculator.calculate_summary_statistics()

        summary_para = doc.add_paragraph()
        summary_para.add_run("Total Lifetime Medical Costs (Nominal): ").bold = True
        summary_para.add_run(f"${summary_stats['total_nominal_cost']:,.2f}\n")

        summary_para.add_run("Average Annual Medical Costs: ").bold = True
        summary_para.add_run(f"${summary_stats['average_annual_cost']:,.2f}\n")

        if self.lcp.evaluee.discount_calculations:
            summary_para.add_run("Total Lifetime Medical Costs (Present Value): ").bold = True
            summary_para.add_run(f"${summary_stats['total_present_value']:,.2f}\n")

            savings = summary_stats['total_nominal_cost'] - summary_stats['total_present_value']
            summary_para.add_run("Present Value Savings vs Nominal: ").bold = True
            summary_para.add_run(f"${savings:,.2f}\n")
        
        # Add spacing after summary
        doc.add_paragraph()
        doc.add_paragraph()
        
        # Detailed Service Category Breakdown
        doc.add_heading("Detailed Service Breakdown by Category", level=2)
        category_costs = self.calculator.get_cost_by_category()
        
        for table_name, data in category_costs.items():
            # Category header with summary
            doc.add_heading(f"{table_name}", level=3)
            
            # Category summary paragraph with Daubert compliance
            summary_para = doc.add_paragraph()
            summary_para.add_run("Category Summary: ").bold = True
            summary_para.add_run(f"This category contains {len(data['services'])} medical service(s) with a total lifetime cost of ")
            summary_para.add_run(f"${data['table_nominal_total']:,.2f}").bold = True
            if self.lcp.evaluee.discount_calculations:
                summary_para.add_run(f" (${data['table_present_value_total']:,.2f} in present value)")
            summary_para.add_run(".")
            
            # Add methodology documentation for this category
            doc.add_paragraph()
            methodology_category_para = doc.add_paragraph()
            methodology_category_para.add_run("Data Source Requirements for This Category: ").bold = True
            methodology_category_para.add_run("Cost estimates for services in this category should be supported by ")
            methodology_category_para.add_run("current market rates, provider quotes, published fee schedules, or peer-reviewed literature. ")
            methodology_category_para.add_run("Service frequencies should be based on medical necessity, physician recommendations, ")
            methodology_category_para.add_run("clinical practice guidelines, or established treatment protocols. ")
            methodology_category_para.add_run("All assumptions regarding timing, duration, and intensity of services ")
            methodology_category_para.add_run("should be documented and supportable through medical evidence.")
            
            reliability_category_para = doc.add_paragraph()
            reliability_category_para.add_run("Reliability Considerations: ").bold = True
            reliability_category_para.add_run("Cost projections assume continuation of current service delivery models. ")
            reliability_category_para.add_run("Actual utilization may vary based on individual response to treatment, ")
            reliability_category_para.add_run("medical complications, technological advances, or changes in standard of care. ")
            reliability_category_para.add_run("Geographic cost variations and insurance coverage changes may affect actual expenses.")
            
            doc.add_paragraph()  # Spacing
            
            if data['services']:
                # Create detailed service table for this category
                service_table_headers = [
                    'Service Name',
                    'Cost per Unit\n(Data Source Required)',
                    'Frequency per Year\n(Medical Basis Required)',
                    'Service Period\n(Clinical Justification)',
                    'Annual Inflation Rate\n(Economic Basis)',
                    'Total Lifetime Cost\n(Calculated)'
                ]
                
                if self.lcp.evaluee.discount_calculations:
                    service_table_headers.append('Present Value\nLifetime Cost\n(Calculated)')
                
                # Create service table
                service_table = doc.add_table(rows=len(data['services']) + 1, cols=len(service_table_headers))
                service_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                service_table.style = 'Table Grid'
                
                # Set column widths for service table
                col_widths = [Inches(2.0), Inches(1.0), Inches(0.8), Inches(1.5), Inches(0.8), Inches(1.3)]
                if self.lcp.evaluee.discount_calculations:
                    col_widths.append(Inches(1.3))
                
                for i, width in enumerate(col_widths):
                    if i < len(service_table.columns):
                        service_table.columns[i].width = width
                
                # Header row
                hdr_cells = service_table.rows[0].cells
                for idx, header_text in enumerate(service_table_headers):
                    hdr_cells[idx].text = header_text
                    paragraph = hdr_cells[idx].paragraphs[0]
                    run = paragraph.runs[0]
                    run.bold = True
                    run.font.size = Pt(9)
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    # Cell formatting
                    hdr_cells[idx].top_margin = Pt(4)
                    hdr_cells[idx].bottom_margin = Pt(4)
                    hdr_cells[idx].left_margin = Pt(3)
                    hdr_cells[idx].right_margin = Pt(3)
                
                # Data rows for each service
                for row_idx, service in enumerate(data['services'], start=1):
                    row_cells = service_table.rows[row_idx].cells
                    
                    # Determine service period description
                    if service['is_one_time_cost']:
                        service_period = f"One-time in {service['one_time_cost_year']}"
                    elif service['occurrence_years']:
                        years = service['occurrence_years']
                        if len(years) == 1:
                            service_period = f"Year {years[0]} only"
                        else:
                            service_period = f"Years {min(years)}-{max(years)}\n({len(years)} specific years)"
                    else:
                        start_yr = service['start_year'] if service['start_year'] else 'Start of plan'
                        end_yr = service['end_year'] if service['end_year'] else 'End of plan'
                        service_period = f"{start_yr} to {end_yr}"
                    
                    # Fill in service data
                    service_data = [
                        service['name'],
                        f"${service['unit_cost']:,.2f}",
                        f"{service['frequency_per_year']:.1f}x",
                        service_period,
                        f"{service['inflation_rate']:.1f}%",
                        f"${service['nominal_total']:,.2f}"
                    ]
                    
                    if self.lcp.evaluee.discount_calculations:
                        service_data.append(f"${service['present_value_total']:,.2f}")
                    
                    for col_idx, cell_value in enumerate(service_data):
                        row_cells[col_idx].text = cell_value
                        
                        # Cell formatting
                        row_cells[col_idx].top_margin = Pt(3)
                        row_cells[col_idx].bottom_margin = Pt(3)
                        row_cells[col_idx].left_margin = Pt(3)
                        row_cells[col_idx].right_margin = Pt(3)
                        
                        # Text formatting
                        paragraph = row_cells[col_idx].paragraphs[0]
                        if paragraph.runs:
                            paragraph.runs[0].font.size = Pt(8)
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Add legal and methodological explanatory text
                doc.add_paragraph()
                explanation_para = doc.add_paragraph()
                explanation_para.add_run("Expert Opinion Basis: ").bold = True
                explanation_para.add_run("Each service listed requires supporting documentation including: ")
                explanation_para.add_run("(1) Medical necessity determined by qualified healthcare providers; ")
                explanation_para.add_run("(2) Cost estimates from reliable sources (providers, fee schedules, market research); ")
                explanation_para.add_run("(3) Frequency based on treatment protocols or physician recommendations; ")
                explanation_para.add_run("(4) Duration supported by medical literature or clinical experience. ")
                
                doc.add_paragraph()
                calculation_para = doc.add_paragraph()
                calculation_para.add_run("Calculation Methodology: ").bold = True
                calculation_para.add_run("Costs are projected using compound inflation modeling applied annually. ")
                if self.lcp.evaluee.discount_calculations:
                    calculation_para.add_run("Present value calculations discount future costs to current dollars using ")
                    calculation_para.add_run(f"{self.lcp.settings.discount_rate:.1%} annual discount rate").bold = True
                    calculation_para.add_run(" consistent with federal economic guidelines. ")
                calculation_para.add_run("All mathematical operations follow established financial principles ")
                calculation_para.add_run("and are subject to independent verification and cross-examination.")
                
                doc.add_paragraph()
                limitations_service_para = doc.add_paragraph()
                limitations_service_para.add_run("Service-Specific Limitations: ").bold = True
                limitations_service_para.add_run("Projections assume medical stability and standard treatment protocols. ")
                limitations_service_para.add_run("Individual variations in treatment response, complications, or medical advances ")
                limitations_service_para.add_run("may alter actual service needs and costs. Expert opinions should be updated ")
                limitations_service_para.add_run("as medical conditions and standards of care evolve.")
                
            # Add spacing between categories
            doc.add_paragraph()
            doc.add_page_break() if len(category_costs) > 1 else doc.add_paragraph()
        
        # Annual Cost Schedule with Category Breakdown
        doc.add_page_break()
        doc.add_heading("Annual Cost Schedule Summary", level=2)
        
        # Add explanation paragraph
        explanation_para = doc.add_paragraph()
        explanation_para.add_run("Understanding Your Annual Costs: ").bold = True
        explanation_para.add_run("The table below shows the total medical costs for each year of the life care plan. ")
        explanation_para.add_run("These costs represent all services combined and include inflation adjustments. ")
        if self.lcp.evaluee.discount_calculations:
            explanation_para.add_run("The present value column shows what future costs are worth in today's dollars.")
        
        doc.add_paragraph()  # Spacing

        df = self.calculator.build_cost_schedule()
        
        # Create simplified annual summary table
        if "Present Value" in df.columns:
            table_columns = ['Year', 'Evaluee Age', 'Total Annual Cost', 'Present Value Cost']
            table_data = []
            for _, row in df.iterrows():
                table_data.append([
                    str(int(row['Year'])),
                    str(int(row['Age'])),
                    f"${row['Total Nominal']:,.0f}",
                    f"${row['Present Value']:,.0f}"
                ])
        else:
            table_columns = ['Year', 'Evaluee Age', 'Total Annual Cost']
            table_data = []
            for _, row in df.iterrows():
                table_data.append([
                    str(int(row['Year'])),
                    str(int(row['Age'])),
                    f"${row['Total Nominal']:,.0f}"
                ])
        
        # Create summary table
        summary_table = doc.add_table(rows=len(table_data) + 1, cols=len(table_columns))
        summary_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        summary_table.style = 'Table Grid'
        
        # Set column widths
        year_width = Inches(1.0)
        age_width = Inches(1.2) 
        cost_width = Inches(1.8)
        
        summary_table.columns[0].width = year_width
        summary_table.columns[1].width = age_width
        for i in range(2, len(table_columns)):
            summary_table.columns[i].width = cost_width

        # Header row
        hdr_cells = summary_table.rows[0].cells
        for idx, header_text in enumerate(table_columns):
            hdr_cells[idx].text = header_text
            paragraph = hdr_cells[idx].paragraphs[0]
            run = paragraph.runs[0]
            run.bold = True
            run.font.size = Pt(10)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            hdr_cells[idx].top_margin = Pt(4)
            hdr_cells[idx].bottom_margin = Pt(4)
            hdr_cells[idx].left_margin = Pt(3)
            hdr_cells[idx].right_margin = Pt(3)

        # Data rows
        for row_idx, row_data in enumerate(table_data, start=1):
            row_cells = summary_table.rows[row_idx].cells
            
            for col_idx, cell_value in enumerate(row_data):
                row_cells[col_idx].text = cell_value
                row_cells[col_idx].top_margin = Pt(3)
                row_cells[col_idx].bottom_margin = Pt(3)
                row_cells[col_idx].left_margin = Pt(3)
                row_cells[col_idx].right_margin = Pt(3)
                
                paragraph = row_cells[col_idx].paragraphs[0]
                if paragraph.runs:
                    paragraph.runs[0].font.size = Pt(9)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add Year-by-Year Loss Schedule
        doc.add_page_break()
        doc.add_heading("Year-by-Year Loss Schedule", level=2)
        
        # Add explanation
        loss_schedule_explanation = doc.add_paragraph()
        loss_schedule_explanation.add_run("Loss Schedule Overview: ").bold = True
        loss_schedule_explanation.add_run("This section provides a comprehensive year-by-year analysis of projected medical costs, ")
        loss_schedule_explanation.add_run("organized both by overall yearly totals and detailed service category breakdowns. ")
        loss_schedule_explanation.add_run("This format assists in understanding annual cost patterns and service delivery timing.")
        
        doc.add_paragraph()
        
        # Create overall summary table showing yearly totals by category
        doc.add_heading("Overall Yearly Summary by Service Category", level=3)
        
        # Calculate year-by-year totals by category
        years = list(range(int(self.lcp.settings.base_year), int(self.lcp.settings.base_year) + int(self.lcp.settings.projection_years)))
        category_names = list(self.lcp.tables.keys())
        
        # Create matrix of costs: year x category
        yearly_category_matrix = {}
        yearly_totals = {}
        category_totals = {}
        
        for year in years:
            yearly_category_matrix[year] = {}
            yearly_totals[year] = 0
            
            for table_name, table in self.lcp.tables.items():
                category_cost = 0
                for service in table.services:
                    service_cost = self.calculator.calculate_service_cost(service, year)
                    category_cost += float(service_cost)
                
                yearly_category_matrix[year][table_name] = category_cost
                yearly_totals[year] += category_cost
                
                if table_name not in category_totals:
                    category_totals[table_name] = 0
                category_totals[table_name] += category_cost
        
        # Create summary table with years as rows, categories as columns
        summary_headers = ['Year', 'Evaluee Age'] + category_names + ['Annual Total']
        
        # Calculate table dimensions
        num_years = len(years)
        num_cols = len(summary_headers)
        
        summary_table = doc.add_table(rows=num_years + 2, cols=num_cols)  # +2 for header and totals
        summary_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        summary_table.style = 'Table Grid'
        
        # Set column widths for summary table
        year_col_width = Inches(0.7)
        age_col_width = Inches(0.8)
        category_col_width = Inches(1.1)
        total_col_width = Inches(1.2)
        
        summary_table.columns[0].width = year_col_width
        summary_table.columns[1].width = age_col_width
        for i in range(2, len(category_names) + 2):
            summary_table.columns[i].width = category_col_width
        summary_table.columns[-1].width = total_col_width
        
        # Header row
        header_cells = summary_table.rows[0].cells
        for idx, header in enumerate(summary_headers):
            header_cells[idx].text = header
            paragraph = header_cells[idx].paragraphs[0]
            run = paragraph.runs[0]
            run.bold = True
            run.font.size = Pt(9)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Data rows
        for row_idx, year in enumerate(years, start=1):
            evaluee_age = int(self.lcp.evaluee.current_age + (year - int(self.lcp.settings.base_year)))
            row_cells = summary_table.rows[row_idx].cells
            
            # Year and age
            row_cells[0].text = str(year)
            row_cells[1].text = str(evaluee_age)
            
            # Category costs
            for col_idx, category_name in enumerate(category_names, start=2):
                cost = yearly_category_matrix[year][category_name]
                row_cells[col_idx].text = f"${cost:,.0f}" if cost > 0 else "-"
                
                # Format cell
                paragraph = row_cells[col_idx].paragraphs[0]
                if paragraph.runs:
                    paragraph.runs[0].font.size = Pt(8)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Annual total
            row_cells[-1].text = f"${yearly_totals[year]:,.0f}"
            
            # Format year, age, and total cells
            for cell_idx in [0, 1, -1]:
                paragraph = row_cells[cell_idx].paragraphs[0]
                if paragraph.runs:
                    paragraph.runs[0].font.size = Pt(8)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Totals row
        totals_cells = summary_table.rows[-1].cells
        totals_cells[0].text = "TOTALS"
        totals_cells[1].text = ""
        
        for col_idx, category_name in enumerate(category_names, start=2):
            total_cost = category_totals[category_name]
            totals_cells[col_idx].text = f"${total_cost:,.0f}"
            
            # Format cell
            paragraph = totals_cells[col_idx].paragraphs[0]
            run = paragraph.runs[0] if paragraph.runs else paragraph.add_run(totals_cells[col_idx].text)
            run.bold = True
            run.font.size = Pt(9)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Grand total
        grand_total = sum(yearly_totals.values())
        totals_cells[-1].text = f"${grand_total:,.0f}"
        paragraph = totals_cells[-1].paragraphs[0]
        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run(totals_cells[-1].text)
        run.bold = True
        run.font.size = Pt(9)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Format first column of totals row
        paragraph = totals_cells[0].paragraphs[0]
        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run(totals_cells[0].text)
        run.bold = True
        run.font.size = Pt(9)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph()
        
        # Add summary explanation
        summary_explanation = doc.add_paragraph()
        summary_explanation.add_run("Summary Table Explanation: ").bold = True
        summary_explanation.add_run("This table shows the total cost for each service category by year. ")
        summary_explanation.add_run("Reading across each row shows the annual cost distribution across different types of medical services. ")
        summary_explanation.add_run("Reading down each column shows how costs for a specific service category change over time due to inflation and service timing.")
        
        # Add comprehensive year-by-year breakdown by category
        doc.add_page_break()
        doc.add_heading("Detailed Year-by-Year Service Breakdown by Category", level=2)
        
        # Add explanation and validation notice
        detailed_explanation = doc.add_paragraph()
        detailed_explanation.add_run("Year-by-Year Service Details: ").bold = True
        detailed_explanation.add_run("The following section shows exactly which services are provided each year and their individual costs. ")
        detailed_explanation.add_run("This detailed breakdown helps you understand what drives the costs in each year of the plan.")
        
        doc.add_paragraph()
        validation_para = doc.add_paragraph()
        validation_para.add_run("Cross-Verification Notice: ").bold = True
        validation_para.add_run("All calculations in this detailed breakdown use identical mathematical methods as the Summary Schedule above. ")
        validation_para.add_run("Year totals in this section should match corresponding years in the Annual Cost Schedule Summary. ")
        validation_para.add_run("Any discrepancies indicate calculation errors that require correction.")
        
        doc.add_paragraph()
        
        # Get detailed year-by-year data
        category_costs = self.calculator.get_cost_by_category()
        years = list(range(int(self.lcp.settings.base_year), int(self.lcp.settings.base_year) + int(self.lcp.settings.projection_years)))
        
        # Create a comprehensive table showing services by year
        for year in years:
            evaluee_age = int(self.lcp.evaluee.current_age + (year - self.lcp.settings.base_year))
            doc.add_heading(f"Year {year} (Evaluee Age: {evaluee_age})", level=3)
            
            year_services = []
            year_total = 0
            year_total_pv = 0
            
            # Use calculator's service cost method for consistency
            for table_name, table in self.lcp.tables.items():
                for service in table.services:
                    # Use the calculator's method to get the correct cost for this year
                    service_cost = self.calculator.calculate_service_cost(service, year)
                    
                    if service_cost > 0:  # Service applies to this year
                        # Calculate present value using calculator's method
                        years_from_base = year - int(self.lcp.settings.base_year)
                        service_cost_pv = 0
                        if self.lcp.evaluee.discount_calculations:
                            service_cost_pv = float(self.calculator.calculate_present_value(service_cost, years_from_base))
                        
                        # Determine frequency display
                        if service.is_one_time_cost:
                            frequency_display = 1
                        else:
                            frequency_display = service.frequency_per_year
                        
                        year_services.append({
                            'category': table_name,
                            'name': service.name,
                            'frequency': frequency_display,
                            'unit_cost': service.unit_cost,
                            'inflated_cost': float(service_cost),
                            'present_value_cost': service_cost_pv,
                            'is_one_time': service.is_one_time_cost
                        })
                        
                        year_total += float(service_cost)
                        year_total_pv += service_cost_pv
            
            if year_services:
                # Create table for this year's services
                year_table_headers = ['Service Category', 'Service Name', 'Frequency', 'Cost This Year']
                if self.lcp.evaluee.discount_calculations:
                    year_table_headers.append('Present Value Cost')
                
                year_table = doc.add_table(rows=len(year_services) + 2, cols=len(year_table_headers))  # +2 for header and total
                year_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                year_table.style = 'Table Grid'
                
                # Set column widths
                year_col_widths = [Inches(1.8), Inches(2.2), Inches(0.8), Inches(1.2)]
                if self.lcp.evaluee.discount_calculations:
                    year_col_widths.append(Inches(1.2))
                
                for i, width in enumerate(year_col_widths):
                    if i < len(year_table.columns):
                        year_table.columns[i].width = width
                
                # Headers
                hdr_cells = year_table.rows[0].cells
                for idx, header_text in enumerate(year_table_headers):
                    hdr_cells[idx].text = header_text
                    paragraph = hdr_cells[idx].paragraphs[0]
                    run = paragraph.runs[0]
                    run.bold = True
                    run.font.size = Pt(9)
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Service rows
                for row_idx, service in enumerate(year_services, start=1):
                    row_cells = year_table.rows[row_idx].cells
                    
                    frequency_text = "One-time" if service['is_one_time'] else f"{service['frequency']:.1f}x/year"
                    
                    service_row_data = [
                        service['category'],
                        service['name'],
                        frequency_text,
                        f"${service['inflated_cost']:,.0f}"
                    ]
                    
                    if self.lcp.evaluee.discount_calculations:
                        service_row_data.append(f"${service['present_value_cost']:,.0f}")
                    
                    for col_idx, cell_value in enumerate(service_row_data):
                        row_cells[col_idx].text = cell_value
                        paragraph = row_cells[col_idx].paragraphs[0]
                        if paragraph.runs:
                            paragraph.runs[0].font.size = Pt(8)
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Total row
                total_row_cells = year_table.rows[-1].cells
                total_row_cells[0].text = "YEAR TOTAL"
                total_row_cells[1].text = ""
                total_row_cells[2].text = ""
                total_row_cells[3].text = f"${year_total:,.0f}"
                
                if self.lcp.evaluee.discount_calculations:
                    total_row_cells[4].text = f"${year_total_pv:,.0f}"
                
                # Format total row
                for cell in total_row_cells:
                    if cell.text:
                        paragraph = cell.paragraphs[0]
                        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run(cell.text)
                        run.bold = True
                        run.font.size = Pt(9)
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                # No services for this year
                no_services_para = doc.add_paragraph()
                no_services_para.add_run("No medical services scheduled for this year.").italic = True
            
            doc.add_paragraph()  # Spacing between years
        
        # Add Cross-Verification and Quality Control Section
        doc.add_page_break()
        doc.add_heading("Calculation Cross-Verification and Quality Control", level=2)
        
        # Verify totals match between different sections
        verification_para = doc.add_paragraph()
        verification_para.add_run("Quality Control Verification: ").bold = True
        verification_para.add_run("The following cross-checks ensure calculation accuracy and consistency throughout this report:")
        
        doc.add_paragraph()
        
        # Check 1: Category totals vs Executive total
        total_from_categories = sum(data['table_nominal_total'] for data in category_costs.values())
        summary_stats = self.calculator.calculate_summary_statistics()
        executive_total = summary_stats['total_nominal_cost']
        
        check1_para = doc.add_paragraph()
        check1_para.add_run("Check 1 - Category Totals vs Executive Summary: ").bold = True
        check1_para.add_run(f"Sum of all category totals: ${total_from_categories:,.2f}. ")
        check1_para.add_run(f"Executive summary total: ${executive_total:,.2f}. ")
        if abs(total_from_categories - executive_total) < 1.0:
            check1_para.add_run("✓ MATCH - Calculation consistent.").bold = True
        else:
            check1_para.add_run(f"✗ DISCREPANCY of ${abs(total_from_categories - executive_total):,.2f} - Requires review.").bold = True
        
        doc.add_paragraph()
        
        # Check 2: Average annual cost calculation
        check2_para = doc.add_paragraph()
        check2_para.add_run("Check 2 - Average Annual Cost Calculation: ").bold = True
        actual_years = summary_stats.get('actual_years_with_costs', int(self.lcp.settings.projection_years))
        calculated_average = executive_total / actual_years if actual_years > 0 else 0
        reported_average = summary_stats['average_annual_cost']
        check2_para.add_run(f"Total cost ÷ {actual_years} years = ${calculated_average:,.2f}. ")
        check2_para.add_run(f"Reported average: ${reported_average:,.2f}. ")
        if abs(calculated_average - reported_average) < 1.0:
            check2_para.add_run("✓ MATCH - Calculation consistent.").bold = True
        else:
            check2_para.add_run(f"✗ DISCREPANCY of ${abs(calculated_average - reported_average):,.2f} - Requires review.").bold = True
        
        doc.add_paragraph()
        
        # Check 3: Schedule summary vs detailed totals verification WITH ACTUAL COMPARISON
        check3_para = doc.add_paragraph()
        check3_para.add_run("Check 3 - Schedule Summary vs Detailed Breakdown: ").bold = True
        
        # Recalculate detailed year totals and compare with schedule
        schedule_df = self.calculator.build_cost_schedule()
        detailed_year_totals = {}
        
        for year in years:
            year_total = 0
            for table_name, table in self.lcp.tables.items():
                for service in table.services:
                    service_cost = self.calculator.calculate_service_cost(service, year)
                    year_total += float(service_cost)
            detailed_year_totals[year] = year_total
        
        # Compare a few key years
        test_years = [years[0], years[len(years)//4], years[len(years)//2], years[-5], years[-1]] if len(years) >= 5 else years[:3]
        max_discrepancy = 0
        all_match = True
        
        for test_year in test_years:
            schedule_row = schedule_df[schedule_df['Year'] == test_year]
            if not schedule_row.empty:
                schedule_total = schedule_row['Total Nominal'].iloc[0]
                detailed_total = detailed_year_totals[test_year]
                discrepancy = abs(schedule_total - detailed_total)
                max_discrepancy = max(max_discrepancy, discrepancy)
                
                if discrepancy > 1.0:
                    all_match = False
                    check3_para.add_run(f"Year {test_year}: Schedule=${schedule_total:,.0f}, Detailed=${detailed_total:,.0f}, Δ=${discrepancy:,.0f}. ")
        
        if all_match:
            check3_para.add_run("✓ MATCH - All tested years match between Schedule Summary and Detailed Breakdown.").bold = True
        else:
            check3_para.add_run(f"✗ DISCREPANCY - Maximum difference of ${max_discrepancy:,.0f} found between sections.").bold = True
        
        doc.add_paragraph()
        
        # Check 4: Total verification across all sections
        schedule_total_sum = schedule_df['Total Nominal'].sum()
        detailed_total_sum = sum(detailed_year_totals.values())
        
        check4_para = doc.add_paragraph()
        check4_para.add_run("Check 4 - Total Sum Verification: ").bold = True
        check4_para.add_run(f"Schedule 39-year sum: ${schedule_total_sum:,.2f}. ")
        check4_para.add_run(f"Detailed 39-year sum: ${detailed_total_sum:,.2f}. ")
        check4_para.add_run(f"Executive total: ${executive_total:,.2f}. ")
        
        if (abs(schedule_total_sum - detailed_total_sum) < 1.0 and 
            abs(schedule_total_sum - executive_total) < 1.0):
            check4_para.add_run("✓ ALL MATCH - Perfect reconciliation across all sections.").bold = True
        else:
            check4_para.add_run("✗ DISCREPANCY - Requires immediate correction.").bold = True
        
        doc.add_paragraph()
        
        # Check 5: Quality Control Matrix Validation (Audit Template)
        check5_para = doc.add_paragraph()
        check5_para.add_run("Check 5 - Quality Control Matrix Validation: ").bold = True
        
        qc_validation = self.calculator.quality_control_validation()
        check5_para.add_run(f"Matrix reconciliation test: ")
        
        if qc_validation['reconciliation_passes']:
            check5_para.add_run(f"✓ PASS - Discrepancy of ${qc_validation['discrepancy']:.2f} (< $1.00).").bold = True
        else:
            check5_para.add_run(f"✗ FAIL - Discrepancy of ${qc_validation['discrepancy']:.2f} exceeds $1.00 tolerance.").bold = True
        
        check5_para.add_run(f" Sum of lifetime costs: ${qc_validation['sum_lifetime_costs']:,.2f}. ")
        check5_para.add_run(f"Sum of annual schedule: ${qc_validation['sum_annual_schedule']:,.2f}.")
        
        doc.add_paragraph()
        
        # Matrix validation explanation
        matrix_para = doc.add_paragraph()
        matrix_para.add_run("Matrix Validation Method: ").bold = True
        matrix_para.add_run("This test implements the audit-recommended quality control template: ")
        matrix_para.add_run("(1) Extract service master table; ")
        matrix_para.add_run("(2) Generate yearly cost matrices using Cost[year,service] = UnitCost × Frequency × (1+inflation)^years; ")
        matrix_para.add_run("(3) Calculate row-sums (annual totals) and column-sums (lifetime costs); ")
        matrix_para.add_run("(4) Verify absolute difference < $1.00. ")
        matrix_para.add_run("This ensures mathematical lock-step across all presentation layers.")
        
        doc.add_paragraph()
        
        # Mathematical accuracy statement
        accuracy_para = doc.add_paragraph()
        accuracy_para.add_run("Mathematical Accuracy Statement: ").bold = True
        accuracy_para.add_run("All calculations in this report use established financial mathematics with consistent ")
        accuracy_para.add_run("inflation compounding and present value discounting. Rounding is applied consistently ")
        accuracy_para.add_run("to the nearest cent. All computational methods are reproducible and subject to ")
        accuracy_para.add_run("independent verification through cross-examination.")
        
        # Add spacing after table
        doc.add_paragraph()
        doc.add_paragraph()
        
        # Add chart if requested
        if include_chart:
            chart_path = self._create_chart()
            if chart_path and os.path.exists(chart_path):
                doc.add_page_break()
                doc.add_heading("Cost Visualization", level=2)
                doc.add_paragraph()  # Add spacing before chart
                
                # Center the chart
                chart_para = doc.add_paragraph()
                chart_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                chart_run = chart_para.add_run()
                chart_run.add_picture(chart_path, width=Inches(8))  # Larger chart for better readability
                
                # Clean up temporary chart file
                os.remove(chart_path)
        
        doc.save(file_path)
    
    def _create_chart(self) -> Optional[str]:
        """Create a temporary chart file for inclusion in Word document."""
        try:
            df = self.calculator.build_cost_schedule()
            
            plt.figure(figsize=(10, 6))
            
            if "Present Value" in df.columns:
                plt.bar(df["Year"], df["Present Value"], color='steelblue', alpha=0.7)
                plt.title(f"Present Value of Medical Costs by Year\nEvaluee: {self.lcp.evaluee.name}")
                plt.ylabel("Present Value ($)")
            else:
                plt.bar(df["Year"], df["Total Nominal"], color='green', alpha=0.7)
                plt.title(f"Nominal Medical Costs by Year\nEvaluee: {self.lcp.evaluee.name}")
                plt.ylabel("Nominal Cost ($)")
            
            plt.xlabel("Year")
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save to temporary file
            temp_path = f"temp_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(temp_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return temp_path
        except Exception as e:
            print(f"Warning: Could not create chart: {e}")
            return None


class PDFExporter:
    """Export life care plan data to PDF format using ReportLab."""
    
    def __init__(self, calculator: CostCalculator):
        self.calculator = calculator
        self.lcp = calculator.lcp
    
    def export(self, file_path: str) -> None:
        """Export the life care plan to PDF file in landscape mode."""
        from reportlab.lib.pagesizes import letter, A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER

        # Create PDF document in landscape mode
        doc = SimpleDocTemplate(
            file_path,
            pagesize=landscape(letter),
            leftMargin=0.5*inch,
            rightMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            alignment=TA_CENTER,
            spaceAfter=20
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=30
        )

        story.append(Paragraph("Life Care Plan Economic Projection", title_style))
        story.append(Paragraph(f"Evaluee: {self.lcp.evaluee.name}", subtitle_style))
        story.append(Spacer(1, 20))
        
        # Enhanced Metadata
        story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"<b>Evaluee Age at Analysis Start:</b> {self.lcp.evaluee.current_age} years old (in {self.lcp.settings.base_year})", styles['Normal']))

        end_year = self.lcp.settings.base_year + int(self.lcp.settings.projection_years) - 1
        story.append(Paragraph(f"<b>Analysis Period:</b> {self.lcp.settings.projection_years} years "
                             f"({self.lcp.settings.base_year} to {end_year})", styles['Normal']))

        if self.lcp.evaluee.discount_calculations:
            story.append(Paragraph(f"<b>Discount Rate Applied:</b> {self.lcp.settings.discount_rate:.1%} annually", styles['Normal']))
            story.append(Paragraph("<b>Present Value Calculations:</b> Enabled", styles['Normal']))
        else:
            story.append(Paragraph("<b>Present Value Calculations:</b> Not Applied", styles['Normal']))

        story.append(Paragraph(f"<b>Service Categories Analyzed:</b> {len(self.lcp.tables)}", styles['Normal']))
        story.append(Paragraph(f"<b>Total Individual Services:</b> {sum(len(table.services) for table in self.lcp.tables.values())}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Summary statistics
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        summary_stats = self.calculator.calculate_summary_statistics()
        
        summary_data = [
            ['Financial Summary', 'Amount'],
            ['Total Lifetime Medical Costs (Nominal)', f"${summary_stats['total_nominal_cost']:,.0f}"],
            ['Average Annual Medical Costs', f"${summary_stats['average_annual_cost']:,.0f}"]
        ]

        if self.lcp.evaluee.discount_calculations:
            summary_data.append(['Total Lifetime Medical Costs (Present Value)', f"${summary_stats['total_present_value']:,.0f}"])
            savings = summary_stats['total_nominal_cost'] - summary_stats['total_present_value']
            summary_data.append(['Present Value Savings vs Nominal', f"${savings:,.0f}"])
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Category breakdown
        story.append(Paragraph("Cost Breakdown by Service Category", styles['Heading2']))
        category_costs = self.calculator.get_cost_by_category()

        if self.lcp.evaluee.discount_calculations:
            category_data = [['Service Category', 'Lifetime Cost (Nominal)', 'Lifetime Cost (Present Value)', 'Number of Services']]
            for table_name, data in category_costs.items():
                category_data.append([
                    table_name,
                    f"${data['table_nominal_total']:,.0f}",
                    f"${data['table_present_value_total']:,.0f}",
                    str(len(data['services']))
                ])
        else:
            category_data = [['Service Category', 'Total Lifetime Cost (Nominal)', 'Number of Services']]
            for table_name, data in category_costs.items():
                category_data.append([
                    table_name,
                    f"${data['table_nominal_total']:,.0f}",
                    str(len(data['services']))
                ])
        
        category_table = Table(category_data)
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(category_table)
        story.append(PageBreak())
        
        # Detailed cost schedule
        story.append(Paragraph("Annual Cost Schedule", styles['Heading2']))
        df = self.calculator.build_cost_schedule()

        # Prepare table data with improved headers
        if "Present Value" in df.columns:
            table_data = [['Year', 'Evaluee Age', 'Annual Cost (Nominal)', 'Annual Cost (Present Value)']]
            for _, row in df.iterrows():
                table_data.append([
                    str(int(row['Year'])),
                    str(int(row['Age'])),
                    f"${row['Total Nominal']:,.0f}",
                    f"${row['Present Value']:,.0f}"
                ])
        else:
            table_data = [['Year', 'Evaluee Age', 'Annual Medical Cost (Nominal)']]
            for _, row in df.iterrows():
                table_data.append([
                    str(int(row['Year'])),
                    str(int(row['Age'])),
                    f"${row['Total Nominal']:,.0f}"
                ])
        
        detail_table = Table(table_data)
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(detail_table)
        
        # Build PDF
        doc.build(story)