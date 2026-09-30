import uuid
from django.conf import settings
from django.db import models

class ProjectQuerySet(models.QuerySet):
    def accessible(self,user):
        if not user.is_authenticated or not user.is_staff: return self.none()
        if user.is_superuser: return self
        return self.filter(models.Q(owner=user)|models.Q(readers=user)).distinct()

class Project(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name = models.CharField(max_length=120)
    root = models.CharField(max_length=1000)
    canonical_key = models.CharField(max_length=1000,unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='owned_projects')
    readers = models.ManyToManyField(settings.AUTH_USER_MODEL,blank=True,related_name='readable_projects')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    checked_at = models.DateTimeField(null=True,blank=True)
    issue = models.CharField(max_length=300,blank=True)
    objects = ProjectQuerySet.as_manager()
    class Meta: ordering = ['name']
    def __str__(self): return self.name
    @property
    def latest(self): return self.snapshots.order_by('-created_at').first()

class InventoryJob(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    project = models.ForeignKey(Project,on_delete=models.PROTECT,related_name='jobs')
    status = models.CharField(max_length=20,default='queued')
    cancel_requested = models.BooleanField(default=False)
    source_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True,blank=True)
    heartbeat_at = models.DateTimeField(null=True,blank=True)
    finished_at = models.DateTimeField(null=True,blank=True)
    message = models.CharField(max_length=300,blank=True)
    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['project'],condition=models.Q(status__in=['queued','running']),name='one_active_inventory_per_project')]

class ActionPlan(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    project=models.ForeignKey(Project,on_delete=models.PROTECT,related_name='action_plans')
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    payload=models.JSONField()
    status=models.CharField(max_length=20,default='prepared')
    job=models.ForeignKey(InventoryJob,on_delete=models.PROTECT,null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
