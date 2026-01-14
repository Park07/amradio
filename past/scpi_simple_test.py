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

print("Sending 1 MHz sine wave...")
send_scpi("SOUR1:FUNC SINE")
send_scpi("SOUR1:FREQ:FIX 1000000")  # 1 MHz
send_scpi("SOUR1:VOLT 0.9")
send_scpi("OUTPUT1:STATE ON")

print("Transmitting at 1 MHz for 30 seconds...")
print(">> Look at CubicSDR at 1 MHz - should see spike!")
time.sleep(30)

send_scpi("OUTPUT1:STATE OFF")
print("Done!")
