# Atualização MGT — Fluxo de Autuações e Ordenação de Clientes

## Fluxo implantado
1. O Diário Oficial importa os condomínios notificados.
2. O MGT tenta vincular automaticamente a publicação a um condomínio já cadastrado.
3. Na visão de clientes, o usuário abre **Autovistoria**.
4. Os dados do endereço são preparados para consulta no portal oficial.
5. Cada autuação encontrada é cadastrada separadamente.
6. O mesmo condomínio pode possuir várias autuações.
7. O MGT bloqueia repetição do mesmo número de autuação para o mesmo condomínio.
8. As autuações são vinculadas à publicação do Diário Oficial e à oportunidade comercial.
9. Uma oportunidade de origem **Autovistoria Rio** é criada ou atualizada para contato por WhatsApp/e-mail.

## Visão de clientes
- Ordenação clicável por condomínio, rua, bairro, processo, notificação e atualização.
- Ordem padrão: rua, bairro e nome do condomínio.
- Os filtros atuais são preservados ao ordenar.
- Rua e bairro agora aparecem em colunas próprias.

## Banco de dados
Executar `python manage.py migrate` durante o deploy.
A migração `0013_autovistoria_infraction_and_gazette_client.py` cria a tabela de autuações e o vínculo opcional entre publicação e cliente.
