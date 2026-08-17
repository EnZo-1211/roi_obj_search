// RoiControlsAccordion.js - Settings panel accordion controls
// Location: plugins/roi-controls-accordion/RoiControlsAccordion.js

import { Plugin } from '../../core/Plugin.js';
import { stateManager } from '../../core/StateManager.js';
import { eventBus } from '../../core/EventBus.js';
import { RoiViewer } from '../roi-viewer/RoiViewer.js';
import { roiService } from '../roi-service/RoiService.js';


export class RoiControlsAccordion extends Plugin {
    constructor(app, options = {}) {
        super(app, options);
        this.isExpanded = true;
        this.currentOpacity = 0.7;
        this.isSelecting = false;
        this.selectedProject = null;
        this.selectedBiosample = null;
        this.selectedSection = null;
        this.selectedStain = null;
        this.searchResults = [];
        this.roiViewer = null;
        this.hoverThumbnail = null;
        this.processingProgress = 0;
        this.totalSections = 0;
        this.progressPollInterval = null;
        this.currentTaskId = null;
        this.currentHashValue = null;
        this.isProcessing = false;
        this.savedSearches = [];
        this.currentDescription = '';
        this.lastCompletedTasksCount = 0;
        this.completedTasksPollingInterval = null;
        this.extractUrlParams();
    }

