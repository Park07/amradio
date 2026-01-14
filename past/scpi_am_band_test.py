import socket
import time

RP_IP = "192.168.0.100"
RP_PORT = 5000

def send_scpi(cmd):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((RP_IP, RP_PORT))
    sock.send((cmd + "\r\n").encode())
    time.sleep(0.1)
    sock.close()

freq = 1000000  # 1000 kHz = 1 MHz (in AM band)

print(f"Transmitting at {freq/1000} kHz (AM band)...")
send_scpi("SOUR1:FUNC SINE")
send_scpi(f"SOUR1:FREQ:FIX {freq}")
send_scpi("SOUR1:VOLT 0.9")
send_scpi("OUTPUT1:STATE ON")

print("Running for 30 seconds...")
print(">> Tune CubicSDR to 1000 kHz (1 MHz)")
time.sleep(30)

send_scpi("OUTPUT1:STATE OFF")
print("Done!")
