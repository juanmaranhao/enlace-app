from pathlib import Path
from urllib.parse import quote
import hashlib
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model,login
from django.contrib.auth.forms import UserCreationForm
from django.core import signing
from django.db import transaction
from django.http import Http404,JsonResponse
from django.urls import reverse
from django.shortcuts import redirect
from django.views.generic import ListView,TemplateView,FormView,View
from core.access import StaffRequiredMixin,project_for
from agentic_core.paths import authorized_root,ROOT_DOCUMENTS,EXCLUDED
from .forms import ProjectForm
from .models import Project
from .services import register,queue_inventory
from .models import ActionPlan
from .actions import execute_refresh,task_data

def fingerprint(root):
    entries=[]
    for p in sorted(Path(root).iterdir()):
        if p.name.lower() in ROOT_DOCUMENTS and p.is_file():
            stat=p.stat(); entries.append(f'{p.name}:{stat.st_size}:{stat.st_mtime_ns}')
    return hashlib.sha256('\n'.join(entries).encode()).hexdigest()

class PortfolioView(StaffRequiredMixin,ListView):
    template_name='projetos/portfolio.html'
    context_object_name='projects'
    def get_queryset(self):
        projects=Project.objects.accessible(self.request.user).filter(active=True)
        query=self.request.GET.get('q','')[:120]
        return projects.filter(name__icontains=query) if query else projects
    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        rows=[]
        for project in context['projects']:
            snap=project.latest
            rows.append({'project':project,'snapshot':snap,'count':len(snap.graph['nodes']) if snap else 0,
                         'job':project.jobs.first(),'events':project.events.count(),'has_connector':project.connectors.filter(active=True).exists()})
        context.update(rows=rows,screen='projects',query=self.request.GET.get('q',''))
        return context

class RegisterView(StaffRequiredMixin,FormView):
    template_name='projetos/register.html'
    form_class=ProjectForm
    def form_valid(self,form):
        try:
            root=authorized_root(form.cleaned_data['root'],settings.ENLACE_ALLOWED_ROOTS)
            plan={'root':str(root),'name':form.cleaned_data['name'],'owner':self.request.user.pk,'fingerprint':fingerprint(root)}
            token=form.cleaned_data['confirmation']
            if token:
                saved=signing.loads(token,salt='enlace-registration',max_age=900)
                if saved!=plan:raise ValueError('A pasta ou o plano mudou. Revise a detecção novamente.')
                project,created=register(self.request.user,form.cleaned_data['name'],str(root))
                project_for(self.request.user,project.pk,edit=True)
                if not project.active:
                    project.active=True;project.save(update_fields=['active'])
                queue_inventory(project)
                messages.success(self.request,'Projeto vinculado. A leitura está na fila do worker.' if created else 'Projeto já vinculado; atualização solicitada.')
                return redirect('dashboard',pk=project.pk)
            form=ProjectForm(initial={**form.cleaned_data,'root':str(root),'confirmation':signing.dumps(plan,salt='enlace-registration')})
            preview={'root':root,'name':plan['name'] or root.name,'git':(root/'.git').exists(),
                     'instructions':(root/'AGENTS.md').is_file(),'skills':(root/'.agents'/'skills').is_dir()}
            return self.render_to_response(self.get_context_data(form=form,preview=preview))
        except (OSError,ValueError,signing.BadSignature) as exc:
            form.add_error(None,str(exc) if isinstance(exc,ValueError) else 'Não foi possível validar a pasta ou a confirmação. Revise e tente novamente.')
            return self.form_invalid(form)
    def get_context_data(self,**kwargs):
        return {**super().get_context_data(**kwargs),'roots':settings.ENLACE_ALLOWED_ROOTS,'screen':'projects'}

class DashboardView(StaffRequiredMixin,TemplateView):
    template_name='projetos/dashboard.html'
    def get_context_data(self,**kwargs):
        project=project_for(self.request.user,kwargs['pk'])
        snap=project.latest
        graph=snap.graph if snap else {}
        return {**super().get_context_data(**kwargs),'project':project,'snapshot':snap,'graph':graph,
                'flows':[n for n in graph.get('nodes',[]) if n['kind']=='flow'],'jobs':project.jobs.all()[:5],
                'events':project.events.all()[:10],'event_count':project.events.count(),'screen':'dashboard',
                'has_connector':project.connectors.filter(active=True).exists(),
                'can_edit':self.request.user.is_superuser or project.owner_id==self.request.user.pk}

