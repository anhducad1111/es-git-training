# Technical Documentation — ESP32-Cam FPV Client

## 1. Overview

A PyQt6 desktop application that receives and displays live MJPEG video streams from ESP32-Cam modules over HTTP. Includes real-time object detection using YOLOv8 with toggleable detection and bounding box overlay.

**Target hardware:** ESP32-CAM (AI-Thinker module or compatible) running MJPEG stream firmware.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CameraApp (QWidget)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────────┐  │
│  │ URL Bar  │  │ Controls │  │        CameraCanvas          │  │
│  │ (Input)  │  │ (Sliders)│  │ (QLabel + paintEvent)        │  │
│  │          │  │ + Detect │  │  ┌────────────────────────┐  │  │
│  │          │  │  Toggle  │  │  │ detections: list[dict] │  │  │
│  └──────────┘  └──────────┘  │  └────────────────────────┘  │  │
│       │              │        └──────────────────────────────┘  │
│       │         HTTP GET                ▲                       │
│       │         (debounced)    _poll_frame()                    │
│       │              │          QTimer (33ms)                   │
│       │              │               │                          │
│       ▼              ▼               │                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              CameraThread (QThread)                       │   │
│  │  ┌────────────────────────────────────────────────┐      │   │
│  │  │  frame_queue (queue.Queue, maxsize=2)         │      │   │
│  │  └────────────────────────────────────────────────┘      │   │
│  │  - urllib.request.urlopen() stream reader                │   │
│  │  - JPEG boundary detection (\xff\xd8 / \xff\xd9)          │   │
│  │  - QImage.loadFromData() decode                          │   │
│  │  - Frame dropping when queue full                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  detector.py — YOLOv8 Object Detection                   │   │
│  │  - YOLO("yolov8n.pt") — nano model (fastest)            │   │
│  │  - detect(image, conf) → list[dict]                      │   │
│  │  - Runs every Nth frame (configurable)                   │   │
│  │  - Returns: [{box, label, confidence}, ...]              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│                 HTTP MJPEG Stream                                │
│                (ESP32-Cam module)                                │
└─────────────────────────────────────────────────────────────────┘
```

**Pattern:** Queue-based producer-consumer with optional detection stage. `CameraThread` produces `QImage` frames into a bounded queue. `CameraApp` polls the queue, optionally runs YOLOv8 detection, and displays results with bounding box overlay.

---

## 3. Component Details

### 3.1 `main.py` — Entry Point

```python
app = QApplication(sys.argv)
window = CameraApp()
window.show()
sys.exit(app.exec())
```

### 3.2 `camera_thread.py` — Stream Reader

**Class:** `CameraThread(QThread)`

**Attributes:**
| Attribute | Type | Description |
|-----------|------|-------------|
| `frame_queue` | `queue.Queue(maxsize=2)` | Bounded frame buffer |
| `connected` | `bool` | Current connection state |
| `error_msg` | `str \| None` | Last error message (consumed by GUI) |

**Frame dropping logic:**
```python
if self.frame_queue.full():
    self.frame_queue.get_nowait()   # drop oldest
