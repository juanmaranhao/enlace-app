from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404
from django.core.exceptions import ValidationError
from apps.projetos.models import Project

class StaffRequiredMixin(LoginRequiredMixin,UserPassesTestMixin):
    def test_func(self): return self.request.user.is_staff

def project_for(user,pk,edit=False):
    projects = Project.objects.accessible(user)
    if edit and not user.is_superuser: projects = projects.filter(owner=user)
    try: return projects.get(pk=pk)
    except (Project.DoesNotExist,ValidationError,ValueError): raise Http404
