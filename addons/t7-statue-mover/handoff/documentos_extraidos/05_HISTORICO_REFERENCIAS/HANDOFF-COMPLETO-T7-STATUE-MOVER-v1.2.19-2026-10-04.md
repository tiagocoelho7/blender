# HANDOFF COMPLETO — T7 Statue Mover / Blender

**Data do handoff:** 2026-10-04  
**Estado atual:** candidata **v1.2.19 congelada**, aguardando **pré-auditoria barata independente**.  
**Runtime de produção alvo:** **Blender 5.0.0 exatamente**.  
**Snapshot schema atual:** **6**.

---

## 0. IMPORTANTE — NATUREZA E ESCOPO DO PROJETO

Este projeto é **apenas um plugin/add-on pessoal para Blender**, usado pelo próprio usuário em um fluxo legítimo de produção de estátuas.

Este trabalho **não é uma solicitação de cibersegurança ofensiva, pentest, invasão, exploração de sistemas, bypass de controles de acesso, malware, persistência maliciosa ou comprometimento de terceiros**.

O trabalho solicitado é exclusivamente de **engenharia de software, QA, debugging, auditoria defensiva do próprio código, testes de regressão, preservação de dados e confiabilidade do plugin**.

Não há alvo de terceiros, credenciais alheias, exploração de serviço externo ou objetivo ofensivo. Trate o código como um projeto pessoal legítimo.

---

## 1. O QUE É O T7 STATUE MOVER

Add-on pessoal para Blender usado para movimentar uma estátua inteira a partir de um corpo/guia final, preservando todas as outras partes relacionadas.

Fluxo de produção pretendido:

1. existe uma **base/referência católica fixa**, que nunca deve se mover;
2. o usuário escolhe o **corpo final/guia**;
3. **Preparar Estátua** congela o estado original e desabilita temporariamente modifiers pesados de viewport nos alvos gerenciados;
4. o usuário move **somente o guia** com os comandos normais do Blender `G`, `R` e `S`;
5. **Aplicar Transformação** propaga a transformação do guia para todos os alvos;
6. o usuário pode **Finalizar** ou **Restaurar Estado Inicial** exatamente;
7. coleções ocultas/excluídas também fazem parte do escopo;
8. a base/referência nunca se move;
9. não deve haver parenting permanente criado pelo add-on.

A transformação matemática central é:

```text
D = current_guide_world @ inverse(saved_guide_world)
new_world = D @ original_world
```

Regras importantes do contrato:

- scale do guia deve ser uniforme e positivo;
- zero/negative/non-uniform scale do guia é bloqueado;
- shear/effective non-similarity é bloqueado quando material;
- todos os objetos gerenciados devem acompanhar o guia corretamente;
- Restore deve ser exato e fail-closed;
- Finalize só pode remover checkpoint/snapshot depois de validar o estado aplicado;
- snapshot deve sobreviver a Prepare -> fechar sem salvar -> reabrir para `.blend` já salvo;
- hidden/excluded collections precisam ser consideradas;
- o add-on não deve depender de `matrix_world` stale de objetos nunca avaliados quando isso puder ser evitado.

---

## 2. REFERÊNCIA / ASSET FUTURO

Existe uma base católica fixa planejada, aproximadamente **12 MB**, que futuramente poderá ser empacotada em:

```text
assets/base_reference.blend
```

O import planejado:

- cria/usa `T7_BASE_REFERENCIA`;
- tagueia IDs importados;
- objetos importados ficam `hide_select=True`;
- coleção/master de referência fica `hide_render=True`;
- mismatch de unidade gera aviso, sem alterar unidades da cena;
- não incluir o asset real até o import/cleanup estar robusto.

---

## 3. REGRAS DO FLUXO DE AUDITORIA

Estas regras são obrigatórias daqui para frente:

