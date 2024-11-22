from enum import Enum
import logging

# the startup handler actually runs in the main
# thread: it takes two queues, the primary event
# queue and the tick event queue.
# Note that basically whenever we wait, we
# run next tick because either it's going to be
# a long wait, or it never should've had us wait
# at all and so it's actually an error.
class StartupHandler:
    LMK_FILE = "/usr/local/share/SURF6_LMK.txt"
        
    class StartupState(int, Enum):
        STARTUP_BEGIN = 0
        WAIT_CLOCK = 1
        PROGRAM_ACLK = 2
        WAIT_ACLK_LOCK = 3
        ENABLE_ACLK = 4
        WAIT_PLL_LOCK = 5
        ALIGN_RXCLK = 6
        LOCATE_EYE = 7
        TURFIO_LOCK = 8
        WAIT_TURFIO_LOCKED = 9
        ENABLE_TRAIN = 10
        WAIT_TURFIO = 11
#        DISABLE_TRAIN = 12
        STARTUP_FAILURE = -1

        def __index__(self) -> int:
            return self.value

    def __init__(self,
                 logName,
                 surfDev,
                 surfClock,
                 surfClockReset,
                 autoHaltState,
                 eventFifo,
                 tickFifo,
                 eventType):
        self.state = self.StartupState.STARTUP_BEGIN
        self.logger = logging.getLogger(logName)
        self.surf = surfDev
        self.clock = surfClock
        surf.clockReset = surfClockReset
        self.endState = autoHaltState
        self.immediate = eventFifo
        self.tick = tickFifo
        self.eventType = eventType
        if self.endState is None:
            self.endState = self.StartupState.STARTUP_BEGIN

    def _runNextTick(self):
        if not self.tick.full():
            self.tick.put((self.eventType, NULL))
        else:
            raise RuntimeError("tick FIFO became full in handler!!")

    def _runImmediate(self):
        if not self.immediate.full():
            self.immediate.put((self.eventType, NULL))
        else:
            raise RuntimeError("immediate FIFO became full in handler!!")
        
    def run(self):
        # endState is used to allow us to single-step
        # so if you set startup to 0 in the EEPROM, you can
        # set the end state via HSK and single-step through
        # startup.
        if self.state == self.endState or self.state == self.StartupState.STARTUP_FAILURE:
            self._runNextTick()
            return
        elif self.state == self.StartupState.STARTUP_BEGIN:
            id = self.surf.read(0).to_bytes(4,'big')
            if id != b'SURF':
                self.logger.error("failed identifying SURF:", id)
                self.state == self.StartupState.STARTUP_FAILURE
                self._runNextTick()
                return
            else:
                dv = self.surf.DateVersion(self.surf.read(0x4))
                self.logger.info("this is SURF", str(dv))
                self.state = self.StartupState.WAIT_CLOCK
                self._runImmediate()
                return
        elif self.state == self.StartupState.WAIT_CLOCK:
            r = bf(self.surf.read(0xC))
            if not r[31]:
                self._runNextTick()
                return
            else:
                self.logger.info("RACKCLK is ready.")                
                self.state = self.StartupState.PROGRAM_ACLK
                self._runImmediate()
                return
        elif self.state == self.StartupState.PROGRAM_ACLK:
            if not os.path.exists(LMK_FILE):
                self.logger.error("failed locating %s" % LMK_FILE)
                self.state = self.StartupState.STARTUP_FAILURE
                self._runNextTick()
                return
            self.clockReset.write(1)
            self.clockReset.write(0)
            self.clock.surfClock.configure(LMK_FILE)
            self.state = self.StartupState.WAIT_ACLK_LOCK
            self._runImmediate()
            return
        elif self.state == self.StartupState.WAIT_ACLK_LOCK:
            st = self.clock.surfClock.status()
            if st & 0x2 == 0:
                self._runNextTick()
                return
            else:
                self.logger.info("ACLK is ready.")
                self.state = self.StartupState.ENABLE_ACLK
                self._runImmediate()
                return
        elif self.state == self.StartupState.ENABLE_ACLK:
            # write 1 to enable CE on ACLK BUFGCE
            rv = bf(self.surf.read(0xC))
            rv[0] = 1
            self.surf.write(0xC, int(rv))
            # write 0 to pull PLLs out of reset
            rv = bf(self.surf.read(0x800))
            rv[13] = 0
            self.surf.write(0x800, int(rv))
            self.state = self.StartupState.WAIT_PLL_LOCK
            self._runImmediate()
            return
        elif self.state == self.StartupState.WAIT_PLL_LOCK
            rv = bf(self.surf.read(0x800))
            if not rv[14]:
                self._runNextTick()
                return
            self.state = self.StartupState.ALIGN_RXCLK
            self._runImmediate()
            return
        elif self.state == self.StartupState.ALIGN_RXCLK:
            # use firmware parameters for this eventually!!!
            # this needs to freaking do something if it fails!!
            self.surf.align_rxclk()
            self.state = self.StartupState.LOCATE_EYE
            self._runImmediate()
            return
        elif self.state == self.StartupState.LOCATE_EYE:
            # use firmware parameters for this eventually!!!
            eye = self.surf.locate_eyecenter()
            self.surf.setDelay(eye[0])
            self.surf.turfioSetOffset(eye[1])
            self.state = self.StartupState.TURFIO_LOCK
            self._runImmediate()
            return
        elif self.state == self.StartupState.TURFIO_LOCK:
            self.surf.turfioLock(True)
            self.state = self.StartupState.WAIT_TURFIO_LOCKED
            self._runImmediate()
            return
        elif self.state == self.StartupState.WAIT_TURFIO_LOCKED:
            if not self.surf.turfioLocked():
                self._runNextTick()
                return
            self.state = self.StartupState.ENABLE_TRAIN
            self._runImmediate()
            return
        elif self.state == self.StartupState.ENABLE_TRAIN:
            # dangit lookup what to do here
            self.state = self.StartupState.WAIT_TURFIO
            self._runImmediate()
            return
        elif self.state == self.StartupState.WAIT_TURFIO:
            # figure out what to do here too!!!
            self._runNextTick()
            return
