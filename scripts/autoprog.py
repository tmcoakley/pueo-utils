from pyzynqmp import PyZynqMP
from pathlib import Path

from importlib import import_module
import sys
import time
from re import split as resplit

LIBFWDIR = "/lib/firmware/"
CURFW = LIBFWDIR + "current"
NXTFW = LIBFWDIR + "next"
SLOTFW = [ LIBFWDIR + "0", LIBFWDIR + "1", LIBFWDIR + "2" ]

# reworked entirely to use slot system
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("syntax: autoprog.py <python_config_class>")
        print("      : e.g. autoprog.py pysoceeprom.PySOCEEPROM")
        exit(1)

    cfg = sys.argv[1]
    # try handling cfg first
    ml = cfg.split('.')
    pymod = '.'.join(ml[:-1])
    pycls = ml[-1]
    m = import_module(pymod)
    c = getattr(m, pycls)
    zynq = PyZynqMP()

    # fetch load order config
    bsLoadOrder = None
    with c(mode='AUTO') as prom:
        # if the prom specifies an override, immediately eliminate it in the EEPROM
        # and kill it in the cache so that next time it loads the fallback
        bsLoadOrder = prom.bsLoadOrder
        if len(bsLoadOrder) == 1 and bsLoadOrder[0] != 0:
            print("autoprog.py: override loading slot %d - next attempt will use 0" % bsLoadOrder[0])
            prom.bsLoadOrder = [0]
            prom.save()
            prom.updateEeprom()
    
    # are we running currently
    if zynq.state() != 'operating' or (not os.path.islink(CURFW)):
        current_fw = None
    else:
        current_fw = os.readlink(CURFW)
    # what's the next pointer
    if not os.path.islink(NXTFW):
        next_fw = None
    else:
        next_fw = os.readlink(NXTFW)

    # what are the slot pointers
    slot = [ None, None, None ]
    for slotNum in range(3):
        if os.path.islink(SLOTFW[slotNum]):
            slot[slotNum] = os.readlink(SLOTFW[slotNum])

    # if the next pointer is the current pointer and they're not None, we do _nothing_
    # bmForceReload is implemented by unlinking the 'current' pointer in software
    if current_fw == next_fw and current_fw:
        print("autoprog.py: current/next both %s : skipping load" % current_fw)
        exit(0)
    # if there is a next pointer, use it
    if next_fw is not None:
        loadOk = False
        try:
            print("autoprog.py: Programming %s" % next_fw)
            zynq.load(next_fw)
            loadOk = True
        except Exception as e:
            print("autoprog.py: Loading %s threw an exception:" % next_fw, repr(e))
    else:
        loadOk = False
        # run the load order
        for s in bsLoadOrder:
            try:
                print("autoprog.py: Programming %s" % slot[s])
                zynq.load(slot[s])
                loadOk = True
            except Exception as e:
                print("autoprog.py: Loading %s threw an exception:" % slot[s], repr(e))
            if loadOk:
                break
    if not loadOk:
        print("autoprog.py: Falling back to %s" % slot[0])
        try:
            zynq.load(slot[0])
        except Exception as e:
            print("autoprog.py: Loading %s threw an exception:" % slot[s], repr(e))
            exit(1)
    # by default next is current
    if os.path.islink(CURFW):
        c = os.readlink(CURFW)
        if os.path.exists(NXTFW) or os.path.islink(NXTFW):            
            os.remove(NXTFW)
        os.symlink(c, NXTFW)        
    exit(0)
    
    
