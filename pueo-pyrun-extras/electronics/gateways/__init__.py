import platform
from .buspirate import *
if "Linux" in platform.system():
    from .linuxdevice import *
from .mock import *
