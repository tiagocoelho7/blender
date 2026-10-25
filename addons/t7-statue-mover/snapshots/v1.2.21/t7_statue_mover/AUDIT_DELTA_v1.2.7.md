# AUDIT DELTA — T7 Statue Mover v1.2.7-candidate

## Source baseline

v1.2.7 is derived from the frozen v1.2.6 candidate. The v1.2.6 independent Blender 5.0.0 audit returned HOLD.

The original v1.2.6 artifact had one absolute blocker:

- **N-22 CRITICAL:** `CLASSES` was referenced but never defined, so the add-on could not enable.

The auditor then applied a separate, explicitly non-candidate `CLASSES` patch to measure the architecture. With that patch, N-01..N-10 from the v1.2.5 audit passed in Blender/bpy 5.0.0. Remaining defects were:

- N-20 MEDIUM — tagged Library residual prevents reference cleanup from completing;
- N-21 MEDIUM — `snapshot_external_ok` remains true after post-save promotion failure;
- N-23 MEDIUM — POINTCLOUD can bypass geometry/origin verification;
- N-24 LOW — orphan `.candidate` after crash recovery.

## v1.2.7 changes

### N-22

- Restores an explicit `CLASSES` tuple before any registration helper uses it.
- Tuple contains all 13 classes in the same order used by the auditor's successful experimental patch.
- Developer gate now checks Python compilation and unresolved global names with `symtable`; `CLASSES` is confirmed defined.

### N-20

- Libraries are excluded from the generic `users == 0` data-block pass.
- A Library external-reuse preflight runs **before any destructive reference cleanup**.
- External reuse means an untagged ID actually points to the Library via `.library` or override reference.
- The broad Scene/user-map relationship is not considered Library reuse.
- After all other tagged IDs are removed, a tagged Library with no real external linked/override users is removed last even if Blender reports `users == 1`.
- Any Library external reuse blocks cleanup before objects/collections are deleted.

### N-23

- POINTCLOUD fingerprint added from the `position` attribute.
- Prepare policy generalized: every unsupported target type fails closed unless in explicit no-local-geometry allowlist (`EMPTY`, `LIGHT`, `CAMERA`, `SPEAKER`, `LIGHT_PROBE`).
- Postflight geometry verification follows the same generic policy.
- Existing CURVES/GREASEPENCIL/VOLUME remain refused until they have a safe fingerprint.

### N-21

- A failed real-save external promotion immediately clears `snapshot_external_ok` and `snapshot_backup_path` and records a visible panel warning.
- Successful promotion clears that warning.
- `persist_snapshot()` revalidates redundancy only when the frozen baseline path/SHA still match the **fresh SHA of the bytes currently on disk**. An old-SHA baseline can no longer re-enable the indicator after a failed promotion.
- Recovery displays an explicit warning when only embedded persistence is valid.

### N-24

- When a validated `.previous` is recovered after the narrow crash window, validated orphan `.candidate` files for the same `snapshot_id` are removed.
- Normal valid canonical loads do not indiscriminately delete candidate files, avoiding unnecessary interference with another live process.

### Minor message correction

`Restore Modifiers` no longer reports the misleading text "Finalização bloqueada" for a geometry gate failure.

## Persistence/schema

No persistent field layout used for restoration/disk-state changed, so schema remains **6**. The new `snapshot_persistence_warning` is runtime/UI status rather than recovery identity.

## Developer-side gates executed

- `python -m py_compile`: PASS.
- AST/static security scan: PASS for prohibited imports/actions; no network/subprocess/shell/eval/exec/modifier_apply/auto-save patterns.
- `symtable` unresolved-global gate: PASS (`[]`).
- `CLASSES` tuple is present before `register()`/`unregister()` use.
- ZIP integrity/hashes to be frozen after documentation generation.

`pyflakes` was requested in the audit, but the developer container could not download it because DNS/network access is unavailable. The independent auditor must run `pyflakes` or `ruff F821` in its environment and treat any undefined name as HOLD.

## Mandatory independent regressions

The auditor must use the **unmodified v1.2.7 ZIP**, with no `CLASSES` patch or other source patch, and rerun the v1.2.6 evidence bundle. Priority gates:

1. install/enable/register/unregister/re-enable/F8;
2. N-20 happy cleanup + F-05 failed import cleanup in the same session;
3. N-23 Point Cloud Set Origin and generic unsupported-type refusal;
4. N-21 failed save-post promotion followed by operator persistence;
5. N-24 real `os._exit` crash-window recovery and candidate cleanup;
6. N-01..N-10 and H/F/R historical regression suites;
7. Blender 5.0.0 GUI-only pending gates.
