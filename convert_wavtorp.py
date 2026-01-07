#!/usr/bin/env python3
"""
WAV to AM Transmitter for Red Pitaya (Single Channel)
"""

import socket
import struct
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample
import argparse
import time


def transmit_wav(filepath, freq_hz=702000, addr="192.168.1.100", port=1001):
    """Transmit WAV file as AM signal"""

    # Load WAV
    orig_rate, audio = wavfile.read(filepath)
    print(f"Loaded: {filepath} ({len(audio)/orig_rate:.1f}s)")

    # Mono
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)

    # Normalize
    audio = audio.astype(np.float32) / 32768.0

    # Resample to 100kSPS
    sample_rate = 100000
    audio = resample(audio, int(len(audio) * sample_rate / orig_rate)).astype(np.float32)

    # AM modulate: carrier + audio
    carrier = 0.5
    depth = 0.8
    modulated = carrier * (1.0 + depth * audio)
    modulated = np.clip(modulated, 0, 1)

    # Convert to IQ (I = signal, Q = 0)
    iq = np.zeros(len(modulated) * 2, dtype=np.float32)
    iq[0::2] = modulated  # I
    iq[1::2] = 0          # Q

    # Connect
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((addr, port))
    print(f"Connected to {addr}:{port}")

    # Set frequency
    sock.sendall(struct.pack('<I', int(freq_hz)))
    print(f"Frequency: {freq_hz/1000:.0f} kHz")

    # Transmit
    print("Transmitting...")
    start = time.time()
    chunk_size = 8192

    for i in range(0, len(iq), chunk_size):
        sock.sendall(iq[i:i+chunk_size].tobytes())
        # Pace transmission
        elapsed = time.time() - start
        expected = (i // 2) / sample_rate
        if elapsed < expected:
            time.sleep(expected - elapsed)

    print(f"Done ({time.time()-start:.1f}s)")
    sock.close()


def create_test_tone(filename="test_tone.wav"):
    """Create 1kHz test tone"""
    t = np.linspace(0, 5, 48000 * 5, dtype=np.float32)
    audio = (0.8 * np.sin(2 * np.pi * 1000 * t) * 32767).astype(np.int16)
    wavfile.write(filename, 48000, audio)
    print(f"Created: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", type=str)
    parser.add_argument("--freq", type=int, default=702000)
    parser.add_argument("--addr", type=str, default="192.168.1.100")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        create_test_tone("test_tone.wav")
        args.file = "test_tone.wav"

    if args.file:
        transmit_wav(args.file, args.freq, args.addr)
    else:
        print("Usage: python wav_to_am.py --file audio.wav --freq 702000")
        print("       python wav_to_am.py --test")