from django.db import transaction
from agentic_core.events import validate_event
from .models import ExecutionEvent

def ingest(project,events,channel):
    if not project.active:raise ValueError('Acompanhamento desativado.')
    if not isinstance(events,list) or not 1<=len(events)<=100:raise ValueError('Envie de um a cem eventos.')
    validated=[validate_event(event) for event in events]
    if any(event['channel']!=channel for event in validated):raise ValueError('Canal divergente do conector.')
    created=0
    with transaction.atomic():
        for event in validated:
            values={key:event[key] for key in ['event_type','name','occurred_at','details']}
            existing,is_new=ExecutionEvent.objects.get_or_create(project=project,channel=channel,external_id=event['external_id'],defaults=values)
            if not is_new and any(getattr(existing,key)!=value for key,value in values.items()):raise ValueError('Evento reenviado com conteúdo diferente; use outro ID.')
            created+=is_new
    return {'accepted':len(events),'created':created,'duplicates':len(events)-created}
