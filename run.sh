#!/bin/bash

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE}")")"
cd "${SCRIPT_DIR}"

export PATH="${PATH}":"${SCRIPT_DIR}"
export SECRET_KEY="$(openssl rand -hex 24)"
gunicorn --workers=2 --log-level=info --access-logfile - -b 0.0.0.0:8080 --timeout 300 summarizer_service:app --limit-request-line 65535