    render() {
        const el = document.createElement('div');
        el.className = 'accordion-section';
        el.id = 'roiControlsAccordion';
        el.setAttribute('data-section', 'roi-controls');

        el.innerHTML = `
            <div class="accordion-header">
                <span class="accordion-title">ROI Object Search</span>
                <span class="accordion-chevron"></span>
            </div>
            <div class="accordion-content" style="max-height: 80vh; overflow-y: auto;">
                <div class="roi-accordion-content">
                    <!-- Layer Info Section (layers-like layout) -->
                    <div class="layer-info-section" style="background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 10px; margin-bottom: 12px;">
                        <div class="info-header" style="display: flex; align-items: center; gap: 6px; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border-color);">
                            <span style="font-size: 13px; font-weight: 600; color: var(--text-primary);">📍 Current Context</span>
                        </div>
                        
                        <div class="info-grid" style="display: grid; gap: 8px;">
                            <div class="info-row" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; background: var(--bg-secondary); border-radius: 4px;">
                                <span style="font-size: 13px; color: var(--text-muted); font-weight: 500;">Project ID:</span>
                                <span id="roiProjectId" style="font-size: 14px; color: var(--text-primary); font-weight: 600; font-family: monospace;">
                                    ${this.selectedProject || 'Not Available'}
                                </span>
                            </div>
                            
                            <div class="info-row" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; background: var(--bg-secondary); border-radius: 4px;">
                                <span style="font-size: 13px; color: var(--text-muted); font-weight: 500;">Biosample:</span>
                                <span id="roiBiosample" style="font-size: 14px; color: var(--text-primary); font-weight: 600; font-family: monospace;">
                                    ${this.selectedBiosample || 'Not Available'}
                                </span>
                            </div>
                            
                            <div class="info-row" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; background: var(--bg-secondary); border-radius: 4px;">
                                <span style="font-size: 13px; color: var(--text-muted); font-weight: 500;">Section:</span>
                                <span id="roiSection" style="font-size: 14px; color: var(--text-primary); font-weight: 600; font-family: monospace;">
                                    ${this.selectedSection || 'Not Available'}
                                </span>
                            </div>
                        </div>
                    </div>

                    <!-- Processing Progress Section -->
                    <div class="processing-section" style="background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 12px; margin-bottom: 16px;">
                        <div class="progress-header" style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">
                            <span style="font-size: 14px; font-weight: 600; color: var(--text-primary);">⚡ Processing Status</span>
                        </div>
                        
                        <div class="progress-container">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-size: 11px; color: var(--text-muted); font-weight: 500;" id="progressText">Ready to process</span>
                                <span style="font-size: 11px; color: var(--text-primary); font-weight: 600;" id="progressPercentage">0%</span>
                            </div>
                            <div style="width: 100%; height: 6px; background: var(--bg-secondary); border-radius: 3px; overflow: hidden; border: 1px solid var(--border-color);">
                                <div id="progressBar" style="height: 100%; width: 0%; background: linear-gradient(90deg, #3b82f6, #1d4ed8); border-radius: 2px; transition: width 0.5s ease, background 0.3s ease;"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Action Controls Section -->
                    <div class="action-controls-section" style="background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 12px; margin-bottom: 16px;">
                        <div class="controls-header" style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">
                            <span style="font-size: 14px; font-weight: 600; color: var(--text-primary);">🎯 ROI Controls</span>
                        </div>
                        
                        <!-- Description Input -->
                        <div class="description-section" style="margin-bottom: 8px;">
                            <input type="text" 
                                   id="roiDescription" 
                                   placeholder="Optional: Describe this search..." 
                                   maxlength="500"
                                   style="width: 100%; padding: 6px 8px; border: 1px solid var(--border-color);
                                          border-radius: 3px; font-size: 11px; background: white;">
                        </div>

                        <!-- Saved Searches Dropdown -->
                        <div class="saved-searches-section" style="margin-bottom: 8px;">
                            <select id="savedSearchesDropdown" 
                                    style="width: 100%; padding: 6px 8px; border: 1px solid var(--border-color); 
                                           border-radius: 3px; font-size: 11px; background: white;">
                                <option value="">Load a previous search...</option>
                            </select>
                        </div>
                        
                        <!-- Primary Action Buttons -->
                        <div class="primary-actions" style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 10px;">
                            <button id="roiSelectBtn" class="roi-action-btn roi-select-btn" style="
                                display: flex; align-items: center; justify-content: center; gap: 3px; 
                                padding: 6px 8px; border: 1px solid #3b82f6; border-radius: 3px; 
                                background: white; color: #3b82f6; font-weight: 500; font-size: 10px; 
                                cursor: pointer; transition: all 0.2s ease; min-height: 28px;
                            ">
                                <span style="font-size: 10px;">⊡</span>
                                <span id="roiSelectBtnText">Select</span>
                            </button>
                            
                            <button id="roiSearchBtn" class="roi-action-btn roi-search-btn" style="
                                display: flex; align-items: center; justify-content: center; gap: 3px; 
                                padding: 6px 8px; border: 1px solid #10b981; border-radius: 3px; 
                                background: #10b981; color: white; font-weight: 500; font-size: 10px; 
                                cursor: pointer; transition: all 0.2s ease; min-height: 28px;
                            ">
                                <span style="font-size: 10px;">🔍</span>
                                <span>Search</span>
                            </button>
                        </div>
                        
                        <!-- Secondary Action Buttons -->
                        <div class="secondary-actions" style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                            <button id="roiClearBtn" class="roi-action-btn roi-clear-btn" style="
                                display: flex; align-items: center; justify-content: center; gap: 6px; 
                                padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 4px; 
                                background: var(--bg-secondary); color: var(--text-primary); 
                                font-weight: 500; font-size: 12px; cursor: pointer; 
                                transition: all 0.2s ease;
                            ">
                                <span style="font-size: 14px;">🗑️</span>
                                <span>Clear</span>
                            </button>
                            <button id="roiRefreshBtn" class="roi-action-btn roi-refresh-btn" style="
                                display: flex; align-items: center; justify-content: center; gap: 6px; 
                                padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 4px; 
                                background: var(--bg-secondary); color: var(--text-primary); 
                                font-weight: 500; font-size: 12px; cursor: pointer; 
                                transition: all 0.2s ease;
                            ">
                                <span style="font-size: 14px;">🔄</span>
                                <span>Refresh</span>
                            </button>
                        </div>
                    </div>

                    <!-- Results Control Section -->
                    <div class="results-control-section" style="background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 12px;">
                        <div class="results-header" style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">
                            <span style="font-size: 14px; font-weight: 600; color: var(--text-primary);">🎨 Results Display</span>
                        </div>
                        
                        
                        <!-- Results Summary -->
                        <div class="results-summary" style="padding: 8px; background: var(--bg-secondary); border-radius: 4px; border: 1px solid var(--border-color); display: none;" id="roiResultsSummary">
                            <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-primary); margin-bottom: 6px; font-weight: 500;">
                                <span>📊</span>
                                <span>Search Results:</span>
                                <span id="roiResultsCount" style="background: var(--bg-primary); padding: 2px 6px; border-radius: 2px; font-weight: 600;">0</span>
                                <span style="color: var(--text-muted);">matches</span>
                            </div>
                            <div id="roiResultsList" style="margin-top: 8px;">
                                <!-- Results will be populated here -->
                            </div>
                        </div>
                        
                        <!-- Results Viewer Button -->
                        <div id="roiViewerButtonContainer" style="margin-top: 8px; display: none;">
                            <button id="roiViewerBtn" style="
                                width: 100%; padding: 10px 12px; border: 2px solid black; border-radius: 4px;
                                background: white; color: black; font-weight: 700; font-size: 12px; cursor: pointer;
                                display: flex; align-items: center; justify-content: center; gap: 8px;
                                transition: all 0.2s ease;
                            ">
                                <span style="font-size: 16px;">🖼️</span>
                                <span>Open Results Viewer</span>
                            </button>
                        </div>

                        <!-- Running Tasks Button - Always Visible -->
                        <div style="margin-top: 8px;">
                            <button id="runningTasksBtn" style="
                                width: 100%; padding: 10px 12px; border: 2px solid #3b82f6; border-radius: 4px;
                                background: #eff6ff; color: #3b82f6; font-weight: 700; font-size: 12px; cursor: pointer;
                                display: flex; align-items: center; justify-content: center; gap: 8px;
                                transition: all 0.2s ease;
                            ">
                                <span style="font-size: 16px;">⏳</span>
                                <span>Running Tasks</span>
                                <span id="runningTasksCount" style="
                                    background: #3b82f6; color: white; border-radius: 10px; 
                                    padding: 2px 6px; font-size: 10px; min-width: 16px; text-align: center;
                                    display: none;
                                ">0</span>
                            </button>
                        </div>
                        
                        <!-- Status Display -->
                        <div class="status-display" style="margin-top: 12px; padding: 6px 8px; background: var(--bg-secondary); border-radius: 4px; border-left: 3px solid #3b82f6;">
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <span style="font-size: 12px; color: var(--text-muted); font-weight: 500;">Status:</span>
                                <span id="roiStatus" style="font-size: 12px; color: var(--text-primary); font-weight: 500;">Ready</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        return el;
    }

    mount() {
        // Mount into dynamic accordions container
        const dynamicContainer = document.getElementById('dynamicAccordionsContainer');

        if (dynamicContainer) {
            this.element = this.render();
            dynamicContainer.appendChild(this.element);
            this.init();
            this.bindEvents();
            
            // Initialize ROI viewer
            this.roiViewer = new RoiViewer(this.app);
            this.roiViewer.mount();
            
            console.log('RoiControlsAccordion: Mounted');
        } else {
            console.warn('RoiControlsAccordion: Container not found');
        }
    }

    extractUrlParams() {
        // Extract parameters from URL pattern: /detection/viewer/[biosample]/[section id]/[stain]
        const urlPath = window.location.pathname;
        const urlMatch = urlPath.match(/\/detection\/viewer\/(\d+)\/(\d+)\/([^/]+)/);
        
        if (urlMatch) {
            this.selectedBiosample = urlMatch[1];
            this.selectedSection = urlMatch[2];
            this.selectedStain = urlMatch[3];
            console.log('RoiControlsAccordion: Extracted from URL - Biosample:', this.selectedBiosample, 'Section:', this.selectedSection, 'Stain:', this.selectedStain);
        }
        
        // Get project ID from session storage
        const projectId = sessionStorage.getItem('projectId');
        if (projectId) {
            this.selectedProject = projectId;
            console.log('RoiControlsAccordion: Project ID from session storage:', this.selectedProject);
        }
    }

    init() {
        // Hidden by default - shown when ROI layer is loaded
        if (this.element) {
            this.element.style.display = 'none';
        }

        // Set expanded state
        if (this.isExpanded) {
            this.element?.classList.add('expanded');
        }

        // Pre-populate fields if we have values from URL/session
        this.populateFields();

        // Check if we have all required parameters
        if (this.selectedProject && this.selectedBiosample && this.selectedSection) {
            this.setStatus('Ready');
            this.enableROISelection();
            // Load saved searches for the project
            this.loadSavedSearches();
            // Load running tasks count
            this.loadRunningTasksCount();
        } else {
            if (!this.selectedProject) {
                console.warn('RoiControlsAccordion: No project ID found in session storage');
                this.setStatus('No project ID found');
            } else if (!this.selectedBiosample || !this.selectedSection) {
                console.warn('RoiControlsAccordion: Missing biosample or section from URL');
                this.setStatus('Missing biosample or section');
            }
        }

        // Always load running tasks count (even without full project context)
        this.loadRunningTasksCount();
        
        // Start background polling for completed tasks (to auto-refresh dropdown)
        this.startCompletedTasksPolling();
    }

    populateFields() {
        // Update project ID display
        const projectIdDiv = this.$('#roiProjectId');
        if (projectIdDiv && this.selectedProject) {
            projectIdDiv.textContent = this.selectedProject;
        }
        
        // Update biosample display
        const biosampleDiv = this.$('#roiBiosample');
        if (biosampleDiv && this.selectedBiosample) {
            biosampleDiv.textContent = this.selectedBiosample;
        }
        
        // Update section display
        const sectionDiv = this.$('#roiSection');
        if (sectionDiv && this.selectedSection) {
            sectionDiv.textContent = this.selectedSection;
        }
    }

    show() {
        if (this.element) {
            this.element.style.display = 'block';
            console.log('RoiControlsAccordion: Shown');
        }
    }

    hide() {
        if (this.element) {
            this.element.style.display = 'none';
            console.log('RoiControlsAccordion: Hidden');
        }
    }

    setStatus(message) {
        const statusEl = this.$('#roiStatus');
        if (statusEl) {
            statusEl.textContent = message;
        }
    }

    toggleSection() {
        this.isExpanded = !this.isExpanded;
        this.element?.classList.toggle('expanded', this.isExpanded);
    }

    addButtonHoverEffects() {
        // Add hover effects for primary action buttons
        const selectBtn = this.$('#roiSelectBtn');
        const searchBtn = this.$('#roiSearchBtn');
        const clearBtn = this.$('#roiClearBtn');
        const refreshBtn = this.$('#roiRefreshBtn');

        // Select button hover
        if (selectBtn) {
            selectBtn.addEventListener('mouseenter', () => {
                if (!this.isSelecting) {
                    selectBtn.style.opacity = '0.9';
                    selectBtn.style.transform = 'scale(1.02)';
                }
            });
            selectBtn.addEventListener('mouseleave', () => {
                if (!this.isSelecting) {
                    selectBtn.style.opacity = '1';
                    selectBtn.style.transform = 'scale(1)';
                }
            });
        }

        // Search button hover
        if (searchBtn) {
            searchBtn.addEventListener('mouseenter', () => {
                searchBtn.style.opacity = '0.9';
                searchBtn.style.transform = 'scale(1.02)';
            });
            searchBtn.addEventListener('mouseleave', () => {
                searchBtn.style.opacity = '1';
                searchBtn.style.transform = 'scale(1)';
            });
        }

        // Clear button hover
        if (clearBtn) {
            clearBtn.addEventListener('mouseenter', () => {
                clearBtn.style.background = 'var(--bg-tertiary)';
                clearBtn.style.borderColor = '#ef4444';
                clearBtn.style.color = '#ef4444';
            });
            clearBtn.addEventListener('mouseleave', () => {
                clearBtn.style.background = 'var(--bg-secondary)';
                clearBtn.style.borderColor = 'var(--border-color)';
                clearBtn.style.color = 'var(--text-primary)';
            });
        }

        // Refresh button hover
        if (refreshBtn) {
            refreshBtn.addEventListener('mouseenter', () => {
                refreshBtn.style.background = 'var(--bg-tertiary)';
                refreshBtn.style.borderColor = '#3b82f6';
                refreshBtn.style.color = '#3b82f6';
            });
            refreshBtn.addEventListener('mouseleave', () => {
                refreshBtn.style.background = 'var(--bg-secondary)';
                refreshBtn.style.borderColor = 'var(--border-color)';
                refreshBtn.style.color = 'var(--text-primary)';
            });
        }
    }

    bindEvents() {
        // Add hover effects for buttons
        this.addButtonHoverEffects();
        
        // Accordion header toggle
        this.$('.accordion-header')?.addEventListener('click', () => {
            this.toggleSection();
        });

        // No longer need biosample selection or section input handlers since they're read-only

        // Description input
        const descriptionInput = this.$('#roiDescription');
        if (descriptionInput) {
            descriptionInput.addEventListener('input', (e) => {
                this.currentDescription = e.target.value;
            });
        }

        // Saved searches dropdown
        const savedSearchesDropdown = this.$('#savedSearchesDropdown');
        if (savedSearchesDropdown) {
            savedSearchesDropdown.addEventListener('change', (e) => {
                this.handleSavedSearchSelection(e.target.value);
            });
        }

        // ROI selection button
        this.$('#roiSelectBtn')?.addEventListener('click', () => {
            this.toggleSelectionMode();
        });

        // Search button - emit event for layer to handle
        this.$('#roiSearchBtn')?.addEventListener('click', async () => {
            if (this.selectedProject && this.selectedBiosample && this.selectedSection) {
                this.setStatus('Initializing search...');
                this.resetProgress();
                
                try {
                    // Start the search and get task ID for progress tracking
                    const searchParams = {
                        projectId: this.selectedProject,
                        biosample: this.selectedBiosample,
                        section: this.selectedSection,
                        stain: this.selectedStain || 'NISL',
                        description: this.currentDescription || null
                    };
                    
                    // Set up progress monitoring before search starts
                    this.resetProgress();
                    
                    // Listen for the search response to get the task ID
                    const searchPromise = new Promise((resolve, reject) => {
                        const handleAsyncTask = (taskInfo) => {
                            console.log('Got async task info:', taskInfo);
                            eventBus.off('roi:asyncTaskStarted', handleAsyncTask);
                            eventBus.off('roi:searchCompleted', handleSync);
                            eventBus.off('roi:searchFailed', handleError);
                            
                            // Progress polling will be handled by the async task event listener
                            // Don't start duplicate polling here
                            resolve(taskInfo);
                        };
                        
                        const handleSync = (results) => {
                            eventBus.off('roi:asyncTaskStarted', handleAsyncTask);
                            eventBus.off('roi:searchCompleted', handleSync);
                            eventBus.off('roi:searchFailed', handleError);
                            resolve(results);
                        };
                        
                        const handleError = (error) => {
                            eventBus.off('roi:asyncTaskStarted', handleAsyncTask);
                            eventBus.off('roi:searchCompleted', handleSync);
                            eventBus.off('roi:searchFailed', handleError);
                            reject(error);
                        };
                        
                        eventBus.once('roi:asyncTaskStarted', handleAsyncTask);
                        eventBus.once('roi:searchCompleted', handleSync);
                        eventBus.once('roi:searchFailed', handleError);
                    });
                    
                    // Emit search event
                    eventBus.emit('roi:search', searchParams);
                    
                    // Wait for response
                    await searchPromise;
                    
                } catch (error) {
                    console.error('Search initiation failed:', error);
                    this.setStatus('Search failed to start');
                    this.resetProgress();
                }
            }
        });

        // Opacity slider
        this.$('#roiOpacitySlider')?.addEventListener('input', (e) => {
            const opacity = parseInt(e.target.value) / 100;
            this.currentOpacity = opacity;
            this.$('#roiOpacityValue').textContent = `${e.target.value}%`;
            eventBus.emit('roi:opacity', opacity);
        });

        // Clear button
        this.$('#roiClearBtn')?.addEventListener('click', () => {
            this.clearResults();
        });

        // Refresh button
        this.$('#roiRefreshBtn')?.addEventListener('click', () => {
            this.setStatus('Refreshing...');
            eventBus.emit('roi:refresh');
            // Re-extract URL parameters
            this.extractUrlParams();
            this.populateFields();
            if (this.selectedProject && this.selectedBiosample && this.selectedSection) {
                this.enableROISelection();
                this.setStatus('Ready');
                // Load saved searches when project info is available
                this.loadSavedSearches();
            }
        });

        // Running Tasks button
        this.$('#runningTasksBtn')?.addEventListener('click', () => {
            this.showRunningTasks();
        });

        // No longer need to listen for biosamples loaded since we're using URL params

        // Listen for ROI selection
        this.on('roi:selected', () => {
            this.isSelecting = false;
            const selectBtn = this.$('#roiSelectBtn');
            const selectBtnText = this.$('#roiSelectBtnText');
            selectBtn?.classList.remove('active');
            if (selectBtnText) selectBtnText.textContent = 'Select Area';
            this.setStatus('ROI selected');
        });

        // Listen for async task start
        this.on('roi:asyncTaskStarted', (taskInfo) => {
            this.setStatus(`Processing ${taskInfo.section_count} sections... ${taskInfo.estimated_time}`);
            
            // Store hash value for later use when task completes
            this.currentHashValue = taskInfo.hash_value;
            console.log('Stored hash value from async task:', this.currentHashValue);
            
            // Start progress polling with the actual task ID from backend
            if (taskInfo.task_id) {
                console.log('Starting progress polling for backend task ID:', taskInfo.task_id);
                this.startProgressPolling(taskInfo.task_id, taskInfo.section_count || 10);
            }
        });

        // Listen for search results
        this.on('roi:searchCompleted', (results) => {
            this.displayResults(results);
            const mode = results.processing_mode === 'sync' ? 'Sync' : 'Async';
            const resultCount = results.items ? results.items.length : 0;
            this.setStatus(`${mode}: Found ${resultCount} matches`);
            
            // For sync mode, complete immediately
            // For async mode, let polling handle completion
            if (results.processing_mode === 'sync') {
                this.stopProgressPolling();
                this.updateProgress(resultCount, resultCount, `Found ${resultCount} sections`);
            }
            // For async mode, don't update progress here - let polling handle it completely
            
            // Instead of external viewer link, add embedded viewer button
            this.addEmbeddedViewerButton(results);

            // Reload saved searches dropdown to include the newly completed search
            this.loadSavedSearches();
        });

        this.on('roi:searchFailed', () => {
            this.setStatus('Search failed');
            this.stopProgressPolling();
            this.resetProgress();
        });

        // Show/hide when layer is loaded/unloaded
        this.on('roiControls:show', () => this.show());
        this.on('roiControls:hide', () => this.hide());
    }

    enableROISelection() {
        // Buttons are no longer disabled by default, so this just logs
        console.log('RoiControlsAccordion: ROI selection enabled');
    }

    toggleSelectionMode() {
        this.isSelecting = !this.isSelecting;
        
        const selectBtn = this.$('#roiSelectBtn');
        const selectBtnText = this.$('#roiSelectBtnText');
        
        if (this.isSelecting) {
            selectBtn?.classList.add('active');
            if (selectBtnText) selectBtnText.textContent = 'Cancel';
            selectBtn?.style.setProperty('background', 'white');
            selectBtn?.style.setProperty('border-color', '#dc2626');
            selectBtn?.style.setProperty('color', '#dc2626');
            eventBus.emit('roi:startSelection');
            this.setStatus('Click and drag to select ROI');
        } else {
            selectBtn?.classList.remove('active');
            if (selectBtnText) selectBtnText.textContent = 'Select Area';
            selectBtn?.style.setProperty('background', 'white');
            selectBtn?.style.setProperty('border-color', '#3b82f6');
            selectBtn?.style.setProperty('color', '#3b82f6');
            eventBus.emit('roi:cancelSelection');
            this.setStatus('Ready');
        }
    }

    displayResults(results) {
        const summaryDiv = this.$('#roiResultsSummary');
        const countSpan = this.$('#roiResultsCount');
        const listDiv = this.$('#roiResultsList');
        
        if (!results || !results.items) {
            if (summaryDiv) summaryDiv.style.display = 'none';
            return;
        }
        
        if (summaryDiv) summaryDiv.style.display = 'block';
        if (countSpan) countSpan.textContent = results.items.length;
        
        // EMBEDDED_VIEWER_START - Changes for embedded results viewer
        if (listDiv) {
            listDiv.innerHTML = '';
            
            // Create view toggle button
            // Create container for detailed view only
            const viewContainer = document.createElement('div');
            viewContainer.id = 'roiViewContainer';
            listDiv.appendChild(viewContainer);
            
            // Always show detailed view
            this.showDetailedView(viewContainer, results);
        }
        // EMBEDDED_VIEWER_END
        
        this.searchResults = results.items;
    }

    // EMBEDDED_VIEWER_START - New methods for embedded viewer
    
    showDetailedView(container, results) {
        container.innerHTML = '';
        container.style.cssText = 'max-height: 400px; overflow-y: auto;';
        
        // Create tree structure from results
        const tree = this.buildResultsTree(results);
        
        // Create expandable tree view
        const treeView = document.createElement('div');
        treeView.style.cssText = 'font-size: 11px;';
        
        Object.entries(tree).forEach(([biosample, stains]) => {
            const biosampleDiv = document.createElement('div');
            biosampleDiv.style.cssText = 'margin-bottom: 8px; border: 1px solid var(--border-color); border-radius: 4px; padding: 4px;';
            
            // Biosample header
            const biosampleHeader = document.createElement('div');
            biosampleHeader.style.cssText = 'cursor: pointer; padding: 4px; background: var(--bg-secondary); border-radius: 2px;';
            biosampleHeader.innerHTML = `
                <span class="expand-icon">▶</span>
                <strong>Biosample ${biosample}</strong>
                <span style="color: var(--text-muted); margin-left: 8px;">
                    ${Object.keys(stains).length} stain(s)
                </span>
            `;
            biosampleDiv.appendChild(biosampleHeader);
            
            // Stains container
            const stainsContainer = document.createElement('div');
            stainsContainer.style.cssText = 'display: none; padding-left: 12px; margin-top: 4px;';
            
            Object.entries(stains).forEach(([stain, sections]) => {
                const stainDiv = document.createElement('div');
                stainDiv.style.cssText = 'margin: 4px 0; padding: 4px; background: var(--bg-primary); border-radius: 2px;';
                
                const stainHeader = document.createElement('div');
                stainHeader.style.cssText = 'cursor: pointer; padding: 2px;';
                stainHeader.innerHTML = `
                    <span class="stain-expand-icon">▶</span>
                    ${stain} Stain
                    <span style="color: var(--text-muted); margin-left: 8px;">
                        ${sections.length} section(s)
                    </span>
                `;
                stainDiv.appendChild(stainHeader);
                
                // Sections container
                const sectionsContainer = document.createElement('div');
                sectionsContainer.style.cssText = 'display: none; padding-left: 12px; margin-top: 4px;';
                
                // Create grid of section buttons
                const sectionsGrid = document.createElement('div');
                sectionsGrid.style.cssText = 'display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; margin-top: 4px;';
                
                sections.forEach(section => {
                    const sectionBtn = document.createElement('button');
                    sectionBtn.className = 'btn btn-secondary';
                    sectionBtn.style.cssText = 'font-size: 10px; padding: 6px 8px; position: relative; min-height: 28px;';
                    sectionBtn.textContent = `Section ${section.section}`;
                    sectionBtn.title = `Section ${section.section}`;
                    
                    // Click handler
                    sectionBtn.addEventListener('click', () => {
                        this.showSectionDetails(section);
                        eventBus.emit('roi:focusResult', section);
                    });
                    
                    // Hover thumbnail preview
                    let hoverTimeout;
                    
                    sectionBtn.addEventListener('mouseenter', (e) => {
                        // Show thumbnail after short delay
                        hoverTimeout = setTimeout(() => {
                            console.log('Hovering over section:', section);
                            this.showHoverThumbnail(e.target, section);
                        }, 300);
                    });
                    
                    sectionBtn.addEventListener('mouseleave', () => {
                        // Cancel thumbnail show
                        clearTimeout(hoverTimeout);
                        
                        // Hide thumbnail
                        this.hideHoverThumbnail();
                    });
                    
                    sectionsGrid.appendChild(sectionBtn);
                });
                
                sectionsContainer.appendChild(sectionsGrid);
                stainDiv.appendChild(sectionsContainer);
                
                // Toggle sections visibility
                stainHeader.addEventListener('click', () => {
                    const icon = stainHeader.querySelector('.stain-expand-icon');
                    if (sectionsContainer.style.display === 'none') {
                        sectionsContainer.style.display = 'block';
                        icon.textContent = '▼';
                    } else {
                        sectionsContainer.style.display = 'none';
                        icon.textContent = '▶';
                    }
                });
                
                stainsContainer.appendChild(stainDiv);
            });
            
            biosampleDiv.appendChild(stainsContainer);
            
            // Toggle stains visibility
            biosampleHeader.addEventListener('click', () => {
                const icon = biosampleHeader.querySelector('.expand-icon');
                if (stainsContainer.style.display === 'none') {
                    stainsContainer.style.display = 'block';
                    icon.textContent = '▼';
                } else {
                    stainsContainer.style.display = 'none';
                    icon.textContent = '▶';
                }
            });
            
            treeView.appendChild(biosampleDiv);
        });
        
        container.appendChild(treeView);
        
        // Add selected section viewer
        const sectionViewer = document.createElement('div');
        sectionViewer.id = 'roiSectionViewer';
        sectionViewer.style.cssText = 'margin-top: 8px; padding: 8px; background: var(--bg-secondary); border-radius: 4px; display: none;';
        container.appendChild(sectionViewer);
    }
    
    buildResultsTree(results) {
        const tree = {};
        
        if (results.items) {
            results.items.forEach(item => {
                if (!tree[item.biosample]) {
                    tree[item.biosample] = {};
                }
                const stain = item.stain || item.metadata?.stain || 'NISL';
                if (!tree[item.biosample][stain]) {
                    tree[item.biosample][stain] = [];
                }
                tree[item.biosample][stain].push(item);
            });
        }
        
        return tree;
    }
    
    showHoverThumbnail(button, section) {
        // Remove any existing thumbnail
        this.hideHoverThumbnail();
        
        // Check for image URL in multiple possible properties
        const imageUrl = section.image_url || section.imageUrl || section.url || section.preview_url;
        
        // Only show if section has image URL
        if (!imageUrl) {
            console.log('No image URL found for section:', section);
            return;
        }
        
        // Create thumbnail container
        this.hoverThumbnail = document.createElement('div');
        this.hoverThumbnail.style.cssText = `
            position: fixed;
            width: 180px;
            height: 130px;
            background: white;
            border: 2px solid #3b82f6;
            border-radius: 6px;
            box-shadow: 0 8px 20px -5px rgba(0, 0, 0, 0.3);
            z-index: 10001;
            padding: 6px;
            display: flex;
            flex-direction: column;
            pointer-events: none;
        `;
        
        // Add loading state
        this.hoverThumbnail.innerHTML = `
            <div style="
                flex: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #f3f4f6;
                border-radius: 4px;
                margin-bottom: 6px;
                color: #6b7280;
                font-size: 11px;
            ">
                Loading preview...
            </div>
            <div style="
                font-size: 10px;
                color: #374151;
                font-weight: 500;
                text-align: center;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            ">
                Section ${section.section}
            </div>
        `;
        
        // Position relative to button using fixed positioning
        document.body.appendChild(this.hoverThumbnail);
        
        // Calculate position relative to button
        const buttonRect = button.getBoundingClientRect();
        this.hoverThumbnail.style.top = `${buttonRect.top + (buttonRect.height / 2) - 65}px`;
        this.hoverThumbnail.style.left = `${buttonRect.right + 10}px`;
        
        // Load the image
        const img = document.createElement('img');
        img.style.cssText = `
            width: 100%;
            height: 100%;
            object-fit: contain;
            border-radius: 4px;
        `;
        
        img.onload = () => {
            const imageContainer = this.hoverThumbnail?.querySelector('div');
            if (imageContainer) {
                imageContainer.innerHTML = '';
                imageContainer.appendChild(img);
            }
        };
        
        img.onerror = () => {
            const imageContainer = this.hoverThumbnail?.querySelector('div');
            if (imageContainer) {
                imageContainer.innerHTML = `
                    <div style="text-align: center;">
                        <div style="font-size: 14px; margin-bottom: 3px;">⚠️</div>
                        <div style="font-size: 9px;">Preview unavailable</div>
                    </div>
                `;
            }
        };
        
        img.src = imageUrl;
        img.alt = `Section ${section.section} preview`;
        
        // Adjust position if thumbnail would go off-screen
        setTimeout(() => {
            if (this.hoverThumbnail) {
                const rect = this.hoverThumbnail.getBoundingClientRect();
                const viewport = {
                    width: window.innerWidth,
                    height: window.innerHeight
                };
                
                // If thumbnail goes off right edge, show on left side
                if (rect.right > viewport.width - 20) {
                    this.hoverThumbnail.style.left = `${buttonRect.left - 190}px`;
                }
                
                // If thumbnail goes off top, adjust to stay within viewport
                if (rect.top < 20) {
                    this.hoverThumbnail.style.top = '20px';
                } else if (rect.bottom > viewport.height - 20) {
                    this.hoverThumbnail.style.top = `${viewport.height - 150}px`;
                }
            }
        }, 10);
    }
    
    hideHoverThumbnail() {
        if (this.hoverThumbnail) {
            this.hoverThumbnail.remove();
            this.hoverThumbnail = null;
        }
    }

    updateProgress(current, total, statusText = '') {
        this.processingProgress = current;
        this.totalSections = total;
        
        const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
        
        console.log(`[UpdateProgress] ${current}/${total} = ${percentage}% - "${statusText}"`);
        
        const progressBar = this.$('#progressBar');
        const progressText = this.$('#progressText');
        const progressPercentage = this.$('#progressPercentage');
        
        console.log('Progress elements found:', {
            progressBar: !!progressBar,
            progressText: !!progressText, 
            progressPercentage: !!progressPercentage
        });
        
        if (progressBar) {
            console.log(`Setting progress bar width to ${percentage}%`);
            progressBar.style.width = `${percentage}%`;
            
            // Change color based on completion
            if (percentage === 100) {
                progressBar.style.background = 'linear-gradient(90deg, #10b981, #059669)'; // Green
            } else if (percentage > 0) {
                progressBar.style.background = 'linear-gradient(90deg, #3b82f6, #1d4ed8)'; // Blue
            }
        } else {
            console.error('Progress bar element not found!');
        }
        
        if (progressText) {
            progressText.textContent = statusText || `Processing ${current} of ${total} sections`;
        } else {
            console.error('Progress text element not found!');
        }
        
        if (progressPercentage) {
            progressPercentage.textContent = `${percentage}%`;
        } else {
            console.error('Progress percentage element not found!');
        }
    }

    resetProgress() {
        this.updateProgress(0, 0, 'Ready to process');
    }

    startProcessing(totalSections, statusText = 'Starting processing...') {
        this.totalSections = totalSections;
        this.updateProgress(0, totalSections, statusText);
    }

    incrementProgress(statusText = '') {
        if (this.processingProgress < this.totalSections) {
            this.processingProgress++;
            this.updateProgress(this.processingProgress, this.totalSections, statusText);
        }
    }

    completeProcessing(statusText = 'Processing complete') {
        this.updateProgress(this.totalSections, this.totalSections, statusText);
        this.stopProgressPolling();
    }

    async startProgressPolling(taskId, totalSections) {
        console.log(`Starting progress polling for task: ${taskId}`);
        
        // Clear any existing polling first
        if (this.progressPollInterval) {
            clearInterval(this.progressPollInterval);
            this.progressPollInterval = null;
        }
        
        // Set task state after clearing
        this.currentTaskId = taskId;
        this.totalSections = totalSections;
        this.isProcessing = true;
        this.progressErrorCount = 0; // Reset error count
        
        console.log(`[DEBUG] Set state - taskId: ${this.currentTaskId}, isProcessing: ${this.isProcessing}`);
        
        // Start polling every 1 second for faster updates
        this.progressPollInterval = setInterval(async () => {
            await this.checkProgress();
        }, 1000);
        
        // Initial check
        await this.checkProgress();
    }

    async checkProgress() {
        console.log(`[DEBUG] checkProgress called - taskId: ${this.currentTaskId}, isProcessing: ${this.isProcessing}`);
        if (!this.currentTaskId || !this.isProcessing) {
            console.log(`[DEBUG] Progress check skipped - taskId: ${this.currentTaskId}, isProcessing: ${this.isProcessing}`);
            return;
        }

        console.log(`[POLLING] Checking progress for task: ${this.currentTaskId}`);
        try {
            // Use the /task-status/{taskId} endpoint 
            const response = await fetch(`http://172.20.23.236:21000/task-status/${this.currentTaskId}`);
            
            if (!response.ok) {
                console.warn(`[POLLING] Progress check failed: ${response.status}`);
                // Don't stop polling on 404 - task might not be ready yet
                return;
            }
            
            const progressData = await response.json();
            console.log('[POLLING] Progress data received:', progressData);
            console.log('[POLLING] Task state:', progressData.state, 'Current/Total:', progressData.current, '/', progressData.total);
            
            if (progressData) {
                // Extract progress information from new response format
                const biosampleProgress = progressData.current || 0;
                const biosampleTotal = progressData.total || 1;
                const currentBiosample = progressData.current_biosample || 1;
                const totalBiosamples = progressData.total_biosamples || 1;
                const statusText = progressData.status || `Processing ${biosampleProgress}/${biosampleTotal}`;
                
                // Only consider complete when backend explicitly says SUCCESS
                const isComplete = progressData.state === 'SUCCESS';
                const hasError = progressData.state === 'FAILURE' || progressData.error;
                
                console.log(`Biosample Progress: ${biosampleProgress}/${biosampleTotal} (${Math.round((biosampleProgress/biosampleTotal)*100)}%)`);
                console.log(`Overall Progress: Biosample ${currentBiosample}/${totalBiosamples}`);
                console.log('Status:', statusText);
                console.log('Complete:', isComplete, 'Error:', hasError);
                
                if (hasError) {
                    this.setStatus(`Error: ${progressData.error || 'Processing failed'}`);
                    this.stopProgressPolling();
                    this.resetProgress();
                    return;
                }
                
                // Update progress bar with per-biosample progress
                this.updateProgress(biosampleProgress, biosampleTotal, statusText);
                
                // Check if completed
                if (isComplete) {
                    this.isProcessing = false;
                    
                    // Store task values before they might get cleared
                    const completedTaskId = this.currentTaskId;
                    const completedHashValue = this.currentHashValue;
                    
                    // First check task completion while we still have task values
                    setTimeout(() => {
                        // The task should be completed, check for final results
                        this.checkTaskCompletion(completedTaskId, completedHashValue);
                        // Then complete processing (which clears task values)
                        this.completeProcessing('Processing complete');
                    }, 1000);
                }
            }
        } catch (error) {
            console.error('Progress check failed:', error);
            // Only stop polling on persistent errors
            this.progressErrorCount = (this.progressErrorCount || 0) + 1;
            if (this.progressErrorCount > 5) {
                this.stopProgressPolling();
                this.setStatus('Progress tracking failed - too many errors');
            }
        }
    }

    stopProgressPolling() {
        if (this.progressPollInterval) {
            clearInterval(this.progressPollInterval);
            this.progressPollInterval = null;
        }
        this.currentTaskId = null;
        this.currentHashValue = null;
        this.isProcessing = false;
        this.progressErrorCount = 0;
    }

    async checkTaskCompletion(taskId = null, hashValue = null) {
        // Use provided values or fall back to instance values
        const effectiveTaskId = taskId || this.currentTaskId;
        const effectiveHashValue = hashValue || this.currentHashValue;
        
        console.log('🔍 checkTaskCompletion called - effectiveTaskId:', effectiveTaskId, 'effectiveHashValue:', effectiveHashValue);
        if (!effectiveTaskId || !effectiveHashValue) {
            console.error('❌ Missing taskId or hashValue for completion');
            return;
        }

        try {
            // Use the ROI service to get results using the stored hash value
            console.log('🎉 Task completed, fetching results using hash:', effectiveHashValue);
            
            // Get results directly using project_id and stored hash_value
            const results = await roiService.getSearchResults(
                this.selectedProject, 
                effectiveHashValue
            );
            
            console.log('📊 Results fetched:', results);
            
            // Mark task as completed in history
            try {
                console.log('🏁 About to mark task complete - effectiveTaskId:', effectiveTaskId, 'total_sections:', results.total_sections || 0);
                const completeResponse = await fetch(`http://172.20.23.236:21000/task-history/${effectiveTaskId}/complete?processed_sections=${results.total_sections || 0}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                if (completeResponse.ok) {
                    console.log('✅ Task marked as completed in history');
                } else {
                    console.warn('⚠️ Failed to mark task as completed in history:', completeResponse.statusText);
                }
            } catch (error) {
                console.warn('⚠️ Error marking task as completed:', error);
            }

            // Emit search completed event
            eventBus.emit('roi:searchCompleted', {
                ...results,
                processing_mode: 'async',
                task_id: effectiveTaskId,
                hash_value: effectiveHashValue
            });
            
        } catch (error) {
            console.error('Failed to check task completion:', error);
            eventBus.emit('roi:searchFailed', error);
        }
    }

    async loadSavedSearches() {
        try {
            // Direct API call instead of using RoiService to avoid import issues
            const params = new URLSearchParams();
            if (this.selectedProject) {
                params.append('project_id', this.selectedProject);
            }
            params.append('limit', 50);

            const response = await fetch(`http://172.20.23.236:21000/completed-searches?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch completed searches: ${response.statusText}`);
            }

            const data = await response.json();
            this.savedSearches = data.searches || [];
            this.populateSavedSearchesDropdown();
            console.log('✅ Saved searches loaded:', this.savedSearches.length);
        } catch (error) {
            console.error('Failed to load saved searches:', error);
        }
    }

    populateSavedSearchesDropdown() {
        const dropdown = this.$('#savedSearchesDropdown');
        if (!dropdown) return;

        // Clear existing options except the first one
        dropdown.innerHTML = '<option value="">Load a previous search...</option>';

        this.savedSearches.forEach(search => {
            const option = document.createElement('option');
            option.value = JSON.stringify({
                hash_value: search.hash_value,
                project_id: search.project_id
            });
            option.textContent = `${search.description} (${new Date(search.timestamp).toLocaleDateString()})`;
            dropdown.appendChild(option);
        });
    }

    handleSavedSearchSelection(selectedValue) {
        if (!selectedValue) return;

        try {
            const searchData = JSON.parse(selectedValue);
            
            // Show the ROI viewer with the selected search results
            this.showRoiViewer(searchData.project_id, searchData.hash_value);
            
        } catch (error) {
            console.error('Error handling saved search selection:', error);
        }
    }

    showRoiViewer(projectId, hashValue) {
        // Hide the controls accordion
        const controlsContainer = this.$('#roi-controls-content');
        if (controlsContainer) {
            controlsContainer.style.display = 'none';
        }

        // Show the ROI viewer using existing showResults method
        if (this.roiViewer) {
            // Use the existing showResults method which can fetch data by project_id and hash_value
            this.roiViewer.showResults({
                project_id: projectId,
                hash_value: hashValue
            });
            
            // Update status
            this.updateStatus('Viewing saved search results');
        }
    }

    async showRunningTasks() {
        try {
            // Fetch active tasks from API
            const projectId = sessionStorage.getItem('projectId');
            const response = await fetch(`http://172.20.23.236:21000/active-tasks${projectId ? `?project_id=${projectId}` : ''}`);
            const data = await response.json();
            
            this.createActiveTasksModal(data.active_tasks || []);
            
        } catch (error) {
            console.error('Error fetching active tasks:', error);
            this.showError('Failed to load running tasks');
        }
    }

    createActiveTasksModal(activeTasks) {
        // Remove existing modal if present
        const existingModal = document.getElementById('activeTasksModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal
        const modal = document.createElement('div');
        modal.id = 'activeTasksModal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        modal.innerHTML = `
            <div style="
                background: white;
                border-radius: 12px;
                padding: 24px;
                width: 90%;
                max-width: 600px;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 25px 50px rgba(0,0,0,0.25);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #1f2937; font-size: 18px; font-weight: 600;">
                        ⏳ Running Tasks
                    </h3>
                    <button id="closeActiveTasksModal" style="
                        background: none;
                        border: none;
                        font-size: 18px;
                        cursor: pointer;
                        color: #6b7280;
                        padding: 4px;
                    ">✕</button>
                </div>
                
                <div id="activeTasksList">
                    ${this.renderActiveTasks(activeTasks)}
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Add event listeners
        modal.querySelector('#closeActiveTasksModal').addEventListener('click', () => {
            this.closeActiveTasksModal();
        });

        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeActiveTasksModal();
            }
        });

        // Start polling for updates
        this.startActiveTasksPolling();
    }

    renderActiveTasks(activeTasks) {
        if (activeTasks.length === 0) {
            return `
                <div style="text-align: center; padding: 40px 20px; color: #6b7280;">
                    <div style="font-size: 48px; margin-bottom: 16px;">😴</div>
                    <div style="font-size: 16px; font-weight: 500; margin-bottom: 8px;">No Running Tasks</div>
                    <div style="font-size: 14px;">All tasks have been completed.</div>
                </div>
            `;
        }

        return activeTasks.map(task => `
            <div class="active-task-item" data-task-id="${task.task_id}" style="
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
                background: #f9fafb;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                    <div>
                        <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">
                            ${task.description}
                        </div>
                        <div style="font-size: 12px; color: #6b7280;">
                            Biosample ${task.biosample} • Section ${task.section} • ${task.stain}
                        </div>
                    </div>
                    <div style="font-size: 11px; color: #6b7280;">
                        ${new Date(task.timestamp).toLocaleTimeString()}
                    </div>
                </div>

                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <span style="font-size: 12px; color: #374151; font-weight: 500;">
                            ${task.progress?.status_message || 'Processing...'}
                        </span>
                        <span style="font-size: 12px; color: #6b7280;">
                            ${task.progress?.current || 0}/${task.progress?.total || 1} sections
                        </span>
                    </div>
                    
                    <div style="background: #e5e7eb; border-radius: 4px; height: 6px; overflow: hidden;">
                        <div style="
                            background: linear-gradient(90deg, #3b82f6, #1d4ed8);
                            height: 100%;
                            width: ${task.progress?.progress_percent || 0}%;
                            transition: width 0.3s ease;
                        "></div>
                    </div>
                </div>

                <div style="font-size: 11px; color: #9ca3af;">
                    Task ID: ${task.task_id.substring(0, 8)}...
                </div>
            </div>
        `).join('');
    }

    closeActiveTasksModal() {
        const modal = document.getElementById('activeTasksModal');
        if (modal) {
            modal.remove();
        }
        // Stop polling when modal is closed
        if (this.activeTasksPollingInterval) {
            clearInterval(this.activeTasksPollingInterval);
            this.activeTasksPollingInterval = null;
        }
    }

    startActiveTasksPolling() {
        // Clear any existing polling
        if (this.activeTasksPollingInterval) {
            clearInterval(this.activeTasksPollingInterval);
        }

        // Poll every 2 seconds for updates
        this.activeTasksPollingInterval = setInterval(async () => {
            try {
                const modal = document.getElementById('activeTasksModal');
                if (!modal) {
                    // Modal was closed, stop polling
                    clearInterval(this.activeTasksPollingInterval);
                    this.activeTasksPollingInterval = null;
                    return;
                }

                const projectId = sessionStorage.getItem('projectId');
                const response = await fetch(`http://172.20.23.236:21000/active-tasks${projectId ? `?project_id=${projectId}` : ''}`);
                const data = await response.json();
                
                // Update the tasks list
                const tasksList = modal.querySelector('#activeTasksList');
                if (tasksList) {
                    tasksList.innerHTML = this.renderActiveTasks(data.active_tasks || []);
                }

                // Update running tasks count in the button
                this.updateRunningTasksCount(data.active_tasks?.length || 0);

            } catch (error) {
                console.error('Error polling active tasks:', error);
            }
        }, 2000);
    }

    updateRunningTasksCount(count) {
        const countElement = this.$('#runningTasksCount');
        if (countElement) {
            if (count > 0) {
                countElement.textContent = count;
                countElement.style.display = 'inline-block';
            } else {
                countElement.style.display = 'none';
            }
        }
    }

    async loadRunningTasksCount() {
        try {
            const projectId = sessionStorage.getItem('projectId');
            const response = await fetch(`http://172.20.23.236:21000/active-tasks${projectId ? `?project_id=${projectId}` : ''}`);
            const data = await response.json();
            
            this.updateRunningTasksCount(data.active_tasks?.length || 0);
            
            // Also check if we need to refresh the saved searches dropdown
            await this.checkForNewCompletedTasks();
        } catch (error) {
            console.error('Error loading running tasks count:', error);
        }
    }

    async checkForNewCompletedTasks() {
        try {
            // Get current completed tasks count
            const projectId = sessionStorage.getItem('projectId');
            const response = await fetch(`http://172.20.23.236:21000/completed-searches${projectId ? `?project_id=${projectId}` : ''}&limit=50`);
            const data = await response.json();
            const currentCompletedCount = data.searches?.length || 0;
            
            // If count increased, refresh the dropdown
            if (!this.lastCompletedTasksCount) {
                this.lastCompletedTasksCount = currentCompletedCount;
            } else if (currentCompletedCount > this.lastCompletedTasksCount) {
                console.log(`New completed task detected! Count changed from ${this.lastCompletedTasksCount} to ${currentCompletedCount}`);
                // Refresh the saved searches dropdown
                await this.loadSavedSearches();
                this.lastCompletedTasksCount = currentCompletedCount;
            }
        } catch (error) {
            console.error('Error checking for new completed tasks:', error);
        }
    }

    startCompletedTasksPolling() {
        // Clear any existing polling
        if (this.completedTasksPollingInterval) {
            clearInterval(this.completedTasksPollingInterval);
        }

        // Poll every 5 seconds to check for new completed tasks
        this.completedTasksPollingInterval = setInterval(async () => {
            await this.checkForNewCompletedTasks();
        }, 5000);
    }

    showSectionDetails(section) {
        const viewer = this.$('#roiSectionViewer');
        if (viewer) {
            viewer.style.display = 'block';
            viewer.innerHTML = `
                <div style="font-size: 11px;">
                    <strong>Section ${section.section}</strong>
                    <div style="margin-top: 4px; color: var(--text-muted);">
                        Biosample: ${section.biosample}<br>
                        Stain: ${section.stain || 'NISL'}<br>
                        ${section.coordinates ? `Coordinates: [${section.coordinates.join(', ')}]` : ''}
                    </div>
                    ${section.image_url ? `
                        <div style="margin-top: 8px;">
                            <img src="${section.image_url}" 
                                 style="max-width: 100%; height: auto; border-radius: 4px; max-height: 200px;"
                                 onerror="this.style.display='none'">
                        </div>
                    ` : ''}
                </div>
            `;
        }
    }
    // EMBEDDED_VIEWER_END

    clearResults() {
        const summaryDiv = this.$('#roiResultsSummary');
        if (summaryDiv) summaryDiv.style.display = 'none';
        
        const viewerContainer = this.$('#roiViewerButtonContainer');
        if (viewerContainer) viewerContainer.style.display = 'none';
        
        this.searchResults = [];
        this.hideHoverThumbnail();
        this.stopProgressPolling();
        this.resetProgress();
        eventBus.emit('roi:clearResults');
        this.setStatus('Results cleared');
    }

    addEmbeddedViewerButton(results) {
        console.log('addEmbeddedViewerButton called with:', results);
        // Show the viewer button container
        const viewerContainer = this.$('#roiViewerButtonContainer');
        console.log('Viewer container found:', !!viewerContainer);
        if (viewerContainer) {
            viewerContainer.style.display = 'block';
            console.log('Viewer container made visible');
        }
        
        let viewerBtn = this.$('#roiViewerBtn');
        console.log('Viewer button found:', !!viewerBtn);
        if (viewerBtn) {
            viewerBtn.onclick = () => {
                if (this.roiViewer) {
                    // Prepare data for the embedded viewer
                    const viewerData = {
                        project_id: results.project_id,
                        hash_value: results.hash_value,
                        total_biosamples: results.total_biosamples || Object.keys(results.results || {}).length,
                        results: this.convertItemsToResultsFormat(results.items)
                    };
                    
                    // Open embedded viewer
                    eventBus.emit('roi:openViewer', viewerData);
                }
            };
        }
    }

    // Convert flat items array back to nested results format for viewer
    convertItemsToResultsFormat(items) {
        const results = {};
        
        if (items) {
            items.forEach(item => {
                const biosample = item.biosample;
                const stain = item.metadata?.stain || item.stain || 'NISL';
                
                if (!results[biosample]) {
                    results[biosample] = {};
                }
                if (!results[biosample][stain]) {
                    results[biosample][stain] = [];
                }
                
                results[biosample][stain].push({
                    section: item.section,
                    image_url: item.imageUrl || item.image_url,
                    filename: item.filename
                });
            });
        }
        
        return results;
    }


    unmount() {
        // Stop progress polling
        this.stopProgressPolling();
        
        // Stop completed tasks polling
        if (this.completedTasksPollingInterval) {
            clearInterval(this.completedTasksPollingInterval);
            this.completedTasksPollingInterval = null;
        }
        
        // Hide hover thumbnails
        this.hideHoverThumbnail();
        
        // Unmount ROI viewer
        if (this.roiViewer) {
            this.roiViewer.unmount();
            this.roiViewer = null;
        }
        
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
        this.element = null;
        super.unmount();
    }
}

export default RoiControlsAccordion;