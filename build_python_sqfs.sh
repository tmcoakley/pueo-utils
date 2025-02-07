#!/usr/bin/env bash

# this builds the python.sqfs file that gets
# merged with pueo.sqfs. python.sqfs contains
# the PyRun stuff and is much less likely to
# change and also huuuge

# this one is a lot simpler than the pueo sqfs build
# right now, since it's just "store all these prebuilt 
# binaries and libraries"
if [ "$#" -ne 1 ] ; then
    echo "usage: build_python_sqfs.sh <destination filename>"
    exit 1
fi

DEST=$1
WORKDIR=$(mktemp -d)

cp -R python_squashfs/* ${WORKDIR}
mksquashfs ${WORKDIR} $1 -noappend
rm -rf ${WORKDIR}
