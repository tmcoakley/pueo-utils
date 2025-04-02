import time 
from HskSerial import HskSerial, HskPacket

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


class HskParser:

    def __init__(self, cmd, dest, pkt): 

        self.cmd = cmd 
        self.dest = dest
        self.pkt = pkt

        if dest == 0x40 or dest == 0.48 or dest == 0x50 or dest == 0x58: 
            if cmd == 0x12: 
                self.tfIdentify()
            elif cmd == 0x10: 
                self.tfTemp()
            elif cmd == 0x11: 
                self.tfVolts()
        else: 
            if cmd == 0x12: 
                self.sfIdentify()
            elif cmd == 0x10: 
                self.sfTemp()
            elif cmd == 0x11: 
                self.sfVolts()
                
    def tfIdentify(self): 
        """Currently just returns what HSK software version"""

        vSoftware = int.from_bytes(self.pkt[0:1])
        bitSF = int.from_bytes(self.pkt[1:2])
        print('TURFIO HSK: v{}'.format(vSoftware))
        

    def sfIdentify(self): 
        
        splitvals = self.pkt.split(b'\x00')
            
        print("SURF ", self.surfID(iter))
        print('PS ID: ', splitvals[0].decode("utf-8"))
        print('MAC Addr: ', splitvals[1].decode("utf-8"))
        print('Petalinux Version: ', splitvals[2].decode("utf-8"))
        print('PUEO SQFS Version: ', splitvals[3].decode("utf-8"))
        print('Git Short Hash PUEO SQFS: ', splitvals[4].decode("utf-8"))
        print('PUEO SQFS Build Date: ', splitvals[5].decode("utf-8"))
        print("")
        
    
    def tfTemp(self):

        tfiotemp = int.from_bytes(self.pkt[0:2])
        srftemp = []
        for iter in range(2,16,2): 
            srftemp.append(int.from_bytes(self.pkt[iter:iter+2]))

        temparray = []
        tfiotemp = ((tfiotemp * 503.975) / 2 ** 12) - 273.15
        temparray.append(tfiotemp)
        
            
        for iter in range(len(srftemp)): 
            if srftemp[iter] != 0: 
                srftemp[iter] = format((( srftemp[iter] * 10 - 31880 ) / 42), '.2f')
                temparray.append(srftemp[iter])
                
            else:
                temparray.append('NaN')
                
            
            
            print("{}: {}C".format('TURFIO Slot 0', format(tfiotemp, '.2f')))
            print("")
            for iter in range(len(srftemp)): 
                print("SURF Slot {}: {}C".format(iter + 1, temparray[iter]))
                print("")
                
        return temparray
    
    def sfTemp(self): 

        def SFTempFunc(val): 
            return (val * 509.3140064) / 2 ** 16 - 280.23087870
        
        decimal_values = []
        for iter in range(0,4,2): 
            decimal_values.append(int.from_bytes(self.pkt[iter:iter+2]))
        
        for iter in range(0,len(decimal_values),2) : 
            rpuTemp = (SFTempFunc(decimal_values[iter]))
            apuTemp = (SFTempFunc(decimal_values[iter+1]))
        
        print("RPU: {}C".format(format(rpuTemp, '.2f')))
        print("APU: {}C".format(format(apuTemp, '.2f')))
                
        return rpuTemp, apuTemp

    
    def tfVolts(self):
        
        def vSFeq(num): 
            return ((num + 0.5) * 5.104) / 1000
        
        voltsTF = int.from_bytes(self.pkt[0:2])

        voltsTF = (voltsTF * 26.35) / 2 ** 12
        print('')
        print('TURFIO')
        print('Vin: {}V'.format(format(voltsTF, '.2f')))

        voltsSFin = []
        voltsSFout = []

        endVal = len(self.pkt)
        for iter in range(2,endVal,4): 
            voltsSFin.append(int.from_bytes(self.pkt[iter:iter+2]))
            voltsSFout.append(int.from_bytes(self.pkt[iter+2:iter+4]))

        for iter in range(len(voltsSFin)): 
            voltsSFin[iter] = (vSFeq(voltsSFin[iter]))
            voltsSFout[iter] = (vSFeq(voltsSFout[iter]))
            print('')
            print('SURF Slot {}'.format(iter))
            print('Vin: {}V'.format(format(voltsSFin[iter], '.2f')))
            print('Vout: {}V'.format(format(voltsSFout[iter], '.2f')))
    
    def sfVolts(self): 
        
        def vSFRF(num): 
            return (num / 2 ** 16) * 3

        print('0.85V: {}V'.format(self.rounding(vSFRF(int.from_bytes(self.pkt[0:2])))))
        print('1.8V: {}V'.format(self.rounding(vSFRF(int.from_bytes(self.pkt[2:4])))))
        print('PS_MGTRAVTT (nominal 1.8V): {}V'.format(format(vSFRF(int.from_bytes(self.pkt[4:6])), '.2f')))
        print('PS_MGTRAVCC (nominal 0.85V): {}V'.format(format(vSFRF(int.from_bytes(self.pkt[6:8])), '.2f')))
        print('MGTAVTT (nominal 1.2V): {}V'.format(format(vSFRF(int.from_bytes(self.pkt[8:10])), '.2f')))
        print('DDR_1V2 (nominal 1.2V): {}V'.format(self.rounding(vSFRF(int.from_bytes(self.pkt[10:12])))))

        
    # Random utils in case
    def rounding(self, num): 
        return format(num, '.2f')
       