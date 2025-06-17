// Global variables
let currentEvaluee = null;
let currentTables = {};
let lastCalculationResults = null;
// Template system removed - users create their own tables
let appSettings = {
    defaultBaseYear: 2025,
    defaultProjectionYears: 30,
    defaultDiscountRate: 3.5,
    autoCalculate: true,
    showWelcome: true
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏥 Life Care Plan Table Generator initialized');
    console.log('📊 Using Plotly.js v2.27.0 for charts');
    
    // Set up event listeners
    document.getElementById('evalueeForm').addEventListener('submit', createEvaluee);
    document.getElementById('serviceForm').addEventListener('submit', function(e) { e.preventDefault(); });
    document.getElementById('configFile').addEventListener('change', uploadConfig);
    
    // Load any existing data
    loadCurrentData();
    
    // Show welcome message if enabled
    if (appSettings.showWelcome) {
        showAlert('Welcome to Life Care Plan Table Generator! Click "Load Sample Data" to get started quickly.', 'info');
    }
    
    // Load application settings
    loadApplicationSettings();
    
    // Auto-load saved plans on startup
    loadSavedPlans();
});

// Navigation functions
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.style.display = 'none';
    });
    
    // Remove active class from all nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // Show selected section
    document.getElementById(sectionName + '-section').style.display = 'block';
    
    // Add active class to selected nav link
    document.querySelector(`a[href="#${sectionName}-section"]`).classList.add('active');
    
    // Auto-calculate if showing calculations section
    if (sectionName === 'calculations' && currentEvaluee) {
        calculateCosts();
    }
    
    // Auto-refresh growth rates if showing growth rates section
    if (sectionName === 'growth-rates' && currentEvaluee) {
        refreshGrowthRates();
    }
    
    // Update dashboard if showing dashboard
    if (sectionName === 'dashboard') {
        updateDashboard();
    }
    
    // Load settings if showing settings
    if (sectionName === 'settings') {
        updateSettingsSection();
    }
}

// Alert functions
function showAlert(message, type = 'info', autoHide = true) {
    const alertContainer = document.getElementById('alert-container');
    const alertId = 'alert-' + Date.now();
    
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" id="${alertId}">
            <i class="fas fa-${getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    if (autoHide && type === 'success') {
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                alert.remove();
            }
        }, 3000);
    }
}

