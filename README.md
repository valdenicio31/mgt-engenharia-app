# MGT Engenharia — aplicação web de homologação

Entrega da Fase 22 que consolida o protótipo homologado em uma aplicação Django implantável no Render. O pacote contempla autenticação, painel, clientes, oportunidades, propostas, projetos, tarefas, RAT, auditoria e verificação de saúde.

## Atualização de 03/08/2026

- alteração e exclusão com confirmação em clientes, oportunidades, propostas, projetos e tarefas;
- exportação das bases em Excel, CSV, XML e texto;
- comunicação da oportunidade por e-mail, WhatsApp ou carta pronta para impressão/PDF;
- cadastro e acompanhamento completo de propostas;
- campos e situações de projetos e tarefas traduzidos para português;
- pesquisa do Diário Oficial por data inicial e final, limitada a 31 dias;
- trilha de auditoria para inclusão, alteração e exclusão.

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

## Atualização automática no Windows

1. Extraia o pacote completo em uma pasta.
2. Clique duas vezes em `ATUALIZAR_MGT.bat`.
3. Na primeira execução, o Git poderá abrir o navegador para autorizar a conta do GitHub.
4. O atualizador baixa o repositório, compara os arquivos, cria o commit e envia a atualização.
5. Ao concluir, o painel do Render é aberto para acompanhar o deploy.

O atualizador não armazena senha nem token e gera um arquivo de log ao lado do pacote caso algo impeça o envio.

Se o Git precisar de autenticação, o Gerenciador de Credenciais abrirá o navegador. Mensagens de progresso do Git são registradas no log sem interromper a atualização.

## Segurança

- Nenhuma senha ou chave real está neste repositório.
- `SECRET_KEY` é gerada no Render; `DATABASE_URL` é secreta e inserida no painel.
- HTTPS, cookies seguros, HSTS, CSRF e bloqueio de iframe estão ativados fora do modo local.
- O banco usa PostgreSQL no Render; SQLite existe apenas como conveniência local.
- O histórico inicial de criação de registros fica em `AuditLog`.

## Limites desta entrega

É um MVP para homologação controlada. Propostas e RATs são consultados na interface e administrados no `/admin/`. Antes da produção, executar teste de carga, política de backup/restauração, perfis de acesso por função, monitoramento e revisão LGPD.

Veja [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md) para o roteiro operacional.

## Padrão dos cadastros

- Cadastros com tabela devem oferecer importação e exportação em XLSX, CSV, TXT e XML.
- Antes de incluir registros importados, deve ser feita análise de duplicidade usando os identificadores próprios da entidade.
- Para clientes e condomínios, a prioridade é: processo + notificação, CNPJ/CPF e nome + endereço.
- Usuários podem complementar foto, telefone, data de nascimento e endereço em **Meu cadastro**.
