# dumb module for parsing the SoC EEPROM (16 byte pages)
# page 0 (SOCID)       says PUEO_RFSO_C###_#### (identifier)
# page 1 (LOCATION)    says MMDD_YYYY_000C_00LS (date + crate + slot ID)
# page 2 (ORIENTATION) says MMDD_YYYY_00PP_00QQ (date + first phi or LF + second phi or LF#)
# page 3 (STARTUP)     says STRT_####_####_#### (state to stop at in startup)
# page 4 (OVER/LOAD)   says OVER_xxxx_xxxx_xxx# (load bitstream at # once and erase) or
#                           LOAD_xxx#_xxx#_xxx# (bitstream load order)
# page 5 (BCCOUNT)     says BCNT_####_####_#### (wait for this many packets in broadcast)

import os

pysoceeprom_cache = os.getenv('PYSOCEEPROM_CACHE')
pysoceeprom_cache = "/tmp/pueo/eeprom" if pysoceeprom_cache is None else pysoceeprom_cache

# this is in a try/except block for testing-y stuff 
try:
    from smbus2 import SMBus
except ImportError:
    pass

import datetime
import time
import sys
from pathlib import Path
from enum import Enum

# SUPER-REWORKED MULTIPLE TIMES NOW
# if you change anything internally you MUST MUST MUST
# call save() to have it store to the cache
# you must call updateEeprom() to save to EEPROM
# in EEPROM mode you must do a close() afterwards
# to unbind the driver!
# don't use any of the secret functions!!
class PySOCEEPROM:
    PUEORFSOC = b'PUEORFSOC'
    PAGELEN = 16
    HALFPAGE = 8
    SOCIDPAGE = 0
    LOCATIONPAGE = 1
    ORIENTATIONPAGE = 2
    ORIENTATION_LF = b'LF'    
    STARTUPPAGE = 3
    STARTUP_PFX = b'STRT'
    OVERLOADPAGE = 4
    BSOVERRIDE_PFX = b'BSOV'
    BSLOAD_PFX = b'BSLD'
    SFOVERRIDE_PFX = b'SFOV'
    SFLOAD_PFX = b'SFLD'
    BCCOUNTPAGE = 5
    BCCOUNT_PFX = b'BCNT'

    PAGECOUNT=6
    
    class AccessType(str, Enum):
        EEPROM='EEPROM'
        CACHE='CACHE'
        AUTO='AUTO'
        def __str__(self) -> str:
            return self.value
    
    def __init__(self,
                 bus=1,
                 dev=0x50,
                 mode=None,
                 cacheFn=pysoceeprom_cache):        
        # store the overall characteristics
        self.dev = dev
        self.bus = bus
        self.cache = Path(cacheFn)
        self.eepromNeedsRebind = False
        if mode != None:
            self.open(mode)
        else:
            self.mode = None

    def open(self, mode):
        if mode is None:
            raise ValueError("Access type must be specified")
        
        # determine if cache exists
        haveCache = self.cache.exists()
        if not haveCache:
            if mode == self.AccessType.CACHE:
                raise TypeError("Access mode %s specified, but %s does not exist" % (mode, cacheFn))
            else:
                self.mode = self.AccessType.EEPROM
        else:
            self.mode = self.AccessType.CACHE
            
        if mode == self.AccessType.EEPROM or not haveCache:
            self.readEeprom()
        else:
            self.readCache()
        return self
            
    def close(self):
        if self.mode == self.AccessType.EEPROM and self.eepromNeedsRebind:
            self._bindEeprom()
            
    def __enter__(self):
        if self.mode is None:
            raise ValueError("Access type must be specified")
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    # returns a bytes object b/c read_i2c_block_data returns list
    def _readEepromPage(self, bus, page) -> bytes:
        return bytearray(bus.read_i2c_block_data(self.dev,
                                                 page*self.PAGELEN,
                                                 self.PAGELEN))
    # accepts a bytes object, converts to list
    def _writeEepromPage(self, bus, page, d):
        bus.write_i2c_block_data(self.dev,
                                 page*self.PAGELEN,
                                 list(d))

    # unbinds driver
    def _unbindEeprom(self):
        devStr = '/sys/bus/i2c/devices/%d-00%2.2x' % (self.bus, self.dev)
        p = Path(devStr)
        if not p.exists():
            raise IOError("device at bus %d dev %2.2x has no sysfs entry" % (self.bus, self.dev))
        if ( p / 'driver' ).exists():
            ( p / 'driver' / 'unbind' ).write_text(p.name)
            self.eepromNeedsRebind = True

    # binds driver
    def _bindEeprom(self):
        drvStr = '/sys/bus/i2c/drivers/at24'
        p = Path(drvStr)
        if not p.exists():
            print("not binding EEPROM since at24 driver does not exist")
        else:
            ( p / 'bind').write_text('%d-00%2.2x' % (self.bus, self.dev) )
            self.eepromNeedsRebind = False        
            
    def readEeprom(self):
        self._unbindEeprom()
        self._data = bytearray()
        with SMBus(self.bus) as bus:
            for i in range(8):
                d = self._readEepromPage(bus, i)
                self._data = self._data + d
        self.mode = self.AccessType.EEPROM

    def readCache(self):
        self._data = bytearray(self.cache.read_bytes())

    @classmethod
    def _autonumpad(cls, pfx, n, pagelen=None):
        if pagelen is None:
            pagelen = cls.PAGELEN
        return pfx + str(n).rjust(pagelen-len(pfx),'0').encode()
        
    @staticmethod
    def _fromdate(d):
        datestr = str(d.month).rjust(2,'0')
        datestr += str(d.day).rjust(2,'0')
        datestr += str(d.year).rjust(4, '0')
        return datestr.encode()
            
    @staticmethod
    def _todate(data):
        try:
            month = int(bytes(data[0:2]))
            day = int(bytes(data[2:4]))
            year = int(bytes(data[4:8]))
            date = datetime.datetime(year, month, day)
            return date
        except:
            return None

    @classmethod
    def _fromSOCID(cls, socid):
        return cls._autonumpad(cls.PUEORFSOC, socid)

    @classmethod
    def _toSOCID(cls, pg):
        if pg[0:9] != cls.PUEORFSOC:
            return None
        else:
            try:
                return int(pg[9:])
            except:
                return None
            
    # used in both soft/bs
    @classmethod
    def _fromLoadOrder(cls, order, ovpfx, ldpfx):
        if len(order) == 1:
            if order[0] != 0:
                # single non-zero is an override
                pg = cls._autonumpad(ovpfx, order[0], pagelen=cls.HALFPAGE)
            else:
                pg = b'\xFF'*8
        else:
            str0 = str(order[0])
            str1 = str(order[1])
            str2 = str(order[2])
            pg = ldpfx + (str0+str1+str2+'0').encode()
        return pg

    # used in both soft/bs
    @classmethod
    def _toLoadOrder(cls, pg, ovpfx, ldpfx):
        if pg[0:4] == ovpfx:
            try:
                tmp = int(pg[7:8])
                if tmp < 3:
                    return [tmp]
                else:
                    return [0]
            except:
                return [0]
        elif pg[0:4] == ldpfx:
            order = [0, 0, 0]
            try:
                tmp = int(pg[4:5])
                order[0] = tmp if tmp < 3 else 0
                tmp = int(pg[5:6])
                order[1] = tmp if tmp < 3 else 0
                tmp = int(pg[6:7])
                order[2] = tmp if tmp < 3 else 0
            except:
                pass
            return order
        else:
            return [0]

    @classmethod
    def _fromBSLoadOrder(cls, order):
        return cls._fromLoadOrder(order, cls.BSOVERRIDE_PFX, cls.BSLOAD_PFX)

    @classmethod
    def _fromSoftLoadOrder(cls, order):
        return cls._fromLoadOrder(order, cls.SFOVERRIDE_PFX, cls.SFLOAD_PFX)

    @classmethod
    def _toBSLoadOrder(cls, pg):
        return cls._toLoadOrder(pg, cls.BSOVERRIDE_PFX, cls.BSLOAD_PFX)

    @classmethod
    def _toSoftLoadOrder(cls, pg):
        return cls._toLoadOrder(pg, cls.SFOVERRIDE_PFX, cls.SFLOAD_PFX)

    @classmethod
    def _toStartup(cls, pg):
        if pg[0:4] != cls.STARTUP_PFX:
            return None
        try:
            tmp = int(pg[4:])
            return tmp
        except:
            return None

    @classmethod
    def _fromStartup(cls, startup):
        if startup is None:
            return b'\xFF'*16
        else:
            return cls._autonumpad(cls.STARTUP_PFX, startup)

    @classmethod
    def _toLocation(cls, pg):
        if pg[0] == 0xFF:
            return None
        else:
            l = {}
            l['date'] = cls._todate(pg[0:8])
            if l['date'] is None:
                return None
            l['crate'] = pg[12:13]
            l['slot'] = pg[14:16]
            return l

    @classmethod
    def _fromLocation(cls, loc):
        if loc is None:
            return b'\xFF'*16
        else:
            return cls._fromdate(loc['date'])+b'000'+loc['crate']+b'00'+loc['slot']

    @classmethod
    def _toOrientation(cls, pg):
        if pg[0] == 0xFF:
            return None
        else:
            o = {}
            o['date'] = cls._todate(pg[0:8])
            if o['date'] is None:
                return None
            if pg[10:12] == cls.ORIENTATION_LF:
                o['phi'] = None
                try:
                    o['lfid'] = int(pg[14:16])
                except:
                    return None
            else:
                try:
                    phi0 = int(pg[10:12])
                    phi1 = int(pg[14:16])
                    o['phi'] = [phi0, phi1]
                    o['lfid'] = None
                except:
                    return None
        return o

    @classmethod
    def _fromOrientation(cls, o):
        if o is None:
            return b'\xFF'*16
        else:
            if o['lfid'] is not None:
                return cls._fromdate(o['date'])+b'00'+cls.ORIENTATION_LF + str(o['lfid']).rjust(4, '0').encode()
            else:
                p = lambda n : str(n).rjust(4,'0')
                return cls._fromdate(o['date'])+''.join(list(map(p, o['phi']))).encode()

    @classmethod
    def _toBroadcastCount(cls, pg):
        if pg[0:4] != cls.BCCOUNT_PFX:
            return None
        else:
            try:
                return int(pg[4:16])
            except:
                return None

    @classmethod
    def _fromBroadcastCount(cls, bc):
        if bc is None:
            return b'\xFF'*16
        else:
            return cls._autonumpad(cls.BCCOUNT_PFX, bc)

    def _getPropertyPage(self, fn, num, hp=None):
        ofs = hp*self.HALFPAGE if hp is not None else 0
        ll = self.HALFPAGE if hp is not None else self.PAGELEN
        st = num*self.PAGELEN + ofs
        sp = st + ll
        return fn(self._data[st:sp])

    def _setPropertyPage(self, fn, num, arg, hp=None):
        pg = fn(arg)
        ofs = hp*self.HALFPAGE if hp is not None else 0
        ll = self.PAGELEN if hp is not None else self.HALFPAGE
        st = num*self.PAGELEN + ofs
        sp = st + ll
        self._data[st:sp] = pg        

    @property
    def socid(self):
        return self._getPropertyPage(self._toSOCID, self.SOCIDPAGE)

    @property
    def location(self):
        return self._getPropertyPage(self._toLocation, self.LOCATIONPAGE)

    @property
    def orientation(self):
        return self._getPropertyPage(self._toOrientation, self.ORIENTATIONPAGE)

    @property
    def startup(self):
        return self._getPropertyPage(self._toStartup, self.STARTUPPAGE)

    @property
    def bsLoadOrder(self):
        return self._getPropertyPage(self._toBSLoadOrder, self.OVERLOADPAGE, 0)
    
    @property
    def softLoadOrder(self):
        return self._getPropertyPage(self._toSoftLoadOrder, self.OVERLOADPAGE, 1)

    @property
    def broadcastCount(self):
        return self._getPropertyPage(self._toBroadcastCount, self.BCCOUNTPAGE)

    @location.setter
    def location(self, loc):
        self._setPropertyPage(self._fromLocation, self.LOCATIONPAGE, loc)

    @orientation.setter
    def orientation(self, o):
        self._setPropertyPage(self._fromOrientation, self.ORIENTATIONPAGE, o)

    @startup.setter
    def startup(self, s):
        self._setPropertyPage(self._fromStartup, self.STARTUPPAGE, s)

    @broadcastCount.setter
    def broadcastCount(self, bc):
        self._setPropertyPage(self._fromBroadcastCount, self.BCCOUNTPAGE, bc)

    @bsLoadOrder.setter
    def bsLoadOrder(self, order):
        self._setPropertyPage(self._fromBSLoadOrder, self.OVERLOADPAGE, order, 0)

    @softLoadOrder.setter
    def softLoadOrder(self, order):
        self._setPropertyPage(self._fromSoftLoadOrder, self.OVERLOADPAGE, order, 1)

    def save(self):
        if self.mode != self.AccessType.CACHE:
            raise IOError("mode %s is read-only" % self.mode)
        self.cache.write_bytes(self._data)

    def updateEeprom(self):
        if self.mode != self.AccessType.CACHE:
            raise IOError("mode %s is read-only" % self.mode)
        # we open a new version of this in EEPROM mode
        # and do page-writes of pages
        with PySOCEEPROM(mode='EEPROM') as dev:
            with SMBus(dev.bus) as bus:
                for i in range(1, self.PAGECOUNT):
                    d = self._data[i*self.PAGELEN:(i+1)*self.PAGELEN]
                    dev._writeEepromPage(bus, i, d)
                    time.sleep(0.1)
        
