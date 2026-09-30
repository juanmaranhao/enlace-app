"""QA local isolada: nunca usa o banco do usuário ou chama provedores."""
from .settings import *
DEBUG=True
SESSION_COOKIE_NAME='enlace_qa_session'
CSRF_COOKIE_NAME='enlace_qa_csrf'
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'.local'/'qa.sqlite3'}}
JEV_IA=''
JEV_CONFIGURED=False
TEXT_CONFIGURED=False
OPENAI_API_KEY=''
