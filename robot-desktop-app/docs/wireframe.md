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
├──────────────────────────────────────────────────┤  ┌────────────────────────┐ │
│                    BOTTOM PANEL                  │  │  🎯 GIMBAL CONTROL     │ │
│  ┌────────────────────────────────────────────┐  │  │  Pan:   [====] 90°    │ │
│  │  SPEED: [============] 180 / 255          │  │  │  Tilt:  [====] 90°    │ │
│  └────────────────────────────────────────────┘  │  │  [C] Center Gimbal    │ │
│  ┌────────────────────────────────────────────┐  │  └────────────────────────┘ │
│  │  KEYS: W/S=Forward/Back  A/D=Spin         │  │                            │
│  │        IJKL=Gimbal  C=Center  Space=Stop   │  │                            │
│  └────────────────────────────────────────────┘  │                            │
│                                                  │                            │
│                              ┌─────┬─────┐       │                            │
│                              │ 💬  │ 🚗  │       │                            │
│                              └─────┴─────┘       │                            │
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
│                                                  │  │                        │ │
│                                                  │  │  System: Ready to      │ │
│                                                  │  │  analyze sensor data.  │ │
│                                                  │  │                        │ │
│                                                  │  │  You: Show me temp     │ │
│                                                  │  │  chart                 │ │
│                                                  │  │                        │ │
│                                                  │  │  Gemini: Creating      │ │
│                                                  │  │  temperature chart...  │ │
│                                                  │  │                        │ │
│                                                  │  ├────────────────────────┤ │
│                                                  │  │ [Type a message... ] [Send]│
│                                                  │  └────────────────────────┘ │
│                                                  │  ┌────────────────────────┐ │
│                                                  │  │ 🎯 GIMBAL CONTROL     │ │
│                                                  │  │  Pan:   [====] 90°    │ │
│                                                  │  │  Tilt:  [====] 90°    │ │
│                                                  │  │  [C] Center Gimbal    │ │
│                                                  │  └────────────────────────┘ │
├──────────────────────────────────────────────────┤                            │
│                    BOTTOM PANEL                  │                            │
│  ┌────────────────────────────────────────────┐  │                            │
│  │  SPEED: [============] 180 / 255          │  │                            │
│  └────────────────────────────────────────────┘  │                            │
│  ┌────────────────────────────────────────────┐  │                            │
│  │  KEYS: W/S=Forward/Back  A/D=Spin         │  │                            │
│  │        IJKL=Gimbal  C=Center  Space=Stop   │  │                            │
│  └────────────────────────────────────────────┘  │                            │
│                              ┌─────┬─────┐       │                            │
│                              │ 💬  │ 🚗  │       │                            │
│                              └─────┴─────┘       │                            │
└──────────────────────────────────────────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  [Log] Click to expand                                            ▼ COLLAPSED  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen Layout — RC Car View (🚗 Active)

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
│                                                  │    RC CAR CONTROL           │
│                                                  │  ┌────────────────────────┐ │
│                                                  │  │ 🚗 RC Car Control      │ │
│                                                  │  ├────────────────────────┤ │
│                                                  │  │   Status: Connected    │ │
│                                                  │  │                        │ │
│                                                  │  │      ┌─────┐          │ │
│                                                  │  │      │  ▲  │          │ │
│                                                  │  │   ┌──┼──┼──┼──┐       │ │
│                                                  │  │   │ ◀ │STOP│▶ │       │ │
│                                                  │  │   └──┼──┼──┼──┘       │ │
│                                                  │  │      │  ▼  │          │ │
│                                                  │  │      └─────┘          │ │
│                                                  │  │                        │ │
│                                                  │  │   ┌──────────────┐     │ │
│                                                  │  │   │  LIVE VIDEO  │     │ │
│                                                  │  │   │    FEED      │     │ │
│                                                  │  │   │  (Camera)    │     │ │
│                                                  │  │   └──────────────┘     │ │
│                                                  │  │                        │ │
│                                                  │  │   [Reset Camera]       │ │
│                                                  │  │   Speed: 50%           │ │
│                                                  │  └────────────────────────┘ │
│                                                  │  ┌────────────────────────┐ │
├──────────────────────────────────────────────────┤  │  🎯 GIMBAL CONTROL     │ │
│                    BOTTOM PANEL                  │  │  Pan:   [====] 90°    │ │
│  ┌────────────────────────────────────────────┐  │  │  Tilt:  [====] 90°    │ │
│  │  SPEED: [============] 180 / 255          │  │  │  [C] Center Gimbal    │ │
│  └────────────────────────────────────────────┘  │  └────────────────────────┘ │
│  ┌────────────────────────────────────────────┐  │                            │
│  │  KEYS: W/S=Forward/Back  A/D=Spin         │  │                            │
│  │        IJKL=Gimbal  C=Center  Space=Stop   │  │                            │
│  └────────────────────────────────────────────┘  │                            │
│                              ┌─────┬─────┐       │                            │
│                              │ 💬  │ 🚗  │       │                            │
│                              └─────┴─────┘       │                            │
└──────────────────────────────────────────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  [Log] Click to expand                                            ▼ COLLAPSED  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Floating Buttons & Panel Toggle Behavior

