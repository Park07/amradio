#!/usr/bin/env python3
"""Mock FPGA server for testing"""

import socket
import threading

class MockFPGA:
    def __init__(self):
        self.channels = {i: {'enabled': False, 'freq': 540000} for i in range(1, 13)}
        self.broadcasting = False
        self.source = 'BRAM'
    
    def handle_command(self, cmd):
        cmd = cmd.strip().upper()
        print(f"  RX: {cmd}")
        
        if cmd == "*IDN?":
            return "MockFPGA,UGL-Radio,v1.0"
        if cmd == "STATUS?":
            return f"BROADCAST:{'1' if self.broadcasting else '0'},WATCHDOG:0,TEMP:42.5"
        if cmd == "WATCHDOG:RESET":
            return "OK"
        if cmd == "OUTPUT:STATE ON":
            self.broadcasting = True
            print("  *** BROADCAST STARTED ***")
            return "OK"
        if cmd == "OUTPUT:STATE OFF":
            self.broadcasting = False
            print("  *** BROADCAST STOPPED ***")
            return "OK"
        if cmd.startswith("FREQ:CH"):
            return "OK"
        if cmd.startswith("OUTPUT:CH"):
            return "OK"
        if cmd.startswith("SOURCE:MODE"):
            return "OK"
        return "OK"

def handle_client(conn, addr, fpga):
    print(f"[+] Connected: {addr}")
    buffer = ""
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode()
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line.strip():
                    response = fpga.handle_command(line)
                    conn.sendall(f"{response}\n".encode())
    except:
        pass
    print(f"[-] Disconnected: {addr}")
    conn.close()

def main():
    fpga = MockFPGA()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 5000))
    server.listen(5)
    
    print("=" * 40)
    print("  MOCK FPGA SERVER - Port 5000")
    print("=" * 40)
    print("Connect GUI to: 127.0.0.1:5000")
    print()
    
    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr, fpga))
        t.daemon = True
        t.start()

if __name__ == "__main__":
    main()
