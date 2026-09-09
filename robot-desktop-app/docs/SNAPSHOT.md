# Snapshot Feature

## Overview
Capture video frames with sensor data overlay and upload to server. Browse captured snapshots in a paginated gallery with thumbnail previews.

## Usage

### Taking Snapshots
1. Click "SNAPSHOT" button in bottom controls
2. Frame saved to `snapshot/` folder
3. Sensor data overlaid on image
4. Uploaded to cloud server (if endpoint available)

### Snapshot Gallery
- Navigate to "SNAPSHOTS" view from sidebar
- **6 snapshots per page** in 3x2 grid
- **Tab navigation** (1, 2, 3...) for multiple pages
- **PREV/NEXT buttons** for sequential navigation
- **Thumbnail previews** loaded from cloud

### Gallery Controls
| Control | Function |
|---------|----------|
| **Tab buttons** | Jump to specific page |
| **PREV/NEXT** | Navigate sequentially |
| **REFRESH** | Reload all snapshots |
| **DOWNLOAD** | Save selected/processed image |
| **DELETE** | Remove snapshot from cloud |

## Implementation

### Snapshot Capture
```python
def _take_snapshot(self):
    # Get current frame
    pixmap = self._video_canvas.pixmap()
    
    # Create overlay with sensor data
    overlay = pixmap.copy()
    painter = QPainter(overlay)
    
    # Draw green text with sensor values
    painter.setPen(QPen(QColor(16, 185, 129), 1))
    painter.drawText(panel_x, panel_y, f"T:{temp}°C  H:{humidity}%  G:{gas}PPM  {time}")
    
    # Save to file
    overlay.save(filepath, "PNG")
    
    # Upload to server
    self._upload_snapshot_to_server(filepath)
```

### Paginated Gallery
```python
PAGE_SIZE = 6

def _show_current_page(app):
    data = getattr(app, '_snapshot_data', [])
    page = app._snapshot_page
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_data = data[start:end]
    
    # Display in 3x2 grid
    for i, snap in enumerate(page_data):
        row = i // 3
        col = i % 3
        app._snapshot_grid_layout.addWidget(card, row, col)
```

### Tab Navigation
```python
def _build_tab_buttons(app):
    for p in range(app._snapshot_total_pages):
        btn = QPushButton(f"{p + 1}")
        btn.setCheckable(True)
        btn.clicked.connect(lambda checked, page=p: _go_to_page(app, page))
        app._snapshot_tab_layout.insertWidget(...)
```

### Thumbnail Loading
```python
# Load thumbnail from cloud for each snapshot
snap_id = snap.get("id")
if snap_id:
    image_data = app._cloud_api.get_media_item(snap_id)
    if image_data:
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        if not pixmap.isNull():
            scaled = pixmap.scaled(208, 140, ...)
            thumb_label.setPixmap(scaled)
```

### Server Upload
```python
def _upload_snapshot_to_server(self, filepath):
    url = self._cloud_api._url(f"/rovers/{self._cloud_api._device_uid}/media")
    with open(filepath, 'rb') as f:
        files = {'file': (os.path.basename(filepath), f, 'image/png')}
        response = requests.post(url, files=files, timeout=10)
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| **GET** | `/api/v1/rovers/{uid}/media` | List all snapshots |
| **GET** | `/api/v1/rovers/{uid}/media/{id}` | Get snapshot binary |
| **POST** | `/api/v1/rovers/{uid}/media` | Upload snapshot |
| **DELETE** | `/api/v1/rovers/{uid}/media/{id}` | Delete snapshot |

## Overlay Format
```
T:28.5°C  H:47.0%  G:150PPM  14:30:25
```

## File Naming
```
snapshot_20260908_162504.png
```

## Super Resolution
Optional bicubic interpolation for higher resolution output.
- Toggle via "Super-Res" checkbox
- Output saved as `high_snapshot_*.png`

## Gallery Layout
```
┌─────────────────────────────────────────┐
│  SNAPSHOT GALLERY          [REFRESH]    │
│  [1] [2] [3] ... (page tabs)           │
│  [< PREV] Page 1/3 [NEXT >]            │
├─────────────────────────────────────────┤
│ ┌─────┐ ┌─────┐ ┌─────┐               │
│ │ img │ │ img │ │ img │  Row 1         │
│ │ 1   │ │ 2   │ │ 3   │               │
│ └─────┘ └─────┘ └─────┘               │
│ ┌─────┐ ┌─────┐ ┌─────┐               │
│ │ img │ │ img │ │ img │  Row 2         │
│ │ 4   │ │ 5   │ │ 6   │               │
│ └─────┘ └─────┘ └─────┘               │
└─────────────────────────────────────────┘
```
