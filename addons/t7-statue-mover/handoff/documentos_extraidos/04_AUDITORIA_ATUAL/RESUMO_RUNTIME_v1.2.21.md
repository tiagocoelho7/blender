# RESUMO FIEL DO RELATÓRIO DE RUNTIME RECEBIDO — v1.2.21

**NÃO É O ARQUIVO ORIGINAL NEM CÓPIA BYTE A BYTE DO RELATÓRIO.** Esta consolidação preserva os resultados, estatísticas e qualificações do relatório de auditoria anexado pelo proprietário em 06/10/2026. Para validar cadeia de custódia, obter o MD original e ZIP de evidências originais listados em `INVENTARIO_FONTES_NAO_EMPACOTADAS.md`.

## Auditor / alvo

- Auditor: Claude runtime (ambiente `bpy`/Blender 5.0.0 exato); Python 3.11.15; Blender build `a37564c4df7a` (2025-11-18).
- Candidata original SHA `7d475cfb4453ba3abc34da32a56274e4c296caebb614a78363c4c63edd57044f`, `__init__.py` `3678a278f60afa84850167618d0e659359948cfc913e671101195963fc7c8a7e`, snapshot schema 6, manifesto 24/24.
- Bundle de entrada auditado SHA `7cc7e3bb5538c7b3d62723061ec536ef2b0908c3b05bccb2377e9963f00a1e77`, manifesto 16/16; nenhum patch ou repack na candidata.
- Parecer **GO COM CONDIÇÕES**, **nenhum HIGH/CRITICAL**, GUI/event loop/undo interativo/drivers auto-exec pendentes.
- Selo de primeira passagem reportado: SHA `c46ec89a2c4bdc33515a0ceabd9e4452108ec0264d0489a80daa5b4fc9786657`, selado antes de ler referências.

## Fechamentos centrais

| Probe | Resultado registrado | Interpretação |
|---|---|---|
| N-56 p59 janela de near-gimbal root | **96/96 aceitos; world correto; Finalize 96/96; Restore 96/96** | fechado |
| N-56 p50 window | **0 falhas /1152** (vs 88 na v1.2.20) | fechado |
| p50 singular | **0/1440 falhas** | preservado |
| p50 full | **0/7560 falhas** | preservado |
| p50 mirror / random / childcmp / quatax / extra | 240 /1500 /360 /720 /1440 casos; **todos 0 falhas** | preservado |
| p50 singbig (k 1e4..1e5) | 1/240 falha no filho k65536; 0 root | N-55x LOW antigo |
| p50 bigchild | 4/648 falhas, todas em k65536 | N-55x LOW antigo |
| N-52 p58 | **0/300 trocas branch**, vs 73/300 na v1.2.20 | fechado no sentido usuário |
| N-52 p58b | **0/360** com ±1..3 voltas | fechado no domínio |
| N-52 p51 save/reopen | **32/0**, root/child/BONE/delta, Finalize e Restore exatos, drift->CANCELLED | preservado |
| N-53 produção p52 | **59/59**, máximos ratio: vetor 0.458, comprimento 0.046, componente 0.0027, translação 0.59 | fechado |
| N-51 t62 | **583/0** | +1.1e-5 e +2e-5 rejeitados |
| N-51 t63 | **532/0** | rejeição de drift, roots/chains, vários scales |
| p55 | **0 falsos rejects k1000..65536; 3/72 k100000** | N-55x LOW pré-existente |
| Bateria t02..t31, t40, t42 | **0 FAIL** no conjunto relatado | regressões principais preservadas |
| t01 | 9 FAIL conhecidos, injetor H03-D obsoleto | não regredir gate sem revisar harness |
| t50 | 1 FAIL conhecido N-46 LOW | não é blocker atual |
| t61 | 11 FAIL iguais à v1.2.20, N-49 INFO e expectativas antigas | monitorar/retificar harness futuramente |
| `py_compile`, ruff, aridade, duplicatas | PASS | estático |

## N-57 LOW novo — muitas voltas Euler

Causa inferida pelo auditor: como v1.2.21 preserva a branch Euler original, canais com muitas revoluções crescem tanto que a quantização float32 do Blender começa a afetar a rotação reconstruída após girar o guia. Risco é **falso reject, nunca certificação de world errado**.

No p60, com R/T/S e os seis Euler orders:

| Voltas completas armazenadas | Aceitos v1.2.21 | Aceitos v1.2.20 | Erro coluna max v1.2.21 |
|---|---|---|---|
| 0 | 36/36 | 36/36 | 1.5e-7 |
| 1 | 36/36 | 36/36 | 6.1e-7 |
| 3 | 36/36 | 36/36 | 1.4e-6 |
| 10 | 36/36 | 36/36 | 3.6e-6 |
| 30 | 36/36 | 36/36 | 8.6e-6 |
| 100 | 30/36 | 36/36 | 4.4e-5 |
| 300 | 24/36 | 36/36 | 9.0e-5 |
| 1000 | 24/36 | 36/36 | 3.1e-4 |

p60b **64/0**: toda recusa `Finalize CANCELLED`, snapshot intacto, Restore exato; todo aceite `Finalize FINISHED` com readback válido. Auditor classificou LOW por falta de plausibilidade operacional (100 voltas = 36.000 graus). Critério FUTURO opcional: preservar canais gigantes só até limiar de quantização, senão branch modulo 2π; requer reabrir N-52, portanto **não corrigir sem evidência real e autorização**.

## Outros LOW/INFO do relatório

- N-55x LOW (pré-existente): cap N-48 0.0125 vs roundoff float32 em world columns enormes ~65536/4e5.
- N-46 LOW (pré-existente) anisotropia extrema sob parent rotacionado, fail-closed.
- N-49 INFO: pequena janela direcional que retorna accepted conforme envelope v1.2.18/v1.2.20; não confundir com HIGH.
- AUD-5 INFO: label de UI antiga corrigida para v1.2.21.

## Pendência explícita do auditor

**GUI real, event loop, undo interativo e drivers/auto-exec não receberam PASS em headless**. Parecer não autoriza production GO absoluto. O relatório original afirma este escopo explicitamente.
