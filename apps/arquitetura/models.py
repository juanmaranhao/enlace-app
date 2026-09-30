import uuid
from django.db import models
from django.conf import settings

class Snapshot(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    project = models.ForeignKey('projetos.Project',on_delete=models.PROTECT,related_name='snapshots')
    digest = models.CharField(max_length=64)
    graph = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']

class ExecutionEvent(models.Model):
    project = models.ForeignKey('projetos.Project',on_delete=models.PROTECT,related_name='events')
    external_id = models.CharField(max_length=160)
    channel = models.CharField(max_length=20)
    event_type = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    occurred_at = models.DateTimeField()
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-occurred_at']
        constraints = [models.UniqueConstraint(fields=['project','channel','external_id'],name='unique_execution_event')]

class Connector(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    project=models.ForeignKey('projetos.Project',on_delete=models.PROTECT,related_name='connectors')
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    name=models.CharField(max_length=100)
    channel=models.CharField(max_length=20)
    token_hash=models.CharField(max_length=64,unique=True)
    active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    last_seen_at=models.DateTimeField(null=True,blank=True)
