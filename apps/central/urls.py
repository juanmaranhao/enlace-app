from django.urls import path
from .views import (CentralHomeView, BrainView, TaskCreateView, ContractView, TaskDetailView,
                    TaskActionView, CheckpointView, TaskContextView, ProbeView, CodexQueueView, HumanReviewView)

urlpatterns = [
    path('', CentralHomeView.as_view(), name='central_home'),
    path('como-funciona/', BrainView.as_view(), name='central_brain'),
    path('tarefas/nova/', TaskCreateView.as_view(), name='central_task_new'),
    path('projetos/<uuid:pk>/contrato/', ContractView.as_view(), name='central_contract'),
    path('tarefas/<uuid:pk>/', TaskDetailView.as_view(), name='central_task_detail'),
    path('tarefas/<uuid:pk>/acao/', TaskActionView.as_view(), name='central_task_action'),
    path('tarefas/<uuid:pk>/checkpoint/', CheckpointView.as_view(), name='central_task_checkpoint'),
    path('tarefas/<uuid:pk>/conferencia/', HumanReviewView.as_view(), name='central_task_human_review'),
    path('tarefas/<uuid:pk>/contexto/', TaskContextView.as_view(), name='central_task_context'),
    path('tarefas/<uuid:pk>/observar/', ProbeView.as_view(), name='central_task_probe'),
    path('tarefas/<uuid:pk>/codex/', CodexQueueView.as_view(), name='central_task_codex'),
]
