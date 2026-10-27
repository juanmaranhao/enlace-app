"""Superfície autenticada do harness; GET nunca inicia uma execução."""
import json
import uuid

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView, FormView, View

from apps.projetos.models import Project
from core.access import StaffRequiredMixin, project_for
from .forms import TaskForm, ContractForm, ActionForm, CheckpointForm, HumanReviewForm
from .models import Task, ProjectContract
from .execution import observe_task, queue_consultation
from .services import (prepare_task, configure_contract, get_contract, task_context,
                       start_task, pause_task, resume_task, approve_task, record_checkpoint, record_human_review)


def accessible_task(user, pk, *, edit=False):
    """Resolver primeiro o escopo do projeto, inclusive em links diretos."""
    task = get_object_or_404(Task.objects.select_related('project', 'owner', 'contract'), pk=pk)
    project_for(user, task.project_id, edit=edit)
    return task


class CentralHomeView(StaffRequiredMixin, TemplateView):
    template_name = 'central/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = Project.objects.accessible(self.request.user).filter(active=True)
        for project in projects:
            project.can_edit = self.request.user.is_superuser or project.owner_id == self.request.user.pk
        tasks = Task.objects.filter(project__in=projects).select_related('project', 'owner').order_by('-created_at')[:40]
        context.update(screen='central', projects=projects, tasks=tasks,
                       contracts=ProjectContract.objects.filter(project__in=projects).select_related('project').order_by('-created_at')[:40])
        return context


class BrainView(StaffRequiredMixin, TemplateView):
    template_name = 'central/cerebro.html'

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'screen': 'brain'}


class TaskCreateView(StaffRequiredMixin, FormView):
    template_name = 'central/task_form.html'
    form_class = TaskForm

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'user': self.request.user}

    def get_initial(self):
        return {**super().get_initial(), 'project': self.request.GET.get('project'), 'workflow': 'coding'}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'screen': 'central'}

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            task = prepare_task(self.request.user, data['project'], data['objective'], data['workflow'], data['criteria'], str(data['request_key']))
        except (ValueError, ValidationError, PermissionDenied) as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, 'Tarefa preparada com contrato e conhecimento fixados. A execução ainda não começou.')
        return redirect('central_task_detail', pk=task.pk)


class ContractView(StaffRequiredMixin, FormView):
    template_name = 'central/contract_form.html'
    form_class = ContractForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.project = project_for(request.user, kwargs['pk'], edit=True)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        contract = get_contract(self.project)
        if not contract:
            return {**super().get_initial(), 'execution_mode': 'guided', 'restrictions': 'Preservar alterações e arquivos exclusivos.\nMerge e produção dependem da autorização aplicável.'}
        data = dict(contract.payload)
        for key in ('restrictions', 'validation_commands'):
            data[key] = '\n'.join(data.get(key, []))
        return data

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'screen': 'central', 'project': self.project, 'contract': get_contract(self.project)}

    def form_valid(self, form):
        try:
            configure_contract(self.request.user, self.project, form.contract_payload())
        except (ValueError, ValidationError, PermissionDenied) as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, 'Contrato versionado. Tarefas existentes preservam a versão que adotaram.')
        return redirect('central_home')


class TaskDetailView(StaffRequiredMixin, TemplateView):
    template_name = 'central/task_detail.html'

    def get_context_data(self, **kwargs):
        task = accessible_task(self.request.user, kwargs['pk'])
        bundle = task_context(task)
        events = list(task.events.order_by('-created_at')[:60])
        for event in events:
            event.payload_pretty = json.dumps(event.payload, ensure_ascii=False, indent=2)
        return {**super().get_context_data(**kwargs), 'screen': 'central', 'task': task,
                'steps': task.steps.order_by('position'), 'events': events,
                'context_bundle': bundle, 'context_bundle_pretty': json.dumps(bundle, ensure_ascii=False, indent=2),
                'can_edit': self.request.user.is_superuser or task.project.owner_id == self.request.user.pk,
                'action_form': ActionForm(initial={'expected_revision': task.revision}),
                'checkpoint_form': CheckpointForm(task=task, initial={'expected_revision': task.revision, 'stage_key': task.current_stage}),
                'human_review_form': HumanReviewForm(task=task, initial={'expected_revision': task.revision}),
                'codex_operation_key': str(uuid.uuid4()), 'codex_runs': task.codex_runs.order_by('-created_at')[:10]}


