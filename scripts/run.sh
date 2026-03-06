#!/bin/bash -e

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE}")")"
. "${SCRIPT_DIR}/.venv/bin/activate"

# Absolute path to the project root
PROJECT_ROOT="$(cd "$(dirname "${SCRIPT_DIR}")/.." && pwd)"

cd "${SCRIPT_DIR}" || exit 1
source "${PROJECT_ROOT}/summarizer_service/config.py"
export SECRET_KEY
SECRET_KEY="$(openssl rand -hex 24)"

model_name="$(${VIA_BIN} --get-model-name)"
case "$model_name" in
    *gemma*3*)
        export ADD_BOS=""       # do not use unset for ADD_BOS                  
        export INFERENCE_MODE=instruct
        export KEEP_PROMPT_TEMP_FILE=ERRORS
        export MIN_P=0.05
        export REPEAT_PENALTY=1.0
        export SEED=123
        export TEMPERATURE=0.8
        export TOP_K=40
        export TOP_P=0.95
        export VIA=api
        unset INHIBIT_GRAMMAR
        unset USE_SYSTEM_ROLE
        unset VIA_API_INHIBIT_GRAMMAR
        ;;
    *Magistral*)
        unset USE_SYSTEM_ROLE
        export TEMPERATURE=0.70
        export TOP_P=0.95
        export INFERENCE_MODE=instruct
        ;;
    gpt-oss*)
        unset USE_SYSTEM_ROLE
        export temperature=1.0
        export top_p=1.0
        export top_k=0
        export INFERENCE_MODE=instruct
        ;;
    *)
        echo "* Unknown model $model_name"
        exit 1
esac

gunicorn --workers=2 --log-level=info --access-logfile - -b "${LISTEN_HOST}":"${PORT}" --timeout 900 "${PROJECT_ROOT}/summarizer_service:app" --limit-request-line 0
