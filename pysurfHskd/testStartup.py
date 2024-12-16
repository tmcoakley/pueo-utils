#!/usr/bin/env python3
# super simple early implementation of pysurfhskd
# to test stuff.

import os
import struct
import selectors
import signal
from pueoTimer import HskTimer
from signalhandler import SignalHandler
from pyHskHandler import HskHandler
from surfStartupHandler import StartupHandler
from serial.threaded import ReaderThread
from serial import Serial

from pysoceeprom import PySOCEEPROM
from pyzynqmp import PyZynqMP
from pueo.surf import PueoSURF
from pueo.common.wbspi import WBSPI
from pueo.common.bf import bf
from s6clk import SURF6Clock
from gpio import GPIO

import queue
import logging

LOG_NAME = "testStartup"

# https://stackoverflow.com/questions/2183233/how-to-add-a-custom-loglevel-to-pythons-logging-facility/35804945
def addLoggingLevel(levelName, levelNum, methodName=None):
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
       raise AttributeError('{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
       raise AttributeError('{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
       raise AttributeError('{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)

# the logging stuff might be farmed off into
# a separate thread using the QueueHandler stuff
addLoggingLevel('TRACE', logging.DEBUG-5)
addLoggingLevel('DETAIL', logging.INFO-5)
logger = logging.getLogger(LOG_NAME)
logging.basicConfig(level=10)

eeprom = PySOCEEPROM(mode='AUTO')
if eeprom.socid is None:
    logger.error("cannot start up without an SOCID!")
    exit(1)

zynq = PyZynqMP()
    
surf = PueoSURF(WBSPI.find_device('osu,surf6revB'),'SPI')
clk = SURF6Clock()
clk.trenzClock.powerdown(True)
clkrst = GPIO(GPIO.get_gpio_pin(3),'out')

# create the selector first
sel = selectors.DefaultSelector()
# now create our tick FIFO
tickFifo = queue.Queue()
# create a function for processing the tick FIFO
def runTickFifo(fd, mask):
    tick = os.read(fd, 1)
    logger.trace("tick %d", tick[0])
    # empty the tick FIFO before running them
    toDoList = []
    while not tickFifo.empty():
        toDoList.append(tickFifo.get())
    for task in toDoList:
        logger.trace("processing %s", task)
        try:
            task()
        except Exception as e:
            import traceback
            
            logger.error("callback threw an exception: %s", repr(e))
            logger.error(traceback.format_exc())
            
            handler.set_terminate()
            
        
# they all take the selector now
timer = HskTimer(sel, callback=runTickFifo, interval=1)
# this new version takes the selector
handler = SignalHandler(sel)
# spawn up the hsk handler
hsk = HskHandler(sel)
# and the surf startup handler
startup = StartupHandler(LOG_NAME,
                         surf,
                         clk,
                         clkrst,
                         StartupHandler.StartupState.LOCATE_EYE,
                         tickFifo)
# sigh stupidity
def runHandler(fd, mask):
    st = os.read(fd, 1)
    logger.trace("immediate run: handler in state %d", st[0])
    startup.run()

# double sigh    
sel.register(startup.rfd, selectors.EVENT_READ, runHandler)


# this is all pretty clean now
timer.start()
# here we would spec a callback normally.
# let's do a Really Stupid One right now


#######################
# MOVE THIS SOMEWHERE #
#######################
# NOTE NOTE: we should also have hsk.slotID and respond
# with hsk.myID only if pkt[1] is hsk.myID

def ePingPong(pkt):
    rpkt = bytearray(pkt)
    rpkt[1] = rpkt[0]
    rpkt[0] = hsk.myID
    hsk.sendPacket(rpkt)

def eStatistics(pkt):
    rpkt = bytearray(9)
    rpkt[0] = pkt[1]
    rpkt[1] = hsk.myID
    rpkt[2] = 15
    rpkt[3] = 4
    rpkt[4:8] = hsk.statistics()
    rpkt[8] = 256-(sum(rpkt[4:8]) % 256)
    hsk.sendPacket(pkt)
    
def eVolts(pkt):
    rpkt = bytearray(17)
    rpkt[0] = pkt[1]
    rpkt[1] = hsk.myID
    rpkt[2] = 17
    rpkt[3] = 12
    rpkt[4:16] = struct.pack(">IIIIII", *zynq.raw_volts())
    rpkt[16] = 256-(sum(rpkt[4:16]) % 256)
    hsk.sendPacket(pkt)

def eTemps(pkt):
    rpkt = bytearray(13)
    rpkt[0] = pkt[1]
    rpkt[1] = hsk.myID
    rpkt[2] = 16
    rpkt[3] = 8
    rpkt[4:12] = struct.pack(">IIII", *zynq.raw_temps())
    rpkt[12] = 256-(sum(rpkt[4:12]) % 256)
    hsk.sendPacket(pkt)
    
hskMap = { 0 : ePingPong,
           15 : eStatistics,
           16 : eVolts,
           17 : eTemps }
    
def basicHandler(fd, mask):
    if hsk.fifo.empty():
        logger.error("handler called but FIFO is empty?")
        return
    pktno = os.read(fd, 1)
    pkt = hsk.fifo.get()
    cmd = pkt[2]
    if cmd in hskMap:
        try:
            cb = hskMap.get(cmd)
            logger.debug("calling %s", str(cb))
            cb(pkt)
        except Exception as e:
            import traceback
            logger.error("exception %s thrown inside housekeeping handler?", repr(e))
            logger.error(traceback.format_exc())
            handler.set_terminate()
    else:
        logger.info("ignoring unknown hsk command: %2.2x", cmd)
            
######################
            
hsk.start(callback=basicHandler)
# need to call the startup handler once, but it can except
try:
    startup.run()
except Exception as e:
    import traceback
            
    logger.error("callback threw an exception: %s", repr(e))
    logger.error(traceback.format_exc())
    
    handler.set_terminate()    
    
# terminate is now inside the handler
while not handler.terminate:
    events = sel.select()
    for key, mask in events:
        callback = key.data
        logger.trace("processing %s", callback)
        try:
            callback(key.fileobj, mask)
        except Exception as e:
            import traceback
            
            logger.error("callback threw an exception: %s", repr(e))
            logger.error(traceback.format_exc())
            
            handler.set_terminate()

logger.info("Terminating!")
timer.cancel()
hsk.stop()
