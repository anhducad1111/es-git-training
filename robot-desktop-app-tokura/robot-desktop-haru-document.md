# Robot Desktop App - Haru Documentation

## Changes Made (2026-09-14)

### 1. Fixed Sensor Data Reception Issue

**Problem:** Sensor data from ESP32 was not being received or displayed in the UI.

**Root Cause:**
- `TelemetryPoller.data_received` signal was never connected to update the UI
- Signal connection was attempted in `connect_signals()` before `start_connections()`, so `telemetry_poller` was still `None`
- `reconnect_rover()` created new `TelemetryPoller` instances but signal connections were lost

**Solution:**
- Added `telemetry_data` signal to `ConnectionManager` class
- Connected `TelemetryPoller.data_received` to `ConnectionManager.telemetry_data` in `_start_telemetry()`
- App connects to `ConnectionManager.telemetry_data` in `start_connections()`
- Added `_on_telemetry_received()` handler in `app.py` to update UI elements

**Files Modified:**
- `connection_manager.py` - Added `telemetry_data` signal, connected to poller
- `app.py` - Added signal connection and UI update handler

---

### 2. Added Cloud Telemetry Sending

**Problem:** Sensor data was displayed locally but not sent to the cloud.

**Solution:**
- Added `self._cloud_mgr.send_telemetry(data)` call in `_on_telemetry_received()` handler
- Telemetry data is now sent to cloud every time it's received from ESP32 (default 1 second interval)

**Files Modified:**
- `app.py` - Added cloud send call in telemetry handler

---

### 3. Fixed Settings Page Readability

**Problem:** Settings page UI elements were hard to read due to low contrast and text truncation.

**Solution:**
- Increased label colors from `#94a3b8` to `#e2e8f0` for better contrast
- Increased group box title colors for better visibility
- Widened label widths from `28px` to `36px` to prevent text truncation
- Widened value label widths from `32px` to `40px`
- Added `setMaximumWidth(600)` to left panel to prevent over-stretching

**Files Modified:**
- `views/settings_view.py` - Updated styles and widget dimensions

---

### 4. Created Missing Sensor Cards

**Problem:** `_temp_card`, `_humidity_card`, `_gas_card` were referenced in `diagnostics_view.py` but never created.

**Solution:**
- Added `SensorCard` instances for temperature, humidity, and gas in `sidebar.py`

**Files Modified:**
- `views/sidebar.py` - Added missing sensor card widgets

---

### 5. Translated UI Text to English

**Problem:** User requested all UI text be in English.

**Solution:**
- Translated all user-visible log messages, status messages, tooltips, and labels from Japanese to English

**Files Modified:**
- `app.py` - Log messages
- `detection_manager.py` - Follow mode log messages
- `follow_detector.py` - Frame processing log messages
- `follow_controller.py` - Gimbal control log messages
- `app2/app.py` - Marker detection, capture mode, tooltips
- `app2/calibration.py` - Calibration tips

**Translation Examples:**
| Japanese | English |
|----------|---------|
| 検出なし(yaw/dist欠測) | No detection (yaw/dist missing) |
| 検出器が初期化されていません | Detector not initialized |
| フレーム受信中... | Receiving frame... |
| カメラ接続 - 安定するまで待機 | Camera connected - waiting for stabilization |
| 車をlost → 方向を探索 | Target lost → searching direction |
| Stanley制御で前の車を自動追従 | Auto-follow the car ahead using Stanley control |
| 履歴がありません。 | No history available. |
| 撮影するには接続してください | Connect to the stream first |

---

## Architecture Notes

### Telemetry Data Flow
```
ESP32 → TelemetryPoller → ConnectionManager.telemetry_data → App._on_telemetry_received()
                                                                    ↓
                                                              UI Update
                                                              Cloud Send
```

### Signal Chain
1. `TelemetryPoller.data_received` (from HTTP polling)
2. `ConnectionManager.telemetry_data` (propagated signal)
3. `RoverTeleopApp._on_telemetry_received()` (handler)

---

### 6. Updated OTA Firmware Upload to API Contract

**Problem:** OTA upload was using incorrect endpoint `?action=ota` which didn't exist on the server.

**Solution:**
- Updated to use `POST /firmware` endpoint per API Contract
- Form data includes `version` (required) and `release_notes` (optional)
- Removed `X-OTA-Key` header (API has no authentication)
- Removed file renaming logic (server computes SHA-256 hash)
- Updated URL placeholder to `http://rpi5.local/api/v1`
- Added `data` parameter to `CloudWorker` for form data support

**API Contract:**
```
POST /firmware
multipart/form-data: version (required), file, release_notes (optional)
Response: 201 with metadata (id, version, file_size_bytes, mime_type, file_hash, release_notes, created_at)
```

**Files Modified:**
- `views/settings_view.py` - Updated `_upload_ota_file()` function
- `cloud_worker.py` - Added `data` parameter for form data

---

### 7. Added Upload Progress Display

**Problem:** No progress feedback during OTA firmware upload.

**Solution:**
- Added `progress` signal to `CloudWorker`
- Created `_UploadFileWrapper` class to track file upload progress
- Progress bar now shows percentage during upload
- Enabled text display on progress bar

