"""MCP stdio local: contexto multiprojeto com operador e alvos explícitos.

O processo é iniciado pelo usuário do host. Não serve HTTP e não aceita um
operador ou uma allowlist vindos de argumentos de ferramenta.
"""
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections
from django.http import Http404
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from apps.projetos.models import Project
from apps.central.models import Task
from apps.central.services import (prepare_task, task_context, start_task, pause_task,
                                   resume_task, record_checkpoint, get_contract, contract_data)
from agentic_core.harness import knowledge_bundle, WORKFLOWS

mcp = MCPServer('Enlace Central', instructions='Direcione o trabalho ao projeto explícito e consulte o contexto fixado. Registre etapas e evidências como autorrelato. Aprovação humana, verificação técnica, merge, deploy e limpeza não são concedidos por estas ferramentas. Não há shell genérico.')


def scope():
    close_old_connections()
    operator = os.environ.get('ENLACE_OPERATOR', '')
    allowed = [item.strip() for item in os.environ.get('ENLACE_CENTRAL_PROJECT_IDS', '').split(',') if item.strip()]
    if not operator or not allowed:
        raise ToolError('Configure operador e projetos autorizados da central neste host.')
    user = get_user_model().objects.filter(username=operator, is_active=True, is_staff=True).first()
    if user is None:
        raise ToolError('Operador indisponível.')
    return user, Project.objects.accessible(user).filter(pk__in=allowed, active=True)


def dispatch(action, **data):
    try:
        user, projects = scope()
        if action == 'projects':
            return {'projects': [{'id': str(project.pk), 'name': project.name, 'root': project.root,
                                  'contract': contract_data(get_contract(project))} for project in projects],
                    'knowledge': knowledge_bundle(), 'workflows': WORKFLOWS}
        if action == 'prepare':
            project = projects.get(pk=data['project_id'])
            task = prepare_task(user, project, data['objective'], data['workflow'], data['criteria'], data['operation_key'])
        else:
            task = Task.objects.select_related('project').get(pk=data['task_id'], project__in=projects)
            if action == 'start':
                task = start_task(user, task, expected_revision=data['revision'])
            elif action == 'pause':
                task = pause_task(user, task, data.get('note', ''), expected_revision=data['revision'])
            elif action == 'resume':
                task = resume_task(user, task, expected_revision=data['revision'])
            elif action == 'checkpoint':
                # O lease pertence ao executor; ler contexto não concede uma posse nova.
                task = record_checkpoint(user, task, data['stage_key'], data['note'], data['evidence'],
                                         data['operation_key'], data['revision'], lease_token=data['lease_token'])
            elif action != 'context':
                raise ValueError('Ação indisponível.')
        result = task_context(task)
        if action in {'start', 'resume'}:
            result['lease_token'] = str(task.lease_token)
        return result
    except (Project.DoesNotExist, Task.DoesNotExist, ValueError, ValidationError, PermissionDenied, Http404):
        raise ToolError('Projeto, tarefa, contexto ou autorização incompatível. Confira o estado na central.') from None


@mcp.tool()
def list_work_projects() -> dict[str, Any]:
    """Lista somente projetos explicitamente habilitados para este operador local."""
    return dispatch('projects')


@mcp.tool()
def prepare_work(project_id: str, objective: str, criteria: list[str], operation_key: str, workflow: str = 'coding') -> dict[str, Any]:
    """Fixa objetivo/contrato/fluxo; reenvio com a mesma chave não duplica a tarefa."""
    return dispatch('prepare', project_id=project_id, objective=objective, criteria=criteria, operation_key=operation_key, workflow=workflow)


@mcp.tool()
def get_work_context(task_id: str) -> dict[str, Any]:
    """Recupera plano, revisão, fontes e evidências do projeto autorizado."""
    return dispatch('context', task_id=task_id)


@mcp.tool()
def start_work(task_id: str, revision: int) -> dict[str, Any]:
    """Reserva a tarefa e devolve token da geração; execução permanece no projeto alvo."""
    return dispatch('start', task_id=task_id, revision=revision)


@mcp.tool()
def pause_work(task_id: str, revision: int, note: str) -> dict[str, Any]:
    """Persiste pausa e revoga posse anterior; preserva arquivos e evidências."""
    return dispatch('pause', task_id=task_id, revision=revision, note=note)


@mcp.tool()
def resume_work(task_id: str, revision: int) -> dict[str, Any]:
    """Revalida fontes e contrato antes de conceder nova geração de execução."""
    return dispatch('resume', task_id=task_id, revision=revision)


@mcp.tool()
def record_work_checkpoint(task_id: str, revision: int, stage_key: str, note: str, evidence: list[dict[str, str]], operation_key: str, lease_token: str) -> dict[str, Any]:
    """Registra uma etapa. Autorrelato nunca é promovido a teste ou aprovação humana."""
    return dispatch('checkpoint', task_id=task_id, revision=revision, stage_key=stage_key, note=note,
                    evidence=evidence, operation_key=operation_key, lease_token=lease_token)


if __name__ == '__main__':
    mcp.run()
