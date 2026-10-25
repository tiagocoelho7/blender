# T7 Measures — Matriz vinculante adicional QA SPEC-R8.1 (candidata)

**Normas anteriores:** SPEC-R8 e sua matriz permanecem congeladas e aplicaveis; R8.1 somente acrescenta/desambigua. **Somente testes OFFLINE agora.** Casos com BMesh/Blender 5.2.2 sao GATES FUTUROS; nao executar neste ciclo.

| ID | Fixture | Aceitacao exigida |
|---|---|---|
| R81-Q01 | V-F com face P: GEOM PASS, AREA TOTAL FAIL, distancia `[4.9998,5.0002] mm` | distancia positiva certificada com intervalo; area sem nominal; sem falso contato |
| R81-Q02 | E-F como acima, intervalo `[0,0.0004]` | distancia indeterminada com faixa, sem contato, sem nominal de area |
| R81-Q03 | V-F/E-F com GEOM FAIL | recusa consulta inteira, sem numero, mesmo que proxy Q pareca plausivel |
| R81-Q04 | V-F/E-F com distancia nao certificada, AREA TOTAL FAIL | indeterminado sem faixa, sem numero antigo |
| R81-Q05 | Capturar A em area 1, capturar A em area 2 | unico slot global; estado da area 1 liberado/invalido e area 2 assume slot |
| R81-Q06 | Capturar A e B na area 1, capturar A novamente na area 1 | descartar B anterior antes de novo A; nunca misturar ciclos |
| R81-Q07 | Capturar A em area 1 e B em area 2 | invalidar e solicitar novo A/B no mesmo contexto, sem misturar referencias |
| R81-Q08 | `S_A=45MiB,S1=45MiB,S2=45MiB` | recusa preflight para teto candidato 128MiB, mesmo sem outros buffers |
| R81-Q09 | 30 areas concorrentes com buffer retido | nao existem 30 slots ativos; teto agregado e unico slot eliminam contagem local ingênua |
| R81-Q10 | Bounds NaN, Inf, -Inf, strings invalidas ou invertidos | `SEM_FAIXA`, sem excecao, sem numero |
| R81-Q11 | Nominal nao contido no intervalo da mesma grandeza | `SEM_FAIXA`, nunca imprimir nominal incoerente |
| R81-Q12 | `p=3`, `[.00025,.00135]`, nominal `.0004` | positivo com faixa outward, **proibido** `0<d<.001` |
| R81-Q13 | `p=3`, `[.00025,.0009]`, nominal `.0004` | sub-q estrito permitido (bounds internos), area P somente se gate TOTAL permite |
| R81-Q14 | `d_L=0`, `d_U=.0004` e nominal 0 | indeterminado com faixa, **nao** contato certificado |
| R81-Q15 | p=0,3,6: vizinho binary64 anterior e posterior a q/2 | arredondamento nominal acompanha valor representado, nao string decimal inicial |
| R81-Q16 | binary32 convertido para coordenada, magnitudes distintas, zeros/subnormais | teste documentado de bits; decidir pelo valor realmente lido; Blender real pendente |
| R81-Q17 | `S_A+S1+S2` abaixo da heuristica, overhead incerto | nao inferir RAM real garantida; exigir estimador conservador/recusa em fase de implementacao |
| R81-Q18 | Undo/Redo, modo, load, unregister, contextos multiplos | no Blender real FUTURO, provar limpeza/invalidez sem mutar malha ou salvar estado |
| R81-Q19 | `q/2` decimal empatado e `float(q/2)` no lado de cima | diferenciar empates matematicos e floats representados; HALF_EVEN so para nominal |
| R81-Q20 | Helper anterior R8 com `Infinity` e NaN | detectar inconsistencia; novo helper recusa, R8 original preservado sem modificacao |
| R81-Q21 | Decimal tipo `NaN`, floats e `None` como nominal/bounds | recusa padronizada SEM_FAIXA, sem obter 0 fabricado |
| R81-Q22 | Uma consulta falha apos ter exibido resultado anterior | invalidar/limpar valor anterior; nao mostrar numero stale como atual |

| R81-Q23 | Distancia certificada apenas por faixa, sem nominal publicavel | painel pode publicar faixa e estado, sem inventar valor pontual; helper de NOMINAL pode recusar por ausencia de nominal |

**Prova exigida aos auditores:** revisar independentemente as regras e executar oraculos com contraexemplos proprios, nao apenas contar testes PASS. Declarar separadamente PASS de script, conformidade normativa, memoria real NAO TESTADA e contexto Blender 5.2.2 LTS NAO TESTADO. Rejeitar qualquer hipotese de que essa suite prova geometria real ou no-write.
