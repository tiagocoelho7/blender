# AUDIT DELTA — T7 Statue Mover v1.2.16-candidate

Target runtime: **Blender 5.0.0 exactly**.

This candidate is a narrow correction over the frozen v1.2.15 candidate. Snapshot schema remains **6**. It does not redesign persistence, G/R/S math (`D @ M0`), N-35 Armature policy, modifiers, geometry fingerprints, N-24..N-32, N-29 temp/symlink safety, or reference cleanup.

## Why v1.2.15 was HOLD — N-45 HIGH

The Blender 5.0.0 runtime audit proved that `matrix_basis` is not stored as 16 independent floats. Blender stores transform channels (location, rotation and scale, plus deltas) in float32 and reconstructs `matrix_basis` from them. The v1.2.15 gate compared the requested double-precision basis matrix against that reconstructed matrix component-by-component.

That correctly solved N-42, but it falsely rejected correct poses when the object's own scale was around 50–1000 or the Euler rotation was near gimbal lock. Representative failures included a root object at scale 100 with ordinary rotation and only G10, and scale-1 objects around Y=89.9 degrees. Restore/checkpoint remained safe, but Apply could not certify a correct pose.

## v1.2.16 architecture

### 1. Strict gate moves from recomposed matrix_basis to Blender's raw transform channels

`set_channel_world_matrix()` still computes and writes the same requested local basis. Immediately after that synchronous write, Apply captures the **canonical representable RNA transform channels** Blender actually stored:

- `location`;
- active rotation representation (`rotation_euler`, `rotation_quaternion` or `rotation_axis_angle`);
- `scale`;
- `delta_location`;
- active delta rotation representation;
- `delta_scale`;
- `rotation_mode`.

After all targets are written and the ViewLayer update runs, `verify_applied_transform_channels()` rereads those exact channels and verifies that they did not change. The tolerance is expected-only and local to the same scalar channel. A later mutation cannot widen or redefine its own expected value.

This avoids N-45 because no matrix decomposition/recomposition is compared as the strict gate.

### 2. N-38/N-39/N-40 fault detection is preserved

Wrong-pose injections after the setter necessarily mutate one or more real transform channels. The frozen post-write channel state therefore remains the strict reference. If any raw channel changes before certification:

- Apply reports an error;
- valid applied-world readback is not captured;
- `applied_world_valid` remains false/cleared;
- Finalize remains blocked;
- Restore remains available.

### 3. Secondary coarse world-material sanity gate

A raw-channel gate alone proves stability of what Blender stored, but not the mathematical correctness of a hypothetical broken setter/prefix. v1.2.16 therefore adds a second, deliberately coarse world-space sanity gate after the strict channel check.

It is **not** a precision gate. Its purpose is only to catch materially wrong worlds while allowing the legitimate float32 propagation that caused N-42/N-45:

- linear components use a budget derived from the norm of their own expected column plus an absolute floor;
- world translation uses the magnitude of the full expected translation vector because rotated parents legitimately couple world axes;
- the affine bottom row stays tight.

This should reject gross ill-conditioned/wrong-prefix results such as the N-46-style ~17-unit displacement while not reintroducing N-42/N-45 false rejects.

### 4. Finalize architecture is unchanged

Only after the strict raw-channel gate and coarse world sanity gate succeed does the existing `capture_applied_pose_readbacks()` run. Finalize still compares the current world pose against that frozen applied readback before modifier restoration or checkpoint deletion.

## Mandatory next audit targets

A cheap audit must first verify the code structure and fault paths independently. The exact Blender 5.0.0 runtime audit must then repeat:

- p30/p31/p32/p33 or equivalent N-45 cases;
- root and child pieces at scale 1/10/50/100/1000 with ordinary rotations;
- Y=89.9 and 90.1 degree gimbal-near rotations;
- N-42 G 100/150/300/1000/10000/100000 with rotated parents;
- large G+R+S, S4/S8, scale-100 guide/pieces, `G_large`, stress;
- N-38/N-39/N-40 and 2e-5 fault injection after setter;
- N-44 parent/BONE/hidden/excluded/MPI/delta cases;
- N-35 and N-24..N-32 regression battery;
- save/reopen, modifiers, Restore/Finalize.

No production GO is claimed without an independent exact Blender/bpy 5.0.0 runtime audit of the frozen ZIP.
