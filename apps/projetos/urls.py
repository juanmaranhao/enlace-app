from django.urls import path
from .views import PortfolioView,RegisterView,DashboardView,UpdateView,CancelView,DisconnectView,DirectoryView,JobStatusView,SetupView,ActionPlanView,ExecutePlanView
urlpatterns=[path('',PortfolioView.as_view(),name='carteira'),path('primeiro-acesso/',SetupView.as_view(),name='setup'),
    path('projetos/<uuid:pk>/planos/<uuid:plan_id>/',ActionPlanView.as_view(),name='action_plan'),path('projetos/<uuid:pk>/planos/<uuid:plan_id>/executar/',ExecutePlanView.as_view(),name='execute_plan'),
    path('projetos/novo/',RegisterView.as_view(),name='register'),path('pastas/',DirectoryView.as_view(),name='directories'),
    path('projetos/<uuid:pk>/',DashboardView.as_view(),name='dashboard'),path('projetos/<uuid:pk>/atualizar/',UpdateView.as_view(),name='update_inventory'),
    path('projetos/<uuid:pk>/desconectar/',DisconnectView.as_view(),name='disconnect'),path('projetos/<uuid:pk>/status/',JobStatusView.as_view(),name='job_status'),
    path('projetos/<uuid:pk>/coletas/<uuid:job_id>/cancelar/',CancelView.as_view(),name='cancel_inventory')]
