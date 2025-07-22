/**
 * D3.js Graph Visualization for CodeBased
 */

class GraphVisualizer {
    constructor(containerId) {
        this.containerId = containerId;
        this.svg = d3.select(containerId);
        this.width = 0;
        this.height = 0;
        this.nodes = [];
        this.edges = [];
        this.filteredNodes = [];
        this.filteredEdges = [];
        this.simulation = null;
        this.selectedNode = null;
        this.isFrozen = false;
        
        // Graph elements
        this.g = null;
        this.nodeGroup = null;
        this.edgeGroup = null;
        
        // Zoom behavior
        this.zoom = null;
        this.currentZoom = 1;
        
        // Color scheme for different node types
        this.nodeColors = {
            'File': '#8b5cf6',
            'Module': '#06b6d4',
            'Class': '#10b981',
            'Function': '#f59e0b',
            'Variable': '#ef4444',
            'Import': '#6b7280'
        };
        
        // Node size mapping - increased for better visibility
        this.nodeSizes = {
            'File': 20,
            'Module': 18,
            'Class': 16,
            'Function': 14,
            'Variable': 12,
            'Import': 10
        };
        
        this.init();
        this.createLegend();
    }
    
    init() {
        // Get container dimensions
        const container = d3.select(this.containerId).node();
        this.width = container.clientWidth;
        this.height = container.clientHeight;
        
        // Setup SVG
        this.svg
            .attr('width', this.width)
            .attr('height', this.height);
        
        // Create main group for zoom/pan
        this.g = this.svg.append('g')
            .attr('class', 'graph-group');
        
        // Create groups for edges and nodes (order matters for rendering)
        this.edgeGroup = this.g.append('g')
            .attr('class', 'edges');
            
        this.edgeLabelGroup = this.g.append('g')
            .attr('class', 'edge-labels');
            
        this.nodeGroup = this.g.append('g')
            .attr('class', 'nodes');
            
        // Create tooltip
        this.tooltip = d3.select('body').append('div')
            .attr('class', 'graph-tooltip')
            .style('opacity', 0)
            .style('position', 'absolute')
            .style('pointer-events', 'none');
        
        // Setup zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
                this.currentZoom = event.transform.k;
                this.updateZoomDisplay();
            });
        
        this.svg.call(this.zoom);
        
        // Setup force simulation - adjusted for larger nodes
        this.simulation = d3.forceSimulation()
            .force('link', d3.forceLink().id(d => d.id).distance(120))
            .force('charge', d3.forceManyBody().strength(-500))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(d => this.getNodeSize(d) + 5))
            .alphaDecay(0.05);  // Faster cooling for quicker stabilization
        
        // Handle window resize
        window.addEventListener('resize', () => this.handleResize());
    }
    
    updateData(graphData) {
        this.nodes = graphData.nodes || [];
        this.edges = graphData.edges || [];
        
        // Initialize filtered data to show all nodes/edges by default
        this.filteredNodes = [...this.nodes];
        this.filteredEdges = [...this.edges];
        
        // Update simulation data - use ALL nodes and edges for stable physics
        this.simulation.nodes(this.nodes);
        this.simulation.force('link').links(this.edges);
        
        this.render();
        this.restart();
    }
    
    render() {
        this.renderEdges();
        this.renderNodes();
    }
    
    renderEdges() {
        const edges = this.edgeGroup
            .selectAll('.edge')
            .data(this.edges, d => `${d.source.id || d.source}-${d.target.id || d.target}-${d.relationship_type}`); // Use ALL edges
        
        // Don't remove edges - keep them all in DOM
        
        const edgesEnter = edges.enter()
            .append('line')
            .attr('class', d => `edge ${d.relationship_type.toLowerCase()}`)
            .attr('stroke', '#64748b')
            .attr('stroke-width', 2)
            .attr('opacity', 0.5);
        
        // Merge enter and update selections
        const allEdges = edgesEnter.merge(edges);
        
        // Apply visibility-based filtering - hide edges if either endpoint is filtered out
        const visibleNodeIds = new Set(this.filteredNodes.map(n => n.id));
        allEdges.style('opacity', d => {
            const sourceVisible = visibleNodeIds.has(d.source.id || d.source);
            const targetVisible = visibleNodeIds.has(d.target.id || d.target);
            return (sourceVisible && targetVisible) ? 0.5 : 0;
        });
            
        // Add hover handlers to show/hide labels
        edgesEnter.on('mouseenter', (event, d) => {
            // Show label for this edge
            const edgeId = `${d.source.id || d.source}-${d.target.id || d.target}-${d.relationship_type}`;
            this.edgeLabelElements
                .filter(function(label) {
                    const labelId = `${label.source.id || label.source}-${label.target.id || label.target}-${label.relationship_type}`;
                    return labelId === edgeId;
                })
                .transition()
                .duration(200)
                .style('opacity', 1);
        }).on('mouseleave', (event, d) => {
            // Hide label for this edge
            const edgeId = `${d.source.id || d.source}-${d.target.id || d.target}-${d.relationship_type}`;
            this.edgeLabelElements
                .filter(function(label) {
                    const labelId = `${label.source.id || label.source}-${label.target.id || label.target}-${label.relationship_type}`;
                    return labelId === edgeId;
                })
                .transition()
                .duration(200)
                .style('opacity', 0);
        });
        
        // Add edge labels for all relationships in separate group  
        const edgeLabels = this.edgeLabelGroup
            .selectAll('.edge-label-group')
            .data(this.edges, d => `${d.source.id || d.source}-${d.target.id || d.target}-${d.relationship_type}`); // Use ALL edges
        
        // Don't remove edge labels - keep them all in DOM
        
        const edgeLabelsEnter = edgeLabels.enter()
            .append('g')
            .attr('class', 'edge-label-group')
            .style('opacity', 0)
            .style('pointer-events', 'none');  // Start hidden and non-interactive
            
        // Add background rect for better readability
        edgeLabelsEnter.append('rect')
            .attr('class', 'edge-label-bg')
            .attr('fill', 'white')
            .attr('stroke', '#e2e8f0')
            .attr('stroke-width', 1)
            .attr('rx', 3);
            
        // Add text
        edgeLabelsEnter.append('text')
            .attr('class', 'edge-label')
            .attr('font-size', '11px')
            .attr('font-weight', '500')
            .attr('fill', '#475569')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .text(d => this.formatRelationshipType(d.relationship_type));
            
        // Update background size to fit text
        edgeLabelsEnter.each(function() {
            const text = d3.select(this).select('text');
            const bbox = text.node().getBBox();
            d3.select(this).select('rect')
                .attr('x', bbox.x - 4)
                .attr('y', bbox.y - 2)
                .attr('width', bbox.width + 8)
                .attr('height', bbox.height + 4);
        });
        
        // Update all edges to have hover handlers
        this.edgeElements = allEdges;
        this.edgeElements.on('mouseenter', (event, d) => {
            // Show label for this edge
            const edgeId = `${d.source.id || d.source}-${d.target.id || d.target}-${d.relationship_type}`;
            this.edgeLabelElements
                .filter(function(label) {
                    const labelId = `${label.source.id || label.source}-${label.target.id || label.target}-${label.relationship_type}`;
                    return labelId === edgeId;
                })
                .transition()
                .duration(200)
                .style('opacity', 1);
        }).on('mouseleave', (event, d) => {
            // Hide label for this edge
            const edgeId = `${d.source.id || d.source}-${d.target.id || d.target}-${d.relationship_type}`;
            this.edgeLabelElements
                .filter(function(label) {
                    const labelId = `${label.source.id || label.source}-${label.target.id || label.target}-${label.relationship_type}`;
                    return labelId === edgeId;
                })
                .transition()
                .duration(200)
                .style('opacity', 0);
        });
        
        this.edgeLabelElements = edgeLabelsEnter.merge(edgeLabels);
    }
    
    renderNodes() {
        // Always render ALL nodes, never remove them - use visibility for filtering
        const nodeSelection = this.nodeGroup
            .selectAll('.node-group')
            .data(this.nodes, d => d.id); // Use ALL nodes, not filtered
        
        // Create new node groups for nodes that don't exist yet
        const nodeGroupsEnter = nodeSelection.enter()
            .append('g')
            .attr('class', 'node-group')
            .call(this.dragBehavior());
        
        // Add circles to new node groups
        nodeGroupsEnter.append('circle')
            .attr('class', d => `node ${d.type.toLowerCase()}`)
            .attr('r', d => this.getNodeSize(d))
            .attr('fill', d => this.getNodeColor(d))
            .attr('stroke', '#ffffff')
            .attr('stroke-width', 2);
        
        // Add labels to new node groups
        nodeGroupsEnter.append('text')
            .attr('class', 'node-label')
            .attr('dy', d => this.getNodeSize(d) + 12)
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .attr('fill', '#1e293b')
            .text(d => this.getNodeLabel(d));
        
        // Merge enter and update selections - now we have ALL nodes in DOM
        const allNodes = nodeGroupsEnter.merge(nodeSelection);
        
        // Add event handlers to all nodes (enter + update)
        allNodes.on('click', (event, d) => {
            event.stopPropagation();
            this.selectNode(d);
        });
        
        allNodes.on('mouseenter', (event, d) => {
            this.highlightNode(d, true);
            this.showTooltip(event, d);
        }).on('mouseleave', (event, d) => {
            this.highlightNode(d, false);
            this.hideTooltip();
        });
        
        // Update the nodeElements reference to ALL nodes
        this.nodeElements = allNodes;
    }
    
    dragBehavior() {
        return d3.drag()
            .on('start', (event, d) => {
                // Fix the node position when dragging starts
                d.fx = d.x;
                d.fy = d.y;
            })
            .on('drag', (event, d) => {
                // Update position while dragging
                d.fx = event.x;
                d.fy = event.y;
                // Manually update positions without restarting simulation
                this.updateNodePosition(d);
            })
            .on('end', (event, d) => {
                // Keep the node fixed at its new position
                // Don't release fx/fy to prevent simulation from moving it
            });
    }
    
    restart() {
        this.simulation.on('tick', () => {
            // Update edge positions
            this.edgeElements
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            // Update edge label positions
            this.edgeLabelElements
                .attr('transform', d => {
                    const x = (d.source.x + d.target.x) / 2;
                    const y = (d.source.y + d.target.y) / 2;
                    return `translate(${x}, ${y})`;
                });
            
            // Update node positions
            this.nodeElements
                .attr('transform', d => `translate(${d.x},${d.y})`);
        });
        
        this.simulation.alpha(1).restart();
        
        // Stop simulation after stabilization
        setTimeout(() => {
            this.simulation.stop();
            // Fix all nodes at their current positions
            this.nodes.forEach(node => {
                node.fx = node.x;
                node.fy = node.y;
            });
            this.isFrozen = true;
        }, 5000);  // Stop after 5 seconds
    }
    
    selectNode(node) {
        // Remove previous selection
        this.nodeElements.selectAll('.node').classed('selected', false);
        
        // Select new node
        if (this.selectedNode !== node) {
            this.selectedNode = node;
            this.nodeElements
                .filter(d => d.id === node.id)
                .selectAll('.node')
                .classed('selected', true);
            
            // Trigger node selection event
            this.onNodeSelected(node);
        } else {
            this.selectedNode = null;
            this.onNodeDeselected();
        }
    }
    
    highlightNode(node, highlight) {
        const nodeElement = this.nodeElements.filter(d => d.id === node.id);
        
        if (highlight) {
            nodeElement.selectAll('.node')
                .transition()
                .duration(200)
                .attr('transform', 'scale(1.2)');
            
            // Highlight connected edges
            this.edgeElements
                .filter(d => d.source.id === node.id || d.target.id === node.id)
                .transition()
                .duration(200)
                .attr('opacity', 1)
                .attr('stroke-width', 3);
        } else {
            nodeElement.selectAll('.node')
                .transition()
                .duration(200)
                .attr('transform', 'scale(1)');
            
            // Reset edge highlighting
            this.edgeElements
                .transition()
                .duration(200)
                .attr('opacity', 0.5)
                .attr('stroke-width', 2);
        }
    }
    
    getNodeColor(node) {
        return this.nodeColors[node.type] || '#6b7280';
    }
    
    getNodeSize(node) {
        return this.nodeSizes[node.type] || 6;
    }
    
    getNodeLabel(node) {
        if (node.name.length > 15) {
            return node.name.substring(0, 12) + '...';
        }
        return node.name;
    }
    
    centerGraph() {
        if (this.nodes.length === 0) return;
        
        // Calculate bounding box
        const bounds = this.getGraphBounds();
        
        // Calculate scale and translation to fit graph
        const scale = 0.9 * Math.min(
            this.width / (bounds.maxX - bounds.minX),
            this.height / (bounds.maxY - bounds.minY)
        );
        
        const translate = [
            this.width / 2 - scale * (bounds.minX + bounds.maxX) / 2,
            this.height / 2 - scale * (bounds.minY + bounds.maxY) / 2
        ];
        
        // Apply transform
        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
    }
    
    getGraphBounds() {
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;
        
        this.nodes.forEach(node => {
            if (node.x < minX) minX = node.x;
            if (node.x > maxX) maxX = node.x;
            if (node.y < minY) minY = node.y;
            if (node.y > maxY) maxY = node.y;
        });
        
        return { minX, maxX, minY, maxY };
    }
    
    resetZoom() {
        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity);
    }
    
    updateZoomDisplay() {
        const zoomPercent = Math.round(this.currentZoom * 100);
        const zoomDisplay = document.getElementById('zoom-level');
        if (zoomDisplay) {
            zoomDisplay.textContent = `${zoomPercent}%`;
        }
    }
    
    filterNodes(filters) {
        const { nodeTypes, searchText, fileFilter } = filters;
        
        let filteredNodes = this.nodes;
        let filteredEdges = this.edges;
        
        // Filter by node types - fix case sensitivity bug
        if (nodeTypes && nodeTypes.length > 0) {
            const lowerCaseNodeTypes = nodeTypes.map(t => String(t).toLowerCase());
            filteredNodes = filteredNodes.filter(node => 
                node && node.type && lowerCaseNodeTypes.includes(String(node.type).toLowerCase())
            );
        }
        
        // Filter by search text
        if (searchText) {
            const searchLower = searchText.toLowerCase();
            filteredNodes = filteredNodes.filter(node => 
                node.name.toLowerCase().includes(searchLower) ||
                (node.file_path && node.file_path.toLowerCase().includes(searchLower))
            );
        }
        
        // Filter by file path
        if (fileFilter) {
            const filterLower = fileFilter.toLowerCase();
            filteredNodes = filteredNodes.filter(node => 
                node.file_path && node.file_path.toLowerCase().includes(filterLower)
            );
        }
        
        // Filter edges to only include connections between visible nodes
        const visibleNodeIds = new Set(filteredNodes.map(n => n.id));
        filteredEdges = filteredEdges.filter(edge => 
            visibleNodeIds.has(edge.source.id || edge.source) && 
            visibleNodeIds.has(edge.target.id || edge.target)
        );
        
        // Update visualization
        this.updateFilteredData(filteredNodes, filteredEdges);
    }
    
    updateFilteredData(nodes, edges) {
        // Store the filtered data (for statistics and visibility)
        this.filteredNodes = nodes;
        this.filteredEdges = edges;
        
        // DON'T update simulation - keep all nodes in simulation at all times
        // This prevents position loss and maintains stability
        
        // Apply visibility changes efficiently without full re-render
        this.applyFilterVisibility();
        
        // No need to restart simulation since we didn't change its data
    }
    
    applyFilterVisibility() {
        const visibleNodeIds = new Set(this.filteredNodes.map(n => n.id));

        // Update node visibility efficiently
        if (this.nodeElements) {
            this.nodeElements
                .style('opacity', d => visibleNodeIds.has(d.id) ? 1 : 0)
                .style('pointer-events', d => visibleNodeIds.has(d.id) ? 'all' : 'none');
        }

        // Update edge visibility efficiently
        if (this.edgeElements) {
            this.edgeElements
                .style('opacity', d => {
                    const sourceVisible = visibleNodeIds.has(d.source.id || d.source);
                    const targetVisible = visibleNodeIds.has(d.target.id || d.target);
                    return (sourceVisible && targetVisible) ? 0.8 : 0; // Increased opacity
                })
                .style('pointer-events', d => {
                    const sourceVisible = visibleNodeIds.has(d.source.id || d.source);
                    const targetVisible = visibleNodeIds.has(d.target.id || d.target);
                    return (sourceVisible && targetVisible) ? 'all' : 'none';
                });
        }
    }
    
    
    handleResize() {
        const container = d3.select(this.containerId).node();
        this.width = container.clientWidth;
        this.height = container.clientHeight;
        
        this.svg
            .attr('width', this.width)
            .attr('height', this.height);
        
        // Update force center
        this.simulation.force('center', d3.forceCenter(this.width / 2, this.height / 2));
        this.simulation.alpha(0.3).restart();
    }
    
    // Event handlers (to be overridden by application)
    onNodeSelected(node) {
        // Override in application
    }
    
    onNodeDeselected() {
        // Override in application
    }
    
    // Public API methods
    clear() {
        this.nodes = [];
        this.edges = [];
        this.filteredNodes = [];
        this.filteredEdges = [];
        this.selectedNode = null;
        this.nodeGroup.selectAll('*').remove();
        this.edgeGroup.selectAll('*').remove();
        this.edgeLabelGroup.selectAll('*').remove();
        this.simulation.nodes([]);
        this.simulation.force('link').links([]);
    }
    
    getSelectedNode() {
        return this.selectedNode;
    }
    
    getStats() {
        return {
            nodeCount: this.filteredNodes.length,
            edgeCount: this.filteredEdges.length,
            nodeTypes: [...new Set(this.filteredNodes.map(n => n.type))]
        };
    }
    
    createLegend() {
        const legendContainer = d3.select('#legend-items');
        legendContainer.selectAll('*').remove();
        
        // Create legend items for each node type
        const nodeTypes = Object.keys(this.nodeColors);
        
        nodeTypes.forEach(type => {
            const item = legendContainer.append('div')
                .attr('class', 'legend-item');
                
            item.append('div')
                .attr('class', 'legend-color')
                .style('background-color', this.nodeColors[type]);
                
            item.append('span')
                .text(type);
        });
    }
    
    formatRelationshipType(type) {
        // Convert relationship types to more readable format
        const typeMap = {
            'FILE_CONTAINS_MODULE': 'contains',
            'FILE_CONTAINS_CLASS': 'contains',
            'FILE_CONTAINS_FUNCTION': 'contains',
            'FILE_CONTAINS_VARIABLE': 'contains',
            'FILE_CONTAINS_IMPORT': 'contains',
            'MODULE_CONTAINS_CLASS': 'contains',
            'MODULE_CONTAINS_FUNCTION': 'contains',
            'MODULE_CONTAINS_VARIABLE': 'contains',
            'CLASS_CONTAINS_FUNCTION': 'contains',
            'CLASS_CONTAINS_VARIABLE': 'contains',
            'FUNCTION_CONTAINS_VARIABLE': 'contains',
            'FUNCTION_CONTAINS_FUNCTION': 'contains',
            'CLASS_CONTAINS_CLASS': 'contains',
            'CALLS': 'calls',
            'IMPORTS': 'imports',
            'INHERITS': 'inherits',
            'USES': 'uses',
            'DECORATES': 'decorates'
        };
        
        return typeMap[type] || type.toLowerCase();
    }
    
    updateNodePosition(node) {
        // Update node position
        this.nodeElements
            .filter(d => d.id === node.id)
            .attr('transform', d => `translate(${d.fx},${d.fy})`);
            
        // Update connected edges
        this.edgeElements
            .filter(d => d.source.id === node.id || d.target.id === node.id)
            .attr('x1', d => d.source.id === node.id ? node.fx : d.source.x)
            .attr('y1', d => d.source.id === node.id ? node.fy : d.source.y)
            .attr('x2', d => d.target.id === node.id ? node.fx : d.target.x)
            .attr('y2', d => d.target.id === node.id ? node.fy : d.target.y);
            
        // Update edge labels
        this.edgeLabelElements
            .filter(d => d.source.id === node.id || d.target.id === node.id)
            .attr('transform', d => {
                const x1 = d.source.id === node.id ? node.fx : d.source.x;
                const y1 = d.source.id === node.id ? node.fy : d.source.y;
                const x2 = d.target.id === node.id ? node.fx : d.target.x;
                const y2 = d.target.id === node.id ? node.fy : d.target.y;
                return `translate(${(x1 + x2) / 2}, ${(y1 + y2) / 2})`;
            });
    }
    
    freezeLayout() {
        // Stop the simulation
        this.simulation.stop();
        
        // Fix all nodes at their current positions
        this.nodes.forEach(node => {
            node.fx = node.x;
            node.fy = node.y;
        });
        
        this.isFrozen = true;
    }
    
    unfreezeLayout() {
        // Release all fixed positions for all nodes
        this.nodes.forEach(node => {
            node.fx = null;
            node.fy = null;
        });
        
        this.isFrozen = false;
        
        // Restart simulation
        this.simulation.alpha(0.3).restart();
    }
    
    showTooltip(event, node) {
        const content = `
            <div class="tooltip-header">${node.type}: ${node.name}</div>
            <div class="tooltip-body">
                ${node.file_path ? `<div class="tooltip-item"><span class="tooltip-label">File:</span> ${node.file_path}</div>` : ''}
                ${node.line_start ? `<div class="tooltip-item"><span class="tooltip-label">Lines:</span> ${node.line_start}${node.line_end && node.line_end !== node.line_start ? `-${node.line_end}` : ''}</div>` : ''}
                ${node.metadata && Object.keys(node.metadata).length > 0 ? `
                    <div class="tooltip-section">Details:</div>
                    ${Object.entries(node.metadata)
                        .filter(([key, value]) => value !== null && value !== undefined && key !== 'file_id')
                        .map(([key, value]) => `<div class="tooltip-item"><span class="tooltip-label">${this.formatMetadataKey(key)}:</span> ${this.formatMetadataValue(value)}</div>`)
                        .join('')}
                ` : ''}
            </div>
        `;
        
        this.tooltip
            .html(content)
            .transition()
            .duration(200)
            .style('opacity', 1);
            
        // Position tooltip
        const tooltipNode = this.tooltip.node();
        const bbox = tooltipNode.getBoundingClientRect();
        const x = event.pageX + 10;
        const y = event.pageY - bbox.height / 2;
        
        // Keep tooltip on screen
        const finalX = Math.min(x, window.innerWidth - bbox.width - 10);
        const finalY = Math.max(10, Math.min(y, window.innerHeight - bbox.height - 10));
        
        this.tooltip
            .style('left', finalX + 'px')
            .style('top', finalY + 'px');
    }
    
    hideTooltip() {
        this.tooltip
            .transition()
            .duration(200)
            .style('opacity', 0);
    }
    
    formatMetadataKey(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    formatMetadataValue(value) {
        if (typeof value === 'boolean') {
            return value ? 'Yes' : 'No';
        }
        if (typeof value === 'string' && value.length > 50) {
            return value.substring(0, 50) + '...';
        }
        return value;
    }
}