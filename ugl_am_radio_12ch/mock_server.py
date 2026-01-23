#!/usr/bin/env python3
"""
Mock SCPI Server for testing GUI without hardware.
Run this in one terminal, then run main.py in another.

Usage:
    Terminal 1: python mock_server.py
    Terminal 2: python main.py
    Connect to 127.0.0.1:5000
"""

import socket


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 5000))
    server.listen(1)

    print("=" * 50)
    print("Mock SCPI Server - 12 Channel Version")
    print("=" * 50)
    print("Listening on 127.0.0.1:5000")
    print("Waiting for GUI connection...")
    print()

    while True:
        conn, addr = server.accept()
        print(f"[CONNECTED] {addr}")

        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break

                commands = data.decode().strip().split("\n")
                for cmd in commands:
                    cmd = cmd.strip()
                    if not cmd:
                        continue

                    print(f"[RX] {cmd}")

                    # Respond to queries
                    if cmd == "*IDN?":
                        response = "Mock AM Radio,12CH,v2.0\n"
                    elif cmd.endswith("?"):
                        response = "0x00000000\n"
                    else:
                        response = "OK\n"

                    conn.sendall(response.encode())

        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            conn.close()
            print("[DISCONNECTED]")
            print()


if __name__ == "__main__":
    main()
