from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import timezone
from agentic_core.paths import authorized_root
from agentic_core.inventory import collect
from apps.arquitetura.models import Snapshot
from .models import Project, InventoryJob

def register(user,name,path):
    root = authorized_root(path,settings.ENLACE_ALLOWED_ROOTS)
    key = str(root).casefold()
    existing = Project.objects.filter(canonical_key=key).first()
    if existing:
        if not Project.objects.accessible(user).filter(pk=existing.pk).exists():
            raise ValueError('Esta pasta já está vinculada por outro administrador.')
        return existing,False
    return Project.objects.create(owner=user,name=name or root.name,root=str(root),canonical_key=key),True

def queue_inventory(project):
    if not project.active: raise ValueError('Ative o acompanhamento antes de atualizar.')
    with transaction.atomic():
        Project.objects.select_for_update().get(pk=project.pk)
        existing = project.jobs.filter(status__in=['queued','running']).first()
        if existing: return existing
        return InventoryJob.objects.create(project=project)

def process_one():
    now = timezone.now()
    stale = InventoryJob.objects.filter(status='running',heartbeat_at__lt=now-timedelta(minutes=10))
    stale.update(status='failed',finished_at=now,message='Worker interrompido. Solicite uma nova leitura.')
    job = InventoryJob.objects.filter(status='queued').order_by('created_at').first()
    if not job: return False
    claimed = InventoryJob.objects.filter(pk=job.pk,status='queued').update(status='running',started_at=now,heartbeat_at=now)
    if not claimed: return False
    job.refresh_from_db()
    try:
        root = authorized_root(job.project.root,settings.ENLACE_ALLOWED_ROOTS)
        def cancelled():
            return InventoryJob.objects.filter(pk=job.pk,cancel_requested=True).exists() or not Project.objects.filter(pk=job.project_id,active=True).exists()
        def progress(count):
            if count % 10 == 0: InventoryJob.objects.filter(pk=job.pk).update(source_count=count,heartbeat_at=timezone.now())
        graph = collect(root,progress,cancelled)
        with transaction.atomic():
            project = Project.objects.select_for_update().get(pk=job.project_id)
            locked = InventoryJob.objects.select_for_update().get(pk=job.pk)
            if locked.cancel_requested or not project.active: raise InterruptedError
            latest = project.latest
            changed = not latest or latest.digest != graph['digest'] or latest.graph['coverage'] != graph['coverage']
            if changed: Snapshot.objects.create(project=project,digest=graph['digest'],graph=graph)
            project.checked_at=timezone.now(); project.issue=''; project.save(update_fields=['checked_at','issue'])
            locked.status='done'; locked.source_count=len(graph['sources']); locked.finished_at=timezone.now()
            locked.message='Novo snapshot registrado.' if changed else 'Sem mudança nas fontes; snapshot preservado.'
            locked.save()
    except InterruptedError:
        InventoryJob.objects.filter(pk=job.pk).update(status='cancelled',finished_at=timezone.now(),message='Cancelada. Último snapshot preservado.')
    except (OSError,ValueError):
        issue='Não foi possível ler a pasta. Confira acesso, localização e raízes autorizadas.'
        Project.objects.filter(pk=job.project_id).update(issue=issue)
        InventoryJob.objects.filter(pk=job.pk).update(status='failed',finished_at=timezone.now(),message=issue)
    except Exception:
        InventoryJob.objects.filter(pk=job.pk).update(status='failed',finished_at=timezone.now(),message='Falha interna na coleta. Último snapshot preservado.')
        raise
    return True
