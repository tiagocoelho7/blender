# AUDIT DELTA — T7 Statue Mover v1.2.6-candidate

Source baseline: v1.2.5-candidate (`__init__.py` SHA-256 `e4208e4b120690729c91ccec100fdb1aa9bf1d2c191a2fb7c3afa928e7b1162f`).

The v1.2.5 Blender 5.0.0 audit ended HOLD with N-01..N-19. v1.2.6 intentionally changes architecture rather than patching the HIGH findings independently.

## N-01 / N-03 — depsgraph-independent world truth

- Added `channel_world_matrix()` from `matrix_basis`, `matrix_parent_inverse`, OBJECT/BONE parent chains.
- Prepare freezes target world transforms through this helper.
- Apply computes the same D as before but writes a desired local `matrix_basis` via `set_channel_world_matrix()`.
- Apply and Restore verification use channel-derived world values.
- External recovery disk-state validation uses channel-derived world values.
- Unsupported target parent modes fail before Prepare/Apply mutation.

## N-02 / N-09 / N-11 — persistence separation

- Schema bumped 5 -> 6.
- Payload now separates immutable restore state from `disk_state` (what the bound `.blend` actually saved).
- load/register recovery never calls post-save promotion.
- save_pre no longer mutates snapshot identity and is not registered.
- save_post accepts promotion only when handler filepath == current `bpy.data.filepath`; Save Copy is ignored.
- Save As preserves the old file baseline.
- Active embedded snapshots are rebound at runtime to the file actually open, preventing a copied `.blend` from deleting the original's baseline.

## N-04 — arbitrary file deletion

- No filesystem deletion uses `snapshot_backup_path` or any other raw path loaded from a `.blend`.
- External deletion is derived from `(blend path, SHA-256, Scene)` into the CONFIG snapshot directory.
- Canonical realpath, filename format, symlink, checksum, payload identity and snapshot ID are validated before removal.

## N-05 / N-06 / N-07

- Import collection membership now uses `.name in collection` semantics required by Blender 5.0.
- Multi-Scene reference sources fail closed; exactly one Scene is required.
- `user_map()` current Scene relationship is treated as internal, while other Scenes remain external.
- Tagged collections containing untagged objects/child collections block cleanup.
- Manual collection parent/root scans use names and no longer swallow `__contains__` TypeError.
- `libraries` added to tagged datasets for cleanup.

## N-08

- unregister uses exact module class objects in reverse order.
- stale cleanup additionally attempts Blender RNA subclass lookup before attribute fallback.

## N-10

- D must be a positive uniform similarity: Gram matrix approximately `s^2 I` and determinant positive.
- Shear/non-uniform inherited transforms cancel before mutation.

## N-12

- Added local geometry fingerprints for Mesh, Curve/Surface, Font, Armature, Lattice and Meta.
- Unsupported geometry-bearing target types are refused during Prepare.

## N-13..N-19

- N-13: multi-Scene reference source refused.
- N-14: save_post ignores incompatible schemas; no save_pre relabeling.
- N-15: atomic writer removes `.tmp` in `finally`.
- N-16: matrix/sequence verification uses absolute + relative tolerance.
- N-17: no identity mutation in save_pre; Save As preserves old baseline.
- N-18: Library IDs included in reference cleanup datasets.
- N-19: external loader can restore exactly one validated `.previous` baseline after the initial-promotion crash window.

## Deliberate non-go statement

No Blender 5.0.0 runtime is available in the developer container. v1.2.6 has only Python compile/AST/static verification here. It must be audited using the v1.2.5 runtime harness bundle and Blender/bpy 5.0.0 before production.
