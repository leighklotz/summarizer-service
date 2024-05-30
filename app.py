#!/usr/bin/env python3

### Copyright 2024 Leigh Klotz <klotz@klotz.me>
###
### A web application that provides LLM-based text web page summarization for bookmarking
### services using Flask, subprocesses, and custom scripts.
###
### The application accepts GET and POST requests to summarize text with or without a custom prompt.
### It also provides a bookmarking service using the Scuttle tool.
### 
### flask run --host 0.0.0.0 --port 8080
### or ./app.py

from flask import Flask, request, redirect, render_template, jsonify
from subprocess import check_output
import json
from flask import Flask, url_for
import codecs

from config import *

app = Flask(__name__)

@app.route("/")
def index():
      return render_template("index.page", stats=get_stats())

@app.route("/scuttle", methods=["GET", "POST"])
def summarize_for_scuttle():
    if request.method == "POST":
        url = request.form.get('url')
        if url:
            return redirect(call_scuttle(url))
        else:
            stats = get_stats()
            return render_template("scuttle.page", data={}, stats=stats)
    else:
        url = request.form.get('url', '')
        stats = get_stats()
        return render_template("scuttle.page", data={'url': url}, stats=stats)

@app.route("/summarize", methods=["GET", "POST"])
def summarize_with_prompt():
    if request.method == "GET":
        prompt = 'Summarize' if not request.args.get('prompt') else request.args.get('prompt')
        data={
              'url': request.args.get('url', ''), 
              'prompt': prompt,
              'summary': '',
        }
        return render_template("summarize.page", data=data, stats=get_stats())
    elif request.method == "POST":
        url = request.form.get('url')
        prompt = request.form.get('prompt')
        if url and prompt:
            summary = summarize(url, prompt)
            print(f"{url=} {summary=}")
            data = {
                  'prompt': prompt,
                  'url': url,
                  'summary': summary,
            }
            response_text = render_template("summarize.page", data=data, stats=get_stats())
            return response_text
        else:
            return "Error: Missing required fields: url and prompt", 400

def call_scuttle(url):
    output = check_output([SCUTTLE_BIN, '--json', url]).decode('utf-8')
    print(f"*** output = {output}")
    result = json.loads(output)
    url = decode_scuttle_output(result)
    return url

import urllib.parse

def decode_scuttle_output(data):
    link = data['link']
    title = data['title']
    description = data['description']
    tags = list_to_comma_separated(data['keywords'])

    # use '+' for space and leave comma unescaped
    # link = urllib.parse.quote(link, safe='/(),:@!$-_.*+')
    # title = urllib.parse.quote(title, safe='/(),:@!$-_.*+')
    # description = urllib.parse.quote(description, safe='/(),:@!$-_.*+')
    # tags = urllib.parse.quote(tags, safe='/(),:@!$-_.*+')

    url = f"https://scuttle.klotz.me/bookmarks/klotz?action=add&address={link}&description={urllib.parse.quote(description)}&title={urllib.parse.quote(title)}&tags={tags}"
    return url

def list_to_comma_separated(keywords):
      if isinstance(keywords, list):
            return ', '.join(keywords)
      elif isinstance(keywords, str):
            return keywords
      else:
            raise ValueError("Not a string or list of strings", keywords)

def summarize(url, prompt):
      return check_output([SUMMARIZE_BIN, url, prompt]).decode('utf-8')

def get_stats():
      nvfree = (check_output([NVFREE_BIN]).decode('utf-8') or "0").strip()
      model_name = (check_output([VIA_API_BIN, '--get-model-name']).decode('utf-8') or "Mistral?").strip()
      stats = { 'nvfree': nvfree, 'model_name': model_name }
      return stats


if __name__ == "__main__":
      app.run(host='0.0.0.0', port=8080)
