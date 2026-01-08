#!/usr/bin/env python3
"""
AM Modulation - Same Timeline Comparison
Shows original audio, carrier wave, and AM output aligned on same time axis
"""

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample
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

# === AM Modulation ===
carrier_level = 0.5
mod_depth = 0.8
modulated = carrier_level * (1.0 + mod_depth * audio)

# Create a visible carrier wave for display (not the real RF carrier)
# Real carrier would be 700kHz - too fast to see
# Using 500Hz just for visualisation
carrier_freq = 500  # Hz (just for display)
carrier_wave = np.cos(2 * np.pi * carrier_freq * time)

# AM with visible carrier (for visualisation only)
am_with_carrier = modulated * carrier_wave

# === PLOT: Full timeline comparison ===
fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)

# 1. Original audio (message signal)
axes[0].plot(time, audio, color='blue')
axes[0].set_ylabel('Amplitude')
axes[0].set_title('1. Original Audio (Message Signal)')
axes[0].grid(True, alpha=0.3)
axes[0].set_ylim(-1.2, 1.2)

# 2. Carrier wave
axes[1].plot(time, carrier_wave, color='orange')
axes[1].set_ylabel('Amplitude')
axes[1].set_title(f'2. Carrier Wave ({carrier_freq}Hz - slowed down for visualisation)')
axes[1].grid(True, alpha=0.3)
axes[1].set_ylim(-1.2, 1.2)

# 3. AM envelope (what we send to Red Pitaya)
axes[2].plot(time, modulated, color='green')
axes[2].axhline(y=carrier_level, color='r', linestyle='--', alpha=0.5, label=f'Carrier level ({carrier_level})')
axes[2].set_ylabel('Amplitude')
axes[2].set_title('3. AM Envelope (sent to Red Pitaya)')
axes[2].legend(loc='upper right')
axes[2].grid(True, alpha=0.3)
axes[2].set_ylim(0, 1.2)

# 4. AM with carrier (what actually gets transmitted)
axes[3].plot(time, am_with_carrier, color='purple')
axes[3].set_ylabel('Amplitude')
axes[3].set_title('4. AM Output = Envelope × Carrier (actual RF signal)')
axes[3].set_xlabel('Time (seconds)')
axes[3].grid(True, alpha=0.3)
axes[3].set_ylim(-1.2, 1.2)

plt.tight_layout()
plt.savefig('am_timeline_full.png', dpi=150)
print("Saved: am_timeline_full.png")

# === PLOT: Zoomed view (first 0.05 seconds) ===
fig2, axes2 = plt.subplots(4, 1, figsize=(14, 10), sharex=True)

zoom_end = 0.05  # seconds
mask = time <= zoom_end

axes2[0].plot(time[mask], audio[mask], color='blue')
axes2[0].set_ylabel('Amplitude')
axes2[0].set_title('1. Original Audio (Message Signal)')
axes2[0].grid(True, alpha=0.3)
axes2[0].set_ylim(-1.2, 1.2)

axes2[1].plot(time[mask], carrier_wave[mask], color='orange')
axes2[1].set_ylabel('Amplitude')
axes2[1].set_title(f'2. Carrier Wave ({carrier_freq}Hz)')
axes2[1].grid(True, alpha=0.3)
axes2[1].set_ylim(-1.2, 1.2)

axes2[2].plot(time[mask], modulated[mask], color='green')
axes2[2].axhline(y=carrier_level, color='r', linestyle='--', alpha=0.5, label=f'Carrier level ({carrier_level})')
axes2[2].set_ylabel('Amplitude')
axes2[2].set_title('3. AM Envelope')
axes2[2].legend(loc='upper right')
axes2[2].grid(True, alpha=0.3)
axes2[2].set_ylim(0, 1.2)

axes2[3].plot(time[mask], am_with_carrier[mask], color='purple')
axes2[3].set_ylabel('Amplitude')
axes2[3].set_title('4. AM Output = Envelope × Carrier')
axes2[3].set_xlabel('Time (seconds)')
axes2[3].grid(True, alpha=0.3)
axes2[3].set_ylim(-1.2, 1.2)

plt.tight_layout()
plt.savefig('am_timeline_zoomed.png', dpi=150)
print("Saved: am_timeline_zoomed.png")

# === PLOT: 3 panels only (what supervisor asked for) ===
fig3, axes3 = plt.subplots(3, 1, figsize=(14, 8), sharex=True)

axes3[0].plot(time[mask], audio[mask], color='blue')
axes3[0].set_ylabel('Amplitude')
axes3[0].set_title('Original Audio')
axes3[0].grid(True, alpha=0.3)

axes3[1].plot(time[mask], carrier_wave[mask], color='orange')
axes3[1].set_ylabel('Amplitude')
axes3[1].set_title(f'Carrier Wave ({carrier_freq}Hz)')
axes3[1].grid(True, alpha=0.3)

axes3[2].plot(time[mask], am_with_carrier[mask], color='purple')
axes3[2].set_ylabel('Amplitude')
axes3[2].set_title('AM Output')
axes3[2].set_xlabel('Time (seconds)')
axes3[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('am_timeline_3panel.png', dpi=150)
print("Saved: am_timeline_3panel.png")

plt.close('all')
print("\nDone! Three files:")
print("  - am_timeline_full.png   (4 panels, full timeline)")
print("  - am_timeline_zoomed.png (4 panels, zoomed to 0.05s)")
print("  - am_timeline_3panel.png (3 panels - what supervisor asked for)")