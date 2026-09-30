# Evidências da primeira versão local

Data: 30/09/2026. Python 3.12.14, Django 6.0.8, MCP SDK 2.2.0. Ambiente Windows, banco de teste em memória e banco de UI separado em `.local/qa.sqlite3`. Credenciais de IA desativadas em ambos. Não houve chamada paga ou evento de execução fabricado no piloto.

## Verificações automatizadas

31 testes passaram com `manage.py test --settings=core.settings_test --noinput`. Cobrem cadastro com confirmação, raiz canônica, segredo excluído, traversal/tamanho/junction real no Windows, snapshots imutáveis e normalização, recorte correto do fluxo, aviso de versão, cancelamento, CSRF, fontes escapadas e isolamento de acesso.

Incluem avaliações sob demanda, fonte alterada antes da atualização do inventário, permissão revogada, idempotência e consumo incerto sem retry; conversa com histórico e revogação de escopo; contrato HTTP estruturado com transporte mockado, rejeição de citação inexistente e resposta incompleta; eventos fora de ordem, reenvio divergente, autenticação Bearer e revogação; tarefa com plano/hash/recibo; falha da central sem bloqueio em emit; descoberta e chamadas MCP com SDK real em memória.

`check`, verificação de migrações sem diferença e `pip check` passaram. A skill enlace-guide passou pelo quick_validate oficial com UTF-8. O teste de provider verifica o contrato, sem comprovar disponibilidade, qualidade semântica ou preço de uma chamada real.

## Piloto somente leitura

| Projeto | Fontes capturadas | Fluxos detectados | Eventos de produto |
|---|---:|---:|---|
| DJANGO_LANDPAGE | 46 | 15 | nenhum conector instalado |
| LICIPUB | 10 | 1 | nenhum conector instalado |
| SOCIAL_APP | 5 | 0 | nenhum conector instalado |

Essa quantidade corresponde ao catálogo autorizado, não a uma auditoria de todos os arquivos do projeto. O mesmo núcleo coletou os três sem condicionais por nome ou import de seus módulos. ZERO fluxos no SOCIAL_APP significa ausência de fluxo detectado neste recorte; não ausência de automações no produto.

## Interface em navegador

Carteira, mapa, análise e revisão de plano foram verificados em larguras CSS medidas de 1440/1024/768/390/320 px, sem overflow horizontal da página. Seleção de pasta, revisão de detecção e fontes reais foram exercitadas; o cadastro duplicado não foi confirmado novamente no banco QA.

Mapa: seleção destaca vizinhos, apoio recolhido, zoom, abas Elemento/Fluxo, fonte e retorno preservando seleção/zoom/apoio. Escape fecha, remove bloqueio de rolagem e devolve foco a Detalhes. Abertura do chat a partir do inspetor mantém somente um dialog aberto e fecha com retorno ao disparador externo. Inspetor e chat foram vistos em 390×660 CSS com conteúdo contido. Console sem erros/warnings na verificação.

Busca local “Como criar um site?” retornou referências reais do DJANGO_LANDPAGE com links para mapa, fonte e avaliação. Cada fluxo retorna o próprio trecho, evitando reutilização de todo FLUXOS.md. Revisão Jev mostrou duas chamadas e textos selecionados; botão de envio permaneceu desativado sem chave. As figuras estão em `docs/evidencias/` e foram capturadas do app, não do mockup.

Larguras da interface foram medidas no DOM. Capturas desktop usam viewport que cabe na janela do host, para evitar cortes do screenshot em larguras maiores que a tela física. Não foi feito teste em aparelho físico, leitor de tela ou em todos os motores de navegador.

## Serviços locais

O script local foi exercitado em partida/parada/reinício/status. O servidor respondeu `/healthz/` com status ok após consultar o banco. Os workers de inventário e análises permaneceram ativos, com recibos dos launchers e filhos Python; a parada verificou toda a árvore própria. Acesso ao inventário de processos exigiu execução fora do sandbox do Codex; a versão normal do PowerShell do usuário não usa essa restrição do agente.

O banco inicial de uso continua sem usuário/projetos. A criação de acesso é oferecida em loopback; o usuário cadastra sua senha e vincula os projetos desejados. Não há deploy, tarefa agendada, instrumentação instalada nos apps ou observação completa do Codex desktop.

## Limites ainda abertos

Mapa mostra relações documentais; sequência condicional completa e rastros visuais de execução ainda não estão implementados. Jev possui contrato testado e rubrica experimental, sem benchmark de qualidade. Conversa IA exige provedor de texto separado; citações são verificadas por ID/trecho, sem validação semântica automática. Buffer de eventos é memória, sem spool persistente.

A spec tem 42 critérios e continua sendo alvo de evolução. Esta evidência não declara todos atendidos. Plano de instalação/remapeamento de carteira, conectores globais, import de sessões desktop, executores de produção, diff visual entre versões e benchmark de recuperação permanecem futuros.
