"""Contrato portátil v1 de eventos. Não aceita prompts, credenciais ou anexos."""
import math
import re
from datetime import datetime

TYPES={'source_read','self_report','tool_run','verified_result','provider_started','provider_finished','provider_failed'}
DETAILS={'trace_id','parent_id','node_id','snapshot_digest','duration_ms','wait_ms','attempt','result','input_tokens','output_tokens','usage_uncertain','evidence_ref'}
NUMBERS={'duration_ms','wait_ms','attempt','input_tokens','output_tokens'}

def validate_event(event):
    if not isinstance(event,dict) or set(event)-{'schema_version','external_id','channel','event_type','name','occurred_at','details'}:raise ValueError('Evento fora do schema v1.')
    if type(event.get('schema_version')) is not int or event['schema_version']!=1:raise ValueError('Versão de evento incompatível.')
    if event.get('channel') not in {'codex','product'} or event.get('event_type') not in TYPES:raise ValueError('Canal ou tipo inválido.')
    for key,limit in [('external_id',160),('name',160)]:
        if not isinstance(event.get(key),str) or not 1<=len(event[key])<=limit or any(c in event[key] for c in '\r\n\x00'):raise ValueError('Identificação de evento inválida.')
    moment=datetime.fromisoformat(event.get('occurred_at','').replace('Z','+00:00'))
    if not moment.tzinfo:raise ValueError('Informe horário com fuso.')
    details=event.get('details',{})
    if not isinstance(details,dict) or set(details)-DETAILS:raise ValueError('Metadados não autorizados; conteúdo de pedidos fica fora dos eventos.')
    for key,value in details.items():
        if key in NUMBERS:
            if type(value) not in {int,float} or not math.isfinite(value) or value<0 or value>10**12:raise ValueError('Métrica inválida.')
        elif key=='usage_uncertain':
            if type(value) is not bool:raise ValueError('Consumo incerto deve ser booleano.')
        elif not isinstance(value,str) or len(value)>200 or not re.fullmatch(r'[\w./: -]*',value):raise ValueError('Referência incompatível. Use IDs, sem conteúdo privado.')
    return {**event,'details':details,'occurred_at':moment}

def bottlenecks(events):
    """Amostras por etapa, sem somar paralelismo ou inferir caminho crítico."""
    groups={}
    for event in events:
        if event['channel']!='product' or event['event_type'] not in {'provider_finished','provider_failed'}:continue
        values=event['details'];name=event['name'];group=groups.setdefault(name,{'name':name,'durations':[],'waits':[],'failures':0,'samples':0,'uncertain':0})
        group['samples']+=1;group['failures']+=event['event_type']=='provider_failed';group['uncertain']+=bool(values.get('usage_uncertain'))
        if 'duration_ms' in values:group['durations'].append(values['duration_ms'])
        if 'wait_ms' in values:group['waits'].append(values['wait_ms'])
    rows=[]
    for group in groups.values():
        def median(values):
            values=sorted(values);n=len(values);return (values[(n-1)//2]+values[n//2])/2 if n else None
        rows.append({**{key:value for key,value in group.items() if key not in {'durations','waits'}},'median_ms':median(group['durations']),'median_wait_ms':median(group['waits']),'duration_samples':len(group['durations'])})
    return sorted(rows,key=lambda r:(r['median_wait_ms'] is None,-(r['median_wait_ms'] or 0),r['name']))
