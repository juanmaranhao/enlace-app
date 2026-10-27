"""Instala contratos do piloto em projetos indicados, sem escrever nos repositórios."""
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.projetos.services import register, queue_inventory, process_one
from apps.central.services import configure_contract, get_contract, prepare_task


class Command(BaseCommand):
    help = 'Vincula projetos explícitos ao piloto local da central; não chama IA.'

    def add_arguments(self, parser):
        parser.add_argument('--operator', required=True)
        parser.add_argument('--project-root', action='append', required=True)

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options['operator'], is_active=True, is_staff=True).first()
        if user is None:
            raise CommandError('Operador ativo não encontrado.')
        for path in options['project_root']:
            project, _ = register(user, Path(path).name, path)
            if get_contract(project) is None:
                configure_contract(user, project, {
                    'stack': 'Django · Python · PostgreSQL · HTML/CSS/JavaScript',
                    'restrictions': ['Preservar alterações, branches, worktrees e arquivos exclusivos.',
                                     'Identidade e decisões específicas permanecem canônicas no projeto.',
                                     'O piloto consulta metadados e contexto; merge, deploy e limpeza não são executados.'],
                    'validation_commands': [], 'execution_mode': 'guided'})
            queue_inventory(project)
            task = prepare_task(user, project, 'Piloto da central: conferir direcionamento, contexto e retomada em ' + project.name,
                                'audit', ['O contexto identifica a raiz e o contrato deste projeto.',
                                          'O inventário Git é consultado sem alterar o projeto.',
                                          'A tarefa preserva etapas e evidências após pausa e retomada.'],
                                'central-pilot-v1:' + str(project.pk))
            self.stdout.write(json.dumps({'project': project.name, 'project_id': str(project.pk), 'task_id': str(task.pk), 'status': task.status}))
        # Apenas a fila de inventários declarativos, nunca execução de projeto ou IA.
        while process_one():
            pass
