#!/bin/bash

source ~/wip/answer/bin/commands/hx-bootstrap.sh && hx core
source ~/wip/summarizer-service/summarizer_service/config.py

# PROMPT="'Read the following last 15 minutes of journal and recent git commits for the LLM-based summarizer and scuttle bookmark service and give status. If there is a recent error (parsing error, backtrace, network issues, Python failures, etc..), report on it and consult earlier journal and commits for root cause analysis. Ignore any previous `status` output you find in the journal.'"
PROMPT="Output a status update:"

if [ "$1" = "--plain" ]; then
    bx journalctl -l --user -u summarizer-service.service --since -15m 
else
    ( 
        bx journalctl -l --user -u summarizer-service.service --since -15m;
        bx git log --oneline --since="1 hour ago";
    ) | 
        ask "$PROMPT" |
        answer
fi
