# PARECER TÉCNICO INDEPENDENTE — AUDITOR B — E3

Data: 20/10/2026. Projeto pessoal: Tiago Tools v1.0.2, migração Blender 5.0.0 → 5.2.2 LTS.

## 1. VEREDITO

**GO ESTÁTICO PARA TESTES E4, COM RESTRIÇÕES.**
**GO PRODUÇÃO: NEGADO / NÃO AVALIADO.**

Trata-se de liberação **somente da passagem documental-estática** para execução de testes reais controlados em perfis, cenas e arquivos descartáveis, após conciliação dos auditores e autorização do proprietário. Não autoriza instalar em perfil habitual, usar com trabalho real, executar batch em acervo ou presumir compatibilidade real.

Motivos do GO estático: nenhum defeito de API 5.0/5.2.2 demonstrado documentalmente; manifesto corrigido para o formato oficial; cadeia de custódia e cinco diffs verificados; código funcional preservado da v1.0.1 em batch, coleta e painel; limpeza direcionada ao handle novo confirmada em simulações com setter que lança exceção; registro/desregistro melhorado no cenário comum e rollback preexistente em falha injetada *antes* do efeito. **GO estático não significa que todos os riscos foram eliminados.**

Há um risco operacional de alto impacto residual (B-001) se a limpeza do Safe Sub falhar: um modifier pode permanecer parcialmente configurado. A opção `FINISHED` + `UNDO` é mitigação alinhada à documentação, mas a existência/eficácia da etapa Undo foi **apenas inferida da API, não observada no Blender**. Uma falha real nesse gate ou falha na verificação do manifesto deverá retornar **HOLD**, exigindo decisão do Master.

## 2. Prova e metodologia

- **PROVA de bytes**: ZIP externo, ZIP comum, 3 ZIPs de código, manifesto SHA-256, CRC, path traversal, symlink e 5 diffs exatos, conforme `custodia_indep_b_e3.json` e `log_custodia_b_e3.txt`.
- **PROVA estrutural**: AST idêntico entre 1.0.1 e 1.0.2 para `_collect_objects_from_visible_collections`, `TIAGO_OT_disable_modifiers` e `VIEW3D_PT_tiago_tools`; `bl_info` e TOML analisados localmente.
- **PROVA de execução simulada**, não do Blender: 60 cenários, Python 3.13.5, módulos `bpy` falsos independentes, 30 conformes, 30 injeções/estados adversariais observados, nenhuma asserção final falha. O programa foi escrito independentemente do harness do autor; `test_adversarial_independent_b_e3.py`, JSON/log anexos. `PASS` significa que a **expectativa declarada do auditor** foi observada. `OBSERVED/RISCO_OBSERVADO` significa que um modelo adversarial atingiu o comportamento de risco esperado. Não significa bug verificado em RNA real.
- **PROVA documental externa**: as referências oficiais indicam `schema_version = "1.0.0"`, `ObjectModifiers.new/remove`, propriedades do modifier e contrato `FINISHED`/`CANCELLED` e `UNDO`. Validador e versão executável oficiais **não rodados**.
- **Hipóteses**: exceções nativas pós-efeito, setters silenciosamente ignorados, falha de `new()` após alocação, efeito performance transitório e hot-reload devem ser comprovados ou rejeitados em Blender real; o mock não os prova no runtime.

**Não consultei o parecer atual do Auditor A nem usei o Work. Não houve acesso a `.blend` real.**

## 3. Dez achados/ressalvas (nenhuma incompatibilidade Blender comprovada)

### B-001 — HIGH — Estado residual se `remove(modifier)` falhar
- **Arquivo:linha:** `__init__.py:158-185`, especialmente `171-185`.
- **Prova:** fluxo do código + simulação T-015..T-020 para todos os seis setters com `remove()` lançando **antes** da remoção. Observado `FINISHED` + `WARNING` + um SUBSURF recém-criado permanecendo; as propriedades podem estar nos valores default. `T-021..T-026` cobrem remoção efetiva seguida de exceção: ainda retorna `FINISHED` com warning, sem resto, uma opção conservadora.
- **Impacto:** modifier parcial potencialmente ativo; efeitos imprevistos no viewport/render e, em meshes pesadas, custo computacional. Não constitui regressão simples: nova mitigação em 1.0.2 é melhor que 1.0.1, mas não garante rollback.
- **Correção/teste mínimo:** teste real em fixture leve com erro de permissão/configuração seguro, inspecionar estado e efetividade do Undo via operador no painel. Caso Undo não reverta, HOLD. Não inferir Undo automático em execução de Python fora do fluxo usual de operadores.

