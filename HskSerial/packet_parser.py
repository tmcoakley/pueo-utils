import time 
from HskSerial import HskSerial, HskPacket

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
surfsHL = [ 0x97, 0xa0, 0x99, 0x8d, 0x9d, 0x94, 0x8a ]

# SURFs in Hpol RRACK --> SOCID
surfsHR = [ 0x8c, 0x95, 0x9f, 0x9a, 0x87, 0x85, 0x9c ] 

# SURFs in Vpol LRACK --> SOCID
surfsVL = [ 0x93, 0x9b, 0x96, 0x8e, 0x90, 0x8f ] 

# SURFs in Vpol RRACK --> SOCID
surfsVR = [ 0x89, 0x88, 0x9e, 0x8b, 0xa1, 0x98 ] 


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

        if crate == 'H': 
            self.endVal = 7 # 14 SURFs in HDAQ
        else: 
            self.endVal = 6 # 12 SURFs in VDAQ

        self.crate = crate
        self.sqfsCurrent = b'0.2.9'

    def help(self): 
        helpText = """
        Welcome to my Packet Parser :) 

        Methods 
        --------
        sayHi()
        Returns which TURFIOs/SURFs are online and responsive

        getTemps()
        Returns the TURFIO die temperature, as well as the SURF hotswap and die temperatures 

        getVolts()
        Returns the input voltage of TURFIO, I/O voltage of SURFs

        softwareVersion()
        Returns the TURFIO houskeeping version, SURF Petalinux and SQFS versions 

        sfIdentify()
        Returns the SURF PS IDs, MAC Addr, and various software versions

        tfIdentify()


        sqfsAllUpdated()
        Returns information on if all the SURFs have successfully updated to the most recent version of SQFS

        If you have any questions, email coakley.64@osu.edu
        """
        print(helpText)

    # Packet send and receive
    def packetsend(self, addr, cmd): 
        self.dev.send(HskPacket(addr, cmd))
        pkt = self.dev.receive()
        return pkt.data

    def surfID(self, num): 
        return self.hextodec(self.SF[num])

    def sayHi(self): 
        """Returns which TURFIOs/SURFs are online and responsive"""

        cmd = 'ePingPong'

        if self.crate == 'H': 
            endVal = 7 # 14 SURFs in HDAQ
        else: 
            endVal = 6 # 12 SURFs in VDAQ
        
        try:
            self.packetsend(self.TF, cmd)
            print('TURFIO says hi back!')
        except: 
            print('TURFIO ignored you :(')
        
      
        for iter in range(0, endVal):
            print("")
            try: 
                self.packetsend(self.SF[iter], cmd)
                print('SURF {} says hi back!'.format(self.surfID(iter)))
                
            except: 
                print('SURF {} ignored you :('.format(self.surfID(iter)))


    def tfIdentify(self): 
        cmd = 'eIdentify'
        recpkt = self.packetsend(self.TF, cmd)
        vSoftware = int.from_bytes(recpkt[0:1])
        bitSF = int.from_bytes(recpkt[1:2])
        print('TURFIO housekeeping: v{}'.format(vSoftware))
        

    def sfIdentify(self): 
        cmd = 'eIdentify'
        for iter in range(0, self.endVal): 
            recpkt = (self.packetsend(self.SF[iter], cmd)) 
            splitvals = recpkt.split(b'\x00')
            
            print("SURF ", self.surfID(iter))
            print('PS ID: ', splitvals[0].decode("utf-8"))
            print('MAC Addr: ', splitvals[1].decode("utf-8"))
            print('Petalinux Version: ', splitvals[2].decode("utf-8"))
            print('PUEO SQFS Version: ', splitvals[3].decode("utf-8"))
            print('Git Short Hash PUEO SQFS: ', splitvals[4].decode("utf-8"))
            print('PUEO SQFS Build Date: ', splitvals[5].decode("utf-8"))
            print("")

    def sqfsAllUpdated(self): 
        cmd = 'eIdentify'
        good = 0
        for iter in range(0, self.endVal): 
            recpkt = (self.packetsend(self.SF[iter], cmd)) 
            splitvals = recpkt.split(b'\x00')
            
            if splitvals[3] == self.sqfsCurrent: 
                good += 1
                continue
            else: 
                print("")
                print('SURF {} is out of date!'.format(self.SF[iter]))

        if good == self.endVal:
            print("")
            print("Current version: ", self.sqfsCurrent.decode('utf-8'))
            print("All SURFs have up-to-date SQFS")
            print("") 

        
    def softwareVersion(self, surf = True, turfio = True):
        cmd = 'eIdentify'
        
        print('Software Version')
        print("")

        if turfio == True:
            pkttf = self.packetsend(self.TF, cmd)
            vSoftware = int.from_bytes(pkttf[0:1])
            print('TURFIO housekeeping: v{}'.format(vSoftware))
            

        if surf == True: 
            for iter in range(0, self.endVal): 
                recpkt = (self.packetsend(self.SF[iter], cmd)) 
                splitvals = recpkt.split(b'\x00')
                print("")
                print("SURF ", self.surfID(iter))
                
                print('Petalinux Version: ', splitvals[2].decode("utf-8"))
                print('PUEO SQFS Version: ', splitvals[3].decode("utf-8"))
                
                print("")
             

        

    # Runs and Interprets eTemps for all boards
    def getTemps(self): 
        print("")
        pkttf = self.packetsend(self.TF, 'eTemps')
        tftemp = self.tempTURFIO(pkttf) # just in case

        if self.crate == 'H': 
            endVal = 7 # 14 SURFs in HDAQ
        else: 
            endVal = 6 # 12 SURFs in VDAQ

        rpuTemps = []
        apuTemps = []
        for iter in range(0,endVal):
            
            pktsf = self.packetsend(self.SF[iter], 'eTemps' )
            rpuTemp, apuTemp = self.tempSURF(pktsf, self.SF[iter])
            rpuTemps.append(rpuTemp)
            apuTemps.append(apuTemp)

        print("TURFIO: {}C".format(format(tftemp[0], '.2f')))
        print("")
        for iter in range(0, endVal): 
            print('SURF {}'.format(self.hextodec(self.SF[iter])))
            print('Hotswap: {}C'.format(tftemp[iter+1]))
            print("RPU: {}C".format(format(rpuTemps[iter], '.2f')))
            print("APU: {}C".format(format(apuTemps[iter], '.2f')))
            print("")
        
        
        
        

    def tempTURFIO(self, recpacket, printall = False):
        tfiotemp = int.from_bytes(recpacket[0:2])
        srftemp = []
        for iter in range(2,16,2): 
            srftemp.append(int.from_bytes(recpacket[iter:iter+2]))

        temparray = []
        tfiotemp = ((tfiotemp * 503.975) / 2 ** 12) -273.15
        temparray.append(tfiotemp)
        
            
        for iter in range(len(srftemp)): 
            if srftemp[iter] != 0: 
                srftemp[iter] = format((( srftemp[iter] * 10 - 31880) / 42), '.2f')
                temparray.append(srftemp[iter])
                
            else:
                temparray.append('NaN')
                
            
            if printall == True: 
                print("{}: {}C".format('TURFIO Slot 0', format(tfiotemp, '.2f')))
                print("")
                for iter in range(len(srftemp)): 
                    print("SURF Slot {}: {}C".format(iter + 1, temparray[iter]))
                    print("")
                
        return temparray
    
    def tempSURF(self, recpacket, surfid, printall = False): 

        def SFTempFunc(val): 
            return (val * 509.3140064) / 2 **16 - 280.23087870
        
        decimal_values = []
        for iter in range(0,4,2): 
            decimal_values.append(int.from_bytes(recpacket[iter:iter+2]))
        
        for iter in range(0,len(decimal_values),2) : 
            rpuTemp = (SFTempFunc(decimal_values[iter]))
            apuTemp = (SFTempFunc(decimal_values[iter+1]))
        
        if printall == True: 
            for iter in range(0, len(decimal_values)): 
                print('SURF {}'.format(self.hextodec(surfid)))
                print("RPU: {}C".format(format(rpuTemp[iter], '.2f')))
                print("APU: {}C".format(format(apuTemp[iter], '.2f')))
        return rpuTemp, apuTemp

    
    def getVolts(self):
        
        def vSFeq(num): 
            return ((num + 0.5) * 5.104) / 1000

        cmd = 'eVolts'
        pktTF = self.packetsend(self.TF, cmd)
        voltsTF = int.from_bytes(pktTF[0:2])

        voltsSFin = []
        voltsSFout = []

        endVal = self.endVal * 4 + 2
        for iter in range(2,endVal,4): 
            voltsSFin.append(int.from_bytes(pktTF[iter:iter+2]))
            voltsSFout.append(int.from_bytes(pktTF[iter+2:iter+4]))

        voltsTF = (voltsTF * 26.35) / 2 ** 12
        print('')
        print('TURFIO')
        print('Vin: {}V'.format(format(voltsTF, '.2f')))
        
        def vSFRF(num): 
            return (num / 2 ** 16) * 3
        
        for iter in range(len(voltsSFin)): 
            voltsSFin[iter] = (vSFeq(voltsSFin[iter]))
            voltsSFout[iter] = (vSFeq(voltsSFout[iter]))
            print('')
            print('SURF {}'.format(self.hextodec(self.SF[iter])))
            print('Vin: {}V'.format(format(voltsSFin[iter], '.2f')))
            print('Vout: {}V'.format(format(voltsSFout[iter], '.2f')))

            pktSF = self.packetsend(self.SF[iter], cmd)

            print('0.85V: {}V'.format(self.rounding(vSFRF(int.from_bytes(pktSF[0:2])))))
            print('1.8V: {}V'.format(self.rounding(vSFRF(int.from_bytes(pktSF[2:4])))))
            print('PS_MGTRAVTT (nominal 1.8V): {}V'.format(format(vSFRF(int.from_bytes(pktSF[4:6])), '.2f')))
            print('PS_MGTRAVCC (nominal 0.85V): {}V'.format(format(vSFRF(int.from_bytes(pktSF[6:8])), '.2f')))
            print('MGTAVTT (nominal 1.2V): {}V'.format(format(vSFRF(int.from_bytes(pktSF[8:10])), '.2f')))
            print('DDR_1V2 (nominal 1.2V): {}V'.format(self.rounding(vSFRF(int.from_bytes(pktSF[10:12])))))

        
    def rounding(self, num): 
        return format(num, '.2f')
        

    # Random utils in case
    def bintohex(self, num): 
        return hex(int(str(num), 2))

    def dectohex(self, num): 
        return hex(num + 128)

    def hextodec(self, num): 
        return int(str(num)) - 128

    def dectobin(self, num):
        return format(num, '08b')
        
      