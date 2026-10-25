# AUDIT DELTA — T7 Statue Mover v1.2.20-candidate

## Base imutável

- predecessor: `t7-statue-mover-v1.2.19-candidate.zip`
- v1.2.19 status: **HOLD** por N-54 HIGH + N-53 HIGH; N-52 MEDIUM conhecido
- snapshot schema: **6** (inalterado)
- runtime alvo: **Blender 5.0.0 exatamente**

## Evidência que motivou esta candidata

A auditoria runtime v1.2.19 confirmou que N-50 foi fechado para peças raiz, N-51 foi fechado e N-38/39/40/47/48 continuaram bloqueados. Porém encontrou duas regressões HIGH:

1. **N-54:** filhos de pais rotacionados chegam ao refinamento Euler com ~1e-7 de não-ortogonalidade no `local` por produtos float32. Perto de gimbal esse ruído é amplificado; em 90° exato houve 1008/1008 falhas nos filhos. O probe contrafactual do auditor mostrou que ortonormalizar antes da decomposição reduz o erro novamente para ~3e-7.
2. **N-53:** o budget vetorial de coluna `1e-5` fechou N-51, mas recusou 15/15 combinações de produção com rotação multieixo do guia anisotrópico `(12,12,1)`; v1.2.18 havia passado 59/59 no mesmo probe.

Também permaneceu **N-52 MEDIUM**: as duas branches Euler equivalentes podem diferir no erro de reconstrução por apenas ~1e-16, e a v1.2.19 escolhia primeiro por esse ruído numérico, causando saltos representacionais próximos de pi.

## Alteração funcional v1.2.20

### 1. N-54 — projeção polar para rotação própria antes de matrix->Euler

O fluxo continua:

`desired_world = D @ original_world`

`local = inverse(channel_parent_prefix(obj)) @ desired_world`

`obj.matrix_basis = local`

O setter nativo continua sendo executado primeiro para preservar location, signed scale e delta factoring. Para modos Euler, `_requested_basis_rotation_from_setter_channels()` continua dividindo a parte linear do `local` pelos signed total scales escolhidos pelo Blender e normalizando as colunas.

A diferença é que, após o **mesmo shear guard `max_dot <= 1e-4`**, a matriz de rotação aproximada é projetada para a rotação própria mais próxima por iteração polar em double:

`X_next = 0.5 * (X + inverse(X)^T)`

A projeção:

- rejeita matriz não finita/singular;
- exige determinante positivo;
- verifica residual de ortogonalidade;
- não roda em inputs que o shear guard já classificou como materialmente sheared.

O decompositor Euler usa `EULER_SINGULAR_THRESHOLD = 1e-6` para não tratar ruído float32 de ~1e-7 como evidência confiável de um lado específico do gimbal exato.

### 2. N-53 + preservação de N-51 — dois budgets geométricos independentes

O budget de **erro vetorial total da coluna** volta para:

`max(2.5e-5, 2.5e-5 * max(1, ||expected_column||))`

Esse envelope é o que já havia preservado a hierarquia de produção na v1.2.18.

Ao mesmo tempo é adicionado um budget separado para **erro de comprimento da coluna**:

`abs(||actual_column|| - ||expected_column||) <= max(1e-5, 1e-5 * max(1, ||expected_column||))`

Intenção:

- ruído pequeno de direção/recomposição em parent chains pode usar o envelope vetorial 2.5e-5;
- drift real de escala N-51 `1 -> 1.00002` altera o comprimento em 2e-5 e continua REJECT;
- o cap N-48 por componente continua igual (`max(0.0125, 8 ULP(...))`).

O auditor deve tentar contradizer essa separação com erros combinados de direção + comprimento e com parent/sibling magnitudes adversariais.

### 3. N-52 — desempate de branch por continuidade

As duas branches Euler ainda são reconstruídas e medidas. Agora:

1. calcula-se o menor `max_error`;
2. branches com `max_error <= min_error + 1e-12` são consideradas numericamente equivalentes;
3. entre elas, escolhe-se a de menor distância aos canais Euler atuais.

O objetivo é remover saltos representacionais causados apenas por diferenças de arredondamento ~1e-16, sem aceitar uma branch materialmente pior.

## Deliberadamente inalterado

- raw-channel gate v1.2.16+;
- translation sanity / N-42;
- N-48 per-component cap;
- `channel_parent_prefix()` / `channel_world_matrix()`;
- `D @ M0`;
- applied-world readback e Finalize;
- snapshot/persistence/schema 6;
- N-24..N-35;
- modifiers, geometry fingerprint, N-29 e reference cleanup.

## Cheap audit obrigatória

### N-54

- atacar a projeção polar com ruído ~1e-7, ruído assimétrico, sinais e matrizes quase singulares;
- seis Euler orders, +/-89.9, 90.1, 89.99, 90.01 e 90.0 exatos;
- confirmar que shear material continua sem refinamento;
- signed scales/reflections;
- delta_rotation_euler;
- provar que a projeção não muda materialmente uma rotação já correta.

### N-53/N-51

- direção correta com erro vetorial entre 1e-5 e 2.5e-5 deve poder passar se o comprimento permanecer correto;
- unit scale `+2e-5` e `+1.1e-5` devem falhar no length gate;
- atacar erros mistos direção + length;
- repetir N-38/N-39/N-40/N-47/N-48;
- tentar fazer uma magnitude grande emprestar tolerância ao comprimento de uma coluna pequena.

### N-52

- procurar casos em que uma branch >1e-12 pior seja escolhida apenas por proximidade; isso seria finding;
- fuzz das duas branches nos seis orders, inclusive perto de gimbal e wrap +/-2pi.

Procure explicitamente **N-55**: qualquer novo falso sucesso, falso reject ou regressão introduzida pelas três mudanças.

## Runtime obrigatório depois de cheap audit limpa

No Blender/bpy **5.0.0 exatamente**, ZIP congelado sem patch:

- p50 full/mirror/random/childcmp, com **0 falhas** em root, child e child + `matrix_parent_inverse` + deltas, incluindo 90° exato;
- p54: input com ~1e-7 de ruído deve voltar a erro ~1e-7, não amplificar;
- p52: **59/59**;
- t40/t50 A3, A3_adv e `B_repeated_apply`;
- t62: unit +2e-5 e +1.1e-5 REJECT, controles corretos PASS;
- N-52 instrumentado: branch escolhida, distância, persistência/save-reopen;
- N-48/47/38/39/40, N-42, N-44, N-46;
- N-24..N-35, G/R/S, BONE, hidden/excluded, persistence, modifiers e stress.

Critério: **não** aceitar uma correção baseada em simplesmente afrouxar todos os gates. O world independente precisa continuar materialmente correto e qualquer fault obrigatório precisa permanecer fail-closed.
