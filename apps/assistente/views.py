import json
import uuid
from django.http import JsonResponse
from django.views.generic import View
from core.access import StaffRequiredMixin,project_for
from .services import catalog
from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import TemplateView
from django.http import Http404
from django.urls import reverse
from .models import Assessment
from .assessments import prepare_assessment,authorize
from .conversations import send_message,turn_data,permitted
from .models import ChatTurn,Conversation

class CatalogView(StaffRequiredMixin,View):
    def post(self,request):
        try:
            payload=json.loads(request.body)
            question=payload['question']
            if not isinstance(question,str) or not 1<=len(question.strip())<=500:raise ValueError
            project_id=payload.get('project_id')
            if project_id:project_for(request.user,project_id)
        except (ValueError,KeyError,TypeError):return JsonResponse({'error':'Informe uma pergunta com até 500 caracteres.'},status=400)
        results=catalog(request.user,question,project_id)
        return JsonResponse({'mode':'local_catalog','results':results,'message':
                            'Encontrei estas referências nas fontes locais. Presença no catálogo não comprova que uma tarefa foi executada.' if results else
                            'Não encontrei fontes suficientes nos projetos conectados para indicar um caminho. Tente um termo específico ou atualize o inventário.'})

class PrepareAssessmentView(StaffRequiredMixin,View):
    def post(self,request,pk):
        project=project_for(request.user,pk,edit=True)
        try:
            criteria=[c.strip() for c in request.POST.get('criteria','').splitlines() if c.strip()]
            run=prepare_assessment(request.user,project,request.POST.get('goal',''),criteria,request.POST.getlist('sources'))
            return redirect('assessment',pk=pk,run_id=run.pk)
        except ValueError as exc:messages.error(request,str(exc));return redirect('analysis',pk=pk)

def assessment_for(user,pk,run_id,edit=False):
    project=project_for(user,pk,edit=edit)
    run=Assessment.objects.filter(project=project,pk=run_id).first()
    if not run:raise Http404
    return project,run

class AssessmentView(StaffRequiredMixin,TemplateView):
    template_name='assistente/assessment.html'
    def get_context_data(self,**kwargs):
        project,run=assessment_for(self.request.user,kwargs['pk'],kwargs['run_id'])
        return {**super().get_context_data(**kwargs),'project':project,'run':run,'snapshot':run.snapshot,'screen':'analysis','can_edit':self.request.user.is_superuser or project.owner_id==self.request.user.pk}

class AuthorizeAssessmentView(StaffRequiredMixin,View):
    def post(self,request,pk,run_id):
        project,run=assessment_for(request.user,pk,run_id,edit=True)
        try:authorize(run,request.user,request.POST.get('plan_hash',''));messages.success(request,'Envio autorizado. O worker processará a análise.')
        except ValueError as exc:messages.error(request,str(exc))
        return redirect('assessment',pk=pk,run_id=run_id)

class CancelAssessmentView(StaffRequiredMixin,View):
    def post(self,request,pk,run_id):
        project,run=assessment_for(request.user,pk,run_id,edit=True)
        run.cancel_requested=True
        if run.status in {'prepared','queued'}:run.status='cancelled'
        run.save();messages.success(request,'Cancelamento registrado. Uma chamada em andamento pode terminar antes da parada.')
        return redirect('assessment',pk=pk,run_id=run_id)

class ChatMessageView(StaffRequiredMixin,View):
    def post(self,request):
        try:
            payload=json.loads(request.body)
            turn=send_message(request.user,payload['question'],payload.get('project_id'),uuid.UUID(payload['conversation_id']),uuid.UUID(payload['request_id']),payload.get('mode','local'),payload.get('selection'))
            return JsonResponse({**turn_data(request.user,turn),'poll_url':reverse('chat_turn',kwargs={'turn_id':turn.pk})})
        except (ValueError,TypeError,KeyError) as exc:return JsonResponse({'error':str(exc) if isinstance(exc,ValueError) else 'Mensagem inválida.'},status=400)

class ChatTurnView(StaffRequiredMixin,View):
    def get(self,request,turn_id):
        turn=ChatTurn.objects.select_related('conversation').filter(pk=turn_id,conversation__owner=request.user).first()
        if not turn:raise Http404
        return JsonResponse(turn_data(request.user,turn))

class ConversationView(StaffRequiredMixin,View):
    def get(self,request,conversation_id):
        conversation=Conversation.objects.filter(pk=conversation_id,owner=request.user).first()
        if not conversation:raise Http404
        permitted(request.user,conversation)
        return JsonResponse({'id':str(conversation.pk),'turns':[turn_data(request.user,turn) for turn in conversation.turns.all()]})
