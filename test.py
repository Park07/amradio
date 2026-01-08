import numpy as np
from scipy.io import wavfile
from scipy.signal import resample

# Load
orig_rate, audio = wavfile.read("MXLamAMF.wav")
print(f"Loaded: {len(audio)/orig_rate:.1f}s")

# Mono
if len(audio.shape) > 1:
    audio = audio.mean(axis=1)

# Normalize
audio = audio.astype(np.float32) / 32768.0

# Resample
sample_rate = 100000
audio = resample(audio, int(len(audio) * sample_rate / orig_rate)).astype(np.float32)

# AM modulate
modulated = 0.5 * (1.0 + 0.8 * audio)
modulated = np.clip(modulated, 0, 1)

# Save
output = (modulated * 32767).astype(np.int16)
wavfile.write("am_output.wav", sample_rate, output)
print("Saved: am_output.wav")
