from serial.threaded import Packetizer, ReaderThread
from cobs import cobs
import logging
import traceback
import threading

# This ONLY HANDLES COBS DECODING
# filterFn handles checking if it's for us or if it has a checksum error
# filterFn returns 0 if no issues, 1 if it's filtered, and -1 if it's
# an error (really anything other than 0 or 1)
class HskPacketHandler(Packetizer):
    def __init__(self,
                 eventFifo,
                 logName='pysurfHskd',
                 eventType=None,
                 filterFn=None
                 ):
        super(HskPacketHandler, self).__init__()
        self.logger = logging.getLogger(logName)
        self.eventType = eventType
        self.eventFifo = eventFifo
        self.filterFn = lambda pkt : 0 if not filterFn else filterFn
        self._statisticsLock = threading.Lock()
        self._receivedPackets = 0
        self._sentPackets = 0
        self._errorPackets = 0
        self._droppedPackets = 0
        self._filteredPackets = 0
        self._mod = lambda x : x & 0xFF
        
    def connection_made(self, transport):
        super(HskPacketHandler, self).connection_made(transport)
        self.logger.info("opened port")

    def connection_lost(self, exc):
        if exc:
            self.logger.error("closed port due to exception")
            traceback.print_exc(exc)
        else:
            self.logger.info("closed port")

    def handle_packet(self, packet):
        if len(packet) == 0:
            return
        try:
            pkt = cobs.decode(packet)
        except cobs.DecodeError:
            with self._statisticsLock:
                self._errorPackets = self._errorPackets + 1
                errorPackets = self._errorPackets
            errMsg = "COBS decode error #%d : %s" % (errorPackets, ' '.join(list(map(hex,packet))))
            self.logger.error(errMsg)
            return
        # COBS decode OK
        filterResult = self.filterFn(pkt)
        if filterResult == 0:
            if not self.eventFifo.full():
                # everything OK
                with self._statisticsLock:
                    self._receivedPackets = self._receivedPackets + 1
                self.eventFifo.put((self.eventType, pkt))
            else:
                with self._statisticsLock:
                    self._droppedPackets = self._droppedPackets + 1
                    droppedPackets = self._droppedPacket
                errMsg = "Event FIFO full: dropped packet #%d" % droppedPackets
                self.logger.error(errMsg)
        elif filterResult == 1:
            # not for us
            with self._statisticsLock:
                self._filteredPackets = self._filteredPackets + 1
        else:
            # filter found an error
            with self._statisticsLock:
                self._errorPackets = self._errorPackets + 1
                errorPackets = self._errorPackets
            errMsg = "Filter error #%d : %s" % (errorPackets, ' '.join(list(map(hex,))))
            self.logger.error(errMsg)
    
    def send_packet(self, packet):
        d = cobs.encode(packet) + b'\x00'
        if self.transport:
            self.transport.write(d)
        with self._statisticsLock:
            self._sentPackets = self._sentPackets + 1

    def statistics(self):
        r = []
        with self._statisticsLock:
            r = [self._receivedPackets,
                 self._sentPackets,
                 self._errorPackets,
                 self._droppedPackets,
                 self._filteredPackets]
        return list(map(self._mod, r))
    
