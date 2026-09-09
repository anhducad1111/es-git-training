# Space Rover Desktop Teleoperation Cockpit
## Phase 1 — UI Design & Plan Proposal

**Document version:** v1.0
**Date:** 2026-09-03
**Author:** Haru Sakihara (Python Desktop App Engineer Intern)
**Status:** Awaiting mentor review. No implementation code has been written.

---

## 1. Purpose

This proposal presents the UI design and implementation plan for the Space Rover Desktop Teleoperation Cockpit, a PyQt6 application for remote piloting an ESP32-based rover.

**Deliverables:**
1. UI wireframes and screen layout design
2. Keyboard event and state machine mapping
3. Thread architecture diagram
4. Implementation plan

**Reference:** For detailed technical specifications, see `HARU-PRD-DESIGN-PROPOSAL.md`.

---

## 2. System Overview

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
│             │   │  Gimbal)    │   │ Data        │
└─────────────┘   └─────────────┘   └─────────────┘
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
│                                                  │  │ [🚶 Follow Mode]       │ │
├──────────────────────────────────────────────────┤  └────────────────────────┘ │
│ BOTTOM CONTROLS                                                         │
│ ┌──────────────────────┐ ┌──────────────────┐ ┌────────────────────┐ ┌────────┐ │
│ │ Motor Speed          │ │ Auto-Brake [ON]  │ │ Gimbal: Pan 90°   │ │ W/S    │ │
│ │ 220 (86%) [====]     │ │ Threshold: 30cm  │ │        Tilt 90°   │ │ A/D    │ │
│ │                      │ │ [====]           │ │ [Center]           │ │[STOP]  │ │
│ └──────────────────────┘ └──────────────────┘ └────────────────────┘ └────────┘ │
├──────────────────────────────────────────────────────────────────────────────────┤
│ [LOG] Click to expand/collapse • 4 Events                                      │
│ ┌──────────────────────────────────────────────────────────────────────────────┐ │
│ │ 10:00:01 [CONNECTED] WebSocket connected to 192.168.1.100 (ESP32-MCU)      │ │
│ │ 10:00:02 [VIDEO]      Stream active at 640x480 @ 30 FPS                    │ │
│ │ 10:00:05 [TELEMETRY]  Chassis Temp 28.5°C, Dist 45cm, Humidity 65%         │ │
│ │ 10:00:08 [SAFETY]     Auto-brake threshold set to 30 cm                    │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Diagnostics View

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
│   └──────────────────────────────────────────┘    │  │                      │ │
│                                                    │  │ ┌──────────────────┐ │ │
│ 🌫 Air Quality & 📏 Obstacle Proximity             │  │ │ create_custom_   │ │ │
│   CO2: 450 ppm    Sonar: 45 cm                    │  │ │ charts [0.12s]   │ │ │
└────────────────────────────────────────────────────┘  └──────────────────────┘ │
```

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

### 4.2 Key Mapping

| Key | Action | WebSocket Command (Plain Text) |
|-----|--------|--------------------------------|
| `W` | Drive forward | `"forward"` or `"drive:speed,0"` |
| `S` | Drive backward | `"backward"` or `"drive:-speed,0"` |
| `A` | Spin left | `"left"` or `"drive:0,-speed"` |
| `D` | Spin right | `"right"` or `"drive:0,speed"` |
| `Space` | Emergency stop | `"stop"` |
| `I` | Tilt up | `"servo:pan,tilt+5"` |
| `K` | Tilt down | `"servo:pan,tilt-5"` |
| `J` | Pan left | `"servo:pan-5,tilt"` |
| `L` | Pan right | `"servo:pan+5,tilt"` |
| `C` | Center gimbal | `"servo:90,90"` |

---

## 5. Thread Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     THREAD ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────┐                                        │
│   │   MAIN THREAD       │ ◄── PyQt6 Event Loop                  │
│   └──────────┬──────────┘                                        │
│              │                                                   │
│   ┌──────────┴──────────┐                                        │
│   ▼                     ▼                                        │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│ │ VIDEO       │  │ COMMAND     │  │ TELEMETRY   │              │
│ │ THREAD      │  │ THREAD      │  │ THREAD      │              │
│ │ (ESP32-CAM) │  │ (ESP32-MCU) │  │ (Cloud API) │              │
│ └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│        │                │                │                      │
│        ▼                ▼                ▼                      │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                    ESP32 ROVER                           │  │
│   │  ┌─────────────┐  ┌─────────────┐                      │  │
│   │  │ ESP32-CAM   │  │ ESP32-MCU   │                      │  │
│   │  │ WS: Video   │  │ WS: Cmd/Tlm │                      │  │
│   │  └─────────────┘  └─────────────┘                      │  │
│   └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Plan

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

## 7. Next Steps

1. **Duke reviews this proposal** → Approves or requests changes
2. **Official API documentation unlocked** → ESP32 WebSocket protocol details
3. **Implementation begins** → Following Phase 3+ of the plan

---

## 8. Duke's Review Notes (Phase 3+)

### 8.1 Communication Protocol

| Priority | Item | Note |
|----------|------|------|
| 🔴 Must | WebSocket message format | Use plain text: `"forward"`, `"servo:90,65"`, `"drive:200,-50"` |
| 🔴 Must | Default speed 220, slider min 150 | 6WD skid-steer chassis cannot turn below PWM 220 |


### 8.2 Subsystem Health

| Priority | Item | Note |
|----------|------|------|
| 🟡 Should | Subsystem health | Poll `GET /api/telemetry` on ESP32-Car directly |

### 8.3 AI Chat

| Priority | Item | Note |
|----------|------|------|
| 🟡 Should | AI Chat | Call Ollama at `http://rpi5.local:11434/api/generate` (local network) |
| 🟡 Should | Panel name | Rename to "Local AI Sensor Analyst (Ollama)" |
| 🟡 Should | Models | Use `phi3:mini` (3.8B) or `llama3.2:3b` on RPi5 |

### 8.4 Media & Snapshots

| Priority | Item | Note |
|----------|------|------|
| 🟡 Should | Media upload | Snapshot uploads to `POST /api/v1/rovers/{uid}/media` |

### 8.5 Cloud API

| Item | Value |
|------|-------|
| Base URL | `http://192.168.1.116/es-git-training/rover-telemetry-backend/public/api` |
| Endpoints | 17 endpoints (telemetry, rovers, media, system, config) |

### 8.6 Person-Following (Future)

| Priority | Item | Note |
|----------|------|------|
| 🟡 Future | Follow Mode button | Add toggle button in sidebar |
| 🟡 Future | Endpoints | `POST /follow/start`, `POST /follow/stop`, `GET /follow/status` |

### 8.7 Architecture Notes

| Item | Note |
|------|------|
| Authentication | None in Phase 1 |
| Clock sync | Gateway applies UTC timestamp on receipt |

---

## 9. Reference Documents

| Document | Purpose |
|----------|---------|
| `HARU-PRD-DESIGN-PROPOSAL.md` | Full technical specification (28 sections) |
| `wireframe.md` | Detailed UI component descriptions |
| `docs/README.md` | Documentation index |

> **Note:** If any part of this proposal plan is vague, please refer to `HARU-PRD-DESIGN-PROPOSAL.md` for detailed specifications.
