import socket
import struct
import numpy as np
import time

RED_PITAYA_IP = "192.168.0.100"
HPSDR_PORT = 1024
SAMPLE_RATE = 48000
TX_FREQ = 10000000  # 700 kHz

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2)

# HPSDR Protocol constants
SYNC = 0xEFFE

def send_command(cmd_type, c0=0, c1=0, c2=0, c3=0, c4=0):
    """Send HPSDR command packet"""
    packet = struct.pack('>HB', SYNC, cmd_type)
    packet += bytes([c0, c1, c2, c3, c4])
    packet += bytes(63 - len(packet))  # Pad to 63 bytes
    sock.sendto(packet, (RED_PITAYA_IP, HPSDR_PORT))

def start_tx():
    """Start HPSDR in TX mode"""
    # Start command: 0x04, with TX enabled
    # C0: MOX bit (bit 0) = 1 for transmit
    send_command(0x04, c0=0x01)
    print("Sent start TX command")

def stop_tx():
    """Stop transmission"""
    send_command(0x04, c0=0x00)
    print("Stopped TX")

def set_frequency(freq_hz):
    """Set TX frequency"""
    # Frequency is sent as 4 bytes, big-endian
    f = int(freq_hz)
    c1 = (f >> 24) & 0xFF
    c2 = (f >> 16) & 0xFF
    c3 = (f >> 8) & 0xFF
    c4 = f & 0xFF
    send_command(0x02, c0=0x02, c1=c1, c2=c2, c3=c3, c4=c4)  # TX freq
    print(f"Set TX frequency to {freq_hz} Hz")

def generate_am_tone(duration_sec, audio_freq=1000):
    """Generate AM modulated IQ samples"""
    t = np.arange(int(SAMPLE_RATE * duration_sec)) / SAMPLE_RATE

    # Audio tone (modulating signal)
    audio = np.sin(2 * np.pi * audio_freq * t)

    # AM modulation: carrier * (1 + m*audio), m=0.5
    modulation_depth = 0.5
    envelope = 1.0 + modulation_depth * audio

    # IQ samples (carrier is at baseband, so I=envelope, Q=0)
    i_samples = (envelope * 32767 * 0.5).astype(np.int16)
    q_samples = np.zeros_like(i_samples)

    return i_samples, q_samples

def send_iq_data(i_samples, q_samples):
    """Send IQ samples using HPSDR protocol"""
    # HPSDR uses 504-byte USB frames with 63-byte packets
    # Each packet: sync(2) + type(1) + endpoint(1) + sequence(4) + data(504)

    idx = 0
    sequence = 0
    samples_per_packet = 126  # 504 bytes / 4 bytes per IQ pair

    while idx < len(i_samples):
        # Build data packet
        chunk_i = i_samples[idx:idx + samples_per_packet]
        chunk_q = q_samples[idx:idx + samples_per_packet]

        # Interleave I and Q as 16-bit samples
        iq_data = np.empty(len(chunk_i) * 2, dtype=np.int16)
        iq_data[0::2] = chunk_i
        iq_data[1::2] = chunk_q

        # Build HPSDR data packet
        header = struct.pack('>HBB I', SYNC, 0x01, 0x02, sequence)
        packet = header + iq_data.tobytes()

        # Pad to 512 bytes if needed
        if len(packet) < 512:
            packet += bytes(512 - len(packet))

        sock.sendto(packet, (RED_PITAYA_IP, HPSDR_PORT))

        idx += samples_per_packet
        sequence += 1

        # Pace the transmission
        time.sleep(samples_per_packet / SAMPLE_RATE * 0.8)

    return sequence

# Main
print("HPSDR AM Transmitter")
print("=" * 40)

# Set frequency
set_frequency(TX_FREQ)
time.sleep(0.1)

# Start TX
start_tx()
time.sleep(0.1)

# Generate and send 5 seconds of 1kHz AM tone
print(f"Transmitting 1kHz tone at {TX_FREQ/1000} kHz for 5 seconds...")
i_samples, q_samples = generate_am_tone(10.0, audio_freq=1000)
packets = send_iq_data(i_samples, q_samples)

print(f"Sent {packets} packets")

# Stop TX
stop_tx()
sock.close()
print("Done!")

