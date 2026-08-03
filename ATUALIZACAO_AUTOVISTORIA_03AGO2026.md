# Atualização — Autovistoria e importação otimizada — 03/08/2026

## Entregas

- Landing page pública em `/autovistoria/` e compatibilidade com `/apresentacao/`.
- Logotipo MGT no início e conteúdo comercial focado em autovistoria predial.
- Formulário completo para orçamento, com consentimento LGPD.
- Criação automática de cliente e oportunidade na etapa Lead.
- Título automático `Autovistoria — nome do condomínio`.
- Aviso para `mgtengenharia@ia.com.br` e continuidade pelo WhatsApp `(21) 97516-4643`.
- Registro da origem como Landing Page, com data e hora.
- Importador otimizado com análise de duplicidade em memória e gravação em lotes.
- Compatibilidade com datas no formato `2026-07-01 04:00:00`.

## Render

O `build.sh` executa as migrações automaticamente. Após publicar os arquivos no GitHub, aguarde o Auto-Deploy concluir.

Variável opcional no Render:

`MGT_LEAD_NOTIFICATION_EMAIL=mgtengenharia@ia.com.br`
