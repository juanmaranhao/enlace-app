from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from agentic_core.inventory import collect
from agentic_core.paths import read_source,authorized_root
from agentic_core.search import search
from .models import Project
from .services import register,queue_inventory,process_one

class ProjectWorkflowTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.settings=override_settings(ENLACE_ALLOWED_ROOTS=[self.root]);self.settings.enable();self.addCleanup(self.settings.disable)
        self.folder=self.root/'Example';self.folder.mkdir()
        (self.folder/'AGENTS.md').write_text('# Instruções\nUse criar-site.\n<script>alert(1)</script>',encoding='utf8')
        skill=self.folder/'.agents'/'skills'/'criar-site';skill.mkdir(parents=True)
        (skill/'SKILL.md').write_text('# Site\nCria site usando frontend e landing page.',encoding='utf8')
        (self.folder/'FLUXOS.md').write_text('# Fluxos\n## Criar um site\nUse criar-site.',encoding='utf8')
        (self.folder/'.env').write_text('SECRET=must-not-index',encoding='utf8')
        self.user=get_user_model().objects.create_user('owner',password='test-password',is_staff=True)
        self.other=get_user_model().objects.create_user('other',is_staff=True)
        self.project,_=register(self.user,'Example',self.folder)
        self.client.force_login(self.user)

    def test_queue_snapshot_and_normalized_no_change(self):
        first=queue_inventory(self.project);self.assertEqual(queue_inventory(self.project).pk,first.pk)
        self.assertTrue(process_one());self.assertEqual(self.project.snapshots.count(),1)
        file=self.folder/'AGENTS.md';file.write_bytes(file.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
        queue_inventory(self.project);process_one();self.assertEqual(self.project.snapshots.count(),1)
        file.write_text('# Changed',encoding='utf8');queue_inventory(self.project);process_one();self.assertEqual(self.project.snapshots.count(),2)

    def test_sensitive_and_escape_sources_rejected(self):
        for path in ['.env','../AGENTS.md','.git/config','db.sqlite3','docs/contratos/.env.md']:
            with self.assertRaises(ValueError):read_source(self.folder,path)
        graph=collect(self.folder);self.assertNotIn('must-not-index',str(graph))
        with self.assertRaises(ValueError):authorized_root(self.root.parent,[self.root])
        huge=self.folder/'README.md';huge.write_text('x'*262145,encoding='utf8')
        self.assertTrue(collect(self.folder)['coverage']['partial'])

    def test_cancel_preserves_snapshot(self):
        queue_inventory(self.project);process_one();snapshot=self.project.latest
        job=queue_inventory(self.project);job.cancel_requested=True;job.save();process_one();job.refresh_from_db()
        self.assertEqual(job.status,'cancelled');self.assertEqual(self.project.latest.pk,snapshot.pk)

    def test_permissions_and_escaped_source(self):
        queue_inventory(self.project);process_one();snap=self.project.latest;source=snap.graph['sources'][0]
        url=reverse('source',args=[self.project.pk,snap.pk,source['id']])
        self.assertContains(self.client.get(url),'&lt;script&gt;')
        self.client.force_login(self.other)
        for name,args in [('dashboard',[self.project.pk]),('map',[self.project.pk]),('source',[self.project.pk,snap.pk,source['id']]),('inspect_node',[self.project.pk,snap.pk,source['id']])]:self.assertEqual(self.client.get(reverse(name,args=args)).status_code,404)
        self.project.readers.add(self.other)
        self.assertEqual(self.client.get(reverse('dashboard',args=[self.project.pk])).status_code,200)
        self.assertEqual(self.client.post(reverse('update_inventory',args=[self.project.pk])).status_code,404)

    def test_registration_confirmation_and_duplicate(self):
        new=self.root/'New';new.mkdir();(new/'AGENTS.md').write_text('# New',encoding='utf8')
        url=reverse('register');response=self.client.post(url,{'root':str(new),'name':'New'})
        self.assertEqual(Project.objects.count(),1)
        token=response.context['form']['confirmation'].value()
        denied=self.client.post(url,{'root':str(new),'name':'Changed','confirmation':token})
        self.assertEqual(denied.status_code,200);self.assertEqual(Project.objects.count(),1)
        self.assertEqual(self.client.post(url,{'root':str(new),'name':'New','confirmation':token}).status_code,302)
        self.assertEqual(Project.objects.count(),2)
        again,created=register(self.user,'alias',new/'..'/'New');self.assertFalse(created)

    def test_real_catalog_and_abstention(self):
        queue_inventory(self.project);process_one()
        results=self.client.post(reverse('catalog'),{'question':'Como criar um site?'},content_type='application/json').json()['results']
        self.assertTrue(results);self.assertTrue(all(r['project_id']==str(self.project.pk) for r in results))
        self.assertEqual(search(self.project.latest.graph,'helicóptero submarino'),[])
        with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')):
            for name,args in [('carteira',[]),('dashboard',[self.project.pk]),('map',[self.project.pk]),('analysis',[self.project.pk])]:
                self.assertEqual(self.client.get(reverse(name,args=args)).status_code,200)

    def test_csrf_required(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        self.assertEqual(client.post(reverse('update_inventory',args=[self.project.pk])).status_code,403)

    def test_cross_project_snapshot_and_invalid_id(self):
        queue_inventory(self.project);process_one();snap=self.project.latest
        folder=self.root/'Another';folder.mkdir();project,_=register(self.user,'Another',folder)
        self.assertEqual(self.client.get(reverse('map',args=[project.pk]),{'snapshot':str(snap.pk)}).status_code,404)
        self.assertEqual(self.client.get(reverse('map',args=[self.project.pk]),{'snapshot':'invalid'}).status_code,404)

    def test_flow_excerpts_are_specific_and_freshness_changes(self):
        (self.folder/'FLUXOS.md').write_text('# Fluxos\n## Site\nUse criar-site para frontend.\n## Vídeo\nUse criar-site para cenas animadas.',encoding='utf8')
        queue_inventory(self.project);process_one()
        before=self.client.get(reverse('job_status',args=[self.project.pk])).json()['snapshot_id']
        rows=search(self.project.latest.graph,'animadas')
        flow=next(r for r in rows if r['kind']=='flow')
        self.assertEqual(flow['name'],'Vídeo');self.assertNotIn('frontend',flow['excerpt'])
        (self.folder/'FLUXOS.md').write_text('# Fluxos\n## Site\nUse criar-site para frontend atualizado.',encoding='utf8')
        queue_inventory(self.project);process_one()
        self.assertNotEqual(before,self.client.get(reverse('job_status',args=[self.project.pk])).json()['snapshot_id'])
        self.assertEqual(self.client.get(reverse('health')).json(),{'status':'ok'})

    def test_windows_junction_cannot_expose_another_project(self):
        import os,subprocess
        if os.name!='nt':self.skipTest('Contrato de junction Windows')
        outside=self.root/'OtherProject';outside.mkdir()
        (outside/'SKILL.md').write_text('# Private\nMust never be read',encoding='utf8')
        link=self.folder/'.agents'/'skills'/'escape'
        made=subprocess.run(['cmd','/c','mklink','/J',str(link),str(outside)],capture_output=True)
        self.assertEqual(made.returncode,0,'Não foi possível preparar junction para validar isolamento.')
        self.assertTrue(link.is_junction())
        with self.assertRaises(ValueError):read_source(self.folder,'.agents/skills/escape/SKILL.md')
        self.assertFalse(any('escape' in s['path'] for s in collect(self.folder)['sources']))
