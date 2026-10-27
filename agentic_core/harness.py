"""Contratos puros do harness: conhecimento explícito e fluxos versionados."""
from copy import deepcopy
import hashlib
import json

BUNDLE_VERSION = "central-1.0.0"
BUNDLE = {
    "version": BUNDLE_VERSION,
    "rules": [
        {"id": "context", "title": "Contexto antes da execução", "instruction": "Confirme projeto, contrato, objetivo e critérios de aceite antes de editar."},
        {"id": "scope", "title": "Escopo rastreável", "instruction": "Cada etapa atende ao objetivo registrado. Propostas adicionais permanecem separadas."},
        {"id": "evidence", "title": "Evidência tem origem", "instruction": "Autorrelato, execução observada, verificação técnica e aprovação humana são evidências distintas."},
        {"id": "recovery", "title": "Retomada reconciliada", "instruction": "Retome a partir do estado persistido; confirme versões e resultados externos antes de repetir ações."},
        {"id": "preservation", "title": "Preservação de trabalho", "instruction": "Merge, deploy e limpeza são estados independentes. Conteúdo exclusivo, ignorado ou posterior ao merge é preservado."},
        {"id": "local", "title": "Contrato do projeto", "instruction": "Identidade, negócio e exceções aprovadas pertencem ao projeto. Conflitos são apresentados antes da ação dependente."},
    ],
    "skills": {
        "coding": ["arquitetura-sistema", "backend-django", "frontend-templates", "testes-automatizados", "git-workflow"],
        "media": ["sistema-visual-multicanal", "social-video", "social-visuais", "midia-gerada", "git-workflow"],
        "audit": ["arquitetura-sistema", "git-workflow"],
    },
    "distribution": "As skills de domínio são referências por nome; presença e versão precisam ser conferidas no ambiente de execução.",
}

WORKFLOWS = {
    "coding": {"label": "Desenvolvimento", "description": "Implementar e revisar uma mudança no projeto.", "version": 1},
    "media": {"label": "Imagem e vídeo", "description": "Criar uma peça preservando identidade, fontes e aprovação visual.", "version": 1},
    "audit": {"label": "Pesquisa e diagnóstico", "description": "Investigar uma questão e entregar evidências sem alterar o projeto.", "version": 1},
}

STAGES = [
    {"key": "intake", "title": "Entender", "role": "Coordenador", "description": "Delimitar necessidade, projeto e critérios de aceite.", "output": "Pedido compreendido"},
    {"key": "decision", "title": "Validar a abordagem", "role": "Arquitetura", "description": "Conferir decisões vigentes, alternativas e limites.", "output": "Abordagem justificada"},
    {"key": "plan", "title": "Planejar", "role": "Coordenador", "description": "Definir entregas, habilidades, responsáveis e verificações.", "output": "Plano rastreável"},
    {"key": "execution", "title": "Executar", "role": "Especialista", "description": "Trabalhar no projeto correto e registrar checkpoints.", "output": "Entrega da etapa"},
    {"key": "review", "title": "Revisar", "role": "Revisor", "description": "Comparar alterações e evidências com a proposta.", "output": "Revisão registrada"},
    {"key": "validation", "title": "Validar", "role": "Verificador", "description": "Comprovar critérios de aceite com recibos verificáveis.", "output": "Critérios comprovados"},
    {"key": "delivery", "title": "Entregar", "role": "Coordenador", "description": "Apresentar resultado e registrar os próximos passos de integração e retenção.", "output": "Entrega para aprovação"},
]


def digest(value):
    """Hash estável de contratos e recibos JSON, sem dependência do framework."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def get_flow(workflow="coding"):
    """Devolve uma cópia da sequência, impedindo mutação do catálogo global."""
    if workflow not in WORKFLOWS:
        raise ValueError("Fluxo desconhecido.")
    return deepcopy(STAGES)


def knowledge_bundle():
    """Pacote mínimo comum fixado em cada tarefa."""
    bundle = deepcopy(BUNDLE)
    bundle["digest"] = digest(BUNDLE)
    return bundle


def validate_contract(payload):
    """Valida configuração declarativa; comandos não são executados pelo contrato."""
    if not isinstance(payload, dict):
        raise ValueError("Contrato inválido.")
    allowed = {"stack", "restrictions", "validation_commands", "execution_mode", "notes"}
    if set(payload) - allowed:
        raise ValueError("Contrato contém campos não suportados.")
    clean = {}
    stack = payload.get("stack", "")
    if isinstance(stack, list):
        if len(stack) > 30 or any(not isinstance(item, str) or not item.strip() for item in stack):
            raise ValueError("Stack inválida.")
        stack = " · ".join(stack)
    if not isinstance(stack, str) or len(stack) > 1000:
        raise ValueError("Stack inválida.")
    clean["stack"] = stack.strip()
    for key in ("restrictions", "validation_commands"):
        items = payload.get(key, [])
        if not isinstance(items, list) or len(items) > 30 or any(not isinstance(item, str) or not item.strip() or len(item) > 500 for item in items):
            raise ValueError("Use listas de textos curtos no contrato.")
        clean[key] = [item.strip() for item in items]
    mode = payload.get("execution_mode", "guided")
    if mode not in {"guided", "read_only"}:
        raise ValueError("Modo de execução inválido.")
    notes = payload.get("notes", "")
    if not isinstance(notes, str) or len(notes) > 2000:
        raise ValueError("Notas acima do limite.")
    clean.update(execution_mode=mode, notes=notes.strip())
    return clean
