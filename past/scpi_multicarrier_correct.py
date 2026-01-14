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

def generate_multicarrier(carrier_freqs_khz, message_freq=1000, num_carriers=None):
    """
    Generate combined AM signal per Rob's spec:
    Output = sum of [1 + m*sin(message)] * sin(carrier) for each carrier
    """
    num_samples = 16384
    sample_rate = 125e6  # Red Pitaya native rate
    t = np.arange(num_samples) / sample_rate

    # 1 kHz message signal (per spec)
    message = np.sin(2 * np.pi * message_freq * t)

    # Modulation depth
    m = 0.5

    # Combine carriers
    if num_carriers:
        carrier_freqs_khz = carrier_freqs_khz[:num_carriers]

    combined = np.zeros(num_samples)

    for fc_khz in carrier_freqs_khz:
        fc = fc_khz * 1000  # kHz to Hz
        carrier = np.sin(2 * np.pi * fc * t)
        am_signal = (1 + m * message) * carrier
        combined += am_signal

    # Normalize to 0-1 for DAC
    combined = combined / np.max(np.abs(combined))
    combined = (combined + 1) / 2

    return combined

# AM Band carriers per spec
all_carriers = [500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600]

print("="*50)
print("MULTI-CARRIER CAPACITY TEST (Rob's Spec)")
print("Carriers: 500-1600 kHz")
print("Message: 1 kHz")
print("Formula: sum of [1 + m*sin(1kHz)] * sin(carrier)")
print("="*50)

for n in range(1, 13):
    carriers = all_carriers[:n]

    print(f"\nTEST {n}/12: {carriers} kHz")

    waveform = generate_multicarrier(all_carriers, 1000, n)
    waveform_str = ",".join([f"{x:.5f}" for x in waveform])

    send_scpi(f"SOUR1:TRAC:DATA:DATA {waveform_str}")
    send_scpi("SOUR1:FUNC ARB")
    send_scpi("SOUR1:FREQ:FIX 7629")  # 125MHz / 16384 = 7629 Hz for native playback
    send_scpi("SOUR1:VOLT 0.9")
    send_scpi("OUTPUT1:STATE ON")

    print(f"Transmitting... Check CubicSDR at {carriers} kHz")
    print("Look for: Clean spikes vs weird sidebands")
    time.sleep(15)

    send_scpi("OUTPUT1:STATE OFF")
    time.sleep(2)

print("\n" + "="*50)
print("TEST COMPLETE")
print("="*50)
