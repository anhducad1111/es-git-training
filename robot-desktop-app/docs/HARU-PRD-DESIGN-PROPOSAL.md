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
4. Communication protocol specification
5. Feature requirements
6. Safety features
7. OTA firmware update design
8. Implementation plan
9. Questions for Duke

**Note:** Cloud API integration details will be added in Phase 3 after receiving the official API documentation from Duke.

---

## 2. System Architecture

```
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
│ │ 10:00:01 [CONNECTED] UDP Port 5005 bound to 192.168.1.100 (ACK in 4.2ms)   │ │
│ │ 10:00:02 [VIDEO]      Stream active at 640x480 @ 30 FPS                    │ │
│ │ 10:00:05 [TELEMETRY]  Chassis Temp 28.5°C, Dist 45cm, Humidity 65%         │ │
│ │ 10:00:08 [SAFETY]     Auto-brake threshold set to 30 cm                    │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
                              ┌─────┐
                              │ 💬  │ ← FLOATING BUTTON (bottom-right)
                              └─────┘
```

### 3.2 AI Chat View (💬 Active — Diagnostics Panel)

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

### 3.4 Screen Zones Summary

#### Main View

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

#### Diagnostics View (💬 Active)

| Zone | Position | Size | Purpose |
|------|----------|------|---------|
| Header Bar | Top | 100% width × 48px | Same as Main View |
| Analytics Deck | Left | ~70% width × flex | Historical sensor charts |
| Analytics Control Bar | Top of Analytics | 100% width × 48px | Auto-Refresh, Add Chart, Reset Layout |
| Command Tip Banner | Below Control Bar | 100% width × 32px | /chart command hints |
| Chart 1: Temp & Humidity | Full Width | 100% × 192px | Dual-axis line chart with live values |
| Chart 2: Air Quality | Left Half | 50% × 180px | CO2 + PM2.5 multi-trend |
| Chart 3: Obstacle Proximity | Right Half | 50% × 180px | Sonar bar chart timeline |
| Gemini Chat Panel | Right | 384px (w-96) | AI analyst chat |
| Chat Header | Top of Chat | 100% × 48px | Model name, status, close button |
| Chat Stream | Middle | Flex | Messages, tool cards, suggestions |
| Chat Input | Bottom | 100% × auto | Text input + send button |
| Log Bar | Very Bottom | 100% width × 24px | Debug logs (collapsible) |
| Floating Button | Bottom-Right | 52×52px circle | Purple, close/return to Main View |

### 3.5 Component Descriptions

#### HEADER BAR

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

#### CENTER VIDEO VIEWPORT

| Element | Type | Function |
|---------|------|----------|
| `Video Canvas` | Widget | Live MJPEG stream display |
| `Crosshair` | SVG Overlay | Fixed center marker for aiming |
| `Status Overlay` | Widget (top center) | FPS, Ping, Distance, Temp, Humidity |
| `Resolution Dropdown` | ComboBox (bottom right) | 640x480 / 1280x720 / 320x240 |

#### TELEMETRY SIDEBAR

| Element | Type | Function |
|---------|------|----------|
| `Panel Header` | Widget | "Telemetry Sensors" + Link quality |
| `E-STOP Button` | Button (red) | Emergency stop |
| `Chassis Core Temp` | Card + Progress Bar | Current °C with color coding |
| `Ambient Humidity` | Card + Progress Bar | Current % RH |
| `Air Purity Metric` | Card + Progress Bar | Gas concentration in PPM |
| `Obstacle Distance` | Card + Progress Bar | Ultrasonic distance in cm |
| `Subsystem Health` | List | ESP32, Motor Drivers, Servos, Battery |
| `Take Snapshot` | Button | Save current frame as JPEG |
| `System Diagnostics` | Link | Open diagnostics view |
| `Device Configuration` | Link | Open config view |

#### BOTTOM CONTROLS

| Element | Type | Function |
|---------|------|----------|
| `Motor Speed` | Slider + Label | PWM power 0-255 (displayed as %) |
| `Auto-Brake Toggle` | Switch | Enable/disable automatic braking |
| `Threshold Slider` | Slider + Label | Safety distance (10cm - 100cm) |
| `Gimbal Pan` | Slider + Label | Servo angle 0-180° |
| `Gimbal Tilt` | Slider + Label | Servo angle 0-180° |
| `Center Gimbal` | Button | Reset to 90°/90° |
| `Keybinds Display` | Labels | W/S=Drive, A/D=Turn, I/J/K/L=Gimbal |
| `Emergency Stop` | Button (red) | Space: Stop all motors |

