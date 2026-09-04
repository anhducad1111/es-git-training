# Space Rover Desktop Teleoperation Cockpit

A real-time IoT rover teleoperation system featuring a PyQt6 Windows desktop controller, ESP32-based hardware rover, and cloud-backed data pipeline.

---

## docs/ — Design & Specification Documents

The `docs/` folder contains all planning and design documents created **before writing code**. These documents define the application's architecture, UI layout, and implementation plan.

```
docs/
├── HARU-PRD-DESIGN-PROPOSAL.md   # Phase 1 design proposal (submitted to Duke for approval)
├── wireframe.md                   # UI wireframes, component descriptions, architecture diagrams
└── README.md                      # Documentation index and file reference
```

| File | Purpose | When to Use |
|------|---------|-------------|
| `HARU-PRD-DESIGN-PROPOSAL.md` | Complete design proposal with wireframes, protocols, implementation plan | Submit to Duke for Phase 1 approval |
| `wireframe.md` | Detailed UI specification with visual wireframes and component tables | Reference during coding |
| `README.md` | Documentation index explaining each file's purpose | Quick reference for docs folder |

**Workflow:**
1. Read `HARU-PRD-DESIGN-PROPOSAL.md` → Submit to Duke for review
2. Duke approves → Official API docs unlocked
3. Use `wireframe.md` → Reference during implementation
4. Code begins → Follow §14 Implementation Plan in proposal

---

## 1. Executive Summary

The **Space Rover Desktop Teleoperation Cockpit** is the primary command and control hub used by human operators to remotely pilot the Space Rover in real-time.

The application integrates high-speed manual driving controls, 2-axis precision camera gimbal steering, zero-lag first-person view (FPV) video streaming, and real-time environmental telemetry feeds into a single, cohesive user interface.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PyQt6 Desktop App                         │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
  WebSocket         WebSocket            HTTP REST
  (Video)           (Commands/            (Cloud API)
                     Telemetry)
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ ESP32-CAM   │   │ ESP32-MCU   │   │  Cloud API  │
│ (Camera)    │   │ (Sensors,   │   │   (RPi5)    │
│ Binary JPEG │   │  Motors,    │   │ Historical  │
│ frames      │   │  Gimbal)    │   │ Data        │
│ ws://?:?/ws │   │ ws://?:?/ws │   │ HTTP REST   │
└─────────────┘   └─────────────┘   └─────────────┘
```

### Thread Architecture

| Thread | Responsibility | Protocol |
|--------|----------------|----------|
| Main Thread | UI updates, event loop | PyQt6 |
| Video Thread | Receive video frames from ESP32-CAM | WebSocket (binary) |
| Command Thread | Send commands to ESP32-MCU | WebSocket (JSON) |
| Telemetry Thread | POST sensor data to cloud | HTTP REST |
| Gimbal Thread | Send pan/tilt commands | WebSocket (JSON) |
| AI Chat Thread | Gemini API calls | HTTPS |

---

## 3. UI Layout

### 3.1 Main View (Default)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ HEADER: 🏭 Rover Teleop Cockpit v2.4.0  │ Main View │ Gimbal │ Diag │ Subsys   │
│         Rover IP: [192.168.1.100]  Cam IP: [192.168.1.101]  ● Rover ● Cam  [⚡]│
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┬──────────────────────────────┐
│                                                  │  ┌────────────────────────┐ │
│                                                  │  │ Telemetry Sensors      │ │
│                                                  │  │ Link: 98% (Optimal)   │ │
│                                                  │  │              [E-STOP]  │ │
│                                                  │  ├────────────────────────┤ │
│                                                  │  │ 🌡 Chassis Core Temp   │ │
│                                                  │  │ ████████░░░░ 28.5°C    │ │
│                                                  │  ├────────────────────────┤ │
│                                                  │  │ 💧 Ambient Humidity    │ │
│                                                  │  │ ████████████░ 65.0%    │ │
│             CENTER VIDEO VIEWPORT                 │  ├────────────────────────┤ │
│                                                  │  │ 🌫 Air Purity Metric   │ │
│   ┌─────────────────────────────────────────┐    │  │ ██████░░░░░ 450 PPM    │ │
│   │    🟢 30.0 FPS │ 5 ms │ 📏 45 cm │ ... │    │  ├────────────────────────┤ │
│   │─────────────────────────────────────────│    │  │ 📏 Obstacle Distance   │ │
│   │                                         │    │  │ ██████░░░░░ 45 cm      │ │
│   │              ╋ CROSSHAIR               │    │  ├────────────────────────┤ │
│   │                                         │    │  │ SUBSYSTEM HEALTH       │ │
│   │                                         │    │  │ ESP32 Main MCU    OK   │ │
│   │                                         │    │  │ Motor Drivers     OK   │ │
│   └─────────────────────────────────────────┘    │  │ Pan/Tilt Servos   OK   │ │
│                                                  │  │ Battery Level  12.4V   │ │
│   ┌─────────────────────────────────────┐        │  ├────────────────────────┤ │
│   │  📷 640x480 (30 FPS) ▼             │        │  │ [📷 Take Snapshot]     │ │
│   └─────────────────────────────────────┘        │  │ [🔧 System Diagnostics]│ │
│                                                  │  │ [⚙ Device Configuration]│
├──────────────────────────────────────────────────┤  └────────────────────────┘ │
│ BOTTOM CONTROLS                                                         │
│ ┌──────────────────────┐ ┌──────────────────┐ ┌────────────────────┐ ┌────────┐ │
│ │ Motor Speed          │ │ Auto-Brake [ON]  │ │ Gimbal: Pan 90°   │ │ W/S    │ │
│ │ 180 (70%) [====]     │ │ Threshold: 30cm  │ │        Tilt 90°   │ │ A/D    │ │
│ │                      │ │ [====]           │ │ [Center]           │ │[STOP]  │ │
│ └──────────────────────┘ └──────────────────┘ └────────────────────┘ └────────┘ │
├──────────────────────────────────────────────────────────────────────────────────┤
│ [LOG] Click to expand/collapse • 4 Events                         115200 Baud  │
│ ┌──────────────────────────────────────────────────────────────────────────────┐ │
│ │ 10:00:01 [CONNECTED] WebSocket connected to 192.168.1.100 (ESP32-MCU)             │ │
│ │ 10:00:02 [VIDEO]      Stream active at 640x480 @ 30 FPS                    │ │
│ │ 10:00:05 [TELEMETRY]  Chassis Temp 28.5°C, Dist 45cm, Humidity 65%         │ │
│ │ 10:00:08 [SAFETY]     Auto-brake threshold set to 30 cm                    │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
                              ┌─────┐
                              │ 💬  │ ← FLOATING BUTTON (bottom-right)
                              └─────┘
```

