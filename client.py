from socket import *
import sys
import _thread
import time
from datetime import datetime
import os.path
from os import path

if len(sys.argv) != 4:
    print("\n===== Error usage, python3 client.py SERVER_IP SERVER_PORT UDP_PORT =====\n")
    exit(0)

serverHost = sys.argv[1]
serverPort = int(sys.argv[2])
udpPort = int(sys.argv[3])
serverAddress = (serverHost, serverPort)

# Login changes to to username of client once logged in
login = 0

# define a socket for the client side, it would be used to communicate with the server
clientSocket = socket(AF_INET, SOCK_STREAM)

# build connection with the server and send message to it
clientSocket.connect(serverAddress)

# Sending function for Upload file
def upd(servernumber, portnumber, file1, sender):
    udpListener = socket(AF_INET, SOCK_DGRAM)
    udpListener.sendto(f"{file1} {sender}".encode(), (servernumber, portnumber))
    print("Sending file ...")
    time.sleep(0.01)

    with open(file1, 'rb') as f1:
        while True:
            chunk = f1.read(1024)
            if not chunk:
                break
            udpListener.sendto(chunk, (servernumber, portnumber))
    
    print("File has finished sending.")


# Receiving thread for Upload file
def updListen():
    udpSock = socket(AF_INET, SOCK_DGRAM)
    udpSock.bind((gethostbyname(gethostname()), udpPort))

    chunk, addr = udpSock.recvfrom(1024)
    chunk = chunk.decode()
    filename = chunk.split()[0]
    sender = chunk.split()[1]

    print("\n----------")
    print(f"Receiving {filename} from {sender} ...")
    print("----------")

    new_filename = f"{sender}_{filename}"
    while True:
        with open(new_filename, 'wb') as new:
            try:
                chunk, addr = udpSock.recvfrom(1024)
                try:
                    new.write(chunk)
                except:
                    print("Error writing file")
                    exit(0)
                udpSock.settimeout(2)
            except timeout:
                print(f"{sender}_{filename} has been received.")
                break
    # Restart thread
    _thread.start_new_thread(updListen, ())
    print("Answer the last prompt as normal")
    
        

