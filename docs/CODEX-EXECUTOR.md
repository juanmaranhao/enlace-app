# Execução contextual e observação Git — piloto v1

O Enlace direciona o trabalho ao projeto escolhido e fornece conhecimento comum.
O adaptador deste piloto inicia **pareceres contextuais** no Codex app-server;
implementação de produto continua no Codex guiado pelo contrato da tarefa. Ele não
oferece shell genérico, limpeza, merge, deploy ou geração de mídia.

## Inventário verificável

`agentic_core.git_inventory.inspect_repository(root, allowed_roots)` resolve a raiz
autorizada e chama uma lista fechada de consultas Git. A ponte `.git` pode apontar
para um gitdir externo: o worktree da consulta permanece explícito. FSMonitor,
locks opcionais e prompts Git são desabilitados nesta invocação.

O recibo contém HEAD, branch, contagens de alterações/rastreamento/ignorados, flags
ocultas do índice, worktrees visíveis e data da observação. Nenhum conteúdo desses
arquivos é lido ou retornado. Não há fetch, consulta de PR ou prova de integração.
`cleanup_authorized` permanece `false`, inclusive quando a árvore está limpa.
Consultas são sequenciais; trabalho concorrente exige uma nova observação.

## Codex app-server

`CodexReadOnlyRunner.run(...)` usa transporte stdio JSON-RPC com o executável Codex
da instalação. O schema gerado pelo executável em 27/10/2026 confirmou:

- `thread/start.sandbox = "read-only"` e `approvalPolicy = "never"`;
- `turn/start.sandboxPolicy.type = "readOnly"`, `networkAccess = false`;
- `initialize` / `initialized`, `thread/start` ou `thread/resume`, `turn/start`;
- eventos `item/completed`, `turn/completed` e interrupção `turn/interrupt`.

O processo recebe overrides de configuração para desabilitar shell, apps, plugins,
memórias e delegação. O carregamento de instruções locais é desabilitado: o contexto
relevante já vem da central. A sonda exige a política devolvida pelo servidor e uma
lista de fontes de instrução vazia. Nenhum arquivo de configuração
do usuário é alterado. Credenciais de produto em variáveis de ambiente não são
repassadas; autenticação do Codex usa sua instalação já configurada.

**Aprendizado verificado no runtime:** `mcp_servers={}` não remove servidores
herdados. A sonda enumera nomes sem iniciar modelo, reabre o processo uma única vez
com `mcp_servers.<nome>.enabled=false` e exige zero servidores disponíveis. A lista
de status ainda pode conter entradas `disabled`, desde que ferramentas, recursos
e templates estejam vazios. Estado ausente/ambíguo bloqueia `turn/start`.

`probe(root, allowed_roots)` testa apenas essa preparação, sem chamar modelo.
A sonda real do template em 27/10/2026 confirmou `readOnly`, raiz correta, zero fontes
automáticas e os conectores `comfyui-local` e `node_repl` desativados, sem ferramentas.
Isso comprova a preparação do canal; um turno real e sua retomada são provas separadas.
O piloto posterior concluiu consultas reais nos dois projetos, com raiz correta,
política de leitura e zero MCP disponível. Resultados e limites dessa validação
estão em [QA-CENTRAL-v0.2.md](QA-CENTRAL-v0.2.md).
A sonda pós-instalação, sem invocar modelo, confirmou também `enlace-central`
desativado junto de `comfyui-local` e `node_repl`, todos sem ferramentas/recursos.

Essas fronteiras devem ser revalidadas no runtime ao atualizar o Codex. Sandbox de
somente leitura, isoladamente, não impede leitura de segredos. O piloto não depende
de instruções em linguagem natural para oferecer ferramentas irrestritas ao modelo.

## Persistência e retomada

O chamador persiste `thread_ready` antes do turno, `turn_ready` antes de consumir
resultados e cada evento pelo callback `on_event`. Eventos contêm somente IDs, tipo,
estado e horários; comandos, stdout, prompts e raciocínio não entram no recibo.
Falha de persistência interrompe e propaga a exceção.

A retomada exige `thread_id` e `resume_receipt` guardado pelo servidor com a mesma
raiz e `policy_version`. Um timeout retorna `timed_out`, uma interrupção retorna
`interrupted`; processo encerrado sem evento terminal retorna `failed`. Nunca há
retry automático. O chamador reconcilia a operação anterior antes de reenviar.

O resultado textual é sempre `evidence_level=self_report`: turno Codex concluído
não equivale a teste aprovado, implementação realizada ou publicação confirmada.

## Validação sem modelo

`tests.test_codex_runner` usa servidor falso como subprocesso real, cobrindo stdio,
negação de aprovação, retomada, timeout, cancelamento, falha de persistência, falha
terminal e evento antecipado. `tests.test_git_inventory` cria repositórios descartáveis
para provar contagens, gitdir externo, flags ocultas e preservação de conteúdo.

Fonte consultada: [Codex app-server](https://learn.chatgpt.com/docs/app-server).
Os nomes e payloads concretos também foram conferidos com
`codex app-server generate-json-schema`; o schema local prevalece sobre exemplos
da documentação quando a instalação usa outra versão do protocolo.
