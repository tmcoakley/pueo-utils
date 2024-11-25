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
class Converter:
    XILFRAME = "/usr/local/bin/xilframe"
    XILFRAME_ARGS = "-"
    def __init__(self):
        if not os.access(self.XILFRAME, os.X_OK):
            raise FileNotFoundError("cannot execute %s" % self.XILFRAME)
        self.xf = subprocess.Popen([self.XILFRAME, self.XILFRAME_ARGS],
                                   stdin=PIPE,
                                   stdout=PIPE)

    def convert(self, fr):
        self.xf.stdin.write(fr)
        return self.xf.stdout.read(49152)

# signal handler
class SignalHandler:
    terminate = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.set_terminate)
        signal.signal(signal.SIGTERM, self.set_terminate)

    def set_terminate(self, signum, frame):
        self.terminate = True

# this is supertrimmed for PUEO
class Event:
    # ll = struct timespec, H=type, H=code, I=value
    FORMAT='llHHI'
    LENGTH=struct.calcsize(FORMAT)
    def __init__(self, data):
        vals = struct.unpack(self.FORMAT, data)
        if vals[1] == 0 and vals[2] == 0 and vals[3] == 0:
            self.code = None
        else:
            self.code = vals[3]
            self.value = vals[4]

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
    lenPath.write_text(FRAMELEN)
    # start up with bank A mode
    typePath.write_text(bankA)
    stateA = (30, gpioA, bankA, None)
    stateB = (31, gpioB, bankB, None)

    stateA[3] = stateB
    stateB[3] = stateA

    state = stateA
    
    # start with no file
    curFile = None
    # spawn the converter
    conv = Converter()
    # and open the event path

    # dear god this is insane
    with open(EVENTPATH, "rb") as evf:
        while not handler.terminate:
            e = evf.read(Event.LENGTH)
            if not e or len(e) != Event.LENGTH:
                # uhhh what
                continue            
            e = Event(evf.read(Event.LENGTH))
            if e.code is not None:
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
                        if data[0:4] != PYFW:
                            print("pyfwupd: communication error!")
                            print("pyfwupd: no current file but got", list(data[0:4]))
                            print("pyfwupd: instead of", list(PYFW))
                            handler.set_terminate()
                            continue
                        else:
                            thisLen = struct.unpack(">I", data[4:8])
                            data = data[8:]
                            endFn = data.index(b'\x00')
                            thisFn = data[:endFn].decode()
                            data = data[endFn+1:]
                            dlen = len(data)
                            curFile = (thisFn, thisLen)
                    if dlen > curFile[1]:
                        print("pyfwupd: completed file %s" % curFile[0])
                        curFile = None
                    else:
                        curFile[1] = curFile[1] - dlen
                        # should be only when a verbose option given!!
                        print("pyfwupd: %d/%d" % (curFile[1], dlen))
    print("pyfwupd: terminating")
    if curFile:
        print("pyfwupd: deleting incomplete file:", curFile)

    # kill both psdones if needed
    stateA[1].write(1)
    stateA[1].write(0)
    stateB[1].write(1)
    stateB[1].write(0)
    
