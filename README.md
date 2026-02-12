# AM Radio Break-in System

A 12-channel AM radio broadcast system using Red Pitaya FPGA for emergency alert transmission in unmanned tunnels.

![Channels: 12](https://img.shields.io/badge/Channels-12-blue)
![Platform: Red Pitaya](https://img.shields.io/badge/Platform-Red%20Pitaya-red)
![Backend: Rust](https://img.shields.io/badge/Backend-Rust-orange)
![Frontend: JavaScript](https://img.shields.io/badge/Frontend-JavaScript-yellow)
![Formal Verification: 14/14 PASS](https://img.shields.io/badge/Formal_Verification-14%2F14_PASS-brightgreen)

---

## Features

| Feature | Status |
|---------|--------|
| 12 simultaneous carrier frequencies | ✅ |
| Runtime frequency configuration (no hardware changes) | ✅ |
| AM modulation with pre-recorded audio | ✅ |
| Dynamic power scaling | ✅ |
| MVC architecture (Rust + JavaScript) | ✅ |
| Event-driven pub/sub via event bus | ✅ |
| Stateless UI — device is source of truth | ✅ |
| Network polling & auto-reconnect | ✅ |
| Fail-safe hardware watchdog (5s timeout) | ✅ |
| Formal verification (14 properties, 6 covers, all proven) | ✅ |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     SOFTWARE (GUI)                        │
│                                                          │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   View     │  │  Controller  │  │      Model       │ │
│  │  (JS)      │  │    (JS)      │  │     (Rust)       │ │
│  │ index.html │  │ controller.js│  │    model.rs      │ │
│  │ view.js    │  │              │  │  NetworkManager   │ │
│  └─────┬──────┘  └──────┬───────┘  │  StateMachine    │ │
│        │                │           └────────┬─────────┘ │
│        │         ┌──────▼───────┐            │           │
│        └─────────┤  Event Bus   ├────────────┘           │
│                  │ event_bus.rs  │                        │
│                  │ event_bus.js  │                        │
│                  └──────┬───────┘                         │
│                         │ Tauri Bridge                    │
└─────────────────────────┼────────────────────────────────┘
                          │ TCP/SCPI (Port 5000)
┌─────────────────────────▼────────────────────────────────┐
│                     HARDWARE (FPGA)                       │
│                                                          │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  SCPI Server    │  │ AM Radio     │  │  Watchdog  │  │
│  │ am_scpi_server  │─▶│ Controller   │  │   Timer    │  │
│  │    .py          │  │ am_radio_    │  │   wd.v     │  │
│  └─────────────────┘  │ ctrl.v       │  └──────┬─────┘  │
│                       └──────┬───────┘         │         │
│                              │            ┌────▼─────┐   │
│                        ┌─────▼──────┐     │ RF Kill  │   │
│                        │ 12x NCO +  │     │ Switch   │   │
│                        │ AM Mod     │     └──────────┘   │
│                        └─────┬──────┘                    │
│                              ▼                           │
│                       ┌─────────────┐                    │
│                       │  RF Output  │                    │
│                       │ 505-1605kHz │                    │
│                       └─────────────┘                    │
└──────────────────────────────────────────────────────────┘
```

### Software Layer

- **Framework**: Rust (Tauri) backend + JavaScript frontend
- **Architecture**: MVC with event-driven pub/sub
- **Model** (`model.rs`): NetworkManager handles TCP/SCPI, device state, 500ms polling, auto-reconnect with exponential backoff
- **View** (`view.js`, `index.html`): Stateless — only renders confirmed device state. Never assumes hardware state.
- **Controller** (`controller.js`): Handles user input, publishes events to bus
- **Event Bus** (`event_bus.rs`, `event_bus.js`): Components communicate through a central bus instead of calling each other directly. Rust emits events to JS frontend via Tauri bridge.
- **State Machine** (`state_machine.rs`): IDLE → ARMING → ARMED → STARTING → BROADCASTING → STOPPING. Intermediate states prevent invalid transitions.
- **Source of Truth**: The device, not the software. UI only updates after hardware confirms.

### Hardware Layer

- **NCO**: 12 Numerically Controlled Oscillators generate carrier frequencies (505–1605 kHz)
- **AM Modulator**: Combines audio source with each carrier
- **Dynamic Scaling**: Output power adjusts based on enabled channel count
- **Audio Buffer**: BRAM stores pre-recorded emergency messages. AXI audio loader available for runtime loading.
- **Watchdog Timer** (`wd.v`): Hardware fail-safe — if GUI heartbeat stops for 5 seconds, RF output is killed and latched. Only manual operator reset restores output.
- **SCPI Server** (`am_scpi_server.py`): Runs on Red Pitaya, parses text commands, converts frequencies to phase increments, writes to FPGA registers via `/dev/mem`.

### Signal Generation Flow

```
GUI click → invoke("set_frequency") → model.rs sends "FREQ:CH1 700000" over TCP
→ am_scpi_server.py converts to phase_inc = (700000 × 2³²) / 125MHz
→ writes to FPGA register via /dev/mem → NCO generates carrier → AM modulates → RF output
```

---

## Formal Verification

The watchdog timer is mathematically proven correct using bounded model checking and k-induction (SymbiYosys + Z3 SMT solver). Unlike simulation-based testing which checks individual scenarios, formal verification proves correctness across **every possible input, in every possible state, for all time**.

### 14 Safety Properties (All PASS)

| Category | # | Property | Guarantee |
|----------|---|----------|-----------|
| **Basic** | 1 | Reset clears all | `!rstn` → counter=0, triggered=0, warning=0 |
| | 2 | Heartbeat prevents trigger | Heartbeat resets counter, clears triggered and warning |
| | 6 | Disable kills everything | `!enable` → all outputs cleared |
| | 7 | Counter bounded | Counter never exceeds TIMEOUT_CYCLES |
| | 8 | Force reset works | `force_reset` clears all state |
| | 9 | Warning low before threshold | counter < WARNING_CYCLES → warning=0 |
| **Safety** | 3 | **No early trigger** | **triggered ONLY when counter ≥ TIMEOUT_CYCLES** |
| | 4 | Trigger guaranteed at timeout | Liveness: timeout always fires trigger |
| | 5 | Warning before trigger | triggered=1 → warning=1 |
| | 5b | Contrapositive | !warning → !triggered |
| | 10 | Warning high in zone | counter > WARNING_CYCLES → warning=1 |
| | 11 | Counter increments correctly | Exactly +1 per clock cycle during counting |
| **Output** | 12 | time_remaining at zero | counter=0 → time_remaining = TIMEOUT_SEC |
| | 13 | time_remaining at trigger | triggered → time_remaining = 0 |
| | 14 | time_remaining monotonic | Decreases every cycle during counting |

### 6 Cover Scenarios (All Reached)

| # | Scenario | Steps | Description |
|---|----------|-------|-------------|
| 1 | Trigger fires | 23 | Counter reaches timeout |
| 2 | Warning without trigger | 21 | In warning zone, not yet timed out |
| 3 | Exact timeout boundary | 22 | Counter = TIMEOUT_CYCLES exactly |
| 4 | Last-second heartbeat | 19 | Heartbeat at counter = T-1 |
| 5 | Recovery from triggered | 24 | Triggered state cleared by force_reset |
| 6 | Warning-to-trigger lifecycle | 23 | Warning then immediate trigger |

### Running Verification

```bash
cd fpga/formal/
sby -f wd.sby
```

Expected output:
```
SBY [wd_prove] DONE (PASS, rc=0)
    summary: successful proof by k-induction.
SBY [wd_cover] DONE (PASS, rc=0)
    summary: 6/6 cover statements reached.
```

### Scalability

Verification uses `CLK_FREQ=1`, `TIMEOUT_SEC=5` to keep state space tractable. Production uses `CLK_FREQ=125000000`. The RTL is parameterised — same if/else logic, same state transitions. Proof at reduced scale implies correctness at production scale.

See [`fpga/formal/README.md`](ugl_am_radio/fpga/formal/README.md) for full technical details.

---

## Requirements

### Software
- Rust + Cargo
- Node.js (for Tauri)
- npm

### Hardware
- Red Pitaya STEMlab 125-10
- AM Radio receiver(s) for testing

### Formal Verification (optional)
- SymbiYosys
- Yosys
- Z3 SMT solver

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/Park07/amradio.git
cd amradio/ugl_am_radio
```

### 2. Build the GUI
```bash
cd gui
npm install
npm run tauri build
```

### 3. Setup Red Pitaya

SSH into the Red Pitaya:
```bash
ssh root@<RED_PITAYA_IP>
# Default password: root
```

Copy required files:
```bash
scp am_scpi_server.py root@<RED_PITAYA_IP>:/root/
scp axi_audio_loader.py root@<RED_PITAYA_IP>:/root/
scp *.wav root@<RED_PITAYA_IP>:/root/
```

---

## Usage

### Step 1: Start the SCPI server on Red Pitaya
```bash
ssh root@<RED_PITAYA_IP>
sudo python3 am_scpi_server.py
```

### Step 2: Load audio (separate SSH terminal)
```bash
sudo python3 /axi_audio_loader.py alarm_fast.wav
```

### Step 3: Run the GUI
```bash
cd gui
npm run tauri dev
```

### Step 4: Connect and broadcast
1. Enter Red Pitaya IP address
2. Click **Connect**
3. Select audio source
4. Enable desired channels (1–12)
5. Adjust frequencies if needed
6. Click **START BROADCAST**
7. Tune AM radio to any enabled frequency

---

## File Structure

```
ugl_am_radio/
├── gui/
│   ├── src/
│   │   ├── index.html              # HTML + CSS
│   │   └── js/
│   │       ├── event_bus.js        # Frontend pub/sub + Tauri listener
│   │       ├── model.js            # Rust API calls (stateless)
│   │       ├── view.js             # DOM rendering
│   │       └── controller.js       # Event handlers
│   └── src-tauri/src/
│       ├── main.rs                 # Entry point
│       ├── model.rs                # NetworkManager + DeviceState
│       ├── commands.rs             # Tauri command bridge
│       ├── event_bus.rs            # Rust pub/sub + Tauri emit
│       ├── state_machine.rs        # Broadcast state transitions
│       └── config.rs               # Constants
├── fpga/
│   ├── formal/
│   │   ├── wd.v                    # Watchdog + 14 formal properties
│   │   ├── wd.sby                  # SymbiYosys config
│   │   └── README.md               # Formal verification docs
│   ├── am_radio_ctrl.v             # 12-channel AM radio controller
│   ├── watchdog_timer.v            # Watchdog timer module
│   └── red_pitaya_top.sv           # Top-level FPGA integration
├── am_scpi_server.py               # SCPI server (runs on Red Pitaya)
├── axi_audio_loader.py             # Runtime audio loader
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

Frequencies adjustable at runtime (500–1700 kHz range).

---

## Watchdog Safety Design

```
Standard watchdog:  device hangs → timer overflows → restarts device → back to normal
This watchdog:      GUI dies → counter hits timeout → kills RF output → stays dead until operator resets
```

**Why different:** Automatically restarting a radio transmitter in an unmanned tunnel is dangerous. The system requires human confirmation before RF output resumes. Fail-safe, not fail-recover.

**Safety margin:** GUI polls every 500ms. Watchdog timeout is 5s. That's 10 consecutive missed heartbeats before trigger — resilient against transient network delays.


---

## Performance Notes

| Channels | Signal Strength | Recommendation |
|----------|-----------------|----------------|
| 1–2 | Excellent | ✅ Best quality |
| 3–4 | Good | ✅ Recommended max |
| 5–8 | Fair | ⚠️ May need amplifier |
| 9–12 | Weak | ⚠️ Short range only |

**Recommendation**: 4–5 channels maximum for reliable reception.

---

## SCPI Commands Reference

| Command | Description |
|---------|-------------|
| `*IDN?` | Device identification |
| `STATUS?` | Full device state |
| `OUTPUT:STATE ON/OFF` | Master broadcast enable |
| `CH1:FREQ 505000` | Set CH1 frequency (Hz) |
| `CH1:OUTPUT ON/OFF` | Enable/disable CH1 |
| `SOURCE:MSG 1` | Select audio message |
| `WATCHDOG:RESET` | Reset watchdog timer |
| `WATCHDOG:STATUS?` | Query watchdog state |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| GUI won't connect | Check IP, ensure SCPI server is running |
| No audio, only carrier | Load audio: `python3 axi_audio_loader.py alarm_fast.wav` |
| Weak signal | Reduce enabled channels (max 4–5) |
| Connection timeout | Check network, Red Pitaya power |
| Watchdog triggered unexpectedly | Check network stability, increase timeout if needed |

---

## Authors

- **William Park** — Software architecture (GUI, MVC, event bus), hardware watchdog timer, formal verification
- **Bowen** — FPGA development (NCO, AM modulation, RF output)

## Acknowledgments

- **UGL Limited** — Project sponsor
- **University of New South Wales** — EPI program
- **Robert Mahood** (UGL) — Engineering supervisor
- **Andrew Wong** (UNSW) — Academic supervisor

*Final Version: 13th February 2026*