#### LOG PANEL

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
| CONNECTED | Green | `UDP Port 5005 bound (ACK in 4.2ms)` |
| VIDEO | Blue | `Stream active at 640x480 @ 30 FPS` |
| TELEMETRY | White | `Chassis Temp 28.5°C, Dist 45cm` |
| SAFETY | Orange | `Auto-brake threshold set to 30 cm` |
| ERROR | Red | `Connection lost to rover` |

#### FLOATING CHAT BUTTON

| Element | Type | Function |
|---------|------|----------|
| `💬 Chat` | Circular Button (40×40) | Toggle AI chat + graphs view |

**Position:** Bottom-right corner (fixed, not overlapping sidebar)
**Styling:** Blue (`#3b82f6`), hover scale effect, tooltip on hover

#### BOTTOM PANEL

| Element | Type | Function |
|---------|------|----------|
| `Speed Slider` | Slider | Motor PWM power (80-255) |
| `Speed Value` | Label | Current speed value |
| `Keys Reference` | Label | Keyboard shortcuts reminder |

#### FLOATING CHAT BUTTON

| Element | Type | Function |
|---------|------|----------|
| `💬 Chat` | Circular Button (40×40) | Toggle to Diagnostics view |

**Position:** Bottom-right corner (fixed, not overlapping sidebar)
**Styling:** Blue (`#3b82f6`), hover scale effect, tooltip on hover
**States:** 💬 (inactive) → ✖ (active, returns to Main View)

#### ANALYTICS DECK (Diagnostics View — Left Side)

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

#### GEMINI CHAT PANEL (Diagnostics View — Right Side)

| Element | Type | Function |
|---------|------|----------|
| `Chat Header` | Widget | Model name (gemini-3.5-flash-lite), status, close button |
| `Close Button` | Button | Return to Main View |
| `Telemetry Context Pill` | Card | Current sensor readings attached to context |
| `Chat Messages` | Scroll Area | User questions + Gemini responses |
| `Tool Execution Card` | Card | Shows function calls with args and execution time |
| `Suggestion Pills` | Buttons | Quick action commands (/chart, /filter, /export) |
| `Chat Input` | Text Input | Type /chart commands or natural language queries |
| `Send Button` | Button | Submit message to Gemini |

#### LOG SCREEN

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

### 3.6 Floating Button & Panel Toggle Behavior

| State | 💬 Button | Left Side | Right Side |
|-------|-----------|-----------|------------|
| **Default** | OFF (💬) | Video Camera | Telemetry Sensors |
| **AI Chat** | ON (✖) | Historical Graphs | AI Chat Panel |

- Click 💬 to open AI Chat view
- Click ✖ to close and return to Default view
- Floating button stays at bottom-right corner (fixed position)

### 3.7 Chart Customization (Like haru-app2)

#### Default Charts (Always Visible)

| Chart | Sensors | Description |
|-------|---------|-------------|
| Temperature & Humidity | `temperature`, `humidity` | Dual-axis line chart |
| Air Quality | `co2`, `pm1.0`, `pm2.5`, `pm10` | Multi-line chart |

#### Custom Charts (User Created via Gemini or /chart command)

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

#### Chart Commands

| Command | Description |
|---------|-------------|
| `/chart {sensors}` | Create chart with specified sensors |
| `-n` | Normalize values (Min-Max scaling to 0-1) |
| `-d` | Separate into individual charts |
| `-m {name}` | Name the chart |

#### Chart Features

- **Drag & Drop:** Drag charts to rearrange
- **Delete:** Right-click → Remove chart
- **Export:** Right-click → Save as PNG
- **Real-time:** Updates every 5 seconds with new data

---

## 4. Keyboard State Machine

### 4.1 Drive Control

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

### 4.2 Gimbal Control

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

### 4.3 Key Mapping

| Key | Action | UDP Command |
|-----|--------|-------------|
| `W` | Drive forward | `DRIVE:{speed}:FORWARD` |
| `S` | Drive backward | `DRIVE:{speed}:BACKWARD` |
| `A` | Spin left | `STEER:LEFT` |
| `D` | Spin right | `STEER:RIGHT` |
| `Space` | Emergency stop | `STOP` |
| `I` | Tilt up | `GIMBAL:{pan}:{tilt+5}` |
| `K` | Tilt down | `GIMBAL:{pan}:{tilt-5}` |
| `J` | Pan left | `GIMBAL:{pan-5}:{tilt}` |
| `L` | Pan right | `GIMBAL:{pan+5}:{tilt}` |
| `C` | Center gimbal | `CENTER` |
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

