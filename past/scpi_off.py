import socket

RP_IP = "192.168.0.100"
RP_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
sock.connect((RP_IP, RP_PORT))
sock.send(("OUTPUT1:STATE OFF\r\n").encode())
sock.close()
print("Output OFF")
