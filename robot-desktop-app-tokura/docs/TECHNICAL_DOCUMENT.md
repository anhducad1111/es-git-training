# Robot Desktop Application - Technical Document

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Core Modules](#3-core-modules)
4. [Data Flow](#4-data-flow)
5. [Safety Features](#5-safety-features)
6. [API Reference](#6-api-reference)
7. [Configuration](#7-configuration)

---

## 1. System Overview

### 1.1 Features

- ESP32-CAM MJPEG stream reception and display
- YOLOv8-Pose based car detection and pose estimation
- Stanley control for autonomous follow mode
- Gimbal control (pan/tilt) with auto-centering
- Keyboard and mouse input handling
- Real-time telemetry display (distance, temperature, humidity, gas)
- OTA firmware upload capability
- Cloud synchronization
- Snapshot and video recording
- Auto-brake and speed limiting based on obstacle distance
- Target angle calculation and display

### 1.2 Target Hardware

| Device | Role |
|--------|------|
| ESP32-CAM | Front car (camera equipped) |
| ESP32 | Rear car (control target) |
| Raspberry Pi 5 | Server (cloud API, OTA) |
| PC | Desktop control application |

---

## 2. Architecture

### 2.1 File Structure

```
robot-desktop-app-tokura/
├── app.py                      # Main application (PyQt6 GUI)
├── main.py                     # Application entry point
├── config.json                 # Configuration file
├── config.py                   # Configuration loader
├── esp32_api.py                # ESP32 HTTP API client
├── connection_manager.py       # Camera/rover connection management
├── mjpeg_receiver.py           # MJPEG stream receiver
├── detection_manager.py        # Detection mode management
├── follow_detector.py          # YOLOv8-Pose based detection
├── follow_controller.py        # Stanley control + PID
├── hog_detector.py             # HOG human detection
├── yolo_detector.py            # YOLO object detection
├── input_handler.py            # Keyboard input handling
├── cloud_worker.py             # Cloud API worker
├── cloud_manager.py            # Cloud synchronization
├── cloud_api.py                # Cloud API client
├── image_processor.py          # Image processing utilities
├── calibration.py              # Camera calibration
├── views/
│   ├── header.py               # Top header bar
│   ├── sidebar.py              # Left sidebar controls
│   ├── main_view.py            # Main video view
│   ├── diagnostics_view.py     # Diagnostics table
│   ├── settings_view.py        # Settings panel
│   ├── snapshots_view.py       # Snapshots gallery
│   ├── debug_view.py           # Debug parameters
│   └── key_legend.py           # Key binding legend
├── widgets/
│   ├── video_canvas.py         # Video display widget
│   ├── speed_meter.py          # Speed gauge widget
│   └── sensor_card.py          # Sensor display cards
└── rccar_pose_inference/       # Pose estimation module
    ├── pose_inference.py       # YOLOv8-Pose inference
    ├── pose_kalman.py          # Kalman filter for smoothing
    └── rccar_pose_model/       # Geometry calculations
```

### 2.2 Class Diagram

```
MainWindow (app.py)
├── ConnectionManager (connection_manager.py)
│   ├── Camera connection (MJPEG)
│   └── Rover connection (WebSocket)
├── DetectionManager (detection_manager.py)
│   ├── HOGDetector (hog_detector.py)
│   ├── YOLODetector (yolo_detector.py)
│   └── FollowDetector (follow_detector.py)
├── FollowController (follow_controller.py)
│   ├── StanleyControl
│   ├── GimbalThread
│   └── DetectionThread
├── InputHandler (input_handler.py)
├── CloudWorker (cloud_worker.py)
└── ESP32API (esp32_api.py)
```

---

## 3. Core Modules

### 3.1 Detection Manager

Manages different detection modes (HOG, YOLO, Follow).

```python
class DetectionManager(QObject):
    # Signals
    detections_updated = pyqtSignal(list)
    follow_detected = pyqtSignal(dict)
    target_lost = pyqtSignal()
    target_found = pyqtSignal()
    target_angle_updated = pyqtSignal(float)
    
    def toggle_detection(self):
        """Switch between HOG and YOLO detection."""
        
    def toggle_follow_mode(self):
        """Start/stop follow mode with YOLOv8-Pose."""
```

### 3.2 Follow Controller

Implements Stanley control for autonomous following.

```python
class FollowController:
    def __init__(self, config: FollowConfig):
        self.config = config
        self.state = FollowState.SEARCHING
        
    def update(self, detection: dict):
        """Process detection and compute control commands."""
        
    def _compute_command(self, detection: dict) -> dict:
        """Stanley control algorithm."""
```

**Stanley Control Formula:**
```
δ = ψ + atan(k × e / v)

δ: Steering angle
ψ: Heading error (yaw)
e: Cross-track error
k: Gain parameter
v: Vehicle speed
```

### 3.3 Follow Detector

YOLOv8-Pose based car detection with Kalman filtering.

```python
class FollowDetector(QThread):
    detected = pyqtSignal(dict)
    
    def run(self):
        """Main detection loop at ~10 FPS."""
        # 1. Capture frame
        # 2. Run YOLOv8-Pose inference
        # 3. Extract keypoints (wheels, front)
        # 4. Calculate yaw and distance
        # 5. Apply Kalman filtering
        # 6. Emit detection result
```

**Detection Output:**
```python
{
    "yaw_deg": float,      # Heading error in degrees
    "dist_m": float,       # Distance in meters
    "confidence": float,   # Detection confidence
    "bbox": tuple,         # Bounding box (x, y, w, h)
    "frame_w": int,        # Frame width
    "frame_h": int,        # Frame height
    "bearing_deg": float,  # Camera-relative bearing
    "vx_mps": float,       # Velocity X (Kalman)
    "vz_mps": float,       # Velocity Z (Kalman)
    "dist_m_predicted": float  # Predicted distance
}
```

### 3.4 Input Handler

Processes keyboard inputs for manual control.

| Key | Action |
|-----|--------|
| W | Forward |
| S | Backward |
| A | Left |
| D | Right |
| Space | Emergency stop |
| V | Toggle follow mode |
| I/K | Gimbal up/down |
| J/L | Gimbal left/right |
| C | Center gimbal |
| Shift | Speed up |
| Ctrl | Slow down |

---

## 4. Data Flow

### 4.1 Video Stream

```
ESP32-CAM → MJPEG Receiver → ConnectionManager → VideoCanvas → Display
                                      ↓
                              DetectionManager → FollowDetector
```

### 4.2 Control Commands

```
Keyboard Input → InputHandler → send_command() → ESP32 API
                                    ↓
                              Speed Meter Display
```

### 4.3 Follow Mode

```
Camera Frame → FollowDetector → Pose Inference → Kalman Filter
                                                    ↓
                                          FollowController → Stanley Control
                                                    ↓
                                              Motor Commands → ESP32
```

### 4.4 Telemetry

```
ESP32 Sensors → WebSocket → ConnectionManager → Header Display
                                    ↓
                              Diagnostics Table
```

---

## 5. Safety Features

### 5.1 Auto-Brake

Automatically stops the rover when obstacle distance is below threshold.

```python
# In app.py
if distance < self._config["brake_threshold"] and self._config["auto_brake"]:
    self._send_command("stop")
    self._obstacle_brake_active = True
```

**Configuration:**
- `brake_threshold`: 80cm (default)
- `auto_brake`: true/false

### 5.2 Speed Limiting

Reduces speed based on obstacle distance (forward only).

```python
# Quadratic decay from 150cm to 50cm
if distance < 150:
    factor = ((distance - 50) / 100) ** 2
    limited_speed = max(150, int(255 * factor))
```

**Rules:**
- Forward movement only
- Minimum speed: 150
- Reverse: Always full speed

### 5.3 Obstacle Warning

Visual warning when obstacle is detected.

```python
if distance < 100:
    self._obstacle_warning.setText(f"⚠ OBSTACLE: {distance:.0f} cm")
    self._obstacle_warning.show()
```

---

## 6. API Reference

### 6.1 ESP32 API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/distance` | GET | Get ultrasonic distance |
| `/api/temperature` | GET | Get temperature |
| `/api/humidity` | GET | Get humidity |
| `/api/gas` | GET | Get gas sensor value |
| `/api/led?val=0-255` | GET | Set LED brightness |
| `/api/pid?kp=&ki=&kd=&enabled=&bias=` | GET | Set PID parameters |
| `/api/ota` | POST | Upload firmware |

### 6.2 Cloud API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/telemetry` | POST | Send telemetry data |
| `/api/v1/firmware` | POST | Upload OTA firmware |

### 6.3 WebSocket Commands

```
forward     → Move forward
backward    → Move backward
left        → Turn left
right       → Turn right
stop        → Emergency stop
speed:N     → Set speed (0-255)
servo:P,T   → Set gimbal pan/tilt
```

---

## 7. Configuration

### 7.1 config.json

```json
{
    "car_ip": "192.168.1.100",
    "server_url": "http://192.168.1.77/es-git-training/rover-telemetry-backend/public/api/v1",
    "ota_server_url": "http://192.168.1.77",
    "brake_threshold": 80,
    "auto_brake": true,
    "follow_distance": 0.4,
    "follow_band": 0.075,
    "kp_lin": 70.0,
    "ki_lin": 0.4,
    "kd_lin": 10.0
}
```

### 7.2 Follow Config

| Parameter | Default | Description |
|-----------|---------|-------------|
| `follow_distance` | 0.4m | Target following distance |
| `follow_band` | 0.075m | Distance band tolerance |
| `kp_lin` | 70.0 | Proportional gain |
| `ki_lin` | 0.4 | Integral gain |
| `kd_lin` | 10.0 | Derivative gain |
| `min_distance` | 0.2m | Minimum safe distance |
| `max_distance` | 3.0m | Maximum tracking distance |

---

## 8. Thread Safety

### 8.1 Thread Architecture

```
Main Thread (GUI)
├── Detection Thread (FollowDetector)
├── Gimbal Thread (GimbalThread)
├── Control Thread (DetectionThread)
└── Cloud Workers (CloudWorker)
```

### 8.2 Signal-Slot Communication

All cross-thread communication uses PyQt6 signals:

```python
# Thread emits signal
self.detected.emit(detection_data)

# Main thread receives via slot
self._detection_mgr.follow_detected.connect(self._on_follow_detected)
```

### 8.3 Locks and Queues

- `_frame_lock`: Protects camera frame access
- `_detection_queue`: Thread-safe detection data passing
- `_control_queue`: Motor command queuing

---

## 9. Performance Considerations

### 9.1 Detection Rate

- HOG: ~10 FPS
- YOLO: ~3 FPS
- Follow Mode: ~10 FPS (with Kalman filtering)

### 9.2 Network Optimization

- Debounced slider updates (400ms)
- Async HTTP requests via CloudWorker
- Camera stream pause during OTA upload

### 9.3 Memory Management

- Frame buffer recycling
- Detection result caching (last frame only)
- Log file rotation

---

## 10. Debugging

### 10.1 Log Files

Logs are saved to `logs/follow_YYYYMMDD_HHMMSS.log`

### 10.2 Debug View

Access via Settings → Debug tab for real-time parameter tuning.

### 10.3 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Camera not connecting | Network timeout | Check ESP32-CAM IP |
| Gimbal not moving | Camera stream active | Pause stream during commands |
| Follow mode unstable | PID tuning needed | Adjust kp/ki/kd in settings |
| OTA upload fails | Stream active | Stop camera during upload |
