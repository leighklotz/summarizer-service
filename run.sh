#!/bin/bash

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE}")")"

gunicorn --workers=2 --log-level=info --access-logfile - -b 0.0.0.0:8080 --timeout 300 summarizer_service:app
