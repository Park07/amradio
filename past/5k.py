#!/usr/bin/env python3
"""
AM Modulation - 5 kHz Carrier, 50ms zoom
"""

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample, hilbert
import matplotlib.pyplot as plt

# Load audio
orig_rate, orig = wavfile.read("MXLamAMF.wav")
if len(orig.shape) > 1:
    orig = orig.mean(axis=1)

# Normalise uint8 to -1 to +1
audio = (orig.astype(np.float32) - 128) / 128.0

# Resample to 100kHz
sample_rate = 100000
audio = resample(audio, int(len(audio) * sample_rate / orig_rate)).astype(np.float32)

# Create time axis
time = np.arange(len(audio)) / sample_rate

# AM parameters
carrier_level = 0.5
mod_depth = 0.8
envelope = carrier_level * (1.0 + mod_depth * audio)

# 5 kHz carrier
carrier_freq = 5000
carrier_wave = np.cos(2 * np.pi * carrier_freq * time)
am_output = envelope * carrier_wave

# Get envelope using Hilbert transform
am_envelope = np.abs(hilbert(am_output))
envelope_scaled = (am_envelope - carrier_level) / (carrier_level * mod_depth)

# Zoom to 50ms
zoom_end = 0.05
mask = time <= zoom_end

# === PLOT: 3 panel ===
fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

# 1. Original audio
axes[0].plot(time[mask], audio[mask], color='blue', linewidth=1.5)
axes[0].set_ylabel('Amplitude')
axes[0].set_title('Original Audio (~100 Hz)', fontsize=12, fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].set_ylim(-1.2, 1.2)

# 2. Carrier wave
axes[1].plot(time[mask], carrier_wave[mask], color='orange', linewidth=0.5)
axes[1].set_ylabel('Amplitude')
axes[1].set_title(f'Carrier Wave ({carrier_freq} Hz) - Real transmission uses 700 kHz', fontsize=12, fontweight='bold')
axes[1].grid(True, alpha=0.3)
axes[1].set_ylim(-1.2, 1.2)

# 3. AM output
axes[2].plot(time[mask], am_output[mask], color='purple', linewidth=0.3)
axes[2].set_ylabel('Amplitude')
axes[2].set_title('AM Output (5 kHz carrier, amplitude follows original)', fontsize=12, fontweight='bold')
axes[2].set_xlabel('Time (seconds)')
axes[2].grid(True, alpha=0.3)
axes[2].set_ylim(-1.2, 1.2)

plt.tight_layout()
plt.savefig('am_5kHz_50ms.png', dpi=150)
print("Saved: am_5kHz_50ms.png")
plt.close()


# === PLOT: 4 panel with envelope ===
fig2, axes2 = plt.subplots(4, 1, figsize=(14, 12), sharex=True)

# 1. Original audio
axes2[0].plot(time[mask], audio[mask], color='blue', linewidth=1.5)
axes2[0].set_ylabel('Amplitude')
axes2[0].set_title('1. Original Audio (~100 Hz)', fontsize=11, fontweight='bold')
axes2[0].grid(True, alpha=0.3)
axes2[0].set_ylim(-1.2, 1.2)

# 2. Carrier wave
axes2[1].plot(time[mask], carrier_wave[mask], color='orange', linewidth=0.5)
axes2[1].set_ylabel('Amplitude')
axes2[1].set_title(f'2. Carrier Wave ({carrier_freq} Hz)', fontsize=11, fontweight='bold')
axes2[1].grid(True, alpha=0.3)
axes2[1].set_ylim(-1.2, 1.2)

# 3. AM output with envelope
axes2[2].plot(time[mask], am_output[mask], color='purple', linewidth=0.3, alpha=0.7)
axes2[2].plot(time[mask], am_envelope[mask], color='red', linewidth=2, label='Envelope')
axes2[2].plot(time[mask], -am_envelope[mask], color='red', linewidth=2)
axes2[2].set_ylabel('Amplitude')
axes2[2].set_title('3. AM Output with Envelope (red)', fontsize=11, fontweight='bold')
axes2[2].legend(loc='upper right')
axes2[2].grid(True, alpha=0.3)
axes2[2].set_ylim(-1.2, 1.2)

# 4. Comparison
axes2[3].plot(time[mask], audio[mask], color='blue', linewidth=2, label='Original Audio')
axes2[3].plot(time[mask], envelope_scaled[mask], color='red', linewidth=2, linestyle='--', label='AM Envelope')
axes2[3].set_ylabel('Amplitude')
axes2[3].set_title('4. Amplitude Comparison - Original (blue) vs Envelope (red)', fontsize=11, fontweight='bold')
axes2[3].set_xlabel('Time (seconds)')
axes2[3].legend(loc='upper right')
axes2[3].grid(True, alpha=0.3)
axes2[3].set_ylim(-1.2, 1.2)

plt.tight_layout()
plt.savefig('am_5kHz_50ms_envelope.png', dpi=150)
print("Saved: am_5kHz_50ms_envelope.png")
plt.close()


# === PLOT: Even shorter zoom (10ms) to see carrier better ===
zoom_short = 0.01
mask_short = time <= zoom_short

fig3, axes3 = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

axes3[0].plot(time[mask_short], audio[mask_short], color='blue', linewidth=1.5)
axes3[0].set_ylabel('Amplitude')
axes3[0].set_title('Original Audio (~100 Hz)', fontsize=12, fontweight='bold')
axes3[0].grid(True, alpha=0.3)
axes3[0].set_ylim(-1.2, 1.2)

axes3[1].plot(time[mask_short], carrier_wave[mask_short], color='orange', linewidth=1)
axes3[1].set_ylabel('Amplitude')
axes3[1].set_title(f'Carrier Wave ({carrier_freq} Hz)', fontsize=12, fontweight='bold')
axes3[1].grid(True, alpha=0.3)
axes3[1].set_ylim(-1.2, 1.2)

axes3[2].plot(time[mask_short], am_output[mask_short], color='purple', linewidth=0.5)
axes3[2].set_ylabel('Amplitude')
axes3[2].set_title('AM Output', fontsize=12, fontweight='bold')
axes3[2].set_xlabel('Time (seconds)')
axes3[2].grid(True, alpha=0.3)
axes3[2].set_ylim(-1.2, 1.2)

plt.tight_layout()
plt.savefig('am_5kHz_10ms.png', dpi=150)
print("Saved: am_5kHz_10ms.png")
plt.close()


print("\nDone! Files:")
print("  - am_5kHz_50ms.png          (3 panel, 50ms)")
print("  - am_5kHz_50ms_envelope.png (4 panel with envelope)")
print("  - am_5kHz_10ms.png          (3 panel, 10ms - clearer carrier)")

# What audio format will the real emergency messages be?


# 1k Hz audio file, very clean side band around the carrier, see the frequency line go on spotify lots of places
# that would help with the visualising
# audio input format is fine, proving that it's feasible doesn't matter too much..
