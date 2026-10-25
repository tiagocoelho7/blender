# Reexecucoes Master — offline

Replays foram realizados em diretorios temporarios extraidos dos ZIPs, nao em Blender. Logs incluidos em `EVIDENCIAS_MASTER/`; os scripts originais continuam nos ZIPs A/B originais.

| Fonte | Comando (apos extrair em copia) | Resultado |
|---|---|---|
| Candidata QA | `python -m unittest discover -s qa -p test_candidate_v101.py -v` | 57/57 |
| Oraculo A | `python qa/oracle_A_adapted_to_candidate.py src/remover_duplicatas_blend_v1_0_1.py saida.json` | 266/266 |
| Geometria A | `python qa/audit_A_geometry_adapted.py src/remover_duplicatas_blend_v1_0_1.py` | 2649/2649 |
| Grafo B | `python qa/verify_B_graph32_on_candidate.py` (criar `evidencias/` antes) | 32/32 |
| Oraculo indep. A | `python HARNESSES/independent_geometry_oracle.py` | 400/400 |
| Oraculo indep. B | `python tests/independent_B_geometry_oracle.py` | 160/160; NAO e suite unittest |
| Contra A | `python HARNESSES/adversarial_references.py` | reproduz REF-01 a 05 (falhas da candidata) |
| Contra B | `python -m unittest discover -s tests -p independent_B_adversarial.py -v` | 11 cenarios demonstram comportamentos observados, nao conformidade |
| Crosscheck B | `python -m unittest discover -s tests -p independent_B_crosscheck.py -v` | 2/2 cenarios demonstram lacunas |
| Deadline A | `python HARNESSES/adversarial_deadline.py` | ~0.719s p/ 0.01s cooperativo |

Observacao: a primeira tentativa de `verify_B_graph32_on_candidate.py` falhou apenas porque a copia descartavel nao tinha a pasta de saida `evidencias/`. Apos criar a pasta, obteve 32/32. Chamar o oraculo B por `unittest` descobre 0 testes porque se trata de script direto: foi executado por `python tests/independent_B_geometry_oracle.py`, gerando 160/160.
