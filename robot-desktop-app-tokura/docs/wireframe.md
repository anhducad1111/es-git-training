# Space Rover Desktop Teleoperation Cockpit — UI Wireframe

## Screen Layout — Main View (Default)

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
│                                                  │  │ [🚶 Follow Mode]       │ │
├──────────────────────────────────────────────────┤  └────────────────────────┘ │
│ BOTTOM CONTROLS                                                         │
│ ┌──────────────────────┐ ┌──────────────────┐ ┌────────────────────┐ ┌────────┐ │
│ │ Motor Speed          │ │ Auto-Brake [ON]  │ │ Gimbal: Pan 90°   │ │ W/S    │ │
│ │ 220 (86%) [====]     │ │ Threshold: 30cm  │ │        Tilt 90°   │ │ A/D    │ │
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
```

---

## Screen Layout — Diagnostics View

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ HEADER: 🏭 Rover Teleop Cockpit v2.4.0  │ Main View │ Gimbal │ Diag │ Subsys   │
│         Rover IP: [192.168.1.100]  Cam IP: [192.168.1.101]  ● Rover ● Cam  [⚡]│
└─────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┬────────────────────────────┐
│ 📊 Historical Sensor Analytics                     │  Local AI Sensor Analyst   │
│   Window: 15m Telemetry Deck                       │  ┌──────────────────────┐ │
│   Auto-Refresh (5s) [ON]  [+ Add Chart] [Reset]   │  │ ● Ollama active      │ │
├────────────────────────────────────────────────────┤  ├──────────────────────┤ │
│ 💡 Tip: /chart in AI chat to customize plots       │  │ ℹ TELEMETRY CONTEXT  │ │
│    SYNC_RATE: 100ms • BUFFER: 900pts               │  │ Temp:28.5°C Air:450  │ │
├────────────────────────────────────────────────────┤  │ Dist:45cm Batt:94%   │ │
│                                                    │  ├──────────────────────┤ │
│ 🌡 Temperature & Humidity (Dual-Axis)  ● LIVE      │  │ You:                 │ │
│   Temp: 28.5°C  Humidity: 58.2%RH                 │  │ Show me temp and     │ │
│   ┌──────────────────────────────────────────┐    │  │ humidity together... │ │
│   │ 35°┤     ╭────╮                         │    │  ├──────────────────────┤ │
│   │    │   ╭─╯    ╰──╮    ╭────╮           │    │  │ AI:                  │ │
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
[LOG] 12:14:11 Ollama API tool response OK | 12:12:00 Radio Ping: 18ms   expand ▼
```

---

## Video Overlay Status Bar (Top Center of Video)

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

## Screen Zones Summary

### Main View

| Zone | Position | Size | Purpose |
|------|----------|------|---------|
| Header Bar | Top | 100% width × 48px | App title, nav tabs, IPs, status, actions |
| Video Canvas | Center | ~75% width × flex | Live FPV feed |
| Video Overlay | Top of Video | Auto-width × 32px | FPS, Ping, Distance, Temp, Humidity |
| Resolution Dropdown | Bottom-Right of Video | Auto | Camera resolution selector |
| Telemetry Sidebar | Right | 320px (w-80) | Sensor cards, subsystem health |
| Bottom Controls | Bottom | 100% width × auto | Speed, Auto-Brake, Gimbal, Keys, Stop |
| Log Panel | Very Bottom | 100% width × 24px | Debug logs (collapsible) |
| Floating Button | Bottom-Right | 40×40px circle | Toggle to Diagnostics view |

### Diagnostics View

| Zone | Position | Size | Purpose |
|------|----------|------|---------|
| Header Bar | Top | 100% width × 48px | Same as Main View |
| Analytics Deck | Left | ~70% width × flex | Historical sensor charts |
| Analytics Control Bar | Top of Analytics | 100% width × 48px | Auto-Refresh, Add Chart, Reset Layout |
| Command Tip Banner | Below Control Bar | 100% width × 32px | /chart command hints |
| Chart 1: Temp & Humidity | Full Width | 100% × 192px | Dual-axis line chart with live values |
| Chart 2: Air Quality | Left Half | 50% × 180px | CO2 + PM2.5 multi-trend |
| Chart 3: Obstacle Proximity | Right Half | 50% × 180px | Sonar bar chart timeline |
| Ollama Chat Panel | Right | 384px (w-96) | AI analyst chat |
| Chat Header | Top of Chat | 100% × 48px | Model name, status, close button |
| Chat Stream | Middle | Flex | Messages, tool cards, suggestions |
| Chat Input | Bottom | 100% × auto | Text input + send button |
| Log Bar | Very Bottom | 100% width × 24px | Debug logs (collapsible) |
| Floating Button | Bottom-Right | 52×52px circle | Purple, close/return to Main View |

