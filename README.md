# AM Radio Break-in System

A 12-channel AM radio broadcast system using Red Pitaya FPGA for emergency alert transmission.

![Channels: 12](https://img.shields.io/badge/Channels-12-blue)
![Platform: Red Pitaya](https://img.shields.io/badge/Platform-Red%20Pitaya-red)
![GUI: DearPyGui](https://img.shields.io/badge/GUI-DearPyGui-green)

---
....
test
bowen
## Features

| Feature | Status |
|---------|--------|
| 12 simultaneous carrier frequencies | ✅ |
| Runtime frequency configuration (no hardware changes) | ✅ |
| AM modulation with pre-recorded audio | ✅ |
| Dynamic power scaling | ✅ |
| True stateless UI architecture | ✅ |
| Network polling & auto-reconnect | ✅ |
| Fail-safe watchdog |  WIP |

---

## Architecture

```
┌─────────────────┐         TCP/SCPI          ┌─────────────────┐
│                 │ ────────────────────────► │                 │
│   GUI (Python)  │        Port 5000          │   Red Pitaya    │
│                 │ ◄──────────────────────── │     (FPGA)      │
└─────────────────┘         STATUS?           └─────────────────┘
                                                      │
                                                      ▼
                                               ┌─────────────┐
                                               │  RF Output  │
                                               │  (AM Band)  │
                                               └─────────────┘
```

### Software (GUI)

- **Framework**: DearPyGui with Observer Pattern (loosely coupled components)
- **Stateless UI**: Display only updates after device confirmation
- **Network Manager**: Polls device every 500ms, auto-reconnects on failure (5 retries before termination)
- **SCPI Protocol**: Standard instrument control over TCP

### Hardware (FPGA)

- **NCO**: 12 Numerically Controlled Oscillators generate carrier frequencies (505-1605 kHz)
- **AM Modulator**: Combines audio with each carrier
- **Dynamic Scaling**: Power automatically adjusts based on enabled channel count
- **Audio Buffer**: BRAM stores pre-recorded emergency messages

---

## Requirements

### Software
- Python 3.8+
- DearPyGui

### Hardware
- Red Pitaya STEMlab 125-14
- AM Radio receiver(s) for testing

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-repo/ugl_am_radio.git
cd ugl_am_radio
```

### 2. Install Python dependencies
```bash
pip install dearpygui
```

### 3. Setup Red Pitaya

SSH into the Red Pitaya:
```bash
ssh root@<RED_PITAYA_IP>
# Default password: root
```

Copy required files:
```bash
# From your computer
scp am_scpi_server.py root@<RED_PITAYA_IP>:/root/
scp axi_audio_loader.py root@<RED_PITAYA_IP>:/root/
scp *.wav root@<RED_PITAYA_IP>:/root/
```

---

## Usage

### Step 1: Start the SCPI server on Red Pitaya
```bash
ssh root@<RED_PITAYA_IP>
sudo python3 /root/am_scpi_server.py
```

You should see:
```
==================================================
AM RADIO SCPI SERVER (12-Channel)
==================================================
Listening on 0.0.0.0:5000
```

### Step 2: Load audio (in a separate SSH terminal)
```bash
sudo python3 /root/axi_audio_loader.py /root/alarm_fast.wav
```

### Step 3: Run the GUI
```bash
python3 main.py
```

### Step 4: Connect and broadcast
1. Enter Red Pitaya IP address
2. Click **Connect**
3. Check **BRAM** checkbox
4. Select audio message from dropdown
5. Enable desired channels (1-12)
6. Adjust frequencies if needed (sliders)
7. Click **START BROADCAST**
8. Tune AM radio to any enabled frequency!

---

## File Structure

```
ugl_am_radio/
├── main.py              # Entry point
├── controller.py        # UI logic & layout
├── model.py             # Device state & SCPI communication
├── event_bus.py         # Observer pattern event system
├── config.py            # Configuration (frequencies, colors, etc.)
├── am_scpi_server.py    # Server for Red Pitaya
└── README.md
```

---

## Channel Frequencies (Default)

| Channel | Frequency |
|---------|-----------|
| CH1 | 505 kHz |
| CH2 | 605 kHz |
| CH3 | 705 kHz |
| CH4 | 805 kHz |
| CH5 | 905 kHz |
| CH6 | 1005 kHz |
| CH7 | 1105 kHz |
| CH8 | 1205 kHz |
| CH9 | 1305 kHz |
| CH10 | 1405 kHz |
| CH11 | 1505 kHz |
| CH12 | 1605 kHz |

Frequencies can be adjusted at runtime via the GUI (500-1700 kHz range).

---

## Performance Notes

⚠️ **Power vs Channel Count**: Red Pitaya has fixed RF output power. Signal strength decreases as more channels are enabled:

| Channels | Signal Strength | Recommendation |
|----------|-----------------|----------------|
| 1-2 | Excellent | ✅ Best quality |
| 3-4 | Good | ✅ Recommended max |
| 5-8 | Fair | ⚠️ May need amplifier |
| 9-12 | Weak | ⚠️ Short range only |

**Recommendation**: Use 4-5 channels maximum for reliable reception.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| GUI won't connect | Check IP address, ensure SCPI server is running |
| No audio, only carrier | Load audio: `python3 axi_audio_loader.py alarm_fast.wav` |
| Weak signal | Reduce enabled channels (max 4-5 recommended) |
| Connection timeout | Check network, Red Pitaya power, firewall settings |
| WinError 10061 | SCPI server not running on Red Pitaya |

---

## SCPI Commands Reference

| Command | Description |
|---------|-------------|
| `*IDN?` | Device identification |
| `STATUS?` | Get full device state |
| `OUTPUT:STATE ON/OFF` | Master broadcast enable |
| `CH1:FREQ 505000` | Set CH1 frequency (Hz) |
| `CH1:OUTPUT ON/OFF` | Enable/disable CH1 |
| `SOURCE:MSG 1` | Select audio message |

---

## Tested On

- ✅ SDR (Software Defined Radio)
- ✅ Analog AM Radio receivers
- ✅ Red Pitaya STEMlab 125-14

---

## Authors

- **William Park** - GUI & Integration
- **Bowen** - FPGA & Verilog

---

## License

University of Glasgow - UGL Project

---

*Last updated: 30th January 2026*