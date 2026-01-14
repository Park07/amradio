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

print("Carrier: 500 kHz (no message yet)")
send_scpi("SOUR1:FUNC SINE")
send_scpi("SOUR1:FREQ:FIX 500000")  # 500 kHz carrier
send_scpi("SOUR1:VOLT 0.9")
send_scpi("OUTPUT1:STATE ON")

print("Transmitting for 20 seconds...")
print(">> Tune CubicSDR to 500 kHz")
time.sleep(20)

send_scpi("OUTPUT1:STATE OFF")
print("Done!")
