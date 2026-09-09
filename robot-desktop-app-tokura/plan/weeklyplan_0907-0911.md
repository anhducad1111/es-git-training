- **Car & Camera Control**: Handled locally between the Desktop App and ESP32 over WebSocket (`ws://<esp32-ip>:<port>`).
- **Telemetry & Media Forwarding**: The Desktop App acts as a gateway/relay, consuming telemetry and video frames, rendering them to the UI, and forwarding structured JSON metrics and captured snapshots to the Cloud REST API.

---

## 2. Core Functional Specifications

| Feature Area | Key Requirements & Protocol / Format |
| :--- | :--- |
| **1. Car Movement** | • **Controls**: WASD keys (Forward/Left/Backward/Right), `Space` (Emergency Stop).<br>• **Commands**: Text payloads (e.g., `"forward"`, `"stop"`).<br>• **Safety**: Auto-repeat key suppression and automatic `"stop"` on key release or disconnect. |
| **2. Speed Control** | • **Controls**: UI PWM Speed Slider (Range: 150–255 / 0–100%).<br>• **Command Format**: Dynamic motor drive parameters (e.g., `"drive:<speed>,<turn>"`). |
| **3. Gimbal (Pan/Tilt)** | • **Controls**: IJKL keys (Up/Left/Down/Right), `C` key (Center: 90°, 90°), UI Pan/Tilt Sliders (0–180°).<br>• **Commands**: `"servo:<pan>,<tilt>"` to ESP32-MCU. |
| **4. Telemetry & Auto-Brake** | • **Telemetry Display**: Temperature, Humidity, Air Quality, Distance (`distance_cm`), Battery voltage.<br>• **Auto-Brake**: Evaluates distance against UI threshold (10–100 cm). Triggers instant `"stop"` & UI alert when distance < threshold. |
| **5. Video & Camera Controls** | • **Video Feed**: MJPEG streaming over WebSocket/HTTP.<br>• **Resolution Switch**: UI Dropdown (640x480, 1280x720, 320x240) sending `"resolution:WIDTH,HEIGHT"`, waiting for ACK (`"ack:ok"`).<br>• **Image Flip**: Horizontal (`"flip:h"`) and Vertical (`"flip:v"`) toggle buttons. |
| **6. Cloud Integration** | • **Telemetry Forwarding**: Asynchronous `POST /api/v1/telemetry` every 1–3s.<br>• **Snapshot Upload**: Frame capture from UI buffer to local temp file, uploaded via `POST /api/v1/rovers/{device_uid}/media` (`multipart/form-data`). |

---

## 3. Detailed 5-Day Development Schedule

### Day 1: Chassis Movement & Camera Gimbal Control
- **Goal**: Establish WebSocket connection with ESP32-MCU and implement vehicle movement and camera angle manipulation.
- **Tasks**:
  1. **Configuration Setup (`config.py` / `config.json`)**: Define ESP32 IP, WebSocket ports, device UID, and API endpoints.
  2. **WebSocket Client (`command.py`)**: Implement `CommandSender` for non-blocking command transmission.
  3. **Chassis Control (`app.py`)**:
     - Handle `keyPressEvent` and `keyReleaseEvent` for WASD / `Space`.
     - Filter `event.isAutoRepeat()` to avoid command flood.
     - Send `"stop"` on key release.
  4. **Gimbal Control (`gimbal.py`)**:
     - Manage Pan and Tilt angle state (`0°` to `180°`, step size `5°`).
     - Map IJKL and `C` keys to angle updates.
     - Connect UI Pan/Tilt sliders and "Center Gimbal" button to send `"servo:pan,tilt"`.

---

