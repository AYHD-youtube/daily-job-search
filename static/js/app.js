// Main JavaScript for Daily Job Search application

// Global variables
let searchConfigs = [];
let currentEditingConfig = null;
let isSaving = false;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Utility functions
function showAlert(message, type = 'info', duration = 5000) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-dismiss after duration
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, duration);
}

function showLoading(element, text = 'Loading...') {
    const originalContent = element.innerHTML;
    element.innerHTML = `
        <div class="text-center">
            <div class="spinner-border spinner-border-sm" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span class="ms-2">${text}</span>
        </div>
    `;
    return originalContent;
}

function hideLoading(element, originalContent) {
    element.innerHTML = originalContent;
}

// API functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'API call failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        showAlert(`Error: ${error.message}`, 'danger');
        throw error;
    }
}

// Search configuration functions
async function loadSearchConfigs() {
    try {
        const data = await apiCall('/api/search-configs');
        searchConfigs = data;
        updateSearchConfigsDisplay();
    } catch (error) {
        console.error('Failed to load search configs:', error);
    }
}

function updateSearchConfigsDisplay() {
    const container = document.getElementById('searchConfigsContainer');
    if (!container) return;
    
    if (searchConfigs.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-plus-circle fa-3x text-muted mb-3"></i>
                <p class="text-muted">No search configurations yet</p>
                <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#newSearchModal">
                    <i class="fas fa-plus"></i> Create First Configuration
                </button>
            </div>
        `;
        return;
    }
    
    let html = '';
    searchConfigs.forEach(config => {
        const lastRun = config.last_run ? new Date(config.last_run).toLocaleString() : 'Never';
        const statusClass = config.is_active ? 'success' : 'secondary';
        const statusText = config.is_active ? 'Active' : 'Inactive';
        
        html += `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6 class="card-title mb-0">${config.name}</h6>
                            <span class="badge bg-${statusClass}">${statusText}</span>
                        </div>
                        <p class="text-muted small mb-2">
                            <i class="fas fa-clock"></i> ${config.search_time} | 
                            <i class="fas fa-search"></i> ${config.keywords.length} keywords |
                            <i class="fas fa-hourglass-half"></i> Max ${config.max_job_age}h old
                        </p>
                        <p class="text-muted small mb-3">
                            Last run: ${lastRun}
                        </p>
                        <div class="btn-group w-100">
                            <button class="btn btn-outline-primary btn-sm" onclick="editSearchConfig(${config.id})">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button class="btn btn-outline-success btn-sm" onclick="testSearchConfig(${config.id})">
                                <i class="fas fa-play"></i> Test
                            </button>
                            <button class="btn btn-outline-danger btn-sm" onclick="deleteSearchConfig(${config.id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function saveSearchConfig(configData) {
    try {
        isSaving = true;
        const url = currentEditingConfig ? `/api/search-configs/${currentEditingConfig}` : '/api/search-configs';
        const method = currentEditingConfig ? 'PUT' : 'POST';
        
        await apiCall(url, {
            method: method,
            body: JSON.stringify(configData)
        });
        
        showAlert('Search configuration saved successfully!', 'success');
        await loadSearchConfigs();
        
        // Reset editing state after successful save
        currentEditingConfig = null;
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('newSearchModal'));
        modal.hide();
        
        // Reset form
        document.getElementById('searchConfigForm').reset();
        
    } catch (error) {
        console.error('Failed to save search config:', error);
    } finally {
        isSaving = false;
    }
}

async function editSearchConfig(configId) {
    const config = searchConfigs.find(c => c.id === configId);
    if (!config) return;
    
    currentEditingConfig = configId;
    
    // Populate form
    document.getElementById('configName').value = config.name;
    document.getElementById('keywords').value = config.keywords.join(', ');
    document.getElementById('locationFilter').value = config.location_filter;
    document.getElementById('maxJobAge').value = config.max_job_age || 24;
    
    // Set search logic
    document.getElementById('searchLogic').value = config.search_logic || 'AND';
    if (config.search_logic === 'CUSTOM') {
        document.getElementById('customLogicContainer').style.display = 'block';
        document.getElementById('customLogic').value = config.custom_logic || '';
    } else {
        document.getElementById('customLogicContainer').style.display = 'none';
    }
    
    // Set frequency
    document.getElementById('frequency').value = config.frequency || 'daily';
    if (config.frequency === 'custom') {
        document.getElementById('customFrequencyContainer').style.display = 'block';
        if (config.custom_frequency) {
            // Set selected days
            document.querySelectorAll('#customFrequencyContainer input[type="checkbox"]').forEach(checkbox => {
                checkbox.checked = config.custom_frequency.days.includes(checkbox.value);
            });
            // Set interval
            document.getElementById('frequencyInterval').value = config.custom_frequency.interval || 1;
        }
    } else {
        document.getElementById('customFrequencyContainer').style.display = 'none';
    }
    
    // Update time input label based on frequency
    const timeLabel = document.querySelector('label[for="searchTime"]');
    const timeHelp = document.querySelector('#searchTime').nextElementSibling;
    
    if (config.frequency === 'hourly') {
        timeLabel.textContent = 'Start Minute';
        timeHelp.textContent = 'Minute of the hour to start (0-59)';
    } else if (config.frequency === '2hourly' || config.frequency === '3hourly') {
        timeLabel.textContent = 'Start Time';
        timeHelp.textContent = 'Time to start the interval schedule';
    } else {
        timeLabel.textContent = 'Email Time';
        timeHelp.textContent = 'When to send job search emails';
    }
    
    // Set search time
    document.getElementById('searchTime').value = config.search_time;
    
    document.getElementById('isActive').checked = config.is_active;
    
    // Update job sites checkboxes
    const jobSites = config.job_sites || [];
    document.querySelectorAll('#jobSitesContainer input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = jobSites.includes(checkbox.value);
    });
    
    // Update modal title
    document.querySelector('#newSearchModal .modal-title').textContent = 'Edit Search Configuration';
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('newSearchModal'));
    modal.show();
}

