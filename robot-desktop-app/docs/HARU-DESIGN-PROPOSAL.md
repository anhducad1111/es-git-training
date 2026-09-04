# Space Rover Desktop Teleoperation Cockpit
## Phase 1 — UI Design & Plan Proposal

**Document version:** v1.0
**Date:** 2026-09-03
**Author:** Haru Sakihara (Python Desktop App Engineer Intern)
**Status:** Awaiting mentor review. No implementation code has been written.

---

## 1. Purpose

This is the Phase 1 deliverable requested in PRD §6. It contains:

1. UI wireframes and screen layout design
2. Keyboard event and state machine mapping
3. Thread architecture diagram
4. Implementation plan

**Note:** Cloud API integration details will be added in Phase 3 after receiving the official API documentation from Duke.

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

> **Note:** WebSocket addresses will be provided by supervisor during implementation.

---

## 3. UI Wireframes

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
│ │ 10:00:01 [CONNECTED] WebSocket connected to 192.168.1.100 (ESP32-MCU)      │ │
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

## 4. Keyboard State Machine

### 4.1 Drive Control

```
   [IDLE] ──────────────────────────────────────►
      │
      │ Key Press (W/A/S/D)
      ▼
   [DRIVING] ───────────────────────────────────►
      │
      │ Key Release / Space
      ▼
   [STOPPING] ──────────────────────────────────►
      │
      │ Send STOP command
      ▼
   [IDLE]
```

### 4.2 Gimbal Control

```
   [IDLE] ──────────────────────────────────────►
      │
      │ Key Press (I/J/K/L)
      ▼
   [GIMBAL MOVING] ────────────────────────────►
      │
      │ Key Release
      ▼
   [GIMBAL HOLD] ───────────────────────────────►
      │
      │ C Key
      ▼
   [GIMBAL CENTERING] ─────────────────────────►
      │
      │ Send center command (90°, 90°)
      ▼
   [IDLE]
```

### 4.3 Key Mapping

| Key | Action | WebSocket Command (JSON) |
|-----|--------|--------------------------|
| `W` | Drive forward | `{"type":"drive","speed":180,"direction":"forward"}` |
| `S` | Drive backward | `{"type":"drive","speed":180,"direction":"backward"}` |
| `A` | Spin left | `{"type":"steer","direction":"left"}` |
| `D` | Spin right | `{"type":"steer","direction":"right"}` |
| `Space` | Emergency stop | `{"type":"stop"}` |
| `I` | Tilt up | `{"type":"gimbal","pan":pan,"tilt":tilt+5}` |
| `K` | Tilt down | `{"type":"gimbal","pan":pan,"tilt":tilt-5}` |
| `J` | Pan left | `{"type":"gimbal","pan":pan-5,"tilt":tilt}` |
| `L` | Pan right | `{"type":"gimbal","pan":pan+5,"tilt":tilt}` |
| `C` | Center gimbal | `{"type":"gimbal","center":true}` |
| `Tab` | Autocomplete in chat | — |
| `Enter` | Send chat message | — |
| `Shift+Enter` | New line in chat | — |

---

## 5. Thread Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     THREAD ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────┐                                        │
│   │   MAIN THREAD       │ ◄── PyQt6 Event Loop                  │
│   │   (UI Updates)      │                                        │
│   └──────────┬──────────┘                                        │
│              │                                                   │
│   ┌──────────┴──────────┐                                        │
│   │                     │                                        │
│   ▼                     ▼                                        │
│   │                                                                 │
│   ├─────────────────────┼─────────────────────────────────────────┤
│   │                     │                                         │
│   ▼                     ▼                                         │
│                                                                 │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ │ VIDEO       │  │ COMMAND     │  │ TELEMETRY   │  │ AI CHAT     │
│ │ THREAD      │  │ THREAD      │  │ THREAD      │  │ THREAD      │
│ │             │  │             │  │             │  │             │
│ │ WebSocket   │  │ WebSocket   │  │ HTTP POST   │  │ HTTPS       │
│ │ (ESP32-CAM) │  │ (ESP32-MCU) │  │ (Cloud API) │  │ (Gemini)    │
│ └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
│        │                │                │                │
│        ▼                ▼                ▼                ▼
│   ┌─────────────────────────────────────────────────────────────┐
│   │                    ESP32 ROVER                               │
│   │  ┌─────────────┐  ┌─────────────┐                          │
│   │  │ ESP32-CAM   │  │ ESP32-MCU   │                          │
│   │  │ (Camera)    │  │ (Sensors,   │                          │
│   │  │ WS: Video   │  │  Motors,    │                          │
│   │  │             │  │  Gimbal)    │                          │
│   │  │             │  │ WS: Cmd/Tlm │                          │
│   │  └─────────────┘  └─────────────┘                          │
│   └─────────────────────────────────────────────────────────────┘
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Thread | Responsibility | Protocol |
|--------|----------------|----------|
| Main Thread | UI updates, event loop | PyQt6 |
| Video Thread | Receive video frames from ESP32-CAM | WebSocket (binary) |
| Command Thread | Send commands to ESP32-MCU | WebSocket (JSON) |
| Telemetry Thread | POST sensor data to cloud | HTTP REST |
| AI Chat Thread | Gemini API calls | HTTPS |

