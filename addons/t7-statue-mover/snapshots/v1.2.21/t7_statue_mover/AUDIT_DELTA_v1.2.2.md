# Audit delta — v1.2.2-candidate

The v1.2.1 independent audit returned **HOLD**. This file records developer-declared changes only; auditors must reproduce them independently.

## R-01 HIGH — Restore geometry/origin sentinel

Declared correction:

- new `verify_geometry_sentinels(settings)` centralizes target mesh sentinel readback;
- Restore checks it **before** restoring transforms/modifiers and returns `CANCELLED` with snapshot preserved on mismatch;
- Restore checks it again post-restore before snapshot deletion;
- Finalize also refuses to delete the checkpoint if target geometry/origin sentinel changed.

Local regression using the auditor's v1.2.1 geometry harness, updated only for schema 4/version 1.2.2:

`PASS RESTORE_geometry_sentinel_gate_expected ... res={'CANCELLED'} clear=False`

## R-02 HIGH — external reuse of imported Objects/Collections

Declared correction:

- destructive cleanup now preflights every tagged Object/Collection/Scene before deleting any priority ID;
- Object links to Collections outside the same import are blockers;
- external children are blockers;
- Collection parent/root/instance links outside the same import are blockers;
- when available, `bpy.data.user_map()` is consulted for direct external ID users;
- if any blocker exists, no priority Object/Collection/Scene is deleted, residual markers and `reference_import_id` are preserved.

Auditor harness replay now reports the externally linked Object as retained, with cleanup failure/residual and state preserved. Additional local harness does the same for an imported Collection linked under an external parent.

## R-03 MEDIUM — retry losing old import identity

Declared correction:

- ImportReference now calls `reference_import_state_blockers()` before allocating a new import ID;
- any existing `reference_collection`, non-empty `reference_import_id`, tagged residual ID, or master collection blocks a new import;
- a single orphan tagged import can be adopted by RemoveReference even if settings lost its ID;
- cleanup never overwrites an old pending import ID just to start a retry.

Auditor harness replay now keeps `oldimp` unchanged and refuses the retry before append.

## R-04 MEDIUM — metadata when original parent is None

Declared correction:

- Restore writes `parent_type`, `parent_bone`, `parent_vertices` unconditionally after setting the saved parent (including None);
- readback verifies those three fields unconditionally for every managed target.

Auditor harness replay now detects deliberate divergence on an originally-unparented target.

## Previous v1.2.0 findings

The v1.2.2 changes retain the v1.2.1 corrections for:

- F-01 external snapshot identity;
- F-02 frozen modifier scope + readback gate;
- F-03 per-Scene backup paths;
- F-04 field-level Restore verification;
- F-05 tagged/observable reference cleanup (further hardened above).

## Schema

Snapshot schema: **4** (`_t7sm_snapshot_v4`). v1.2.1 schema-3 active snapshots are intentionally incompatible.

## Remaining mandatory validation

No real Blender runtime is available in the developer environment. Independent testing in **Blender 5.0.0 exactly** remains mandatory, especially:

- install/enable/disable/re-enable;
- P1/P2/P3 save-load persistence;
- parent/bone/armature/matrix_parent_inverse;
- Set Origin behavior;
- reference import/remove using real `bpy.data.user_map()` and real ID user counts;
- normal cleanup happy path with nested Collections;
- external Object reuse and external Collection reuse;
- short stress test.
