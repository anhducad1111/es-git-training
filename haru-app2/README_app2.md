# Haru App 2 - Technical Documentation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Haru App 2 (PyQt6)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐│
│  │ Server      │  │ Sensor      │  │ Charts      │  │ Gemini AI           ││
│  │ Config      │  │ Cards       │  │ (Center)    │  │ Chat + Custom       ││
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘│
│         │                │                │                     │           │
│         └────────────────┴────────────────┴─────────────────────┘           │
│                                    │                                        │
│                              ┌─────┴─────┐                                  │
│                              │  Main App │                                  │
│                              │ (app.py)  │                                  │
│                              └─────┬─────┘                                  │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐             │
│         │                          │                          │             │
│  ┌──────┴──────┐            ┌──────┴──────┐            ┌──────┴──────┐     │
│  │ HTTP GET/POST│            │ UDP Send    │            │ UDP Receive │     │
│  │ (worker.py) │            │ (Port 5005) │            │ (Port 5006) │     │
│  └──────┬──────┘            └──────┬──────┘            └──────┬──────┘     │
│         │                          │                          │             │
└─────────┼──────────────────────────┼──────────────────────────┼─────────────┘
          │                          │                          │
          ▼                          ▼                          ▼
   ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
   │ Cloud API   │            │ Unity       │            │ Unity       │
   │ (Sensor DB) │            │ Car Control │            │ Video Feed  │
   └─────────────┘            └─────────────┘            └─────────────┘
```

## API Integration

### 1. Sensor Data API (GET)

**Endpoint:** `GET https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/get-data.php`

**Purpose:** Fetch latest sensor readings and historical data from the cloud database.

**Request:**
```python
import requests

url = "https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/get-data.php"
response = requests.get(url, timeout=10)
data = response.json()
```

**Response Structure:**
```json
{
  "success": true,
  "server_time": "2026-08-28 10:00:00",
  "latest": {
    "co2": {
      "data": 2164,
      "reading_time": "2026-08-28 09:59:00"
    },
    "temperature": {
      "data": 29.03,
      "reading_time": "2026-08-28 09:59:00"
    },
    "humidity": {
      "data": 65.2,
      "reading_time": "2026-08-28 09:59:00"
    },
    "pm1.0": { "data": 1, "reading_time": "..." },
    "pm2.5": { "data": 2, "reading_time": "..." },
    "pm10": { "data": 3, "reading_time": "..." },
    "pressure": { "data": 1013, "reading_time": "..." },
    "gas": { "data": 150, "reading_time": "..." },
    "battery": { "data": 85, "reading_time": "..." }
  },
  "history": {
    "co2": [
      {"reading_time": "2026-08-28 09:55:00", "data": 2100},
      {"reading_time": "2026-08-28 09:56:00", "data": 2120}
    ],
    "temperature": [
      {"reading_time": "2026-08-28 09:55:00", "data": 28.5},
      {"reading_time": "2026-08-28 09:56:00", "data": 28.8}
    ]
  }
}
```

**Data Flow in App:**
1. `fetch_data()` creates `Worker("get", url)` thread
2. Worker sends HTTP GET request
3. `on_fetch_result()` receives response
4. `update_cards()` updates sensor values in UI
5. `chart_widget.update_charts()` updates all charts

**Polling Interval:** 5 seconds (configurable in app)

### 2. Analysis API (POST)

**Endpoint:** `POST https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/post-analysis.php`

**Purpose:** Send AI analysis results to the server for logging or further processing.

**Request:**
```python
import requests

