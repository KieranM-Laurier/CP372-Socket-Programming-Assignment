"""
Server.py
Kieran Mochrie 169048254 moch8254@mylaurier.ca 
Anirudh Vashisht 169066628 vash6628@mylaurier.ca 
"""

import socket
import threading
import os
from datetime import datetime

host = '127.0.0.1'
port = 65432
maxClients = 3
repo = r'C:\repository'  # file location as path
if not os.path.exists(repo):
    os.makedirs(repo, exist_ok=True)
clientFormat = "Client{:02d}"

clientLock = threading.Lock()
line = '==========================================================='


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


class Client:
    # client has information unique to them and its stored in a class object
    def __init__(self, name, address):
        self.name = name
        self.accepted = datetime.now()
        self.finish = None
        self.address = address

    def finished(self):
        self.finish = datetime.now()

    def toString(self):
        accepted = self.accepted.strftime("%Y-%m-%d %H:%M:%S")
        if(self.finish):
            finish = self.finish.strftime("%Y-%m-%d %H:%M:%S")
        else:
            finish = None  # client still using the program
        return f"{self.name} | Accepted: {accepted} | Finished: {finish}."


class Server:
    def __init__(self, host, port, MAXCLIENTS=maxClients, repo_dir=repo):
        self.host = host
        self.port = port
        self.max_clients = MAXCLIENTS
        self.repo_dir = repo_dir
        self.clientCount = 0
        self.activeClients = {}
        self.cache = []
        self.socks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socks.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.online = True
        self.repoExists = True
        if not os.path.exists(repo_dir):
            self.repoExists = False  # program can still run and perform other tasks
            # creating a repository is useless since it would be empty
# python Server.py

    def startServer(self):
        # only 1 server can run at a time
        self.socks.bind((self.host, self.port))
        self.socks.listen(10)
        print(
            f"Server Online And Listening On Address: {self.host} Port: {self.port}.")
        while self.online == True:
            # used to send info to specific clients and not all
            connection, address = self.socks.accept()  # waits until a client connects
            print(f"[SERVER] {connection} Connected From {address}.")
            m1 = f"[SERVER] {connection} Connected From {address}."
            safeSend(connection, m1)
            with clientLock:  # thread lock to make sure server talks to correct client
                # this number is decreased when a client exits the program in the clientExit method
                activeClientCount = len(self.activeClients)
                #activeClientCount = 3
                if activeClientCount >= self.max_clients:
                    connection.send(b"Server Full.")
                    print(f"Client From {address} [ERROR: SERVER FULL].")
                    connection.close()  # connection to client closes
                    continue

                self.clientCount += 1  # total not active
                print(self.clientCount)
                clientName = clientFormat.format(self.clientCount)
                # create client object here

                clientRecord = Client(clientName, address)

                self.cache.append(clientRecord)
                self.activeClients[clientName] = {
                    'connection': connection, 'address': address, 'clientRecord': clientRecord}
            print(line+'\n')
            # each client gets their own thread since the server must communicate with up to 3 at once
            clientActionThread = threading.Thread(
                target=self.clientAction, args=(clientName,), daemon=True)
            # no join back since there is no need to wait for a client to finish
            clientActionThread.start()

    def clientAction(self, clientName):
        # have to tell client what they can do
        clientInfo = self.activeClients.get(clientName)
        connection = clientInfo['connection']
        clientRecord = clientInfo['clientRecord']
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        m1 = "Please Enter Your Name:"
        safeSend(connection, m1)
        data = safeRec(connection)  # updates client name
        print(data)
        # updates so a human name is attached to a client number
        updateName = f"{clientName} Name: {data}"
        clientRecord.name = updateName
        with clientLock:
            self.activeClients.pop(clientName, None)
            self.activeClients[updateName] = {
                'connection': connection,
                'address': clientInfo['address'],
                'clientRecord': clientRecord
            }
            for c in self.cache:
                if c is clientRecord:
                    c.name = updateName
                    # name obtained

        commands = """These Are The Available Commands:
Status: Prints Out Other Clients With Date and Time Accepted and Finished.
List: Prints Out File Names From The Repository If It Exists.
Stream: Streams The Content Of A File From The Repository (Case And File Type Specific).
Help: Repeats The Available Commands.
Exit: Exits The Session.
If Your Input Is Not Known The Server Will Echo It Back."""

        welcome = f"{clientRecord.toString().strip()}\n{commands}"
        safeSend(connection, welcome)

        while True:  # as long as client is sending inputs this contines\
            safeSend(connection, "\nPlease Enter Your Command")
            data = safeRec(connection)  # get input from client
            clientInput = data.strip()
            if data:

                if clientInput.lower() == 'status':  # user wants cache
                    with clientLock:
                        for c in self.cache:
                            safeSend(connection, c.toString().strip())

                elif clientInput.lower() == 'list':  # user wants directory
                    if not self.repoExists:
                        m1 = "No Repository Exists At This Time."
                        safeSend(connection, m1)
                        # we can still get other commands so dont break while loop
                    else:
                        files = os.listdir(self.repo_dir)
                        if(files):
                            fileMessage = "\n".join(files)
                        else:
                            fileMessage = "repository empty"
                        safeSend(connection, fileMessage)

                elif clientInput.lower().startswith("stream: "):
                    if not self.repoExists:
                        m1 = "No Repository Exists At This Time."
                        safeSend(connection, m1)
                        # we can still get other commands so dont break while loop
                    else:
                        # the file could have uppercase letters so dont lowercase the string
                        fileName = clientInput[8:].strip()
                        fileLocation = os.path.join(
                            self.repo_dir, fileName)
                        files = os.listdir(self.repo_dir)
                        if fileName not in files:
                            m1 = "That File Does Not Exist Or A Typo Was Made. This Repository Is Case And File Type Sensitive."
                            safeSend(connection, m1)
                        else:

                            m1 = f"Streaming {fileName}:\n"
                            safeSend(connection, m1)
                            # stream file in chunks
                            with open(fileLocation, 'rb') as f:
                                while True:
                                    contentStream = f.read(4096)
                                    # shouda named this fileStream but at this point who cares
                                    if not contentStream:
                                        break
                                    safeSend(connection, contentStream)
                            m1 = f"{fileName} Has Finished Streaming."
                            safeSend(connection, m1)

                elif clientInput.lower() == 'exit':  # end connection
                    m1 = "Exit Requested"
                    safeSend(connection, m1)
                    break

                elif clientInput.lower() == 'help':
                    safeSend(connection, commands)

                else:  # client sends a message not a command
                    safeSend(connection, f"{clientInput}ACK.")
            else:
                m1 = "No Input Given, Please Try Again, Use The 'Help' Command For A List Of Commands."
                safeSend(connection, m1)

        # should not get over here
        clientRecord.finished()
        with clientLock:
            safeSend(
                connection, f"Session finished: {clientRecord.toString()}")
            connection.close()
            self.activeClients.pop(updateName, None)
        return  # hey look at that we are over here
    # i wrote that comment at least 10 working hours ago


if __name__ == "__main__":
    TCPserver = Server(host, port, maxClients, repo)
    TCPserver.startServer()
