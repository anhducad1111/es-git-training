# Space Rover Desktop Teleoperation Cockpit - UI Wireframe

## Screen Layout — Main View (Default)

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
│                                                  │  ┌─────┐                   │
│                                                  │  │ 💬  │ ← FLOATING BUTTON │
├──────────────────────────────────────────────────┤  └─────┘                   │
│                    BOTTOM PANEL                  │  ┌────────────────────────┐ │
│  ┌────────────────────────────────────────────┐  │  │  🎯 GIMBAL CONTROL     │ │
│  │  SPEED: [============] 180 / 255          │  │  │  Pan:   [====] 90°    │ │
│  └────────────────────────────────────────────┘  │  │  Tilt:  [====] 90°    │ │
│  ┌────────────────────────────────────────────┐  │  │  [C] Center Gimbal    │ │
│  │  KEYS: W/S=Forward/Back  A/D=Spin         │  │  └────────────────────────┘ │
│  │        IJKL=Gimbal  C=Center  Space=Stop   │  │                            │
│  └────────────────────────────────────────────┘  │                            │
└──────────────────────────────────────────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  [Log] Click to expand                                            ▼ COLLAPSED  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen Layout — AI Chat View (💬 Active)

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
│                                                  │    AI CHAT PANEL            │
│                                                  │  ┌────────────────────────┐ │
│                                                  │  │ 💬 Gemini Chat         │ │
│                                                  │  ├────────────────────────┤ │
│             HISTORICAL GRAPHS                     │  │                        │ │
│             (Drag & Drop to Customize)            │  │  System: Ready to      │ │
│                                                  │  │  analyze sensor data.  │ │
│  ┌──────────────────────────────────────────┐    │  │                        │ │
│  │  📊 Temperature & Humidity               │    │  │  You: Show me temp     │ │
│  │  ┌──────────────────────────────────┐    │    │  │  chart                 │ │
│  │  │  30°┤      ╭─╮                   │    │    │  │                        │ │
│  │  │     │    ╭─╯ ╰─╮    ╭──╮        │    │    │  │  Gemini: Creating      │ │
│  │  │  25°┤───╯       ╰──╯  ╰──       │    │    │  │  temperature chart...  │ │
│  │  │     │                            │    │    │  │                        │ │
│  │  │  20°┤                            │    │    │  ├────────────────────────┤ │
│  │  │     └────────────────────────────┘    │    │  │ [Type a message... ] [Send]│
│  │  │      12:00  12:05  12:10  12:15      │    │  └────────────────────────┘ │
│  │  └──────────────────────────────────┘    │    │  ┌─────┐                   │
│  └──────────────────────────────────────────┘    │  │ ✖  │ ← FLOATING BUTTON  │
│                                                  │  └─────┘   (active)        │
│  ┌──────────────────────────────────────────┐    │  ┌────────────────────────┐ │
│  │  📊 Air Quality (CO2, PM2.5)            │    │  │  🎯 GIMBAL CONTROL     │ │
│  │  ┌──────────────────────────────────┐    │    │  │  Pan:   [====] 90°    │ │
│  │  │  500┤      ╭──╮                  │    │    │  │  Tilt:  [====] 90°    │ │
│  │  │     │    ╭─╯  ╰─╮  ╭───╮        │    │    │  │  [C] Center Gimbal    │ │
│  │  │  400┤───╯        ╰─╯   ╰──      │    │    │  └────────────────────────┘ │
│  │  │     │                            │    │    │                            │
│  │  │  300┤                            │    │    │                            │
│  │  │     └────────────────────────────┘    │    │                            │
│  │  │      12:00  12:05  12:10  12:15      │    │                            │
│  │  └──────────────────────────────────┘    │    │                            │
│  └──────────────────────────────────────────┘    │                            │
│                                                  │                            │
│  [+ Add Chart]  [Reset Layout]                  │                            │
├──────────────────────────────────────────────────┤                            │
│                    BOTTOM PANEL                  │                            │
│  ┌────────────────────────────────────────────┐  │                            │
│  │  SPEED: [============] 180 / 255          │  │                            │
│  └────────────────────────────────────────────┘  │                            │
│  ┌────────────────────────────────────────────┐  │                            │
│  │  KEYS: W/S=Forward/Back  A/D=Spin         │  │                            │
│  │        IJKL=Gimbal  C=Center  Space=Stop   │  │                            │
│  └────────────────────────────────────────────┘  │                            │
└──────────────────────────────────────────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  [Log] Click to expand                                            ▼ COLLAPSED  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Chart Customization (Like haru-app2)

### Default Charts (Always Visible)

| Chart | Sensors | Description |
|-------|---------|-------------|
| Temperature & Humidity | `temperature`, `humidity` | Dual-axis line chart |
| Air Quality | `co2`, `pm1.0`, `pm2.5`, `pm10` | Multi-line chart |

### Custom Charts (User Created via Gemini or /chart command)

**Via Gemini Chat:**
```
You: Show me gas and battery on one chart
Gemini: Creating custom chart...
→ New chart appears with gas + battery lines
```

**Via /chart Command:**
```
/chart temperature humidity -n -m "My Environment Chart"
/chart co2 gas -d
/chart pm -n
```

### Chart Commands

| Command | Description |
|---------|-------------|
| `/chart {sensors}` | Create chart with specified sensors |
| `-n` | Normalize values (Min-Max scaling to 0-1) |
| `-d` | Separate into individual charts |
| `-m {name}` | Name the chart |