### 3.2 Diagnostics View (💬 Active)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ HEADER: 🏭 Rover Teleop Cockpit v2.4.0  │ Main View │ Gimbal │ Diag │ Subsys   │
│         Rover IP: [192.168.1.100]  Cam IP: [192.168.1.101]  ● Rover ● Cam  [⚡]│
└─────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┬────────────────────────────┐
│ 📊 Historical Sensor Analytics                     │  Gemini 3.5 Sensor Analyst │
│   Window: 15m Telemetry Deck                       │  ┌──────────────────────┐ │
│   Auto-Refresh (5s) [ON]  [+ Add Chart] [Reset]   │  │ ● gemini-3.5 active  │ │
├────────────────────────────────────────────────────┤  ├──────────────────────┤ │
│ 💡 Tip: /chart in Gemini chat to customize plots   │  │ ℹ TELEMETRY CONTEXT  │ │
│    SYNC_RATE: 100ms • BUFFER: 900pts               │  │ Temp:28.5°C Air:450  │ │
├────────────────────────────────────────────────────┤  │ Dist:45cm Batt:94%   │ │
│                                                    │  ├──────────────────────┤ │
│ 🌡 Temperature & Humidity (Dual-Axis)  ● LIVE      │  │ You:                 │ │
│   Temp: 28.5°C  Humidity: 58.2%RH                 │  │ Show me temp and     │ │
│   ┌──────────────────────────────────────────┐    │  │ humidity together... │ │
│   │ 35°┤     ╭────╮                         │    │  ├──────────────────────┤ │
│   │    │   ╭─╯    ╰──╮    ╭────╮           │    │  │ Gemini 3.5:          │ │
│   │ 30°┤──╯          ╰──╯    ╰──           │    │  │ I have analyzed the  │ │
│   │    │  ~~~~ Temp (orange) ~~~~           │    │  │ last 15 minutes of   │ │
│   │ 25°┤  ---- Humidity (blue) ----         │    │  │ telemetry. Temp is   │ │
│   │    └────────────────────────────────────┘    │  │ stable at 28.5°C...  │ │
│   │ 12:00    12:03    12:06    12:12  12:15 LIVE│  │                      │ │
│   └──────────────────────────────────────────┘    │  │ ┌──────────────────┐ │ │
│                                                    │  │ │ Tool Call:       │ │ │
│ ┌──────────────────────────┬─────────────────────┐ │  │ │ create_custom_   │ │ │
│ │ 🌫 Air Quality &         │ 📏 Obstacle Proximity│ │  │ │ charts [0.12s]   │ │ │
│ │    Particulate           │    & Sonar           │ │  │ │ {sensors:[temp,  │ │ │
│ │   CO2: 450 ppm           │   ● CLEAR > 30cm     │ │  │ │  humidity]}      │ │ │
│ │   PM2.5: 12 µg/m³        │   Sonar: 45 cm       │ │  │ └──────────────────┘ │ │
│ │ ┌──────────────────┐     │ ┌──────────────────┐ │ │  ├──────────────────────┤ │
│ │ │  ~~~CO2(emerald)~│     │ │  █ █ █ █ █ █ █  │ │ │  │ 💊 /chart co2 temp  │ │
│ │ │  - -PM2.5(blue) -│     │ │  █ █ █ █ █ █ █  │ │ │  │    /filter anomalies │ │
│ │ └──────────────────┘     │ │  █ █ █ █ █ █ █  │ │ │  │    /export csv 15m   │ │
│ │ CO2:Nominal <600          │ │  NOW ← threshold │ │ │  ├──────────────────────┤ │
│ │ PM2.5:Clean <25  Gas:Clean│ │ Safety:30cm OPTIMAL│ │  │ [/chart co2 temp -n] │ │
│ └──────────────────────────┴─────────────────────┘ │  │               [Send] │ │
└────────────────────────────────────────────────────┘  └──────────────────────┘ │
                                                               ┌──────────────┐ │
                                                               │ ❖ close      │ │
                                                               └──────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
