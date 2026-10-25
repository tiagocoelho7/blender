# AUDIT DELTA — T7 Statue Mover v1.2.15-candidate

Target runtime: **Blender 5.0.0 exactly**.

This candidate is a narrow correction over the frozen v1.2.14 candidate. It does **not** change snapshot schema 6, persistence layout, G/R/S math, N-35 Armature policy, geometry fingerprints, modifier handling, reference cleanup, crash recovery, or temp/symlink safety.

## Why v1.2.14 was HOLD — N-42 HIGH

The v1.2.14 runtime audit showed that the strict Apply gate was validating reconstructed **world-matrix components** against ideal `D @ original_world` with per-component float32 budgets.

That model is incorrect for large transforms through a parent rotated in 3D. Blender stores float32 transform channels. When a large translated child is reconstructed through a rotated parent, normal quantization from one large axis can appear as residual in another small world axis. Examples from the immutable v1.2.14 runtime evidence:

- G=100: Head Z diff about `2.38e-6` vs world-axis tol `2e-6`;
- G=150: Head Y diff about `6.70e-6` vs world-axis tol `2e-6`;
- G=1000: Head Y diff about `2.21e-5` vs world-axis tol `2e-6`;
- all mandatory G=150/300/1000/10000/100000 cases failed Apply/Finalize in rotated-parent scenes;
- historical `G_large` and the 601-target stress test regressed for the same reason.

Restore remained fail-closed and exact, but the primary workflow could not keep correct large translations.

## v1.2.15 architecture

### 1. Apply no longer uses reconstructed world components as its strict precision gate

The world target is still computed exactly as before:

`desired_world = D @ original_world`

and the existing setter still computes:

`expected_basis = inverse(channel_parent_prefix(obj)) @ desired_world`

The setter now returns that requested `expected_basis` after assigning it to `obj.matrix_basis`.

### 2. New primary Apply gate: requested matrix_basis vs stored matrix_basis

For each successfully written target, Apply transiently retains `(object, expected_basis)` and, after the writes/update, compares:

`obj.matrix_basis readback` vs `expected_basis requested`

This comparison is intentionally in the storage/channel space Blender directly quantizes. Parent-chain world multiplication is outside the strict gate, so a large world X translated through a 3D-rotated parent cannot create a false failure in a small world Y/Z component.

### 3. Expected-only component budgets

The channel-space comparator uses only the expected component to derive its allowance:

- linear 3x3: `max(2e-6, 8 * ulp(expected_component))`;
- matrix_basis translation X/Y/Z: `max(2e-6, 4 * ulp(expected_axis))`;
- affine bottom row: `2e-6`.

A sibling component, another axis, a parent world coordinate, and the divergent actual readback cannot widen the allowance.

### 4. World readback is still preserved for Finalize

After the channel-space Apply gate succeeds, v1.2.15 keeps the existing applied-world-readback architecture:

- capture the actual channel-derived world matrix Blender represented;
- persist it in the existing schema-6 `applied_matrix_world` fields;
- Finalize compares current world readback against that frozen applied readback before restoring modifiers or deleting the checkpoint.

Thus N-42 is addressed without weakening the later drift/checkpoint gate.

### 5. Historical world verifier retained as diagnostic only

`verify_applied_world_matrices()` remains available for audit/history probes, including N-38/N-39/N-40 pure vectors, but **is no longer the blocking Apply precision gate**. Its v1.2.14 world-component assumptions are known to reject correct rotated-parent large-translation cases.

## Must not regress

A future runtime audit must still prove:

- `(12,12,1) x2 -> (24,24,2)` + Finalize;
- G 100/150/300/1000/10000/100000 with 3D-rotated parents;
- large G+R+S;
- S4/S8 and pieces at scale 100;
- historical `G_large` and stress ~601 targets/~1200 modifiers;
- N-38/N-39/N-40 wrong-pose injection rejected before valid readback capture;
- post-Apply drift >=1e-5 at ordinary scale blocked by Finalize;
- N-35, N-24..N-32, hidden/excluded, modifiers, persistence/save-reopen remain clean.

## Intentionally unchanged LOW/INFO items

- N-43 LOW diagnostic from v1.2.14 world verifier is not the release blocker and the historical world helper remains diagnostic-only.
- N-37 LOW, N-33 LOW and N-34 LOW/UX remain unchanged.

No production GO is claimed without an independent Blender/bpy 5.0.0 runtime audit of the exact frozen ZIP.
