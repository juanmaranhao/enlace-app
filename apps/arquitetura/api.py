import hashlib
import json
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.http import Http404
from core.access import project_for
from apps.assistente.services import catalog
from .models import Connector
from .events import ingest
from .services import map_data,snapshot_for
from apps.assistente.assessments import prepare_assessment
from apps.assistente.models import Assessment,Conversation
from apps.assistente.conversations import permitted,turn_data
from apps.projetos.actions import prepare_refresh,task_data

@method_decorator(csrf_exempt,name='dispatch')
class ConnectorAPI(View):
    """Bearer obrigatório; sessão/cookie não concede acesso a este endpoint."""
    def post(self,request):
        auth=request.headers.get('Authorization','')
        if not auth.startswith('Bearer ') or len(auth)>300:return JsonResponse({'error':'Conector não autenticado.'},status=401)
        hashed=hashlib.sha256(auth[7:].encode()).hexdigest()
        connector=Connector.objects.select_related('project','owner').filter(token_hash=hashed,active=True).first()
        if not connector or not connector.owner.is_active or not connector.owner.is_staff:return JsonResponse({'error':'Conector não autenticado.'},status=401)
        project=project_for(connector.owner,connector.project_id)
        if not project.active:return JsonResponse({'error':'Acompanhamento desativado.'},status=403)
        try:
            payload=json.loads(request.body);action=payload.get('action')
            if action=='events':result=ingest(project,payload.get('events'),connector.channel)
            elif action=='search':
                question=payload.get('question','')
                if not isinstance(question,str) or not 1<=len(question)<=500:raise ValueError('Pergunta inválida.')
                result={'results':catalog(connector.owner,question,project.pk)}
            elif action=='flow':
                snapshot=snapshot_for(project,payload.get('snapshot_id'));result=map_data(project,snapshot,payload.get('focus'))
            elif action=='prepare_assessment':
                project_for(connector.owner,project.pk,edit=True)
                run=prepare_assessment(connector.owner,project,payload.get('goal'),payload.get('criteria',[]),payload.get('source_ids',[]))
                result={'id':str(run.pk),'status':run.status,'review_url':reverse('assessment',kwargs={'pk':project.pk,'run_id':run.pk})}
            elif action=='analysis':
                run=Assessment.objects.filter(pk=payload.get('id'),project=project).first()
                if not run:raise Http404
                result={'id':str(run.pk),'status':run.status,'summary':run.summary,'message':run.message,'snapshot_id':str(run.snapshot_id)}
            elif action=='prepare_task':
                project_for(connector.owner,project.pk,edit=True)
                if payload.get('executor')!='inventory-refresh-v1':raise ValueError('Executor ausente. Continue a produção no Codex com as fontes encontradas.')
                plan=prepare_refresh(connector.owner,project)
                result={'id':str(plan.pk),'status':plan.status,'plan':plan.payload,'review_url':reverse('action_plan',kwargs={'pk':project.pk,'plan_id':plan.pk})}
            elif action=='task':
                plan=project.action_plans.filter(pk=payload.get('id')).first()
                if not plan:raise Http404
                result=task_data(plan)
            elif action=='conversation':
                conversation=Conversation.objects.filter(pk=payload.get('id'),owner=connector.owner,project=project).first()
                if not conversation:raise Http404
                permitted(connector.owner,conversation)
                result={'id':str(conversation.pk),'turns':[turn_data(connector.owner,turn) for turn in conversation.turns.all()]}
            else:raise ValueError('Ação não suportada.')
            Connector.objects.filter(pk=connector.pk).update(last_seen_at=timezone.now())
            def links(value):
                if isinstance(value,list):return [links(item) for item in value]
                if isinstance(value,dict):return {key:request.build_absolute_uri(item) if key.endswith('_url') and isinstance(item,str) and item.startswith('/') else links(item) for key,item in value.items()}
                return value
            return JsonResponse(links(result))
        except (ValueError,TypeError,AttributeError,ValidationError):return JsonResponse({'error':'Entrada inválida ou evento incompatível.'},status=400)
