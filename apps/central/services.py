"""Serviços da central: transições explícitas, recibos e contexto fixado."""
from datetime import timedelta
from pathlib import Path
import uuid

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from agentic_core.harness import digest, get_flow, knowledge_bundle, validate_contract
from agentic_core.paths import authorized_root, read_source
from apps.projetos.models import Project
from .models import ProjectContract, Task, TaskEvent, TaskStep

LEASE_MINUTES = 30
SOURCE_PATHS = ("AGENTS.md", "PROJETO.md", "IDENTIDADE.md", "docs/agentica/DOUTRINA.md", "docs/agentica/CODEX.md", "docs/agentica/FLUXOS.md")
VERIFIERS = {"git-inspection-v1", "context-inspection-v1", "contract-inspection-v1"}


class TaskConflict(ValueError):
    """O cliente tentou agir sobre uma versão ou posse que deixou de existir."""


def _key(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 120:
        raise ValueError("Identificador da operação inválido.")
    return value.strip()


def _authorized(user, project):
    if not user.is_authenticated or not user.is_active or not user.is_staff or not (user.is_superuser or project.owner_id == user.pk):
        raise PermissionDenied("Somente o responsável pode conduzir este projeto.")
    if not project.active:
        raise ValueError("Ative o acompanhamento do projeto antes de continuar.")


def get_contract(project):
    """Última versão publicada para o projeto, sem inferir um contrato ausente."""
    return ProjectContract.objects.filter(project=project).order_by("-revision").first()


def contract_data(contract):
    if contract is None:
        return None
    return {"id": str(contract.pk), "revision": contract.revision, "digest": contract.digest, "payload": contract.payload, "created_at": contract.created_at.isoformat()}


@transaction.atomic
def configure_contract(user, project, payload):
    """Publica uma nova versão declarativa, preservando todas as anteriores."""
    project = Project.objects.select_for_update().get(pk=project.pk)
    _authorized(user, project)
    clean = validate_contract(payload)
    root = authorized_root(project.root, settings.ENLACE_ALLOWED_ROOTS)
    clean["root"] = str(root)
    fingerprint = digest(clean)
    current = get_contract(project)
    if current and current.digest == fingerprint:
        return current
    return ProjectContract.objects.create(project=project, revision=(current.revision + 1 if current else 1), digest=fingerprint, payload=clean, created_by=user)


def _source_fingerprints(root):
    """Lê apenas documentos canônicos permitidos; conteúdo não é duplicado no banco."""
    sources = []
    for relative in SOURCE_PATHS:
        if (Path(root) / relative).is_file():
            text = read_source(root, relative)
            sources.append({"path": relative, "digest": digest(text)})
    return sources


def _context(project, contract):
    root = authorized_root(project.root, settings.ENLACE_ALLOWED_ROOTS)
    if str(root) != contract.payload["root"]:
        raise TaskConflict("A raiz mudou. Publique um novo contrato para este projeto.")
    return {"project_id": str(project.pk), "root": str(root), "contract": contract_data(contract), "knowledge": knowledge_bundle(), "sources": _source_fingerprints(root)}


def _assert_context(task):
    current = get_contract(task.project)
    if current is None or current.pk != task.contract_id:
        raise TaskConflict("O contrato mudou. Prepare uma nova tarefa com o contexto atualizado.")
    context = _context(task.project, current)
    # O pacote completo foi fixado na preparação. Publicar um pacote posterior
    # não altera a tarefa em curso; apenas documentos/contrato locais são relidos.
    frozen_bundle = task.context_snapshot.get("knowledge", {})
    if not isinstance(frozen_bundle, dict) or frozen_bundle.get("digest") != digest({key: value for key, value in frozen_bundle.items() if key != "digest"}):
        raise TaskConflict("O pacote de conhecimento da tarefa perdeu integridade.")
    context["knowledge"] = frozen_bundle
    if digest(context) != digest(task.context_snapshot):
        raise TaskConflict("As fontes do projeto mudaram. Revise o contexto e prepare uma nova tarefa.")


def assert_task_context(task):
    """Revalida alvo/contrato/fontes antes de despachar um executor externo."""
    task = Task.objects.select_related("project", "contract").get(pk=task.pk)
    if not task.project.active:
        raise TaskConflict("O acompanhamento do projeto está desativado.")
    _assert_context(task)
    return task


def _event(task, kind, payload, user=None, request_key=None):
    return TaskEvent.objects.create(task=task, kind=kind, payload=payload, payload_digest=digest(payload), created_by=user, request_key=request_key)


def _locked_task(user, task, expected_revision=None):
    locked = Task.objects.select_for_update().select_related("project", "contract").get(pk=task.pk)
    _authorized(user, locked.project)
    if not user.is_superuser and locked.owner_id != user.pk:
        raise PermissionDenied("Esta tarefa pertence a outro responsável.")
    if expected_revision is not None and (isinstance(expected_revision, bool) or locked.revision != int(expected_revision)):
        raise TaskConflict("A tarefa mudou. Atualize a página antes de continuar.")
    return locked


def _save(task, **updates):
    """Compare-and-swap também protege backends sem select_for_update efetivo."""
    revision = task.revision
    updates.update(revision=revision + 1, updated_at=timezone.now())
    if Task.objects.filter(pk=task.pk, revision=revision).update(**updates) != 1:
        raise TaskConflict("Outra execução atualizou a tarefa.")
    for key, value in updates.items():
        setattr(task, key, value)
    return task


@transaction.atomic
def prepare_task(user, project, objective, workflow, criteria, request_key):
    """Persiste pedido e etapas de forma idempotente; não inicia nenhum executor."""
    project = Project.objects.select_for_update().get(pk=project.pk)
    _authorized(user, project)
    request_key = _key(request_key)
    if not isinstance(objective, str) or not 3 <= len(objective.strip()) <= 4000:
        raise ValueError("Descreva um objetivo entre 3 e 4.000 caracteres.")
    if not isinstance(criteria, list) or not 1 <= len(criteria) <= 12 or any(not isinstance(c, str) or not 3 <= len(c.strip()) <= 500 for c in criteria):
        raise ValueError("Informe entre um e doze critérios de aceite objetivos.")
    flow = get_flow(workflow)
    criteria = [c.strip() for c in criteria]
    payload = {"project": str(project.pk), "objective": objective.strip(), "workflow": workflow, "criteria": criteria}
    request_digest = digest(payload)
    existing = Task.objects.filter(owner=user, request_key=request_key).first()
    if existing:
        if existing.request_digest != request_digest:
            raise TaskConflict("Esta operação já foi usada para outro pedido.")
        return existing
    contract = get_contract(project)
    if contract is None:
        raise ValueError("Configure o contrato do projeto antes de preparar a tarefa.")
    task = Task.objects.create(project=project, owner=user, contract=contract, objective=payload["objective"], workflow=workflow, criteria=criteria,
                               context_snapshot=_context(project, contract), request_key=request_key, request_digest=request_digest,
                               outcome={"approval": "pending", "integration": "not_requested", "deployment": "not_requested", "cleanup": "retained"})
    TaskStep.objects.bulk_create([TaskStep(task=task, key=stage["key"], position=index, title=stage["title"]) for index, stage in enumerate(flow)])
    _event(task, "prepared", {"workflow": workflow, "contract_digest": contract.digest, "knowledge_digest": task.context_snapshot["knowledge"]["digest"]}, user)
    return task


def _claim(task, user):
    now = timezone.now()
    # Serializa claims pelo projeto e preserva tarefas cujo executor parou de renovar.
    Project.objects.select_for_update().get(pk=task.project_id)
    for stale in Task.objects.select_for_update().filter(project=task.project, status="running", lease_expires_at__lte=now).exclude(pk=task.pk):
        _save(stale, status="blocked", lease_token=None, lease_expires_at=None)
        _event(stale, "lease_expired", {"message": "Execução sem renovação. Retomada exige reconciliação."})
    if Task.objects.filter(project=task.project, status="running").exclude(pk=task.pk).exists():
        raise TaskConflict("Há outra tarefa em execução neste projeto.")
    _save(task, status="running", lease_token=uuid.uuid4(), lease_generation=task.lease_generation + 1, lease_expires_at=now + timedelta(minutes=LEASE_MINUTES))
    _event(task, "started" if task.lease_generation == 1 else "resumed", {"generation": task.lease_generation, "root": task.context_snapshot["root"]}, user)
    return task


@transaction.atomic
def start_task(user, task, expected_revision=None):
    task = _locked_task(user, task, expected_revision)
    if task.status != "prepared":
        raise TaskConflict("Somente uma tarefa preparada pode ser iniciada.")
    _assert_context(task)
    return _claim(task, user)


@transaction.atomic
def pause_task(user, task, note="", expected_revision=None):
    task = _locked_task(user, task, expected_revision)
    if task.status not in {"running", "blocked"}:
        raise TaskConflict("Esta tarefa não está em execução.")
    _save(task, status="paused", lease_token=None, lease_expires_at=None)
    _event(task, "paused", {"note": str(note)[:2000]}, user)
    return task


@transaction.atomic
def resume_task(user, task, expected_revision=None):
    task = _locked_task(user, task, expected_revision)
    expired = task.status == "running" and task.lease_expires_at and task.lease_expires_at <= timezone.now()
    if task.status not in {"paused", "blocked"} and not expired:
        raise TaskConflict("A tarefa não está disponível para retomada.")
    _assert_context(task)
    return _claim(task, user)


def _lease(task, lease_token):
    if task.status != "running" or not task.lease_token or str(task.lease_token) != str(lease_token) or not task.lease_expires_at or task.lease_expires_at <= timezone.now():
        raise TaskConflict("A posse da execução expirou ou foi substituída. Retome a tarefa.")


@transaction.atomic
def heartbeat_task(task, lease_token, expected_revision=None):
    """Renova somente a geração corrente; executor antigo não recupera a posse."""
    locked = Task.objects.select_for_update().get(pk=task.pk)
    _lease(locked, lease_token)
    if expected_revision is not None and locked.revision != int(expected_revision):
        raise TaskConflict("A revisão da tarefa mudou.")
    until = timezone.now() + timedelta(minutes=LEASE_MINUTES)
    if Task.objects.filter(pk=locked.pk, lease_token=lease_token, status="running", revision=locked.revision).update(lease_expires_at=until) != 1:
        raise TaskConflict("A posse da execução mudou.")
    locked.lease_expires_at = until
    return locked


def _evidence(task, evidence):
    if evidence is None:
        evidence = []
    if not isinstance(evidence, list) or len(evidence) > 20:
        raise ValueError("Evidências devem ser uma lista de até vinte itens.")
    normalized = []
    for item in evidence:
        if not isinstance(item, dict) or set(item) - {"note", "reference", "result", "receipt_id", "kind"}:
            raise ValueError("Formato de evidência inválido.")
        receipt_id = item.get("receipt_id")
        if receipt_id:
            try:
                receipt = task.events.get(pk=receipt_id, kind__in=["verified_result", "human_review"])
            except (TaskEvent.DoesNotExist, ValidationError, ValueError):
                raise ValueError("Recibo não pertence à tarefa ou não é uma verificação.") from None
            normalized.append({"kind": receipt.kind, "evidence_level": receipt.kind, "receipt_id": str(receipt.pk), "verifier": receipt.payload.get("verifier", "human-review"), "result": receipt.payload["result"], "criteria_indices": receipt.payload["criteria_indices"]})
        else:
            clean = {"kind": "self_report"}
            for key in ("note", "reference", "result"):
                value = item.get(key, "")
                if not isinstance(value, str) or len(value) > 1000:
                    raise ValueError("Evidência acima do limite.")
                clean[key] = value
            normalized.append(clean)
    return normalized


@transaction.atomic
def record_checkpoint(user, task, stage_key, note, evidence, request_key, expected_revision, lease_token=None):
    """Conclui apenas a etapa corrente; reenvio idêntico devolve o estado existente."""
    request_key = _key(request_key)
    task = _locked_task(user, task)
    normalized = _evidence(task, evidence)
    if not isinstance(note, str) or not 3 <= len(note.strip()) <= 4000:
        raise ValueError("Registre uma descrição da entrega desta etapa.")
    payload = {"stage": stage_key, "note": note.strip(), "evidence": normalized}
    prior = task.events.filter(request_key=request_key).first()
    if prior:
        if prior.kind != "checkpoint" or prior.payload_digest != digest(payload):
            raise TaskConflict("A operação já foi registrada com outro conteúdo.")
        return task
    if expected_revision is None or isinstance(expected_revision, bool) or task.revision != int(expected_revision):
        raise TaskConflict("A tarefa mudou. Atualize a página antes de registrar a etapa.")
    _lease(task, lease_token)
    _assert_context(task)
    if stage_key != task.current_stage:
        raise TaskConflict("Conclua a etapa corrente antes de avançar.")
    if stage_key == "validation":
        covered = {index for item in normalized if (item.get("kind"), item.get("result")) in {("verified_result", "passed"), ("human_review", "accepted")} for index in item["criteria_indices"]}
        if covered != set(range(len(task.criteria))):
            raise ValueError("A validação precisa de recibos aprovados para todos os critérios de aceite.")
    step = task.steps.get(key=stage_key)
    step.status = "completed"
    step.note = note.strip()
    step.evidence = normalized
    step.completed_at = timezone.now()
    step.save(update_fields=["status", "note", "evidence", "completed_at"])
    following = task.steps.filter(position__gt=step.position).first()
    updates = {"current_stage": following.key if following else "delivery"}
    if following:
        updates["lease_expires_at"] = timezone.now() + timedelta(minutes=LEASE_MINUTES)
    else:
        updates.update(status="review", lease_token=None, lease_expires_at=None)
    _save(task, **updates)
    _event(task, "checkpoint", payload, user, request_key)
    return task


@transaction.atomic
def record_verification(task, verifier, result, details, criteria_indices, lease_token, expected_revision=None):
    """Entrada INTERNA de verificadores determinísticos; não expor como ferramenta genérica.

    O chamador é responsável por executar a verificação registrada. Texto do modelo
    não é resultado deste serviço; deve entrar como autorrelato/execução observada.
    """
    task = Task.objects.select_for_update().get(pk=task.pk)
    _lease(task, lease_token)
    if expected_revision is not None and task.revision != int(expected_revision):
        raise TaskConflict("A revisão da tarefa mudou.")
    if verifier not in VERIFIERS or result not in {"passed", "failed"}:
        raise ValueError("Verificador ou resultado não registrado.")
    if not isinstance(criteria_indices, list) or any(type(index) is not int or index < 0 or index >= len(task.criteria) for index in criteria_indices):
        raise ValueError("Critérios de verificação inválidos.")
    if not isinstance(details, dict) or len(str(details)) > 16000:
        raise ValueError("Recibo de verificação inválido.")
    payload = {"verifier": verifier, "result": result, "details": details, "criteria_indices": sorted(set(criteria_indices)), "generation": task.lease_generation}
    _save(task, lease_expires_at=timezone.now() + timedelta(minutes=LEASE_MINUTES))
    return _event(task, "verified_result", payload)


@transaction.atomic
def record_human_review(user, task, criteria_indices, note, expected_revision, request_key=None):
    """Aceite explícito por critério, reservado à sessão web humana com CSRF.

    Não expor em MCP ou tratar como teste técnico. A revisão humana pode apoiar
    critérios visuais e de negócio mantendo sua origem em todos os recibos.
    """
    task = _locked_task(user, task)
    if not isinstance(note, str) or not 3 <= len(note.strip()) <= 2000:
        raise ValueError("Descreva o que você conferiu antes de registrar o aceite.")
    if not isinstance(criteria_indices, list) or not criteria_indices or any(type(index) is not int or index < 0 or index >= len(task.criteria) for index in criteria_indices):
        raise ValueError("Selecione ao menos um critério de aceite válido.")
    payload = {"result": "accepted", "criteria_indices": sorted(set(criteria_indices)), "note": note.strip(), "technical_validation": False, "evidence_level": "human_review", "reviewer_id": user.pk}
    if request_key is not None:
        request_key = _key(request_key)
        previous = task.events.filter(request_key=request_key).first()
        if previous:
            if previous.kind != "human_review" or previous.payload_digest != digest(payload):
                raise TaskConflict("A operação já foi registrada com outro conteúdo.")
            return previous
    if expected_revision is None or isinstance(expected_revision, bool) or task.revision != int(expected_revision):
        raise TaskConflict("A tarefa mudou. Atualize a página antes de conferir os critérios.")
    _lease(task, task.lease_token)
    _assert_context(task)
    if task.current_stage != "validation":
        raise TaskConflict("A conferência dos critérios pertence à etapa de validação.")
    _save(task, lease_expires_at=timezone.now() + timedelta(minutes=LEASE_MINUTES))
    return _event(task, "human_review", payload, user, request_key)


@transaction.atomic
def approve_task(user, task, note="", expected_revision=None):
    """Registra aceite humano da entrega; não representa merge, deploy ou limpeza."""
    task = _locked_task(user, task, expected_revision)
    if task.status != "review":
        raise TaskConflict("A tarefa ainda não está pronta para aprovação.")
    if not isinstance(note, str) or len(note.strip()) > 2000:
        raise ValueError("Registre a conclusão da revisão humana.")
    note = note.strip() or "Entrega aprovada pelo responsável."
    outcome = {**task.outcome, "approval": "approved"}
    _save(task, status="completed", outcome=outcome)
    _event(task, "human_approval", {"note": note.strip(), "technical_validation": "recorded_separately", "outcome": outcome}, user)
    return task


@transaction.atomic
def append_event(user, task, kind, payload, request_key=None, expected_revision=None, lease_token=None):
    """Acrescenta telemetria, sem avançar etapa ou promover validação técnica.

    O chamador deve sanitizar o payload. Um token opcional permite ao worker
    recusar eventos produzidos por uma geração substituída.
    """
    task = _locked_task(user, task, expected_revision)
    if lease_token is not None:
        _lease(task, lease_token)
    if kind not in {"git_observed", "codex_queued", "codex_event", "codex_result"}:
        raise ValueError("Tipo de observação não autorizado.")
    if not isinstance(payload, dict) or len(str(payload)) > 64000:
        raise ValueError("Observação inválida ou acima do limite.")
    if request_key is not None:
        request_key = _key(request_key)
        previous = task.events.filter(request_key=request_key).first()
        if previous:
            if previous.kind != kind or previous.payload_digest != digest(payload):
                raise TaskConflict("A operação já foi registrada com outro conteúdo.")
            return previous
    return _event(task, kind, payload, user, request_key)


def record_observation(user, task, kind, payload, request_key=None, lease_token=None):
    """Alias sem revisão de interface para coletores de observação."""
    return append_event(user, task, kind, payload, request_key=request_key, lease_token=lease_token)


def task_context(task):
    """Contexto portátil sem segredo ou conteúdo privado do projeto acompanhado."""
    task = Task.objects.select_related("project", "contract").get(pk=task.pk)
    return {
        "task_id": str(task.pk), "project": {"id": str(task.project_id), "name": task.project.name, "root": task.context_snapshot["root"]},
        "objective": task.objective, "workflow": task.workflow, "criteria": task.criteria,
        "status": task.status, "status_label": task.get_status_display(), "revision": task.revision,
        "stage": task.current_stage, "lease_generation": task.lease_generation,
        "lease_expires_at": task.lease_expires_at.isoformat() if task.lease_expires_at else None,
        "context": task.context_snapshot, "outcome": task.outcome,
        "steps": [{"key": step.key, "title": step.title, "position": step.position, "status": step.status, "note": step.note, "evidence": step.evidence} for step in task.steps.all()],
        "events": [{"id": str(event.pk), "kind": event.kind, "payload": event.payload, "created_at": event.created_at.isoformat()} for event in task.events.order_by("-created_at")[:100]],
    }
