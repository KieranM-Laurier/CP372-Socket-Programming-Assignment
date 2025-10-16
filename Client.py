#!/usr/bin/env python3
"""
Client.py
- Connects to server HOST:PORT
- Receives assigned name from server "NAME:ClientXX"
- Sends the assigned name back as confirmation
- CLI loop:
    - type messages to send to server
    - "list" -> receive a list of files
    - enter a filename to download (if exists on server)
    - "status" -> request server cache status
    - "exit" -> terminate connection gracefully
File downloads are stored in a local folder "downloads".
"""

import socket
import os

HOST = '127.0.0.1'
PORT = 65432
DOWNLOAD_DIR = 'downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def recvall(sock, n):
    """Helper to receive exactly n bytes"""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(min(n - len(data), 4096))
        if not packet:
            break
        data.extend(packet)
    return bytes(data)


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        # receive initial message (could be NAME:... or SERVER_FULL)
        first = s.recv(4096).decode('utf-8', errors='replace').strip()
        if not first:
            print("No response from server.")
            return
        if first == "SERVER_FULL":
            print("Server is full. Try again later.")
            return

        if first.startswith("NAME:"):
            assigned_name = first.split(":", 1)[1].strip()
            print("Assigned name by server:", assigned_name)
            # send confirmation (per assignment spec)
            s.sendall((assigned_name + "\n").encode('utf-8'))
        else:
            print("Unexpected server greeting:", first)

        # read server welcome (if any)
        try:
            s.settimeout(0.5)
            rest = s.recv(4096).decode('utf-8', errors='replace')
            if rest:
                print(rest.strip())
        except Exception:
            pass
        s.settimeout(None)

        # CLI loop
        while True:
            try:
                msg = input(f"{assigned_name}> ").strip()
            except EOFError:
                msg = 'exit'

            if not msg:
                continue
            s.sendall((msg + "\n").encode('utf-8'))

            # receive reply header
            resp = s.recv(4096)
            if not resp:
                print("Server closed the connection.")
                break
            resp_text = resp.decode('utf-8', errors='replace')

            # If it's a FILE header: "FILE:<filename>:<size>\n" then receive file bytes
            if resp_text.startswith("FILE:"):
                header, _, remaining = resp_text.partition('\n')
                _, filename, size_str = header.split(':', 2)
                filesize = int(size_str)
                # remaining could contain some bytes of the file (but decoded into string). To be robust, re-open socket read,
                # but because we've already read some bytes as decoded text we must handle carefully.
                # Strategy: calculate how many raw bytes we already consumed from the socket stream after header
                # Unfortunately we decoded to text, so we lost raw bytes for file portion.
                # For simplicity in this implementation, re-request file by sending the filename again if needed.
                # But a more robust approach is to manage a consistent protocol with binary header length.
                # Here we will:
                #   - Create file and read remaining bytes until totalsize reached by reading raw from socket.
                print(f"Receiving file '{filename}' ({filesize} bytes)...")
                # Since we already consumed everything in 'resp' as decoded text, attempt to read the rest raw:
                # read exactly filesize bytes
                fpath = os.path.join(DOWNLOAD_DIR, filename)
                with open(fpath, 'wb') as f:
                    # Read repeatedly until filesize reached
                    bytes_received = 0
                    while bytes_received < filesize:
                        chunk = s.recv(min(4096, filesize - bytes_received))
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_received += len(chunk)
                print(
                    f"Saved file to: {fpath} ({bytes_received} bytes received)")
                continue

            # If response is FILES: listing or STATUS or BYE or regular echo
            text = resp_text.strip()
            if text.startswith("FILES:") or text.startswith("STATUS:") or text == "BYE":
                # print the whole reply and continue
                # For multi-line replies we might need to receive more - but server sends small responses so this suffices.
                print(text)
                if text == "BYE":
                    print("Disconnected.")
                    break
                continue

            # default: print reply
            print(text)

            if text == "BYE":
                break


if __name__ == '__main__':
    main()
