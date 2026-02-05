#!/usr/bin/env python3
"""
AM Radio SCPI Server - 12 Channel Version
Compatible with UGL AM Radio Control GUI

Register Map (when Bowen updates Verilog):
  0x00: CTRL_REG - [0]=master_en, [3]=source_sel, [7:4]=msg_select
  0x04: CH1_FREQ
  0x08: CH2_FREQ
  0x0C: CH3_FREQ
  0x10: CH4_FREQ
  0x14: CH5_FREQ
  0x18: CH6_FREQ
  0x1C: CH7_FREQ
  0x20: CH8_FREQ
  0x24: CH9_FREQ
  0x28: CH10_FREQ
  0x2C: CH11_FREQ
  0x30: CH12_FREQ
  0x34: CH_ENABLE - [11:0] = channel enable bits
  0x38: STATUS_REG (read-only)

Author: William Park
Date: January 2026
"""
import socket
import mmap
import os
import struct
import subprocess
import threading
import time

# ============================================================================
# Audio File Configuration
# ============================================================================
# Audio files in /root/ (no subdirectory needed)
AUDIO_FILES = {
    1: "/root/alarm_fast.wav",
    2: "/root/0009_part1.wav",
    3: "/root/0009_part2_fast.wav",
}

# Path to the audio loader script
AUDIO_LOADER = "/root/axi_audio_loader.py"

# FPGA Register Map
FPGA_BASE = 0x40700000  # sys[7] slot
FPGA_SIZE = 0x1000

# Register offsets
REG_CTRL      = 0x00
REG_CH1_FREQ  = 0x04
REG_CH2_FREQ  = 0x08
REG_CH3_FREQ  = 0x0C
REG_CH4_FREQ  = 0x10
REG_CH5_FREQ  = 0x14
REG_CH6_FREQ  = 0x18
REG_CH7_FREQ  = 0x1C
REG_CH8_FREQ  = 0x20
REG_CH9_FREQ  = 0x24
REG_CH10_FREQ = 0x28
REG_CH11_FREQ = 0x2C
REG_CH12_FREQ = 0x30
REG_CH_ENABLE = 0x34
REG_STATUS    = 0x38

# Channel freq register lookup (channel 1-12)
CH_FREQ_REGS = {
    1: REG_CH1_FREQ,   2: REG_CH2_FREQ,
    3: REG_CH3_FREQ,   4: REG_CH4_FREQ,
    5: REG_CH5_FREQ,   6: REG_CH6_FREQ,
    7: REG_CH7_FREQ,   8: REG_CH8_FREQ,
    9: REG_CH9_FREQ,   10: REG_CH10_FREQ,
    11: REG_CH11_FREQ, 12: REG_CH12_FREQ,
}

# Control register bits
CTRL_MASTER_EN = 0
CTRL_SOURCE    = 3
CTRL_MSG_SHIFT = 4
CTRL_WATCHDOG_EN = 4

FPGA_CLK_HZ = 125000000


class FPGARegs:
    def __init__(self, base_addr=FPGA_BASE, size=FPGA_SIZE):
        self.base = base_addr
        self.size = size
        self.mem = None
        self.fd = None

    def open(self):
        try:
            self.fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
            self.mem = mmap.mmap(
                self.fd,
                self.size,
                mmap.MAP_SHARED,
                mmap.PROT_READ | mmap.PROT_WRITE,
                offset=self.base
            )
            print("FPGA registers mapped at 0x%08X" % self.base)
            return True
        except Exception as e:
            print("Failed to open /dev/mem: %s" % str(e))
            print("Make sure you're running as root on Red Pitaya")
            return False

    def close(self):
        if self.mem:
            self.mem.close()
        if self.fd:
            os.close(self.fd)

    def read32(self, offset):
        self.mem.seek(offset)
        return struct.unpack('<I', self.mem.read(4))[0]

    def write32(self, offset, value):
        self.mem.seek(offset)
        self.mem.write(struct.pack('<I', value & 0xFFFFFFFF))