1. **Cada candidata é congelada.** Depois que o ZIP candidato é emitido, qualquer alteração de código vira uma nova versão.
2. Auditor deve manter a candidata **somente leitura**.
3. Não aplicar patch experimental na candidata para obter veredito final.
4. Qualquer **HIGH/CRITICAL reproduzível = HOLD**.
5. Sem Blender 5.0.0 real, o máximo permitido é **GO COM CONDIÇÕES**.
6. **Production GO nunca deve ser declarado sem auditoria runtime independente em Blender/bpy 5.0.0 exatamente.**
7. Em runtime, instalar/ativar o **ZIP original congelado**, sem recompilar/reempacotar.
8. Preservar protocolo de independência: primeira passagem antes de abrir referências históricas/precheck.
9. `FIRST_PASS_SEALED.md` deve ser produzido antes de abrir materiais pós-primeira-passagem.
10. Evidence bundle deve conter hashes, ambiente, outputs brutos, harnesses/probes e manifest.
11. Raw evidence prevalece sobre o texto do relatório se houver inconsistência.
12. Não criar a próxima versão automaticamente ao receber HOLD; primeiro congelar o resultado e identificar a correção focal.

---

## 4. REGRA NOVA DOS BUNDLES / PRÓXIMO CHAT

**A partir da v1.2.17, todo bundle deve incluir um prompt de continuidade em Markdown.**

Obrigatório incluir:

```text
00_PROMPT_PARA_PROXIMO_CHAT.md
```

Preferencialmente também uma cópia em:

```text
99_NEXT_CHAT/00_PROMPT_PARA_PROXIMO_CHAT.md
```

O **mesmo prompt** deve ser entregue separadamente ao usuário como `.md`.

Esse prompt deve começar deixando explícito que:

- é um plugin/add-on pessoal de Blender;
- é QA/debugging/engenharia de software defensiva;
- não é cybersecurity ofensiva;
- não é pentest;
- não é invasão;
- não é bypass;
- não é malware;
- não é comprometimento de terceiros.

O bundle atual v1.2.19 já cumpre essa regra.

---

## 5. HISTÓRICO TÉCNICO — PRINCIPAIS VERSÕES E FINDINGS

A lista abaixo serve para impedir regressões e evitar repetir soluções já invalidadas.

### v1.2.0 / v1.2.1 / v1.2.2 / v1.2.3 / v1.2.4

Primeiras rodadas fecharam problemas de identidade de snapshot, restore de modifiers, colisões multi-Scene, geometry sentinel, import identity, parent metadata, Finalize geometry sentinel, rename/backup e validação de arquivo salvo.

Finding importante final da sequência:

- **H-03:** Prepare aceitava filepath não vazio sem provar que o `.blend` existia realmente em disco. Fechado na v1.2.5.

### v1.2.5

Auditoria oficial `bpy==5.0.0` abriu a série **N-01..N-19**, envolvendo recovery matrix, baseline safety, hidden matrices stale, backup paths, import membership, cleanup, unregister, multi-Scene, parent shear, save-state e geometry sentinel.

### v1.2.6

Encontrado:

- **N-22 CRITICAL:** `CLASSES` undefined.

Também ficaram N-20/N-21/N-23/N-24.

### v1.2.7

Fechou arquitetura anterior, mas ficou:

- **N-25 HIGH:** cleanup de `bpy.data.libraries.remove()` podia atingir linked IDs do usuário fora do preflight.

### v1.2.8

Fechou N-25, mas runtime encontrou:

- **N-26 CRITICAL:** enable normal falhava em `_RestrictData` porque `register()` iterava `bpy.data.scenes` cedo demais;
- **N-27 HIGH:** constraint pós-Prepare podia deixar Restore/Finalize aceitar estado errado;
- **N-28 HIGH:** Mesh geometry sentinel incompleto;
- **N-29 HIGH:** `.json.tmp` previsível / symlink overwrite.

### v1.2.9

Fechou N-26..N-29. Runtime encontrou:

- **N-30 CRITICAL:** aridade do sentinel no Prepare;
- **N-31 HIGH:** ancestor/external constraints;
- **N-32 HIGH:** keyframe/action/NLA/driver reassertion.

### v1.2.10

Fechou N-30..N-32. Runtime encontrou:

- **N-36 HIGH:** tolerância world `2e-6` estrita demais para float32 e parent chains;
- **N-35 MEDIUM:** bone scanner incompleto;
- N-37 LOW.

