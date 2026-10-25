# Blender Dedup — Kit inicial para Codex Cloud

**Missão:** desenvolver exclusivamente offline uma candidata NOVA `v1.0.2-test1` para o script de remoção de duplicatas no Blender. A v1.0.1 está em HOLD; não está autorizada para uso real. Este repositório é um laboratório de código, **não** contém qualquer `.blend` de produção.

## Começo rápido — Codex Cloud

1. Extraia ESTE ZIP em uma pasta temporária. O conteúdo extraído (inclusive `AGENTS.md`, `PROMPT_CODEX_CLOUD.md` e `handoff/`) deve ser a RAIZ de um **repositório privado e dedicado** do GitHub. Não suba o ZIP como único arquivo do repositório: disponibilize os arquivos internos para leitura do Codex.
2. No Codex Cloud (web ou aplicativo), crie/seleciona um ambiente de nuvem apontado para esse repositório e publique o ambiente, conforme as opções disponíveis na sua conta.
3. Crie uma tarefa no ambiente, preferencialmente no modo de **código**, e cole o conteúdo de `PROMPT_CODEX_CLOUD.md` (também disponível como arquivo separado fora do ZIP).
4. O Codex deve trabalhar **somente na própria área de trabalho da nuvem**, numa branch isolada, sem acesso a diretórios locais do Mac, sem Blender e sem arquivos `.blend` do proprietário.
5. Ao terminar, exporte o ZIP MASTER de entrega gerado pelo Codex, ou obtenha os arquivos pelo Git/PR para revisão. Não faça merge na branch principal antes da auditoria independente.

Se a interface da sua conta permitir anexar um ZIP diretamente **como material da tarefa e torná-lo acessível ao agente**, pode anexar este pacote em vez de publicá-lo no repositório; certifique-se de que o Codex pode efetivamente ler os arquivos. Se não existir tal opção, use o repositório privado.

## Índice

- `PROMPT_CODEX_CLOUD.md` — instruções iniciais completas.
- `AGENTS.md` — restrições permanentes de execução e alterações.
- `handoff/04_PROMPT_EXECUTOR.md` — contrato técnico original e detalhado.
- `handoff/03_PLANO_DE_CORRECOES.md` — 7 frentes MC01–MC07.
- `handoff/01_PARECER_MASTER.md` — por que v1.0.1 permaneceu HOLD.
- `handoff/CONGELADOS/` — baselines intactas, especificação e diff.
- `handoff/ORIGINAIS/` — os dois resultados originais A e B (ZIPs, não alterar).
- `handoff/EVIDENCIAS_MASTER/` — reexecuções já existentes.
- `handoff/MANIFESTO.json` e `handoff/SHA256SUMS.txt` — custódia original.
- `MANIFESTO_CODEX_SHA256.txt` — hashes deste KIT Codex; pode ser conferido com `verificar_kit.py`.

**Nota:** nenhum dos resultados anteriores é homologação do código para Blender 5.0.0 real. Só os auditores independentes e o Master decidem sobre a próxima fase.
