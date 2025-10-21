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


def safeSend(sock, message):
    if isinstance(message, str):
        message = message.encode()
    length = len(message)
    length_bytes = length.to_bytes(4, 'big')
    sock.sendall(length_bytes + message)


def safeRec(sock):
    length_bytes = b''
    while len(length_bytes) < 4:
        chunk = sock.recv(4 - len(length_bytes))
        if not chunk:
            return ''
        length_bytes += chunk
    length = int.from_bytes(length_bytes, 'big')

    data = b''
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            return ''
        data += chunk
    return data.decode(errors='ignore')


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

        askName = safeRec(c)
        print(askName)
        name = input()
        while name is None:
            name = input("You Must Enter Your Name:")
        name.strip()
        safeSend(c, name)

        instruction = safeRec(c)
        print(instruction)

        #tAway = ""
        #    safeSend(c, tAway)
        while True:
            message = safeRec(c)  # pelase enter ur comand
            print(message)
            command = input()
            while command is None:
                command = input("You Must Enter A Command")
            command.strip()
            safeSend(c, command)

            response = safeRec(c)
            print(response)


if __name__ == "__main__":
    clientStart()
