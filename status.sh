#!/bin/bash

source ~/.bash.d/aliases.sh
source ~/wip/summarizer-service/summarizer_service/config.py
#whatsty summarizer | ${HELP_BIN} 'Read the following screen capture (status.sh) from the LLM-based summarizer and scuttle bookmark service and give status:'

${BASHBLOCK_BIN} journalctl -l --user -u summarizer-service.service -e | ${HELP_BIN} 'Read the following logs from the LLM-based summarizer and scuttle bookmark service and give status. Use the most recent log lines as the current status, and consult earlier logs for root cause analysis only if recent requests are failing.'
