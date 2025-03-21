#!/usr/bin/env python3
# Copyright 2024-2025 Leigh Klotz
# A web application that provides LLM-based text web page summarization for bookmarking services using Flask, subprocesses, and custom scripts.

import logging
import os
import json
import yaml
import base64

from urllib.parse import quote_plus
from subprocess import check_output, CalledProcessError
from tempfile import NamedTemporaryFile
import shlex

from flask import Flask, request, redirect, render_template, jsonify, url_for, session
from flask_session import Session

from typing import List, Dict, Any
from .config import *

MAIN_HEADER = {
    "/card/home": "Home",
    "/card/scuttle": "Scuttle",
    "/card/summarize": "Summarize",
    "/card/ask": "Ask",
    "/card/via-api-model": "Via API Models"
}

app = None

def create_app():
    global app
    if app is None:
        app = Flask(__name__)

        if not app.config.get('SECRET_KEY', None):
            try:
                app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
            except KeyError:
                raise ValueError("No 'SECRET_KEY' specified in environment variables; sessions will not work.")
        app.config['SESSION_TYPE'] = 'filesystem'
    Session(app)
    return app

def validate_url(url: str) -> bool:
    return url.startswith('http://') or url.startswith('https://')

app = create_app()

class BaseCard:
    VIA_FLAG = '--via'
    API_FLAG = 'api'
    GET_MODEL_NAME_FLAG = '--get-model-name'

    def __init__(self, template: str, params: List[str]=[]):
        self.template = template
        self.params = params
        self.stats = self.get_stats()

    def get_template(self):
        return render_template(self.template, card=self, main_header=MAIN_HEADER)

    def pre_process(self):
        for param in request.args:  
            value = request.args.get(param)
            setattr(self, param, value) 
            session[param] = value

        for param in request.form:
            value = request.form.get(param)
            setattr(self, param, value) 
            session[param] = value

        for param in self.params:
            if not getattr(self, param) and param in session:
                setattr(self, param, session[param]) 

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

    def _get_via_script(self, script_bin: str, *args):
        try:
            return (check_output([script_bin] + list(args)).decode('utf-8') or '').strip()
        except CalledProcessError:
            return None

    def _determine_model_link(self, via: str, model_type: str):
        return OPENAPI_UI_SERVER if via == 'api' else LLAMAFILES_LINK

    def get_stats(self):
        nvfree = self._get_via_script(NVFREE_BIN) or '0'
        stats = {'nvfree': nvfree}
        model_info = self._get_model_info()
        stats.update(model_info)
        return stats

    def read_file(self, fn):
        try:
            with open(fn, 'r') as file:
                return file.read()
        except Exception as e:
            logger.error(f"*** [ERROR] could not read file {fn=}; {e}")
            raise

class URLCard(BaseCard):
    def __init__(self, template: str, params: List[str]=[]):
        self.url = ''
        super().__init__(template=template, params=(params + ['url']))

    def form(self):
        return super().form() + [
            { 'name':'url', 'label':"Enter URL:", 'type':'url', 'required':'required', 'value': self.url, 'autocomplete':  'off' }, 
        ]

    def process(self):
        if self.url:
            if not validate_url(self.url):
                raise ValueError("Unsupported URL type", self.url)
        return None
                                    