### B-002 — MEDIUM — Falha de `new()` pós-efeito ou interrupção pode deixar mod sem Undo
- **Arquivo:linha:** `__init__.py:153-169`; handler `except Exception`.
- **Prova de modelo:** T-028 (fake `new()` adiciona e lança antes de devolver handle) e T-029 (`new()` devolve `None` após alocar): `CANCELLED` com residual. T-059 injeta `KeyboardInterrupt` durante setter, que escapa de `except Exception`, deixando novo modifier sem controle do retorno. Documentação: `CANCELLED` não cria undo step normal.
- **Limite/hipótese:** `ObjectModifiers.new` na API oficial normalmente devolve modifier; **não foi demonstrado** que Blender 5.0/5.2.2 gere esses cenários. Não recomendar manipular `BaseException` sem análise da semântica de cancelamento do Blender.
- **Mitigação/gate:** registrar a limitação de atomicidade; investigar retornos reais da API, interrupção e fixtures de estresse limitadas, sem fingir teste de crash.

### B-003 — MEDIUM — Registro pode ficar órfão se `register_class` altera estado e depois lança
- **Arquivo:linha:** `__init__.py:251-272`, `257-259`.
- **Prova de modelo:** T-046..T-048: mock registra classe N=1..3 e lança **depois**; a classe ofensora fica fora de `_REGISTERED_CLASSES` e `unregister()` subsequente não consegue descobri-la.
- **Limite:** o comportamento pós-efeito é hipótese para `bpy.utils.register_class`; não é uma falha real constatada. Os testes normais e falhas **antes** do efeito passaram T-043..T-045.
- **Mitigação/gate:** ciclo nativo com erro de registro e controle de duplicidade, habilitar/desabilitar/atualizar e reiniciar perfil isolado; validar ausência de classes órfãs sem interferir em addons terceiros.

### B-004 — MEDIUM — Tracking fantasma quando unregister remove classe e em seguida lança
- **Arquivo:linha:** `__init__.py:275-293`, `281-287`.
- **Prova de modelo:** T-052..T-054: mock faz remoção da classe N=1..3, depois lança; classe permanece no tracking e não no registro efetivo. Retry falha e `register()` ignora classe fantasma.
- **Limite:** pós-efeito modelado, sem prova no Blender. T-049..T-051 confirmam que falha **antes** da remoção é recuperável por segundo `unregister()`.
- **Mitigação/gate:** verificação real RNA após unregister/retry e ciclo de habilitação, desabilitação, reload e reinício. Não apagar classes externas para “limpar”.

### B-005 — MEDIUM — Janela `new` → `show_viewport=False` não é blindada contra avaliação pesada
- **Arquivo:linha:** `__init__.py:155-160`.
- **Prova:** código chama `new()` antes de conseguir ajustar propriedades; padrão também existia na 1.0.1. Pela API `new()` adiciona modifier; não há garantia documental aqui de nenhuma atualização/avaliação antes de `show_viewport = False`.
- **Hipótese:** eventual pico de avaliação/consumo na criação nativa; sem Blender real, não se pode declarar que ocorreu.
- **Mitigação/gate:** medir GUI e consumo/tempo primeiro em mesh pequena, aumentar gradualmente, nunca estrear na base pesada, testar 5.0 e 5.2.2. Não prometer que o script impede todos os picos.

### B-006 — LOW — Ausência de verificação pós-setter contra retorno silenciosamente errado
- **Arquivo:linha:** `__init__.py:159-164`, `193-197`.
- **Prova de modelo:** T-030..T-035: simulações onde uma propriedade aceita escrita mas não atualiza mostram `FINISHED`/INFO com um flag incorreto.
- **Limite:** comportamento contrafactual: não há prova de que setters nativos RNA sejam silenciosos nessas propriedades; sem bug de API comprovado.
- **Mitigação:** E4 ler os seis campos depois da chamada, exigir estados exatos; caso detectado em Blender real, HOLD e proteção por validação pós-escrita.

### B-007 — LOW — Batch best-effort deixa estado parcial por contrato
- **Arquivo:linha:** `__init__.py:78-129`, especialmente `93-114`.
- **Prova:** T-040: uma leitura e um setter falham, terceiro objeto é alterado, operador retorna `FINISHED` com `WARNING` e 2 erros no console; não há rollback integral. É contrato herdado, não regressão.
- **Mitigação:** fixture Blender real com objetos read-only e modificadores não editáveis, inspecionar números, `show_render`, Undo, expectativa do usuário.

