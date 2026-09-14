# Speed Control & Auto-Brake

## Overview
Motor speed control with obstacle-based auto-braking system.

## Speed Control

### Manual Control
- **Slider**: 180-255 range (bottom controls)
- **Shift**: Increase speed by 1 per tick (50ms timer)
- **Ctrl**: Decrease speed by 1 per tick (50ms timer)

### Two-Speed System
- `_global_speed`: Slider value, persistent
- `_forward_speed`: Auto-calculated by obstacle distance

### ESP32 Command
```
speed:220    # Set motor speed
```

## Auto-Brake

### Toggle
- **BRAKE** button in bottom controls
- ON/OFF toggle

### Behavior
When auto-brake ON and driving forward:
- **>100cm**: Full speed (255)
- **100cm → 15cm**: Linear slowdown
- **<15cm**: Stop (speed 0)

### Formula
```python
if distance <= 15:
    forward_speed = 0
else:
    ratio = (distance - 15) / 85.0
    forward_speed = int(255 * ratio)
```

### ESP32 API
```python
# Set auto-brake
esp32_api.set_brake(True)   # Enable
esp32_api.set_brake(False)  # Disable

# GET /api/distance?brake=1  # Enable and get distance
# GET /api/distance?brake=0  # Disable and get distance
```

## UI Components

### Speed Group
- Slider: 80px width
- Label: Current speed value (cyan)

### Brake Group
- Toggle button: ON/OFF
- Color: Green when ON, Gray when OFF

## Safety Notes
- Auto-brake only affects forward movement
- Backward movement unaffected
- Emergency stop available via STOP button
