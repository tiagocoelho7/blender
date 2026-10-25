# T7 Statue Mover v1.2.10-candidate — Audit Delta

Target runtime: **Blender 5.0.0 exactly**.

This is a narrow corrective delta over the frozen v1.2.9 candidate after the Claude runtime audit. Treat this document as context only; every claim must be reproduced against the ZIP.

## N-30 CRITICAL — Prepare unpacked the Mesh sentinel with the obsolete arity

### v1.2.9 failure

`mesh_geometry_sentinel()` returned `(valid, digest)`, but `T7SM_OT_Prepare.execute()` still unpacked four legacy values. Any scene with at least one object raised `ValueError: not enough values to unpack (expected 4, got 2)` before Prepare could complete, leaving partial in-memory snapshot fields.

### v1.2.10 correction

Prepare no longer calls the obsolete four-value interface. It computes `geometry_sentinel()` once, stores the full geometry hash, and keeps the old schema-v6 `mesh_*` fields only as neutral compatibility metadata. The entire object-state capture phase is wrapped in a fail-closed transaction: any unexpected capture exception clears the partial in-memory snapshot and returns `CANCELLED` before modifiers or external baselines are touched.

Mandatory regression:

- install the original ZIP and run `bpy.ops.t7sm.prepare()` in a scene containing Mesh and non-Mesh objects;
- expect `FINISHED` on the valid happy path;
- inject an exception during capture and confirm `snapshot_active=False`, empty object/modifier state, empty `snapshot_id`, modifiers unchanged and no external candidate/baseline mutation;
- run the tuple-unpack arity probe and require zero mismatches.

## N-31 HIGH — constraint on an external ancestor

### v1.2.9 failure

The add-on checked constraints only on target objects. `channel_world_matrix()` intentionally ignores depsgraph constraints, so a constrained external parent could make the real evaluated world matrix differ from the channel-derived matrix. Apply could return success with a target in the wrong place, and Finalize could then delete the snapshot.

### v1.2.10 correction

Dynamic transform influence validation now scans **every target and its complete Object parent chain**. It rejects:

- Object constraints on the target or any ancestor;
- constraints on the specific pose bone used by BONE parenting;
- Object animation data described below for N-32.

The same check runs:

- before Prepare creates snapshot state;
- before Apply mutates targets;
- before Restore mutates targets and again before checkpoint deletion;
- before Finalize mutates modifiers or deletes the checkpoint.

Mandatory regression:

- external parent + `COPY_LOCATION` before Prepare -> Prepare `CANCELLED`;
- add the parent constraint after Prepare -> Apply/Restore/Finalize fail closed with snapshot/baseline preserved;
- remove the constraint -> normal flow resumes;
- include guide rotation/scale, not translation only;
- keep the existing clean external-parent hierarchy case passing.

## N-32 HIGH — object animation can silently overwrite applied transforms

### v1.2.9 failure

A keyframed root target could be transformed successfully, then a frame change could re-evaluate the F-curve and revert only part of the statue. Finalize did not verify the current target pose before deleting the snapshot and could report success with the statue split.

### v1.2.10 correction

The same target/ancestor influence scan now conservatively rejects Object-level animation data on managed target chains when it contains:

- an Action;
- one or more NLA tracks;
- one or more drivers.

This is intentionally fail-closed even if the animated Object property is not a transform channel. Exact checkpoint deletion is more important than supporting ambiguous animated Object state in this workflow.

Finalize also has a second independent safety gate: when an Apply has occurred, it reconstructs the delta from the saved/current guide and verifies every target is still at `D @ original_world` **before** modifiers are restored or the snapshot is deleted. Therefore a dynamic influence that was added, evaluated, then removed cannot leave a reverted pose that Finalize silently accepts.

Mandatory regression:

- target with location keyframe before Prepare -> Prepare `CANCELLED`;
- target ancestor with Action/NLA/driver -> Prepare `CANCELLED`;
- add animation after Prepare -> Apply/Restore/Finalize fail closed;
- Apply normally, then perturb a target back to a wrong pose without leaving animation data -> Finalize `CANCELLED`, snapshot preserved;
- remove the offending animation and restore the expected pose -> normal flow resumes.

## Known LOW items intentionally not redesigned in this delta

- **N-33:** `atomic_write_text()` currently tolerates an `fsync` failure. Atomic replacement still works, but power-loss durability signaling can be improved later.
- **N-34:** Library cleanup fail-closed messaging is safe but not very explanatory to the user.

These are not release blockers unless a new audit demonstrates higher impact.

## Version / schema

- Add-on version: **1.2.10**
- Snapshot schema remains **6** (`_t7sm_snapshot_v6`)
- No persisted payload format change is intended.

## Required non-regression

Preserve the v1.2.9/v1.2.8 evidence for:

- N-26 normal enable under faithful `_RestrictData`;
- N-27 post-Prepare target constraints;
- N-28 complete Mesh fingerprint;
- N-29 temporary-file symlink safety;
- N-24 crash recovery;
- N-25 real linked-ID/Library Override cleanup safety;
- G/R/S, including `(12,12,1) x 2 -> (24,24,2)`;
- external parent without dynamic influences;
- BONE parent, Armature modifier, deltas, matrix_parent_inverse;
- hidden/excluded targets;
- modifiers;
- P1/P2/P3, Save As, Save Copy, autosave and multi-Scene;
- stress around 651 objects / 1200 modifiers.
