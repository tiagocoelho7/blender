# Blender Dedup v1.0.2-test1 — entrega de desenvolvimento

**Veredito do executor: candidata preparada para auditoria independente.** Blender real e produção permanecem HOLD. Resultados próprios não aprovam a candidata. Data: 27/10/2026, America/Sao_Paulo.

## Base, escopo e preservação

Repositório `tiagocoelho7/blender`, base `828aeab4280f650d3d2786d75eee55634b728736`, branch `dev/blender-dedup-v102-test1-2026-10-27`. A `main` remota foi verificada pela integração GitHub antes de trabalhar. O checkout veio como branch `work` nesse mesmo commit; a referência local `origin/main` estava antiga e não foi usada como base. Nenhuma referência `main` foi alterada.

`python verificar_kit.py` foi executado antes de modificar arquivos: **33/33**. Fontes e evidências congeladas permanecem byte a byte; os dois arquivos ZIP originais têm CRC e SHA verificados. Somente arquivos novos em `src_v102_test1/`, `tests_v102_test1/` e `entrega_v102_test1/` integram a entrega. Extrações e adaptações descartáveis ficam em `work/`. Os demais add-ons não foram modificados. Não foi reimportado ZIP nem criado repositório.

## Contrato preservado

Compara toda malha-base MESH em `bpy.data.objects`, independentemente de scene/collection, G/R/S, materiais, UVs, modifiers e shape keys. Quantização float32 promovida a float64, `np.rint(x*100000)`. A bijeção global preserva multiplicidade das arestas e ciclos orientados das faces, permitindo rotação do início e renumeração. Hash/refinamento nunca constituem prova positiva de igualdade. Geometria/topologia destrutivamente alterada continua diferente quando não existe essa bijeção.

Ranking absoluto: mais modifiers, depois mais key blocks, depois ordenação determinística de nome e identidade. Animação não é preferência. Não há remapeamento para KEEP, remoção de Mesh, confirmação individual nem autosave. O modo seguro permite remoção automática; qualquer inconclusivo detectado antes da primeira chamada do executor impede todas as suas chamadas de remoção.

## Evidências executadas

| Prova | v1.0.1 histórica | v1.0.2-test1 |
|---|---:|---:|
| unittest executor | 57/57 | 57/57 |
| Oráculo A adaptado | 266/266 | 266/266 |
| Geometria A | 2649/2649 | 2649/2649 |
| Grafo B | 32/32 | 32/32 |
| Oráculo independente A, seed 20261023 | 400/400 | 400/400 |
| Oráculo independente B/NetworkX | 160/160 | 160/160 |
| B adversariais e crosschecks | 11 + 2 reproduzem observações históricas | 11 + 2 com inversões de segurança PASS |
| Novos testes de segurança | não aplicável | 34/34 PASS, com subcasos |
| Custo A n=100,200,240 | subestimação/prazo reproduzidos | aborto pré-alocação com cap 60 KB; prazos de 10 ms observados |
| Benchmark NumPy 1M vértices + 999999 arestas por malha | igual após renumeração | igual após renumeração |
| Rook × Shrikhande | INCONCLUSIVO por budget | INCONCLUSIVO por budget |

Os detalhes efetivamente medidos estão em `logs/`, `replay_candidate.json` e `replay_original.json`. Tempo/RSS variam por máquina. No replay histórico final, n=200 levou 1.0090 s para prazo cooperativo de 0,01 s. Na candidata, os probes correspondentes abortam perto de 0,01 s. Com cap de 60000 bytes, as três classes ambíguas são recusadas antes de criar os buffers da busca; isso é INCONCLUSIVO, não desigualdade. Um caso simulado de 1M vértices coincidentes é recusado antes de ler/alocar buffers. O benchmark de 1M vértices distintos permanece positivo; não representa tempo de Blender real.

## Adaptações reproduzíveis e limitações de reprodução

`tests_v102_test1/replay.py` extrai os originais para `work/replay/`. Somente a cópia do alvo sob o nome legado `src/remover_duplicatas_blend_v1_0_1.py` recebe os bytes da nova candidata. Casos, seeds e oráculos permanecem inalterados. Os rótulos históricos “v1.0.1” que aparecem nos logs provêm desses harnesses; o alvo efetivo é registrado pelo hash.

O oráculo 266 contém PIN literal da v1.0.1. `oracle266_adapter.py` confirma o PIN histórico e vincula somente sua variável global em memória ao SHA do alvo atual. Não altera arquivo original, hash congelado, corpus, testemunhas ou asserções geométricas.

