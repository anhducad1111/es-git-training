# Haru App 2 - Sensor Dashboard

## Overview

A PyQt6 desktop application that displays real-time sensor data (9 types from ESP32) via cloud API, with AI-powered analysis using Gemini, custom chart generation, drag-and-drop functionality, and persistent layout state.

## Features

### Real-Time Sensor Monitoring
- **9 Sensor Types**: co2, pm1.0, pm2.5, pm10, temperature, humidity, pressure, gas, battery
- **6 Grouped Cards**: Air Quality, Particulate Matter, Temperature & Humidity, Pressure, Gas, Battery
- **Value Change Indicators**: Arrows (↑↓→) with color coding show sensor trends
  - ↑ Blue (#2196F3): value increased
  - ↓ Red (#FF5252): value decreased
  - → Green (#4CAF50): value unchanged
- **Large Font Display**: 14pt values, 12pt labels for dashboard readability
- **3 Line Charts**: Air Quality, Environment, Other
- **5-Second Polling**: Auto-refresh data from server
- **Stale Data Warning**: Alerts when data is 3+ minutes old

### Gemini AI Chat
- Ask questions about your sensor data
- Get real-time analysis and insights
- Responses limited to ~100 words for quick reading
- Tab completion for sensor names after `/chart`

### AI Custom Charts
- Create custom charts via natural language (e.g., "Show temperature and CO2 together")
- **Persistent**: Custom charts are saved and restored on app restart
- Normalize option for sensors with different scales (`-n` flag)
- Separate charts option (`-d` flag)
- Toggle visibility with X/O button
- Hover tooltips with dynamic positioning (top/bottom based on value)

### Center Charts
- **Persistent**: Layout and hidden state saved across restarts
- Drag-and-drop between center and AI Custom Charts
- **Move to Charts**: Button to move all AI custom charts to center (with auto-rename on conflicts)
- Charts moved from custom to center are visible and saved correctly

### Slash Commands
- `/chart co2 temperature` - Create chart with both sensors
- `/chart gas co2 -n` - Create chart with normalization
- `/chart pm1.0 pm2.5 pm10 -d` - Create separate charts
- Tab completion for sensor names

### Data Analysis
- Click "Analyze Data" to get Gemini insights
- Analysis is automatically sent to server via `api/post-analysis.php`

## How to Use

### 1. Start the Application
```bash
cd haru-app2
python main.py
```

### 2. Configure Server Connection
1. Enter your API URL in the "API URL" field (default: `https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/get-data.php`)
2. Click "Test" to verify connection
3. Click "Start Polling" to begin receiving data

### 3. View Sensor Data
- **Left Column**: Sensor cards show current values with change arrows
- **Center Column**: Line charts show historical trends
- **Right Column**: Gemini chat and AI Custom Charts

### 4. Use Gemini Chat
1. Type a question about your sensors
2. Press Enter to send
3. Press Tab to auto-complete sensor names
4. Get AI-powered insights

### 5. Create Custom Charts
**Option A: Natural Language**
- Type: "Show me temperature and humidity together"
- Gemini creates the chart automatically

**Option B: Slash Command**
- `/chart co2 temperature` - Combined chart
- `/chart gas co2 -n` - Normalized (0-1 scale)
- `/chart pm1.0 pm2.5 pm10 -d` - Separate charts

**Option C: Drag and Drop**
- Drag any chart from center to AI Custom Charts area
- Drag any chart from AI Custom Charts to center

**Option D: Move to Charts Button**
- Click "Move to Charts" to move all AI custom charts to center
- Auto-rename on conflicts (e.g., "Other (2)")

### 6. Analyze Data
1. Click "Analyze Data (Gemini)" button
2. Wait for Gemini response
3. Analysis is sent to server automatically

## Layout

```
+-------------------+-------------------+-------------------+-------------------+
|  Config Panel     |  Sensor Cards     |  Main Charts      |  Gemini Chat      |
|  [API URL]        |  +-------------+  |  Air Quality      |  [Input field]    |
|  [Test] [Poll]    |  | CO2         |  |  +-----------+    |  [Send button]    |
+-------------------+  | 2164 ppm →  |  |  | co2, pm   |    |                   |
                       | +-------------+  |  | /\  /\    |    |                   |
                       | | Particulate |  |  +-----------+    |                   |
                       | | PM1.0: 1 ↑ |  |                   |                   |
                       | | PM2.5: 2 ↓ |  |  Environment      |  AI Custom Charts |
                       | +-------------+  |  +-----------+    |  +-----------+    |
                       | | Temp & Hum  |  |  | temp, hum |    |  | User      |    |
                       | | 29.0 C →    |  |  | /\  /\    |    |  | created   |    |
                       | +-------------+  |  +-----------+    |  | charts    |    |
                       | | ...         |  |                   |  +-----------+    |
                       +-------------------+-------------------+-------------------+
|  [Log]  <-- click to expand                                                       |
+-----------------------------------------------------------------------------------+
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/get-data.php` | GET | Fetch sensor data (latest + history) |
| `/api/post-analysis.php` | POST | Send analysis results |

### POST Request Body
```json
{"content": "Analysis text from Gemini..."}
```

## File Structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point - initializes QApplication and shows the dashboard |
| `app.py` | Main UI class (`SensorDashboardApp`) - layout, cards, charts, chat, polling, drag-and-drop, persistence |
| `chart.py` | `ChartWidget` class - matplotlib charts with drag-and-drop, normalization, hover tooltips |
| `worker.py` | `Worker` class - background HTTP GET/POST requests using QThread |
| `gemini_worker.py` | `GeminiWorker` class - Gemini AI integration with function calling |
| `config.py` | Save/load settings to `config.json` |
| `config.json` | Runtime configuration (gitignored) |

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

### chart.py - Key Methods
| Method | Description |
|--------|-------------|
| `_build_charts()` | Creates all chart widgets from `current_groups` |
| `_build_draggable_chart()` | Creates a single draggable chart widget |
| `update_charts()` | Updates all charts with new data, reconnects hover events |
| `remove_chart()` | Removes a chart from the widget |
| `_on_drop()` | Handles drop events for drag-and-drop |

## Dependencies

```bash
pip install PyQt6 requests matplotlib google-genai
```

## Sensor Data Format

```json
{
  "success": true,
  "server_time": "2026-08-27 12:00:00",
  "latest": {
    "co2": {"data": 2164, "reading_time": "2026-08-27 11:59:00"},
    "temperature": {"data": 29.03, "reading_time": "2026-08-27 11:59:00"}
  },
  "history": {
    "co2": [{"reading_time": "2026-08-27 11:55:00", "data": 2100}, ...],
    "temperature": [{"reading_time": "2026-08-27 11:55:00", "data": 28.5}, ...]
  }
}
```

## Slash Command Options

| Flag | Description |
|------|-------------|
| `-n` | Normalize data to 0-1 range (Min-Max scaling) |
| `-d` | Display each sensor in separate charts |

### Examples
```
/chart co2                    # Single sensor
/chart co2 temperature       # Multiple sensors combined
/chart gas co2 -n            # Normalized for comparison
/chart pm1.0 pm2.5 pm10 -d  # Separate charts
/chart temperature -n -d     # Normalized and separate
```

## Drag and Drop

1. Hover over any chart title to grab it
2. Drag to AI Custom Charts area (right) to copy
3. Drag from AI Custom Charts to center to move
4. Use "Move to Charts" button to move all custom charts to center
5. Use X button to hide, O button to show

## Configuration

Settings are saved to `config.json` (gitignored):

```json
{
  "api_url": "https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/get-data.php",
  "gemini_api_key": "",
  "center_charts": {"Air Quality": ["co2", "pm1.0", "pm2.5"]},
  "center_charts_hidden": ["Other"],
  "custom_charts": {"My Chart": ["temperature", "humidity"]},
  "custom_charts_normalize": {"My Chart": true}
}
```

## Troubleshooting

### "Disconnected" Status
- Check API URL is correct
- Click "Test" to verify connection
- Ensure server is running

### Charts Not Updating
- Click "Start Polling"
- Check log for errors
- Verify API returns data

### Gemini Not Responding
- Check internet connection
- Verify API key is set (hidden in config)
- Check log for Gemini errors

### Charts Disappearing on Restart
- Center charts and AI custom charts are now saved automatically
- Check `config.json` for saved state

![alt text](image.png)
