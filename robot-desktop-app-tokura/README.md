# Space Rover Desktop Teleoperation Cockpit (tokura branch)

A real-time IoT rover teleoperation system featuring a PyQt6 Windows desktop controller, ESP32-based hardware rover, and cloud-backed data pipeline.

This is the **tokura** variant, developed in parallel with the sibling `robot-desktop-app` project. It shares the same core cockpit (driving, gimbal, telemetry, cloud sync) but carries its own set of experimental features around car-follows-car autonomy, image super-resolution, and file-based session logging. See [§10 Relationship to `robot-desktop-app`](#10-relationship-to-robot-desktop-app) for how the two diverge.

---

## docs/ — Design & Specification Documents

The `docs/` folder contains planning, design, and technical documents for this application.

| File | Purpose |
|------|---------|
| `INDEX.md` | Documentation index and quick reference |
| `APP_TECHNICAL.md` | Technical deep dive into the main cockpit app (classes, data flow, follow mode) |
| `TECHNICAL_DOCUMENT.md` | Technical deep dive into `app2`'s Stanley-control car-follow-car mode |
| `HARU-PRD-DESIGN-PROPOSAL.md`, `HARU-DESIGN-PROPOSAL.md` | Design proposals submitted for approval |
| `wireframe.md` | UI wireframes and component descriptions |
| `CONFIGURATION.md`, `CLOUD_API.md`, `ESP32_API.md` | Integration references |
| `OBJECT_DETECTION.md`, `SNAPSHOT.md`, `IMAGE_PROCESSING.md`, `VIDEO_RECORDING.md`, `GIMBAL_CONTROL.md`, `SPEED_CONTROL.md`, `UI_LAYOUT.md` | Feature-specific references |

Follow-mode's inference and control behavior (formerly three separate early design-notes files, now superseded and removed) is documented in `APP_TECHNICAL.md` §3.2/§3.3/§12 (control) and `rccar_pose_inference/README.md` (inference pipeline).

---

## 1. Executive Summary

The **Space Rover Desktop Teleoperation Cockpit** is the primary command and control hub used by human operators to remotely pilot the Space Rover in real-time.

The application integrates high-speed manual driving controls, 2-axis precision camera gimbal steering, zero-lag first-person view (FPV) video streaming, real-time environmental telemetry, autonomous car-follow-car tracking, and cloud-backed history/AI analysis into a single, cohesive interface.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PyQt6 Desktop App                         │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
  WebSocket         WebSocket            HTTP REST
  (Video)           (Commands/            (Cloud API,
                     Telemetry)            PID params)
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ ESP32-CAM   │   │ ESP32-MCU   │   │  Cloud API  │
│ (Camera)    │   │ (Sensors,   │   │   (RPi5)    │
│ Binary JPEG │   │  Motors,    │   │ Historical  │
│ frames      │   │  Gimbal)    │   │ Data        │
└─────────────┘   └─────────────┘   └─────────────┘
```

### Thread Architecture

| Thread | Responsibility | Protocol |
|--------|----------------|----------|
| Main Thread | UI updates, event loop | PyQt6 |
| Video Thread | Receive video frames from ESP32-CAM | WebSocket (binary, local) |
| Command Thread | Send commands to ESP32-MCU | WebSocket (text, local) |
| Telemetry Poller (`telemetry_poller.py`) | Poll `/api/telemetry` on an interval; pauses while driving | HTTP REST (local) |
| Cloud Worker (`cloud_worker.py`) | Fire-and-forget async GET/POST/DELETE, e.g. debounced PID updates | HTTP REST (local) |
| Super-Resolution Worker (`super_resolution.py`) | Upscale snapshots via Hugging Face API, falls back to bicubic | HTTP / local |
| AI Chat Thread | Ollama on RPi5 | HTTP (local) |

---

## 3. Communication Protocol

| Direction | Protocol | Purpose |
|-----------|----------|---------|
| PC → ESP32-CAM | WebSocket | Receive video stream (binary JPEG) |
| PC → ESP32-MCU | WebSocket | Send commands (JSON/plain text), receive telemetry |
| PC → ESP32-MCU | HTTP REST (`telemetry_poller.py`) | Poll `/api/telemetry` for sensor snapshot |
| PC → Cloud | HTTP REST | Store/retrieve historical data |

### WebSocket / REST Commands

```
"forward" | "backward" | "left" | "right" | "stop"
"drive:200,0"          # speed 200, straight forward
"speed:200"            # set target speed (80-255)
"servo:90,90"          # pan 90°, tilt 90°
```

```
GET /speed?val={80-255}
GET /api/distance
GET /api/distance?brake={0|1}
GET /api/telemetry
GET /servo/angle?pan={0-180}&tilt={0-180}
GET /api/pid?kp=&ki=&kd=&enabled=&bias=
```

### PID Parameter Debouncing

Dragging the gyro-straight PID sliders no longer fires a synchronous HTTP request per pixel of drag. `_schedule_pid_apply()` restarts a 400ms single-shot `QTimer`; only when the slider settles does `_apply_pid_params()` fire, and it sends the request through `CloudWorker` (a `QThread`) so the GUI thread is never blocked.

---

## 4. Car-Follow-Car Autonomy

Two independent implementations exist:

- **Root-level follow mode** (`follow_detector.py` + `follow_controller.py`): YOLOv8-pose detection driving a continuous `drive:v,w` controller — a distance PID (Kp/Ki/Kd) blended with a heading term (image yaw error + gimbal pan offset), running through its own 8-state machine (FOLLOWING/TURNING/WAITING/SEARCHING/HEAD_ON_HOLD/HOLDING/APPROACHING_BLIND/LOST_TIMEOUT) and gimbal feed-forward compensation during turns. It is driven directly from the main cockpit UI. See `docs/APP_TECHNICAL.md` §12-14 for the current control-loop breakdown. Note: a comment in the code references a "Stanley/PID hybrid," but no Stanley steering law is actually used here — see the caveat below.
- **`app2/`**: A standalone experimental app (own `README.md`, `requirements.txt`, entry point) using ArUco/CharUco marker calibration and a **real Stanley control** implementation with its own 4-state machine (FOLLOWING / TURNING / WAITING / SEARCHING), including reverse/backward handling for when the lead car turns around. Its "rover" I/O is currently just `print()` — it is not wired to the real WebSocket/ESP32 path. See `docs/TECHNICAL_DOCUMENT.md` for the full control-law breakdown.

Shared pose-estimation logic (Kalman filtering, ArUco fusion, gimbal-angle correction) lives in `rccar_pose_inference/`, duplicated under `car_follow_car/rccar_pose_inference/` for the in-progress car-follow-car workspace.

Model training assets live in `follow-mode/` (`annotate_data.py`, `train_angle_model.py`, `last.pt`, `angle_mlp.pth`); the Colab notebook used for training is linked in `follow-mode/README.md`.

Follow-mode sessions are logged to `logs/follow_<timestamp>.log` (created on demand by `app.py`) since the in-app log widget only keeps a limited scrollback.

---

## 5. Image Processing & Snapshots

- `image_processor.py` — filter pipeline (Auto Correct, Contrast, Denoise, Bicubic)
- `super_resolution.py` — 4x upscaling of snapshots via a Hugging Face Gradio Space API (`hichi2-reals`), with automatic fallback to local PIL bicubic + unsharp mask if the API call fails or no `hf_token` is configured
- `stream_quality.py` — adaptive video stream quality control

---

## 6. Safety Features

### Rover-Side Failsafe

- ESP32 firmware maintains last-received packet timestamp
- If no command received within 1.0 second → emergency motor stop
- (This is documented ESP32-firmware behavior; no firmware source lives in this repo, so it cannot be verified from the app codebase alone — confirm against the firmware if depending on it for a safety-critical change.)

### App-Side Connection Monitoring

- Monitors incoming WebSocket streams; on drop, UI shows "Disconnected" and reconnects in the background

### Auto-Brake System

- Ultrasonic sensor detects obstacle distance; below threshold, warning banner flashes and (if enabled) auto-brake stops motors
- Configurable threshold: 10cm–100cm

---

## 7. Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `W` / `S` | Drive forward / backward |
| `A` / `D` | Spin left / right |
| `Space` | Emergency stop |
| `I` / `K` | Gimbal tilt up / down |
| `J` / `L` | Gimbal pan left / right |
| `C` | Center gimbal |
| `Shift` / `Ctrl` | Speed +/- |

---

## 8. File Structure

```
robot-desktop-app-tokura/
├── main.py                    # Application entry point
├── app.py                     # Main window, UI wiring, PID debounce, follow-mode logging
├── config.py / config.json    # Configuration load/save
├── styles.py                  # UI styling
├── connection_manager.py      # WebSocket/HTTP connection management
├── rover_ws.py                # WebSocket client (drive/servo commands)
├── mjpeg_receiver.py          # Video stream receiver
├── video_manager.py / video_worker.py / video_feed.py
├── stream_quality.py          # Adaptive stream quality
├── super_resolution.py        # Snapshot 4x upscaling (HF API + bicubic fallback)
├── image_processor.py         # Filter pipeline
├── hog_detector.py / yolo_detector.py / detection_manager.py
├── follow_detector.py         # YOLOv8-pose car detection
├── follow_controller.py       # PID-based follow control
├── esp32_api.py                # ESP32 REST client
├── cloud_api.py / cloud_manager.py / cloud_worker.py   # Cloud telemetry + debounced async requests
├── telemetry_poller.py        # Periodic /api/telemetry polling
├── input_handler.py           # Keyboard/mouse input
├── remote_control_server.py   # WebSocket relay server
├── ollama_chat.py             # Local AI (Ollama) chat integration
├── rccar_pose_inference/      # Shared pose-estimation package (Kalman, ArUco fusion, gimbal transform)
├── car_follow_car/            # In-progress car-follow-car workspace (duplicates rccar_pose_inference)
├── follow-mode/               # Model training pipeline (annotate/train scripts, weights)
├── app2/                      # Standalone Stanley-control car-follow-car experimental app
├── views/                     # UI panels (header, main view, diagnostics, sidebar, etc.)
├── widgets/                   # Custom widgets (gimbal HUD, speed meter, sensor gauges)
├── design/                    # HTML design mockups
├── docs/                      # Documentation (see index above)
├── logs/                      # Per-session follow-mode log files
├── snapshot/ / recordings/    # Captured frames / recorded video
├── stubs/ / tests/            # Test doubles and unit tests
└── yolov8n.pt / yolov8m.pt    # YOLOv8 model weights
```

---

## 9. Configuration

### Config File (`config.json`)

```json
{
  "car_ip": "192.168.1.113",
  "cam_ip": "192.168.1.117",
  "cloud_api_url": "http://<cloud-host>/api/v1",
  "device_uid": "rover-001",
  "ollama_url": "http://rpi5.local:11434/api/generate",
  "follow_mode_url": "http://rpi5.local/follow/start",
  "motor_speed": 220,
  "auto_brake": true,
  "brake_threshold": 30,
  "center_charts": {},
  "custom_charts": {},
  "custom_charts_normalize": {},
  "hf_token": "<your-huggingface-token>",
  "remote_control_port": 8765
}
```

> `hf_token` is only required to use the Hugging Face super-resolution API; without it, snapshots fall back to local bicubic upscaling. **Never commit a real token** — treat `config.json` as local/untracked configuration.

### Installation

```bash
pip install -r requirements.txt
```

(`requirements.txt`: PyQt6, websocket-client, websockets, requests, opencv-python, numpy)

### Usage

```bash
python main.py
```

---

## 10. Relationship to `robot-desktop-app`

`robot-desktop-app-tokura` and `robot-desktop-app` are sibling projects with near-identical core file layouts. Notable differences:

| Area | `robot-desktop-app-tokura` | `robot-desktop-app` |
|------|------------------------------|----------------------|
| PID slider updates | `CloudWorker` + 400ms debounce (this repo) | Adopted the same pattern from tokura |
| Snapshot upscaling | `super_resolution.py` (HF API + bicubic fallback) | Not present |
| Telemetry | `telemetry_poller.py` (periodic REST poll) | Push-based via WebSocket only |
| Follow-mode logging | Persists to `logs/follow_<timestamp>.log` | Not present |
| Car-follow-car workspace | `car_follow_car/` (in progress) | — |
| AI integration | Ollama only | Ollama + Gemini (`gemini_chat.py`) |
| Rover control model | PID-based (`follow_controller.py`) | PID-based, plus ρ-α-β control experiments (`rho_alpha_beta_control.py`) |

Both share `app2/` (Stanley-control car-follow-car experimental app) and the `rccar_pose_inference/` pose-estimation package.

---

## 11. User Stories

| Persona | Need | Feature |
|---------|------|---------|
| Rover Pilot | Intuitive game-like driving | WASD controls |
| Rover Pilot | Inspect surroundings without turning | IJKL gimbal |
| Rover Pilot | Avoid obstacles due to lag | Low-latency FPV video |
| Rover Pilot | Autonomously trail another rover | Follow mode (PID) / `app2` Stanley control |
| Safety Officer | Prevent collisions | Obstacle alarm + auto-brake |
| Safety Officer | Monitor environment | Real-time telemetry (push + poll) |
| Field Technician | Record discoveries | Snapshot with sensor overlay, optional AI upscale |
| Data Analyst | Visualize sensor trends | Historical charts |
| Data Analyst | Query data with natural language | Local AI chat (Ollama) |
