#!/bin/bash

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE}")")"
. "${SCRIPT_DIR}/.venv/bin/activate"

cd "${SCRIPT_DIR}" || exit 1
source "${SCRIPT_DIR}/summarizer_service/config.py" 
export SECRET_KEY
SECRET_KEY="$(openssl rand -hex 24)"

model_name="$(${VIA_BIN} --get-model-name)"
case "$model_name" in
    *gemma-3*)
        export USE_SYSTEM_ROLE=1
        export TEMPERATURE=0.15
        export INFERENCE_MODE=instruct
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

gunicorn --workers=2 --log-level=info --access-logfile - -b "${LISTEN_HOST}":"${PORT}" --timeout 900 summarizer_service:app --limit-request-line 0