| Thread | Responsibility | Protocol |
|--------|----------------|----------|
| Main Thread | UI updates, event loop | PyQt6 |
| Video Thread | Receive live video feed | UDP Port 5006 |
| Command Thread | Send driving commands | UDP Port 5005 |
| Telemetry Thread | Send sensor data to cloud | HTTP POST |
| Gimbal Thread | Send pan/tilt commands | UDP Port 5005 |
| AI Chat Thread | Gemini API calls | HTTPS |

---

## 6. Communication Protocol

| Direction | Protocol | Port | Purpose |
|-----------|----------|------|---------|
| PC → ESP32 | UDP | 5005 | Low-latency control commands |
| ESP32 → PC | UDP | 5006 | Real-time MJPEG video + sensors |
| PC → Cloud | HTTP | REST API | Historical data storage |

### 6.1 UDP Commands (Port 5005)

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

### 6.2 Telemetry Data (Port 5006)

| Field | Format | Description |
|-------|--------|-------------|
| `temp` | `TEMP:{value}` | Temperature in °C |
| `humi` | `HUMI:{value}` | Humidity in % |
| `gas` | `GAS:{value}` | Gas concentration in ppm |
| `dist` | `DIST:{value}` | Obstacle distance in cm |
| `video` | JPEG bytes | Video frame data |

### 6.3 Resolution Change Architecture

#### Resolution Options

| Resolution | Width | Height | FPS | Use Case |
|------------|-------|--------|-----|----------|
| `640x480` | 640 | 480 | 30 FPS | Standard Fluid (default) |
| `800x600` | 800 | 600 | 25 FPS | Balanced quality |
| `1280x720` | 1280 | 720 | 15-20 FPS | High Detail |

#### Resolution Change Flow

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         RESOLUTION CHANGE FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────┐                                                               │
│   │  USER       │                                                               │
│   │  selects    │                                                               │
│   │  resolution │                                                               │
│   └──────┬──────┘                                                               │
│          │                                                                       │
│          ▼                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  DESKTOP APP                                                            │   │
│   │  1. Update UI Dropdown Selection                                        │   │
│   │  2. Send UDP Command to ESP32-CAM (RES:640:480)                        │   │
│   │  3. Stop Current Video Stream                                           │   │
│   │  4. Wait for ESP32-CAM Response (timeout: 2s)                          │   │
│   │     - ACK received: Resume video thread                                 │   │
│   │     - Timeout: Show error, retry or revert                             │   │
│   │  5. Update Stream Diagnostics                                           │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│          │                                                                       │
│          ▼                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  ESP32-CAM                                                              │   │
│   │  1. Receive RES command on UDP Port 5005                                │   │
│   │  2. Stop Camera Stream                                                  │   │
│   │  3. Reconfigure Camera Sensor                                           │   │
│   │  4. Send ACK to Desktop App (ACK:RES:{width}:{height}:OK)             │   │
│   │  5. Resume Camera Stream at new resolution                              │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Resolution Change State Machine

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

#### Error Handling

| Error | Detection | Recovery |
|-------|-----------|----------|
| No ACK received | Timeout (2s) | Revert to previous resolution |
| ACK:FAIL received | Parse response | Show error, keep old resolution |
| Stream corrupted | Frame decode error | Request keyframe, retry |
| Connection lost | No frames for 5s | Show "Disconnected" status |

---

## 7. Safety Features

### 7.1 Rover-Side Failsafe (HW-008)

- ESP32 firmware maintains last-received packet timestamp
- If no command received within 1.0 second → emergency motor stop
- Prevents runaway behavior during network drops

### 7.2 App-Side Connection Monitoring

- Monitors incoming UDP streams
- If packets stop arriving → UI shows "Disconnected"
- Initiates background reconnection without app restart

### 7.3 Auto-Brake System

- Ultrasonic sensor detects obstacle distance
- When distance < threshold → warning banner flashes
- Auto-brake engages (if enabled) to stop motors
- Configurable threshold: 5cm to 60cm

---

## 8. OTA Firmware Updates

### 8.1 OTA Hub

- Central OTA Hub: `http://rpi5.local/ota/`
- Supports all three microcontrollers
- Version metadata and progress tracking
- Automatic file renaming: `{device}-{version}-{info}-{client}.bin`
- Version verification after upload

