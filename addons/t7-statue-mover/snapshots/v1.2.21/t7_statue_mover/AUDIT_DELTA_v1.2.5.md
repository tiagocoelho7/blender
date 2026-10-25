# AUDIT DELTA — T7 Statue Mover v1.2.5-candidate

## Trigger

v1.2.4 received HOLD for **H-03 HIGH**: `T7SM_OT_Prepare` could disable managed viewport modifiers and return `FINISHED` even when `bpy.data.filepath` referred to no readable/hashable file and therefore no first external baseline existed.

## Fix

Prepare is now a transaction with a hard disk-identity gate:

1. Refuse dirty files before mutation.
2. Require an existing on-disk `.blend`.
3. Require a valid SHA-256 from `blend_file_sha256()`.
4. Re-read the bytes without cache and require the same SHA.
5. Freeze snapshot state.
6. Disable managed modifiers.
7. Re-read/hash the `.blend` again immediately before first-baseline commit.
8. Write the JSON to an isolated candidate path.
9. Read back and verify checksum + schema/snapshot/path/SHA/Scene identity.
10. Promote the candidate to the canonical baseline path and validate it again.
11. Only then set `snapshot_external_ok=True`, expose the embedded snapshot and allow Prepare to return `FINISHED`.

On write/readback/checksum/identity failure, managed modifiers are restored and verified, the partial embedded/runtime snapshot is removed, and Prepare returns `CANCELLED`. A previous external baseline at the same disk identity is preserved until the candidate has already passed validation.

If modifier rollback itself cannot be proven exact, the add-on fails closed and deliberately retains the in-memory snapshot with an explicit `NAO feche o Blender` diagnostic rather than destroying the only remaining restoration evidence.

## Schema

No serialization fields changed. Snapshot schema remains **5**.

## Required regression

Audit the real `T7SM_OT_Prepare` class for:

- non-empty filepath but missing file;
- hash/read failure;
- first external write failure;
- readback/checksum failure;
- happy path with verified JSON;
- file mutation/disappearance between preflight and commit if practical;
- preservation of a prior baseline on failed replacement.

Then re-run H-02, H-01, R-01..R-04 and F-01..F-05, plus exact Blender 5.0.0 runtime gates.
