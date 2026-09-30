import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.projetos.models import Project
from apps.projetos.services import process_one,queue_inventory

class Command(BaseCommand):
    help = 'Worker persistente de inventário. --once processa a fila e termina.'
    def add_arguments(self,parser): parser.add_argument('--once',action='store_true')
    def handle(self,*args,**options):
        while True:
            while process_one(): self.stdout.write('Coleta processada.')
            if options['once']: break
            for project in Project.objects.filter(active=True):
                last=project.jobs.first()
                if last and last.status in {'failed','cancelled'}:continue
                if not project.checked_at or project.checked_at < timezone.now()-timedelta(minutes=5):
                    queue_inventory(project)
            time.sleep(3)
