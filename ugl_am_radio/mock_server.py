#!/usr/bin/env python3
"""
Mock SCPI Server for Testing GUI
================================

Run this to test the GUI without a real Red Pitaya.
Prints all received commands so you can verify they're correct.

Usage:
    python mock_server.py
    
Then connect GUI to: 127.0.0.1 port 5000
"""

import socket


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 5000))
    server.listen(1)
    
    print("=" * 50)
    print("MOCK SCPI SERVER")
    print("=" * 50)
    print("Listening on port 5000...")
    print("Connect GUI to: 127.0.0.1:5000")
    print("=" * 50)
    print()
    
    while True:
        conn, addr = server.accept()
        print(f"[CONNECTED] {addr}")
        print("-" * 50)
        
        while True:
            try:
                data = conn.recv(1024).decode().strip()
                if not data:
                    break
                
                # Log received command
                print(f"[RX] {data}")
                
                # Respond to queries
                if data == "*IDN?":
                    response = "RedPitaya,STEMlab125-10,MOCK,v1.0"
                    conn.send((response + "\n").encode())
                    print(f"[TX] {response}")
                
                elif data == "SYST:STAT?":
                    response = "OK"
                    conn.send((response + "\n").encode())
                    print(f"[TX] {response}")
                
                # Parse and display command details
                elif data.startswith("SOURCE:INPUT "):
                    source = data.split()[1]
                    print(f"     -> Audio source set to: {source}")
                
                elif data.startswith("SOURCE:MSG "):
                    msg = data.split()[1]
                    print(f"     -> Message selected: #{msg}")
                
                elif data.startswith("CH") and ":FREQ " in data:
                    parts = data.replace(":", " ").split()
                    ch = parts[0]
                    freq = int(parts[2])
                    print(f"     -> {ch} frequency: {freq} Hz ({freq/1000:.0f} kHz)")
                
                elif data.startswith("CH") and ":OUTPUT " in data:
                    parts = data.replace(":", " ").split()
                    ch = parts[0]
                    state = parts[2]
                    print(f"     -> {ch} output: {state}")
                
                elif data.startswith("OUTPUT:STATE "):
                    state = data.split()[1]
                    if state == "ON":
                        print(f"     -> *** BROADCAST STARTED ***")
                    else:
                        print(f"     -> *** BROADCAST STOPPED ***")
                
                print()
                
            except ConnectionResetError:
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                break
        
        conn.close()
        print("-" * 50)
        print(f"[DISCONNECTED]")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped.")
