# Contratos do pacote v0.1

## Inventário v2

O núcleo recebe uma raiz autorizada e produz fontes, nós, relações, digest e cobertura. Toda fonte tem caminho relativo, ID estável por caminho, texto sanitizado e SHA-256 do texto normalizado em LF. Fluxos usam ID por caminho/título, com distinção de títulos repetidos. Relações são referências documentais; não representam execução ou dependência causal medida. O hash também inclui versão do parser, nós e relações.

Catálogo: AGENTS.md, CODEX.md, DOUTRINA.md, FLUXOS.md, PROJETO.md, IDENTIDADE.md, README.md e DESIGN_APROVADO.md na raiz; `.agents/skills/**/SKILL.md`; `.codex/agents/*.toml`; Markdown em `docs/{agentica,arquitetura,fluxos,contratos}/`; documentos `docs/arquitetura-*.md`. Fora disso não há coleta. `.env`, banco, anexos, mídia, Git, dependências e código de produto ficam excluídos.

Raiz canônica é resolvida antes do cadastro. O leitor confere também o destino do handle aberto no Windows, antes de ler; traversal e escapes de symlinks/junctions são recusados. Diretórios de links não são percorridos. Até 256 KiB por arquivo, 1.800 arquivos e 8 MiB por inventário; fontes recusadas e limites aparecem como cobertura parcial. Não há prova de completude sobre arquivos fora deste catálogo.

Captura é feita arquivo a arquivo, sem bloquear edições no projeto observado. Ela preserva precisamente os textos capturados, mas não é uma transação sobre todo o checkout. Não há hash de commit validado, resolução de herança global de skills ou análise AST nessa versão. Uma mudança é percebida na próxima coleta; os projetos observados não recebem modificações.

## Eventos v1

Campos: `schema_version=1`, `external_id`, `channel`, `event_type`, `name`, `occurred_at` com fuso e `details`. Canal `codex` ou `product`, fixado pela credencial do conector. Tipos: source_read, self_report, tool_run, verified_result, provider_started, provider_finished, provider_failed. Autorrelato não vira resultado verificado.

Metadados permitidos: trace_id, parent_id, node_id, snapshot_digest, duration_ms, wait_ms, attempt, result, input_tokens, output_tokens, usage_uncertain e evidence_ref. Referências são IDs, não conteúdo. Campos desconhecidos, prompts e chaves são recusados; métricas devem ser finitas e não negativas. Valores temporais ausentes são desconhecidos, nunca zero.

Até 100 eventos por lote, transação completa e deduplicação por projeto/canal/external_id. Reenvio idêntico é aceito sem duplicar; reenvio divergente recusa o lote. Horários podem chegar fora de ordem. O remetente define o grau de evidência: essa versão não valida automaticamente o artefato apontado por evidence_ref nem comprova que um nó existe no snapshot informado.

Gargalos mostram amostras dos últimos 1.000 eventos terminais do produto, medianas de duração/espera e contagens de falha/consumo incerto. Não somam paralelismo, calculam caminho crítico ou alegam causalidade. A tela de execução é uma lista temporal de até 100 eventos; árvore visual completa de traces permanece futura.

## Análises e ações

Plano Jev versionado com objetivo, até seis critérios obrigatórios e seis fontes, requests integrais por fonte, modelo, bytes, número de chamadas e hash. Nenhum corte silencioso: limite estrutural exige outro escopo. Opções supported/partial/absent/unknown e probabilidades são validadas; apoio a todos os critérios obrigatórios é separado da completude do envio. Limiar de triagem ainda experimental, sem calibração.

Cada parte registra estado antes do HTTP; respostas anteriores são preservadas. Erro estrutural não vira retry; timeout/resposta inválida deixa consumo incerto. A recuperação desta versão encerra o run interrompido como incerto, permitindo preparar um novo plano após verificar o fornecedor. Não há retomada automática do saldo de partes nem preço monetário validado.

Executor único `inventory-refresh-v1`: prepara leitura da pasta vinculada, snapshot e efeitos esperados. Confirmação por hash e permissão do responsável; reenvio do mesmo plano retorna o job existente. Recibo registra fila/progresso/resultado. Não existe executor genérico, shell remoto, produção de site ou vídeo habilitada pela busca.

## Dependências e acesso

`agentic_core` não importa Django, projetos ou fornecedores. Apps Django persistem dados; adaptadores usam esses serviços. Cada projeto tem dono e leitores. Views staff + autorização de projeto; ações de escrita do projeto dependem do responsável. Sessão web não substitui Bearer na API de conectores. Tokens são armazenados como hash e revogados no painel.

Integrações têm IDs de projeto/snapshot/nó, fontes relativas e schema público. A configuração de raiz e credenciais pertence à instalação. Portabilidade atual consiste no núcleo e pacote de conectores, validados com três projetos; importação/exportação de toda a carteira e remapeamento assistido permanecem no roadmap.

Documentação técnica consultada em 30/09/2026: [TypeSafe API](https://docs.typesafe.ai/api), [Choice](https://docs.typesafe.ai/primitives/choice), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/get-started/).
