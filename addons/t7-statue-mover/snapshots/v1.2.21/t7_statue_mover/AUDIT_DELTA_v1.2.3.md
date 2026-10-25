# Audit delta — v1.2.3-candidate

The v1.2.2 independent audit returned **HOLD** for one localized HIGH finding. This file is developer-declared evidence only; auditors must reproduce independently.

## H-01 HIGH — Finalize geometry/origin sentinel bypass

Declared correction:

- `T7SM_OT_Finalize.execute()` now calls `verify_geometry_sentinels(settings)` immediately after snapshot/schema checks and **before** `restore_modifier_states()`;
- on mismatch it attempts `persist_snapshot()` best-effort, reports ERROR and returns `CANCELLED`;
- the mismatch path does not restore modifiers and does not call `clear_snapshot_data()`;
- the intact-geometry path is unchanged: restore managed modifiers, verify readback, then clear the snapshot.

Local direct-operator harness result:

```text
MISMATCH_RESULT {'CANCELLED'} ['geometry', 'persist'] ... snapshot_active=True
HAPPY_RESULT {'FINISHED'} ['geometry', 'restore_mods', 'verify_mods', 'CLEAR_SNAPSHOT'] ... snapshot_active=False
HARNESS_RESULT=FINALIZE_GEOMETRY_GATE_PASS
```

## Regression status in the developer environment

Replayed harnesses from the v1.2.2 audit against the v1.2.3 source:

- v1.2.0 logical regressions / persistence corruption checks: **8 PASS / 0 FAIL**;
- R-02/R-03/R-04 reference cleanup + parent metadata harness: **PASS**;
- registration/unregistration/re-enable/rollback/version gate harness: **PASS**.

These are not substitutes for Blender runtime.

## Schema

Snapshot schema remains **4** (`_t7sm_snapshot_v4`). No persisted field format changed in v1.2.3.

## Mandatory remaining validation

Independent testing in **Blender 5.0.0 exactly** remains required, especially:

- install/enable/disable/re-enable;
- P1/P2/P3 process-level persistence;
- H-01 with real Set Origin / vertex count / sampled vertex edits;
- parent/bone/armature/matrix_parent_inverse;
- reference import/remove with real `bpy.data.user_map()` and unlink semantics;
- G/R/S numerical behavior;
- short stress test.
