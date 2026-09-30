"""Dados de marca para o shell compartilhado."""
from django.conf import settings
from django.contrib.auth import get_user_model


def brand(request):
    from apps.projetos.models import Project
    projects = Project.objects.accessible(request.user).filter(active=True)
    return {'site_nome':'Enlace','jev_configured':settings.JEV_CONFIGURED,'text_configured':settings.TEXT_CONFIGURED,
            'versao':settings.VERSAO,'sidebar_projects':projects[:8],'first_setup':settings.DEBUG and not get_user_model().objects.exists()}

