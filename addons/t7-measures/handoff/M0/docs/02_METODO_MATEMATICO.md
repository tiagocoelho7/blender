# Método matemático e interfaces de confiança

## Entradas e referencial

Aceitam-se somente tipos nativos exatos `int`, `float`, `Fraction` e `Decimal` finitos, com limites de tamanho. `bool`, strings, subclasses numéricas e conversores arbitrários são recusados. Um float vira sua razão binária exata por `as_integer_ratio`, sem passagem por representação decimal. Decimal vira a razão exata, depois de validar finitude, quantidade de dígitos e expoente antes de alocações grandes. Coordenadas são copiadas em tuplas de racionais.

O chamador afirma que os operandos pertencem à mesma malha local e à mesma matriz/unidade. O kernel não pode identificar um objeto Blender inexistente. O modelo A/B acrescenta a prova **sintética** de igualdade desses contextos.

Usa-se `anchor = A.points[0]` e `w = unit * M3 * (p-anchor)` em aritmética racional para **ambos** os operandos. A translação de mundo cancela. `unit = scale_length*1000` em METRIC/IMPERIAL, com escala positiva; NONE usa unit=1 e texto BU/BU2. Não se recebe nem se calcula uma posição mundial absoluta. As unidades ficam quadradas automaticamente porque as áreas são calculadas depois da transformação.

O determinante de M3 é racional exato. Zero recusa; adicionalmente recusa-se o limite de condicionamento de Frobenius ao quadrado `||M||F² ||M^-1||F² > 10^24`. Essa é uma restrição conservadora experimental do M0, não tolerância de contato nem medida física. Matrizes que passam não precisam de aproximação float nas operações seguintes.

## Operações racionais e raízes

Distâncias quadradas de primitivas planas e segmentos são racionais. Sinais, incidências, projeções e parâmetros limitados ao segmento são decididos exatamente. Cada operação vetorial guardada valida bit-length; somas longas de áreas/centroides são guardadas incrementalmente. Operações maiores que os limites retornam recusa/indeterminação, sem reinterpretar o dado como contato.

Para `x>=0` racional, a raiz é encerrada num intervalo diádico. Quadrados perfeitos racionais são reconhecidos exatamente por `isqrt(numerator)` e `isqrt(denominator)`. Nos demais casos, escolhe-se escala diádica s a partir dos bit-lengths, calcula-se `k=isqrt(floor(x*s²))` e publica-se `[k/s,(k+1)/s]`, com correção para igualdade exata. Assim `lo²<=x<=hi²` é uma desigualdade racional testável. A escala adapta-se à magnitude; não há overflow/subnormal de float nessa raiz. A precisão interna de referência é 192 bits; os limites de bits continuam podendo recusar certas entradas.

## Primitivas finitas

- V-E minimiza `||p-(a+t(b-a))||²` com `t` racional limitado a [0,1]. Segmento degenerado é um ponto, com aviso.
- E-E verifica os quatro casos de endpoint contra segmento e o ponto estacionário interior se o determinante exato `aa*cc-bb²` é positivo e os dois parâmetros pertencem a [0,1]. Paralelos ficam nos casos de borda; não há epsilon de quase paralelismo.
- V-triângulo projeta no plano e verifica os três semiplanos do triângulo; fora da região usa as três bordas.
- E-triângulo testa interseção do segmento fechado com o triângulo, incluindo coplanaridade e contenção. Se não intersectam, minimiza endpoints contra triângulo e segmento contra as três bordas. Um raio que alcança o plano além do endpoint não serve como contato.
- Triângulo-triângulo minimiza os seis casos de aresta contra triângulo. Contenção e crossing coplanar são incluídos pelas primitivas. Para conjuntos planos finitos separados, se os interiores não contêm um par mínimo, o mínimo está em borda; o caso de planos paralelos com projeção interior está incluído em V-triângulo.

O certificado de contato não é derivado do texto ou de `lo==0`. Além da distância quadrada zero, exige-se um predicado de incidência separado: igualdade de pontos, colinearidade/pertinência, solução de linhas via produtos vetoriais, ou segmento-plano mais semiplanos. Inconsistência entre distância zero e predicado de incidência recusa a certificação.

O oráculo de testes evita essas fórmulas: enumera suportes ativos de dois simplexos convexos e resolve o sistema KKT racional da minimização quadrática de pesos baricêntricos, com somas de pesos unitárias e pesos não negativos. Suportes singulares são descartados; a busca usa suportes menores. Isso dá independência algorítmica parcial, embora ambos usem `Fraction` do Python e tenham sido escritos pelo mesmo executor. Não equivale a auditor independente A/B.

## Faces, triangulação e planaridade exata

Calculam-se o centro racional c e Newell `N=sum((wi-c)×(wi+1-c))`. N zero recusa. Se todos os produtos `(wi-c)·N` são zero, o polígono é exatamente planar sobre os valores lidos. Não se usa tau para essa classificação.

A projeção é escrita sem raiz nem normal unitária aproximada:

`qi = wi - (((wi-c)·N)/(N·N))*N`.

Os qi são racionais exatos. Remove-se uma coordenada correspondente à maior componente absoluta de N para obter uma carta 2D injetiva do plano. Checam-se vértices repetidos e todas as interseções de arestas não adjacentes, incluindo contato tangencial/endpoint-interior; cantos consecutivos colineares são recusados conservadoramente, inclusive se seriam apenas redundantes. Área projetada nula recusa.

