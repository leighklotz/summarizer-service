#!/bin/bash

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE}")")"
. "${SCRIPT_DIR}/.venv/bin/activate"

cd "${SCRIPT_DIR}" || exit 1
source "${SCRIPT_DIR}/summarizer_service/config.py" 
export SECRET_KEY="$(openssl rand -hex 24)"

# gemma-3: move these elsewhere
export USE_SYSTEM_ROLE=1
export TEMPERATURE=0.15
export INFERENCE_MODE=instruct

${VIA_BIN} --get-via || exit 1

gunicorn --workers=2 --log-level=info --access-logfile - -b ${LISTEN_HOST}:${PORT} --timeout 900 summarizer_service:app --limit-request-line 0
