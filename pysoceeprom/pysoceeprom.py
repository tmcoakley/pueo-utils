# dumb module for parsing the SoC EEPROM (16 byte pages)
# page 0 (SOCID)       says PUEO_RFSO_C###_#### (identifier)
# page 1 (LOCATION)    says MMDD_YYYY_000C_00LS (date + crate + slot ID)
# page 2 (ORIENTATION) says MMDD_YYYY_00PP_00QQ (date + first phi or LF + second phi or LF#)
from smbus2 import SMBus
import datetime
import time

class PySOCEEPROM:
    PUEORFSOC = b'PUEORFSOC'
    PAGELEN = 16
    SOCIDPAGE = 0
    LOCATIONPAGE = 1
    ORIENTATIONPAGE = 2
    ORIENTATION_LF = 'LF'
    
    def __init__(self, bus=0, dev=0x50):
        self.dev = dev
        self.parseEeprom()

    def _readPage(self, bus, page):
        return bus.read_i2c_block_data(self.dev,
                                       page*self.PAGELEN,
                                       self.PAGELEN)
    def _writePage(self, bus, page):
        bus.write_i2c_block_data(self.dev,
                                 page.self.PAGELEN,
                                 self.PAGELEN)

    @staticmethod
    def _fromdate(date):
        datestr = str(d.month).rjust(2,'0')
        datestr += str(d.day).rjust(2,'0')
        datestr += str(d.year).rjust(4, '0')
        return datestr
            
    @staticmethod
    def _todate(data):
        month = int(bytes(data[0:1]))
        day = int(bytes(data[2:3]))
        year = int(bytes(data[4:7]))
        date = datetime.datetime(year, month, day)
        return date        
        
    def parseEeprom(self):
        with SMBus(0) as bus:
            socidPage = self._readPage(bus, self.SOCIDPAGE)
            locationPage = self._readPage(bus, self.LOCATIONPAGE)
            orientationPage = self._readPage(bus, self.ORIENTATIONPAGE)
            
            if bytes(socidPage)[0:9] != self.PUEORFSOC:
                self.socid = None
            else:
                self.socid = int(bytes(socidPage)[9:])
            # with the others we just check the first byte
            if locationPage[0] == 0xFF:
                self.location = None                
            else:
                self.location = {}
                self.location['date'] = self._todate(locationPage)
                self.location['crate'] = bytes(locationPage[11])
                self.location['slot'] = bytes(locationPage[12:13])
            if orientationPage[0] == 0xFF:
                self.orientation = None
            else:
                self.orientation = {}
                self.orientation['date'] = self._todate(orientationPage)
                if bytes(orientationPage[10:11]) == self.ORIENTATION_LF:
                    self.orientation['phi'] = None
                    self.orientation['lfid'] = int(bytes(orientationPage[14:15]))
                else:
                    self.orientation['phi'] = [ int(bytes(orientationPage[10:11])),
                                                int(bytes(orientationPage[14:15]))]

# update PUEORFSOC id
def updateID():
    dev = PySOCEEPROM()
    id = input('Enter new SOC ID: ')
    paddedId = dev.PUEORFSOC + bytes(id.rjust(7, '0'), encoding='utf-8')
    yep = input('About to write %s : enter yep to proceed: ' % str(paddedId))
    if yep != 'yep':
        print('Aborting')
        return
    else:
        with SMBus(0) as bus:
            dint = list(paddedId)
            dev._writePage(bus, dev.SOCIDPAGE, dint)
        time.sleep(0.1)

# update the EEPROM location ID
def updateLocation():
    dev = PySOCEEPROM()
    date_str = input("Enter today's date (MM/DD/YYYY): ")
    date = datetime.datetime.strptime(date_str, "%m/%d/%Y")
    crate = None
    while crate is None:
        crateStr = input("Which crate, H or V? ")
        if crateStr != 'H' and crateStr != 'V':
            print("Incorrect crate.")
        else:
            crate = crateStr
    slot = None
    while slot is None:
        slotStr = input("Which slot (L1-7 or R1-7)? ")
        lrOkay = slotStr[0] == 'L' or slotStr[0] == 'R'
        slotNum = int(slotStr[1])
        if (not lrOkay) or slotNum < 1 or slotNum > 7: 
            print("Incorrect slot.")
        else:
            slot = slotStr
    writeStr = dev._fromdate(date) + '000' + crate + '00' + slot
    print("Writing Location:", writeStr)
    writeList = list(bytes(writeStr, encoding='utf-8'))
    with SMBus(0) as bus:
        dev._writePage(bus, dev.LOCATIONPAGE, writeList)
    time.sleep(0.1)

# update the EEPROM orientation ID
def updateOrientation():
    dev = PySOCEEPROM()
    date_str = input("Enter today's date (MM/DD/YYYY): ")
    date = datetime.datetime.strptime(date_str, "%m/%d/%Y")
    firstPhi = None
    while firstPhi is None:
        firstPhiStr = input("Enter first phi (0-23) or %s: " % dev.ORIENTATION_LF)
        if firstPhiStr == 'LF':
            firstPhi = firstPhiStr
        else:
            firstPhiInt = int(firstPhi)
            if firstPhiInt < 0 or firstPhiInt > 23:
                print("Incorrect first phi.")
            else:
                firstPhi = firstPhiStr

    secondPhi = None
    while secondPhi is None:
        secondPhiStr = input("Enter second phi (0-23) or %s # (0-1): " % dev.ORIENTATION_LF)
        if firstPhi == dev.ORIENTATION_LF:
            max = 1
        else:
            max = 23
        secondPhiInt = int(secondPhi)
        if secondPhiInt < 0 or secondPhiInt > max:
            print("Incorrect second phi.")
        else:
            secondPhi = secondPhiStr

    writeStr = dev._fromdate(date) + firstPhi.rjust(4, '0') + secondPhi.rjust(4, '0')
    print("Writing orientation:", writeStr)
    writeList = list(bytes(writeStr, encoding='utf-8'))
    with SMBus(0) as bus:
        dev._writePage(bus, dev.ORIENTATIONPAGE, writeList)
    time.sleep(0.1)            
