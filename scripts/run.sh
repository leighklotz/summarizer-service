#!/bin/bash -e

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE}")")"
. "${SCRIPT_DIR}/.venv/bin/activate"
cd "${SCRIPT_DIR}" || exit 1

# Absolute path to the project root
PROJECT_ROOT="$(cd "$(dirname "${SCRIPT_DIR}")" && pwd)"
export PYTHONPATH="${PROJECT_ROOT}"

source "${PROJECT_ROOT}/summarizer_service/config.py"
export SECRET_KEY
SECRET_KEY="$(openssl rand -hex 24)"

source ~/wip/answer/bin/commands/hx-bootstrap.sh && hx core

gunicorn --workers=2 --log-level=info --access-logfile - -b "${LISTEN_HOST}":"${PORT}" --timeout 900 "summarizer_service:app" --limit-request-line 0
