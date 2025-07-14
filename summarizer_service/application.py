#!/usr/bin/env python3
# Copyright 2024-2025 Leigh Klotz
# A web application that provides LLM-based text web page summarization for bookmarking services using Flask, subprocesses, and custom scripts.

import logging
import os
import json
import yaml
import base64
import subprocess 

from urllib.parse import quote_plus
from tempfile import NamedTemporaryFile
from collections import Counter

import shlex

from flask import Flask, request, redirect, render_template, jsonify, url_for, session
from flask_session import Session

from typing import List, Dict, Any
from .config import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


MAIN_HEADER = {
    "/card/home": "Home",
    "/card/scuttle?autosubmit=false": "Scuttle",
    "/card/summarize": "Summarize",
    "/card/ask": "Ask",
    "/card/via-api-model": "Via API Models",
    "/card/status": "Status"
}

app = None

def create_app():
    global app
    if app is None:
        app = Flask(__name__)

        # More robust SECRET_KEY handling
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "")
        if not app.config['SECRET_KEY']:
            raise ValueError("Set SECRET_KEY environment variable for production.")
        app.config['SESSION_TYPE'] = 'filesystem'

    Session(app)
    app.config['MODEL_TRACKER'] = ModelTracker(app)  # Pass the app instance
    return app

def validate_url(url: str) -> bool:
    return url.startswith('http://') or url.startswith('https://')

class ModelTracker:
    def __init__(self, app):  # Pass the Flask app instance
        self.app = app
        # Do NOT initialize session here.  Defer initialization to when it's needed
        # within a request context.

    def note_usage(self, model_name):
        with self.app.app_context(): # Access session within an app context
            if 'model_counts' not in session:
                session['model_counts'] = Counter() # Initialize only when needed
            session['model_counts'][model_name] += 1
            session.modified = True

    def get_model_count(self, model_name):
        if 'model_counts' not in session:
            return 0  # Or any default value if not initialized
        return session['model_counts'][model_name] # MODEL NAMES ARE CASE SENSITIVE!

    def get_sorted(self):
        if 'model_counts' not in session:
            return []  # Return an empty list if not initialized
        sorted_items = sorted(session['model_counts'].items(), key=lambda item: (item[1], item[0]), reverse=True) # Sort by count then name
        sorted_keys = [item[0] for item in sorted_items]
        return sorted_keys

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

    def get_model_name(self):
        via = os.environ.get('VIA', DEFAULT_VIA)
        return self._get_via_script(VIA_BIN, self.VIA_FLAG, via, self.GET_MODEL_NAME_FLAG) or f"{model_type}?";

    def _get_model_info(self):
        via = os.environ.get('VIA', DEFAULT_VIA)
        model_type = os.environ.get('MODEL_TYPE', DEFAULT_MODEL_TYPE)
        model_name = self.get_model_name()
        return {
            'via': via,
            'model_type': model_type,
            'model_name': model_name,
            'model_link': self._determine_model_link(via, model_type),
            'model_count': app.config['MODEL_TRACKER'].get_model_count(model_name)
        }

    def _get_via_script(self, script_bin: str, *args):
        try:
            return (subprocess.check_output([script_bin] + list(args)).decode('utf-8') or '').strip()
        except subprocess.CalledProcessError:
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
            logger.error(f"[ERROR] could not read file {fn=}; {e}")
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
        self.set_user_agent()
        super().process()
        if self.url:
            if not validate_url(self.url):
                raise ValueError("Unsupported URL type", self.url)
        app.config['MODEL_TRACKER'].note_usage(self.get_model_name())
        return None

    def set_user_agent(self):
        user_agent = request.headers.get('User-Agent', None)
        if user_agent:
            logger.debug(f"Setting USER_AGENT to {user_agent}")
            os.environ["USER_AGENT"] = user_agent

class ScuttleCard(URLCard):
    def __init__(self):
        super().__init__(template='cards/scuttle/index.page')

    def process(self):
        super().process()

        data, full_text = self.call_scuttle(self.url)
        scuttle_url = self.decode_scuttle_output(data)
        app.config['MODEL_TRACKER'].note_usage(self.get_model_name())
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

            print(' '.join([SCUTTLE_BIN, '--capture-file', capture_filename, '--json', shlex.quote(url)]))
            logger.info(f"scuttle {url=} {capture_filename=}")
            output = subprocess.check_output([SCUTTLE_BIN, '--capture-file', capture_filename, '--json', shlex.quote(url)]).decode('utf-8')
            logger.info(f"scuttle {url=} {capture_filename=} {output=}")

            if not output:
                logger.error(f"[ERROR] Empty Output: try VIA_API_INHIBIT_GRAMMAR or USE_SYSTEM_ROLE: output=%s", output)
            try:
                result = json.loads(output)
            except json.decoder.JSONDecodeError:
                full_text = self.read_file(capture_filename)
                logger.error(f"[ERROR] cannot parse output; try VIA_API_INHIBIT_GRAMMAR or USE_SYSTEM_ROLE: output='%s' full_text='%s'", output, full_text)
                # import pdb;pdb.set_trace()
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
        try:
            super().process()
            self.summary = subprocess.check_output([SUMMARIZE_BIN, self.url, self.prompt]).decode('utf-8')
            app.config['MODEL_TRACKER'].note_usage(self.get_model_name())
            # hack: propagate summary to Ask context
            session['summary'] = self.summary
            return self.get_template()
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
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
        try:
            super().process()
            self.answer = subprocess.check_output([ASK_BIN, 'any', self.question], input=self.context.encode('utf-8')).decode('utf-8')
            app.config['MODEL_TRACKER'].note_usage(self.get_model_name())
            return self.get_template()
        except Exception as e:
            logger.error(f"Error during question answering: {e}")
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
       models_list = subprocess.check_output([VIA_BIN, self.VIA_FLAG, self.API_FLAG, self.LIST_MODELS_FLAG]).decode('utf-8').split('\n')
       models_list = [ model_name.strip() for model_name in models_list ]
       popular_models = app.config['MODEL_TRACKER'].get_sorted()
       models_list = popular_models + ["----"] + models_list
       return models_list

    def process(self):
       super().process()
       if self.model_name:
          self.output = subprocess.check_output([VIA_BIN, self.VIA_FLAG, self.API_FLAG, self.LOAD_MODEL_FLAG, self.model_name]).decode('utf-8')
       return self.get_template()

class HomeCard(BaseCard):
    def __init__(self):
        super().__init__(template='cards/home/index.page')

    def get_template(self):
        # clear session on home card
        clear_session()
        return super().get_template()

class StatusCard(BaseCard):
    def __init__(self):
        super().__init__(template='cards/status/index.page')
        self.status_output = 'No Status'

    def get_template(self):
        try:
            process = subprocess.Popen(STATUS_BIN, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                self.status_output = f"Error executing command (return code {process.returncode}): {stderr}"
                logger.error(f"Error executing status command (return code {process.returncode}): {stderr}")
            else:
                self.status_output = stdout.strip()
                logger.error(f"StatusCard: {self.status_output=}")
                
        except Exception as e: #Catch broader exceptions, including file not found, etc.
            self.status_output = f"Unexpected error: {e}"
            logger.error(f"Unexpected error executing status command: {e}")

        return render_template(self.template, card=self, main_header=MAIN_HEADER, status_output=self.status_output)


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
    'error': ErrorCard,
    'status': StatusCard
}

def clear_session():
    session.clear()
    session['url'] = ''
    session['question'] = ''
    session['context'] = ''
    session.modified = True

### Flask App
app = create_app()

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