class AMRadioController:
    def __init__(self, fpga):
        self.fpga = fpga
        self.ctrl_shadow = 0
        self.ch_enable_shadow = 0  # 12-bit channel enable mask

        # Track channel frequencies for STATUS? query
        self.ch_freqs = {}
        for i in range(1, 13):
            self.ch_freqs[i] = 0

        # Audio loading state
        self.current_msg = 0
        self.audio_loading = False
        self.audio_loader_thread = None

    def freq_to_phase_inc(self, freq_hz):
        return int((freq_hz * (1 << 32)) / FPGA_CLK_HZ) & 0xFFFFFFFF

    def set_ctrl_bit(self, bit, value):
        if value:
            self.ctrl_shadow |= (1 << bit)
        else:
            self.ctrl_shadow &= ~(1 << bit)
        if self.fpga:
            self.fpga.write32(REG_CTRL, self.ctrl_shadow)

    def set_channel_enable(self, ch_num, enabled):
        """Enable/disable channel 1-12."""
        if 1 <= ch_num <= 12:
            bit = ch_num - 1
            if enabled:
                self.ch_enable_shadow |= (1 << bit)
            else:
                self.ch_enable_shadow &= ~(1 << bit)
            if self.fpga:
                self.fpga.write32(REG_CH_ENABLE, self.ch_enable_shadow)
            print("CH%d: %s (mask=0b%s)" % (ch_num, "ON" if enabled else "OFF", bin(self.ch_enable_shadow)[2:].zfill(12)))

    def set_channel_freq(self, ch_num, freq_hz):
        """Set channel frequency."""
        if ch_num in CH_FREQ_REGS:
            phase_inc = self.freq_to_phase_inc(freq_hz)
            self.ch_freqs[ch_num] = freq_hz
            if self.fpga:
                self.fpga.write32(CH_FREQ_REGS[ch_num], phase_inc)
            print("CH%d: %d Hz -> phase_inc=0x%08X" % (ch_num, freq_hz, phase_inc))

    def load_audio_file(self, msg_id):
        """Load audio file in background thread."""
        if msg_id not in AUDIO_FILES:
            print("ERROR: Unknown message ID %d" % msg_id)
            return False

        audio_file = AUDIO_FILES[msg_id]

        # Check if file exists
        if not os.path.exists(audio_file):
            print("ERROR: Audio file not found: %s" % audio_file)
            return False

        # Check if loader exists
        if not os.path.exists(AUDIO_LOADER):
            print("ERROR: Audio loader not found: %s" % AUDIO_LOADER)
            return False

        # Don't start if already loading
        if self.audio_loading:
            print("WARNING: Audio still loading, please wait...")
            return False

        def _load_thread():
            self.audio_loading = True
            print("=" * 40)
            print("LOADING AUDIO: %s" % audio_file)
            print("=" * 40)

            try:
                result = subprocess.run(
                    ["python3", AUDIO_LOADER, audio_file],
                    capture_output=True,
                    text=True,
                    timeout=30  # 30 second timeout
                )

                if result.returncode == 0:
                    print("AUDIO LOADED OK")
                    if result.stdout:
                        print(result.stdout)
                else:
                    print("AUDIO LOAD FAILED:")
                    if result.stderr:
                        print(result.stderr)

            except subprocess.TimeoutExpired:
                print("ERROR: Audio loading timed out")
            except Exception as e:
                print("ERROR: %s" % str(e))
            finally:
                self.audio_loading = False
                print("=" * 40)

        # Start loading in background
        self.audio_loader_thread = threading.Thread(target=_load_thread, daemon=True)
        self.audio_loader_thread.start()

        return True

    def get_status(self):
        """Return status string for STATUS? query."""
        parts = []
        parts.append("broadcasting=%d" % (1 if (self.ctrl_shadow & 1) else 0))
        parts.append("source=%s" % ("ADC" if (self.ctrl_shadow & 8) else "BRAM"))
        parts.append("current_msg=%d" % self.current_msg)
        parts.append("audio_loading=%d" % (1 if self.audio_loading else 0))

        for ch in range(1, 13):
            enabled = bool(self.ch_enable_shadow & (1 << (ch - 1)))
            parts.append("ch%d_enabled=%d" % (ch, 1 if enabled else 0))
            parts.append("ch%d_freq=%d" % (ch, self.ch_freqs[ch]))

        return ";".join(parts)

    def process_command(self, cmd):
        cmd = cmd.strip().upper()

        # Identity
        if cmd == "*IDN?":
            return "RedPitaya,AMRadio-12CH,v2.0"

        # Status query
        if cmd == "STATUS?":
            return self.get_status()

        if cmd == "SYST:STAT?":
            if self.fpga:
                status = self.fpga.read32(REG_STATUS)
                return "0x%08X" % status
            return "0x00000000"

        # Master enable
        if cmd == "OUTPUT:STATE ON":
            self.set_ctrl_bit(CTRL_MASTER_EN, True)
            self.set_ctrl_bit(CTRL_WATCHDOG_EN, True)
            print("BROADCAST: ON")
            return "OK"
        if cmd == "OUTPUT:STATE OFF":
            self.set_ctrl_bit(CTRL_MASTER_EN, False)
            print("BROADCAST: OFF")
            return "OK"

        # Channel enable/disable: CH1:OUTPUT ON, CH12:OUTPUT OFF
        for ch in range(1, 13):
            if cmd == "CH%d:OUTPUT ON" % ch:
                self.set_channel_enable(ch, True)
                return "OK"
            if cmd == "CH%d:OUTPUT OFF" % ch:
                self.set_channel_enable(ch, False)
                return "OK"

        # Channel frequency: CH1:FREQ 540000 or FREQ:CH1 540000
        for ch in range(1, 13):
            prefix1 = "CH%d:FREQ " % ch
            prefix2 = "FREQ:CH%d " % ch

            if cmd.startswith(prefix1):
                try:
                    freq = int(cmd.split()[1])
                    self.set_channel_freq(ch, freq)
                    return "OK"
                except:
                    return "ERROR"

            if cmd.startswith(prefix2):
                try:
                    freq = int(cmd.split()[1])
                    self.set_channel_freq(ch, freq)
                    return "OK"
                except:
                    return "ERROR"

        # Bulk channel enable: CH:EN 0b000000001111 or CH:EN 15
        if cmd.startswith("CH:EN "):
            try:
                val_str = cmd.split()[1]
                if val_str.startswith("0B"):
                    mask = int(val_str, 2)
                elif val_str.startswith("0X"):
                    mask = int(val_str, 16)
                else:
                    mask = int(val_str)
                self.ch_enable_shadow = mask & 0xFFF
                if self.fpga:
                    self.fpga.write32(REG_CH_ENABLE, self.ch_enable_shadow)
                print("CH:EN mask=0b%s" % bin(self.ch_enable_shadow)[2:].zfill(12))
                return "OK"
            except:
                return "ERROR"

        # Audio source
        if cmd == "SOURCE:INPUT ADC":
            self.set_ctrl_bit(CTRL_SOURCE, True)
            print("Source: ADC (live mic)")
            return "OK"
        if cmd == "SOURCE:INPUT BRAM":
            self.set_ctrl_bit(CTRL_SOURCE, False)
            print("Source: BRAM (stored audio)")
            return "OK"

        # Message select - TRIGGERS AUDIO LOADING
        if cmd.startswith("SOURCE:MSG "):
            try:
                msg_id = int(cmd.split()[1])

                # Update control register
                self.ctrl_shadow &= ~(0xF << CTRL_MSG_SHIFT)
                self.ctrl_shadow |= ((msg_id & 0xF) << CTRL_MSG_SHIFT)
                if self.fpga:
                    self.fpga.write32(REG_CTRL, self.ctrl_shadow)

                self.current_msg = msg_id
                print("Message selected: %d" % msg_id)

                # Trigger audio loading in background
                if self.load_audio_file(msg_id):
                    return "OK:LOADING"
                else:
                    return "OK:NO_FILE"
            except:
                return "ERROR"

        # Watchdog (stub)
        if cmd == "WATCHDOG:STATUS?":
            return "watchdog_enabled=1;watchdog_triggered=0;watchdog_time=5"
        if cmd == "WATCHDOG:RESET":
            print("Watchdog reset")
            return "OK"
        if cmd.startswith("WATCHDOG:ENABLE "):
            return "OK"

        # Audio status query
        if cmd == "AUDIO:STATUS?":
            return "loading=%d;msg=%d" % (1 if self.audio_loading else 0, self.current_msg)

        # Direct audio load command: AUDIO:LOAD /path/to/file.wav
        if cmd.startswith("AUDIO:LOAD "):
            try:
                filepath = cmd.split(None, 1)[1]
                if os.path.exists(filepath):
                    # Temporarily add to AUDIO_FILES and load
                    AUDIO_FILES[99] = filepath
                    if self.load_audio_file(99):
                        return "OK:LOADING"
                    else:
                        return "ERROR:BUSY"
                else:
                    return "ERROR:FILE_NOT_FOUND"
            except:
                return "ERROR"

        print("Unknown command: %s" % cmd)
        return "ERROR"


