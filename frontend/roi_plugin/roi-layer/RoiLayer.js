// RoiLayer.js - Map layer plugin
// Location: plugins/roi-layer/RoiLayer.js

import { Plugin } from '../../core/Plugin.js';
import { stateManager } from '../../core/StateManager.js';
import { eventBus } from '../../core/EventBus.js';
import { roiService } from '../../services/RoiService.js';

export class RoiLayer extends Plugin {
    constructor(app, options = {}) {
        super(app, options);
        this.layer = null;
        this.source = null;
        this.selectionLayer = null;
        this.selectionSource = null;
        this.isVisible = true;
        this.isSelecting = false;
        this.currentROI = null;
        this.searchResults = [];
    }

    async init() {
        console.log('RoiLayer: Initializing...');

        // Create the OpenLayers layers
        this.createLayers();

        // Register in Layers panel
        eventBus.emit('layers:add', {
            id: 'roi',
            name: 'ROI Search',
            active: true,
            pluginId: this.pluginId,
            title: 'Region of Interest object search overlay'
        });

        // Show the controls accordion
        eventBus.emit('roiControls:show');
    }

    createLayers() {
        const map = stateManager.get('map');

        if (!map) {
            console.warn('RoiLayer: Map not available');
            return;
        }

        // Create source for search results
        this.source = new ol.source.Vector();

        // Create layer for search results
        this.layer = new ol.layer.Vector({
            source: this.source,
            style: (feature) => this.getResultStyle(feature),
            zIndex: 150
        });

        // Create source for ROI selection
        this.selectionSource = new ol.source.Vector();

        // Create layer for ROI selection
        this.selectionLayer = new ol.layer.Vector({
            source: this.selectionSource,
            style: this.getSelectionStyle(),
            zIndex: 151
        });

        // Add layers to map
        map.addLayer(this.layer);
        map.addLayer(this.selectionLayer);
        
        // Add interaction for ROI selection
        this.setupSelectionInteraction(map);

        console.log('RoiLayer: Layers added to map');
    }

    setupSelectionInteraction(map) {
        // Create draw interaction for rectangle selection
        this.drawInteraction = new ol.interaction.Draw({
            source: this.selectionSource,
            type: 'Circle',
            geometryFunction: ol.interaction.Draw.createBox(),
            condition: () => this.isSelecting
        });

        this.drawInteraction.on('drawend', (event) => {
            this.handleROISelection(event.feature);
        });

        map.addInteraction(this.drawInteraction);
    }

    handleROISelection(feature) {
        const geometry = feature.getGeometry();
        const extent = geometry.getExtent();
        
        // Convert extent to bbox format [x1, y1, x2, y2]
        this.currentROI = {
            bbox: [extent[0], extent[1], extent[2], extent[3]],
            feature: feature
        };

        console.log('RoiLayer: ROI selected:', this.currentROI.bbox);

        // Emit selection event
        eventBus.emit('roi:selected', this.currentROI);

        // Clear previous selection after a delay
        setTimeout(() => {
            this.selectionSource.clear();
        }, 60000);

        // Disable selection mode
        this.isSelecting = false;
    }

    getResultStyle(feature) {
        const opacity = 0.7;

        return new ol.style.Style({
            stroke: new ol.style.Stroke({
                color: `rgba(255, 0, 0, ${opacity})`,
                width: 2
            }),
            fill: new ol.style.Fill({
                color: `rgba(255, 0, 0, ${opacity * 0.3})`
            }),
            text: new ol.style.Text({
                text: feature.get('section') || '',
                font: '12px sans-serif',
                fill: new ol.style.Fill({ color: '#fff' }),
                stroke: new ol.style.Stroke({ color: '#000', width: 3 }),
                offsetY: -15
            })
        });
    }

    getSelectionStyle() {
        return new ol.style.Style({
            stroke: new ol.style.Stroke({
                color: 'rgba(0, 150, 255, 1)',
                width: 3,
                lineDash: [10, 10]
            }),
            fill: new ol.style.Fill({
                color: 'rgba(0, 150, 255, 0.1)'
            })
        });
    }

    async performSearch(searchParams) {
        try {
            console.log('RoiLayer: Performing search with params:', searchParams);
            
            // Check if ROI has been selected
            if (!this.currentROI || !this.currentROI.bbox) {
                throw new Error('Please select a ROI area on the map before searching');
            }

            eventBus.emit('loading:start');

            // Clear previous results
            this.source.clear();

            // Get projectId from params or session storage
            const projectId = searchParams.projectId || sessionStorage.getItem('projectId');
            
            if (!projectId) {
                throw new Error('Project ID not found in params or session storage');
            }

            console.log('RoiLayer: Using ROI bbox:', this.currentROI.bbox);

            // Perform ROI search (backend decides sync vs async based on section count)
            const response = await roiService.searchROI({
                projectId: projectId,
                biosample: searchParams.biosample,
                section: searchParams.section,
                bbox: this.currentROI.bbox,
                stain: searchParams.stain || 'NISL',
                description: searchParams.description
            });

            if (response.processing_mode === 'sync') {
                // Synchronous - results ready immediately
                console.log('RoiLayer: Sync processing completed');
                
                // Extract project ID and hash from results URL
                const urlParts = response.results_url.split('/');
                const hashValue = urlParts[urlParts.length - 1];
                const projectId = urlParts[urlParts.length - 2];
                
                // Fetch and render the results
                const results = await roiService.getSearchResults(projectId, hashValue);
                this.searchResults = results;
                this.renderSearchResults(results);
                
                eventBus.emit('roi:searchCompleted', {
                    ...results,
                    processing_mode: 'sync',
                    viewer_url: response.viewer_url
                });
                
            } else {
                // Asynchronous - need to poll for results
                console.log('RoiLayer: Async processing started, task:', response.task_id);
                eventBus.emit('roi:asyncTaskStarted', response);
                
                // Start polling for task status
                this.pollForResults(response.task_id, searchParams.projectId);
            }

        } catch (error) {
            console.error('RoiLayer: Search failed:', error);
            eventBus.emit('roi:searchFailed', error);
            eventBus.emit('loading:end');
        }
    }

