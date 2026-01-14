import numpy as np
import matplotlib.pyplot as plt

# Fewer samples, lower frequencies for clearer view
samples = 1000
t = np.linspace(0, 1, samples)

# 1. Single sine - LOW frequency
single_sine = np.sin(2 * np.pi * 5 * t)  # 5 Hz - easy to see

# 2. Two sines combined - different frequencies
sine1 = np.sin(2 * np.pi * 5 * t)   # 5 Hz
sine2 = np.sin(2 * np.pi * 12 * t)  # 12 Hz
two_sines = (sine1 + sine2) / 2

# 3. Complex wave with harmonics
wave1 = np.sin(2 * np.pi * 3 * t)                    # Base
wave2 = 0.5 * np.sin(2 * np.pi * 6 * t + np.pi/3)   # 2nd harmonic
wave3 = 0.3 * np.sin(2 * np.pi * 9 * t + np.pi/2)   # 3rd harmonic
complex_wave = wave1 + wave2 + wave3
complex_wave = complex_wave / np.max(np.abs(complex_wave))

# AM modulation
depth = 0.5
am_single = 1.0 + depth * single_sine
am_two = 1.0 + depth * two_sines
am_complex = 1.0 + depth * complex_wave

# Plot
fig, axes = plt.subplots(3, 2, figsize=(14, 10))

# Row 1: Single sine
axes[0, 0].plot(t, single_sine, 'b-', linewidth=1.5)
axes[0, 0].set_title('Single Sine (5 Hz) - Audio')
axes[0, 0].set_ylabel('Amplitude')
axes[0, 0].set_ylim(-1.5, 1.5)
axes[0, 0].grid(True, alpha=0.3)

axes[0, 1].plot(t, am_single, 'r-', linewidth=1.5)
axes[0, 1].set_title('Single Sine - AM Modulated')
axes[0, 1].axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Carrier')
axes[0, 1].set_ylim(0, 1.8)
axes[0, 1].grid(True, alpha=0.3)

# Row 2: Two sines
axes[1, 0].plot(t, two_sines, 'b-', linewidth=1.5)
axes[1, 0].set_title('Two Sines (5 Hz + 12 Hz) - Audio')
axes[1, 0].set_ylabel('Amplitude')
axes[1, 0].set_ylim(-1.5, 1.5)
axes[1, 0].grid(True, alpha=0.3)

axes[1, 1].plot(t, am_two, 'r-', linewidth=1.5)
axes[1, 1].set_title('Two Sines - AM Modulated')
axes[1, 1].axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
axes[1, 1].set_ylim(0, 1.8)
axes[1, 1].grid(True, alpha=0.3)

# Row 3: Complex
axes[2, 0].plot(t, complex_wave, 'b-', linewidth=1.5)
axes[2, 0].set_title('Complex (3 + 6 + 9 Hz with phases) - Audio')
axes[2, 0].set_ylabel('Amplitude')
axes[2, 0].set_xlabel('Time (s)')
axes[2, 0].set_ylim(-1.5, 1.5)
axes[2, 0].grid(True, alpha=0.3)

axes[2, 1].plot(t, am_complex, 'r-', linewidth=1.5)
axes[2, 1].set_title('Complex - AM Modulated')
axes[2, 1].set_xlabel('Time (s)')
axes[2, 1].axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
axes[2, 1].set_ylim(0, 1.8)
axes[2, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('waveform_clear.png', dpi=150)
plt.show()
print("Saved to waveform_clear.png")
