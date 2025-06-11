# Life Care Plan Table Generator - Web Application

An interactive, browser-based GUI for creating, calculating, and exporting life care plan cost projections with real-time updates and professional reporting capabilities.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Option 1: Quick install
pip install -r web_requirements.txt

# Option 2: Update all dependencies and check for issues
python update_dependencies.py
```

### 2. Launch Web Application
```bash
python run_web.py
```

### 3. Open in Browser
Navigate to: **http://localhost:8000**

## 📋 Features

### **Interactive Web Interface**
- **Modern, responsive design** - Works on desktop, tablet, and mobile
- **Step-by-step workflow** - Guided process from evaluee creation to export
- **Real-time calculations** - Instant updates as you add services
- **Professional charts** - Interactive Plotly visualizations

### **Evaluee Management**
- Create evaluee profiles with demographic information
- Set projection parameters (years, discount rates)
- Save and load configurations

### **Service Table Management**
- **Multiple service categories** - Organize services by type (medications, therapy, equipment, etc.)
- **Two service types:**
  - **Recurring Services** - Regular services with start/end years
  - **Discrete Services** - One-time events in specific years
- **Flexible pricing** - Custom inflation rates per service
- **Easy editing** - Add, modify, and remove services through forms

### **Advanced Calculations**
- **Inflation adjustments** - Individual inflation rates for each service
- **Present value calculations** - Discount future costs to current value
- **Summary statistics** - Total costs, averages, category breakdowns
- **Year-by-year projections** - Detailed cost schedules

### **Data Visualization**
- **Present Value Chart** - Bar chart showing costs by year
- **Nominal vs Present Value** - Comparison trends over time
- **Category Breakdown** - Cost distribution by service type
- **Interactive charts** - Zoom, pan, and export chart images

### **Export Capabilities**
- **Excel Reports** - Comprehensive spreadsheets with multiple worksheets
- **Word Documents** - Professional reports with charts and tables
- **PDF Reports** - Finalized documents ready for presentation
- **JSON Configuration** - Save/load life care plan configurations

### **File Management**
- **Upload configurations** - Load existing JSON configurations
- **Download configurations** - Save current work as JSON
- **Automatic file naming** - Includes evaluee name and timestamp
- **Temporary file cleanup** - Automatic cleanup of generated files

## 🎯 User Interface Guide

### **Navigation Sidebar**
- **Evaluee Information** - Create and configure evaluee
- **Service Tables** - Manage service categories and individual services
- **Calculations** - View results, charts, and detailed schedules
- **Export Results** - Download reports in multiple formats

### **Workflow**

#### **Step 1: Create Evaluee**
1. Enter evaluee name and current age
2. Set base year for projections (default: 2025)
3. Choose projection period (default: 30 years)
4. Set discount rate (default: 3%)
5. Click "Create Life Care Plan"

#### **Step 2: Add Service Tables**
1. Navigate to "Service Tables" section
2. Enter table name (e.g., "Medications", "Physical Therapy")
3. Click "Add Table"
4. Repeat for each service category

#### **Step 3: Add Services**
1. Click "Add Service" on any table
2. Fill in service details:
   - Service name
   - Unit cost
   - Frequency per year
   - Inflation rate
   - Service type (recurring or discrete)
3. For recurring: Set start and end years
4. For discrete: List specific occurrence years
5. Click "Add Service"

#### **Step 4: Calculate Costs**
1. Navigate to "Calculations" section
2. View summary statistics
3. Examine interactive charts
4. Review detailed cost schedule
5. Click "Recalculate" if you make changes

#### **Step 5: Export Results**
1. Navigate to "Export Results" section
2. Choose format: Excel, Word, or PDF
3. Download professional reports

## 🔧 Technical Details

### **Architecture**
- **Backend**: FastAPI (Python web framework)
- **Frontend**: HTML5, Bootstrap 5, JavaScript
- **Charts**: Plotly.js for interactive visualizations
- **Styling**: Modern CSS with gradient themes
- **File Handling**: Temporary file management with automatic cleanup

### **API Endpoints**
- `POST /api/create_evaluee` - Create new evaluee
- `POST /api/add_service_table` - Add service table
- `POST /api/add_service` - Add service to table
- `GET /api/calculate` - Calculate costs and generate charts
- `GET /api/export/{format}` - Export results (excel/word/pdf)
- `POST /api/upload_config` - Upload JSON configuration
- `GET /api/download_config` - Download current configuration
- `GET /api/current_data` - Get current life care plan data

### **Data Flow**
1. **User Input** → Forms and modals
2. **Client-side Validation** → JavaScript validation
3. **API Calls** → FastAPI backend processing
4. **Data Storage** → Server-side session management
5. **Calculations** → Cost calculation engine
6. **Visualization** → Plotly chart generation
7. **Export** → File generation and download

## 📁 File Structure

```
LCP_Table_Generator_Econ/
├── web_app.py              # FastAPI web application
├── run_web.py              # Application launcher
├── web_requirements.txt    # Web-specific dependencies
├── templates/
│   └── index.html          # Main web interface
├── static/
│   └── app.js              # Frontend JavaScript
├── temp_files/             # Temporary export files
└── src/                    # Core calculation modules
```

## 🎨 User Experience Features

### **Visual Design**
- **Professional gradient themes** - Modern, medical-appropriate styling
- **Intuitive navigation** - Clear section-based workflow
- **Responsive layout** - Works on all screen sizes
- **Loading indicators** - Visual feedback during calculations
- **Success/error alerts** - Clear user feedback

### **Interaction Design**
- **Modal forms** - Clean service entry dialogs
- **Real-time updates** - Dynamic table and chart updates
- **Keyboard shortcuts** - Efficient data entry
- **Form validation** - Prevent invalid data entry
- **Auto-save behavior** - Preserve work across sessions

### **Data Visualization**
- **Interactive charts** - Zoom, pan, hover details
- **Color-coded categories** - Easy visual distinction
- **Professional formatting** - Publication-ready charts
- **Multiple chart types** - Bar charts, line graphs
- **Export chart images** - Save charts separately

## 🔒 Security & Performance

### **Security Features**
- **Input validation** - Server-side validation of all inputs
- **File type restrictions** - Only JSON files for uploads
- **Temporary file cleanup** - Automatic removal of generated files
- **Safe file handling** - Secure file upload/download processes

### **Performance Optimizations**
- **Async processing** - Non-blocking server operations
- **Client-side caching** - Reduce redundant API calls
- **Efficient calculations** - Optimized mathematical operations
- **Responsive UI** - Smooth user interactions

## 🚨 Troubleshooting

### **Common Issues**

#### **Web server won't start**
```bash
# Check if port 8000 is in use
lsof -i :8000

