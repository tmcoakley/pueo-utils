# programming class using pyElectronics
# for Si5395. Probably works with other clock modules too.
# I use pyElectronics because it's easy to create gateway stuff
# for various different devices so the same code works in multiple
# places and I am violently sick of constantly writing programming
# code for these damn clocks

# this is a direct copy of the Si5341 code, they're in different
# classes because at some point I might add new functions or something
# - like, now, namely clock detection and shutdown

from electronics.device import I2CDevice
from csv import DictReader
from time import sleep

class Si5395(I2CDevice):
    def __init__(self, bus, address=0x76):
        super().__init__(bus, address)
        # set page to 0 so we know where we are
        self.page = 0
        self.i2c_write(b'\x01\x00')

    def set_page(self, page):
        if self.page != page:
            d = b'\x01' + bytes([page])
            self.i2c_write(d)
            self.page = page

    def read_register(self, addr):
        pg = (addr >> 8) & 0xFF
        a = (addr & 0xFF)
        self.set_page(pg)
        # i2c_read_register doesn't work for some weird reason
        self.i2c_write(bytes([a]))
        return self.i2c_read(1)

    def write_register(self, addr, val):
        pg = (addr >> 8) & 0xFF
        a = bytes([addr & 0xFF])
        self.set_page(pg)
        self.i2c_write(a + bytes([val]))

    def powerdown(self, val):
        r = self.read_register(0x1E)
        reg = r[0]
        if val:
            self.write_register(0x1E, reg | 0x1)
        else:
            self.write_register(0x1E, reg & 0xFE)

    def identify(self, verbose=False):
        id = []
        r = self.read_register(0x2)
        id.append(r[0])
        r = self.read_register(0x3)
        id.append(r[0])
        r = self.read_register(0x4)
        id.append(r[0])
        r = self.read_register(0x5)
        id.append(r[0])
        r = self.read_register(0x9)
        id.append(r[0])
        r = self.read_register(0xA)
        id.append(r[0])
        if verbose:
            print("Si",
                  f'{id[1]:x}', # 53
                  f'{id[0]:x}', # 95
                  chr(ord('A')+id[2]),
                  "-",
                  chr(ord('A')+id[3]),
                  "-",
                  "G" if id[4] == 0 else "?",
                  "M" if id[5] == 0 else "?",
                  sep='')
        return id

    # Status for the 5395 is split between
    # 0xC and 0xE
    def status(self):
        r = self.read_register(0xC)
        err = False
        print("Internal Status:", hex(r[0]))
        if r[0] & 0x1B:
            err = True
        if r[0] & 0x1:
            print("SYSINCAL = 1: Calibrating")
        if r[0] & 0x2:
            print("LOSXAXB = 1: No signal at XAXB pins")
        if r[0] & 0x8:
            print("XAXB_ERR: Problem locking to XAXB signal")
        if r[0] & 0x10:
            print("SMBUS_TIMEOUT: SMBus timeout error")

        r = self.read_register(0xE)
        print("Holdover/LOL Status:", hex(r[0]))

        if r[0] & 0x2:
            print("LOL: DSPLL is out of lock")
            err = True

        if err is False:
            print("Clock status OK: no errors.")
            
    # This loads a CSV file exported from CBPro.
    # pausestep is either a number or an array of step index
    # (starting at 1) that require delays.
    # pausetime is either a number or an array of lengths
    # of the number of milliseconds to wait.
    # Pauses occur *after* the step in question.
    def loadconfig(self, filename, pausestep=6, pausetime=300):
        # convert parameters to iterables
        if isinstance(pausestep, int):
            pausestep = [pausestep]
        if isinstance(pausetime, int):
            pausetime = [pausetime]*len(pausestep)
        # yes, there are all sorts of checks I'm not doing
        # here, whatever
        fp = open(filename)
        rdr = DictReader(filter(lambda row: row[0]!='#', fp))
        regs = []
        for row in rdr:
            regs.append(row)
        idx = 0
        for reg in regs:
            if idx in pausestep:
                sleep(pausetime[pausestep.index(idx)]/1000.)
            self.write_register(int(reg['Address'],0), int(reg['Data'],0))
            idx = idx + 1
            
