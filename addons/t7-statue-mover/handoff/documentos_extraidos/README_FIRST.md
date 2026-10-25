# LEIA PRIMEIRO — TRANSFERÊNCIA T7 STATUE MOVER (2026-10-23)

**Candidata operacional:** `02_CANDIDATA_CONGELADA/t7-statue-mover-v1.2.21-candidate.zip` (**instalar ESTE ZIP dentro do Blender**, não o presente ZIP de handoff).

**Status:** 3 cheap audits GO COM CONDIÇÕES + runtime Blender/bpy 5.0.0 headless GO COM CONDIÇÕES (nenhum HIGH/CRITICAL); GUI interativa Windows, event loop, Undo, drivers auto-exec não verificados. **Sem homologação irrestrita de produção.**

**Leitura rápida:** `00_PROMPT_PARA_PROXIMO_CHAT.md`, `01_HANDOFF_COMPLETO.md`, `04_AUDITORIA_ATUAL/RESUMO_RUNTIME_v1.2.21.md`, `06_PLANO_GUI/GUI_GATE_BLENDER_5.0.0.md`.

**Cadeia:** conferir `MANIFEST.sha256`, depois a candidata SHA-256 `7d475cfb4453ba3abc34da32a56274e4c296caebb614a78363c4c63edd57044f`. Não alterar o arquivo: qualquer patch vira nova versão. Não declarar GO de produção por conta própria.

**Lacuna honesta:** o relatório e evidence ZIP originais de SAÍDA da auditoria v1.2.21 estavam anexados ao chat de origem, mas não puderam ser transportados em bytes para este ZIP; existe resumo detalhado e inventário. O bundle de ENTRADA do runtime v1.2.21 está incluído integralmente.

**Arquivos relevantes:**

```text
00_PROMPT_PARA_PROXIMO_CHAT.md
01_HANDOFF_COMPLETO.md
02_CANDIDATA_CONGELADA/t7-statue-mover-v1.2.21-candidate.zip
03_BUNDLE_ORIGINAL_ENTRADA_RUNTIME/T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-BUNDLE.zip
04_AUDITORIA_ATUAL/RESUMO_RUNTIME_v1.2.21.md
04_AUDITORIA_ATUAL/INVENTARIO_FONTES_NAO_EMPACOTADAS.md
05_HISTORICO_REFERENCIAS/[versões anteriores/diffs/precheck]
06_PLANO_GUI/GUI_GATE_BLENDER_5.0.0.md
99_NEXT_CHAT/00_PROMPT_PARA_PROXIMO_CHAT.md
MANIFEST.sha256
```

Projeto: **add-on pessoal legítimo Blender**, QA/engenharia defensiva, nada relacionado a ofensiva digital.