### B-008 — LOW — Cliques repetidos no Safe Sub criam modifiers múltiplos
- **Arquivo:linha:** `__init__.py:158`, painel `233-237`.
- **Prova:** T-002: dois cliques resultam em dois SUBSURF. Deliberado e declarado, não defeito novo.
- **Mitigação:** documentação e confirmação real do comportamento; usuários de cenas pesadas devem evitar cliques acidentais.

### B-009 — MEDIUM — Rastreamento é por identidade do módulo e não persiste através de hot-reload atípico
- **Arquivo:linha:** `__init__.py:239-259`, `275-287`.
- **Prova de modelo:** T-057: duas instâncias de módulo têm objetos de classe com identidades diferentes. No mock, IDs poderiam duplicar; a RNA real pode rejeitar IDs repetidos. O tracking é local ao módulo, não inventário global.
- **Limite:** não foi reproduzido problema nativo em atualização via Blender Preferences. **Não extrapolar** de `FakeUtils` permissivo para real registro RNA.
- **Mitigação:** E4 atualizar 1.0.1→1.0.2, desligar/religar, reiniciar, observar IDs e painel duplicados em perfil temporário.

### B-010 — LOW — Exceção na aquisição inicial de objetos fora do best-effort
- **Arquivo:linha:** `__init__.py:63-70`.
- **Prova de modelo:** T-041, fake `scene.objects` lança; exceção escapa do operador. Diferente de falhas em `obj.modifiers` dentro do laço. Nenhum objeto havia sido modificado nesse cenário.
- **Limite:** artificial; premissa de `scene.objects` válida no contexto normal. Contrato herdado.
- **Mitigação:** limitar operador ao contexto correto; se identificado em Blender real, considerar patch em outra etapa autorizada.

## 4. Correções E2 confirmadas independentemente nesta E3

1. **Safe Sub:** no erro de setter com remocão bem-sucedida, remove o handle criado e retorna `CANCELLED`; todos os seis setters, falhas antes/depois, T-003..T-014. T-058 prova proteção do modifier preexistente mesmo com nome coincidente no mock.
2. **Registro:** rollback reverso em falha antes do registro nativo, N=1..3, T-043..T-045; retries normais T-049..T-051; rollback parcialmente falho e retry T-055..T-056; idempotência local T-042.
3. **Manifesto:** `schema_version="1.0.0"` e `version="1.0.2"`, com `blender_version_min="5.0.0"`, parse TOML; ainda requer CLI oficial.
4. **Sem regressão estrutural identificada** em coleta de objects, batch, painel e exclusão de cores aleatórias; os 5 diffs recebidos são reproduzidos byte a byte.

## 5. Comparação Blender 5.0.0 → 5.2.2 LTS

- `bpy.types.Operator`, `Panel`, `EnumProperty`, `bpy.utils.register_class/unregister_class`, `ObjectModifiers.new/remove`, `Modifier.show_viewport/show_render/show_in_editmode/show_on_cage`, `SubsurfModifier.levels/render_levels`, `LayerCollection.is_visible` e `view_layer.layer_collection`: nenhuma incompatibilidade de API foi **comprovada** com as fontes publicadas consultadas. A existência documental de métodos/campos não substitui testá-los em ambos os executáveis.
- `schema_version` é **formato do manifesto**, distinto de `version` do addon. A correção na 1.0.2 segue o exemplo oficial.
- Nenhum import de biblioteca externa, handler, timer, I/O de disco, rede, exporter, mudança de material, origem, transforms ou configuração global encontrado no corpo candidato; a modificação de `.blend` pode ocorrer indiretamente ao editar o estado em memória e salvar o arquivo depois.
- **Classificação:** `A - provável compatível` para a função batch estática; `C - testes especiais` para Safe Sub e ciclo de registro; classificação geral `C - testes especiais`. Sem prova para `D - incompatibilidade comprovada`.

## 6. Recomendação ao Master

Concilie o parecer independente B com o independente A somente **após** ambas as entregas. Mantenha o pacote v1.0.2 congelado no SHA indicado. Se não houver achado bloqueante novo nem divergência irreconciliável, autorize **somente** E4 Windows/Blender real com fixtures descartáveis, hashes, logs, screens e exit codes. Se CLI falhar ou Undo, Safe Sub, registro ou batch falharem de forma funcional real, reverta para **HOLD**. O Master/autor não autoaprova sua candidata; somente proprietário decide produção depois das provas.