async function deleteSearchConfig(configId) {
    if (!confirm('Are you sure you want to delete this search configuration?')) {
        return;
    }
    
    try {
        await apiCall(`/api/search-configs/${configId}`, {
            method: 'DELETE'
        });
        
        showAlert('Search configuration deleted successfully!', 'success');
        await loadSearchConfigs();
        
    } catch (error) {
        console.error('Failed to delete search config:', error);
    }
}

async function testSearchConfig(configId) {
    const config = searchConfigs.find(c => c.id === configId);
    if (!config) return;
    
    try {
        const testResults = document.getElementById('testResults');
        const originalContent = showLoading(testResults, 'Testing search...');
        
        const data = await apiCall('/api/test-search', {
            method: 'POST',
            body: JSON.stringify({
                keywords: config.keywords,
                search_logic: config.search_logic || 'AND',
                custom_logic: config.custom_logic || '',
                location_filter: config.location_filter,
                job_sites: config.job_sites,
                max_job_age: config.max_job_age
            })
        });
        
        displayTestResults(data);
        
        // Refresh the dashboard to show new job results
        if (data.jobs && data.jobs.length > 0) {
            setTimeout(() => {
                window.location.reload();
            }, 2000); // Wait 2 seconds to show the success message, then refresh
        }
        
    } catch (error) {
        console.error('Failed to test search:', error);
    }
}

