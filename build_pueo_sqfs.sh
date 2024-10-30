#!/usr/bin/env bash

# individual single-file python modules
PYTHON_SINGLE_FILES="pysoceeprom/pysoceeprom.py \
	        pyzynqmp/pyzynqmp.py"
# multi-file python modules wrapped in directories
PYTHON_DIRS="pyrfdc/pyrfdc/ \
	       s6clk/ "

SCRIPTS="scripts/build_squashfs"

if [ "$#" -ne 1 ] ; then
    echo "usage: build_pueo_sqfs.sh <destination filename>"
    exit 1
fi

DEST=$1
WORKDIR=$(mktemp -d)

cp -R base_squashfs/* ${WORKDIR}
for f in ${PYTHON_SINGLE_FILES} ; do
    cp $f ${WORKDIR}/pylib/
done
for d in ${PYTHON_DIRS} ; do
    cp -R $d ${WORKDIR}/pylib/
done

# SURF build is special, it extracts stuff
cd pueo-python && bash pueo-python/make_surf.sh ${WORKDIR}/pylib/

for s in ${SCRIPTS} ; do
    cp $s ${WORKDIR}/bin/
done

mksquashfs ${WORKDIR} $1
rm -rf ${WORKDIR}