# Try different port
uvicorn web_app:app --port 8080
```

#### **Dependencies missing**
```bash
# Install all requirements
pip install -r web_requirements.txt

# Check specific packages
pip list | grep fastapi
```

#### **Charts not displaying**
- Ensure JavaScript is enabled in browser
- Check browser console for errors
- Try refreshing the page

#### **Export files not downloading**
- Check browser download permissions
- Ensure temp_files directory is writable
- Try different export format

### **Browser Compatibility**
- **Recommended**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Required**: JavaScript enabled
- **Required**: Modern CSS support (Grid, Flexbox)
- **Charts**: Plotly.js v2.27.0 (latest stable version)

## 🔄 Development Mode

For development with auto-reload:
```bash
uvicorn web_app:app --reload --host 0.0.0.0 --port 8000
```

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review console errors in browser developer tools
3. Verify all dependencies are installed
4. Ensure proper file permissions

## 🎉 Example Workflow

1. **Launch**: `python run_web.py`
2. **Open**: http://localhost:8000
3. **Create**: Evaluee "John Doe, age 35"
4. **Add**: "Medications" table
5. **Add**: Service "Pain Medication, $200/month, 5% inflation"
6. **Calculate**: View $80,000+ present value
7. **Export**: Download professional Word report
8. **Save**: Download JSON configuration for future use

The web interface provides a complete, professional solution for life care plan economic analysis with an intuitive, modern user experience.