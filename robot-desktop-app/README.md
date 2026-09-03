# Space Rover Desktop Teleoperation Cockpit

A real-time IoT rover teleoperation system featuring a PyQt6 Windows desktop controller, ESP32-based hardware rover, and cloud-backed data pipeline.

---

## 1. Executive Summary

The **Space Rover Desktop Teleoperation Cockpit** is the primary command and control hub used by human operators to remotely pilot the Space Rover in real-time.

The application integrates high-speed manual driving controls, 2-axis precision camera gimbal steering, zero-lag first-person view (FPV) video streaming, and real-time environmental telemetry feeds into a single, cohesive user interface.

---

## 2. System Architecture

```text
                  [ ESP32 Rover ]
                    │       ▲
   UDP (Port 5005)  │       │  UDP (Port 5006)
   Command Out      │       │  Video & Sensors In
                    ▼       │
            ┌──────────────────────────┐
            │   Desktop App            │
            │   (PyQt6 + QThreads)     │
            └───────┬──────────┬───────┘
                    │          │
                    ▼          ▼
             [ Live UI ]   [ HTTP POST ]
                            │
                            ▼
                    ┌──────────────────────────┐
                    │   Cloud Backend          │
                    │   (Raspberry Pi 5)       │
                    └──────────────────────────┘
```

### Thread Architecture

| Thread | Responsibility | Protocol |
|--------|----------------|----------|
| Main Thread | UI updates, event loop | PyQt6 |
| Video Thread | Receive live video feed | UDP Port 5006 |
| Command Thread | Send driving commands | UDP Port 5005 |
| Telemetry Thread | Send sensor data to cloud | HTTP POST |
| Gimbal Thread | Send pan/tilt commands | UDP Port 5005 |
| AI Chat Thread | Gemini API calls | HTTPS |

---

## 3. Communication Protocol

| Direction | Protocol | Port | Purpose |
|-----------|----------|------|---------|
| PC → ESP32 | UDP | 5005 | Low-latency control commands |
| ESP32 → PC | UDP | 5006 | Real-time MJPEG video + sensors |
| PC → Cloud | HTTP | REST API | Historical data storage |

### UDP Commands (Port 5005)

| Command | Format | Description |
|---------|--------|-------------|
| `DRIVE` | `DRIVE:{speed}:{direction}` | Move with PWM speed |
| `STEER` | `STEER:{direction}` | Spin left/right |
| `STOP` | `STOP` | Emergency stop |
| `GIMBAL` | `GIMBAL:{pan}:{tilt}` | Set servo angles |
| `CENTER` | `CENTER` | Reset gimbal to 90°/90° |
| `RESOLUTION` | `RES:{width}:{height}` | Set camera resolution |
| `FLIP` | `FLIP:{h/v}` | Flip camera orientation |
| `SNAPSHOT` | `SNAPSHOT` | Capture frame |
| `OTA` | `OTA:{version}` | Trigger firmware update |

### Telemetry Data (Port 5006)

| Field | Format | Description |
|-------|--------|-------------|
| `temp` | `TEMP:{value}` | Temperature in °C |
| `humi` | `HUMI:{value}` | Humidity in % |
| `gas` | `GAS:{value}` | Gas concentration in ppm |
| `dist` | `DIST:{value}` | Obstacle distance in cm |
| `video` | JPEG bytes | Video frame data |

---

## 4. Cloud API Endpoints

