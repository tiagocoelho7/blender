# T7 Measures — Matriz de aceitação SPEC-R8 (CANDIDATA)

**Status:** DOCUMENTO DE QA CANDIDATO para auditoria R8, NÃO testes do addon. **Run-time futuro exclusivamente Blender 5.2.2 LTS**, em `.blend` descartáveis e com autorização. Nenhuma linha representa prova de addon funcionando. Qualquer ensaio matematico offline tem escopo limitado ao contrato.

## Convenções de teste

Todas as coordenadas da tabela G são **mm físicos** no espaço de mundo, salvo especificação explícita BU. Em fixtures normais usar Scene `METRIC`, `scale_length=0.001` e `matrix_world=Identity`, portanto `1 BU = 1 mm`, a menos que indicado; criar vértices via meio de teste e **reler coordenadas realmente armazenadas** antes de comparar resultados. Os oráculos abaixo usam geometria matemática pretendida; tolerâncias para geometria armazenada bem condicionada/sem perda relevante: distâncias `τd=0.0001 mm` e áreas `τA=0.001 mm²`, com possibilidade de tolerância específica mais estrita em G-U/R. Essas tolerâncias **não** são epsilon geométrico nem promessa universal de medição. Em teste com precisão insuficiente, esperar aviso/recusa; nunca aumentar τ global para encobrir erro. Registrar erro absoluto, escala, magnitude das coordenadas lidas e runtime.

## G — Geometria e oráculos numéricos

