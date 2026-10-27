"""A central opera por sessão autorizada; renderizar páginas não aciona IA."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.projetos.models import Project
from .models import CodexRun, Task
from .services import configure_contract, prepare_task, record_checkpoint, start_task


class CentralFixture(TestCase):
    """Projeto temporário sem dependência dos dados ou ambientes da instalação."""

    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / "AGENTS.md").write_text("Respeitar o contrato local.", encoding="utf-8")
        (self.root / ".env").write_text("PRIVATE_TEST_VALUE=never-index-me", encoding="utf-8")
        self.override = override_settings(ENLACE_ALLOWED_ROOTS=[self.root], ENLACE_CENTRAL_RUN_TIMEOUT=15, ENLACE_CODEX_EXECUTABLE="")
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.owner = get_user_model().objects.create_user("central-owner", is_staff=True)
        self.reader = get_user_model().objects.create_user("central-reader", is_staff=True)
        self.stranger = get_user_model().objects.create_user("central-stranger", is_staff=True)
        self.project = Project.objects.create(name="Projeto de teste", root=str(self.root), canonical_key=str(self.root).casefold(), owner=self.owner)
        self.project.readers.add(self.reader)
        self.contract = configure_contract(self.owner, self.project, {"stack": "Django · Python", "restrictions": ["Preservar dados."], "execution_mode": "guided"})
        self.task = prepare_task(self.owner, self.project, "Conferir o contexto do projeto de teste", "audit", ["Projeto e contrato identificados"], "fixture-task")

    def url(self, name):
        return reverse(name, kwargs={"pk": self.task.pk})

    def validation_task(self):
        task = start_task(self.owner, self.task)
        while task.current_stage != "validation":
            task = record_checkpoint(self.owner, task, task.current_stage, "Etapa de preparação conferida.", [], f"prepare-{task.current_stage}", task.revision, task.lease_token)
        self.task = task
        return task


class CentralWebTests(CentralFixture):
    def test_anonymous_pages_require_login_and_bearer_is_not_a_session(self):
        names = ["central_home", "central_brain", "central_task_new"]
        urls = [reverse(name) for name in names] + [self.url("central_task_detail"), self.url("central_task_context")]
        for url in urls:
            response = self.client.get(url, HTTP_AUTHORIZATION="Bearer not-a-session")
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("login"), response["Location"])

    def test_owner_can_read_all_pages_without_starting_tools(self):
        self.client.force_login(self.owner)
        urls = [reverse("central_home"), reverse("central_brain"), reverse("central_task_new"),
                reverse("central_contract", kwargs={"pk": self.project.pk}), self.url("central_task_detail"), self.url("central_task_context")]
        with patch("apps.central.execution.CodexReadOnlyRunner") as runner, patch("apps.central.execution.inspect_repository") as inspect:
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 200, url)
            runner.assert_not_called()
            inspect.assert_not_called()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "prepared")
        self.assertEqual(CodexRun.objects.count(), 0)

    def test_reader_can_read_but_cannot_mutate_by_direct_links(self):
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(self.url("central_task_detail")).status_code, 200)
        self.assertEqual(self.client.get(self.url("central_task_context")).status_code, 200)
        self.assertEqual(self.client.get(reverse("central_contract", kwargs={"pk": self.project.pk})).status_code, 404)
        for name in ("central_task_action", "central_task_checkpoint", "central_task_probe", "central_task_codex"):
            self.assertEqual(self.client.post(self.url(name), {"action": "start", "expected_revision": self.task.revision}).status_code, 404)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "prepared")

    def test_unrelated_staff_cannot_download_context_or_see_task(self):
        self.client.force_login(self.stranger)
        for name in ("central_task_detail", "central_task_context"):
            self.assertEqual(self.client.get(self.url(name)).status_code, 404)
        self.assertNotContains(self.client.get(reverse("central_home")), self.task.objective)

    def test_nonstaff_has_no_central_access(self):
        user = get_user_model().objects.create_user("ordinary")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("central_home")).status_code, 403)

    def test_create_task_post_is_idempotent_and_does_not_run_codex(self):
        self.client.force_login(self.owner)
        payload = {"project": str(self.project.pk), "objective": "Preparar uma entrega verificável", "workflow": "coding", "criteria": "Resultado demonstrado\nContrato preservado", "request_key": str(uuid.uuid4())}
        with patch("apps.central.execution.CodexReadOnlyRunner") as runner:
            first = self.client.post(reverse("central_task_new"), payload)
            second = self.client.post(reverse("central_task_new"), payload)
            runner.assert_not_called()
        self.assertEqual(first.status_code, 302)
        self.assertEqual(first["Location"], second["Location"])
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(CodexRun.objects.count(), 0)

    def test_reader_cannot_forge_project_in_task_form(self):
        self.client.force_login(self.reader)
        response = self.client.post(reverse("central_task_new"), {"project": str(self.project.pk), "objective": "Pedido não autorizado", "workflow": "audit", "criteria": "Verificar acesso", "request_key": str(uuid.uuid4())})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), 1)

    def test_contract_form_publishes_revision_without_rewriting_task(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("central_contract", kwargs={"pk": self.project.pk}), {"stack": "Django · PostgreSQL", "restrictions": "Preservar dados.\nNão publicar sem aprovação.", "execution_mode": "read_only", "validation_commands": "python manage.py check"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.project.contracts.count(), 2)
        self.task.refresh_from_db()
        self.assertEqual(self.task.context_snapshot["contract"]["revision"], 1)

    def test_task_context_omits_lease_token_and_private_source_contents(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url("central_task_context"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["project"]["id"], str(self.project.pk))
        self.assertEqual(payload["context"]["contract"]["revision"], 1)
        self.assertNotIn("lease_token", payload)
        self.assertNotIn("never-index-me", response.content.decode())
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))

    def test_actions_require_post_and_csrf(self):
        self.client.force_login(self.owner)
        for name in ("central_task_action", "central_task_checkpoint", "central_task_probe", "central_task_codex"):
            self.assertEqual(self.client.get(self.url(name)).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.post(self.url("central_task_action"), {"action": "start", "expected_revision": self.task.revision})
        self.assertEqual(response.status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "prepared")

    def test_codex_post_only_queues_and_replays_same_intention(self):
        self.task = start_task(self.owner, self.task)
        self.client.force_login(self.owner)
        with patch("apps.central.execution.CodexReadOnlyRunner") as runner:
            for _ in range(2):
                self.assertEqual(self.client.post(self.url("central_task_codex"), {"operation_key": "web-intention"}).status_code, 302)
            runner.assert_not_called()
        self.assertEqual(CodexRun.objects.count(), 1)
        self.assertEqual(CodexRun.objects.get().status, "queued")

    def test_human_review_requires_session_csrf_and_preserves_evidence_level(self):
        task = self.validation_task()
        url = self.url("central_task_human_review")
        payload = {"criteria_indices": ["0"], "note": "Conferi o contrato e a identificação do projeto.", "expected_revision": task.revision, "request_key": str(uuid.uuid4())}
        anonymous = self.client.post(url, payload, HTTP_AUTHORIZATION="Bearer cannot-authorize-human-review")
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn(reverse("login"), anonymous["Location"])
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(url, payload).status_code, 403)
        client.get(self.url("central_task_detail"))
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        response = client.post(url, {**payload, "csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 302)
        event = task.events.get(kind="human_review")
        self.assertFalse(event.payload["technical_validation"])
        self.assertEqual(event.payload["evidence_level"], "human_review")
        self.assertEqual(task.events.filter(kind="verified_result").count(), 0)

    def test_reader_cannot_register_human_review(self):
        task = self.validation_task()
        self.client.force_login(self.reader)
        response = self.client.post(self.url("central_task_human_review"), {"criteria_indices": ["0"], "note": "Conferi os critérios.", "expected_revision": task.revision, "request_key": str(uuid.uuid4())})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(task.events.filter(kind="human_review").exists())