url = "https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/post-analysis.php"
payload = {
    "content": "Analysis text from Gemini..."
}
response = requests.post(url, json=payload, timeout=10)
```

**Response:**
```json
{
  "success": true,
  "message": "Analysis saved"
}
```

**Data Flow in App:**
1. User clicks "Analyze Data" button
2. `analyze_data()` collects current sensor readings
3. Sends data to Gemini for analysis
4. `Worker("post", url, payload)` sends analysis to server
5. Response appears in chat as system message

### 3. Gemini AI Integration

**Model:** `gemini-3.5-flash-lite`

**Configuration:**
```python
# config.py
DEFAULT_CONFIG = {
    "gemini_api_key": "",  # Leave empty for environment variable
    # ...
}
```

**Function Calling:**
The app uses Gemini's function calling to create custom charts:

```python
# gemini_worker.py
def create_custom_charts(self, custom_groups: dict, normalize: bool = False) -> str:
    """Creates custom charts based on user requests.
    
    Args:
        custom_groups: {"Chart Name": ["sensor1", "sensor2"]}
        normalize: Scale values to 0-1 range
    """
    self.tool_called.emit("create_custom_charts", {
        "custom_groups": custom_groups,
        "normalize": normalize
    })
    return "Custom charts created successfully."
```

**Example Conversation:**
```
User: "Show me temperature and humidity together"
Gemini: [Calls create_custom_charts({"Temperature & Humidity": ["temperature", "humidity"]})]
App: Creates chart and displays it in AI Custom Charts area
```

**System Prompt (Embedded):**
- Includes current sensor readings
- Limits responses to ~100 words
- Handles ambiguous queries about "PM data" → all three PM sensors

### 4. LLM Chart Generation System

#### Overview

The app uses Google's Gemini LLM to generate charts from natural language requests. Instead of manually selecting sensors, users can describe what they want to see, and the AI creates the appropriate chart configuration.

#### How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LLM Chart Generation Flow                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User Input                                                                 │
│  "Show me temperature and humidity trends"                                  │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────┐                                                            │
│  │ Parse Input │                                                            │
│  │ (app.py)    │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │ Gemini      │────>│ Function    │────>│ Create      │                   │
│  │ API Call    │     │ Calling     │     │ Chart       │                   │
│  └─────────────┘     └─────────────┘     └──────┬──────┘                   │
│                                                  │                          │
│                                                  ▼                          │
│                                         ┌─────────────┐                     │
│                                         │ Display     │                     │
│                                         │ in UI       │                     │
│                                         └─────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Step 1: User Request Processing

**Natural Language Input Examples:**
- "Show me temperature and humidity together"
- "I want to see air quality data"
- "Compare PM1.0 and PM2.5"
- "Show gas sensor trends"
- "Create a chart with all environment sensors"

**Input Processing in `app.py`:**
```python
def send_chat(self):
    text = self.chat_input.text().strip()
    if not text:
        return
    
    # Check for slash commands first
    if text.startswith("/chart"):
        self._handle_chart_command(text)
        return
    
    # Send to Gemini for natural language processing
    self.append_chat("You", text)
    self.gemini_worker.send_message(text)
```

#### Step 2: Gemini Function Calling

**Function Definition:**
```python
# gemini_worker.py
def create_custom_charts(self, custom_groups: dict, normalize: bool = False) -> str:
    """Creates custom charts based on user requests.
    
    Args:
        custom_groups: A dictionary where keys are chart titles and values are lists 
                       of sensor names.
                       Valid sensor names: "co2", "pm1.0", "pm2.5", "pm10", 
                       "temperature", "humidity", "pressure", "gas", "battery".
                       Example: {"CO2 Levels": ["co2"]}
        normalize: If True, apply Min-Max normalization to scale all values to 0-1 range.
                   Useful when comparing sensors with vastly different value scales.
    
    Returns:
        Confirmation message.
    """
    self.tool_called.emit("create_custom_charts", {
        "custom_groups": custom_groups, 
        "normalize": normalize
    })
    return "Custom charts created successfully."
