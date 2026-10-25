# PROMPT PARA O PRÓXIMO CHAT — T7 Statue Mover v1.2.21 — CHEAP AUDIT

## IMPORTANTE — NATUREZA E ESCOPO

Este projeto é **somente um plugin/add-on pessoal de Blender**, usado pelo próprio usuário em um fluxo legítimo de produção de estátuas.

O trabalho solicitado é exclusivamente de **engenharia de software, QA, debugging, auditoria defensiva do próprio código, testes de regressão, preservação de dados e confiabilidade do plugin**.

**Não é cibersegurança ofensiva. Não é pentest. Não é invasão. Não é exploração de terceiros. Não é bypass de autenticação ou controle de acesso. Não é malware. Não há objetivo de comprometer serviços, dispositivos, contas ou dados de terceiros.**

Termos como `adversarial`, `fault injection`, `fail-closed`, `crash recovery` e similares aparecem apenas no contexto de QA defensivo do próprio add-on.

---

## TAREFA

Faça uma **auditoria independente e adversarial** da candidata congelada **T7 Statue Mover v1.2.21-candidate**.

Runtime de produção alvo: **Blender 5.0.0 exatamente**.

Mantenha a candidata **somente leitura**. Não aplique patch, não reempacote e não gere v1.2.22 durante a auditoria.

Veredito desta etapa:

- **GO COM CONDIÇÕES**; ou
- **HOLD**.

Qualquer HIGH/CRITICAL reproduzível => **HOLD**.

Sem Blender/bpy 5.0.0 real, nunca declarar production GO ou runtime PASS.

---

## ORDEM OBRIGATÓRIA DE INDEPENDÊNCIA

1. Leia `README_FIRST.md` e este prompt.
2. Valide o manifesto externo, ZIP/CRC, traversal/symlink e `SHA256SUMS.txt` interno.
3. Leia somente a candidata e `03_DIFF_AND_CONTEXT/AUDIT_DELTA_v1.2.21.md`.
4. Gere seu próprio diff v1.2.20 -> v1.2.21.
5. Ataque N-56 e N-52 e tente encontrar um novo N-57.
6. Verifique regressões focais N-54/N-53/N-51/N-48.
7. **Sele a primeira conclusão** em `FIRST_PASS_SEALED.md` com SHA-256.
8. Só depois abra `04_REFERENCES_AFTER_FIRST_PASS/`, `05_FAILURE_HISTORY/` e `06_LOCAL_PRECHECK_NOT_PROOF/`.

Não use os relatórios anteriores ou precheck do desenvolvedor para formar a primeira conclusão.

---

# CONTEXTO

O contrato central continua:

```text
D = current_guide_world @ inverse(saved_guide_world)
new_world = D @ original_world
```

A base/referência fixa nunca se move.

Fluxo: Prepare -> usuário move apenas o guia com G/R/S -> Apply -> Finalize ou Restore.

Snapshot schema: **6**.

A v1.2.20 foi **HOLD** no Blender 5.0.0 por **N-56 HIGH**. O runtime também mostrou que N-52 ainda era MEDIUM do ponto de vista da continuidade dos canais do usuário.

A v1.2.21 deve ter um delta extremamente estreito:

- threshold singular Euler `1e-6 -> 1e-12`;
- branch continuity baseada nos canais Euler **pré-escrita**.

Nada mais deveria ser redesenhado.

---

# 1. N-56 — PRIORIDADE ABSOLUTA

A v1.2.20 já fechou N-54 com projeção polar em double, mas depois usava:

```python
EULER_SINGULAR_THRESHOLD = 1e-6
```

O runtime real mostrou falso reject numa janela legítima muito próxima de +/-90 graus porque o branch singular descartava O(cy) informação apesar de a matriz pós-polar já estar ortonormal em double.

A v1.2.21 usa:

```python
EULER_SINGULAR_THRESHOLD = 1e-12
```

## Ataques baratos obrigatórios

Extraia e execute os helpers **reais** da candidata por AST ou técnica equivalente. Não teste apenas uma reimplementação idealizada.

Cobrir:

- 6 Euler orders;
- exact +/-90;
- +/-89.9, 90.1, 89.99, 90.01;
- janela muito estreita do N-56: deltas ~`1e-5 .. 1e-4` graus de 90;
- `cy` em escala log de ~1e-14 até 1e-5;
- outer angles variados;
- 20k+ orientações aleatórias;
- ruído assimétrico 1e-8..1e-6 antes da polar;
- signed scales/reflections;
- singular/quase singular;
- shear abaixo/acima do guard;
- non-finite;
- tentar demonstrar instabilidade do branch geral quando `cy` está entre 1e-12 e 1e-6.

