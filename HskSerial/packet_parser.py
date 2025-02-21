import time 
from HskSerial.HskSerial import HskSerial, HskPacket

# These are the slots on the DAQ Crate. They are numbered such that you start 
# in the middle and move outwards for each RACK
Slots = {
    0 : "TURFIO Slot 0",
    1 : "SURF Slot 1",
    2 : "SURF Slot 2",
    3 : "SURF Slot 3",
    4 : "SURF Slot 4",
    5 : "SURF Slot 5",
    6 : "SURF Slot 6",
    7 : "SURF Slot 7"
}

# SURFs in Hpol LRACK --> SOCID
surfsHL = [ 0x8a, 0x94, 0x9d, 0x8d, 0x99, 0xa0, 0x97 ]

# SURFs in Hpol RRACK --> SOCID
surfsHR = [ 0x8c, 0x95, 0x9f, 0x9a, 0x87, 0x85, 0x9c ] 

surfsVR = [  ] 
surfsVL = [  ] 

# TURFIOs
turfioHL = 0x58 # Hpol LRACK
turfioHR = 0x50 # Hpol RRACK
turfioVL = 0x48 # Vpol LRACK
turfioVR = 0x40 # Vpol RRACK


class PacketParser: 

    def __init__(self, port, crate, rack): 

        self.dev = HskSerial(port)
        
        if crate == 'H': 
            if rack == 'R': 
                self.SF = surfsHR 
                self.TF = turfioHR
            else: 
                self.SF = surfsHL
                self.TF = turfioHL
        else: 
            if rack == 'R':
                self.SF = surfsVR 
                self.TF = turfioVR 
            else: 
                self.SF = surfsVL
                self.TF = turfioVL



    # Packet send and receive
    def packetsend(self, addr, cmd): 
        self.dev.send(HskPacket(addr, cmd))
        pkt = self.dev.receive()
        return pkt.data

    # Runs and Interprets eTemps for all boards
    def getTemp(self): 
        print()
        pkttf = self.packetsend(self.TF, 'eTemps')
        tftemp = self.tempTURFIO(pkttf)

        for iter in range(0,7):
            pktsf = self.packetsend(self.SF[iter], 'eTemps' )
            rpu, apu = self.tempSURF(pktsf, self.SF[iter])
        print()
        return tftemp, rpu, apu
        

    def tempTURFIO(self, recpacket): # this isnt just a packet readdddd its a packet read with a very specific applicaiton 
        # i heavily need to fix this

        tfiotemp = int.from_bytes(recpacket[0:2])
        srftemp = []
        for iter in range(2,16,2): 
            srftemp.append(int.from_bytes(recpacket[iter:iter+2]))

        temparray = []
        tfiotemp = ((tfiotemp * 503.975) / 2 ** 12) -273.15
        temparray.append(tfiotemp)
        print("{}: {}C".format('TURFIO Slot 0', format(tfiotemp, '.2f')))
            
        for iter in range(len(srftemp)): 
            if srftemp[iter] != 0: 
                srftemp[iter] = ( srftemp[iter] * 10 - 31880) / 42
                temparray.append(srftemp[iter])
                print("SURF Slot {}: {}C".format(iter + 1, format(srftemp[iter], '.2f')))
                
            else: 
                print("SURF Slot {}: NaN".format(iter + 1))
                temparray.append('NaN')
        return temparray
    
    def tempSURF(self, recpacket, surfid): 
        decimal_values = []
        for iter in range(0,4,2): 
            decimal_values.append(int.from_bytes(recpacket[iter:iter+2]))
       
        for iter in range(len(decimal_values)) : 
            decimal_values[iter] =  (decimal_values[iter] * 509.3140064) / 2 **16 - 280.23087870
            print('SURF {}'.format(self.hextodec(surfid)))
            if iter == 0:

                print("RPU: {}C".format(format(decimal_values[iter], '.2f')))
                rpuarray = decimal_values[iter]
            else: 
                print("APU: {}C".format(format(decimal_values[iter], '.2f')))
                apuarray = (decimal_values[iter])
        return rpuarray, apuarray
    
    # Random utils in case
    def bintohex(num): 
        return hex(int(str(num), 2))

    def dectohex(num): 
        return hex(num + 128)

    def hextodec(num): 
        return int(str(num)) - 128
  
        
       