while True:
    if login == 0:
        message = input("===== Please type any messsage you want to send to server: =====\n")
    else:
        message = input("Enter one of the following commands (BCM, ATU, SRB, SRM, RDM, OUT, UPD): ")
    # Check for errors in input / Add information to arguments for server to process

    if (login == 0) & (message != "login"):
        print("You must login before interacting with Toom (Enter 'login')")
        continue
    
    if (len(message) < 3):
        print("Command does not exist")
        continue
    
    # if login is entered, add udpPort to arguments
    if message == "login":
        message = message + f" {udpPort}"
    
    # Check args for BCM
    if (message[0:3] == "BCM") & (message[3:].strip() == ""):
        print("Command BCM requires a message")
        continue
    elif (message[0:3] == "BCM") & (len(message.split()) < 2):
        print("Separate 'BCM' and message with a space")
        continue
    
    # If command is BCM, add username for server to handle
    if message[0:3] == "BCM":
        message = message[0:3] + f" {login} " + message[4:]
    
    # Check args for ATU
    if (message[0:3] == "ATU") & (message != "ATU"):
        print("Command ATU does not take arguments")
        continue
    
    # Append username to ATU for server to handle
    if (message[0:3] == "ATU"):
        message = message[0:3] + " " + login
    
    # Check args for SRB
    if (message[0:3] == "SRB") & (message[3:].strip() == ""):
        print("Command SRB requires usernames of other users")
        continue
    elif (message[0:3] == "SRB") & (len(message.split()) < 2):
        print("Separate 'SRB' and usernames with a space")
        continue
    elif (message[0:3] == "SRB") & (login in message.split()):
        print("Command SRB cannot include your own name")
        continue

    # Add username to SRB for server to handle
    if (message[0:3] == "SRB"):
        message = message[0:3] + " " + login + " " + message[4:]
    
    # Check args for SRM
    if (message[0:3] == "SRM") & (message[3:].strip() == ""):
        print("Command SRM requires a room ID and a message")
        continue
    elif (message[0:3] == "SRM") & (len(message.split()) < 3):
        print("Separate 'SRM', room ID and usernames with a space")
        continue
    
    # Add username to SRM for server to handle
    if (message[0:3] == "SRM"):
        message = message[0:3] + " " + login + " " + message[4:]

    # Check args for RDM
    # Server checks for message type b/s
    if (message[0:3] == "RDM") & (message[3:].strip() == ""):
        print("Command RDM requires a message type (b/s) and a timestamp (1 Jun 2022 21:39:04)")
        continue
    elif (message[0:3] == "RDM") & (len(message.split()) < 6):
        print("Separate 'RDM', message type and timestamp with a space.")
        print("Ensure timestamp is in correct format (1 Jun 2022 21:39:04)")
        continue
    elif (message[0:3] == "RDM"):
        # Check if timestamp is correct
        try:
            timestamp = ' '.join(message.split()[2:])
            datetime.strptime(timestamp, "%d %b %Y %H:%M:%S")
        except:
            print("Timestamp is in wrong format, format should be '1 Jun 2022 21:39:04'")
            continue

    # Check args for OUT
    if (message[0:3] == "OUT") & (message != "OUT"):
        print("Command OUT does not take arguments")
        continue
    
    # Append username to OUT for server to handle
    if (message[0:3] == "OUT"):
        message = message[0:3] + " " + login

    # Check args for UPD
    if (message[0:3] == "UPD") & (message[3:].strip() == ""):
        print("Command UPD requires an online user and a file")
        continue
    elif (message[0:3] == "UPD") & (len(message.split()) < 3):
        print("Separate 'UPD', receiving user and file with a space.")
        continue
    elif (message[0:3] == "UPD") & (login == message.split()[1]):
        print("Cannot upload file to yourself")
        continue
    elif (message[0:3] == "UPD"):
        if not path.isfile(message.split()[2]):
            print("Cannot find file specified")
            continue

    if (message[0:3] != "UPD"):
        clientSocket.sendall(message.encode())
    else:
        # Request arguments for P2P communication from server (UPD)
        receiver = message.split()[1]
        filename = message.split()[2]
        newstring = f"udp {receiver} {filename}"
        clientSocket.sendall(newstring.encode())
        data = clientSocket.recv(1024)
        data = data.decode()
        if data[0:5] == "Error":
            print(f"[recv] {data}")
            continue
        servernumber = data.split()[0]
        portnumber = int(data.split()[1])
        filename = data.split()[2]
        upd(servernumber, portnumber, filename, login)
        continue
    
    data = clientSocket.recv(1024)
    receivedMessage = data.decode()

    # parse the message received from server and take corresponding actions
    if receivedMessage == "":
        print("[recv] Message from server is empty!")
    elif receivedMessage == "user credentials request":
        print("[recv] You need to provide username and password to login")
        while True:
            username = input("Enter Username: ")
            password = input("Enter Password: ")
            # Check username and password
            if (username == "") | (password == ""):
                print("Please enter a username and password")
                continue
            elif (" " in username) | (" " in password):
                print("There should be no spaces in username/password")
                continue
            sendmsg = username + " " + password
            clientSocket.sendall(sendmsg.encode())
            # Listen for response to login details
            data = clientSocket.recv(1024)
            servermsg = data.decode()
            # If login successful, update login variable and start UDP thread to listen in background
            if servermsg[0:2] == "Y ":
                login = servermsg.split()[1]
                print(f"[recv] Login successful!")
                print("Welcome to Toom!")
                # Retrieve IP and start listening thread
                _thread.start_new_thread(updListen, ())
                break
            elif "blocked" in servermsg:
                print(f"[recv] {servermsg}")
                exit(0)
            else:
                print(f"[recv] {servermsg}")

    elif receivedMessage[0:4] == "BCM ":
        print(f"[recv] {receivedMessage}")
    elif receivedMessage[0:4] == "ATU ":
        print(f"[recv] {receivedMessage}")
    elif receivedMessage[0:3] == "SRB":
        print(f"[recv] {receivedMessage}")
    elif receivedMessage[0:3] == "SRM":
        print(f"[recv] {receivedMessage}")
    elif receivedMessage[0:3] == "RDM":
        print(f"[recv] {receivedMessage}")
    elif receivedMessage[0:3] == "OUT":
        print(f"[recv] {receivedMessage}")
        print(f"Goodbye {login}!")
        break
    else:
        print("[recv] Message makes no sense")
        
    ans = input('Do you want to continue(y/n): ')
    if ans == 'y':
        continue
    else:
        break

# close the socket
clientSocket.close()
