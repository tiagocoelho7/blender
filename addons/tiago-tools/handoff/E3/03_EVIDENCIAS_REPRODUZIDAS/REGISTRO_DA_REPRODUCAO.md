# Reexecucao offline independente pelo Master — 20/10/2026

- Ambiente disponível: CPython 3.13.5, Linux, Blender real **não disponível** no PATH.
- Auditor A: `python -B <copia>/03_EVIDENCIAS_E_TESTES/08_REPRODUZIR_E3.py` → **59 testes, 0 FAIL, 0 ERROR** (log anexo).
- Auditor B: `python -I <copia>/03_EVIDENCIAS_E_TESTES/test_adversarial_independent_b_e3.py` → **60 cenários: 30 PASS, 30 riscos observados intencionalmente, 0 assert failure** (log anexo).
- Cópias descartáveis usadas. Nenhum `.blend` real, Blender 5.0.0 ou 5.2.2 foi executado, instalado ou alterado.
- Asserções sobre riscos que se reproduzem em um mock contam como execuções corretas do harness, **não aprovação de segurança**.
- Manifests dos relatórios: A **21/21**, B **19/19**; sem arquivos não listados.
- Candidata byte a byte idêntica entre A e B e idêntica ao ZIP v1.0.2 E2 previamente publicado, SHA-256 `28cba4b80e058e726f1e802498588d80278897918a4163b554c6697edda5bad2`.