---

## Component Descriptions

### Header Bar

| Element | Type | Function |
|---------|------|----------|
| `App Title` | Label | 🏭 Rover Teleop Cockpit v2.4.0 |
| `Navigation Tabs` | Tab Bar | Main View / Gimbal / Diagnostics / Subsystems |
| `Rover IP` | Text Input (readonly) | Rover chassis IP address |
| `Camera IP` | Text Input (readonly) | Camera module IP address |
| `Rover Status` | LED Indicator | ● GREEN = Online, ● RED = Offline |
| `Cam Status` | LED Indicator | ● GREEN = Online, ● RED = Offline |
| `Flip Orientation` | Button | Mirror video feed horizontally/vertically |
| `OTA Update` | Button | Trigger firmware update (with confirmation) |
| `Connection Toggle` | Button | Connect/Disconnect to rover |

### Center Video Viewport (Main View)

| Element | Type | Function |
|---------|------|----------|
| `Video Canvas` | Widget | Live video stream display (Binary JPEG over WebSocket) |
| `Crosshair` | SVG Overlay | Fixed center marker for aiming |
| `Status Overlay` | Widget (top center) | FPS, Ping, Distance, Temp, Humidity |
| `Resolution Dropdown` | ComboBox (bottom right) | 640x480 / 1280x720 / 320x240 |

### Telemetry Sidebar (Main View)

| Element | Type | Function |
|---------|------|----------|
| `Panel Header` | Widget | "Telemetry Sensors" + Link quality |
| `E-STOP Button` | Button (red) | Emergency stop |
| `Chassis Core Temp` | Card + Progress Bar | Current °C with color coding |
| `Ambient Humidity` | Card + Progress Bar | Current % RH |
| `Air Purity Metric` | Card + Progress Bar | Gas concentration in PPM |
| `Obstacle Distance` | Card + Progress Bar | Ultrasonic distance in cm |
| `Subsystem Health` | List | ESP32, Motor Drivers, Servos, Battery (from ESP32 directly) |
| `Take Snapshot` | Button | Capture frame and upload to `POST /api/v1/rovers/{uid}/media` |
| `System Diagnostics` | Link | Open diagnostics view |
| `Device Configuration` | Link | Open config view |
| `Follow Mode` | Toggle Button | Call `POST http://rpi5.local/follow/start` |

### Bottom Controls

| Element | Type | Function |
|---------|------|----------|
| `Motor Speed` | Slider + Label | PWM power 150-255 (displayed as %), default 220 |
| `Auto-Brake Toggle` | Switch | Enable/disable automatic braking |
| `Threshold Slider` | Slider + Label | Safety distance (10cm - 100cm) |
| `Gimbal Pan` | Slider + Label | Servo angle 0-180° |
| `Gimbal Tilt` | Slider + Label | Servo angle 0-180° |
| `Center Gimbal` | Button | Reset to 90°/90° |
| `Keybinds Display` | Labels | W/S=Drive, A/D=Turn, I/J/K/L=Gimbal |
| `Emergency Stop` | Button (red) | Space: Stop all motors |

### Analytics Deck (Diagnostics View)

| Element | Type | Function |
|---------|------|----------|
| `Analytics Control Bar` | Widget | Title + Auto-Refresh toggle + Add Chart + Reset Layout |
| `Auto-Refresh Toggle` | Switch (5s interval) | Enable/disable automatic chart refresh |
| `Add Chart Button` | Button | Create new custom chart |
| `Reset Layout Button` | Button | Restore default chart arrangement |
| `Command Tip Banner` | Banner | /chart command hints and sync rate display |
| `Chart 1: Temp & Humidity` | Dual-Axis Line Chart | Temperature (orange) + Humidity (blue) with live values |
| `Chart 2: Air Quality` | Multi-Trend Chart | CO2 (emerald) + PM2.5 (blue) dashed line |
| `Chart 3: Obstacle Proximity` | Bar Chart Timeline | Sonar distance history with threshold marker |

### Ollama Chat Panel (Diagnostics View)

| Element | Type | Function |
|---------|------|----------|
| `Chat Header` | Widget | Model name (phi3:mini), status, close button |
| `Close Button` | Button | Return to Main View |
| `Telemetry Context Pill` | Card | Current sensor readings attached to context |
| `Chat Messages` | Scroll Area | User questions + AI responses |
| `Tool Execution Card` | Card | Shows function calls with args and execution time |
| `Suggestion Pills` | Buttons | Quick action commands (/chart, /filter, /export) |
| `Chat Input` | Text Input | Type /chart commands or natural language queries |
| `Send Button` | Button | Submit message to Ollama |

