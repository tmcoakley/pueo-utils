#!/bin/bash

# reload systemd to pick up our service files
systemctl daemon-reload

PYSURFHSKDIR="/usr/local/pysurfHskd"
PYSURFHSKD_NAME="testStartup.py"
PYSURFHSKD=${PYSURFHSKDIR}/${PYSURFHSKD_NAME}

# we do need to tack on a subdir
export PYTHONPATH=$PYTHONPATH:$PYSURFHSKDIR

# dead duplicate of what's in pueo-squashfs
catch_term() {
    echo "termination signal caught"
    kill -TERM "$waitjob" 2>/dev/null
}

# automatically program the FPGA, weee!
autoprog.py pysoceeprom.PySOCEEPROM

# here's where pysurfHskd would run
$PYSURFHSKD &
waitjob=$!

wait $waitjob
RETVAL=$?

exit $RETVAL
