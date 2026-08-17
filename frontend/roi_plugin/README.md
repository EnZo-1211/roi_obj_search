# ROI Object Search Plugin

This plugin enables ROI (Region of Interest) object search functionality in brain imaging data for the Detection Studio application.

## Features

- Interactive ROI selection on brain sections
- Cross-section object matching using XFeat neural network
- Visual overlay of matched regions
- Database integration with OPEN_ATLAS and HBA_V2
- Real-time search results visualization

## Folder Structure

```
roi_plugin/
├── roi-layer/
│   └── RoiLayer.js              # Map layer for ROI visualization
├── roi-controls-accordion/
│   └── RoiControlsAccordion.js  # UI controls for ROI search
├── roi-service/
│   └── RoiService.js            # API service for ROI operations
└── README.md
```

## Integration Points

### Backend API Endpoints

The plugin communicates with the following API endpoints:

- `POST /api/roi/search` - Perform ROI search
- `GET /api/roi/projects` - Get available projects
- `GET /api/roi/sections/{project_id}` - Get sections for a project
- `GET /api/roi/metadata/{biosample}` - Get section metadata

### Data Flow

1. User selects ROI on brain section
2. Plugin sends ROI coordinates to backend
3. Backend performs feature matching across sections
4. Results returned and visualized as overlays

## Configuration

The plugin requires the following configuration:

```javascript
// In RoiService.js
this.baseUrl = 'http://your-api-host:21000/api';
```

## Events

### Layer Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `roi:toggle` | Listen | Toggle ROI layer visibility |
| `roi:select` | Emit | ROI selection completed |
| `roi:search` | Emit | Trigger ROI search |
| `roi:results` | Listen | Display search results |

### Control Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `roiControls:show` | Listen | Show ROI controls |
| `roiControls:hide` | Listen | Hide ROI controls |
| `roi:opacity` | Emit | Adjust results overlay opacity |

## Usage

### Registration in App.js

```javascript
import { RoiLayer } from './plugins/roi-layer/RoiLayer.js';
import { RoiControlsAccordion } from './plugins/roi-controls-accordion/RoiControlsAccordion.js';

this.plugins = [
    // ... existing plugins
    new RoiLayer(this),
    new RoiControlsAccordion(this)
];
```

### Service Registration

The RoiService is imported in the layer:

```javascript
import { roiService } from '../../services/RoiService.js';
```

## Dependencies

- OpenLayers for map rendering
- XFeat model (loaded via torch.hub)
- MySQL database connections
- Docker environment for backend services