| ID | Entrada/ação | Resultado esperado e armadilha |
|---|---|---|
| G01 V-V | V1=(0,0,0), V2=(3,4,0) | 5 mm |
| G02 V-E interno | P=(1,1,0), E=(0,0,0)→(10,0,0) | 1 mm |
| G03 V-E externo | P=(15,4,0), E=(0,0,0)→(10,0,0) | √41 = 6.403124237 mm, não distância ao prolongamento |
| G04 E-E cruzadas | E1=(-1,0,0)→(1,0,0), E2=(0,-1,0)→(0,1,0) | 0 mm |
| G05 E-E quase paralelas | E1=(0,0,0)→(1000000,0,0), E2=(0,1,0)→(1000000,1.001,0) | mínimo **1 mm** no oráculo analítico; não dividir cegamente por determinante cancelado. Em runtime, comprovar coordenadas armazenadas e incerteza; não aplicar τ normal como se fosse bem condicionado |
| G06 E-E colineares sobrepostas | E1=(0,0,0)→(5,0,0), E2=(2,0,0)→(7,0,0) | 0 mm |
| G07 E-E colineares separadas | E1=(0,0,0)→(2,0,0), E2=(5,0,0)→(7,0,0) | 3 mm |
| G08 E degenerada | E1 extremos coincidentes (3,3,3), E2=(0,0,0)→(3,0,0) | comprimento E1=0 com aviso; E-E=√18=4.242640687 mm se tratado como ponto; aceitar erro explícito se impossibilidade de construir E degenerada no Blender |
| G09 Área triângulo | F=(0,0,0),(30,0,0),(0,40,0) | 600 mm² |
| G10 Área após rotação | F de G09 rotacionada rigidamente por transformacao de OBJETO (malha local identica) | 600 mm² |
| G11 Área após transformação não uniforme | Tri local BU=(0,0,0),(1,0,0),(0,1,1), `matrix_world=diag(2,3,4)` e `scale_length=0.001` | 5 mm²; não usar determinante da matriz como fator de área |
| G12 Área após shear | Mesmo tri local, transformação `z_world=z+2x`, `scale_length=0.001` | √6/2 = 1.224744871 mm², embora determinante seja 1 |
| G13 F-F paralelas sobrepostas | Quad F1 xy=[0,2]×[0,2], z=0; F2 mesmo xy, z=5 | 5 mm |
| G14 F-F deslocadas | F1 xy=[0,2]×[0,2] z=0; F2 xy=[5,7]×[0,2] z=4 | 5 mm (3 lateral + 4 vertical), não 4 mm do plano |
| G15 F-F borda comum | Dois triângulos no mesmo plano que compartilham uma aresta | 0 mm |
| G16 F-F cruzam interior | F1=(-2,-2,0),(2,-2,0),(0,2,0); F2=(0,-1,-1),(0,1,1),(0,2,-1) | F-F=0; intersecao interna, sem vertices compartilhados |
| G17 F-F coplanares com cruzamento só de arestas | F1=(0,2,0),(-2,-1,0),(2,-1,0); F2=(0,-2,0),(-2,1,0),(2,1,0) | 0 mm; nenhum vértice está dentro da outra face; algoritmo só V-tri falha |
| G18 V-F finita | Tri F=(0,0,0),(2,0,0),(0,2,0); P=(2,2,3) | √11=3.316624790 mm, não 3 mm do plano infinito |
| G19 E-F cruza | F=(0,0,0),(10,0,0),(0,10,0); E=(2,2,-3)→(2,2,4) | 0 mm; atravessa o interior, pontas fora |
| G19b E-F falso raio | E=(0,0,0)→(0,0,1); F=(-1,-1,2),(1,-1,2),(0,1,2) | 1 mm; o **raio** toca, o **segmento** NÃO |
| G20 E-F coplanar dentro | Tri F=(0,0,0),(2,0,0),(0,2,0); E=(0.25,0.25,0)→(0.5,0.25,0) | 0 mm, contato por contenção, sem cruzar bordas |
| G20b E-F folga positiva | Mesmo E de G20 com z=0.01 | 0.01 mm; não zerar por ε indiscriminado |
| G21 Côncava plana | L em xy=(0,0),(4,0),(4,1),(1,1),(1,4),(0,4), z=0; P=(2,2,1) | área 7 mm² (16−9); V-F=√2 = 1.414213562 mm; convex hull/plano infinito erram |
| G22 N-gon muito torcido | Q=(0,0,0),(1,0,0),(1,1,1),(0,1,0) | fora de tolerancia P, recusar area e quaisquer distancias F, sem resultado parcial enganoso |
| G22b N-gon planar rotacionado | Face côncava L de G21, rigidamente rotacionada via matriz do OBJETO (sem regravar vertices de Edit Mode) | área 7 mm² e ponto correspondente rotacionado com mesma distância √2 |
| G23 Face inválida | vértices coincidentes, face colapsada, contorno autointersectante, NaN/inf, ou face pós-transformação degenerada | erro diagnóstico, sem NaN, `0 mm²` inventado ou crash |
| G24 Contenção coplanar | Tri grande=(0,0,0),(10,0,0),(0,10,0); tri pequeno=(1,1,0),(2,1,0),(1,2,0) | F-F=0 sem exigência de cruzamento de arestas |
| G25 Contato só em vértice | Segmento termina exatamente num vértice da face, sem penetração | E-F=0 |
| G26 Positivo abaixo da exibição | V-V=0.00049 mm, preferência 3 casas | mostrar `0 < d < 0,001 mm` SOMENTE se o limite superior certificado `d_U<0,001 mm`; conservar valor interno positivo; não `0,000 mm` como contato |
| G27 Mal condicionado local | Números hipotéticos f32 `10000 BU` e `10000.0004 BU`, `scale_length=1` | não prometer recuperar diferença pretendida 0.4 mm se ambos forem armazenados iguais; explicitar limitação de representação, verificar runtime e adaptar oráculo a bytes lidos |
| G28 Plano vs P | Quad Q=(0,0,0),(1,0,0),(1,1,0),(0,1,0); variante com terceiro vertice z=2e-6 mm | Q EXATA; variante quase plana pode ser APROX com certificado de h, R, ΔA e aviso; NAO tratar como area exata |
| G29 Área degenerada minúscula | Tri=(0,0,0),(1,0,0),(2,1e-12,0) mm | sem falso número de precisão alta; conforme regra de condicionamento, erro/indeterminação |
| G05b E-E almost-parallel crossing | E1=(0,0,0) -> (1000000,0,0); E2=(0,-0.0005,0) -> (1000000,0.0005,0) | 0 mm no cruzamento **interno** em x=500000; nao usar denominador float que arredonda a zero para declarar gap falso |
| G05c E-E almost-parallel separated | E1 como G05b; E2 deslocada +0.002 mm em z | distancia positiva 0.002 mm; sem falso contato por epsilon de UI |
| G28b Rigid object rotation | Q plana e Q quase plana de G28, com transformacao de **objeto** rotacional de 45 graus (BMesh local identico) | classe exata/aproximada invariante dentro dos certificados; area da plana preservada, independentemente de AABB mundo |
| G28c Microface twisted | Q=(0,0,0),(s,0,0),(s,s,3e-6),(0,2s,0), s=1e-6 mm | recusar P pela cota de erro relativo de area e/ou geometria numericamente mal condicionada; tau de altura SOZINHA nao basta |
| G30 Face near-degenerate strict planar | triangulo com area matematica 5e-13 mm2, coords armazenadas auditadas | plana por 3 vertices se nao colineares; area numerica so se demonstravel, caso contrario indeterminado, nunca zero silencioso |
| G31 Translation cancellation | dois vertices locais com delta 0.001 BU, objeto translacao mundo 1e7 BU, parte linear identidade | distancia fisica calculada por `M3*delta`, sem conversao prematura a f32 de pontos mundo; se delta ja foi perdido na malha, nao inventar valor |
| G32 Singular transform | malha planar com escala zero em um eixo relevante | recusa diagnostica como transformacao degenerada, sem area/distancia enganosa |