### Button Position (Same as haru-app2)

```
                              ┌─────┬─────┐
                              │ 💬  │ 🚗  │  ← Floating buttons
                              └─────┴─────┘     (bottom-right, above log tab)
```

### Toggle Logic

| State | 💬 Button | 🚗 Button | Main Content |
|-------|-----------|-----------|--------------|
| **Default** | OFF (💬) | OFF (🚗) | Video + Telemetry |
| **AI Chat** | ON (✖) | OFF (🚗) | AI Chat Panel |
| **RC Car** | OFF (💬) | ON (✖) | RC Car Control |

- **Only one sub-panel can be active at a time**
- Clicking the active button again returns to Default view
- Clicking the other button switches directly to that panel

### Panel Content

**💬 AI Chat Panel:**
- Chat history (scrollable)
- Text input + Send button
- Gemini responses with markdown rendering
- `/chart` command support for custom charts

**🚗 RC Car Control Panel:**
- D-pad buttons (▲◀▶▼ + STOP)
- Live video feed (smaller preview)
- Reset Camera button
- Speed percentage display
- WASD keyboard control (when panel active)

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

### 3. TELEMETRY SIDEBAR (Main View)

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

### 4. AI CHAT PANEL (💬 View)

| Element | Type | Function |
|---------|------|----------|
| `Chat History` | QScrollArea | Scrollable message bubbles |
| `Chat Input` | QTextEdit | Type messages (Tab autocomplete) |
| `Send Button` | QPushButton | Send message to Gemini |
| `Gimbal Control` | Panel | Always visible in sidebar |

---

### 5. RC CAR CONTROL PANEL (🚗 View)

| Element | Type | Function |
|---------|------|----------|
| `D-Pad` | QGridLayout | ▲◀▶▼ directional buttons |
| `STOP Button` | QPushButton | Emergency stop (center) |
| `Video Preview` | QLabel | Smaller live camera feed |
| `Reset Camera` | QPushButton | Reset camera gimbal |
| `Speed Display` | QLabel | Current speed percentage |
| `Gimbal Control` | Panel | Always visible in sidebar |

---

### 6. BOTTOM PANEL — Speed & Keys

| Element | Type | Function |
|---------|------|----------|
| `Speed Slider` | Slider | Motor PWM power (80-255) |
| `Speed Value` | Label | Current speed value |
| `Keys Reference` | Label | Keyboard shortcuts reminder |

---

### 7. FLOATING BUTTONS

| Element | Type | Function |
|---------|------|----------|
| `💬 AI Chat` | QPushButton | Toggle AI chat panel |
| `🚗 RC Car` | QPushButton | Toggle RC car control panel |

**Styling:**
- Round buttons (50x50px)
- 💬: Purple (`#9C27B0`)
- 🚗: Blue (`#2196F3`)
- Hover effect: Darker shade
- Active state: Shows ✖ instead of emoji

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
| AI Chat Button | Purple | `#9C27B0` |
| RC Car Button | Blue | `#2196F3` |

---

## Screen Zones Summary

| Zone | Position | Size | Purpose |
|------|----------|------|---------|
| Top Bar | Top | 100% width × 80px | Connection, Camera, Tools |
| Video Canvas | Center-Left | ~75% width × ~70% height | Live FPV feed (Main View) |
| Telemetry Sidebar | Right | ~25% width × ~70% height | Gauges, Alarms, Gimbal |
| AI Chat Panel | Right | ~25% width × ~70% height | Gemini Chat (💬 View) |
| RC Car Panel | Right | ~25% width × ~70% height | D-pad + Video (🚗 View) |
| Bottom Panel | Bottom | 100% width × 120px | Speed, Keys Reference |
| Floating Buttons | Bottom-Right | 2 × 50x50px | Toggle AI/RC panels |
| Log Screen | Very Bottom | 100% width × 150px (collapsed: 30px) | Debug logs |
