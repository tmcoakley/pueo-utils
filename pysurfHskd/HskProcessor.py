import logging
import os
from subprocess import Popen, PIPE, TimeoutExpired
from pathlib import Path

class HskProcessor:
    def ePingPong(self, pkt):
        rpkt = bytearray(pkt)
        rpkt[1] = rpkt[0]
        rpkt[0] = self.hsk.myID
        self.hsk.sendPacket(rpkt)

    def eStatistics(self, pkt):
        rpkt = bytearray(9)
        rpkt[1] = pkt[0]
        rpkt[0] = self.hsk.myID
        rpkt[2] = 15
        rpkt[3] = 4
        rpkt[4:8] = hsk.statistics()
        rpkt[8] = (256-sum(rpkt[4:8])) & 0xFF
        self.hsk.sendPacket(rpkt)
    
    def eVolts(self, pkt):
        rpkt = bytearray(17)
        rpkt[1] = pkt[0]
        rpkt[0] = self.hsk.myID
        rpkt[2] = 17
        rpkt[3] = 12
        rpkt[4:16] = struct.pack(">IIIIII", *zynq.raw_volts())
        rpkt[16] = (256-sum(rpkt[4:16])) & 0xFF
        self.hsk.sendPacket(rpkt)

    def eTemps(self, pkt):
        rpkt = bytearray(13)
        rpkt[1] = pkt[0]
        rpkt[0] = self.hsk.myID
        rpkt[2] = 16
        rpkt[3] = 8
        rpkt[4:12] = struct.pack(">IIII", *zynq.raw_temps())
        rpkt[12] = (256-sum(rpkt[4:12])) & 0xFF
        self.hsk.sendPacket(rpkt)

    # identify sends the PS DNA+MAC addr+slot ident if any (not fixed len)
    def eIdentify(self, pkt):
        rpkt = bytearray(4)
        rpkt[1] = pkt[0]
        rpkt[0] = self.hsk.myID
        rpkt[2] = 18
        rpkt += self.zynq.dna.encode()
        rpkt += self.zynq.mac.encode()
        l = self.eeprom.location
        if l is not None:
            rpkt += l['crate']
            rpkt += l['slot']
        rpkt[3] = len(rpkt[4:])
        cks = (256 - sum(rpkt[4:])) & 0xFF
        rpkt.append(cks)
        self.hsk.sendPacket(rpkt)

    def eStartState(self, pkt):
        if len(pkt) > 5:
            self.startup.endState = rpkt[4]
        rpkt = bytearray(6)
        rpkt[1] = pkt[0]
        rpkt[0] = self.hsk.myID
        rpkt[2] = 32
        rpkt[3] = 1
        rpkt[4] = self.startup.state
        rpkt[5] = (256 - rpkt[4]) & 0xFF
        self.hsk.sendPacket(rpkt)

    def eFwNext(self, pkt):
        rpkt = bytearray(4)
        rpkt[1] = pkt[0]
        rpkt[0] = self.hsk.myID
        if len(pkt) > 5:
            fn = pkt[4:-1]
            if fn[0] == 0:
                os.unlink(self.zynq.NEXT)
            elif not os.path.isfile(fn):
                rpkt[2] = 255
                rpkt[3] = 0
                rpkt.append(0)
                self.hsk.sendPacket(rpkt)
                return
            else:
                os.unlink(self.zynq.NEXT)
                os.symlink(fn, self.zynq.NEXT)
        rpkt[2] = 129
        if not os.path.exists(self.zynq.NEXT):
            rpkt[3] = 1
            rpkt += b'\x00\x00'
            self.hsk.sendPacket(rpkt)
        else:
            fn = os.readlink(self.zynq.NEXT).encode()+b'\x00'
            rpkt += fn
            cks = (256 - sum(rpkt[4:])) & 0xFF
            rpkt.append(cks)
            self.hsk.sendPacket(rpkt)

    def eDownloadMode(self, pkt):
        rpkt = bytearray(6)
        rpkt[1] = pkt[0]
        rpkt[0] = self.hsk.myID
        rpkt[2] = 190
        rpkt[3] = 1
        d = pkt[4:-1]
        if len(d):
            st = d[0]
            if st == 0:
                os.system("systemctl stop pyfwupd")
            else:
                os.unlink("/tmp/pyfwupd.loglevel")
                if st & 0x80:
                    loglevel = st & 0x7F
                    Path("/tmp/pyfwupd.loglevel").write_text(str(loglevel))
                os.system("systemctl start pyfwupd")
        rpkt[4] = 0 if os.system("systemctl is-active --quiet pyfwupd") else 1
        rpkt[5] = (256 - rpkt[4]) & 0xFF
        self.hsk.sendPacket(rpkt)
        
    def eJournal(self, pkt):
        rpkt = bytearray(4)
        rpkt[1] = pkt[0]
        rpkt[0] = self.hsk.myID
        rpkt[2] = 189
        d = pkt[4:-1]
        if len(d):
            args = d.decode().split(' ')
            cmd = [ "journalctl" ] + args
            try:
                p = Popen(cmd, stdin=PIPE, stdout=PIPE)
                self.journal = p.communicate(timeout=5)[0]
            except TimeoutExpired:
                p.kill()
                self.journal = p.communicate()[0]
                
        # all of this works even if journal is b''
        rd = self.journal[:255]
        self.journal = self.journal[255:]
        rpkt += rd
        rpkt[3] = len(rpkt[4:])
        cks = (256 - sum(rpkt[4:])) & 0xFF
        rpkt.append(cks)
        self.hsk.sendPacket(rpkt)
            
    hskMap = { 0 : ePingPong,
               15 : eStatistics,
               16 : eVolts,
               17 : eTemps,
               18 : eIdentify,
               32 : eStartState,
               129 : eFwNext,
               189 : eJournal,
               190 : eDownloadMode
              }

    # this guy is like practically the whole damn program
    def __init__(self,
                 hsk,
                 zynq,
                 eeprom,
                 startup,
                 logName,
                 terminateFn):
        self.hsk = hsk
        self.zynq = zynq
        self.eeprom = eeprom
        self.startup = startup
        self.logger = logging.getLogger(logName)
        self.terminate = terminateFn
        self.journal = b''
        
    def basicHandler(self, fd, mask):
        if self.hsk.fifo.empty():
            self.logger.error("handler called but FIFO is empty?")
            return
        pktno = os.read(fd, 1)
        pkt = self.hsk.fifo.get()
        cmd = pkt[2]
        if cmd in self.hskMap:
            try:
                cb = self.hskMap.get(cmd)
                self.logger.debug("calling %s", str(cb))
                cb(pkt)
            except Exception as e:
                import traceback
                self.logger.error("exception %s thrown inside housekeeping handler?", repr(e))
                self.logger.error(traceback.format_exc())
                self.terminate()
        else:
            self.logger.info("ignoring unknown hsk command: %2.2x", cmd)
            
