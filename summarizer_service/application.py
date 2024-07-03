#!/usr/bin/env python3

# Copyright 2024 Leigh Klotz
# A web application that provides LLM-based text web page summarization for bookmarking services using Flask, subprocesses, and custom scripts.

import os
from flask import Flask, request, redirect, render_template, jsonify, url_for
from subprocess import check_output, CalledProcessError
import json
import urllib.parse
from .config import *

app = Flask(__name__)

def create_app():
   return app

class BaseCard:
   VIA_FLAG = '--via'
   API_FLAG = 'api'
   GET_MODEL_NAME_FLAG = '--get-model-name'

   def __init__(self, template, params):
       self.template = template
       self.params = params
       self.stats = self.get_stats()

   def get_template(self):
      return render_template(self.template, card=self)

   def process(self):
       raise NotImplementedError

   def _get_model_info(self):
      via = os.environ.get('VIA', DEFAULT_VIA)
      model_type = os.environ.get('MODEL_TYPE', DEFAULT_MODEL_TYPE)
      return {
         'via': via,
         'model_type': model_type,
         'model_name': self._get_via_script(VIA_BIN, self.VIA_FLAG, via, self.GET_MODEL_NAME_FLAG) or f"{model_type}?",
         'model_link': self._determine_model_link(via, model_type)
      }

   def _get_via_script(self, script_bin, *args):
      try:
         return (check_output([script_bin] + list(args)).decode('utf-8') or "").strip()
      except CalledProcessError:
         return None

   def _determine_model_link(self, via, model_type):
      return OPENAPI_UI_SERVER if via == "api" else LLAMAFILES_LINK

   def get_stats(self):
      nvfree = self._get_via_script(NVFREE_BIN) or "0"
      stats = {'nvfree': nvfree}
      model_info = self._get_model_info()
      stats.update(model_info)
      return stats

class HomeCard(BaseCard):
   def __init__(self):
       super().__init__(template='cards/home/index.page', params=[])

class SummarizeCard(BaseCard):
   def __init__(self):
      super().__init__(template='cards/summarize/index.page', params=['url', 'prompt'])
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
      super().__init__(template='cards/scuttle/index.page', params=['url'])
      self.url = ''

   def process(self):
      if self.url:
         if not (self.url.startswith('http://') or self.url.startswith('https://')):
            raise ValueError("Unsupported URL type", self.url)
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
      super().__init__(template='cards/via-api-model/index.page', params=['model_name', 'output'])
      self.model_name = ''
      self.output = ''
      self.models_list = self.get_models_list()

   def get_models_list(self):
      # use shell via --api to get the newline separated list of model names into an array of strings
      models_list = check_output([VIA_BIN, self.VIA_FLAG, self.API_FLAG, self.LIST_MODELS_FLAG]).decode('utf-8').split('\n')
      models_list = [ model_name.strip() for model_name in models_list ]
      return models_list

   def process(self):
      if self.model_name:
         self.output = check_output([VIA_BIN, self.VIA_FLAG, self.API_FLAG, self.LOAD_MODEL_FLAG, self.model_name]).decode('utf-8')
      return self.get_template()

@app.route("/")
def home():
   return redirect(url_for('home_card'))

def card_router(card_constructor):
   card = card_constructor()
   for param in card.params:
      setattr(card, param, request.args.get(param, request.form.get(param, '')))
   if request.method == "POST":
      result = card.process()
      if result is not None: return result
   return card.get_template()
   
@app.route("/card/home")
def home_card():
   return card_router(HomeCard)

@app.route("/card/summarize", methods=["GET", "POST"])
def summarize_with_prompt():
   return card_router(SummarizeCard)

@app.route("/card/scuttle", methods=["GET", "POST"])
def summarize_for_scuttle():
   return card_router(ScuttleCard)

@app.route("/card/via-api-model", methods=["GET", "POST"])
def via_api_model():
   return card_router(ViaAPIModelCard)

# deprecated
@app.route("/scuttle", methods=["GET", "POST"])
def old_scuttle():
   return redirect(url_for('summarize_for_scuttle'))

@app.route("/summarize", methods=["GET", "POST"])
def old_summarize():
   return redirect(url_for('summarize_with_prompt'))


def main():
   app.run(host=LISTEN_HOST, port=PORT)

if __name__ == "__main__":
   main()