---

## 6. Communication Protocol

| Direction | Protocol | Purpose |
|-----------|----------|---------|
| PC → ESP32-CAM | WebSocket | Receive video stream (binary JPEG) |
| PC ↔ ESP32-MCU | WebSocket | Send commands (JSON), receive telemetry (JSON) |
| PC → Cloud | HTTP REST | Store/retrieve historical data |

### 6.1 WebSocket Commands (PC → ESP32-MCU, JSON)

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

### 6.2 Telemetry Data (ESP32-MCU → PC, JSON)

ESP32-MCU sends sensor data via the same WebSocket connection:

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

### 6.3 Video Stream (ESP32-CAM → PC)

Binary JPEG frames sent over WebSocket:
- Each message is a complete JPEG frame
- Frame rate: 25-30 FPS at 640x480
- No text encoding needed (raw binary)

---

## 7. Safety Features

### 7.1 Rover-Side Failsafe (HW-008)

- ESP32 firmware maintains last-received packet timestamp
- If no command received within 1.0 second → emergency motor stop
- Prevents runaway behavior during network drops

### 7.2 App-Side Connection Monitoring

- Monitors incoming WebSocket streams
- If packets stop arriving → UI shows "Disconnected"
- Initiates background reconnection without app restart

### 7.3 Auto-Brake System

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

### OTA Headers

```
X-OTA-Key: shodai-haru-2026-8-25
Content-Type: multipart/form-data
```

---

## 9. Color Scheme

| Element | Color Name | Hex Code |
|---------|------------|----------|
| Background | Charcoal | `#0b1326` |
| Surface | Dark Navy | `#131b2e` |
| Surface Container | Navy | `#171f33` |
| Surface Container Low | Deep Navy | `#0f172a` |
| Surface Container High | Slate | `#1e293b` |
| Surface Container Highest | Blue Slate | `#28344e` |
| Primary | Soft Blue | `#b4c5ff` |
| Primary Container | Indigo | `#2e3a5f` |
| Secondary | Light Gray | `#c4c7d4` |
| Tertiary | Warm Coral | `#ffb596` |
| Outline | Dim Gray | `#5a5f72` |
| Outline Variant | Muted Gray | `#3d4257` |

**Font:** IBM Plex Sans, IBM Plex Mono

---

## 10. File Structure

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
    └── README.md
```

---

## 11. Installation

```bash
pip install PyQt6 requests matplotlib google-genai websocket-client
```

---

## 12. Usage

```bash
python main.py
```

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
| Data Analyst | Visualize sensor trends | Historical charts |
| Data Analyst | Query data with natural language | Gemini AI chat |

---

## 14. Implementation Plan

| Phase | Content | Depends on |
|---|---|---|
| 1 | This proposal document, submitted for review | — |
| 2 | Mentor review, receipt of official API documentation | Approval |
| 3 | Project setup, config system, main window skeleton | Phase 2 |
| 4 | Video feed thread and viewport widget | Phase 3 |
| 5 | Keyboard input handling and command sender | Phase 3 |
| 6 | Telemetry sidebar and sensor display | Phase 4, 5 |
| 7 | Gimbal control panel | Phase 5 |
| 8 | Cloud API integration | Phase 6 |
| 9 | AI chat and historical graphs | Phase 8 |
| 10 | OTA firmware upload | Phase 8 |
| 11 | Safety features (auto-brake, alarms) | Phase 6 |
| 12 | Integration testing and bug fixes | Phases 4-11 |

---

## 15. Development Checklist

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ⏳ In Progress | Design proposal (this document) |
| 2 | ⏸️ Pending | Mentor review |
| 3 | ⏸️ Pending | Project skeleton |
| 4 | ⏸️ Pending | Video feed |
| 5 | ⏸️ Pending | Keyboard controls |
| 6 | ⏸️ Pending | Telemetry display |
| 7 | ⏸️ Pending | Gimbal control |
| 8 | ⏸️ Pending | Cloud integration |
| 9 | ⏸️ Pending | AI chat |
| 10 | ⏸️ Pending | OTA updates |
| 11 | ⏸️ Pending | Safety features |
| 12 | ⏸️ Pending | Testing & bug fixes |