### Log Panel

| Element | Type | Function |
|---------|------|----------|
| `Log Toggle` | Summary/Header | `[LOG] Click to expand/collapse • N Events` |
| `Log Display` | Scrollable Area | Colored log entries with timestamps |
| `Baud Rate` | Label | Serial baud rate display |

**Log Entry Format:**
```
[HH:MM:SS] [CATEGORY] Message content
```

**Log Categories:**
| Category | Color | Example |
|----------|-------|---------|
| CONNECTED | Green | `WebSocket connected (ACK in 4.2ms)` |
| VIDEO | Blue | `Stream active at 640x480 @ 30 FPS` |
| TELEMETRY | White | `Chassis Temp 28.5°C, Dist 45cm` |
| SAFETY | Orange | `Auto-brake threshold set to 30 cm` |
| ERROR | Red | `Connection lost to rover` |

---
- Floating button stays at bottom-right corner (fixed position)

---

## Color Scheme

| Element | Color Name | Hex Code |
|---------|------------|----------|
| Background | Charcoal | `#0b1326` |
| Surface | Dark Navy | `#0b1326` |
| Surface Container | Navy | `#171f33` |
| Surface Container Low | Deep Navy | `#131b2e` |
| Surface Container High | Slate | `#222a3d` |
| Surface Container Highest | Blue Slate | `#2d3449` |
| Surface Bright | Bright Slate | `#31394d` |
| Outline | Gray | `#8d90a0` |
| Outline Variant | Dark Slate | `#434655` |
| Primary | Light Blue | `#b4c5ff` |
| Primary Container | Blue | `#2563eb` |
| Secondary | Light Slate | `#b7c8e1` |
| Tertiary | Coral | `#ffb596` |
| Error | Light Red | `#ffb4ab` |
| Text Primary | White Smoke | `#dae2fd` |
| Text Secondary | Light Slate | `#c3c6d7` |

**Fonts:**
- Sans: Inter
- Mono: JetBrains Mono (for telemetry values)

---

## Chart Customization (Like haru-app2)

### Default Charts (Always Visible)

| Chart | Sensors | Description |
|-------|---------|-------------|
| Temperature & Humidity | `temperature`, `humidity` | Dual-axis line chart |
| Air Quality | `co2`, `pm2.5` | Multi-line chart |
| Obstacle Proximity | `distance` | Bar chart timeline |

### Custom Charts (User Created via Ollama or /chart command)

**Via Ollama Chat:**
```
You: Show me gas and battery on one chart
AI: Creating custom chart...
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
- **Auto-Refresh:** Toggle on/off in Analytics Control Bar

---

## Keyboard State Machine

### Drive Control

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
└─────────────────────────────────────────────────────────────────┘
```

### Gimbal Control

```
┌─────────────────────────────────────────────────────────────────┐
│                    GIMBAL STATE MACHINE                          │
├─────────────────────────────────────────────────────────────────┤
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
│ │ WebSocket   │  │ HTTP GET    │  │ WebSocket   │  │ WebSocket   │
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

## Resolution Change Architecture

### Resolution Options

| Resolution | Width | Height | FPS | Use Case |
|------------|-------|--------|-----|----------|
| `640x480` | 640 | 480 | 30 FPS | Standard Fluid (default) |
| `1280x720` | 1280 | 720 | 15-20 FPS | High Detail |
| `320x240` | 320 | 240 | 60 FPS | High Frame Rate |

### Resolution Change State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                RESOLUTION CHANGE STATE MACHINE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   [STREAMING] ──────────────────────────────────────────────────►│
│      │                                                           │
│      │ User selects new resolution                               │
│      ▼                                                           │
│   [CHANGING] ───────────────────────────────────────────────────►│
│      │                                                           │
│      │ Send RES command                                          │
│      │ Stop video thread                                         │
│      ▼                                                           │
│   [WAITING_ACK] ────────────────────────────────────────────────►│
│      │                                                           │
│      ├─ ACK received ───────────────────────────────────────────►│
│      │   │                                                       │
│      │   ▼                                                       │
│      │ [STREAMING] (new resolution)                              │
│      │                                                           │
│      └─ Timeout (2s) ───────────────────────────────────────────►│
│          │                                                       │
│          ▼                                                       │
│      [ERROR] ───────────────────────────────────────────────────►│
│          │                                                       │
│          │ Show error in log                                     │
│          │ Revert to previous resolution                         │
│          ▼                                                       │
│      [STREAMING] (old resolution)                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```
