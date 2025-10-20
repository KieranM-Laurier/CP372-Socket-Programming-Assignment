"""
Client.py
Kieran Mochrie 169048254 moch8254@mylaurier.ca 
Anirudh Vashisht 169066628 vash6628@mylaurier.ca 
"""
import socket
import os
import sys
import time

HOST = '127.0.0.1'  # the host and port of server.py
PORT = 65432
# downloadFolder = "C:\Users\kiera\OneDrive\Desktop\Computer Science Courses\CP372 Submissions\CP372 Assignment 1 downloads"
# usually this would be download but i want to keep organized

# python Client.py


def safeRec(connection, buffer_size=4096):
    """Receive data safely — returns '' on any failure."""
    try:
        data = connection.recv(buffer_size)
        if not data:
            # Client closed connection gracefully
            return ''
        return data.decode(errors='ignore').strip()
    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
        # Any socket issue: treat as client gone
        return ''
    except Exception:
        # Catch-all safeguard
        return ''


def safeSend(sock, data):
    """
    Safely send data to a socket.
    Accepts str or bytes. Returns True if sent, False if failed.
    Never throws.
    """
    try:
        if isinstance(data, str):
            data = data.encode()
        sock.sendall(data)
        return True
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
        return False
    except Exception:
        return False


def clientStart():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c:
        c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        c.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # clientAddress = sys.argv[1]  # ip address
        c.connect((HOST, PORT))  # connect to server
        data = safeRec(c)
        # first message should be a connect message
        print(f"Received {data!r}")
        # this message should tell if the server is full
        if data == "Server Full.":
            print("Server Is Full, Try Again Later")
            sys.exit()

        while True:
            message = safeRec(c)
            if "Please Enter Your Name:" == message:
                print(message)
                name = input()
                while name is None:
                    name = input("You Must Enter Your Name:")
                safeSend(c, name+'\n')
            else:
                print(message)
                command = input()
                while command is None:
                    command = input("You Must Enter A Command")
                safeSend(c, command+'\n')


if __name__ == "__main__":
    clientStart()