[LOG] 12:14:11 Gemini API tool response OK | 12:12:00 Radio Ping: 18ms   expand ▼
                              ┌─────┐
                              │ ✖   │ ← FLOATING BUTTON (purple, bottom-right)
                              └─────┘
```

### 3.3 Video Overlay Status Bar (Top Center of Video)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│   🟢 30.0 FPS   │   5 ms   │  📏 45 cm   │  🌡 28.5 °C   │  💧 65.0 %      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

| Indicator | Icon | Color Logic | Description |
|-----------|------|-------------|-------------|
| `🟢 30.0 FPS` | — | 🟢 ≥25, 🟡 15-24, 🔴 <15 | Live frame rate |
| `5 ms` | network_ping | White | Network ping to rover |
| `📏 45 cm` | radar | 🟢 >30, 🟡 15-30, 🔴 <15 | Obstacle distance |
| `🌡 28.5 °C` | device_thermostat | Orange | Temperature |
| `💧 65.0 %` | water_drop | Blue | Humidity |

---

## 4. Communication Protocol

| Direction | Protocol | Purpose |
|-----------|----------|---------|
| PC → ESP32-CAM | WebSocket | Receive video stream (binary JPEG) |
| PC → ESP32-MCU | WebSocket | Send commands (JSON), receive telemetry (JSON) |
| PC → Cloud | HTTP REST | Store/retrieve historical data |

### WebSocket Commands (PC → ESP32-MCU, JSON)

**Drive Commands:**
```json
{"type": "drive", "speed": 180, "direction": "forward"}
{"type": "drive", "speed": 180, "direction": "backward"}
{"type": "steer", "direction": "left"}
{"type": "steer", "direction": "right"}
{"type": "stop"}
```

**Gimbal Commands:**
```json
{"type": "gimbal", "pan": 90, "tilt": 90}
{"type": "gimbal", "center": true}
```

**Camera Commands:**
```json
{"type": "resolution", "width": 640, "height": 480}
{"type": "flip", "axis": "horizontal"}
{"type": "flip", "axis": "vertical"}
{"type": "snapshot"}
```

### Telemetry Data (ESP32-MCU → PC, JSON)

```json
{
  "type": "telemetry",
  "temperature": 28.5,
  "humidity": 65.0,
  "air_purity": 450,
  "distance": 45.0
}
```

| Field | Unit | Description |
|-------|------|-------------|
| `temperature` | °C | Ambient temperature |
| `humidity` | % | Relative humidity |
| `air_purity` | PPM | Gas/smoke concentration (MQ-2) |
| `distance` | cm | Obstacle distance (HC-SR04) |

### Video Stream (ESP32-CAM → PC)

Binary JPEG frames sent over WebSocket:
- Each message is a complete JPEG frame
- Frame rate: 25-30 FPS at 640x480
- No text encoding needed (raw binary)

---

## 5. Cloud API Endpoints

**Base Path:** `/api/v1`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/telemetry` | Send sensor data to cloud |
| `GET` | `/api/v1/rovers/{id}/latest` | Get latest reading (<30ms) |
| `GET` | `/api/v1/rovers/{id}/readings` | Get last N records or time range |
| `GET` | `/api/v1/rovers/{id}/summary` | Get aggregated statistics |
| `GET` | `/api/v1/health` | Service health check |

---

## 6. Feature Requirements

### 6.1 Header Bar

- App title with version number
- Navigation tabs: Main View / Gimbal / Diagnostics / Subsystems
- Rover IP and Camera IP displays
- Online status indicators (Rover: Online, Cam: Online)
- Flip Orientation button
- OTA Update button
- Connection toggle button

