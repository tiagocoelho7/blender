# Relatório técnico ao Master e aos auditores A/B

22/10/2026 — T7 Measures M0, candidata `0.0.1-m0`.

## Entrega e autoridade

O M0 autorizado foi implementado exclusivamente em Python offline, com oito modalidades, projeções P certificadas por aritmética racional e intervalos, apresentação pura e estado A/B sintético. A implementação é **candidata para auditoria**, sem GO autoconcedido. Nenhum Blender foi iniciado; não houve acesso a `.blend`, instalação ou integração. O HOLD de M1/M2 e produção foi preservado.

A autorização literal está em `00_AUTORIZACAO.md`. Os documentos históricos mantêm seus avisos originais de não autorização; a autorização posterior é a única mudança de autoridade. O ZIP original foi preservado byte a byte; seu manifesto interno passou **32/32** membros. SHA-256 original: `b09fdc972ec725958d015d4e02035fcee0004440695a4d6aabfab07e6126c452`. Não se repetiram as auditorias históricas nem se somaram seus testes aos desta candidata.

## Implementação

| Parte | Implementado e exercitado |
|---|---|
| V-V / V-E / E-E | Distâncias a pontos e segmentos fechados; candidatos exatos, paralelismo, degeneração e cruzamentos quase paralelos |
| V-F / E-F / F-F | Faces finitas, triangulação de polígono simples, interiores/bordas e incidência, incluindo coplanaridade e contenção |
| Comprimento E / área F | Medidas no espaço transformado, unidades físicas ou BU, reflexão e shear |
| P | Newell e projeção racionais; h, L, área e resolução com bounds; gates de altura, resolução e duas cotas de área |
| Certificados | Bounds internos separados da exibição, contato por predicado de incidência, faixa positiva e indeterminada |
| Texto numérico | HALF_EVEN do valor representado, outward por inteiros, sem falso zero, `-0` normalizado somente no texto |
| A/B abstrato | Slot único por instância modelada, contexto/geração, bytes históricos completos, seleção mista, invalidação e descarte |
| Recursos | Preflight global de pares, majorante de candidatos, bit-length, limite cooperativo de operações e reservas de memória |

As áreas de duas faces são independentes e identificadas por ocorrência 1/2. A ordenação usa intervalos internos estritamente disjuntos. O formatter assinala quando a separação interna desaparece no arredondamento outward. Comprimentos E-E seguem a mesma regra de ordenação.

A translação global é ausente da API matemática porque cancela no mesmo objeto; no modelo A/B ela faz parte do token, de modo que sua mudança invalida a sessão. Coordenadas das duas entidades são reconstruídas com a primeira coordenada de A como âncora compartilhada. Não existem proxies de origens independentes comparadas diretamente.

## Evidência executada

Comando: `python run_offline.py --output evidence/work_run`.

- **44 métodos unittest, zero falhas e zero erros** na execução registrada. Subcasos são apresentados separadamente e não inflacionam esse total.
- Casos geométricos analíticos R8: distância 3-4-5, segmento finito vs prolongamento/raio, segmentos colineares e quase paralelos, cruzamentos de faces, contenção, L côncavo de área 7, áreas com rotação/reflexão/shear, coordenadas grandes e faces minúsculas certificáveis.
- **36 pares convexos determinísticos**, semente 73181, comparados por igualdade da distância ao quadrado com oráculo KKT racional independente; inversão dos operandos também verificada. É amostragem limitada, não exploração exaustiva.
- Duas diagonais admissíveis de um quad P: área 3D confrontada em Decimal de 100 dígitos e distância a superfícies levantadas confrontada com o oráculo KKT. A validação racional dos bounds é distinta dessa conferência Decimal.
- Controles negativos de triangulação: quantidade, orientação, índice e duplicação.
- Falha exclusiva de incerteza TOTAL de área: testada por **injeção explícita de um enclosure conservador mais largo**, preservando a distância V-F/E-F/F-F. Não se alega que esse caso foi observado naturalmente na aritmética de 192 bits.
- Falha do gate geométrico: recusa toda a consulta. Falha exclusiva da certificação da distância: áreas independentes podem continuar disponíveis, distância sem faixa.
- Sessões: mudança silenciosa de vértice, troca de ocorrências, `loop.edge` com endpoints iguais, flags dentro do clique, seleção oculta entre cliques, 30 áreas modeladas, contexto/unidades/geração, novo A e descarte após sucesso/erro/evento.
- Memória/custo: testes de preflight para 448/512/513 loops, 226×226 loops, 135 MiB de assinaturas apenas por contagens, limites globais e quotas aritméticas. **Não foram alocados 135 MiB para esse teste.**
- Inspeção AST do núcleo: nenhum import de Blender/rede/processos e nenhuma chamada direta aos primitivos de arquivo/avaliação listados no verificador. A inspeção é limitada; não é prova de no-write em Blender.

