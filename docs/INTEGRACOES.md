# Integrações locais

O cadastro de pasta habilita inventário. O pacote opcional abaixo habilita consulta pelo Codex e recepção de eventos de um produto. Não foi instalado automaticamente em nenhum deles.

## Credencial por projeto e canal

Após criar seu usuário e vincular um projeto, copie seu ID da URL do painel:

```powershell
.venv\Scripts\python.exe manage.py create_connector --project ID_DO_PROJETO --user SEU_USUARIO --channel codex --name "Codex local"
```

O comando grava a credencial apenas em `.local/connectors/ID_DO_CONECTOR.env`. Não imprime o token. No banco permanece somente seu hash. Para um produto, crie outra credencial com `--channel product`; não reutilize a chave Jev ou de texto. Responsável pode revogar em **Análise → Conectores do projeto**. Preserva histórico e impede novos pedidos por aquele token.

## MCP stdio

O host deve iniciar `.venv/Scripts/python.exe` com o caminho absoluto de `integrations/mcp_server.py` e fornecer, por ambiente local, `ENLACE_URL` e `ENLACE_TOKEN` do conector. Usar a `.venv` do Enlace mantém a dependência MCP fora dos projetos observados. A central deve estar ativa para as ferramentas responderem; quando indisponível, retornam erro, sem respostas simuladas. HTTP sem TLS só é aceito em loopback e redirects não são seguidos.

Ferramentas: search_capabilities, get_flow_context, assess_goal, get_analysis, prepare_task, get_task, get_conversation_context. A avaliação e a tarefa devolvem links para revisão no painel; preparar não executa. O conector consulta apenas seu projeto, sem acesso a shell arbitrário ou ao restante da carteira.

O formato de configuração do host deve ser conferido na instalação, evitando incluir credencial em arquivo versionado. A instalação global no Codex não faz parte desta entrega; nenhuma configuração de outros chats foi alterada.

## Skill

Pacote em `integrations/skills/enlace-guide`. Sua estrutura foi validada pela ferramenta oficial skill-creator. Após configurar o MCP, a skill pode ser copiada para `.agents/skills/enlace-guide` no projeto desejado ou instalada no host, conforme o escopo escolhido. Essa operação deve ser planejada antes de gravar em outros projetos; preserve regras e skills existentes.

No Codex, o próprio modelo do chat redige a orientação, usando as ferramentas da central. Não precisa acionar o provedor de texto do app outra vez. IDs autorizados permitem retomar uma conversa específica do mesmo usuário/projeto; não importam automaticamente os chats do desktop.

## Eventos de produto

Integre `EnlaceClient` e `EventBuffer` em um ponto real de execução do produto. Exemplo de formato, não registro realizado:

```python
event = {
    'schema_version': 1,
    'external_id': 'operacao-123:provider_finished',
    'channel': 'product',
    'event_type': 'provider_finished',
    'name': 'Revisão de documento',
    'occurred_at': '2026-09-30T15:00:00-03:00',
    'details': {'trace_id': 'operacao-123', 'duration_ms': 2400, 'usage_uncertain': False},
}
buffer.emit(event)  # apenas memória; não usa rede
buffer.flush()     # chamar num worker do host, fora do caminho crítico
```

Buffer suporta até 500 eventos e informa descartes pelo contador `dropped`. Falha de flush mantém o lote em memória; reenvio idêntico é deduplicado pela central. Não há spool persistente: reiniciar o host pode perder eventos não enviados. O host decide onde/como drenar e mostrar cobertura insuficiente. A central desligada não deve bloquear a tarefa principal do produto.

Para Codex, relatórios de leitura/invocação precisam ser produzidos por integração disponível no host. Consultar mapa ou skill não comprova execução. Este MCP não observa automaticamente o desktop nem registra todos os seus acionamentos.

## Limite de execução

Somente atualização do inventário possui executor nesta versão. As capacidades de criar site/vídeo são referências orientadas às fontes. Executores desses produtos exigem contratos próprios, validação e revisão dos efeitos antes de instalação.