```

**Gemini Client Initialization:**
```python
def init_chat(self):
    try:
        self.client = genai.Client(api_key=self.api_key)
        self.chat = self.client.chats.create(
            model='gemini-3.5-flash-lite',
            config={
                'tools': [self.create_custom_charts],  # Register function
                'temperature': 0.7,  # Balance creativity and accuracy
            }
        )
        return True
    except Exception as e:
        self.error.emit(f"Failed to initialize Gemini: {str(e)}")
        return False
```

#### Step 3: Tool Call Handling

**Signal Connection in `app.py`:**
```python
# Connect tool_called signal
self.gemini_worker.tool_called.connect(self._handle_tool_call)

def _handle_tool_call(self, tool_name, args):
    """Handle Gemini function calls"""
    if tool_name == "create_custom_charts":
        custom_groups = args.get("custom_groups", {})
        normalize = args.get("normalize", False)
        
        # Create charts in the AI Custom Charts area
        for chart_name, sensors in custom_groups.items():
            self.custom_charts[chart_name] = sensors
            if normalize:
                self.custom_charts_normalize[chart_name] = True
        
        # Save configuration
        self.save_current_config()
        
        # Rebuild charts
        self.chart_widget._build_charts()
        
        self.append_chat("System", f"Created {len(custom_groups)} chart(s)")
```

#### Step 4: Chart Creation

**Chart Configuration Generation:**
```python
def _build_single_chart(self, chart_name, sensor_keys, normalize=False):
    """Create a single chart widget"""
    # Get historical data for these sensors
    chart_data = {}
    for sensor_key in sensor_keys:
        if sensor_key in self.history_data:
            points = self.history_data[sensor_key]
            if normalize:
                points = self.normalize_data(points)
            chart_data[sensor_key] = points
    
    # Create chart widget
    chart = ChartWidget(
        title=chart_name,
        data=chart_data,
        sensor_keys=sensor_keys,
        normalize=normalize
    )
    
    return chart
```

**Data Normalization (when `-n` flag or `normalize=True`):**
```python
def normalize_data(self, data_points):
    """Min-Max normalization to 0-1 range"""
    values = [p["data"] for p in data_points]
    if not values:
        return data_points
    
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        return [{"reading_time": p["reading_time"], "data": 0.5} 
                for p in data_points]
    
    normalized = []
    for p in data_points:
        norm_val = (p["data"] - min_val) / (max_val - min_val)
        normalized.append({
            "reading_time": p["reading_time"],
            "data": norm_val
        })
    return normalized
```

#### Example Interactions

**Example 1: Simple Chart Request**
```
User: "Show me temperature and humidity together"

Gemini Response: [Calls create_custom_charts({
    "Temperature & Humidity": ["temperature", "humidity"]
})]

Result: Single chart with both temperature and humidity lines
```

**Example 2: Normalized Comparison**
```
User: "Compare gas and CO2 on the same scale"

Gemini Response: [Calls create_custom_charts({
    "Gas vs CO2": ["gas", "co2"]
}, normalize=True)]

Result: Normalized chart (0-1 scale) showing relative trends
```

**Example 3: Multiple Charts**
```
User: "Create separate charts for each PM sensor"

Gemini Response: [Calls create_custom_charts({
    "PM1.0": ["pm1.0"],
    "PM2.5": ["pm2.5"],
    "PM10": ["pm10"]
})]

Result: Three separate charts for each particulate matter sensor
```

**Example 4: Complex Request**
```
User: "I want to see air quality trends with CO2 and all PM sensors, normalized"

Gemini Response: [Calls create_custom_charts({
    "Air Quality Trends": ["co2", "pm1.0", "pm2.5", "pm10"]
}, normalize=True)]

Result: Single normalized chart with all four sensors
```

#### Slash Commands (Alternative to Natural Language)

**Command Syntax:**
```
/chart <sensor1> <sensor2> ... [flags]
```

**Available Flags:**
- `-n` : Normalize data to 0-1 range
- `-m <name>` : Set custom chart name
- `-d` : Display each sensor in separate charts

**Examples:**
```bash
# Basic chart
/chart co2 temperature

