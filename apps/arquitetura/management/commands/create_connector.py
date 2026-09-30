import hashlib
import secrets
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from core.access import project_for
from apps.arquitetura.models import Connector

class Command(BaseCommand):
    help='Cria credencial local por projeto; grava uma vez em .local, nunca imprime chave.'
    def add_arguments(self,parser):
        parser.add_argument('--project',required=True);parser.add_argument('--user',required=True)
        parser.add_argument('--channel',choices=['codex','product'],required=True);parser.add_argument('--name',default='Conector local')
    def handle(self,*args,**options):
        user=get_user_model().objects.filter(username=options['user'],is_active=True,is_staff=True).first()
        if not user:raise CommandError('Administrador indisponível.')
        project=project_for(user,options['project'],edit=True)
        token=secrets.token_urlsafe(48)
        connector=Connector.objects.create(project=project,owner=user,name=options['name'],channel=options['channel'],token_hash=hashlib.sha256(token.encode()).hexdigest())
        folder=settings.BASE_DIR/'.local'/'connectors';folder.mkdir(parents=True,exist_ok=True)
        path=folder/f'{connector.pk}.env'
        path.write_text(f'ENLACE_URL=http://127.0.0.1:8766\nENLACE_TOKEN={token}\nENLACE_PROJECT={project.pk}\nENLACE_CHANNEL={connector.channel}\n',encoding='utf8')
        self.stdout.write(f'Conector {connector.pk}. Credencial local: {path}')