**Nota neutra G21:** o L desta matriz tem area 7 mm2 (4x4 - 3x3); nao reutilizar oraculos de geometria diferente.


## QP — Planaridade prática P, area e distancia de faces (introduzida R5, mantida R7)

Para QP, a geometria usada como fixture teórica nao substitui a geometria binary32 efetivamente observada no Blender. Em runtime reler coordenadas; separar testes de `Object Mode` (matriz M3) de `Edit Mode` (regrava vertices). Os pisos/caps/teto de area sao **propostos** e passíveis de auditoria A/B. Todas as inequacoes precisam ser testadas com limites arredondados para fora, nao so `float` normal.

| ID | Caso | Oraculo/aceite documental proposto |
|---|---|---|
| QP01 | `L=10 mm` | `tau=0.001 mm`; `L=5000 mm` => `tau=0.005 mm`; `L=20000 mm` => `tau=0.010 mm` |
| QP02 | `L_BU=1`, Scene `NONE` | `tau_BU=0.000001 BU`, **sem** inferir equivalencia em mm |
| QP03 | Quad xy=10x10 mm, z do terceiro vertice = +0.0002 mm | `PLANAR_EXATA` falha se armazenamento preservar torcao; P admissivel somente se h/R/ΔA/contorno passam; apresentar area ~ e intervalo |
| QP04 | Mesmo quad com z do terceiro vertice = 0.05 mm | h deve exceder tau (ou provar outra recusa); nenhum numero P |
| QP05 | Quad pequeno s=0.001 mm e torcao=0.0003 mm | tau de h isolada pode passar; gate `ΔA <= 0.01 A_Q` deve impedir falsa area precisa |
| QP06 | Quad QP03 rotacionado rigidamente por `matrix_world`, malha local intacta | classe P, area nominal e limites invariantes dentro de erro certificado; nao projetar por AABB |
| QP07 | Quad de QP03 deslocado por translacao de Object Mode de `+1e8 BU` | distancias/area usam deltas relativos; sem cancelamento por ponto absoluto global |
| QP08 | Face P distancia a plano/paralelo separado nominalmente 5 mm | intervalo real `[max(0,dQ_L-h), dQ_U+h]`; positivo so com limite inferior >0 |
| QP09 | Face P quase toca outra; `dQ_L<=h` | intervalo inclui zero: mostrar `Contato/folga indeterminados`, NUNCA `0 contato` |
| QP10 | Duas faces P com envelopes hA,hB | `H=hA+hB`, usar soma; 1 so h nao basta |
| QP11 | Face P com vertices quase duplicados, autointersecao na projecao, area Q=0 | REJEITAR, mesmo se h<=tau |
| QP12 | R_U maior que tau/4 por coordenadas locais f32 enormes | REJEITAR `Resolucao de malha insuficiente`; nenhuma precisao recuperada de valores pre-arredondamento |
| QP13 | Face P de 513 loops e face limite de 512 loops | preflight antes de projeccao/pares; QP custo de diametro L=130816 pares quando n=512 |
| QP14 | Dois caminhos possiveis de triangulacao de um quad quase plano | valor nominal A_Q independente de diagonal; ambas areas 3D reais pertencem a `[A_Q,A_Q+D_A]` |
| QP15 | Valores de h/R/area exatamente nos limiares com intervalos que atravessam a fronteira | so aceitar se desigualdades certificadas; se incerto, INDETERMINADO e nao "arredondar para dentro" |
| QP16 | Alterar scale_length sem alterar malha, em METRIC | os numeros mm/tau podem mudar conforme escala; A/B deve verificar nao invariancia esperada sob alteracao de unidade FISICA |
| QP17 | Combinar face P e face plana, A/B, ocultar A entre capturas | distancia no intervalo, metadados historicos e sem acesso a wrapper antigo |
| QP18 | Limiar h=0 e face realmente planar | preferir rota EXATA: sem aviso P e sem area proxy desnecessaria |

## U — Unidades, transformações e apresentação

| ID | Condição | Aceite |
|---|---|---|
| U01 | E world = 0.01 BU; METRIC scale_length=1 | 10 mm |
| U02 | E world = 10 BU; METRIC scale_length=0.001 | 10 mm |
| U03 | Área world = 0.0002 BU²; METRIC scale_length=1 | 200 mm² |
| U04 | Parent, matriz não uniforme, shear e escala não aplicada | todos os pontos são transformados em mundo antes de medir; não aplicar transforms no objeto |
| U05 | Reflexão world com escala negativa | área/comprimentos positivos |
| U06 | Scene system=NONE; scale_length=0.001; aresta world=10 BU | `10 BU`, aviso de unidade física indefinida, nunca mm |
| U07 | METRIC ou IMPERIAL scale_length=0.01, 1 BU | 10 mm, `length_unit` não altera fator |
| U08 | `scale_length<=0` ou NaN/inf em sistema físico | recusa de medida física, sem número inventado |
| U09 | Decimal 0/3/6 em gap pequeno positivo e em zero real | 0 só significa contato confirmado; positivo abaixo da resolução explicitado; indeterminado sem zero |

