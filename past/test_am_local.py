#!/usr/bin/env python3
"""
Local AM Test - Process audio and verify modulation without transmitting
Tests everything EXCEPT the 700 kHz carrier (which Red Pitaya adds)
"""

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample
import matplotlib.pyplot as plt
import os

def test_am_local(input_file, output_file=None):
    """Test AM modulation locally"""

    if output_file is None:
        base = os.path.splitext(input_file)[0]
        output_file = f"{base}_am_output.wav"

    print("="*50)
    print("LOCAL AM TEST")
    print("="*50)

    # Load audio
    print(f"\n1. Loading: {input_file}")
    orig_rate, audio = wavfile.read(input_file)
    print(f"   Sample rate: {orig_rate} Hz")
    print(f"   Duration: {len(audio)/orig_rate:.2f}s")
    print(f"   Samples: {len(audio)}")

    # Mono
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)
        print("   Converted to mono")

    # Normalise
    if audio.dtype == np.uint8:
        audio_norm = (audio.astype(np.float32) - 128) / 128.0
    elif audio.dtype == np.int16:
        audio_norm = audio.astype(np.float32) / 32768.0
    else:
        audio_norm = audio.astype(np.float32)
        audio_norm = audio_norm / (np.max(np.abs(audio_norm)) + 1e-10)

    print(f"   Audio range: {audio_norm.min():.2f} to {audio_norm.max():.2f}")

    # Resample to 100kHz
    sample_rate = 100000
    print(f"\n2. Resampling to {sample_rate} Hz...")
    audio_resampled = resample(audio_norm, int(len(audio_norm) * sample_rate / orig_rate)).astype(np.float32)
    print(f"   New samples: {len(audio_resampled)}")

    # AM Modulation
    carrier_level = 0.5
    mod_depth = 0.8
    print(f"\n3. AM Modulation:")
    print(f"   Carrier level: {carrier_level}")
    print(f"   Modulation depth: {mod_depth}")
    print(f"   Formula: {carrier_level} * (1 + {mod_depth} * audio)")

    envelope = carrier_level * (1.0 + mod_depth * audio_resampled)
    envelope = np.clip(envelope, 0, 1)

    print(f"   Envelope range: {envelope.min():.2f} to {envelope.max():.2f}")

    # Check for issues
    print(f"\n4. Quality checks:")
    if envelope.min() <= 0:
        print("   ⚠️  WARNING: Envelope hits zero (overmodulation!)")
    else:
        print("   ✅ Envelope stays positive (no overmodulation)")

    if envelope.max() > 1:
        print("   ⚠️  WARNING: Envelope exceeds 1 (clipping!)")
    else:
        print("   ✅ Envelope within range")

    # Save output (as audio you can hear)
    # Convert envelope back to audio format
    output_audio = ((envelope - 0.5) * 2 * 32767).astype(np.int16)
    wavfile.write(output_file, sample_rate, output_audio)
    print(f"\n5. Saved: {output_file}")
    print(f"   Play with: afplay {output_file}")

    # Plot
    print(f"\n6. Generating plot...")

    # Time axis (show first 50ms)
    time_ms = 50
    samples_to_show = int(sample_rate * time_ms / 1000)
    time = np.arange(samples_to_show) / sample_rate * 1000  # in ms

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Original audio (resampled)
    axes[0].plot(time, audio_resampled[:samples_to_show], color='blue')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title('Original Audio (normalized)')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim(-1.2, 1.2)
# 192.168.0.101
    # AM envelope
    axes[1].plot(time, envelope[:samples_to_show], color='green')
    axes[1].axhline(y=carrier_level, color='r', linestyle='--', label=f'Carrier level ({carrier_level})')
    axes[1].set_ylabel('Amplitude')
    axes[1].set_title('AM Envelope (what gets sent to Red Pitaya)')
    axes[1].set_xlabel('Time (ms)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim(0, 1.2)

    plot_file = f"{os.path.splitext(input_file)[0]}_am_plot.png"
    plt.tight_layout()
    plt.savefig(plot_file, dpi=150)
    print(f"   Saved plot: {plot_file}")
    plt.close()

    print("\n" + "="*50)
    print("LOCAL TEST COMPLETE")
    print("="*50)
    print(f"\nNext steps:")
    print(f"  1. Listen: afplay {output_file}")
    print(f"  2. View:   open {plot_file}")
    print(f"  3. If OK, transmit:")
    print(f"     python3 transmit_am.py --file {input_file} --freq 700000")

    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Default test file
        input_file = "tone_500Hz_2s.wav"

        # Generate if doesn't exist
        if not os.path.exists(input_file):
            print(f"Generating {input_file}...")
            sample_rate = 44100
            duration = 2
            t = np.arange(int(sample_rate * duration)) / sample_rate
            tone = np.sin(2 * np.pi * 500 * t)
            envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 1 * t)
            tone = (tone * envelope * 32767 * 0.8).astype(np.int16)
            wavfile.write(input_file, sample_rate, tone)
            print(f"Created: {input_file}\n")

    test_am_local(input_file)