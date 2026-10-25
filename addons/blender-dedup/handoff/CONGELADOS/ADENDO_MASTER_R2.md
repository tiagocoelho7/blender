# ADENDO MASTER R2 PROPOSTO - BLENDER DEDUP v1.0.1 (DOCUMENTAL)

**Status:** RASCUNHO PARA A/B, nao ratificado, nao modifica a especificacao R1-R5 nem o plano R1, nao e candidata executavel. 22/10/2026.

Este documento explicita COMO validar e impedir exclucoes inseguras sem prejudicar a remocao automatica de casos seguros. Onde a prova de integridade nao for possivel, parar todo o arquivo antes da primeira exclusao. Nao prometer inspecao completa de referencias em codigo Python arbitrario.

## AD-R2-01: fronteira, taxonomia e evidencia de referencias

Escopo investigado: TODOS os Objects MESH de `bpy.data.objects` e consumidores relevantes entre TODOS os IDs do blendfile. `keep`/`drop` sao calculados SEM depender da localizacao em scenes/collections. Fazer inventario DEPOIS de calcular candidatos e ANTES da primeira remocao; nao confundir animacao como criterio de identidade com driver como dependencia de referencia.

Para todo `drop`, registrar grafo de uso com campos:
- `drop_key` (identificador/snapshot da sessao, nome, tipo, ponteiro se seguro); `owner_key` (ID usuario e tipo), `owner_lifecycle` (KEEP/SURVIVE/DROP), `target_key`;
- `rna_path` (quando enumeravel), `source_surface` (Object/Constraint/Modifier/Driver/NodeTree/IDProperty/Collection/Scene/etc), `relation_category`, `scan_status`, `evidence`, `action`, `why`;
- inventario agregado das fontes inspecionadas e NAO inspecionadas, com contagem por tipo e justificativa.

Classificar cada caminho ou uso em UMA das classes:
1. `PERTENCIMENTO_AUTORIZADO`: vinculo simples Object <-> Scene/Collection, por si so nao bloqueia.
2. `FUNCIONAL_DIRETA`: referencia ID->drop partindo de entidade sobrevivente (child.parent, constraint target, modifier pointer, driver target, custom ID pointer etc) -> ABORTO GLOBAL.
3. `FUNCIONAL_INDIRETA`: drop pertence a Collection/estrutura de dados cujo conteudo e consumido por sobrevivente (Object.instance_collection; Collection Info de node tree usada por survivor; cadeia de instanciamento transitiva) -> ABORTO GLOBAL.
4. `INTERNA_A_REMOVIDOS`: relacao oriunda de ID que sera excluido e sem consumidor relevante sobrevivente, contanto que seja comprovada -> PERMITIR quando todo o restante for seguro.
5. `DESCONHECIDA`/`DESCOBERTA_INCOMPLETA`: fonte de uso, caminho RNA, consumidor, estado ou classificacao nao suficientemente identificados -> ABORTO GLOBAL.

Protocolo de cobertura exigido do executor:
- Enumerar IDs acessiveis em `bpy.data` por tipo, varrer ponteiros ID do RNA **inclusive colecoes/estruturas aninhadas relevantes**, IDProperties que armazenem IDs, drivers/variables, parents, constraints, modifiers, nodes/sockets e instance_collection. Documentar visitados, ignorados intencionalmente e nao suportados; deduplicar ciclos de introspeccao e limitar profundidade/trabalho com erro tipado.
- Usar `bpy.data.user_map()`/`ID.user_of_id()` como **verificacao cruzada agregada**, nunca como prova unica de path nem de semantica. Se existe usuario incompreendido, classificar DESCONHECIDA. Referencias por nomes em `Text`, drivers com expressoes arbitrarias e scripts Python externos NAO sao integralmente demonstraveis por varredura de ID pointers; nao alegar cobertura absoluta.
- Strings/scripts: ao encontrar no `.blend` expressao de driver ou Text com acesso potencial nao demonstravel por nome a Object/Collection, registrar como dinamico/incerto e ABORTAR antes de remocao quando possa atingir `drop`. A ausencia de scripts externos nao e demonstravel; documentar **risco residual externo** que requer consciencia do proprietario antes de producao. Nao prometer que um scan textual simples equivale a prova de inexistencia.
- Closure funcional: investigar referencias de sobreviventes a uma Collection transitivamente contendo `drop`, e a node groups/instancing que consumam seu conteudo. Separar membership comum de **conteudo consumido**. Ao falhar em determinar se um ID sobrevivente consome a Collection, ABORTO GLOBAL. Nao bloquear qualquer Collection comum por ser Collection.
- Se um owner nao-Object referencia um `drop` e permanece no arquivo, a classificacao deve ser conservadora; exemplos Material com driver target e node group, alem de parenting a EMPTY.
- NUNCA redirecionar referencias a `keep` apenas por equivalencia geometrica, pois G/R/S podem diferir. Nao remover/editar outros IDs em resposta ao plano.

