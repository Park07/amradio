# UGL Tunnel AM Break-In System

Professional control panel for emergency AM broadcast in road tunnels using Red Pitaya FPGA.

**UNSW EPI Project for UGL**

![Architecture](docs/architecture.png)

## Features

- 🔴 **Emergency Broadcast** - One-click activation with safety confirmation
- 📻 **Multi-Channel** - Simultaneous broadcast on 531 kHz and 702 kHz
- 📊 **Real-Time Spectrum** - Live RF spectrum analyzer display
- 🎤 **Audio Monitoring** - Waveform visualization
- 🔌 **SCPI Control** - Red Pitaya FPGA communication
- 💾 **Settings Persistence** - Remembers IP and preferences
- ⌨️ **Keyboard Shortcuts** - F1/Space to broadcast, ESC to stop

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd tunnel_am_breakin

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m tunnel_am_breakin
```

## Usage

### Basic Usage

```bash
# Run with mock SCPI client (for testing without hardware)
python -m tunnel_am_breakin

# Run in demo mode
python -m tunnel_am_breakin --demo

# Run with real Red Pitaya connection
python -m tunnel_am_breakin --real --ip 192.168.1.100
```

### Python API

```python
from tunnel_am_breakin import TunnelAMBreakIn

# Simple usage
app = TunnelAMBreakIn()
app.run()

# Custom configuration
from tunnel_am_breakin import SystemModel, MainView, SCPIClient

model = SystemModel()
view = MainView()
scpi = SCPIClient()

app = TunnelAMBreakIn(model=model, view=view, scpi=scpi, use_mock=False)
app.run()
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      TunnelAMBreakIn (App)                      │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   SystemModel │  │   MainView    │  │  Controller   │       │
│  │   (State)     │◄─┤   (Display)   │◄─┤  (Logic)      │       │
│  └───────────────┘  └───────────────┘  └───────┬───────┘       │
│                                                 │               │
│                                        ┌───────▼───────┐       │
│                                        │  SCPIClient   │       │
│                                        │  (Hardware)   │       │
│                                        └───────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ SCPI over TCP
                    ┌─────────────────────┐
                    │   Red Pitaya FPGA   │
                    │   - NCO             │
                    │   - AM Modulator    │
                    │   - BRAM Audio      │
                    └─────────────────────┘
```

## Project Structure

```
tunnel_am_breakin/
├── __init__.py          # Package exports
├── __main__.py          # Entry point (python -m tunnel_am_breakin)
├── app.py               # Main application orchestration
├── configs.py           # All constants and configuration
├── tags.py              # Widget tag management (no magic strings)
├── models.py            # State and data management
├── views.py             # View components (MainView, ChannelView, etc.)
├── ui_builder.py        # UI construction
├── controllers.py       # Business logic and callbacks
├── themes.py            # Industrial dark theme
├── scpi_client.py       # Red Pitaya SCPI communication
└── requirements.txt     # Python dependencies
```

## MVC Architecture

| Component | File | Responsibility |
|-----------|------|----------------|
| **Model** | `models.py` | System state, channel states, logging |
| **View** | `views.py`, `ui_builder.py` | UI components and display |
| **Controller** | `controllers.py` | Business logic, callbacks, hardware |

## SCPI Commands

The GUI sends these commands to the Red Pitaya FPGA:

| Command | Description |
|---------|-------------|
| `FREQ:CH1 531000` | Set channel 1 frequency |
| `FREQ:CH2 702000` | Set channel 2 frequency |
| `MSG:SELECT emergency` | Select broadcast message |
| `OUTPUT:CH1 ON` | Enable channel 1 output |
| `OUTPUT:ALL OFF` | Disable all outputs |
| `STATUS?` | Query system status |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F1` or `Space` | Toggle broadcast |
| `Escape` | Emergency stop |

## Development

### Running Tests

```bash
# Run with pytest
pytest tests/

# Run with coverage
pytest --cov=tunnel_am_breakin tests/
```

### Code Style

```bash
# Format with black
black tunnel_am_breakin/

# Check with flake8
flake8 tunnel_am_breakin/
```

## Configuration

Edit `configs.py` to customize:

- **Channels**: Frequencies and phase increments
- **Messages**: Emergency messages and durations
- **Colors**: UI theme colors
- **Display**: Update rate and buffer sizes

## License

MIT License - UNSW EPI Project

## Authors

UNSW EPI Team - UGL Tunnel Project