### 8.2 OTA Headers

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
| Outline | Slate Gray | `#334155` |
| Outline Variant | Dark Slate | `#243147` |
| Primary | Blue | `#3b82f6` |
| Primary Container | Dark Blue | `#1d4ed8` |
| Secondary | Light Slate | `#94a3b8` |
| Status Safe | Emerald | `#10b981` |
| Status Warning | Amber | `#f59e0b` |
| Status Danger | Red | `#ef4444` |
| Text Primary | White Smoke | `#f1f5f9` |
| Text Secondary | Light Slate | `#94a3b8` |
| Text Muted | Gray | `#64748b` |

**Fonts:**
- Sans: Inter
- Mono: JetBrains Mono

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

## 13. Configuration

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

## 14. User Stories

| Persona | Need | Feature |
|---------|------|---------|
| Rover Pilot | Intuitive game-like driving | WASD controls |
| Rover Pilot | Inspect surroundings without turning | IJKL gimbal |
| Rover Pilot | Avoid obstacles due to lag | Low-latency FPV video |
| Safety Officer | Prevent collisions | Obstacle alarm + auto-brake |
| Safety Officer | Monitor environment | Real-time telemetry |
| Field Technician | Record discoveries | Snapshot with timestamp |
| Field Technician | Upgrade firmware wirelessly | OTA update |

---

## 15. Implementation Plan

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

## 16. Development Checklist

- [ ] **Phase 1:** UI wireframes & layout mockups
- [ ] **Phase 2:** Keyboard state machine mapping
- [ ] **Phase 3:** Multi-threaded architecture diagram
- [ ] **Phase 4:** Desktop application prototype
- [ ] **Phase 5:** Cloud API integration
- [ ] **Phase 6:** Safety testing (HW-008 compliance)
- [ ] **Phase 7:** End-to-end integration testing



---

## 18. Technical Reference — Worker Thread System

### 18.1 HTTP Worker

```python
# worker.py
class Worker(QThread):
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str)
    
    def __init__(self, task, url, payload=None, headers=None):
        super().__init__()
        self.task = task  # "get" or "post"
        self.url = url
        self.payload = payload
        self.headers = headers or {}
    
    def run(self):
        try:
            if self.task == "get":
                response = requests.get(self.url, headers=self.headers, timeout=10)
                self.finished.emit("get", response)
            elif self.task == "post":
                response = requests.post(self.url, json=self.payload, 
                                       headers=self.headers, timeout=10)
                self.finished.emit("post", response)
        except requests.exceptions.RequestException as e:
            self.error.emit(str(e))
```

### 18.2 Gemini Worker

```python
# gemini_worker.py
class GeminiWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    tool_called = pyqtSignal(str, dict)
    
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.client = None
        self.chat = None
    
    def init_chat(self):
        try:
            self.client = genai.Client(api_key=self.api_key)
            self.chat = self.client.chats.create(
                model='gemini-3.5-flash-lite',
                config={
                    'tools': [self.create_custom_charts],
                    'temperature': 0.7,
                }
            )
            return True
        except Exception as e:
            self.error.emit(f"Failed to initialize Gemini: {str(e)}")
            return False
    
    def send_message(self, text):
        if not self.chat:
            if not self.init_chat():
                return
        self._pending_message = text
        self.start()
    
    def run(self):
        try:
            if self._pending_message:
                response = self.chat.send_message(self._pending_message)
                self._pending_message = None
                if response.text:
                    self.finished.emit(response.text)
        except Exception as e:
            self.error.emit(f"Gemini error: {str(e)}")
```

### 18.3 Video Receiver Thread

```python
# video_feed.py
class VideoReceiverThread(QThread):
    frame_received = pyqtSignal(bytes)
    
    def __init__(self, port=5006):
        super().__init__()
        self.port = port
        self.running = False
    
    def run(self):
        self.running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", self.port))
        sock.settimeout(1.0)
        
        while self.running:
            try:
                data, addr = sock.recvfrom(65536)
                self.frame_received.emit(data)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Video receive error: {e}")
        
        sock.close()
    
    def stop(self):
        self.running = False
```

### 18.4 Command Sender

```python
# command.py
import socket

class CommandSender:
    def __init__(self, car_ip, port=5005):
        self.car_ip = car_ip
        self.port = port
    
    def send(self, command: str):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(command.encode("utf-8"), (self.car_ip, self.port))
            sock.close()
        except Exception as e:
            print(f"Error sending {command}: {e}")
```

---

## 19. Technical Reference — Configuration System

### 19.1 config.json Structure

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

### 19.2 Configuration Loading

```python
# config.py
import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "car_ip": "192.168.1.100",
    "cam_ip": "192.168.1.101",
    "cloud_api_url": "http://rpi5.local/api/v1",
    "device_uid": "rover-001",
    "gemini_api_key": "",
    "center_charts": {},
    "custom_charts": {},
    "custom_charts_normalize": {}
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"Failed to save config: {e}")
```