## S — Seleção, sessões, capturas e atualidade

| ID | Passos | Aceite |
|---|---|---|
| S01 | FACE ativa implica V/E selecionados implicitamente | 1 face produz área; não contam V/E |
| S02 | VERT+FACE simultâneo | erro `Modo combinado indisponível`, não mudar seleção |
| S03 | Seleção vazia, 3 elementos, não Mesh ou não Edit | erro sem resultado novo |
| S04 | VERT 2; EDGE 1 e 2; FACE 1 e 2 | todas as 5 saídas diretas conformes |
| S05 | Capturar V A, mudar apenas seleção/mode, capturar E B | V-E calculável sem invalidação por seleção |
| S06 | Capturar V A, mudar apenas seleção/mode, capturar F B | V-F calculável sem invalidação por seleção |
| S07 | Capturar E A, mudar apenas seleção/mode, capturar F B | E-F calculável sem invalidação por seleção |
| S08 | Capturar A em x=0; mover este mesmo V para x=10; capturar B em x=1 | invalidar A/B, **não** apresentar híbrido 1 mm; com recaptura distância corrente =9 mm |
| S09 | Capturar A x=0, mover A para x=10, capturar B x=20 | invalidar A/B, não rotular híbrido de 20 mm como atual; corrente=10 mm |
| S10 | Capturar A, modificar apenas matriz de objeto/parent/driver, sem editar vertex | invalidação por verificação atual antes de B/cálculo |
| S11 | Troca Scene, sistema/unidade, View Layer ou objeto homônimo/substituído | invalidar slots, mesmo que nome coincida |
| S12 | Undo, Redo, load outro arquivo, unregister e reload | invalidar; nenhuma referência BMesh obsoleta ou callback residual |
| S13 | Dois VIEW_3D em janelas diferentes; A janela1, B janela2 | isolamento por janela+área; nunca mistura |
| S14 | Dois objetos em multi-edit usando o MESMO datablock mesh | bloquear por `objects_in_mode>1` |
| S15 | Hidden `select=True` residual | ignorar seleção oculta e não desocultar/mudar flags |
| S16 | Duas arestas/faces selecionadas via box select em ordem inversa | rotular como Aresta 1/2 ou Face 1/2; mostrar `menor/maior` SOMENTE com limites certificados estritamente disjuntos, senao ordem indeterminada |
| S17 | Resultado 5 mm, usuário troca seleção e não clica | texto continua `Última medição — instantâneo`, nunca `medida atual` |
| S18 | Clique com nova seleção inválida ou acima de limite | limpa resultado novo, exibe erro, sem reaproveitar número antigo |
| S19 | Apenas seleção/`mesh_select_mode` muda entre A e B, sem geometria | assinatura de geometria igual e captura ainda válida |
| S20 | Um vértice não relacionado ao par muda entre A/B | fingerprint global detecta, falha fechado (política conservadora R4) |
| S20b | Capturar A no vertice ordinal 0 em (0,0,0) e B mais tarde; trocar coordenadas de v0 e v1=(10,0,0), conectividade inalterada | fingerprint por ocorrencia muda; invalidacao mesmo que multiconjunto ordenado por coordenadas seja igual |
| S20c | Dois vertices coincidentes com conectividades distintas; ou faces com mesmos multiconjuntos de vertices mas ordem de loops diferente | digest diferente quando ocorrencias/conectividade diferem, ou falha fechada |
| S21 | Capturar A; trocar frame e retornar; avaliar constraint/driver com `matrix_world` avaliada divergente | invalidar por evento/geracao temporal; nao misturar estado proprio e avaliado |
| S22 | A e B em janela que foi fechada e area recriada com token reaproveitado | negar reutilizacao, mesmo nome/contexto aparentemente semelhante |
| S23 | Captura A: mutacao de geometria entre snapshot inicial/final simulada no harness descartavel | S1 != S2 implica erro e descarte; nao publicar slot ou valor parcial |
| S24 | Undo/Redo ou load apos medicao direta rotulada instantaneo | esconder/inutilizar instantaneo e A/B ao detectar o evento; sem polling permanente |

## R — Segurança somente leitura e integração futura (AINDA NÃO EXECUTADOS)

