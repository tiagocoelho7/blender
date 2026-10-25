# T7 Measures — Adendo normativo candidato SPEC-R8.1

**Data:** 2026-10-22. **Autor:** Chat Master. **Estado:** CANDIDATA NAO HOMOLOGADA; exclusivamente reauditoria documental/offline. **Referencia intocada:** `ORIGINAL_R8/01_ESPECIFICACAO_R8.md` (SHA-256 ver manifesto). **Destino futuro:** addon pessoal apenas leitura, Blender 5.2.2 LTS. **Work, Blender real, instalacao e producao:** HOLD. D04=P ratificada SOMENTE como conceito. Parametros numericos permanecem PROPOSTOS.

## 1. Hierarquia e intencao

Este adendo complementa a SPEC-R8 congelada; nenhuma alteracao retroativa nela e autorizada. Onde houver divergencia explicita, R8.1 prevalecera SOMENTE se formalmente aprovado apos reauditoria e ratificacao pertinente. Fora dos itens R81-01 a R81-06, permanece o contrato R8 integral, inclusive oito modalidades (V-V, V-E, V-F, E-E, E-F, F-F, E isolada, F isolada), aviso sobre modifiers ignorados, calculos por clique e proibicao absoluta de escrita na malha/arquivo.

## R81-01 — Distancias mistas com uma face P

Em V-F e E-F com face QUASE_PLANA_APROX valida, a falha *exclusiva* do gate TOTAL de **apresentacao da AREA** nao invalida a distancia quando sua **certificacao numerica independente** for concluida. Nao exibir nominal de area P enquanto seu gate TOTAL falhar. Quando existir um certificado de distancia finito `[d_L,d_U]` com `0<d_L<=d_U`, permitir **POSITIVO_CERTIFICADO_COM_FAIXA** e intervalo outward visivel. Para `[0,d_U]` sem outra prova, apresentar **INDETERMINADO_COM_FAIXA**, sem contato/zero. Sem certificado valido, **INDETERMINADO_SEM_FAIXA**, sem numero. Uma falha do gate GEOMETRICO P ou de validade topologica/predicado recusa a consulta inteira, como nas F-F. A distancia deve continuar a usar ancora mundial compartilhada, sem reuso de proxy com referencia espacial divergente. A permissao de publicar a distancia nao dispensa o gate da *propria distancia* e nao torna a face 'exata'.

## R81-02 — Estado A/B unico na instancia do addon

Politica de V1 proposta ao proprietario: **exatamente UM slot A/B ativo em toda a instancia registrada do addon dentro do processo Blender**, independentemente de janelas/areas `VIEW_3D`. O slot registra janela, area, Scene, objeto, datablock, modo, geracao e contexto relevante. `Capturar A` em qualquer area inicia ciclo novo: invalida, libera e substitui `S_A`, B e estado anterior ANTES de alocar novos buffers; o resultado de consulta anterior nao e reutilizado como medicao atual. Se B for capturado noutra area/contexto, falha fechada, limpa o slot e pede novo A no destino. Novo A apos A+B apaga B antigo. `Calcular` apenas no mesmo contexto e geracao, com `S_A`, S1 e S2 integrais, comparados byte a byte, como R8.4. `Limpar`, invalidacao, Undo/Redo, load, unregister e erro liberam referencias; nunca escrevem no `.blend`. Comportamento visual em areas alternativas: nenhuma area exibe estado A/B como ativo quando ela nao for dona do slot.

**Memoria:** o teto provisoriamente proposto em R8 (128 MiB) significa **orcamento agregado da instancia**, nao por janela/area/operacao. Preflight conservador contabiliza TODOS os buffers e duplicacoes/transientes vivos (`S_A+S1+S2` quando coexistentes, B e outros mapas, arrays, triangulos e representacoes temporarias), inclusive memoria de sessao anterior durante transicao ate ser liberada. A formula R8 e **estimativa minima**, nao certificado de uso real nem promessa de que RSS fica abaixo de 128 MiB. Antes de Work M0 o projeto precisa especificar limites superiores ou recusa segura por memoria/complexidade; se nao demonstravel, recusar. Antes de GO operacional, benchmarks de RSS/alloc no Blender 5.2.2 e testes multi-area/sessao sao obrigatorios. Nao pressupor que del/GC implique liberacao imediata de RSS. Limites ainda aguardam decisao do proprietario.

