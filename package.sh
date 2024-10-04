#!/bin/bash

# create a tarball of the necessary files for standalone xsdb

tar --transform="s,bin/unwrapped/lnx64.o,xsdb," -cf standalone_xsdb.tar bin/unwrapped/lnx64.o/rdi_xsdb
tar --transform="s,lib/lnx64.o,xsdb," -rf standalone_xsdb.tar lib/lnx64.o/libtcl8.5.so
tar --transform="s,lib/lnx64.o,xsdb," -rf standalone_xsdb.tar lib/lnx64.o/libtcltcf.so
tar --transform="s,tps/tcl,xsdb/tclLib," -rf standalone_xsdb.tar tps/tcl/tcl8.5
tar --transform="s,scripts/xsdb,xsdb/tclLib," -rf standalone_xsdb.tar scripts/xsdb/xsdb
tar --transform="s,scripts/xsdb,xsdb/tclLib," -rf standalone_xsdb.tar scripts/xsdb/tcf

tar --transform="s,tps/tcl/tcllib1.11.1,xsdb/tclLib," -rf standalone_xsdb.tar tps/tcl/tcllib1.11.1/cmdline
tar --transform="s,tps/tcl/tcllib1.11.1,xsdb/tclLib," -rf standalone_xsdb.tar tps/tcl/tcllib1.11.1/control
tar --transform="s,tps/tcl/tcllib1.11.1,xsdb/tclLib," -rf standalone_xsdb.tar tps/tcl/tcllib1.11.1/fileutil
tar --transform="s,tps/tcl/tcllib1.11.1,xsdb/tclLib," -rf standalone_xsdb.tar tps/tcl/tcllib1.11.1/json
tar --transform="s,tps/tcl/tcllib1.11.1,xsdb/tclLib," -rf standalone_xsdb.tar tps/tcl/tcllib1.11.1/uuid
tar --transform="s,scripts/xsdb/xsdb,xsdb," -rf standalone_xsdb.tar scripts/xsdb/xsdb/cmdlist
gzip standalone_xsdb.tar
