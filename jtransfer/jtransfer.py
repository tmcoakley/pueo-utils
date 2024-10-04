
# why did I ever create this program
# - this script transfers a file via a jtagterminal spawned by
#   Xilinx's debug stuff (xsct/xsdb).

import socket
import sys
import argparse
import os

prog = "jtransfer.py"

defaultHost = "localhost"
defaultPrompt = "xilinx@pynq:~$"

parser = argparse.ArgumentParser(prog=prog)
parser.add_argument("localFile", help="local filename to transfer")
parser.add_argument("remoteFile", help="remote filename")
parser.add_argument("port", help="JTAG terminal port",type=int)
parser.add_argument("--host", help="Host of the JTAG terminal (default: {})".format(defaultHost),
                    default=defaultHost)
parser.add_argument("--prompt", help="bash prompt to expect (default: {})".format(defaultPrompt),
                    default=defaultPrompt)
parser.add_argument("--safeStart",action='store_true',
                    help="Try to read out all characters possible before starting (takes 5+ seconds)")
parser.add_argument("--verbose", "-v", action="count", default=0,
                    help="Increase verbosity")

args = parser.parse_args()

v = args.verbose
port = args.port
host = args.host

# check filename
if not os.path.isfile(args.localFile):
    print("%s: local file does not exist?" % prog)
    exit(1)
    
localFileSize = os.path.getsize(args.localFile)
localFile = open(args.localFile, "rb")


newline = b'\r\n'
# bash ends every command we send with this
# it does NOT end every LINE we send with this
endcmd = b'\x1b[?2004l\r'
# prompt - note we're assuming home dir
beginprompt = b'\x1b[?2004h'
prompt = beginprompt + bytes(args.prompt, encoding='utf-8') + b' '
# this is EOT
endfile = b'\n\x04'

# create TCP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (host, port)
if v > 0:
    print('%s: connecting to %s port %d' % (prog, host, port))
sock.connect(server_address)

# the way jtransfer works is by using xxd in reverse
# mode. the command line is
# xxd -r -p - $fileName
# then we send lines of 16 hex digits (32 characters)
# syncing up requires looking for the prompt
# then after sending the command, we look for the echo,
# 
try:
    if v > 0:
        print('%s: fetching prompt' % prog)
    # note that it's also going to convert \n to \r\n
    message = b'\n'
    sock.sendall(message)
    # this timeout sucks but it's kinda necessary
    sock.settimeout(5)
    msg = b''
    while True:
        try:        
            data = sock.recv(500)
            msg += data
            if v > 1:
                print('%s: got %d bytes, up to %d' %
                      (prog, len(data), len(msg)))
            if (msg[-len(prompt):None] == prompt):
                if args.safeStart:
                    if v > 0:
                        print('%s: found prompt after %d bytes, continuing due to safeStart'
                              % (prog, len(msg)))
                else:
                    if v > 0:
                        print('%s: found prompt after %d bytes'
                              % (prog, len(msg)))
                        break            
        except socket.timeout:
            if v > 0:
                print('%s: timed out waiting for more data' % prog)
            break
    # did we get our prompt
    if v > 1:
        print("%s: got %d bytes - " % (prog, len(msg)))
        print("{!r}".format(msg))
    if msg[-len(prompt):None] == prompt:
        if v > 0:
            print("%s: found prompt, continuing" % prog)
    else:
        print("%s: did not find prompt, maybe try --safeStart?" % prog)
        print("%s: got %d bytes - " % (prog, len(msg)))
        print("{!r}".format(msg))
        exit(1)
    # now we can shorten it
    sock.settimeout(1)

    # construct message
    rFn = bytes(args.remoteFile, encoding='utf-8')
    command = b'xxd -r -p - ' + rFn
    # add newline...
    message = command + b'\n'
    # but expect \r\n plus newline + endcmd
    expectedEcho = command + newline + endcmd
    if v > 0:
        print("%s: sending %s" % (prog, str(command)))
    sock.sendall(message)

    if v > 0:
        print("%s: finding echo" % prog)
    msg = b''
    while True:
        try:
            data = sock.recv(500)
            msg += data
            if v > 1:
                print('%s: got %d bytes, up to %d' %
                      (prog, len(data), len(msg)))
            if msg == expectedEcho:
                break
        except socket.timeout:
            print("%s: never received echo before timeout??" % prog)
            print("{!r}".format(expectedEcho))
            print("{!r}".format(msg))
            # send EOT to be safe
            sock.sendall(endfile)
            exit(1)
    nchunks = int(localFileSize/16) + (1 if (localFileSize % 16) else 0)
    if v > 0:
        print('%s: found echo, sending file (%d chunks)' % (prog, nchunks))    

    curChunk = 0
    while True:
        print('%s: chunk %d / %d' % (prog, curChunk, nchunks))
        line = localFile.read(16)
        if line == b'':
            break
        hexStr = bytes(line.hex(), 'utf-8')
        hexMsg = hexStr + b'\n'
        expectedEcho = hexStr + newline
        if v > 2:
            print('%s: sending %s' % (prog, line.hex()))
        sock.sendall(hexMsg)
        msg = b''
        while True:
            try:
                data = sock.recv(500)
                msg += data
                if v > 1:
                    print('%s: got %d bytes, up to %d' %
                          (prog, len(data), len(msg)))
                if msg == expectedEcho:
                    if v > 2:
                        print('{!r}'.format(msg))
                    break
            except socket.timeout:
                print("%s: never received echo before timeout???" % prog)
                print("{!r}".format(expectedEcho))
                print("{!r}".format(msg))
                # send EOT to be safe
                sock.sendall(endfile)
                exit(1)
        curChunk = curChunk + 1
    if v > 0:
        print("%s: file send complete, sending EOT" % prog)
    sock.sendall(endfile)

    msg = b''
    expectedEcho = newline + prompt
    while True:
        try:        
            data = sock.recv(500)
            msg += data
            if v > 1:
                print('%s: got %d bytes, up to %d' %
                      (prog, len(data), len(msg)))
            if msg == expectedEcho:
                break
        except socket.timeout:
            print("%s: never received prompt after EOT???" % prog)
            print("{!r}".format(expectedEcho))
            print("{!r}".format(msg))
            exit(1)
    print("%s: transfer complete" % prog)
finally:
    if v > 0:
        print('%s: closing socket' % prog)
    sock.close()
    
