# UGL Tunnel AM Radio Control System

GUI control panel for the Red Pitaya-based AM broadcast system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           MVC ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    Events    ┌──────────────┐    SCPI    ┌──────┐ │
│  │             │ ───────────► │              │ ─────────► │      │ │
│  │    VIEW     │              │  CONTROLLER  │            │ MODEL│ │
│  │ (DearPyGui) │ ◄─────────── │              │ ◄───────── │      │ │
│  │             │   Updates    │              │   State    │      │ │
│  └─────────────┘              └──────────────┘            └──────┘ │
│                                                               │     │
│                                                               ▼     │
│                                                     ┌──────────────┐│
│                                                     │  Red Pitaya  ││
│                                                     │  (SCPI/TCP)  ││
│                                                     └──────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## Signal Flow (Rob's Whiteboard)

### Mode A: Live Microphone (ADC)
```
Mic → PA Console → [Analog Cable] → RP ADC IN → FPGA → DAC → RF OUT
                                        ▲
                                        │ SCPI: "SOURCE:INPUT ADC"
                                   ┌────┴────┐
                                   │   GUI   │
                                   └─────────┘
```

### Mode B: Stored Message (BRAM)
```
                    BRAM ──────────────► FPGA → DAC → RF OUT
                      ▲                    ▲
                      │                    │
               "SOURCE:MSG 2"        "SOURCE:INPUT BRAM"
                      │                    │
                   ┌──┴────────────────────┴──┐
                   │           GUI            │
                   └──────────────────────────┘
```

## Files

```
ugl_am_radio/
├── main.py          # Entry point
├── config.py        # All configuration (no hardcoding elsewhere)
├── model.py         # State, SCPI client, logging
├── controller.py    # UI construction, event handlers
├── requirements.txt # Dependencies
└── README.md        # This file
```

## SCPI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `SOURCE:INPUT <src>` | Set audio source | `SOURCE:INPUT ADC` |
| `SOURCE:MSG <n>` | Select message (1-4) | `SOURCE:MSG 2` |
| `CH<n>:FREQ <hz>` | Set frequency | `CH1:FREQ 531000` |
| `CH<n>:OUTPUT <state>` | Enable channel | `CH1:OUTPUT ON` |
| `OUTPUT:STATE <state>` | Master broadcast | `OUTPUT:STATE ON` |
| `*IDN?` | Query identity | `*IDN?` |

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run
python main.py
```

## GUI Layout

```
┌─────────────────────────────────────────┐
│ CONNECTION                              │
│ IP: [192.168.1.100]  Port: [5000]       │
│ [Connect]       Status: Disconnected    │
├─────────────────────────────────────────┤
│ AUDIO SOURCE                            │
│ ○ Live Mic (ADC)  ● Stored Message      │
│ Message: [Emergency Evacuation ▼]       │
├─────────────────────────────────────────┤
│ CHANNELS                                │
│ ☐ CH1  [531] kHz  ●                     │
│ ☐ CH2  [702] kHz  ●                     │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │          ● BROADCAST                │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ LOG                                     │
│ [2026-01-21 10:30:15] System ready.     │
│ [2026-01-21 10:30:20] TX: SOURCE:INPUT  │
└─────────────────────────────────────────┘
```

## Configuration

Edit `config.py` to change:
- Default IP/Port
- Channel frequencies
- Stored messages
- UI colors/theme
- Log settings

## For FPGA Team (Bowen)

The GUI sends these commands. FPGA needs to implement a parser for:

1. **Source selection MUX** - Switch between ADC input and BRAM
2. **Message address** - Which BRAM slot to read from
3. **NCO frequency** - Phase increment for each channel
4. **Output enable** - Gate each channel's output
5. **Master output** - Enable/disable RF output

---

**Author:** William (UGL EPI Team)  
**Date:** January 2026
