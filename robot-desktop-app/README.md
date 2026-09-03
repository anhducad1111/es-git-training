# Earth Rover - Desktop Controller & ESP32 Integration Guide

A real-time IoT rover monitoring and control system featuring a PyQt6 Windows desktop controller, an ESP32-based hardware rover, and a cloud-backed data pipeline.

---

## 1. System Architecture Overview

To ensure that high-latency cloud operations or network jitter never compromise the safety and real-time responsiveness of the physical rover, the desktop application separates operations into **two independent execution paths (decoupled via an asynchronous FIFO queue)**.

```text
                  [ ESP32 Rover ]
                    │       ▲
   UDP (Port 5005)  │       │  UDP (Port 5006)
   Command Out      │       │  Video & Sensors In
                    ▼       │
            ┌──────────────────────────┐
            │   Desktop Receiver       │
            │   (Thread A - Realtime)  │
            └───────┬──────────┬───────┘
                    │          │
                    ▼          ▼
             [ Live UI ]   [ Local Queue (FIFO) ]
                            │
                            │ Asynchronous Background Worker
                            ▼
                    ┌──────────────────────────┐
                    │   Cloud Uploader         │
                    │   (Thread B - Async)     │
                    └───────┬──────────────────┘
                            │ HTTPS (REST API)
                            ▼
                     [ Cloud Database ]

```

### Path A: Real-Time Control & Display (Thread A / High Priority)

* **Responsibility:** Handles high-frequency tasks such as receiving live video feeds and sensor data from the ESP32, updating the desktop GUI instantly, and transmitting driving commands.
* **Characteristics:** Completely non-blocking. It is designed never to wait for external network responses (like cloud APIs), ensuring smooth 10–30Hz command-and-response loops.

### Path B: Cloud Upload Pipeline (Thread B / Background)

* **Responsibility:** Ingests sensor data received by Thread A, buffers it into a **thread-safe FIFO (First-In, First-Out) Queue**, and runs a background worker to push data securely to the cloud backend.
* **Characteristics:** If the cloud API or internet connection slows down or temporarily drops (e.g., a 500ms delay), data is safely queued in memory. The rover's live driving and video rendering remain entirely unaffected.

---

## 2. Hardware Microcontroller Architecture

The physical deployment consists of **three distinct microcontrollers** handling specialized roles within the local Wi-Fi network:

* `esp32_car`: Manages rover motion and motor driving.
* `esp32_cam`: Handles FPV video feed capture and streaming.
* `esp32_monitor`: Acts as the base station sensor node for environment data acquisition.

---

## 3. Communication Protocol & Network Design

The system carefully selects networking protocols based on performance requirements. (Note: Radar telemetry has been intentionally omitted to focus strictly on robust manual driving and video streaming).

| Direction & Target | Protocol | Port / Method | Purpose & Rationale |
| --- | --- | --- | --- |
| **PC -> ESP32 Rover** | **UDP** | Port `5005` | Low-latency control commands (`FORWARD`, `BACKWARD`, `LEFT`, `RIGHT`, `STOP`, `CAMERA:*`). |
| **ESP32 Rover -> PC** | **UDP** | Port `5006` | Real-time MJPEG video stream and environment sensors. Avoids TCP head-of-line blocking so dropped frames never freeze the display. |
| **PC -> Cloud Backend** | **HTTPS** | REST API (JSON) | Historical data storage and analysis logging, handled asynchronously via the FIFO queue. |

---

## 4. Thread Architecture

```text
Main Thread (UI)
    │
    ├── RC Control ──────> UDP Socket (send commands)
    │
    ├── Video Feed ──────> QThread (recv packets)
    │
    ├── Sensor Polling ──> QThread (HTTP GET)
    │
    ├── OTA Upload ──────> QThread (HTTP POST + progress)
    │
    └── AI Chat ─────────> QThread (Gemini API)
```

- **Main Thread**: PyQt6 event loop, UI updates
- **Video Thread**: `QThread` receiving UDP packets on port 5006
- **Worker Thread**: `QThread` for HTTP requests (GET/POST)
- **OTA Thread**: `QThread` for chunked file uploads with progress

---

## 5. Handling Disconnections & Failsafes (Why UDP + Timers?)

While UDP is stateless and connectionless, **disconnection detection and automatic recovery are strictly implemented at the application layer**:

1. **Rover-Side Failsafe (HW-008 Compliance):**
* The ESP32 firmware maintains a last-received packet timestamp. If no command or heartbeat packet is received from the controller within a defined timeout (e.g., 1.0 second), the firmware automatically triggers an emergency motor stop to prevent runaway behavior during network drops.


2. **App-Side Connection Monitoring:**
* The desktop application monitors incoming UDP streams. If sensor or video packets stop arriving, the UI updates its status indicator to "Disconnected" and initiates background reconnection logic without restarting the application framework.

---

## 6. Wireless Firmware Flashing (OTA)

To fulfill requirements **HW-004** and **APP-007**, all three microcontrollers support wireless firmware updates over Wi-Fi, eliminating the need to constantly plug and unplug USB cables:

