#!/usr/bin/env python3
"""Test WAV to AM conversion locally - no hardware needed"""

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample

# Load WAV
orig_rate, audio = wavfile.read("MXLamAMF.wav")
print(f"Loaded: MXLamAMF.wav ({len(audio)/orig_rate:.1f}s)")

# Mono
if len(audio.shape) > 1:
    audio = audio.mean(axis=1)

# Normalize
audio = audio.astype(np.float32) / 32768.0

# Resample to 100kSPS
sample_rate = 100000
audio = resample(audio, int(len(audio) * sample_rate / orig_rate)).astype(np.float32)

# AM modulate
carrier = 0.5
depth = 0.8
modulated = carrier * (1.0 + depth * audio)
modulated = np.clip(modulated, 0, 1)

# Save as WAV to verify
output = (modulated * 32767).astype(np.int16)
wavfile.write("am_output.wav", sample_rate, output)
print("Saved: am_output.wav - open in Audacity to verify AM modulation")