### v1.2.11

Tentou ULP matrix-wide para N-36, mas abriu:

- **N-38 HIGH:** grande translation podia alargar tolerância linear e aceitar erro `1 -> 1.02`.

### v1.2.12

Separou domínios, mas abriu:

- **N-39 HIGH:** sibling linear grande ainda mascarava erro de componente pequeno.

### v1.2.13

Tentou cap local, mas abriu:

- **N-40 HIGH:** sibling ainda podia ampliar o orçamento do componente protegido em certos regimes.

### v1.2.14

N-40 foi fechado. Runtime Blender 5.0.0 encontrou:

- **N-42 HIGH:** parent chain rotacionada + grandes translations fazia world verifier recusar pose correta por propagação de roundoff float32 entre eixos;
- **N-43 LOW:** diagnóstico reportava maior diff absoluto em vez da maior razão diff/tol.

N-42 mostrou que “X grande não pode influenciar Y” era incompatível com roundoff legítimo de parent chain rotacionada.

### v1.2.15

Moveu o blocker de world para `matrix_basis` requested vs readback.

Runtime Blender 5.0.0:

- **N-42 fechado**;
- N-44 não reproduzido em 19 cenários;
- N-38/N-39/N-40 preservados;
- mas apareceu **N-45 HIGH**: `matrix_basis` é recomposta dos canais do Blender e a decomposição/recomposição gerava falso reject em escala ~50–1000 e near-gimbal;
- **N-46 LOW/INFO:** escala anisotrópica extrema pode escrever pose errada antes de falhar, mas permanece fail-closed/Restore exato.

### v1.2.16

Passou a capturar/verificar raw transform channels depois do setter e adicionou world sanity coarse.

Cheap audit encontrou:

- **N-47 HIGH:** world sanity coarse podia aceitar world materialmente errado e congelá-lo como `applied_world_valid=True`.

Exemplos:

```text
(1e6,0,0) -> (1e6,3.5,0)
(65536,1,0) -> (65536,2.9,0)
```

### v1.2.17

Reduziu o world sanity, mas ainda usava budget linear por norma da coluna.

Cheap audit encontrou:

- **N-48 HIGH:** componente enorme da mesma coluna ainda podia emprestar tolerância a sibling pequeno.

Exemplo:

```text
expected (65536,1,0)
actual   (65536,2.5,0)
```

### v1.2.18

Adicionou cap local por componente, mantendo budget vetorial da coluna.

Cheap audits: **GO COM CONDIÇÕES**.

Runtime Blender/bpy 5.0.0 exato:

- **N-48 fechado**;
- N-47/N-38/N-39/N-40 bloqueados;
- N-42 continua fechado;
- N-44 não reproduzido;
- p30/p31/p33 do N-45 passaram;
- regressões centrais passaram;
- mas apareceu **N-50 HIGH** e **N-51 MEDIUM**.

#### N-50 HIGH — causa real

O problema não era mais tolerância. O próprio caminho:

```text
obj.matrix_basis = local
```

faz o Blender decompor matrix -> Euler float32. Perto de gimbal (eixo central do Euler perto de +/-90 graus), o setter pode introduzir erro real significativo.

Runtime mediu:

- ~22% de falha em Y = ±89,9° / ±90,1° com X/Z arbitrários;
- 145/930 no grid completo;
- erro relativo do setter até ~`5.3e-4`;
- erro real world de até ~`0.075` em peça escala 100;
- o Euler float32 calculado diretamente a partir da mesma rotação usando matemática double ficou ~3–4 ordens de grandeza mais preciso.

Conclusão: **não afrouxar world sanity**. Corrigir o writer de canais.

#### N-51 MEDIUM

Fault obrigatório:

```text
scale.y += 2e-5
```

em peça unitária era aceito porque o raw state é capturado depois do setter/injetor e o world linear sanity tinha piso grande demais.

#### N-49 INFO

Existe janela abaixo do cap `0.0125`, mas no runtime v1.2.18 foi caracterizada como imaterial.

---

## 6. ESTADO ATUAL — v1.2.19-CANDIDATE

### Status

