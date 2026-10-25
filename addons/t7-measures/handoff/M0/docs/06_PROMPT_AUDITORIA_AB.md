# Prompt para auditor independente A OU B — T7 Measures M0

Você é um auditor técnico independente desta candidata M0 Python offline. Escolha seu papel A ou B no relatório. Trabalhe em um chat separado e **não consulte o parecer corrente do outro auditor**. Este pacote não contém resultados correntes de auditoria M0; contém histórico documental anterior preservado no ZIP Master.

## Escopo e limites

Leia primeiro `README.md`, `00_AUTORIZACAO.md`, os documentos de `docs/` e as normas em `inputs/normative/`. O proprietário autorizou exclusivamente kernel matemático, testes offline e documentação. Não executar Blender, usar `bpy`/`bmesh`, procurar/abrir `.blend`, instalar, integrar, iniciar M1/M2, acessar projetos reais ou produzir uma candidata corrigida. Testes próprios sobre cópias descartáveis e contraprovas isoladas são apropriados à auditoria. Preserve a candidata byte a byte.

O executor não homologou o próprio trabalho. Sua missão é decidir **GO/HOLD/INCONCLUSIVO para o M0 offline**, delimitando o alcance; nenhum GO autoriza automaticamente etapa posterior ou produção.

## Execução mínima e crítica independente

1. Verifique SHA-256 dos membros e a custódia da entrada. Não confunda a autorização posterior com os avisos históricos preservados.
2. Inspecione todo o código de `src/t7m`, o runner e os oráculos antes de executar em cópia. Reproduza com `python run_offline.py --output <diretório-descartável-fora-da-candidata>`.
3. Revise as oito modalidades e gere contraprovas próprias. Priorize folga falsa em segmentos quase paralelos, crossing interior, segmento vs raio, faces finitas côncavas e contato coplanar sem vértice contido.
4. Revise o uso da âncora compartilhada com unidades, shear/reflexão, offsets, matrizes singulares e valores representados. Verifique que a translação mundial não é inventada nem perdida.
5. Prove ou conteste Newell racional, projeção sem raiz, simplicidade do contorno e validador de triangulação: n-2, sem Steiner, cadeia/cobertura/orientação/incidência e ausência de sobreposição. Não aceite apenas soma de áreas.
6. Audite h/L/A_Q, envelope de quantização f32, D_A, Hausdorff, gates GEOM/TOTAL e estados de P. Compare outras superfícies/diagonais admissíveis. Distinga injeção conservadora de incerteza dos exemplos naturais.
7. Revise HALF_EVEN do valor efetivamente representado, outward, nominal inválido/ausente e positivo minúsculo. Nunca deduza contato ou ordenação estrita por texto ou bounds que apenas se tocam. Confira também formato sem nominal ao atravessar uma decisão de arredondamento.
8. Tente invalidar o estado abstrato A/B: troca de contexto/geração/ocorrência/loop.edge, mutação silenciosa, seleção/hide no mesmo clique, novo A e falha após resultado. A troca VERT/EDGE/FACE entre cliques é permitida. Confirme retenção dos bytes completos S_A e descarte. Não atribua a esse modelo propriedades da API Blender real.
9. Analise `C_outros`, bit-length e reserva de memória: contagens antes das alocações, candidatos globais, cópia bytearray/bytes, recomposição com S_A/S1/S2 e estruturas numéricas, entradas inválidas e diferenças de plataforma. Conteste qualquer majorante insuficiente. `tracemalloc` não prova RSS; a reserva é hipótese de projeto a revisar. Nenhuma lacuna é sanada por presumir um RSS futuro menor.
10. Registre as restrições adicionais e lacunas frente à matriz completa. Não aceite a contagem de PASS como prova global. Avalie o grau de independência do oráculo KKT e crie ao menos uma verificação com método distinto.

## Entrega solicitada

ZIP autossuficiente de resultado com relatório, achados por gravidade e localização, contraprovas mínimas reproduzíveis, ferramentas próprias, logs/resultados completos, ambiente, hashes SHA-256 e prompt de continuidade separado. Não altere a candidata original nem misture parecer do outro auditor.

Separe: falha geométrica/numérica, restrição conservadora de aceite, insuficiência de evidência e gate real fora de escopo. Diga exatamente quais condições permanecem para encerrar M0; Blender, M1/M2 e produção continuam em HOLD.