### 19.3 Layout Persistence Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Layout Persistence Flow                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  App Start                                                                  │
│     │                                                                       │
│     ▼                                                                       │
│  ┌─────────────┐                                                            │
│  │ load_config │──── Read config.json                                       │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────┐                                                            │
│  │ load_saved  │──── Restore chart groups                                   │
│  │ _config()   │     Restore API settings                                   │
│  └──────┬──────┘     Rebuild UI                                             │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────┐                                                            │
│  │  App        │──── User interacts with charts                             │
│  │  Running    │     (create, move, toggle, delete)                         │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼ (on each change)                                                  │
│  ┌─────────────┐                                                            │
│  │ save_config │──── Write to config.json                                   │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────┐                                                            │
│  │ App Exit    │──── Final save (if needed)                                 │
│  └─────────────┘                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 20. Technical Reference — Gemini AI Integration

### 20.1 Model Configuration

```python
# gemini_worker.py
MODEL = 'gemini-3.5-flash-lite'

def init_chat(self):
    self.client = genai.Client(api_key=self.api_key)
    self.chat = self.client.chats.create(
        model=MODEL,
        config={
            'tools': [self.create_custom_charts],
            'temperature': 0.7,
        }
    )
```

### 20.2 Function Calling — Chart Creation

```python
def create_custom_charts(self, custom_groups: dict, normalize: bool = False) -> str:
    """Creates custom charts based on user requests.
    
    Args:
        custom_groups: A dictionary where keys are chart titles and values are lists 
                       of sensor names.
                       Valid sensor names: "co2", "pm1.0", "pm2.5", "pm10", 
                       "temperature", "humidity", "pressure", "gas", "battery".
        normalize: If True, apply Min-Max normalization to scale all values to 0-1 range.
    
    Returns:
        Confirmation message.
    """
    self.tool_called.emit("create_custom_charts", {
        "custom_groups": custom_groups, 
        "normalize": normalize
    })
    return "Custom charts created successfully."
```

### 20.3 System Prompt

```python
system_prompt = f"""You are a sensor data analyst. Current readings:
- CO2: {latest.get('co2', {}).get('data', 'N/A')} ppm
- Temperature: {latest.get('temperature', {}).get('data', 'N/A')}°C
- Humidity: {latest.get('humidity', {}).get('data', 'N/A')}%
- Pressure: {latest.get('pressure', {}).get('data', 'N/A')} hPa
- PM1.0: {latest.get('pm1.0', {}).get('data', 'N/A')} µg/m³
- PM2.5: {latest.get('pm2.5', {}).get('data', 'N/A')} µg/m³
- PM10: {latest.get('pm10', {}).get('data', 'N/A')} µg/m³
- Gas: {latest.get('gas', {}).get('data', 'N/A')}
- Battery: {latest.get('battery', {}).get('data', 'N/A')}%

Respond in ~100 words. Use create_custom_charts function when user asks for charts.
Valid sensor keys: co2, pm1.0, pm2.5, pm10, temperature, humidity, pressure, gas, battery
"""
```

### 20.4 Example Interactions

**Example 1: Simple Chart Request**
```
User: "Show me temperature and humidity together"

Gemini Response: [Calls create_custom_charts({
    "Temperature & Humidity": ["temperature", "humidity"]
})]

Result: Single chart with both temperature and humidity lines
```

**Example 2: Normalized Comparison**
```
User: "Compare gas and CO2 on the same scale"

Gemini Response: [Calls create_custom_charts({
    "Gas vs CO2": ["gas", "co2"]
}, normalize=True)]

Result: Normalized chart (0-1 scale) showing relative trends
```

**Example 3: Multiple Charts**
```
User: "Create separate charts for each PM sensor"

Gemini Response: [Calls create_custom_charts({
    "PM1.0": ["pm1.0"],
    "PM2.5": ["pm2.5"],
    "PM10": ["pm10"]
})]

Result: Three separate charts for each particulate matter sensor
```

### 20.5 Ambiguity Rules

- "pm" / "pms" / "pm data" / "particulate matter" / "dust" → all three PM sensors
- "environment" → temperature, humidity, pressure
- "air quality" → co2, pm1.0, pm2.5, pm10

---

## 21. Technical Reference — Chart System

