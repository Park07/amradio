#!/usr/bin/env python3
"""
WAV to BRAM Converter
UGL Tunnel AM Break-In System

Converts WAV audio files to Verilog-compatible .mem files
for loading into FPGA Block RAM.

Usage:
    python wav_to_bram.py emergency.wav emergency.mem
    python wav_to_bram.py --help

Output format:
    Hex file with 14-bit signed samples (for Red Pitaya DAC)
    Compatible with Verilog $readmemh()
"""

import wave
import struct
import argparse
import sys
from pathlib import Path


def wav_to_mem(
    wav_path: str,
    mem_path: str,
    max_samples: int = 16384,
    target_rate: int = 48000,
    bit_depth: int = 14
) -> dict:
    """
    Convert WAV file to BRAM .mem format.

    Args:
        wav_path: Input WAV file path
        mem_path: Output .mem file path
        max_samples: Maximum samples to include (BRAM limit)
        target_rate: Target sample rate (will resample if different)
        bit_depth: Output bit depth (14 for Red Pitaya DAC)

    Returns:
        Dictionary with conversion statistics
    """
    # Read WAV file
    with wave.open(wav_path, 'rb') as wav:
        n_channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        frame_rate = wav.getframerate()
        n_frames = wav.getnframes()

        print(f"Input: {wav_path}")
        print(f"  Channels: {n_channels}")
        print(f"  Sample width: {sample_width} bytes ({sample_width * 8}-bit)")
        print(f"  Frame rate: {frame_rate} Hz")
        print(f"  Total frames: {n_frames}")
        print(f"  Duration: {n_frames / frame_rate:.2f} seconds")

        # Read all frames
        raw_data = wav.readframes(n_frames)

    # Parse samples based on sample width
    if sample_width == 1:
        # 8-bit unsigned
        fmt = f"{len(raw_data)}B"
        samples = [s - 128 for s in struct.unpack(fmt, raw_data)]  # Convert to signed
    elif sample_width == 2:
        # 16-bit signed (most common)
        fmt = f"<{len(raw_data) // 2}h"
        samples = list(struct.unpack(fmt, raw_data))
    elif sample_width == 4:
        # 32-bit signed
        fmt = f"<{len(raw_data) // 4}i"
        samples = list(struct.unpack(fmt, raw_data))
    else:
        raise ValueError(f"Unsupported sample width: {sample_width}")

    # If stereo, convert to mono (average channels)
    if n_channels == 2:
        samples = [(samples[i] + samples[i + 1]) // 2
                   for i in range(0, len(samples), 2)]
        print(f"  Converted stereo to mono")
    elif n_channels > 2:
        # Take first channel only
        samples = samples[::n_channels]
        print(f"  Extracted first channel from {n_channels} channels")

    # Resample if needed (simple decimation/interpolation)
    if frame_rate != target_rate:
        ratio = frame_rate / target_rate
        new_samples = []
        i = 0.0
        while int(i) < len(samples) and len(new_samples) < max_samples:
            idx = int(i)
            new_samples.append(samples[idx])
            i += ratio
        samples = new_samples
        print(f"  Resampled from {frame_rate} Hz to {target_rate} Hz")

    # Limit to max_samples
    if len(samples) > max_samples:
        samples = samples[:max_samples]
        print(f"  Truncated to {max_samples} samples (BRAM limit)")

    # Convert to target bit depth
    # Input is 16-bit (-32768 to 32767), output is 14-bit (-8192 to 8191)
    if sample_width == 2:
        # 16-bit to 14-bit: shift right by 2
        samples_out = [s >> 2 for s in samples]
    elif sample_width == 1:
        # 8-bit to 14-bit: shift left by 6
        samples_out = [s << 6 for s in samples]
    else:
        # Normalize to 14-bit range
        max_val = max(abs(min(samples)), abs(max(samples)))
        if max_val > 0:
            scale = 8191 / max_val
            samples_out = [int(s * scale) for s in samples]
        else:
            samples_out = samples

    # Clamp to 14-bit signed range
    samples_out = [max(-8192, min(8191, s)) for s in samples_out]

    # Write .mem file (hex format for Verilog $readmemh)
    with open(mem_path, 'w') as f:
        f.write(f"// Generated from {Path(wav_path).name}\n")
        f.write(f"// Samples: {len(samples_out)}, Rate: {target_rate} Hz\n")
        f.write(f"// Duration: {len(samples_out) / target_rate * 1000:.1f} ms\n")
        f.write(f"// Format: 14-bit signed, hex (2's complement for negative)\n\n")

        for i, sample in enumerate(samples_out):
            # Convert signed to unsigned for hex representation
            if sample < 0:
                sample = sample + 16384  # 2's complement for 14-bit
            f.write(f"{sample:04X}\n")

    duration_ms = len(samples_out) / target_rate * 1000

    print(f"\nOutput: {mem_path}")
    print(f"  Samples: {len(samples_out)}")
    print(f"  Duration: {duration_ms:.1f} ms")
    print(f"  BRAM usage: {len(samples_out) * 2} bytes ({len(samples_out) * 2 / 1024:.1f} KB)")

    return {
        "input_file": wav_path,
        "output_file": mem_path,
        "samples": len(samples_out),
        "duration_ms": duration_ms,
        "bram_bytes": len(samples_out) * 2
    }


