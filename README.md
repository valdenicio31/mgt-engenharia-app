# MGT Engenharia — aplicação web de homologação

Entrega da Fase 22 que consolida o protótipo homologado em uma aplicação Django implantável no Render. O pacote contempla autenticação, painel, clientes, oportunidades, propostas, projetos, tarefas, RAT, auditoria e verificação de saúde.

## Execução local

Requer Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

Acesse `http://127.0.0.1:8000`. O endpoint `http://127.0.0.1:8000/health/` verifica aplicação e banco.

## Implantação no Render

1. Coloque esta pasta em um repositório privado no GitHub.
2. No Render, use **New > Blueprint** e conecte o repositório. O arquivo `render.yaml` será detectado.
3. Crie antes um PostgreSQL no Render, copie a **Internal Database URL** e informe-a na variável obrigatória `DATABASE_URL` do serviço.
4. Confirme o primeiro deploy e aguarde `/health/` retornar `status: ok`.
5. No **Shell** do serviço, execute `python manage.py createsuperuser` e depois `python manage.py seed_demo`.
6. Valide a URL temporária `*.onrender.com` antes de configurar o domínio.
7. Adicione `homologacao-mgt.viaiasolucoes.com` em **Settings > Custom Domains** e replique no DNS da HostGator apenas os registros mostrados pelo Render.

## Segurança

- Nenhuma senha ou chave real está neste repositório.
- `SECRET_KEY` é gerada no Render; `DATABASE_URL` é secreta e inserida no painel.
- HTTPS, cookies seguros, HSTS, CSRF e bloqueio de iframe estão ativados fora do modo local.
- O banco usa PostgreSQL no Render; SQLite existe apenas como conveniência local.
- O histórico inicial de criação de registros fica em `AuditLog`.

## Limites desta entrega

É um MVP para homologação controlada. Propostas e RATs são consultados na interface e administrados no `/admin/`. Antes da produção, executar teste de carga, política de backup/restauração, perfis de acesso por função, monitoramento e revisão LGPD.

Veja [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md) para o roteiro operacional.