def updateID():
    with PySOCEEPROM(mode='EEPROM') as dev:
        id = input('Enter new SOC ID: ')
        pg = dev._fromSOCID(id)
        yep = input('About to write %s : enter yep to proceed ' % pg.decode('utf-8'))
        if yep != 'yep':
            print('Aborting')
            return
        else:
            with SMBus(dev.bus) as bus:
                dev._writeEepromPage(bus, dev.SOCIDPAGE, pg)
            time.sleep(0.1)

def updateLocation():
    with PySOCEEPROM(mode='EEPROM') as dev:        
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

        writeBytes = dev._fromdate(date) + b'000' + crate.encode() + '00' + slot.encode()
        print("Writing Location:", writeBytes.decode())
        yep = input("Enter yep if this looks OK: ")
        if yep != 'yep':
            print("Aborting")
            return
        with SMBus(dev.bus) as bus:
            dev._writeEepromPage(bus, dev.LOCATIONPAGE, writeBytes)
            time.sleep(0.1)        


def updateOrientation():
    with PySOCEEPROM(mode='EEPROM') as dev:        
        date_str = input("Enter today's date (MM/DD/YYYY): ")
        date = datetime.datetime.strptime(date_str, "%m/%d/%Y")
        firstPhi = None
        while firstPhi is None:
            firstPhiStr = input("Enter first phi (0-23) or %s: " % dev.ORIENTATION_LF.decode())
            if firstPhiStr.encode() == dev.ORIENTATION_LF:
                firstPhi = b'00' + dev.ORIENTATION_LF
            else:
                firstPhiInt = int(firstPhi)
                if firstPhiInt < 0 or firstPhiInt > 23:
                    print("Incorrect first phi.")
                else:
                    firstPhi = firstPhiStr.rjust(4, '0').encode()

        secondPhi = None
        while secondPhi is None:
            secondPhiStr = input("Enter second phi (0-23) or %s # (0-1): " % dev.ORIENTATION_LF.decode())
            if firstPhi == dev.ORIENTATION_LF:
                max = 1
            else:
                max = 23
            secondPhiInt = int(secondPhi)
            if secondPhiInt < 0 or secondPhiInt > max:
                print("Incorrect second phi or ID#.")
            else:
                secondPhi = secondPhiStr.rjust(4, '0').encode()

        writeBytes = dev._fromdate(date) + firstPhi + secondPhi
        print("Writing orientation: %s" % writeBytes.decode())
        yep = input("Enter yep if this looks OK: ")
        if yep != 'yep':
            print("Aborting")
            return
        with SMBus(dev.bus) as bus:
            dev._writeEepromPage(bus, dev.LOCATIONPAGE, writeBytes)
            time.sleep(0.1)        

