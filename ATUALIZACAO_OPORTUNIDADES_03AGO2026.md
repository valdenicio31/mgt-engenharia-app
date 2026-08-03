# Atualização - conversão de condomínios em oportunidades

## Melhorias incluídas

- Seleção individual ou de todos os condomínios na tela de clientes.
- Botão **Criar oportunidades** para conversão em lote.
- Título automático no padrão `Autovistoria — Nome do condomínio`.
- Etapa inicial `Lead`, valor estimado `R$ 0,00` e responsável igual ao usuário conectado.
- Proteção contra a criação repetida da mesma oportunidade para o mesmo condomínio.
- Registro da operação no log de auditoria.
- Preenchimento automático do título também no cadastro manual de oportunidades, mantendo o campo editável.

## Validação

- 28 testes automatizados executados com sucesso.
- Nenhuma migração de banco de dados é necessária.

## Instalação

Envie o conteúdo deste pacote para a raiz do repositório `mgt-engenharia-app`. O Render iniciará o Auto-Deploy após a atualização da branch principal.
