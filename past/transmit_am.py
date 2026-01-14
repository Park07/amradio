#!/usr/bin/env python3

# WAV to AM Transmitter for Red Pitaya (Single Channel)

import socket
import struct
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample
import argparse
import time

# ============ SETTINGS ============
RED_PITAYA_IP = "192.168.0.101"
RED_PITAYA_PORT = 1001
CARRIER_FREQ = 700000  # Hz (700 kHz)
SAMPLE_RATE = 100000   # Hz (100 kHz)
CARRIER_LEVEL = 0.5
MOD_DEPTH = 0.8
# ================================================


def transmit_wav(filepath, freq_hz=CARRIER_FREQ, addr=RED_PITAYA_IP, port=RED_PITAYA_PORT):
    """Transmit WAV file as AM signal"""

    # Load WAV
    orig_rate, audio = wavfile.read(filepath)
    print(f"Loaded: {filepath}")
    print(f"  Duration: {len(audio)/orig_rate:.1f}s")
    print(f"  Sample rate: {orig_rate} Hz")
    print(f"  Samples: {len(audio)}")

    # Mono
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)
        print("  Converted to mono")

    # Normalise based on dtype
    if audio.dtype == np.uint8:
        audio = (audio.astype(np.float32) - 128) / 128.0
    elif audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    else:
        audio = audio.astype(np.float32)
        audio = audio / (np.max(np.abs(audio)) + 1e-10)

    print(f"  Audio range: {audio.min():.2f} to {audio.max():.2f}")

    # Resample
    if orig_rate != SAMPLE_RATE:
        print(f"Resampling {orig_rate} Hz -> {SAMPLE_RATE} Hz...")
        audio = resample(audio, int(len(audio) * SAMPLE_RATE / orig_rate)).astype(np.float32)
        print(f"  New samples: {len(audio)}")

    # AM modulate
    print(f"AM Modulation:")
    print(f"  Carrier level: {CARRIER_LEVEL}")
    print(f"  Modulation depth: {MOD_DEPTH}")

    modulated = CARRIER_LEVEL * (1.0 + MOD_DEPTH * audio)
    modulated = np.clip(modulated, 0, 1)
    print(f"  Output range: {modulated.min():.2f} to {modulated.max():.2f}")

    # Convert to IQ (I = signal, Q = 0)
    iq = np.zeros(len(modulated) * 2, dtype=np.float32)
    iq[0::2] = modulated  # I
    iq[1::2] = 0          # Q

    # Connect
    print(f"\nConnecting to Red Pitaya at {addr}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((addr, port))
        print("  Connected!")
    except socket.timeout:
        print("  ERROR: Connection timed out")
        print("  Is Red Pitaya on? Is SDR Transceiver app running?")
        return
    except socket.error as e:
        print(f"  ERROR: {e}")
        return

    # Set frequency
    sock.sendall(struct.pack('<I', int(freq_hz)))
    print(f"Frequency set: {freq_hz/1000:.0f} kHz ({freq_hz} Hz)")

    # Transmit
    print(f"\nTransmitting {len(audio)/SAMPLE_RATE:.1f} seconds of audio...")
    start = time.time()
    chunk_size = 8192

    for i in range(0, len(iq), chunk_size):
        sock.sendall(iq[i:i+chunk_size].tobytes())
        elapsed = time.time() - start
        expected = (i // 2) / SAMPLE_RATE
        if elapsed < expected:
            time.sleep(expected - elapsed)

    elapsed = time.time() - start
    print(f"\nDone! Transmitted in {elapsed:.1f}s")
    print(f"Check CubicSDR at {freq_hz/1000:.0f} kHz to verify!")
    sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AM Transmitter for Red Pitaya')
    parser.add_argument("--file", "-f", type=str, default="MXLamAMF.wav")
    parser.add_argument("--freq", type=int, default=CARRIER_FREQ)
    parser.add_argument("--addr", "-a", type=str, default=RED_PITAYA_IP)
    parser.add_argument("--port", "-p", type=int, default=RED_PITAYA_PORT)
    args = parser.parse_args()

    print("="*50)
    print("AM Transmitter for Red Pitaya")
    print("="*50)
    transmit_wav(args.file, args.freq, args.addr, args.port)