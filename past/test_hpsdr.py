import socket

# HPSDR discovery packet
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2)

# Send HPSDR discovery
discovery = bytes([0xEF, 0xFE, 0x02] + [0]*60)
sock.sendto(discovery, ("192.168.0.100", 1024))

try:
    data, addr = sock.recvfrom(1024)
    print(f"Got response from {addr}: {data[:10].hex()}")
except socket.timeout:
    print("No response - HPSDR might not be running or different port")