**Critério de aceite:** fixtures fake cobrindo 1) par solto, 2) memberships normais multi-collection e multi-scene, 3) parent/constraint/driver em Material/custom ID/NodeTree, 4) instancing de Collection via EMPTY e via Geometry Nodes, 5) referencias de DROP a KEEP, 6) owner desconhecido e 7) falha ao enumerar; nos inseguros provar zero chamadas remove em todo o arquivo. Nao reivindicar que fake comprova RNA real do Blender.

## AD-R2-02: oraculo exato para geometria/topologia/winding

R1 permanece: duas malhas-base sao equivalentes quando EXISTE **uma bijecao global** dos vertices preservando (a) coordenadas quantizadas a 5 casas, (b) multiconjunto de arestas nao orientadas com multiplicidades, e (c) multiconjunto de faces entendidas como **ciclos orientados** modulo rotacao ciclica do indice inicial, SEM operacao de inversao de ciclo. A mesma bijecao deve valer para todos os elementos. Duplicacao de coordenadas NAO identifica vertices diferentes automaticamente.

Caso SEM-01: triangulo com 3 vertices coincidentes e faces [0,1,2] vs [0,2,1] pode ser equivalente pela bijecao global que troca 1 e 2. Isso NAO autoriza reverse de face na comparacao; explicita apenas a leitura consistente com permutacao arbitraria do R1. Para rejeitar isso sempre, seria preciso mudar a semantica R1 com autorizacao do proprietario.

Pre-filtros seguros: contagens, cores/coords, graus, incidencias/multiplicidades, componentes por **arestas E faces (hipergrafo)**, refinamento e SHA; so podem retornar negativo quando invariantes necessarios divergem. Nao usar histograma de coords, graus, hash ou WL como prova POSITIVA. Quando o filtro nao discrimina, usar verificador de isomorfismo orientado exato com testemunha de correspondencia global, ou retornar erro tipado INCONCLUSIVO por budget. Preservar loops longos, faces repetidas, arestas soltas, grafos regulares, vertices coincidentes, topologias distintas de mesma contagem. O algoritmo nao precisa construir uma forma canonica universal se o verificador exato e limitado por budget.

Precisao 5 casas: preservar comportamento de quantizacao da baseline ate alteracao formal verificada, registrar uso de float32 -> `np.rint(x*100000)` e os casos de fronteira; vetar NaN/Inf/overflow com aborto global. Nao afirmar igualdade em precisao nativa, apenas pela regra de quantizacao.

## AD-R2-03: budget de computacao, monitoramento e abortos

**Proposta de defaults iniciais para QA OFFLINE (aferir no hardware real ANTES de homologar):**

| Nome | Default proposto | Unidade/ponto de prova |
|---|---|---|
| `MAX_PLAN_SECONDS` | 300 | segundos monotonic, planejamento inteiro |
| `MAX_PAIR_SECONDS` | 45 | segundos monotonic, uma comparacao exata |
| `MAX_COMPARISONS_TOTAL` | 50000 | tentativas de comparar pares de malhas em todos os buckets |
| `MAX_SEARCH_STATES_TOTAL` | 2000000 | expansoes de busca/isomorfismo no arquivo inteiro |
| `MAX_SEARCH_STATES_PAIR` | 250000 | expansoes de busca em um par |
| `MAX_ESTIMATED_TEMP_BYTES` | 2147483648 | bytes de memoria temporaria estimada no plano |
| `MAX_ESTIMATED_PAIR_BYTES` | 536870912 | bytes temporarios estimados por comparacao |
| `MAX_BUCKET_CANDIDATES` | 2048 | candidatos em mesmo bucket grosso |

Esses numeros sao PROPOSTOS para verificacao dos auditores, NAO calibrados em Blender real e NAO equivalem a limite fisico garantido. Executor pode sugerir valores diferentes com evidencia e nova revisao, sem permitir fallback de exatidao. Importante medir CPU/RSS/pico estimado em fixtures grandes; `tracemalloc` nao contabiliza de modo completo toda memoria NumPy/nativa; operacoes NumPy grandes podem nao ser interrompiveis ate retornarem. Os limites nao garantem SLA ou imunidade a OOM do SO.

