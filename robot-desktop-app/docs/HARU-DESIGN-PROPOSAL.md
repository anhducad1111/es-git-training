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
├──────────────────────────────────────────────────┤  └────────────────────────┘ │
│ BOTTOM CONTROLS                                                         │
│ ┌──────────────────────┐ ┌──────────────────┐ ┌────────────────────┐ ┌────────┐ │
│ │ Motor Speed          │ │ Auto-Brake [ON]  │ │ Gimbal: Pan 90°   │ │ W/S    │ │
│ │ 180 (70%) [====]     │ │ Threshold: 30cm  │ │        Tilt 90°   │ │ A/D    │ │
│ │                      │ │ [====]           │ │ [Center]           │ │[STOP]  │ │
│ └──────────────────────┘ └──────────────────┘ └────────────────────┘ └────────┘ │
├──────────────────────────────────────────────────────────────────────────────────┤
│ [LOG] Click to expand/collapse • 4 Events                                      │
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
│   └──────────────────────────────────────────┘    │  │                      │ │
│                                                    │  │ ┌──────────────────┐ │ │
│ 🌫 Air Quality & 📏 Obstacle Proximity             │  │ │ create_custom_   │ │ │
│   CO2: 450 ppm    Sonar: 45 cm                    │  │ │ charts [0.12s]   │ │ │
└────────────────────────────────────────────────────┘  └──────────────────────┘ │
                              ┌─────┐
                              │ ✖   │ ← FLOATING BUTTON (purple, returns to Main)
                              └─────┘
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

## 8. Reference Documents

| Document | Purpose |
|----------|---------|
| `HARU-PRD-DESIGN-PROPOSAL.md` | Full technical specification (28 sections) |
| `wireframe.md` | Detailed UI component descriptions |
| `docs/README.md` | Documentation index |
