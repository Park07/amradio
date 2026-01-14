import numpy as np
import matplotlib.pyplot as plt

samples = 16384
t = np.linspace(0, 1, samples)

# 1. Single sine (what you tested)
single_sine = np.sin(2 * np.pi * 1000 * t * 10)

# 2. Two sines combined
sine1 = np.sin(2 * np.pi * 500 * t * 10)
sine2 = np.sin(4 * np.pi * 800 * t * 10)
two_sines = (sine1 + sine2) / 2

# 3. Complex wave (harmonics + phase shifts)
wave1 = np.sin(2 * np.pi * 400 * t * 10)
wave2 = 0.5 * np.sin(4 * np.pi * 400 * t * 10 + np.pi/3)
wave3 = 0.3 * np.sin(6 * np.pi * 400 * t * 10 + 4*np.pi/3)
complex_wave = wave1 + wave2 + wave3
complex_wave = complex_wave / np.max(np.abs(complex_wave))

# AM modulation for each
depth = 0.5
am_single = 1.0 + depth * single_sine
am_two = 1.0 + depth * two_sines
am_complex = 1.0 + depth * complex_wave

# Plot
fig, axes = plt.subplots(3, 2, figsize=(14, 10))

# Row 1: Single sine
axes[0, 0].plot(t[:500], single_sine[:500], 'b-')
axes[0, 0].set_title('Single Sine (1 kHz) - Audio')
axes[0, 0].set_ylabel('Amplitude')

axes[0, 1].plot(t[:500], am_single[:500], 'r-')
axes[0, 1].set_title('Single Sine - AM Modulated')
axes[0, 1].axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)

# Row 2: Two sines
axes[1, 0].plot(t[:500], two_sines[:500], 'b-')
axes[1, 0].set_title('Two Sines (500 + 800 Hz) - Audio')
axes[1, 0].set_ylabel('Amplitude')

axes[1, 1].plot(t[:500], am_two[:500], 'r-')
axes[1, 1].set_title('Two Sines - AM Modulated')
axes[1, 1].axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)

# Row 3: Complex
axes[2, 0].plot(t[:500], complex_wave[:500], 'b-')
axes[2, 0].set_title('Complex (Harmonics + Phase) - Audio')
axes[2, 0].set_ylabel('Amplitude')
axes[2, 0].set_xlabel('Time')

axes[2, 1].plot(t[:500], am_complex[:500], 'r-')
axes[2, 1].set_title('Complex - AM Modulated')
axes[2, 1].set_xlabel('Time')
axes[2, 1].axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('waveform_comparison.png', dpi=150)
plt.show()
print("Saved to waveform_comparison.png")
