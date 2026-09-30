from django.contrib import admin
from .models import Project,InventoryJob
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display=('name','root','active','checked_at')
    readonly_fields=('id','canonical_key','created_at','checked_at')
    filter_horizontal=('readers',)
@admin.register(InventoryJob)
class JobAdmin(admin.ModelAdmin):
    list_display=('project','status','source_count','created_at')
    readonly_fields=('project','status','source_count','message','created_at','started_at','finished_at','heartbeat_at')
    def has_add_permission(self,request):return False
    def has_delete_permission(self,request,obj=None):return False
