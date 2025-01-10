from serial import Serial
from cobs import cobs

# dev.send(HskPacket(0x80, 0x00)) as well as fully-filling it
# from a response.
# data can be
# - bytearray
# - bytes
# - string
# - list of integers under 256
# - anything else castable to bytes via bytes()
class HskPacket:
    def __init__(self,
                 dest,
                 ptype,
                 data=None,
                 src=0x00):
        if data is None:
            self.data = b''
        elif isinstance(data, str):
            self.data = data.encode()
        else:
            self.data = bytes(data)
        self.dest = dest
        self.src = src
        self.type = ptype

    def encode(self):
        pkt = bytearray(4)
        pkt[0] = self.src
        pkt[1] = self.dest
        pkt[2] = self.type
        pkt[3] = len(self.data)
        pkt += self.data
        pkt.append((256-(sum(pkt[4:]))) & 0xFF)
        return cobs.encode(pkt)
        

# build up and send the command given the destination, type,
# and the data to deliver if any.
# Data defaults to none b/c it allows us to do like
# sendHskCmd(dev, 0x80, 0x00) straight out.
# the smart user may create dicts or something to lookup
# IDs and command types with enums that can cast to ints or some'n
# src defaults to zero
# ...
# i am not smart
class HskSerial(Serial):
    def __init__(self, path):
        super().__init__(path, baudrate=500000, timeout=5)

    def send(self, pkt):
        if not isinstance(pkt, HskPacket):
            raise TypeError("pkt must be of type HskPacket")
        self.write(pkt.encode()+b'\x00')

    def receive(self):
        crx = self.read_until(expected=b'\x00').strip(b'\x00')
        rx = cobs.decode(crx)
        # checky checky
        if len(rx) < 5:
            raise IOError("received data only %d bytes" % len(rx))
        if sum(rx[4:]) & 0xFF:
            raise IOError("checksum failure: " + rx.hex(sep=' '))
        return HskPacket(rx[1],
                         rx[2],
                         data=rx[4:-1],
                         src=rx[0])
