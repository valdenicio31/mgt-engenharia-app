# Atualização MGT — versão 2 — 03/08/2026

## Ajustes aplicados

- inclusão de foto no cadastro de clientes e condomínios, com limite de 5 MB;
- exibição de miniatura da foto na listagem de condomínios;
- filtros por texto, cidade, bairro e situação de validação;
- dashboard com filtro de localização e agrupamento de condomínios por rua, bairro e cidade;
- botões e ações principais identificados com emojis;
- refinamentos visuais e de chamadas para ação na landing page de Autovistoria;
- nova migração `0011_client_photo.py`.

## Publicação

O `build.sh` já executa as migrações. Após enviar os arquivos ao GitHub, acompanhe o Auto-Deploy do Render e valide o cadastro e a exibição das imagens.
