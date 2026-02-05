# Watchdog Timer Formal Verification
# ====================================

## Quick Start

    cd ~/amradio/ugl_am_radio/fpga/formal/
    sby -f watchdog.sby

## What Each Task Does

    sby -f watchdog.sby bmc      # Find bugs within 60 clock cycles
    sby -f watchdog.sby prove    # Mathematically prove ALL properties
    sby -f watchdog.sby cover    # Generate example waveforms

## Expected Output

    SBY [watchdog_bmc]   PASS    ← No bugs found
    SBY [watchdog_prove] PASS    ← All properties PROVEN correct
    SBY [watchdog_cover] PASS    ← All scenarios reachable

## If Something FAILS

    SBY [watchdog_prove] FAIL

    Look in watchdog_prove/ folder for:
    - engine_0/trace.vcd    ← Open in GTKWave to see the bug

    Install GTKWave:
    brew install --cask gtkwave

## The 9 Properties Being Verified

    1. Reset clears everything
    2. Heartbeat prevents trigger
    3. Trigger ONLY after timeout (KEY SAFETY PROPERTY)
    4. Trigger ALWAYS happens at timeout
    5. Warning comes before trigger
    6. Disable kills everything
    7. Counter never exceeds timeout
    8. Force reset clears trigger
    9. Warning timing is correct

## The 4 Cover Properties

    1. Can reach triggered state
    2. Warning before triggered
    3. Heartbeat saves us at last moment
    4. Recovery from triggered via force_reset

## Why Small Parameters?

    CLK_FREQ = 10 instead of 125,000,000
    TIMEOUT_SEC = 2 instead of 5

    The logic is identical - same if/else structure.
    SAT solver would take forever with 125M * 5 = 625M cycles.
    Proving at small scale = proven at all scales (same RTL).

## File Structure

    fpga/formal/
    ├── watchdog_formal.v   ← Watchdog + formal properties
    ├── watchdog.sby         ← SymbiYosys config
    └── README.md            ← This file
