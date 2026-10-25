# AUDIT DELTA — T7 Statue Mover v1.2.18-candidate

## Base imutável

- predecessor: `t7-statue-mover-v1.2.17-candidate.zip`
- v1.2.17 status: **HOLD** por N-48 HIGH
- snapshot schema: **6** (inalterado)
- runtime alvo: **Blender 5.0.0 exatamente**

## Motivo único desta candidata

Dois auditores independentes reproduziram que o world-sanity linear da v1.2.17 ainda permitia masking dentro da própria coluna.

Reprodutor mínimo:

- expected column `(65536, 1, 0)`;
- actual `(65536, 2.5, 0)`;
- erro do sibling pequeno = `1.5`;
- budget vetorial da coluna = `~1.6384`;
- resultado v1.2.17: **aceito** e passível de canonicalização como `applied_world_valid=True`.

O problema não era a implementação da norma; era a política de usar apenas um orçamento derivado da norma total da coluna.

## Alteração funcional v1.2.18

O raw-channel gate N-45, o translation sanity v1.2.17, bottom row, NaN/Inf, `D @ M0`, setter/prefix, persistence e Finalize permanecem inalterados.

A única mudança funcional é o **linear world sanity**.

### Regra 1 — budget vetorial da coluna

Permanece:

`max(1e-4, 2.5e-5 * max(1, ||expected_column||))`

Esse limite preserva o envelope de recomposição/decomposição N-45 que pode distribuir erro entre componentes da mesma coluna.

### Regra 2 — cap por componente, expected-only

Novo em v1.2.18. Cada componente linear da coluna deve também satisfazer:

`abs(actual_component - expected_component) <= max(0.0125, 8 * ULP(max(1, |expected_component|)))`

Características:

- sibling da mesma coluna não amplia esse cap;
- sibling de outra coluna não amplia esse cap;
- `actual` divergente não amplia o próprio cap;
- componentes grandes ainda recebem seu próprio orçamento float32 por ULP;
- componentes pequenos recebem um piso absoluto empírico de `0.0125`.

O piso `0.0125` foi escolhido apenas como candidata de engenharia: ele fica acima do pior resíduo linear sem add-on observado no Blender 5.0.0 em p32 até escala 1000 (`~0.01031`) e abaixo do vetor N-38 `1 -> 1.02` (`0.02`). Ele **não** é considerado provado até a auditoria independente e o runtime Blender 5.0.0.

## Vetores N-48 que agora devem falhar

- `(65536,1,0) -> (65536,2.5,0)`;
- `(65536,1,0) -> (65536,2.0,0)`;
- `(1e6,1,0) -> (1e6,20,0)`;
- variantes `2.6`, `2.63`, sinais negativos e small siblings.

## Vetores históricos que devem continuar falhando

- N-47 translation `(1e6,0,0) -> (1e6,3.5,0)`;
- `100000 -> 100000.4`;
- N-47 linear `(65536,1,0) -> (65536,2.9,0)`;
- N-38 `1 -> 1.02`;
- N-40 `2048 -> 2048.025`, `32768 -> 32768.4`, `65536 -> 65536.8`;
- non-finite / bottom row corruption.

## Envelopes legítimos baratos que devem continuar cabendo

- linear p32 escala 1000: `~0.01031` por componente;
- near-gimbal escala 1: poucos `1e-6`;
- translation G=100000: `~0.0167` no runtime histórico.

Esses controles baratos não substituem runtime Blender 5.0.0.

## Deliberadamente inalterado

- `capture_transform_channel_state()` / `verify_applied_transform_channels()`;
- translation sanity da v1.2.17;
- cálculo `D @ original_world`;
- setter/prefix;
- applied-world readback e Finalize;
- snapshot/persistence/schema;
- N-24..N-35;
- modifiers, geometry fingerprint, N-29, reference cleanup.

## LOW/INFO herdados

N-46, N-37, N-33 e N-34 não são objetivo desta candidata.

## Prova ainda necessária

Após cheap audit limpa, a mesma candidata congelada deve passar runtime Blender/bpy 5.0.0 real, incluindo p30/p31/p32/p33, escalas 10/50/100/1000, near-gimbal, N-42 G 100..100000, N-48 fault injection, N-38/N-39/N-40, N-44, N-46, G/R/S, persistence e stress.