**Base Path:** `/api/v1`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/telemetry` | Send sensor data to cloud |
| `GET` | `/api/v1/rovers/{id}/latest` | Get latest reading (<30ms) |
| `GET` | `/api/v1/rovers/{id}/readings` | Get last N records or time range |
| `GET` | `/api/v1/rovers/{id}/summary` | Get aggregated statistics |
| `GET` | `/api/v1/rovers/{id}/export` | Export CSV or JSON |
| `GET` | `/api/v1/health` | Service health check |

### POST /api/v1/telemetry

**Request:**
```json
{
  "device_uid": "rover-001",
  "recorded_at": "2026-09-03T10:00:00.123Z",
  "temperature_c": 25.4,
  "humidity_pct": 61.2,
  "gas_ppm": 128.0,
  "distance_cm": 34.5,
  "auto_brake": false
}
```

**Response 201:**
```json
{
  "success": true,
  "device_id": 1,
  "recorded_at": "2026-09-03T10:00:00.123Z",
  "duplicate": false
}
```

### GET /api/v1/rovers/{id}/latest

**Response (<30ms target):**
```json
{
  "device_id": 1,
  "recorded_at": "2026-09-03T10:00:00.123Z",
  "age_seconds": 1.4,
  "temperature_c": 25.4,
  "humidity_pct": 61.2,
  "gas_ppm": 128.0,
  "distance_cm": 34.5,
  "auto_brake": false
}
```

### GET /api/v1/rovers/{id}/readings

**Parameters:** `limit`, `start`, `end`, `order`

**Response:**
```json
{
  "device_id": 1,
  "count": 2,
  "readings": [
    { "recorded_at": "...", "temperature_c": 25.3, "humidity_pct": 61.0, "gas_ppm": 127.0, "distance_cm": 40.2, "auto_brake": false }
  ]
}
```

### GET /api/v1/rovers/{id}/summary

**Parameters:** `granularity` (hour/day), `start`, `end`

**Response:**
```json
{
  "device_id": 1,
  "granularity": "day",
  "buckets": [
    {
      "bucket_start": "2026-09-03T00:00:00Z",
      "sample_count": 17280,
      "temperature_c": { "min": 18.2, "avg": 24.1, "max": 31.7 },
      "humidity_pct": { "min": 40.1, "avg": 58.9, "max": 72.4 },
      "gas_ppm": { "min": 95.0, "avg": 130.2, "max": 402.0 },
      "distance_cm": { "min": 4.0, "avg": 88.3, "max": 400.0 },
      "obstacle_events": 12
    }
  ]
}
```

### GET /api/v1/health

```json
{ "status": "ok", "database": "ok", "api": "ok", "uptime_seconds": 84213 }
```

---

## 5. Feature Requirements

### 5.1 Connection Management (Top Bar)

- Independent IP fields for **Rover Chassis (CAR IP)** and **Camera Module (CAM IP)**
- One-click Connect/Disconnect button
- Status indicators: `● CAR ONLINE/OFFLINE`, `● CAM ONLINE/OFFLINE`
- Resolution dropdown: 640x480 / 800x600 / 1280x720
- Flip Horizontal / Flip Vertical toggles
- Snapshot button (saves JPEG with timestamp)
- OTA Update trigger (with confirmation)

### 5.2 FPV Video Viewport (Center)

- Live video feed at 25–30 FPS
- Fixed center crosshair for aiming
- Real-time diagnostics: FPS, Ping, and Obstacle Distance overlay

### 5.3 Rover Teleoperation (Keyboard)

| Key | Action |
|-----|--------|
| `W` | Drive forward |
| `S` | Drive backward |
| `A` | Spin left |
| `D` | Spin right |
| `Space` / Key Release | Emergency stop |
| Speed Slider | PWM power (80–255) |

### 5.4 Camera Gimbal Control (Keyboard)

| Key | Action |
|-----|--------|
| `I` | Tilt up |
| `K` | Tilt down |
| `J` | Pan left |
| `L` | Pan right |
| `C` | Center gimbal (90°, 90°) |

### 5.5 Telemetry & Safety (Sidebar)

- Temperature (°C) with color-coded ranges
- Humidity (% RH)
- Gas Concentration (ppm)
- Obstacle Distance (cm)
- Auto-brake warning banner when obstacle < threshold
- Configurable safety threshold slider (5cm–60cm)
- Enable/disable auto-brake checkbox

### 5.6 AI Chat & Historical Graphs

- Floating 💬 button on right side (overlapping telemetry sidebar)
- When active:
  - Left side: Historical graphs (temperature, humidity, gas)
  - Right side: Gemini AI chat panel
- Chart customization via `/chart` command or Gemini chat
- Drag & drop to rearrange charts

---

## 6. Safety Features

### Rover-Side Failsafe (HW-008)

- ESP32 firmware maintains last-received packet timestamp
- If no command received within 1.0 second → emergency motor stop
- Prevents runaway behavior during network drops

### App-Side Connection Monitoring

- Monitors incoming UDP streams
- If packets stop arriving → UI shows "Disconnected"
- Initiates background reconnection without app restart

### Auto-Brake System

- Ultrasonic sensor detects obstacle distance
- When distance < threshold → warning banner flashes
- Auto-brake engages (if enabled) to stop motors
- Configurable threshold: 5cm to 60cm

---

## 7. OTA Firmware Updates

- Central OTA Hub: `http://rpi5.local/ota/`
- Supports all three microcontrollers
- Version metadata and progress tracking
- Automatic file renaming: `{device}-{version}-{info}-{client}.bin`
- Version verification after upload

