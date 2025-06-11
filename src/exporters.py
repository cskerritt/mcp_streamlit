import pandas as pd
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
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
        """Export the life care plan to Excel file."""
        df = self.calculator.build_cost_schedule()
        summary_stats = self.calculator.calculate_summary_statistics()
        category_costs = self.calculator.get_cost_by_category()
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Main cost schedule
            df.to_excel(writer, sheet_name='Cost Schedule', index=False)
            
            # Enhanced Summary statistics
            summary_data = [
                ['Evaluee Name', self.lcp.evaluee.name],
                ['Current Age', f"{self.lcp.evaluee.current_age} years"],
                ['Base Year', self.lcp.settings.base_year],
                ['Projection Period', f"{self.lcp.settings.projection_years} years ({summary_stats['projection_period']})"],
                ['Total Nominal Cost', f"${summary_stats['total_nominal_cost']:,.2f}"],
                ['Average Annual Cost', f"${summary_stats['average_annual_cost']:,.2f}"],
            ]
            
            # Only include discount rate info if calculations are enabled
            if self.lcp.evaluee.discount_calculations:
                summary_data.extend([
                    ['Discount Rate', f"{summary_stats['discount_rate']:.2f}%"],
                    ['Total Present Value', f"${summary_stats['total_present_value']:,.2f}"],
                    ['Present Value Calculations', 'Enabled']
                ])
            else:
                summary_data.append(['Present Value Calculations', 'Disabled'])
            
            summary_data.extend([
                ['Report Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                ['Number of Service Categories', len(self.lcp.tables)],
                ['Total Number of Services', sum(len(table.services) for table in self.lcp.tables.values())]
            ])
            
            summary_df = pd.DataFrame(summary_data, columns=['Metric', 'Value'])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Enhanced Category breakdown
            category_rows = []
            if self.lcp.evaluee.discount_calculations:
                category_columns = ['Category', 'Total Nominal', 'Total Present Value', 'Service Count']
                for table_name, data in category_costs.items():
                    category_rows.append([
                        table_name, 
                        f"${data['table_nominal_total']:,.2f}",
                        f"${data['table_present_value_total']:,.2f}",
                        len(data['services'])
                    ])
            else:
                category_columns = ['Category', 'Total Nominal', 'Service Count']
                for table_name, data in category_costs.items():
                    category_rows.append([
                        table_name, 
                        f"${data['table_nominal_total']:,.2f}",
                        len(data['services'])
                    ])
            
            category_df = pd.DataFrame(category_rows, columns=category_columns)
            category_df.to_excel(writer, sheet_name='Category Summary', index=False)
            
            # Detailed Service Information
            service_rows = []
            service_columns = ['Category', 'Service Name', 'Unit Cost', 'Frequency/Year', 'Inflation Rate %', 
                              'Service Type', 'Start Year', 'End Year', 'Total Nominal']
            
            if self.lcp.evaluee.discount_calculations:
                service_columns.append('Total Present Value')
            
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
                        service['frequency_per_year'],
                        f"{service['inflation_rate']:.2f}%",
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
        """Export the life care plan to Word document."""
        doc = Document()
        
        # Title and header information
        title = doc.add_heading(f"Life Care Plan Projection for {self.lcp.evaluee.name}", level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Enhanced Document metadata
        doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_paragraph(f"Evaluee age at {self.lcp.settings.base_year}: {self.lcp.evaluee.current_age} years")
        doc.add_paragraph(f"Projection period: {self.lcp.settings.projection_years} years "
                         f"({self.lcp.settings.base_year} to {self.lcp.settings.base_year + int(self.lcp.settings.projection_years) - 1})")
        
        if self.lcp.evaluee.discount_calculations:
            doc.add_paragraph(f"Discount rate: {self.lcp.settings.discount_rate:.2%}")
            doc.add_paragraph("Present value calculations: Enabled")
        else:
            doc.add_paragraph("Present value calculations: Disabled")
            
        doc.add_paragraph(f"Total service categories: {len(self.lcp.tables)}")
        doc.add_paragraph(f"Total services: {sum(len(table.services) for table in self.lcp.tables.values())}")
        
        # Summary statistics
        doc.add_heading("Executive Summary", level=2)
        summary_stats = self.calculator.calculate_summary_statistics()
        
        summary_para = doc.add_paragraph()
        summary_para.add_run(f"Total Nominal Cost: ${summary_stats['total_nominal_cost']:,.2f}\n").bold = True
        summary_para.add_run(f"Average Annual Cost: ${summary_stats['average_annual_cost']:,.2f}\n").bold = True
        
        if self.lcp.evaluee.discount_calculations:
            summary_para.add_run(f"Total Present Value: ${summary_stats['total_present_value']:,.2f}\n").bold = True
        
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
        doc.add_heading("Detailed Cost Schedule", level=2)
        
        df = self.calculator.build_cost_schedule()
        
        # Create table with proper formatting
        table = doc.add_table(rows=1, cols=len(df.columns))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = 'Table Grid'
        
        # Header row
        hdr_cells = table.rows[0].cells
        for idx, col in enumerate(df.columns):
            hdr_cells[idx].text = str(col)
            hdr_cells[idx].paragraphs[0].runs[0].bold = True
        
        # Data rows
        for _, row in df.iterrows():
            row_cells = table.add_row().cells
            for idx, col in enumerate(df.columns):
                value = row[col]
                if isinstance(value, (int, float)) and col not in ['Year', 'Age']:
                    row_cells[idx].text = f"${value:,.2f}"
                else:
                    row_cells[idx].text = str(value)
        
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
        """Export the life care plan to PDF file."""
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        
        # Create PDF document
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        story.append(Paragraph(f"Life Care Plan Projection for {self.lcp.evaluee.name}", title_style))
        story.append(Spacer(1, 20))
        
        # Enhanced Metadata
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"<b>Evaluee age at {self.lcp.settings.base_year}:</b> {self.lcp.evaluee.current_age} years", styles['Normal']))
        story.append(Paragraph(f"<b>Projection period:</b> {self.lcp.settings.projection_years} years "
                             f"({self.lcp.settings.base_year} to {self.lcp.settings.base_year + int(self.lcp.settings.projection_years) - 1})", styles['Normal']))
        
        if self.lcp.evaluee.discount_calculations:
            story.append(Paragraph(f"<b>Discount rate:</b> {self.lcp.settings.discount_rate:.2%}", styles['Normal']))
            story.append(Paragraph("<b>Present value calculations:</b> Enabled", styles['Normal']))
        else:
            story.append(Paragraph("<b>Present value calculations:</b> Disabled", styles['Normal']))
        
        story.append(Paragraph(f"<b>Total service categories:</b> {len(self.lcp.tables)}", styles['Normal']))
        story.append(Paragraph(f"<b>Total services:</b> {sum(len(table.services) for table in self.lcp.tables.values())}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Summary statistics
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        summary_stats = self.calculator.calculate_summary_statistics()
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Nominal Cost', f"${summary_stats['total_nominal_cost']:,.2f}"],
            ['Average Annual Cost', f"${summary_stats['average_annual_cost']:,.2f}"]
        ]
        
        if self.lcp.evaluee.discount_calculations:
            summary_data.append(['Total Present Value', f"${summary_stats['total_present_value']:,.2f}"])
        
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
        story.append(Paragraph("Cost Breakdown by Category", styles['Heading2']))
        category_costs = self.calculator.get_cost_by_category()
        
        category_data = [['Category', 'Total Nominal', 'Total Present Value', 'Service Count']]
        for table_name, data in category_costs.items():
            category_data.append([
                table_name,
                f"${data['table_nominal_total']:,.2f}",
                f"${data['table_present_value_total']:,.2f}",
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
        story.append(Paragraph("Detailed Cost Schedule", styles['Heading2']))
        df = self.calculator.build_cost_schedule()
        
        # Prepare table data (conditional columns based on PV calculations)
        if "Present Value" in df.columns:
            table_data = [['Year', 'Age', 'Total Nominal', 'Present Value']]
            for _, row in df.iterrows():
                table_data.append([
                    str(row['Year']),
                    str(row['Age']),
                    f"${row['Total Nominal']:,.2f}",
                    f"${row['Present Value']:,.2f}"
                ])
        else:
            table_data = [['Year', 'Age', 'Total Nominal']]
            for _, row in df.iterrows():
                table_data.append([
                    str(row['Year']),
                    str(row['Age']),
                    f"${row['Total Nominal']:,.2f}"
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