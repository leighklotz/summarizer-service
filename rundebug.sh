#!/bin/bash

flask --app summarizer_service:app --debug run --host=127.0.0.1 --port=8080
