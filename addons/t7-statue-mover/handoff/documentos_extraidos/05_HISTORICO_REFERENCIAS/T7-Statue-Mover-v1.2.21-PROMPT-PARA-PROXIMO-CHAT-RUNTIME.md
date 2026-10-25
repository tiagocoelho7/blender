# PROMPT PARA O PROXIMO CHAT — T7 Statue Mover v1.2.21 — Auditoria Runtime Blender 5.0.0

## IMPORTANTE — NATUREZA E ESCOPO DESTE TRABALHO

Este projeto e somente um **plugin/add-on pessoal para Blender**, usado pelo proprio usuario em um fluxo legitimo de producao de estatuas.

Esta tarefa **nao e uma solicitacao de ciberseguranca ofensiva, pentest, invasao, exploracao de sistemas, bypass de controles de acesso, malware, persistencia maliciosa, roubo de credenciais ou comprometimento de terceiros**.

O trabalho solicitado e exclusivamente de **engenharia de software, QA, debugging, auditoria defensiva do proprio codigo, testes de regressao, preservacao de dados e confiabilidade do plugin**.

Termos como `fault injection`, `adversarial`, `fail-closed`, `tampering`, `sanity gate` e similares aparecem apenas porque os testes tentam contradizer o comportamento do **proprio add-on local** e provar que ele nao aceita uma transformacao errada como valida.

---

# SUA FUNCAO

Aja como **auditor independente e adversarial** da candidata congelada:

`T7 Statue Mover v1.2.21-candidate`

O alvo e **Blender/bpy 5.0.0 exatamente**.

A candidata e somente leitura. **Nao aplique patch, nao reempacote, nao sobrescreva o ZIP e nao gere v1.2.22 durante esta auditoria.**

Instrumentacao, monkeypatch, fault injection e contrafactuais sao permitidos apenas em harnesses/copias experimentais separadas. Nunca use uma copia modificada como evidencia de PASS da candidata congelada.

---

# IDENTIDADE IMUTAVEL

Candidata:

- arquivo: `01_CANDIDATE/t7-statue-mover-v1.2.21-candidate.zip`
- SHA-256: `7d475cfb4453ba3abc34da32a56274e4c296caebb614a78363c4c63edd57044f`
- `t7_statue_mover/__init__.py` SHA-256: `3678a278f60afa84850167618d0e659359948cfc913e671101195963fc7c8a7e`
- versao: `(1, 2, 21)`
- snapshot schema: `6`
- runtime alvo: **Blender 5.0.0 exatamente**

Predecessora para diff independente:

- `05_DIFF_AND_CONTEXT/t7-statue-mover-v1.2.20-candidate.zip`
- SHA-256: `79692b6a128e19707b949ff14d0d4ffc3fe99d554ccaee5d4b647e6060ec3161`

Se a identidade da candidata nao conferir, pare e reporte cadeia de custodia invalida.

---

# ORDEM OBRIGATORIA DE INDEPENDENCIA

1. Verifique o `MANIFEST.sha256` deste runtime bundle, CRC, traversal/symlink e hashes da candidata.
2. Confirme **Blender/bpy 5.0.0 exatamente** e registre build hash/Python/OS.
3. Leia este prompt e `README_FIRST.md`.
4. Antes de abrir qualquer referencia historica, leia somente:
   - a candidata congelada;
   - `05_DIFF_AND_CONTEXT/T7-Statue-Mover-v1.2.21-AUDIT-DELTA.md`;
   - a predecessora v1.2.20 para gerar seu proprio diff.
5. Instale/habilite o ZIP original pelos operadores reais do Blender/add-on quando aplicavel.
6. Rode a **primeira passagem runtime independente** dos gates abaixo.
7. Grave `FIRST_PASS_SEALED.md` com hashes, ambiente, resultados, findings e veredito provisorio.
8. Somente depois do selo abra:
   - `03_CURRENT_CHEAP_AUDITS/`;
   - `04_PREVIOUS_RUNTIME_BASELINE/`;
   - `06_DEVELOPER_CONTEXT_AFTER_INDEPENDENT_PASS/`.
9. Depois das referencias, tente contradizer a propria conclusao e acrescente probes se necessario.
10. Preserve scripts, logs brutos, CSV/JSON, diffs, hashes e reproducoes suficientes para auditoria posterior.

