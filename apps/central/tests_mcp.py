"""Fronteiras do MCP local: operador, allowlist e posse não vêm da ferramenta."""
import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

from apps.projetos.models import Project
from integrations.central_mcp import dispatch, mcp
from .models import Task
from .services import configure_contract, prepare_task


class CentralMCPTests(TransactionTestCase):
    """Transações reais evitam alterar a semântica de close_old_connections."""

    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / "AGENTS.md").write_text("Contrato local do piloto.", encoding="utf-8")
        other_root = self.root / "other-project"
        other_root.mkdir()
        (other_root / "AGENTS.md").write_text("Outro projeto autorizado no host.", encoding="utf-8")
        self.override = override_settings(ENLACE_ALLOWED_ROOTS=[self.root])
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.owner = get_user_model().objects.create_user("mcp-owner", is_staff=True)
        self.reader = get_user_model().objects.create_user("mcp-reader", is_staff=True)
        self.project = Project.objects.create(name="Projeto habilitado", root=str(self.root), canonical_key=str(self.root).casefold(), owner=self.owner)
        self.other = Project.objects.create(name="Projeto fora da allowlist", root=str(other_root), canonical_key=str(other_root).casefold(), owner=self.owner)
        self.project.readers.add(self.reader)
        for project in (self.project, self.other):
            configure_contract(self.owner, project, {"stack": "Django", "execution_mode": "guided"})
        self.task = prepare_task(self.owner, self.project, "Conferir o projeto habilitado", "audit", ["Contrato identificado"], "fixture")
        self.other_task = prepare_task(self.owner, self.other, "Conferir outro projeto", "audit", ["Outro contrato identificado"], "other-fixture")
        self.environment = patch.dict(os.environ, {"ENLACE_OPERATOR": self.owner.username, "ENLACE_CENTRAL_PROJECT_IDS": str(self.project.pk)})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def start(self):
        return dispatch("start", task_id=str(self.task.pk), revision=self.task.revision)

    def test_missing_operator_or_allowlist_fails_closed(self):
        for values in ({"ENLACE_OPERATOR": ""}, {"ENLACE_CENTRAL_PROJECT_IDS": ""}):
            with patch.dict(os.environ, values), self.assertRaises(ToolError):
                dispatch("projects")

    def test_unknown_inactive_and_nonstaff_operators_are_rejected(self):
        with patch.dict(os.environ, {"ENLACE_OPERATOR": "missing-operator"}), self.assertRaises(ToolError):
            dispatch("projects")
        for updates in ({"is_active": False, "is_staff": True}, {"is_active": True, "is_staff": False}):
            get_user_model().objects.filter(pk=self.owner.pk).update(**updates)
            with self.assertRaises(ToolError):
                dispatch("projects")

    def test_allowlist_filters_projects_and_blocks_task_ids_from_other_projects(self):
        projects = dispatch("projects")["projects"]
        self.assertEqual([item["id"] for item in projects], [str(self.project.pk)])
        with self.assertRaises(ToolError):
            dispatch("context", task_id=str(self.other_task.pk))
        with self.assertRaises(ToolError):
            dispatch("prepare", project_id=str(self.other.pk), objective="Pedido fora da allowlist", workflow="audit", criteria=["Sem acesso"], operation_key="forbidden")
        self.assertEqual(Task.objects.count(), 2)

    def test_disabled_project_is_not_available_even_with_explicit_allowlist(self):
        Project.objects.filter(pk=self.project.pk).update(active=False)
        self.assertEqual(dispatch("projects")["projects"], [])
        with self.assertRaises(ToolError):
            dispatch("context", task_id=str(self.task.pk))

    def test_malformed_allowlist_is_an_actionable_tool_error(self):
        with patch.dict(os.environ, {"ENLACE_CENTRAL_PROJECT_IDS": "not-a-uuid"}), self.assertRaises(ToolError):
            dispatch("projects")

    def test_prepare_replay_is_idempotent_and_changed_payload_is_rejected(self):
        payload = {"project_id": str(self.project.pk), "objective": "Preparar nova entrega", "workflow": "coding", "criteria": ["Entrega verificável"], "operation_key": "prepare-one"}
        first = dispatch("prepare", **payload)
        replay = dispatch("prepare", **payload)
        self.assertEqual(first["task_id"], replay["task_id"])
        self.assertNotIn("lease_token", first)
        self.assertEqual(Task.objects.count(), 3)
        with self.assertRaises(ToolError):
            dispatch("prepare", **{**payload, "objective": "Pedido diferente na mesma chave"})
        self.assertEqual(Task.objects.count(), 3)

    def test_context_never_exposes_or_renews_execution_lease(self):
        started = self.start()
        self.assertTrue(started["lease_token"])
        self.task.refresh_from_db()
        before = (self.task.lease_token, self.task.lease_generation, self.task.lease_expires_at, self.task.revision)
        context = dispatch("context", task_id=str(self.task.pk))
        self.assertNotIn("lease_token", context)
        self.assertNotIn(started["lease_token"], str(context))
        self.task.refresh_from_db()
        self.assertEqual(before, (self.task.lease_token, self.task.lease_generation, self.task.lease_expires_at, self.task.revision))

    def test_reader_can_obtain_context_but_cannot_claim_or_prepare(self):
        with patch.dict(os.environ, {"ENLACE_OPERATOR": self.reader.username}):
            self.assertEqual(dispatch("context", task_id=str(self.task.pk))["task_id"], str(self.task.pk))
            with self.assertRaises(ToolError):
                self.start()
            with self.assertRaises(ToolError):
                dispatch("prepare", project_id=str(self.project.pk), objective="Pedido indevido", workflow="audit", criteria=["Acesso verificado"], operation_key="reader-request")
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "prepared")

    def test_checkpoint_requires_current_stage_revision_and_lease(self):
        started = self.start()
        payload = {"task_id": str(self.task.pk), "revision": started["revision"], "stage_key": "delivery", "note": "Tentativa de pular o plano", "evidence": [], "operation_key": "skip-stage", "lease_token": started["lease_token"]}
        with self.assertRaises(ToolError):
            dispatch("checkpoint", **payload)
        with self.assertRaises(ToolError):
            dispatch("checkpoint", **{**payload, "stage_key": "intake", "lease_token": "not-the-owner-token"})
        self.task.refresh_from_db()
        self.assertEqual(self.task.current_stage, "intake")
        self.assertFalse(self.task.events.filter(kind="checkpoint").exists())

    def test_checkpoint_replay_preserves_self_report_and_does_not_expose_lease(self):
        started = self.start()
        payload = {"task_id": str(self.task.pk), "revision": started["revision"], "stage_key": "intake", "note": "Objetivo delimitado com o contexto local.", "evidence": [{"kind": "verified_result", "result": "passed", "note": "Relato do agente."}], "operation_key": "checkpoint-one", "lease_token": started["lease_token"]}
        first = dispatch("checkpoint", **payload)
        replay = dispatch("checkpoint", **payload)
        self.assertEqual(first["revision"], replay["revision"])
        self.assertNotIn("lease_token", first)
        self.assertEqual(first["steps"][0]["evidence"][0]["kind"], "self_report")
        self.assertEqual(self.task.events.filter(kind="checkpoint").count(), 1)

    def test_resume_revokes_old_token_and_read_context_cannot_recover_it(self):
        started = self.start()
        paused = dispatch("pause", task_id=str(self.task.pk), revision=started["revision"], note="Pausa explícita.")
        self.assertNotIn("lease_token", paused)
        resumed = dispatch("resume", task_id=str(self.task.pk), revision=paused["revision"])
        self.assertNotEqual(started["lease_token"], resumed["lease_token"])
        self.assertNotIn("lease_token", dispatch("context", task_id=str(self.task.pk)))
        with self.assertRaises(ToolError):
            dispatch("checkpoint", task_id=str(self.task.pk), revision=resumed["revision"], stage_key="intake", note="Executor anterior tenta escrever", evidence=[], operation_key="stale-worker", lease_token=started["lease_token"])

    def test_mcp_does_not_publish_human_approval_or_destructive_tools(self):
        async def scenario():
            async with Client(mcp) as client:
                listed = await client.list_tools()
                names = {tool.name for tool in listed.tools}
                self.assertEqual(names, {"list_work_projects", "prepare_work", "get_work_context", "start_work", "pause_work", "resume_work", "record_work_checkpoint"})
                with patch("integrations.central_mcp.dispatch", return_value={"projects": []}) as route:
                    response = await client.call_tool("list_work_projects", {})
                    self.assertEqual(response.structured_content["projects"], [])
                    route.assert_called_once_with("projects")
        asyncio.run(scenario())
        with self.assertRaises(ToolError):
            dispatch("human_review", task_id=str(self.task.pk))

    def test_inprocess_mcp_tools_reach_the_real_scoped_database(self):
        """Exercita também a ponte sync/async do SDK, sem mockar o dispatcher."""
        async def scenario():
            async with Client(mcp) as client:
                listed = await client.call_tool("list_work_projects", {})
                self.assertFalse(listed.is_error, str(listed.content))
                self.assertEqual([item["id"] for item in listed.structured_content["projects"]], [str(self.project.pk)])
                context = await client.call_tool("get_work_context", {"task_id": str(self.task.pk)})
                self.assertFalse(context.is_error, str(context.content))
                self.assertEqual(context.structured_content["task_id"], str(self.task.pk))
                self.assertNotIn("lease_token", context.structured_content)
        asyncio.run(scenario())
