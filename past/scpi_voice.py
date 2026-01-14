import socket
import time
import numpy as np
import librosa

RP_IP = "192.168.0.100"
RP_PORT = 5000

def send_scpi(cmd):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((RP_IP, RP_PORT))
    sock.send((cmd + "\r\n").encode())
    time.sleep(0.1)
    sock.close()

def transmit_voice(audio_file, freq_hz=10000000, duration=20):
    print(f"Loading {audio_file}...")
    
    # Load audio with librosa (handles any format)
    audio, sr = librosa.load(audio_file, sr=None, mono=True)
    print(f"  Original: {len(audio)} samples at {sr} Hz")
    print(f"  Duration: {len(audio)/sr:.2f} seconds")
    
    # Take first 0.3 seconds (SCPI buffer limit)
    samples_needed = int(0.3 * sr)
    audio_clip = audio[:samples_needed]
    print(f"  Using first {len(audio_clip)} samples ({len(audio_clip)/sr:.2f}s)")
    
    # Resample to fit exactly 16384 samples
    target_samples = 16384
    audio_resampled = librosa.resample(audio_clip, orig_sr=sr, target_sr=int(target_samples / 0.3))
    audio_resampled = audio_resampled[:target_samples]
    
    # Pad if needed
    if len(audio_resampled) < target_samples:
        audio_resampled = np.pad(audio_resampled, (0, target_samples - len(audio_resampled)))
    
    print(f"  Resampled to {len(audio_resampled)} samples")
    
    # Normalize to -1 to +1
    audio_resampled = audio_resampled / (np.max(np.abs(audio_resampled)) + 1e-10)
    
    # AM modulation
    depth = 0.5
    carrier = 0.5
    envelope = carrier * (1.0 + depth * audio_resampled)
    waveform = np.clip(envelope, 0, 1)
    
    print(f"  AM modulated: {waveform.min():.2f} to {waveform.max():.2f}")
    
    # Convert to Red Pitaya format (comma-separated string)
    waveform_str = ",".join([f"{x:.5f}" for x in waveform])
    
    print("Uploading to Red Pitaya...")
    send_scpi(f"SOUR1:TRAC:DATA:DATA {waveform_str}")
    send_scpi("SOUR1:FUNC ARB")
    send_scpi(f"SOUR1:FREQ:FIX {freq_hz}")
    send_scpi("SOUR1:VOLT 0.9")
    send_scpi("OUTPUT1:STATE ON")
    
    print(f"Transmitting at {freq_hz/1e6} MHz for {duration}s (voice loops)...")
    time.sleep(duration)
    
    send_scpi("OUTPUT1:STATE OFF")
    print("Done!")

if __name__ == "__main__":
    import sys
    audio_file = sys.argv[1] if len(sys.argv) > 1 else "voice_test_5s.wav"
    transmit_voice(audio_file, 10000000, 20)