Arquivos: `tests.json`, `unittest.log`, `samples.json`, `static_inspection.json`, `allocation_samples.json` e `environment.json`. O runner permite replay sem rede e sem dependências externas.

## Recursos e concessões experimentais

O máximo provisório de 512 loops não é uma promessa de aceite: o modelo conservador de custo limita ainda mais consultas. O M0 reduz o envelope estrutural para 32 loops por face e mantém o teto de 200.000 candidatos; uma face de 32 loops já falha no custo atual, enquanto a amostra de 30 passou. Mantém 50.000 pares de triângulos, 128 MiB agregados como orçamento de projeto, 2 MiB por assinatura sintética, 2048 bits por entrada e 4096 bits nos resultados aritméticos guardados.

As amostras de área planar com 8/16/24/30 vértices passaram; 32 foi recusada no preflight. A instrumentação foi `tracemalloc` Python em fixtures isoladas e não mediu RSS. Valores brutos e duração estão no JSON. Não extrapolar essas amostras para todo o envelope ou Blender. A reserva de memória é um modelo de projeto com hipóteses explícitas, **não um limite real provado**. A insuficiência de prova operacional permanece um gate obrigatório anterior à integração real.

## Limitações que os auditores devem julgar

1. Certificados são sobre os valores representados fornecidos, não sobre a intenção decimal, a malha de modifiers ou a peça do slicer.
2. O caminho P exige que as coordenadas locais possam ser demonstradas como binary32 exato. Entradas racionais/double não representáveis em f32 são recusadas nesse caminho; faces exatamente planas não precisam desse diagnóstico P. O armazenamento Blender real continua desconhecido.
3. Cantos de contorno consecutivos colineares, inclusive redundantes válidos, são recusados conservadoramente neste M0; não são automaticamente diagnosticados como malha defeituosa.
4. A máquina de estado usa snapshots sintéticos imutáveis, duas leituras fornecidas pelo driver e IDs de contexto de teste. Não comprova callbacks, identidade RNA, imutabilidade real durante cálculo, seletores ou API `BMLoop.edge`.
5. O tipo `Certificate` e o formatter são interfaces internas: intervalos fornecidos externamente são **asserções do chamador**, não certificados geométricos autenticados. A evidência geométrica vem de `measure`, não de criar um objeto `Certificate` com números arbitrários.
6. Restrições de custo/bit-length e condicionamento podem recusar dados geometricamente válidos. Não houve calibragem de impressora, SLA ou benchmark de runtime real.

Essas limitações não autorizam enfraquecer o contrato normativo. A/B devem apontar qualquer discrepância bloqueante, inclusive insuficiência dos majorantes, em vez de presumir que o fechamento do M0 libera o M1.

## Estado de encaminhamento

Implementação e evidências congeladas para crítica independente A/B. O Master decidirá como incorporar os pareceres e se deve pedir correção M0. **Nenhuma próxima etapa foi autorizada pelo executor.**