Compare reconstrução contra a rotação projetada e contra a rotação limpa quando aplicável.

É desejável demonstrar explicitamente que o mesmo vetor falhava com threshold 1e-6 e deixa de falhar com 1e-12, sem apenas assumir o relatório anterior.

---

# 2. N-52 — REFERÊNCIA PRÉ-ESCRITA

Na v1.2.20 a branch equivalente era comparada contra `obj.rotation_euler` **depois** de `obj.matrix_basis = local`. O runtime mostrou que o setter do Blender pode ele próprio mudar para a branch distante.

A v1.2.21 deve capturar a continuidade antes da escrita:

```text
prewrite rotation_euler
        ↓
obj.matrix_basis = local
        ↓
Euler double refinement
        ↓
branch mais próxima da referência pré-escrita
```

## Verificações obrigatórias

- por AST/estrutura, prove que a captura ocorre antes da atribuição a `matrix_basis`;
- prove que o valor pré-escrita é realmente passado para o refinamento;
- prove que o fallback do helper continua válido quando referência explícita não é passada;
- 6 Euler orders;
- branches companheiras;
- current channels fora de [-pi, pi];
- wraps +/-2pi;
- near/exact gimbal;
- delta_rotation_euler não zero;
- repeated Apply conceitual;
- caso em que branch próxima é >1e-12 pior: ela **não** pode ganhar só por proximidade;
- caso em que branches são equivalentes dentro de 1e-12: a mais próxima deve ganhar.

Procure um novo N-57 em que usar canais pré-escrita cause world errado, grande salto em outra situação ou branch incorreta após rotação legítima grande.

---

# 3. REGRESSÃO N-54 / N-53 / N-51

Confirme que a v1.2.21 não mexeu indevidamente em:

- polar projection;
- shear guard;
- signed scale;
- vetor linear `2.5e-5`;
- length gate `1e-5`;
- N-48 component cap `0.0125`/ULP;
- translation sanity.

Repetir no domínio barato:

- N-54 noisy gimbal;
- N-51 `+1.1e-5` e `+2e-5` => REJECT;
- N-48 clássicos => REJECT;
- N-38/N-39/N-40 => REJECT;
- N-47 translation vectors => REJECT;
- NaN/Inf/bottom row fail-closed.

---

# 4. DIFF / ARQUITETURA

Confirme por diff próprio que não houve redesign indevido de:

- `D @ M0`;
- Prepare/Apply/Finalize/Restore;
- snapshot schema/persistence;
- parent/world helpers;
- raw-channel gate;
- readback certification;
- geometry fingerprint;
- modifiers;
- reference import/cleanup;
- N-24..N-35.

O aviso DIM-300 **não pertence** à v1.2.21; se aparecer, documente como scope creep.

---

# 5. RUNTIME BLENDER 5.0.0 — SE DISPONÍVEL

Se houver Blender/bpy **5.0.0 exatamente**, execute sem patch no ZIP original congelado:

- p59 N-56: alvo 96/96 e world correto;
- p50 window: 0 false rejects / 1152;
- p50 singular: 1440/1440;
- p50 full: 7560/7560;
- p50 singbig: sem root regression;
- p50 child/mpi+deltas/mirror/random;
- p58 ou equivalente N-52: objetivo 0/300 branch swaps vs canais **pré-escrita** em caso não-gimbal, com world correto;
- p51 save/reopen/Finalize/Restore;
- p52 produção: 59/59;
- t62/t63 N-51;
- t61 N-48/47/38/39/40/NaN;
- t40/t50 N-42/N-44/N-46/A3/A3_adv/repeated Apply;
- N-24..N-35;
- BONE, hidden/excluded, persistence, modifiers e stress.

Para todo caso aceito relevante, valide world independente; Apply FINISHED sozinho não é prova.

---

# 6. ACHADOS HISTÓRICOS QUE NÃO DEVEM SER CONFUNDIDOS COM NOVA REGRESSÃO

- N-46 LOW: extremo anisotrópico, fail-closed.
- N-49 INFO: pequena janela direcional da política 2.5e-5.
- N-55x LOW: muito grande (~4e5 world-column), pré-existente.
- GUI/event loop/undo/drivers auto-exec podem ficar PENDING em headless.

---

# ENTREGA

Produza relatório Markdown com:

1. identidade e hashes;
2. ambiente;
3. first-pass seal;
4. diff próprio;
5. N-56;
6. N-52;
7. regressões N-54/N-53/N-51/N-48;
8. qualquer N-57;
9. matriz PASS/FAIL/PENDING;
10. veredito inequívoco **GO COM CONDIÇÕES** ou **HOLD**;
11. reproduções completas de qualquer HIGH/CRITICAL.

Se gerar evidências, entregue evidence bundle separado.
