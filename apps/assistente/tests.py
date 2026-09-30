from unittest.mock import patch
from django.test import TestCase,override_settings
from apps.projetos.tests import ProjectWorkflowTests
from apps.projetos.services import queue_inventory,process_one
from agentic_core.assessment import validate_response,compose
from .assessments import prepare_assessment,authorize,process_assessment
from .providers import ProviderFailure

def answer(payload,choice='supported'):
    return {'model':payload['model'],'answers':{key:{'type':'choice','choice':choice,'confidence':.9,'probabilities':{name:(.9 if name==choice else .1/3) for name in question['criteria']}} for key,question in payload['questions'].items()},'usage':{'input_tokens':100,'output_tokens':10}}

class AssessmentTests(TestCase):
    setUp=ProjectWorkflowTests.setUp
    def run_plan(self):
        queue_inventory(self.project);process_one()
        return prepare_assessment(self.user,self.project,'Criar um site',['Produzir frontend'],[s['id'] for s in self.project.latest.graph['sources']][:2])

    def test_prepare_never_calls_provider_and_key_required(self):
        with patch('apps.assistente.assessments.evaluate',side_effect=AssertionError('unexpected call')):
            run=self.run_plan();self.assertEqual(run.status,'prepared');self.assertFalse(process_assessment())
        with self.assertRaises(ValueError):authorize(run,self.user,run.plan['hash'])

    @override_settings(JEV_IA='test-only')
    def test_authorization_idempotency_and_demand_only(self):
        run=self.run_plan();authorize(run,self.user,run.plan['hash']);authorize(run,self.user,run.plan['hash'])
        with patch('apps.assistente.assessments.evaluate',side_effect=answer) as provider:
            self.assertTrue(process_assessment());self.assertFalse(process_assessment());self.assertEqual(provider.call_count,run.plan['calls'])
        run.refresh_from_db();self.assertEqual(run.status,'done');self.assertTrue(run.summary['declared_support'])

    @override_settings(JEV_IA='test-only')
    def test_partial_progress_and_uncertain_no_retry(self):
        run=self.run_plan();authorize(run,self.user,run.plan['hash'])
        with patch('apps.assistente.assessments.evaluate',side_effect=[answer(run.plan['parts'][0]['request']),ProviderFailure('timeout',uncertain=True)]) as provider:
            process_assessment();self.assertFalse(process_assessment());self.assertEqual(provider.call_count,2)
        run.refresh_from_db();self.assertEqual(run.status,'uncertain');self.assertIsNotNone(run.results[0]);self.assertIsNone(run.results[1]);self.assertFalse(run.summary['complete'])

    @override_settings(JEV_IA='test-only')
    def test_plan_snapshot_divergence_blocks(self):
        run=self.run_plan()
        with self.assertRaises(ValueError):authorize(run,self.user,'incorrect')
        (self.folder/'AGENTS.md').write_text('# changed',encoding='utf8');queue_inventory(self.project);process_one()
        with self.assertRaises(ValueError):authorize(run,self.user,run.plan['hash'])

    def test_strict_schema(self):
        run=self.run_plan();payload=run.plan['parts'][0]['request'];valid=answer(payload);validate_response(valid,payload['questions'])
        valid['answers']['criterion_0']['probabilities']['supported']=float('nan')
        with self.assertRaises(ValueError):validate_response(valid,payload['questions'])
        valid=answer(payload);valid['usage']['input_tokens']=True
        with self.assertRaises(ValueError):validate_response(valid,payload['questions'])

    def test_mandatory_criteria_not_averaged(self):
        run=self.run_plan();plan=run.plan;plan['criteria']=['Frontend','Acessibilidade']
        results=[]
        for part in plan['parts']:
            result=answer(part['request']);result['answers']['criterion_1']={'type':'choice','choice':'unknown','confidence':1,'probabilities':{'supported':0,'partial':0,'absent':0,'unknown':1}};results.append(result)
        self.assertFalse(compose(plan,results)['declared_support'])

    @override_settings(JEV_IA='test-only')
    def test_live_change_before_inventory_and_permission_revocation(self):
        run=self.run_plan()
        (self.folder/'AGENTS.md').write_text('# New architecture',encoding='utf8')
        with self.assertRaises(ValueError):authorize(run,self.user,run.plan['hash'])
        run=self.run_plan();authorize(run,self.user,run.plan['hash'])
        self.user.is_active=False;self.user.save()
        with patch('apps.assistente.assessments.evaluate',side_effect=AssertionError('revoked')):process_assessment()
        run.refresh_from_db();self.assertEqual(run.status,'failed')

class ChatTests(TestCase):
    setUp=ProjectWorkflowTests.setUp
    def test_selected_node_context_is_pinned_and_authorized(self):
        import uuid
        from django.http import Http404
        from .conversations import send_message
        queue_inventory(self.project);process_one()
        snapshot=self.project.latest;node=next(n for n in snapshot.graph['nodes'] if n['kind']=='skill')
        selection={'id':node['id'],'snapshot_id':str(snapshot.pk)}
        turn=send_message(self.user,'Explique este elemento',self.project.pk,uuid.uuid4(),uuid.uuid4(),selection=selection)
        self.assertEqual(turn.answer['results'][0]['id'],node['id']);self.assertEqual(turn.context['selection'],selection)
        with self.assertRaises(Http404):send_message(self.other,'Explique',self.project.pk,uuid.uuid4(),uuid.uuid4(),selection=selection)
        with self.assertRaises(Http404):send_message(self.user,'Explique',self.project.pk,uuid.uuid4(),uuid.uuid4(),selection={**selection,'id':'unknown'})
    def test_scope_history_and_message_idempotency(self):
        import uuid
        from .conversations import send_message,turn_data
        queue_inventory(self.project);process_one()
        conversation=uuid.uuid4();request=uuid.uuid4()
        turn=send_message(self.user,'Criar site',self.project.pk,conversation,request)
        self.assertEqual(send_message(self.user,'Criar site',self.project.pk,conversation,request).pk,turn.pk)
        next_turn=send_message(self.user,'E como faço isso?',self.project.pk,conversation,uuid.uuid4())
        self.assertTrue(next_turn.context['history']);self.assertTrue(next_turn.answer['results'])
        from django.http import Http404
        with self.assertRaises(Http404):turn_data(self.other,turn)
        self.project.active=False;self.project.save()
        with self.assertRaises(Http404):turn_data(self.user,turn)
    def test_ai_gate_and_cancelled_permission_before_provider(self):
        import uuid
        from .conversations import send_message,process_chat
        with self.assertRaises(ValueError):send_message(self.user,'Criar site',self.project.pk,uuid.uuid4(),uuid.uuid4(),'ai')
        with override_settings(TEXT_CONFIGURED=True):turn=send_message(self.user,'Criar site',self.project.pk,uuid.uuid4(),uuid.uuid4(),'ai')
        self.user.is_active=False;self.user.save()
        with patch('apps.assistente.conversations.converse',side_effect=AssertionError('should not call')):process_chat()
        turn.refresh_from_db();self.assertEqual(turn.status,'failed')
