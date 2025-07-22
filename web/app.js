/**
 * Main Application for CodeBased Web Interface
 */

class CodeBasedApp {
    constructor() {
        this.graph = null;
        this.currentFilters = {
            nodeTypes: [],
            searchText: '',
            fileFilter: ''
        };
        this.queryTemplates = [];
        
        this.init();
    }
    
    init() {
        // Initialize graph visualization
        this.graph = new GraphVisualizer('#graph-svg');
        
        // Initialize performance manager
        this.performanceManager = new PerformanceManager(this.graph);
        this.performanceManager.onPerformanceUpdate = (stats) => this.handlePerformanceUpdate(stats);
        
        // Setup event handlers
        this.graph.onNodeSelected = (node) => this.handleNodeSelected(node);
        this.graph.onNodeDeselected = () => this.handleNodeDeselected();
        
        // Setup UI event handlers
        this.setupEventHandlers();
        
        // Load initial data
        this.loadQueryTemplates();
        this.loadGraphData();
        
        // Setup periodic status updates
        setInterval(() => this.updateStatus(), 30000); // Every 30 seconds
    }
    
    setupEventHandlers() {
        // Update button
        const updateBtn = document.getElementById('update-btn');
        updateBtn?.addEventListener('click', () => this.updateGraph());
        
        // Freeze/Unfreeze button
        const freezeBtn = document.getElementById('freeze-btn');
        this.isFrozen = false;
        freezeBtn?.addEventListener('click', () => {
            if (this.isFrozen) {
                this.graph.unfreezeLayout();
                freezeBtn.textContent = 'Freeze Layout';
                freezeBtn.classList.remove('btn-primary');
                freezeBtn.classList.add('btn-secondary');
            } else {
                this.graph.freezeLayout();
                freezeBtn.textContent = 'Unfreeze Layout';
                freezeBtn.classList.remove('btn-secondary');
                freezeBtn.classList.add('btn-primary');
            }
            this.isFrozen = !this.isFrozen;
        });
        
        // Store reference to freeze button for auto-freeze
        this.freezeBtn = freezeBtn;
        
        // Reset view button
        const resetBtn = document.getElementById('reset-btn');
        resetBtn?.addEventListener('click', () => this.resetView());
        
        // Filter inputs
        const fileFilter = document.getElementById('file-filter');
        fileFilter?.addEventListener('input', (e) => {
            this.currentFilters.fileFilter = e.target.value;
            this.debounce(() => this.applyFilters(), 300);
        });
        
        const searchInput = document.getElementById('search-input');
        searchInput?.addEventListener('input', (e) => {
            this.currentFilters.searchText = e.target.value;
            this.debounce(() => this.applyFilters(), 300);
        });
        
        // Modal handlers
        const modal = document.getElementById('query-modal');
        const closeModal = document.getElementById('close-modal');
        const cancelBtn = document.getElementById('cancel-query-btn');
        const executeBtn = document.getElementById('execute-query-btn');
        
        closeModal?.addEventListener('click', () => this.hideQueryModal());
        cancelBtn?.addEventListener('click', () => this.hideQueryModal());
        executeBtn?.addEventListener('click', () => this.executeQuery());
        
        // Close modal on background click
        modal?.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hideQueryModal();
            }
        });
        
        // Error retry button
        const retryBtn = document.getElementById('retry-btn');
        retryBtn?.addEventListener('click', () => this.loadGraphData());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideQueryModal();
            }
        });
    }
    
    async loadGraphData() {
        this.showLoading(true);
        this.hideError();
        
        try {
            const response = await fetch('/api/graph');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Apply performance optimizations based on data size
            this.performanceManager.optimizeForNodeCount(data.nodes.length);
            
            // Update graph visualization
            this.graph.updateData(data);
            
            // Update statistics
            this.updateStatistics(data.metadata);
            
            // Auto-freeze layout after 5 seconds (matching the timeout in graph.js)
            setTimeout(() => {
                if (!this.isFrozen && this.freezeBtn) {
                    this.graph.freezeLayout();
                    this.freezeBtn.textContent = 'Unfreeze Layout';
                    this.freezeBtn.classList.remove('btn-secondary');
                    this.freezeBtn.classList.add('btn-primary');
                    this.isFrozen = true;
                    this.updateStatus('Layout frozen - drag nodes to reposition');
                }
            }, 5000);
            
            // Setup node type filters
            this.setupNodeTypeFilters(data.metadata.node_types);
            
            // Center the graph after loading
            setTimeout(() => this.graph.centerGraph(), 1000);
            
            this.updateStatus('Graph loaded successfully');
            
        } catch (error) {
            console.error('Failed to load graph data:', error);
            this.showError(`Failed to load graph data: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }
    
    async updateGraph() {
        const updateBtn = document.getElementById('update-btn');
        const originalText = updateBtn.textContent;
        
        try {
            updateBtn.textContent = 'Updating...';
            updateBtn.disabled = true;
            
            this.updateStatus('Updating graph...');
            
            const response = await fetch('/api/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.updateStatus('Graph updated successfully');
                // Reload graph data
                await this.loadGraphData();
            } else {
                throw new Error(result.message || 'Update failed');
            }
            
        } catch (error) {
            console.error('Failed to update graph:', error);
            this.updateStatus(`Update failed: ${error.message}`);
        } finally {
            updateBtn.textContent = originalText;
            updateBtn.disabled = false;
        }
    }
    
    resetView() {
        this.graph.resetZoom();
        setTimeout(() => this.graph.centerGraph(), 100);
        this.updateStatus('View reset');
    }
    
    async loadQueryTemplates() {
        try {
            const response = await fetch('/api/templates');
            if (!response.ok) return;
            
            const data = await response.json();
            this.queryTemplates = data.templates;
            this.renderQueryTemplates();
            
        } catch (error) {
            console.error('Failed to load query templates:', error);
        }
    }
    
    renderQueryTemplates() {
        const container = document.getElementById('query-templates');
        if (!container) return;
        
        container.innerHTML = '';
        
        this.queryTemplates.forEach(template => {
            const templateElement = document.createElement('div');
            templateElement.className = 'template-item';
            templateElement.innerHTML = `
                <h4>${template.name}</h4>
                <p>${template.description}</p>
            `;
            
            templateElement.addEventListener('click', () => {
                this.showQueryModal(template);
            });
            
            container.appendChild(templateElement);
        });
    }
    
    setupNodeTypeFilters(nodeTypes) {
        const container = document.getElementById('node-type-filters');
        if (!container) return;
        
        container.innerHTML = '';
        
        nodeTypes.forEach(nodeType => {
            const filterItem = document.createElement('div');
            filterItem.className = 'checkbox-item';
            filterItem.innerHTML = `
                <input type="checkbox" id="filter-${nodeType.toLowerCase()}" value="${nodeType}" checked>
                <label for="filter-${nodeType.toLowerCase()}">${nodeType}</label>
            `;
            
            const checkbox = filterItem.querySelector('input');
            checkbox.addEventListener('change', () => {
                this.updateNodeTypeFilters();
                this.applyFilters();
            });
            
            container.appendChild(filterItem);
        });
    }
    
    updateNodeTypeFilters() {
        const checkboxes = document.querySelectorAll('#node-type-filters input[type="checkbox"]');
        this.currentFilters.nodeTypes = Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
    }
    
    applyFilters() {
        this.graph.filterNodes(this.currentFilters);
        
        // Update statistics for filtered view
        const stats = this.graph.getStats();
        document.getElementById('node-count').textContent = stats.nodeCount;
        document.getElementById('edge-count').textContent = stats.edgeCount;
    }
    
    updateStatistics(metadata) {
        const nodeCount = document.getElementById('node-count');
        const edgeCount = document.getElementById('edge-count');
        
        if (nodeCount) nodeCount.textContent = metadata.total_nodes;
        if (edgeCount) edgeCount.textContent = metadata.total_edges;
    }
    
    handleNodeSelected(node) {
        const detailsContainer = document.getElementById('node-details');
        if (!detailsContainer) return;
        
        detailsContainer.innerHTML = `
            <div class="detail-item">
                <div class="detail-label">Name:</div>
                <div class="detail-value">${node.name}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Type:</div>
                <div class="detail-value">${node.type}</div>
            </div>
            ${node.file_path ? `
                <div class="detail-item">
                    <div class="detail-label">File:</div>
                    <div class="detail-value">${node.file_path}</div>
                </div>
            ` : ''}
            ${node.line_start ? `
                <div class="detail-item">
                    <div class="detail-label">Lines:</div>
                    <div class="detail-value">${node.line_start}${node.line_end ? `-${node.line_end}` : ''}</div>
                </div>
            ` : ''}
            ${Object.keys(node.metadata).length > 0 ? `
                <div class="detail-item">
                    <div class="detail-label">Metadata:</div>
                    <div class="detail-value font-mono">${JSON.stringify(node.metadata, null, 2)}</div>
                </div>
            ` : ''}
        `;
    }
    
    handleNodeDeselected() {
        const detailsContainer = document.getElementById('node-details');
        if (detailsContainer) {
            detailsContainer.innerHTML = '<p>Click a node to see details</p>';
        }
    }
    
    showQueryModal(template) {
        const modal = document.getElementById('query-modal');
        const queryInput = document.getElementById('query-input');
        const paramsInput = document.getElementById('query-params');
        
        if (!modal || !queryInput || !paramsInput) return;
        
        queryInput.value = template.query;
        paramsInput.value = JSON.stringify(template.example_params, null, 2);
        
        modal.style.display = 'flex';
    }
    
    hideQueryModal() {
        const modal = document.getElementById('query-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    async executeQuery() {
        const queryInput = document.getElementById('query-input');
        const paramsInput = document.getElementById('query-params');
        const executeBtn = document.getElementById('execute-query-btn');
        
        if (!queryInput || !executeBtn) return;
        
        const query = queryInput.value.trim();
        if (!query) return;
        
        let parameters = {};
        try {
            if (paramsInput.value.trim()) {
                parameters = JSON.parse(paramsInput.value);
            }
        } catch (error) {
            alert('Invalid JSON parameters');
            return;
        }
        
        const originalText = executeBtn.textContent;
        
        try {
            executeBtn.textContent = 'Executing...';
            executeBtn.disabled = true;
            
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    parameters: parameters
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Display results in console for now
            console.log('Query Results:', result);
            alert(`Query executed successfully! ${result.record_count} records returned. Check console for details.`);
            
            this.hideQueryModal();
            
        } catch (error) {
            console.error('Query execution failed:', error);
            alert(`Query failed: ${error.message}`);
        } finally {
            executeBtn.textContent = originalText;
            executeBtn.disabled = false;
        }
    }
    
    showLoading(show) {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.style.display = show ? 'flex' : 'none';
        }
    }
    
    showError(message) {
        const error = document.getElementById('error');
        const errorMessage = document.getElementById('error-message');
        
        if (error && errorMessage) {
            errorMessage.textContent = message;
            error.style.display = 'flex';
        }
    }
    
    hideError() {
        const error = document.getElementById('error');
        if (error) {
            error.style.display = 'none';
        }
    }
    
    updateStatus(message) {
        const statusInfo = document.getElementById('status-info');
        if (statusInfo) {
            statusInfo.textContent = message;
        }
    }
    
    // Utility function for debouncing
    debounce(func, delay) {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        this.debounceTimer = setTimeout(func, delay);
    }
    
    handlePerformanceUpdate(stats) {
        // Update performance indicators in the UI
        const statusControls = document.querySelector('.status-controls');
        if (statusControls) {
            let perfIndicator = document.getElementById('perf-indicator');
            if (!perfIndicator) {
                perfIndicator = document.createElement('span');
                perfIndicator.id = 'perf-indicator';
                statusControls.appendChild(perfIndicator);
            }
            
            // Show FPS and frame time
            perfIndicator.textContent = `${stats.fps} FPS`;
            
            // Change color based on performance
            if (stats.fps >= 55) {
                perfIndicator.style.color = 'var(--success-color)';
            } else if (stats.fps >= 30) {
                perfIndicator.style.color = 'var(--warning-color)';
            } else {
                perfIndicator.style.color = 'var(--error-color)';
            }
        }
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.codeBasedApp = new CodeBasedApp();
});