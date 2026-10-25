# Limitações conhecidas e condições de uso

Esta é uma candidata M0, sem instalação e sem homologação. Os parâmetros permanecem provisórios.

| Limitação | Comportamento atual | Pendência |
|---|---|---|
| Envelope de custo menor que o máximo de produto | 32 loops estruturais; soma de custo pode recusar antes disso | A/B revisar custo; ampliar só após prova e autorização pertinente |
| Crescimento racional | 2048 bits na entrada, 4096 guardados, 2 milhões de passos | Pode recusar entradas válidas ou deixar apenas áreas certificadas |
| Memória de projeto | Reservas e contagens agregadas com transientes; plataforma CPython restrita | Majorante de objetos/temporários a auditar; sem garantia de RSS |
| Contorno com cantos colineares | Recusa conservadora de casos válidos redundantes e de retrocessos inválidos | Melhorar a aceitação exige prova de tessela, sem relaxar simplicidade |
| P sobre entrada não f32 | Recusa até comprovar origem binary32 no valor recebido | Blender real deverá confirmar formato de armazenamento |
| P sem superfície original única | Faixa para qualquer tessela admissível; contato nunca certificado por P | Não anuncia qual diagonal Blender/slicer usa |
| Nominal suprimido | Faixa de referência atravessa arredondamento ou largura P excede q; área TOTAL falha | Comportamento conservador; ainda não é UI final |
| Contexto A/B abstrato | IDs sintéticos, snapshots integrais, seleção por ocorrências e dois estados de clique fornecidos | Não prova callbacks, ordem real das leituras, atomicidade durante cálculo ou identidade RNA |
| Instância abstrata | `Instance` tem um slot; instâncias distintas modelam processos distintos | Não há singleton registrado no Blender, pois integração está em HOLD |
| Comparação de contexto | Valores numéricos normalizados, translação incluída no token | API real deverá provar matriz avaliada, dependências e shape key ativa |
| Certificados de política | Formatter valida números e coerência; assume autenticidade geométrica do chamador interno | Não expor como serviço de certificação de bounds fornecidos pelo usuário |
| Independência | Oráculo usa algoritmo separado, escrito pelo executor e biblioteca Fraction comum | Auditorias A/B externas continuam necessárias |
| Corpus amostral | Analíticos, 36 pares convexos determinísticos, quad P com duas diagonais | Sem exaustividade de todas as faces, degenerações ou diagonais |
| Runtime Blender | Não executado, não consultado, não instalado | Exige nova autorização e testes na build-alvo |

Os nomes de erro descrevem uma recusa do protótipo, não uma conclusão de que toda face recusada é defeituosa. Não alterar a malha nem aumentar tolerâncias para forçar um número.

Exclusões preservadas: ausência de `bpy`, `bmesh`, adaptador real, registro de addon, UI, operadores, timers, acesso a `.blend`, modifiers e projetos reais. `run_offline.py` é ferramenta de teste/documentação que escreve evidências em diretório explícito; o núcleo matemático não lê nem grava arquivos.

Não se detectou falha de asserção na execução final registrada. Isso não equivale a declaração de ausência de bugs. A/B devem julgar especialmente o argumento de cobertura da triangulação, os majorantes de recursos, as restrições adicionais, o intervalo de área P e a semântica da sessão abstrata.
