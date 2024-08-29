#!/bin/bash

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE}")")"

# export SECRET_KEY="$(python3 -c 'import os; print(os.urandom(24).hex())')"
export SECRET_KEY="$(openssl rand -hex 24)"
gunicorn --workers=2 --log-level=info --access-logfile - -b 0.0.0.0:8080 --timeout 300 summarizer_service:app 
