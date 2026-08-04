# MGT V1.0 RC2 — Clientes e oportunidades

## Alterações
- Origem abreviada na grade: **DM** (Digitado manualmente), **IP** (Importado por planilha/arquivo) e **ID** (Importado do Diário Oficial).
- Remoção do campo manual **Validar** da tela e do formulário.
- Nova situação comercial calculada automaticamente:
  - **DI** — Dados incompletos;
  - **AA** — Aguardando registro das infrações da Autovistoria;
  - **PO** — Pronto para gerar oportunidade;
  - **OP** — Oportunidade gerada.
- A geração de oportunidade agora exige cadastro completo e ao menos uma infração de Autovistoria ainda não vinculada.
- O campo legado `validation` foi mantido no banco para compatibilidade da versão 1.0, mas não é mais operado manualmente na interface.
