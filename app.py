#!/usr/bin/env python3

# Copyright 2024 Leigh Klotz
# A web application that provides LLM-based text web page summarization for bookmarking services using Flask, subprocesses, and custom scripts.

import os
from flask import Flask, request, redirect, render_template, jsonify
from subprocess import check_output
import json
import urllib.parse
from config import *

app = Flask(__name__)

class Card:
   def __init__(self):
       self.stats = self.get_stats()

   def get_stats(self):
      # Fetch stats from the system
      nvfree = (check_output([NVFREE_BIN]).decode('utf-8') or "0").strip()
      MODEL_TYPE=os.environ.get('MODEL_TYPE', 'Mistral')
      model_name = None

      if MODEL_TYPE == "via-api":
         model_name = ((check_output([VIA_API_BIN, '--get-model-name']).decode('utf-8') or "").strip())
         model_link = OPENAPI_UI_SERVER

      if not model_name:
         model_name = f"{MODEL_TYPE}?"
         model_link = LLAMAFILES_LINK

      stats = {'nvfree': nvfree, 'model_name': model_name, 'model_link': model_link }
      return stats

class HomeCard(Card):
   def __init__(self):
       super().__init__()

   def get_template(self):
       return render_template("cards/home/index.page", stats=self.stats)

class SummarizeCard(Card):
   def __init__(self, url=None, prompt='Summarize'):
       super().__init__()
       self.url = url
       self.prompt = prompt
       self.summary = ''

   def get_template(self):
       data = {'url': self.url, 'prompt': self.prompt, 'summary': self.summary}
       return render_template("cards/summarize/index.page", data=data, stats=self.stats)

   def process(self):
       if self.url:
          # Summarize the text from the URL using the provided prompt
          self.summary = check_output([SUMMARIZE_BIN, self.url, self.prompt]).decode('utf-8')


class ScuttleCard(Card):
   def __init__(self, url=None):
       super().__init__()
       self.url = url
       self.scuttle_url = None

   def get_template(self):
       return render_template("cards/scuttle/index.page", data={}, stats=self.stats)

   def process(self):
       if self.url:
           self.scuttle_url = self.decode_scuttle_output(self.call_scuttle(self.url))
           return redirect(self.scuttle_url)
       else:
          return self.get_template()

   def call_scuttle(self, url):
      output = check_output([SCUTTLE_BIN, '--json', url]).decode('utf-8')
      print(f"*** {url=} {output=}")
      try:
         result = json.loads(output)
      except:
         print(f"*** [ERROR] cannot parse output; try VIA_API_INHIBIT_GRAMMAR or USE_SYSTEM_ROLE")
         raise
      return result

   def decode_scuttle_output(self, data):
      # Decode the output from the Scuttle tool
      link = data['link']
      title = data['title']
      description = data['description']
      tags = self.list_to_comma_separated(data['keywords'])
      url = f"https://scuttle.klotz.me/bookmarks/klotz?action=add&address={link}&description={urllib.parse.quote(description)}&title={urllib.parse.quote(title)}&tags={tags}"
      return url

   def list_to_comma_separated(self, keywords):
      # Convert a list of keywords to a comma-separated string
      if isinstance(keywords, list):
         return ', '.join(keywords)
      elif isinstance(keywords, str):
         return keywords
      else:
         raise ValueError("Not a string or list of strings", keywords)

class ViaAPIModelCard(Card):
   LOAD_MODEL_FLAG = '--load-model'
   LIST_MODELS_FLAG = '--list-models'

   def __init__(self):
      self.stats = self.get_stats()
      self.model_name = None

   def get_models_list(self):
      # use shell via-api.sh to get the newline separated list of model names into an array of strings
      models_list = check_output([VIA_API_BIN, self.LIST_MODELS_FLAG]).decode('utf-8').split('\n')
      models_list = [ model_name.strip() for model_name in models_list ]
      return models_list

   def get_template(self):
      data = { 'models_list': self.get_models_list(), 'output': '' }
      return render_template("cards/via-api-model/index.page", data=data, stats=self.stats)

   def process(self):
      if self.model_name:
         # Summarize the text from the URL using the provided prompt
         output = check_output([VIA_API_BIN,
                                self.LOAD_MODEL_FLAG, self.model_name]).decode('utf-8')
         data = { 'models_list': self.get_models_list(), 'output': output }
         return render_template("cards/via-api-model/index.page", data=data, stats=self.stats)          

# Rest of the code remains the same. Here's the example of how you can use the cards:

@app.route("/")
def index():
   card = HomeCard()
   return card.get_template()

@app.route("/summarize", methods=["GET", "POST"])
def summarize_with_prompt():
   card = SummarizeCard()
   if request.method == "GET":
       card.url = request.args.get('url', '')
       card.prompt = request.args.get('prompt', '')
   elif request.method == "POST":
       card.url = request.form.get('url')
       card.prompt = request.form.get('prompt', '')
       card.process()
   return card.get_template()

@app.route("/scuttle", methods=["GET", "POST"])
def summarize_for_scuttle():
   card = ScuttleCard()
   if request.method == "POST":
       card.url = request.form.get('url')
       return card.process()
   else:
      return card.get_template()

@app.route("/via-api-model", methods=["GET", "POST"])
def via_api_model():
   card = ViaAPIModelCard()
   if request.method == "POST":
       card.model_name = request.form.get('model_name')
       return card.process()
   else:
      return card.get_template()

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8080)
