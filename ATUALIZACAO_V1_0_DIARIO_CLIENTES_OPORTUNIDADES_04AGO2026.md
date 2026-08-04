# MGT V1.0 — Atualização 04/08/2026

## Ajustes incluídos
- Pesquisa no Diário Oficial cria automaticamente o condomínio em Clientes.
- Geração automática de oportunidade na etapa Lead.
- Controle de duplicidade por processo + notificação e reaproveitamento do cadastro existente.
- Campo Origem do cadastro: Digitado manualmente, Importado por arquivo ou Importado do Diário Oficial.
- Coluna Origem disponível na grade de Clientes e nos filtros.
- Publicação do Diário Oficial fica vinculada ao cliente e à oportunidade.

## Instalação
1. Faça backup do banco e da pasta atual.
2. Substitua os arquivos da aplicação pelos deste kit.
3. Instale dependências: `pip install -r requirements.txt`.
4. Execute: `python manage.py migrate`.
5. Execute: `python manage.py collectstatic --noinput`.
6. Reinicie o serviço web.
7. Acesse Diário Oficial, pesquise um período e valide Clientes e Oportunidades.
