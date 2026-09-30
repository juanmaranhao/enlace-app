# Estado de implementação

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

Prioridades seguintes: validar a integração MCP no host escolhido; instrumentar um ponto real de produto com eventos; testar qualidade do Jev por critérios reais; parser de sequência explícita/condições e trace visual; diff de snapshots; plano de instalação/remapeamento e persistência de eventos; executores de produção por contrato. Não há atividade real dos apps inferida das fontes.

