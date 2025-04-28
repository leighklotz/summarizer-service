#!/bin/bash

source ~/.bash.d/aliases.sh
source ~/wip/summarizer-service/summarizer_service/config.py
whatsty summarizer | ${HELP_BIN} 'Read the following screen capture (status.sh) from the LLM-based summarizer and scuttle bookmark service and give status:'
