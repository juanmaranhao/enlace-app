from hashlib import sha256
from django.http import Http404,JsonResponse
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import TemplateView,View
from core.access import StaffRequiredMixin,project_for
from agentic_core.paths import read_source
from agentic_core.inventory import redact
from agentic_core.events import bottlenecks
from .services import snapshot_for,map_data

class MapView(StaffRequiredMixin,TemplateView):
    template_name='arquitetura/map.html'
    def get_context_data(self,**kwargs):
        project=project_for(self.request.user,kwargs['pk'])
        snapshot=project.latest
        if self.request.GET.get('snapshot'):snapshot=snapshot_for(project,self.request.GET['snapshot'])
        data=map_data(project,snapshot,self.request.GET.get('focus')) if snapshot else None
        graph=snapshot.graph if snapshot else {}
        return {**super().get_context_data(**kwargs),'project':project,'snapshot':snapshot,'map_data':data,
                'flows':sorted([n for n in graph.get('nodes',[]) if n['kind']=='flow'],key=lambda n:(not n['path'].lower().endswith('fluxos.md'),n['name'])),'all_nodes':graph.get('nodes',[]),
                'snapshots':project.snapshots.all()[:20],'screen':'map','view':self.request.GET.get('view','declared'),
                'can_edit':self.request.user.is_superuser or project.owner_id==self.request.user.pk,
                'events':project.events.all()[:100]}

class SourceView(StaffRequiredMixin,TemplateView):
    template_name='arquitetura/source.html'
    def get_context_data(self,**kwargs):
        project=project_for(self.request.user,kwargs['pk'])
        snapshot=snapshot_for(project,kwargs['snapshot_id'])
        source=next((s for s in snapshot.graph['sources'] if s['id']==kwargs['source_id']),None)
        if not source:raise Http404
        try:changed=sha256(redact(read_source(project.root,source['path'])).encode()).hexdigest()!=source['digest']
        except (OSError,ValueError,UnicodeError):changed=True
        focus=self.request.GET.get('focus',source['id'])
        if not any(n['id']==focus for n in snapshot.graph['nodes']):focus=source['id']
        return {**super().get_context_data(**kwargs),'project':project,'snapshot':snapshot,'source':source,'return_focus':focus,'changed':changed,'screen':'map'}

class InspectView(StaffRequiredMixin,View):
    def get(self,request,pk,snapshot_id,node_id):
        project=project_for(request.user,pk)
        snapshot=snapshot_for(project,snapshot_id)
        graph=snapshot.graph
        node=next((n for n in graph['nodes'] if n['id']==node_id),None)
        if not node:raise Http404
        source=next(s for s in graph['sources'] if s['id']==node['source_id'])
        text=source['text']
        if node['kind']=='flow':text='\n'.join(text.splitlines()[node['line']-1:node.get('end_line',len(text.splitlines()))])
        related_ids=set()
        relationships=[]
        for edge in graph['relations']:
            if edge['source']==node_id or edge['target']==node_id:
                relationships.append(edge);related_ids.update([edge['source'],edge['target']])
        related=[n for n in graph['nodes'] if n['id'] in related_ids and n['id']!=node_id]
        return JsonResponse({'node':node,'related':related,'relations':relationships,
                             'source':{'path':source['path'],'digest':source['digest'],'excerpt':text[:6000],
                                       'excerpt_partial':len(text)>6000,
                                       'url':reverse('source',kwargs={'pk':pk,'snapshot_id':snapshot_id,'source_id':source['id']})}})

class AnalysisView(StaffRequiredMixin,TemplateView):
    template_name='arquitetura/analysis.html'
    def get_context_data(self,**kwargs):
        project=project_for(self.request.user,kwargs['pk'])
        snapshot=project.latest
        graph=snapshot.graph if snapshot else {}
        referenced={e['target'] for e in graph.get('relations',[])}
        unlinked=[n for n in graph.get('nodes',[]) if n['kind']=='skill' and n['id'] not in referenced]
        sample=list(project.events.filter(channel='product',event_type__in=['provider_finished','provider_failed']).values('channel','event_type','name','details','occurred_at')[:1000])
        return {**super().get_context_data(**kwargs),'project':project,'snapshot':snapshot,'unlinked':unlinked,'screen':'analysis',
                'bottlenecks':bottlenecks(sample),'event_samples':len(sample),'sample_start':sample[-1]['occurred_at'] if sample else None,
                'connectors':project.connectors.all(),'sample_end':sample[0]['occurred_at'] if sample else None,
                'sources':graph.get('sources',[]),'assessments':project.assessments.all()[:10],
                'goal':self.request.GET.get('goal','')[:500],
                'can_edit':self.request.user.is_superuser or project.owner_id==self.request.user.pk}

class RevokeConnectorView(StaffRequiredMixin,View):
    def post(self,request,pk,connector_id):
        project=project_for(request.user,pk,edit=True)
        connector=project.connectors.filter(pk=connector_id).first()
        if not connector:raise Http404
        connector.active=False
        connector.save(update_fields=['active'])
        messages.success(request,'Conector revogado. Histórico preservado.')
        return redirect('analysis',pk=pk)
