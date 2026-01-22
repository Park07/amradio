# UGL AM Radio Control System

A professional GUI application for controlling AM radio broadcast hardware via SCPI commands over TCP/IP.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)

## Overview

This application provides a graphical interface for operators to control an AM radio broadcast system built on Red Pitaya FPGA hardware. It's designed for tunnel emergency broadcast systems where reliable, simple operation is critical.

### Features

- **Dual Channel Control** - Independent frequency control for two AM channels
- **Real-time Status** - Live connection monitoring and system feedback
- **Audio Source Selection** - Switch between pre-loaded BRAM audio and live ADC input
- **Message Presets** - Quick selection of emergency broadcast messages
- **Audit Logging** - Complete log of all operations for compliance
- **Dark Theme** - Operator-friendly interface for control room environments

## Architecture

The application follows the **Model-View-Controller (MVC)** pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                         VIEW                                │
│                      (main.py)                              │
│   UI Components: Buttons, Inputs, Status Display            │
└──────────────────────────┬──────────────────────────────────┘
                           │ User Events
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      CONTROLLER                             │
│                   (controller.py)                           │
│   Business Logic: Command Building, Validation              │
└─────────┬───────────────────────────────────────┬───────────┘
          │ State Updates                         │ SCPI Commands
          ▼                                       ▼
┌─────────────────────┐                ┌─────────────────────┐
│       MODEL         │                │    RED PITAYA       │
│    (model.py)       │                │   (TCP:5000)        │
│  Application State  │                │   FPGA Hardware     │
└─────────────────────┘                └─────────────────────┘
```

### File Structure

```
ugl_am_radio/
├── main.py              # Application entry point & View
├── model.py             # Data models and state management
├── controller.py        # Business logic and SCPI communication
├── config.py            # Application constants
├── config.yaml          # User-configurable settings
├── mock_server.py       # Development/testing server
├── requirements.txt     # Python dependencies
├── tests/               # Unit tests
│   ├── __init__.py
│   ├── conftest.py      # Pytest fixtures
│   ├── test_model.py    # Model unit tests
│   └── test_controller.py # Controller unit tests
└── README.md
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Park07/amradio.git
   cd amradio/ugl_am_radio
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

## Configuration

### config.yaml

```yaml
connection:
  default_ip: "192.168.0.100"
  default_port: 5000
  timeout_seconds: 5
  retry_attempts: 3

channels:
  ch1:
    default_freq_khz: 700
    min_freq_khz: 530
    max_freq_khz: 1700
  ch2:
    default_freq_khz: 900
    min_freq_khz: 530
    max_freq_khz: 1700

audio:
  default_source: "BRAM"
  messages:
    - id: 1
      name: "Emergency Evacuation"
    - id: 2
      name: "System Test"
    - id: 3
      name: "All Clear"
```

## Usage

### Basic Operation

1. **Connect to Hardware**
   - Enter Red Pitaya IP address
   - Click "Connect"
   - Status bar shows connection state

2. **Configure Channels**
   - Enable desired channels (CH1/CH2)
   - Set carrier frequency (530-1700 kHz)

3. **Select Audio Source**
   - BRAM: Pre-loaded emergency message
   - ADC: Live audio input

4. **Broadcast**
   - Click "Start Broadcast" to begin transmission
   - Click "Stop Broadcast" to end

### SCPI Commands

The application sends standard SCPI commands:

| Command | Description |
|---------|-------------|
| `*IDN?` | Query device identity |
| `OUTPUT:STATE ON/OFF` | Enable/disable RF output |
| `CH1:OUTPUT ON/OFF` | Enable/disable channel 1 |
| `CH1:FREQ <Hz>` | Set channel 1 frequency |
| `SOURCE:INPUT BRAM/ADC` | Select audio source |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_model.py -v
```

### Mock Server

For development without hardware:

```bash
# Terminal 1: Start mock server
python mock_server.py

# Terminal 2: Run application
python main.py
# Connect to 127.0.0.1:5000
```

### Code Style

This project follows PEP 8 guidelines. Run linting with:

```bash
# Install dev dependencies
pip install flake8 black mypy

# Format code
black .

# Check style
flake8 .

# Type checking
mypy .
```

## Testing

### Test Coverage

| Module | Coverage |
|--------|----------|
| model.py | 95% |
| controller.py | 85% |
| config.py | 100% |

### Test Categories

- **Unit Tests** - Individual component testing
- **Integration Tests** - Component interaction
- **Mock Tests** - Hardware simulation

## Hardware Integration

### Red Pitaya Setup

1. Load FPGA bitstream with AM radio modules
2. Copy `am_scpi_server.py` to Red Pitaya
3. Run server: `python3 am_scpi_server.py`
4. Connect GUI to Red Pitaya IP

### FPGA Register Map

| Address | Register | Description |
|---------|----------|-------------|
| 0x00 | CTRL | Control bits (master, ch1, ch2, source) |
| 0x04 | CH1_FREQ | Channel 1 NCO phase increment |
| 0x08 | CH2_FREQ | Channel 2 NCO phase increment |
| 0x0C | STATUS | Read-only status register |

## Troubleshooting

### Connection Issues

| Problem | Solution |
|---------|----------|
| Connection timeout | Check IP address, ensure server is running |
| Connection refused | Verify port 5000 is open, check firewall |
| No response | Restart SCPI server on Red Pitaya |

### Common Errors

```
"Frequency out of range"
→ Enter value between 530-1700 kHz

"Not connected"
→ Click Connect before sending commands

"Send error: Broken pipe"
→ Server disconnected, reconnect
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## Authors

- **William Park** - GUI Development
- **Bowen** - FPGA Integration

## Acknowledgments

- UGL Limited - Project sponsor
- University of New South Wales - Academic support
- Red Pitaya - Hardware platform
