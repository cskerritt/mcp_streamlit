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
                        f"{service['frequency_per_year']}x per year",
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
        end_year = self.lcp.settings.base_year + int(self.lcp.settings.projection_years) - 1
        metadata_para.add_run(f"{self.lcp.settings.projection_years} years ({self.lcp.settings.base_year} to {end_year})\n")

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
        
        # Category breakdown
        doc.add_heading("Cost Breakdown by Category", level=2)
        category_costs = self.calculator.get_cost_by_category()
        
        for table_name, data in category_costs.items():
            doc.add_heading(table_name, level=3)
            para = doc.add_paragraph()
            para.add_run(f"Total Nominal: ${data['table_nominal_total']:,.2f}\n")
            
            if self.lcp.evaluee.discount_calculations:
                para.add_run(f"Total Present Value: ${data['table_present_value_total']:,.2f}\n")
            
            para.add_run(f"Number of Services: {len(data['services'])}\n\n")
            
            if data['services']:
                para.add_run("Services included:\n").bold = True
                for service in data['services']:
                    service_type = 'One-time' if service['is_one_time_cost'] else \
                                  'Discrete' if service['occurrence_years'] else 'Recurring'
                    
                    if service['occurrence_years']:
                        service_type += f" ({len(service['occurrence_years'])} occurrences)"
                        years_info = f"Years: {min(service['occurrence_years'])}-{max(service['occurrence_years'])}"
                    elif service['is_one_time_cost']:
                        years_info = f"Year: {service['one_time_cost_year']}"
                    else:
                        start_yr = service['start_year'] if service['start_year'] else 'N/A'
                        end_yr = service['end_year'] if service['end_year'] else 'N/A'
                        years_info = f"Years: {start_yr}-{end_yr}"
                    
                    para.add_run(f"  • {service['name']}: ${service['unit_cost']:,.2f} "
                               f"({service['frequency_per_year']}x/year, {service['inflation_rate']:.1f}% inflation, "
                               f"{service_type}, {years_info})\n"
                               f"    Total Nominal: ${service['nominal_total']:,.2f}")
                    
                    if self.lcp.evaluee.discount_calculations:
                        para.add_run(f", Total PV: ${service['present_value_total']:,.2f}")
                    
                    para.add_run("\n")
        
        # Detailed cost schedule table
        doc.add_page_break()
        doc.add_heading("Annual Cost Schedule", level=2)

        df = self.calculator.build_cost_schedule()

        # Create table with improved headers and formatting for landscape
        improved_headers = {
            'Year': 'Year',
            'Age': 'Evaluee Age',
            'Total Nominal': 'Annual Cost (Nominal)',
            'Present Value': 'Annual Cost (Present Value)',
            'Cumulative Nominal': 'Cumulative Cost (Nominal)',
            'Cumulative PV': 'Cumulative Cost (Present Value)'
        }

        # Create table with proper formatting
        table = doc.add_table(rows=1, cols=len(df.columns))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = 'Table Grid'

        # Set column widths for better fit in landscape
        for i, col in enumerate(table.columns):
            if i == 0:  # Year column
                col.width = Inches(0.8)
            elif i == 1:  # Age column
                col.width = Inches(1.0)
            else:  # Cost columns
                col.width = Inches(1.8)

        # Header row with improved names
        hdr_cells = table.rows[0].cells
        for idx, col in enumerate(df.columns):
            header_text = improved_headers.get(col, col)
            hdr_cells[idx].text = header_text
            hdr_cells[idx].paragraphs[0].runs[0].bold = True
            # Center align headers
            hdr_cells[idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Data rows with improved formatting
        for _, row in df.iterrows():
            row_cells = table.add_row().cells
            for idx, col in enumerate(df.columns):
                value = row[col]
                if isinstance(value, (int, float)) and col not in ['Year', 'Age']:
                    row_cells[idx].text = f"${value:,.0f}"  # Remove decimals for cleaner look
                else:
                    row_cells[idx].text = str(int(value) if isinstance(value, float) and value.is_integer() else value)
                # Center align all data
                row_cells[idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add chart if requested
        if include_chart:
            chart_path = self._create_chart()
            if chart_path and os.path.exists(chart_path):
                doc.add_page_break()
                doc.add_heading("Present Value Chart", level=2)
                doc.add_picture(chart_path, width=Inches(6))
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