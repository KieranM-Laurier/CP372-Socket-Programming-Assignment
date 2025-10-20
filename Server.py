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
repo = 'C:\repository'  # file location as path
clientFormat = "Client{:02d}"

clientLock = threading.Lock()


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
        self.socks.bind(self.host, self.port)
        self.socks.listen(20)
        print(f"Server Online And Listening On {self.host}:{self.port}.\n")
        while self.online == True:
            # used to send info to specific clients and not all
            connection, address = self.socks.accept()
            with clientLock:  # thread lock to make sure server talks to correct client
                # this number is decreased when a client exits the program in the clientExit method
                activeClientCount = len(self.activeClients)
                if activeClientCount >= self.max_clients:
                    connection.sendall(b"Server Full.\n")
                    print(f"Client From {address} [ERROR: SERVER FULL].\n")
                    connection.close()  # connection to client closes
                    continue
                self.clientCount += 1  # total not active
                clientName = clientFormat.format(self.clientCounter)
                # create client object here
                clientRecord = Client(clientName, address)
                self.cache.append(clientRecord)
                self.activeClients[clientName] = {
                    'connection': connection, 'address': address, 'clientRecord': clientRecord}
            clientActionThread = threading.Thread(
                target=self.clientAction, args=(clientName,))  # each client gets their own thread since the server must communicate with up to 3 at once
            # no join back since there is no need to wait for a client to finish
            clientActionThread.start()

        def clientAction(self, clientName):
            # have to tell client what they can do

            clientInfo = self.activeClients.get(clientName)
            connection = clientInfo['connection']
            address = clientInfo['address']
            clientRecord = clientInfo['clientRecord']
            connection.sendall(b"Please Enter Your Name:\n")

            while True:  # keeps client here until a name is given
                data = connection.recv(1024).decode().strip()
                if data:  # updates so a human name is attached to a client number
                    updateName = f"{clientName} Name: {data}"
                    with clientLock:
                        clientRecord.name = updateName
                        del self.activeClients[clientName]
                        self.activeClients[updateName] = {
                            'connection': connection,
                            'address': address,
                            'clientRecord': clientRecord
                        }
                        for c in self.cache:  # updates clientname
                            if c is clientRecord:
                                c.name = updateName
                                message = c.toString()+"\n"
                                # print out their new information, mostly for demonstration purposes
                                connection.sendall(message.encode())
                                break
                            # name obtained
                else:
                    connection.sendall(
                        b"You Must Enter Your Name, Please Enter Your Name:\n")

            connection.sendall(b"These Are The Available Commands:\n")
            connection.sendall(
                b"Status: Prints Out Other Clients With Date and Time Accepted and Finished.\n")
            connection.sendall(
                b"List: Prints Out File Names From The Repository If It Exists.\n")
            connection.sendall(
                b"Stream: Streams The Content Of A File From The Repository(Case And File Type Specific).\n")
            connection.sendall(b"Help: Repeats The Available Commands.\n")
            connection.sendall(b"Exit: Exits The Session.\n")
            connection.sendall(
                b"If Your Input Is Not Known The Server Will Echo It Back.\n")

            flag = True
            while(flag):  # as long as client is sending inputs this contines\
                connection.sendall(b"Please Enter Command:\n")
                data = connection.recv(2048)  # get input from client
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
                                b"No Repository Exists At This Time.\n")
                            pass  # we can still get other commands so dont break while loop
                        else:
                            files = os.listdir(self.repo_dir)
                            for f in files:
                                connection.sendall((f+'.\n').encode())

                    elif clientInput.lower().startswith("stream: "):
                        if not self.repoExists:
                            connection.sendall(
                                b"No Repository Exists At This Time.\n")
                            pass  # we can still get other commands so dont break while loop
                        else:
                            # the file could have uppercase letters so dont lowercase the string
                            fileName = clientInput[8:].strip()
                            fileLocation = os.path.join(
                                self.repo_dir, fileName)
                            files = os.listdir(self.repo_dir)
                            if fileName not in files:
                                connection.sendall(
                                    b"That File Does Not Exist Or A Typo Was Made. This Repository Is Case And File Type Sensitive.\n")
                            else:
                                connection.sendall(
                                    b"Streaming {fileName} Now:\n")
                                with open(fileLocation, 'rb') as f:
                                    contentStream = f.read(2048)
                                    while contentStream:
                                        connection.sendall(
                                            contentStream.encode())
                                connection.sendall(
                                    b"\n{filename} Has Finished Streaming.\n")

                    elif clientInput.lower() == 'exit':  # end connection
                        connection.sendall(b"Exit Requested.\n")
                        flag = False  # another failsafe
                        clientExit(updateName)

                    elif clientInput.lower() == 'help':
                        connection.sendall(
                            b"These Are The Available Commands:\n")
                        connection.sendall(
                            b"Status: Prints Out Other Clients With Date and Time Accepted and Finished.\n")
                        connection.sendall(
                            b"List: Prints Out File Names From The Repository If It Exists.\n")
                        connection.sendall(
                            b"Stream: Streams The Content Of A File From The Repository(Case And File Type Specific).\n")
                        connection.sendall(
                            b"Help: Repeats The Available Commands.\n")
                        connection.sendall(b"Exit: Exits The Session.\n")
                        connection.sendall(
                            b"If Your Input Is Not Known The Server Will Echo It Back.\n")

                    elif clientInput is None:
                        # this shouldnt happen its just a failsafe
                        connection.sendall(
                            b"No Input Given, Please Try Again.\n")

                    else:  # client sends a message not a command
                        clientInput = clientInput+"ACK.\n"
                        connection.sendall(clientInput)
                else:
                    connection.sendall(
                        b"No Input Given, Please Try Again, Use The 'Help' Command For A List Of Commands.\n")
            # should not get over here

        def clientExit(self, clientName):  # exits client
            with clientLock:
                clientInfo = self.activeClients.get(clientName)
                connection = clientInfo['connection']
                clientRecord = clientInfo['clientRecord']

                clientInfo['clientRecord'].finished()
                # im sure theres a better way to do this but it serves its purpose
                message = clientRecord.toString()+"\n"
                # print out their old information, mostly for demonstration purposes
                connection.sendall(message.encode())

                # Client might not be able to see this
                connection.sendall(b"Successful Exit.\n")
                print("Successful Exit.\n")
                connection.close()
                del self.activeClients[clientName]


if __name__ == "__main__":
    TCPserver = Server(host, port, maxClients, repo)
    TCPserver.startServer()
