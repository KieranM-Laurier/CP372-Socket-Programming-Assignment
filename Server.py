#!/usr/bin/env python3
"""
Server.py
"""

import socket
import threading
import os
from datetime import datetime
host = '0.0.0.0'
port = 50000
maxClients = 3
repo = 'repository'
clientFormat = "Client{:02d}"

clientLock = threading.Lock()


class Client:
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
        return f"{self.name} | accepted: {accepted} | finished: {finish}"


class Server:
    def __init__(self, host, port, MAXCLIENTS, repo_dir):
        self.host = host
        self.port = port
        self.max_clients = MAXCLIENTS
        self.repo_dir = repo_dir
        self.clientCount = 0
        self.activeClients = {}
        self.cache = []
        self.socks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.online = True
        self.repoExists = True
        if not os.path.exists(repo_dir):
            self.repoExists = False  # program can still run and perform other tasks
            # creating a repository is useless since it would be empty

    def startServer(self):
        self.socks.bind((self.host, self.port))
        self.socks.listen(20)
        while self.online == True:
            # used to send info to specific clients and not all
            connection, address = self.socks.accept()
            connection.sendall(b"Server Online and Active\n")
            with clientLock:
                activeClientCount = len(self.activeClients)
                if activeClientCount >= self.max_clients:
                    connection.sendall(b"Server Full\n")
                    connection.close()
                    continue
                self.clientCount += 1
                clientName = clientFormat.format(self.clientCounter)
                clientRecord = Client(clientName, address)
                self.cache.append(clientRecord)
                self.activeClients[clientName] = {
                    'connection': connection, 'address': address, 'clientRecord': clientRecord}
            clientActionThread = threading.Thread(
                target=self.clientAction, args=(clientName,))
            clientActionThread.start()

        def clientAction(self, clientName):
            #
            clientInfo = self.activeClients.get(clientName)
            connection = clientInfo['connection']
            address = clientInfo['address']
            clientRecord = clientInfo['clientRecord']
            connection.sendall(b"Please Enter Your Name:\n")
            data = connection.recv(1024).decode().strip()
            if data:  # updates so a human name is attatched to a client number
                updateName = f"{clientName} Name: {data}"
                with clientLock:
                    clientRecord.name = updateName
                    del self.activeClients[clientName]
                    self.activeClients[updateName] = {
                        'connection': connection,
                        'address': address,
                        'clientRecord': clientRecord
                    }
                    for c in self.cache:
                        if c is clientRecord:
                            c.name = updateName
                            break
            # name obtained
            flag = True
            while(flag):  # as long as client is sending inputs this contines
                connection.sendall(b"Please Enter Command:\n")
                data = connection.recv(1024)
                if data:
                    clientInput = data.decode().strip()
                    if clientInput.lower() == 'status':  # user wants cache
                        with clientLock:
                            for c in self.cache:
                                message = c.toString()+"\n"
                                connection.sendall(message.encode())

                    elif clientInput.lower() == 'list':  # user wants directory
                        if not self.repoExists:
                            connection.sendall(
                                b"No repository exists at this time\n")
                            pass  # we can still get other commands so dont break while loop
                        else:
                            files = os.listdir(self.repo_dir)
                            for f in files:
                                connection.sendall((f+'\n').encode())

                    elif clientInput.lower() == 'exit':  # end connection
                        connection.sendall(b"Exit Requested\n")
                        flag = False
                        clientExit(updateName)

                    elif clientInput is None:
                        # this shouldnt happen its just a failsafe
                        connection.sendall(
                            b"No input given, please try again\n")

                    else:  # client sends a message not a command
                        clientInput = clientInput+"ACK\n"
                        connection.sendall(clientInput)
            # should not get over here

        def clientExit(self, clientName):
            with clientLock:
                clientInfo = self.activeClients.get(clientName)
                connection = clientInfo['connection']
                connection.close()
                clientInfo['clientRecord'].finished()
                del self.activeClients[clientName]
                print("Successful Exit\n")


if __name__ == "__main__":
    TCPserver = Server(host, port, maxClients, repo)
    TCPserver.startServer()
