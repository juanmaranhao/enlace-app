import hashlib
import uuid
from unittest.mock import patch
from django.test import TestCase,Client
from django.urls import reverse
from apps.projetos.tests import ProjectWorkflowTests
from apps.projetos.services import queue_inventory,process_one
from apps.projetos.actions import prepare_refresh,execute_refresh,task_data
from agentic_core.events import validate_event,bottlenecks
from .models import Connector
from .events import ingest
from integrations.enlace_client import EventBuffer,EnlaceUnavailable

class EvidenceTests(TestCase):
    setUp=ProjectWorkflowTests.setUp
    def event(self,ident='event-1',**details):
        return {'schema_version':1,'external_id':ident,'channel':'product','event_type':'provider_finished','name':'Jev avaliação','occurred_at':'2026-09-30T12:00:00+00:00','details':details}
    def test_idempotent_ordered_and_divergent_event(self):
        first=self.event(duration_ms=125,usage_uncertain=True)
        self.assertEqual(ingest(self.project,[first],'product')['created'],1)
        self.assertEqual(ingest(self.project,[first],'product')['duplicates'],1)
        earlier=self.event('previous');earlier['occurred_at']='2026-09-29T10:00:00+00:00';ingest(self.project,[earlier],'product')
        self.assertEqual(self.project.events.first().external_id,'event-1')
        changed={**first,'name':'changed'}
        with self.assertRaises(ValueError):ingest(self.project,[self.event('new'),changed],'product')
        self.assertEqual(self.project.events.count(),2)
    def test_schema_rejects_sensitive_unknown_and_invalid_numeric(self):
        for details in [{'prompt':'private'},{'api_key':'secret'},{'duration_ms':float('nan')},{'input_tokens':True}]:
            with self.assertRaises(ValueError):validate_event(self.event(**details))
        with self.assertRaises(ValueError):validate_event({**self.event(),'schema_version':2})
        with self.assertRaises(ValueError):ingest(self.project,[self.event()],'codex')
    def test_api_requires_bearer_and_respects_revocation(self):
        client=Client(enforce_csrf_checks=True)
        url=reverse('connector_api');client.force_login(self.user)
        self.assertEqual(client.post(url,{'action':'search','question':'site'},content_type='application/json').status_code,401)
        connector=Connector.objects.create(project=self.project,owner=self.user,name='test',channel='product',token_hash=hashlib.sha256(b'test-token').hexdigest())
        self.assertEqual(client.post(url,{'action':'events','events':[self.event()]},content_type='application/json',HTTP_AUTHORIZATION='Bearer test-token').status_code,200)
        connector.active=False;connector.save()
        self.assertEqual(client.post(url,{},content_type='application/json',HTTP_AUTHORIZATION='Bearer test-token').status_code,401)

    def test_review_links_and_revoke_use_project_permissions(self):
        queue_inventory(self.project);process_one()
        connector=Connector.objects.create(project=self.project,owner=self.user,name='test',channel='codex',token_hash=hashlib.sha256(b'test-token').hexdigest())
        response=self.client.post(reverse('connector_api'),{'action':'prepare_task','executor':'inventory-refresh-v1'},content_type='application/json',HTTP_AUTHORIZATION='Bearer test-token')
        self.assertTrue(response.json()['review_url'].startswith('http://testserver/'))
        url=reverse('revoke_connector',args=[self.project.pk,connector.pk])
        self.client.force_login(self.other);self.assertEqual(self.client.post(url).status_code,404)
        self.client.force_login(self.user);self.assertEqual(self.client.post(url).status_code,302)
        connector.refresh_from_db();self.assertFalse(connector.active)
    def test_no_parallel_sum_or_missing_zero(self):
        report=bottlenecks([self.event('1',duration_ms=100),self.event('2',duration_ms=300),self.event('3')])
        self.assertEqual(report[0]['median_ms'],200);self.assertEqual(report[0]['duration_samples'],2);self.assertIsNone(report[0]['median_wait_ms'])
    def test_refresh_plan_separate_execution_hash_and_idempotency(self):
        queue_inventory(self.project);process_one()
        plan=prepare_refresh(self.user,self.project);self.assertIsNone(plan.job_id)
        with self.assertRaises(ValueError):execute_refresh(self.user,plan,'wrong')
        job=execute_refresh(self.user,plan,plan.payload['hash']);self.assertEqual(execute_refresh(self.user,plan,plan.payload['hash']).pk,job.pk)
        process_one();plan.refresh_from_db();self.assertEqual(task_data(plan)['status'],'done')
        other=prepare_refresh(self.user,self.project);(self.folder/'AGENTS.md').write_text('# changed',encoding='utf8');queue_inventory(self.project);process_one()
        with self.assertRaises(ValueError):execute_refresh(self.user,other,other.payload['hash'])
    def test_observation_failure_does_not_raise_from_emit_or_drop_silently(self):
        class Offline:
            def call(self,*args,**kwargs):raise EnlaceUnavailable()
        buffer=EventBuffer(Offline(),capacity=1);self.assertTrue(buffer.emit(self.event()));self.assertFalse(buffer.emit(self.event('2')))
        self.assertEqual(buffer.dropped,1);self.assertFalse(buffer.flush());self.assertEqual(len(buffer.events),1)