`replay_inversions.py` executa os mesmos 11 métodos B, inverte as 7 expectativas inseguras e preserva os 4 controles. Os 2 crosschecks passam a exigir `PreflightAborted` e zero chamadas. Todas as transformações estão explícitas no código. A REF-01 a REF-05 de A foram reexecutadas literalmente contra a v1.0.1; as inversões equivalentes estão em `test_safety.py`. REF-02 original aponta `objs[2]`, que é o primeiro DROP pela prioridade. Mantivemos esse alvo e adicionamos um caso separado que aponta ao próximo DROP (`objs[0]`), exigindo parar após uma chamada.

Não faltou nenhum dos arquivos das seis suítes exigidas: todas foram executadas. Não foi executada a parte **real** de C09 nem qualquer gate Blender 5.0/RNA/handlers: não autorizados. A referência a `handoff/05_PROMPT_REAUDITOR_A_FUTURO.md` e `06_PROMPT_REAUDITOR_B_FUTURO.md` no índice original aponta para arquivos ausentes. Os modelos históricos equivalentes existem dentro do Master R2 aninhado nos ZIPs (06/07); foram lidos e usados como orientação para novos prompts, sem reparar o handoff congelado.

O wrapper original `run_memory_samples.py` foi substituído por três subprocessos diretos, com timeout externo, dos mesmos probes n=100/200/240. Evita subprocessos dentro de harness sob o guard offline. É a mesma fixture e algoritmo medidos. Replays de “PASS” históricos adversariais não são contados como correções.

A primeira rodada de desenvolvimento falhou no PIN do oráculo e em duas asserções novas que consultavam o DROP errado na ordem do ranking. As falhas foram preservadas em `logs/development_attempt01/`. Não se alterou a candidata para acomodar essas duas asserções: foram corrigidas as seleções de alvo nos testes. Uma tentativa de verificação de custódia A depois dos replays encontrou os outputs de evidência reescritos na cópia descartável; o runner foi corrigido para verificar custódia antes de executar suítes que escrevem. O log dessa tentativa está em `logs/development_attempt02/`; os originais congelados nunca foram modificados.

## Replay e entrega

Ambiente utilizado: CPython 3.12.14, NumPy 2.4.2 e NetworkX 3.6.1, já instalados. Nenhuma dependência foi obtida pela rede. Consulte `AMBIENTE.json` e `tests_v102_test1/requirements.txt`.

Na raiz `addons/blender-dedup/`, com esse Python isolado:

```sh
python verificar_kit.py
python tests_v102_test1/replay.py --original
python tests_v102_test1/replay.py
python tests_v102_test1/build_packages.py
python tests_v102_test1/verify_packages.py
```

O runner aplica um Python audit hook antes dos imports dos harnesses: bloqueia importação de `bpy`, abertura de `.blend`, rede e execução de subprocessos dentro dos testes. O runner externo controla os subprocessos e seus timeouts. O teste `test_offline_guard_active` prova essas fronteiras. Nenhum Blender real, arquivo `.blend`, ChatGPT Work ou agente auditor foi acionado.

`SHA256SUMS_NOVA_ENTREGA.txt` sela fonte, diff, testes, relatórios e logs. `PACOTES_SHA256.json`/`.txt` registram caminhos, tamanhos e hashes dos três ZIPs, sem autorreferência. O MASTER inclui o kit integral inalterado, nova entrega e os ZIPs A/B. Cada ZIP cego contém a mesma candidata, baseline/contratos, testes originais com proveniência e um único prompt. Não inclui pareceres históricos A/B, resultados ou matriz de conclusões do executor nem o prompt do outro auditor. O Master deve fornecer somente o ZIP de cada auditor e preservar a separação até receber ambos os selos. Os dois ZIPs cegos foram extraídos em diretórios independentes e seus replays completos passaram; o MASTER extraído também passou na verificação de manifestos, diff e kit 33/33. Esses replays de portabilidade continuam sendo QA do executor, não auditoria independente.

O proxy do transporte Git da VM recusou conexão (`Failed to connect to proxy port 8080`). A publicação da branch usa a integração GitHub autorizada, com parent fixo na base e árvore comparada à árvore Git local. Não houve alteração de rede, credenciais, política, `main`, merge, release ou PR. A identidade do commit publicado é informada na resposta final para evitar autorreferência no conteúdo commitado.
