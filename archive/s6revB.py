from pynq import Overlay, GPIO

from s6clk import SURF6Clock

import os
import subprocess
import time

MODULE_PATH = os.path.dirname(os.path.realpath(__file__))

def resolve_binary_path(bitfile_name):
    """ this helper function is necessary to locate the bit file during overlay loading"""
    if os.path.isfile(bitfile_name):
        return bitfile_name
    elif os.path.isfile(os.path.join(MODULE_PATH, bitfile_name)):
        return os.path.join(MODULE_PATH, bitfile_name)
    else:
        raise FileNotFoundError(f'Cannot find {bitfile_name}.')

class s6revB(Overlay):
    def __init__(self, bitfile_name='s6revB.bit', **kwargs):
        # Run lsmod command to get the loaded modules list
        output = subprocess.check_output(['lsmod'])
        # Check if "zocl" is present in the output
        if b'zocl' in output:
            # If present, remove the module using rmmod command
            rmmod_output = subprocess.run(['rmmod', 'zocl'])
            # Check return code
            assert rmmod_output.returncode == 0, "Could not restart zocl. Please Shutdown All Kernels and then restart"
            # If successful, load the module using modprobe command
            modprobe_output = subprocess.run(['modprobe', 'zocl'])
            assert modprobe_output.returncode == 0, "Could not restart zocl. It did not restart as expected"
        else:
            modprobe_output = subprocess.run(['modprobe', 'zocl'])
            # Check return code
            assert modprobe_output.returncode == 0, "Could not restart ZOCL!"

        super().__init__(resolve_binary_path(bitfile_name), **kwargs)

        self.clk = SURF6Clock()
        self.uartsel = GPIO(GPIO.get_gpio_pin(1),'out')
        self.clkreset = GPIO(GPIO.get_gpio_pin(3),'out')

    def clockReset(self):
        self.clkreset.write(1)
        self.clkreset.write(0)
        time.sleep(0.5)
        # have to reset the SDO behavior
        self.clk.surfClockInit()
        