* **Central OTA Hub:** Accessible via `http://rpi5.local/ota/`, handling wireless updates for `esp32_car`, `esp32_cam`, and `esp32_monitor`.
* **Initiation & Monitoring (APP-007):** The desktop controller app allows operators to specify version metadata, select compiled `.bin` firmware files, and track progress via an interactive progress bar.
* **Automatic File Renaming:** The client app automatically standardizes and renames uploaded binaries into a strict naming convention (`filename-version-info-client.bin`) to track releases cleanly.
* **Version Verification & Unpinning:** After a successful upload, the application queries the server to check version synchronization (`latest.php`), warning the operator of any mismatches and providing an "Unpin" option (`target.php`) to ensure devices boot correctly into the new image.

### OTA Upload Details

**Headers:**
```
X-OTA-Key: shodai-haru-2026-8-25
Content-Type: multipart/form-data
```

**Filename Convention:**
```
{device}-{version}-{info}-{client}.bin
```
Example: `esp32_car-1_0_0-InitialRelease-Haru_Client.bin`

---

## 7. Migration Roadmap: Simulation to ESP32 Hardware

Transitioning the PyQt6 codebase from simulation to physical hardware involves the following steps:

1. **Network Endpoint Adjustment:**
* Replace local loopback addresses (`127.0.0.1`) with the actual static or DHCP-assigned IP address of the ESP32 units on the local Wi-Fi network.


2. **FIFO Queue & Sensor Integration:**
* Implement Python's `queue.Queue` inside `app.py` to decouple sensor ingestion from cloud HTTP POST requests. Receive sensor data directly via UDP port 5006 instead of HTTP fetching.


3. **ESP32 Firmware Development:**
* Set up Wi-Fi connection routines on the ESP32.
* Bind a UDP server on port `5005` to parse incoming command strings and drive motors via a motor driver (e.g., L298N) using PWM.
* Implement the safety watchdog timer for communication loss.

---

## 8. HTTP API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `api/get-data.php` | Fetch latest sensor data + history |
| POST | `api/post-data.php` | Upload sensor readings |
| POST | `api/api.php?action=ota` | Upload firmware `.bin` file |

---

## 9. Sensor Data Format

### GET Response

```json
{
  "success": true,
  "server_time": "2026-09-03 12:00:00",
  "latest": {
    "temperature": {"data": "28.5", "reading_time": "..."},
    "humidity": {"data": "65", "reading_time": "..."},
    "co2": {"data": "450", "reading_time": "..."}
  },
  "history": {
    "temperature": [{"data": "28.5", "reading_time": "..."}, ...]
  }
}
```

### Sensor Labels

| Group | Sensors |
|-------|---------|
| Air Quality | `co2`, `pm1.0`, `pm2.5`, `pm10` |
| Environment | `temperature`, `humidity`, `pressure` |
| Other | `gas`, `battery` |

---

## 10. Quick Start & File Structure

### Installation & Execution

```bash
pip install PyQt6 requests matplotlib
python main.py
```

### Core Source Files

| File | Purpose |
| --- | --- |
| `main.py` | Application entry point (initializes `QApplication` and main window). |
| `app.py` | Main window class, manages UI layout, timers, auto-mode, and disconnect dialogs. |
| `rc_control.py` | RC car control panel with D-pad and keyboard input. |
| `video_feed.py` | Video receiver thread for UDP MJPEG stream. |
| `sensors.py` | Sensor dashboard, cards, and chart widgets. |
| `ota.py` | Handles firmware file selection, validation (`.bin` only), automatic renaming, and upload execution. |
| `ai_chat.py` | Gemini AI chat interface with custom chart creation. |
| `worker.py` | Background `QThread` worker handling HTTP GET/POST and chunked file uploads with progress tracking. |
| `config.py` | Config load/save utilities. |

### Controls

- **WASD** - Drive the rover (when RC panel is open)
- **E + Mouse Move** - Control camera gimbal
- **Tab** - Autocomplete sensor names in chat
- **Enter** - Send chat message
- **Shift+Enter** - New line in chat
- **/chart** - Create custom charts (e.g., `/chart temperature humidity -n`)

### Configuration

1. Enter ESP32 rover IP in the "Rover IP" field
2. Enter cloud API URL in the "API URL" field
3. Enter Gemini API key in the "Gemini Key" field (optional)

**Config File Format:**
```json
{
  "rover_ip": "192.168.1.100",
  "api_url": "https://example.com/api/get-data.php",
  "gemini_api_key": "",
  "center_charts": {},
  "custom_charts": {},
  "custom_charts_normalize": {}
}
```

---

## 11. Development Checklist

* [ ] **Desktop App:** Remove UI components for Port 5007 (radar telemetry).
* [ ] **Desktop App:** Implement `queue.Queue` and background thread worker for cloud telemetry uploads.
* [ ] **Firmware:** Set up ESP32 Wi-Fi configuration and UDP command listener (Port 5005).
* [ ] **Hardware:** Integrate motor drivers, sensors, and camera module onto the rover chassis (`esp32_car`, `esp32_cam`, `esp32_monitor`).
* [ ] **Safety Testing:** Verify that disconnecting the Wi-Fi mid-drive successfully stops the rover within the timeout limit (HW-008).
* [ ] **End-to-End Integration:** Validate full data flow from ESP32 -> Desktop App -> Cloud Database -> Historical Chart Retrieval (INT-003).

---

## 12. Code Sources

| Component | Source |
|-----------|--------|
| RC Control, Video, Sensors, AI | `haru-app2/` |
| OTA Firmware Upload | `haru-app/` |