    async pollForResults(taskId, projectId) {
        try {
            // Poll for task completion
            const result = await roiService.pollTaskStatus(taskId);
            
            if (result.state === 'SUCCESS') {
                // Extract hash from result
                const hashValue = result.result?.hash_value;
                
                if (hashValue) {
                    // Fetch and render the results
                    const results = await roiService.getSearchResults(projectId, hashValue);
                    this.searchResults = results;
                    this.renderSearchResults(results);
                    
                    eventBus.emit('roi:searchCompleted', {
                        ...results,
                        processing_mode: 'async',
                        task_id: taskId,
                        viewer_url: result.viewer_url
                    });
                }
            }
        } catch (error) {
            console.error('RoiLayer: Async task failed:', error);
            eventBus.emit('roi:searchFailed', error);
        } finally {
            eventBus.emit('loading:end');
        }
    }

    renderSearchResults(results) {
        // Clear existing features
        this.source.clear();

        if (!results || !results.items) {
            console.log('RoiLayer: No results to render');
            return;
        }

        // Create features for each matched region
        results.items.forEach(item => {
            const feature = new ol.Feature({
                geometry: new ol.geom.Point([0, 0]) // Placeholder - replace with actual coordinates
            });

            // Set feature properties
            feature.set('id', item.id);
            feature.set('biosample', item.biosample);
            feature.set('section', item.section);
            feature.set('imageUrl', item.imageUrl);
            feature.set('metadata', item.metadata);

            this.source.addFeature(feature);
        });

        console.log(`RoiLayer: Rendered ${this.source.getFeatures().length} search results`);
    }

    enableSelectionMode() {
        this.isSelecting = true;
        this.selectionSource.clear();
        console.log('RoiLayer: Selection mode enabled');
    }

    disableSelectionMode() {
        this.isSelecting = false;
        this.selectionSource.clear();
        console.log('RoiLayer: Selection mode disabled');
    }

    show() {
        if (this.layer) {
            this.layer.setVisible(true);
            this.selectionLayer.setVisible(true);
            this.isVisible = true;
        }
    }

    hide() {
        if (this.layer) {
            this.layer.setVisible(false);
            this.selectionLayer.setVisible(false);
            this.isVisible = false;
        }
    }

    setOpacity(opacity) {
        if (this.layer) {
            this.layer.setOpacity(opacity);
        }
    }

    clearResults() {
        this.source.clear();
        this.searchResults = [];
        console.log('RoiLayer: Results cleared');
    }

    async reload() {
        console.log('RoiLayer: Reloading...');
        roiService.clearCache();
    }

    bindEvents() {
        // Toggle visibility from Layers panel
        this.on('roi:toggle', (show) => {
            show ? this.show() : this.hide();
        });

        // Opacity changes from accordion
        this.on('roi:opacity', (opacity) => {
            this.setOpacity(opacity);
        });

        // Enable/disable selection mode
        this.on('roi:startSelection', () => {
            this.enableSelectionMode();
        });

        this.on('roi:cancelSelection', () => {
            this.disableSelectionMode();
        });

        // Handle data loading requests from accordion
        this.on('roi:loadBiosamples', async (projectId) => {
            try {
                const sections = await roiService.getSections(projectId);
                eventBus.emit('roi:biosamplesLoaded', sections);
            } catch (error) {
                console.error('RoiLayer: Failed to load biosamples:', error);
            }
        });

        // Perform search
        this.on('roi:search', (params) => {
            this.performSearch(params);
        });

        // Clear results
        this.on('roi:clearResults', () => {
            this.clearResults();
        });

        // Refresh
        this.on('roi:refresh', () => {
            this.reload();
        });

        // Handle task changes
        this.on('task:changed', async () => {
            console.log('RoiLayer: Task changed, reloading...');
            this.clearResults();
            await this.reload();
        });
    }

    unmount() {
        console.log('RoiLayer: Unmounting...');

        // Remove from Layers panel
        eventBus.emit('layers:remove', 'roi');

        // Hide controls accordion
        eventBus.emit('roiControls:hide');

        // Remove layers from map
        const map = stateManager.get('map');
        if (map) {
            if (this.layer) map.removeLayer(this.layer);
            if (this.selectionLayer) map.removeLayer(this.selectionLayer);
            if (this.drawInteraction) map.removeInteraction(this.drawInteraction);
        }

        this.layer = null;
        this.source = null;
        this.selectionLayer = null;
        this.selectionSource = null;
        this.drawInteraction = null;

        super.unmount();
    }
}

export default RoiLayer;