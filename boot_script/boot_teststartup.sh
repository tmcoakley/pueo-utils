#!/bin/bash

PYSURFHSKDIR="/usr/local/pysurfHskd"
PYSURFHSKD_NAME="testStartup.py"
PYSURFHSKD=${PYSURFHSKDIR}/${PYSURFHSKD_NAME}

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
