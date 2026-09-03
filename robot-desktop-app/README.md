
---

# Earth Rover - Desktop Controller & ESP32 Integration Guide

A real-time IoT rover monitoring and control system featuring a PyQt6 Windows desktop controller, an ESP32-based hardware rover, and a cloud-backed data pipeline.

---

## 1. System Architecture Overview

To ensure that high-latency cloud operations or network jitter never compromise the safety and real-time responsiveness of the physical rover, the desktop application separates operations into **two independent execution paths (decoupled via an asynchronous FIFO queue)**.

```
                  [ ESP32 Rover ]
                    │       ▲
   UDP (Port 5005)  │       │  UDP (Port 5006/5007)
   Command Out      │       │  Video / Telemetry In
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

* **Responsibility:** Handles high-frequency tasks such as receiving live video feeds and sensor telemetry from the ESP32, updating the desktop GUI instantly, and transmitting driving commands.
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

The system carefully selects networking protocols based on performance requirements:

| Direction & Target | Protocol | Port / Method | Purpose & Rationale |
| --- | --- | --- | --- |
| **PC $\to$ ESP32 Rover** | **UDP** | Port `5005` | Low-latency control commands (`FORWARD`, `BACKWARD`, `LEFT`, `RIGHT`, `STOP`, `CAMERA:*`).

 |
| **ESP32 Rover $\to$ PC** | **UDP** | Port `5006` | Real-time MJPEG video stream. Avoids TCP head-of-line blocking so dropped frames never freeze the display.

 |
| **ESP32 Rover $\to$ PC** | **UDP** | Port `5007` | Positional telemetry and sensor readings for radar mapping and UI cards.

 |
| **PC $\to$ Cloud Backend** | **HTTPS** | REST API (JSON) | Historical data storage and analysis logging, handled asynchronously via the FIFO queue.

 |

---

## 4. Handling Disconnections & Failsafes (Why UDP + Timers?)

While UDP is stateless and connectionless, **disconnection detection and automatic recovery are strictly implemented at the application layer**:

1. **Rover-Side Failsafe (HW-008 Compliance):**
* The ESP32 firmware maintains a last-received packet timestamp. If no command or heartbeat packet is received from the controller within a defined timeout (e.g., 1.0 second), the firmware automatically triggers an emergency motor stop to prevent runaway behavior during network drops.




2. **App-Side Connection Monitoring:**
* The desktop application monitors incoming UDP streams. If telemetry or video packets stop arriving, the UI updates its status indicator to "Disconnected" and initiates background reconnection logic without restarting the application framework.





---

## 5. OTA (Over-The-Air) Firmware Update Mechanism

To fulfill requirements **HW-004** and **APP-007**, the system supports wireless firmware updates managed through the desktop client:

* **Initiation & Monitoring (APP-007):** The desktop controller app allows operators to specify version metadata, select compiled `.bin` firmware files, and track progress via an interactive progress bar.


* **Automatic File Renaming:** The client app automatically standardizes and renames uploaded binaries into a strict naming convention (`filename-version-info-client.bin`) to track releases cleanly.


* **Secure Transmission:** Firmware files are sent via an authenticated HTTP POST request (`?action=ota`) using multipart form data, protected by specialized security headers (e.g., `X-OTA-Key`).


* **Version Verification & Unpinning:** After a successful upload, the application queries the server to check version synchronization (`latest.php`), warning the operator of any mismatches and providing an "Unpin" option (`target.php`) to ensure devices boot correctly into the new image.



---

## 6. Migration Roadmap: Simulation to ESP32 Hardware

Transitioning the PyQt6 codebase from simulation to physical hardware involves the following steps:

1. **Network Endpoint Adjustment:**
* Replace local loopback addresses (`127.0.0.1`) with the actual static or DHCP-assigned IP address of the ESP32 units on the local Wi-Fi network.




2. **FIFO Queue Integration:**
* Implement Python's `queue.Queue` inside `app.py` to decouple sensor ingestion from cloud HTTP POST requests.


3. **ESP32 Firmware Development:**
* Set up Wi-Fi connection routines on the ESP32.
* Bind a UDP server on port `5005` to parse incoming command strings and drive motors via a motor driver (e.g., L298N) using PWM.
* Implement the safety watchdog timer for communication loss.



---

## 7. Quick Start & File Structure

### Installation & Execution

```bash
# Install dependencies
pip install PyQt6 requests matplotlib

# Run the client application
python main.py

```

### Core Source Files

| File | Purpose |
| --- | --- |
| `main.py` | Application entry point (initializes `QApplication` and main window).

 |
| `app.py` | Main window class (`SensorClientApp`), manages UI layout, timers, auto-mode, and disconnect dialogs.

 |
| `panels.py` | UI component generators (`create_config_group`, `create_input_group`, `create_upload_group`).

 |
| `upload.py` | Handles firmware file selection, validation (`.bin` only), automatic renaming, and upload execution.

 |
| `worker.py` | Background `QThread` worker handling HTTP GET/POST and chunked file uploads with progress tracking.

 |
| `chart.py` | Matplotlib-based dual-axis line chart widget for real-time temperature and humidity history.

 |

---

## 8. Development Checklist

* [ ] **Desktop App:** Implement `queue.Queue` and background thread worker for cloud telemetry uploads.
* [ ] **Firmware:** Set up ESP32 Wi-Fi configuration and UDP command listener (Port 5005).
* [ ] **Hardware:** Integrate motor drivers, sensors, and camera module onto the rover chassis (`esp32_car`, `esp32_cam`, `esp32_monitor`).
* [ ] **Safety Testing:** Verify that disconnecting the Wi-Fi mid-drive successfully stops the rover within the timeout limit (HW-008).


* [ ] **End-to-End Integration:** Validate full data flow from ESP32 $\to$ Desktop App $\to$ Cloud Database $\to$ Historical Chart Retrieval (INT-003).