def combine_messages(
    wav_files: list,
    mem_path: str,
    max_samples_per_msg: int = 16384
) -> dict:
    """
    Combine multiple WAV files into a single .mem file with message table.

    Args:
        wav_files: List of (message_id, wav_path) tuples
        mem_path: Output .mem file path
        max_samples_per_msg: Max samples per message

    Returns:
        Dictionary with message offsets for Verilog
    """
    all_samples = []
    message_table = []

    for msg_id, wav_path in wav_files:
        print(f"\n--- Processing message {msg_id}: {wav_path} ---")

        # Convert WAV
        temp_mem = f"/tmp/temp_{msg_id}.mem"
        result = wav_to_mem(wav_path, temp_mem, max_samples=max_samples_per_msg)

        # Read back samples
        with open(temp_mem, 'r') as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith('//')]

        start_addr = len(all_samples)
        samples = [int(line, 16) for line in lines]

        message_table.append({
            "id": msg_id,
            "start": start_addr,
            "length": len(samples),
            "duration_ms": result["duration_ms"]
        })

        all_samples.extend(samples)

    # Write combined .mem file
    with open(mem_path, 'w') as f:
        f.write(f"// Combined message file\n")
        f.write(f"// Total samples: {len(all_samples)}\n")
        f.write(f"// Message table:\n")
        for msg in message_table:
            f.write(f"//   {msg['id']}: start={msg['start']}, len={msg['length']}, {msg['duration_ms']:.1f}ms\n")
        f.write("\n")

        for sample in all_samples:
            f.write(f"{sample:04X}\n")

    print(f"\n=== Combined output: {mem_path} ===")
    print(f"Total samples: {len(all_samples)}")
    print(f"Total BRAM: {len(all_samples) * 2 / 1024:.1f} KB")
    print("\nMessage Table (for Verilog):")
    for msg in message_table:
        print(f"  {msg['id']}: START={msg['start']}, LEN={msg['length']}")

    return {
        "output_file": mem_path,
        "total_samples": len(all_samples),
        "messages": message_table
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convert WAV files to BRAM .mem format for FPGA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Convert single file
    python wav_to_bram.py emergency.wav emergency.mem

    # Convert with custom settings
    python wav_to_bram.py voice.wav voice.mem --max-samples 32768 --rate 44100

    # Combine multiple messages
    python wav_to_bram.py --combine messages.mem \\
        test:test_tone.wav \\
        emergency:emergency.wav \\
        fire:fire_alert.wav
"""
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="Input WAV file (or message:file pairs with --combine)"
    )

    parser.add_argument(
        "output",
        nargs="?",
        help="Output .mem file"
    )

    parser.add_argument(
        "--combine",
        action="store_true",
        help="Combine multiple messages: output msg1:file1.wav msg2:file2.wav ..."
    )

    parser.add_argument(
        "--max-samples",
        type=int,
        default=16384,
        help="Maximum samples per message (default: 16384)"
    )

    parser.add_argument(
        "--rate",
        type=int,
        default=48000,
        help="Target sample rate in Hz (default: 48000)"
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="Additional msg:file pairs for --combine mode"
    )

    args = parser.parse_args()

    if args.combine:
        # Combine mode: output msg1:file1 msg2:file2 ...
        if not args.input:
            parser.error("Output file required for --combine mode")

        output_file = args.input
        pairs = []

        for item in [args.output] + args.files if args.output else args.files:
            if item and ':' in item:
                msg_id, wav_path = item.split(':', 1)
                pairs.append((msg_id, wav_path))

        if not pairs:
            parser.error("No message:file pairs provided")

        combine_messages(pairs, output_file, args.max_samples)

    else:
        # Single file mode
        if not args.input or not args.output:
            parser.error("Both input and output files required")

        wav_to_mem(
            args.input,
            args.output,
            max_samples=args.max_samples,
            target_rate=args.rate
        )


if __name__ == "__main__":
    main()