**CONGELADA.** Ainda não recebeu auditoria barata independente externa nesta conversa.

Qualquer mudança de código daqui em diante deve virar **v1.2.20**.

### Base

Predecessora congelada:

```text
t7-statue-mover-v1.2.18-candidate.zip
```

Status da predecessora: **HOLD por N-50 HIGH**, com N-51 MEDIUM conhecido.

### O que a v1.2.19 muda

#### 6.1 N-50 — refinamento Euler em precisão double

A matemática world permanece:

```text
desired_world = D @ original_world
local = inverse(channel_parent_prefix(obj)) @ desired_world
```

A v1.2.19 **continua chamando primeiro**:

```python
obj.matrix_basis = local
```

Isso preserva a semântica nativa do Blender para location, signed scale, delta location, delta scale e factoring geral já exercitado historicamente.

Depois, **somente nos seis rotation modes Euler**:

```text
XYZ, XZY, YXZ, YZX, ZXY, ZYX
```

faz um refinamento imediato do canal de rotação:

1. usa o signed total scale escolhido pelo setter Blender para normalizar a parte linear **do `local` pedido**;
2. se houver shear material (`dot` entre colunas normalizadas > `1e-4`), não refina e mantém caminho histórico/fail-closed;
3. reconstrói a rotação total pedida em Python `float`/double;
4. monta `delta_rotation_euler` no mesmo rotation order;
5. remove delta na convenção Blender **`delta @ base`**;
6. converte a base rotation para Euler em double;
7. avalia as duas soluções Tait-Bryan equivalentes;
8. escolhe a branch equivalente mais próxima dos canais atuais;
9. grava **somente `obj.rotation_euler`**.

Quaternion e Axis-Angle permanecem no setter histórico e **não** passam por esse refinamento.

O objetivo é fechar N-50 sem mascarar erro real através de tolerância maior.

#### 6.2 N-51 — world sanity unitário mais estreito

Budget vetorial linear mudou de:

```text
max(1e-4, 2.5e-5 * max(1, ||expected_column||))
```

para:

```text
max(1e-5, 1e-5 * max(1, ||expected_column||))
```

Translation sanity N-42 permanece inalterado.

O cap N-48 por componente permanece:

```text
max(0.0125, 8 ULP(max(1, |expected_component|)))
```

A coluna precisa passar **budget vetorial + cap local**.

### Deliberadamente inalterado

- raw-channel gate v1.2.16+;
- translation sanity/N-42 four-ULP vector budget;
- `channel_parent_prefix()`;
- `channel_world_matrix()`;
- `D @ M0`;
- applied-world readback;
- Finalize;
- snapshot/persistence/schema 6;
- N-24..N-35;
- modifiers;
- geometry fingerprint;
- N-29 temp/symlink;
- reference cleanup.

---

## 7. IDENTIDADE EXATA DOS ARTEFATOS v1.2.19

### Candidata

```text
t7-statue-mover-v1.2.19-candidate.zip
SHA-256: bfac2b2bf1712c3a7c7a3613189477b5d8845f8c5f97b75c6b56ceb25e9e0552
```

`__init__.py`:

```text
SHA-256: 1124540bec926047b5d546494469efc17959c6e8b795cb1f706a59c3d4370d3e
```

### Bundle barato

```text
T7-Statue-Mover-v1.2.19-CHEAP-AUDIT-BUNDLE.zip
SHA-256: 4602d4606d893f530c94b2b14a868878091fa902c35630e9ced5c8409972e42b
```

### Prompt para próximo chat

```text
T7-Statue-Mover-v1.2.19-PROMPT-PARA-PROXIMO-CHAT.md
SHA-256: 3581188b691d6c497f65b0c3f6233b48061370c4c68551f66643c25b362c9909
```

### Prompt do auditor barato

```text
T7-Statue-Mover-v1.2.19-CHEAP-AUDITOR-PROMPT.md
SHA-256: 75041d4e95838b906117e1b1bad22ce987333311112f7b2fd4f25467e4e58754
```

### Audit delta

```text
T7-Statue-Mover-v1.2.19-AUDIT-DELTA.md
SHA-256: 452ff6c5b1b69011ab85ba1c307dae61ae9626728769e0c811e16f2412d8a298
```

