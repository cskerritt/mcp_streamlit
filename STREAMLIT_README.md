# Life Care Plan Table Generator - Streamlit Web Application

A modern, interactive Streamlit web application for creating, calculating, and exporting life care plan cost projections with inflation adjustments and present value calculations.

## 🌟 Features

- **🎯 Interactive Web Interface**: Modern, user-friendly Streamlit interface
- **👤 Evaluee Management**: Create and edit evaluee information with projection settings
- **📋 Advanced Service Management**: Add, edit, and organize medical services with flexible options
  - **💰 Cost Range Support**: Enter high/low cost estimates for uncertainty modeling
  - **📅 Flexible Timing**: Four service types including interactive year selection
  - **🔄 Real-time Updates**: Immediate cost calculations as you make changes
- **🧮 Comprehensive Calculations**: Instant cost calculations with inflation and present value adjustments
- **📊 Interactive Charts**: Dynamic visualizations using Plotly for cost projections
- **📄 Multiple Export Formats**: Export to Excel, Word, and PDF formats
- **💾 Configuration Management**: Save and load life care plan configurations as JSON files
- **📱 Responsive Design**: Works on desktop, tablet, and mobile devices

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd LCP_Table_Generator_Econ_Streamlit

# Install Streamlit dependencies
pip install -r streamlit_requirements.txt
```

### 2. Run the Application

```bash
# Start the Streamlit application
streamlit run streamlit_app.py
```

The application will open in your default web browser at `http://localhost:8501`

### 3. Getting Started

1. **Create an Evaluee**: Start by creating a new evaluee (person receiving care)
2. **Add Service Tables**: Create categories for different types of medical services
3. **Add Services**: Add specific medical services with costs, frequencies, and timing
4. **Calculate Costs**: View real-time cost projections and interactive charts
5. **Export Reports**: Generate professional reports in Excel, Word, or PDF format

## 📖 User Guide

### Navigation

The application uses a sidebar navigation with the following pages:

- **🏠 Home**: Overview and quick start options
- **👤 Create/Edit Evaluee**: Set up evaluee information and projection settings
- **📋 Manage Service Tables**: Create and manage service categories and individual services
- **🧮 Calculate & View Results**: View cost calculations, charts, and detailed schedules
- **📊 Export Reports**: Generate and download professional reports
- **💾 Load/Save Configurations**: Save your work and load existing configurations

### Creating a Life Care Plan

#### Step 1: Create Evaluee
- Enter the evaluee's name and current age
- Set the base year for projections (usually current year)
- Define the projection period (how many years to project)
- Set the discount rate for present value calculations
- Choose whether to enable present value calculations

#### Step 2: Add Service Tables
- Create categories for different types of services (e.g., "Medications", "Physician Visits")
- Set default inflation rates for each category

#### Step 3: Add Services
Choose from four service types and two cost input methods:

**Service Types:**
- **Recurring Services**: Regular services within a date range
  - Example: Annual check-ups from 2025 to 2050
- **Discrete Occurrences**: Services that occur only in specific years (text input)
  - Example: Surgery in 2027 and 2045
- **Specific Years**: Services that occur in selected years (interactive selector)
  - Example: Equipment replacements in 2025, 2030, 2035, 2040, 2045
- **One-time Costs**: Services that occur once in a specific year
  - Example: Home modifications in 2026

**Cost Input Methods:**
- **Single Cost**: Enter a specific unit cost
- **Cost Range**: Enter high and low estimates - the average is used as the unit cost
  - Useful when you have cost estimates with uncertainty
  - Example: Wheelchair cost range $3,000 - $4,000 (average: $3,500)

#### Step 4: Calculate and Review
- View summary statistics and key metrics
- Explore interactive charts showing cost projections over time
- Review detailed year-by-year cost schedules
- Analyze costs by service category

#### Step 5: Export Reports
- Generate Excel spreadsheets with detailed calculations
- Create Word documents with professional formatting
- Export PDF reports for presentations
- Download all formats as a ZIP file

## 📊 Understanding the Calculations

### Inflation Adjustment
Each service cost is adjusted for inflation using:
```
Adjusted Cost = Base Cost × (1 + Inflation Rate)^(Year - Base Year)
```

### Present Value Calculation
Future costs are discounted to present value using:
```
Present Value = Future Value ÷ (1 + Discount Rate)^(Year - Base Year)
```

### Service Types

1. **Recurring Services**: Use `start_year` and `end_year`
2. **Discrete Occurrences**: Use `occurrence_years` list
3. **One-time Costs**: Use `is_one_time_cost` and `one_time_cost_year`

## 💾 Configuration Files

The application uses JSON configuration files to save and load life care plans. These files contain:

- Evaluee information (name, age, settings)
- Service tables and their services
- All cost and timing parameters

Example configuration structure:
```json
{
  "evaluee_name": "John Doe",
  "current_age": 35,
  "base_year": 2025,
  "projection_years": 30,
  "discount_rate": 0.035,
  "tables": {
    "Medications": [
      {
        "name": "Daily Medication",
        "inflation_rate": 0.05,
        "unit_cost": 300.00,
        "frequency_per_year": 12,
        "start_year": 2025,
        "end_year": 2054
      }
    ]
  }
}
```

## 🔧 Technical Details

### Dependencies

- **Streamlit**: Web application framework
- **Pandas**: Data manipulation and analysis
- **Plotly**: Interactive charts and visualizations
- **Python-docx**: Word document generation
- **OpenPyXL**: Excel file handling
- **ReportLab**: PDF generation
- **Pydantic**: Data validation

### File Structure

```
streamlit_app.py          # Main Streamlit application
pages/
├── create_plan.py        # Evaluee creation and editing
├── manage_services.py    # Service table and service management
├── calculate_results.py  # Cost calculations and charts
├── export_reports.py     # Report generation and export
└── load_save.py         # Configuration management
src/                      # Core business logic (shared with CLI/FastAPI)
├── models.py            # Data models
├── calculator.py        # Cost calculation engine
└── exporters.py         # Export functionality
```

## 🆚 Comparison with Other Interfaces

This repository includes three different interfaces:

1. **Command Line Interface (CLI)**: `python main.py` - For batch processing and automation
2. **FastAPI Web Application**: `python run_web.py` - Full-featured web API with HTML templates
3. **Streamlit Application**: `streamlit run streamlit_app.py` - Modern, interactive web interface

### When to Use Streamlit

- **Interactive Analysis**: Best for exploring data and trying different scenarios
- **User-Friendly Interface**: Ideal for non-technical users
- **Quick Prototyping**: Rapid development and iteration
- **Data Visualization**: Excellent built-in charting capabilities
- **Responsive Design**: Works well on different screen sizes

## 🐛 Troubleshooting

### Common Issues

1. **Port Already in Use**: If port 8501 is busy, Streamlit will automatically try the next available port
2. **Missing Dependencies**: Run `pip install -r streamlit_requirements.txt` to install all required packages
3. **File Upload Issues**: Ensure uploaded JSON files are valid and follow the expected format
4. **Export Errors**: Check that you have write permissions and sufficient disk space

### Getting Help

- Check the built-in help text and tooltips in the application
- Review the configuration format documentation in the Load/Save page
- Use the sample data to understand the expected workflow
- Check the console output for detailed error messages

## 📝 License

This project is provided as-is for educational and professional use in life care planning and economic analysis.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests to improve the application.
