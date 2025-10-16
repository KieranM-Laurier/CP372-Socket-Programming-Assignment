#!/usr/bin/env python3
"""
Server.py
Simple multi-client TCP server for CP372 assignment.
- Assigns client names Client01, Client02, ...
- Maintains in-memory cache of accepted/finished timestamps
- Supports commands from clients:
    - any string -> echo back appended with " ACK"
    - "status" -> send cache contents
    - "list" -> list files in server repo
    - "<filename>" (if exists in repo) -> stream file bytes with header "FILE:<filename>:<size>"
    - "exit" -> close connection (and record finished timestamp)
- Limits concurrent clients (MAX_CLIENTS)
"""

import socket
import threading
import os
from datetime import datetime

HOST = '127.0.0.1'
PORT = 65432
MAX_CLIENTS = 3
REPO_DIR = 'repo'   # server repository directory (files to serve)

# Ensure repo directory exists and create a sample file if empty
os.makedirs(REPO_DIR, exist_ok=True)
if not os.listdir(REPO_DIR):
    with open(os.path.join(REPO_DIR, 'sample.txt'), 'w') as f:
        f.write("This is a sample file from the server repository.\n")

# Global state
client_counter_lock = threading.Lock()
client_counter = 0

cache_lock = threading.Lock()
# cache mapping assigned_name -> {'accepted': datetime, 'finished': datetime or None}
client_cache = {}

# Semaphore to limit concurrent active clients
conn_semaphore = threading.Semaphore(MAX_CLIENTS)


def format_timestamp(ts):
    if ts is None:
        return "N/A"
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def send_text(conn, text):
    """Helper to send a UTF-8 text message (no binary)."""
    conn.sendall(text.encode('utf-8'))


def recv_line(conn):
    """Receive a text message delimited by socket boundaries (reads up to 4096 bytes).
       For this simple CLI protocol we assume each send corresponds to one logical message."""
    try:
        data = conn.recv(4096)
        if not data:
            return None
        return data.decode('utf-8', errors='replace').rstrip('\n')
    except ConnectionResetError:
        return None


def recvall(conn, n):
    """Receive exactly n bytes (or return fewer if connection breaks)."""
    data = bytearray()
    while len(data) < n:
        packet = conn.recv(min(n - len(data), 4096))
        if not packet:
            break
        data.extend(packet)
    return bytes(data)


def handle_client(conn, addr, assigned_name):
    global client_cache
    try:
        # Receive confirmation (client should send its name back per assignment)
        confirmation = recv_line(conn)
        print(f"[{assigned_name}] confirmation from {addr}: {confirmation}")

        with cache_lock:
            client_cache[assigned_name] = {
                'accepted': datetime.now(),
                'finished': None,
                'addr': f"{addr[0]}:{addr[1]}"
            }

        send_text(conn, f"Welcome {assigned_name}!\n")  # friendly acknowledge

        while True:
            msg = recv_line(conn)
            if msg is None:
                # client disconnected unexpectedly
                print(f"[{assigned_name}] disconnected unexpectedly.")
                break

            print(f"[{assigned_name}] -> {msg}")

            # "exit"
            if msg.lower() == 'exit':
                send_text(conn, "BYE\n")
                with cache_lock:
                    client_cache[assigned_name]['finished'] = datetime.now()
                print(f"[{assigned_name}] finished connection.")
                break

            # "status" -> send cache content
            elif msg.lower() == 'status':
                with cache_lock:
                    lines = []
                    for name, info in client_cache.items():
                        lines.append(
                            f"{name} | accepted: {format_timestamp(info['accepted'])} | finished: {format_timestamp(info['finished'])} | addr: {info.get('addr','')}"
                        )
                send_text(conn, "STATUS:\n" + "\n".join(lines) + "\n")

            # "list" -> send repo file list
            elif msg.lower() == 'list':
                files = os.listdir(REPO_DIR)
                if not files:
                    send_text(conn, "FILES:\n<no files>\n")
                else:
                    send_text(conn, "FILES:\n" + "\n".join(files) + "\n")

            # If message matches a filename, stream the file
            elif os.path.isfile(os.path.join(REPO_DIR, msg)):
                filepath = os.path.join(REPO_DIR, msg)
                filesize = os.path.getsize(filepath)
                header = f"FILE:{msg}:{filesize}\n"
                conn.sendall(header.encode('utf-8'))
                # send file bytes
                with open(filepath, 'rb') as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        conn.sendall(chunk)
                # After sending file, continue loop
                print(f"[{assigned_name}] served file {msg} ({filesize} bytes)")

            # Default: echo back appended with " ACK"
            else:
                send_text(conn, msg + " ACK\n")

    except Exception as e:
        print(f"[{assigned_name}] exception: {e}")
    finally:
        conn.close()
        with cache_lock:
            # if finished was never set, set finished now
            if assigned_name in client_cache and client_cache[assigned_name]['finished'] is None:
                client_cache[assigned_name]['finished'] = datetime.now()
        conn_semaphore.release()
        print(f"[{assigned_name}] connection closed; semaphore released.")


def main():
    global client_counter

    print(f"Starting server on {HOST}:{PORT} (max clients {MAX_CLIENTS})")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            print(f"Incoming connection from {addr}")

            # Try to acquire slot for a client without blocking forever
            acquired = conn_semaphore.acquire(blocking=False)
            if not acquired:
                # server full: politely inform and close
                try:
                    conn.sendall(b"SERVER_FULL\n")
                except Exception:
                    pass
                conn.close()
                print(f"Refused connection from {addr} - server full.")
                continue

            # assign client name
            with client_counter_lock:
                client_counter += 1
                assigned_index = client_counter
            assigned_name = f"Client{assigned_index:02d}"

            # send assigned name so client knows it
            try:
                conn.sendall(f"NAME:{assigned_name}\n".encode('utf-8'))
            except Exception:
                conn.close()
                conn_semaphore.release()
                continue

            # Spawn thread to handle client
            t = threading.Thread(target=handle_client, args=(
                conn, addr, assigned_name), daemon=True)
            t.start()


if __name__ == '__main__':
    main()
