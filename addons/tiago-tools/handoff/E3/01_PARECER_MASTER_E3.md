# Parecer do Chat Master — Fase E3 — Tiago Tools 1.0.2
**Data:** 20/10/2026  
**Veredito:** **GO PARA E4 CONTROLADO, CONDICIONADO A AUTORIZAÇÃO EXPRESSA DE TESTES NO AMBIENTE WINDOWS.**  
**Para produção:** **HOLD — E4 não executada; nenhuma certificação nativa 5.0/5.2.2.**

## 1. Papel, autoria e independência

O Master criou o patch E2 e **não o auto-homologa**. E3 contém duas auditorias externas independentes de A e B, feitas sobre candidatos congelados e sem consulta cruzada declarada. O Master verificou integridade, reexecutou harnesses offline e conciliou os achados; isso permite decisão de passagem de gate, NÃO comprova funcionamento real. O Work não foi acionado e não foi feito novo patch.

## 2. Cadeia de custódia recalculada

| Artefato | SHA-256 recalculado |
|---|---|
| Auditor A E3 (ZIP resultado) | `c55ae03ccaed596573ddec6850db14949816fb9794c2cd7a4f862821f39293ce` |
| Auditor B E3 (ZIP resultado) | `30d7fa2806ebaf73d1f5897ab7eb83ca49a06d3fa7af449ad87548a9b8f7cd54` |
| Candidata v1.0.2, idêntica A/B e ao E2 | `28cba4b80e058e726f1e802498588d80278897918a4163b554c6697edda5bad2` |
| Baseline v1.0.1 | `30dc30ec35dc2b8444366bf4faea40dbe4106176cdea68b2604ae0750f191548` |
| Referência histórica v1.0.0 | `18f727f6cb58297e94ac14af4c656b7ae631e56f71076aaf68bf9bb863406e99` |

Manifestos recalculados: A **21/21**, B **19/19**, sem divergências ou arquivos não listados. ZIP CRC: limpo. Arquivos internos da candidata: **4/4** hashes do `SHA256SUMS.txt` conferidos. Metadados: `schema_version="1.0.0"`, `version="1.0.2"`, `blender_version_min="5.0.0"`. Diferentes nomes de remessa individual A/B não implicam diferenciação dos arquivos comuns.

## 3. Evidências e resultados

| Controle | Auditor A | Auditor B | Reprodução Master |
|---|---|---|---|
| Gate | GO estático | GO estático com restrições | GO apenas E4 |
| Tipo | Simulado + revisão API | Simulado + adversarial | Reprodução em cópias |
| Casos | **59 testes** | **60 cenários** (30 conformes, 30 observações de risco) | A: 59/59; B: 60/60 expectativas do harness |
| Falhas de asserção | 0 | 0 | 0 |
| Blender 5.0.0 ou 5.2.2 real | Não | Não | Não |

**ATENÇÃO:** um teste de risco que observa falha sintética é um PASS do harness, mas não um atestado de segurança. Não confundir 30 `RISCO_OBSERVADO` com 30 defeitos confirmados no Blender.

## 4. Correções E1 atendidas dentro do alcance estático

1. **Safe Sub:** removendo somente modifier recém-criado se a escrita de uma propriedade falha, preservando preexistentes; quando a remoção também falha, retorna `FINISHED`+`WARNING`, para permitir Undo. Testado somente em fake `bpy`. A eficácia do Undo depende do Blender real.
2. **Registro:** tracking, rollback e retries em falhas antes dos efeitos; falhas após efeitos podem desalinhar tracking (mock artificial, não comprovado nativamente).
3. **Manifesto:** schema correto e versão distinta; validação CLI oficial ainda não executada.
4. **Invariantes:** coletores, batch e painel com AST idêntica à v1.0.1; comportamento `Visíveis` por collection, adição nova de SUBSURF por clique, sem Random Colors. Não redesenhar contrato sem pedido.

