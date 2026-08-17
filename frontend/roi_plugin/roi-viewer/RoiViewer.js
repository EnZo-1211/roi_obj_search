import { Plugin } from '../../core/Plugin.js';
import { eventBus } from '../../core/EventBus.js';

export class RoiViewer extends Plugin {
    constructor(app, options = {}) {
        super(app, options);

        this.resultsData = null;
        this.groupedData = {};
        this.expandedBiosample = null;
        this.isVisible = false;

        this.tileWidth = 160;
        this.tileHeight = 130;

        this.previewModal = null;

        this.currentSections = [];
        this.currentPreviewIndex = -1;
    }

    render() {
        const el = document.createElement('div');
        el.id = 'roiThumbnailDock';

        el.style.cssText = `
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background: #f3f4f6;
            border-top: 1px solid #d1d5db;
            box-shadow: 0 -6px 20px rgba(0,0,0,0.15);
            transform: translateY(100%);
            transition: transform 0.25s ease;
            z-index: 9999;
            padding: 16px 20px;
        `;

        el.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <div style="font-weight:600; font-size:16px;">
                        Thumbnail Viewer
                    </div>

                    <button id="thumbPrev"
                        style="width:30px;height:30px;border-radius:50%;border:1px solid #d1d5db;background:white;cursor:pointer;">
                        ‹
                    </button>

                    <button id="thumbNext"
                        style="width:30px;height:30px;border-radius:50%;border:1px solid #d1d5db;background:white;cursor:pointer;">
                        ›
                    </button>
                </div>

                <button id="roiCloseBtn"
                    style="height:32px;padding:0 14px;background:#dc2626;color:white;border:none;border-radius:6px;font-size:13px;cursor:pointer;">
                    Close
                </button>
            </div>

            <div id="roiThumbnailStrip"
                style="display:flex; gap:14px; overflow-x:auto; scroll-behavior:smooth; padding:10px 0;">
            </div>
        `;

        return el;
    }

    mount() {
        this.element = this.render();
        document.body.appendChild(this.element);
        this.bindEvents();
    }

    bindEvents() {
        this.$('#thumbPrev')?.addEventListener('click', () => {
            this.$('#roiThumbnailStrip')?.scrollBy({ left: -400, behavior: 'smooth' });
        });

        this.$('#thumbNext')?.addEventListener('click', () => {
            this.$('#roiThumbnailStrip')?.scrollBy({ left: 400, behavior: 'smooth' });
        });

        this.$('#roiCloseBtn')?.addEventListener('click', () => {
            this.hide();
        });

        eventBus.on('roi:openViewer', (data) => {
            this.showResults(data);
        });
    }

    async showResults(data) {
        let resultsData;

        if (data.project_id && data.hash_value) {
            const response = await fetch(
                `http://172.20.23.236:21000/results/${data.project_id}/${data.hash_value}`
            );
            resultsData = await response.json();
        } else {
            resultsData = data;
        }

        this.resultsData = resultsData;
        this.groupedData = resultsData?.results || {};

        this.renderBiosamples();
        this.show();
    }

    createBaseTile() {
        const tile = document.createElement('div');

        tile.style.cssText = `
            width:${this.tileWidth}px;
            height:${this.tileHeight}px;
            background:white;
            border:1px solid #d1d5db;
            border-radius:12px;
            flex-shrink:0;
            position:relative;
            cursor:pointer;
            box-shadow:0 2px 6px rgba(0,0,0,0.06);
            padding:4px;
            display:flex;
            flex-direction:column;
            justify-content:center;
            align-items:center;
            transition:all 0.2s ease;
        `;

        tile.onmouseenter = () => {
            tile.style.transform = 'translateY(-3px)';
            tile.style.boxShadow = '0 6px 14px rgba(0,0,0,0.12)';
        };

        tile.onmouseleave = () => {
            tile.style.transform = 'translateY(0)';
            tile.style.boxShadow = '0 2px 6px rgba(0,0,0,0.06)';
        };

        return tile;
    }

    renderBiosamples() {
        const strip = this.$('#roiThumbnailStrip');
        strip.innerHTML = '';

        Object.entries(this.groupedData).forEach(([biosample]) => {
            const tile = this.createBaseTile();

            tile.innerHTML = `
                <div style="font-size:15px;font-weight:600;text-align:center;">
                    Biosample ${biosample}
                </div>
            `;

            tile.addEventListener('click', () => {
                this.toggleBiosample(biosample);
            });

            strip.appendChild(tile);
        });
    }

    toggleBiosample(biosample) {
        if (this.expandedBiosample === biosample) {
            this.expandedBiosample = null;
            this.renderBiosamples();
        } else {
            this.expandedBiosample = biosample;
            this.renderExpanded(biosample);
        }
    }

    renderExpanded(biosample) {
        const strip = this.$('#roiThumbnailStrip');
        strip.innerHTML = '';

        Object.entries(this.groupedData).forEach(([sample, stains]) => {

            const biosampleTile = this.createBaseTile();
            biosampleTile.style.border =
                sample === biosample
                    ? '2px solid #2563eb'
                    : '1px solid #d1d5db';

            biosampleTile.innerHTML = `
                <div style="font-size:15px;font-weight:600;text-align:center;">
                    Biosample ${sample}
                </div>
            `;

            biosampleTile.addEventListener('click', () => {
                this.toggleBiosample(sample);
            });

            strip.appendChild(biosampleTile);

            if (sample === biosample) {

                let sections = [];
                Object.values(stains).forEach(images => {
                    sections = sections.concat(images);
                });

                sections.sort((a, b) => Number(a.section) - Number(b.section));

                this.currentSections = sections;

                sections.forEach((section, index) => {
                    const sectionTile = this.createBaseTile();

                    sectionTile.innerHTML = `
                        <img src="${section.image_url}"
                            style="width:100%; height:105px; object-fit:contain;"
                        />
                        <div style="
                            position:absolute;
                            bottom:6px;
                            left:8px;
                            font-size:13px;
                            color:#dc2626;
                            font-weight:600;">
                            ${section.section}
                        </div>
                    `;

                    sectionTile.addEventListener('click', () => {
                        this.currentPreviewIndex = index;
                        this.openPreview();
                    });

                    strip.appendChild(sectionTile);
                });
            }
        });
    }

    /* ---------------- PREVIEW MODAL ---------------- */

    openPreview() {
        if (this.previewModal) {
            this.previewModal.remove();
        }

        const section = this.currentSections[this.currentPreviewIndex];

        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 540px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.25);
            z-index: 10000;
            overflow: hidden;
        `;

        modal.innerHTML = `
            <div id="previewHeader"
                style="
                    padding: 10px 14px;
                    background: #f3f4f6;
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    font-weight:600;
                    font-size:14px;
                    cursor:move;
                ">
                <div>
                    Human Brain - Section ${section.section}
                </div>

                <div style="display:flex; gap:8px; align-items:center;">
                    <button id="previewPrev"
                        style="border:none;background:white;padding:4px 8px;border-radius:6px;cursor:pointer;">
                        ‹
                    </button>

                    <button id="previewNext"
                        style="border:none;background:white;padding:4px 8px;border-radius:6px;cursor:pointer;">
                        ›
                    </button>

                    <button id="previewCloseBtn"
                        style="border:none;background:transparent;font-size:16px;cursor:pointer;">
                        ✕
                    </button>
                </div>
            </div>

            <div style="
                height:440px;
                background:#f9fafb;
                display:flex;
                align-items:center;
                justify-content:center;
            ">
                <img id="previewImage"
                    src="${section.image_url}"
                    style="max-width:90%; max-height:90%;"
                />
            </div>
        `;

        document.body.appendChild(modal);
        this.previewModal = modal;

        modal.querySelector('#previewCloseBtn')
            .addEventListener('click', () => this.closePreview());

        modal.querySelector('#previewPrev')
            .addEventListener('click', () => this.navigatePreview(-1));

        modal.querySelector('#previewNext')
            .addEventListener('click', () => this.navigatePreview(1));

        this.makeDraggable(modal, modal.querySelector('#previewHeader'));
    }

    navigatePreview(direction) {
        const newIndex = this.currentPreviewIndex + direction;

        if (newIndex < 0 || newIndex >= this.currentSections.length) return;

        this.currentPreviewIndex = newIndex;

        const section = this.currentSections[this.currentPreviewIndex];

        this.previewModal.querySelector('#previewImage').src = section.image_url;
        this.previewModal.querySelector('#previewHeader div')
            .textContent = `Human Brain - Section ${section.section}`;
    }

    makeDraggable(modal, handle) {
        let offsetX = 0;
        let offsetY = 0;
        let isDragging = false;

        handle.addEventListener('mousedown', (e) => {
            isDragging = true;
            const rect = modal.getBoundingClientRect();
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            modal.style.transform = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            modal.style.left = `${e.clientX - offsetX}px`;
            modal.style.top = `${e.clientY - offsetY}px`;
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    }

    closePreview() {
        if (this.previewModal) {
            this.previewModal.remove();
            this.previewModal = null;
        }
    }

    show() {
        this.isVisible = true;
        this.element.style.transform = 'translateY(0)';
        document.body.style.paddingBottom = '260px';
    }

    hide() {
        this.isVisible = false;
        this.element.style.transform = 'translateY(100%)';
        document.body.style.paddingBottom = '0px';
        this.expandedBiosample = null;
    }
}

export default RoiViewer;