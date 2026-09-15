# Robot Desktop App - Complete Feature Documentation

## Overview

The Robot Desktop App is a real-time IoT rover teleoperation system built with PyQt6. It provides a comprehensive cockpit for controlling an ESP32-based hardware rover with camera, gimbal, motors, and sensors, while also integrating cloud-backed data pipeline and autonomous features.

---

## 1. Core Driving Controls

### Manual Driving
- **WASD Keys**: Control rover movement
  - `W`: Move forward
  - `S`: Move backward
  - `A`: Turn left
  - `D`: Turn right
- **Space Bar**: Emergency stop (immediately stops all motors)
- **Speed Control**: 
  - `Shift`: Increase speed
  - `Ctrl`: Decrease speed
  - Speed range: 180-255 (configurable via slider)

### Speed Meter
- Real-time visual speed display with analog gauge
- Shows current motor speed (0-255)
- Color-coded: Green (low), Yellow (medium), Red (high)
- Immediately shows 0 when rover stops

---

## 2. Camera Gimbal Control

### Manual Control
- **IJKL Keys**: Control gimbal movement
  - `I`: Tilt up
  - `K`: Tilt down
  - `J`: Pan left
  - `L`: Pan right
  - `C`: Center gimbal (90°, 90°)

### Mouse Gimbal
- Toggle with "MOUSE GIMBAL" button
- When enabled, mouse movement controls gimbal pan/tilt
- Real-time HUD overlay shows gimbal position

### Direct Input
- Enter specific pan/tilt angles (0-180°) in sidebar input fields
- Press Enter to send command
- Auto-resets to 90°, 90° on app startup

---

## 3. Video Streaming

### FPV Video
- Real-time MJPEG video stream from ESP32-CAM
- Low-latency display with FPS counter
- Configurable resolution: 320x240 to 1600x1200
- Flip horizontal/vertical options

### Video Quality
- Adjustable quality setting (0-63)
- Real-time quality adjustment without stream restart

### Recording
- Record video to local files
- Start/stop recording via sidebar button

---

## 4. Safety Features

### Auto-Brake System
- **Distance Monitoring**: Ultrasonic sensor measures obstacle distance
- **Automatic Stop**: When distance < threshold (default 80cm), sends stop command
- **Warning Banner**: Amber warning banner appears on video feed
- **Configurable**: Threshold adjustable in settings (10-100cm)

### Distance-Based Speed Limiting
- **Forward Movement Only**: Speed reduced when approaching obstacles
- **Progressive Reduction**: 
  - 150cm: Full speed
  - 100cm: ~75% speed
  - 80cm: ~50% speed
  - 50cm: ~25% speed
- **Minimum Speed**: Never goes below 150
- **Reverse Movement**: Always full speed (no limit)

### Connection Monitoring
- Automatic reconnection on WebSocket disconnect
- Visual disconnect indicators
- Rover-side failsafe: stops if no command received for 1 second

---

## 5. Telemetry & Sensors

### Real-Time Data
- **Temperature**: Ambient temperature (°C)
- **Humidity**: Relative humidity (%)
- **Air Quality**: Gas sensor (PPM)
- **Distance**: Ultrasonic obstacle distance (cm)

### Display
- Sidebar sensor cards with live values
- Distance gauge with color-coded proximity warning
- Diagnostics view with detailed sensor history

### Cloud Sync
- Automatic telemetry upload to cloud API
- Historical data storage and retrieval
- Export to CSV/JSON formats

---

## 6. OTA Firmware Updates

### Upload Process
1. Select firmware file (.bin)
2. Enter version number
3. Optional release notes
4. Click UPLOAD
5. Progress bar shows upload percentage

### API Integration
- Uses `POST /firmware` endpoint
- Server validates version uniqueness
- SHA-256 hash computed server-side
- Automatic UI reset after successful upload

---

## 7. Settings & Configuration

### Main Settings
- **Car IP**: ESP32-MCU IP address
- **Camera IP**: ESP32-CAM IP address
- **Cloud API URL**: Cloud backend endpoint
- **Device UID**: Rover identifier
- **OTA Server URL**: Firmware upload endpoint

### PID Tuning (Gyro Straight)
- **Kp**: Proportional gain (0-100)
- **Ki**: Integral gain (0-100)
- **Kd**: Derivative gain (0-100)
- **Bias**: Offset correction (-50 to 50)
- **Toggle**: Enable/disable PID control