Mocks/helpers puros nao contam como PASS runtime.

---

# CONTRATO CENTRAL DO ADD-ON

A base/referencia catolica fixa nunca se move.

Fluxo:

1. usuario seleciona o corpo/guia final;
2. `Preparar Estatua` congela o estado inicial e desativa modifiers pesados de viewport;
3. usuario move somente o guia com Blender G/R/S, com escala uniforme positiva;
4. `Aplicar Transformacao` propaga a transformacao aos alvos;
5. usuario pode Finalizar ou Restaurar exatamente o estado inicial.

Matematica:

`D = current_guide_world @ inverse(saved_guide_world)`

`new_world = D @ original_world`

Sem parenting permanente. Hidden/excluded entram no escopo conforme o contrato existente. Escala zero/negativa/nao uniforme e shear/effective non-similarity continuam bloqueados. Snapshot deve sobreviver save/close/reopen para `.blend` ja salvo.

---

# HISTORICO IMEDIATO

## v1.2.20 = HOLD

O runtime Blender 5.0.0 exato da v1.2.20 encontrou **N-56 HIGH**:

- `EULER_SINGULAR_THRESHOLD = 1e-6` era grosseiro demais depois da projecao polar;
- numa janela genuinamente muito proxima de +/-90 graus, o ramo singular descartava termos O(cy);
- com colunas world grandes, isso ultrapassava o cap N-48 de componente e causava falso reject de world materialmente correto;
- p59: v1.2.20 aceitou 54/96 e recusou incorretamente 42/96;
- contrafactual probe-only com threshold `1e-12`: 96/96;
- p50 window contrafactual: 0/1152 falsos rejects;
- p50 full/singular/childcmp/singbig tambem ficaram limpos no contrafactual.

A v1.2.20 tambem deixou **N-52 MEDIUM** parcialmente corrigido:

- 73/300 swaps de branch Euler equivalente distante contra os canais originais;
- contrafactual usando referencia de continuidade **pre-write**: 0/300, world correto.

Ao mesmo tempo, a v1.2.20 fechou no runtime:

- N-54: p50 full 7560/7560, filhos e 90 graus exato;
- N-53: p52 producao 59/59;
- N-51: t62/t63 mantiveram +1.1e-5 e +2e-5 rejeitados.

---

# DELTA v1.2.21 — DEVE PERMANECER ESTREITO

Mudancas funcionais pretendidas:

1. **N-56:** `EULER_SINGULAR_THRESHOLD` de `1e-6` para **`1e-12`**.
2. **N-52:** `set_channel_world_matrix()` captura `rotation_euler` **antes** de `obj.matrix_basis = local` e usa essa referencia pre-write apenas no desempate entre branches equivalentes.
3. A projecao polar da v1.2.20 permanece intacta.
4. Budgets N-53/N-51/N-48, N-42, snapshot, persistence, modifiers, fingerprints e demais subsistemas nao devem ter sido redesenhados.
5. **DIM-300 nao faz parte desta candidata.** Nao trate a ausencia desse futuro aviso como finding.

Se seu diff mostrar scope creep funcional fora disso, investigue e reporte.

---

# GATE A — N-56 HIGH: THRESHOLD SINGULAR POS-POLAR

Este e o gate bloqueante principal.

## A1 — p59

Reproduza o caso da v1.2.20 em Blender 5.0.0 real:

- root sem parent;
- seis Euler orders;
- eixo central em +/- (90 - delta), com delta incluindo pelo menos 3e-5, 4e-5, 5e-5 e 5.5e-5 graus;
- casos k=2000 + guia S8 e/ou k=10000;
- G10 e combinacoes equivalentes que reproduziam a janela.

**Meta:** `96/96` casos corretos aceitos, world independente correto, Finalize `FINISHED` quando aplicavel e Restore exato nos controles.

## A2 — p50 window

Cubra densamente a janela ao redor do antigo threshold.

**Meta:** `0/1152` falsos rejects.

## A3 — p50 singular

Reexecute a bateria singular historica.

**Meta:** `1440/1440` corretos.

## A4 — p50 full

Reexecute a bateria principal historica com:

