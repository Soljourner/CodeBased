/**
 * Performance optimization utilities for CodeBased graph visualization
 */

class PerformanceManager {
    constructor(graphVisualizer) {
        this.graph = graphVisualizer;
        this.isWebGLAvailable = this.checkWebGLSupport();
        this.useLevelOfDetail = true;
        this.useViewportCulling = true;
        this.animationFrameId = null;
        
        // Performance thresholds
        this.thresholds = {
            webgl: 2000,        // Use WebGL when nodes > 2000
            lod: 500,           // Use level-of-detail when nodes > 500
            culling: 1000,      // Use viewport culling when nodes > 1000
            lazy: 5000          // Use lazy loading when nodes > 5000
        };
        
        // Cached data for performance
        this.visibleNodes = new Set();
        this.visibleEdges = new Set();
        this.nodeQuadtree = null;
        
        this.init();
    }
    
    init() {
        // Setup viewport culling if enabled
        if (this.useViewportCulling) {
            this.setupViewportCulling();
        }
        
        // Setup performance monitoring
        this.setupPerformanceMonitoring();
    }
    
    checkWebGLSupport() {
        try {
            const canvas = document.createElement('canvas');
            return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
        } catch (e) {
            return false;
        }
    }
    
    shouldUseWebGL(nodeCount) {
        return this.isWebGLAvailable && nodeCount > this.thresholds.webgl;
    }
    
    shouldUseLevelOfDetail(nodeCount) {
        return this.useLevelOfDetail && nodeCount > this.thresholds.lod;
    }
    
    shouldUseViewportCulling(nodeCount) {
        return this.useViewportCulling && nodeCount > this.thresholds.culling;
    }
    
    shouldUseLazyLoading(nodeCount) {
        return nodeCount > this.thresholds.lazy;
    }
    
    optimizeForNodeCount(nodeCount) {
        console.log(`Optimizing for ${nodeCount} nodes`);
        
        const optimizations = {
            webgl: this.shouldUseWebGL(nodeCount),
            levelOfDetail: this.shouldUseLevelOfDetail(nodeCount),
            viewportCulling: this.shouldUseViewportCulling(nodeCount),
            lazyLoading: this.shouldUseLazyLoading(nodeCount)
        };
        
        // Apply optimizations
        if (optimizations.levelOfDetail) {
            this.enableLevelOfDetail();
        }
        
        if (optimizations.viewportCulling) {
            this.enableViewportCulling();
        }
        
        if (optimizations.lazyLoading) {
            this.enableLazyLoading();
        }
        
        if (optimizations.webgl) {
            this.enableWebGLRenderer();
        }
        
        console.log('Applied optimizations:', optimizations);
        return optimizations;
    }
    
    enableLevelOfDetail() {
        // Implement level-of-detail rendering based on zoom level
        const originalRender = this.graph.render.bind(this.graph);
        
        this.graph.render = () => {
            const zoom = this.graph.currentZoom || 1;
            
            // Adjust detail level based on zoom
            if (zoom < 0.3) {
                this.renderLowDetail();
            } else if (zoom < 0.7) {
                this.renderMediumDetail();
            } else {
                originalRender();
            }
        };
    }
    
    renderLowDetail() {
        // Only show major nodes (Files, Classes)
        const majorTypes = ['File', 'Class'];
        
        this.graph.nodeElements
            .style('opacity', d => majorTypes.includes(d.type) ? 1 : 0.1);
        
        // Hide node labels
        this.graph.nodeElements.selectAll('.node-label')
            .style('opacity', 0);
        
        // Simplify edges
        this.graph.edgeElements
            .style('opacity', 0.2)
            .style('stroke-width', 1);
    }
    
    renderMediumDetail() {
        // Show most nodes but simplified
        this.graph.nodeElements
            .style('opacity', d => d.type === 'Variable' ? 0.3 : 1);
        
        // Show labels for major nodes only
        this.graph.nodeElements.selectAll('.node-label')
            .style('opacity', d => ['File', 'Class', 'Function'].includes(d.type) ? 1 : 0);
        
        // Normal edges
        this.graph.edgeElements
            .style('opacity', 0.6)
            .style('stroke-width', 1.5);
    }
    
    enableViewportCulling() {
        // Only render nodes/edges within viewport bounds
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
        }
        
        const performCulling = () => {
            const bounds = this.getViewportBounds();
            this.updateVisibleElements(bounds);
            this.animationFrameId = requestAnimationFrame(performCulling);
        };
        