class TaskActionView(StaffRequiredMixin, View):
    def post(self, request, pk):
        task = accessible_task(request.user, pk, edit=True)
        form = ActionForm(request.POST)
        actions = {'start': start_task, 'pause': pause_task, 'resume': resume_task, 'approve': approve_task}
        action = request.POST.get('action')
        if not form.is_valid() or action not in actions:
            messages.error(request, 'Ação inválida. Atualize a tarefa antes de continuar.')
        else:
            try:
                actions[action](request.user, task, expected_revision=form.cleaned_data['expected_revision'])
                messages.success(request, 'Estado da tarefa atualizado.')
            except (ValueError, ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
        return redirect('central_task_detail', pk=pk)


class CheckpointView(StaffRequiredMixin, View):
    def post(self, request, pk):
        task = accessible_task(request.user, pk, edit=True)
        form = CheckpointForm(request.POST, task=task)
        if not form.is_valid():
            messages.error(request, 'Preencha a etapa e a evidência; recarregue se o plano mudou.')
        else:
            data = form.cleaned_data
            try:
                record_checkpoint(request.user, task, data['stage_key'], data['note'],
                                  [{'note': data['note'], 'reference': data['reference']}] + [{'receipt_id': str(receipt.pk)} for receipt in data['receipts']],
                                  str(data['request_key']), data['expected_revision'], lease_token=task.lease_token)
                messages.success(request, 'Checkpoint registrado. O relato permanece identificado como autorrelato.')
            except (ValueError, ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
        return redirect('central_task_detail', pk=pk)


class HumanReviewView(StaffRequiredMixin, View):
    """Conferência humana acessível somente por sessão autenticada e CSRF."""
    def post(self, request, pk):
        task = accessible_task(request.user, pk, edit=True)
        form = HumanReviewForm(request.POST, task=task)
        if form.is_valid():
            data = form.cleaned_data
            try:
                record_human_review(request.user, task, data['criteria_indices'], data['note'], data['expected_revision'], str(data['request_key']))
                messages.success(request, 'Conferência humana registrada. Vincule seu recibo ao checkpoint de validação.')
            except (ValueError, ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, 'Selecione os critérios conferidos e descreva a evidência.')
        return redirect('central_task_detail', pk=pk)


class TaskContextView(StaffRequiredMixin, View):
    def get(self, request, pk):
        task = accessible_task(request.user, pk)
        body = json.dumps(task_context(task), ensure_ascii=False, indent=2)
        response = HttpResponse(body, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="enlace-{task.pk}.json"'
        return response


class ProbeView(StaffRequiredMixin, View):
    def post(self, request, pk):
        task = accessible_task(request.user, pk, edit=True)
        try:
            observe_task(request.user, task)
            messages.success(request, 'Estado Git observado. Nenhum arquivo do projeto foi alterado.')
        except (ValueError, OSError, ValidationError, PermissionDenied) as exc:
            messages.error(request, str(exc))
        return redirect('central_task_detail', pk=pk)


class CodexQueueView(StaffRequiredMixin, View):
    def post(self, request, pk):
        task = accessible_task(request.user, pk, edit=True)
        try:
            queue_consultation(request.user, task, request.POST.get('operation_key') or str(uuid.uuid4()))
            messages.success(request, 'Consulta encaminhada ao worker Codex. Acompanhe o recibo nesta tarefa.')
        except (ValueError, ValidationError, PermissionDenied) as exc:
            messages.error(request, str(exc))
        return redirect('central_task_detail', pk=pk)
