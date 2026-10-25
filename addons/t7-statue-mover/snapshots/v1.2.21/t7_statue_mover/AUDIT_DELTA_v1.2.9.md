# T7 Statue Mover v1.2.9-candidate — Audit Delta

Target: **Blender 5.0.0 exactly**.

This is a narrow corrective delta over the frozen v1.2.8 candidate. Do not treat this document as proof; reproduce every claim against the ZIP.

## N-26 CRITICAL — normal enable under `_RestrictData`

### v1.2.8 failure

Normal `bpy.ops.preferences.addon_enable()` / `addon_utils.enable()` executes add-on `register()` while `bpy.data` is `_RestrictData`. v1.2.8 performed `list(bpy.data.scenes)` inside `register()` and raised `AttributeError`, so the ZIP could not enable normally.

### v1.2.9 correction

Registration no longer accesses scene data. After classes, Scene property and handlers are registered, `_schedule_initial_recovery()` schedules `_initial_recovery_timer()` with `bpy.app.timers`. The callback accesses `bpy.data.scenes` only after restriction is released; if it is still unavailable it returns a short retry interval. Pending timer cleanup is attempted on unregister/rollback.

Mandatory runtime regression: Install ZIP -> standard enable -> disable -> re-enable -> reload/F8 in Blender 5.0.0, without direct `module.register()` bypass.

## N-27 HIGH — constraint added after Prepare

### v1.2.8 failure

Prepare refused constraints, Apply also refused them, but Restore/Finalize did not. A constraint added after Prepare could leave evaluated world placement divergent while Restore returned `FINISHED` and deleted the snapshot.

### v1.2.9 correction

`verify_target_constraints()` is called before both Restore and Finalize. Any target constraint blocks before mutation and preserves the snapshot/external checkpoint. Restore also checks constraints again before final checkpoint deletion.

Mandatory regression: Prepare -> add `COPY_LOCATION` -> Apply/Restore/Finalize all fail closed where applicable, with checkpoint intact and no false exact-restoration message.

## N-28 HIGH — incomplete Mesh geometry sentinel

### v1.2.8 failure

Mesh fingerprint sampled only four vertices. Editing another vertex or topology could leave the digest unchanged, allowing false `Estado inicial restaurado e verificado` followed by checkpoint deletion.

### v1.2.9 correction

Mesh fingerprint is complete over the raw Mesh datablock and uses RNA `foreach_get` buffers. It hashes counts plus all vertex coordinates, edge vertex pairs, loop vertex indices, polygon loop spans, and shape-key coordinates. Modifiers are still excluded.

Mandatory regression: edit a formerly unsampled vertex; edit edges/faces/loops; Set Origin; shape-key coordinate edit if present. Restore and Finalize must cancel before checkpoint deletion. Happy path must remain stable across save/reopen.

## N-29 SECURITY — deterministic temporary symlink

### v1.2.8 failure

`atomic_write_text()` used `<path>.tmp` and ordinary `open(..., 'w')`, so a pre-created symlink could redirect the write to an external file.

### v1.2.9 correction

Temporary files are now created exclusively with `tempfile.mkstemp()` inside the destination directory and atomically promoted with `os.replace()`. The predictable legacy `<path>.tmp` name is not opened.

Mandatory regression: pre-create `<canonical>.tmp` as symlink to an external sentinel; trigger Prepare/save promotion; external sentinel must remain byte-identical. Inject mid-write failure and confirm no add-on-created temporary residue.

## Version / schema

- Add-on version: 1.2.9
- Snapshot schema remains 6 (`_t7sm_snapshot_v6`)
- No persisted payload format change is intended.

## Required non-regression

Re-run the prior Blender 5.0.0 evidence suite and preserve at minimum:

- N-01 P2/load_post including non-active Scenes;
- N-02 Save Copy/autosave/re-enable/Save As baseline immutability;
- N-03 hidden/excluded channel-derived transforms;
- N-04 safe snapshot deletion boundary;
- N-05 import;
- N-06/N-07/N-25 cleanup safety;
- N-08 lifecycle plus the new N-26 standard-enable gate;
- N-09 multi-Scene isolation;
- N-10 shear/nonuniform/negative/zero gates;
- N-11/N-21 honest external persistence state;
- N-12/N-23 geometry policy;
- N-24 crash-window recovery;
- H-01/R-01..R-04, F-01..F-05;
- modifiers;
- G/R/S and `(12,12,1) x 2 -> (24,24,2)`;
- hierarchy/armature/bone/deltas/mpi;
- P1/P2/P3;
- stress with hidden/excluded targets.
