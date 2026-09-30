from django.db import transaction
from django.conf import settings
from agentic_core.paths import authorized_root
from agentic_core.assessment import digest
from .models import ActionPlan
from .services import queue_inventory

def prepare_refresh(user,project):
    root=authorized_root(project.root,settings.ENLACE_ALLOWED_ROOTS)
    snapshot=project.latest
    plan={'executor':'inventory-refresh-v1','project_id':str(project.pk),'root':str(root),'snapshot_id':str(snapshot.pk) if snapshot else None,
          'effects':['Ler fontes de governança autorizadas','Registrar snapshot no banco do Enlace'],'writes_observed_project':False,'estimated_cost':0}
    return ActionPlan.objects.create(project=project,owner=user,payload={**plan,'hash':digest(plan)})

def execute_refresh(user,plan,plan_hash):
    if not (user.is_superuser or plan.project.owner_id==user.pk):raise ValueError('Acesso de escrita não autorizado.')
    if plan_hash!=plan.payload['hash']:raise ValueError('Plano divergente.')
    with transaction.atomic():
        locked=ActionPlan.objects.select_for_update().select_related('project','job').get(pk=plan.pk)
        if locked.job_id:return locked.job
        project=locked.project;root=authorized_root(project.root,settings.ENLACE_ALLOWED_ROOTS);snapshot=project.latest
        if str(root)!=locked.payload['root'] or str(snapshot.pk if snapshot else '')!=str(locked.payload['snapshot_id'] or '') or not project.active:raise ValueError('Alvo ou versão mudou. Prepare um novo plano.')
        job=queue_inventory(project);locked.job=job;locked.status='dispatched';locked.save()
        return job

def task_data(plan):
    job=plan.job
    return {'id':str(plan.pk),'status':job.status if job else plan.status,'executor':plan.payload['executor'],
            'job_id':str(job.pk) if job else None,'message':job.message if job else 'Plano preparado; ainda não executado.',
            'sources':job.source_count if job else None,'finished_at':job.finished_at.isoformat() if job and job.finished_at else None}