- Um **BudgetContext compartilhado** acompanha tempo total, tempo por par, comparacoes totais, estados totais/por par e estimativa cumulativa/peak de memoria de temporarios. Definir semantica alocada/liberada para evitar somar lixo ja coletado como pico. Nao fazer copia O(g^2) das classes ambíguas. Verificar limite antes de `np.empty`, ordenacao, construcao de estrutura de dados, recursao e loops grandes; checar monotonic periodicamente em laços Python e depois de operacoes vetorizadas.
- `ComplexityBudgetExceeded` ou status tipado equivalente NAO E `False` e NAO E `True`. `MemoryError`, erro de overflow, array invalido, referencia nao enumeravel, `KeyboardInterrupt` no preflight e erros de integridade encerram planejamento global antes da remocao (com tratamento coerente de excecoes sem esconder o erro). Proibir catch-all retornando booleano ou prosseguir para buckets seguintes.
- Separar FASE 1 (extracao, identificacao e verificador exato de TODOS os clusters) e FASE 2 (inventario completo de refs, elegibilidade e ledger), ambas sem mutacoes; somente depois FASE 3 remove sequencial. Se qualquer bucket tardio estourar o budget, **zero** `remove` em todo o arquivo, mesmo que grupos anteriores estejam prontos.
- Total do bucket pode exceder limite por invariantes negativos provados; caso nao haja separacao demonstravelmente exata e limite estoure, abortar, nao pular.

**QA obrigatorio:** custo K=6 e K=8 em classes sem matches, timeout interno em par tardio apos grupo seguro, overflow/NaN/Inf, OOM fake em prealocacao, limite global de pares, cancelamento de inventario, hash lento e qualquer erro antes do primeiro remove -> chamadas remove = 0. Distinguir `SEM_DUPLICATA` de `INCONCLUSIVO` no log e no retorno.

## AD-R2-04: matriz de elegibilidade por papeis (KEEP, DROP, Mesh)

| Estado | KEEP | DROP | Acao antes do primeiro remove |
|---|---|---|---|
| Object local, editavel, modo OBJECT e sem incoming funcional inseguro | Pode vencer R2 | Pode remover | Prosseguir, se todo o plano seguro |
| Object local e READONLY / is_editable=False | Pode permanecer como KEEP sem alteracao, sob prova | Nao demonstrado removivel | Se for DROP, aborto global |
| Object vinculado `library != None` | Pode permanecer como KEEP somente leitura | NAO elegivel por default | Se for DROP, aborto global |
| Object `is_library_indirect=True` | KEEP permitido como leitura se consistente | NAO elegivel por default | Se for DROP, aborto global |
| Object com `override_library != None` | KEEP permitido como leitura sem mudar | NAO elegivel por default | Se for DROP, aborto global |
| Object avaliado/runtime, referencia invalida, status desconhecido | Nao substituir outro vencedor | Nao remover | Aborto global quando afetar plano |
| Mesh datablock compartilhada | KEEP mantem Mesh, sem edicao | remover apenas Object comprovado seguro | NAO chamar `bpy.data.meshes.remove` |
| Object em varias scenes/collections comuns | Permitido | Permitido se sem dependencias funcionais | Registro do unlink, NAO veto por membership |
| Objeto em modo EDIT ou dados desatualizados | Nao confiar em snapshot | Nao remover | Aborto global ate modo seguro |

Ranking absoluto e deterministico: **mais modifiers > mais shape key blocks > nome alfabetico**, sem trocar o KEEP por um outro mais facil de remover. Se elegibilidade das fontes ou destinos nao for comprovada, aborto GLOBAL. Classificar combos contraditorios (linked+editavel, override+indirect inesperado) como desconhecido, sem inventar manipulacao de biblioteca. Mesh data linked/overrides e co-ownership devem ser inspecionados para nao danificar survivors; nao editar dados originais.

## AD-R2-05: ledger e falha de exclusao NAO transacional

Antes de remover qualquer objeto, capturar ledger/manifesto de keep/drop, hashes/checks e identidades disponiveis da sessao (nome, tipo, pointer/snapshot de objetos sem dereferenciar depois de removidos). Exibir no console imediatamente com flush; opcional export de log de texto/JSON sem salvar o `.blend`. Nao exigir confirmacao por objeto.

