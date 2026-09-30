"""Corpus de QA com fontes reais e banco separado, sem eventos fabricados."""
import json
import os
import secrets
import sys
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE_DIR))
os.environ['DJANGO_SETTINGS_MODULE']='core.settings_qa'
(BASE_DIR/'.local').mkdir(exist_ok=True)
import django
django.setup()
from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.projetos.services import register,queue_inventory,process_one
call_command('migrate',interactive=False,verbosity=0)
user,_=get_user_model().objects.get_or_create(username='enlace-qa',defaults={'is_staff':True})
credentials=BASE_DIR/'.local'/'qa-login.json'
if not credentials.exists():
    password=secrets.token_urlsafe(24);user.set_password(password);user.save()
    credentials.write_text(json.dumps({'username':user.username,'password':password}),encoding='utf8')
workspace=BASE_DIR.parent.parent
paths=[workspace/'APPS'/'LICIPUB',workspace/'APPS'/'SOCIAL_APP',workspace/'DJANGO_LANDPAGE']
for path in paths:
    if path.is_dir():
        project,_=register(user,path.name,path);queue_inventory(project)
while process_one():pass
for project in user.owned_projects.all():
    graph=project.latest.graph
    print(json.dumps({'project':project.name,'id':str(project.pk),'sources':len(graph['sources']),'flows':sum(n['kind']=='flow' for n in graph['nodes']),'partial':graph['coverage']['partial']}))
