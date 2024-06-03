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

class BaseCard:
   def __init__(self, template):
       self.template = template
       self.stats = self.get_stats()

   def get_template(self):
      return render_template(self.template, card=self)

   def process(self):
       raise NotImplementedError

   def get_model_info(self):
      model_type=os.environ.get('MODEL_TYPE', DEFAULT_MODEL_TYPE)
      model_name = ''
      model_link = ''
      if model_type == "via-api":
         model_name = (check_output([VIA_API_BIN, GET_MODEL_NAME_FLAG]).decode('utf-8') or "").strip()
         model_link = OPENAPI_UI_SERVER
      if not model_name:
         model_name = f"{model_type}?"
         model_link = LLAMAFILES_LINK
         return (model_type, model_name, model_link)

   def get_nvfree(self):
      return (check_output([NVFREE_BIN]).decode('utf-8') or "0").strip()

   def get_stats(self):
      # Fetch stats from the system
      nvfree = self.get_nvfree()
      model_type, model_name, model_link = self.get_model_info()
      stats = {'nvfree': nvfree, 'model_name': model_name, 'model_link': model_link }
      return stats

class HomeCard(BaseCard):
   def __init__(self):
       super().__init__(template='cards/home/index.page')

class SummarizeCard(BaseCard):
   def __init__(self):
      super().__init__(template='cards/summarize/index.page')
      self.url = ''
      self.prompt = 'Summarize'
      self.summary = ''

   def process(self):
      if self.url:
         if not (self.url.startswith('http://') or self.url.startswith('https://')):
            raise ValueError("Unsupported URL type", self.url)
         self.summary = check_output([SUMMARIZE_BIN, self.url, self.prompt]).decode('utf-8')
      return self.get_template()

class ScuttleCard(BaseCard):
   def __init__(self):
      super().__init__(template='cards/scuttle/index.page')
      self.url = ''

   def process(self):
      if self.url:
         if not (self.url.startswith('http://') or self.url.startswith('https://')):
            raise ValueError("Unsupported URL type", url)
         scuttle_url = self.decode_scuttle_output(self.call_scuttle(self.url))
         return redirect(scuttle_url)
      else:
         return self.get_template()

   def call_scuttle(self, url):
      if not (url.startswith('http://') or url.startswith('https://')):
         raise ValueError("Unsupported URL type", url)
      output = check_output([SCUTTLE_BIN, '--json', url]).decode('utf-8')
      print(f"*** {url=} {output=}")
      try:
         result = json.loads(output)
      except json.JSONDecodeError:
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

class ViaAPIModelCard(BaseCard):
   LOAD_MODEL_FLAG = '--load-model'
   LIST_MODELS_FLAG = '--list-models'

   def __init__(self):
      super().__init__(template='cards/via-api-model/index.page')
      self.model_name = ''
      self.models_list = self.get_models_list()
      self.output = ''

   def get_models_list(self):
      # use shell via-api.sh to get the newline separated list of model names into an array of strings
      models_list = check_output([VIA_API_BIN, self.LIST_MODELS_FLAG]).decode('utf-8').split('\n')
      models_list = [ model_name.strip() for model_name in models_list ]
      return models_list

   def process(self):
      if self.model_name:
         self.output = check_output([VIA_API_BIN, self.LOAD_MODEL_FLAG, self.model_name]).decode('utf-8')
      return self.get_template()

def card_router(card_constructor, params):
   card = card_constructor()
   for param in params:
      setattr(card, param, request.args.get(param, request.form.get(param, '')))
      if request.method == "POST":
         card.process()
   return card.get_template()
   
@app.route("/")
def home():
   return card_router(HomeCard, [])

@app.route("/summarize", methods=["GET", "POST"])
def summarize_with_prompt():
   return card_router(SummarizeCard, ['url', 'prompt'])

@app.route("/scuttle", methods=["GET", "POST"])
def summarize_for_scuttle():
   return card_router(ScuttleCard, ['url'])

@app.route("/via-api-model", methods=["GET", "POST"])
def via_api_model():
   return card_router(ViaAPIModelCard, ['model_name'])

if __name__ == "__main__":
   app.run(host=LISTEN_HOST, port=PORT)
