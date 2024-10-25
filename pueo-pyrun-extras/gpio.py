# stripped down version of PYNQ/pynq/gpio.py: zynqmp only
# we also fix the "you can't talk to MIO!!" stupidity
#   Copyright (c) 2016, Xilinx, Inc.
#   SPDX-License-Identifier: BSD-3-Clause
#   modified PSA 10/23/24

import os
import weakref

class _GPIO:
    def __init__(self, gpio_index, direction):
        if direction not in ('in', 'out'):
            raise ValueError("Direction should be in or out.")
        self.index = gpio_index
        self.direction = direction
        self.path = '/sys/class/gpio/gpio{}/'.format(gpio_index)
        if not os.path.exists(self.path):
            with open('/sys/class/gpio/export', 'w') as f:
                f.write(str(self.index))
        with open(self.path + 'direction', 'w') as f:
            f.write(self.direction)
    
    def read(self):
        if self.direction != 'in':
            raise AttributeError("Cannot read GPIO output.")
        
        with open(self.path + 'value', 'r') as f:
            return int(f.read())
    
    def write(self, value):
        if self.direction != 'out':
            raise AttributeError("Cannot write GPIO input.")
        if value not in (0, 1):
            raise ValueError("Can only write integer 0 or 1.")
        
        with open(self.path + 'value', 'w') as f:
            f.write(str(value))
        return
    
    def unexport(self):
        if os.path.exists(self.path):
            with open('/sys/class/gpio/unexport', 'w') as f:
                f.write(str(self.index))
    
    def is_exported(self):
        return os.path.exists(self.path)
    
_gpio_map = weakref.WeakValueDictionary()

class GPIO:
    # idiots
    _GPIO_MIN_EMIO_PIN = 78
    
    def __init__(self, gpio_index, direction):
        self._impl = None
        if gpio_index in _gpio_map:
            self._impl = _gpio_map[gpio_index]
            if self._impl and self._impl.is_exported() and \
               self._impl.direction != direction:
                   raise AttributeError("GPIO already in use in other direction")
        
        if not self._impl or not self._impl.is_exported():
            self._impl = _GPIO(gpio_index, direction)
            _gpio_map[gpio_index] = self._impl
    
    @property
    def index(self):
        return self._impl.index
    
    @property
    def direction(self):
        return self._impl.direction
    
    @property
    def path(self):
        return self._impl.path
    
    def read(self):
        return self._impl.read()
    
    def write(self, value):
        self._impl.write(value)
        
    def release(self):
        self._impl.unexport()
        del self._impl
        
    @staticmethod
    def get_gpio_base_path(target_label=None):
        valid_labels = []
        if target_label is not None:
            valid_labels.append(target_label)
        else:
            valid_labels.append('zynqmp_gpio')
        
        for root, dirs, files in os.walk('/sys/class/gpio'):
            for name in dirs:
                if 'gpiochip' in name:
                    with open(os.path.join(root, name, "label")) as fd:
                        label = fd.read().rstrip()
                    if label in valid_labels:
                        return os.path.join(root, name)
    
    @staticmethod
    def get_gpio_base(target_label=None):
        base_path = GPIO.get_gpio_base_path(target_label)
        if base_path is not None:
            return int(''.join(x for x in base_path if x.isdigit()))

    # so stupid
    @staticmethod
    def get_gpio_pin(gpio_user_index, gpio_type='EMIO'):
        if gpio_type == 'MIO':
            GPIO_OFFSET = 0
        else:
            GPIO_OFFSET = GPIO._GPIO_MIN_EMIO_PIN
        
        return (GPIO.get_gpio_base("zynqmp_gpio")+GPIO_OFFSET+gpio_user_index)
    
    @staticmethod
    def get_gpio_npins(gpio_type='EMIO'):
        base_path = GPIO.get_gpio_base_path("zynqmp_gpio")
        if base_path is not None:
            with open(os.path.join(base_path, "ngpio")) as fd:
                ngpio = fd.read().rstrip()
            raw = int(''.join(x for x in ngpio if x.isdigit()))
            # YES THIS IS DUMB
            if gpio_type == 'MIO':
                return raw - (raw - GPIO._GPIO_MIN_EMIO_PIN)
            else:
                return raw - GPIO._GPIO_MIN_EMIO_PIN
            