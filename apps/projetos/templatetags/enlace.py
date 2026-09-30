from django import template
from django.templatetags.static import static
from django.utils.html import format_html
register=template.Library()
@register.simple_tag
def icon(name):
    return format_html('<svg class="el-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><use href="{}#{}"></use></svg>',static('global/images/icons.svg'),name)
@register.filter
def kind_label(value):
    return {'flow':'Fluxo','skill':'Skill','rule':'Regras','contract':'Contrato','agent':'Agente','guide':'Guia'}.get(value,value)
@register.filter
def status_label(value):
    return {'prepared':'Em revisão','queued':'Na fila','running':'Em andamento','done':'Concluída','failed':'Falhou','cancelled':'Cancelada','uncertain':'Consumo incerto','authorized':'Autorizada'}.get(value,value)