def run_server(host="0.0.0.0", port=5000):
    fpga = FPGARegs()
    if not fpga.open():
        print("\n" + "=" * 50)
        print("WARNING: Running in SIMULATION mode")
        print("FPGA registers not accessible")
        print("=" * 50 + "\n")
        fpga = None

    controller = AMRadioController(fpga)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)

    print("=" * 50)
    print("AM RADIO SCPI SERVER (12-Channel)")
    print("=" * 50)
    print("Listening on %s:%d" % (host, port))
    print("Channels: CH1-CH12")
    print("")
    print("Audio Files:")
    for msg_id, filepath in AUDIO_FILES.items():
        exists = "OK" if os.path.exists(filepath) else "MISSING"
        print("  MSG %d: %s [%s]" % (msg_id, filepath, exists))
    print("")
    print("Commands:")
    print("  CH1:FREQ 540000    - Set CH1 to 540 kHz")
    print("  CH1:OUTPUT ON      - Enable CH1")
    print("  SOURCE:MSG 1       - Load audio file 1")
    print("  OUTPUT:STATE ON    - Start broadcast")
    print("  STATUS?            - Get all states")
    print("")
    print("Waiting for GUI connection...")
    print("=" * 50)

    try:
        while True:
            conn, addr = server.accept()
            print("\n[CONNECTED] %s" % str(addr))
            client_connected = [True]

            def heartbeat():
                while client_connected[0]:
                    if fpga:
                        current = fpga.read32(REG_CTRL)
                        fpga.write32(REG_CTRL, current)
                    time.sleep(2)
            hb_thread = threading.Thread(target=heartbeat, daemon=True)
            hb_thread.start()
            while True:
                try:
                    data = conn.recv(1024).decode().strip()
                    if not data:
                        break

                    # Handle multiple commands
                    for line in data.split('\n'):
                        line = line.strip()
                        if not line:
                            continue

                        print("[RX] %s" % line)
                        response = controller.process_command(line)

                        if "?" in line:
                            conn.send((response + "\n").encode())
                            print("[TX] %s" % response)

                except ConnectionResetError:
                    break
                except Exception as e:
                    print("[ERROR] %s" % str(e))
                    break

            conn.close()
            client_connected[0] = False
            print("[DISCONNECTED]\n")

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.close()
        if fpga:
            fpga.close()


if __name__ == "__main__":
    run_server()