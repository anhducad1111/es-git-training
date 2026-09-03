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

## 2. UI Wireframes

### 2.1 Main View (Default)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TOP BAR                                            │
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
│             CENTER VIDEO VIEWPORT                 │  ┌────────────────────────┐ │
│                                                  │  │  🌫 AIR QUALITY        │ │
│   ┌─────────────────────────────────────────┐    │  │  ██████░░░░░ 450 ppm   │ │
│   │ 🟢 30.0 FPS   │   5 ms   │  📏 45 cm │    │  └────────────────────────┘ │
│   │─────────────────────────────────────────│    │  ┌────────────────────────┐ │
│   │                                         │    │  │  📏 OBSTACLE           │ │
│   │              ╋ CROSSHAIR               │    │  │  ██████░░░░░ 45 cm     │ │
│   │                                         │    │  │  ⚠ AUTO-BRAKE: ON     │ │
│   │                                         │    │  └────────────────────────┘ │
│   │                                         │    │  ┌────────────────────────┐ │
│   └─────────────────────────────────────────┘    │  │  ⚠ SAFETY ALARM        │ │
│                                                  │  │  AUTO-BRAKE: [ON]      │ │
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

### 2.2 AI Chat View (💬 Active)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TOP BAR                                            │
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
│  │  │     └────────────────────────────┘    │    │  │ [Type... ] [Send]      │ │
│  │  │      12:00  12:05  12:10  12:15      │    │  └────────────────────────┘ │
│  │  └──────────────────────────────────┘    │    │  ┌─────┐                   │
│  └──────────────────────────────────────────┘    │  │ ✖  │ ← FLOATING BUTTON  │
│                                                  │  └─────┘   (active)        │
│  ┌──────────────────────────────────────────┐    │  ┌────────────────────────┐ │
│  │  📊 Air Quality (Gas)                   │    │  │  🎯 GIMBAL CONTROL     │ │
│  │  ┌──────────────────────────────────┐    │    │  │  Pan:   [====] 90°    │ │
│  │  │  500┤      ╭──╮                  │    │    │  │  Tilt:  [====] 90°    │ │
│  │  │     │    ╭─╯  ╰─╮  ╭───╮        │    │    │  │  [C] Center Gimbal    │ │
│  │  │  400┤───╯        ╰─╯   ╰──      │    │    │  └────────────────────────┘ │
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

### 2.3 Video Overlay Status Bar

```
┌─────────────────────────────────────────────────────────────────┐
│ 🟢 30.0 FPS   │   5 ms   │  📏 45 cm │  🌡 28.5°C │  💧 65% │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Keyboard State Machine

### 3.1 Drive Control

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

### 3.2 Gimbal Control

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

### 3.3 Key Mapping

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

---

## 4. Thread Architecture

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
│              ├─────────────────────────────────────────────────┤ │
│              │                     │                            │ │
│              ▼                     ▼                            │ │
│                                                                  │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ │ VIDEO       │  │ TELEMETRY   │  │ COMMAND     │  │ GIMBAL      │
│ │ THREAD      │  │ THREAD      │  │ THREAD      │  │ THREAD      │
│ │             │  │             │  │             │  │             │
│ │ recv UDP    │  │ HTTP POST   │  │ UDP send    │  │ UDP send    │
│ │ port 5006   │  │ to cloud    │  │ on keypress │  │ on keypress │
│ └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
│        │                │                │                │
│        ▼                ▼                ▼                ▼
│   ┌─────────────────────────────────────────────────────────────┐
│   │                    ESP32 ROVER                               │
│   └─────────────────────────────────────────────────────────────┘
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Thread | Responsibility |
|--------|----------------|
| Main | UI event loop, widget updates |
| Video | Receive UDP video frames (Port 5006) |
| Command | Send drive/steer commands (Port 5005) |
| Telemetry | POST sensor data to cloud |
| Gimbal | Send pan/tilt commands |
| AI Chat | Call Gemini API |

---

## 5. Implementation Plan

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


