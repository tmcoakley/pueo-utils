# There are 2 possible clocks on the SURF6.

from electronics.gateways import LinuxDevice
from electronics.devices import Si5395

from enum import Enum

import spi

import os
import time
import glob
import re
import struct
from pathlib import Path
from collections import defaultdict

class SURF6Clock:
    class Revision(Enum):
        REVA = 'Rev A'
        REVB = 'Rev B'
        # maybe a rev B2 if there are breaking changes
        
    def __init__(self):
        self.gw = LinuxDevice(0)
        self.trenzClock = Si5395(self.gw, 0x69)
        surfClockPath = self._find_lmk()
        if surfClockPath is None:
            print("no LMK04610 found, assuming rev A")
            self.rev = self.Revision.REVA
            self.surfClock = None
        else:
            self.rev = self.Revision.REVB
            self.surfClock = LMK0461x(surfClockPath)
            # we need to configure the LMK properly
            # first to talk to it.
            # We occasionally switch SYNC behavior so
            # make sure to force it properly here
            self.surfClock.transfer([0x01, 0x41, 0x04])
            self.surfClock.transfer([0x01, 0x42, 0x30])
            
    def identify(self):
        if self.rev == self.Revision.REVB:
            id = self.surfClock.identify()
            print("SURF Clock: type %2.2x id %4.4x rev %2.2x" %
                  ( id[0], id[1], id[2] ))
        id = self.trenzClock.identify()
        print("Trenz Clock: Si%2.2x%2.2x%c-%c-%c%c" %
              (id[1], id[0],chr(ord('A')+id[2]),chr(ord('A')+id[3]),
               'G' if id[4] == 0 else "?",
               'M' if id[5] == 0 else "?"))
            
    def _find_lmk(self):
        for dev in Path('/sys/bus/spi/devices').glob('*'):
            # Xilinx's original method for this was stupid
            fullCompatible = (dev / 'of_node' / 'compatible').read_text().rstrip('\x00')
            if fullCompatible == "ti,lmk0461x":
                if ( dev / 'driver').exists():
                    ( dev / 'driver' / 'unbind').write_text(dev.name)
                ( dev / 'driver_override').write_text('spidev')
                Path('/sys/bus/spi/drivers/spidev/bind').write_text(dev.name)
                devname = "/dev/spidev"+dev.name[3:]
                return devname
        return None
    
