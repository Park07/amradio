# UGL Tunnel AM Radio Control System

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              GUI (Python)                               │
│  ┌──────────┐    ┌───────────┐    ┌──────────────────────────────────┐ │
│  │   View   │◄──►│ Controller│◄──►│     Event Bus (Central Hub)      │ │
│  │(DearPyGui)│   │           │    │  - CONNECT_SUCCESS               │ │
│  └──────────┘    └───────────┘    │  - DEVICE_STATE_UPDATED          │ │
│                        ▲          │  - BROADCAST_STARTED             │ │
│                        │          │  - WATCHDOG_TRIGGERED            │ │
│                        ▼          └──────────────────────────────────┘ │
│                  ┌───────────┐                   ▲                      │
│                  │   Model   │◄──────────────────┘                      │
│                  │           │                                          │
│                  │ ┌───────────────────┐                               │
│                  │ │  NetworkManager   │ ← Background Threads          │
│                  │ │  - Poll loop      │   (500ms polling)             │
│                  │ │  - Heartbeat      │                               │
│                  │ │  - Auto-reconnect │                               │
│                  │ └───────────────────┘                               │
│                  └───────────┘                                          │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ TCP/SCPI
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Red Pitaya (ARM + FPGA)                          │
│  ┌──────────────┐    ┌──────────────────────────────────────────────┐  │
│  │ SCPI Server  │◄──►│                   FPGA                       │  │
│  │  (Python)    │    │  ┌────────────┐  ┌─────────────────────────┐ │  │
│  │              │    │  │  Watchdog  │  │   AM Radio Chain        │ │  │
│  │ /dev/mem ────┼────┼─►│   Timer    │  │  NCO → Modulator → DAC  │ │  │
│  │              │    │  │            │  │                         │ │  │
│  │              │    │  │ 5s timeout │  │  broadcast_enable_safe  │ │  │
│  │              │    │  │ = RF OFF   │──┼──────────┘              │ │  │
│  └──────────────┘    │  └────────────┘  └─────────────────────────┘ │  │
│                      └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```




## Key Design Decisions

### 1. Stateless UI (Most Important)

**Problem:** GUI says "BROADCASTING" but FPGA is actually off.

**Solution:** UI ONLY updates from device polling, never assumes commands worked.

```python
# WRONG (old way)
def start_broadcast(self):
    self.send_command("OUTPUT:STATE ON")
    self.broadcasting = True  # ❌ Assumes it worked!
    self.update_ui()

# RIGHT (stateless)
def start_broadcast(self):
    self.send_command("OUTPUT:STATE ON")
    self.broadcast_state = ARMING  # Shows "ARMING..." in UI
    # UI updates ONLY when polling confirms device state changed
```

### 2. Event Bus

**Problem:** Controller is a tangled mess calling everything directly.

**Solution:** All components communicate through events.

```python
# Components publish events
event_bus.publish(Event(EventType.DEVICE_STATE_UPDATED, {"broadcasting": True}))

# Other components subscribe
event_bus.subscribe(EventType.DEVICE_STATE_UPDATED, self._on_state_updated)
```

### 3. Hardware Watchdog

**Problem:** GUI crashes → RF keeps transmitting forever.

**Solution:** FPGA has watchdog timer that kills RF if no heartbeat for 5 seconds.

```verilog
// In FPGA
if (watchdog_count > 5_SEC)
    broadcast_enable <= 0;  // Auto-kill RF
```

---

## Files

```
ugl_am_radio_final/
├── main.py           # Entry point
├── config.py         # All configuration in one place
├── event_bus.py      # Central event dispatcher
├── model.py          # Business logic + networking
├── controller.py     # UI logic + event handlers
└── README.md         # This file
```

---

## State Machines

### Connection State
```
DISCONNECTED → CONNECTING → CONNECTED
                    ↓            ↓
                  ERROR ← RECONNECTING
```

### Broadcast State
```
IDLE → ARMING → BROADCASTING
  ↑               ↓
  └── STOPPING ←──┘
```

### Watchdog State
```
OK → WARNING → TRIGGERED
↑               ↓
└─── (reset) ───┘
```

---

## Running

```bash
# Install dependencies
pip install dearpygui

# Run
python main.py
```

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## Authors

- **William Park** - GUI Development
- **Bowen** - FPGA Integration

## Acknowledgments

- UGL Limited - Project sponsor
- University of New South Wales - Academic support
- Red Pitaya - Hardware platform
