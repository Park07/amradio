#!/usr/bin/env python3
"""
Generate test audio files for AM transmission testing
"""

import numpy as np
from scipy.io import wavfile

def generate_tone(frequency, duration, sample_rate=44100, filename=None):
    """Generate a sine wave test tone"""
    if filename is None:
        filename = f"test_{frequency}Hz_{duration}s.wav"

    t = np.arange(int(sample_rate * duration)) / sample_rate

    # Pure tone
    tone = np.sin(2 * np.pi * frequency * t)

    # Add envelope variation (makes it more interesting)
    envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 1 * t)  # 1 Hz envelope
    tone = tone * envelope

    # Convert to int16
    tone = (tone * 32767 * 0.8).astype(np.int16)  # 0.8 to avoid clipping

    wavfile.write(filename, sample_rate, tone)
    print(f"Created: {filename} ({frequency} Hz, {duration}s, {sample_rate} Hz)")
    return filename


def generate_sweep(start_freq, end_freq, duration, sample_rate=44100, filename=None):
    """Generate a frequency sweep"""
    if filename is None:
        filename = f"sweep_{start_freq}_{end_freq}Hz_{duration}s.wav"

    t = np.arange(int(sample_rate * duration)) / sample_rate

    # Linear frequency sweep
    freq = np.linspace(start_freq, end_freq, len(t))
    phase = 2 * np.pi * np.cumsum(freq) / sample_rate
    sweep = np.sin(phase)

    # Convert to int16
    sweep = (sweep * 32767 * 0.8).astype(np.int16)

    wavfile.write(filename, sample_rate, sweep)
    print(f"Created: {filename} ({start_freq}-{end_freq} Hz sweep, {duration}s)")
    return filename


def generate_voice_like(duration, sample_rate=44100, filename=None):
    """Generate voice-like test signal (multiple frequencies)"""
    if filename is None:
        filename = f"voice_test_{duration}s.wav"

    t = np.arange(int(sample_rate * duration)) / sample_rate

    # Combine multiple frequencies (like voice harmonics)
    signal = np.zeros_like(t)

    # Fundamental + harmonics
    for freq, amp in [(200, 1.0), (400, 0.5), (600, 0.3), (800, 0.2), (1000, 0.1)]:
        signal += amp * np.sin(2 * np.pi * freq * t)

    # Add amplitude modulation (like speech patterns)
    envelope = 0.3 + 0.7 * np.abs(np.sin(2 * np.pi * 3 * t))  # 3 Hz variation
    signal = signal * envelope

    # Normalise
    signal = signal / np.max(np.abs(signal))

    # Convert to int16
    signal = (signal * 32767 * 0.8).astype(np.int16)

    wavfile.write(filename, sample_rate, signal)
    print(f"Created: {filename} (voice-like, {duration}s)")
    return filename


if __name__ == "__main__":
    print("Generating test audio files...\n")

    # Short tones (for quick tests)
    generate_tone(500, 2, filename="tone_500Hz_2s.wav")
    generate_tone(1000, 2, filename="tone_1000Hz_2s.wav")

    # Longer tones (for proper testing)
    generate_tone(500, 10, filename="tone_500Hz_10s.wav")
    generate_tone(1000, 10, filename="tone_1000Hz_10s.wav")

    # Frequency sweep (to test range)
    generate_sweep(200, 2000, 5, filename="sweep_200_2000Hz_5s.wav")

    # Voice-like signal
    generate_voice_like(5, filename="voice_test_5s.wav")
    generate_voice_like(10, filename="voice_test_10s.wav")

    print("\n" + "="*50)
    print("Test files created!")
    print("="*50)
    print("\nUsage:")
    print("  python3 transmit_am.py --file tone_500Hz_10s.wav --freq 700000")
    print("  python3 transmit_am.py --file voice_test_10s.wav --freq 700000")

