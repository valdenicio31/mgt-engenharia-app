# Correção de deploy — Migração da Consulta Autovistoria

## Erro corrigido

O deploy falhava no PostgreSQL com:

`django.db.utils.ProgrammingError: column "source" of relation "core_opportunity" already exists`

## Solução aplicada

A migração `0012_opportunity_autovistoria_consultation.py` agora:

- consulta as colunas existentes em `core_opportunity`;
- não tenta recriar a coluna `source` quando ela já existe;
- cria somente os campos da consulta de Autovistoria que estiverem faltando;
- atualiza normalmente o estado de migrações do Django;
- funciona em banco já existente e em instalação nova;
- preserva dados em eventual rollback.

## Publicação

Envie todo o conteúdo deste pacote ao repositório e faça um novo deploy no Render.
O `build.sh` já executa `python manage.py migrate` automaticamente.
