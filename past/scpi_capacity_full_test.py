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

def generate_multi_carrier(carrier_freqs_khz, message_freq_hz=1000):
    num_samples = 16384
    sample_rate = 125e6
    t = np.arange(num_samples) / sample_rate
    
    message = np.sin(2 * np.pi * message_freq_hz * t)
    combined = np.zeros(num_samples)
    depth = 0.5
    
    for fc_khz in carrier_freqs_khz:
        fc = fc_khz * 1000
        carrier = np.sin(2 * np.pi * fc * t)
        am_signal = (1 + depth * message) * carrier
        combined += am_signal
    
    combined = combined / (len(carrier_freqs_khz) * 1.5)
    combined = np.clip((combined + 1) / 2, 0, 1)
    return combined

def run_test(num_carriers, duration=15):
    all_carriers = [500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600]
    carriers = all_carriers[:num_carriers]
    
    print(f"\n{'='*50}")
    print(f"TEST {num_carriers}/12: {carriers} kHz")
    print(f"{'='*50}")
    
    waveform = generate_multi_carrier(carriers, 1000)
    waveform_str = ",".join([f"{x:.5f}" for x in waveform])
    
    send_scpi(f"SOUR1:TRAC:DATA:DATA {waveform_str}")
    send_scpi("SOUR1:FUNC ARB")
    send_scpi("SOUR1:FREQ:FIX 1")
    send_scpi("SOUR1:VOLT 0.9")
    send_scpi("OUTPUT1:STATE ON")
    
    print(f"Transmitting {num_carriers} carrier(s) for {duration}s...")
    print(">> CHECK CUBICSDR NOW - Clean or weird sidebands?")
    time.sleep(duration)
    
    send_scpi("OUTPUT1:STATE OFF")

# Run all tests 1 → 12
print("CAPACITY TEST: 1 to 12 carriers")
print("Watch CubicSDR — note when weird sidebands appear!\n")

for n in range(1, 13):
    run_test(n, duration=15)
    print("\n--- Next test in 3 seconds ---")
    time.sleep(3)

print("\n" + "="*50)
print("ALL TESTS COMPLETE")
print("="*50)