# Normalized chart
/chart gas co2 -n

# Custom name
/chart co2 temperature -m My Analysis

# Separate charts for PM sensors
/chart pm1.0 pm2.5 pm10 -d

# Combined flags
/chart temperature humidity -n -m Environment Data
```

**Command Parsing in `app.py`:**
```python
def _handle_chart_command(self, text):
    """Parse /chart commands with flags"""
    parts = text.split()
    if len(parts) < 2:
        self.append_chat("System", "Usage: /chart <sensors> [flags]")
        return
    
    sensors = []
    normalize = False
    separate = False
    custom_name = None
    
    i = 1  # Skip "/chart"
    while i < len(parts):
        if parts[i] == "-n":
            normalize = True
        elif parts[i] == "-d":
            separate = True
        elif parts[i] == "-m" and i + 1 < len(parts):
            custom_name = parts[i + 1]
            i += 1
        elif parts[i] in VALID_SENSORS:
            sensors.append(parts[i])
        else:
            # Try to expand PM shorthand
            if parts[i] in ["pm", "pms", "pm data", "particulate matter", "dust"]:
                sensors.extend(["pm1.0", "pm2.5", "pm10"])
            else:
                self.append_chat("System", f"Unknown sensor: {parts[i]}")
        i += 1
    
    if not sensors:
        self.append_chat("System", "No valid sensors specified")
        return
    
    # Create chart(s)
    chart_name = custom_name or "Custom Chart"
    
    if separate:
        # Create separate chart for each sensor
        for sensor in sensors:
            self.custom_charts[f"{sensor.upper()} Chart"] = [sensor]
            if normalize:
                self.custom_charts_normalize[f"{sensor.upper()} Chart"] = True
    else:
        # Create single chart with all sensors
        self.custom_charts[chart_name] = sensors
        if normalize:
            self.custom_charts_normalize[chart_name] = True
    
    self.save_current_config()
    self.chart_widget._build_charts()
    self.append_chat("System", f"Created chart(s) for: {', '.join(sensors)}")
```

#### System Prompt Context

**Current Sensor Data in Prompt:**
The system prompt includes real-time sensor values to help Gemini understand the current state:

```python
system_prompt = f"""You are a sensor data analyst. Current readings:
- CO2: {latest.get('co2', {}).get('data', 'N/A')} ppm
- Temperature: {latest.get('temperature', {}).get('data', 'N/A')}°C
- Humidity: {latest.get('humidity', {}).get('data', 'N/A')}%
- Pressure: {latest.get('pressure', {}).get('data', 'N/A')} hPa
- PM1.0: {latest.get('pm1.0', {}).get('data', 'N/A')} µg/m³
- PM2.5: {latest.get('pm2.5', {}).get('data', 'N/A')} µg/m³
- PM10: {latest.get('pm10', {}).get('data', 'N/A')} µg/m³
- Gas: {latest.get('gas', {}).get('data', 'N/A')}
- Battery: {latest.get('battery', {}).get('data', 'N/A')}%

Respond in ~100 words. Use create_custom_charts function when user asks for charts.
Valid sensor keys: co2, pm1.0, pm2.5, pm10, temperature, humidity, pressure, gas, battery
"""
```

**Ambiguity Rules:**
- "pm" / "pms" / "pm data" / "particulate matter" / "dust" → all three PM sensors
- "environment" → temperature, humidity, pressure
- "air quality" → co2, pm1.0, pm2.5, pm10

#### Configuration Storage

**Custom Charts in config.json:**
```json
{
  "custom_charts": {
    "Temperature & Humidity": ["temperature", "humidity"],
    "Air Quality Trends": ["co2", "pm1.0", "pm2.5", "pm10"]
  },
  "custom_charts_normalize": {
    "Air Quality Trends": true
  }
}
```

**Saving After LLM Generation:**
```python
def save_current_config(self):
    """Save current layout to config.json"""
    config = {
        "api_url": self.api_url,
        "gemini_api_key": self.gemini_api_key,
        "center_charts": self.center_charts,
        "center_charts_hidden": self.center_charts_hidden,
        "custom_charts": self.custom_charts,
        "custom_charts_normalize": self.custom_charts_normalize,
    }
    save_config(config)
