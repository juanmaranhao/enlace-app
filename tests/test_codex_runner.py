"""Protocolo real em stdio com servidor falso; nenhum modelo ou API é chamado."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase

from agentic_core.codex_runner import CodexReadOnlyRunner, CodexRunnerError, POLICY_VERSION


SERVER = r'''
import json,sys
scenario=sys.argv[1]
log=sys.argv[2]
def send(value):
    print(json.dumps(value),flush=True)
def terminal():
    send({'method':'item/completed','params':{'threadId':'thread-1','turnId':'turn-1','item':{'id':'message-1','type':'agentMessage','text':'Parecer limitado. token=secreto-nao-persistir'}}})
    send({'method':'turn/completed','params':{'threadId':'thread-1','turn':{'id':'turn-1','status':'failed' if scenario=='failed' else 'completed'}}})
for line in sys.stdin:
    m=json.loads(line)
    with open(log,'a',encoding='utf8') as f:f.write(json.dumps(m)+'\n')
    method=m.get('method')
    if method=='initialize':send({'id':m['id'],'result':{}})
    elif method in ('thread/start','thread/resume'):
        assert m['params']['sandbox']=='read-only'
        assert m['params']['approvalPolicy']=='never'
        send({'id':m['id'],'result':{'thread':{'id':'thread-1'},'cwd':m['params']['cwd'],'sandbox':{'type':'readOnly'},'approvalPolicy':'never','instructionSources':[]}})
    elif method=='mcpServerStatus/list':
        servers=[{'name':'unexpected','runtimeStatus':'disabled','tools':{},'resources':[],'resourceTemplates':[]}] if scenario=='disabled' else ([{'name':'unexpected'}] if scenario=='mcp' else [])
        send({'id':m['id'],'result':{'data':servers,'nextCursor':None}})
    elif method=='turn/start':
        assert m['params']['sandboxPolicy']=={'type':'readOnly','networkAccess':False}
        if scenario=='early':terminal()
        send({'id':m['id'],'result':{'turn':{'id':'turn-1'}}})
        if scenario in ('normal','failed'):
            send({'id':'approval-1','method':'item/commandExecution/requestApproval','params':{'command':'cat .env TOKEN=supersecret','threadId':'thread-1','turnId':'turn-1'}})
        elif scenario=='exit':sys.exit(0)
    elif m.get('id')=='approval-1':
        assert m['result']['decision']=='decline'
        terminal()
    elif method=='turn/interrupt':
        send({'id':m['id'],'result':{}})
        send({'method':'turn/completed','params':{'turn':{'id':'turn-1','status':'interrupted'}}})
'''


class CodexRunnerTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / "protocol.jsonl"
        self.commands = []

    def runner(self, scenario="normal"):
        def factory(command, **kwargs):
            self.commands.append((command, kwargs))
            return subprocess.Popen([sys.executable, "-u", "-c", SERVER, scenario, str(self.log)], **kwargs)
        return CodexReadOnlyRunner(sys.executable, popen=factory)

    def messages(self):
        return [json.loads(line) for line in self.log.read_text(encoding="utf8").splitlines()]

    def test_context_execution_denies_approval_and_omits_sensitive_events(self):
        events = []
        receipt = self.runner().run(self.root, [self.root], "Avalie o contexto de teste.", on_event=events.append)
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["evidence_level"], "self_report")
        self.assertIn("[redigido]", receipt["answer"])
        self.assertNotIn("supersecret", json.dumps(events))
        self.assertNotIn(".env", json.dumps(events))
        self.assertEqual(events[0]["type"], "thread_ready")
        self.assertEqual(events[-1]["type"], "runner_finished")
        self.assertIn("features.shell_tool=false", self.commands[0][0])
        self.assertFalse(self.commands[0][1]["shell"])

    def test_resume_requires_same_root_and_policy_receipt(self):
        receipt = {"root": str(self.root), "thread_id": "thread-1", "policy_version": POLICY_VERSION}
        result = self.runner().run(self.root, [self.root], "Continue a análise.", thread_id="thread-1", resume_receipt=receipt)
        self.assertEqual(result["status"], "completed")
        self.assertIn("thread/resume", [m.get("method") for m in self.messages()])
        with self.assertRaises(CodexRunnerError):
            self.runner().run(self.root, [self.root], "Continue.", thread_id="thread-1", resume_receipt={**receipt, "root": "/another"})

    def test_failed_completed_event_does_not_report_success(self):
        receipt = self.runner("failed").run(self.root, [self.root], "Teste.")
        self.assertEqual(receipt["status"], "failed")

    def test_probe_does_not_start_model(self):
        receipt = self.runner().probe(self.root, [self.root])
        self.assertEqual(receipt["status"], "ready")
        self.assertFalse(receipt["model_invoked"])
        self.assertNotIn("turn/start", [m.get("method") for m in self.messages()])

    def test_mcp_inventory_blocks_before_model(self):
        receipt = self.runner("mcp").run(self.root, [self.root], "Teste.")
        self.assertEqual(receipt["status"], "failed")
        self.assertNotIn("turn/start", [m.get("method") for m in self.messages()])

    def test_disabled_mcp_with_empty_catalog_is_allowed(self):
        receipt = self.runner("disabled").probe(self.root, [self.root])
        self.assertEqual(receipt["status"], "ready")
        self.assertEqual(receipt["mcp_servers"], 0)
        self.assertEqual(receipt["mcp_inventory"][0]["runtime_status"], "disabled")

    def test_completion_before_start_reply_is_not_lost(self):
        receipt = self.runner("early").run(self.root, [self.root], "Teste.")
        self.assertEqual(receipt["status"], "completed")

    def test_process_exit_is_failure(self):
        receipt = self.runner("exit").run(self.root, [self.root], "Teste.")
        self.assertEqual(receipt["status"], "failed")

    def test_cancel_sends_interrupt_and_preserves_receipt(self):
        events = []
        receipt = self.runner("wait").run(self.root, [self.root], "Teste.",
            on_event=events.append, cancelled=lambda: any(e["type"] == "turn_ready" for e in events))
        self.assertEqual(receipt["status"], "interrupted")
        self.assertEqual(receipt["thread_id"], "thread-1")
        self.assertIn("turn/interrupt", [m.get("method") for m in self.messages()])

    def test_timeout_is_not_success_and_does_not_retry(self):
        receipt = self.runner("wait").run(self.root, [self.root], "Teste.", timeout=1)
        self.assertEqual(receipt["status"], "timed_out")
        self.assertEqual(sum(m.get("method") == "turn/start" for m in self.messages()), 1)

    def test_outside_allowed_root_never_starts_process(self):
        child = self.root / "allowed"
        child.mkdir()
        with self.assertRaises(ValueError):
            self.runner().run(self.root, [child], "Teste.")
        self.assertEqual(self.commands, [])

    def test_persistence_failure_interrupts_and_propagates(self):
        def callback(event):
            if event["type"] == "turn_ready":
                raise RuntimeError("storage unavailable")
        with self.assertRaisesRegex(RuntimeError, "storage unavailable"):
            self.runner("wait").run(self.root, [self.root], "Teste.", on_event=callback)
        self.assertIn("turn/interrupt", [m.get("method") for m in self.messages()])
