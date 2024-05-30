# Summarizer Service

Summarizer Service is a bare-bones sample Flask web application using Flask, using subprocesses and custom scripts. The application provides text web page summarization for bookmarking services, accepting both GET and POST requests with or without a custom prompt.

### Installation
The app is designed to use  <a href="https://github.com/leighklotz/llamafiles">llamafiles</a>, but is easily adapted to use other mechanisms for LLM access.

Install <a href="https://github.com/leighklotz/llamafiles">llamafiles</a> and edit `config.py` accordingly.
```bash
cp config.py.example config.py
emacs config.py
```

Clone this repository:
```bash
git clone https://github.com/leighklotz/summarizer-service.git
cd summarizer-service

```
Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage
Run the application using either of the following commands:

```bash
python app.py

```
or

```bash
flask run --host 127.0.0.1 --port 8080
```

The application will be accessible at `http://localhost:8080`.

### Pages
- `/`: Home page
- `/scuttle?url=`: Scuttle bookmarking service
- `/summarize?url=&prompt=`: Text summarization with optional prompt

### License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
