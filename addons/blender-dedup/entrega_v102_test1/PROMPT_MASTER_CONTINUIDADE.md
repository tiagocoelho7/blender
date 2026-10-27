# Continuidade MASTER — v1.0.2-test1

Receba esta entrega como desenvolvimento offline, não homologação. Verifique os SHA-256 externos dos três ZIPs e os manifestos internos; confirme o mesmo SHA da candidata nos pacotes A/B. Preserve os originais, a branch main e a v1.0.1.

Distribua somente o ZIP A ao Auditor A e somente o ZIP B ao Auditor B. Cada pacote contém código novo idêntico, contratos, baseline, diff, testes originais e seu prompt. Não disponibilize MASTER, pareceres, logs/conclusões do executor nem resultados da outra auditoria aos auditores durante a fase cega. Exija relatórios selados com hash, reprodução dos gates e achados próprios antes da consolidação.

Priorize MC01–MC07, as fronteiras de estabilidade em callbacks/último remove, aliases IDProps/Text, memória e deadlines internos, KEEP, normalização user_map e ledger parcial. Questione a legalidade dos mocks e quaisquer garantias de atomicidade. Exija logs e fixtures próprios; PASS do desenvolvedor não substitui auditoria.

Blender 5.0 real, bpy real, `.blend` descartável ou de produção, instalação, autosave, release, PR e merge continuam fora deste trabalho. Qualquer gate real exige nova decisão explícita do proprietário após a consolidação A/B. Resultado admissível desta fase: candidata preparada para auditoria independente; nenhum GO de produção.
