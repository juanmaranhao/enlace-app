"""Entradas da central: objetivo, contrato e evidência têm fronteiras explícitas."""
import uuid

from django import forms

from apps.projetos.models import Project
from .models import TaskEvent


WORKFLOW_CHOICES = [('coding', 'Desenvolvimento'), ('media', 'Imagem e vídeo'), ('audit', 'Diagnóstico')]


class TaskForm(forms.Form):
    project = forms.ModelChoiceField(label='Projeto', queryset=Project.objects.none())
    objective = forms.CharField(label='O que precisa ser entregue?', max_length=3000, widget=forms.Textarea(attrs={'rows': 3}))
    workflow = forms.ChoiceField(label='Fluxo de trabalho', choices=WORKFLOW_CHOICES)
    criteria = forms.CharField(label='Critérios de aceite', help_text='Um resultado verificável por linha.', widget=forms.Textarea(attrs={'rows': 4}), max_length=6000)
    request_key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        projects = Project.objects.accessible(user).filter(active=True, contracts__isnull=False)
        if not user.is_superuser:
            projects = projects.filter(owner=user)
        self.fields['project'].queryset = projects.distinct()

    def clean_criteria(self):
        items = [line.strip() for line in self.cleaned_data['criteria'].splitlines() if line.strip()]
        if not 1 <= len(items) <= 12 or any(len(item) > 500 for item in items):
            raise forms.ValidationError('Informe de 1 a 12 critérios, com até 500 caracteres cada.')
        return items


class ContractForm(forms.Form):
    stack = forms.CharField(label='Stack', initial='Django · Python · PostgreSQL · HTML/CSS/JavaScript', max_length=500)
    restrictions = forms.CharField(label='Regras específicas', max_length=6000, widget=forms.Textarea(attrs={'rows': 5}), help_text='Uma regra por linha. As regras canônicas do projeto continuam válidas.')
    execution_mode = forms.ChoiceField(label='Modo', choices=[('guided', 'Execução dirigida no Codex'), ('read_only', 'Consulta e diagnóstico')])
    validation_commands = forms.CharField(label='Verificações do projeto', max_length=3000, required=False, widget=forms.Textarea(attrs={'rows': 3}), help_text='Referências para o plano. Estes comandos não são executados pelo formulário.')

    def contract_payload(self):
        data = self.cleaned_data
        return {'stack': data['stack'], 'restrictions': data['restrictions'].splitlines(),
                'execution_mode': data['execution_mode'], 'validation_commands': data['validation_commands'].splitlines()}


class ActionForm(forms.Form):
    expected_revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)


class CheckpointForm(ActionForm):
    stage_key = forms.ChoiceField(label='Etapa')
    note = forms.CharField(label='O que foi concluído?', max_length=3000, widget=forms.Textarea(attrs={'rows': 3}))
    reference = forms.CharField(label='Referência da evidência', max_length=1000, required=False, help_text='URL, arquivo ou identificador de recibo. Um relato não vira teste verificado.')
    request_key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)
    receipts = forms.ModelMultipleChoiceField(label='Recibos de conferência', queryset=TaskEvent.objects.none(), required=False,
                                              help_text='Na validação, selecione recibos que cubram os critérios. Relatos livres continuam sendo autorrelatos.')

    def __init__(self, *args, task, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['stage_key'].choices = [(step.key, step.title) for step in task.steps.order_by('position')]
        self.fields['receipts'].queryset = task.events.filter(kind__in=['verified_result', 'human_review'])
        self.fields['receipts'].label_from_instance = lambda event: '{} · critérios {} · {}'.format(
            'Conferência humana' if event.kind == 'human_review' else 'Verificação técnica',
            ', '.join(str(index + 1) for index in event.payload.get('criteria_indices', [])), str(event.pk)[:8])


class HumanReviewForm(ActionForm):
    criteria_indices = forms.MultipleChoiceField(label='Critérios conferidos', widget=forms.CheckboxSelectMultiple)
    note = forms.CharField(label='Como você conferiu?', min_length=10, max_length=2000, widget=forms.Textarea(attrs={'rows': 3}))
    request_key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)

    def __init__(self, *args, task, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['criteria_indices'].choices = [(str(index), text) for index, text in enumerate(task.criteria)]

    def clean_criteria_indices(self):
        return [int(value) for value in self.cleaned_data['criteria_indices']]
