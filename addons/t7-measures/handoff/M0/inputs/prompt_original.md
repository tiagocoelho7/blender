# T7 Measures - Prompt de futura tarefa Work M0 (RASCUNHO NAO AUTORIZADO)

**STOP / NAO EXECUTAR**: este prompt e somente preparacao documental para proxima decisao. Sem autorizacao explicita e ratificacao dos limites propostos, nenhum Work deve iniciar.

## Papel
Voce sera executor/programador Work do addon pessoal de medicao T7 Measures; Master e o coordenador, auditores A/B sao independentes. O destino e Blender 5.2.2 LTS. M0 e exclusivamente **Python offline**, nao um addon instalado ou operado.

## Entrada congelada
- SPEC-R8 integra, adendo R8.1 candidato, nota de clarificacoes do Master, matriz QA e resultados A/B R8.1.
- Nao inferir que GO documental e homologacao do codigo.
- D04=P conceitualmente aprovada; outras constantes dependem do registro de aprovacao fornecido separadamente.

## M0 - escopo limitado (sujeito a aprovacao)
- Pesquisar e implementar um kernel *isolado de Blender* e interfaces de dominio para distancias V-V/V-E/V-F/E-E/E-F/F-F, comprimento de uma aresta e area individual de face, incluindo poligonos, degeneracoes, intersecoes e proxies P sob intervalos geometricos conservadores.
- Formalizar uso de uma **ancora espacial compartilhada** para cada consulta; nunca usar origens independentes que convertam distancia real positiva em 0.
- Definir certificados de intervalo com nao-negatividade, bounds internos vs arredondamento outward, contato somente por prova, leitura de nominal opcional e recusa por dados invalidos.
- Escrever bateria offline baseada em fixtures racionais/decimais + floats representados e testes adversariais, incluindo objetos grandes, pequenos e valores invalidos; inclui `nextafter`, binary32, HALF_EVEN, `-0`, memoria e complexidade.
- Modelar estado de capturas A/B em maquina de estados abstrata com identidade de contexto/geracao; aceitar mudanca apenas do **tipo** de selecao entre VERT/EDGE/FACE. Nao abrir Blender.
- Pesquisar limites superiores defensaveis de memoria/custo ou recusa segura antes de qualquer runtime Blender; nao alegar prova RSS obtida offline.
- Validar todas as oito modalidades e estados positivos/indeterminados, sem inventar area ou distancia quando geometria/certificados sao insuficientes.
- Fazer TODO codigo de calculo apenas sobre fixtures isolados/copiados e offline, sem acessar projetos reais.

## Exclusoes (HOLD absoluto)
- `bpy`, `bmesh` real, inicializar Blender, UI, instalar extensao, tocar em arquivos `.blend` de propriedade do usuario, mudar vertices/arestas/faces, aplicar modifiers, editar malha/scene e testes de producao.
- Nao copiar helpers didaticos R8/R8.1 para codigo de producao.
- Nao aprovar o proprio trabalho nem chamar Work adicionais por conta propria.

## Entrega M0
Um unico ZIP autossuficiente com codigo fonte, harness standalone, oraculos independentes, testes positivos/negativos, resultados completos, `README`, SHA-256 e prompt Markdown de continuidade. Explicitar hipoteses abertas e discrepancias. Submeter candidatos congelados aos auditores A/B; GO para proxima fase decidido pelo Master e proprietario, nao pelo executor.
