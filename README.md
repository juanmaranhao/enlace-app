# Enlace

Central local de projetos com carteira, arquitetura declarada, mapa interativo, fontes versionadas, busca de capacidades e análise sob demanda. A interface segue a direção Compacto aprovada; a especificação completa está em `docs/spec-central-projetos-v0.2.md` e o estado entregue em `docs/ROADMAP.md`.

## Primeiro acesso local

Python 3.12 e PowerShell no Windows. Este checkout já possui `.venv`, dependências e `.env` local com chaves de IA vazias.

```powershell
.\tools\local.ps1 -Action Start
```

Abra http://127.0.0.1:8766/primeiro-acesso/ e crie seu próprio usuário e senha. Essa rota só existe em modo local, para acesso loopback, enquanto não há nenhum usuário. Depois use **Vincular projeto**, escolha a pasta, revise a detecção e confirme. O cadastro não instala nada no projeto acompanhado. O banco inicial do usuário começa vazio; o piloto visual foi validado em banco QA separado.

```powershell
.\tools\local.ps1 -Action Status
.\tools\local.ps1 -Action Stop
```

O script lança servidor e dois workers em janelas ocultas. A parada confere caminho, comando, horário de criação e árvore dos processos próprios; preserva banco, projetos e histórico. Recibos e logs locais ficam em `.local/`, fora do Git. É um ambiente de desenvolvimento loopback, sem publicação ou serviço de inicialização automática do Windows.

Em um checkout novo, crie `.venv`, instale `requirements.txt`, copie `.env.example` para `.env` e defina uma `DJANGO_SECRET_KEY` aleatória. Não reutilize uma chave de outro projeto. Se o cache do pip travar no ambiente restrito do Codex, use `--isolated --no-cache-dir --keyring-provider disabled`.

## Acompanhamento atualizado

O worker de inventário relê projetos ativos a cada cinco minutos. **Atualizar leitura** solicita uma coleta antes desse intervalo. Mudança de conteúdo normalizado, relações ou cobertura gera snapshot novo; ausência de mudança preserva o snapshot e atualiza a data da verificação. O painel consulta o estado e mostra **Nova versão disponível**, preservando o mapa aberto até você decidir trocar de versão.

O acompanhamento exige o worker em execução. Após reiniciar, ele volta a verificar os projetos atrasados. Falha ou cancelamento exige uma atualização manual antes de retomar a rotina automática. Conteúdo de um snapshot permanece acessível mesmo quando o arquivo atual muda ou desaparece.

A leitura atual cobre documentos de governança da raiz, `.agents/skills/**/SKILL.md`, `.codex/agents/*.toml` e áreas autorizadas de `docs`. Detalhes em `docs/CONTRATOS.md`. Mudança apenas no código executável não recria automaticamente um fluxo; precisa ser refletida nas fontes declaradas ou aparecer nos eventos de um conector.

## Jev e conversa

Edite somente o `.env` do Enlace e reinicie os serviços:

```dotenv
JEV_IA=
JEV_API_URL=https://api.typesafe.ai/v1/systemone
JEV_MODEL=jev-1.13.0
OPENAI_API_KEY=
OPENAI_TEXT_MODEL=
```

`JEV_IA` permite avaliar critérios obrigatórios contra fontes selecionadas. O painel prepara o plano, mostra conteúdo, quantidade de chamadas e custo ainda desconhecido; o envio depende da autorização daquele plano. Mudança nas fontes, snapshot, acesso ou modelo bloqueia partes ainda não enviadas. Respostas recebidas ficam preservadas; interrupção incerta não provoca retry automático. As probabilidades são sinais experimentais, sem calibração de domínio e sem certificação de execução.

A busca do chat funciona sem chave. Para conversa livre, configure também o provedor de texto e marque **Conversa IA** na mensagem. Ele recebe pergunta, excertos autorizados e até seis turnos da própria conversa. Jev julga critérios; o provedor de texto redige a conversa. Abrir páginas, mapas ou o chat não chama IA. Os testes e o piloto não enviaram chamadas pagas.

## Pacote portátil

- `agentic_core/`: leitura e contratos sem Django ou regras particulares de um projeto.
- `integrations/enlace_client.py`: cliente e buffer opcional de eventos para integrar cada produto.
- `integrations/mcp_server.py`: MCP stdio para consultar a central pelo Codex.
- `integrations/skills/enlace-guide/`: skill de orientação com as mesmas fontes e IDs do painel.

Instalação e limites em `docs/INTEGRACOES.md`. O pacote não foi instalado automaticamente nos projetos ou na configuração global do Codex. Arquivos encontrados são evidência de arquitetura declarada; eventos, tempos e acionamentos exigem integração explícita.

## Verificação

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe manage.py test --settings=core.settings_test --noinput
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe -m pip check
```

O banco de testes é isolado e as credenciais dos provedores ficam desativadas. `tools/bootstrap_qa.py` prepara outro banco em `.local/qa.sqlite3`, com leitura do piloto; nunca substitui `db.sqlite3`. Evidências visuais e limites estão em `docs/QA-v0.1.md`.

Fora do modo local, PostgreSQL via `DATABASE_URL`, HTTPS e configuração operacional própria são obrigatórios. Não há deploy incluído nesta entrega.
