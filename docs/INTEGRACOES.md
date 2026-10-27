# Integrações locais

O cadastro de pasta habilita inventário. Os pacotes abaixo habilitam consulta pelo Codex, recepção de eventos de um produto e coordenação local de tarefas. Sua distribuição não instala conexões automaticamente no host ou nos projetos.

## Central de tarefas v0.2

`integrations/central_mcp.py` é um MCP stdio local separado do conector HTTP por projeto. O host deve iniciar a `.venv/Scripts/python.exe` do Enlace com o caminho absoluto desse arquivo e fornecer `ENLACE_OPERATOR` e `ENLACE_CENTRAL_PROJECT_IDS` (UUIDs separados por vírgulas). O operador precisa estar ativo e ser staff; a lista explícita é intersectada com os projetos ativos acessíveis a ele. Mutações de tarefas também conferem propriedade ou superusuário.

Esses valores são configuração do processo no host e não podem ser trocados por argumento de ferramenta. O servidor usa o banco local do Enlace, não autentica clientes remotos e não depende de um servidor HTTP. Acesso à configuração local faz parte de sua confiança.

Em 27/10/2026, o MCP `enlace-central` foi instalado globalmente via `codex mcp add`, com operador `juanmaranhao` e allowlist apenas dos projetos DJANGO_LANDPAGE (`25a0c00f-4f28-4dc8-86d8-4d7e97f741d1`) e TIMBRE_DIGITAL (`d739e47e-0d9d-49ac-8387-c6e953e03c32`). Usa a configuração e o SQLite da instalação Enlace existente. A sessão atual não recebe retroativamente ferramentas novas: abra uma nova sessão do Codex para carregá-las.

O smoke stdio real de 15:42:57 UTC usou a configuração TOML instalada no host e consultou projetos e contexto dos dois pilotos com sucesso, sem expor token de posse. O recibo registra `host_installed=true`. Instalação, smoke de transporte e descoberta numa nova sessão são evidências distintas. Detalhes em [QA-CENTRAL-v0.2.md](QA-CENTRAL-v0.2.md).

Ferramentas: `list_work_projects`, `prepare_work`, `get_work_context`, `start_work`, `pause_work`, `resume_work` e `record_work_checkpoint`. Revisão e token de posse protegem alterações; ler contexto não concede posse. Não há shell, merge, deploy, limpeza, conferência humana nem aprovação final nessas ferramentas.

A skill portátil correspondente é `integrations/skills/enlace-central/SKILL.md`. A cópia global em `.codex/skills/enlace-central` foi instalada com hash conferido. Ela descreve a condução das sete etapas e preserva a origem das evidências. Skills de domínio continuam como referências, sem migração automática. Veja o fluxo e os limites completos em [HARNESS-CENTRAL.md](HARNESS-CENTRAL.md).

## Credencial por projeto e canal

Após criar seu usuário e vincular um projeto, copie seu ID da URL do painel:

```powershell
.venv\Scripts\python.exe manage.py create_connector --project ID_DO_PROJETO --user SEU_USUARIO --channel codex --name "Codex local"
```

O comando grava a credencial apenas em `.local/connectors/ID_DO_CONECTOR.env`. Não imprime o token. No banco permanece somente seu hash. Para um produto, crie outra credencial com `--channel product`; não reutilize a chave Jev ou de texto. Responsável pode revogar em **Análise → Conectores do projeto**. Preserva histórico e impede novos pedidos por aquele token.

## MCP de consulta por conector

O host deve iniciar `.venv/Scripts/python.exe` com o caminho absoluto de `integrations/mcp_server.py` e fornecer, por ambiente local, `ENLACE_URL` e `ENLACE_TOKEN` do conector. Usar a `.venv` do Enlace mantém a dependência MCP fora dos projetos observados. A central deve estar ativa para as ferramentas responderem; quando indisponível, retornam erro, sem respostas simuladas. HTTP sem TLS só é aceito em loopback e redirects não são seguidos.

Ferramentas: search_capabilities, get_flow_context, assess_goal, get_analysis, prepare_task, get_task, get_conversation_context. A avaliação e a tarefa devolvem links para revisão no painel; preparar não executa. O conector consulta apenas seu projeto, sem acesso a shell arbitrário ou ao restante da carteira.

O formato de configuração do host deve ser conferido na instalação, evitando incluir credencial em arquivo versionado. Este conector HTTP por projeto não foi instalado como parte do piloto central. A instalação global registrada acima é a do MCP local `enlace-central`.

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

A atualização do inventário possui executor com revisão e recibo. A v0.2 acrescenta observação Git por comandos fechados e uma fila de consulta contextual ao Codex app-server. Essa consulta não recebe ferramentas de execução, não lê código por conta própria nem implementa mudanças. Sua resposta permanece autorrelato; conferência humana e resultados técnicos são registros diferentes.

As capacidades de criar site/vídeo são referências orientadas às fontes. A implementação continua no projeto responsável e dentro das permissões de seu executor. A central não executa merge, deploy ou limpeza. Veja [CODEX-EXECUTOR.md](CODEX-EXECUTOR.md) para política, herança de MCP, retomada e limites de observação.