### 6.2 FPV Video Viewport (Main View)

- Live video feed at 25–30 FPS
- Fixed center crosshair for aiming
- Real-time diagnostics overlay: FPS, Ping, Distance, Temp, Humidity
- Resolution dropdown: 640x480 / 1280x720 / 320x240

### 6.3 Telemetry Sidebar

- Sensor cards: Chassis Core Temp, Ambient Humidity, Air Purity, Obstacle Distance
- Progress bars with color coding
- Subsystem Health: ESP32, Motor Drivers, Servos, Battery
- E-STOP button
- Take Snapshot, System Diagnostics, Device Configuration buttons

### 6.4 Bottom Controls

- Motor Speed slider (0-255 PWM, displayed as %)
- Auto-Brake toggle with threshold slider (10-100cm)
- Gimbal controls: Pan slider, Tilt slider, Center button
- Keybinds display: W/S=Drive, A/D=Turn, I/J/K/L=Gimbal
- Emergency Stop button (Space)

### 6.5 Diagnostics View (💬 Active)

- Historical Sensor Analytics with 3 charts:
  - Temperature & Humidity dual-axis line chart
  - Air Quality & Particulate (CO2 + PM2.5) multi-trend
  - Obstacle Proximity & Sonar bar chart timeline
- Gemini 3.5 Sensor Analyst chat panel
- Telemetry context pill
- Tool execution cards
- Suggestion pills (/chart, /filter, /export)

### 6.6 Log Panel

- Collapsible at bottom
- Colored log entries with timestamps
- Categories: CONNECTED, VIDEO, TELEMETRY, SAFETY, ERROR

---

## 7. Keyboard Shortcuts

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

---

## 8. Chart Commands

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

## 9. Safety Features

### Rover-Side Failsafe (HW-008)

- ESP32 firmware maintains last-received packet timestamp
- If no command received within 1.0 second → emergency motor stop
- Prevents runaway behavior during network drops

### App-Side Connection Monitoring

- Monitors incoming WebSocket streams
- If packets stop arriving → UI shows "Disconnected"
- Initiates background reconnection without app restart

### Auto-Brake System

- Ultrasonic sensor detects obstacle distance
- When distance < threshold → warning banner flashes
- Auto-brake engages (if enabled) to stop motors
- Configurable threshold: 10cm to 100cm

---

## 10. OTA Firmware Updates

- Central OTA Hub: `http://rpi5.local/ota/`
- Supports all three microcontrollers
- Version metadata and progress tracking
- Automatic file renaming: `{device}-{version}-{info}-{client}.bin`

### OTA Headers

```
X-OTA-Key: shodai-haru-2026-8-25
Content-Type: multipart/form-data
```

---

## 11. File Structure

```
robot-desktop-app/
├── main.py           # Application entry point
├── app.py            # Main window, UI layout, timers
├── video_feed.py     # Video receiver thread (WebSocket)
├── command.py        # Command sender (WebSocket)
├── sensors.py        # Sensor dashboard + charts
├── gimbal.py         # Gimbal control panel
├── ota.py            # Firmware upload
├── ai_chat.py        # Gemini AI chat interface
├── charts.py         # Historical graph widgets
├── cloud_api.py      # Cloud backend API client
├── worker.py         # Background QThread workers
├── config.py         # Config load/save
├── panels.py         # UI component generators
├── config.json       # Saved settings
└── docs/
    ├── HARU-PRD-DESIGN-PROPOSAL.md
    ├── wireframe.md
    └── ...
```

---

## 12. Configuration

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

## 13. Installation

```bash
pip install PyQt6 requests matplotlib google-genai
```

---

## 14. Usage

```bash
python main.py
```

---

## 15. User Stories

| Persona | Need | Feature |
|---------|------|---------|
| Rover Pilot | Intuitive game-like driving | WASD controls |
| Rover Pilot | Inspect surroundings without turning | IJKL gimbal |
| Rover Pilot | Avoid obstacles due to lag | Low-latency FPV video |
| Safety Officer | Prevent collisions | Obstacle alarm + auto-brake |
| Safety Officer | Monitor environment | Real-time telemetry |
| Field Technician | Record discoveries | Snapshot with timestamp |
| Field Technician | Upgrade firmware wirelessly | OTA update |
| Data Analyst | Visualize sensor trends | Historical charts |
| Data Analyst | Query data with natural language | Gemini AI chat |

---

## 16. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyQt6 | 6.x | Desktop GUI framework |
| requests | 2.x | HTTP requests |
| matplotlib | 3.x | Chart rendering |
| google-genai | 0.3+ | Gemini AI integration |
| websocket-client | 1.x | WebSocket communication |
| json | stdlib | Configuration persistence |