Ear clipping escolhe exatamente n-2 triângulos orientados e sem novos vértices. Um **validador separado** verifica índices, quantidade, orientação estrita, multiplicidades, cancelamento das arestas interiores e cadeia de borda igual à do polígono, soma exata das áreas orientadas e ausência de cruzamentos entre arestas não incidentes. Com cadeia de borda simples e triângulos com orientação coerente, a multiplicidade orientada no interior é 1 e no exterior 0: a união preenche a região e não inclui sobreposições de área positiva. A/B devem revisar esse argumento e sua tradução ao validador, não confiar apenas na soma das áreas.

A área da região projetada é `A_Q=||N||/2`: a projeção na direção de N conserva a componente vetorial de área, e a cadeia projetada simples tem vetor área paralelo a N. São calculados bounds racionais para a raiz de `N·N`. Para uma face exatamente plana, isso encerra a área real da face; não é soma arbitrária de triângulos de um n-gon torcido.

## Caminho P

Somente para uma face não exatamente plana, calcular:

- `h²=max(((wi-c)·N)²)/(N·N)`; h_U pela raiz outward;
- L² pelo máximo das distâncias quadradas entre todos os pares de vértices; L_L/L_U por raiz outward;
- tau(L_L) com os pisos/tetos provisoriamente ratificados, inclusive a variante NONE;
- resolução local por metade do maior passo dos dois vizinhos binary32 de cada componente, norma do vetor de raios, multiplicada conservadoramente por `||M3||F` e unidade.

Para P o M0 só aceita coordenadas que tenham origem binary32 demonstrável pelo valor exato: faz pack/unpack f32 e exige igualdade racional com o valor recebido. Para zero/subnormal a metade do passo é `2^-150`. O maior float32 é recusado porque um vizinho é infinito. Não se afirma que valores arbitrary double foram quantizados dessa forma no Blender. Não se exige que os elementos da matriz sejam f32: seus valores observados são tratados como racionais exatos.

Exigir h_U<=tau e R_U<=tau/4. Exigir A_Q,L>0. A conta dos pares de L já entra no preflight mesmo antes de saber se a face é P, como reserva de pior caso.

Para qualquer triangulação admissível (n vértices originais, n-2 triângulos preenchendo Q, nenhum Steiner), cada vértice levantado está a uma altura absoluta <=h_U. Em cada triângulo, a parte adicional do produto vetorial tem norma <=4*h_U*L_U, usando diferenças de altura <=2h_U e comprimentos projetados <=L_U. A desigualdade triangular, após divisão por 2, dá incremento de área <=2*h_U*L_U. Somando n-2 triângulos:

`A_Q <= A_superficie <= A_Q + D_A`, `D_A=2*h_U*L_U*(n-2)`.

O gate geométrico é `D_A<=A_Q,L/100`. A largura TOTAL usa `A_U=A_Q,U+D_A` e exige `A_U-A_L<=A_L/100` para nominal de área. Os qi são racionais exatos; portanto não há erro adicional não contabilizado de projeção. Bounds de raízes e D_A são outward por desigualdades racionais. Alterar apenas esse gate TOTAL não invalida uma distância certificada independentemente; falha do gate geométrico recusa a consulta inteira.

Cada ponto de um triângulo levantado tem projeção em Q e altura <=h_U por convexidade baricêntrica; cada ponto de Q tem um lift em algum triângulo da tessela. A distância de Hausdorff é <=h_U. Para duas entidades, H é a soma dos h_U das faces P; as demais têm h=0. Se o proxy fornece `[l,u]`, a distância real a qualquer triangulação admissível pertence a `[max(0,l-H),u+H]`.

P nunca certifica contato neste M0. Se o envelope inclui zero, publica apenas INDETERMINADO_COM_FAIXA. Com lower>0, publica positividade e intervalo obrigatório. Ausência de bounds provados retorna INDETERMINADO_SEM_FAIXA. Nenhuma escolha de diagonal 3D é anunciada como a superfície do Blender/slicer.

## Apresentação e confiança

O certificado geométrico é produzido por `measure`. O formatter `publish` valida tipos, finitude, ordem, dimensão e contradições entre contato/referência/nominal, mas **não prova a origem geométrica de um intervalo arbitrário**. Essa interface é interna e também serve a fixtures de política. Não se permite transformar um `Certificate` fabricado pelo chamador em alegação de medida verificada.

HALF_EVEN usa quociente e resto de inteiros; bounds são floor/ceil racionais. Um intervalo de referência que atravessa uma decisão de arredondamento suprime o nominal, mesmo se um nominal pontual foi fornecido. Sem referência, um nominal opcional explicitamente fornecido e coerente pode ser formatado como valor representado. Nominal ausente não é tratado como zero.

`0<x<q` exige lower>0, upper<q, gate de publicação e gatilho de arredondamento a zero. Upper=q nunca passa. Uma faixa P mais larga que q também suprime o nominal, conservadoramente. As faixas permanecem visíveis no objeto de apresentação. A ordenação estrita de áreas/comprimentos usa bounds internos, nunca os textos outward.
