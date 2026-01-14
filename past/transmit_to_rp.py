#!/usr/bin/env python3

# WAV to AM Transmitter for Red Pitaya (Single Channel)


import socket
import struct
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample
import argparse
import time


def transmit_wav(filepath, freq_hz=700000, addr="localhost", port=1001):
    """Transmit WAV file as AM signal"""

    # Load WAV
    orig_rate, audio = wavfile.read(filepath)
    print(f"Loaded: {filepath} ({len(audio)/orig_rate:.1f}s)")

    # Mono
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)

    # Normalise
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", type=str, default="MXLamAMF.wav")
    parser.add_argument("--freq", type=int, default=702000)
    parser.add_argument("--addr", type=str, default="localhost")
    args = parser.parse_args()

    transmit_wav(args.file, args.freq, args.addr)
