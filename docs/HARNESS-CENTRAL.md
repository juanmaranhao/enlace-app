# Central de trabalho — v0.2

O Enlace concentra o pedido, o contexto de cada projeto, as decisões comuns e o
acompanhamento das etapas. O projeto continua responsável por suas regras de
negócio, identidade, contratos e arquivos. A central fica em uma aplicação
separada; cadastrar um projeto não instala instruções nem modifica sua pasta.

Abra a [Central](/central/) para trabalhar e o [Cérebro da central](/central/como-funciona/)
para consultar ou apresentar o fluxo. No ambiente local padrão, os endereços são
`http://127.0.0.1:8766/central/` e `http://127.0.0.1:8766/central/como-funciona/`.

## O que esta versão faz

- Mantém contratos versionados por projeto e tarefas com objetivo, critérios de
  aceite, contexto fixado, sete etapas e histórico.
- Controla uma tarefa em execução por projeto, com revisão, posse temporária e
  retomada explícita. O controle vale para tarefas da central; não trava editores
  ou processos externos que estejam trabalhando na mesma pasta.
- Observa Git por consultas fechadas e registra metadados de conservação.
- Enfileira pareceres do Codex sobre o contexto fornecido, sem ferramentas de
  execução. Essa consulta não implementa código, executa testes ou produz mídia.
- Oferece um MCP local com ações limitadas de preparação e acompanhamento.

Os papéis do desenho — coordenador, arquitetura, especialista, revisor e
verificador — descrevem responsabilidades. A v0.2 não inicia automaticamente um
subagente diferente para cada papel. O trabalho de implementação segue no Codex
direcionado ao projeto, dentro das permissões reais daquele ambiente.

## Conhecimento comum e contrato específico

O pacote comum de `agentic_core/harness.py` reúne regras de contexto, escopo,
evidência, retomada e preservação, além de referências de skills por fluxo:
desenvolvimento (`coding`), imagem/vídeo (`media`) e pesquisa/diagnóstico (`audit`).
Sua versão atual é `central-1.0.0`. É conhecimento explícito versionado; não é
treinamento de rede neural nem uma memória que promove automaticamente tudo o
que aparece nas conversas.

Cada projeto tem um contrato com stack, restrições, comandos de validação
declarados, modo `guided` ou `read_only` e notas. A raiz autorizada é resolvida
pelo servidor. Os comandos são informação para planejar o trabalho; o contrato
não os transforma em comandos executáveis pela central. O modo guiado também
não concede permissão de escrita ao parecer contextual do Codex.

As regras locais continuam em seus projetos. O registro de contrato na central
resume a configuração necessária à coordenação. Divergências entre o pacote
comum e uma regra local exigem decisão explícita, sem sobrescrever o projeto.
Skills de domínio são referenciadas por nome; sua presença, versão e adequação
precisam ser verificadas no executor. Esta entrega não as migra nem duplica.
A skill específica de condução `enlace-central` foi instalada no host, conforme
o estado de integração abaixo.

Ao preparar uma tarefa, o Enlace fixa projeto, raiz, versão do contrato, pacote
comum completo e hashes das fontes canônicas autorizadas existentes:
`AGENTS.md`, `PROJETO.md`, `IDENTIDADE.md`, `docs/agentica/DOUTRINA.md`,
`docs/agentica/CODEX.md` e `docs/agentica/FLUXOS.md`. Não copia o conteúdo dessas
fontes para o contexto da tarefa. Uma mudança de contrato, raiz ou dessas fontes
bloqueia a continuidade dependente e requer nova tarefa com contexto revisto.
Publicar um pacote comum posterior preserva a versão fixada na tarefa anterior.

## As sete etapas

| Etapa | Responsabilidade | Registro esperado |
|---|---|---|
| Entender | Delimitar necessidade, projeto e critérios | Pedido compreendido |
| Validar a abordagem | Conferir decisões, alternativas e limites | Abordagem justificada |
| Planejar | Definir entregas, skills e verificações | Plano rastreável |
| Executar | Realizar o trabalho no projeto responsável | Entrega da etapa |
| Revisar | Comparar o resultado com a proposta | Revisão registrada |
| Validar | Relacionar evidências aos critérios de aceite | Critérios comprovados |
| Entregar | Apresentar resultado e próximos passos | Entrega para aprovação |

