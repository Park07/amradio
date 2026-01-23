#!/usr/bin/env python3
"""
AM Radio SCPI Server - 12 Channel Version
==========================================
Runs on Red Pitaya's ARM CPU (Linux).
Receives SCPI commands from GUI over TCP, writes to FPGA registers.

Deploy to Red Pitaya:
    scp am_scpi_server.py root@192.168.1.100:/opt/am_radio/
    ssh root@192.168.1.100
    python3 /opt/am_radio/am_scpi_server.py

Supports 12 channels for stress testing.
"""

import socket
import mmap
import os
import struct
import re

# =============================================================================
# FPGA Register Map (must match am_radio_ctrl.v)
# =============================================================================

FPGA_BASE = 0x40700000  # sys[7] slot

# Register offsets
REG_CTRL = 0x00

# Channel frequency registers (0x04, 0x08, 0x0C, ... 0x30)
REG_CH_FREQ = {
    1: 0x04,
    2: 0x08,
    3: 0x0C,
    4: 0x10,
    5: 0x14,
    6: 0x18,
    7: 0x1C,
    8: 0x20,
    9: 0x24,
    10: 0x28,
    11: 0x2C,
    12: 0x30,
}

REG_STATUS = 0x34

# Control register bits
CTRL_MASTER_EN = 0      # bit 0
CTRL_SOURCE_SEL = 1     # bit 1
CTRL_MSG_SHIFT = 4      # bits 7:4
CTRL_CH_EN_SHIFT = 8    # bits 19:8 (12 channel enable bits)

# Clock frequency for phase increment calculation
FPGA_CLK_HZ = 125_000_000


# =============================================================================
# FPGA Memory Access
# =============================================================================

class FPGARegs:
    """Direct FPGA register access via /dev/mem."""

    def __init__(self, base_addr=FPGA_BASE, size=0x1000):
        self.base_addr = base_addr
        self.size = size
        self.mem = None
        self.fd = None

    def open(self):
        """Open /dev/mem and map FPGA registers."""
        try:
            self.fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
            self.mem = mmap.mmap(
                self.fd,
                self.size,
                mmap.MAP_SHARED,
                mmap.PROT_READ | mmap.PROT_WRITE,
                offset=self.base_addr
            )
            print(f"[FPGA] Mapped 0x{self.base_addr:08X}")
            return True
        except Exception as e:
            print(f"[FPGA] Failed to open /dev/mem: {e}")
            return False

    def close(self):
        """Close memory mapping."""
        if self.mem:
            self.mem.close()
        if self.fd:
            os.close(self.fd)

    def write32(self, offset, value):
        """Write 32-bit value to register."""
        if self.mem:
            self.mem[offset:offset+4] = struct.pack("<I", value & 0xFFFFFFFF)
            print(f"[FPGA] Write 0x{offset:02X} = 0x{value:08X}")

    def read32(self, offset):
        """Read 32-bit value from register."""
        if self.mem:
            data = struct.unpack("<I", self.mem[offset:offset+4])[0]
            print(f"[FPGA] Read 0x{offset:02X} = 0x{data:08X}")
            return data
        return 0


# =============================================================================
# SCPI Command Parser
# =============================================================================

