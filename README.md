# ROI Object Search Pipeline - Full Workspace

Welcome to the **ROI Object Search Pipeline** workspace! This application provides a comprehensive suite of tools for region-of-interest (ROI) object matching and search across multiple histological sections in large-scale neural datasets. 

This repository has been organized into a unified workspace containing both the frontend plugin and the FastAPI backend, complete with Celery-based asynchronous processing.

## 📁 Workspace Structure

```
final/
├── backend/                  # Core processing engine, API, and task queues
│   ├── app.py                # Main application entrypoint
│   ├── main.py               # FastAPI server and endpoint definitions
│   ├── celery_config.py      # Configuration for Celery & Redis integration
│   ├── celery_tasks.py       # Async workers for processing large datasets
│   ├── obj_search_utils/     # Core algorithms for matching, metadata, and database integrations
│   ├── task_history.py       # Task logging and management utilities
│   └── README_roi_plugin     # Detailed backend documentation
│
└── frontend/                 # Interactive Viewer UI (plugin)
    └── roi_plugin/           # Frontend components for selection and visualization
        ├── roi-viewer/       # Main viewer component
        ├── roi-layer/        # Overlay logic for rendering bounding boxes
        ├── roi-controls-accordion/ # User interface controls
        └── roi-service/      # API communication service
```

## ✨ Application Features

### 🚀 High-Performance Backend (FastAPI + Deep Learning)
- **FastAPI REST API**: Serves robust endpoints for starting searches, checking progress, retrieving matched results, and querying project statistics.
- **Deep Learning Feature Extraction**: Uses **PyTorch** and **XFeat** (Accelerated Features) to extract and match up to 4096 local features per image, robust to rotation and scale changes.
- **Geometric Validation**: Implements RANSAC-based affine transformation estimation to validate and filter high-confidence matches.
- **Dynamic Bounding Box Crop**: Seamlessly converts user-drawn bounding boxes in world-space coordinates to image crops dynamically while adjusting for rotation parameters.

### ⏱️ Asynchronous Processing (Celery + Redis)
- **Task Queues**: Offloads heavy, multi-biosample processing jobs to background Celery workers, preventing API bottlenecks.
- **Real-Time Progress Tracking**: Granular tracking on a per-section basis, allowing the frontend to poll for remaining sections and real-time status.
- **Task History Management**: Built-in persistence for active and completed tasks, allowing users to revisit past search queries without reprocessing.

### 🧠 Advanced Image & Biological Analytics
- **Multi-Biosample & Multi-Stain Support**: Automatically scans across multiple biosamples and various histological stains (e.g., NISSL, MYELIN, H&E, IHC) to find structural equivalents.
- **Intelligent Database Integrations**: Interfaces with OPEN_ATLAS and HBA_V2 MySQL databases to dynamically map section metadata, world-coordinates, and physical rotation angles.

### 💻 Interactive Frontend Plugin
- **ROI Controls & Selection**: Easy-to-use interactive accordion interface for users to select target sections and stains.
- **Visual Overlays (roi-layer)**: Highlights matching regions across different sections with visually distinct bounding boxes and match-confidence visualizations.
- **Seamless Service Integration (roi-service)**: Automatically orchestrates the lifecycle of API requests—submitting queries, polling the async celery endpoints, and rendering the final transformed results onto the viewer.

## 🛠️ Quick Start (Development)

1. Ensure you have **Redis** running locally (`redis-server`).
2. Install Python dependencies and launch the API server inside `backend/`:
   ```bash
   cd backend
   uvicorn main:app --port 21000 --reload
   ```
3. Start the Celery worker to process jobs:
   ```bash
   celery -A celery_config worker --loglevel=info
   ```
4. Load the `frontend/` components into your primary viewer application to interact with the API.

> **Note**: For detailed configuration regarding the database environment variables, Docker setup, and the underlying XFeat implementation, please refer to the `backend/README_roi_plugin` file.
