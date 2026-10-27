# Enlace

Central local para entender, coordenar e acompanhar a arquitetura agêntica de vários projetos. O usuário principal administra uma carteira de aplicações, escolhe a pasta de cada uma, vê regras, skills, contratos e fluxos em um mapa, examina evidências e conduz tarefas com objetivo e critérios de aceite.

O núcleo de leitura e os contratos são independentes de cada projeto. Adaptadores acrescentam particularidades sem inserir condicionais de LICIPUB, SOCIAL_APP ou DJANGO_LANDPAGE nas views comuns. O Enlace concentra regras comuns versionadas; identidade, negócio e exceções pertencem ao projeto. Skills de domínio são referenciadas, sem cópia ou instalação automática. Alterar um projeto exige execução autorizada naquele ambiente; a central não amplia as permissões do agente.

Na v0.2, cada tarefa fixa raiz, contrato, pacote comum e hashes das fontes canônicas. Sete etapas organizam entendimento, decisão, plano, execução, revisão, validação e entrega. Revisão e posse temporária protegem continuidade; checkpoints persistem o progresso relatado. Os papéis do fluxo não significam que subagentes autônomos foram iniciados.

O trabalho dominante é **Operar** na central, carteira, dashboard, mapa e análises; a fonte detalhada é **Ler**. Não há site público ou módulo de marketing. Desenvolvimento no Codex e execução dentro dos apps têm o mesmo peso, mas origens de evidência distintas. A entrada operacional fica em `/central/` e o desenho de consulta em `/central/como-funciona/`.

O produto responde com a informação efetivamente descoberta. Arquivo presente é arquitetura declarada, não prova de invocação. Ausência de evento pode significar conector indisponível. O assistente localiza capacidades e fontes; avaliação Jev e conversa livre exigem suas conexões próprias. A consulta Codex enfileirada analisa somente o contexto fornecido, sem ferramentas de execução: seu parecer é autorrelato, não implementação ou teste aprovado.

Recibos técnicos e conferência humana na sessão web têm origens distintas. Aprovar entrega não confirma integração, deploy ou limpeza. O observador Git consulta metadados e recomenda retenção; não apaga worktrees ou arquivos. O MCP local da central limita suas ações ao operador e aos projetos explicitamente configurados, sem shell ou aprovação humana genérica.

O destino inicial é local. Credenciais ficam no `.env` do Enlace, separado dos apps. O SQLite existente preserva usuários, carteira e histórico ao receber migrações da central. A especificação base e os critérios AC-01 a AC-42 permanecem em `docs/spec-central-projetos-v0.2.md`; `docs/ROADMAP.md` indica o que já foi validado. O funcionamento e os limites da central estão em `docs/HARNESS-CENTRAL.md`.
