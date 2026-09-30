from datetime import timedelta
import json
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.http import Http404
from core.access import project_for
from apps.projetos.models import Project
from .models import Conversation,ChatTurn
from .services import catalog,selected_context
from .providers import converse,ProviderFailure

def permitted(user,conversation):
    if conversation.owner_id!=user.pk:raise Http404
    if conversation.project_id:
        if not project_for(user,conversation.project_id).active:raise Http404
    referenced={r['project_id'] for turn in conversation.turns.all() for r in turn.context.get('results',[])}
    if referenced-set(map(str,Project.objects.accessible(user).filter(active=True).values_list('pk',flat=True))):raise Http404
    return conversation

def send_message(user,question,project_id,conversation_id,request_id,mode='local',selection=None):
    if mode not in {'local','ai'} or not isinstance(question,str) or not 1<=len(question.strip())<=500:raise ValueError('Pergunta ou modo inválido.')
    if mode=='ai' and not settings.TEXT_CONFIGURED:raise ValueError('Configure OPENAI_API_KEY e OPENAI_TEXT_MODEL para conversar com IA.')
    if conversation_id:
        conversation=Conversation.objects.filter(pk=conversation_id,owner=user).first()
        if not conversation:
            if Conversation.objects.filter(pk=conversation_id).exists():raise Http404
            project=project_for(user,project_id) if project_id else None
            if project and not project.active:raise Http404
            conversation=Conversation.objects.create(id=conversation_id,owner=user,project=project)
        permitted(user,conversation)
        if str(conversation.project_id or '')!=str(project_id or ''):raise ValueError('Escopo mudou; inicie outra conversa.')
    else:
        project=project_for(user,project_id) if project_id else None
        if project and not project.active:raise Http404
        conversation=Conversation.objects.create(owner=user,project=project)
    existing=conversation.turns.filter(request_id=request_id).first()
    if existing:
        if existing.question!=question or existing.mode!=mode or existing.context.get('selection')!=selection:raise ValueError('Reenvio divergente. Gere uma nova mensagem.')
        return existing
    if conversation.turns.filter(status__in=['queued','running']).exists():raise ValueError('Aguarde a mensagem em processamento antes de enviar outra.')
    results=catalog(user,question,project_id)
    selected=selected_context(user,project_id,selection) if selection else None
    if selected:results=[selected]+[r for r in results if (r['project_id'],r['id'],r['snapshot_id'])!=(selected['project_id'],selected['id'],selected['snapshot_id'])][:7]
    prior=list(conversation.turns.filter(status='done').order_by('-created_at')[:6]);prior.reverse()
    retrieval_question=question
    if not results and prior:
        retrieval_question=prior[-1].question+' '+question;results=catalog(user,retrieval_question,project_id)
    local_message='Estas referências podem ajudar. Abra o mapa ou a fonte para conferir o caminho.' if results else 'Não encontrei fontes suficientes para apontar um caminho. Especifique a tarefa ou atualize o inventário.'
    context={'results':results,'selection':selection,'retrieval_question':retrieval_question,'history':[{'question':t.question,'answer':t.answer.get('message','')} for t in prior],'history_partial':conversation.turns.count()>6}
    # IA recebe apenas excertos já exibidos, IDs de fonte e histórico desta conversa.
    answer={'message':local_message,'results':results,'mode':'local_catalog'}
    return ChatTurn.objects.create(conversation=conversation,request_id=request_id,question=question,mode=mode,
                                   status='queued' if mode=='ai' else 'done',context=context,answer=answer)

def turn_data(user,turn):
    permitted(user,turn.conversation)
    return {'conversation_id':str(turn.conversation_id),'turn_id':str(turn.pk),'status':turn.status,'question':turn.question,**turn.answer,'error':turn.message if turn.status in {'failed','uncertain'} else None}

def process_chat():
    ChatTurn.objects.filter(status='running',updated_at__lt=timezone.now()-timedelta(minutes=10)).update(status='uncertain',message='Worker interrompido; confira consumo antes de reenviar.')
    turn=ChatTurn.objects.select_related('conversation__owner').filter(mode='ai',status='queued').order_by('created_at').first()
    if not turn:return False
    if not ChatTurn.objects.filter(pk=turn.pk,status='queued').update(status='running',updated_at=timezone.now()):return False
    try:
        if not turn.conversation.owner.is_active or not turn.conversation.owner.is_staff:raise ProviderFailure('Acesso revogado antes do envio.')
        permitted(turn.conversation.owner,turn.conversation)
        result=converse(turn.question,turn.context)
        turn.answer={**turn.answer,**result,'mode':'ai_advisory'};turn.status='done'
    except Http404:turn.status='failed';turn.message='Escopo indisponível antes do envio.'
    except ProviderFailure as exc:turn.status='uncertain' if exc.uncertain else 'failed';turn.message=str(exc)
    except Exception:turn.status='uncertain';turn.message='Falha após início do envio. Consumo incerto.'
    turn.save();return True
