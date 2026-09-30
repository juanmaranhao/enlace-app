from .settings import *
DEBUG = True
ALLOWED_HOSTS = ['testserver','localhost','127.0.0.1']
DATABASES = {'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:','OPTIONS':{'cached_statements':0}}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
JEV_CONFIGURED = False
TEXT_CONFIGURED = False
JEV_IA = ''
OPENAI_API_KEY = ''
