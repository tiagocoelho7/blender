# Tarefa Codex Cloud — Blender Dedup v1.0.2-test1

Atue como **DESENVOLVEDOR técnico** do Blender Dedup, em um ambiente **Codex Cloud isolado**, não como auditor do próprio trabalho.

Leia primeiro `AGENTS.md`, depois `handoff/00_LEIA_PRIMEIRO.md`, `handoff/01_PARECER_MASTER.md`, `handoff/02_MATRIZ_CONSOLIDADA.md`, `handoff/03_PLANO_DE_CORRECOES.md` e execute integralmente o contrato de `handoff/04_PROMPT_EXECUTOR.md`. Examine os relatórios, testes e contraprovas nos ZIPs A/B em `handoff/ORIGINAIS/`; não dependa apenas dos resumos.

**Objetivo:** criar uma candidata **nova e separada** chamada `v1.0.2-test1`, corrigindo MC01–MC07 da v1.0.1: TOCTOU/mutação e reentrância; referências textuais/IDProps/aliases; memória de topologias degeneradas; deadlines internos; modo do objeto preservado (KEEP); coerência de `user_map`; ledger de decisão e falhas parciais.

**Contrato funcional inalterável:** localizar objetos `MESH` duplicados de todo o `.blend`, mesmo em collections/cenas diferentes, por equivalência da geometria e topologia originais, independente de ordem de vértices/arestas/faces, posição/rotação/escala, materiais, UVs, modifiers e shape keys. Precisão de 5 casas decimais. Preservar mais modifiers; desempate por shape keys; depois critério determinístico. Ignorar animação como preferência. Malhas alteradas destrutivamente em sua geometria/topologia não são duplicatas. Exclusão automática somente depois de preflight seguro, sem pedir confirmação e sem salvar o arquivo automaticamente.

**Limites e segurança:** NÃO acessar meu Mac nem pastas locais. NÃO executar Blender real, `bpy` real, nem ler, criar, modificar ou remover arquivos `.blend`. NÃO alterar qualquer arquivo em `handoff/` ou em `CONGELADOS/` e `ORIGINAIS/`. NÃO usar Work. Execute somente testes sintéticos em Python e cópias descartáveis, sem serviço externo. Não instalar nem habilitar o script em Blender real, não fazer merge na principal nem declarar GO de produção.

**Provas de aceitação:** reproduza as regressões 57/57, 266/266, 2649/2649, 32/32, oráculos A 400/400 e B 160/160 (ou documente substituto rigorosamente equivalente); inverta os testes adversariais que antes demonstravam insegurança, com atenção a mutação em callbacks, acessos indiretos, NaN, prazos e falha de `remove`/logger. Se alguma suíte não puder ser reconstruída dos materiais recebidos, indique precisamente quais arquivos faltam e quais testes realmente foram executados — não invente resultados. Qualquer incerteza antes da primeira remoção = **zero exclusões**; erro depois = parar e produzir ledger honesto, sem alegar rollback.

**Entregáveis:** novo `.py` e SHA-256; diff v1.0.1→v1.0.2-test1; testes, logs e comandos para replay; matriz MC01–MC07 com provas; relatório de limites/riscos; ZIP MASTER autocontido e dois ZIPs separados para Auditores A e B contendo o mesmo novo código, hashes e prompts de auditoria cega. Conserve os originais imutáveis. Caso a interface não permita baixar ZIPs, mantenha os três ZIPs no repositório/artefatos da tarefa e informe seus caminhos, tamanho e SHA-256 para que eu possa obtê-los.

**Veredito admissível do executor:** "candidata preparada para auditoria independente" ou "implementação parcial/HOLD". A homologação depende de Auditores A/B e Chat Master. Faça a implementação e os testes nesta tarefa, sem pedir autorização para etapas já previstas neste escopo.
