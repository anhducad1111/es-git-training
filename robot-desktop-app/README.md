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
            │   Desktop Receiver       │
            │   (Thread A - Realtime)  │
            └───────┬──────────┬───────┘
                    │          │
                    ▼          ▼
             [ Live UI ]   [ Local Queue (FIFO) ]
                            │
                            │ Asynchronous Background Worker
                            ▼
                    ┌──────────────────────────┐
                    │   Cloud Uploader         │
                    │   (Thread B - Async)     │
                    └───────┬──────────────────┘
                            │ HTTPS (REST API)
                            ▼
                     [ Cloud Database ]
```

### Thread Architecture

| Thread | Responsibility | Protocol |
|--------|----------------|----------|
| Main Thread | UI updates, event loop | PyQt6 |
| Video Thread | Receive live video feed | UDP Port 5006 |
| Command Thread | Send driving commands | UDP Port 5005 |
| Telemetry Thread | Poll sensor data | HTTP GET |
| Gimbal Thread | Send pan/tilt commands | UDP Port 5005 |
| AI Chat Thread | Gemini API calls | HTTPS |

---

## 3. Hardware Microcontroller Architecture

| Microcontroller | Role | Description |
|-----------------|------|-------------|
| `esp32_car` | Motion Control | Manages rover motion and motor driving |
| `esp32_cam` | Video Feed | Handles FPV video feed capture and streaming |
| `esp32_monitor` | Sensors | Base station sensor node for environment data |

---

## 4. Communication Protocol

| Direction | Protocol | Port | Purpose |
|-----------|----------|------|---------|
| PC → ESP32 | UDP | 5005 | Low-latency control commands |
| ESP32 → PC | UDP | 5006 | Real-time MJPEG video + sensors |
| PC → Cloud | HTTPS | REST API | Historical data storage |

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
- Real-time diagnostics: FPS and Ping display

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
- Air Quality / Gas (ppm)
- Obstacle Distance (cm)
- Auto-brake warning banner when obstacle < threshold
- Configurable safety threshold slider (5cm–60cm)
- Enable/disable auto-brake checkbox

### 5.6 AI Chat & Historical Graphs

- Floating 💬 button on right side (overlapping telemetry sidebar)
- When active:
  - Left side: Historical graphs (temperature, humidity, air quality)
  - Right side: Gemini AI chat panel
- Chart customization via `/chart` command or Gemini chat
- Drag & drop to rearrange charts

---

## 6. Screen Layout

### Main View (Default)

```
┌─────────────────────────────────────────────────────────────────┐
│                         TOP BAR                                 │
├─────────────────────────────────────┬───────────────────────────┤
│                                     │   TELEMETRY SIDEBAR       │
│         VIDEO VIEWPORT              │   ┌─────────────────┐    │
│         (Live Camera Feed)          │   │ Temperature     │    │
│                                     │   │ Humidity        │    │
│              ╋                      │   │ Air Quality     │    │
│         (Crosshair)                 │   │ Obstacle        │    │
│                                     │   │ Safety Alarm    │    │
│    FPS: 30.0 | Ping: 5ms           │   │     ┌───┐       │    │
│                                     │   │     │💬 │       │    │
├─────────────────────────────────────┤   │     └───┘       │    │
│  SPEED: [===========] 180/255      │   │ Gimbal Control  │    │
│  KEYS: WASD=Drive IJKL=Gimbal      │   └─────────────────┘    │
└─────────────────────────────────────┴───────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  [Log] Click to expand                                          │
└─────────────────────────────────────────────────────────────────┘
```

### AI Chat View (💬 Active)

```
┌─────────────────────────────────────────────────────────────────┐
│                         TOP BAR                                 │
├─────────────────────────────────────┬───────────────────────────┤
│                                     │   AI CHAT PANEL           │
│      HISTORICAL GRAPHS              │   ┌─────────────────┐    │
│   ┌─────────────────────────────┐   │   │ 💬 Gemini Chat  │    │
│   │ Temperature & Humidity      │   │   │                 │    │
│   │ ┌───────────────────────┐   │   │   │ You: Show temp  │    │
│   │ │ 30°┤    ╭─╮           │   │   │   │ Gemini: Chart   │    │
│   │ │    │  ╭─╯ ╰─╮  ╭──╮  │   │   │   │ created...      │    │
│   │ │ 25°┤─╯      ╰─╯  ╰──│   │   │   │                 │    │
│   │ └───────────────────────┘   │   │   │ [Input] [Send]  │    │
│   └─────────────────────────────┘   │   │     ┌───┐       │    │
│   ┌─────────────────────────────┐   │   │     │✖  │       │    │
│   │ Air Quality                 │   │   │     └───┘       │    │
│   │ ┌───────────────────────┐   │   │   │ Gimbal Control  │    │
│   │ │ 500┤    ╭──╮          │   │   │   └─────────────────┘    │
│   │ │    │  ╭─╯  ╰─╮  ╭───╮│   │   │                           │
│   │ │ 400┤─╯       ╰─╯   ╰│   │   │                           │
│   │ └───────────────────────┘   │   │                           │
│   └─────────────────────────────┘   │                           │
│   [+ Add Chart] [Reset Layout]      │                           │
├─────────────────────────────────────┤                           │
│  SPEED: [===========] 180/255      │                           │
│  KEYS: WASD=Drive IJKL=Gimbal      │                           │
└─────────────────────────────────────┴───────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  [Log] Click to expand                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Safety Features

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

