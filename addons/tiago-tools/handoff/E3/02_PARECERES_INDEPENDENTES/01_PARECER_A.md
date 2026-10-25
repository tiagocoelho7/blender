# 01 — Parecer técnico Auditor A / E3 / Tiago Tools 1.0.2

**Data:** 20/10/2026  
**Veredito principal: `GO ESTÁTICO PARA TESTES`**  
**Classificação por addon: `C — testes especiais`** (código aparentemente apto a testes nativos, mas risco operacional específico de Safe Sub e histórico de registro que exigem gate real).  
**GO PRODUÇÃO: NÃO.**

## Resumo executivo

Os três reparos autorizados estão efetivamente presentes no ZIP congelado da v1.0.2. O manifesto foi alinhado ao formato Blender (`schema_version = "1.0.0"`, independente de `version = "1.0.2"`). Safe Sub passou a remover **somente** o modifier criado quando um setter falha, e preservar `FINISHED`+`WARNING` se a remoção falhar, para oferecer a oportunidade de Undo. Registro agora rastreia classes e trata rollback/retries. Operadores de batch, coleta de collections e painel são **AST idênticos** a v1.0.1.

**Provas independentes:** remessa e manifestos íntegros, comparação byte a byte e diff refeito dos 5 arquivos, parse TOML, compile() Python sem gerar bytecode, AST invariants e **59 testes simulados independentes, 0 FAIL, 0 ERROR**. O material do autor com 23 testes **não foi usado como atestado** e seu harness não foi executado pelo Auditor A. Não houve validação via CLI real do Blender, install/register RNA real, UI, undo real nem Windows.

### Custódia essencial

| Item | SHA-256 recalculado |
|---|---|
| Remessa individual A E3 (ZIP original) | `d622154d8351c446c5afc338110818500175e0dedf15b8e76df177a50bc09173` |
| Base comum `01_E3_BASE_COMUM.zip` | `aa65457eb4ff6035976d4181e9627ea3f7d287b465fad2a4b1c082d21f5b96a8` |
| Candidata `tiago-tools-1.0.2.zip` | `28cba4b80e058e726f1e802498588d80278897918a4163b554c6697edda5bad2` |
| Baseline `tiago-tools-1.0.1.zip` | `30dc30ec35dc2b8444366bf4faea40dbe4106176cdea68b2604ae0750f191548` |
| Histórico `tiago-tools-1.0.0_HISTORICO.zip` | `18f727f6cb58297e94ac14af4c656b7ae631e56f71076aaf68bf9bb863406e99` |

## Observações verificadas, não defeitos novos

**V-E3-01 — Manifesto corrigido (PASS documental).** `blender_manifest.toml:1,4` usa schema `1.0.0` e versão da extensão `1.0.2`, `__init__.py:6` registra `(1,0,2)`. O formato da documentação Blender 5.0 e 5.2 mantém a distinção. **O validador nativo ainda não foi rodado**.

**V-E3-02 — Safe Sub rollback (PASS em mocks).** `__init__.py:151-197`: 12 cenários simulados de falha antes/depois da escrita de cada um dos 6 setters, remoção do modifier recém-criado, preservação do modifier preexistente, retorno `CANCELLED` após limpeza. Além disso 12 cenários de falha simulada do `remove`: `FINISHED`+`WARNING`, novo modifier residual (quando a remoção falhou antes da mutação). Dois cliques criam dois modifiers como antes.

**V-E3-03 — register/unregister (PASS em mocks).** `__init__.py:239-293`: registro normal/inverso, dupla chamada, falha antes de cada `register_class`, rollback parcial, falha de rollback, nova tentativa, falha em cada `unregister_class` e retry. Classes pendentes corretamente rastreadas quando `register_class` lançou antes do efeito colateral.

**V-E3-04 — Semântica anterior preservada.** `_collect_objects_from_visible_collections`, `TIAGO_OT_disable_modifiers`, `VIEW3D_PT_tiago_tools` e `CLASSES` são AST idênticos à v1.0.1. `Todos` inclui objects da Scene, `Visíveis` filtra collections e **não** `obj.visible_get()`, só `show_viewport` é alterado, batch tolera erros individuais e retorna FINISHED, painel mantém 2 botões de batch + Safe Sub e **sem** Random Colors. Não são novos regressos.

## Achados e riscos residuais

### A-E3-001 — MEDIUM — Falha de `new()` após mutação antes de devolver handle

- **Tipo:** lacuna do contrato de rollback, **hipótese no Blender real**, reproduzida **somente por injeção sintética**; preexistente na v1.0.1.
- **Fonte:** `__init__.py:153-169`.
- **Causa:** a variável `modifier` segue `None` quando o mock `obj.modifiers.new()` adiciona o modifier e lança antes de retornar.
- **Efeito sintético comprovado:** o operador retorna `CANCELLED`, não remove o novo modifier e, por regra documentada do Blender, `CANCELLED` não cria Undo. Isso violaria a expectativa de rollback se ocorrer no runtime nativo.
- **Reprodução:** `test_new_partial_side_effect_leak_known_gap` em `04_HARNESS_A_INDEPENDENTE.py`, resultado PASS por validar **o risco**, não a segurança.
- **Recomendação mínima:** não atribuir essa sequência ao Blender sem prova; testar erro em dados linked/override de fixtures e inspecionar antes/depois. Em relatório E4, tratar qualquer side effect real com CANCELLED como HOLD.