## R81-03 — Validacao segura de valores e certificados de exibicao

O contrato normativo R8.5 e UX07 prevalece sobre qualquer *helper* didatico anterior. Valores nominais, `d_L/d_U`, `A_L/A_U`, precisao p e unidades devem ser validados antes de calculos/apresentacao: tipo/conversao suportada, todos FINITOS, `p` inteiro entre 0 e 6, `0<=L<=U` e, quando nominal represente a **mesma grandeza certificada**, `L<=nominal<=U`. Se nao puder comprovar a correspondencia entre nominal e intervalo, omitir nominal, nao inventar certificado. `NaN`, `Infinity`, `-Infinity`, ausencia, tipo invalido, bounds invertidos ou nominal contraditorio produzem estado de falha fechado **SEM_FAIXA** (mapeado na interface para `INDETERMINADO_SEM_FAIXA`) sem excecao nao tratada e sem numero. Nao deduzir contato apenas de nominal zero ou bounds outward exibidos. `0<x<q` SOMENTE se os limites internos certificados atenderem `0<L<=U<q`, nunca usando valores arredondados da viewport. O script `qa_r81_contracts_offline.py` e ORACULO DIDATICO NOVO, nao algoritmo de addon nem prova de certificados geometricos; nenhum codigo do helper R8 original pode ser copiado ou usado como validador em producao.

## R81-04 — HALF_EVEN e bits realmente observados

QA vinculante deve usar casos `math.nextafter` nos dois vizinhos binary64 de `q/2`, `Decimal.from_float` ou representacao exata equivalente, e amostras binary32 com bits de origem quando a malha do Blender real vier a ser testada. Um valor inicialmente decimal empatado pode cair acima/abaixo do limiar apos representacao binaria. Somente o valor efetivamente certificado e arredondado HALF_EVEN para o **nominal**; faixas usam arredondamento outward dirigido. Onde o intervalo de erro possa cruzar o ponto de empate, nao anunciar uma decisao nominal falsamente certificada; privilegiar faixa/diagnostico. Execucao de Python offline nao prova que Blender use os mesmos bits.

## R81-05 — QA do runtime e viabilidade

Antes de autorizar qualquer M0, o prompt Work deve distinguir: (i) projeto/demonstracao de limites conservadores (M0), (ii) integracao Blender real, somente com autorizacao separada, (iii) validacao independente posterior. Benchmark e estimador de pico com `S_A+S1+S2+overheads`, custo de serializacao e multiplas areas, tratamento de recaptura e cancelamento; recusar em falta de majorante defendivel. Nenhuma promessa de 128 MiB garantidos so pelo estimador minimo R8. Uso real do addon e instalacao continuam bloqueados ate gates futuros.

## R81-06 — Proveniencia/controle de qualidade

Os dois resultados atuais da auditoria R8 pertencem SOMENTE ao acervo Master; os auditores da R8.1 recebem a mesma R8 congelada, este adendo e a matriz nova, sem parecer atual do outro nem atribuicao nominal historica nos arquivos compartilhados. A referencia R6 nao embutida em R8 fica identificada como **historica nao entregue**, sem obrigacao de replay; regressao R6 integral futura so com harness explicitamente incluido. O QA da R8.1 e *adicional*: nao substitui a matriz R8 nem exige reabrir sem achado os teoremas geometricos anteriores.

## Permanecem pendentes de ratificacao do proprietario

Tolerancia `tau` (piso 0,001 mm, teto 0,010 mm, termo 1e-6*L), variante em BU para NONE, `R_U<=tau/4`, limites geometrico/TOTAL de 1% de area, 512 loops por face, 200000 pares, 50000 pares de triangulos, 128 MiB, e politica *um slot A/B global*. Sao CANDIDATAS; nao declarar os valores como calibracao certificada para impressora 3D. Work nao recebe autorizacao automaticamente de um GO documental R8.1.