function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Evaluee management
async function createEvaluee(event) {
    event.preventDefault();
    
    const formData = new FormData();
    formData.append('name', document.getElementById('evaluee_name').value);
    formData.append('age', document.getElementById('current_age').value);
    formData.append('base_year', document.getElementById('base_year').value);
    formData.append('projection_years', document.getElementById('projection_years').value);
    formData.append('discount_rate', parseFloat(document.getElementById('discount_rate').value) / 100);
    formData.append('discount_calculations', document.getElementById('discount_calculations').checked);
    
    try {
        const response = await fetch('/api/create_evaluee', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentEvaluee = result.evaluee;
            showAlert(result.message, 'success');
            updateTablesSection();
            updateEvalueeDisplay();
            updateDashboard();
            showSection('dashboard');
        } else {
            showAlert('Error creating evaluee: ' + result.message, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}

// Evaluee management
function editEvaluee() {
    if (!currentEvaluee) {
        showAlert('No evaluee to edit', 'warning');
        return;
    }
    
    // Populate form with current data
    document.getElementById('evaluee_name').value = currentEvaluee.name;
    document.getElementById('current_age').value = currentEvaluee.age;
    document.getElementById('base_year').value = currentEvaluee.base_year;
    document.getElementById('projection_years').value = currentEvaluee.projection_years;
    document.getElementById('discount_rate').value = (currentEvaluee.discount_rate * 100).toFixed(2);
    document.getElementById('discount_calculations').checked = currentEvaluee.discount_calculations;
    
    // Show form and update button text
    document.getElementById('evaluee-info-container').style.display = 'none';
    document.getElementById('evaluee-form-container').style.display = 'block';
    document.getElementById('save-evaluee-btn').innerHTML = '<i class="fas fa-save me-2"></i>Update Life Care Plan';
    document.getElementById('cancel-evaluee-btn').style.display = 'inline-block';
    
    showAlert('Editing evaluee information', 'info');
}

function cancelEvalueeEdit() {
    // Hide form and show info
    document.getElementById('evaluee-form-container').style.display = 'none';
    document.getElementById('evaluee-info-container').style.display = 'block';
    document.getElementById('save-evaluee-btn').innerHTML = '<i class="fas fa-save me-2"></i>Create Life Care Plan';
    document.getElementById('cancel-evaluee-btn').style.display = 'none';
    
    // Reset form
    document.getElementById('evalueeForm').reset();
}

async function deleteEvaluee() {
    if (!currentEvaluee) {
        showAlert('No evaluee to delete', 'warning');
        return;
    }
    
    const confirmMessage = `Are you sure you want to delete "${currentEvaluee.name}" and all associated data?\n\nThis action cannot be undone and will remove:\n- All service tables\n- All services\n- All calculations\n- All settings`;
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    try {
        const response = await fetch('/api/delete_evaluee', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Clear all data
            currentEvaluee = null;
            currentTables = {};
            lastCalculationResults = null;
            
            // Reset UI
            updateEvalueeDisplay();
            updateTablesSection();
            updateDashboard();
            document.getElementById('evaluee-form-container').style.display = 'block';
            document.getElementById('evaluee-info-container').style.display = 'none';
            document.getElementById('save-evaluee-btn').innerHTML = '<i class="fas fa-save me-2"></i>Create Life Care Plan';
            document.getElementById('cancel-evaluee-btn').style.display = 'none';
            document.getElementById('evalueeForm').reset();
            
            showAlert(result.message, 'success');
            showSection('dashboard');
        } else {
            showAlert('Error deleting evaluee: ' + result.message, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}

// Table management
function updateTablesSection() {
    const container = document.getElementById('tables-container');
    
    if (!currentEvaluee) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                Create an evaluee first, then add service tables and services.
            </div>
        `;
        return;
    }
    
    if (Object.keys(currentTables).length === 0) {
        container.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                No service tables created yet. Add your first table above.
            </div>
        `;
        return;
    }
    
    let html = '';
    for (const [tableName, services] of Object.entries(currentTables)) {
        html += createTableCard(tableName, services);
    }
    
    container.innerHTML = html;
}

function createTableCard(tableName, services) {
    let servicesHtml = '';
    
    if (services.length === 0) {
        servicesHtml = `
            <div class="alert alert-info mb-0">
                <i class="fas fa-info-circle me-2"></i>
                No services in this table yet.
            </div>
        `;
    } else {
        services.forEach((service, index) => {
            // Build cost display
            let costDisplay;
            if (service.use_cost_range) {
                costDisplay = `$${service.cost_range_low.toFixed(2)} - $${service.cost_range_high.toFixed(2)} (avg: $${service.unit_cost.toFixed(2)})`;
            } else {
                costDisplay = `$${service.unit_cost.toFixed(2)}`;
            }
            
            // Build timing info
            let typeInfo;
            let badgeColor;
            if (service.type === 'one_time') {
                typeInfo = `One-time cost in ${service.one_time_cost_year}`;
                badgeColor = 'danger';
            } else if (service.type === 'discrete') {
                typeInfo = `Occurs: ${service.occurrence_years.join(', ')}`;
                badgeColor = 'warning';
            } else {
                typeInfo = `${service.start_year} - ${service.end_year}`;
                badgeColor = 'primary';
            }
            
            // Build frequency display
            const frequencyDisplay = service.is_one_time_cost ? 'One-time' : `${parseFloat(service.frequency_per_year).toFixed(1)}/year`;
            
            servicesHtml += `
                <div class="service-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${service.name}</h6>
                            <p class="mb-1 text-muted">
                                ${costDisplay} × ${frequencyDisplay}
                                | ${service.inflation_rate.toFixed(2)}% inflation
                            </p>
                            <small class="text-muted">${typeInfo}</small>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge bg-${badgeColor} service-type-badge">
                                ${service.type.replace('_', ' ')}
                            </span>
                            <button class="btn btn-outline-primary btn-sm" onclick="editService('${tableName}', ${index})" title="Edit Service">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-outline-danger btn-sm" onclick="deleteService('${tableName}', ${index})" title="Delete Service">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
    }
    
    return `
        <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">${tableName}</h5>
                <button class="btn btn-primary btn-sm" onclick="openServiceModal('${tableName}')">
                    <i class="fas fa-plus me-1"></i>Add Service
                </button>
            </div>
            <div class="card-body">
                ${servicesHtml}
            </div>
        </div>
    `;
}

async function addTable(event) {
    event.preventDefault();
    
    const tableName = document.getElementById('new_table_name').value.trim();
    const inflationRate = parseFloat(document.getElementById('table_inflation_rate').value);
    
    if (!tableName) {
        showAlert('Please enter a table name', 'warning');
        return;
    }
    
    if (!currentEvaluee) {
        showAlert('Please create an evaluee first', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('table_name', tableName);
    formData.append('default_inflation_rate', inflationRate);
    
    try {
        const response = await fetch('/api/add_service_table', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentTables[tableName] = [];
            document.getElementById('new_table_name').value = '';
            document.getElementById('table_inflation_rate').value = '3.5';
            updateTablesSection();
            showAlert(result.message, 'success');
        } else {
            showAlert('Error adding table: ' + result.message, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}

// Service management
function openServiceModal(tableName) {
    // Reset editing state
    editingService = null;
    document.querySelector('#serviceModal .modal-title').textContent = 'Add Service';
    document.getElementById('submit-service-btn').textContent = 'Add Service';
    
    document.getElementById('service_table_name').value = tableName;
    document.getElementById('serviceForm').reset();
    document.getElementById('service_type').value = '';
    toggleServiceFields();
    
    // Reset cost range and one-time cost states
    document.getElementById('use_cost_range').checked = false;
    document.getElementById('is_one_time_cost').checked = false;
    toggleCostRange();
    toggleOneTimeCost();
    
    // Set default years based on evaluee settings
    if (currentEvaluee) {
        document.getElementById('start_year').value = currentEvaluee.base_year;
        document.getElementById('end_year').value = currentEvaluee.base_year + Math.floor(currentEvaluee.projection_years) - 1;
    }
    
    // Set default inflation rate (default to 3.5% if table doesn't have one stored)
    document.getElementById('inflation_rate').value = 3.5;
    
    // Add event listeners for cost range inputs
    document.getElementById('cost_range_low').addEventListener('input', updateCostAverage);
    document.getElementById('cost_range_high').addEventListener('input', updateCostAverage);
    
    const modal = new bootstrap.Modal(document.getElementById('serviceModal'));
    modal.show();
}

function toggleServiceFields() {
    const serviceType = document.getElementById('service_type').value;
    const recurringFields = document.getElementById('recurring-fields');
    const discreteFields = document.getElementById('discrete-fields');
    
    if (serviceType === 'recurring') {
        recurringFields.style.display = 'block';
        discreteFields.style.display = 'none';
        // Initialize duration fields with current evaluee data
        initializeDurationFields();
    } else if (serviceType === 'discrete') {
        recurringFields.style.display = 'none';
        discreteFields.style.display = 'block';
        // Set default discrete years based on evaluee settings
        if (currentEvaluee) {
            document.getElementById('discrete_start_year').value = currentEvaluee.base_year;
            document.getElementById('discrete_end_year').value = currentEvaluee.base_year + Math.floor(currentEvaluee.projection_years) - 1;
            updateDiscreteYearOptions();
        }
    } else {
        recurringFields.style.display = 'none';
        discreteFields.style.display = 'none';
    }
}

function toggleCostRange() {
    const useCostRange = document.getElementById('use_cost_range').checked;
    const singleCostInput = document.getElementById('single-cost-input');
    const costRangeInputs = document.getElementById('cost-range-inputs');
    const unitCostInput = document.getElementById('unit_cost');
    
    if (useCostRange) {
        singleCostInput.style.display = 'none';
        costRangeInputs.style.display = 'block';
        unitCostInput.required = false;
        document.getElementById('cost_range_low').required = true;
        document.getElementById('cost_range_high').required = true;
    } else {
        singleCostInput.style.display = 'block';
        costRangeInputs.style.display = 'none';
        unitCostInput.required = true;
        document.getElementById('cost_range_low').required = false;
        document.getElementById('cost_range_high').required = false;
    }
    
    updateCostAverage();
}

function updateCostAverage() {
    const lowCost = parseFloat(document.getElementById('cost_range_low').value) || 0;
    const highCost = parseFloat(document.getElementById('cost_range_high').value) || 0;
    const average = (lowCost + highCost) / 2;
    document.getElementById('cost-average').textContent = average.toFixed(2);
}

// Duration-based year calculation functions
function initializeDurationFields() {
    if (!currentEvaluee) return;
    
    // Set default values based on current evaluee
    const baseYear = currentEvaluee.base_year;
    const projectionYears = currentEvaluee.projection_years;
    
    // Default to full projection period if no duration set
    if (!document.getElementById('service_duration_years').value) {
        document.getElementById('service_duration_years').value = projectionYears;
    }
    
    // Set start year to base year if not set
    if (!document.getElementById('start_year').value) {
        document.getElementById('start_year').value = baseYear;
    }
    
    // Calculate end year if duration is set
    calculateYearsFromDuration();
}

function calculateYearsFromDuration() {
    if (!currentEvaluee) {
        showAlert('Please create an evaluee first', 'warning');
        return;
    }
    
    const duration = parseFloat(document.getElementById('service_duration_years').value);
    const startOffset = parseFloat(document.getElementById('duration_start_offset').value) || 0;
    const baseYear = currentEvaluee.base_year;
    const maxProjectionYear = baseYear + Math.floor(currentEvaluee.projection_years) - 1;
    
    if (!duration || duration <= 0) {
        document.getElementById('duration-preview').style.display = 'none';
        return;
    }
    
    // Calculate start and end years
    const startYear = baseYear + Math.floor(startOffset);
    const endYear = startYear + Math.floor(duration) - 1;
    
    // Validate against projection period
    if (endYear > maxProjectionYear) {
        const adjustedEndYear = maxProjectionYear;
        const adjustedDuration = adjustedEndYear - startYear + 1;
        
        showAlert(`Duration adjusted: Service extends beyond projection period (${maxProjectionYear}). Duration reduced to ${adjustedDuration} years.`, 'info');
        
        document.getElementById('service_duration_years').value = adjustedDuration;
        document.getElementById('start_year').value = startYear;
        document.getElementById('end_year').value = adjustedEndYear;
        
        updateDurationPreview(startYear, adjustedEndYear, adjustedDuration);
    } else {
        // Set the calculated values
        document.getElementById('start_year').value = startYear;
        document.getElementById('end_year').value = endYear;
        
        updateDurationPreview(startYear, endYear, duration);
    }
}

function updateDurationFromYears() {
    const startYear = parseInt(document.getElementById('start_year').value);
    const endYear = parseInt(document.getElementById('end_year').value);
    
    if (startYear && endYear && endYear >= startYear) {
        const duration = endYear - startYear + 1;
        const startOffset = startYear - (currentEvaluee ? currentEvaluee.base_year : 2025);
        
        document.getElementById('service_duration_years').value = duration;
        document.getElementById('duration_start_offset').value = Math.max(0, startOffset);
        
        updateDurationPreview(startYear, endYear, duration);
    }
}

function updateDurationPreview(startYear, endYear, duration) {
    if (!currentEvaluee) return;
    
    const startAge = currentEvaluee.age + (startYear - currentEvaluee.base_year);
    const endAge = currentEvaluee.age + (endYear - currentEvaluee.base_year);
    
    const previewText = `Service will run for ${duration} year${duration !== 1 ? 's' : ''} from ${startYear} to ${endYear} (age ${startAge.toFixed(1)} to ${endAge.toFixed(1)})`;
    
    document.getElementById('duration-preview-text').textContent = previewText;
    document.getElementById('duration-preview').style.display = 'block';
}

function toggleOneTimeCost() {
    const isOneTimeCost = document.getElementById('is_one_time_cost').checked;
    const frequencyInput = document.getElementById('frequency_per_year');
    const oneTimeFields = document.getElementById('one-time-fields');
    const serviceTypeSelect = document.getElementById('service_type');
    const recurringFields = document.getElementById('recurring-fields');
    const discreteFields = document.getElementById('discrete-fields');
    
    if (isOneTimeCost) {
        // Hide service type selection and related fields
        serviceTypeSelect.disabled = true;
        serviceTypeSelect.required = false;
        recurringFields.style.display = 'none';
        discreteFields.style.display = 'none';
        
        // Show one-time cost fields
        oneTimeFields.style.display = 'block';
        document.getElementById('one_time_cost_year').required = true;
        
        // Set frequency to 1 and make it readonly
        frequencyInput.value = 1;
        frequencyInput.readOnly = true;
        
        // Set default year
        if (currentEvaluee) {
            document.getElementById('one_time_cost_year').value = currentEvaluee.base_year;
        }
    } else {
        // Re-enable service type selection
        serviceTypeSelect.disabled = false;
        serviceTypeSelect.required = true;
        
        // Hide one-time cost fields
        oneTimeFields.style.display = 'none';
        document.getElementById('one_time_cost_year').required = false;
        
        // Reset frequency input
        frequencyInput.readOnly = false;
        frequencyInput.value = '';
        
        // Re-show appropriate service type fields
        toggleServiceFields();
    }
}

// Cost range event listeners will be added when modal opens

// Global variable to track if we're editing a service
let editingService = null;

function editService(tableName, serviceIndex) {
    const services = currentTables[tableName];
    const service = services[serviceIndex];
    
    if (!service) {
        showAlert('Service not found', 'danger');
        return;
    }
    
    // Set editing mode
    editingService = { tableName, serviceIndex };
    
    // Populate form with service data
    document.getElementById('service_table_name').value = tableName;
    document.getElementById('service_name').value = service.name;
    document.getElementById('unit_cost').value = service.unit_cost;
    document.getElementById('frequency_per_year').value = service.frequency_per_year;
    document.getElementById('inflation_rate').value = service.inflation_rate;
    document.getElementById('service_type').value = service.type;
    
    // Update UI for editing mode
    document.querySelector('#serviceModal .modal-title').textContent = 'Edit Service';
    document.getElementById('submit-service-btn').textContent = 'Update Service';
    
    // Show appropriate fields and populate them
    toggleServiceFields();
    
    if (service.type === 'recurring') {
        document.getElementById('start_year').value = service.start_year;
        document.getElementById('end_year').value = service.end_year;
    } else if (service.type === 'discrete') {
        // Find the min/max years from occurrence_years
        const occurrenceYears = service.occurrence_years;
        if (occurrenceYears && occurrenceYears.length > 0) {
            const minYear = Math.min(...occurrenceYears);
            const maxYear = Math.max(...occurrenceYears);
            document.getElementById('discrete_start_year').value = minYear;
            document.getElementById('discrete_end_year').value = maxYear;
            updateDiscreteYearOptions();
            
            // Check the appropriate checkboxes
            setTimeout(() => {
                occurrenceYears.forEach(year => {
                    const checkbox = document.getElementById(`year_${year}`);
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
                updateOccurrenceYears();
            }, 100);
        }
    }
    
    const modal = new bootstrap.Modal(document.getElementById('serviceModal'));
    modal.show();
}

function updateDiscreteYearOptions() {
    const startYear = parseInt(document.getElementById('discrete_start_year').value);
    const endYear = parseInt(document.getElementById('discrete_end_year').value);
    const container = document.getElementById('discrete-year-checkboxes');
    
    if (!startYear || !endYear || startYear > endYear) {
        container.innerHTML = '<p class="text-muted">Please set valid start and end years</p>';
        return;
    }
    
    let html = '<div class="row">';
    for (let year = startYear; year <= endYear; year++) {
        html += `
            <div class="col-md-3 col-sm-4 col-6 mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="year_${year}" value="${year}" onchange="updateOccurrenceYears()">
                    <label class="form-check-label" for="year_${year}">
                        ${year}
                    </label>
                </div>
            </div>
        `;
    }
    html += '</div>';
    
    container.innerHTML = html;
}

function updateOccurrenceYears() {
    const checkboxes = document.querySelectorAll('#discrete-year-checkboxes input[type="checkbox"]:checked');
    const years = Array.from(checkboxes).map(cb => cb.value).sort((a, b) => parseInt(a) - parseInt(b));
    document.getElementById('occurrence_years').value = years.join(',');
}

async function deleteService(tableName, serviceIndex) {
    if (!confirm('Are you sure you want to delete this service?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/delete_service', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `table_name=${encodeURIComponent(tableName)}&service_index=${serviceIndex}`
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(result.message, 'success');
            loadCurrentData(); // Refresh data
        } else {
            showAlert('Error deleting service: ' + result.message, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}

async function submitService() {
    const form = document.getElementById('serviceForm');
    const formData = new FormData(form);
    
    // Debug: Log all form data
    console.log('DEBUG: Form submission data:');
    for (let [key, value] of formData.entries()) {
        console.log(`  ${key}: ${value}`);
    }
    
    // Validate required fields
    const serviceName = formData.get('service_name');
    const tableName = formData.get('table_name');
    const frequency = formData.get('frequency_per_year');
    const inflationRate = formData.get('inflation_rate');
    
    console.log('DEBUG: Key fields:', {serviceName, tableName, frequency, inflationRate});
    
    if (!serviceName || !tableName || !frequency || !inflationRate) {
        showAlert('Please fill in all required fields', 'warning');
        return;
    }
    
    // Validate cost fields
    const useCostRange = formData.get('use_cost_range') === 'on';
    const isOneTimeCost = formData.get('is_one_time_cost') === 'on';
    
    if (useCostRange) {
        const lowCost = formData.get('cost_range_low');
        const highCost = formData.get('cost_range_high');
        if (!lowCost || !highCost) {
            showAlert('Please enter both low and high cost values', 'warning');
            return;
        }
    } else {
        const unitCost = formData.get('unit_cost');
        if (!unitCost) {
            showAlert('Please enter unit cost', 'warning');
            return;
        }
    }
    
    // Validate service type and timing
    if (!isOneTimeCost) {
        const serviceType = formData.get('service_type');
        if (!serviceType) {
            showAlert('Please select a service type', 'warning');
            return;
        }
        
        if (serviceType === 'recurring') {
            const startYear = formData.get('start_year');
            const endYear = formData.get('end_year');
            if (!startYear || !endYear) {
                showAlert('Please enter start and end years for recurring service', 'warning');
                return;
            }
        } else if (serviceType === 'discrete') {
            const occurrenceYears = formData.get('occurrence_years');
            if (!occurrenceYears || occurrenceYears.trim() === '') {
                showAlert('Please select occurrence years for discrete service', 'warning');
                return;
            }
        }
    } else {
        const oneTimeCostYear = formData.get('one_time_cost_year');
        if (!oneTimeCostYear) {
            showAlert('Please enter the year for one-time cost', 'warning');
            return;
        }
    }
    
    // Determine if we're adding or editing
    const isEditing = editingService !== null;
    const endpoint = isEditing ? '/api/edit_service' : '/api/add_service';
    
    // Add edit-specific data
    if (isEditing) {
        formData.append('service_index', editingService.serviceIndex);
    }
    
    try {
        console.log('DEBUG: Sending request to:', endpoint);
        
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        console.log('DEBUG: Response status:', response.status);
        
        const result = await response.json();
        console.log('DEBUG: Response data:', result);
        
        if (result.success) {
            showAlert(result.message, 'success');
            loadCurrentData(); // Refresh data
            bootstrap.Modal.getInstance(document.getElementById('serviceModal')).hide();
            
            // Reset editing state
            editingService = null;
            document.querySelector('#serviceModal .modal-title').textContent = 'Add Service';
            document.getElementById('submit-service-btn').textContent = 'Add Service';
        } else {
            showAlert(`Error ${isEditing ? 'updating' : 'adding'} service: ` + result.message, 'danger');
        }
    } catch (error) {
        console.error('DEBUG: Submit error:', error);
        showAlert('Error: ' + error.message, 'danger');
    }
}

// Calculations
async function calculateCosts() {
    if (!currentEvaluee) {
        showAlert('Please create an evaluee first', 'warning');
        return;
    }
    
    const loadingElement = document.getElementById('calculations-loading');
    loadingElement.style.display = 'block';
    
    try {
        const response = await fetch('/api/calculate');
        const result = await response.json();
        
        if (result.success) {
            lastCalculationResults = result;
            displayCalculationResults(result);
            showAlert('Calculations completed successfully', 'success');
        } else {
            showAlert('Error calculating costs: ' + (result.message || 'Unknown error occurred'), 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    } finally {
        loadingElement.style.display = 'none';
    }
}

function displayCalculationResults(results) {
    // Display summary statistics
    displaySummaryStats(results.summary, results.category_costs);
    
    // Display charts
    displayCharts(results.chart_data);
    
    // Display cost schedule table
    displayCostSchedule(results.cost_schedule);
}

function displaySummaryStats(summary, categoryCosts) {
    const container = document.getElementById('summary-stats');
    
    let categoryHtml = '';
    for (const [tableName, data] of Object.entries(categoryCosts)) {
        categoryHtml += `
            <div class="col-md-6 col-lg-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h6 class="card-title">${tableName}</h6>
                        <p class="card-text">
                            <strong>$${(data.table_present_value_total || 0).toFixed(2)}</strong><br>
                            <small class="text-muted">${data.services.length} services</small>
                        </p>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = `
        <div class="cost-summary mb-4">
            <div class="row text-center">
                <div class="col-md-4">
                    <h3>$${(summary.total_present_value || 0).toFixed(2)}</h3>
                    <p class="mb-0">Total Present Value</p>
                </div>
                <div class="col-md-4">
                    <h3>$${(summary.total_nominal_cost || 0).toFixed(2)}</h3>
                    <p class="mb-0">Total Nominal Cost</p>
                </div>
                <div class="col-md-4">
                    <h3>$${(summary.average_annual_cost || 0).toFixed(2)}</h3>
                    <p class="mb-0">Average Annual Cost</p>
                </div>
            </div>
        </div>
        
        <h5>Cost Breakdown by Category</h5>
        <div class="row mb-4">
            ${categoryHtml}
        </div>
    `;
    
    container.style.display = 'block';
}

function displayCharts(chartData) {
    const container = document.getElementById('charts-container');
    
    try {
        // Present Value Chart
        const pvChart = JSON.parse(chartData.present_value_chart);
        Plotly.newPlot('present-value-chart', pvChart.data, pvChart.layout, {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
        });
        
        // Comparison Chart
        const compChart = JSON.parse(chartData.comparison_chart);
        Plotly.newPlot('comparison-chart', compChart.data, compChart.layout, {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
        });
        
        container.style.display = 'block';
        console.log('Charts rendered successfully with Plotly v2.27.0');
        
    } catch (error) {
        console.error('Error rendering charts:', error);
        showAlert('Error rendering charts. Please try recalculating.', 'warning');
    }
}

function displayCostSchedule(costSchedule) {
    const tbody = document.getElementById('cost-table-body');
    
    let html = '';
    costSchedule.forEach(row => {
        html += `
            <tr>
                <td>${row.Year}</td>
                <td>${row.Age}</td>
                <td>$${(row['Total Nominal'] || 0).toFixed(2)}</td>
                <td>$${(row['Present Value'] || 0).toFixed(2)}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
    document.getElementById('cost-schedule').style.display = 'block';
}

// Export functions
async function exportFile(format) {
    if (!lastCalculationResults) {
        showAlert('Please calculate costs first', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/export/${format}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = response.headers.get('content-disposition')?.split('filename=')[1] || `lcp_report.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showAlert(`${format.toUpperCase()} export completed`, 'success');
        } else {
            showAlert(`Error exporting ${format.toUpperCase()} file`, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}

// File operations
async function uploadConfig(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload_config', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentEvaluee = result.evaluee;
            
            // Update form fields
            document.getElementById('evaluee_name').value = result.evaluee.name;
            document.getElementById('current_age').value = result.evaluee.age;
            document.getElementById('base_year').value = result.evaluee.base_year;
            document.getElementById('projection_years').value = result.evaluee.projection_years;
            document.getElementById('discount_rate').value = result.evaluee.discount_rate * 100;
            
            loadCurrentData();
            showAlert(result.message, 'success');
            showSection('tables');
        } else {
            showAlert('Error uploading config: ' + result.message, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
    
    // Reset file input
    event.target.value = '';
}

async function downloadConfig() {
    if (!currentEvaluee) {
        showAlert('Please create a life care plan first', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/download_config');
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = response.headers.get('content-disposition')?.split('filename=')[1] || 'lcp_config.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showAlert('Configuration downloaded', 'success');
        } else {
            showAlert('Error downloading configuration', 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}

function clearAll() {
    if (confirm('Are you sure you want to clear all data? This cannot be undone.')) {
        currentEvaluee = null;
        currentTables = {};
        lastCalculationResults = null;
        
        // Reset forms
        document.getElementById('evalueeForm').reset();
        document.getElementById('base_year').value = '2025';
        document.getElementById('projection_years').value = '30';
        document.getElementById('discount_rate').value = '3.0';
        
        // Reset sections
        updateTablesSection();
        document.getElementById('summary-stats').style.display = 'none';
        document.getElementById('charts-container').style.display = 'none';
        document.getElementById('cost-schedule').style.display = 'none';
        
        showAlert('All data cleared', 'info');
        showSection('evaluee');
    }
}

// Load current data from server
async function loadCurrentData() {
    try {
        const response = await fetch('/api/current_data');
        const result = await response.json();
        
        if (result.success) {
            currentEvaluee = result.evaluee;
            currentTables = result.tables;
            updateTablesSection();
        }
    } catch (error) {
        console.log('No existing data to load');
    }
}

// Template functions removed - users create tables directly

// Load sample data
async function loadSampleData() {
    try {
        const response = await fetch('/api/load_sample_data', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentEvaluee = result.evaluee;
            
            // Update form fields
            document.getElementById('evaluee_name').value = result.evaluee.name;
            document.getElementById('current_age').value = result.evaluee.age;
            document.getElementById('base_year').value = result.evaluee.base_year;
            document.getElementById('projection_years').value = result.evaluee.projection_years;
            document.getElementById('discount_rate').value = result.evaluee.discount_rate * 100;
            
            loadCurrentData();
            showAlert(`Sample data loaded: ${result.total_services} services in ${result.tables_count} tables`, 'success');
            updateDashboard();
            updateEvalueeDisplay();
            showSection('dashboard');
        } else {
            showAlert('Error loading sample data: ' + result.message, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}

// Template button functions removed

// All template modal functions removed

// Growth rates management
async function refreshGrowthRates() {
    if (!currentEvaluee) {
        const container = document.getElementById('growth-rates-container');
        container.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Create service tables first to manage their growth rates.
            </div>
        `;
        return;
    }
    
    try {
        const response = await fetch('/api/table_growth_rates');
        const result = await response.json();
        
        if (result.success) {
            displayGrowthRates(result.growth_rates);
        } else {
            showAlert('Error loading growth rates: ' + result.message, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}

function displayGrowthRates(growthRates) {
    const container = document.getElementById('growth-rates-container');
    
    if (Object.keys(growthRates).length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No service tables found. Add tables first to manage their growth rates.
            </div>
        `;
        return;
    }
    
    let html = '';
    
    for (const [tableName, data] of Object.entries(growthRates)) {
        html += `
            <div class="card mb-3">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">${tableName}</h6>
                    <button class="btn btn-outline-primary btn-sm" onclick="openGrowthRateModal('${tableName}', ${data.average_inflation_rate})">
                        <i class="fas fa-edit me-1"></i>Update Rate
                    </button>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="text-center">
                                <h5 class="text-primary">${data.average_inflation_rate.toFixed(2)}%</h5>
                                <small class="text-muted">Average Rate</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h5 class="text-info">${data.service_count}</h5>
                                <small class="text-muted">Services</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h5 class="text-warning">${data.table_default.toFixed(2)}%</h5>
                                <small class="text-muted">Table Default</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <span class="badge ${data.average_inflation_rate === data.table_default ? 'bg-success' : 'bg-warning'}">
                                    ${data.average_inflation_rate === data.table_default ? 'Matches Default' : 'Modified'}
                                </span>
                            </div>
                        </div>
                    </div>
                    
                    <hr>
                    
                    <h6>Services in this table:</h6>
                    <div class="row">
                        ${data.services.map(service => `
                            <div class="col-md-6 mb-2">
                                <div class="d-flex justify-content-between">
                                    <span>${service.name}</span>
                                    <span class="badge bg-secondary">${service.inflation_rate.toFixed(2)}%</span>
                                </div>
                                <small class="text-muted">$${service.unit_cost} × ${parseFloat(service.frequency_per_year).toFixed(1)}/year</small>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

function openGrowthRateModal(tableName, currentRate) {
    document.getElementById('growth_table_name').value = tableName;
    document.getElementById('current_rate_display').value = `${currentRate}%`;
    document.getElementById('new_inflation_rate').value = currentRate;
    
    const modal = new bootstrap.Modal(document.getElementById('growthRateModal'));
    modal.show();
}

async function updateTableInflation() {
    const tableName = document.getElementById('growth_table_name').value;
    const newRate = document.getElementById('new_inflation_rate').value;
    
    const formData = new FormData();
    formData.append('table_name', tableName);
    formData.append('new_inflation_rate', newRate);
    
    try {
        const response = await fetch('/api/update_table_inflation', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(result.message, 'success');
            refreshGrowthRates();
            bootstrap.Modal.getInstance(document.getElementById('growthRateModal')).hide();
        } else {
            showAlert('Error updating inflation rate: ' + result.message, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}

// Dashboard functions
function updateDashboard() {
    const container = document.getElementById('dashboard-content');
    
    if (!currentEvaluee) {
        container.innerHTML = `
            <div class="row">
                <div class="col-12">
                    <div class="text-center py-5">
                        <i class="fas fa-chart-pie fa-4x text-muted mb-3"></i>
                        <h5>Welcome to Life Care Plan Generator</h5>
                        <p class="text-muted">Follow these steps to create your Life Care Plan:</p>
                        <ol class="text-muted text-start" style="max-width: 400px; margin: 0 auto;">
                            <li>Create an evaluee (patient information)</li>
                            <li>Add service tables (categories of care)</li>
                            <li>Add services to each table (specific treatments/equipment)</li>
                            <li>Calculate costs and generate reports</li>
                        </ol>
                        <p class="text-muted mt-3">Start by creating an evaluee or loading sample data:</p>
                        <div class="d-flex justify-content-center gap-3">
                            <button class="btn btn-primary" onclick="showSection('evaluee')">
                                <i class="fas fa-user me-2"></i>Create New Evaluee
                            </button>
                            <button class="btn btn-outline-primary" onclick="loadSampleData()">
                                <i class="fas fa-database me-2"></i>Load Sample Data
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        return;
    }
    
    const tablesCount = Object.keys(currentTables).length;
    const servicesCount = Object.values(currentTables).reduce((total, services) => total + services.length, 0);
    
    container.innerHTML = `
        <div class="row mb-4">
            <div class="col-12">
                <div class="d-flex align-items-center">
                    <div class="me-3">
                        <i class="fas fa-user-circle fa-4x text-primary"></i>
                    </div>
                    <div>
                        <h4 class="mb-1">${currentEvaluee.name}</h4>
                        <p class="text-muted mb-1">
                            Age: ${currentEvaluee.age} | 
                            Base Year: ${currentEvaluee.base_year} | 
                            Projection: ${currentEvaluee.projection_years} years
                        </p>
                        <small class="text-muted">
                            Discount Rate: ${(currentEvaluee.discount_rate * 100).toFixed(2)}% | 
                            Present Value: ${currentEvaluee.discount_calculations ? 'Enabled' : 'Disabled'}
                        </small>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card text-center bg-primary text-white">
                    <div class="card-body">
                        <h3>${tablesCount}</h3>
                        <p class="mb-0">Service Tables</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center bg-success text-white">
                    <div class="card-body">
                        <h3>${servicesCount}</h3>
                        <p class="mb-0">Total Services</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center bg-info text-white">
                    <div class="card-body">
                        <h3>${currentEvaluee.projection_years}</h3>
                        <p class="mb-0">Projection Years</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center bg-warning text-white">
                    <div class="card-body">
                        <h3>${(currentEvaluee.discount_rate * 100).toFixed(2)}%</h3>
                        <p class="mb-0">Discount Rate</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Quick Actions</h6>
                    </div>
                    <div class="card-body">
                        <div class="d-grid gap-2">
                            <button class="btn btn-outline-primary" onclick="showSection('tables')">
                                <i class="fas fa-table me-2"></i>Manage Service Tables
                            </button>
                            <button class="btn btn-outline-success" onclick="showSection('calculations')">
                                <i class="fas fa-calculator me-2"></i>View Calculations & Charts
                            </button>
                            <button class="btn btn-outline-info" onclick="showSection('growth-rates')">
                                <i class="fas fa-chart-line me-2"></i>Monitor Growth Rates
                            </button>
                            <button class="btn btn-outline-secondary" onclick="showSection('export')">
                                <i class="fas fa-download me-2"></i>Export Reports
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Service Tables Overview</h6>
                    </div>
                    <div class="card-body">
                        ${tablesCount === 0 ? 
                            '<p class="text-muted">No service tables created yet. <a href="#" onclick="showSection(\'tables\')">Add your first table</a></p>' : 
                            Object.entries(currentTables).map(([tableName, services]) => `
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <span>${tableName}</span>
                                    <span class="badge bg-primary">${services.length} services</span>
                                </div>
                            `).join('')
                        }
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Evaluee management functions
function updateEvalueeDisplay() {
    if (!currentEvaluee) {
        document.getElementById('current-evaluee-display').style.display = 'none';
        document.getElementById('evaluee-form-container').style.display = 'block';
        document.getElementById('edit-evaluee-btn').style.display = 'none';
        document.getElementById('new-evaluee-btn').innerHTML = '<i class="fas fa-plus me-1"></i>New Evaluee';
        return;
    }
    
    // Update display fields
    document.getElementById('current-evaluee-name').textContent = currentEvaluee.name;
    document.getElementById('current-evaluee-age').textContent = currentEvaluee.age;
    document.getElementById('current-evaluee-base-year').textContent = currentEvaluee.base_year;
    document.getElementById('current-evaluee-projection').textContent = currentEvaluee.projection_years;
    document.getElementById('current-evaluee-discount').textContent = (currentEvaluee.discount_rate * 100).toFixed(2);
    document.getElementById('current-evaluee-pv-status').textContent = currentEvaluee.discount_calculations ? 'Enabled' : 'Disabled';
    
    const tablesCount = Object.keys(currentTables).length;
    const servicesCount = Object.values(currentTables).reduce((total, services) => total + services.length, 0);
    
    document.getElementById('evaluee-tables-count').textContent = tablesCount;
    document.getElementById('evaluee-services-count').textContent = servicesCount;
    
    // Show evaluee display, hide form
    document.getElementById('current-evaluee-display').style.display = 'block';
    document.getElementById('evaluee-form-container').style.display = 'none';
    document.getElementById('edit-evaluee-btn').style.display = 'inline-block';
    document.getElementById('new-evaluee-btn').innerHTML = '<i class="fas fa-user-plus me-1"></i>New Evaluee';
}

function createNewEvaluee() {
    // Reset form
    document.getElementById('evalueeForm').reset();
    document.getElementById('base_year').value = appSettings.defaultBaseYear;
    document.getElementById('projection_years').value = appSettings.defaultProjectionYears;
    document.getElementById('discount_rate').value = appSettings.defaultDiscountRate;
    
    // Show form, hide display
    document.getElementById('current-evaluee-display').style.display = 'none';
    document.getElementById('evaluee-form-container').style.display = 'block';
    document.getElementById('cancel-evaluee-btn').style.display = 'none';
    document.getElementById('save-evaluee-btn').innerHTML = '<i class="fas fa-save me-2"></i>Create Life Care Plan';
}

function editCurrentEvaluee() {
    if (!currentEvaluee) return;
    
    // Populate form with current data
    document.getElementById('evaluee_name').value = currentEvaluee.name;
    document.getElementById('current_age').value = currentEvaluee.age;
    document.getElementById('base_year').value = currentEvaluee.base_year;
    document.getElementById('projection_years').value = currentEvaluee.projection_years;
    document.getElementById('discount_rate').value = currentEvaluee.discount_rate * 100;
    document.getElementById('discount_calculations').checked = currentEvaluee.discount_calculations;
    
    // Show form in edit mode
    document.getElementById('current-evaluee-display').style.display = 'none';
    document.getElementById('evaluee-form-container').style.display = 'block';
    document.getElementById('cancel-evaluee-btn').style.display = 'inline-block';
    document.getElementById('save-evaluee-btn').innerHTML = '<i class="fas fa-save me-2"></i>Update Life Care Plan';
}

function cancelEvalueeEdit() {
    updateEvalueeDisplay();
}

// Settings functions
function updateSettingsSection() {
    // Update application settings form only (template management removed)
    document.getElementById('default-base-year').value = appSettings.defaultBaseYear;
    document.getElementById('default-projection-years').value = appSettings.defaultProjectionYears;
    document.getElementById('default-discount-rate').value = appSettings.defaultDiscountRate;
    document.getElementById('auto-calculate').checked = appSettings.autoCalculate;
    document.getElementById('show-welcome').checked = appSettings.showWelcome;
}

// Template management functions removed

function saveApplicationSettings() {
    appSettings.defaultBaseYear = parseInt(document.getElementById('default-base-year').value);
    appSettings.defaultProjectionYears = parseFloat(document.getElementById('default-projection-years').value);
    appSettings.defaultDiscountRate = parseFloat(document.getElementById('default-discount-rate').value);
    appSettings.autoCalculate = document.getElementById('auto-calculate').checked;
    appSettings.showWelcome = document.getElementById('show-welcome').checked;
    
    // Save to localStorage
    localStorage.setItem('lcpAppSettings', JSON.stringify(appSettings));
    
    showAlert('Application settings saved', 'success');
}

function loadApplicationSettings() {
    const saved = localStorage.getItem('lcpAppSettings');
    if (saved) {
        appSettings = { ...appSettings, ...JSON.parse(saved) };
    }
}

function exportSettings() {
    const settings = {
        appSettings: appSettings,
        exportedAt: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lcp_settings_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showAlert('Settings exported successfully', 'success');
}

// Database Management Functions
async function loadSavedPlans() {
    try {
        const response = await fetch('/api/list_evaluees');
        const result = await response.json();
        
        if (result.success) {
            const select = document.getElementById('saved-plans-select');
            const listContainer = document.getElementById('saved-plans-list');
            
            // Clear existing options
            select.innerHTML = '<option value="">Select a saved plan...</option>';
            
            if (result.evaluees.length > 0) {
                result.evaluees.forEach(evaluee => {
                    const option = document.createElement('option');
                    option.value = evaluee.name;
                    option.textContent = `${evaluee.name} (${evaluee.table_count} tables, ${evaluee.service_count} services)`;
                    select.appendChild(option);
                });
                
                listContainer.style.display = 'block';
            } else {
                listContainer.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading saved plans:', error);
    }
}

async function loadSelectedPlan() {
    const select = document.getElementById('saved-plans-select');
    const evalueName = select.value;
    
    if (!evalueName) {
        showAlert('Please select a plan to load', 'warning');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('evaluee_name', evalueName);
        
        const response = await fetch('/api/load_evaluee', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Update current data
            currentEvaluee = result.evaluee;
            currentTables = result.tables;
            
            // Update UI
            updateEvalueeDisplay();
            updateTablesSection();
            updateDashboard();
            
            showAlert(result.message, 'success');
            showSection('dashboard');
        } else {
            showAlert('Error loading plan: ' + result.message, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}

async function deleteSelectedPlan() {
    const select = document.getElementById('saved-plans-select');
    const evalueName = select.value;
    
    if (!evalueName) {
        showAlert('Please select a plan to delete', 'warning');
        return;
    }
    
    if (!confirm(`Are you sure you want to permanently delete "${evalueName}" and all associated data?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/delete_evaluee_db/${encodeURIComponent(evalueName)}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(result.message, 'success');
            loadSavedPlans(); // Refresh the list
        } else {
            showAlert('Error deleting plan: ' + result.message, 'danger');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'danger');
    }
}
