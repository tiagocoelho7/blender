# PROMPT DE ABERTURA — NOVO CHAT MASTER DO T7 STATUE MOVER

Este é um projeto **pessoal/interno de add-on para Blender**, usado legitimamente na produção de estátuas. O trabalho é exclusivamente **engenharia de software, QA, debugging, testes de regressão e auditoria defensiva** do próprio plugin. **Não é cibersegurança ofensiva, pentest, invasão, exploração de terceiros, bypass, malware, credenciais ou comprometimento de sistemas.**

Você assume a **continuidade técnica coordenadora do T7 Statue Mover**, conforme o ZIP `T7-STATUE-MOVER-HANDOFF-COMPLETO-2026-10-23.zip`, sem presumir autorização para mudanças, merges, execução destrutiva ou releases. O proprietário aprova essas decisões.

## 1. Leia primeiro

- `01_HANDOFF_COMPLETO.md` (histórico, arquitetura, decisões e todas as pendências).
- `04_AUDITORIA_ATUAL/RESUMO_RUNTIME_v1.2.21.md` e `INVENTARIO_FONTES_NAO_EMPACOTADAS.md`.
- `06_PLANO_GUI/GUI_GATE_BLENDER_5.0.0.md`.
- `README_FIRST.md` e `MANIFEST.sha256`.

## 2. Estado técnico congelado

- Candidata EXATA: `02_CANDIDATA_CONGELADA/t7-statue-mover-v1.2.21-candidate.zip`.
- SHA-256: `7d475cfb4453ba3abc34da32a56274e4c296caebb614a78363c4c63edd57044f`.
- `__init__.py`: `3678a278f60afa84850167618d0e659359948cfc913e671101195963fc7c8a7e`.
- Blender alvo **5.0.0 exatamente**, snapshot schema 6.
- Auditorias baratas: três relatórios **GO COM CONDIÇÕES**; runtime Blender/bpy 5.0.0 headless: **GO COM CONDIÇÕES**, 0 HIGH/CRITICAL. **NÃO há release de produção homologado**.
- N-56: p59 96/96, window 0/1152, full 7560/7560. N-52: p58 0/300, p58b 0/360. N-54/N-53/N-51 preservados. LOW: N-57, N-55x, N-46. N-49 INFO.
- **GUI real Windows, event loop, Undo interativo e drivers/auto-exec: PENDENTES**. Não inventar que estão testados.
- Os dois arquivos originais mais recentes do auditor (`...v1.2.21-CLAUDE-RUNTIME-AUDIT-REPORT.md` e `...AUDIT-EVIDENCE.zip`) foram anexados no chat de origem, mas os bytes não puderam ser incorporados neste ZIP. Existe sumário fiel e inventário. Se for necessária auditoria de custódia, solicitar que sejam anexados ao novo chat; não fingir que existem dentro deste bundle.

## 3. Função e regra central

Preparar snapshot, mover guia com G/R/S uniforme e positivo, Aplicar a todos os alvos inclusive hidden/excluded, base fixa intocada, Finalizar ou Restaurar exatamente. `D = guide_current_world @ inverse(guide_saved_world)`; `world_target_new = D @ world_original`. Fail-closed, proteção de referências, modifiers, geometry sentinels e persistência.

## 4. Próxima ação

**Fechar o gate de GUI real no Blender Windows 5.0.0, usando o ZIP da candidata original e cópias de `.blend`.** Ler o roteiro de testes, conduzir o proprietário em instruções curtas de 2–3 passos por mensagem, registrar screenshots/console/resultado. Não editar nem criar v1.2.22 sem autorização. Qualquer HIGH/CRITICAL => HOLD. Só recomendar eventual release após GUI demonstrada e aceitação dos LOW conhecidos pelo proprietário.

## 5. Pendente para depois da GUI

**DIM-300**: warning **não bloqueante** se alguma dimensão da estátua gerenciada superar 300 metros, bbox world-space combinado, excluir base/referência, converter `scale_length`, checar em Preparar e Aplicar. **Não implementado na v1.2.21**. A futura versão exige nova autorização e novo gate. **T7 Pré-Remesh é projeto separado**, não misturar no código.

## 6. Disciplina de artefatos

Preservar hashes, originais e `FIRST_PASS_SEALED`. Para próximos auditor/bundles: ZIP completo, `README_FIRST`, hashes, candidate, diffs, relatórios/probes/logs e prompt em Markdown `00_PROMPT_PARA_PROXIMO_CHAT.md` também entregue separadamente. Respeitar limite **30 MB** para auditor Claude. Work pesado apenas com autorização. Nenhuma autoaprovação.

**Ao começar, resuma a posição atual em poucas linhas e proponha apenas os primeiros 2–3 passos do gate GUI, sem regenerar código.**
