import uuid
from django.conf import settings
from django.db import models

class Assessment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    project=models.ForeignKey('projetos.Project',on_delete=models.PROTECT,related_name='assessments')
    snapshot=models.ForeignKey('arquitetura.Snapshot',on_delete=models.PROTECT)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    plan=models.JSONField()
    status=models.CharField(max_length=20,default='prepared')
    results=models.JSONField(default=list)
    summary=models.JSONField(default=dict)
    message=models.CharField(max_length=300,blank=True)
    cancel_requested=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:ordering=['-created_at']

class AssessmentPart(models.Model):
    assessment=models.ForeignKey(Assessment,on_delete=models.PROTECT,related_name='parts')
    index=models.PositiveSmallIntegerField()
    status=models.CharField(max_length=20,default='pending')
    result=models.JSONField(default=dict)
    class Meta:constraints=[models.UniqueConstraint(fields=['assessment','index'],name='one_assessment_part')]

class Conversation(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    project=models.ForeignKey('projetos.Project',on_delete=models.PROTECT,null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class ChatTurn(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    conversation=models.ForeignKey(Conversation,on_delete=models.PROTECT,related_name='turns')
    request_id=models.UUIDField()
    question=models.CharField(max_length=500)
    mode=models.CharField(max_length=20,default='local')
    status=models.CharField(max_length=20,default='done')
    context=models.JSONField(default=dict)
    answer=models.JSONField(default=dict)
    message=models.CharField(max_length=300,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['created_at']
        constraints=[models.UniqueConstraint(fields=['conversation','request_id'],name='unique_chat_request')]
