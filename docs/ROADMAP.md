# Estado de implementação

## Base v0.1 e especificação original

| Etapa | Objetivo | Estado |
|---|---|---|
| E0 | Spec v0.2 | concluída como documento base |
| E1 | Projeto, identidade, carteira, dashboard, mapa, inspetor e assistente visual | primeira versão local implementada; QA visual em cinco larguras |
| E2 | Cadastro, leitura segura, snapshots e piloto LICIPUB | implementado e testado, inclusive junction Windows; rotina automática de cinco minutos |
| E3 | Catálogo, conversa e análise Jev sob demanda | busca local e persistência validadas; adaptadores IA testados com mock, sem chamada paga ou calibração |
| E4 | Evidências Codex e execução de produto | contrato, API, lista temporal e medidas implementados; instrumentação nos apps e captura desktop ainda não instaladas |
| E5 | MCP, skill e executor inicial | pacote pronto e contrato MCP validado; executor de inventário com revisão/recibo; instalação no host permanece separada |
| E6 | Segundo projeto sem regra no núcleo | mesmo núcleo validado em LICIPUB, DJANGO_LANDPAGE e SOCIAL_APP; migração integral da carteira ainda pendente |
| E7 | Critérios completos e QA final | QA da v0.1 registrada; conjunto completo AC-01 a AC-42 ainda não certificado |

O status aqui deve mudar apenas com evidência de execução/teste. Identidade aprovada e telas validadas são portões distintos.

Entrega local v0.1.0 em 30/09/2026: 31 testes, check e pip check aprovados; capturas e limitações em QA-v0.1.md. O banco de uso começa vazio para o usuário criar seu acesso. A base do piloto é separada.

Prioridades remanescentes da base: validar o MCP de consulta por conector no host escolhido; instrumentar um ponto real de produto com eventos; testar qualidade do Jev por critérios reais; parser de sequência explícita/condições e trace visual; diff de snapshots; plano de instalação/remapeamento e persistência de eventos; executores de produção por contrato. O MCP central local da v0.2 tem estado próprio abaixo. Não há atividade real dos apps inferida das fontes.

## Extensão central de trabalho v0.2 — 27/10/2026

A extensão está descrita em [HARNESS-CENTRAL.md](HARNESS-CENTRAL.md), com entrada
em `/central/` e desenho em `/central/como-funciona/`. Ela não substitui a
certificação pendente do conjunto completo de critérios da especificação base.

| Capacidade | Estado e limite |
|---|---|
| Contratos, contexto fixado e sete etapas | implementados com histórico, revisão, posse temporária e retomada; não significam delegação automática de subagentes |
| Checkpoints e recibos | autorrelato separado de verificação técnica; conferência humana por critério e aprovação final na sessão web |
| Observação Git | adaptador implementado; testes isolados cobrem gitdir externo e contagens; não verifica PR nem executa limpeza |
| Fila Codex | consultas reais concluídas em DJANGO_LANDPAGE e TIMBRE_DIGITAL; somente parecer contextual, sem implementação de código |
| Protocolo e isolamento Codex | sonda sem modelo e turnos reais confirmaram raiz correta, leitura e zero MCP disponível; 17 testes isolados dos adaptadores passaram |
| MCP central | smoke stdio real de listagem e contexto passou nos dois projetos; `enlace-central` instalado no host com allowlist só dos pilotos; novas ferramentas exigem nova sessão |
| Skills | `enlace-central` instalada em `.codex/skills/enlace-central` com hash conferido; skills de domínio continuam apenas referenciadas, sem migração |
| Persistência | backup validado e migração do SQLite realizados; disputa entre workers corrigida com timeout de 20s e transação IMMEDIATE; retomada real passou com workers ativos |
| Interface | 15 combinações de tela/largura em 1440, 390 e 320 px sem overflow ou erros; apresentação, foco e fallback sem JavaScript conferidos |
| Validação final | 106 testes passaram em cerca de 10s; sem novas migrações pendentes, system check e diff check limpos |

O piloto funcional concluiu as consultas reais ao modelo nos dois projetos,
verificou três critérios por tarefa, pausa/retomada e igualdade dos metadados
Git antes/depois. As duas tarefas estão em `review`, aguardando aprovação do
usuário: concluir o turno não concede aceite humano. Não houve executor de
produto, merge, deploy ou limpeza. Resultados, fontes e limites da revisão
visual estão em [QA-CENTRAL-v0.2.md](QA-CENTRAL-v0.2.md).

Evidência MCP de 27/10/2026 às 15:42:57 UTC: o smoke usou a configuração TOML
real instalada no host. `list_work_projects` retornou somente
os dois IDs autorizados, ambos com contrato revisão 1; `get_work_context`
retornou sete etapas por tarefa, sem `lease_token`. Foram chamadas apenas
ferramentas de leitura. Recibo local sanitizado em `.local/central-mcp-smoke.json`;
esse arquivo não contém tokens, prompts ou conteúdo dos projetos e não é versionado.
Seu campo `host_installed=true` corresponde à nova execução após a instalação
via `codex mcp add`, com leitura da configuração efetiva.
