# Adoção do DJANGO_LANDPAGE

Checkpoint de 30/09/2026. Referência do checkout consultado: `7278a42d872d84e9f83b3e3aac058d4129ca9014`. Não houve alteração do template ou promoção de aprendizado.

Aplicados os princípios de apps proprietários de templates/CSS/JS, shell operacional compartilhado, disclosures, coordenação de diálogos e autorização no servidor. Referências: capacidades `painel-shell-operacional-v2` e `painel-core`; skills arquitetura-sistema, design-operacional, frontend-templates, frontend-css-design e frontend-js-dom. A aparência foi subordinada à direção Compacto aprovada pelo usuário, registrada em DESIGN_APROVADO.md e mockups/aprovados/compacto.md.

Especialização local: carteira de projetos, dois tipos de evidência, mapa com inspetor, análise de arquitetura e assistente. Módulos de marketing, textos de domínio e bancos do template não foram incorporados. Não há dependência de import ou link runtime ao DJANGO_LANDPAGE.

Desvio técnico deliberado: SQLite somente para a primeira instalação local e bancos de QA/testes. PostgreSQL via DATABASE_URL é obrigatório quando DEBUG=false. Manter ambiente loopback e workers leves permite validar o produto sem instalar serviços globais ou envolver produção dos projetos acompanhados.

Próximos padrões candidatos só devem ser promovidos após validação em uso: organização de fontes versionadas, atualização de mapa com preservação de contexto e julgamento por critério. A validação funcional desta versão não certifica esses padrões como universais nem autoriza gravar de volta no template.