- seis Euler orders;
- +/-89.9, +/-90.1, +/-89.99, +/-90.01, +/-90 exato;
- k 1/10/50/100/1000/2000;
- root/child/child+matrix_parent_inverse+deltas;
- G10/R/S2/S4/S8/G300R/G1000RS2;
- mirror, random e controles relevantes.

**Meta:** `7560/7560` no full e nenhuma regressao nos submodos obrigatorios.

## A5 — singbig

Ataque k 1e4..1e5 e variantes de parent/scale.

No minimo, **nenhuma regressao root nova** por causa do threshold `1e-12`.

## A6 — verdade independente

Apply aceito nao basta. Para todos os casos focais:

- compare world real com `D @ M0` calculado independentemente;
- registre erro por coluna, comprimento, componente e material ratio;
- confirme `applied_world_valid` somente quando o readback e realmente valido;
- confira Finalize e Restore.

Qualquer workflow correto obrigatorio recusado por N-56 => HIGH/HOLD.

---

# GATE B — N-52 MEDIUM: CONTINUIDADE CONTRA CANAIS PRE-WRITE

A v1.2.21 implementa o contrafactual que na v1.2.20 produziu 0/300 swaps.

## B1 — p58-like

Use pelo menos 300 orientacoes nao-gimbal representativas, incluindo:

- seis Euler orders;
- canais fora de [-pi, pi];
- wraps +/-2pi e algumas voltas adicionais realistas;
- transformacao que nao deveria exigir troca visual de branch;
- root e hierarquias quando util.

Compare a representacao final contra os **canais pre-write do usuario**, nao apenas contra os canais depois do setter.

**Meta:** `0/300` swaps de branch equivalente distante nos casos nao-gimbal, com world correto.

## B2 — prioridade correta

Continuidade nunca pode vencer reconstrucao materialmente pior. Se uma branch exceder o envelope de erro equivalente, a escolha deve priorizar exatidao.

## B3 — save/reopen

Reexecute p51 ou equivalente:

- root;
- parent_with_child;
- BONE;
- delta;
- reopen -> Finalize;
- reopen -> Restore;
- drift de checkpoint deve continuar fail-closed.

Meta historica: pelo menos `24/24` no conjunto equivalente.

## B4 — gimbal exato

Em gimbal exato, redistribuicao de canais pode ser matematicamente inevitavel. Nao classifique como falha apenas por canais diferentes se:

- world e equivalente;
- nao ha branch pior evitavel;
- Finalize/Restore permanecem corretos.

---

# GATE C — N-54 DEVE CONTINUAR FECHADO

A projecao polar nao foi alterada.

Revalide no runtime real:

- filhos com parent rotacionado;
- matrix_parent_inverse;
- deltas;
- exact 90 nos seis Euler orders;
- noise amplification p54;
- mirror/signed scale validos;
- singular/reflection/shear guards.

A v1.2.20 tinha p50 full 7560/7560 e p54 ~3e-7 apos polar. A v1.2.21 nao pode reabrir N-54.

---

# GATE D — N-53 / N-51 / N-48

## D1 — p52 producao

Reexecute a estatua/hierarquia de producao usada anteriormente.

**Meta:** `59/59` casos corretos PASS.

Inclua guia anisotropico historico aproximadamente `(12,12,1)`, Arm/Hand/Finger/BONE, hidden/excluded, G/R/S e combinacoes multi-eixo.

## D2 — N-51 t62/t63

Obrigatorio:

- `+1.1e-5` de comprimento => REJECT;
- `+2e-5` => REJECT;
- controles corretos => PASS conforme envelope historico.

Teste normas 1/2/4/12/100/1000/2000, root e chain/deltas quando aplicavel.

## D3 — N-48 / masking

Os ataques historicos de sibling/component masking devem continuar fail-closed.

Nao aumente tolerancias para fazer N-56 passar.

## D4 — extremos conhecidos

N-55x LOW historico aparecia apenas em colunas extremas ~4e5 e era pre-existente. Meça novamente para detectar regressao, mas nao transforme automaticamente um comportamento pre-existente LOW em HIGH sem impacto novo no contrato obrigatorio.

---

# GATE E — REGRESSOES OBRIGATORIAS

Reexecute, conforme os harnesses historicos disponiveis:

