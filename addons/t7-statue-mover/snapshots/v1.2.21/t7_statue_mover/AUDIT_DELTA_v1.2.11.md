# T7 Statue Mover v1.2.11-candidate — Audit Delta

Target runtime: **Blender 5.0.0 exactly**.

This is a narrow corrective delta over the frozen v1.2.10 candidate after the Claude runtime HOLD. Treat this document as context only; auditors must reproduce every claim against the ZIP.

## N-36 HIGH — Finalize rejected correct poses because ideal math was compared to float32 channel readback

### v1.2.10 failure

`Finalize` rebuilt the ideal `D @ original_world` matrix and compared that ideal matrix directly with `channel_world_matrix()` using per-component tolerances. Blender stores transform channels as float32, and hierarchy multiplication can move a few float32 ulps of rounding into otherwise small world-matrix components.

The runtime audit reproduced false rejection for:

- the mandatory `(12,12,1) x 2 = (24,24,2)` case in the standard hierarchy;
- translations starting around 150 units in some hierarchies;
- 1,000 / 10,000 / 100,000-unit translations;
- large G+R+S cases.

Restore remained safe, but the user could not complete “keep new position”.

### v1.2.11 correction

Two separate verification stages now have different purposes:

1. **Apply intended-pose verification** still compares the result against ideal `D @ M0`, but uses a matrix-wide tolerance derived from the float32 ulp of the largest matrix magnitude. This accounts for representational roundoff propagated through supported clean parent chains without accepting macroscopic placement errors.
2. **Finalize current-pose verification** no longer recomputes ideal `D @ M0`. After a fully verified Apply, the add-on captures the **actual channel-derived world matrix Blender stored** for every target. Finalize compares the current pose against that captured representable readback before checkpoint deletion.

The applied readback is stored per target in two additive schema-v6 fields:

- `applied_world_valid`;
- `applied_matrix_world`.

They are serialized into the embedded/external snapshot and hydrated after save/reopen. An older schema-v6 snapshot that does not contain these optional fields fails closed at Finalize after an Apply: the snapshot is preserved and Restore remains available.

Mandatory regression in Blender/bpy 5.0.0:

- standard hierarchy, guide `(12,12,1)`, scale x2 -> Apply and Finalize both succeed;
- G = 150, 300, 1,000 and 10,000 units -> Apply and Finalize succeed when the pose is correct;
- large G+R+S -> succeeds;
- save after Apply -> new process -> Finalize succeeds with unchanged pose;
- manual target drift after Apply (including ~1e-3 at ordinary production magnitudes) -> Finalize `CANCELLED`, snapshot/baseline/modifiers preserved;
- dynamic influence added, evaluated and removed after Apply -> wrong pose still blocked by the captured-readback gate;
- gross misplacement such as the historical ~0.78-unit bone/constraint case must never be accepted by Apply verification.

The auditor should explicitly measure the accepted float32 tolerance and challenge it at large translations. Do not infer PASS from synthetic matrices alone.

## N-35 MEDIUM — pose-bone constraint scan covered only the direct parent bone

### v1.2.10 gap

The ancestry scanner checked Object constraints/animation across the full Object parent chain, but for BONE parenting it inspected only the specific direct parent pose bone. The runtime audit found unscanned cases involving:

- a constraint on a bone above the direct parent bone;
- IK/constraints on another bone affecting the chain;
- an Armature that is itself a target and has a constrained pose bone.

One target-Armature case mutated a piece by ~0.78 units before the later verification stopped Finalize.

### v1.2.11 correction

For a **relevant Armature** — either:

- the Armature is itself a managed target; or
- it provides BONE parenting to a managed target —

v1.2.11 conservatively refuses **any pose-bone constraint anywhere in that Armature**.

This intentionally does not attempt to solve Blender’s complete IK/constraint dependency graph. The workflow fails closed instead.

Mandatory regression:

- clean BONE-parent Armature remains allowed;
- constraint on the direct parent bone -> blocked;
- constraint on a parent/root bone -> blocked;
- IK or other constraint on a different pose bone -> blocked;
- Armature target with any constrained pose bone -> blocked;
- influence added after Prepare/Apply -> Apply/Restore/Finalize block before destructive completion;
- removing the pose constraint permits a clean retry.

## Historical fixes that must not regress

Preserve runtime evidence for:

- N-30 Prepare real smoke test and capture rollback;
- N-31 Object ancestor constraints;
- N-32 Action/NLA/driver protection;
- N-26 normal enable under faithful `_RestrictData`;
- N-27 direct target constraint after Prepare;
- N-28 complete Mesh fingerprint;
- N-29 secure temporary writes;
- N-24 crash recovery;
- N-25 linked-ID/Library Override cleanup safety;
- G/R/S, hierarchy, external parent, BONE parent, Armature modifier, deltas and `matrix_parent_inverse`;
- hidden/excluded collections;
- modifiers;
- P1/P2/P3, Save As, Save Copy, autosave and two Scenes;
- stress around 651 objects / 1200 modifiers.

## Known LOW items intentionally not redesigned

- **N-37:** unexpected exception in the Prepare preflight may still surface a traceback, but no mutation occurs and retry is safe.
- **N-33:** `fsync` failure is still tolerated; power-loss durability signaling can be improved in a later narrow delta.
- **N-34:** Library-cleanup fail-closed messaging remains generic.

These remain non-blocking unless a new audit demonstrates higher impact.

## Version / persistence

- Add-on version: **1.2.11**
- Snapshot schema remains **6** (`_t7sm_snapshot_v6`).
- The schema-v6 payload gains only the optional additive applied-readback fields listed above.
- Missing applied-readback fields never cause checkpoint deletion; Finalize fails closed and Restore remains available.
