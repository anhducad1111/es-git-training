# Haru App 2 - Sensor Dashboard

A PyQt6 desktop application for real-time IoT sensor monitoring with AI-powered analysis, interactive charts, and persistent layout customization.

## Overview

Haru App 2 connects to your ESP32 sensor array via a cloud API, displaying live readings for 9 sensor types. The app features:

- Real-time sensor data display with value change indicators
- Interactive line charts with drag-and-drop functionality
- Gemini AI chat for natural language data analysis
- Custom chart creation via AI or slash commands
- Persistent layout that remembers your configuration across restarts

## Quick Start

### Installation

```bash
cd haru-app2
pip install PyQt6 requests matplotlib google-genai
```

### Running the App

```bash
python main.py
```

### Initial Setup

1. **Configure Server Connection**
   - Enter your API URL in the "API URL" field
   - Default: `https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/get-data.php`
   - Click **Test** to verify the connection works
   - Click **Start Polling** to begin receiving live data

2. **Set Up Gemini AI** (Optional)
   - The Gemini API key is configured in `config.py`
   - Leave `gemini_api_key = ""` to use environment variable or set it directly
   - The AI chat enables natural language questions about your sensor data

## Features

### Real-Time Sensor Monitoring

**9 Sensor Types Supported:**
- CO2 (carbon dioxide)
- PM1.0, PM2.5, PM10 (particulate matter)
- Temperature
- Humidity
- Pressure
- Gas (analog gas sensor)
- Battery level

**6 Sensor Categories (Grouped Cards):**
1. **Air Quality**: CO2 readings
2. **Particulate Matter**: PM1.0, PM2.5, PM10 readings
3. **Temperature & Humidity**: Temperature and humidity readings
4. **Pressure**: Atmospheric pressure
5. **Gas**: Gas sensor readings
6. **Battery**: Battery level