self.frame_queue.put_nowait(image)  # add newest
```

### 3.3 `detector.py` — YOLOv8 Detection

**Model:** YOLOv8n (nano) — smallest/fastest YOLOv8 variant.

**Functions:**
| Function | Signature | Description |
|----------|-----------|-------------|
| `get_model()` | `() → YOLO` | Lazy-loads YOLOv8n model (singleton) |
| `detect()` | `(image, conf=0.5) → list[dict]` | Runs detection on QImage |

**Detection output:**
```python
[
    {
        "box": (x1, y1, x2, y2),   # bounding box pixels
        "label": "person",          # class label
        "confidence": 0.87          # confidence score
    },
    ...
]
```

**Performance:** Detection runs on CPU. YOLOv8n processes ~50ms per frame at 640x480. Detection runs every Nth frame (default 3) to balance accuracy and CPU usage.

### 3.4 `app.py` — GUI

#### Timers

| Timer | Interval | Purpose |
|-------|----------|---------|
| `_frame_timer` | 33ms (~30 FPS) | Polls `frame_queue`, displays latest frame |
| `_status_timer` | 500ms | Checks connection state and errors |
| `_fps_timer` | 1000ms | Updates FPS counter |
| `_time_timer` | 1000ms | Updates clock display |
| `_led_timer` | 100ms (one-shot) | Debounces LED slider HTTP requests |
| `_quality_timer` | 100ms (one-shot) | Debounces quality slider HTTP requests |

#### `CameraCanvas(QLabel)`

Displays video. Uses `FastTransformation` (nearest-neighbor) for scaling.

**Attributes:**
| Attribute | Type | Description |
|-----------|------|-------------|
| `detections` | `list[dict]` | Current frame detection results |

**`paintEvent` draws:**
1. Crosshair overlay (centered, semi-transparent white)
2. Timestamp (top-left, green monospace)
3. Detection bounding boxes (green rectangles with labels)

#### `CameraApp(QWidget)`

Main window. Layout (top to bottom):
1. **URL bar** — stream URL input + Connect/Disconnect toggle
2. **Controls** — resolution combo, LED slider, quality slider, **Detect toggle button**
3. **CameraCanvas** — video display with detection overlay
4. **Status bar** — connection state, FPS counter, current time
5. **Log panel** — timestamped event log

**Detection state:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `_detection_enabled` | `bool` | `True` | Toggle detection on/off |
| `_detection_interval` | `int` | `3` | Run detection every N frames |
| `_detection_confidence` | `float` | `0.5` | Minimum confidence threshold |
| `_frame_count_total` | `int` | `0` | Total frames processed |

### 3.5 `config.py` — Configuration

**Default config:**
```python
{
    "cam_ip": "192.168.1.114",
    "cam_port": 80,
    "stream_path": "/640x480.mjpeg",
    "led_brightness": 0,
    "jpeg_quality": 14,
    "detection_enabled": true,
    "detection_interval": 3,
    "detection_confidence": 0.5
}
```

Config is saved to `config.json` on window close.

---

## 4. Data Flow

### 4.1 Video Pipeline

```
ESP32-Cam
  │
  ▼ HTTP chunked transfer
CameraThread._stream.read(1024)
  │
  ▼ Buffer scan for \xff\xd8 ... \xff\xd9
JPEG extraction
  │
  ▼ QImage.loadFromData(data, "JPEG")
  │
  ▼ queue.put_nowait() (drops oldest if full)
frame_queue (maxsize=2)
  │
  ▼ _poll_frame() drains queue, keeps latest
  │
  ├─ If detection enabled AND frame_count % interval == 0:
  │    ▼ detector.detect(image, conf) → detections list
  │    ▼ canvas.detections = detections
  │
  ├─ Else:
  │    ▼ canvas.detections = []
  │
  ▼ CameraCanvas.update_frame()
QPixmap → FastTransformation scale → setPixmap()
  │
  ▼ Qt paintEvent
  ├─ Crosshair + timestamp overlay
  └─ Bounding boxes + labels (if detections present)
```

### 4.2 Detection Pipeline

```
_poll_frame() (every 33ms)
  │
  ▼ frame_count_total += 1
  │
  ▼ Check: detection_enabled AND frame_count % interval == 0?
  │
  ├─ Yes → detector.detect(image, conf=0.5)
  │         │
  │         ▼ YOLOv8n inference (~50ms)
  │         ▼ Returns list of {box, label, confidence}
  │         ▼ canvas.detections = results
  │
  └─ No  → canvas.detections = []
  │
  ▼ _on_frame(image) → canvas update → paintEvent draws boxes
```

### 4.3 Control Pipeline (LED / Quality)

```
Slider valueChanged(int)
  │
  ▼ Stores value in _led_pending / _quality_pending
  ▼ Starts debounce timer (100ms one-shot)
  │
  ▼ Timer fires → _send_led() / _send_quality()
  ▼ requests.get(f"http://{ip}/api/{endpoint}?val={n}", timeout=2)
HTTP GET to ESP32-Cam
```

### 4.4 Connection State Polling

```
_status_timer (500ms)
  │
  ▼ Reads camera_thread.connected (bool)
  │
  ├─ False → True:  _on_connected() (update UI)
  ├─ True → False:  _on_disconnected() (update UI)
  │
  ▼ Reads camera_thread.error_msg (str | None)
  ├─ Not None: _add_log() + clear error_msg