| ID | Ensaio Blender 5.2.2 LTS, autorizado no futuro | Critério de GO de implementação |
|---|---|---|
| R01 | 100 medições em `.blend` descartável; controle sem addon | snapshot canônico de geometria, seleção, hide, IDs, shape keys, attrs, modifiers, mat/Scene/unidades sem diff causado pelo addon |
| R02 | Capturar A, B, calcular e limpar; Undo após edição real de usuário | nenhum passo extra de Undo; edição real é desfeita, sem stale BMesh |
| R03 | Negativos que mudam 1 vértice, flag, modifier e unidade (somente cópias) | coletor detecta todos os controles positivos de escrita |
| R04 | Save/reload controle e experimento | sem objeto auxiliar, layer, anotação, custom property nem medição persistida; sem confiar só no SHA binário do `.blend` |
| R05 | register/unregister 10 vezes, duas janelas, load e troca de workspace | sem callbacks, handlers, timers, classes ou slots vazados |
| R06 | Modifiers ativos/inativos e shape keys, edit cage | aviso certo e medição da geometria REALMENTE lida no BMesh, sem prometer malha final/slicer |
| R07 | `bpy.app.version` e `version_string`, build exata, instalação de extensão e manifesto | PASS somente em 5.2.2 LTS; versão diferente bloqueada como não homologada |
| R08 | Auditoria estática de setters RNA/BMesh, bmesh.ops, UI hooks e operadores | nenhuma escrita escondida, nenhum UNDO flag, nenhuma conversão que grave no mesh ativo |

## SN — Selecao, incidencia e apresentacao: casos adicionais R5

| ID | Caso | Aceite |
|---|---|---|
| SN01 | Duas ocorrencias distintas de aresta com mesmos endpoints; mudar somente `BMLoop.edge` | assinatura versionada DIFERENTE, ou recusar topologia se representacao Blender real inviavel; sem falso frescor |
| SN02 | Mesmo snapshot geometrico, `select` trocado entre S1 e S2 no mesmo clique | abortar, limpar resultado novo, nao publicar snapshot antigo |
| SN03 | Mesmo snapshot geometrico, `hide` trocado entre S1 e S2 | abortar |
| SN04 | Capturar A visivel, ocultar A **entre cliques**, capturar B visivel, geometria intacta | A historico permanece valido; rotulo `Captura historica, pode estar oculta` |
| SN05 | `select`/modo troca entre A/B, geometria intacta | permitir; flags nao entram no fingerprint persistente |
| SN06 | `p` = 0,1,2,3,6; nominal de distancia positivo arredonda visualmente a zero | `0<d<q` **somente** com faixa real conservadora finita `0<d_L<=d_U<q`; se `d_U>=q`, exibir positivo certificado + faixa outward, **jamais sub-q**; se `d_L=0`, indeterminado com faixa; sem bounds, sem numero. `q=10^-p` na unidade apresentada, nao contato por formato. Confrontar UX01/UX03. |
| SN07 | `p`=0/3/6; nominal de area pequena, inclusive `NONE` | `0<A<q` em `mm2`/`BU2` **somente** com `0<A_L<=A_U<q`, bounds outward e **gate de apresentacao de area P valido**, quando aplicavel. Se `A_U>=q`, vedado sub-q; se area P nao passou gate total, sem nominal; `A_L=0` nao permite positivo. Confrontar UX10/UX11/UX12. |
| SN08 | Intervalo P `[0,0.0004 mm]`, p=3 | estado indeterminado; intervalo arredondado PARA FORA; jamais `0 contato` |
| SN09 | README/prompt identifica exatamente os nomes existentes | navegacao sem README ausente |
| SN10 | Verificador externo altera uma coordenada ou uma incidencia entre operacoes | mutacao realmente detectada pelo teste de controle positivo |

## P — Performance e falha fechada (AINDA NÃO EXECUTADOS)

| ID | Situação | Aceite |
|---|---|---|
| P01 | Face selecionada com 513 loops | preflight recusa ANTES de triangulacao/tessela; fixture com 512 loops passa somente na cota de LOOPS, nao passa automaticamente no preflight GLOBAL de custo, condicionada a validade geometrica |
| P02 | Duas faces com 224 triângulos cada (`224×224=50.176` pares) | preflight recusa F-F antes dos laços `triA×triB` |
| P03 | A/B em mesh com `n_verts+n_edges+n_faces>500000` | preflight recusa captura sem congelar a viewport e sem slot parcial |
| P04 | A/B em mesh com `n_loops>1000000` | idem |
| P05 | 100 consultas em malha pequena no Blender 5.2.2, hardware documentado | tempo por clique registrado, sem timer/frame; não assumir SLA antes de benchmark |
| P06 | Estimador de memória temporária >128 MiB | recusa prévia; medir memória para aferir estimador |
| P07 | Memoria A/B para `Nv+Ne+Nf` grande, `Nloops` grande, abaixo dos tetos numericos | estimador da R8.7 pode recusar **antes** do fingerprint; medir pico RSS/alloc; proibir alegar que 128 MiB e garantia sem ensaio |
| P08 | F-F com faces de n=226 loops cada, `ntri<=224` | bound 224x224=50176 >50000; deve recusar antes de tesselar |
| P09 | 25%, 50%, 90%, 100% de cada cota (malha global, loops, area, par de triangulos) | registrar hardware Blender 5.2.2 e RSS/pico/wallclock; acima do orcamento deve falhar fechado |

