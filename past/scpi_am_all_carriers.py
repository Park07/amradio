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

# Generate 1 kHz message envelope (only need to do once)
num_samples = 16384
t = np.linspace(0, 1, num_samples)
message = np.sin(2 * np.pi * 1000 * t)  # 1 kHz message
envelope = 1.0 + 0.5 * message
envelope = envelope / np.max(envelope)
waveform_str = ",".join([f"{x:.5f}" for x in envelope])

# Upload waveform once
print("Uploading 1 kHz message envelope...")
send_scpi(f"SOUR1:TRAC:DATA:DATA {waveform_str}")

# AM Band carriers per spec
carriers_khz = [500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600]

print("\n" + "="*50)
print("AM BAND TEST (per spec)")
print("Message: 1 kHz")
print("Carriers: 500-1600 kHz")
print("="*50)

for freq_khz in carriers_khz:
    freq_hz = freq_khz * 1000
    
    print(f"\n>> Carrier: {freq_khz} kHz + 1 kHz message")
    print(f"   Tune CubicSDR to {freq_khz} kHz")
    
    send_scpi("SOUR1:FUNC ARB")
    send_scpi(f"SOUR1:FREQ:FIX {freq_hz}")
    send_scpi("SOUR1:VOLT 0.9")
    send_scpi("OUTPUT1:STATE ON")
    
    time.sleep(10)
    
    send_scpi("OUTPUT1:STATE OFF")
    time.sleep(2)

print("\n" + "="*50)
print("All 12 carriers tested!")
print("="*50)
