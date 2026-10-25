# Parecer MASTER — Auditoria A/B do CODIGO Blender Dedup v1.0.1

Data: 2026-10-23. Escopo: documentos, codigo e harnesses Python **offline** dos Auditores A e B.

## Decisao

**HOLD para prosseguir ao gate Blender 5.0.0 real, instalacao, exclusao automatica em .blend e producao.**

**GO limitado para trabalho de correcao OFFLINE** em candidata nova, preservando o original v1.0.1 (SHA-256 `1d4175b1190732ea6077232b32d4fd632021f99c9ccb80e5ba15dd5e4dcb9956`). Este GO nao autoriza executar o script real.

A reporta 1 P0, 3 P1, 2 P2. B reporta 0 P0, 3 P1, 2 P2. As 11 observacoes agrupam-se em sete frentes, sem conclusoes opostas. A trata mutacao entre preflight e exclusao como P0; B reconhece a mesma classe P1, com ressalva de nao demonstracao em Blender real.

## Sete frentes a corrigir

1. **TOCTOU / mutacao depois do preflight (A P0-01; B P1-02):** os mocks aceitam mudanca de geometria ou referencias por callback `emit`/side effect da remocao; conferem apenas conjunto de ponteiros, depois removem e afirmam `REMOVOES_CONFIRMADAS`. Evidencia decisiva de fragilidade da API Python da candidata, mas *nao prova* que handlers reais de Blender produzam o mesmo interleaving. Restringir callback, definir dominio de estabilidade, revalidar invariantes criticos; quando impossivel garantir, declarar e abortar conservadoramente. Sem alegar atomicidade/rollback.
2. **Lookup por nome em Text/IDProps (A P1-02; B P1-03):** aliases simples `from bpy import data`, `module=bpy.data`, `getattr(...)` nao ativam scanner; mocks removem 2 objetos. Expandir cobertura ou adotar veto conservador para textos com risco indeterminado. Nao prometer identificar scripts arbitrarios, externos ou computados.
3. **Memoria em grupos ambiguos (A P1-03):** `candidates[a] = tuple(sorted(verts_b))` replica lista por vertice; memoria real supera estimativa cooperativa. Candidatos compartilhados por classe, estimativa O(g^2), refinamento e aborto antes de criar estruturas excessivas.
4. **Granularidade do prazo (A P1-04):** 200 vertices coincidentes com `pair_seconds=0.01` levaram ~0.72 s em replay Master antes de abortar; inserir checkpoints nos loops custosos. Nao prometer deadline rigido de sistema operacional.
5. **KEEP em Edit Mode (B P1-01):** mock com KEEP.mode=`EDIT` e contexto `OBJECT` permite duas remocoes; guardas devem abranger KEEP e DROP, contexto relevante, e estados nao confiaveis; compatibilidade das combinacoes depende de futuro Blender real.
6. **`user_map` unilateral (A P2-05; B P2-01):** mapeamento vazio em mock e aceito apesar de owners conhecidos. Normalizar somente superficies comparaveis, nao exigir equivalencia ingenua com todo RNA; incerteza => aborto.
7. **Ledger incompleto (A P2-06; B P2-02):** incluir lifecycle do owner, `drop_key`, `scan_status`, `action`, `evidence` e diagnosticos acumulados em abortos, distinguindo escopo inspecionado/nao inspecionado.

## Cadeia de custodia Master

- ZIP A recebido: SHA-256 `d28d68e58da01df9a4bcadefe0e5cc2791232ec442f2dcc26e796f2efa5c1ad1`, 94 membros, CRC OK, manifesto 92/92, SHA256SUMS 92/92.
- ZIP B recebido: SHA-256 `ebe1fe227c05ea9608d066d13b16c741ccd3b102016829e8af83d2933848c3d8`, 93 membros, CRC OK, manifesto 91/91, SHA256SUMS 91/91.
- Entrada candidata interna de ambos: 62/62; Master R2 embutido: 33/33 em ambos, sem divergencias.
- Mesmo codigo de candidata A/B: SHA-256 `1d4175b1190732ea6077232b32d4fd632021f99c9ccb80e5ba15dd5e4dcb9956`. Baseline v1.0 e adendo R2 tambem coincidem nos dois pacotes.
- Os dois relatorios afirmam auditoria cega da rodada de codigo; independencia nao foi comprovada alem dessa declaracao e da separacao de entrada.

## Replays realmente conduzidos pelo Master

- 57/57 unittest sinteticos da candidata; 266/266 oraculo A; 2649/2649 geometria A; 32/32 grafo B.
- Oraculo proprio de A: 400/400, sem mismatch; oraculo proprio de B: 160/160 (script executado diretamente, nao como teste unittest).
- Reproduzidos A REF-01 a REF-05; B 11/11 ensaios adversariais e 2/2 crosschecks. **Esses PASS dos adversariais confirmam defeitos**, nao seguranca.
- Prazo cooperativo A: limite 0.01s, medido ~0.7189s, 71.9x, abortou por budget.
- Memoria A: caso n=240 excede em RSS amostrado o cap por par de 60KB, enquanto estimativa fica abaixo. RSS contem overhead e nao e quota fisica.
- Todos os ensaios usaram mock Python/NumPy/NetworkX; nao e homologacao runtime.

## Regras do proprietario permanecem inalteradas

- Identificar a mesma geometria/topologia apesar de renumeracao interna; ignorar posicao, rotacao, escala, materiais, UVs, modifiers e shape keys na deteccao.
- Priorizar por quantidade de modifiers, depois shape keys, depois desempate deterministico; ignorar animacoes.
- Todo objeto MESH do .blend e candidato, independentemente de cenas/collections; cinco casas decimais; malha alterada destrutivamente nao equivale se geometria/topologia diferente.
- Excluir automaticamente apos verificacoes, sem salvar .blend. Qualquer incerteza de comparacao/seguranca aborta ANTES da primeira exclusao; erro durante remocoes impede continuar, com ledger de remocao parcial (sem rollback).

## Limites e gate futuro

Nao foi executado Blender real, nem comprovada semantica concreta de RNA, user_map, scripts externos, dependencias de handlers e desempenho em .blend grande. Qualquer nova candidata requer codigo/arquivo separado, SHA novo, regressao offline + contraprovas A/B e **nova auditoria independente A/B**. Somente apos isso pode ser discutida autorizacao explicita do proprietario para Blender 5.0 em .blend sintetico descartavel. Producao segue HOLD.
