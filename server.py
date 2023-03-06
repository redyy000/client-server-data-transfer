from socket import *
from threading import Thread
import sys, select
import time
from datetime import datetime


# acquire server host and port from command line parameter
if len(sys.argv) != 3:
    print("\n===== Error usage, python3 server.py SERVER_PORT number_of_consecutive_failed_attempts ======\n")
    exit(0)

# Verify the number of allowed failed consecutive attempts
try:
    if (int(sys.argv[2]) < 1) | (int(sys.argv[2]) > 5):
        exit(0)
except:
    print(f"Invalid number of allowed failed consecutive attempts: {sys.argv[2]}")
    print("Must be an integer between 1 and 5")
    exit(0)

attempts = int(sys.argv[2])
user_dict = {}
user_number = 0
message_number = 0

# SR is a dictionary of dictionaries
# Each dictionary contains a user list and a SR message id number.
SR_number = 0
SR = {}
username = ''

# Process credentials.txt into dictionary
# each username has a list; index 0 is password, index 1 is time until unblocked (if not 0)
with open("credentials.txt") as f:
    for line in f:
        line = line.split()
        user_dict[line[0]] = [line[1], 0]


# get IP for serverHost
hostname = gethostname()
serverHost = gethostbyname(hostname)
serverPort = int(sys.argv[1])
serverAddress = (serverHost, serverPort)

# define socket for the server side and bind address
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(serverAddress)


