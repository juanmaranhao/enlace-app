from django.urls import reverse
from agentic_core.search import search
from apps.projetos.models import Project
from core.access import project_for
from apps.arquitetura.services import snapshot_for
from django.http import Http404

def reference(project,snapshot,result):
    return {**result,'project':project.name,'project_id':str(project.pk),'snapshot_id':str(snapshot.pk),
            'map_url':reverse('map',kwargs={'pk':project.pk})+f'?snapshot={snapshot.pk}&focus={result["id"]}',
            'source_url':reverse('source',kwargs={'pk':project.pk,'snapshot_id':snapshot.pk,'source_id':result['source_id']})}

def selected_context(user,project_id,selection):
    if not isinstance(selection,dict) or set(selection)!={'id','snapshot_id'}:raise ValueError('Contexto de mapa inválido.')
    project=project_for(user,project_id)
    if not project.active:raise Http404
    snapshot=snapshot_for(project,selection['snapshot_id'])
    node=next((n for n in snapshot.graph['nodes'] if n['id']==selection['id']),None)
    if not node:raise Http404
    source=next(s for s in snapshot.graph['sources'] if s['id']==node['source_id'])
    text=source['text']
    if node['kind']=='flow':text='\n'.join(text.splitlines()[node['line']-1:node['end_line']])
    return reference(project,snapshot,{**node,'excerpt':text[:500],'score':1000,'matched':[]})

def catalog(user,question,project_id=None):
    projects=Project.objects.accessible(user).filter(active=True)
    if project_id:projects=projects.filter(pk=project_id)
    results=[]
    for project in projects:
        snapshot=project.latest
        if not snapshot:continue
        for result in search(snapshot.graph,question):
            results.append(reference(project,snapshot,result))
    return sorted(results,key=lambda n:(-n['score'],n['name']))[:8]
