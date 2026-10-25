# Plano de correcao para candidata separada (nome proposto: v1.0.2-test1)

Escopo: somente offline; requisitos funcionais originais congelados. Nao editar a v1.0.1.

## P0 — Confiabilidade antes/depois da exclusao

- Desacoplar logger de callback com efeitos externos. `emit` injetavel nunca pode produzir sucesso com dados obsoletos silenciosamente: restringir seu uso, ou revalidar continuamente as invariantes observaveis; nao depender so de IDs/pointers.
- Preflight com snapshot de geometria/topologia, elegibilidade/flags e grafo de incoming refs dos objetos KEEP/DROP; recheck imediatamente antes da primeira remocao e antes de remocoes adicionais conforme contrato de reentrancia.
- Distinguir: `INCONCLUSIVO_ZERO_REMOVOES`, `ABORT_POR_MUTACAO_ZERO_REMOVOES`, `FALHA_PARCIAL_POSSIVEL`, `REMOVOES_CONFIRMADAS`; nunca registrar sucesso quando o plano esta obsoleto.
- Testar A REF-01/02 e B02/B03/B04: observar 0 remocoes se a mutacao ocorrer antes da primeira; se depois de uma remocao, parar sem prosseguir e emitir ledger parcial. Se eventos internos de Blender nao puderem ser neutralizados, declarar limite e gate de validacao na API real; nenhuma promessa de atomicidade absoluta.

## P1 — Referencias textuais e modos

- Scanner AST/estatico para imports e aliases comuns do namespace `bpy.data`; `getattr`, chamadas .get, indexacao, literais e nomes calculados, inclusive em strings de IDProperty.
- Para escopo realmente indeterminado, escolha conservadora de aborto com razao clara, nao executar scripts. Nao prometer detectar fontes externas ou metaprogramacao arbitraria.
- Corrigir modo/estado de KEEP e DROP em todas cenas/view layers: qualquer objeto candidato em modo nao confiavel resulta em aborto sem remocoes. Fixture do B01 obrigatoria.

## P1 — Comparacao escalavel

- Tratar cada classe de coordenadas coincidentes como unidade; nao duplicar tupla de candidatos por vertice; estimar buffers Python/Numpy conservadoramente, limitar cardinalidade antes de construir.
- Refinamento de particoes antes de backtracking; checkpoint dentro de ranking, adjacency, face-pruning, loops grandes.
- Oraculo exato mantido (bijeccao topologica global, multiplicidades, ciclos orientados de faces); limite => inconclusivo, **nunca** diferente por atalho e nunca igual por hash.
- Regressao com n=100,200,240; pair_seconds=0.01; Rook-vs-Shrikhande; malha com 1M vertices simulada (testar memoria e timeout). Definir criterio de observabilidade de budget cooperativo, sem confundir com hard cap.

## P2 — Evidencias e auditabilidade

- Normalizar semantica efetiva do `user_map` e escopo das memberships comparaveis; ausencia de coverage corroborativa => inconclusivo conservador.
- Ledger com `drop_key`, `owner_lifecycle`, `scan_status`, `action`, `evidence`, `surface`, `category`, `path`, `reason`, estado e justificativa por DROP; agregar blockers sem executar exclusao.
- Validar a reconciliacao diante de erro em print/ledger, exception de remove antes e depois do side effect, KeyboardInterrupt, ultima remocao.

## Gates de aceite da nova candidata (todos obrigatorios)

1. Congelar SHA/manifesto original, gerando nova candidata, diff e novo hash.
2. 57/57, 266/266, 2649/2649, 32/32 regressivos e oraculos independentes A 400/400, B 160/160 ou substitutos equivalentes documentados.
3. Todos os adversariais A/B anteriores executados como **testes de seguranca**, com assercoes invertidas para vetar falsa remocao/sucesso; documentar casos em que um callback mock e incompativel com contrato novo.
4. Nenhum problema P0/P1 sem resolucao documentada, evidencia e contraprova; conclusoes dependentes de Blender real permanecem pendentes.
5. Dois ZIPs separados de reauditoria cega A e B com candidata identica; impedir auditor novo de ler parecer atual do outro.
6. Testes Blender 5.0 real e arquivos do proprietario continuam nao autorizados ate nova decisao explicita.
