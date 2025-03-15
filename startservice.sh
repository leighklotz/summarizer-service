#!/bin/bash -x
VIA=api
screen -dmS summarizer bash -c '/home/$LOGNAME/wip/summarizer-service/run.sh; tail -f /dev/null'