### Day 2: Telemetry Display, Speed Adjustment & Auto-Brake System
- **Goal**: Process incoming telemetry data, render UI dashboard elements, and enforce obstacle avoidance safety routines.
- **Tasks**:
  1. **Telemetry Reception (`sensors.py`)**:
     - Parse JSON telemetry packets from ESP32 (`distance_cm`, `temp`, `humidity`, `battery`).
  2. **UI Sidebar Integration**:
     - Update progress bars, numerical labels, and battery gauge indicators in real time.
  3. **Motor Speed Control**:
     - Add PWM speed slider (150–255) to the control panel.
     - Integrate selected speed setting into active movement command payloads.
  4. **Auto-Brake System Implementation**:
     - Add Auto-Brake ON/OFF toggle switch and distance threshold slider (10–100 cm).
     - Implement instant distance check upon telemetry receipt.
     - If `distance_cm < threshold` and Auto-Brake is active:
       - Automatically emit `"stop"` command.
       - Display prominent warning banner on the UI dashboard.

---

### Day 3: Cloud Telemetry Forwarding (`ESP32 -> App -> Cloud`)
- **Goal**: Implement non-blocking background workers to forward received telemetry to the Cloud REST API.
- **Tasks**:
  1. **Background Worker Thread (`worker.py`)**:
     - Inherit from `QThread` / `QRunnable` to execute HTTP POST requests without blocking UI rendering.
  2. **Data Formatting & Enriched Payload**:
     - Attach `device_uid`, ISO 8601 timestamp (`recorded_at`), and status flags to raw telemetry.
  3. **Periodic Cloud Sync (1–3 second interval)**:
     - Implement rate-limiting / buffer management to ensure smooth API calls to `POST /api/v1/telemetry`.
  4. **Logging & Diagnostics**:
     - Output HTTP status codes (e.g., `200 OK`, timeouts, connection errors) to the application log widget.

---

### Day 4: Video Stream, Camera Quality Control & Snapshot Cloud Upload
- **Goal**: Render real-time video, enable resolution and image flip toggles, and implement snapshot uploading.
- **Tasks**:
  1. **Video Stream Receiver (`video_feed.py`)**:
     - Create `VideoReceiverThread` to read JPEG frame buffers over WebSocket.
     - Convert JPEG byte buffers to `QPixmap` and paint on UI canvas.
  2. **Camera Settings Control**:
     - **Resolution**: Dropdown selection sends `"resolution:WIDTH,HEIGHT"`. Suspend/resume renderer upon `"ack:ok"`.
     - **Image Flip**: Buttons send `"flip:h"` or `"flip:v"`.
  3. **Snapshot Capture & Cloud Upload**:
     - Store the latest frame buffer in memory.
     - On "Take Snapshot" button click:
       - Write frame buffer to temporary JPEG file (`snapshot_temp.jpg`).
       - Delegate upload to `CloudMediaWorker` (`POST /api/v1/rovers/{device_uid}/media`).
       - Display confirmation toast/log upon successful upload.

---

### Day 5: System Integration, Safety Testing & Refinement
- **Goal**: Execute end-to-end multi-feature testing, edge-case recovery, and UI Polish.
- **Tasks**:
  1. **Integrated Field Testing**:
     - Drive vehicle while panning gimbal, switching camera resolution, and testing Auto-Brake against obstacles.
     - Verify simultaneous cloud streaming of telemetry and snapshot uploads.
  2. **Edge Case & Safety Handling**:
     - **Connection Lost**: Automatically issue `"stop"` and attempt WebSocket auto-reconnect.
     - **Invalid Payload / Timeout**: Handle API timeout errors gracefully without crashing the UI thread.
  3. **Code Cleanup**:
     - Modularize code, remove redundant debug logs, and ensure consistent error catching.

---

## 4. Key Engineering Best Practices & Guidelines

1. **GUI Responsiveness**: All networking and disk I/O (WebSocket calls, HTTP POSTs, file writes) must run on separate `QThread` workers.
2. **Safety First**: The vehicle must default to a stationary state (`"stop"`) upon launch, on key release, during connection drop, or when Auto-Brake triggers.
3. **Memory Optimization**: Avoid retaining large video frame histories in RAM; maintain only the latest frame buffer for snapshot generation.