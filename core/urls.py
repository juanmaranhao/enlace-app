"""Rotas da central."""
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from .health import health

urlpatterns = [
    path('healthz/',health,name='health'),
    path("admin/", admin.site.urls),
    path("entrar/", LoginView.as_view(template_name="login.html"), name="login"),
    path("sair/", LogoutView.as_view(), name="logout"),
    path("", include("apps.projetos.urls")),
    path("", include("apps.arquitetura.urls")),
    path("", include("apps.assistente.urls")),
]