### A-E3-002 — MEDIUM — Remoção falha: operação termina com estado possivelmente parcial e depende de Undo

- **Tipo:** comportamento **comprovado no código e em injeção sintética**; sucesso do Undo **não verificado no Blender**; alterado intencionalmente em v1.0.2.
- **Fonte:** `__init__.py:155-185`.
- **Causa:** falha de setter após criação, seguida de exceção em `obj.modifiers.remove(modifier)`.
- **Efeito:** `FINISHED`+`WARNING`, com modifier ainda presente quando `remove()` falha sem remoção. Se falhar no primeiro setter, o novo modifier pode permanecer ativo. O status é coerente com a recomendação oficial sobre Undo após mutação parcial, mas **não é rollback automático nem garante que o operador possa desfazer no contexto real**.
- **Reprodução:** 12 testes `test_setter_cleanup_fails_*`; adicional `test_remove_after_side_effect_gets_finished_warning` prova que o código não distingue `remove()` que muta antes de lançar — **apenas mock**, não atribuir ao Blender.
- **Recomendação mínima:** validar Undo real via UI/operação registrada (não apenas chamar `execute`), capturar contagem/flags antes/depois/Undo e evitar meshes pesadas enquanto não houver prova.

### A-E3-003 — LOW — Rastreamento pode perder classe se `register_class` mutar e lançar depois

- **Tipo:** hipótese de excepcionalidade no Blender; reproduzida exclusivamente com mock artificial.
- **Fonte:** `__init__.py:251-272,275-293`.
- **Causa:** `_REGISTERED_CLASSES.append(cls)` ocorre **após** `bpy.utils.register_class(cls)` retornar. Se esta última lançar apesar de ter registrado o `cls`, a classe atual não entra no rastreamento e `unregister()` do módulo não a verá.
- **Efeito sintético:** classe órfã em mock. **Não há prova** de que `bpy.utils.register_class` 5.0/5.2 tenha tal efeito pós-exceção, nem de que as classes concretas o provoquem.
- **Reprodução:** `test_side_effect_register_error_orphans_class_known_gap`, com 3 pontos de falha.
- **Recomendação mínima:** ciclo real habilitar/desabilitar, restart e upgrade em ambiente descartável; classificar esta situação como hipótese até evidência nativa. Não criar patch especulativo só por esse mock.

### A-E3-004 — LOW — Semântica de Visíveis continua por coleção, não por objeto

- **Tipo:** **fato comprovado** mas **não defeito novo**; contrato anterior explícito.
- **Fonte:** `__init__.py:23-32,63-69`.
- **Efeito:** objeto individualmente oculto mas pertencente a collection visível é processado. Invariante AST idêntico à v1.0.1.
- **Reprodução:** `test_visible_only_per_collection_not_hidden_object`.
- **Recomendação:** preservar sem alteração; confirmar entendimento da UI em E4.

### A-E3-005 — LOW — Registro em memória não detecta alterações externas

- **Tipo:** hipótese de workflow externo, demonstrado em mock; **não introduzido como falha de API 5.2**.
- **Fonte:** `__init__.py:248,255-259,277-293`.
- **Efeito:** se uma ferramenta externa desregistrar todas as classes sem atualizar `_REGISTERED_CLASSES`, `register()` pula classes, `unregister()` falha e guarda pendências. Fluxo normal do próprio addon não faz isso.
- **Reprodução:** `test_external_deregistration_stale_track_does_not_self_heal`.
- **Recomendação:** testes de refresh/reinstalação/restart reais, sem manipular registros de outros addons.

## Matriz da decisão

| Gate | Resultado | Alcance |
|---|---|---|
| G0 custódia | PASS | original e membros manifestos íntegros |
| G1 patch/AST | PASS | 5 diffs reconstituídos; invariantes estáticos mantidos |
| G2 metadados | PASS estático | TOML válido e esquema oficial `1.0.0`; CLI faltante |
| G3 mocks adversariais | PASS com ressalvas | 59 testes; asserções de riscos residuais também passaram |
| G4 APIs documentadas | Sem contradição documental comprovada | não implica execução nativa |
| G5 Blender real 5.0.0 | BLOCKED / NÃO EXECUTADO | execução indisponível/não autorizada nesta fase |
| G6 Blender real 5.2.2 LTS | BLOCKED / NÃO EXECUTADO | idem |
| G7 Produção | NÃO AUTORIZADO | Master e proprietário são decisores; E4 obrigatório |

**Conclusão:** Ausência de `BLOCKER` comprovado **novo** na v1.0.2, reparos E1 contemplados documentalmente e comportamentos comuns exercitados em mock justificam **GO ESTÁTICO PARA TESTES**. Isso **não certifica compatibilidade runtime, resistência a cenários extremos nem aptidão de produção**. Qualquer comportamento real não previsto, perda de dados ou Undo falho exige HOLD e investigação.
