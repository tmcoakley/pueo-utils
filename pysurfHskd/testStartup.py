#!/usr/bin/env python3
# super simple early implementation of pysurfhskd
# to test stuff.

import os
import selectors
import signal
from pueoTimer import HskTimer
from signalhandler import SignalHandler
from pyHskHandler import HskHandler
from surfStartupHandler import StartupHandler
from serial.threaded import ReaderThread
from serial import Serial

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
logging.basicConfig(level=15)
    
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
# here we would spec a callback normally
hsk.start()
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