        performCulling();
    }
    
    getViewportBounds() {
        const svg = this.graph.svg.node();
        const transform = d3.zoomTransform(svg);
        
        return {
            left: -transform.x / transform.k,
            top: -transform.y / transform.k,
            right: (this.graph.width - transform.x) / transform.k,
            bottom: (this.graph.height - transform.y) / transform.k
        };
    }
    
    updateVisibleElements(bounds) {
        // Update visible nodes
        this.graph.nodeElements.each((d, i, nodes) => {
            const isVisible = (
                d.x >= bounds.left && d.x <= bounds.right &&
                d.y >= bounds.top && d.y <= bounds.bottom
            );
            
            const element = d3.select(nodes[i]);
            if (isVisible) {
                this.visibleNodes.add(d.id);
                element.style('display', 'block');
            } else {
                this.visibleNodes.delete(d.id);
                element.style('display', 'none');
            }
        });
        
        // Update visible edges
        this.graph.edgeElements.each((d, i, edges) => {
            const sourceVisible = this.visibleNodes.has(d.source.id);
            const targetVisible = this.visibleNodes.has(d.target.id);
            const isVisible = sourceVisible || targetVisible;
            
            const element = d3.select(edges[i]);
            if (isVisible) {
                this.visibleEdges.add(d);
                element.style('display', 'block');
            } else {
                this.visibleEdges.delete(d);
                element.style('display', 'none');
            }
        });
    }
    
    enableLazyLoading() {
        // Implement lazy loading for very large graphs
        const originalUpdateData = this.graph.updateData.bind(this.graph);
        
        this.graph.updateData = (graphData) => {
            if (graphData.nodes.length > this.thresholds.lazy) {
                this.loadDataInChunks(graphData);
            } else {
                originalUpdateData(graphData);
            }
        };
    }
    
    loadDataInChunks(graphData) {
        const chunkSize = 1000;
        const nodeChunks = this.chunkArray(graphData.nodes, chunkSize);
        const edgeChunks = this.chunkArray(graphData.edges, chunkSize);
        
        let currentChunk = 0;
        const totalChunks = Math.max(nodeChunks.length, edgeChunks.length);
        
        const loadNextChunk = () => {
            if (currentChunk < totalChunks) {
                const nodes = nodeChunks[currentChunk] || [];
                const edges = edgeChunks[currentChunk] || [];
                
                // Append to existing data
                this.graph.nodes = [...this.graph.nodes, ...nodes];
                this.graph.edges = [...this.graph.edges, ...edges];
                
                // Update visualization
                this.graph.render();
                this.graph.restart();
                
                currentChunk++;
                
                // Load next chunk after a small delay
                setTimeout(loadNextChunk, 50);
                
                // Update progress
                const progress = Math.round((currentChunk / totalChunks) * 100);
                this.updateLoadingProgress(progress);
            } else {
                this.hideLoadingProgress();
            }
        };
        
        // Start loading
        this.showLoadingProgress();
        loadNextChunk();
    }
    
    chunkArray(array, chunkSize) {
        const chunks = [];
        for (let i = 0; i < array.length; i += chunkSize) {
            chunks.push(array.slice(i, i + chunkSize));
        }
        return chunks;
    }
    
    enableWebGLRenderer() {
        if (!this.isWebGLAvailable) {
            console.warn('WebGL not available, falling back to SVG renderer');
            return;
        }
        
        console.log('Enabling WebGL renderer for large graph');
        
        // This would require a more complex implementation
        // For now, we'll optimize the SVG renderer
        this.optimizeSVGRenderer();
    }
    
    optimizeSVGRenderer() {
        // Reduce DOM updates by batching
        const svg = this.graph.svg;
        
        // Use CSS transforms instead of attribute changes
        this.graph.nodeElements
            .style('will-change', 'transform')
            .style('transform-origin', 'center');
        
        // Optimize edge rendering
        this.graph.edgeElements
            .style('shape-rendering', 'optimizeSpeed');
        
        // Use requestAnimationFrame for smooth animations
        const originalRestart = this.graph.restart.bind(this.graph);
        this.graph.restart = () => {
            if (this.animationFrameId) {
                cancelAnimationFrame(this.animationFrameId);
            }
            
            this.animationFrameId = requestAnimationFrame(() => {
                originalRestart();
            });
        };
    }
    
    setupViewportCulling() {
        // Setup intersection observer for more efficient culling
        if ('IntersectionObserver' in window) {
            this.intersectionObserver = new IntersectionObserver(
                (entries) => {
                    entries.forEach(entry => {
                        const element = d3.select(entry.target);
                        element.style('opacity', entry.isIntersecting ? 1 : 0);
                    });
                },
                {
                    root: this.graph.svg.node(),
                    threshold: 0.1
                }
            );
        }
    }
    
    setupPerformanceMonitoring() {
        // Monitor FPS and performance metrics
        this.performanceStats = {
            fps: 60,
            frameTime: 0,
            lastFrame: performance.now(),
            frameCount: 0
        };
        
        const updateStats = () => {
            const now = performance.now();
            this.performanceStats.frameTime = now - this.performanceStats.lastFrame;
            this.performanceStats.lastFrame = now;
            this.performanceStats.frameCount++;
            
            if (this.performanceStats.frameCount % 60 === 0) {
                this.performanceStats.fps = Math.round(1000 / this.performanceStats.frameTime);
                this.onPerformanceUpdate?.(this.performanceStats);
            }
            
            requestAnimationFrame(updateStats);
        };
        
        requestAnimationFrame(updateStats);
    }
    
    showLoadingProgress() {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.style.display = 'flex';
            loading.innerHTML = `
                <div class="loading-spinner"></div>
                <p>Loading large graph...</p>
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
            `;
        }
    }
    
    updateLoadingProgress(percent) {
        const progressFill = document.getElementById('progress-fill');
        if (progressFill) {
            progressFill.style.width = `${percent}%`;
        }
    }
    
    hideLoadingProgress() {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.style.display = 'none';
        }
    }
    
    // Public API
    getPerformanceStats() {
        return this.performanceStats;
    }
    
    setThreshold(type, value) {
        if (this.thresholds.hasOwnProperty(type)) {
            this.thresholds[type] = value;
        }
    }
    
    // Event handler (to be overridden)
    onPerformanceUpdate(stats) {
        // Override in application
    }
    
    cleanup() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
        }
        
        if (this.intersectionObserver) {
            this.intersectionObserver.disconnect();
        }
    }
}

// Export for use in main application
window.PerformanceManager = PerformanceManager;