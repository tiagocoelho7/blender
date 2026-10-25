# GitHub Master — Adaptação de infraestrutura para monorepositório Blender

**Estado:** pacote preparado para importação em branch Git, NÃO importado, NÃO homologado.

## Caminho de destino

`tiagocoelho7/blender/addons/blender-dedup/`

Os 34 arquivos do kit `BLENDER_DEDUP_V102_TEST1_CODEX_CLOUD_2026-10-23.zip` foram copiados sem alterações. Confira os 34 hashes em `GITHUB_MASTER_IMPORT_MANIFEST.json`.

## Exceção à documentação original

`README_COMECE_AQUI.md` foi escrito para um repositório **privado e exclusivo**. O proprietário escolheu posteriormente um monorepositório `blender` **público**. Essa mudança afeta SOMENTE o caminho de trabalho e a visibilidade, não autoriza alteração dos arquivos congelados nem qualquer etapa técnica adicional.

Ao usar o Codex Cloud, o GitHub Master deve delimitar a tarefa a `addons/blender-dedup/` e exigir que nenhuma outra pasta de plugin seja modificada. O arquivo `AGENTS.md` original, agora dentro desta pasta, contém restrições de escopo técnico que permanecem em vigor.

## Limites de autorização

- Este ZIP é material de *staging*, não constitui aprovação de publicação no GitHub, release ou desenvolvimento.
- Não executar scripts Blender ou `bpy` real. Não abrir arquivos `.blend` de produção.
- Não alterar `handoff/`, `CONGELADOS/`, `ORIGINAIS/`, a v1.0.1 ou os manifests.
- O HOLD técnico da v1.0.1 permanece. A v1.0.2-test1 só poderá ser desenvolvida pelo executor após autorização do Master Técnico.
- Registrar publicação pública somente após revisão e autorização do proprietário; não há garantias absolutas de ausência de informação privada em conteúdos históricos de auditoria.

## Passos esperados após aprovação do proprietário

1. Criar branch de importação a partir da `main` protegida do monorepositório Blender.
2. Colocar o conteúdo deste ZIP na raiz do checkout, preservando a estrutura `addons/blender-dedup/`.
3. Executar a validação de hashes: `cd addons/blender-dedup && python verificar_kit.py`.
4. Conferir que o diff adiciona somente a pasta `addons/blender-dedup/`; criar Pull Request, sem merge automático.
5. Após o gate de infraestrutura e autorização do Master Técnico, criar tarefa Codex focada na pasta e seguindo `PROMPT_CODEX_CLOUD.md` com caminhos relativos ajustados.