### OTA Headers

```
X-OTA-Key: shodai-haru-2026-8-25
Content-Type: multipart/form-data
```

---

## 8. File Structure

```
robot-desktop-app/
├── main.py           # Application entry point
├── app.py            # Main window, UI layout, timers
├── video_feed.py     # Video receiver thread (UDP 5006)
├── command.py        # Command sender (UDP 5005)
├── sensors.py        # Sensor dashboard + charts
├── gimbal.py         # Gimbal control panel
├── ota.py            # Firmware upload
├── ai_chat.py        # Gemini AI chat interface
├── charts.py         # Historical graph widgets
├── cloud_api.py      # Cloud backend API client
├── worker.py         # Background QThread workers
├── config.py         # Config load/save
├── panels.py         # UI component generators
└── config.json       # Saved settings
```

---

## 9. Installation

```bash
pip install PyQt6 requests matplotlib
```

---

## 10. Usage

```bash
python main.py
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `W` | Drive forward |
| `A` | Spin left |
| `S` | Drive backward |
| `D` | Spin right |
| `Space` | Emergency stop |
| `I` | Gimbal tilt up |
| `J` | Gimbal pan left |
| `K` | Gimbal tilt down |
| `L` | Gimbal pan right |
| `C` | Center gimbal |
| `Tab` | Autocomplete in chat |
| `Enter` | Send chat message |
| `Shift+Enter` | New line in chat |

### Chart Commands

```
/chart temperature_c humidity_pct -n -m "Environment"
/chart gas_ppm distance_cm -d
/chart temperature_c -n
```

| Flag | Description |
|------|-------------|
| `-n` | Normalize values (0–1 range) |
| `-d` | Separate into individual charts |
| `-m {name}` | Name the chart |

---

## 11. Configuration

### Config File (config.json)

```json
{
  "car_ip": "192.168.1.100",
  "cam_ip": "192.168.1.101",
  "cloud_api_url": "http://rpi5.local/api/v1",
  "device_uid": "rover-001",
  "gemini_api_key": "",
  "center_charts": {},
  "custom_charts": {},
  "custom_charts_normalize": {}
}
```

---

## 12. Development Checklist

- [ ] **Phase 1:** UI wireframes & layout mockups
- [ ] **Phase 2:** Keyboard state machine mapping
- [ ] **Phase 3:** Multi-threaded architecture diagram
- [ ] **Phase 4:** Desktop application prototype
- [ ] **Phase 5:** Cloud API integration
- [ ] **Phase 6:** Safety testing (HW-008 compliance)
- [ ] **Phase 7:** End-to-end integration testing

---

## 13. User Stories

| Persona | Need | Feature |
|---------|------|---------|
| Rover Pilot | Intuitive game-like driving | WASD controls |
| Rover Pilot | Inspect surroundings without turning | IJKL gimbal |
| Rover Pilot | Avoid obstacles due to lag | Low-latency FPV video |
| Safety Officer | Prevent collisions | Obstacle alarm + auto-brake |
| Safety Officer | Monitor environment | Real-time telemetry |
| Field Technician | Record discoveries | Snapshot with timestamp |
| Field Technician | Upgrade firmware wirelessly | OTA update |
