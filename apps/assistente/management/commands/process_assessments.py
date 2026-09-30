import time
from django.core.management.base import BaseCommand
from apps.assistente.assessments import process_assessment
from apps.assistente.conversations import process_chat

class Command(BaseCommand):
    help='Processa exclusivamente análises autorizadas. --once drena a fila e termina.'
    def add_arguments(self,parser):parser.add_argument('--once',action='store_true')
    def handle(self,*args,**options):
        while True:
            while process_assessment():self.stdout.write('Análise processada.')
            while process_chat():self.stdout.write('Conversa processada.')
            if options['once']:return
            time.sleep(3)