### 21.1 Chart Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Chart Update Flow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. fetch_data()                                                │
│     │                                                           │
│     ▼                                                           │
│  2. Worker("get", url) ─────────────────────────────────────┐  │
│     │                                                       │  │
│     ▼                                                       │  │
│  3. on_fetch_result(response)                               │  │
│     │                                                       │  │
│     ├──> update_cards(data)                                 │  │
│     │    └──> Updates sensor values in UI                   │  │
│     │                                                       │  │
│     └──> chart_widget.update_charts(history)                │  │
│          ├──> Updates all default charts                    │  │
│          └──> Updates all custom charts                     │  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 21.2 Normalization Algorithm

```python
def normalize_data(data_points):
    """Min-Max normalization to 0-1 range"""
    values = [p["data"] for p in data_points]
    if not values:
        return data_points
    
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        return [{"reading_time": p["reading_time"], "data": 0.5} 
                for p in data_points]
    
    normalized = []
    for p in data_points:
        norm_val = (p["data"] - min_val) / (max_val - min_val)
        normalized.append({
            "reading_time": p["reading_time"],
            "data": norm_val
        })
    return normalized
```

### 21.3 Slash Commands

**Command Syntax:**
```
/chart <sensor1> <sensor2> ... [flags]
```

**Available Flags:**
- `-n` : Normalize data to 0-1 range
- `-m <name>` : Set custom chart name
- `-d` : Display each sensor in separate charts

**Examples:**
```bash
# Basic chart
/chart co2 temperature

# Normalized chart
/chart gas co2 -n

# Custom name
/chart co2 temperature -m My Analysis

# Separate charts for PM sensors
/chart pm1.0 pm2.5 pm10 -d

# Combined flags
/chart temperature humidity -n -m Environment Data
```

**Command Parsing:**
```python
def _handle_chart_command(self, text):
    """Parse /chart commands with flags"""
    parts = text.split()
    if len(parts) < 2:
        self.append_chat("System", "Usage: /chart <sensors> [flags]")
        return
    
    sensors = []
    normalize = False
    separate = False
    custom_name = None
    
    i = 1
    while i < len(parts):
        if parts[i] == "-n":
            normalize = True
        elif parts[i] == "-d":
            separate = True
        elif parts[i] == "-m" and i + 1 < len(parts):
            custom_name = parts[i + 1]
            i += 1
        elif parts[i] in VALID_SENSORS:
            sensors.append(parts[i])
        else:
            if parts[i] in ["pm", "pms", "pm data", "particulate matter", "dust"]:
                sensors.extend(["pm1.0", "pm2.5", "pm10"])
            else:
                self.append_chat("System", f"Unknown sensor: {parts[i]}")
        i += 1
    
    if not sensors:
        self.append_chat("System", "No valid sensors specified")
        return
    
    chart_name = custom_name or "Custom Chart"
    
    if separate:
        for sensor in sensors:
            self.custom_charts[f"{sensor.upper()} Chart"] = [sensor]
            if normalize:
                self.custom_charts_normalize[f"{sensor.upper()} Chart"] = True
    else:
        self.custom_charts[chart_name] = sensors
        if normalize:
            self.custom_charts_normalize[chart_name] = True
    
    self.save_current_config()
    self.chart_widget._build_charts()
    self.append_chat("System", f"Created chart(s) for: {', '.join(sensors)}")
```

---

## 22. Technical Reference — Drag and Drop System

### 22.1 MIME Data Format

```python
CHART_MIME_TYPE = "application/x-chart"

# Data format: JSON with chart configuration
{
    "source": "center" | "custom",
    "chart_name": "Air Quality",
    "sensors": ["co2", "pm1.0"],
    "normalize": false
}
```

### 22.2 Drop Zone Handling

```python
def _on_drop(self, event):
    """Handle drop events for chart transfer"""
    mime_data = event.mimeData()
    
    if mime_data.hasFormat(CHART_MIME_TYPE):
        chart_data = json.loads(mime_data.data(CHART_MIME_TYPE).data().decode())
        
        if chart_data["source"] == "center":
            self.custom_charts[chart_data["chart_name"]] = chart_data["sensors"]
        else:
            del self.custom_charts[chart_data["chart_name"]]
            self.center_charts[chart_data["chart_name"]] = chart_data["sensors"]
        
        self.save_current_config()
        self._build_charts()
```

---

## 23. Technical Reference — Keyboard Control System

### 23.1 Key Event Handling