class ScuttleCard(URLCard):
    def __init__(self):
        super().__init__(template='cards/scuttle/index.page')

    def process(self):
        super().process()

        data, full_text = self.call_scuttle(self.url)
        scuttle_url = self.decode_scuttle_output(data)
        if full_text:
            session['context'] = full_text
            if scuttle_url:
                return redirect(scuttle_url)
            else:
                return self.get_template()

    def call_scuttle(self, url: str):
        if not validate_url(url):
            raise InvalidURLException(f"Unsupported URL type: {url}")

        with NamedTemporaryFile(dir='/tmp', delete=True) as temp:
            capture_filename = temp.name
            output = check_output([SCUTTLE_BIN, '--capture-file', capture_filename, '--json', shlex.quote(url)]).decode('utf-8')
            logger.info(f"*** scuttle {url=} {output=} {capture_filename=}")

            try:
                result = json.loads(output)
            except json.JSONDecodeError:
                logger.error(f"*** [ERROR] cannot parse output; try VIA_API_INHIBIT_GRAMMAR or USE_SYSTEM_ROLE")
                raise
            full_text = self.read_file(capture_filename)
            return result, full_text

    def decode_scuttle_output(self, data: Dict[str, str]):
       # Decode the output from the Scuttle tool
       link = data['link']
       title = data['title']
       description = data['description']
       tags = self.list_to_comma_separated(data['keywords'])
       url = f'https://scuttle.klotz.me/bookmarks/klotz?action=add&address={quote_plus(link)}&description={quote_plus(description)}&title={quote_plus(title)}&tags={quote_plus(tags)}'
       return url
 
    def list_to_comma_separated(self, keywords: List[str]):
       # Convert a list of keywords to a comma-separated string
       if isinstance(keywords, list):
          return ', '.join(keywords)
       elif isinstance(keywords, str):
          return keywords
       else:
          raise ValueError("Not a string or list of strings", keywords)
 
class SummarizeCard(URLCard):
    prompts = [ "Summarize.",
                "Summarize as bullet points.",
                "Answer the title question in one sentence.",
                "Answer the title question in one paragraph.",
                "Write help text to add to this web page."]
    def __init__(self):
       super().__init__(template='cards/summarize/index.page', params=['prompt'])
       self.prompt = 'Summarize'
       self.summary = '' 
 
    def form(self):
       return super().form() + [
          { 'name':'prompt', id:'prompt-input', 'label':"Prompt:", 'type':"text", 'list':"prompts", 'value': self.prompt }
       ]
 
    def process(self):
       super().process()
       self.summary = check_output([SUMMARIZE_BIN, self.url, self.prompt]).decode('utf-8')
       # hack: propagate summary to Ask context
       session['summary'] = self.summary
       return self.get_template()

class AskCard(BaseCard):
    def __init__(self):
        super().__init__(template='cards/ask/index.page', params=['question', 'context'])
        self.question = ''
        self.context = '' 
        self.answer = '' 
 
    def form(self):
        # hack: propagate summary from Summary to Ask context
        context_value = self.context or session.get('summary', '')
        return super().form() + [
            { 'name':'question','id':'question-textarea', 'label':'Question:', 'type':'text', 'value': self.question , 'tag': 'textarea'},
            { 'name':'context', 'id':'context-textarea', 'label':'Context:', 'type':'text', 'value': context_value, 'tag':'textarea' }
        ]
 
    def process(self):
        super().process()
        self.answer = check_output([ASK_BIN, 'any', self.question], input=self.context.encode('utf-8')).decode('utf-8')
        return self.get_template()
 
 
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

    def get_template(self):
        # clear session on home card
        clear_session()
        return super().get_template()

class ErrorCard(BaseCard):
    def __init__(self):
        super().__init__(template='cards/error/index.page')

### Card Routing
def card_router(card_constructor):
    ## todo: these lifecycle calls are non-standard and somewhat confusing
    card = card_constructor()
    card.pre_process()
    if request.method == 'POST':
       result = card.process()
       if result is not None:
          return result
       else:
          return card.get_template()
    else:
       return card.get_template()
    
CARDS: Dict[str,BaseCard] = {
    'home': HomeCard,
    'scuttle': ScuttleCard,
    'summarize': SummarizeCard,
    'ask': AskCard,
    'via-api-model': ViaAPIModelCard,
    'error': ErrorCard
}

def clear_session():
    session.clear() 
    session['url'] = ''
    session['question'] = ''
    session['context'] = ''
    session.modified = True

### Routes
@app.route("/")
def root():
    return redirect(url_for('route_card', card='home'))

@app.route("/card/<card>", methods=['GET', 'POST'])
def route_card(card):
   return card_router(CARDS.get(card, ErrorCard))

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.warn')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    logger = logging.getLogger(__name__)
    logger.setLevel(gunicorn_logger.level)
