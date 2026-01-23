# UGL AM Radio Control System - 12 Channel Stress Test

## Purpose

This version adds 12 channels to test hardware limits:
- At what point does Red Pitaya run out of capacity?
- When do carrier peaks start dropping (10mW composite power limit)?
- Where do we run out of FPGA speed?

## Files

### Python (GUI - Your Laptop)

| File | Description |
|------|-------------|
| `main.py` | Entry point |
| `config.py` | 12 channels configured |
| `model.py` | State + SCPI client |
| `controller.py` | UI + events (scrollable channel list) |
| `mock_server.py` | Test without hardware |

### Verilog (FPGA - Bowen)

| File | Description |
|------|-------------|
| `fpga/am_radio_ctrl.v` | Register interface for 12 channels |
| `fpga/am_radio_dsp.v` | 12 NCOs + 12 AM modulators + summing |
| `fpga/am_scpi_server.py` | Runs on Red Pitaya ARM, parses CH1-CH12 commands |

## Quick Start

### Test without hardware:

```bash
# Terminal 1
python mock_server.py

# Terminal 2
python main.py
# Connect to 127.0.0.1:5000
```

### Test with hardware:

```bash
# SSH into Red Pitaya
ssh root@192.168.1.100
python3 /opt/am_radio/am_scpi_server.py

# Your laptop
python main.py
# Connect to 192.168.1.100:5000
```

## SCPI Commands

```
CH1:FREQ 531000    # Set channel 1 to 531 kHz
CH1:OUTPUT ON      # Enable channel 1
...
CH12:FREQ 1600000  # Set channel 12 to 1600 kHz
CH12:OUTPUT ON     # Enable channel 12
OUTPUT:STATE ON    # Start broadcasting
```

## Register Map (am_radio_ctrl.v)

| Address | Register |
|---------|----------|
| 0x00 | CTRL (master enable, source sel, channel enables [19:8]) |
| 0x04 | CH1 frequency (phase increment) |
| 0x08 | CH2 frequency |
| 0x0C | CH3 frequency |
| 0x10 | CH4 frequency |
| 0x14 | CH5 frequency |
| 0x18 | CH6 frequency |
| 0x1C | CH7 frequency |
| 0x20 | CH8 frequency |
| 0x24 | CH9 frequency |
| 0x28 | CH10 frequency |
| 0x2C | CH11 frequency |
| 0x30 | CH12 frequency |
| 0x34 | STATUS (read-only) |

## Stress Test Procedure

1. Enable channels one at a time (CH1, then CH2, etc.)
2. Start broadcast after each addition
3. Monitor on SDR/spectrum analyzer:
   - Individual carrier peak amplitude
   - Total composite power
   - Any distortion or artifacts
4. Record at what point:
   - Peaks start dropping
   - Audio quality degrades
   - System becomes unstable

## Expected Results

- 10mW total composite power
- As channels increase → individual peaks drop
- At some point, system runs out of:
  - Power budget
  - FPGA processing speed
  - DAC resolution

Document the limits!
