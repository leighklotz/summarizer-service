#!/bin/bash -x

screen -S summarizer -X quit
ps -efww | grep -i gunicorn | grep python3 | awk '{print $2}' | xargs kill -9
