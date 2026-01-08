#!/usr/bin/env python3
"""
AM Modulator for Tunnel Emergency Broadcast System
===================================================
Production-ready AM modulation with proper DSP filtering.

Features:
- Highpass filter (removes DC offset, rumble)
- Bandpass filter (speech frequencies only)
- Automatic Gain Control (AGC)
- Anti-aliasing filter (clean resampling)
- Hard limiter (prevents overmodulation)
- Configurable parameters
- Auto-adapts to low sample rate files

Usage:
    python3 am_modulator.py input.wav output.wav
    python3 am_modulator.py input.wav output.wav --freq 700000 --depth 0.8

Author: UGL Tunnel Radio Project
"""

import argparse
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, filtfilt, resample
import sys


class AMModulator:
    """
    Professional AM modulator with DSP filtering chain.
    """

    def __init__(
        self,
        output_sample_rate: int = 100000,
        carrier_level: float = 0.5,
        modulation_depth: float = 0.8,
        highpass_freq: float = 50.0,
        bandpass_low: float = 300.0,
        bandpass_high: float = 4000.0,
        agc_target: float = 0.9,
        enable_filters: bool = True,
        verbose: bool = True
    ):
        """
        Initialise AM modulator with configurable parameters.

        Args:
            output_sample_rate: Target sample rate for Red Pitaya (Hz)
            carrier_level: Carrier amplitude (0-1), typically 0.5
            modulation_depth: How much audio affects carrier (0-1), typically 0.8
            highpass_freq: Remove frequencies below this (Hz)
            bandpass_low: Lower bound of speech frequencies (Hz)
            bandpass_high: Upper bound of speech frequencies (Hz)
            agc_target: Target level after AGC (0-1)
            enable_filters: Set False to bypass all filtering (for comparison)
            verbose: Print processing info
        """
        self.output_sample_rate = output_sample_rate
        self.carrier_level = carrier_level
        self.modulation_depth = modulation_depth
        self.highpass_freq = highpass_freq
        self.bandpass_low = bandpass_low
        self.bandpass_high = bandpass_high
        self.agc_target = agc_target
        self.enable_filters = enable_filters
        self.verbose = verbose

        # Processing stats
        self.stats = {}

    def _log(self, msg: str):
        """Print if verbose mode enabled."""
        if self.verbose:
            print(f"[AM] {msg}")

    def _butter_filter(
        self,
        data: np.ndarray,
        cutoff,
        fs: float,
        btype: str = 'low',
        order: int = 4
    ) -> np.ndarray:
        """
        Apply Butterworth filter.

        Args:
            data: Input signal
            cutoff: Cutoff frequency (Hz) or [low, high] for bandpass
            fs: Sample rate (Hz)
            btype: 'low', 'high', or 'band'
            order: Filter order (higher = sharper cutoff)

        Returns:
            Filtered signal
        """
        nyq = fs / 2

        # Normalise cutoff to Nyquist
        if btype == 'band':
            normal_cutoff = [c / nyq for c in cutoff]
            # Ensure cutoffs are valid
            normal_cutoff = [max(0.001, min(0.999, c)) for c in normal_cutoff]
        else:
            normal_cutoff = cutoff / nyq
            normal_cutoff = max(0.001, min(0.999, normal_cutoff))

        b, a = butter(order, normal_cutoff, btype=btype)
        return filtfilt(b, a, data)

    def _apply_highpass(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Remove DC offset and low-frequency rumble."""
        if self.highpass_freq >= sample_rate / 2:
            self._log(f"  Skipping highpass (cutoff too high for sample rate)")
            return audio

        self._log(f"  Highpass filter: removing below {self.highpass_freq}Hz")
        return self._butter_filter(audio, self.highpass_freq, sample_rate, btype='high', order=2)

    def _apply_bandpass(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Keep only speech frequencies. Auto-adapts to low sample rate files."""
        nyquist = sample_rate / 2

        # Auto-adapt bandpass for low sample rate files
        low = max(self.bandpass_low, 20)  # Minimum 20Hz
        high = min(self.bandpass_high, nyquist * 0.9)  # 90% of Nyquist max

        # Need at least 200Hz bandwidth for meaningful filtering
        if high - low < 200:
            self._log(f"  Skipping bandpass (sample rate too low: {sample_rate}Hz)")
            return audio

        if low >= high:
            self._log(f"  Skipping bandpass (invalid frequency range)")
            return audio

        self._log(f"  Bandpass filter: keeping {low:.0f}Hz - {high:.0f}Hz")
        return self._butter_filter(audio, [low, high], sample_rate, btype='band', order=4)

    def _apply_agc(self, audio: np.ndarray) -> np.ndarray:
        """Automatic Gain Control - normalise to target level."""
        peak = np.max(np.abs(audio))

        # Always apply gain if there's any signal
        if peak < 1e-10:
            self._log(f"  AGC: No signal detected (peak={peak:.10f})")
            return audio

        gain = self.agc_target / peak

        if peak < 0.01:
            self._log(f"  AGC: Weak signal (peak={peak:.6f}), boosting with gain={gain:.1f}x")
        else:
            self._log(f"  AGC: peak={peak:.4f}, applying gain={gain:.2f}x")

        self.stats['agc_gain'] = gain
        return audio * gain

    def _apply_antialias(self, audio: np.ndarray, orig_rate: int) -> np.ndarray:
        """Anti-aliasing filter before resampling."""
        target_nyquist = self.output_sample_rate / 2
        cutoff = target_nyquist * 0.8  # 80% of Nyquist

        if cutoff >= orig_rate / 2:
            self._log(f"  Skipping anti-alias (not needed for upsampling)")
            return audio

        self._log(f"  Anti-alias filter: cutoff at {cutoff:.0f}Hz")
        return self._butter_filter(audio, cutoff, orig_rate, btype='low', order=6)

    def _apply_limiter(self, audio: np.ndarray) -> np.ndarray:
        """Hard limiter to prevent overmodulation."""
        before_clip = np.sum(np.abs(audio) > 1.0)
        audio = np.clip(audio, -1.0, 1.0)

        if before_clip > 0:
            self._log(f"  Limiter: clipped {before_clip} samples")
            self.stats['clipped_samples'] = before_clip
        else:
            self._log(f"  Limiter: no clipping needed")
            self.stats['clipped_samples'] = 0

        return audio

    def _resample(self, audio: np.ndarray, orig_rate: int) -> np.ndarray:
        """Resample to target rate."""
        num_samples = int(len(audio) * self.output_sample_rate / orig_rate)
        self._log(f"  Resampling: {orig_rate}Hz → {self.output_sample_rate}Hz ({len(audio)} → {num_samples} samples)")

        return resample(audio, num_samples).astype(np.float32)

    def _am_modulate(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply AM modulation formula.

        AM formula: output = carrier * (1 + depth * audio)

        Where:
            - carrier: DC offset (carrier level)
            - depth: modulation depth (0-1)
            - audio: normalised audio signal (-1 to 1)
        """
        self._log(f"  AM modulation: carrier={self.carrier_level}, depth={self.modulation_depth}")

        modulated = self.carrier_level * (1.0 + self.modulation_depth * audio)

        # Calculate actual modulation percentage
        min_val = np.min(modulated)
        max_val = np.max(modulated)
        mod_percent = ((max_val - min_val) / (2 * self.carrier_level)) * 100

        self._log(f"  Output range: {min_val:.4f} to {max_val:.4f} ({mod_percent:.1f}% modulation)")
        self.stats['modulation_percent'] = mod_percent

        return modulated

    def process_file(self, input_path: str) -> tuple[np.ndarray, int]:
        """
        Process an audio file through the full AM modulation chain.

        Args:
            input_path: Path to input WAV file

        Returns:
            Tuple of (modulated_signal, sample_rate)
        """
        self._log(f"Loading: {input_path}")

        # Load audio file
        try:
            orig_rate, audio = wavfile.read(input_path)
        except Exception as e:
            raise ValueError(f"Failed to load audio file: {e}")

        self._log(f"Input: {orig_rate}Hz, {len(audio)} samples, {audio.dtype}")
        self.stats['input_rate'] = orig_rate
        self.stats['input_samples'] = len(audio)

        # Convert to mono if stereo
        if len(audio.shape) > 1:
            self._log(f"  Converting stereo to mono")
            audio = audio.mean(axis=1)

        # Convert to float32 and normalise
        audio = audio.astype(np.float32)

        # Normalise based on dtype - handle uint8 (0-255) properly
        if audio.min() >= 0 and audio.max() <= 255 and audio.max() > 1:
            # uint8 format: 0-255, centre is 128
            audio = (audio - 128) / 128.0
            self._log(f"  Detected uint8 format, centring around 128")
        elif audio.max() > 1.0:
            max_val = np.iinfo(np.int16).max if audio.max() < 32768 else np.iinfo(np.int32).max
            audio = audio / max_val

        self.stats['input_peak'] = np.max(np.abs(audio))
        self._log(f"  Normalised peak: {self.stats['input_peak']:.4f}")

        # Apply DSP chain
        if self.enable_filters:
            self._log("Applying DSP filters:")

            # 1. Highpass - remove DC and rumble
            audio = self._apply_highpass(audio, orig_rate)

            # 2. Bandpass - speech frequencies only
            audio = self._apply_bandpass(audio, orig_rate)

            # 3. AGC - normalise level
            audio = self._apply_agc(audio)

            # 4. Anti-alias - before resampling
            audio = self._apply_antialias(audio, orig_rate)

            # 5. Resample to target rate
            audio = self._resample(audio, orig_rate)

            # 6. Final limiter
            audio = self._apply_limiter(audio)
        else:
            self._log("Filters DISABLED - raw processing only")
            # Basic normalise
            peak = np.max(np.abs(audio))
            if peak > 0:
                audio = audio / peak
            audio = self._resample(audio, orig_rate)
            audio = np.clip(audio, -1.0, 1.0)

        # 7. AM modulation
        self._log("Applying AM modulation:")
        modulated = self._am_modulate(audio)

        # 8. Final output clip (ensure 0-1 range)
        modulated = np.clip(modulated, 0, 1)

        # 9. Convert to int16
        output = (modulated * 32767).astype(np.int16)

        self.stats['output_samples'] = len(output)
        self.stats['output_rate'] = self.output_sample_rate
        self._log(f"Output: {self.output_sample_rate}Hz, {len(output)} samples")

        return output, self.output_sample_rate

    def save_output(self, output: np.ndarray, output_path: str):
        """Save modulated signal to WAV file."""
        wavfile.write(output_path, self.output_sample_rate, output)
        self._log(f"Saved: {output_path}")

    def get_stats(self) -> dict:
        """Return processing statistics."""
        return self.stats.copy()


def main():
    parser = argparse.ArgumentParser(
        description="AM Modulator for Tunnel Emergency Broadcast System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("input", help="Input WAV file")
    parser.add_argument("output", help="Output WAV file")

    parser.add_argument("--rate", type=int, default=100000,
                        help="Output sample rate (Hz)")
    parser.add_argument("--carrier", type=float, default=0.5,
                        help="Carrier level (0-1)")
    parser.add_argument("--depth", type=float, default=0.8,
                        help="Modulation depth (0-1)")
    parser.add_argument("--highpass", type=float, default=50,
                        help="Highpass filter frequency (Hz)")
    parser.add_argument("--bandpass-low", type=float, default=300,
                        help="Bandpass lower frequency (Hz)")
    parser.add_argument("--bandpass-high", type=float, default=4000,
                        help="Bandpass upper frequency (Hz)")
    parser.add_argument("--agc-target", type=float, default=0.9,
                        help="AGC target level (0-1)")
    parser.add_argument("--no-filters", action="store_true",
                        help="Disable all filtering (raw AM only)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress output messages")

    args = parser.parse_args()

    # Create modulator
    modulator = AMModulator(
        output_sample_rate=args.rate,
        carrier_level=args.carrier,
        modulation_depth=args.depth,
        highpass_freq=args.highpass,
        bandpass_low=args.bandpass_low,
        bandpass_high=args.bandpass_high,
        agc_target=args.agc_target,
        enable_filters=not args.no_filters,
        verbose=not args.quiet
    )

    # Process
    try:
        output, rate = modulator.process_file(args.input)
        modulator.save_output(output, args.output)

        if not args.quiet:
            stats = modulator.get_stats()
            print(f"\n[DONE] Modulation: {stats.get('modulation_percent', 0):.1f}%")
            print(f"       AGC gain: {stats.get('agc_gain', 1):.2f}x")
            print(f"       Clipped samples: {stats.get('clipped_samples', 0)}")

        return 0

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())