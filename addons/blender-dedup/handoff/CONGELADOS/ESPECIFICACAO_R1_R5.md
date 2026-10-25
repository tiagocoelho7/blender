# Requisitos definidos com o proprietário — 21/10/2026

## R1 — O que é duplicado

Dois objetos do tipo MESH são duplicados quando a **malha-base não avaliada** possui os mesmos vértices (coordenadas arredondadas em cinco casas), arestas e faces/topologia, permitindo **permutação arbitrária dos índices de vértices**, reordenação das listas de arestas e faces, e rotação cíclica do ponto inicial de cada face (sem inverter winding).

- **Ignorar** na comparação: materiais, UVs, modifiers, shape keys, animações, posição local/mundial, rotação, escala e collections.
- **Não ignorar**: modificações destrutivas da geometria e/ou topologia que persistam na malha-base.
- Aplicar transformações de objeto, se alterar malha-base, pode causar diferença; isso não equivale a simples manipular G/R/S no Object Mode.

## R2 — O que preservar

1. Mais modifiers presentes no objeto.
2. Se empatar, mais shape key blocks no mesh.
3. Novo empate: nome do objeto em ordem alfabética.

Não há regra de preservar versão com mais shape keys caso outra tenha mais modifiers: modifiers são a prioridade absoluta. A regra aceita a perda de recursos da versão descartada.

## R3 — Alcance

Todos os `MESH` do arquivo (fonte `bpy.data.objects`), incluindo objetos ocultos ou em collections desativadas e outras cenas. Objects que nao sao MESH permanecem intocados.

## R4 — Execucao

Calcular e verificar integralmente o plano antes da primeira exclusão; depois remover **automaticamente** os duplicados, sem diálogo ou aprovação individual. Não exigir modo diagnóstico. Manter relatório em console.

## R5 — Segurança e limites explícitos

- O proprietário declarou possuir duas cópias extras de backup.
- Não executar sobre seu `.blend` real sem uma etapa de homologação no Blender 5.0.0 em cópia.
- O pedido para ignorar animações não autoriza a inferência de que referências, children, drivers e constraints são sempre descartáveis. Na candidata, elas **não** são migradas antes de deletar, o que é um risco conhecido.
- A regra de cinco casas **não** equivale a uma garantia de equivalência exata em precisão nativa. Não existe um teste finito de software que prove ausência de quaisquer falhas.

## Critérios de QA mínimos

- Renumeração integral de vértices, arestas e faces sem falsos negativos.
- Vértices de mesmas coordenadas mas conectividades distintas sem falso positivo.
- Faces com início de loop diferente são equivalentes; winding invertido não é.
- Malhas com topologia aplicada diferente não devem ser deduplicadas.
- Prioridade de modifiers vence a quantidade de shape keys.
- Roteiro de testes com objeto-mãe/child, constraints, multi-collection, malhas instanciadas, hidden e linked.
- Teste progressivo no Blender 5.0.0 real em cópias de arquivos com tamanhos representativos.