**Files Modified:**
- `cloud_worker.py` - Added progress signal and wrapper class
- `views/settings_view.py` - Connected progress signal to progress bar

---

### 8. Fixed Settings View Text Visibility

**Problem:** Labels and text in settings view were invisible or showing as squares.

**Root Cause:** QLabel widgets were inheriting background colors from parent widgets and font fallback was showing squares.

**Solution:**
- Added `border: none` and `background-color: transparent` to `LABEL_STYLE`, `VALUE_LABEL_STYLE`, `PURPLE_VALUE_STYLE`
- Updated label colors for better contrast:
  - `LABEL_STYLE`: `#64748b` → `#94a3b8`
  - `VALUE_LABEL_STYLE`: `#06b6d4` → `#22d3ee`
  - `PURPLE_VALUE_STYLE`: `#7c3aed` → `#a78bfa`
- Increased font sizes for better readability
- Added `border: none` to inline styles for LED and OTA file labels

**Files Modified:**
- `views/settings_view.py` - Updated styles and inline styles

---

### 9. Added Obstacle Warning Banner

**Problem:** No visual warning when obstacle is detected near the rover.

**Solution:**
- Added `_obstacle_warning` QLabel to main view (amber/orange color)
- Warning shows when distance < brake_threshold (80cm)
- Displays current distance: "⚠ OBSTACLE: XX cm"
- Warning centers at top of video canvas
- Auto-hides when distance is safe

**Files Modified:**
- `views/main_view.py` - Added obstacle warning widget
- `app.py` - Added warning logic in `_on_telemetry_received()`

---

### 10. Added Auto-brake Functionality

**Problem:** Rover didn't stop automatically when obstacle was detected.

**Solution:**
- Added `_obstacle_brake_active` flag to prevent duplicate stop commands
- When distance < brake_threshold (80cm) AND auto_brake enabled:
  - Sends `stop` command to ESP32
  - Logs: "Auto-brake: XX cm < YY cm → STOP"
  - Shows obstacle warning banner
- Reset flag when distance returns to safe range

**Files Modified:**
- `app.py` - Added auto-brake logic in `_on_telemetry_received()`

---

### 11. Added Distance-based Speed Limiting

**Problem:** Rover maintained full speed even when approaching obstacles.

**Solution:**
- Speed is automatically reduced based on distance (forward movement only)
- Parameters:
  - `MIN_SPEED = 150` (minimum allowed speed)
  - `SPEED_DIST_MAX = 150` (speed reduction starts at 150cm)
- Speed calculation uses quadratic curve for more aggressive deceleration:
  ```
  ratio = distance / 150
  ratio = ratio * ratio  (quadratic)
  limited = MIN_SPEED + (user_speed - MIN_SPEED) * ratio
  ```
- Speed limit examples (user_speed = 220):
  - 150cm: 220 (full speed)
  - 100cm: ~190
  - 80cm: ~175
  - 50cm: ~160
  - 30cm: ~155
- Reverse movement always uses full speed (no limit)
- Speed label and meter update to show limited speed

**Files Modified:**
- `app.py` - Added speed limiting logic in `_on_telemetry_received()`

---

### 12. Fixed Speed Meter Display

**Problem:** Speed meter didn't show 0 when rover stopped, and wasn't initialized properly.

**Solution:**
- Added `reset_speed()` method to `SpeedMeter` for immediate reset to 0
- Updated `_send_command()` to reset speed meter when `stop` command is sent
- Initialized speed meter with current speed on startup
- Speed meter now shows:
  - Current speed when driving
  - Limited speed when distance-based limiting is active
  - 0 when stopped (immediate, no animation)

**Files Modified:**
- `widgets/speed_meter.py` - Added `reset_speed()` method
- `app.py` - Added speed meter updates in `_send_command()`
- `views/main_view.py` - Initialize speed meter with current speed

---

### 13. Updated Brake Threshold to 80cm

**Problem:** Default brake threshold (30cm) was too close, causing frequent collisions.

**Solution:**
- Updated `brake_threshold` from 30 to 80 in config.json
- Rover now stops at 80cm distance from obstacles

**Files Modified:**
- `config.json` - Updated `brake_threshold` value

---

## Safety Features Summary

| Feature | Trigger Condition | Action |
|---------|-------------------|--------|
| Obstacle Warning | distance < 80cm | Show amber warning banner |
| Auto-brake | distance < 80cm AND auto_brake=true | Send stop command |
| Speed Limiting | distance < 150cm (forward only) | Reduce speed proportionally |
| Min Speed | Always | 150 (never goes below) |
| Reverse Speed | Always | Full speed (no limit) |

## Telemetry Data Flow (Updated)
```
ESP32 → TelemetryPoller → ConnectionManager.telemetry_data → App._on_telemetry_received()
                                                                     ↓
                                                              ┌──────┴──────┐
                                                              │ UI Update   │
                                                              │ Cloud Send  │
                                                              │ Obstacle    │
                                                              │ Warning     │
                                                              │ Auto-brake  │
                                                              │ Speed Limit │
                                                              └─────────────┘
```