```

#### Visual Feedback

**Chart Display:**
- Charts appear in "AI Custom Charts" area (right panel)
- Each chart shows sensor names in legend
- Hover tooltips show exact values
- X/Y axis auto-scale based on data
- Toggle visibility with X/O button

**Chat Feedback:**
```
System: Created 2 chart(s)
- Temperature & Humidity
- Air Quality Trends (normalized)
```

## Unity Integration

### 1. UDP Communication Protocol

**Port 5005: Car Commands (Python → Unity)**

| Command | Format | Description |
|---------|--------|-------------|
| `FORWARD` | UTF-8 string | Move car forward |
| `BACKWARD` | UTF-8 string | Move car backward |
| `LEFT` | UTF-8 string | Turn car left |
| `RIGHT` | UTF-8 string | Turn car right |
| `STOP` | UTF-8 string | Stop all movement |
| `CAMERA:{dx}:{dy}` | UTF-8 string | Pan camera by delta pixels |
| `CAMERA_RESET` | UTF-8 string | Reset camera to default |

**Python Implementation:**
```python
import socket

def send_rc_command(self, command: str):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(command.encode("utf-8"), ("127.0.0.1", 5005))
        sock.close()
    except Exception as e:
        print(f"Error sending {command}: {e}")
```

**Unity Implementation (C#):**
```csharp
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

public class CarController : MonoBehaviour
{
    private UdpClient udpClient;
    private IPEndPoint remoteEndPoint;
    public Rigidbody carRigidbody;
    public float moveForce = 10f;
    public float turnTorque = 5f;

    void Start()
    {
        udpClient = new UdpClient(5005);
        remoteEndPoint = new IPEndPoint(IPAddress.Any, 0);
        InvokeReceivingLoop();
    }

    async void InvokeReceivingLoop()
    {
        while (true)
        {
            var data = await udpClient.ReceiveAsync();
            string command = Encoding.UTF8.GetString(data.Buffer);
            ProcessCommand(command);
        }
    }

    void ProcessCommand(string command)
    {
        switch (command)
        {
            case "FORWARD":
                carRigidbody.AddForce(transform.forward * moveForce);
                break;
            case "BACKWARD":
                carRigidbody.AddForce(-transform.forward * moveForce);
                break;
            case "LEFT":
                carRigidbody.AddTorque(Vector3.up * turnTorque);
                break;
            case "RIGHT":
                carRigidbody.AddTorque(Vector3.up * -turnTorque);
                break;
            case "STOP":
                carRigidbody.linearVelocity = Vector3.zero;
                carRigidbody.angularVelocity = Vector3.zero;
                break;
            default:
                if (command.StartsWith("CAMERA:"))
                {
                    CameraControl(command);
                }
                else if (command == "CAMERA_RESET")
                {
                    CameraReset();
                }
                break;
        }
    }
}
```

**Port 5006: Video Stream (Unity → Python)**

**Unity Implementation (C#):**
```csharp
using System.Net;
using System.Net.Sockets;
using UnityEngine;

public class VideoStreamer : MonoBehaviour
{
    public Camera targetCamera;
    public int width = 640;
    public int height = 480;
    public int quality = 75;
    public float sendInterval = 0.1f; // 10 FPS

    private UdpClient udpClient;
    private IPEndPoint remoteEndPoint;
    private RenderTexture renderTexture;
    private Texture2D texture2D;

