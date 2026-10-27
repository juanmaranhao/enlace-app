"""Histórico operacional consultável; transições passam pelos serviços."""
from django.contrib import admin
from .models import ProjectContract, Task, TaskStep, TaskEvent, CodexRun


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Task)
class TaskAdmin(ReadOnlyAdmin):
    list_display = ('objective', 'project', 'status', 'current_stage', 'revision', 'created_at')
    list_filter = ('status', 'workflow')
    search_fields = ('objective', 'project__name')


@admin.register(ProjectContract)
class ContractAdmin(ReadOnlyAdmin):
    list_display = ('project', 'revision', 'digest', 'created_at')
    search_fields = ('project__name', 'digest')


@admin.register(TaskStep)
class StepAdmin(ReadOnlyAdmin):
    list_display = ('task', 'title', 'status', 'position')
    search_fields = ('task__objective', 'title')


@admin.register(TaskEvent)
class EventAdmin(ReadOnlyAdmin):
    list_display = ('task', 'kind', 'created_at')
    search_fields = ('task__objective', 'kind')


@admin.register(CodexRun)
class CodexRunAdmin(ReadOnlyAdmin):
    list_display = ('task', 'status', 'thread_id', 'created_at')
    search_fields = ('task__objective', 'thread_id')
