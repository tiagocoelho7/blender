# T7 Measures - GitHub custody import

Repository: `tiagocoelho7/blender` / `addons/t7-measures/`.
Target branch: `import/t7-measures-m0-v0001-custody-2026-10-25`. Base main commit: `bab6b840d2b3524ef9754acdeca35995b41dab11`.

## Frozen assets
- `handoff/T7_MEASURES_M0_CANDIDATA_AUDITORIA_AB_2026-10-22.zip` is the COMPLETE original M0 archive: 39 members, SHA-256 `d3ada0f317142f9f21bba7b90836e9981920e08612d7609dd7b35758091028c9`.
- `handoff/M0/` contains a byte-identical extraction of those 39 members, including embedded `inputs/master_original.zip`.
- `snapshots/m0/` mirrors the 12 source, test and runner files of the frozen M0 0.0.1 candidate. Their declared aggregate hash is `5144810350a34011232513b278ae42639c10a48f38cab0e7d237427d6b95cb6a`; individual 12/12 hashes verified.

## Gate
- This is an OFFLINE PURE PYTHON mathematical kernel M0, NOT an installable Blender addon.
- M0 was authorized only for offline implementation/documentation, not integration or live Blender access.
- The M0 ZIP was prepared for later independent A/B review, whose SUBSEQUENT reports (23 Oct) are NOT included in this ZIP. Never represent this import as A/B technical approval. The recorded technical status after independent reviews is unresolved/HOLD; original independent audit bundles must be obtained before closing the technical gate.
- No Blender/bpy, .blend modification, M1/M2, product or release authorized by import.
- GitHub Master gates only byte-preserving import; the technical Master controls next steps.

## Recheck
Run `python3 addons/t7-measures/GITHUB_MASTER_IMPORT_VERIFY.py` from repository root.