### Follow Mode Parameters
- **Kp (Linear)**: Distance proportional gain
- **Ki (Linear)**: Distance integral gain
- **Kd (Linear)**: Distance derivative gain
- **Camera Offset**: Gimbal yaw offset

### Safety Settings
- **Auto-Brake**: Enable/disable automatic braking
- **Brake Threshold**: Distance to trigger stop (10-100cm)

---

## 8. Follow Mode (Car-Follow-Car)

### Autonomous Tracking
- YOLOv8-pose detection for target identification
- PID-based distance control
- Heading control using image yaw error
- 8-state machine:
  - FOLLOWING: Active tracking
  - TURNING: Adjusting heading
  - WAITING: Paused
  - SEARCHING: Looking for target
  - HEAD_ON_HOLD: Direct approach
  - HOLDING: Maintaining position
  - APPROACHING_BLIND: Close approach
  - LOST_TIMEOUT: Target lost

### Gimbal Feed-Forward
- Automatic gimbal compensation during turns
- Predictive pan adjustment based on body rotation

---

## 9. Snapshots & Image Processing

### Capture
- Take snapshot from video feed
- Automatic sensor data overlay
- Save to local storage

### Image Processing
- Auto Correct
- Contrast adjustment
- Denoise
- Bicubic upscaling

### Super Resolution
- 4x upscaling via Hugging Face API
- Fallback to local bicubic + unsharp mask
- Requires HF token for API access

---

## 10. Remote Control

### WebSocket Server
- Listen on configurable port (default 8765)
- Accept commands from remote clients
- Web-based control interface available

### Command Relay
- Forward commands to ESP32
- Status synchronization
- Emergency stop capability

---

## 11. AI Integration

### Ollama Chat
- Local AI model integration
- Natural language data querying
- Sensor data analysis
- Chat interface in diagnostics view

---

## 12. Data Visualization

### Diagnostics View
- Real-time sensor charts
- Historical data graphs
- Custom chart configuration
- Data normalization options

### Export
- CSV format export
- JSON format export
- Date range selection

---

## 13. Keyboard Shortcuts Reference

| Key | Action |
|-----|--------|
| W/S | Forward/Backward |
| A/D | Left/Right |
| Space | Emergency Stop |
| I/K | Gimbal Tilt Up/Down |
| J/L | Gimbal Pan Left/Right |
| C | Center Gimbal |
| Shift/Ctrl | Speed +/- |
| V | Toggle Chassis Follow |

---

## 14. Configuration File

```json
{
  "car_ip": "192.168.1.113",
  "cam_ip": "192.168.1.116",
  "cloud_api_url": "http://192.168.1.77/api/v1",
  "device_uid": "rover-001",
  "motor_speed": 220,
  "auto_brake": true,
  "brake_threshold": 80,
  "hf_token": "",
  "remote_control_port": 8765,
  "cam_quality": 14,
  "ota_server_url": "http://192.168.1.77/api/v1"
}
```

---

## 15. Safety Summary

| Feature | Trigger | Action |
|---------|---------|--------|
| Auto-Brake | Distance < 80cm | Stop motors + warning |
| Speed Limit | Distance < 150cm | Reduce speed proportionally |
| Min Speed | Always | 150 (never lower) |
| Reverse Speed | Always | Full speed (no limit) |
| Connection Loss | WebSocket disconnect | Auto-reconnect |
| Command Timeout | No command for 1s | Emergency stop |

---

## 16. Architecture

### Thread Model
- **Main Thread**: UI updates, event loop
- **Video Thread**: Receive video frames
- **Command Thread**: Send commands to ESP32
- **Telemetry Poller**: Periodic sensor polling
- **Cloud Worker**: Async cloud communication
- **Detection Thread**: Object detection processing

### Data Flow
```
ESP32 → TelemetryPoller → App → UI Display
                            ↓
                         Cloud API
                            ↓
                       Historical Data
```

---

## 17. File Structure

```
robot-desktop-app-tokura/
├── main.py                    # Entry point
├── app.py                     # Main application
├── config.py/json             # Configuration
├── connection_manager.py      # Connection handling
├── esp32_api.py               # ESP32 REST client
├── cloud_api.py               # Cloud API client
├── follow_controller.py       # Follow mode logic
├── views/                     # UI panels
├── widgets/                   # Custom widgets
├── docs/                      # Documentation
└── logs/                      # Session logs
```
