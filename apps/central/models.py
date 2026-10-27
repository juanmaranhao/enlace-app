"""Registro operacional; histórico e contratos permanecem preservados."""
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ProjectContract(models.Model):
    """Uma versão imutável do contrato específico de um projeto."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("projetos.Project", on_delete=models.PROTECT, related_name="contracts")
    revision = models.PositiveIntegerField()
    digest = models.CharField(max_length=64)
    payload = models.JSONField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-revision"]
        constraints = [models.UniqueConstraint(fields=["project", "revision"], name="central_contract_revision")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Crie uma nova versão do contrato; o histórico é imutável.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Contratos históricos não são apagados.")

    def __str__(self):
        return f"{self.project} · contrato {self.revision}"


class Task(models.Model):
    """Pedido com contexto fixado, progresso e exclusividade renovável."""

    STATUS_CHOICES = [
        ("prepared", "Preparada"), ("running", "Em execução"),
        ("paused", "Pausada"), ("blocked", "Precisa de atenção"),
        ("review", "Aguardando aprovação"), ("completed", "Concluída"),
        ("cancelled", "Cancelada"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("projetos.Project", on_delete=models.PROTECT, related_name="central_tasks")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="central_tasks")
    contract = models.ForeignKey(ProjectContract, on_delete=models.PROTECT, related_name="tasks")
    objective = models.TextField(max_length=4000)
    workflow = models.CharField(max_length=20)
    criteria = models.JSONField()
    context_snapshot = models.JSONField()
    request_key = models.CharField(max_length=120)
    request_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="prepared")
    current_stage = models.CharField(max_length=30, default="intake")
    revision = models.PositiveIntegerField(default=1)
    lease_token = models.UUIDField(null=True, blank=True)
    lease_generation = models.PositiveIntegerField(default=0)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    outcome = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_key"], name="central_task_request"),
            models.UniqueConstraint(fields=["project"], condition=models.Q(status="running"), name="central_one_project_runner"),
        ]

    def __str__(self):
        return self.objective[:100]


class TaskStep(models.Model):
    """Marco ordenado de uma tarefa; evidências manuais têm origem declarada."""

    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="steps")
    key = models.CharField(max_length=30)
    position = models.PositiveIntegerField()
    title = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default="pending", choices=[("pending", "Pendente"), ("completed", "Concluída")])
    note = models.TextField(blank=True, max_length=4000)
    evidence = models.JSONField(default=list)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [models.UniqueConstraint(fields=["task", "key"], name="central_step_key")]

    def __str__(self):
        return self.title


class TaskEvent(models.Model):
    """Evento imutável; a aplicação acrescenta fatos em vez de reescrevê-los."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="events")
    kind = models.CharField(max_length=40)
    payload = models.JSONField(default=dict)
    request_key = models.CharField(max_length=120, null=True, blank=True)
    payload_digest = models.CharField(max_length=64)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [models.UniqueConstraint(fields=["task", "request_key"], name="central_event_request")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Eventos existentes são imutáveis.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("O histórico da tarefa é preservado.")


class CodexRun(models.Model):
    """Uma execução externa do Codex, persistida antes do despacho ao worker."""

    STATUS_CHOICES = [("queued", "Na fila"), ("running", "Em execução"), ("completed", "Concluída"), ("failed", "Falhou"), ("interrupted", "Interrompida")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="codex_runs")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    operation_key = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    thread_id = models.CharField(max_length=160, blank=True)
    root = models.CharField(max_length=1000)
    generation = models.PositiveIntegerField(default=0)
    result = models.JSONField(default=dict)
    message = models.CharField(max_length=300, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["task", "operation_key"], name="central_codex_operation"),
            models.UniqueConstraint(fields=["task"], condition=models.Q(status__in=["queued", "running"]), name="central_one_codex_run"),
        ]