    void Start()
    {
        udpClient = new UdpClient(5006);
        remoteEndPoint = new IPEndPoint(IPAddress.Loopback, 5006);
        
        renderTexture = new RenderTexture(width, height, 24);
        texture2D = new Texture2D(width, height, TextureFormat.RGB24, false);
        
        targetCamera.targetTexture = renderTexture;
        
        InvokeRepeating(nameof(SendFrame), 0, sendInterval);
    }

    void SendFrame()
    {
        // Render camera to texture
        targetCamera.Render();
        
        // Read pixels from render texture
        RenderTexture.active = renderTexture;
        texture2D.ReadPixels(new Rect(0, 0, width, height), 0, 0);
        texture2D.Apply();
        
        // Encode as JPEG
        byte[] jpegBytes = texture2D.EncodeToJPG(quality);
        
        // Send via UDP (split into chunks if needed)
        udpClient.Send(jpegBytes, jpegBytes.Length, remoteEndPoint);
    }

    void OnDestroy()
    {
        udpClient?.Close();
        renderTexture?.Release();
    }
}
```

**Python Implementation (Receiver):**
```python
from PyQt6.QtCore import QThread, pyqtSignal
import socket

class VideoReceiverThread(QThread):
    frame_received = pyqtSignal(bytes)
    
    def __init__(self, port=5006):
        super().__init__()
        self.port = port
        self.running = False
    
    def run(self):
        self.running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", self.port))
        sock.settimeout(1.0)  # 1 second timeout for clean shutdown
        
        while self.running:
            try:
                data, addr = sock.recvfrom(65536)  # Max UDP packet size
                self.frame_received.emit(data)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Video receive error: {e}")
        
        sock.close()
    
    def stop(self):
        self.running = False
```

### 2. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Unity RC Car System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    UDP 5005     ┌─────────────┐               │
│  │  Python     │ ──────────────> │  Car        │               │
│  │  App        │    Commands     │  Controller │               │
│  └─────────────┘                 └──────┬──────┘               │
│                                         │                       │
│                                    ┌────┴────┐                 │
│                                    │ Rigidbody│                 │
│                                    └────┬────┘                 │
│                                         │                       │
│                                    ┌────┴────┐                 │
│                                    │  Car    │                 │
│                                    │  Movement│                 │
│                                    └─────────┘                 │
│                                                                 │
│  ┌─────────────┐    UDP 5006     ┌─────────────┐               │
│  │  Python     │ <────────────── │  Camera     │               │
│  │  App        │    JPEG Stream  │  Capture    │               │
│  └─────────────┘                 └──────┬──────┘               │
│                                         │                       │
│                                    ┌────┴────┐                 │
│                                    │ RenderTex│                 │
│                                    └─────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration System

### config.json Structure

```json
{
  "api_url": "https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/get-data.php",
  "gemini_api_key": "",
  "center_charts": {
    "Air Quality": ["co2"],
    "Environment": ["temperature", "humidity", "pressure"],
    "Other": ["pm1.0", "pm2.5", "pm10", "gas", "battery"]
  },
  "center_charts_hidden": [],
  "custom_charts": {
    "My Custom Chart": ["temperature", "humidity"]
  },
  "custom_charts_normalize": {
    "My Custom Chart": true
  }
}
```

### Configuration Loading

```python
# config.py
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                # Merge with defaults
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_CONFIG.copy()
```

### Configuration Saving

```python
def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"Failed to save config: {e}")
```

## Worker Thread System

### HTTP Worker

```python
# worker.py
class Worker(QThread):
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str)
    
    def __init__(self, task, url, payload=None, headers=None):
        super().__init__()
        self.task = task  # "get" or "post"
        self.url = url
        self.payload = payload
        self.headers = headers or {}
    
    def run(self):
        try:
            if self.task == "get":
                response = requests.get(self.url, headers=self.headers, timeout=10)
                self.finished.emit("get", response)
            elif self.task == "post":
                response = requests.post(self.url, json=self.payload, 
                                       headers=self.headers, timeout=10)
                self.finished.emit("post", response)
        except requests.exceptions.RequestException as e:
            self.error.emit(str(e))