## Critério de classificação do QA

- **GO de um caso**: oráculo demonstrado sobre dados armazenados, diagnóstico correto e read-only verificado; tolerâncias numéricas específicas apenas para fixtures bem condicionadas.
- **HOLD**: número incorreto, dado ambíguo apresentado como certo, falta de invalidação de A/B, escrita indevida, regressão de seleção ou custo sem preflight.
- **INCONCLUSIVO**: a build não foi executada, não foi possível controlar armazenamento/condicionamento, ou a ferramenta de teste não comprova o que afirma.

A matriz NAO contém testes executados contra implementação: ainda não existe candidato de addon. Os scripts `qa_r6_fixtures_documentais.py` (baseline R6), `qa_r7_ux_cases.py` (baseline R7) e `qa_r8_delta_contracts.py` (delta R8) demonstram apenas desigualdades, exemplos e propriedades abstratas **independentes** da implementação, nao prova API, area/distance certificados, no-write ou latencia. Nao somar seu numero de PASS a testes de Blender.


## R8-CP — Casos adicionais vinculantes (a auditar, nao sao testes de addon)

| ID | Fixture/oraculo independente | Passa SOMENTE se... |
|---|---|---|
| CP01 | Quads identicos z=0 e z=5 mm; calcular com duas ancoras locais distintas como contraprova negativa | Consulta reconstroi uma origem local compartilhada e distancia certificada 5mm, nunca zero falso. |
| CP02 | Duas faces P separadas 5mm, inclinar uma z=0.0002mm | Intervalo certificado nao pode excluir a distancia real, limite inferior >4.999mm no fixture; comparar com lower bound analitico >=4.9998mm. |
| CP03 | V/F e E/F, face z=0 e V/E z=5; capturas A/B em cliques separados | Compensacao de offset impede que faces e V/E sejam confundidos em origem zero; distancia 5mm. |
| CP04 | Reverter ordem de capturas A/B e de faces no mesmo objeto, sem mudar malha | O referencial pode mudar mas o intervalo final continua conservador e a decisao de contato/folga nao muda. |
| CP05 | Grande translacao apenas no Object Mode e depois por vertices locais com compensacao | A translacao global pura cancela; a translacao local pode ser recusada por representabilidade `R_U`, com aviso e sem falso numero. |
| CP06 | Faces P f32 com ordem proxy A_Q(A)>A_Q(B), mas areas trianguladas de B maiores | Nenhum rotulo menor/maior sem prova por intervalos disjuntos; mostrar ordem indeterminada. |
| CP07 | Intervalos A=[1,1.005] e B=[1.004,1.006] mm2 | Ordem indeterminada, nao confundir nominal com area exata. |
| CP08 | Intervalos A=[1,1.01], B=[1.02,1.03] mm2 | A menor que B certificado; inversao de operandos muda apenas identificador, nao regra. |
| CP09 | Quad original com duas diagonais de triangulacao valida | Exatamente n-2 triangulos, sem Steiner, cobertura Q, limites A_Q<=A_T<=A_Q+D_A. |
| CP10 | Contorno original com vertice interior livre elevado em z sem cota | Fora da classe admissivel; nunca usar formula n-2 nem distancia Hausdorff sem nova prova. |
| CP11 | Certificado numerico enorme `A_Q,L=.999`, `A_Q,U=1e6`, D_A=.001414 | Recusar o nominal A_Q; gate total de largura falha, mesmo quando gate geometrico parcial passa. |
| CP12 | `A_L=100`, `A_U=100.99` mm2, D_A<=1 | Gate total de 1% passa somente se todos os componentes outward sao demonstrados. |
| CP13 | Intervalo de distancia certificado `[0,0.0004]`, p=3 | `INDETERMINADO_COM_FAIXA`, limite superior outward `0.001`mm; nenhum contato nem nominal. |
| CP14 | Falta intervalo numerico confiavel para Q | `INDETERMINADO_SEM_FAIXA`, sem d pontual nem bounds ficticios. |
| CP15 | Certificado de `||N||` inclui zero por cancelamento | Recalcular exatamente com prova de >0 ou recusar; nunca normal float sem certificado. |
| CP16 | Face muito fina com condicao de area instavel e matriz shear/reflexao | Exigir `A_Q,L>0`, contorno valido, bounds de transformacao, ou recusar sem numero. |
| CP17 | Uma face P n=512, Ccontorno=130304 e Cdiametro=130816 | C_total >=261120 >200000, portanto preflight recusa antes de processamento. |
| CP18 | Uma face P n=448, Ccontorno+Cdiametro=199808 | Essa parcela cabe no teto, mas somar C_outros aplicaveis pode recusar; nao confundir com garantia de aceitacao. |
| CP19 | Duas faces F-F cujos triangulos gerariam >50000 pares | Preflight `C_triangulos<=50000` e `C_total<=200000`, ambos obrigatorios. |
| CP20 | Origem/rotação/scale_length alterados entre capturas ou durante um clique | Invalidar snapshots e nao publicar numero; NUNCA recombinar matrizes de instantes diferentes. |
| CP21 | Sinais robustos para contato de segmentos E-E colineares/crossing | Zero somente por prova topologica; incerteza -> desconhecido, nunca usar epsilon de contato. |
| CP22 | Adaptador Blender 5.2.2 com BMLoop.edge, loops, RNA e modo selecao | Teste futuro, somente com autorizacao; snapshots before/after e controles positivos no-write. |
| CP23 | Testes independentes por Fraction/Decimal/intervalar, rotacoes e coordenadas enormes | Nao basta reexecutar funcao do Master ou outro oraculo usando a mesma implementacao. |
| CP24 | Matrizes/shear, unidades NONE e imperial, forma local binaria preservada | Certificar mesma transformacao em ambos operandos, exibir BU sem escala fisica quando NONE. |

