# AUDIT DELTA — T7 Statue Mover v1.2.19-candidate

## Base imutável

- predecessor: `t7-statue-mover-v1.2.18-candidate.zip`
- v1.2.18 status: **HOLD** por N-50 HIGH; N-51 MEDIUM conhecido
- snapshot schema: **6** (inalterado)
- runtime alvo: **Blender 5.0.0 exatamente**

## Motivo desta candidata

A auditoria runtime v1.2.18 provou que o sanity gate estava corretamente recusando vários casos quase-gimbal, mas o erro já havia sido introduzido antes pelo caminho de escrita:

`set_channel_world_matrix()` -> `obj.matrix_basis = local` -> decomposição matrix->Euler float32 do Blender.

Em Euler XYZ com Y próximo de +/-90 graus, o runtime reproduziu até ~`5.3e-4` de erro relativo no setter, enquanto um Euler float32 calculado a partir da mesma rotação com matemática double reproduziu o pose com erro ~`1e-7` ou menor. Portanto **não** é correto alargar o world sanity: a pose escrita estava realmente errada.

O mesmo runtime registrou N-51 MEDIUM: o vetor obrigatório de fault injection `scale.y += 2e-5` em peça unitária era aceito porque o raw-channel esperado é capturado depois do setter/injetor e o world sanity linear tinha piso/budget `1e-4 / 2.5e-5`.

## Alteração funcional v1.2.19

### 1. N-50 — refinamento Euler double após o setter nativo

O cálculo de world e parent prefix continua inalterado:

`desired_world = D @ original_world`

`local = inverse(channel_parent_prefix(obj)) @ desired_world`

A v1.2.19 **continua chamando primeiro**:

`obj.matrix_basis = local`

Isso preserva a semântica nativa do Blender para:

- location;
- signed scale;
- delta location;
- delta scale;
- factoring geral do setter já exercitado nas versões anteriores.

Somente quando `rotation_mode` é um dos seis modos Euler (`XYZ`, `XZY`, `YXZ`, `YZX`, `ZXY`, `ZYX`) ocorre um refinamento imediato do canal de rotação:

1. usa o signed total scale já escolhido pelo setter do Blender para normalizar a parte linear **do `local` pedido**, sem usar a matriz recomposta como verdade;
2. recusa o refinamento se houver shear material (`dot` entre colunas normalizadas > `1e-4`), preservando o caminho histórico/fail-closed para casos como N-46;
3. reconstrói em Python `float` (double) a rotação total pedida;
4. calcula a delta rotation com o mesmo `rotation_mode` e remove-a na ordem Blender `delta @ base`;
5. converte a rotação base para Euler em double, testando as duas soluções Tait-Bryan equivalentes e escolhendo a representação compatível mais próxima dos canais atuais;
6. grava somente `obj.rotation_euler`.

Quaternion e Axis-Angle **não** usam esse refinamento: continuam no setter histórico, pois N-50 é específico da decomposição Euler perto de gimbal e esses modos já passavam no runtime.

### 2. N-51 — world sanity linear mais estreito

Translation sanity N-42 permanece **inalterado**.

O budget vetorial linear muda de:

`max(1e-4, 2.5e-5 * max(1, ||expected_column||))`

para:

`max(1e-5, 1e-5 * max(1, ||expected_column||))`

Objetivo: o fault obrigatório unitário `1 -> 1.00002` (`2e-5`) deve ser rejeitado pelo budget da coluna, agora que N-50 remove a principal fonte de falso reject linear quase-gimbal.

O cap N-48 por componente permanece inalterado:

`max(0.0125, 8 ULP(max(1, |expected_component|)))`

Ele continua sendo uma segunda barreira contra sibling masking; a coluna precisa satisfazer **ambos** os budgets.

## Deliberadamente inalterado

- raw-channel gate v1.2.16+;
- translation sanity / N-42 four-ULP vector budget;
- `channel_parent_prefix()` e `channel_world_matrix()`;
- `D @ M0`;
- applied-world readback e Finalize;
- snapshot/persistence/schema;
- N-24..N-35;
- modifiers, geometry fingerprint, N-29, reference cleanup.

## Vetores obrigatórios na cheap audit

### N-50 / decomposição

- validar matematicamente os 6 Euler orders;
- near-gimbal em ambos os lados de +/-90 graus;
- branch compatibility / wrap de +/-2pi;
- delta_rotation_euler diferente de zero;
- signed scale e shear/fallback;
- confirmar que `matrix_basis` ainda é escrito primeiro e apenas Euler é refinado;
- tentar encontrar N-52: ordem Euler errada, delta factoring errado, branch equivalente errada, ou refinamento que altera semanticamente um caso não-gimbal.

### N-51

- coluna unitária com drift `2e-5` deve exceder o novo budget (`1e-5`);
- N-38/N-39/N-40/N-47/N-48 continuam REJECT;
- N-49 abaixo do cap continua classificado apenas pela materialidade/runtime, não por threshold chasing.

## Runtime obrigatório após cheap audit limpa

No Blender/bpy **5.0.0 exatamente**, repetir o ZIP congelado sem patch:

- p40 `grid`, `gimbal` e `random`;
- p42 setter vs representable/direct channels;
- t50 `A1_gimbal`;
- p30/p31/p33;
- todos os seis Euler orders, com o eixo central de cada order próximo de +/-90 graus;
- delta rotation Euler não zero;
- root/child, parent XYZ, BONE, hidden/excluded, deltas e matrix_parent_inverse;
- Quaternion/Axis-Angle como controles de não-regressão;
- t61 B1/B2/B3 incluindo **unit drift 2e-5**;
- N-42, N-44, N-46;
- G/R/S, persistence/save-reopen, modifiers e stress.

Critério N-50: casos corretos devem chegar a Apply + Finalize e o controle independente do world deve permanecer materialmente correto. **Não aceitar uma solução baseada em simplesmente aumentar tolerâncias.**
