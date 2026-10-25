# T7 Measures - Decisoes pendentes apos R8.1

Estas condicoes estao **PROPOSTAS**: nenhum arquivo constitui autorizacao automatica.

## A. Ratificacao PROVISORIA para desenvolvimento experimental

1. **Slot:** maximo de 1 ciclo de capturas A/B ativo em toda a instancia do addon (nao por area/janela).
2. **Planaridade P:** `tau(L) = min(0.010 mm, max(0.001 mm, 1e-6*L))` em metricas adequadas; regras para Unit System NONE em Blender Units conforme R8.
3. **Resolucao:** `R_U <= tau/4` para aceitar aproximacao.
4. **Area de face P:** dois gates distintos, geometrico e TOTAL, com limite candidato de **1%** nos intervalos definidos na R8.
5. **Teto de complexidade candidato:** ate 512 loops por face, 200.000 pares totais, 50.000 pares de triangulos.
6. **Orcamento de memoria experimental:** 128 MiB **agregado por instancia**, incluindo buffers coexistentes e transientes; objetivo de projeto, **nao prova de limite RSS real**.

Ratificar provisoriamente = permitir estudar, implementar prototipo offline e reduzir limites se a evidencia exigir; NAO significa que a impressao 3D foi calibrada ou que a operacao em Blender real esta liberada. Ampliacoes futuras exigem nova decisao.

## B. Autorizacao operacional de ferramentas (separada)

- **Work M0 (ainda HOLD):** permitir elaborar kernel geometrico/formatacao + testes **offline somente**, com arquivos descartaveis, sem `bpy`, sem arquivos `.blend`, sem instalacao, sem interface Blender real.
- **Work M1/M2 (HOLD):** adaptador/UI Blender 5.2.2, testes em runtime real e qualquer acesso a arquivos reais requerem autorizacao especifica posterior.
- **A/B:** auditar candidata Work M0 antes de avancar.

## Pergunta que desbloqueia apenas a proxima etapa

`Aprovo provisoriamente as constantes e a politica de slot listadas no item A para prototipagem e autorizo Work M0 estritamente offline conforme item B.`

Respostas diferentes tambem sao validas: ratificar parcialmente, rejeitar algum valor ou permitir somente elaborar pacote M0 sem executa-lo.
