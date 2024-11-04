from pyzynqmp import PyZynqMP
from pathlib import Path

from importlib import import_module
import sys
from re import split as resplit

LIBFWDIR = "/lib/firmware/"
CURFW = LIBFWDIR + "current"

# we construct a monotonic version here so comparisons are easy
def _to_vrp(pfx, fn):
    bfn = os.path.basename(fn)
    vrp = list(map(int,resplit("v|r|p", bfn[len(pfx)+1:-4])[1:]))    
    return ( LIBFWDIR+bfn,
             vrp[0] << 12 + vrp[1] << 8 + vrp[2])

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("syntax: autoprog.py <fpga_bitstream_prefix> <python_config_class>")
        print("      : e.g. autoprog.py pueo_surf6 pysoceeprom.PySOCEEPROM")
        exit(1)

    pfx = sys.argv[1]
    cfg = sys.argv[2]
    # try handling cfg first
    ml = cfg.split('.')
    pymod = '.'.join(ml[:-1])
    pycls = ml[-1]
    m = import_module(pymod)
    c = getattr(m, pycls)
    prom = c()
    zynq = PyZynqMP()
    # if /lib/firmware/current doesn't exist, someone wants us to reload
    if zynq.state() != 'operating' or (not os.path.exists(CURFW)):
        current_fw = None
    else:
        cur_fn = os.readlink(CURFW)
        # parse PREFIX_vXrYpZ.bit into (X,Y,Z) as ints, then make monotonic (4096*X+256*Y+Z)
        # store as tuple of fn and version
        current_fw = _to_vrp(pfx, cur_fn)

    override = prom.override
    useThis = None
    if override:
        useThisFn = LIBFWDIR + pfx + "_" + override + ".bit"
        print("autoprog.py: override says to load %s" % fn)
        if not os.path.exists(fn):
            print("autoprog.py: override specified firmware DOES NOT EXIST! - falling back to most current")
        else:
            useThis = _to_vrp(pfx, useThisFn)
    if useThis is None:
        mostCurrent = None
        for p in Path(LIBFWDIR).glob('*.bit'):
            if not os.path.islink(p):
                thisFw = _to_vrp(pfx, p)
                if mostCurrent is None or thisFw[1] > mostCurrent[1]:
                    mostCurrent = thisFw
        if mostCurrent is None:
            print("autoprog.py: we have no firmware to load")
            exit(1)
        print("autoprog.py: most current firmware is %s" % mostCurrent[0])
        useThis = mostCurrent
    if current_fw[1] == useThis[1]:
        print("autoprog.py: current is %s: don't need to load %s" % (current_fw[0], useThis[0]))
        exit(0)
    else:
        print("autoprog.py: programming %s" % useThis[0])
        zynq.load(useThis[0])
        exit(0)
        