```python
def keyPressEvent(self, event):
    if event.isAutoRepeat():
        return
    
    if self._is_text_focused():
        return super().keyPressEvent(event)
    
    key_map = {
        Qt.Key.Key_W: "DRIVE:{speed}:FORWARD",
        Qt.Key.Key_S: "DRIVE:{speed}:BACKWARD",
        Qt.Key.Key_A: "STEER:LEFT",
        Qt.Key.Key_D: "STEER:RIGHT",
        Qt.Key.Key_Space: "STOP",
        Qt.Key.Key_I: "GIMBAL:{pan}:{tilt_up}",
        Qt.Key.Key_K: "GIMBAL:{pan}:{tilt_down}",
        Qt.Key.Key_J: "GIMBAL:{pan_left}:{tilt}",
        Qt.Key.Key_L: "GIMBAL:{pan_right}:{tilt}",
        Qt.Key.Key_C: "CENTER",
    }
    
    command = key_map.get(event.key())
    if command:
        self.send_command(command)
    else:
        super().keyPressEvent(event)
```

### 23.2 Gimbal Control with Angle Tracking

```python
class GimbalController:
    def __init__(self):
        self.pan = 90
        self.tilt = 90
        self.step = 5
        self.min_angle = 0
        self.max_angle = 180
    
    def move(self, direction):
        if direction == "up":
            self.tilt = min(self.tilt + self.step, self.max_angle)
        elif direction == "down":
            self.tilt = max(self.tilt - self.step, self.min_angle)
        elif direction == "left":
            self.pan = max(self.pan - self.step, self.min_angle)
        elif direction == "right":
            self.pan = min(self.pan + self.step, self.max_angle)
        
        return f"GIMBAL:{self.pan}:{self.tilt}"
    
    def center(self):
        self.pan = 90
        self.tilt = 90
        return "CENTER"
```

---

## 24. Technical Reference — ESP32 UDP Protocol

### 24.1 Command Format (PC → ESP32, Port 5005)

```python
# All commands are UTF-8 encoded strings sent via UDP

# Drive commands
"DRIVE:180:FORWARD"    # Speed 180, forward
"DRIVE:180:BACKWARD"   # Speed 180, backward
"STEER:LEFT"           # Spin left
"STEER:RIGHT"          # Spin right
"STOP"                 # Emergency stop

# Gimbal commands
"GIMBAL:90:90"         # Pan 90°, Tilt 90°
"CENTER"               # Reset to 90°, 90°

# Camera commands
"RES:640:480"          # Set resolution
"FLIP:h"               # Flip horizontal
"FLIP:v"               # Flip vertical
"SNAPSHOT"             # Capture frame

# OTA command
"OTA:1.0.0"            # Trigger firmware update
```

### 24.2 Telemetry Format (ESP32 → PC, Port 5006)

```python
# Sensor data is sent as text strings
"TEMP:25.4"            # Temperature in °C
"HUMI:65.2"            # Humidity in %
"GAS:450"              # Gas concentration in ppm
"DIST:34.5"            # Obstacle distance in cm

# Video data is sent as raw JPEG bytes
# Each packet contains one complete JPEG frame
```

### 24.3 Resolution Change ACK

```python
# ESP32-CAM responds with ACK after changing resolution
"ACK:RES:640:480:OK"   # Success
"ACK:RES:640:480:FAIL" # Failure
```

---

## 25. Technical Reference — Cloud API Integration

### 25.1 Telemetry POST

**Endpoint:** `POST /api/v1/telemetry`

**Request:**
```python
import requests

url = "http://rpi5.local/api/v1/telemetry"
payload = {
    "device_uid": "rover-001",
    "recorded_at": "2026-09-03T10:00:00.123Z",
    "temperature_c": 25.4,
    "humidity_pct": 61.2,
    "gas_ppm": 128.0,
    "distance_cm": 34.5,
    "auto_brake": false
}
response = requests.post(url, json=payload, timeout=10)
```

**Response:**
```json
{
  "success": true,
  "device_id": 1,
  "recorded_at": "2026-09-03T10:00:00.123Z",
  "duplicate": false
}
```

### 25.2 Latest Reading GET

**Endpoint:** `GET /api/v1/rovers/{id}/latest`

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

### 25.3 Readings History GET

**Endpoint:** `GET /api/v1/rovers/{id}/readings`

**Parameters:** `limit`, `start`, `end`, `order`

**Response:**
```json
{
  "device_id": 1,
  "count": 2,
  "readings": [
    {
      "recorded_at": "2026-09-03T10:00:00.123Z",
      "temperature_c": 25.3,
      "humidity_pct": 61.0,
      "gas_ppm": 127.0,
      "distance_cm": 40.2,
      "auto_brake": false
    }
  ]
}
```

### 25.4 Summary GET

**Endpoint:** `GET /api/v1/rovers/{id}/summary`

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

### 25.5 Health Check GET

**Endpoint:** `GET /api/v1/health`

