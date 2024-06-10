#!/bin/bash

### 
### SCRIPT_DIR=$(dirname $(realpath "${BASH_SOURCE}"))
### 
### # Use a consistent date syntax for YYYYMMDD-HHMMSS
### stamp="$(date +"%Y%m%d-%H%M%S")"
### 
### # Ensure the log directory exists
### if [ ! -d "/tmp/summarizer" ]; then
###    mkdir -p "/tmp/summarizer"
### fi
### 
### # Use double quotes around file name to handle spaces in log file names
### ${SCRIPT_DIR}/app.py 2>&1 | tee >> "/tmp/summarizer/${stamp}-$$.log"
###

gunicorn -b 0.0.0.0:8080 summarizer_service:app
