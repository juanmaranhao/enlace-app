from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from agentic_core.assessment import prepare,compose
from .models import Assessment,AssessmentPart
from .providers import evaluate,ProviderFailure
from hashlib import sha256
from agentic_core.paths import authorized_root,read_source
from agentic_core.inventory import redact
from core.access import project_for
from django.http import Http404

def sources_current(run):
    try:
        root=authorized_root(run.project.root,settings.ENLACE_ALLOWED_ROOTS)
        return all(sha256(redact(read_source(root,part['path'])).encode()).hexdigest()==part['request']['state']['source']['digest'] for part in run.plan['parts'])
    except (OSError,ValueError,UnicodeError):return False

def prepare_assessment(user,project,goal,criteria,source_ids):
    snapshot=project.latest
    if not snapshot:raise ValueError('Atualize o inventário antes de avaliar.')
    plan=prepare(snapshot.graph,goal,criteria,source_ids,settings.JEV_MODEL)
    with transaction.atomic():
        run=Assessment.objects.create(owner=user,project=project,snapshot=snapshot,plan=plan)
        AssessmentPart.objects.bulk_create([AssessmentPart(assessment=run,index=i) for i in range(plan['calls'])])
    return run

def authorize(run,user,plan_hash):
    if not (user.is_superuser or run.project.owner_id==user.pk):raise ValueError('Somente o responsável pode autorizar envio ao provedor.')
    if plan_hash!=run.plan['hash']:raise ValueError('Plano divergente.')
    if not settings.JEV_IA:raise ValueError('Configure JEV_IA no .env antes de enviar.')
    if not sources_current(run):raise ValueError('As fontes mudaram desde o plano. Atualize o inventário e prepare outra avaliação.')
    latest=run.project.latest
    if not run.project.active or not latest or latest.pk!=run.snapshot_id or settings.JEV_MODEL!=run.plan['model']:raise ValueError('O projeto, snapshot ou modelo mudou. Prepare uma nova análise.')
    Assessment.objects.filter(pk=run.pk,status='prepared').update(status='queued',updated_at=timezone.now())

def process_assessment():
    stale=Assessment.objects.filter(status='running',updated_at__lt=timezone.now()-timedelta(minutes=10))
    stale.update(status='uncertain',message='Worker interrompido. Confira consumo antes de preparar outra análise.')
    run=Assessment.objects.filter(status='queued').order_by('created_at').first()
    if not run:return False
    if not Assessment.objects.filter(pk=run.pk,status='queued').update(status='running',updated_at=timezone.now()):return False
    status='done';message='Avaliação registrada. Resultados são aconselhamento sobre as fontes selecionadas.'
    try:
        latest=run.project.latest
        if not latest or latest.pk!=run.snapshot_id or not run.project.active:raise ProviderFailure('Snapshot ou acompanhamento mudou antes do envio.')
        if not sources_current(run):raise ProviderFailure('Fontes mudaram antes do envio. Atualize o inventário.')
        for part in run.parts.order_by('index'):
            run.refresh_from_db()
            if run.cancel_requested:status='cancelled';message='Cancelada entre partes. Resultados já recebidos foram preservados.';break
            if not run.owner.is_active or not run.owner.is_staff:raise ProviderFailure('Acesso revogado antes do envio.')
            current_project=project_for(run.owner,run.project_id,edit=True)
            if not current_project.active or current_project.latest.pk!=run.snapshot_id or settings.JEV_MODEL!=run.plan['model'] or not sources_current(run):raise ProviderFailure('Projeto, fontes ou modelo mudaram antes da parte. Prepare outra análise.')
            if part.status!='pending':raise ProviderFailure('Parte já enviada. Reenvio automático bloqueado.',uncertain=True)
            part.status='sent';part.save(update_fields=['status'])
            result=evaluate(run.plan['parts'][part.index]['request'])
            part.result=result;part.status='done';part.save()
            if result['model']!=run.plan['model']:raise ProviderFailure('Modelo recebido diverge do plano. Resposta preservada para revisão.',uncertain=True)
            run.updated_at=timezone.now();run.save(update_fields=['updated_at'])
    except Http404:status='failed';message='Permissão revogada antes do envio.'
    except ProviderFailure as exc:status='uncertain' if exc.uncertain else 'failed';message=str(exc)
    except Exception:
        status='uncertain';message='Falha interna após início. Confira consumo antes de repetir.'
        raise
    finally:
        results=[p.result or None for p in run.parts.order_by('index')]
        Assessment.objects.filter(pk=run.pk).update(status=status,message=message,results=results,summary=compose(run.plan,results),updated_at=timezone.now())
    return True
