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
repo = 'C:\repository'  # file location as path
clientFormat = "Client{:02d}"

clientLock = threading.Lock()
line = '==========================================================='


def safeRec(connection, buffer_size=4096):
    try:
        data = connection.recv(buffer_size)  # blocking call
        if not data:
            return ''
        return data.decode(errors='ignore').strip()
    except Exception:
        return ''


def safeSend(sock, data):
    try:
        if isinstance(data, str):
            data = data.encode()
        sock.sendall(data)
        return True
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
        return False
    except Exception:
        return False


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
                target=self.clientAction, args=(clientName,))
            # no join back since there is no need to wait for a client to finish
            clientActionThread.start()

    def clientAction(self, clientName):
        # have to tell client what they can do
        clientInfo = self.activeClients.get(clientName)
        connection = clientInfo['connection']
        address = clientInfo['address']
        clientRecord = clientInfo['clientRecord']
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        m1 = "Please Enter Your Name:"
        safeSend(connection, m1)
        data = safeRec(connection)  # updates client name
        print(data)
        # updates so a human name is attached to a client number
        updateName = f"{clientName} Name: {data}"
        with clientLock:
            clientRecord.name = updateName
            self.activeClients.pop(clientName, None)
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
                    connection.send(message.encode())
                    break
                # name obtained

        m2 = """        
        These Are The Available Commands:
        Status: Prints Out Other Clients With Date and Time Accepted and Finished.
        List: Prints Out File Names From The Repository If It Exists.
        Stream: Streams The Content Of A File From The Repository(Case And File Type Specific).
        Help: Repeats The Available Commands.
        Exit: Exits The Session.
        If Your Input Is Not Known The Server Will Echo It Back.
        """
        safeSend(connection, m2)
        flag = True
        while(flag):  # as long as client is sending inputs this contines\
            m1 = "Please Enter Your Command:"
            safeSend(connection, m1)
            data = connection.recv(2048)  # get input from client
            if data:
                clientInput = data.decode().strip()
                if clientInput.lower() == 'status':  # user wants cache
                    with clientLock:
                        for c in self.cache:
                            message = c.toString()
                            safeSend(connection, message)

                elif clientInput.lower() == 'list':  # user wants directory
                    if not self.repoExists:
                        m1 = "No Repository Exists At This Time."
                        safeSend(connection, m1)
                        pass  # we can still get other commands so dont break while loop
                    else:
                        files = os.listdir(self.repo_dir)
                        for f in files:
                            safeSend(connection, f)

                elif clientInput.lower().startswith("stream: "):
                    if not self.repoExists:
                        m1 = "No Repository Exists At This Time."
                        safeSend(connection, m1)
                        pass  # we can still get other commands so dont break while loop
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
                            fileName = clientInput[8:].strip()
                            m1 = f"Streaming {fileName} Now:\n"
                            safeSend(connection, m1)

                            with open(fileLocation, 'rb') as f:
                                contentStream = f.read(4096)
                                while contentStream:
                                    safeSend(connection, contentStream)
                            m1 = f"{fileName} Has Finished Streaming."
                            safeSend(connection, m1)

                elif clientInput.lower() == 'exit':  # end connection
                    m1 = "Exit Requested"
                    safeSend(connection, m1)
                    flag = False  # another failsafe
                    self.clientExit(updateName)

                elif clientInput.lower() == 'help':
                    safeSend(connection, m2)

                else:  # client sends a message not a command
                    clientInput += "ACK."
                    safeSend(connection, clientInput)
            else:
                m1 = "No Input Given, Please Try Again, Use The 'Help' Command For A List Of Commands."
                safeSend(connection, m1)

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
            safeSend(connection, message)

            # Client might not be able to see this
            m1 = "SUccessful Exit"
            safeSend(connection, m1)
            print("Successful Exit.")
            connection.close()
            del self.activeClients[clientName]


if __name__ == "__main__":
    TCPserver = Server(host, port, maxClients, repo)
    TCPserver.startServer()