function displayTestResults(data) {
    const testResults = document.getElementById('testResults');
    const jobs = data.jobs || [];
    const isRealSearch = data.is_real_search || false;
    const message = data.message || `Found ${jobs.length} jobs`;
    
    if (jobs.length === 0) {
        testResults.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                No jobs found. Check your API configuration and try different keywords.
            </div>
        `;
        return;
    }
    
    const alertClass = isRealSearch ? 'alert-success' : 'alert-info';
    const icon = isRealSearch ? 'fas fa-search' : 'fas fa-flask';
    const searchType = isRealSearch ? 'real Google search' : 'sample data';
    
    let html = `
        <div class="alert ${alertClass}">
            <i class="${icon}"></i>
            ${message} (${searchType})
        </div>
        <div class="list-group">
    `;
    
    jobs.slice(0, 5).forEach(job => {
        html += `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">
                        <a href="${job.link}" target="_blank" class="text-decoration-none">
                            ${job.title}
                        </a>
                    </h6>
                    <small class="text-muted">${job.job_site}</small>
                </div>
                <p class="mb-1 text-muted">${job.snippet.substring(0, 100)}...</p>
            </div>
        `;
    });
    
    html += '</div>';
    
    if (jobs.length > 5) {
        html += `<p class="text-muted small mt-2">Showing first 5 of ${jobs.length} results</p>`;
    }
    
    testResults.innerHTML = html;
}

// Form validation
function validateSearchConfigForm() {
    const name = document.getElementById('configName').value.trim();
    const keywords = document.getElementById('keywords').value.trim();
    const searchTime = document.getElementById('searchTime').value;
    const frequency = document.getElementById('frequency').value;
    
    if (!name) {
        showAlert('Please enter a configuration name', 'warning');
        return false;
    }
    
    if (!keywords) {
        showAlert('Please enter at least one keyword', 'warning');
        return false;
    }
    
    if (!searchTime) {
        showAlert('Please select a search time', 'warning');
        return false;
    }
    
    // For hourly frequency, validate minute input
    if (frequency === 'hourly') {
        const minute = parseInt(searchTime.split(':')[1]);
        if (minute < 0 || minute > 59) {
            showAlert('Please enter a valid minute (0-59) for hourly frequency', 'warning');
            return false;
        }
    }
    
    return true;
}

// Search logic functions
function initSearchLogic() {
    const searchLogicSelect = document.getElementById('searchLogic');
    const customLogicContainer = document.getElementById('customLogicContainer');
    
    if (searchLogicSelect && customLogicContainer) {
        searchLogicSelect.addEventListener('change', function() {
            if (this.value === 'CUSTOM') {
                customLogicContainer.style.display = 'block';
            } else {
                customLogicContainer.style.display = 'none';
            }
        });
    }
}

// Frequency functions
function initFrequency() {
    const frequencySelect = document.getElementById('frequency');
    const customFrequencyContainer = document.getElementById('customFrequencyContainer');
    const searchTimeContainer = document.querySelector('.col-md-6 .mb-3');
    
    if (frequencySelect && customFrequencyContainer) {
        frequencySelect.addEventListener('change', function() {
            if (this.value === 'custom') {
                customFrequencyContainer.style.display = 'block';
            } else {
                customFrequencyContainer.style.display = 'none';
            }
            
            // Update the time input label based on frequency
            const timeLabel = document.querySelector('label[for="searchTime"]');
            const timeHelp = document.querySelector('#searchTime').nextElementSibling;
            
            if (this.value === 'hourly') {
                timeLabel.textContent = 'Start Minute';
                timeHelp.textContent = 'Minute of the hour to start (0-59)';
            } else if (this.value === '2hourly' || this.value === '3hourly') {
                timeLabel.textContent = 'Start Time';
                timeHelp.textContent = 'Time to start the interval schedule';
            } else {
                timeLabel.textContent = 'Email Time';
                timeHelp.textContent = 'When to send job search emails';
            }
        });
    }
}

function buildSearchQuery(keywords, searchLogic, customLogic) {
    switch (searchLogic) {
        case 'AND':
            return `"${keywords.join(' ')}"`;
        case 'OR':
            return keywords.join(' OR ');
        case 'CUSTOM':
            return customLogic || keywords.join(' OR ');
        default:
            return `"${keywords.join(' ')}"`;
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize search logic handler
    initSearchLogic();
    
    // Initialize frequency handler
    initFrequency();
    
    // Load search configs if on dashboard
    if (document.getElementById('searchConfigsContainer')) {
        loadSearchConfigs();
    }
    
    // Search config form submission
    const searchConfigForm = document.getElementById('searchConfigForm');
    if (searchConfigForm) {
        searchConfigForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (!validateSearchConfigForm()) {
                return;
            }
            
            const keywords = document.getElementById('keywords').value.split(',').map(k => k.trim());
            const selectedSites = Array.from(document.querySelectorAll('#jobSitesContainer input[type="checkbox"]:checked'))
                .map(cb => cb.value);
            
            // Get search logic
            const searchLogic = document.getElementById('searchLogic').value;
            const customLogic = document.getElementById('customLogic').value;
            
            // Get frequency settings
            const frequency = document.getElementById('frequency').value;
            let customFrequency = null;
            if (frequency === 'custom') {
                const selectedDays = Array.from(document.querySelectorAll('#customFrequencyContainer input[type="checkbox"]:checked'))
                    .map(cb => cb.value);
                const interval = document.getElementById('frequencyInterval').value;
                customFrequency = {
                    days: selectedDays,
                    interval: parseInt(interval)
                };
            }
            
            // Get search time from the time input
            const searchTime = document.getElementById('searchTime').value;
            
            const configData = {
                name: document.getElementById('configName').value,
                keywords: keywords,
                search_logic: searchLogic,
                custom_logic: customLogic,
                frequency: frequency,
                custom_frequency: customFrequency,
                location_filter: document.getElementById('locationFilter').value,
                job_sites: selectedSites,
                max_job_age: parseInt(document.getElementById('maxJobAge').value),
                is_active: document.getElementById('isActive').checked,
                search_time: searchTime
            };
            
            saveSearchConfig(configData);
        });
    }
    
    // Reset editing state when modal is closed
    const newSearchModal = document.getElementById('newSearchModal');
    if (newSearchModal) {
        newSearchModal.addEventListener('hidden.bs.modal', function() {
            // Only reset if we're not in the middle of saving
            if (!isSaving && currentEditingConfig !== null) {
                currentEditingConfig = null;
                document.getElementById('searchConfigForm').reset();
                // Reset modal title
                document.querySelector('#newSearchModal .modal-title').textContent = 'New Search Configuration';
            }
        });
    }
    
    // Test search form submission
    const testSearchForm = document.getElementById('testSearchForm');
    if (testSearchForm) {
        testSearchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const keywords = document.getElementById('testKeywords').value.split(',').map(k => k.trim());
            const locationFilter = document.getElementById('testLocation').value;
            
            const testResults = document.getElementById('testResults');
            const originalContent = showLoading(testResults, 'Testing search...');
            
            apiCall('/api/test-search', {
                method: 'POST',
                body: JSON.stringify({
                    keywords: keywords,
                    location_filter: locationFilter
                })
            })
            .then(data => {
                displayTestResults(data);
            })
            .catch(error => {
                hideLoading(testResults, originalContent);
            });
        });
    }
});

// Export functions for global access
window.editSearchConfig = editSearchConfig;
window.deleteSearchConfig = deleteSearchConfig;
window.testSearchConfig = testSearchConfig;
