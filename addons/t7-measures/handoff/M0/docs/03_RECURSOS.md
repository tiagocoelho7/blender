# Preflight e recursos — modelo experimental

## O que é limitado

Os limites abaixo são reduções conservadoras permitidas pela ratificação provisória. Não ampliam nenhuma constante de produto.

| Recurso | Máximo aprovado provisório | Limite experimental M0 |
|---|---:|---:|
| Loops por face | 512 | 32, e ainda sujeito à soma de custo |
| Pares/candidatos por consulta | 200.000 | 200.000 |
| Pares de triângulos F-F | 50.000 | 50.000, sujeito a tetos mais restritos |
| Memória agregada de projeto | 128 MiB | 128 MiB por instância modelada |
| Assinatura canônica completa | Dentro da memória | 2 MiB por assinatura sintética |
| Componentes numéricas de entrada | Não especificado | 2048 bits no numerador ou denominador |
| Racionais guardados durante cálculo | Não especificado | 4096 bits no numerador ou denominador |
| Operações aritméticas guardadas | Não especificado | 2.000.000 por chamada matemática |
| Plataforma admitida pelo modelo de memória | Futuro Blender alvo | CPython de 64 bits com hipóteses de tamanho verificadas |

O gate de plataforma exige CPython, ponteiro de 8 bytes, int digit >=30 bits e <=4 bytes, cabeçalhos de int/Fraction/tuple dentro das cotas no código. Outras implementações são recusadas por orçamento não modelado, embora possam executar Python 3.10+ sintaticamente.

## Custo antes das coordenadas e tessela

Para cada face de n loops, antes de transformar ou triangular:

- `C_contorno=n(n-3)/2`;
- `C_diametro=n(n-1)/2`, reservado **mesmo se a face posteriormente for exata**, para evitar depender de planaridade ainda não calculada;
- para duas faces, `C_tri=(nA-2)(nB-2)`;
- `C_outros=sum(4n³+64n²+128n)+32*max(C_tri,sum(n-2),1)`;
- `C_total=C_contorno+C_diametro+C_tri+C_outros` somado sobre a consulta inteira.

`4n³` reserva a busca de ears com testes de pontos contra triângulos e espaço para validação; `64n²` reserva a verificação independente de arestas da tessela, incidências e predicados correlatos; `128n` cobre fases lineares, projeção e vizinhos. O termo final cobre até 32 candidatos de distância por par de triângulos, ou primitivas com uma face. A unidade é **candidato/teste geométrico abstrato**, não instrução de CPU, operação Fraction ou SLA. O contador aritmético separado impede que esses candidatos façam trabalho racional ilimitado. Auditar o majorante como parte do M0; não presumir equivalência entre os dois contadores.

Uma face P de 512 loops já tem 261.120 candidatos principais e é recusada. Para 448, os 199.808 principais não deixam espaço para as etapas obrigatórias. F-F de 226 loops dá 50.176 pares e é recusada. Com o majorante experimental, até 32 loops podem falhar antes da geometria: a amostra de 32 falhou, a de 30 passou. **O número 32 não é garantia de aceite.**

Somas racionais longas são verificadas por passo. O limite de 4096 bits vale para resultados guardados; uma expressão curta pode criar temporários maiores antes da checagem. Não há conversão para epsilon ou publicação parcial para contornar uma recusa. Falha do orçamento durante a distância pode manter áreas já certificadas, com a distância indeterminada sem faixa; falha antes de validar as faces não publica medidas novas.

## Memória, coexistência e modelo de reserva

O estimador mínimo da R8 é mantido. A admissão matemática utiliza o maior entre ele e:

`80 MiB + Nv*65536 + Ntri*65536 + retained_bytes`.

A reserva de 80 MiB é deliberadamente larga para o envelope reduzido: não se armazenam matrizes de todos os pares, triângulos referenciam vértices já copiados e o cálculo é streaming. Uma contagem estrutural de trabalho considera até 4096 slots escalares vivos, incluindo resultados e scratch, com margem para expressões de até oito vezes o bit-length guardado. Sob int digits CPython de 30 bits/4 bytes, a carga de numeradores/denominadores desse modelo é da ordem de 35–40 MiB; os demais MiB reservam cabeçalhos, tuplas, listas, dicionários, contadores e margem. Os termos por vértice/triângulo acrescentam reserva separada. Essa é uma **justificativa de projeto a auditar**, não uma prova mecanizada da quantidade de objetos vivos ou de RSS; em particular temporários internos de gcd/divisão e alocador CPython não são uma API de limite RSS.

Para assinaturas A/B, o preflight soma contagens globais, reserva de mapas, os três comprimentos `S_A+S1+S2` e **uma cópia adicional** do maior S1/S2 durante conversão `bytearray -> bytes`. Não basta a soma dos hashes. Todos os bytes históricos são retidos até o commit final ou invalidação. O tamanho serializado é calculado antes de construir o buffer; a serialização inclui componentes `<3d`, ocorrências e `loop.edge`. O tamanho final é conferido contra o previsto. `-0.0` é preservado nos bytes, mesmo quando o cálculo racional normaliza zero.

Antes do cálculo A/B, a reserva geométrica é recombinada com os comprimentos de assinaturas e os custos globais de mapas; não se concede 128 MiB separados a cada área ou fase. Novo A limpa o ciclo anterior antes da nova alocação. S1/S2 são locais; S_A, A e B são apagados após sucesso, erro ou invalidação. `del`/saída de escopo não é alegado como devolução imediata de RSS ao sistema.

O tamanho da fixture que o chamador já criou é externo ao kernel; o estimador se refere às cópias/estruturas adicionais previstas. Nenhuma entrada ilimitada é carregada de arquivos pelo núcleo. O runner escreve apenas seus logs em diretório informado.

## Medições feitas e prova ainda ausente

`evidence/work_run/allocation_samples.json` contém cinco amostras de áreas planas (8/16/24/30/32 loops), tempo e pico de alocações rastreadas pelo `tracemalloc`. O setup da fixture é anterior ao início da medição. O registro não cobre todas as faces P, todos os condicionamentos, máquinas, versões Python ou transientes internos do alocador.

**Não é prova de RSS <=128 MiB**, de latência universal ou de limite no Blender. Nenhuma medição de hardware Blender nos níveis 25/50/90/100% foi executada. O M0 estuda majorantes e implementa recusas sob um modelo explícito; sua suficiência deve ser julgada pelos auditores. Antes de integração real, continua obrigatória prova operacional com profiling, limite efetivo/recusa segura, comparação de snapshots e autorização nova. Se o Master/auditores considerarem o majorante insuficiente, o resultado é correção/HOLD, não aumento silencioso do orçamento.
