"""Worker local sequencial; não reinicia consultas cujo efeito ficou incerto."""
import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from apps.central.execution import process_consultation


class Command(BaseCommand):
    help = 'Processa consultas de contexto Codex da central.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')

    def handle(self, *args, **options):
        while True:
            close_old_connections()
            processed = process_consultation()
            if options['once']:
                self.stdout.write('Consulta processada.' if processed else 'Fila vazia.')
                return
            if not processed:
                time.sleep(2)