class SCPIHandler:
    """Parses SCPI commands and writes to FPGA."""

    def __init__(self, fpga: FPGARegs):
        self.fpga = fpga
        self.ctrl_reg = 0x00000000

    def freq_to_phase_inc(self, freq_hz: int) -> int:
        """Convert frequency in Hz to NCO phase increment."""
        # phase_inc = (freq_hz * 2^32) / FPGA_CLK_HZ
        return int((freq_hz * (1 << 32)) / FPGA_CLK_HZ) & 0xFFFFFFFF

    def handle_command(self, cmd: str) -> str:
        """Parse and execute SCPI command."""
        cmd = cmd.strip().upper()
        print(f"[RX] {cmd}")

        # *IDN? - Identity query
        if cmd == "*IDN?":
            return "UGL AM Radio Controller,12CH,v2.0"

        # OUTPUT:STATE ON/OFF - Master enable
        if cmd.startswith("OUTPUT:STATE"):
            state = "ON" in cmd
            if state:
                self.ctrl_reg |= (1 << CTRL_MASTER_EN)
            else:
                self.ctrl_reg &= ~(1 << CTRL_MASTER_EN)
            self.fpga.write32(REG_CTRL, self.ctrl_reg)
            return "OK"

        # SOURCE:INPUT ADC/BRAM
        if cmd.startswith("SOURCE:INPUT"):
            is_adc = "ADC" in cmd
            if is_adc:
                self.ctrl_reg |= (1 << CTRL_SOURCE_SEL)
            else:
                self.ctrl_reg &= ~(1 << CTRL_SOURCE_SEL)
            self.fpga.write32(REG_CTRL, self.ctrl_reg)
            return "OK"

        # SOURCE:MSG 1-4
        match = re.match(r"SOURCE:MSG\s+(\d+)", cmd)
        if match:
            msg_id = int(match.group(1)) & 0x0F
            self.ctrl_reg &= ~(0x0F << CTRL_MSG_SHIFT)
            self.ctrl_reg |= (msg_id << CTRL_MSG_SHIFT)
            self.fpga.write32(REG_CTRL, self.ctrl_reg)
            return "OK"

        # CH<n>:FREQ <value> - Set channel frequency
        match = re.match(r"CH(\d+):FREQ\s+(\d+)", cmd)
        if match:
            ch = int(match.group(1))
            freq_hz = int(match.group(2))
            
            if ch < 1 or ch > 12:
                return "ERR:INVALID_CHANNEL"
            
            phase_inc = self.freq_to_phase_inc(freq_hz)
            self.fpga.write32(REG_CH_FREQ[ch], phase_inc)
            return "OK"

        # CH<n>:OUTPUT ON/OFF - Enable/disable channel
        match = re.match(r"CH(\d+):OUTPUT\s+(ON|OFF)", cmd)
        if match:
            ch = int(match.group(1))
            state = match.group(2) == "ON"
            
            if ch < 1 or ch > 12:
                return "ERR:INVALID_CHANNEL"
            
            bit_pos = CTRL_CH_EN_SHIFT + (ch - 1)
            if state:
                self.ctrl_reg |= (1 << bit_pos)
            else:
                self.ctrl_reg &= ~(1 << bit_pos)
            self.fpga.write32(REG_CTRL, self.ctrl_reg)
            return "OK"

        # STATUS? - Read status register
        if cmd == "STATUS?":
            status = self.fpga.read32(REG_STATUS)
            return f"0x{status:08X}"

        # CTRL? - Read control register
        if cmd == "CTRL?":
            return f"0x{self.ctrl_reg:08X}"

        return "ERR:UNKNOWN_CMD"


# =============================================================================
# TCP Server
# =============================================================================

def run_server(host="0.0.0.0", port=5000):
    """Run SCPI server."""
    
    # Initialize FPGA
    fpga = FPGARegs()
    if not fpga.open():
        print("[ERR] Could not open FPGA. Running in simulation mode.")
        fpga = None

    handler = SCPIHandler(fpga) if fpga else None

    # Create socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)

    print(f"[SERVER] Listening on {host}:{port}")
    print("[SERVER] 12-channel stress test version")

    try:
        while True:
            print("[SERVER] Waiting for connection...")
            conn, addr = server.accept()
            print(f"[SERVER] Connected: {addr}")

            try:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break

                    # Handle multiple commands separated by newlines
                    commands = data.decode().strip().split("\n")
                    for cmd in commands:
                        if cmd.strip():
                            if handler:
                                response = handler.handle_command(cmd)
                            else:
                                print(f"[SIM] {cmd}")
                                response = "OK"
                            conn.sendall((response + "\n").encode())

            except Exception as e:
                print(f"[ERR] {e}")
            finally:
                conn.close()
                print("[SERVER] Client disconnected")

    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        server.close()
        if fpga:
            fpga.close()


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    run_server()