### Local precheck

```text
T7-Statue-Mover-v1.2.19-LOCAL-PRECHECK.md
SHA-256: c94954d3d44dda8848584fa4a1b8678396a786499da8c4aa3b03220f50380891
```

### Arquivo de hashes de entrega

```text
T7-Statue-Mover-v1.2.19-DELIVERY-SHA256.txt
SHA-256 do próprio arquivo: 88342dc925073aa6d047021d3c52a13fd663555c3e68f22916e109f7ade550a4
```

---

## 8. PRECHECK LOCAL v1.2.19

Este ambiente **não possui Blender/bpy 5.0.0**, portanto o precheck **não fecha N-50/N-51 em runtime** e não autoriza production GO.

Resultados sobre uma extração nova do ZIP final:

```text
34 PASS / 0 FAIL
```

Cobertura principal:

- roundtrip matemático dos seis Euler orders;
- 5.000 amostras por order;
- near-gimbal XYZ em 89.9, -89.9, 90.01 e 89.999 graus;
- refinamento com `delta_rotation_euler != 0` em todos os seis orders, normal e near-gimbal;
- shear material recusa refinamento;
- N-51: drift `2e-5` excede novo budget `1e-5`;
- margem sintética para Euler double em escala 1000;
- N-48 `1 -> 2.5` continua bloqueado;
- N-38 `1 -> 1.02` continua bloqueado;
- N-47 translation continua bloqueado;
- setter nativo `matrix_basis` ocorre antes do refinamento Euler.

Também passaram:

- `python -m py_compile`;
- `SHA256SUMS.txt` interno **22/22**;
- `unzip -t`;
- 0 defs/classes top-level duplicadas;
- schema 6;
- versão 1.2.19.

`ruff` estava indisponível localmente.

---

## 9. PRÓXIMA AÇÃO — O QUE O NOVO CHAT DEVE FAZER AGORA

### Etapa imediata

Enviar **somente**:

```text
T7-Statue-Mover-v1.2.19-CHEAP-AUDIT-BUNDLE.zip
```

para auditor(es) barato(s) independente(s).

A candidata permanece congelada e somente leitura.

### Prioridade da cheap audit

Tentar **contradizer** a correção, especialmente procurar um novo **N-52**.

Casos obrigatórios:

- validar matematicamente os **seis Euler orders**;
- eixo central de cada order perto de `+/-90°`;
- os dois lados da singularidade;
- branch equivalente / wrap `+/-2pi`;
- `delta_rotation_euler != 0`;
- ordem correta de factoring Blender: **`delta @ base`**;
- signed scale;
- zero scale;
- shear e fallback;
- confirmar que `matrix_basis` é escrito primeiro;
- confirmar que o raw-channel snapshot é capturado **depois** do refinamento;
- Quaternion/Axis-Angle sem regressão;
- N-51 `2e-5` deve ser REJECT;
- N-38/N-39/N-40/N-47/N-48 continuam REJECT;
- procurar false accept, false reject, branch errada, order errado ou alteração de location/scale inesperada.

### Regra de decisão da cheap audit

- qualquer HIGH/CRITICAL reproduzível -> **HOLD**;
- sem HIGH/CRITICAL, mas sem Blender 5.0.0 -> **GO COM CONDIÇÕES** no máximo;
- não criar v1.2.20 durante a auditoria.

---

## 10. SE A CHEAP AUDIT PASSAR

Montar uma nova rodada runtime para **Blender/bpy 5.0.0 exatamente**, usando **o mesmo ZIP congelado v1.2.19**.

O runtime deve repetir pelo menos:

### N-50

- p40 `grid`;
- p40 `gimbal`;
- p40 `random`;
- p42 setter vs canais representáveis/diretos;
- t50 `A1_gimbal`;
- p30/p31/p33;
- todos os seis Euler orders;
- eixo central de cada order próximo de ±90°;
- `delta_rotation_euler != 0`;
- root/child;
- parent XYZ;
- `matrix_parent_inverse`;
- hidden/excluded;
- BONE parent;
- signed scale;
- Quaternion/Axis-Angle como controle de não regressão.