```

### Gemini Worker

```python
# gemini_worker.py
class GeminiWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    tool_called = pyqtSignal(str, dict)
    
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.client = None
        self.chat = None
    
    def init_chat(self):
        try:
            self.client = genai.Client(api_key=self.api_key)
            self.chat = self.client.chats.create(
                model='gemini-3.5-flash-lite',
                config={
                    'tools': [self.create_custom_charts],
                    'temperature': 0.7,
                }
            )
            return True
        except Exception as e:
            self.error.emit(f"Failed to initialize Gemini: {str(e)}")
            return False
    
    def send_message(self, text):
        if not self.chat:
            if not self.init_chat():
                return
        self._pending_message = text
        self.start()  # Starts the thread
    
    def run(self):
        try:
            if self._pending_message:
                response = self.chat.send_message(self._pending_message)
                self._pending_message = None
                if response.text:
                    self.finished.emit(response.text)
        except Exception as e:
            self.error.emit(f"Gemini error: {str(e)}")
```

## Chart System

### Chart Types

1. **Default Charts (Center)**
   - Air Quality (CO2)
   - Environment (Temperature, Humidity, Pressure)
   - Other (PM1.0, PM2.5, PM10, Gas, Battery)

2. **Custom Charts (Right Panel)**
   - Created by user via slash commands or AI
   - Can be normalized (0-1 scale)
   - Drag-and-drop enabled

### Chart Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Chart Update Flow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. fetch_data()                                                │
│     │                                                           │
│     ▼                                                           │
│  2. Worker("get", url) ─────────────────────────────────────┐  │
│     │                                                       │  │
│     ▼                                                       │  │
│  3. on_fetch_result(response)                               │  │
│     │                                                       │  │
│     ├──> update_cards(data)                                 │  │
│     │    └──> Updates sensor values in UI                   │  │
│     │                                                       │  │
│     └──> chart_widget.update_charts(history)                │  │
│          ├──> Updates all default charts                    │  │
│          └──> Updates all custom charts                     │  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Normalization Algorithm

```python
def normalize_data(data_points):
    """Min-Max normalization to 0-1 range"""
    values = [p["data"] for p in data_points]
    if not values:
        return data_points
    
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        return [{"reading_time": p["reading_time"], "data": 0.5} 
                for p in data_points]
    
    normalized = []
    for p in data_points:
        norm_val = (p["data"] - min_val) / (max_val - min_val)
        normalized.append({
            "reading_time": p["reading_time"],
            "data": norm_val
        })
    return normalized
```

## Drag and Drop System

### MIME Data Format

```python
# Custom MIME type for chart transfer
CHART_MIME_TYPE = "application/x-chart"

# Data format: JSON with chart configuration
{
    "source": "center" | "custom",
    "chart_name": "Air Quality",
    "sensors": ["co2", "pm1.0"],
    "normalize": false
}
```

### Drop Zone Handling

```python
def _on_drop(self, event):
    """Handle drop events for chart transfer"""
    mime_data = event.mimeData()
    
    if mime_data.hasFormat(CHART_MIME_TYPE):
        chart_data = json.loads(mime_data.data(CHART_MIME_TYPE).data().decode())
        
        if chart_data["source"] == "center":
            # Copy to custom charts
            self.custom_charts[chart_data["chart_name"]] = chart_data["sensors"]
        else:
            # Move from custom to center
            del self.custom_charts[chart_data["chart_name"]]
            self.center_charts[chart_data["chart_name"]] = chart_data["sensors"]
        
        self.save_current_config()
        self._build_charts()
