# Space Rover Desktop Teleoperation Cockpit - UI Wireframe

## Screen Layout (1920x1080)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TOP BAR (Connection & Quick Controls)              │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐ ┌──────────────────────┐  │
│  │  CAR IP:     │ │  CAM IP:     │ │   [Connect]    │ │ ● CAR ● CAM          │  │
│  │  192.168.x.x │ │  192.168.x.x │ │   [Disconnect] │ │   ONLINE   ONLINE    │  │
│  └──────────────┘ └──────────────┘ └────────────────┘ └──────────────────────┘  │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐ ┌──────────────────────┐  │
│  │  Resolution: │ │  Orientation:│ │   [Snapshot]   │ │   [OTA Update]       │  │
│  │  [640x480 ▼] │ │  [Flip H]   │ │      📷        │ │      ⚡              │  │
│  └──────────────┘ └──────────────┘ └────────────────┘ └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┬──────────────────────────────┐
│                                                  │    TELEMETRY SIDEBAR        │
│                                                  │  ┌────────────────────────┐ │
│                                                  │  │  🌡 TEMPERATURE        │ │
│                                                  │  │  ████████░░░░ 28.5°C   │ │
│                                                  │  └────────────────────────┘ │
│                                                  │  ┌────────────────────────┐ │
│                                                  │  │  💧 HUMIDITY           │ │
│                                                  │  │  ████████████░ 65%     │ │
│                                                  │  └────────────────────────┘ │
│                                                  │  ┌────────────────────────┐ │
│             CENTER VIDEO VIEWPORT                 │  │  🌫 AIR QUALITY        │ │
│                                                  │  │  ██████░░░░░ 450 ppm   │ │
│         ┌──────────────────────────┐             │  └────────────────────────┘ │
│         │                          │             │  ┌────────────────────────┐ │
│         │                          │             │  │  📏 OBSTACLE           │ │
│         │         ╋ CROSSHAIR      │             │  │  ████░░░░░░░ 45 cm     │ │
│         │                          │             │  └────────────────────────┘ │
│         │                          │             │  ┌────────────────────────┐ │
│         │    FPS: 30.0 | Ping: 5ms│             │  │  ⚠ SAFETY ALARM        │ │
│         └──────────────────────────┘             │  │  AUTO-BRAKE: [ON]      │ │
│                                                  │  │  Threshold: [====] 30cm│ │
│                                                  │  └────────────────────────┘ │
├──────────────────────────────────────────────────┤  ┌────────────────────────┐ │
│                    BOTTOM PANEL                  │  │  🎯 GIMBAL CONTROL     │ │
│  ┌────────────────────────────────────────────┐  │  │  Pan:   [====] 90°    │ │
│  │  SPEED: [============] 180 / 255          │  │  │  Tilt:  [====] 90°    │ │
│  └────────────────────────────────────────────┘  │  │  [C] Center Gimbal    │ │
│  ┌────────────────────────────────────────────┐  │  └────────────────────────┘ │
│  │  KEYS: W/S=Forward/Back  A/D=Spin         │  │                            │
│  │        IJKL=Gimbal  C=Center  Space=Stop   │  │                            │
│  └────────────────────────────────────────────┘  │                            │
└──────────────────────────────────────────────────┴──────────────────────────────┘
```

---

## Component Descriptions

### 1. TOP BAR — Connection & Quick Controls

| Element | Type | Function |
|---------|------|----------|
| `CAR IP` | Text Input | Rover chassis IP address |
| `CAM IP` | Text Input | Camera module IP address |
| `Connect/Disconnect` | Button | Toggle connection state |
| `CAR/CAM Status` | LED Indicator | ● GREEN = Online, ● RED = Offline |
| `Resolution Dropdown` | ComboBox | 640x480 / 800x600 / 1280x720 |
| `Flip H / Flip V` | Toggle Button | Mirror video feed horizontally/vertically |
| `Snapshot` | Button | Save current frame as JPEG with timestamp |
| `OTA Update` | Button | Trigger firmware update (with confirmation) |

---

### 2. CENTER VIDEO VIEWPORT

| Element | Type | Function |
|---------|------|----------|
| `Video Canvas` | QLabel | Live MJPEG stream display |
| `Crosshair` | Overlay | Fixed center marker for aiming |
| `FPS Display` | Label | Real-time frame rate (e.g., `30.0 FPS`) |
| `Ping Display` | Label | Network latency (e.g., `5 ms`) |

---

### 3. TELEMETRY SIDEBAR

| Element | Type | Function |
|---------|------|----------|
| `Temperature` | Progress Bar | Current °C with color coding |
| `Humidity` | Progress Bar | Current % RH |
| `Air Quality` | Progress Bar | Gas concentration in ppm |
| `Obstacle Distance` | Progress Bar | Ultrasonic distance in cm |
| `Safety Alarm` | Warning Banner | Flashing when obstacle < threshold |
| `Auto-Brake Toggle` | CheckBox | Enable/disable automatic braking |
| `Threshold Slider` | Slider | Safety distance (5cm - 60cm) |
| `Gimbal Pan` | Slider | Servo angle 0-180° |
| `Gimbal Tilt` | Slider | Servo angle 0-180° |
| `Center Gimbal` | Button | Reset to 90°/90° |

---

### 4. BOTTOM PANEL — Speed & Keys

| Element | Type | Function |
|---------|------|----------|
| `Speed Slider` | Slider | Motor PWM power (80-255) |
| `Speed Value` | Label | Current speed value |
| `Keys Reference` | Label | Keyboard shortcuts reminder |

---

## Keyboard State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                    KEYBOARD STATE MACHINE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   [IDLE] ───────────────────────────────────────────────────────►│
│      │                                                           │
│      │ Key Press (W/A/S/D)                                       │
│      ▼                                                           │
│   [DRIVING] ────────────────────────────────────────────────────►│
│      │                                                           │
│      │ Key Release / Space                                       │
│      ▼                                                           │
│   [STOPPING] ───────────────────────────────────────────────────►│
│      │                                                           │
│      │ Send STOP command                                         │
│      ▼                                                           │
│   [IDLE]                                                         │
│                                                                  │
│   [IDLE] ───────────────────────────────────────────────────────►│
│      │                                                           │
│      │ Key Press (I/J/K/L)                                       │
│      ▼                                                           │
│   [GIMBAL MOVING] ──────────────────────────────────────────────►│
│      │                                                           │
│      │ Key Release                                               │
│      ▼                                                           │
│   [GIMBAL HOLD] ────────────────────────────────────────────────►│
│      │                                                           │
│      │ C Key                                                     │
│      ▼                                                           │
│   [GIMBAL CENTERING] ───────────────────────────────────────────►│
│      │                                                           │
│      │ Send center command (90°, 90°)                            │
│      ▼                                                           │
│   [IDLE]                                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Thread Architecture Diagram

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
│ │ VIDEO       │  │ TELEMETRY   │  │ COMMAND     │  │ GIMBAL      │
│ │ THREAD      │  │ THREAD      │  │ THREAD      │  │ THREAD      │
│ │             │  │             │  │             │  │             │
│ │ recv UDP    │  │ HTTP GET    │  │ UDP send    │  │ UDP send    │
│ │ port 5006   │  │ every 1s    │  │ on keypress │  │ on keypress │
│ └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
│        │                │                │                │
│        ▼                ▼                ▼                ▼
│   ┌─────────────────────────────────────────────────────────────┐
│   │                    ESP32 ROVER                               │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │  │ esp32_car   │  │ esp32_cam   │  │ esp32_monitor│        │
│   │  │ (Motors)    │  │ (Camera)    │  │ (Sensors)   │        │
│   │  └─────────────┘  └─────────────┘  └─────────────┘        │
│   └─────────────────────────────────────────────────────────────┘
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## UDP Command Protocol (Updated)

### Commands (PC → ESP32, Port 5005)

| Command | Format | Description |
|---------|--------|-------------|
| `DRIVE` | `DRIVE:{speed}:{direction}` | Move with PWM speed |
| `STEER` | `STEER:{direction}` | Spin left/right in place |
| `STOP` | `STOP` | Emergency stop all motors |
| `GIMBAL` | `GIMBAL:{pan}:{tilt}` | Set gimbal servo angles |
| `CENTER` | `CENTER` | Reset gimbal to 90°/90° |
| `RESOLUTION` | `RES:{width}:{height}` | Set camera resolution |
| `FLIP` | `FLIP:{h/v}` | Flip camera orientation |
| `SNAPSHOT` | `SNAPSHOT` | Capture high-res frame |
| `OTA` | `OTA:{version}` | Trigger firmware update |

### Telemetry (ESP32 → PC, Port 5006)

| Field | Format | Description |
|-------|--------|-------------|
| `temp` | `TEMP:{value}` | Temperature in °C |
| `humi` | `HUMI:{value}` | Humidity in % |
| `gas` | `GAS:{value}` | Gas concentration in ppm |
| `dist` | `DIST:{value}` | Obstacle distance in cm |
| `video` | JPEG bytes | Video frame data |

---

## Color Scheme

| Element | Color | Hex Code |
|---------|-------|----------|
| Background (Dark) | Charcoal | `#1A1A2E` |
| Panel Background | Dark Navy | `#16213E` |
| Accent (Primary) | Electric Blue | `#0F3460` |
| Status Online | Green | `#4CAF50` |
| Status Offline | Red | `#F44336` |
| Warning Alarm | Orange | `#FF9800` |
| Text Primary | White | `#FFFFFF` |
| Text Secondary | Light Gray | `#B0BEC5` |

---

## Screen Zones Summary

| Zone | Position | Size | Purpose |
|------|----------|------|---------|
| Top Bar | Top | 100% width × 80px | Connection, Camera, Tools |
| Video Canvas | Center-Left | ~75% width × ~70% height | Live FPV feed |
| Telemetry Sidebar | Right | ~25% width × ~70% height | Gauges, Alarms, Gimbal |
| Bottom Panel | Bottom | 100% width × 120px | Speed, Keys Reference |