```

---

## 5. Threading Model

```
Main Thread (Qt Event Loop)
  │
  ├── CameraApp (GUI)
  ├── QTimer: _frame_timer (33ms)   → polls frame_queue + runs detection
  ├── QTimer: _status_timer (500ms) → checks connection state
  ├── QTimer: _fps_timer (1000ms)   → updates FPS
  ├── QTimer: _time_timer (1000ms)  → updates clock
  ├── QTimer: _led_timer (100ms)    → debounces LED API
  ├── QTimer: _quality_timer (100ms)→ debounces quality API
  │
  └── CameraThread (QThread)
        ├── Stream read loop
        ├── JPEG decode
        └── queue.put_nowait() (thread-safe, no lock needed)
```

**Note:** Detection runs on the main thread within `_poll_frame()`. At ~50ms per inference, this blocks the event loop briefly. For production use, detection should be moved to a separate thread.

**Thread safety:** `queue.Queue` is inherently thread-safe. No explicit locks required.

**Frame dropping:** When the queue is full (2 frames), the oldest frame is removed before adding the new one. This ensures the GUI always processes the latest frame, preventing backlog lag.

---

## 6. ESP32-Cam API Protocol

| Method | Endpoint | Parameters | Description |
|--------|----------|------------|-------------|
| GET | `/{WxH}.mjpeg` | — | MJPEG stream at specified resolution |
| GET | `/api/led` | `val` (0-255) | Set onboard LED brightness |
| GET | `/api/quality` | `val` (0-63) | Set JPEG compression quality |

**Supported resolutions:**

| Label | Path |
|-------|------|
| QVGA | `/320x240.mjpeg` |
| VGA | `/640x480.mjpeg` |
| SVGA | `/800x600.mjpeg` |
| XGA | `/1024x768.mjpeg` |
| UXGA | `/1600x1200.mjpeg` |

---

## 7. Performance Optimizations

| Issue | Fix |
|-------|-----|
| Smooth bilinear scaling per frame | `FastTransformation` (nearest-neighbor) |
| HTTP flood on slider drag | 100ms debounce timers |
| Frame backlog causing lag | `queue.Queue(maxsize=2)` with frame dropping |
| Detection CPU overhead | Runs every Nth frame (default 3) |
| Detection toggle | Button to enable/disable entirely |

**Frame dropping behavior:** Queue holds max 2 frames. If the ESP32 sends faster than the GUI displays, old frames are silently dropped. The GUI always renders only the latest frame.

**Detection performance:** YOLOv8n processes ~50ms per frame at 640x480. With `detection_interval=3`, effective detection rate is ~10 FPS while display stays at ~30 FPS.

---

## 8. Error Handling

| Scenario | Behavior |
|----------|----------|
| Connection timeout (10s) | Exception → `error_msg` set → logged → reconnect after 2s |
| Invalid JPEG data | `QImage.isNull()` → frame silently dropped |
| `requests` not installed | `HAS_REQUESTS = False` → API calls silently skipped |
| Network unreachable | Exception → `error_msg` → auto-reconnect loop |
| Queue full | Oldest frame dropped, newest queued |
| YOLOv8 model load fail | First detection call downloads `yolov8n.pt` (~6MB) |
| Detection error | Exception caught, detection skipped for that frame |

---

## 9. Dependencies

| Package | Purpose |
|---------|---------|
| `PyQt6` | GUI framework, threading (QThread, QTimer) |
| `requests` | HTTP API calls (optional, graceful fallback) |
| `ultralytics` | YOLOv8 object detection |

Standard library: `queue`, `urllib.request`, `json`, `os`, `datetime`, `time`.

---

## 10. File Structure

```
camera-screen-app/
├── main.py              # Entry point (15 lines)
├── app.py               # GUI classes + detection integration
├── camera_thread.py     # Stream reader thread (76 lines)
├── detector.py          # YOLOv8 detection wrapper (22 lines)
├── config.py            # Config load/save (24 lines)
├── config.json          # Persisted settings
├── requirements.txt     # Dependencies
├── README.md            # User documentation
└── TECHNICAL_DOC.md     # This file
```

---

## 11. Future Extensibility

The queue-based architecture supports adding processing stages:

```
CameraThread → frame_queue → [Detector] → [Tracker] → display_queue → Display
                                           → [Servo Controller] → ESP32 API
```

**Following mode integration points:**
- Insert a frame processor between `frame_queue` and display
- Read frames from queue without consuming (peek or copy)
- Send motor/servo commands based on detection/tracking results
- Independent processing rate from display rate
