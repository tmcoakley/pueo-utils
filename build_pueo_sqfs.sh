#!/usr/bin/env bash

# individual single-file python modules
PYTHON_SINGLE_FILES="pysoceeprom/pysoceeprom.py \
	        pyzynqmp/pyzynqmp.py"
# multi-file python modules wrapped in directories
PYTHON_DIRS="pyrfdc/pyrfdc/ \
	       s6clk/ "
# scripts
SCRIPTS="scripts/build_squashfs \
         scripts/autoprog.py "

# name of the autoexclude file
SURFEXCLUDE="pueo_sqfs_surf.exclude"

if [ "$#" -ne 1 ] ; then
    echo "usage: build_pueo_sqfs.sh <destination filename>"
    exit 1
fi

DEST=$1
WORKDIR=$(mktemp -d)

cp -R base_squashfs/* ${WORKDIR}
# autocreate the exclude
echo "... __pycache__/*" > ${WORKDIR}/share/${SURFEXCLUDE}
for f in `find python_squashfs -type f` ; do
    FN=`basename $f`
    FULLDIR=`dirname $f`
    DIR=`basename $FULLDIR`
    echo ${DIR}/${FN} >> ${WORKDIR}/share/${SURFEXCLUDE}
done
    
for f in ${PYTHON_SINGLE_FILES} ; do
    cp $f ${WORKDIR}/pylib/
done
for d in ${PYTHON_DIRS} ; do
    cp -R $d ${WORKDIR}/pylib/
done

# SURF build is special, it extracts stuff
bash pueo-python/make_surf.sh ${WORKDIR}/pylib/

for s in ${SCRIPTS} ; do
    cp $s ${WORKDIR}/bin/
done

# avoid gitignores and pycaches
mksquashfs ${WORKDIR} $1 -wildcards -ef pueo_sqfs.exclude
rm -rf ${WORKDIR}

