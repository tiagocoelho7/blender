# T7 Statue Mover - GitHub custody import

Repository: `tiagocoelho7/blender` / `addons/t7-statue-mover/`.
Target branch: `import/t7-statue-mover-v1221-custody-2026-10-25`. Base main commit: `bab6b840d2b3524ef9754acdeca35995b41dab11`.

## Frozen assets
- `handoff/T7-STATUE-MOVER-HANDOFF-COMPLETO-2026-10-23.zip` is the COMPLETE original 21-member handoff, SHA-256 `e0ddd3bd549f7c6112da3a71a47eba7424a25594be4fd853b5d892c6b68f8626`. It includes all historical runtime/cheap bundles as nested original ZIPs.
- `handoff/t7-statue-mover-v1.2.21-candidate.zip` is the EXACT original candidate, SHA-256 `7d475cfb4453ba3abc34da32a56274e4c296caebb614a78363c4c63edd57044f`.
- `snapshots/v1.2.21/t7_statue_mover/` is a byte-identical readable extraction of the candidate ZIP (25 files; 24/24 manifest).
- `handoff/documentos_extraidos/` includes only the NON-ZIP documents for GitHub reading (original nested ZIPs are available inside the complete original handoff). Its `MANIFEST.sha256` applies to the original full ZIP, NOT this selected extracted subset.

## Gate
- v1.2.21 is frozen. Existing reports describe GO WITH CONDITIONS in Blender 5.0.0 headless. This GitHub custody import is NOT a release and adds NO runtime testing.
- Windows interactive GUI/event loop, Undo and drivers auto-exec gates remain pending; no unrestricted production approval.
- The original output report and evidence of the v1.2.21 runtime auditor are NOT in this bundle. Only their summary/inventory is in the handoff. Required filenames:
  * `T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-AUDIT-REPORT.md`
  * `T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-AUDIT-EVIDENCE.zip`
  Do not claim to have checked those original bytes.
- No Blender, bpy, real BLEND, install, tests, code edits, tags, or releases authorized.
- The GitHub Master reviews a PR for custody only; the dedicated technical Master owns technical gates.

## Recheck
Run `python3 addons/t7-statue-mover/GITHUB_MASTER_IMPORT_VERIFY.py` from repository root.
