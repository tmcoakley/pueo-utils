#!/bin/bash

# create a tarball of the necessary files for standalone hw_server
# this ONLY WORKS if you already have the Digilent adept runtime installed
# https://lp.digilent.com/complete-adept-runtime-download
# the Xilinx Platform Cable and Xilinx FTDI stuff is going to require
# other crap
# just use the Digilent stuff if even remotely possible, it's by far the
# cleanest way. Digilent has nicely packaged Linux stuff.

tar --transform="s,bin/unwrapped/lnx64.o,hw_server," -cf standalone_hw_server.tar bin/unwrapped/lnx64.o/hw_server
tar --transform="s,lib/lnx64.o,hw_server," -rf standalone_hw_server.tar lib/lnx64.o/libxftdi.so

gzip standalone_hw_server.tar
