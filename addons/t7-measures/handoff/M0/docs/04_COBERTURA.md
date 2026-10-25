# Cobertura, evidências e pendências

Esta matriz descreve **o que os testes M0 fazem**, sem converter linhas de contrato em PASS de Blender. Os documentos originais completos estão em `inputs/normative/`. O contexto de aprovação é o arquivo `00_AUTORIZACAO.md`.

| Contrato/área | Evidência M0 | Limite |
|---|---|---|
| Oito modalidades / G01–G21 / G24–G26 | `GeometryTests`, `test_single_edge_and_ambiguous_order`; amostras das oito modalidades | Fixtures isoladas; modos de seleção reais não testados |
| G05/G05b/G05c, CP21 | Segmentos paralelos, cruzamento interno quase paralelo e folga z positiva, igualdade exata de distância quadrada | Não é prova exaustiva de todos os casos |
| G22/G23, UX19/UX20 | Repetição, bow-tie, retrocesso adjacente, contato endpoint-interior, deformação excessiva e singularidade | Recusa adicional de todo canto consecutivo colinear |
| G29/G30 | Área planar minúscula certificada racionalmente e apresentada sem falso zero | Difere de um caminho float sem certificado: aqui há prova exata; não usar esse caso para prometer precisão universal |
| G27/G31, CP01–CP05 | Perda de intenção em f32, grande offset racional local, âncora compartilhada, ordem invertida, resolução P após offset | Translação mundial cancela por definição da API; não se testou `matrix_world` real |
| G28/QP, CP09–CP10/CP15–CP16/CP24 | P com dados f32, duas diagonais, validação de tessela, rotação exata racional, 45° representada, shear/reflexão e NONE | Não há novas tesselas com Steiner; tipo de armazenamento Blender não verificado |
| CP11–CP14, D813–D816, R81-Q01–Q04 | Injeção declarada de faixa mais larga apenas na área; distância independente; falha geométrica global; distância sem certificado; faixa incluindo zero | Casos de incerteza TOTAL são enclosures conservadores injetados, não falha natural observada |
| CP06–CP08, UX13–UX15, D817 | Ordenação por intervalos disjuntos e aviso quando outward mascara separação; igualdade/contato das faixas não dá ordem estrita | Não foi construída uma busca exaustiva por inversão de áreas entre todas as diagonais P |
| UX01–UX12, D801–D808, R81-Q10–Q16/Q19–Q21/Q23 | Tipos inválidos, NaN/Inf, ausência de nominal, contradições, sub-q estrito, bounds outward e HALF_EVEN p=0/3/6 em quatro unidades | Formatter aceita certificados como asserções internas; não é verificador de origem geométrica |
| S19–S23, SN01–SN05, UX16–UX18, D809/D810, R81-Q05–Q07/Q22/Q24 proposto | Máquina sintética A/B: captura mista, ocorrência/loop.edge, histórico de bytes, mudança de geração, flags dentro/entre cliques, descarte | Não existe API de digest no modelo: uma colisão de digest não pode substituir a comparação de bytes; não foi simulado um hash real |
| D811/D812, R81-Q08/Q09/Q17 | Contagens de assinaturas coexistentes/transiente, orçamento agregado, 30 áreas e um dono, liberação lógica | Não mede retorno de RSS nem 30 janelas Blender |
| CP17–CP19, UX21–UX24, P01–P04/P06/P08 | Preflight por contagens antes de tessela; quotas de operações e bits; resolução armazenada | P05/P07/P09 de Blender e profiling nos tetos reais permanecem futuros |
| R01–R08, CP22, R81-Q18 | **NÃO EXECUTADOS**, fora do escopo autorizado | AST do núcleo só documenta ausência de imports/chamadas proibidas conhecidas |

## Oráculos

1. Analíticos fixos: valores exatos e distâncias quadradas previstas na matriz, sem chamadas ao algoritmo da candidata para gerar o esperado.
2. KKT racional (`tests/oracle_active_sets.py`): 36 pares convexos gerados com semente fixa, cobrindo V/E/triângulo; igualdade exata de distância quadrada. Não reutiliza auxiliares geométricos do núcleo.
3. Área P: soma independente dos triângulos levantados via Decimal de 100 dígitos, confrontada com a faixa conservadora, para as duas diagonais do quad fixture. Decimal é conferência numérica independente, não prova racional formal da raiz.
4. Negativos injetados: certificados de área alargados conservadoramente, certificação de distância indisponível, geração/ocorrências alteradas, orçamentos excedidos e tesselas inválidas. Os negativos têm asserções explícitas de recusa e não contam como resultados físicos válidos.

## O que a execução prova e o que não prova

O replay registrado demonstra que as asserções dos 44 métodos e seus subcasos passaram nessa plataforma e nessa candidata. Não demonstra cobertura completa das matrizes, correção formal do código inteiro, memória real de Blender, no-write em RNA/BMesh ou homologação. Cada lacuna acima deve ser julgada pelos auditores; a tabela não é uma dispensa de requisitos.

Os testes e evidências históricos do Master estão preservados no ZIP original. Não foram recontados como testes desta implementação. O arquivo `integrity.json` da execução de desenvolvimento antecede o manifesto final do pacote; `input_integrity.json` verifica a entrada original, e o replay da entrega verifica o manifesto final antes dos testes.
