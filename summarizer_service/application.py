#!/usr/bin/env python3
# Copyright 2024 Leigh Klotz
# A web application that provides LLM-based text web page summarization for bookmarking services using Flask, subprocesses, and custom scripts.

import os
from flask import Flask, request, redirect, render_template, jsonify, url_for, session
from subprocess import check_output, CalledProcessError
import json
import yaml
import base64
from urllib.parse import quote_plus
from .config import *

app = None

### main
def create_app():
   global app
   if app is None:
      app = Flask(__name__)
      # todo: preserve this in config between runs
      app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
   return app

app = create_app()

class BaseCard:
   VIA_FLAG = '--via'
   API_FLAG = 'api'
   GET_MODEL_NAME_FLAG = '--get-model-name'

   def __init__(self, template, params=[]):
       self.template = template
       self.params = params
       self.stats = self.get_stats()

   def get_template(self):
      return render_template(self.template, card=self)

   def pre_process(self):
      for param in self.params:
         setattr(self, param, request.args.get(param, request.form.get(param, '')))

   def process(self):
      return self.get_template()

   def form(self):
      return []

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

class URLCard(BaseCard):
   def __init__(self, template, params=[]):
      self.url = ''
      super().__init__(template=template, params=(params + ['url']))

   def form(self):
      return super().form() + [
         { 'name':"url", 'label':"Enter URL:", 'type':"url", 'required':"required", 'value': self.url }, 
      ]

   def pre_process(self):
      super().pre_process()
      if self.url:
         session['url'] = self.url
      elif 'url' in session:
         self.url = session['url']
      if self.url:
         if not (self.url.startswith('http://') or self.url.startswith('https://')):
            raise ValueError("Unsupported URL type", self.url)

   def process(self):
      if self.url:
         if not (self.url.startswith('http://') or self.url.startswith('https://')):
            raise ValueError("Unsupported URL type", self.url)
      return None
                                    
class SummarizeCard(URLCard):
   def __init__(self):
      super().__init__(template='cards/summarize/index.page', params=['prompt'])
      self.prompt = 'Summarize'
      self.summary = '' 

   def form(self):
      return super().form() + [
         { 'name':"prompt", 'label':"Prompt:", 'type':"text", 'list':"prompts" }
      ]

   def process(self):
      super().process()
      self.summary = check_output([SUMMARIZE_BIN, self.url, self.prompt]).decode('utf-8')
      return self.get_template()

class ScuttleCard(URLCard):
   def __init__(self):
      super().__init__(template='cards/scuttle/index.page')

   def process(self):
      super().process()
      scuttle_url = self.decode_scuttle_output(self.call_scuttle(self.url))
      if scuttle_url:
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
      url = f"https://scuttle.klotz.me/bookmarks/klotz?action=add&address={quote_plus(link)}&description={quote_plus(description)}&title={quote_plus(title)}&tags={quote_plus(tags)}"
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
      super().process()
      if self.model_name:
         self.output = check_output([VIA_BIN, self.VIA_FLAG, self.API_FLAG, self.LOAD_MODEL_FLAG, self.model_name]).decode('utf-8')
      return self.get_template()

class HomeCard(BaseCard):
   def __init__(self):
       super().__init__(template='cards/home/index.page')

class ErrorCard(BaseCard):
   def __init__(self):
       super().__init__(template='cards/error/index.page')

### Card Routing
def card_router(card_constructor):
   card = card_constructor()
   card.pre_process()
   if request.method == "POST":
      result = card.process()
      if result is not None:
         return result
      else:
         return card.get_template()
   else:
      return card.get_template()
   
CARDS = {
   'home': HomeCard,
   'summarize': SummarizeCard,
   'scuttle': ScuttleCard,
   'via-api-model': ViaAPIModelCard,
   'error': ErrorCard
}

### Card ROutes
@app.route("/")
def home():
   return redirect(url_for('route_card', card='home'))

@app.route("/card/<card>", methods=["GET", "POST"])
def route_card(card):
   return card_router(CARDS.get(card, ErrorCard))