Critério N-50:

- caso correto -> Apply sem erro;
- `applied_world_valid=True`;
- controle independente world materialmente correto;
- Finalize `FINISHED`;
- Restore continua exato;
- **não aceitar solução baseada em aumentar tolerância**.

### N-51

Repetir fault injection unitário:

```text
scale.y += 2e-5
```

Deve resultar em:

- Apply erro/fail-closed;
- `applied_world_valid=False`;
- Finalize bloqueado;
- snapshot/baseline preservados;
- Restore exato.

### Regressões obrigatórias

Reexecutar:

- N-38;
- N-39;
- N-40;
- N-42;
- N-44;
- N-46;
- N-47;
- N-48;
- N-24..N-35;
- G/R/S completo;
- `(12,12,1) x2 -> (24,24,2)`;
- G 100/150/300/1000/10000/100000;
- `G_large`;
- stress ~601 targets / ~1200 modifiers;
- persistence/save-reopen;
- P1/P2/P3;
- multi-Scene;
- Save Copy / Save As;
- modifiers;
- geometry fingerprint;
- reference cleanup;
- linked Library/Overrides;
- normal addon enable/disable com `_RestrictData`;
- N-24 `os._exit` crash window.

---

## 11. AO RECEBER UM RELATÓRIO RUNTIME FUTURO

Não confiar apenas no texto do relatório.

Se o usuário enviar `...RUNTIME-AUDIT-REPORT.md` + `...RUNTIME-AUDIT-EVIDENCE.zip`, fazer:

1. confirmar SHA da candidata congelada v1.2.19;
2. confirmar `__init__.py`;
3. confirmar Blender/bpy **5.0.0 exatamente**;
4. confirmar instalação/enable do ZIP original, sem patch;
5. testar CRC do evidence ZIP;
6. validar `MANIFEST.sha256` do evidence;
7. comparar relatório embutido com relatório separado;
8. verificar `FIRST_PASS_SEALED.md` e seu hash;
9. confirmar que selo ocorreu antes das referências/precheck;
10. ler outputs brutos dos probes/harnesses;
11. conferir Gate N-50, N-51 e regressões;
12. reconciliar qualquer discrepância entre relatório e raw evidence;
13. raw evidence prevalece.

Se qualquer caso correto obrigatório falhar ou houver HIGH/CRITICAL reproduzível: **HOLD**.

---

## 12. POLÍTICA DE FAIL-CLOSED / DADOS

Prioridades absolutas:

1. não perder estado inicial;
2. não apagar checkpoint se Finalize não estiver realmente validado;
3. não mover base/referência;
4. não certificar world errado;
5. não tocar linked IDs externos indevidamente;
6. Restore exato em falha;
7. qualquer erro de verificação deve manter snapshot/baseline válidos;
8. não mascarar erro real só aumentando tolerâncias.

---

## 13. PREFERÊNCIAS DO USUÁRIO PARA ESTE FLUXO

- respostas em pt-BR;
- orientação objetiva e passo a passo quando necessário;
- artifacts versionados;
- SHA-256 explícito;
- candidata congelada por rodada;
- bundles `.zip` completos;
- auditoria adversarial independente;
- fail-closed e reversibilidade;
- nunca declarar production GO sem Blender 5.0.0 real;
- sempre incluir prompt de próximo chat dentro do bundle e também separadamente em `.md`;
- prompt deve reiterar que é um plugin pessoal legítimo, sem relação com cybersecurity ofensiva.

---

## 14. RESUMO EM UMA LINHA PARA CONTINUIDADE

**Estamos na v1.2.19 congelada; v1.2.18 caiu em runtime por N-50 HIGH (decomposição `matrix_basis -> Euler` imprecisa near-gimbal) e N-51 MEDIUM; v1.2.19 implementa refinamento Euler double pós-setter e estreita o world sanity unitário. Agora deve ser feita a cheap audit independente do bundle v1.2.19; só depois, se vier GO COM CONDIÇÕES sem HIGH/CRITICAL, montar runtime Blender/bpy 5.0.0 exato.**