Preparar não inicia execução. Iniciar concede uma posse de 30 minutos, renovada
por checkpoints e pelo worker enquanto a consulta permanece ativa. Pausar revoga
a posse anterior. Retomar confere o contexto e concede uma nova geração; um
executor antigo não pode continuar registrando progresso com seu token anterior.
A revisão do registro impede atualizações de uma tela desatualizada. Chaves de
operação permitem reconhecer reenvio idêntico sem duplicar tarefas ou marcos.

O acompanhamento exige registros reais do executor ou do responsável. Não há
monitor semântico contínuo de todos os arquivos ou conversas do usuário. O fluxo
impede pular etapas e pede evidências, mas não torna verdadeiro um relato apenas
porque foi salvo.

## Evidência e aprovação

Um checkpoint manual registra o que foi relatado. Texto livre, referência
externa ou resposta do Codex permanecem `self_report`; escrever “teste passou”
não cria um recibo técnico. Uma observação Git mostra o estado consultado naquele
instante e não comprova critérios de produto.

A etapa Validar exige recibos da própria tarefa cobrindo todos os critérios:

- `verified_result`: resultado de um verificador técnico interno registrado,
  com origem, resultado e critérios. Não existe ferramenta genérica MCP para
  fabricar esse resultado; o chamador interno deve executar a verificação.
- `human_review`: conferência explícita dos critérios pela sessão web humana,
  com nota e responsável. Serve para registrar a avaliação feita pela pessoa e
  permanece marcada `technical_validation=false`.

A conferência humana não é um teste automatizado. O MCP não registra essa
conferência nem concede aprovação final. Após Entregar, a tarefa aguarda aprovação
no painel. Aprovar a entrega registra aceite; integração Git, deploy, publicação
de conteúdo e limpeza continuam estados independentes, sem execução implícita.

## Parecer Codex e observação Git

A ação de consulta coloca uma operação persistida na fila. O comando
`manage.py process_central` processa a fila; `tools/local.ps1 -Action Start`
inclui esse worker. Abrir páginas ou consultar o mapa não chama o modelo.
A consulta usa a autenticação da instalação Codex e pode consumir sua cota.

O worker envia objetivo, critérios, etapa, contrato e conhecimento fixado, junto
da observação Git disponível. O app-server é iniciado com raiz explícita,
sandbox de leitura, aprovações desabilitadas, sem shell, apps, plugins ou
delegação. Confirma fontes automáticas vazias e MCP indisponível antes do turno.
O parecer é contextual: não lê o código nem substitui revisão ou testes reais.
Thread e resultados são persistidos para retomada na mesma raiz e política.
Falha, interrupção e timeout têm estados próprios, sem repetição automática de
um turno cujo consumo ou efeito seja incerto.

**Aprendizado de governança:** `mcp_servers={}` pode manter conectores herdados
da configuração do host. A sonda real encontrou esse comportamento. O runner
enumera os nomes, reabre uma vez com cada servidor explicitamente desativado e
verifica zero ferramentas/recursos disponíveis. Estado ambíguo bloqueia o turno.
Direcionar o `cwd` ou usar sandbox de leitura, isoladamente, não garante ausência
de conectores nem impede leitura de segredos. Essas fronteiras precisam ser
conferidas novamente ao mudar o runtime; não são concedidas pelo desenho do fluxo.

O inventário Git informa HEAD, branch, alterações, não rastreados, ignorados,
flags ocultas do índice, worktrees e horário. Não lê conteúdo desses arquivos,
não faz fetch nem verifica PR. A recomendação é preservar; árvore limpa não
prova que uma pasta pode ser apagada. Não existe executor de cleanup nesta versão.
Detalhes de protocolo e limitações estão em [CODEX-EXECUTOR.md](CODEX-EXECUTOR.md).

## MCP local para trabalhar a partir da central

O pacote `integrations/central_mcp.py` oferece uma capacidade local limitada.
É separado do MCP de consulta por conector descrito em
[INTEGRACOES.md](INTEGRACOES.md). O host usa a `.venv` do Enlace e caminhos
absolutos. Em 27/10/2026, o MCP `enlace-central` foi instalado globalmente via
`codex mcp add`, com a allowlist limitada a DJANGO_LANDPAGE e TIMBRE_DIGITAL.
O smoke stdio posterior usou a configuração TOML instalada e confirmou a leitura
dos dois projetos e de seus contextos, sem expor token de posse.
As novas ferramentas exigem uma nova sessão do Codex para serem carregadas.

