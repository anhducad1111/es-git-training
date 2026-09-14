# Technical Document (0907-0911)

## Table of Contents

1. [Video Flip Feature](#1-video-flip-feature)
2. [Video Recording Feature](#2-video-recording-feature)
3. [FPS Display Feature](#3-fps-display-feature)
4. [Web App Remote Control](#4-web-app-remote-control)
5. [Cloud Snapshot Gallery](#5-cloud-snapshot-gallery)
6. [Follow Mode (In Progress)](#6-follow-mode-in-progress)
7. [Sensor Data Cloud Upload & Viewing (Broken)](#7-sensor-data-cloud-upload--viewing-broken)
8. [Technology Stack Summary](#8-technology-stack-summary)

---

## 1. Video Flip Feature

### 1.1 Overview

Flips the MJPEG stream video horizontally or vertically. Implemented to compensate for the ESP32-CAM mounting orientation.

### 1.2 Implementation Files

| File | Role |
|------|------|
| `widgets/video_canvas.py` | Core flip logic |
| `views/main_view.py` | FLIP H / FLIP V button creation and wiring |

### 1.3 Technical Specifications

- **Flip Method**: Affine transformation using Qt's `QTransform`
  - Horizontal flip: `QTransform.scale(-1, 1)`
  - Vertical flip: `QTransform.scale(1, -1)`
- **Target**: `QPixmap` objects (`pixmap.transformed(transform, FastTransformation)`)
- **State Management**: `_flip_h` / `_flip_v` boolean flags in `VideoCanvas` class
- **Application Timing**: Applied after scaling inside `update_frame()` / `update_frame_jpeg()`

### 1.4 Processing Flow

```
QTimer (33ms) → _update_video_frame() → VideoCanvas.update_frame_jpeg()
    → Scaling → _apply_flip(pixmap) → Render
```

### 1.5 Technologies Used

- **PyQt6**: `QPixmap`, `QTransform`, `QLabel`
- OpenCV not used (handled entirely by Qt transformation pipeline)

---

## 2. Video Recording Feature

### 2.1 Overview

Records MP4 video from the MJPEG stream and automatically uploads to the cloud API when recording stops.

### 2.2 Implementation Files

| File | Role |
|------|------|
| `video_manager.py` | Recording start/stop, frame saving, cloud upload |
| `app.py` | QTimer-based frame forwarding and recording trigger |
| `views/bottom_controls.py` | REC button UI toggle |

### 2.3 Technical Specifications

- **Codec**: MP4 (`mp4v` fourcc)
- **FPS**: 10 FPS (fixed)
- **Frame Conversion**: `QImage` → `QBuffer` (JPEG) → `cv2.imdecode` → `numpy.ndarray` → `cv2.VideoWriter.write()`
- **Save Location**: `recordings/` directory (auto-created)
- **File Naming**: Timestamp-based `.mp4` files
- **Cloud Upload**: Auto-uploaded via `cloud_api.upload_media()` when recording stops

### 2.4 Processing Flow

```
QTimer (33ms) → _update_video_frame()
    → frame = ConnectionManager.take_frame()
    → if recording: VideoManager.save_frame(frame)
        → QImage → QBuffer → cv2.imdecode → VideoWriter.write()
    → if stop recording:
        → VideoWriter.release()
        → _upload_recording(filepath) → Cloud API POST
```

### 2.5 Technologies Used

- **OpenCV**: `cv2.VideoWriter`, `cv2.imdecode`, `cv2.VideoWriter_fourcc`
- **PyQt6**: `QImage`, `QBuffer`, `QTimer`
- **NumPy**: Data conversion
- **Cloud API**: `multipart/form-data` file upload

---

## 3. FPS Display Feature

### 3.1 Overview

Real-time overlay display of the video stream's FPS (frames per second).

### 3.2 Implementation Files

| File | Role |
|------|------|
| `widgets/fps_display.py` | FPS display overlay widget |
| `mjpeg_receiver.py` | FPS calculation logic (`DecodeThread`) |
| `connection_manager.py` | `video_stats` signal relay |
| `app.py` | FPS reception and display update |

### 3.3 Technical Specifications

- **Calculation Method**: Records frame arrival timestamps in `deque(maxlen=60)`, calculates as `(frame_count - 1) / elapsed_seconds`
- **Update Interval**: Every 1 second
- **Display Format**: Semi-transparent overlay (bottom-left of screen)
- **Color Coding**:
  - Green: FPS ≥ 25 (good)
  - Yellow: FPS ≥ 15 (acceptable)
  - Red: FPS < 15 (poor performance)

### 3.4 Processing Flow

```
DecodeThread (mjpeg_receiver.py)
    → Records timestamp in deque on each frame arrival
    → Emits stats_updated signal every 1 second
        → ConnectionManager.video_stats signal
            → RoverTeleopApp._on_video_stats()
                → FPSDisplay.update_fps(fps)
                    → Repaint via paintEvent()
```

### 3.5 Technologies Used

- **PyQt6**: `QWidget`, `QPainter`, `pyqtSignal`
- **Python Standard Library**: `collections.deque`, `time` module
- No external libraries (pure Python calculation)

---

## 4. Web App Remote Control

### 4.1 Overview

Remotely controls the robot from a web browser via WebSocket. Enables control from smartphones, tablets, and other devices with a browser, in addition to PC keyboard input.

### 4.2 Implementation Files

| File | Role |
|------|------|
| `remote_control_server.py` | WebSocket server (QThread + asyncio) |
| `app.py` | Server start/stop, command relay |
| `views/sidebar.py` | WEB CONTROL toggle button |
| `web/test.html` | Browser client UI |

### 4.3 Technical Specifications

- **Server**: Python `websockets` library (asyncio-based)
- **Port**: 8765 (configurable in `config.py`)
- **Protocol**: JSON WebSocket
- **Threading Model**: `asyncio.new_event_loop()` created inside a `QThread`

### 4.4 WebSocket Protocol

#### Client → Server

| Message | Description |
|---------|-------------|
| `{"type":"command","command":"forward"}` | Move forward |
| `{"type":"command","command":"backward"}` | Move backward |
| `{"type":"command","command":"left"}` | Turn left |
| `{"type":"command","command":"right"}` | Turn right |
| `{"type":"command","command":"stop"}` | Emergency stop |
| `{"type":"command","command":"speed:200"}` | Set motor speed |
| `{"type":"command","command":"servo:90,75"}` | Set gimbal angle |
| `{"type":"action","action":"snapshot"}` | Capture snapshot |

#### Server → Client

| Message | Description |
|---------|-------------|
| `{"type":"status","allowed":bool,"rover_connected":bool}` | Status notification |
| `{"type":"rejected","reason":"not_allowed"}` | Command rejection |

### 4.5 Processing Flow

```
[Browser] WebSocket connect → ws://<desktop-ip>:8765/
    → RemoteControlServer._on_connect()
        → Send status (allowed, rover_connected)

[Browser] Send {"type":"command","command":"forward"}
    → RemoteControlServer._handle_message()
        → Emit command_received signal
            → RoverTeleopApp._relay_command()
                → ConnectionManager.send_command("forward")
                    → ESP32 WebSocket send
```

### 4.6 Security

- **Permission-based**: Controlled via WEB CONTROL toggle (`allowed` flag)
- **Rejection Response**: Returns `rejected` message when commands arrive while `allowed=False`
- **Auto-disable**: Automatically disables web control when local keyboard input is detected

### 4.7 Technologies Used

- **Python asyncio**: Asynchronous event loop
- **websockets**: WebSocket server library
- **PyQt6 QThread**: Thread isolation (prevents UI freeze)
- **JSON WebSocket**: Real-time bidirectional communication
- **HTML/JS/CSS**: Standalone browser client UI

---

## 5. Cloud Snapshot Gallery

### 5.1 Overview

Gallery feature that displays past snapshots (photos and videos) stored in the cloud API, with preview, download, delete, and image processing capabilities.

### 5.2 Implementation Files

| File | Role |
|------|------|
| `cloud_api.py` | Cloud REST API client |
| `cloud_worker.py` | Asynchronous HTTP request worker |
| `cloud_manager.py` | Cloud connection management |
| `views/snapshots_view.py` | Gallery UI (grid display, pagination, preview, image processing) |
| `views/sidebar.py` | Sidebar snapshot list (compact display) |
| `image_processor.py` | Image processing pipeline |
| `video_manager.py` | Snapshot capture and cloud upload |

### 5.3 Cloud API Specifications

| Method | HTTP | Endpoint | Purpose |
|--------|------|----------|---------|
| `get_media()` | GET | `/rovers/{uid}/media` | Fetch snapshot list |
| `get_media_item()` | GET | `/rovers/{uid}/media/{id}` | Download image/video binary |
| `upload_media()` | POST | `/rovers/{uid}/media` | Upload snapshot |
| `delete_media()` | DELETE | `/rovers/{uid}/media/{id}` | Delete snapshot |

- **Base URL**: `http://192.168.1.77/es-git-training/rover-telemetry-backend/public/api/v1`
- **Device UID**: `rover-001`
- **Timeout**: 10 seconds

### 5.4 Gallery UI Layout

```
+-------------------------------------------+
| SNAPSHOT GALLERY              [REFRESH]   |
| [1] [2] [3] ... (page tabs)              |
| [< PREV] Page 1/3 [NEXT >]              |
| +---------------------------------------+ |
| | [img] [img] [img]   Row 1             | |
| | [img] [img] [img]   Row 2             | |
| +---------------------------------------+ |
+-------------------------------------------+
| Preview | Metadata | DL/Delete | Processing |
+-------------------------------------------+
```

- **Page Size**: 6 items (3 columns x 2 rows)
- **Thumbnails**: Binary fetched from cloud, converted to QPixmap
- **Pagination**: Dynamically generated checkable buttons

### 5.5 Image Processing Features

| Processing Mode | Technology | Description |
|----------------|------------|-------------|
| AUTO CORRECT | CLAHE (LAB color space) | Automatic contrast correction |
| ENHANCE CONTRAST | Gaussian unsharp masking | Contrast enhancement |
| DENOISE | `cv2.fastNlMeansDenoisingColored` | Noise reduction |
| BICUBIC 1.5x | `cv2.resize` (INTER_CUBIC) | Bicubic interpolation upscaling |

- **Execution**: `ImageProcessor` (QThread) runs in background
- **Chain Support**: Multiple modes can be applied sequentially
- **Signals**: `finished(numpy.ndarray)`, `error(str)`, `status(str)`

### 5.6 Processing Flow

```
[Capture]
SNAP button → app._take_snapshot()
    → VideoManager.take_snapshot(pixmap)
        → QPainter sensor data overlay
        → Save PNG to snapshot/
        → CloudAPI.upload_media() POST to cloud

[Gallery Display]
SNAPSHOTS button → app._toggle_snapshots_view()
    → stacks index 2 → _load_snapshots(app)
        → CloudAPI.get_media() GET list
        → Generate pagination
        → Each card: CloudAPI.get_media_item() fetch thumbnail

[Download]
DOWNLOAD button → _download_snapshot(app)
    → If processed image exists: QFileDialog to choose save location
    → Otherwise: fetch binary from cloud → save to snapshot/

[Delete]
DELETE button → _delete_snapshot(app)
    → CloudAPI.delete_media(snap_id) → Reload gallery
```

### 5.7 Technologies Used

- **PyQt6**: `QFrame`, `QLabel`, `QGridLayout`, `QScrollArea`, `QFileDialog`, `QThread`
- **OpenCV**: `cv2.imdecode`, `cv2.fastNlMeansDenoisingColored`, `cv2.resize`
- **requests**: HTTP communication (synchronous)
- **NumPy**: Image array operations

---

## 6. Follow Mode (In Progress)

### 6.1 Overview

Autonomous follow mode that tracks a target RC car using YOLOv8-pose detection, gimbal servoing, and motor control. Uses a 4-thread pipeline architecture.

### 6.2 Architecture

```
GimbalThread (~20Hz)    → Visual servoing for gimbal pan/tilt tracking
DetectionThread          → YOLOv8-pose keypoint detection + Kalman filtering
ControlThread            → State machine for motor command decisions
CommandThread            → ESP32 WebSocket command execution
```

### 6.3 Implementation Files

| File | Role |
|------|------|
| `follow_controller.py` | 4-thread pipeline, state machine, motor commands |
| `follow_detector.py` | QThread YOLO pose detection bridge |
| `rccar_pose_inference/pose_inference.py` | YOLOv8-pose → ground plane projection → yaw/distance |
| `rccar_pose_inference/gimbal_transform.py` | Camera-to-robot-frame coordinate rotation |
| `rccar_pose_inference/pose_kalman.py` | Constant-velocity Kalman filter |
| `rccar_pose_inference/pose_fusion.py` | Confidence-weighted ArUco distance fusion |
| `rccar_pose_inference/rccar_pose_model/geometry.py` | Floor-plane projection (Ground) |
| `rho_alpha_beta_control.py` | Standalone rho-alpha-beta polar controller |
| `detection_manager.py` | Follow mode orchestration |
| `tests/test_follow_controller.py` | Unit tests (388 lines) |

### 6.4 State Machine (9 States)

| State | Description |
|-------|-------------|
| FOLLOWING | Moving toward target with speed/distance control |
| TURNING | Turning to align heading |
| WAITING | Waiting for conditions to resume |
| SEARCHING | Scanning for lost target |
| HEAD_ON_HOLD | Target directly ahead (≈180°), hold position |
| HOLDING | Within distance band (30-45cm), maintain position |
| APPROACHING_BLIND | Moving toward bbox center without yaw/dist |
| LOST_TIMEOUT | Target lost too long, full stop |
| REPOSITIONING | Tail repositioning for large yaw offsets (M key) |

### 6.5 Working Features

| Feature | Status |
|---------|--------|
| Gimbal tracking (~20Hz, tapered-gain) | Working |
| YOLOv8-pose detection pipeline | Working |
| State machine + hysteresis (3-frame) | Working (20+ unit tests) |
| Basic following (distance-based speed) | Working |
| Search logic (directional → spinning) | Working |
| Camera connect/disconnect handling | Working |
| Heading follow (B key) | Partially working |
| Repositioning mode (M key) | Implemented, untested |
| Rho-alpha-beta module | Complete but not integrated |

### 6.6 Known Issues

| Issue | Severity | Description |
|-------|----------|-------------|
| Rho-alpha-beta never called | High | `RhoAlphaBetaController.compute_command()` is never invoked from the control loop |
| FollowConfig UI sliders broken | Medium | Setting non-existent attributes (k/kp/ki/kd/dist_kp) — no effect on behavior |
| Tilt tracking dead code | Medium | `_compute_tilt_step()` defined but never called from `_track_target()` |
| Gimbal sign convention unverified | Medium | `gimbal_transform.py` warning: rotation direction not confirmed on hardware |
| Heading alignment simplistic | Low | Only on/off left/right turn when yaw > 15°, no proportional steering |
| APPROACHING_BLIND always stops | Low | Should drive toward bbox center but currently just stops |

---

## 7. Sensor Data Cloud Upload & Viewing (Broken)

### 7.1 Overview

System for polling ESP32 sensor data, uploading to the cloud, and viewing via diagnostics UI with charts, history tables, and AI analysis.

### 7.2 Architecture

```
ESP32 (sensors) → TelemetryPoller (1s polling)
    → [BROKEN: signal never connected]
        → CloudManager.send_telemetry()
            → Cloud API POST /rovers/{uid}/readings
                → Diagnostics View reads via GET
```

### 7.3 Implementation Files

| File | Role |
|------|------|
| `telemetry_poller.py` | Polls ESP32 `/api/telemetry` every 1s |
| `connection_manager.py` | Manages telemetry poller start/stop |
| `cloud_manager.py` | `send_telemetry()` implementation |
| `cloud_api.py` | REST client (POST telemetry, GET readings) |
| `cloud_worker.py` | QThread HTTP request wrapper |
| `views/diagnostics_view.py` | Charts, history table, AI chat |
| `widgets/sensor_chart.py` | Matplotlib-based sensor chart |
| `widgets/sensor_card.py` | Sensor bar/distance gauge |
| `views/sidebar.py` | Sensor labels, SEND button |

### 7.4 Cloud API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/rovers/{uid}/readings` | Upload telemetry data |
| GET | `/rovers/{uid}/readings` | Fetch readings (with pagination/time range) |
| GET | `/rovers/{uid}/readings/latest` | Fetch latest reading |
| GET | `/rovers/{uid}/readings/summary` | Fetch aggregated summary |
| GET | `/health` | API health check |

### 7.5 Diagnostics View Features

| Feature | Description |
|---------|-------------|
| Sensor Charts | Matplotlib-based real-time charts (temp, humidity, gas) |
| History Table | Configurable limit (10/20/50/100 rows) from cloud |
| AI Sensor Analyst | Gemini API chat with custom chart creation via tool calls |
| System Info | Cloud API health, device status |

### 7.6 Known Bugs

| Bug | Severity | Description |
|-----|----------|-------------|
| **Telemetry never sent to cloud** | Critical | `TelemetryPoller.data_received` signal is never connected to any slot. `CloudManager.send_telemetry()` exists but is never called. |
| **SEND button does nothing** | High | `_manual_send_to_cloud()` only logs a message, does not call `send_telemetry()` |
| **Sidebar sensor labels static** | High | `_temp_label`, `_humidity_label`, `_gas_label` show default values forever (never updated) |
| **Distance card never updates** | High | `_distance_card.update_value()` never called with live data |
| **Diagnostics table always empty** | High | No data in cloud because telemetry is never uploaded |
| **Polling only when diagnostics visible** | Medium | Telemetry starts/stops with view toggle, no background collection |
| **No background telemetry** | Medium | Even if SEND worked, data is only available while diagnostics view is open |

### 7.7 Required Fixes

1. **Connect `TelemetryPoller.data_received` → `CloudManager.send_telemetry()`** in `app.py`
2. **Fix SEND button** to actually call `send_telemetry()` with current sensor data
3. **Update sidebar sensor labels** from live telemetry data
4. **Enable background telemetry polling** independent of UI view state
5. **Update distance card** from live telemetry data

---

## 8. Technology Stack Summary

| Library | Purpose |
|---------|---------|
| PyQt6 | GUI framework, widgets, signals/slots, QThread |
| OpenCV (cv2) | Video recording (VideoWriter), image decoding |
| NumPy | Image data conversion |
| websockets | WebSocket server |
| asyncio | Asynchronous communication |
| requests | Cloud API HTTP client |
| Python Standard Library | `collections.deque`, `time`, `json`, `threading` |
