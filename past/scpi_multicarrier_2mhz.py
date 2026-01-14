import socket
import time
import numpy as np

RP_IP = "192.168.0.100"
RP_PORT = 5000

def send_scpi(cmd):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((RP_IP, RP_PORT))
    sock.send((cmd + "\r\n").encode())
    time.sleep(0.1)
    sock.close()

def generate_multicarrier(carrier_freqs_mhz, num_carriers):
    num_samples = 16384
    sample_rate = 125e6
    t = np.arange(num_samples) / sample_rate

    message = np.sin(2 * np.pi * 1000 * t)  # 1 kHz message
    m = 0.5

    carriers = carrier_freqs_mhz[:num_carriers]
    combined = np.zeros(num_samples)

    for fc_mhz in carriers:
        fc = fc_mhz * 1e6
        carrier = np.sin(2 * np.pi * fc * t)
        am_signal = (1 + m * message) * carrier
        combined += am_signal

    combined = combined / np.max(np.abs(combined))
    combined = (combined + 1) / 2
    return combined

# 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0, 4.2 MHz
all_carriers = [2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0, 4.2]

print("="*50)
print("MULTI-CARRIER TEST (2-4 MHz)")
print("="*50)

for n in range(1, 13):
    carriers = all_carriers[:n]

    print(f"\nTEST {n}/12: {carriers} MHz")

    waveform = generate_multicarrier(all_carriers, n)
    waveform_str = ",".join([f"{x:.5f}" for x in waveform])

    send_scpi(f"SOUR1:TRAC:DATA:DATA {waveform_str}")
    send_scpi("SOUR1:FUNC ARB")
    send_scpi("SOUR1:FREQ:FIX 7629")
    send_scpi("SOUR1:VOLT 0.9")
    send_scpi("OUTPUT1:STATE ON")

    print(f">> Look for {n} spike(s)")
    time.sleep(15)

    send_scpi("OUTPUT1:STATE OFF")
    time.sleep(2)

print("\nDONE")