**Nota de aceitacao R7:** Os fixtures CP01-CP05, CP06-CP10, CP11-CP16 e CP17-CP21 devem ser avaliados independentemente na auditoria documental A/B. CP22 e parte da futura homologacao real, NAO autorizada. CP23 e metodologia, nao prova de testes ja executados. Todos os numeros e limites propostos exigem criticismo independente, especialmente o novo limite total de 1% de area.


## R8-UX — Casos vinculantes do delta R6 -> R7 (nao substituem regressao R6)

**Status:** criterios de aceitacao documental e de futuro QA de codigo; executar o script offline de apoio em copia descartavel NAO valida um addon inexistente. Em toda exibicao `q=10^-p` na unidade mostrada; intervalos sao certificados internamente antes de qualquer formatacao.

| ID | Caso adversarial | Aceitacao vinculante |
|---|---|---|
| UX01 | `p=3`, `q=.001`, nominal `.0004`, `[d_L,d_U]=[.00025,.00135]` | Positivo certificado e faixa outward; **PROIBIDO** `0<d<.001` |
| UX02 | Igual a UX01 com limite superior `.0009` | `0<d<.001` PERMITIDO se limite superior estrito comprovado |
| UX03 | Igual a UX01, mas `d_U=.001` | `0<d<.001` PROIBIDO na igualdade; usar faixa ou desigualdade nao estrita explicitamente certificada |
| UX04 | Valores de UX01 escalados para `p=0` | Com q=1, faixa cruza q; sub-q proibido |
| UX05 | Valores de UX01 escalados para `p=6` | Com q=.000001, faixa cruza q; sub-q proibido |
| UX06 | Certificado `[0,.0003]`, `p=3` | `INDETERMINADO_COM_FAIXA`, sem contato ou nominal |
| UX07 | Bounds ausentes/NaN/inf | `INDETERMINADO_SEM_FAIXA`, sem numero |
| UX08 | `CONTATO_CERTIFICADO` independente, mesmo com intervalo outward positivo aparente por bug | Exigir prova de contato verdadeira; divergencia entre certificados => rejeitar, nao forcar contato |
| UX09 | `d_U=0` obtido apenas por arredondamento de exibicao | Nao equivale a prova de contato |
| UX10 | Area plana muito pequena, `A_L>0`, `A_U>=q` | Nao mostrar `0<A<q`; exibir area positiva e intervalo |
| UX11 | Area P com `A_L>0`, `A_U<q` e gate total valido | `0<A<q` pode ser exibido com unidade quadrada e aviso de aproximacao |
| UX12 | Area P com `A_L=0` | Recusar area positiva certificada/nominal, diagnostico sem area enganosa |
| UX13 | A=[1.0001,1.0040], B=[1.0041,1.0080], p=2 | Ordem A<B certificada internamente, mas limites outward sobrepoem na tela: aviso visivel ou detalhe verificavel |
| UX14 | Faixas disjuntas inclusive apos exibicao | Ordem certificada sem aviso extra, pela decisao interna |
| UX15 | Faixas que apenas se tocam internamente (`A_U=B_L`) | Ordem estrita **indeterminada** |
| UX16 | Mesmos vertices, mas alteracao de ordinal `loop.edge` | Serializacao canonica diferente invalida mesmo se digest parcial colidir |
| UX17 | Forcar colisao artificial de digest com bytes de assinatura diferentes | Nao confirmar identidade sem comparar bytes canonicos completos |
| UX18 | Assinaturas canonicas identicas, geracao diferente por Undo detectado | Invalidar captura pelo token/geracao, nao pela igualdade binaria isolada |
| UX19 | Arestas adjacentes colineares retrocedendo e sobrepostas | Contorno NAO simples, recusar antes da tessela |
| UX20 | Contato nao-adjacente apenas endpoint-interior e vertices duplicados | Contorno invalido, recusar; nenhum teste so crossing transversal aceita |
| UX21 | n=448, P, `C_contorno+C_diametro=199808`, mas >=448 adjacencias | Soma `C_outros` ultrapassa 200000; nao confundir limite de loops com aceite |
| UX22 | n=512, P | Recusar: 261120 pares principais >200000, ainda sem `C_outros` |
| UX23 | `R_U>tau/4` por grande magnitude de coords f32 locais | Recusa segura com diagnostico resolucao armazenada, sem proposta de edicao automatica |
| UX24 | Face extremamente longa e fina, h<tau, mas `D_A/A_Q,L >1%` | Recusa conservadora e aviso de limite relativo de area |
| UX25 | Cross p/intervalo outward no sistema `NONE` | Unidades BU/BU²; nunca converter para mm sem escala metricamente fundamentada |

