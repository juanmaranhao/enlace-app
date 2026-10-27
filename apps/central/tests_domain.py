"""Regressões de retomada, concorrência, autoria e distinção de evidências."""
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.projetos.models import Project
from .models import Task, TaskEvent
from .services import (
    TaskConflict, approve_task, configure_contract, heartbeat_task, pause_task,
    prepare_task, record_checkpoint, record_human_review, record_observation, record_verification,
    resume_task, start_task, task_context,
)


class CentralDomainTests(TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / "AGENTS.md").write_text("Regras locais aprovadas.", encoding="utf-8")
        self.override = override_settings(ENLACE_ALLOWED_ROOTS=[self.root])
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.owner = get_user_model().objects.create_user("owner", is_staff=True)
        self.reader = get_user_model().objects.create_user("reader", is_staff=True)
        self.project = Project.objects.create(owner=self.owner, name="Piloto", root=str(self.root), canonical_key=str(self.root).casefold())
        self.project.readers.add(self.reader)
        self.contract = configure_contract(self.owner, self.project, {"stack": ["Django"], "execution_mode": "guided"})

    def prepare(self, key="one"):
        return prepare_task(self.owner, self.project, "Validar contexto do projeto", "audit", ["Contrato identificado"], key)

    def checkpoint(self, task, evidence=None):
        return record_checkpoint(self.owner, task, task.current_stage, "Etapa conferida com evidências.", evidence or [], f"stage-{task.current_stage}", task.revision, task.lease_token)

    def test_prepare_is_idempotent_and_rejects_payload_reuse(self):
        task = self.prepare()
        self.assertEqual(task.pk, self.prepare().pk)
        self.assertEqual(Task.objects.count(), 1)
        with self.assertRaises(TaskConflict):
            prepare_task(self.owner, self.project, "Outro objetivo diferente", "audit", ["Outro critério"], "one")

    def test_reader_cannot_prepare_or_change_contract(self):
        with self.assertRaises(PermissionDenied):
            configure_contract(self.reader, self.project, {"stack": ["Django"]})
        with self.assertRaises(PermissionDenied):
            prepare_task(self.reader, self.project, "Pedido indevido", "audit", ["Conferir acesso"], "x")

    def test_contract_is_versioned_and_frozen_in_existing_task(self):
        task = self.prepare()
        changed = configure_contract(self.owner, self.project, {"stack": ["Django", "PostgreSQL"]})
        self.assertEqual(changed.revision, 2)
        task.refresh_from_db()
        self.assertEqual(task.context_snapshot["contract"]["revision"], 1)
        with self.assertRaises(TaskConflict):
            start_task(self.owner, task)
        with self.assertRaises(ValidationError):
            self.contract.save()

    def test_one_runner_per_project_and_pause_preserves_progress(self):
        first = start_task(self.owner, self.prepare())
        second = self.prepare("two")
        with self.assertRaises(TaskConflict):
            start_task(self.owner, second)
        first = self.checkpoint(first)
        token = first.lease_token
        first = pause_task(self.owner, first, expected_revision=first.revision)
        first = resume_task(self.owner, first, expected_revision=first.revision)
        self.assertEqual(first.current_stage, "decision")
        self.assertNotEqual(first.lease_token, token)
        with self.assertRaises(TaskConflict):
            heartbeat_task(first, token)

    def test_resume_rejects_changed_sources(self):
        task = start_task(self.owner, self.prepare())
        task = pause_task(self.owner, task)
        (self.root / "AGENTS.md").write_text("Decisão posterior.", encoding="utf-8")
        with self.assertRaises(TaskConflict):
            resume_task(self.owner, task)
        task.refresh_from_db()
        self.assertEqual(task.status, "paused")

    def test_running_task_keeps_its_pinned_knowledge_after_bundle_release(self):
        task = start_task(self.owner, self.prepare())
        original = task.context_snapshot["knowledge"]
        task = pause_task(self.owner, task)
        with patch("apps.central.services.knowledge_bundle", return_value={"version": "new", "digest": "new"}):
            task = resume_task(self.owner, task)
        self.assertEqual(task.context_snapshot["knowledge"], original)

    def test_tampered_frozen_bundle_blocks_dispatch(self):
        task = self.prepare()
        snapshot = task.context_snapshot
        snapshot["knowledge"]["rules"] = []
        Task.objects.filter(pk=task.pk).update(context_snapshot=snapshot)
        with self.assertRaises(TaskConflict):
            start_task(self.owner, task)

    def test_expired_claim_is_preserved_and_old_worker_is_fenced(self):
        task = start_task(self.owner, self.prepare())
        Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
        another = start_task(self.owner, self.prepare("two"))
        task.refresh_from_db()
        self.assertEqual(task.status, "blocked")
        self.assertEqual(another.status, "running")
        with self.assertRaises(TaskConflict):
            self.checkpoint(task)

    def test_checkpoint_cannot_skip_stage_or_use_stale_revision(self):
        task = start_task(self.owner, self.prepare())
        with self.assertRaises(TaskConflict):
            record_checkpoint(self.owner, task, "delivery", "Tudo concluído", [], "x", task.revision, task.lease_token)
        stale_revision = task.revision
        task = self.checkpoint(task)
        with self.assertRaises(TaskConflict):
            record_checkpoint(self.owner, task, "decision", "Decisão conferida", [], "y", stale_revision, task.lease_token)

    def test_checkpoint_replay_is_idempotent(self):
        task = start_task(self.owner, self.prepare())
        original_revision, token = task.revision, task.lease_token
        completed = self.checkpoint(task)
        replay = record_checkpoint(self.owner, task, "intake", "Etapa conferida com evidências.", [], "stage-intake", original_revision, token)
        self.assertEqual(completed.revision, replay.revision)
        self.assertEqual(task.events.filter(kind="checkpoint").count(), 1)

    def test_self_report_cannot_be_promoted_to_verified_result(self):
        task = start_task(self.owner, self.prepare())
        task = self.checkpoint(task, [{"kind": "verified_result", "result": "passed"}])
        self.assertEqual(task.steps.get(key="intake").evidence[0]["kind"], "self_report")
        while task.current_stage != "validation":
            task = self.checkpoint(task)
        with self.assertRaises(ValueError):
            self.checkpoint(task, [{"result": "passed"}])
        self.assertEqual(task.steps.get(key="validation").status, "pending")

    def test_verified_criteria_and_human_approval_are_separate(self):
        task = start_task(self.owner, self.prepare())
        while task.current_stage != "validation":
            task = self.checkpoint(task)
        receipt = record_verification(task, "contract-inspection-v1", "passed", {"digest": self.contract.digest}, [0], task.lease_token, task.revision)
        task.refresh_from_db()
        task = self.checkpoint(task, [{"receipt_id": str(receipt.pk)}])
        task = self.checkpoint(task)
        self.assertEqual(task.status, "review")
        task = approve_task(self.owner, task, expected_revision=task.revision)
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.outcome["integration"], "not_requested")
        self.assertEqual(task.outcome["deployment"], "not_requested")
        self.assertEqual(task.outcome["cleanup"], "retained")

    def test_receipt_from_another_task_cannot_validate(self):
        first = start_task(self.owner, self.prepare())
        receipt = record_verification(first, "contract-inspection-v1", "passed", {}, [0], first.lease_token)
        first = pause_task(self.owner, first)
        second = start_task(self.owner, self.prepare("two"))
        with self.assertRaises(ValueError):
            self.checkpoint(second, [{"receipt_id": str(receipt.pk)}])

    def test_human_review_is_explicit_idempotent_and_not_a_technical_test(self):
        task = start_task(self.owner, self.prepare())
        while task.current_stage != "validation":
            task = self.checkpoint(task)
        revision = task.revision
        receipt = record_human_review(self.owner, task, [0], "Conferi o contrato no projeto.", revision, "review-1")
        replay = record_human_review(self.owner, task, [0], "Conferi o contrato no projeto.", revision, "review-1")
        self.assertEqual(receipt.pk, replay.pk)
        self.assertFalse(receipt.payload["technical_validation"])
        task.refresh_from_db()
        task = self.checkpoint(task, [{"receipt_id": str(receipt.pk)}])
        evidence = task.steps.get(key="validation").evidence[0]
        self.assertEqual(evidence["kind"], "human_review")
        self.assertEqual(evidence["evidence_level"], "human_review")

    def test_reader_cannot_create_human_acceptance(self):
        task = start_task(self.owner, self.prepare())
        while task.current_stage != "validation":
            task = self.checkpoint(task)
        with self.assertRaises(PermissionDenied):
            record_human_review(self.reader, task, [0], "Conferi o contrato.", task.revision)

    def test_human_review_cannot_skip_validation_or_forge_criteria(self):
        task = start_task(self.owner, self.prepare())
        with self.assertRaises(TaskConflict):
            record_human_review(self.owner, task, [0], "Conferi o contrato.", task.revision)
        with self.assertRaises(ValueError):
            record_human_review(self.owner, task, [99], "Conferi o contrato.", task.revision)

    def test_observation_is_idempotent_without_advancing_or_upgrading(self):
        task = start_task(self.owner, self.prepare())
        record_observation(self.owner, task, "git_observed", {"head": "abc"}, "git-1")
        record_observation(self.owner, task, "git_observed", {"head": "abc"}, "git-1")
        task.refresh_from_db()
        self.assertEqual(task.current_stage, "intake")
        self.assertEqual(task.events.filter(kind="git_observed").count(), 1)
        with self.assertRaises(ValueError):
            record_observation(self.owner, task, "verified_result", {})
        event = task.events.first()
        with self.assertRaises(ValidationError):
            event.save()
        self.assertNotIn("lease_token", task_context(task))
