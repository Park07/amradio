import numpy as np
import matplotlib.pyplot as plt

# Setup
x = np.linspace(0, 6.5*np.pi, 500)

# Individual waves
y1 = np.sin(x)           # First sine
y2 = np.sin(2*x)         # Second sine (different frequency)
y_sum = y1 + y2          # Combined

# AM modulation of each
depth = 0.5
am_single = 1.0 + depth * y1
am_combined = 1.0 + depth * (y_sum / 2)  # Normalize combined

# Create figure with 4 rows
fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

# Row 1: First sine wave
axes[0].plot(x, y1, 'b-', lw=2)
axes[0].set_title('Sine Wave 1 (frequency = 1x)', fontsize=12)
axes[0].set_ylabel('Amplitude')
axes[0].axhline(0, color='gray', linestyle='-', alpha=0.3)
axes[0].set_ylim(-2.5, 2.5)
axes[0].grid(True, alpha=0.3)

# Row 2: Second sine wave
axes[1].plot(x, y2, 'g-', lw=2)
axes[1].set_title('Sine Wave 2 (frequency = 2x)', fontsize=12)
axes[1].set_ylabel('Amplitude')
axes[1].axhline(0, color='gray', linestyle='-', alpha=0.3)
axes[1].set_ylim(-2.5, 2.5)
axes[1].grid(True, alpha=0.3)

# Row 3: Sum of both
axes[2].plot(x, y_sum, 'purple', lw=2)
axes[2].set_title('Combined: Wave 1 + Wave 2', fontsize=12)
axes[2].set_ylabel('Amplitude')
axes[2].axhline(0, color='gray', linestyle='-', alpha=0.3)
axes[2].set_ylim(-2.5, 2.5)
axes[2].grid(True, alpha=0.3)

# Row 4: AM modulated
axes[3].plot(x, am_combined, 'r-', lw=2)
axes[3].axhline(1.0, color='gray', linestyle='--', alpha=0.5, label='Carrier level')
axes[3].set_title('AM Modulated (Combined signal on carrier)', fontsize=12)
axes[3].set_ylabel('Amplitude')
axes[3].set_xlabel('Time')
axes[3].set_ylim(0, 2)
axes[3].grid(True, alpha=0.3)
axes[3].legend()

plt.tight_layout()
plt.savefig('am_visualization_clear.png', dpi=150)
plt.show()
print("Saved to am_visualization_clear.png")
