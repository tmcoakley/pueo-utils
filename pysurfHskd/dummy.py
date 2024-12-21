from HskProcessor import HskProcessor

def startDummyHsk(id=128):
    class DummyHsk:
        def __init__(self, id = 128):
            self.myID = id
        def statistics(self):
            return [ 4, 8, 12, 16 ]        
        def sendPacket(self, pkt):
            print("Pkt:", pkt.hex(sep=' '))

    class DummyEeprom:
        def __init__(self, location=None):
            self.location = location
            
    class DummyZynq:
        NEXT = "dummy_next_fw"
        def __init__(self,
                     mac = '010203040506',
                     dna = '400000000169c0262d212085'):
            self.mac = mac
            self.dna = dna
            
        def raw_volts(self):
            return [ 1,2,3,4,5,6 ]

        def raw_temps(self):
            return [ 7, 8, 9, 10 ]
        
    class DummyStartup:
        def __init__(self, state=0):
            self.endState = 1
            self.state = state

    def dummyTerminate():
        print("terminate was called")
            
    z = DummyZynq()
    e = DummyEeprom()
    s = DummyStartup()
    h = DummyHsk(id)
    t = dummyTerminate

    return HskProcessor(h,
                        z,
                        e,
                        s,
                        "DummyHskProcessor",
                        t,
                        "dummy_next_soft")
