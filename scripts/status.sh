#!/bin/bash

source ~/wip/answer/bin/commands/enable
source ~/wip/summarizer-service/summarizer_service/config.py

bx journalctl -l --user -u summarizer-service.service --since -15m | ask 'Read the following last 15 minutes of logs from the LLM-based summarizer and scuttle bookmark service and give status. If there is a recent error (parsing error, backtrace, network issues, Python failures, etc..), report on it and consult earlier logs for root cause analysis. Ignore any previous `status` output.' | answer

