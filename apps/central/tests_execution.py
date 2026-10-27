"""Integração worker/registro: processo externo sempre fica atrás de intenção."""
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from .execution import observe_task, process_consultation, queue_consultation
from .models import CodexRun, Task
from .services import pause_task, record_checkpoint, resume_task, start_task
from .tests_web import CentralFixture


class CentralExecutionTests(CentralFixture):
    def setUp(self):
        super().setUp()
        self.task = start_task(self.owner, self.task)
        self.observation = {"root": str(self.root), "status": "observed", "head": "a" * 40, "dirty": False, "cleanup": "not_evaluated"}

    def test_queue_has_no_model_side_effect_and_is_idempotent(self):
        with patch("apps.central.execution.CodexReadOnlyRunner") as runner:
            first = queue_consultation(self.owner, self.task, "one")
            replay = queue_consultation(self.owner, self.task, "one")
            runner.assert_not_called()
        self.assertEqual(first.pk, replay.pk)
        self.assertEqual(first.result["requested_task_generation"], self.task.lease_generation)
        self.assertEqual(first.result["requested_revision"], self.task.revision)
        self.assertEqual(CodexRun.objects.count(), 1)

    def test_second_active_intention_is_rejected(self):
        queue_consultation(self.owner, self.task, "one")
        with self.assertRaises(ValueError):
            queue_consultation(self.owner, self.task, "two")

    def test_worker_records_observed_events_without_claiming_validation(self):
        run = queue_consultation(self.owner, self.task, "one")

        def execute(root, allowed, prompt, **kwargs):
            self.assertEqual(root, str(self.root))
            self.assertIn(self.task.objective, prompt)
            self.assertFalse(kwargs["cancelled"]())
            kwargs["on_event"]({"event": "thread_started", "thread_id": "thread-test"})
            return {"status": "completed", "thread_id": "thread-test", "answer": "Projeto correto; próximo passo: revisar o contrato."}

        with patch("apps.central.execution.inspect_repository", return_value=self.observation), patch("apps.central.execution.CodexReadOnlyRunner") as runner:
            runner.return_value.run.side_effect = execute
            self.assertTrue(process_consultation())
            runner.return_value.run.assert_called_once()
            self.assertFalse(process_consultation())
        run.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.thread_id, "thread-test")
        self.assertEqual(self.task.current_stage, "intake")
        self.assertEqual(self.task.events.get(kind="codex_result").payload["evidence_level"], "self_report")
        self.assertFalse(self.task.events.filter(kind="verified_result").exists())
        self.assertEqual(queue_consultation(self.owner, self.task, "one").pk, run.pk)

    def test_generation_change_after_queue_does_not_resurrect_old_request(self):
        run = queue_consultation(self.owner, self.task, "one")
        self.task = pause_task(self.owner, self.task)
        self.task = resume_task(self.owner, self.task)
        with patch("apps.central.execution.CodexReadOnlyRunner") as runner, patch("apps.central.execution.inspect_repository") as inspect:
            self.assertTrue(process_consultation())
            runner.assert_not_called()
            inspect.assert_not_called()
        run.refresh_from_db()
        self.assertEqual(run.status, "failed")

    def test_revision_change_after_queue_rejects_outdated_plan(self):
        run = queue_consultation(self.owner, self.task, "one")
        self.task = record_checkpoint(self.owner, self.task, "intake", "Objetivo e projeto conferidos.", [], "advance", self.task.revision, self.task.lease_token)
        with patch("apps.central.execution.CodexReadOnlyRunner") as runner:
            self.assertTrue(process_consultation())
            runner.assert_not_called()
        run.refresh_from_db()
        self.assertEqual(run.status, "failed")

    def test_changed_sources_after_queue_block_model_dispatch(self):
        run = queue_consultation(self.owner, self.task, "one")
        (self.root / "AGENTS.md").write_text("Uma decisão posterior alterou o contexto.", encoding="utf-8")
        with patch("apps.central.execution.CodexReadOnlyRunner") as runner:
            self.assertTrue(process_consultation())
            runner.assert_not_called()
        run.refresh_from_db()
        self.assertEqual(run.status, "failed")

    def test_pause_after_last_callback_prevents_completed_receipt(self):
        run = queue_consultation(self.owner, self.task, "one")

        def execute(*args, **kwargs):
            kwargs["on_event"]({"event": "thread_started", "thread_id": "old-thread"})
            pause_task(self.owner, self.task)
            return {"status": "completed", "thread_id": "old-thread", "answer": "Resposta que chegou depois da pausa."}

        with patch("apps.central.execution.inspect_repository", return_value=self.observation), patch("apps.central.execution.CodexReadOnlyRunner") as runner:
            runner.return_value.run.side_effect = execute
            self.assertTrue(process_consultation())
        run.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(run.status, "interrupted")
        self.assertTrue(run.result["discarded_as_current"])
        self.assertEqual(self.task.status, "paused")
        self.assertEqual(self.task.events.get(kind="codex_result").payload["status"], "interrupted")

    def test_resume_before_old_runner_returns_keeps_new_generation(self):
        run = queue_consultation(self.owner, self.task, "one")
        previous_token = self.task.lease_token

        def execute(*args, **kwargs):
            paused = pause_task(self.owner, self.task)
            resume_task(self.owner, paused)
            return {"status": "completed", "thread_id": "old-thread", "answer": "Resposta da geração antiga."}

        with patch("apps.central.execution.inspect_repository", return_value=self.observation), patch("apps.central.execution.CodexReadOnlyRunner") as runner:
            runner.return_value.run.side_effect = execute
            self.assertTrue(process_consultation())
        run.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(run.status, "interrupted")
        self.assertTrue(run.result["discarded_as_current"])
        self.assertEqual(self.task.status, "running")
        self.assertNotEqual(self.task.lease_token, previous_token)
        self.assertEqual(self.task.lease_generation, 2)

    def test_runner_failure_has_receipt_and_is_not_retried_automatically(self):
        run = queue_consultation(self.owner, self.task, "one")
        with patch("apps.central.execution.inspect_repository", return_value=self.observation), patch("apps.central.execution.CodexReadOnlyRunner") as runner:
            runner.return_value.run.side_effect = OSError("unavailable")
            self.assertTrue(process_consultation())
            self.assertFalse(process_consultation())
            runner.return_value.run.assert_called_once()
        run.refresh_from_db()
        self.assertEqual(run.status, "failed")
        self.assertIsNotNone(run.finished_at)

    def test_abandoned_running_run_is_interrupted_without_requeue(self):
        run = queue_consultation(self.owner, self.task, "one")
        CodexRun.objects.filter(pk=run.pk).update(status="running", heartbeat_at=timezone.now() - timedelta(hours=1))
        with patch("apps.central.execution.CodexReadOnlyRunner") as runner:
            self.assertFalse(process_consultation())
            runner.assert_not_called()
        run.refresh_from_db()
        self.assertEqual(run.status, "interrupted")

    def test_git_observation_does_not_approve_or_authorize_cleanup(self):
        revision = self.task.revision
        with patch("apps.central.execution.inspect_repository", return_value=self.observation):
            result = observe_task(self.owner, self.task)
        self.task.refresh_from_db()
        self.assertEqual(result, self.observation)
        self.assertEqual(self.task.revision, revision)
        self.assertEqual(self.task.outcome["approval"], "pending")
        self.assertEqual(self.task.outcome["cleanup"], "retained")