Em falha na chamada `objects.remove(drop, do_unlink=True)`:
1. Interromper imediatamente novas exclusoes. Nenhuma afirmacao de rollback ou atomicidade do Blender.
2. Nao acessar proxy `Object` potencialmente invalido depois do unlink; reenumerar `bpy.data.objects`, procurar cada identificador antigo por combinacao de snapshot de nome e pointer apenas se a API permitir e se nao houver indeterminacao por rename/reuso. Se nao se puder provar, informar `INDETERMINADO`.
3. Para cada drop, relatar `CONFIRMADO_REMOVIDO`, `CONFIRMADO_PRESENTE` ou `INDETERMINADO`, com contexto e numero de chamadas feitas; distinguir `remove` retornou sem erro de prova efetiva de ausencia.
4. Emitir erro operacional `FALHA_PARCIAL_POSSIVEL`, inclusive se a primeira chamada falhar depois de alterar a cena; nao salvar automaticamente. Handlers e callbacks podem invalidar snapshots entre preflight e exclusao, risco residual a testar no Blender real.

**QA:** excecoes fake antes e depois do efeito na 1a, 2a e ultima remocao, erro na reconciliacao, rename/reuso de proxy, fallo de log, e prova de zero exclusoes para erros que surgem nas fases de planejamento. Nao declarar lista exata onde a evidencia nao sustenta.

## AD-R2-06: matriz de QA, entrega e gates

- Estabilizar fixtures com oraculo independente, incluindo bijecoes POSITIVAS documentadas e NEGATIVOS certificados: 17-gon reindexado, 2 ciclos coincidentes, quantizacao, 6+8 vs 7+7, Rook vs Shrikhande, winding nao isomorfo de vertices distintos, triangulacao aplicada, SEM-01, n-gon 14+, arestas soltas/duplicadas, faces repetidas e conectividade por hiperarestas (faces sem arestas explicitas em mocks).
- Reexecutar TODOS os testes anteriores A/B sobre a **v1.0.1 nova**, alem de C01-C24 do B (apos validar em runtime legalidade de cada fixture). Cada tabela separa: PASS executado offline, falha fechada esperada, caso inconclusivo, oracle ainda nao testado, Blender real nao executado.
- Adicionar fixtures fake de Collection Info, instancing, drivers em Material, IDProperty aninhada, snapshots e modo EDIT; demonstrar que membership simples nao bloqueia e que dependencia funcional bloqueia globalmente. `Object` nao MESH intocado. Aplicar prioridade absoluta R2.
- Nova candidata e testes sao arquivos novos; baseline SHA `f4290a066e23c6a1089c67c88c13b633c4b017d823220240222c4ca78a479fb3`, especificacao SHA `2d1aa740b4ec7a42307dcec253fbce23f452ad45249fa35585bd12a6da0d3653`, plano original SHA `593ab739ebfbbbfa32e7d2f99dd568f56463081fb72c16cf53ba42cc46d2a839` permanecem imutaveis. Referencia de baseline no novo roteiro: `BASELINE/remover_duplicatas_blend_v1.py` (nao CONGELADO).
- Blender 5.0 real somente em `.blend` descartavel, com AUTORIZACAO EXPLICITA futura do proprietario. Nao acessar `.blend` reais/backup nem executar bpy nesta rodada. Sem autosave. Producao HOLD ate reauditoria cega A/B do codigo novo e gate Blender real.

## AD-R2-07: pendencias e fronteiras de confianca

- Esta e uma proposta tecnica de Master, nao uma mudanca de requisito do proprietario. A interpretacao de winding e coerente com R1, mas a alternativa de veto literal a orientacoes textuais reversas sob automorfismo exigiria sua decisao.
- Referencias pelo nome em scripts externos ou textos dinamicos NAO sao exaustivamente observaveis. A fronteira residual deve ser explicitada ao proprietario antes de producao; nenhum auditor pode prometer descoberta perfeita em toda automacao Python externa. A politica padrao proposta e conservadora: incerto detectavel -> aborto global.
- Os valores de budget sao sugestoes quantitativas verificaveis, sujeitos a calibracao. Um ABORTO por complexidade nao e falso negativo silencioso: o script nao declara ausente a duplicata, apenas recusa excluir sem verificacao.
- Qualquer item desta revisao que contradiga R1-R5 prevalece R1-R5 e retorna ao Master para nova decisao. Nao auto-ratificar adendo porque foi redigido pelo Master.
