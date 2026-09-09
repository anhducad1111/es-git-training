# Snapshot Feature

## Overview
Capture video frames with sensor data overlay and upload to server.

## Usage
1. Click "SNAPSHOT" button in bottom controls
2. Frame saved to `snapshot/` folder
3. Sensor data overlaid on image
4. Uploaded to cloud server (if endpoint available)

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

### Server Upload
```python
def _upload_snapshot_to_server(self, filepath):
    url = self._cloud_api._url(f"/rovers/{self._cloud_api._device_uid}/media")
    with open(filepath, 'rb') as f:
        files = {'file': (os.path.basename(filepath), f, 'image/png')}
        response = requests.post(url, files=files, timeout=10)
```

### API Endpoint
- **POST** `/api/v1/rovers/{device_uid}/media`
- **Content-Type**: multipart/form-data
- **Field**: `file`
- **Response**: 201 with metadata

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
