# HskSerial

simple module for testing/interacting with housekeeping via serial

this thing isn't for use on a SURF, it's for testing the SURF

# examples

## Simple, with no data

```
from HskSerial import HskSerial, HskPacket
hsk = HskSerial('/dev/ttyUSB1')
pkt = HskPacket(0x80, "ePingPong")
print(pkt.pretty(asString=True))
hsk.send(pkt)
pkt = hsk.receive()
print(pkt.pretty(asString=True))
```
gives
```
ePingPong from 00 to 80
ePingPong from 80 to 00
```

## With string data

Change the above to
```
pkt = HskPacket(0x80, "ePingPong", "hello world")
```
gives
```
ePingPong from 00 to 80: hello world
ePingPong from 80 to 00: hello world
```

## With list/bytes data

Change the above to
```
pkt = HskPacket(0x80, "ePingPong", [0xBA,0xBE,0xFA,0xCE])
```
or
```
pkt = HskPacket(0x80, "ePingPong", b'\xBA\xBE\xFA\xCE')
```
and change ``asString`` to ``False`` in the pretty call. Gives:
```
ePingPong from 00 to 80: BA BE FA CE
ePingPong from 80 to 00: BA BE FA CE
```

## Accessing the internal data

```
from HskSerial import HskSerial, HskPacket
hsk = HskSerial('/dev/ttyUSB1')
pkt = HskPacket(0x80, "eIdentify")
hsk.send(pkt)
pkt = hsk.receive()
print(pkt.pretty())
print(pkt.pretty(asString=True))
ids = list(map(bytes.decode, pkt.data.split(b'\x00')))
print("DNA:", ids[0], "MAC:", ids[1], "PetaLinux:", ids[2] if lens(ids[2]) else "None")
if len(ids) == 6 or len(ids) == 7:
   print("pueo.sqfs version:", ids[3])
   print("pueo.sqfs hash:", ids[4])
   print("pueo.sqfs date:", ids[5])
if len(ids) == 4 or len(ids) == 7:
   print("Location:", ids[-1])
```
gives
```
eIdentify from 80 to 00: 34 30 30 30 30 30 30 30 30 31 36 39 63 30 32 36 32 64 32 31 32 30 38 35 00 64 38 34 37 38 66 39 36 30 63 30 61 00
eIdentify from 80 to 00: 400000000169c0262d212085d8478f960c0a
DNA: 400000000169c0262d212085  MAC: d8478f960c0a PetaLinux: None
```
Note that pretty-printing the packet here ignores the string terminator
(``b'\x00'``) that splits it into elements. The additional processing
on ``pkt.data`` extracts the information. Here, there were three
strings in the data, as required by the ``eIdentify`` message: the third
string was empty.