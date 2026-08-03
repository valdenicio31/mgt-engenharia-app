# Atualização MGT — Consulta de Autovistoria

## Novidades

- Botão **🔎 Autovistoria** na lista de clientes/condomínios.
- Tela com os dados do imóvel preparados para consulta no portal da Prefeitura.
- Botão para copiar logradouro, número, complemento, bairro e comunicado.
- Abertura do portal oficial em nova aba.
- Registro do resultado da consulta como oportunidade vinculada ao cliente.
- Controle de duplicidade por cliente e número do comunicado.
- Armazenamento da origem, situação, observações, endereço consultado, link e data da consulta.

## Observação operacional

O código de segurança do portal deve ser preenchido manualmente. A atualização não tenta contornar CAPTCHA nem mecanismos de proteção do portal público.

## Publicação

Após substituir os arquivos no repositório e publicar no Render, execute as migrações:

```bash
python manage.py migrate
```