## 8. OTA Firmware Updates

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

## 9. Sensor Data Format

### GET Response

```json
{
  "success": true,
  "server_time": "2026-09-03 12:00:00",
  "latest": {
    "temperature": {"data": "28.5", "reading_time": "..."},
    "humidity": {"data": "65", "reading_time": "..."},
    "co2": {"data": "450", "reading_time": "..."}
  },
  "history": {
    "temperature": [{"data": "28.5", "reading_time": "..."}, ...]
  }
}
```

### Sensor Labels

| Group | Sensors |
|-------|---------|
| Air Quality | `co2`, `pm1.0`, `pm2.5`, `pm10` |
| Environment | `temperature`, `humidity`, `pressure` |
| Other | `gas`, `battery` |

---

## 10. File Structure

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
├── worker.py         # Background QThread workers
├── config.py         # Config load/save
├── panels.py         # UI component generators
└── config.json       # Saved settings
```

---

## 11. Installation

```bash
pip install PyQt6 requests matplotlib
```

---

## 12. Usage

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
/chart temperature humidity -n -m "Environment"
/chart co2 gas -d
/chart pm -n
```

| Flag | Description |
|------|-------------|
| `-n` | Normalize values (0–1 range) |
| `-d` | Separate into individual charts |
| `-m {name}` | Name the chart |

---

## 13. Configuration

### Config File (config.json)

```json
{
  "car_ip": "192.168.1.100",
  "cam_ip": "192.168.1.101",
  "api_url": "https://example.com/api/get-data.php",
  "gemini_api_key": "",
  "center_charts": {},
  "custom_charts": {},
  "custom_charts_normalize": {}
}
```

---

## 14. Development Checklist

- [ ] **Phase 1:** UI wireframes & layout mockups
- [ ] **Phase 2:** Keyboard state machine mapping
- [ ] **Phase 3:** Multi-threaded architecture diagram
- [ ] **Phase 4:** Desktop application prototype
- [ ] **Phase 5:** API integration with ESP32
- [ ] **Phase 6:** Safety testing (HW-008 compliance)
- [ ] **Phase 7:** End-to-end integration testing

---

## 15. User Stories

| Persona | Need | Feature |
|---------|------|---------|
| Rover Pilot | Intuitive game-like driving | WASD controls |
| Rover Pilot | Inspect surroundings without turning | IJKL gimbal |
| Rover Pilot | Avoid obstacles due to lag | Low-latency FPV video |
| Safety Officer | Prevent collisions | Obstacle alarm + auto-brake |
| Field Technician | Record discoveries | Snapshot with timestamp |
| Field Technician | Upgrade firmware wirelessly | OTA update |
