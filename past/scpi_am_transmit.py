import socket
import time
import numpy as np

RP_IP = "192.168.0.100"
RP_PORT = 5000

def send_scpi(cmd):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((RP_IP, RP_PORT))
    sock.send((cmd + "\r\n").encode())
    time.sleep(0.1)
    sock.close()

def transmit_am(freq_hz=10000000, audio_freq=1000, duration=10):
    print(f"Generating AM waveform with {audio_freq}Hz tone...")

    # Generate AM waveform
    samples = 16384
    t = np.linspace(0, samples/16384, samples)
    audio = np.sin(2 * np.pi * audio_freq * t * 10)  # Audio tone
    depth = 0.5
    envelope = 1.0 + depth * audio
    waveform = envelope / np.max(envelope)  # Normalise 0-1

    # Convert to comma-separated string
    waveform_str = ",".join([f"{x:.4f}" for x in waveform])

    print("Uploading waveform to Red Pitaya...")
    send_scpi(f"SOUR1:TRAC:DATA:DATA {waveform_str}")
    send_scpi("SOUR1:FUNC ARB")
    send_scpi(f"SOUR1:FREQ:FIX {freq_hz}")
    send_scpi("SOUR1:VOLT 0.9")
    send_scpi("OUTPUT1:STATE ON")

    print(f"Transmitting AM at {freq_hz/1e6} MHz for {duration} seconds...")
    time.sleep(duration)

    send_scpi("OUTPUT1:STATE OFF")
    print("Done!")

if __name__ == "__main__":
    transmit_am(10000000, 1000, 10)

# for proof of concept
# we have uniform wave already
# try arbitrary waveform
# combine like two sine functions or something