**Value Change Indicators:**
- ↑ Blue arrow (#2196F3): Value increased from previous reading
- ↓ Red arrow (#FF5252): Value decreased from previous reading
- → Green arrow (#4CAF50): Value unchanged

**Display Features:**
- Large 14pt font for sensor values
- 12pt font for sensor names
- Right-aligned values with left-aligned labels
- Centered arrow indicators
- 5-second auto-refresh polling interval

### Line Charts

**3 Default Charts:**
1. **Air Quality**: CO2 data over time
2. **Environment**: Temperature, humidity, and pressure trends
3. **Other**: PM1.0, PM2.5, PM10, gas, and battery levels

**Chart Features:**
- Matplotlib-based interactive charts
- Hover tooltips showing exact values with dynamic positioning
- X-axis shows time (HH:MM format)
- Y-axis auto-scales with MaxNLocator (6 bins)
- Dark theme matching the dashboard style

### Gemini AI Chat

**Chat Features:**
- Natural language questions about your sensor data
- Responses limited to ~100 words for quick reading
- System context includes current sensor readings
- Chat history maintained during session
- Purple 💭 toggle button to show/hide AI panel

**Tab Completion:**
- Type `/chart` followed by partial sensor name
- Press Tab to auto-complete available sensors
- Example: `/chart tem` + Tab → `/chart temperature`

### AI Custom Charts

**Creation Methods:**

1. **Natural Language**
   - Type: "Show me temperature and humidity together"
   - Gemini creates the chart automatically
   - Chart appears in the AI Custom Charts area

2. **Slash Commands**
   - `/chart co2 temperature` - Combined chart
   - `/chart gas co2 -n` - Normalized (0-1 scale)
   - `/chart pm1.0 pm2.5 pm10 -d` - Separate charts
   - `/chart co2 temperature -m My Chart` - Custom name
   - `/chart co2 temperature -n -m My Chart` - Normalized with custom name

3. **Drag and Drop**
   - Drag any chart from Main Charts to AI Custom Charts
   - Drag any chart from AI Custom Charts to Main Charts

4. **Move to Charts Button**
   - Click "Move to Charts" to move all AI custom charts to center
   - Auto-rename on conflicts (e.g., "Other (2)")

**Chart Options:**
- `-n` flag: Normalize data to 0-1 range (Min-Max scaling)
- `-m` flag: Set custom chart name (next token is the name)
- `-d` flag: Display each sensor in separate charts
- Toggle visibility with X/O button on each chart
- Hover tooltips with dynamic positioning

### Layout Persistence

**Saved Settings:**
- Chart arrangement in Main Charts area
- Chart arrangement in AI Custom Charts area
- Hidden chart states (X/O button positions)
- Normalization settings for custom charts
- API URL configuration
- Gemini API key

**Configuration File:**
- Saved to `config.json` (gitignored)
- Auto-saves on layout changes
- Restores on app restart

### Drag and Drop System

**How It Works:**
1. Hover over any chart title to grab it (cursor changes to hand)
2. Drag to target area (dashed border appears when hovering)
3. Drop to copy or move the chart

**Movement Rules:**
- Main Charts → AI Custom Charts: **Copies** the chart
- AI Custom Charts → Main Charts: **Moves** the chart (removes from custom)
- Auto-rename when moving to avoid duplicate names

**Visual Feedback:**
- Blue dashed border when dragging over valid drop zone
- Charts maintain their data and settings during transfer

### Data Analysis

**Analyze Data Button:**
- Click "Analyze Data (Gemini)" in left panel
- Sends current sensor data to Gemini for analysis
- Analysis text is automatically sent to your server via POST request
- Response appears in chat as a system message

**Server Integration:**
- Analysis sent to `/api/post-analysis.php`
- JSON format: `{"content": "Analysis text from Gemini..."}`
- Useful for logging or further processing

### RC Car Control

**Blue 🚙 Button (Bottom Right):**
- Toggle RC control panel on/off
- Exclusive with AI panel (opening one closes the other)
- Sends automatic STOP command when panel is closed (fail-safe)
- All keyboard controls disabled when panel is closed

**RC Panel Layout:**
```
+------------------------------------------+
|        🚙 RC Car Control                 |
|        Status: Disconnected              |
+----------+-------------------------------+
|  D-Pad   |                               |
|  [⬆]     |      Live Video Feed          |
| [⬅][⏹][➡] |     (Widescreen 16:9)        |
|  [⬇]     |                               |
|          |                               |
+----------+-------------------------------+
|        [ Reset Camera ]                  |
|        Speed: 50%                        |
+------------------------------------------+
```

**D-Pad Controls (Touch/Mouse):**
- ⬆ Forward
- ⬇ Backward
- ⬅ Left
- ➡ Right
- ⏹ STOP button (red, center)
- Press and hold to move — car stops on release

**Keyboard Controls (WASD):**
- W → Forward
- S → Backward
- A → Left
- D → Right
- Release any key → Stop
- Keys ignored when typing in text fields
- Keys disabled when RC panel is closed

**Camera Controls (Hold E + Mouse):**
- Hold E key to activate camera mode
- Move mouse to pan camera view
- Sends `CAMERA:{dx}:{dy}` via UDP
- Works simultaneously with WASD driving
- Camera mode disabled when RC panel is closed

**Reset Camera Button:**
- Click "Reset Camera" to return view to default position
- Sends `CAMERA_RESET` command via UDP
- Located below the video feed

**Video Feed:**
- Receives JPEG stream from Unity on UDP port 5006
- Displays in widescreen format (16:9 aspect ratio)
- Auto-scales to fill available space
- Uses `VideoReceiverThread` for non-blocking reception
- Shows "No Signal" when no stream is active

## Layout

### Main Dashboard Layout

```
+-------------------+-------------------+-------------------+-------------------+
|  Server Config    |  Sensor Cards     |  Main Charts      |  Gemini Chat      |
|  [API URL]        |  +-------------+  |  Air Quality      |  [Input field]    |
|  [Test] [Poll]    |  | Air Quality |  |  +-----------+    |  [Send button]    |
+-------------------+  | CO2: 2164 → |  |  | co2, pm   |    |                   |
                       | +-------------+  |  | /\  /\    |    |                   |
                       | | Particulate |  |  +-----------+    |                   |
                       | | PM1.0: 1 ↑ |  |                   |                   |
                       | | PM2.5: 2 ↓ |  |  Environment      |  AI Custom Charts |
                       | +-------------+  |  +-----------+    |  +-----------+    |
                       | | Temp & Hum  |  |  | temp, hum |    |  | User      |    |
                       | | 29.0 C →    |  |  | /\  /\    |    |  | created   |    |
                       | +-------------+  |  +-----------+    |  | charts    |    |
                       | | Pressure    |  |                   |  +-----------+    |
                       | | 1013 hPa →  |  |  Other            |                   |
                       | +-------------+  |  +-----------+    |  [Move to Charts] |
                       | | Gas         |  |  | pm, gas   |    |                   |
                       | | 150 →       |  |  | /\  /\    |    |                   |
                       | +-------------+  |  +-----------+    |                   |
                       | | Battery     |  |                   |                   |
                       | | 85% →       |  |                   |                   |
                       | +-------------+  |                   |                   |
+-------------------+-------------------+-------------------+-------------------+
| 💭 Toggle AI Panel / 🚙 Toggle RC Panel (bottom right corner)                |
+---------------------------------------------------------------------------+
| [Log]  <-- click to expand                                                   |
+---------------------------------------------------------------------------+
```

### Column Breakdown

**Left Column (Server Config + Sensor Cards):**
- API URL input field
- Test Connection button
- Start/Stop Polling button
- Connection status indicator
- 6 sensor category cards with live values

**Center Column (Main Charts):**
- 2-column masonry layout for charts
- Line charts showing historical data
- Drag-and-drop enabled
- Reset Layout button
- Scrollable area for many charts

**Right Column (AI Panel):**
- Gemini chat interface (left side)
- AI Custom Charts area (right side)
- Move to Charts button
- Purple 💭 toggle button at bottom

## API Endpoints

### GET /api/get-data.php

Fetches sensor data from the server.

**Response Format:**
```json
{
  "success": true,
  "server_time": "2026-08-27 12:00:00",
  "latest": {
    "co2": {"data": 2164, "reading_time": "2026-08-27 11:59:00"},
    "temperature": {"data": 29.03, "reading_time": "2026-08-27 11:59:00"},
    "humidity": {"data": 65.2, "reading_time": "2026-08-27 11:59:00"}
  },
  "history": {
    "co2": [
      {"reading_time": "2026-08-27 11:55:00", "data": 2100},
      {"reading_time": "2026-08-27 11:56:00", "data": 2120}
    ],
    "temperature": [
      {"reading_time": "2026-08-27 11:55:00", "data": 28.5},
      {"reading_time": "2026-08-27 11:56:00", "data": 28.8}
    ]
  }
}
```

### POST /api/post-analysis.php

Sends analysis results to the server.

**Request Body:**
```json
{"content": "Analysis text from Gemini..."}
```

**Purpose:**
- Log AI analysis for later review
- Integrate with external systems
- Store insights for dashboarding

### UDP Communication (RC Car)

**Port 5005 — Car Commands (Python → Unity):**
| Command | Description |
|---------|-------------|
| `FORWARD` | Move forward |
| `BACKWARD` | Move backward |
| `LEFT` | Turn left |
| `RIGHT` | Turn right |
| `STOP` | Stop all movement |
| `CAMERA:{dx}:{dy}` | Pan camera by delta pixels |
| `CAMERA_RESET` | Reset camera to default position |

**Port 5006 — Video Stream (Unity → Python):**
- Continuous JPEG frame stream
- Received by `VideoReceiverThread` (QThread)
- Displayed in RC panel camera feed
- Socket timeout: 1 second (for clean shutdown)

### Unity Integration

**Architecture:**
```
Python (PyQt6)                    Unity (RC Car)
+----------------+               +----------------+
|  RC Panel UI   |  UDP 5005     |  Car Controller |
|  D-Pad Buttons | ------------> |  Movement       |
|  WASD Keys     |  Commands     |  Rigidbody      |
+----------------+               +----------------+
|  Camera Feed   |  UDP 5006     |  Camera         |
|  QLabel        | <------------ |  RenderTexture  |
|  VideoThread   |  JPEG Stream  |  JPEG Encoder   |
+----------------+               +----------------+
```

**Unity Setup Required:**
1. **Car Controller Script** — Listen on UDP port 5005 for commands
2. **Camera Capture Script** — Encode camera view as JPEG, send on port 5006
3. **Network Manager** — Handle UDP sockets on both ports

**Command Flow:**
1. User presses button/key in Python app
2. `send_rc_command()` encodes command as UTF-8
3. UDP packet sent to `127.0.0.1:5005`
4. Unity receives and applies command to car Rigidbody
5. Car moves/turns accordingly

**Video Flow:**
1. Unity camera renders to RenderTexture
2. Encode RenderTexture as JPEG (quality ~75)
3. Send JPEG bytes via UDP to `127.0.0.1:5006`
4. Python `VideoReceiverThread` receives packet
5. Emit `frame_received` signal with bytes
6. `update_camera_feed()` converts to QPixmap and displays

## File Structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point - initializes QApplication and shows the dashboard |
| `app.py` | Main UI class (`SensorDashboardApp`) - layout, cards, charts, chat, polling, drag-and-drop, persistence, RC car control |
| `chart.py` | `ChartWidget` class - matplotlib charts with drag-and-drop, normalization, hover tooltips |
| `worker.py` | `Worker` class - background HTTP GET/POST requests using QThread |
| `gemini_worker.py` | `GeminiWorker` class - Gemini AI integration with function calling |
| `config.py` | Save/load settings to `config.json` |
| `config.json` | Runtime configuration (gitignored) |
| `README.md` | This documentation file |

### app.py - Key Methods

| Method | Description |
|--------|-------------|
| `init_ui()` | Creates the 4-column layout |
| `_create_cards()` | Creates sensor value cards with name, value, and arrow labels |
| `update_cards()` | Updates card values and change indicators (↑↓→) |
| `save_current_config()` | Saves API URL, chart layouts, hidden state to config.json |
| `load_saved_config()` | Restores saved layout on startup |
| `_move_custom_to_center()` | Moves all AI custom charts to center with auto-rename |
| `_on_chart_moved_to_center()` | Handles drag-and-drop from custom to center |
| `fetch_data()` | Polls API for sensor data |
| `on_fetch_result()` | Processes fetched data, updates cards and charts |
| `send_chat()` | Sends message to Gemini and displays response |
| `analyze_data()` | Sends sensor data to Gemini for analysis |
| `_handle_chart_command()` | Parses `/chart` commands with `-n`, `-m`, `-d` flags |
| `toggle_rc_panel()` | Toggles RC control panel visibility |
| `send_rc_command()` | Sends UDP command to RC car (port 5005) |
| `update_camera_feed()` | Displays JPEG frame from video stream |
| `keyPressEvent()` | Handles WASD and E key press for car/camera control |
| `keyReleaseEvent()` | Sends STOP command on key release |
| `eventFilter()` | Captures mouse movement for camera control when E held |

### chart.py - Key Methods

| Method | Description |
|--------|-------------|
| `_build_charts()` | Creates all chart widgets from `current_groups` |
| `_build_draggable_chart()` | Creates a single draggable chart widget |
| `_build_single_chart()` | Creates a chart for the custom area |
| `update_charts()` | Updates all charts with new data, reconnects hover events |
| `remove_chart()` | Removes a chart from the widget |
| `_on_drop()` | Handles drop events for drag-and-drop |
| `_toggle_chart()` | Shows/hides a chart with X/O button |
| `_on_hover()` | Handles mouse hover for tooltips |
| `_clear_charts()` | Clears charts while preserving column layouts |

## Dependencies

```bash
pip install PyQt6 requests matplotlib google-genai
```

**Package Purposes:**
- `PyQt6`: Desktop GUI framework
- `requests`: HTTP requests for API calls
- `matplotlib`: Chart rendering
- `google-genai`: Gemini AI integration

## Configuration

### config.json Structure

```json
{
  "api_url": "https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/get-data.php",
  "gemini_api_key": "",
  "center_charts": {
    "Air Quality": ["co2", "pm1.0", "pm2.5"],
    "Environment": ["temperature", "humidity", "pressure"],
    "Other": ["pm1.0", "pm2.5", "pm10", "gas", "battery"]
  },
  "center_charts_hidden": ["Other"],
  "custom_charts": {
    "My Chart": ["temperature", "humidity"]
  },
  "custom_charts_normalize": {
    "My Chart": true
  }
}
```

### Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `api_url` | string | Server endpoint for sensor data |
| `gemini_api_key` | string | Gemini API key (leave empty for env var) |
| `center_charts` | object | Chart names and their sensor labels |
| `center_charts_hidden` | array | List of hidden chart names |
| `custom_charts` | object | User-created chart configurations |
| `custom_charts_normalize` | object | Normalization settings per chart |

## Slash Commands

| Command | Description |
|---------|-------------|
| `/chart co2 temperature` | Create chart with both sensors |
| `/chart gas co2 -n` | Normalized (0-1 scale) for comparison |
| `/chart pm1.0 pm2.5 pm10 -d` | Separate charts for each sensor |
| `/chart co2 temperature -m My Chart` | Custom chart name |
| `/chart co2 temperature -n -m My Chart` | Normalized with custom name |

**Flags:**
- `-n`: Normalize data to 0-1 range (Min-Max scaling)
- `-m`: Set custom chart name (next token is the name)
- `-d`: Display each sensor in separate charts

## Troubleshooting

### Connection Issues

**"Disconnected" Status**
- Verify API URL is correct
- Click Test to check connection
- Ensure server is running and accessible
- Check firewall/proxy settings

**Polling Not Starting**
- Verify API URL returns valid JSON
- Check server response format
- Look for errors in log panel

### Chart Issues

**Charts Not Updating**
- Ensure polling is started (button shows "Stop Polling")
- Check log for HTTP errors
- Verify API returns `success: true`
- Ensure sensor data exists in response

**Charts Disappearing on Restart**
- Check `config.json` for saved state
- Verify file permissions allow writing
- Look for JSON syntax errors in config

**Drag and Drop Not Working**
- Hover over chart title (cursor changes to hand)
- Drag to valid drop zone (dashed border appears)
- Release mouse button to drop

### AI Issues

**Gemini Not Responding**
- Check internet connection
- Verify API key is set correctly
- Check log for Gemini API errors
- Ensure `google-genai` package is installed

**Chat Not Sending**
- Press Enter to send (not just clicking Send button)
- Check if Gemini panel is visible (click 💭 button)
- Verify API key in config

### RC Car Issues

**Car Not Moving**
- Verify Unity app is listening on UDP port 5005
- Check log panel for "RC | Sent:" messages
- Ensure car commands are being sent (press WASD or click D-pad)

**Video Feed Not Showing**
- Verify Unity app is streaming JPEG on UDP port 5006
- Check log for connection errors
- Ensure firewall allows localhost UDP traffic

**Keyboard Controls Not Working**
- Click on the main app window first (not a text field)
- Text fields (chat input, URL) disable WASD temporarily
- Press E + move mouse for camera control

### Layout Issues

**Sensor Cards Overlapping**
- Resize window to see if layout adjusts
- Check minimum window size (1400x750)
- Restart app to reset layout

**Charts Not Saving**
- Verify `config.json` is writable
- Check log for save errors
- Ensure no JSON syntax errors

## License

This project is for educational purposes.

## about Unity 
https://github.com/haru452/es.git
this is folder.