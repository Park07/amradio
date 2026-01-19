# UGL Tunnel AM Break-In System - Control Panel GUI

**Industrial-grade control interface for emergency radio broadcast**

## Quick Start

```bash
# Install DearPyGui
pip install dearpygui

# Run the application
python tunnel_am_breakin_gui.py
```

## Features

| Feature | Description |
|---------|-------------|
| **Industrial Dark Theme** | Control room aesthetic |
| **Dual Channel Support** | 531 kHz + 702 kHz simultaneous |
| **Real-time Spectrum** | RF output visualisation |
| **Audio Waveform** | Live audio monitoring |
| **Keyboard Shortcuts** | F1/SPACE = Broadcast, ESC = Stop |
| **Audit Logging** | Timestamped event log |
| **Channel Control** | Enable/disable individual channels |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F1` or `SPACE` | Toggle broadcast |
| `ESC` | Emergency stop |

## Configuration

Edit the `Config` class in the script:

```python
class Config:
    RP_IP = "192.168.1.100"  # Red Pitaya IP address
    RP_PORT = 5000           # SCPI port

    CHANNELS = [
        {"id": 1, "freq_khz": 531, "name": "Channel 1"},
        {"id": 2, "freq_khz": 702, "name": "Channel 2"},
        # Add more channels as needed (up to 12)
    ]
```

## Architecture

```
┌─────────────────┐     SCPI Commands      ┌─────────────────┐
│                 │ ───────────────────▶   │                 │
│   Python GUI    │   FREQ:CARRIER 531000  │   Red Pitaya    │
│   (DearPyGui)   │   MSG:SELECT emergency │   (FPGA)        │
│                 │   OUTPUT:STATE ON      │                 │
└─────────────────┘ ◀───────────────────   └─────────────────┘
                       Status/Telemetry
```

## Requirements

- Python 3.8+
- DearPyGui 2.0+
- Red Pitaya 125-10 (for actual RF output)

## Screenshots

The GUI features:
- Dark industrial color scheme
- Real-time RF spectrum analyser
- Audio waveform display
- Channel status panels with level meters
- Large emergency broadcast button
- System event log

## Project

**UNSW EPI x UGL Engineering**
Tunnel AM Radio Break-In System
January 2026# UGL Tunnel AM Break-In System - Control Panel GUI

**Industrial-grade control interface for emergency radio broadcast**

## Quick Start

```bash
# Install DearPyGui
pip install dearpygui

# Run the application
python tunnel_am_breakin_gui.py
```

## Features

| Feature | Description |
|---------|-------------|
| **Industrial Dark Theme** | Control room aesthetic |
| **Dual Channel Support** | 531 kHz + 702 kHz simultaneous |
| **Real-time Spectrum** | RF output visualization |
| **Audio Waveform** | Live audio monitoring |
| **Keyboard Shortcuts** | F1/SPACE = Broadcast, ESC = Stop |
| **Audit Logging** | Timestamped event log |
| **Channel Control** | Enable/disable individual channels |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F1` or `SPACE` | Toggle broadcast |
| `ESC` | Emergency stop |

## Configuration

Edit the `Config` class in the script:

```python
class Config:
    RP_IP = "192.168.1.100"  # Red Pitaya IP address
    RP_PORT = 5000           # SCPI port

    CHANNELS = [
        {"id": 1, "freq_khz": 531, "name": "Channel 1"},
        {"id": 2, "freq_khz": 702, "name": "Channel 2"},
        # Add more channels as needed (up to 12)
    ]
```

## Architecture

```
┌─────────────────┐     SCPI Commands      ┌─────────────────┐
│                 │ ───────────────────▶   │                 │
│   Python GUI    │   FREQ:CARRIER 531000  │   Red Pitaya    │
│   (DearPyGui)   │   MSG:SELECT emergency │   (FPGA)        │
│                 │   OUTPUT:STATE ON      │                 │
└─────────────────┘ ◀───────────────────   └─────────────────┘
                       Status/Telemetry
```

## Requirements

- Python 3.8+
- DearPyGui 2.0+
- Red Pitaya 125-10 (for actual RF output)

## Screenshots

The GUI features:
- Dark industrial color scheme
- Real-time RF spectrum analyzer
- Audio waveform display
- Channel status panels with level meters
- Large emergency broadcast button
- System event log

## Project

**UNSW EPI x UGL Engineering**
Tunnel AM Radio Break-In System
January 2026