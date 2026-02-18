# Watchdog Timer Formal Verification

Mathematically proven safety properties for the FPGA watchdog timer using bounded model checking and k-induction.

## Quick Start

```bash
cd ~/amradio/am_radio/fpga/formal/
sby -f watchdog.sby
```

## What Each Task Does

```bash
sby -f watchdog.sby bmc      # Find bugs within 60 clock cycles
sby -f watchdog.sby prove    # Mathematically prove ALL properties
sby -f watchdog.sby cover    # Generate example waveforms (VCD)
```

## Expected Output

```
SBY [watchdog_bmc]   PASS    ← No bugs found
SBY [watchdog_prove] PASS    ← All 14 properties PROVEN correct
SBY [watchdog_cover] PASS    ← All scenarios reachable
```

## If Something FAILS

```
SBY [watchdog_prove] FAIL
Look in watchdog_prove/ folder for:
- engine_0/trace.vcd    ← Open in Surfer or GTKWave to see the bug
```

View waveforms: https://app.surfer-project.org/ (drag VCD file into browser)

## The 14 Properties Being Verified

### Basic (Foundational)

| # | Property | What It Proves |
|---|----------|----------------|
| 1 | Reset clears everything | `!rstn` → counter=0, triggered=0, warning=0 |
| 2 | Heartbeat prevents trigger | `hb` → counter, triggered, warning all cleared |
| 6 | Disable kills everything | `!enable` → counter=0, triggered=0, warning=0 |
| 7 | Counter bounded | Counter never exceeds TIMEOUT_CYCLES |
| 8 | Force reset clears everything | `force_reset` → counter, triggered, warning cleared |
| 9 | Warning low before threshold | Counter < WARNING_CYCLES → warning=0 |

### Intermediate (Safety & Liveness)

| # | Property | What It Proves |
|---|----------|----------------|
| 3 | **No early trigger** | **KEY SAFETY: triggered ONLY when counter ≥ timeout** |
| 4 | Trigger guaranteed at timeout | Liveness: timeout always fires trigger |
| 5 | Warning before trigger | If triggered then warning must be high |
| 5b | Contrapositive | If !warning then !triggered (tightens solver) |
| 10 | Warning high in zone | counter > WARNING_CYCLES → warning=1 |
| 11 | Counter increments correctly | Exactly +1 per clock cycle during counting |

### Advanced (Output Verification)

| # | Property | What It Proves |
|---|----------|----------------|
| 12 | time_remaining at zero | counter=0 → time_remaining = TIMEOUT_SEC |
| 13 | time_remaining at trigger | triggered → time_remaining = 0 |
| 14 | time_remaining monotonic | Decreases every cycle during counting |

### Input Constraint

- Heartbeat modelled as single-cycle pulse (realistic hardware behaviour)

## The 5 Cover Scenarios

| # | Scenario | Steps | Description |
|---|----------|-------|-------------|
| 1 | Trigger fires | 23 | Counter reaches timeout, triggered goes high |
| 2 | Warning without trigger | 21 | In warning zone, not yet timed out |
| 3 | Exact timeout boundary | 22 | Counter = TIMEOUT_CYCLES exactly |
| 4 | Last-second heartbeat + lifecycle | 23 | Heartbeat saves at last moment, then warning→trigger |
| 5 | Recovery from triggered | 24 | Triggered state cleared by force_reset |

VCD waveforms generated in `watchdog_cover/engine_0/trace*.vcd`

## Why Small Parameters?

```
CLK_FREQ    = 10   instead of 125,000,000
TIMEOUT_SEC = 2    instead of 5
```

The logic is identical — same if/else structure, same RTL.
SAT solver would take forever with 125M × 5 = 625M cycles.
Properties are expressed in terms of symbolic constants, not concrete values.
Proving at small scale = proven at all scales.

## Tool Chain

| Tool | Role |
|------|------|
| Yosys | RTL synthesis and formal preparation |
| SymbiYosys | Formal verification front-end |
| Z3 | SMT solver (back-end) |

## Verification Method

- **BMC (Bounded Model Checking)**: Checks all assertions for k=60 time steps
- **k-Induction**: Complete proof — if properties hold for any k consecutive states, they hold for k+1
- **Cover**: Proves scenarios are reachable (model is not vacuously true)

## File Structure

```
fpga/formal/
├── watchdog_formal.v   ← Watchdog module + 14 formal properties
├── watchdog.sby        ← SymbiYosys configuration
└── README.md           ← This file
```