def dump(mode):
    with PySOCEEPROM(mode=mode) as dev:
        print("access mode: %s" % dev.mode)
        print("ID: ", dev.socid)
        loc = dev.location
        if loc:            
            print("Location: ", loc['crate'], loc['slot'])
        o = dev.orientation
        if o:
            print("Orientation: ",end='')
            if o['phi']:
                print(o['phi'][0]," ", o['phi'][1])
            else:
                print("%s%d" % (dev.ORIENTATION_LF.decode(), o['lfid']))
        s = dev.startup
        if s:
            print("Startup final state: ", s)
        blo = dev.bsLoadOrder
        if len(blo) == 1:
            if blo[0] != 0:
                print("Override: bitstream slot %d" % blo[0])
        else:
            print("Bitstream load order: %s" % ' '.join(list(map(str,blo))))
        slo = dev.softLoadOrder
        if len(slo) == 1:
            if slo[0] != 0:
                print("Override: soft slot %d" % slo[0])
        else:
            print("Soft load order: %s" % ' '.join(list(map(str,slo))))
        bc = dev.broadcastCount
        if bc:
            print("Broadcast order: ", bc)
                            
                
if __name__ == "__main__":
    import sys
    fnMap = { 'ID' : updateID,
              'location' : updateLocation,
              'orientation' : updateOrientation,
              'dump' : lambda : dump('AUTO'),
              'dumpEeprom' : lambda : dump('EEPROM'),
              'dumpCache' : lambda : dump('CACHE')}
    updateFn = None    
    if len(sys.argv) != 2:
        updateFn = None
    else:
        updateFn = fnMap.get(sys.argv[1], None)
    if updateFn is None:
        keys = ' '.join(list(fnMap.keys()))
        print("specify (exactly) one of: %s" % keys)        
        quit(1)

    updateFn()