```

## Keyboard Control System

### Key Event Handling

```python
def keyPressEvent(self, event):
    if event.isAutoRepeat():
        return
    
    if self._is_text_focused():
        return super().keyPressEvent(event)
    
    if not self.rc_side_panel.isVisible():
        return super().keyPressEvent(event)
    
    if event.key() == Qt.Key.Key_E:
        self.is_e_pressed = True
        self.last_mouse_pos = QCursor.pos()
        return
    
    key_map = {
        Qt.Key.Key_W: "FORWARD",
        Qt.Key.Key_S: "BACKWARD",
        Qt.Key.Key_A: "LEFT",
        Qt.Key.Key_D: "RIGHT",
    }
    
    command = key_map.get(event.key())
    if command:
        self.send_rc_command(command)
    else:
        super().keyPressEvent(event)
```

### Camera Control with Mouse

```python
def eventFilter(self, obj, event):
    if (self.rc_side_panel.isVisible() and 
        event.type() == QEvent.Type.MouseMove and 
        self.is_e_pressed):
        
        current_pos = QCursor.pos()
        if self.last_mouse_pos is not None:
            dx = current_pos.x() - self.last_mouse_pos.x()
            dy = current_pos.y() - self.last_mouse_pos.y()
            
            if dx != 0 or dy != 0:
                self.send_rc_command(f"CAMERA:{dx}:{dy}")
        
        self.last_mouse_pos = current_pos
    
    return super().eventFilter(obj, event)
```

## Floating Action Buttons

### Position Calculation

```python
def update_floating_buttons_pos(self):
    """Position FABs above log tab, aligned to right edge"""
    if hasattr(self, 'floating_btn_container'):
        self.floating_btn_container.adjustSize()
        x = self.width() - self.floating_btn_container.width() - 30
        y = self.log_tab.y() - self.floating_btn_container.height() - 20
        self.floating_btn_container.move(x, y)
        self.floating_btn_container.raise_()
```

### Resize Handling

```python
def resizeEvent(self, event):
    """Reposition FABs on window resize"""
    super().resizeEvent(event)
    self.update_floating_buttons_pos()
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyQt6 | 6.x | Desktop GUI framework |
| requests | 2.x | HTTP requests |
| matplotlib | 3.x | Chart rendering |
| google-genai | 0.3+ | Gemini AI integration |
| socket | stdlib | UDP communication |
| json | stdlib | Configuration persistence |

## Troubleshooting

### API Issues

**Connection Refused:**
- Check if server is running
- Verify API URL is correct
- Test with curl: `curl https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/get-data.php`

**Invalid JSON Response:**
- Check server logs
- Verify API endpoint exists
- Ensure proper HTTP headers

### Unity Connection Issues

**Car Not Responding:**
1. Check Unity is running on localhost
2. Verify UDP port 5005 is open
3. Check firewall settings
4. Test with: `echo -n "FORWARD" | nc -u localhost 5005`

**Video Feed Not Working:**
1. Verify Unity is streaming on port 5006
2. Check socket is bound correctly
3. Ensure JPEG encoding is enabled
4. Test with: `nc -lu localhost 5006 > test.jpg`

### Performance Issues

**High CPU Usage:**
- Reduce polling interval (default: 5 seconds)
- Lower video quality (default: 75%)
- Reduce video resolution (default: 640x480)

**Memory Leaks:**
- Ensure RenderTexture is released
- Check QPixmap conversion
- Monitor QThread lifecycle

## Development Guide

### Adding New Sensors

1. Add sensor key to `DEFAULT_CONFIG` in `config.py`
2. Update sensor cards in `app.py` → `_create_cards()`
3. Add to chart groups in `config.py`
4. Update system prompt in `gemini_worker.py`

### Adding New Commands

1. Add command to `send_rc_command()` in `app.py`
2. Update Unity `ProcessCommand()` method
3. Add to documentation
4. Test with log panel

### Extending AI Features

1. Add new function to `GeminiWorker` class
2. Register with `tools` parameter
3. Handle `tool_called` signal
4. Update system prompt

## License

This project is for educational purposes.
