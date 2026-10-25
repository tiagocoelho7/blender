# AGENTS - T7 Measures

This is a personal Blender measurement addon project, currently only an offline Python M0 kernel.

For import/custody operations:
- Read GITHUB_MASTER_IMPORT_README.md and GITHUB_MASTER_IMPORT_MANIFEST.json first.
- Preserve handoff/ and snapshots/m0/ byte for byte. Do not patch them in place.
- M0 independent A/B review reports are not in the original M0 bundle; do not infer a GO or production approval.
- Do NOT execute source/tests, install dependencies, run Blender/bpy, access `.blend` files, begin M1/M2 or ship an addon as part of this import.
- No changes outside addons/t7-measures, no merge, tags, release, main mutation.
- Technical changes require separate authorized work under the dedicated technical Master.
