# Matriz consolidada das descobertas — codigo v1.0.1

| Cluster Master | IDs A/B | Priorizacao Master | Demonstrado offline | Limite da evidencia | Aceite minimo |
|---|---|---|---|---|---|
| MC01 Preflight obsoleto | A101-P0-01 / B-CODE-P1-02 | P0 para gate | 2 remocoes e sucesso sob mutacao de refs/geometria por callback | callback real padrao e print; Blender nao testado | revalidar, proibir efeitos do callback/contrato exclusivo, impedir falso sucesso |
| MC02 Lookup dinamico | A101-P1-02 / B-CODE-P1-03 | P1 | aliases triviais em Text e IDProps escapam; 2 remocoes | Text pode nao executar; Python arbitrario impossivel inferir | expandir scanner AST/alias ou abortar indeterminado |
| MC03 Memoria ambigua | A101-P1-03 | P1 | RAM amostrada supera estimativa O(n); custo quadratico | RSS inclui overhead e nao mede uso exato do par | estrut. compartilhada e contabilidade coerente/aborto previo |
| MC04 Prazo cooperativo | A101-P1-04 | P1 | overshoot ~72x a 10ms | limite cooperativo, nao deadline hard | checkpoint em loops internos, oraculo adversarial |
| MC05 Modo KEEP | B-CODE-P1-01 | P1 | KEEP EDIT aceita exclusao em fake | combinacao EDIT/OBJECT real nao validada | veto de modos inelegiveis em todo grupo |
| MC06 user_map | A101-P2-05 / B-CODE-P2-01 | P2 | user_map vazio aceito | semantica RNA nao e 1:1 com user_map | normalizar mapa comparavel; divergencia => inconclusivo |
| MC07 Ledger | A101-P2-06 / B-CODE-P2-02 | P2 | campos faltam no snapshot e aborto incompleto | impacto e auditabilidade, nao erro direto | campos do contrato e blockers agregados |

### Contratos que ja passaram apenas em simulacao

G05, G08, G12 e boa parte das suites G02/G04/G07. A matriz G01–G14 permanece HOLD agregado. Nenhum teste positivo autoriza o Blender real nem supera um bloqueante da cadeia de exclusao.