## 5. Matriz conciliada de achados

| ID Master | Achados de origem | Avaliação | Prova e consequência |
|---|---|---|---|
| **M-E3-01** | A-E3-002 / B-001 | **HIGH CONDICIONAL** — prioridade máxima E4 | Setter falha e `remove()` falha: novo SUBSURF pode permanecer ativo com `FINISHED`/warning; reproduzido **em simulação**, não em bpy nativo. Depende de Undo real e ação do usuário. Bloqueia produção até validação E4 e esclarecimento do residual. |
| **M-E3-02** | A-E3-001 / B-002 | **MEDIUM, hipótese nativa** | `new()` cria mas lança antes de devolver handle, ou retorna None: pode haver mod residual com `CANCELLED` sem Undo. Só demonstrado em fake API, sem prova de ocorrência nativa. Não implementar conserto especulativo antes da E4. |
| **M-E3-03** | A-E3-003 / B-003 / B-004 | **MEDIUM, hipótese nativa** | `register_class` ou `unregister_class` altera estado mas lança depois: rastreamento órfão/fantasma em mocks. Ciclos reais de enable/disable/upgrade têm prioridade. |
| **M-E3-04** | A-E3-005 / B-009 | **LOW–MEDIUM, fluxo excepcional** | Hot-reload / alterações externas podem invalidar identidade de classes e tracking. Testar atualização real e restart; não supor rejeição native. |
| **M-E3-05** | B-005 | **MEDIUM, desempenho hipotético** | Janela entre `modifiers.new()` e `show_viewport=False`: risco de avaliação transiente. Começar teste em mesh pequena, monitorar custo. |
| **M-E3-06** | B-006 | **LOW, injeção contrafactual** | Mock ignora setter silenciosamente; verificar os seis campos diretamente via RNA real em E4. |
| **M-E3-07** | A-E3-004 / B-007 / B-008 / B-010 | **LOW, contrato anterior** | Visíveis filtra collections e não visibilidade individual; batch best-effort; cada clique Safe Sub cria mod; leitura contextual pode lançar antes de laço. Manter contrato; verificar em fixtures. |

**Sem BLOCKER comprovado de compatibilidade API do Blender 5.2.2.** A severidade HIGH acima se refere a impacto potencial de uma cadeia excepcional reproduzida em mock, e não a falha nativa demonstrada.

## 6. GATES

| Gate | Status | Próximo ato |
|---|---|---|
| E0 custódia | CONCLUÍDA | Original congelado |
| E1 A/B v1.0.1 | HOLD encerrado por nova candidata | Não retomar versão antiga |
| E2 patch Master v1.0.2 | CONCLUÍDA | Candidato SHA congelado |
| E3 reauditoria A/B | **GO ESTÁTICO COM RESTRIÇÕES** | Aprovar preparação E4 |
| E4 Blender real 5.0.0 e 5.2.2 | **PENDENTE / NÃO AUTORIZADO NESTA REMESSA** | Pedir autorização específica, perfis/fixtures descartáveis |
| Produção | **HOLD** | Não instalar sobre perfil real |
| Work | **ESTACIONADO** | Escalonar somente por tarefa específica e autorização expressa |

## 7. Deliberação

**Aprovo a passagem documental para preparação de E4, não a versão para uso em produção.** Priorizar verificador CLI nativo, instalação isolada, happy path de Safe Sub, leitura de seis propriedades, batch, UI, Undo, registro/reinstalação e performance mínima, com evidências. O caminho mais econômico é um teste nativo limitado em Windows, em ambiente isolado, sem mobilizar Work. Se existir falha comprovada na E4, abrir uma tarefa de patch E5 mínima e reauditoria A/B; caso contrário, avaliar residual e deliberar produção com proprietário.

Não usar Work apenas porque A/B deram GO estático. A instrução anterior do proprietário exige tarefa específica, justificativa e autorização antes de qualquer chamada.
