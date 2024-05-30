#!/usr/bin/env python3

# Copyright 2024 Leigh Klotz
# A web application that provides LLM-based text web page summarization for bookmarking services using Flask, subprocesses, and custom scripts.

from flask import Flask, request, redirect, render_template, jsonify
from subprocess import check_output
import json
import urllib.parse
from config import *

app = Flask(__name__)

def get_stats():
  # Fetch stats from the system
  nvfree = (check_output([NVFREE_BIN]).decode('utf-8') or "0").strip()
  model_name = (check_output([VIA_API_BIN, '--get-model-name']).decode('utf-8') or "Mistral?").strip()
  stats = {'nvfree': nvfree, 'model_name': model_name}
  return stats

def summarize(url, prompt):
  # Summarize the text from the URL using the provided prompt
  return check_output([SUMMARIZE_BIN, url, prompt]).decode('utf-8')

def call_scuttle(url):
   output = check_output([SCUTTLE_BIN, '--json', url]).decode('utf-8')
   print(f"*** {output=}")
   result = json.loads(output)
   return result

def decode_scuttle_output(data):
  # Decode the output from the Scuttle tool
  link = data['link']
  title = data['title']
  description = data['description']
  tags = list_to_comma_separated(data['keywords'])
  url = f"https://scuttle.klotz.me/bookmarks/klotz?action=add&address={link}&description={urllib.parse.quote(description)}&title={urllib.parse.quote(title)}&tags={tags}"
  return url

def list_to_comma_separated(keywords):
  # Convert a list of keywords to a comma-separated string
  if isinstance(keywords, list):
      return ', '.join(keywords)

  elif isinstance(keywords, str):
     return keywords
  else:
     raise ValueError("Not a string or list of strings", keywords)

@app.route("/")
def index():
  return render_template("index.page", stats=get_stats())

@app.route("/scuttle", methods=["GET", "POST"])
def summarize_for_scuttle():
  if request.method == "POST":
     url = request.form.get('url')
     if url:
         scuttle_url = decode_scuttle_output(call_scuttle(url))
         print(f"*** {scuttle_url=}")
         return redirect(scuttle_url)
  stats = get_stats()
  return render_template("scuttle.page", data={}, stats=stats)

@app.route("/summarize", methods=["GET", "POST"])
def summarize_with_prompt():
  if request.method == "GET":
     prompt = request.args.get('prompt', 'Summarize')
     data = {'url': request.args.get('url', ''), 'prompt': prompt, 'summary': '', }
     return render_template("summarize.page", data=data, stats=get_stats())
  elif request.method == "POST":
     url = request.form.get('url')
     prompt = request.form.get('prompt')
     if url and prompt:
         summary = summarize(url, prompt)
         data = {'prompt': prompt, 'url': url, 'summary': summary, }
         return render_template("summarize.page", data=data, stats=get_stats())
     else:
         return "Error: Missing required fields: url and prompt", 400

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8080)
