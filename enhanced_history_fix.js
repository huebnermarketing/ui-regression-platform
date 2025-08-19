// Enhanced History Modal Functionality with Debugging
// This replaces the existing history functionality

// Global variables for debugging
window.historyDebug = {
    currentProjectId: null,
    currentRunData: null,
    lastApiCall: null,
    lastError: null
};

// Enhanced error handling and logging
function logHistoryDebug(message, data = null) {
    console.log(`[History Debug] ${message}`, data);
    window.historyDebug.lastApiCall = { message, data, timestamp: new Date() };
}

function logHistoryError(message, error = null) {
    console.error(`[History Error] ${message}`, error);
    window.historyDebug.lastError = { message, error, timestamp: new Date() };
    
    // Show user-friendly error message
    showToast('error', `History Error: ${message}`);
}

// Enhanced API call function with better error handling
async function makeHistoryApiCall(url, options = {}) {
    logHistoryDebug(`Making API call to: ${url}`);
    
    try {
        // Ensure credentials are included for authentication
        const defaultOptions = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        const response = await fetch(url, finalOptions);
        
        logHistoryDebug(`API response status: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        logHistoryDebug(`API response data:`, data);
        
        return data;
    } catch (error) {
        logHistoryError(`API call failed for ${url}`, error);
        throw error;
    }
}

// Enhanced load history runs function
async function loadHistoryRunsEnhanced() {
    const runSelector = document.getElementById('runSelector');
    if (!runSelector) {
        logHistoryError('Run selector element not found');
        return;
    }
    
    runSelector.innerHTML = '<option value="">Loading runs...</option>';
    
    try {
        // Validate project ID
        if (!currentProjectId || isNaN(currentProjectId)) {
            throw new Error(`Invalid project ID: ${currentProjectId}`);
        }
        
        window.historyDebug.currentProjectId = currentProjectId;
        
        // Make API call with enhanced error handling
        const url = `/api/history/project/${currentProjectId}/runs`;
        const data = await makeHistoryApiCall(url);
        
        runSelector.innerHTML = '';
        
        if (data.success && data.runs && data.runs.length > 0) {
            // Add default option
            runSelector.innerHTML = '<option value="">Select a process run...</option>';
            
            // Add runs in reverse chronological order (newest first)
            data.runs.forEach(run => {
                const option = document.createElement('option');
                option.value = run.timestamp;
                option.textContent = `${run.datetime} (${run.page_count} pages)`;
                option.dataset.runData = JSON.stringify({
                    run_id: run.timestamp,
                    formatted_date: run.datetime,
                    pages_count: run.page_count,
                    timestamp: run.timestamp
                });
                runSelector.appendChild(option);
            });
            
            // Auto-select the most recent run
            if (data.runs.length > 0) {
                runSelector.value = data.runs[0].timestamp;
                await onRunSelectedEnhanced();
            }
            
            logHistoryDebug(`Successfully loaded ${data.runs.length} runs`);
        } else {
            runSelector.innerHTML = '<option value="">No runs available</option>';
            showHistoryEmpty();
            logHistoryDebug('No runs found for project');
        }
    } catch (error) {
        logHistoryError('Failed to load history runs', error);
        runSelector.innerHTML = '<option value="">Error loading runs</option>';
        showHistoryEmpty();
    }
}

// Enhanced run selection handler
async function onRunSelectedEnhanced() {
    const runSelector = document.getElementById('runSelector');
    if (!runSelector) {
        logHistoryError('Run selector not found');
        return;
    }
    
    const selectedOption = runSelector.options[runSelector.selectedIndex];
    
    if (!selectedOption.value) {
        hideHistoryTable();
        return;
    }
    
    try {
        currentRunData = JSON.parse(selectedOption.dataset.runData);
        window.historyDebug.currentRunData = currentRunData;
        
        logHistoryDebug('Run selected:', currentRunData);
        
        // Update run info
        updateRunInfo(currentRunData);
        
        // Load pages for selected run
        await loadHistoryPagesEnhanced(currentRunData.run_id);
    } catch (error) {
        logHistoryError('Failed to handle run selection', error);
        showHistoryEmpty();
    }
}

// Enhanced load pages function with better error handling
async function loadHistoryPagesEnhanced(runId, page = 1, perPage = currentPerPage) {
    showHistoryLoading();
    
    try {
        // Validate inputs
        if (!currentProjectId || isNaN(currentProjectId)) {
            throw new Error(`Invalid project ID: ${currentProjectId}`);
        }
        
        if (!runId) {
            throw new Error(`Invalid run ID: ${runId}`);
        }
        
        // Construct URL with all required parameters
        const url = `/api/history/project/${currentProjectId}/run/${runId}/pages?page=${page}&per_page=${perPage}`;
        
        logHistoryDebug(`Loading pages for run ${runId}, page ${page}, perPage ${perPage}`);
        
        const data = await makeHistoryApiCall(url);
        
        hideHistoryLoading();
        
        if (data.success && data.pages) {
            logHistoryDebug(`Received ${data.pages.length} page records from API`);
            
            if (data.pages.length > 0) {
                // Group pages by path to avoid duplicates across viewports
                const groupedPages = groupPagesForHistory(data.pages);
                const groupedPagesArray = Object.values(groupedPages);
                
                logHistoryDebug(`After grouping: ${groupedPagesArray.length} unique pages`);
                
                // Update global pagination state
                currentPage = data.pagination.page;
                currentPerPage = data.pagination.per_page;
                currentPagination = data.pagination;
                
                logHistoryDebug(`Backend pagination:`, currentPagination);
                
                populateHistoryTableWithGroupedPages(groupedPagesArray);
                updatePaginationControls(currentPagination);
                showHistoryTable();
                
                logHistoryDebug(`History pagination complete - showing ${groupedPagesArray.length} pages`);
            } else {
                // No pages on this page
                if (data.pagination && data.pagination.total > 0 && data.pagination.page > 1) {
                    // We're on a page beyond available data, go to last page
                    const lastPage = data.pagination.pages;
                    if (lastPage > 0) {
                        logHistoryDebug(`No pages on page ${page}, redirecting to last page ${lastPage}`);
                        await loadHistoryPagesEnhanced(runId, lastPage, perPage);
                        return;
                    }
                }
                logHistoryDebug('No pages found');
                showHistoryEmpty();
            }
        } else {
            logHistoryError('API returned no pages or error', data.error || 'Unknown error');
            showHistoryEmpty();
        }
    } catch (error) {
        logHistoryError('Failed to load pages', error);
        hideHistoryLoading();
        showHistoryEmpty();
    }
}

// Enhanced error display function
function showEnhancedErrorMessage(container, title, message, suggestions = []) {
    const errorHtml = `
        <div class="empty-state">
            <div class="empty-icon">
                <i class="fas fa-exclamation-triangle text-danger"></i>
            </div>
            <h3 class="empty-title">${title}</h3>
            <p class="empty-description">${message}</p>
            ${suggestions.length > 0 ? `
                <div class="mt-3">
                    <h6>Troubleshooting Steps:</h6>
                    <ul class="text-start">
                        ${suggestions.map(s => `<li>${s}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            <button class="btn btn-primary mt-3" onclick="retryHistoryLoad()">
                <i class="fas fa-redo"></i> Retry
            </button>
        </div>
    `;
    
    container.innerHTML = errorHtml;
}

// Retry function
async function retryHistoryLoad() {
    logHistoryDebug('Retrying history load...');
    await loadHistoryRunsEnhanced();
}

// Enhanced initialization
function initializeEnhancedHistory() {
    logHistoryDebug('Initializing enhanced history functionality');
    
    // Replace existing event listeners
    const historyModal = document.getElementById('historyModal');
    if (historyModal) {
        // Remove existing listeners
        historyModal.removeEventListener('show.bs.modal', loadHistoryRuns);
        
        // Add enhanced listener
        historyModal.addEventListener('show.bs.modal', async function() {
            logHistoryDebug('History modal opened');
            await loadHistoryRunsEnhanced();
        });
    }
    
    // Replace run selector listener
    const runSelector = document.getElementById('runSelector');
    if (runSelector) {
        runSelector.removeEventListener('change', onRunSelected);
        runSelector.addEventListener('change', onRunSelectedEnhanced);
    }
    
    // Add debug panel to page
    addDebugPanel();
    
    logHistoryDebug('Enhanced history functionality initialized');
}

// Debug panel for troubleshooting
function addDebugPanel() {
    const debugPanel = document.createElement('div');
    debugPanel.id = 'historyDebugPanel';
    debugPanel.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-size: 12px;
        z-index: 10000;
        max-width: 300px;
        display: none;
    `;
    
    debugPanel.innerHTML = `
        <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 5px;">
            <strong>History Debug</strong>
            <button onclick="toggleDebugPanel()" style="background: none; border: none; color: white; margin-left: 10px;">×</button>
        </div>
        <div id="debugContent">
            <div>Project ID: <span id="debugProjectId">-</span></div>
            <div>Current Run: <span id="debugCurrentRun">-</span></div>
            <div>Last API Call: <span id="debugLastApi">-</span></div>
            <div>Last Error: <span id="debugLastError">-</span></div>
        </div>
        <button onclick="exportDebugInfo()" style="margin-top: 5px; padding: 2px 5px; font-size: 10px;">Export Debug Info</button>
    `;
    
    document.body.appendChild(debugPanel);
    
    // Add keyboard shortcut to toggle debug panel (Ctrl+Shift+H)
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.shiftKey && e.key === 'H') {
            toggleDebugPanel();
        }
    });
}

function toggleDebugPanel() {
    const panel = document.getElementById('historyDebugPanel');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        if (panel.style.display === 'block') {
            updateDebugPanel();
        }
    }
}

function updateDebugPanel() {
    const debug = window.historyDebug;
    document.getElementById('debugProjectId').textContent = debug.currentProjectId || '-';
    document.getElementById('debugCurrentRun').textContent = debug.currentRunData?.run_id || '-';
    document.getElementById('debugLastApi').textContent = debug.lastApiCall?.message || '-';
    document.getElementById('debugLastError').textContent = debug.lastError?.message || '-';
}

function exportDebugInfo() {
    const debugInfo = {
        timestamp: new Date().toISOString(),
        projectId: window.historyDebug.currentProjectId,
        currentRun: window.historyDebug.currentRunData,
        lastApiCall: window.historyDebug.lastApiCall,
        lastError: window.historyDebug.lastError,
        userAgent: navigator.userAgent,
        url: window.location.href
    };
    
    const blob = new Blob([JSON.stringify(debugInfo, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `history-debug-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for other scripts to load
    setTimeout(initializeEnhancedHistory, 1000);
});