class UpdateView(StaffRequiredMixin,View):
    def post(self,request,pk):
        project=project_for(request.user,pk,edit=True)
        try:
            queue_inventory(project)
            messages.success(request,'Atualização solicitada. A leitura será processada pelo worker.')
        except ValueError as exc:messages.error(request,str(exc))
        return redirect('dashboard',pk=pk)

class CancelView(StaffRequiredMixin,View):
    def post(self,request,pk,job_id):
        project=project_for(request.user,pk,edit=True)
        job=project.jobs.filter(pk=job_id,status__in=['queued','running']).first()
        if job:
            job.cancel_requested=True
            if job.status=='queued':job.status='cancelled';job.message='Cancelada antes de iniciar.'
            job.save()
            messages.success(request,'Cancelamento solicitado. O histórico será preservado.')
        return redirect('dashboard',pk=pk)

class DisconnectView(StaffRequiredMixin,View):
    def post(self,request,pk):
        project=project_for(request.user,pk,edit=True)
        project.active=False;project.save(update_fields=['active'])
        project.jobs.filter(status__in=['queued','running']).update(cancel_requested=True)
        messages.success(request,'Acompanhamento desativado. Pasta e histórico preservados.')
        return redirect('carteira')

class DirectoryView(StaffRequiredMixin,View):
    def get(self,request):
        path=request.GET.get('path')
        try:
            root=authorized_root(path,settings.ENLACE_ALLOWED_ROOTS) if path else None
            paths=settings.ENLACE_ALLOWED_ROOTS if root is None else [p for p in root.iterdir() if p.is_dir() and not p.is_symlink() and not p.is_junction() and p.name.lower() not in EXCLUDED and not p.name.startswith('.')]
            directories=[{'name':p.name,'path':str(p),'browse_url':reverse('directories')+'?path='+quote(str(p))} for p in sorted(paths,key=lambda p:p.name.lower())[:100]]
        except (OSError,ValueError):return JsonResponse({'error':'Pasta indisponível ou fora das raízes autorizadas.'},status=400)
        return JsonResponse({'directories':directories,'path':str(root) if root else None})

class JobStatusView(StaffRequiredMixin,View):
    def get(self,request,pk):
        project=project_for(request.user,pk)
        job=project.jobs.first()
        snapshot=project.latest
        return JsonResponse({'status':job.status if job else 'none','source_count':job.source_count if job else 0,'message':job.message if job else '',
                             'snapshot_id':str(snapshot.pk) if snapshot else '', 'checked_at':project.checked_at.isoformat() if project.checked_at else None})

class SetupView(FormView):
    template_name='setup.html'
    form_class=UserCreationForm
    def dispatch(self,request,*args,**kwargs):
        if not settings.DEBUG or request.META.get('REMOTE_ADDR') not in {'127.0.0.1','::1'} or get_user_model().objects.exists():raise Http404
        return super().dispatch(request,*args,**kwargs)
    def form_valid(self,form):
        with transaction.atomic():
            if get_user_model().objects.exists():raise Http404
            user=form.save(commit=False);user.is_staff=True;user.is_superuser=True;user.save()
        login(self.request,user)
        return redirect('carteira')

class ActionPlanView(StaffRequiredMixin,TemplateView):
    template_name='projetos/action_plan.html'
    def get_context_data(self,**kwargs):
        project=project_for(self.request.user,kwargs['pk'])
        plan=project.action_plans.filter(pk=kwargs['plan_id']).first()
        if not plan:raise Http404
        return {**super().get_context_data(**kwargs),'project':project,'plan':plan,'receipt':task_data(plan),'screen':'dashboard','snapshot':project.latest,'can_edit':self.request.user.is_superuser or project.owner_id==self.request.user.pk}

class ExecutePlanView(StaffRequiredMixin,View):
    def post(self,request,pk,plan_id):
        project=project_for(request.user,pk,edit=True)
        plan=project.action_plans.filter(pk=plan_id).first()
        if not plan:raise Http404
        try:execute_refresh(request.user,plan,request.POST.get('plan_hash',''));messages.success(request,'Ação despachada para o worker.')
        except ValueError as exc:messages.error(request,str(exc))
        return redirect('action_plan',pk=pk,plan_id=plan_id)