**Gate futuro:** perfilar bit-length de predicados, picos de RAM e latencia do scan/assinatura em Blender 5.2.2 LTS autorizado, com controles no-write positivos e negativos; nenhuma prova neste documento substitui esses testes reais.


## R8-DELTA — Contratos especificos de reauditoria R7 -> R8 (vinculantes)

| ID | Fixture | Aceitacao |
|---|---|---|
| D801 | `p=3`, nominal `.0004 mm`, certificado `[.00025,.00135] mm` | SN06/UX01/contrato R8.5 concordam: positividade + faixa outward, **nao** `0<d<.001` |
| D802 | Igual D801, mas `d_U=.0009` | Sub-q permitido **somente** se limites certificados e gatilhos atendidos |
| D803 | Igual D801 com `d_U=.001` | Limite igual a q proibe desigualdade estrita sub-q |
| D804 | `p=0` e `p=6`, limites atravessam q | A mesma proibicao, independente de unidade fisica |
| D805 | Area `BU2`, `p=0`, nominal `.4`, bounds `[.25,1.35]` | SN07/UX10 concordam: nao anunciar `0<A<1 BU2` |
| D806 | Area P com bounds inteiramente sub-q mas gate total de 1% falha | Nao publicar nominal, mesmo com bounds sub-q; gate P vem antes |
| D807 | Empate exato `q/2`, p=0/3/6, HALF_EVEN | Resultado nominal coerente em todos os casos; outward nos bounds independente |
| D808 | Numeros representados imediatamente abaixo/acima de `q/2` | Nenhuma escolha de arredondamento invalida condicao geometrica; sem precisao confiavel usar faixa/diagnostico |
| D809 | Capturar A, commit A, alteracao silenciosa em revisao global, forcar colisao **sintetica** de digest antes de B | `S_A` completo ainda retido; B compara bytes e recusa `S_B != S_A` apesar de digest e geracao iguais |
| D810 | Capturar A, B, alterar revisao sem callback, clicar Calcular com digest sinteticamente igual | Calcular compara S1/S2 e `S_A`; recusa diferenca de bytes |
| D811 | `S_A` valido + S1 + S2 simultaneos, pico acima de 128 MiB | Recusa antecipada; preflight inclui memoria simultanea, **nao** apenas um hash |
| D812 | Sucesso em Calcular, erro, Limpar, Undo/Redo, unregister | Liberar `S_A` + slots A/B e nao deixar buffers retidos; novo calculo precisa recaptura |
| D813 | Face P valida no plano/proxy/gate geometrico, mas **gate total da area** falha; intervalo de distancia F-F independente valido | Sem area nominal dessa face; distancia intervalar P pode ser mostrada **com bounds visiveis**, sem contato inventado |
| D814 | Gate GEOMETRICO parcial `D_A` da face P falha; F-F | Recusar **consulta inteira**, sem distancia numerica mesmo que Q aparente computavel |
| D815 | Areas validas, distancia F-F nao certificada | Areas individuais podem ser apresentadas com seus estados; sem numero de distancia nem valor antigo |
| D816 | Distancia F-F P `[0,u]` certificada | Distancia indeterminada COM faixa visivel, nunca contato 0 |
| D817 | Duas arestas com comprimentos empatados/bounds sobrepostos | Mostrar Aresta 1/2; sem menor/maior nao certificado |
| D818 | Auditor recebe ZIP individual e nao bundle Master | Sem acesso a relatorio corrente do outro auditor; preservar independecia por rodada |

**Interpretacao:** a suite Python R8 verifica alguns exemplos logicos, inclusive negativos; as demais linhas sao requisitos para reauditoria documental/implementacao futura. Nao se executou Blender. Se uma regra de R8 divergir de um caso herdado na matriz, **HOLD** ate harmonizacao; o texto principal isolado nao dispensa criterios da matriz.