**Response:**
```json
{ "status": "ok", "database": "ok", "api": "ok", "uptime_seconds": 84213 }
```

---

## 26. Technical Reference — OTA Firmware Updates

### 26.1 OTA Hub

- **Endpoint:** `http://rpi5.local/ota/`
- **Method:** HTTP POST with multipart/form-data
- **Key:** `X-OTA-Key: shodai-haru-2026-8-25`

### 26.2 Upload Implementation

```python
# ota.py
import requests

def upload_firmware(file_path, version, device="esp32-car"):
    url = "http://rpi5.local/ota/"
    headers = {"X-OTA-Key": "shodai-haru-2026-8-25"}
    
    with open(file_path, "rb") as f:
        files = {"file": (f"{device}-{version}-ota.bin", f)}
        data = {"version": version, "device": device}
        response = requests.post(url, files=files, data=data, headers=headers)
    
    return response.json()
```

### 26.3 File Naming Convention

```
{device}-{version}-{info}-{client}.bin
Example: esp32-car-1.0.0-ota-haru.bin
```

---

## 27. Technical Reference — Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyQt6 | 6.x | Desktop GUI framework |
| requests | 2.x | HTTP requests |
| matplotlib | 3.x | Chart rendering |
| google-genai | 0.3+ | Gemini AI integration |
| socket | stdlib | UDP communication |
| json | stdlib | Configuration persistence |

---

## 28. Technical Reference — Troubleshooting

### 28.1 ESP32 Connection Issues

**Car Not Responding:**
1. Check ESP32-CAR IP is correct in config
2. Verify UDP port 5005 is open
3. Check firewall settings
4. Test with: `echo -n "STOP" | nc -u <car_ip> 5005`

**Video Feed Not Working:**
1. Verify ESP32-CAM IP is correct
2. Check UDP port 5006 is bound
3. Ensure JPEG encoding is enabled
4. Test with: `nc -lu <cam_ip> 5006 > test.jpg`

### 28.2 Cloud API Issues

**Connection Refused:**
- Check if RPi5 is running
- Verify API URL is correct
- Test with: `curl http://rpi5.local/api/v1/health`

**Invalid JSON Response:**
- Check server logs
- Verify API endpoint exists
- Ensure proper HTTP headers

### 28.3 Performance Issues

**High CPU Usage:**
- Reduce polling interval (default: 1 second)
- Lower video quality
- Reduce video resolution (default: 640x480)

**Memory Leaks:**
- Ensure QPixmap conversion is efficient
- Check QThread lifecycle
- Monitor frame buffer releases

---

## 29. Technical Reference — Development Guide

### 29.1 Adding New Sensors

1. Add sensor key to `DEFAULT_CONFIG` in `config.py`
2. Update sensor cards in `sensors.py`
3. Add to chart groups in `config.py`
4. Update system prompt in `gemini_worker.py`

### 29.2 Adding New Commands

1. Add command to `command.py`
2. Update ESP32 firmware `ProcessCommand()` method
3. Add to key mapping in `app.py`
4. Test with log panel

### 29.3 Extending AI Features

1. Add new function to `GeminiWorker` class
2. Register with `tools` parameter
3. Handle `tool_called` signal
4. Update system prompt

---

## 30. Technical Reference — Data Flow Diagrams

### 30.1 Complete System Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Complete Data Flow                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    UDP 5005     ┌─────────────┐    UDP 5006    ┌─────────┐│
│  │  Desktop    │ ──────────────> │  ESP32-CAR  │ <──────────── │  ESP32  ││
│  │  App        │    Commands     │  (Motors)   │   Telemetry   │  CAM    ││
│  └──────┬──────┘                 └─────────────┘               └─────────┘│
│         │                                                                   │
│         │ HTTP POST                                                         │
│         ▼                                                                   │
│  ┌─────────────┐                                                            │
│  │  Cloud      │                                                            │
│  │  Backend    │                                                            │
│  │  (RPi5)     │                                                            │
│  └─────────────┘                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 30.2 Thread Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Thread Communication Flow                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Main Thread                                                                │
│     │                                                                       │
│     ├──> Command Thread ──> UDP 5005 ──> ESP32                              │
│     │                                                                       │
│     ├──> Video Thread <── UDP 5006 <── ESP32-CAM                            │
│     │                                                                       │
│     ├──> Telemetry Thread ──> HTTP POST ──> Cloud                           │
│     │                                                                       │
│     ├──> Gimbal Thread ──> UDP 5005 ──> ESP32                               │
│     │                                                                       │
│     └──> AI Chat Thread ──> HTTPS ──> Gemini API                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