O processo recebe `ENLACE_OPERATOR` com o usuário ativo/staff da central e
`ENLACE_CENTRAL_PROJECT_IDS` com UUIDs separados por vírgulas. Só retorna projetos
ativos da lista explícita e acessíveis ao operador. Ações de condução ainda
exigem responsabilidade pelo projeto ou superusuário. Esses valores são
configuração local do processo, não argumentos que o modelo pode trocar numa
chamada. Esse MCP usa o banco local; não oferece autenticação remota nem endpoint
HTTP. Ter acesso à configuração do processo no host faz parte de sua confiança.

| Ferramenta | Capacidade |
|---|---|
| `list_work_projects` | Consultar projetos autorizados, contratos e pacote comum |
| `prepare_work` | Preparar tarefa idempotente com critérios e fluxo |
| `get_work_context` | Recuperar estado, revisão e evidências |
| `start_work` | Iniciar e receber token da posse corrente |
| `pause_work` | Pausar e revogar a posse anterior |
| `resume_work` | Revalidar contexto e receber nova posse |
| `record_work_checkpoint` | Registrar a etapa corrente com revisão e token válidos |

Ler contexto não concede token novo. Não há ferramenta de shell, merge, deploy,
limpeza, conferência humana ou aprovação final nesse servidor. A skill portátil
está em `integrations/skills/enlace-central/SKILL.md`. Sua cópia global em
`.codex/skills/enlace-central` foi instalada e teve o hash conferido. Isso não
migra as skills dos projetos nem instala executores de produto.

## Roteiro de uso e piloto

1. Na Central, escolha o projeto e publique seu contrato. Para o piloto, use
   DJANGO_LANDPAGE e TIMBRE_DIGITAL como alvos distintos, com critérios próprios.
2. Prepare a tarefa com um objetivo verificável. Confira o contexto e inicie.
3. Registre a abordagem e o plano. Se necessário, solicite parecer contextual
   do Codex; acompanhe sua operação e trate a resposta como orientação.
4. Execute o trabalho autorizado no projeto correto, revisando e registrando
   cada etapa com suas evidências. Observe Git para registrar retenção.
5. Na validação, associe recibos reais aos critérios. Registre no painel apenas
   a conferência humana que efetivamente ocorreu.
6. Entregue para aprovação, mantendo os próximos passos de integração, deploy
   e conservação explícitos. Ao retomar, consulte o estado antes de repetir ações.

O SQLite local existente continua sendo o banco de uso; a implementação adiciona
as tabelas da central por migração, preservando carteira, usuários e histórico.
Bancos de QA permanecem separados. Não há troca por dados de demonstração,
reset da base ou instalação automática nos projetos acompanhados.

O backup da base foi validado antes da migração. A disputa observada entre
transações dos workers foi corrigida com `timeout=20` e
`transaction_mode=IMMEDIATE` nas opções SQLite. A reserva de escrita acontece
no início da transação; a retomada real passou com os workers ativos. Isso
coordena o uso local atual, sem transformar SQLite em uma plataforma de execução
distribuída.

Nos dois pilotos, o Codex concluiu consultas reais com raiz correta, sandbox de
leitura e zero MCP disponível. Metadados Git permaneceram iguais antes/depois;
pausa e retomada foram verificadas. Cada tarefa comprovou seus três critérios
do piloto e está em `review`, aguardando aprovação do usuário. A evidência de
igualdade dos metadados não é uma comparação byte a byte de todos os arquivos.
Consulte os recibos e os limites em [QA-CENTRAL-v0.2.md](QA-CENTRAL-v0.2.md).

Aprendizados reutilizáveis devem ser revistos e promovidos ao pacote comum com
versão e justificativa; exceções continuam no contrato do projeto. O histórico
permite essa revisão, mas a v0.2 não promove regras automaticamente. O estado
dos testes e dos pilotos é registrado em [ROADMAP.md](ROADMAP.md), separado das
capacidades implementadas neste guia.
