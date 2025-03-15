#!/usr/bin/env python3
# Copyright 2024-2025 Leigh Klotz
# A web application that provides LLM-based text web page summarization for bookmarking services using Flask, subprocesses, and custom scripts.

# **1. Session Management & Context:**
# 
# *   **Potential Race Condition:**  Multiple requests *could* potentially access and modify `session['model_counts']` concurrently, especially under high load.  While Flask-Session with the filesystem backend is convenient, it's not inherently thread-safe.  Consider using a more robust session store (Redis, database) for production environments if concurrency is a concern. The `with self.app.app_context():` blocks help, but don't entirely eliminate the possibility.
# *   **Session Modification:** The code explicitly sets `session.modified = True` after modifying `session['model_counts']`. This is *crucial* because Flask-Session only saves the session if it detects changes.  Good practice!  But double-check that all modifications to the session trigger this.
# *   **Session Scope:**  The `session` object is tied to the Flask application context.  Ensure that the `ModelTracker` is correctly initialized *within* an application context to avoid potential issues.  The current code appears to handle this correctly using `with self.app.app_context():`, but review any places where `ModelTracker` might be accessed outside of a request lifecycle.
# *   **`clear_session()` - Incomplete Clearing:** The `clear_session()` function doesn't clear *all* session keys. It explicitly resets `url`, `question`, and `context`, but other keys added by cards (like `prompt` in `SummarizeCard`) will persist. This could lead to unexpected behavior if a user navigates back after using a card that sets a session variable not explicitly cleared. Consider `session.clear()` for a full reset, *or* explicitly clear all relevant card-specific keys in `clear_session()`.
# 
# **2. ModelTracker Logic:**
# 
# *   **`get_sorted()` - Potential for Inconsistent Ordering:** The `sorted()` function is stable, but if multiple models have the *same* usage count, their relative order in the `sorted_keys` list isn't guaranteed.  If a consistent order is important (e.g., for display), you might need a secondary sorting key (e.g., model name alphabetically).
# *   **Model Name Handling:**  Ensure that `model_name` values are consistent.  Case sensitivity could lead to different entries for the same model.  Consider normalizing model names (e.g., converting to lowercase) before storing them in `session['model_counts']`.
# 
# **3. Usage within Cards:**
# 
# *   **`app.config['MODEL_TRACKER'].note_usage()`:**  This call happens in several cards (`URLCard`, `ScuttleCard`, `SummarizeCard`, `AskCard`).  Verify that it's always called *after* a successful operation.  If an exception occurs before `note_usage()`, the model count won't be updated.
# *    **`ViaAPIModelCard` and Model Loading:**  The `ViaAPIModelCard`'s `process` method only calls `note_usage` if `self.model_name` is set. This might be unintentional; you might want to track the attempt to *load* a model even if the loading fails.
# 
# **4. Testing & Edge Cases:**
# 
# *   **Session Expiration:**  Test what happens when the session expires.  Will the `ModelTracker` correctly handle the lack of `session['model_counts']`?
# *   **Large Numbers of Models:**  Consider the performance implications of tracking a very large number of models in the session.  The `Counter` object and the sorting operation could become slow.
# *   **Error Handling:**  Add more robust error handling around session access and modification.  While the code has some exception handling, consider adding `try...except` blocks around critical session operations to prevent unexpected crashes.
# 
# **Specific Code Snippets to Review/Modify:**
# 
# *   **`ModelTracker.__init__`:**  Verify that `app.app_context()` is necessary *within* `__init__`. It's likely safe, but double-check.
# *   **`clear_session()`:**  Consider `session.clear()` or adding more explicit clearing of card-specific variables.
# *   **`SummarizeCard.process()` and `AskCard.process()`:** Add `try...except` around the `check_output` call to ensure `note_usage()` is still called even if the summarization/question answering fails.
# *   **`ViaAPIModelCard.process()`:** Decide if `note_usage()` should be called even if `self.model_name` is empty.
# 
# 

import logging
import os
import json
import yaml
import base64

from urllib.parse import quote_plus
from subprocess import check_output, CalledProcessError
from tempfile import NamedTemporaryFile
from collections import Counter

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

        # More robust SECRET_KEY handling
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key') # Provide a default
        if app.config['SECRET_KEY'] == 'your_default_secret_key':
            print("WARNING: Using default SECRET_KEY.  Set SECRET_KEY environment variable for production.")
        app.config['SESSION_TYPE'] = 'filesystem'

    Session(app)
    app.config['MODEL_TRACKER'] = ModelTracker(app)  # Pass the app instance
    return app

def validate_url(url: str) -> bool:
    return url.startswith('http://') or url.startswith('https://')

class ModelTracker:
    def __init__(self, app):  # Pass the Flask app instance
        self.app = app
        with self.app.app_context():  # Access session within an app context
            if 'model_counts' not in session:
                session['model_counts'] = Counter()

    def note_usage(self, model_name):
        with self.app.app_context(): # Access session within an app context
            session['model_counts'][model_name] += 1
            session.modified = True

    def get_model_count(self, model_name):
        return session['model_counts'][model_name]

    def get_sorted(self):
        sorted_items = sorted(session['model_counts'].items(), key=lambda item: item[1], reverse=True)
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
        super().process()
        if self.url:
            if not validate_url(self.url):
                raise ValueError("Unsupported URL type", self.url)
        app.config['MODEL_TRACKER'].note_usage(self.get_model_name())
        return None
                                    
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
            output = check_output([SCUTTLE_BIN, '--capture-file', capture_filename, '--json', shlex.quote(url)]).decode('utf-8')
            logger.info(f"*** scuttle {url=} {output=} {capture_filename=}")

            try:
                result = json.loads(output)
            except json.JSONDecodeError:
                logger.error(f"*** [ERROR] cannot parse output; try VIA_API_INHIBIT_GRAMMAR or USE_SYSTEM_ROLE: %s", output)
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
       app.config['MODEL_TRACKER'].note_usage(self.get_model_name())
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
        app.config['MODEL_TRACKER'].note_usage(self.get_model_name())
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
       popular_models = app.config['MODEL_TRACKER'].get_sorted()
       # todo: start with popular models and then end with models_list - popular_models
       models_list = popular_models + ["----"] + models_list
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
    logger = logging.getLogger(__name__)
    logger.setLevel(gunicorn_logger.level)
