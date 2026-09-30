from django.http import Http404
from django.core.exceptions import ValidationError
from django.urls import reverse

def snapshot_for(project,snapshot_id=None):
    try: snapshot=project.snapshots.filter(pk=snapshot_id).first() if snapshot_id else project.latest
    except (ValidationError,ValueError): raise Http404
    if not snapshot:raise Http404('Ainda não há um snapshot para este projeto.')
    return snapshot

def map_data(project,snapshot,focus=None):
    graph=snapshot.graph
    nodes={n['id']:n for n in graph['nodes']}
    flows=sorted([n for n in graph['nodes'] if n['kind']=='flow'],key=lambda n:(not n['path'].lower().endswith('fluxos.md'),n['name']))
    anchor=nodes.get(focus) or (flows[0] if flows else next((n for n in graph['nodes'] if n['path']=='AGENTS.md'),None)) or next(iter(nodes.values()),None)
    visible={anchor['id']} if anchor else set()
    for edge in graph['relations']:
        if anchor and anchor['id'] in (edge['source'],edge['target']):visible.update([edge['source'],edge['target']])
    selected=[nodes[n] for n in visible if n in nodes]
    selected.sort(key=lambda n:(n['id']!=anchor['id'],n['support'],n['kind'],n['name']))
    shown=selected[:40]
    node_ids={n['id'] for n in shown}
    enriched=[]
    for n in shown:
        enriched.append({**n,'support':n['kind'] not in {'flow','skill'},
                         'inspect_url':reverse('inspect_node',kwargs={'pk':project.pk,'snapshot_id':snapshot.pk,'node_id':n['id']}),
                         'source_url':reverse('source',kwargs={'pk':project.pk,'snapshot_id':snapshot.pk,'source_id':n['source_id']})})
    return {'nodes':enriched,'relations':[e for e in graph['relations'] if e['source'] in node_ids and e['target'] in node_ids],
            'anchor':anchor,'total':len(selected),'shown':len(shown),'snapshot_id':str(snapshot.pk)}
