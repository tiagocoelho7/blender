# AUDIT DELTA — T7 Statue Mover v1.2.21

## Status

Candidate only. **Not production GO.** Runtime target remains **Blender 5.0.0 exactly**.
Snapshot schema remains **6**.

## Frozen predecessor

v1.2.20 candidate:

`79692b6a128e19707b949ff14d0d4ffc3fe99d554ccaee5d4b647e6060ec3161`

The exact Blender 5.0.0 runtime audit of v1.2.20 returned **HOLD** for one HIGH finding, N-56. It also left N-52 as MEDIUM from the user's channel-continuity perspective.

## Scope of v1.2.21

v1.2.21 intentionally changes only two functional areas:

1. **N-56 HIGH:** reduce the Euler singular threshold after polar projection from `1e-6` to `1e-12`.
2. **N-52 MEDIUM:** measure equivalent-Euler branch continuity against the **pre-write** `rotation_euler` channels instead of the channels produced by Blender's `matrix_basis` setter.

No DIM-300 warning is included in this candidate. That feature is intentionally deferred so this numerical fix stays narrow.

---

## N-56 — runtime finding from v1.2.20

v1.2.20 successfully closed N-54: the polar projection removed the catastrophic amplification of ~float32 non-orthogonality in child/local matrices near gimbal.

However, after polar projection the requested rotation is already orthonormal in Python double precision. The v1.2.20 constant:

```python
EULER_SINGULAR_THRESHOLD = 1.0e-6
```

was too coarse for that post-polar input.

The Blender 5.0.0 runtime audit found a narrow legitimate window roughly a few `1e-5` degrees from +/-90 degrees where `cy <= 1e-6` caused the singular Euler branch to discard O(cy) information. At large world-column magnitudes that otherwise tiny reconstruction difference exceeded the unchanged N-48 absolute per-component cap and caused **false reject of a correct pose**.

The runtime report measured, among other cases:

- p59: v1.2.20 accepted 54/96 and falsely rejected 42/96;
- the same inputs on v1.2.19: 96/96 accepted;
- probe-only v1.2.20 with threshold `1e-12`: 96/96 accepted;
- the `1e-12` counterfactual also kept p50 full 7560/7560, singular 1440/1440, childcmp 360/360 and singbig 240/240.

### v1.2.21 change

```python
EULER_SINGULAR_THRESHOLD = 1.0e-12
```

Nothing else in the polar projection, shear guard, signed-scale recovery or world sanity is loosened.

### Required adversarial checks

Try to disprove the new threshold with:

- all six Euler orders;
- exact +/-90 degrees;
- genuine near-gimbal values whose `cy` spans `1e-14 .. 1e-5`;
- the prior N-56 window around ~89.99994..89.99997 degrees and negatives;
- roots and children;
- signed scale / mirror;
- parent chains, matrix_parent_inverse and deltas in runtime;
- large world-column magnitudes: ~2k, 10k, 16k, 100k and beyond;
- shear and nearly singular matrices;
- attempts to make the general branch numerically unstable below the old threshold.

Do **not** accept a fix merely because Apply returns FINISHED. Runtime must compare independent world truth and downstream Finalize/Restore.

---

## N-52 — pre-write continuity reference

v1.2.20 fixed the branch ranking rule: when two equivalent Tait-Bryan branches reconstruct within `min_error + 1e-12`, the closer branch wins.

But it used this as the reference:

```python
current = tuple(obj.rotation_euler)
```

after:

```python
obj.matrix_basis = local
```

The exact Blender 5.0.0 runtime audit showed that the setter itself can jump to an equivalent distant Euler representation. As a result, v1.2.20 still produced a user-visible branch change in 73/300 generic translation-only cases, even though world remained correct.

A probe-only counterfactual using the **pre-write channels** produced 0/300 such swaps.

### v1.2.21 change

For Euler modes only, `set_channel_world_matrix()` now captures:

```python
continuity_reference = tuple(float(v) for v in obj.rotation_euler)
```

**before** assigning `obj.matrix_basis = local`.

That tuple is passed to `_refine_euler_after_matrix_basis_write()` and used only for compatible-branch selection.

If no explicit reference is supplied, the helper retains its historical fallback to the current object channels. This keeps the helper independently callable.

Quaternion and Axis-Angle do not enter Euler refinement.

### Required checks

- confirm the capture happens before the matrix_basis assignment;
- confirm the pre-write tuple is passed into the refinement call;
- six Euler orders;
- +/-2pi wraps;
- channels already outside [-pi, pi];
- ordinary non-gimbal transforms;
- near/exact gimbal;
- repeated Apply;
- nonzero `delta_rotation_euler`;
- save/reopen/Finalize/Restore in exact Blender runtime;
- verify branch continuity does not override a materially more accurate branch: a branch > `1e-12` worse must still lose even if closer.

---

## Explicitly unchanged

The intended functional delta does **not** redesign:

- `D = current_guide_world @ inverse(saved_guide_world)`;
- `new_world = D @ original_world`;
- snapshot schema/persistence;
- Prepare/Finalize/Restore architecture;
- raw-channel gate;
- v1.2.20 polar projection;
- shear guard;
- N-53 vector budget `2.5e-5`;
- N-51 column-length budget `1e-5`;
- N-48 per-component cap;
- N-42 translation sanity;
- parent-prefix/world helpers;
- geometry fingerprinting;
- modifier safety;
- reference import/cleanup;
- N-24..N-35 behavior.

The UI version label is updated to v1.2.21. Documentation/version strings are expected to differ.

## Known non-blocking history still to watch

- N-46 LOW: extreme anisotropic case, fail-closed.
- N-49 INFO: tiny directional window from the 2.5e-5 vector envelope.
- N-55x LOW: very large (~4e5 world-column) pre-existing float32/component-cap false reject observed at k=100000.
- GUI/event loop/undo/driver auto-exec remain outside headless proof unless explicitly run in GUI Blender.

## Mandatory runtime exit criteria before production GO

On the original frozen v1.2.21 ZIP in **Blender/bpy 5.0.0 exactly**, without patch:

1. N-56: p59 96/96 accepted with correct world; p50 window 0 false rejects; singular 1440/1440; full 7560/7560; singbig no root regression.
2. N-52: p58-like ordinary non-gimbal translation test should show 0/300 branch swaps relative to **pre-write** user channels; p51 persistence/Restore behavior remains correct.
3. N-54 remains closed for root/child/mpi+deltas/exact gimbal.
4. N-53 remains p52 59/59.
5. N-51 +1.1e-5 and +2e-5 remain REJECT across t62/t63 controls.
6. N-48/N-47/N-38/N-39/N-40 and NaN/Inf remain fail-closed.
7. N-42/N-44/N-46 and the N-24..N-35 battery remain unchanged.
8. Persistence/save-reopen, BONE, hidden/excluded, modifiers and stress remain clean.

Any new HIGH/CRITICAL => HOLD.
