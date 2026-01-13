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
    """
    Generate combined AM signal with multiple carriers
    Each carrier is AM modulated with 1 kHz message
    """
    num_samples = 16384
    sample_rate = 125e6  # Red Pitaya DAC rate
    
    t = np.arange(num_samples) / sample_rate
    
    # 1 kHz message signal
    message = np.sin(2 * np.pi * message_freq_hz * t)
    
    # Combine all AM carriers
    combined = np.zeros(num_samples)
    depth = 0.5  # 50% modulation
    
    for fc_khz in carrier_freqs_khz:
        fc = fc_khz * 1000  # Convert to Hz
        carrier = np.sin(2 * np.pi * fc * t)
        am_signal = (1 + depth * message) * carrier
        combined += am_signal
    
    # Normalize to 0-1 for DAC
    combined = combined / (len(carrier_freqs_khz) * 1.5)  # Scale by number of carriers
    combined = np.clip((combined + 1) / 2, 0, 1)
    
    return combined

def run_capacity_test(num_carriers):
    # Carrier frequencies: 500, 700, 900, 1100, 1300, 1500 kHz
    all_carriers = [500, 700, 900, 1100, 1300, 1500, 1700]
    carriers = all_carriers[:num_carriers]
    
    print("=" * 50)
    print(f"CAPACITY TEST: {num_carriers} carrier(s)")
    print(f"Carriers: {carriers} kHz")
    print(f"Message: 1 kHz")
    print("=" * 50)
    
    waveform = generate_multi_carrier(carriers, 1000)
    
    print(f"Waveform samples: {len(waveform)}")
    print(f"Range: {waveform.min():.3f} to {waveform.max():.3f}")
    
    waveform_str = ",".join([f"{x:.5f}" for x in waveform])
    
    print("Uploading...")
    send_scpi(f"SOUR1:TRAC:DATA:DATA {waveform_str}")
    send_scpi("SOUR1:FUNC ARB")
    send_scpi("SOUR1:FREQ:FIX 1")
    send_scpi("SOUR1:VOLT 0.9")
    send_scpi("OUTPUT1:STATE ON")
    
    print(f"\nTRANSMITTING - Check CubicSDR at: {carriers} kHz")
    print("Look for:")
    print("  - Clean spikes at each frequency")
    print("  - Clear ±1kHz sidebands")
    print("  - NO unexpected sidebands = PASS")
    print("  - Weird extra sidebands = FAIL (capacity limit)\n")
    
    time.sleep(30)
    
    send_scpi("OUTPUT1:STATE OFF")
    print("Done!")

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_capacity_test(n)
