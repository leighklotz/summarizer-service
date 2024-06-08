#!/bin/bash

# Get the script directory from $0
SCRIPT_DIR="$( dirname "$0" )"

cd "${SCRIPT_DIR}"

# Use a consistent date syntax for YYYYMMDD-HHMMSS
stamp="$(date +"%Y%m%d-%H%M%S")"

# Ensure the log directory exists
if [ ! -d "/tmp/summarizer" ]; then
   mkdir -p "/tmp/summarizer"
fi

# Use double quotes around file name to handle spaces in log file names
./app.py 2>&1 | tee >> "/tmp/summarizer/${stamp}-$$.log"
