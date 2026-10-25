# T7 Measures — M0 0.0.1, candidata offline para auditoria

Data: 22/10/2026. Núcleo Python experimental sobre fixtures desconectadas de Blender.
**Sem homologação. Blender, `.blend`, instalação, M1/M2 e produção permanecem em HOLD.**

## Conteúdo

- `src/t7m/`: núcleo racional, projeção P, certificados, apresentação e máquina abstrata A/B.
- `tests/`: regressões, contraprovas e oráculo independente por otimização convexa exata.
- `evidence/work_run/`: logs completos, resultados por método/subcaso, ambiente, amostras e alocações Python.
- `docs/01_RELATORIO_TECNICO.md`: resultados e parecer do executor, sem autoaprovação.
- `docs/02_METODO_MATEMATICO.md`: definições, argumentos de correção e limites numéricos.
- `docs/03_RECURSOS.md`: preflight, custo, bit-length e memória experimental.
- `docs/04_COBERTURA.md`: relação com as matrizes R8/R8.1 e gates não executados.
- `docs/05_LIMITACOES.md`: restrições e pendências conhecidas.
- `docs/06_PROMPT_AUDITORIA_AB.md`: prompt comum para chats independentes A e B.
- `docs/07_CONTINUIDADE_MASTER.md`: handoff, sem autorização de próxima etapa.
- `00_AUTORIZACAO.md`: escopo autorizado pelo proprietário.
- `inputs/`: ZIP Master e prompt exatos; normas copiadas sem alterações para leitura direta.
- `SHA256_MANIFEST.txt`: SHA-256 dos membros, exceto o próprio manifesto.

## Reproduzir

Requer Python **3.10 ou posterior**, biblioteca padrão; execução registrada em CPython, versão em `evidence/work_run/environment.json`. Nenhuma instalação, dependência externa ou acesso de rede.

Na pasta extraída:

```bash
python run_offline.py --output replay_results
```

O comando primeiro verifica o manifesto, depois executa a bateria e grava evidências apenas no diretório indicado. Para preservar a candidata congelada, prefira um diretório de saída fora da pasta extraída. O runner não importa, inicia, procura ou acessa Blender nem arquivos `.blend`. Não use o instalador de extensões: este ZIP é um pacote de auditoria Python.

Alternativa somente testes:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

No Windows, prefira o primeiro comando, que ajusta os caminhos Python por conta própria.

## API mínima

```python
from t7m import Entity, Query, measure
r = measure(Query(Entity('V', ((0,0,0),)), Entity('V', ((3,4,0),))))
assert r['distance']['certificate'].lo == 5
```

`Query` recebe coordenadas locais copiadas, matriz linear comum, sistema e escala. Não recebe objeto Blender, caminho de arquivo ou operador. Todas as entidades da consulta pertencem ao mesmo referencial local por contrato de entrada. `Instance` em `session.py` modela UMA instância abstrata, com um slot; sua criação não registra addon real.

## Resultado desta entrega

**44 métodos de teste passaram, zero falhas/erros**, com subcasos discriminados no JSON. O oráculo KKT usa método diferente e não importa o kernel. Os testes cobrem as oito modalidades, mas não constituem prova exaustiva de correção nem aprovação independente. As cotas experimentais são menores que os máximos provisoriamente aprovados; detalhes em `docs/03_RECURSOS.md`.
