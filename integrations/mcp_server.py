"""MCP local v2. O token é do conector Enlace; nunca é a chave Jev/OpenAI."""
import os
import sys
from typing import Any
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from integrations.enlace_client import EnlaceClient, EnlaceUnavailable

mcp=MCPServer('Enlace',instructions='Consulte arquitetura declarada com fontes. Preparar uma análise ou ação não a executa; devolva o link de revisão ao usuário. Não há execução genérica de shell nem observação automática do desktop.')

def client():
    token=os.environ.get('ENLACE_TOKEN','')
    if not token:raise ValueError('Conector Enlace não configurado.')
    return EnlaceClient(os.environ.get('ENLACE_URL','http://127.0.0.1:8766'),token)

def call(action, **payload):
    try:
        return client().call(action, **payload)
    except (EnlaceUnavailable, ValueError) as exc:
        raise ToolError(str(exc)) from None

@mcp.tool()
def search_capabilities(objective:str)->dict[str, Any]:
    """Busca local no projeto autorizado pelo conector. Não chama IA ou executa tarefa."""
    return call('search',question=objective)

@mcp.tool()
def get_flow_context(focus:str='',snapshot_id:str|None=None)->dict[str, Any]:
    """Retorna o mapa e as fontes do snapshot, usando os mesmos IDs do painel."""
    return call('flow',focus=focus,snapshot_id=snapshot_id)

@mcp.tool()
def assess_goal(goal:str,criteria:list[str],source_ids:list[str])->dict[str, Any]:
    """Prepara avaliação Jev. O envio aguarda autorização no link do painel."""
    return call('prepare_assessment',goal=goal,criteria=criteria,source_ids=source_ids)

@mcp.tool()
def get_analysis(analysis_id:str)->dict[str, Any]:
    """Consulta estado real e juízos da avaliação autorizada pelo projeto."""
    return call('analysis',id=analysis_id)

@mcp.tool()
def prepare_task(executor:str='inventory-refresh-v1')->dict[str, Any]:
    """Prepara atualização de inventário com hash e link de autorização. Outros executores não estão registrados."""
    return call('prepare_task',executor=executor)

@mcp.tool()
def get_task(task_id:str)->dict[str, Any]:
    """Consulta recibo, progresso e resultado real da tarefa, sem reenviá-la."""
    return call('task',id=task_id)

@mcp.tool()
def get_conversation_context(conversation_id:str)->dict[str, Any]:
    """Retoma explicitamente uma conversa do mesmo usuário e projeto autorizado."""
    return call('conversation',id=conversation_id)

if __name__=='__main__':mcp.run()
