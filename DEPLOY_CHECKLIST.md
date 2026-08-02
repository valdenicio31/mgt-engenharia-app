# Checklist de implantação controlada

## 1. Repositório

- [ ] Criar repositório privado `mgt-engenharia-app`.
- [ ] Enviar somente os arquivos deste pacote; confirmar que `.env` não foi incluído.
- [ ] Proteger a branch principal e registrar Márcio como aprovador, se aplicável.

## 2. Render

- [ ] Criar PostgreSQL de homologação e guardar a Internal Database URL.
- [ ] Criar Blueprint a partir do repositório.
- [ ] Informar `DATABASE_URL` como segredo.
- [ ] Confirmar que `SECRET_KEY` foi gerada automaticamente.
- [ ] Validar build, migrations e endpoint `/health/`.
- [ ] Criar superusuário e carregar dados demonstrativos.

## 3. Homologação

- [ ] Login e logout.
- [ ] Cadastro de cliente, oportunidade, projeto e tarefa.
- [ ] Visualização de propostas e RATs.
- [ ] Painel, progresso e navegação móvel.
- [ ] Registro criado no log de auditoria.

## 4. Domínio

- [ ] Cadastrar `homologacao-mgt.viaiasolucoes.com` no Render.
- [ ] Copiar exatamente os registros DNS informados pelo Render para a HostGator.
- [ ] Aguardar propagação e validar certificado HTTPS.
- [ ] Manter `mgt.viaiasolucoes.com` reservado para produção.

## 5. Antes da produção

- [ ] Aprovar perfis e permissões por papel.
- [ ] Definir retenção, backup e teste de restauração.
- [ ] Realizar testes de segurança, carga e recuperação.
- [ ] Revisar aviso de privacidade, base legal e retenção LGPD.
- [ ] Obter aceite formal do go-live.
