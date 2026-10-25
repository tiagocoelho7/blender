# AUDIT DELTA — T7 Statue Mover v1.2.17-candidate

## Base imutável

- predecessor: `t7-statue-mover-v1.2.16-candidate.zip`
- v1.2.16 status: **HOLD** por N-47 HIGH
- snapshot schema: **6** (inalterado)
- runtime alvo: **Blender 5.0.0 exatamente**

## Motivo único desta candidata

Dois auditores independentes reproduziram que o `verify_applied_world_material_sanity()` da v1.2.16 podia auto-certificar um world materialmente errado quando os canais pós-write permaneciam estáveis.

Casos obrigatórios reproduzidos no predecessor:

- translation expected `(1e6,0,0)`, actual `(1e6,3.5,0)`;
- translation expected `100000`, actual `100000.4`;
- linear column expected `(65536,1,0)`, actual `(65536,2.9,0)`.

O problema era o orçamento agregado de 64 ULP da maior translation para todos os eixos e 256 ULP da norma da coluna para cada componente.

## Alteração funcional v1.2.17

O raw-channel gate introduzido para N-45 **não foi redesenhado**. A única mudança funcional é o world-material sanity secundário.

### Translation world

Antes: cada componente recebia 64 ULP da maior coordenada expected.

Agora: calcula-se uma única norma Euclidiana do erro de translation e ela deve ser <=:

`max(1e-4, 4 * ULP(max(1, |expected X|, |expected Y|, |expected Z|)))`

Isso preserva o acoplamento cross-axis legítimo demonstrado pelo N-42, mas reduz o envelope de 64 para 4 ULP e impede os vetores N-47 conhecidos.

### Bloco linear world

Antes: cada elemento recebia 256 ULP da norma de sua coluna.

Agora: cada coluna inteira é comparada como vetor 3D. A norma Euclidiana do erro da coluna deve ser <=:

`max(1e-4, 2.5e-5 * max(1, ||expected_column||))`

O orçamento relativo permite o ruído de decomposição/recomposição que se move entre componentes da mesma coluna (N-45), mas fica abaixo do masking N-47 reproduzido em `(65536,1,0) -> (65536,2.9,0)`.

### Bottom row / non-finite

- bottom row continua `2e-6` por componente;
- NaN/Inf continuam fail-closed.

## Deliberadamente inalterado

- `capture_transform_channel_state()` / `verify_applied_transform_channels()`;
- cálculo `D @ original_world`;
- setter/prefix;
- applied-world readback e Finalize;
- snapshot/persistence/schema;
- N-24..N-35;
- modifiers, geometry fingerprint, N-29, reference cleanup.

## LOW/INFO herdados

N-46, N-37, N-33 e N-34 não são objetivo desta candidata.

## Prova ainda necessária

Sem Blender 5.0.0, esta candidata não pode fechar N-45/N-42 em runtime. Após cheap audit limpa, a próxima etapa deve repetir o runtime real, incluindo escalas 50/100/1000, near-gimbal, G 100..100000 e fault injection N-47.
