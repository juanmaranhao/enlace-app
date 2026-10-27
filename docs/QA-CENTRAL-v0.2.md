# QA da central v0.2 — 27/10/2026

O piloto local concluiu consultas reais ao Codex em DJANGO_LANDPAGE e
TIMBRE_DIGITAL, preservou os metadados Git observados e exercitou pausa/retomada.
As duas tarefas chegaram a `review`, aguardando aprovação do usuário. O resultado
comprova esse fluxo de coordenação e consulta; não certifica executores automáticos
de produto, publicação, merge, deploy ou limpeza.

## Evidências locais

Os arquivos abaixo ficam em `.local/`, fora do versionamento. São recibos da
execução local; esta documentação consolida seus resultados sem copiar prompts,
credenciais ou conteúdo privado dos projetos.

| Fonte | Evidência |
|---|---|
| `.local/pilot-result.json` | Duas consultas concluídas; três critérios por tarefa; Git antes/depois; pausa/retomada; aceite pendente |
| `.local/qa/report.json` | 15 combinações de página/largura, interações do desenho, foco e fallback sem JavaScript |
| `.local/qa/detail-report.json` | Expansão do histórico e exibição de recibo em três larguras |
| `.local/central-mcp-smoke.json` | Transporte MCP stdio real, sete ferramentas, escopo de dois projetos, contextos sem token de posse |
| `.local/post-install-probe.json` | Sonda posterior à instalação, sem modelo, com todos os três servidores MCP desativados |

## Pilotos com modelo real

| Projeto | Tarefa | Operação Codex concluída |
|---|---|---|
| DJANGO_LANDPAGE | `56a64612-ebaf-47ba-a395-8404007a9bee` | `46eeb630-d26a-4578-8435-3625268f49dc` |
| TIMBRE_DIGITAL | `0fcf1a4c-6144-44b3-add7-93cc25389c3b` | `6c7a2fe7-7b37-4a21-82d3-6433f7b1d8f0` |

As consultas concluíram com raiz correta, política de leitura e zero MCP
disponível para o modelo. Cada tarefa registrou três critérios verificados,
igualdade dos metadados Git pré/pós e pausa/retomada. O recibo final mantém
`human_approval=pending` e `cleanup_authorized=false` nas duas tarefas.

Consulta concluída (`completed`) é o estado da operação Codex. Tarefa em
`review` é o estado da entrega aguardando o usuário. O texto do modelo permanece
autorrelato; os critérios do piloto dependem de verificações separadas. Igualdade
dos metadados Git não equivale a hash de todos os conteúdos ou prova de merge.
Não houve executor automático de implementação nos projetos nesse piloto.

## Interface e apresentação

Foram verificadas Central, Cérebro da central, formulário de tarefa, detalhe da
tarefa e contrato, em 1440, 390 e 320 px: quinze combinações, todas com HTTP 200,
largura do documento igual à viewport e nenhuma ocorrência de overflow. O
relatório não registrou erros de página.

Nas três larguras, passaram seleção da etapa de decisão, modo apresentação,
avanço, saída e foco no controle. Com JavaScript desabilitado, os doze detalhes
permaneceram visíveis e os controles dependentes de script ficaram ocultos.

No detalhe da tarefa, a expansão do histórico aumentou de um para 31 itens
visíveis, o recibo apareceu e não houve overflow nas três larguras.
`humanReviewVisible=false` nesse roteiro: o formulário de conferência humana
não foi exercitado visualmente nesta rodada. Seus estados e autorização têm
cobertura nos testes web; isso não substitui sua conferência visual nem constitui
um aceite humano dos pilotos.

O desenho permanece disponível em `/central/como-funciona/`; a operação começa
em `/central/`. Capturas correspondentes ficam em `.local/qa/`.

## MCP e skill no host

O smoke de 15:42:57 UTC leu a configuração TOML instalada no host, inicializou
o servidor stdio real e confirmou exatamente sete ferramentas. Não usou um
comando de servidor independente dessa configuração. `list_work_projects`
retornou apenas DJANGO_LANDPAGE e
TIMBRE_DIGITAL, ambos com contrato revisão 1. `get_work_context` retornou suas
tarefas em `review`, com sete etapas e sem `lease_token`. Foram feitas somente
chamadas de leitura.

O MCP `enlace-central` foi instalado globalmente via
`codex mcp add`, limitado ao operador configurado e aos dois IDs dos pilotos.
A skill `enlace-central` foi copiada para `.codex/skills/enlace-central` e seu hash
foi conferido. As skills de domínio dos projetos continuam em seus locais de
origem, apenas referenciadas pelo pacote comum.

O recibo registra `host_installed=true` e o horário dessa nova execução após a
instalação. A descoberta das novas ferramentas exige nova sessão do Codex.
Essa instalação não concede ferramentas MCP ao processo isolado de consulta
contextual, que as desativa e verifica antes de iniciar o modelo.

A sonda posterior à instalação confirmou `ready`, sandbox válido e
`model_invoked=false`: `comfyui-local`, `enlace-central` e `node_repl` ficaram
todos `disabled`, com zero ferramentas e recursos. Isso verificou também a
desativação do novo MCP da própria central no processo isolado de consulta.

## SQLite, preservação e concorrência

O backup do SQLite foi validado e a base existente recebeu as migrações da
central, preservando usuários, carteira e histórico. A base de uso não foi
substituída por dados de QA.

A rodada real revelou disputa de escrita entre workers. A configuração SQLite
foi ajustada com `OPTIONS.timeout=20` e `OPTIONS.transaction_mode=IMMEDIATE`:
transações reservam escrita ao iniciar, evitando a promoção tardia de uma
transação de leitura durante essa concorrência. A rodada de retomada passou
com workers ativos após a correção. Esse resultado cobre o uso local exercitado;
não comprova capacidade para múltiplos hosts ou carga de produção.

## Testes e aprendizados

A suíte final passou com **106 testes**, em cerca de 10 segundos.
`makemigrations --check` não apontou mudanças pendentes; system check e diff
check ficaram limpos. Antes da consolidação, os 17 testes isolados dos
adaptadores Git/Codex também passaram: protocolo stdio, negação de aprovação,
isolamento MCP, cancelamento, timeout, retomada, falha de persistência, gitdir
externo e contagens Git.

Aprendizados incorporados à implementação e à documentação:

- Um override `mcp_servers={}` pode preservar servidores herdados. Enumerar,
  desativar explicitamente por nome e confirmar zero ferramentas/recursos antes
  do turno resolveu o caso real, sem editar a configuração global para a consulta.
- No SQLite local com workers concorrentes, reservar a escrita no início da
  transação evita o conflito observado na promoção tardia; o timeout é limitado.
- Autorrelato, observação, recibo técnico e aprovação humana precisam manter
  origens distintas em todo o fluxo, inclusive na apresentação do resultado.

Limites restantes: aprovação humana dos dois pilotos; descoberta das novas
ferramentas numa nova sessão; QA visual específico do formulário de conferência
humana; executores automáticos de produto e limpeza. O conjunto completo dos
critérios AC-01 a AC-42 da especificação original continua sem certificação
integral. Esta entrega é uma central local, sem deploy de produção incluído.