"""
    Define multi-thread class for client
    This class would be used to define the instance for each connection from each client
    For example, client-1 makes a connection request to the server, the server will call
    class (ClientThread) to define a thread for client-1, and when client-2 make a connection
    request to the server, the server will call class (ClientThread) again and create a thread
    for client-2. Each client will be runing in a separate therad, which is the multi-threading
"""
class ClientThread(Thread):
    def __init__(self, clientAddress, clientSocket):
        Thread.__init__(self)
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientAlive = False
        
        print("===== New connection created for: ", clientAddress)
        self.clientAlive = True
        
    def run(self):
        message = ''
        logged_in = 0
        while self.clientAlive:
            # use recv() to receive message from the client
            data = self.clientSocket.recv(1024)
            message = data.decode()
            # if the message from client is empty, the client would be off-line then set the client as offline (alive=Flase)
            if message == '':
                self.clientAlive = False
                print("===== the user disconnected - ", self.clientAddress)
                break
            # handle message from the client
            if message[0:5] == 'login':
                print("[recv] New login request")
                self.process_login(message[6:])
                # if login fails, client.py closes their own connection
                logged_in = 1

            elif logged_in == 0:
                print("[send] Login before using Toom")
                message = "Login first to use Toom"
                self.clientSocket.send(message.encode())
                
            # at this point, the user has logged in already
            elif message[0:3] == "BCM":
                print("[recv] BCM request")
                username = message.split(' ')[1]
                words = message.split(' ')[2:]
                message = ' '.join(words)
                self.bcm(message, username)

            elif message[0:3] == "ATU":
                print("[recv] ATU request")
                username = message.split()[1]
                self.atu(username)

            elif message[0:3] == "SRB":
                print("[recv] SRB request")
                username = message.split()[1]
                users = message.split()[2:]
                self.srb(username, users)

            elif message[0:3] == "SRM":
                global SR_number
                global SR
                print("[recv] SRM request")
                username = message.split()[1]
                message = message.split()[2:]
                try:
                    room = int(message[0])
                except:
                    srmerror = f"SRM Error - The separate room does not exist."
                    print(f"[send] {srmerror}")
                    self.clientSocket.send(srmerror.encode())
                    continue
                # Check if room ID exists
                if room not in SR.keys():
                    srmerror = f"SRM Error - The separate room does not exist."
                    print(f"[send] {srmerror}")
                    self.clientSocket.send(srmerror.encode())
                    continue
                # Check if user is in the room specified
                if username not in SR[room]["users"]:
                    srmerror = f"SRM Error - You are not in this separate room chat."
                    print(f"[send] {srmerror}")
                    self.clientSocket.send(srmerror.encode())
                    continue
                # If no errors, process message
                self.srm(username, message)

            elif message[0:3] == "RDM":
                print("[recv] RDM request")
                messagetype = message.split()[1]
                # If messagetype is wrong
                if (messagetype != "b") & (messagetype != "s"):
                    rdmerror = f"RDM Error - The message type is not b or s."
                    print(f"[send] {rdmerror}")
                    self.clientSocket.send(rdmerror.encode())
                    continue
                timestamp = message.split()[2:]
                self.rdm(messagetype, timestamp)

            elif message[0:3] == "OUT":
                print("[recv] OUT request")
                username = message.split()[1]
                self.out(username)

            elif message[0:3] == "udp":
                online = 0
                receiver = message.split()[1]
                filename = message.split()[2]
                with open("userlog.txt", 'r') as f:
                    for line in f:
                        if receiver in line:
                            servernumber = line.split()[-2][0:-1]
                            portnumber = line.split()[-1]
                            online = 1
                            break
                if online == 0:
                    self.clientSocket.send(f"Error - user is offline.".encode())
                    continue
                else:
                    self.clientSocket.send(f"{servernumber} {portnumber} {filename}".encode())

            else:
                print("[recv] " + message)
                print("[send] Cannot understand this message")
                message = 'Cannot understand this message'
                self.clientSocket.send(message.encode())
    
    """
        You can create more customized APIs here, e.g., logic for processing user authentication
        Each api can be used to handle one specific function, for example:
        def process_login(self):
            message = 'user credentials request'
            self.clientSocket.send(message.encode())
    """
    def process_login(self, udpPort):
        global user_dict
        global username
        message = 'user credentials request'
        print('[send] ' + message)
        self.clientSocket.send(message.encode())
        i = 0
        login = 0
        while (i < attempts):
            # data should contain a username and password
            data = self.clientSocket.recv(1024)
            print("[recv] Login Details")
            message = data.decode()
            # Client entered Ctrl + C
            if message == "":
                self.clientAlive = False
                print("===== the user disconnected - ", self.clientAddress)
                break
            message = message.split()
            # If username is in constructed user dictionary
            if message[0] in user_dict.keys():
                # If password matches username
                if message[1] == user_dict[message[0]][0]:
                    # if no block timer has been set, login
                    if user_dict[message[0]][1] == 0:
                        print("[send] Login Successful")
                        # Send username for client to store
                        sendmsg = f'Y {message[0]}'
                        self.clientSocket.send(sendmsg.encode())
                        login = 1
                        username = message[0]
                        break
                    # if a block timer has been set and the time has elapsed, login
                    elif (user_dict[message[0]][1] != 0) & (time.time() > user_dict[message[0]][1]):
                        print("[send] Login Successful")
                        # Send username for client to store
                        sendmsg = f'Y {message[0]}'
                        self.clientSocket.send(sendmsg.encode())
                        # set the block timer back to 0
                        user_dict[message[0]][1] = 0
                        login = 1
                        username = message[0]
                        break
                    # if a block timer has been set and the time has not elapsed, close client terminal
                    elif (user_dict[message[0]][1] != 0) & (time.time() < user_dict[message[0]][1]):
                        sendmsg = "Account is blocked due to multiple login failures."
                        print(f"[send] {sendmsg}")
                        sendmsg = "Your " + sendmsg + " Please try again later."
                        self.clientSocket.send(sendmsg.encode())
                        break
                else:
                    if i == (attempts - 1):
                        sendmsg = 'Invalid Password. Your account has been blocked.'
                        print(f"[send] {sendmsg}")
                        sendmsg = sendmsg + ' Please try again later.'
                        # set block timer for 10 seconds
                        user_dict[message[0]][1] = time.time() + 10
                        self.clientSocket.send(sendmsg.encode())
                        break
                    else:
                        sendmsg = 'Invalid Password.'
                        print(f"[send] {sendmsg}")
                        sendmsg = sendmsg + ' Please try again.'
                        self.clientSocket.send(sendmsg.encode())
                        i += 1
            else:
                sendmsg = 'Invalid Username.'
                print(f'[send] {sendmsg}')
                sendmsg = sendmsg + ' Please try again.'
                self.clientSocket.send(sendmsg.encode())
        # Update userlog.txt
        if login == 1:
            global user_number
            user_number += 1
            # retrieve UDP port number
            time1 = datetime.now().strftime("%-d %b %Y %H:%M:%S")
            with open("userlog.txt", 'a') as f:
                f.write(f"{user_number}; {time1}; {message[0]}; {self.clientAddress[0]}; {udpPort}\n")
    
    def bcm(self, message, username):
        global message_number
        message_number += 1
        time1 = datetime.now().strftime("%-d %b %Y %H:%M:%S")

        # Write BCM to messagelog.txt
        bcmstring = f"{message_number}; {time1}; {username}; {message}"
        with open("messagelog.txt", 'a') as f:
            f.write(f"{bcmstring}\n")
        # send the string to client
        bcmstring = 'BCM ' + bcmstring
        print(f"[send] {bcmstring}")
        self.clientSocket.send(bcmstring.encode())

    def atu(self, username):
        atustring = ""
        with open("userlog.txt", 'r') as f:
            # Retrieve username, time
            for line in f:
                name = line.split(' ')[5][0:-1]
                time1 = line.split(';')[1][1:]
                ip = line.split(';')[3].strip()
                host = line.split(';')[4].strip()
                # If user is not the client which called ATU
                if (name != username):
                    atustring = atustring + name + f", {ip}, {host}" + ", active since " + time1 + '.\n'
        if atustring == "":
            atustring = "No other active user\n"
        print(f"[send] {atustring}", end='')
        atustring = "ATU " + atustring
        self.clientSocket.send(atustring.encode())

    def srb(self, username, users):
        error = 0
        global SR_number
        global SR
        #check if users exist in credentials.txt
        for user in users:
            user_exist = 0
            with open("credentials.txt", 'r') as f:
                for line in f:
                    if user in line:
                        user_exist = 1
                        break
            # End loop, tell client the user which doesn't exist
            if user_exist == 0:
                srberror = f"SRB Error - {user} does not exist."
                print(f"[send] {srberror}")
                self.clientSocket.send(srberror.encode())
                error = 1
                break

        if error == 1:
            return

        #check if user is online in userlog.txt
        for user in users:
            user_exist = 0
            with open("userlog.txt", 'r') as f:
                for line in f:
                    if user in line:
                        user_exist = 1
                        break
            # End loop, tell client the user which doesn't exist
            if user_exist == 0:
                srberror = f"SRB Error - {user} is not online."
                print(f"[send] {srberror}")
                self.clientSocket.send(srberror.encode())
                error = 1
                break

        if error == 1:
            return

        #check if room already exists with given users
        all_users = users + [username]
        for room in SR:
            if sorted(SR[room]["users"]) == sorted(all_users):
                srberror = f"SRB Error - A separate room (ID: {room}) has already been created for these users."
                print(f"[send] {srberror}")
                self.clientSocket.send(srberror.encode())
                error = 1
                break

        if error == 1:
            return

        # Create separate room ID
        SR_message_number = 0
        SR_number += 1
        room_dict = {"SRID": SR_message_number, "users": all_users}
        SR[SR_number] = room_dict
        with open(f"SR_{SR_number}_messagelog.txt", 'w') as f:
            pass
        srbstring = f"SRB Separate chat room has been created, room ID: {SR_number}, users in this room: {SR[SR_number]['users']}"
        print(f"[send] {srbstring}")
        self.clientSocket.send(srbstring.encode())

    def srm(self, username, message):
        global SR_number
        global SR
        room = int(message[0])
        SR[room]["SRID"] += 1
        message_number = SR[room]["SRID"]
        time1 = datetime.now().strftime("%-d %b %Y %H:%M:%S")
        message = ' '.join(message[1:])
        srmstring = f"{message_number}; {time1}; {username}; {message}"
        with open(f"SR_{room}_messagelog.txt", 'a') as f:
            f.write(f"{srmstring}\n")
        srmstring = 'SRM ' + srmstring
        print(f"[send] {srmstring}")
        self.clientSocket.send(srmstring.encode())

    def rdm(self, messagetype, timestamp):
        global SR_number
        ID_number = 1
        rdmstring = ""
        timestamp = " ".join(timestamp)
        # Create datetime object from timestamp
        timestamp_object = datetime.strptime(timestamp, "%d %b %Y %H:%M:%S")
        if messagetype == "b":
            with open("messagelog.txt", 'r') as f:
                for line in f:
                    time2 = line.split(';')[1][1:]
                    time2object = datetime.strptime(time2, "%d %b %Y %H:%M:%S")
                    if timestamp_object < time2object:
                        rdmstring = rdmstring + line + '\n'
        elif messagetype == "s":
            while ID_number <= SR_number:
                with open(f"SR_{ID_number}_messagelog.txt", 'r') as f:
                    for line in f:
                        time2 = line.split(';')[1][1:]
                        time2object = datetime.strptime(time2, "%d %b %Y %H:%M:%S")
                        if timestamp_object < time2object:
                            rdmstring = rdmstring + line + '\n'
                ID_number += 1
        if (rdmstring == ""):
            rdmstring = "RDM - No new messages"
            print(f"[send] {rdmstring}")
            self.clientSocket.send(rdmstring.encode())
        else:
            print(f"[send] {rdmstring}", end='')
            rdmstring = "RDM " + rdmstring
            self.clientSocket.send(rdmstring.encode())

    def out(self, username):
        user_found = 0
        #Update userlog.txt
        with open("userlog.txt", 'r') as f1:
            lines = f1.readlines()
        with open("userlog.txt", 'w') as f2:
            for line in lines:
                if username not in line:
                    if user_found == 1:
                        message_id = int(line[0]) - 1
                        line = str(message_id) + line[1:]
                    f2.write(line)
                else:
                    user_found = 1
        outstring = "OUT Success"
        print(f"[send] {outstring}")
        self.clientSocket.send(outstring.encode())

print("===== Server is running =====")
print("===== Waiting for connection request from clients...=====")


while True:
    serverSocket.listen()
    clientSockt, clientAddress = serverSocket.accept()
    clientThread = ClientThread(clientAddress, clientSockt)
    clientThread.start()