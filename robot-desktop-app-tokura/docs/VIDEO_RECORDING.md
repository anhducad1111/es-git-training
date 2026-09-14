# Video Recording Feature

## Overview
Record video from the MJPEG camera stream and upload to cloud storage.

## Usage

### Recording Controls
| Button | Action |
|--------|--------|
| **REC** (normal) | Start recording |
| **REC** (recording) | Stop recording |

### Recording Flow
1. Click "REC" button to start recording
2. Button turns solid red, shows recording state
3. Video frames are captured and encoded
4. Click "REC" again to stop
5. Video automatically uploads to cloud
6. Button returns to normal state

### Saved Files
- **Location**: `recordings/` folder
- **Format**: AVI (XVID codec)
- **Naming**: `rec_YYYYMMDD_HHMMSS.avi`
- **Frame Rate**: 10 FPS
- **Resolution**: Matches camera stream (640x480)

## Implementation

### Recording State
```python
# app.py - Initialization
self._recording = False
self._rec_path = None
```

### Start Recording
```python
def _start_recording(self):
    import os
    from datetime import datetime
    os.makedirs("recordings", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    self._rec_path = f"recordings/rec_{timestamp}.avi"
    self._recording = True
    self._add_log("REC", f"Recording started: {self._rec_path}")
```

### Frame Capture
```python
def _update_video_frame(self):
    if hasattr(self, '_video_receiver') and self._video_receiver:
        frame = self._video_receiver.take_frame()
        if frame:
            if self._recording and isinstance(frame, bytes):
                self._save_rec_frame(frame)  # Save frame during recording
            # ... display frame

def _save_rec_frame(self, frame_bytes):
    import cv2
    import numpy as np
    nparr = np.frombuffer(frame_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is not None:
        if not hasattr(self, '_rec_writer') or self._rec_writer is None:
            h, w = img.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self._rec_writer = cv2.VideoWriter(
                self._rec_path, fourcc, 10.0, (w, h)
            )
        self._rec_writer.write(img)
```

### Stop Recording
```python
def _stop_recording(self):
    if self._recording:
        self._recording = False
        if hasattr(self, '_rec_writer') and self._rec_writer is not None:
            self._rec_writer.release()
            self._rec_writer = None
        self._add_log("REC", f"Recording saved: {self._rec_path}")
        self._upload_recording(self._rec_path)  # Auto-upload to cloud
```

### Cloud Upload
```python
def _upload_recording(self, filepath):
    if not self._cloud_api:
        self._add_log("REC", "Cloud API not available")
        return
    
    url = self._cloud_api._url(f"/rovers/{self._cloud_api._device_uid}/media")
    filename = os.path.basename(filepath)
    
    with open(filepath, 'rb') as f:
        files = {'file': (filename, f, 'video/avi')}
        response = requests.post(url, files=files, timeout=60)
    
    if response.status_code == 201:
        self._add_log("REC", f"Uploaded to cloud: {filename}")
```

## API Endpoint
- **POST** `/api/v1/rovers/{device_uid}/media`
- **Content-Type**: multipart/form-data
- **Field**: `file`
- **Response**: 201 with metadata

## Button Styling
```css
/* Normal state */
background-color: rgba(239, 68, 68, 0.15);
color: #ef4444;

/* Recording state */
background-color: #ef4444;
color: white;
```

## Dependencies
- OpenCV (`opencv-python`)
- NumPy (included with OpenCV)

## Notes
- Recording continues while navigating other views
- Frames are captured from the MJPEG stream buffer
- Video codec is XVID for broad compatibility
- Automatic upload after recording stops
- Upload timeout set to 60 seconds for large files
