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

# Generate 1 kHz message as envelope
num_samples = 16384
t = np.linspace(0, 1, num_samples)  # 1 second worth
message_freq = 1000  # 1 kHz per spec

# 1 kHz message signal
message = np.sin(2 * np.pi * message_freq * t)

# AM envelope: 1 + 0.5 * message (50% modulation depth)
envelope = 1.0 + 0.5 * message

# Normalize to 0-1
envelope = envelope / np.max(envelope)

waveform_str = ",".join([f"{x:.5f}" for x in envelope])

print("Carrier: 500 kHz")
print("Message: 1 kHz (AM modulated)")
print()

send_scpi(f"SOUR1:TRAC:DATA:DATA {waveform_str}")
send_scpi("SOUR1:FUNC ARB")
send_scpi("SOUR1:FREQ:FIX 500000")  # 500 kHz carrier
send_scpi("SOUR1:VOLT 0.9")
send_scpi("OUTPUT1:STATE ON")

print("Transmitting for 20 seconds...")
print(">> Tune CubicSDR to 500 kHz — should see sidebands at ±1 kHz")
time.sleep(20)

send_scpi("OUTPUT1:STATE OFF")
print("Done!")