### Chart Features

- **Drag & Drop:** Drag charts to rearrange
- **Delete:** Right-click → Remove chart
- **Export:** Right-click → Save as PNG
- **Real-time:** Updates every 5 seconds with new data

---

## Floating Button & Panel Toggle Behavior

### Button Position (Right side, overlapping telemetry sidebar)

```
    ┌──────────────────────────────┐
    │    TELEMETRY SIDEBAR        │
    │  ┌────────────────────────┐ │
    │  │  🌡 TEMPERATURE        │ │
    │  └────────────────────────┘ │
    │  ┌─────┐                   │
    │  │ 💬  │  ← FLOATING BUTTON
    │  └─────┘    (overlapping sidebar)
    │  ┌────────────────────────┐ │
    │  │  🎯 GIMBAL CONTROL     │ │
    │  └────────────────────────┘ │
    └──────────────────────────────┘
```

### Toggle Logic

| State | 💬 Button | Left Side | Right Side |
|-------|-----------|-----------|------------|
| **Default** | OFF (💬) | Video Camera | Telemetry |
| **AI Chat** | ON (✖) | Historical Graphs | AI Chat Panel |

- Click 💬 to open AI Chat view
- Click ✖ to close and return to Default view
- Floating button always stays in same position

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

### 2. CENTER VIDEO VIEWPORT (Main View)

| Element | Type | Function |
|---------|------|----------|
| `Video Canvas` | QLabel | Live MJPEG stream display |
| `Crosshair` | Overlay | Fixed center marker for aiming |
| `FPS Display` | Label | Real-time frame rate (e.g., `30.0 FPS`) |
| `Ping Display` | Label | Network latency (e.g., `5 ms`) |

---

### 3. HISTORICAL GRAPHS (AI Chat View - Left Side)

| Element | Type | Function |
|---------|------|----------|
| `Chart Widget` | Matplotlib Canvas | Real-time line charts |
| `Add Chart Button` | QPushButton | Create new custom chart |
| `Reset Layout Button` | QPushButton | Reset to default charts |

**Default Charts:**
- Temperature & Humidity (dual-axis)
- Air Quality (CO2, PM1.0, PM2.5, PM10)

**Custom Charts:**
- Created via Gemini chat or `/chart` command
- Draggable, removable, exportable

---

### 4. TELEMETRY SIDEBAR (Main View)

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

### 5. AI CHAT PANEL (💬 View - Right Side)

| Element | Type | Function |
|---------|------|----------|
| `Chat History` | QScrollArea | Scrollable message bubbles |
| `Chat Input` | QTextEdit | Type messages (Tab autocomplete) |
| `Send Button` | QPushButton | Send message to Gemini |
| `Gimbal Control` | Panel | Always visible in sidebar |

---

### 6. BOTTOM PANEL — Speed & Keys

| Element | Type | Function |
|---------|------|----------|
| `Speed Slider` | Slider | Motor PWM power (80-255) |
| `Speed Value` | Label | Current speed value |
| `Keys Reference` | Label | Keyboard shortcuts reminder |

---

### 7. FLOATING BUTTON (Right side, overlapping sidebar)

| Element | Type | Function |
|---------|------|----------|
| `💬 AI Chat` | QPushButton | Toggle AI chat + graphs view |

**Position:** Right side, overlapping telemetry sidebar (between Safety Alarm and Gimbal Control)

**Styling:**
- Round button (50x50px)
- Purple (`#9C27B0`)
- Hover effect: Darker shade
- Active state: Shows ✖ instead of 💬
- Always visible, always in same position

---

### 8. LOG SCREEN — Collapsible Debug Panel

| Element | Type | Function |
|---------|------|----------|
| `Log Toggle Button` | QPushButton | `[Log] Click to expand/collapse` |
| `Log Display` | QTextEdit | Scrollable log output (read-only) |

**Behavior:**
- **Collapsed (Default):** Shows only the toggle button at the bottom
- **Expanded:** Shows full log panel with colored messages
- **Toggle:** Click button to switch between states

**Log Message Format:**
```
[HH:MM:SS] CATEGORY | Message content
```

**Color Coding:**
| Category | Color | Hex |
|----------|-------|-----|
| CONNECTED / OK | Green | `#69F0AE` |
| WARNING | Orange | `#FF9800` |
| ERROR / FAIL | Red | `#FF5252` |
| DRIVE / GIMBAL / STOP | White | `#FFFFFF` |
| SNAPSHOT / OTA | Cyan | `#00BCD4` |

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

## UDP Command Protocol

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
| AI Chat Button | Purple | `#9C27B0` |

---

## Screen Zones Summary

| Zone | Position | Size | Purpose |
|------|----------|------|---------|
| Top Bar | Top | 100% width × 80px | Connection, Camera, Tools |
| Video Canvas | Center-Left | ~75% width × ~70% height | Live FPV feed (Main View) |
| Historical Graphs | Center-Left | ~75% width × ~70% height | Charts (💬 View) |
| Telemetry Sidebar | Right | ~25% width × ~70% height | Gauges, Alarms, Gimbal |
| AI Chat Panel | Right | ~25% width × ~70% height | Gemini Chat (💬 View) |
| Bottom Panel | Bottom | 100% width × 120px | Speed, Keys Reference |
| Floating Button | Right (overlapping sidebar) | 50x50px | Toggle AI Chat + Graphs |
| Log Screen | Very Bottom | 100% width × 150px (collapsed: 30px) | Debug logs |
