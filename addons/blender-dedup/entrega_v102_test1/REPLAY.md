# Comandos de reprodução offline

Use CPython 3.12 com NumPy 2.4.2 e NetworkX 3.6.1 previamente disponíveis. Não é necessário instalar ou importar bpy. Na pasta raiz do MASTER (ou `addons/blender-dedup/` no repositório):

```sh
python verificar_kit.py
python tests_v102_test1/replay.py --original
python tests_v102_test1/replay.py
python tests_v102_test1/build_packages.py
python tests_v102_test1/verify_packages.py
```

O primeiro comando existe no MASTER integral. Nos ZIPs cegos, execute somente `python tests_v102_test1/replay.py`; os testes originais estão em `reference_tests/` com proveniência, e o runner monta as mesmas cópias descartáveis. `--original` também funciona com a baseline v1.0.1 incluída; verificadores dos ZIPs históricos completos só são executados no MASTER, onde esses originais existem. Os scripts não dependem do nome absoluto do diretório da VM. Os caminhos absolutos nos logs registram a execução original, não são requisitos.

`replay_original.json` e `replay_candidate.json` descrevem cada subprocesso, código de retorno e duração. O timeout externo por processo é 180 s; probes n=100/200/240 originais possuem timeout de 8 s. O guard offline é aplicado ao subprocesso de cada harness. Não execute as fontes Blender como `__main__`.

O hash do alvo do oráculo 266 é vinculado em memória, com a lógica/corpus intactos. O nome legado do arquivo na cópia de replay não determina sua versão: confira `TARGET_BINDING_ONLY` e o SHA da fonte nova. Testes históricos adversariais sobre a v1.0.1 reproduzem defeitos; o replay novo usa inversões explícitas e testes equivalentes A. Não somar seus PASS a uma alegação de homologação.
