# s6revB is the ultrabasic firmware with only clock reset
from s6revB import s6revB

import time

print("Initializing SURF6 revB clocking system.")
# create object
dev = s6revB()
# reset clock
print("Resetting LMK clock.")
dev.clockReset()
# program it. By default it selects the external clock.
dev.clk.surfClock.configure("SURF6_LMK.txt")
# did it work?
st = dev.clk.surfClock.status()
print("Using external clock - status %2.2x" % st)
if st & 0x2 == 0:
    print("External clock not present!")
    print("Initializing Si5395 for clock forwarding")
    dev.clk.trenzClock.loadconfig("Si5395-RevA-SURFFWD-Registers.txt")
    # reconfigure to internal clock
    dev.clk.surfClock.writeRegister(0x2C, 0x80)
    time.sleep(0.1)
    st = dev.clk.surfClock.status()
    print("Switched to internal clock - status %2.2x" % st)
    if st & 0x2 == 0:
        print("Error configuring SURF6 clocking system!!")
else:
    print("Internal clock present, shutting down Si5395!")
    dev.clk.trenzClock.powerdown(True)
dev.uartsel.write(1)

