#!/usr/bin/env python3
"""
Compare filtered vs unfiltered AM modulation.
Shows the effect of each DSP stage.
"""

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, filtfilt, resample, freqz
import matplotlib.pyplot as plt
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from am_modulator import AMModulator


def plot_frequency_spectrum(audio, sample_rate, title, ax):
    """Plot frequency spectrum of audio signal."""
    n = len(audio)
    freq = np.fft.rfftfreq(n, 1/sample_rate)
    spectrum = np.abs(np.fft.rfft(audio))
    spectrum_db = 20 * np.log10(spectrum + 1e-10)

    ax.plot(freq, spectrum_db)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Magnitude (dB)')
    ax.set_title(title)
    ax.set_xlim(0, min(sample_rate/2, 10000))
    ax.grid(True, alpha=0.3)


def main():
    # Check for input file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Try to find a WAV file
        for f in ['MXLamAMF.wav', 'test.wav', 'input.wav']:
            if os.path.exists(f):
                input_file = f
                break
        else:
            print("Usage: python3 am_compare.py <input.wav>")
            print("No input file found!")
            return 1

    print(f"Comparing filtered vs unfiltered AM modulation")
    print(f"Input: {input_file}")
    print("=" * 50)

    # Load original
    orig_rate, orig_audio = wavfile.read(input_file)
    if len(orig_audio.shape) > 1:
        orig_audio = orig_audio.mean(axis=1)
    orig_audio = orig_audio.astype(np.float32)

    # Handle uint8 format
    if orig_audio.min() >= 0 and orig_audio.max() <= 255 and orig_audio.max() > 1:
        orig_audio = (orig_audio - 128) / 128.0
    elif orig_audio.max() > 1.0:
        orig_audio = orig_audio / np.max(np.abs(orig_audio))

    print(f"Original: {orig_rate}Hz, {len(orig_audio)} samples")

    # Process with filters
    print("\n--- With Filters ---")
    mod_filtered = AMModulator(
        output_sample_rate=100000,
        enable_filters=True,
        verbose=True
    )
    output_filtered, rate_filtered = mod_filtered.process_file(input_file)

    # Process without filters
    print("\n--- Without Filters ---")
    mod_raw = AMModulator(
        output_sample_rate=100000,
        enable_filters=False,
        verbose=True
    )
    output_raw, rate_raw = mod_raw.process_file(input_file)

    # Save both outputs
    wavfile.write("am_output_filtered.wav", rate_filtered, output_filtered)
    wavfile.write("am_output_raw.wav", rate_raw, output_raw)
    print("\nSaved: am_output_filtered.wav")
    print("Saved: am_output_raw.wav")

    # Create comparison plots
    fig = plt.figure(figsize=(16, 14))

    # Row 1: Original audio - time domain and frequency
    ax1 = fig.add_subplot(4, 2, 1)
    time_orig = np.arange(len(orig_audio)) / orig_rate
    ax1.plot(time_orig, orig_audio)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Amplitude')
    ax1.set_title('Original Audio - Time Domain')
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(4, 2, 2)
    plot_frequency_spectrum(orig_audio, orig_rate, 'Original Audio - Frequency Spectrum', ax2)

    # Row 2: Raw AM output (no filters)
    ax3 = fig.add_subplot(4, 2, 3)
    output_raw_norm = output_raw.astype(np.float32) / 32767
    time_raw = np.arange(len(output_raw)) / rate_raw
    ax3.plot(time_raw, output_raw_norm)
    ax3.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='Carrier')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Amplitude')
    ax3.set_title('AM Output - NO Filters (Raw)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    ax4 = fig.add_subplot(4, 2, 4)
    plot_frequency_spectrum(output_raw_norm, rate_raw, 'AM Output - NO Filters (Spectrum)', ax4)

    # Row 3: Filtered AM output
    ax5 = fig.add_subplot(4, 2, 5)
    output_filt_norm = output_filtered.astype(np.float32) / 32767
    time_filt = np.arange(len(output_filtered)) / rate_filtered
    ax5.plot(time_filt, output_filt_norm)
    ax5.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='Carrier')
    ax5.set_xlabel('Time (s)')
    ax5.set_ylabel('Amplitude')
    ax5.set_title('AM Output - WITH Filters')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    ax6 = fig.add_subplot(4, 2, 6)
    plot_frequency_spectrum(output_filt_norm, rate_filtered, 'AM Output - WITH Filters (Spectrum)', ax6)

    # Row 4: Zoomed comparison
    zoom_start = 50000
    zoom_end = 55000

    ax7 = fig.add_subplot(4, 2, 7)
    ax7.plot(output_raw[zoom_start:zoom_end], label='Raw', alpha=0.7)
    ax7.plot(output_filtered[zoom_start:zoom_end], label='Filtered', alpha=0.7)
    ax7.axhline(y=16384, color='r', linestyle='--', alpha=0.5, label='Carrier')
    ax7.set_xlabel('Samples')
    ax7.set_ylabel('Amplitude')
    ax7.set_title('Zoomed Comparison - Envelope')
    ax7.legend()
    ax7.grid(True, alpha=0.3)

    # Even more zoomed
    zoom_start2 = 50000
    zoom_end2 = 51000

    ax8 = fig.add_subplot(4, 2, 8)
    ax8.plot(output_raw[zoom_start2:zoom_end2], label='Raw', alpha=0.7)
    ax8.plot(output_filtered[zoom_start2:zoom_end2], label='Filtered', alpha=0.7)
    ax8.axhline(y=16384, color='r', linestyle='--', alpha=0.5, label='Carrier')
    ax8.set_xlabel('Samples')
    ax8.set_ylabel('Amplitude')
    ax8.set_title('Zoomed Comparison - Detail')
    ax8.legend()
    ax8.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('am_comparison.png', dpi=150)
    print("\nSaved: am_comparison.png")

    # Print statistics
    print("\n" + "=" * 50)
    print("STATISTICS")
    print("=" * 50)

    stats_filtered = mod_filtered.get_stats()
    stats_raw = mod_raw.get_stats()

    print(f"\n{'Metric':<25} {'Raw':<15} {'Filtered':<15}")
    print("-" * 55)
    print(f"{'Modulation %':<25} {stats_raw.get('modulation_percent', 0):<15.1f} {stats_filtered.get('modulation_percent', 0):<15.1f}")
    print(f"{'AGC Gain':<25} {'N/A':<15} {stats_filtered.get('agc_gain', 1):<15.2f}x")
    print(f"{'Clipped Samples':<25} {stats_raw.get('clipped_samples', 0):<15} {stats_filtered.get('clipped_samples', 0):<15}")

    # Calculate signal quality metrics
    raw_variance = np.var(output_raw)
    filt_variance = np.var(output_filtered)

    print(f"{'Signal Variance':<25} {raw_variance:<15.0f} {filt_variance:<15.0f}")

    print("\n[DONE] Listen to both WAV files to hear the difference!")
    print("       am_output_raw.wav      - May have noise, hum, inconsistent volume")
    print("       am_output_filtered.wav - Cleaner, consistent volume, speech-optimised")

    return 0


if __name__ == "__main__":
    sys.exit(main())