# CHECKLIST / GATE GUI — T7 Statue Mover v1.2.21 / Blender 5.0.0

**Status:** PLANO, NÃO TESTE EXECUTADO NESTE HANDOFF. A auditoria headless foi GO COM CONDIÇÕES; estes testes são os gates faltantes.

## Pré-condições (preencher no momento da execução)

- Data/hora: __________ ; PC/SO: __________ ; Blender About -> **5.0.0**: __________
- ZIP SHA-256 (`7d475cfb...7044f`): __________
- Arquivo de teste COPIADO, não original: __________ ; backup: __________
- Add-on ativo só uma versão: __________ ; outros add-ons conflitantes: __________
- Console de sistema/arquivo de log disponível: __________

## Execução guiada (não fazer tudo de uma vez; conduzir usuário em 2–3 passos)

| ID | Teste | Aceite obrigatório | Status | Evidência |
|---|---|---|---|---|
| GUI-01 | Instalar ZIP frozen no Blender 5.0.0; habilitar/desabilitar/reabilitar | sem traceback, painel na barra N, sem problema de register/unregister | PENDENTE | |
| GUI-02 | Preparar em cópia com guia + 2 targets + base fixa | snapshot legítimo, modifiers viewport conforme original | PENDENTE | |
| GUI-03 | Transformar G/R/S uniforme, inclusive `S 0.5` | alvos gerenciados seguem `D@M0`, referência/base imóveis | PENDENTE | |
| GUI-04 | Aplicar, Finalizar | FINISHED e backup/snapshot excluído somente após validação | PENDENTE | |
| GUI-05 | Preparar/Aplicar e RESTAURAR | transforms/modifiers/geometry exatamente originais | PENDENTE | |
| GUI-06 | Alvo em collection hidden/excluded | acompanha transformação, mesmo sem aparecer | PENDENTE | |
| GUI-07 | Parent, `matrix_parent_inverse`, delta e BONE sem influência proibida | Apply world e Restore corretos | PENDENTE | |
| GUI-08 | Close sem Save após Prepare, reopen de `.blend` já salvo | recuperação/Restore conforme baseline externo | PENDENTE | |
| GUI-09 | Save/reopen após Apply, depois Finalize e Restore em branches distintas | persistence e readback íntegros | PENDENTE | |
| GUI-10 | Guia não-uniforme/zero/negativo; shear | recusa, sem persistir pose inválida nem destruir snapshot | PENDENTE | |
| GUI-11 | Constraints/Action/NLA/drivers/pose constraints proibidos | fail-closed, sem autoexec falso certificado | PENDENTE | |
| GUI-12 | Undo / Redo / event loop / handlers save_post | sem corrupção de snapshot, duplo registro ou falso FINISHED | PENDENTE | |
| GUI-13 | Reload/fechar/abrir/disable addon com estado preparado | resultado explicitamente seguro, documentar comportamento | PENDENTE | |
| GUI-14 | Stress representativo e avaliação de console | sem erro/consumo impraticável, evidência de tempo e memória | PENDENTE | |

## Como documentar

Para cada passo guardar: ID, hash do ZIP, `.blend` sintético/fixture, versão Windows/Blender, objetos e escala, ações clicadas, esperado, observado, `FINISHED`/`CANCELLED`, prints/console, se Restore foi exato, e qualquer divergência. Quando não executado, registrar **PENDENTE**, jamais PASS presumido.

**Condição HOLD:** qualquer cenário obrigatório com transformação incorreta aceita, Restore inexato, perda de estado, deleção de objeto do usuário, crash causado pelo add-on ou regressão HIGH/CRITICAL. Se um teste simplesmente não puder ser realizado, veredito dessa área = INCONCLUSIVO/PENDENTE, não PASS.

**Condição GO de produção:** auditoria runtime + GUI observada + problemas LOW/INFO formalmente aceitos pelo proprietário + release autorizado. Headless isolado NÃO basta.
