#!/bin/bash

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE}")")"
cd "${SCRIPT_DIR}"

export PATH="${PATH}":"${SCRIPT_DIR}"
source "${SCRIPT_DIR}/summarizer_service/config.py" 
export SECRET_KEY="$(openssl rand -hex 24)"

via --get-via || exit 1

gunicorn --workers=2 --log-level=info --access-logfile - -b ${LISTEN_HOST}:${PORT} --timeout 300 summarizer_service:app --limit-request-line 65535