- N-47 / N-38 / N-39 / N-40;
- NaN / Inf / bottom row;
- N-42 translation sanity;
- N-44;
- N-46 conhecido LOW, verificando que nao piorou;
- N-24..N-35;
- A3 / A3_adv;
- `B_repeated_apply`;
- G/R/S;
- BONE / Armature;
- hidden/excluded;
- modifiers;
- persistence;
- Finalize drift;
- save/new process/reopen;
- Restore exato;
- stress.

Se algum teste historico tiver expectativa obsoleta, documente o motivo e prove o comportamento correto independentemente em vez de simplesmente contar FAIL cru.

---

# GATE F — PROCURA DE N-57

Tente encontrar regressao nova causada pelas duas mudancas v1.2.21:

- threshold geral entre `1e-12` e `1e-6`;
- exact/near gimbal;
- signed scales/reflections;
- shear proximo do guard;
- non-finite/singular;
- pre-write continuity com wraps grandes;
- branch continuity vs reconstruction accuracy;
- parent chains;
- repeated Apply;
- save/reopen.

Cheap audit encontrou apenas hipotese LOW/teorica com numero absurdo de voltas Euler, devido a reducao de argumento `sin/cos` em double. Teste magnitudes realistas e, se explorar extremos, separe claramente hipotese artificial de workflow plausivel.

Qualquer N-57 HIGH/CRITICAL reproduzivel => HOLD.

---

# GUI / EVENT LOOP / UNDO

Se o ambiente for apenas headless, marque explicitamente como PENDING:

- GUI real;
- event loop;
- undo interativo;
- drivers/auto-exec que dependam do contexto grafico.

Nao declare PASS para o que nao foi exercitado.

Isso nao precisa impedir um veredito `GO COM CONDICOES` se todos os gates centrais runtime/headless passarem e as pendencias estiverem claramente delimitadas.

---

# REGRA DE DECISAO

## HOLD

Qualquer um destes implica HOLD:

- CRITICAL/HIGH reproduzivel;
- p59 N-56 falhar em workflow correto;
- p50 window/singular/full reabrir falso reject correto;
- world incorreto certificado como valido;
- N-52 introduzir world errado ou continuidade vencer branch materialmente melhor;
- p52 producao regredir;
- N-51 reabrir;
- snapshot/checkpoint perdido;
- Restore inexato;
- Finalize bloquear fluxo correto obrigatorio;
- regressao nova relevante em N-24..N-56.

## GO COM CONDICOES

Pode ser usado se:

- todos os gates centrais obrigatorios acima passarem em Blender/bpy 5.0.0 exato;
- nao houver HIGH/CRITICAL;
- restarem apenas MEDIUM/LOW/INFO bem caracterizados ou pendencias GUI explicitamente nao testadas.

Nao conceda `production GO` absoluto se GUI/event loop/undo obrigatorios nao foram exercitados.

---

# EVIDENCIA / ENTREGAVEIS

Entregue:

1. `T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-AUDIT-REPORT.md`
2. `T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-AUDIT-EVIDENCE.zip`
3. `FIRST_PASS_SEALED.md`
4. ambiente exato;
5. hashes da candidata antes/depois;
6. matriz PASS/FAIL/PENDING;
7. scripts/harnesses;
8. logs brutos;
9. reproducoes completas de qualquer finding bloqueante;
10. veredito inequivoco `HOLD` ou `GO COM CONDICOES`.

Nao gere patch durante a auditoria. Se houver HOLD, apenas descreva a menor correcao plausivel e os criterios de aceite para a proxima candidata.

---

# NOTA SOBRE OS CHEAP AUDITS INCLUIDOS

Ha multiplos resultados cheap convergentes em `03_CURRENT_CHEAP_AUDITS/`, todos sobre a candidata SHA `7d475cfb...7044f`, sem HIGH/CRITICAL e com recomendacao de seguir ao runtime.

Um dos **result bundles de auditor** possui um `SHA256SUMS.txt` que tenta incluir o proprio `SHA256SUMS.txt`; essa entrada auto-referente nao pode validar por construcao. Todos os outros arquivos daquele pacote, inclusive a candidata, validaram independentemente. Outro evidence bundle cheap possui manifesto integralmente valido. Trate isso como **INFO de empacotamento da evidencia**, nao como finding da candidata.

A integridade da candidata deve ser sempre comprovada diretamente pelo SHA imutavel acima.
