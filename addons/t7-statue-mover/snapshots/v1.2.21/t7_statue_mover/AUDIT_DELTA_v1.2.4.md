# AUDIT DELTA — T7 Statue Mover v1.2.4-candidate

## Origin of this candidate

v1.2.3 received **HOLD** for H-02 HIGH: an unsaved rename could make a later operator-side `persist_snapshot()` overwrite/move the external checkpoint using live in-memory names even though the .blend on disk still contained the old names. The last recoverable external baseline could therefore disappear or become invalid before any real save.

The v1.2.3 audit also confirmed at logical/harness level that H-01 from v1.2.2 was fixed and that prior R-02/R-03/R-04 and F-01..F-05 regressions remained passing in the covered scenarios.

## v1.2.4 changes

### H-02 HIGH — persistence baseline redesigned

The external JSON is now treated as an immutable baseline for the **last file actually saved on disk**.

1. Prepare requires a saved, clean .blend.
2. Prepare freezes explicit identity strings:
   - Scene;
   - guide;
   - base;
   - target collection;
   - reference collection;
   - object names/data names;
   - original parent names.
3. Normal `persist_snapshot()` refreshes the in-session embedded checkpoint but does not replace/delete an already existing external baseline.
4. Unsaved renames therefore cannot move or overwrite the recovery JSON for the saved file.
5. `save_pre` refreshes frozen identity strings to the live names that are about to be serialized.
6. `save_post` recomputes the SHA-256 of the newly written .blend and builds the new external identity.
7. The replacement JSON is atomically written and read back.
8. Checksum, schema, snapshot ID, blend path, file SHA-256 and Scene identity are verified.
9. Only after this verification may the previous baseline be removed.

### Saved rename support

Before a real save, object/modifier identity strings are refreshed from stable Blender pointers/indexes so legitimate saved renames remain recoverable under the new on-disk identity without changing original transform/modifier state values.

### Schema

Snapshot schema is bumped from 4 to **5**. Schema-4 snapshots are deliberately not auto-migrated.

## Developer-side non-Blender regression evidence

These are not substitutes for Blender 5.0.0 runtime testing.

### Unsaved Scene/guide rename

`harness_unsaved_rename_v124.py`:

- Scene rename -> RestoreModifiers -> old external baseline remains;
- simulated reopen of unchanged disk file finds the old checkpoint;
- guide rename -> external payload remains bound to original `Guide`;
- simulated reopen validates successfully.

Result: `HARNESS_RESULT=UNSAVED_RENAME_BASELINE_PRESERVED`.

### Save promotion

`harness_save_promotion_v124.py`:

- old baseline exists;
- Scene/guide renamed in memory;
- pre-save identity refresh does not delete old baseline;
- simulated successful save changes file bytes/SHA;
- save-post writes/verifies new JSON;
- only then is old JSON removed;
- promoted payload contains renamed Scene/guide and validates against the new disk identity.

Result: `HARNESS_RESULT=SAVE_POST_TWO_PHASE_PROMOTION_PASS`.

### Failed promotion preserves old baseline

`harness_save_promotion_failure_v124.py` injects a readback/checksum verification failure after the new JSON write attempt. The function raises, the old external file remains present, and `snapshot_backup_path` still points to the old baseline.

Result: `HARNESS_RESULT=FAILED_PROMOTION_PRESERVES_OLD_BASELINE_PASS`.

### Target collection + original parent rename

`harness_collection_parent_rename_v124.py`:

- unsaved target collection/original parent rename does not alter old external baseline;
- reopen of unchanged disk identity validates old names;
- after simulated real save, promoted payload uses the saved renamed collection/parent and validates.

Result: `HARNESS_RESULT=COLLECTION_PARENT_RENAME_PASS`.

### Previous regressions

With schema adjusted to 5 where the previous auditor harness hardcoded schema 4:

- H-01 Finalize geometry gate: PASS;
- R-01 Restore geometry gate: PASS;
- F-01/F-02/F-03/F-04/P2/P3 harness: 8 PASS / 0 FAIL;
- R-02/R-03/R-04 reference/parent harness: PASS;
- import retry blocker: PASS;
- registration/re-enable/rollback/version gate: PASS;
- numeric G/R/S matrix harness: PASS;
- invalid nonuniform/negative/zero scale pre-mutation gate: PASS.

## Required independent audit focus

Do not accept this document as proof. Reproduce H-02 first, especially:

- Scene rename -> Restore Modifiers -> close without save -> reopen;
- guide rename -> same;
- target collection rename -> same;
- original parent rename -> same;
- confirm old baseline remains until a real save completes;
- after real save with rename, confirm new identity is recoverable;
- inject write/readback/checksum failure during save-post and confirm old baseline remains available;
- ensure previous H-01, R-01..R-04 and F-01..F-05 do not regress.

Final GO still requires Blender **5.0.0 exactly** for process-level persistence, parent/bone/armature, Set Origin, append/cleanup and stress gates.
