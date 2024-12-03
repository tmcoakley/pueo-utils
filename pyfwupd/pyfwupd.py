#!/usr/bin/env python3

# pyfwupd is independent of the housekeeping path.
# pysurfHskd spawns it when it receives an eDownloadMode
# message with a value of 1 and then terminates
# it when it receives an eDownloadMode message with
# a value of 0. You don't need eDownloadMode for every
# file, just once will work.

# The first 32-bit word in the first frame needs to be b'PYFW'
# followed by a 32-bit length, then followed by a null-terminated
# string indicating the filename, then lots o data.

# If you screw up, just restart this guy (eDownloadMode=0
# then eDownloadMode=1). It completes whatever it's doing when
# it catches a signal.

from pyzynqmp import Bitstream, PyZynqMP
from gpio import GPIO 
import os
import selectors

import struct
import signal
from subprocess import Popen, PIPE
from pathlib import Path

PYFW=b'PYFW'
CURRENT=PyZynqMP.CURRENT
READBACK_TYPE_PATH=PyZynqMP.READBACK_TYPE_PATH
READBACK_LEN_PATH=PyZynqMP.READBACK_LEN_PATH
IMAGE_PATH=PyZynqMP.IMAGE_PATH
EVENTPATH="/dev/input/event0"

BANKOFFSET=0x40000

FRAMELEN=95704
BANKLEN=49152

# dunno how fast this will be, we'll see
# some part of me thinks I should write this in the damn driver
# or do a ctypes ffi call
class Converter:
    XILFRAME = "/usr/local/bin/xilframe"
    XILFRAME_ARGS = "-"
    def __init__(self):
        if not os.access(self.XILFRAME, os.X_OK):
            raise FileNotFoundError("cannot execute %s" % self.XILFRAME)
        self.xf = Popen([self.XILFRAME, self.XILFRAME_ARGS],
                        stdin=PIPE,
                        stdout=PIPE)

    def convert(self, fr):
        self.xf.stdin.write(fr)
        return self.xf.stdout.read(49152)

# signal handler, using self-pipe trick. need to replicate
# this for main pysurfHskd
class SignalHandler:
    terminate = False
    def __init__(self):
        noop = lambda s,f : None
        self.rfd, self.wfd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        signal.signal(signal.SIGINT, noop)
        signal.signal(signal.SIGTERM, noop)
        signal.set_wakeup_fd(self.wfd)

# this is supertrimmed for PUEO
class Event:
    # ll = struct timespec, H=type, H=code, I=value
    FORMAT='llHHI'
    LENGTH=struct.calcsize(FORMAT)
    def __init__(self, data):
        vals = struct.unpack(self.FORMAT, data)
        print("pyfwupd: unpacked into", vals)
        if vals[1] != 0 or vals[2] != 0 or vals[3] != 0:
            self.code = vals[3]
            self.value = vals[4]
        else:
            self.code = None

if __name__ == "__main__":
    z = PyZynqMP()
    err = None
    try:
        if z.state() != 'operating':
            raise RuntimeError("FPGA is not operating")
        if not os.path.islink(CURRENT):
            raise RuntimeError("Can't determine current firmware")
        userid = Bitstream(os.readlink(CURRENT)).userid
        if userid == 0xFFFFFFFF:
            raise RuntimeError("UserID does not have frame start")
    except Exception as e:
        print("pyfwupd: cannot start up -", repr(e))
        exit(1)

    bankA = PyZynqMP.encodeReadbackType(userid, capture=True)
    bankB = PyZynqMP.encodeReadbackType(userid+BANKOFFSET, capture=True)
    gpioA = GPIO(GPIO.get_gpio_pin(12), 'out')
    gpioB = GPIO(GPIO.get_gpio_pin(13), 'out')
    typePath = Path(READBACK_TYPE_PATH)
    lenPath = Path(READBACK_LEN_PATH)
    image = Path(IMAGE_PATH)
    
    # okey dokey, starting up
    handler = SignalHandler()
    # we always write our length, it's constant
    lenPath.write_text(str(FRAMELEN))
    stateA = [30, gpioA, str(bankA), None]
    stateB = [31, gpioB, str(bankB), None]

    stateA[3] = stateB
    stateB[3] = stateA

    # start up with bank A mode
    # whenever you enter eDownloadMode you need to start with MARK_A
    state = stateA

    typePath.write_text(state[2])
    
    # start with no file
    curFile = None
    # spawn the converter
    conv = Converter()
    # spawn the selector
    sel = selectors.DefaultSelector()

    # dear god this is insane
    with open(EVENTPATH, "rb") as evf:
        terminate = False
        # create handler functions here
        def set_terminate(fd):
            print("terminating")
            terminate = True
        def handleEvent(fd):
            nonlocal state
            
            # don't actually use fd
            eb = evf.read(Event.LENGTH)
            # info
            print("pyfwupd: out of read wait, got %d bytes" % len(eb))
            print(list(eb))
            if not eb or len(eb) != Event.LENGTH:
                # error
                print("skipping malformed read")
                return
            e = Event(evf.read(Event.LENGTH))
            if e.code is None:
                # debugging
                print("skipping separator")
                return
            else:
                if e.code == state[0] and e.value == 0:
                    # debugging
                    print("skipping clear event")
                    return
                if e.code == state[0] and e.value == 1:
                    # sooo much of this needs exception handling
                    r = image.read_bytes()
                    state[1].write(1)
                    state[1].write(0)
                    state = state[3]
                    typePath.write_text(state[2])
                    
                    data = conv.convert(r)
                    dlen = BANKLEN
                    if curFile is None:
                        # info
                        print("pyfwupd: no curFile")
                        print("pyfwupd: marker:", list(data[0:4]))
                        print("pyfwupd: length:", list(data[4:8]))
                        print("pyfwupd: beginning of fn:", list(data[8:12]))
                        if data[0:4] != PYFW:
                            # error
                            print("pyfwupd: communication error!")
                            print("pyfwupd: no current file but got", list(data[0:4]))
                            print("pyfwupd: instead of", list(PYFW))
                            terminate = True
                            return
                        else:
                            print("pyfwupd: PYFW okay, unpacking header")
                            thisLen = struct.unpack(">I", data[4:8])
                            data = data[8:]
                            endFn = data.index(b'\x00')
                            thisFn = data[:endFn].decode()
                            data = data[endFn+1:]
                            dlen = len(data)
                            print("pyfwupd: beginning", thisFn, "len", thisLen)
                            curFile = [thisFn, thisLen]
                    if dlen > curFile[1]:
                        print("pyfwupd: completed file %s" % curFile[0])
                        curFile = None
                    else:
                        curFile[1] = curFile[1] - dlen
                        # should be only when a verbose option given!!
                        print("pyfwupd: %d/%d" % (curFile[1], dlen))
                else:
                    print("pyfwupd: code %d value %d ???" % (e.code, e.value))
            return        

        sel.register(evf, selectors.EVENT_READ, handleEvent)
        sel.register(handler.rfd, selectors.EVENT_READ, set_terminate)
        #do selecty thing here
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fd)

    print("pyfwupd: terminating")
    #do something
    if curFile:
        print("pyfwupd: deleting incomplete file:", curFile)

    # kill both psdones if needed
    stateA[1].write(1)
    stateA[1].write(0)
    stateB[1].write(1)
    stateB[1].write(0)
    
