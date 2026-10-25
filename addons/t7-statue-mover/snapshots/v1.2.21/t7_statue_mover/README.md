# T7 Statue Mover v1.2.21-candidate

Target runtime: **Blender 5.0.0 exactly**. Registration fails closed on any other Blender version.

## Purpose

Use a finished statue body as the guide and propagate its world-space **G / R / uniform positive S** change to the complete statue, including parts in viewport-disabled or View-Layer-excluded collections, while the Catholic base/reference remains fixed.

## Workflow

1. Save the working `.blend`.
2. Optionally import the fixed base/reference `.blend`.
3. Choose guide, fixed base and target collection.
4. Click **Preparar Estátua**.
5. Move only the guide with G / R / uniform positive S.
6. Click **Aplicar Transformação**.
7. **Finalizar / Manter Nova Posição** or **Restaurar Estado Inicial**.

## Architecture retained

### Channel-derived world transforms

Managed target transforms do not trust depsgraph `obj.matrix_world`. World matrices are calculated from `matrix_basis`, `matrix_parent_inverse`, the parent chain and BONE parenting when applicable. Apply converts the desired world matrix back into local basis channels.

`D = M_guide_current @ inverse(M_guide_saved)`

`M_final = D @ M_original`

A delta containing shear / inherited non-uniform scale is refused before target mutation.

### Persistence schema 6

Snapshot schema remains **6** (`_t7sm_snapshot_v6`). Original restoration state and current on-disk `disk_state` remain separate. External baselines are promoted only from `save_post` for the actual file. Serialized paths are never trusted as deletion authority.

### Reference cleanup safety

The all-ID Library preflight remains. Any untagged linked ID or Library Override depending on the tagged source Library blocks cleanup before destructive removal. N-25 and N-24 have runtime evidence in Blender/bpy 5.0.0.

## v1.2.9 safety retained

- N-26: deferred recovery avoids `_RestrictData` during normal add-on enable.
- N-27: post-Prepare target constraints block Restore/Finalize before checkpoint deletion.
- N-28: complete raw Mesh fingerprint via `foreach_get` buffers.
- N-29: exclusive `tempfile.mkstemp()` writes avoid predictable `.tmp` symlink redirection.

## v1.2.10 corrections after the Claude v1.2.9 runtime HOLD

### N-30 CRITICAL — Prepare arity regression

v1.2.9 changed `mesh_geometry_sentinel()` to `(valid, digest)` but Prepare still unpacked four legacy values. v1.2.10 removes that obsolete call from snapshot capture. The full `geometry_sentinel()` is stored once; legacy schema-v6 Mesh sample fields remain neutral metadata only.

Snapshot capture is now fail-closed as its own transaction: an unexpected capture exception clears partial object/modifier state and the snapshot id before returning `CANCELLED`, while modifiers and external baselines are still untouched.

### N-31 HIGH — constraints on external ancestors

Dynamic transform validation now covers every managed target and its complete Object parent chain, not only the target itself. Constraints on an external parent/grandparent — and constraints on the specific BONE parent pose bone — block Prepare and are re-checked at Apply/Restore/Finalize so influences added later cannot produce false success.

A clean external parent remains supported.

### N-32 HIGH — animation can overwrite channels after Apply

Object-level Action, NLA or drivers on a target or target ancestor are now refused conservatively. Exact snapshot deletion is prioritized over supporting ambiguous animated Object state.

Finalize also independently verifies that, after an Apply, every target is still at `D @ original_world` before modifiers are restored or the checkpoint is deleted. This catches a pose that was changed by animation or another channel mutation even if the dynamic influence is later removed.


## v1.2.11 corrections after the Claude v1.2.10 runtime HOLD

### N-36 HIGH — float32 false rejection in Finalize

The v1.2.10 Finalize gate compared an ideal `D @ original_world` matrix directly against Blender's float32 channel readback. Correct production-scale poses could therefore be refused. v1.2.11 separates the two verification jobs:

- Apply checks the ideal target using a matrix-wide float32 ulp budget;
- after a fully verified Apply, each target stores the **actual channel-derived world readback** Blender represented;
- Finalize compares the current pose against that applied readback before modifier restoration or checkpoint deletion.

The additive schema-v6 fields `applied_world_valid` and `applied_matrix_world` are persisted and hydrated. If they are absent (for example an older active candidate snapshot), Finalize fails closed and keeps Restore available.

### N-35 MEDIUM — pose constraints elsewhere in a relevant Armature

The direct-parent-bone-only check was insufficient for root constraints, IK/other constrained bones, and Armatures that are themselves targets. v1.2.11 intentionally avoids trying to solve Blender's entire pose dependency graph: if an Armature is relevant through BONE parenting or is itself a target, **any pose-bone constraint anywhere in that Armature blocks the workflow**. A clean Armature remains supported.

## Known LOW items

- N-37: unexpected exception during Prepare preflight can still surface a traceback, but no mutation occurs and retry remains safe.
- N-33: `fsync` failure is currently tolerated; this is a durability/signaling improvement for a later narrow delta unless impact is escalated by audit.
- N-34: safe Library-cleanup refusal message could be more explanatory.

## Modifiers

- Original `show_viewport` is frozen per modifier.
- Guide/base/reference are excluded from managed shutdown.
- `show_render` is never intentionally changed.
- Restore/Finalize require readback before checkpoint deletion.

## Geometry verification

Fingerprints exist for Mesh, Curve/Surface, Text, Armature, Lattice, Meta and Point Cloud. Unsupported geometry-bearing target types are refused during Prepare; only the explicit no-local-geometry allowlist can prepare without a fingerprint.

## Reference import / cleanup

- Source must contain exactly one Scene.
- Current Scene is never replaced.
- Objects are made non-selectable; master is hidden from render.
- Unit system/scale are compared, never silently changed.
- User-owned/external reuse blocks cleanup before destructive removal.
- Tagged collections containing untagged/user content block cleanup.
- A tagged source Library is removed only after a dynamic all-ID scan proves that no untagged linked/override ID still depends on it.

## Audit status

v1.2.10 received **HOLD** in the Claude runtime audit because N-36 made correct production-scale poses impossible to Finalize and N-35 left a pose-bone-constraint gap. The same audit confirmed N-30/N-31/N-32 and the historical N-24..N-29 regression battery on the original v1.2.10 ZIP.

v1.2.12 later received **HOLD** in an independent cheap audit because N-39 showed that one extreme 3x3 component could still inflate the shared linear tolerance enough to hide an unrelated `1.00 -> 1.02` error and freeze that wrong pose as a valid applied readback.

v1.2.13 then received **HOLD** in a deeper cheap audit because N-40 showed that the 128-ULP local cap could still be widened by a larger sibling when the protected component itself was also large (for example `65536` masking `2048 -> 2048.025`).

v1.2.14 closed N-40 in cheap audits, but its Blender/bpy 5.0.0 runtime audit received **HOLD** for **N-42 HIGH**: strict per-component verification of reconstructed world matrices rejects correct large translations through 3D-rotated parents. The mandatory scale case now passed, but G 150/300/1000/10000/100000, historical `G_large`, and stress could fail because float32 rounding from a large world axis legitimately appears in another small world axis after parent rotation.

**v1.2.18 is not a production release. It must pass an inexpensive independent pre-audit and then an exact Blender 5.0.0 runtime audit before manual production testing.**

## Reference asset

If `assets/base_reference.blend` exists, it has priority. This candidate still ships without the real ~12 MB production reference asset; use the configured external path during audit.

## v1.2.12 correction after the cheap v1.2.11 HOLD

### N-38 HIGH — large translation inflated rotation/scale tolerance

v1.2.11 used one matrix-wide float32 ULP budget. A translation of 100000 could therefore grant a tolerance around 0.03125 to a unit-scale 3x3 component and incorrectly accept `1.00 -> 1.02`. v1.2.12 isolates the numerical domains:

- the affine 3x3 block receives a shared **linear** ULP budget (8 ULPs), independent of translation;
- each translation axis receives its own budget (4 ULPs), independent of the other axes and the 3x3 block;
- the affine bottom row receives only the small absolute floor;
- Finalize readback-vs-readback uses the same domain isolation with a much stricter 0.5-ULP budget plus the ordinary absolute floor.

This keeps the historical Blender float32 roundoff cases representable while preventing a large translation from hiding a real rotation/scale error. The applied-readback architecture and N-35 Armature policy are otherwise unchanged.

## v1.2.13 correction after the cheap v1.2.12 HOLD

### N-39 HIGH — same-domain masking inside the linear 3x3 block

v1.2.12 correctly isolated translation, the linear 3x3 and the affine bottom row, but all nine linear components still shared the same ULP budget. A component around 32768 could therefore grant a tolerance of 0.03125 to another component around 1.0 and incorrectly accept `1.00 -> 1.02`.

v1.2.13 keeps the shared 3x3 budget needed for the Blender parent-chain roundoff seen in N-36, but caps every linear element by a second budget derived only from that element's own magnitude. The effective Apply tolerance is the **minimum** of the shared block budget and a generous local 128-ULP cap. This keeps the observed ~8e-6 to ~1.14e-5 legitimate cross-component error representable while preventing an extreme sibling component from authorizing a macroscopic error in a unit-scale element.

Finalize readback-vs-readback also uses the local cap, with a strict 0.5-ULP shared/local budget plus the existing absolute floor. Translation remains per-axis and the bottom row remains isolated. No snapshot schema or persistence field changed in v1.2.13.


## v1.2.14 correction after the cheap v1.2.13 HOLD

### N-40 HIGH — sibling masking still possible between large linear components

v1.2.13 used `min(shared_8ULP, local_128ULP)` for each 3x3 element. That closed N-39 around unit-scale protected components, but a larger sibling could still raise the shared budget until it reached a large local cap on another already-large component. The reproduced case was `65536` alongside an expected `2048.000` read back as `2048.025`: without the sibling the error was rejected, with the sibling it was accepted and could be frozen as a valid applied readback.

v1.2.14 removes sibling-derived tolerance from the linear 3x3 entirely. Each linear component is checked independently against only:

- a fixed Apply-only absolute allowance of `1.6e-5`, chosen to cover the legitimate ~`7.9e-6` to ~`1.15e-5` N-36 parent-chain roundoff measured in Blender 5.0.0; and
- `8 ULP` of that **expected component's own magnitude**.

The divergent actual value is not allowed to widen its own tolerance. Therefore no other 3x3 component can change the allowance of the component being checked. Translation remains isolated per axis and the bottom row remains on the small absolute floor.

Finalize remains stricter: readback-vs-readback uses `0.5 ULP` of the frozen expected readback component plus the original `2e-6` absolute floor; it does **not** inherit the larger Apply-only N-36 allowance.

No snapshot schema, persistence field, G/R/S math, Armature policy, modifier handling or reference-cleanup behavior changed in v1.2.14.


## v1.2.15 correction after the Claude v1.2.14 runtime HOLD

### N-42 HIGH — world-component verification falsely rejects correct rotated-parent large translations

v1.2.14 treated each reconstructed world-matrix component as if its float32 error budget depended only on the magnitude of that same world component. Blender, however, stores local transform channels as float32. When a large translated child is reconstructed through a parent rotated in 3D, normal quantization from one large axis is mixed into other world axes. The runtime audit reproduced correct poses rejected from roughly 60–100 units onward, including all mandatory G=150/300/1000/10000/100000 cases in rotated-parent scenes.

v1.2.15 keeps the world target math unchanged (`desired_world = D @ original_world`) but changes the **strict Apply verification space**. `set_channel_world_matrix()` now returns the exact `matrix_basis` requested from Blender. Apply retains that basis transiently and verifies Blender's `obj.matrix_basis` readback against the requested basis with expected-only float32 budgets. Parent-chain multiplication is therefore outside the strict precision gate and cannot create cross-axis false failures.

Only after every channel-space write verifies successfully does the existing applied-world-readback capture run. Finalize remains based on that frozen, representable world readback and still blocks drift before modifier restoration/checkpoint deletion.

The historical `verify_applied_world_matrices()` helper remains for diagnostics/audit vectors but is no longer the blocking Apply gate. No snapshot schema, persistence field, G/R/S math, N-35 policy, modifier behavior, geometry fingerprint, N-29 temp/symlink handling or reference cleanup was redesigned in v1.2.15.


## v1.2.16 correction after the Claude v1.2.15 runtime HOLD

### N-45 HIGH — recomposed matrix_basis falsely rejects correct large-scale / near-gimbal poses

The v1.2.15 runtime audit proved that Blender stores transform channels in float32 and reconstructs `matrix_basis`; it does not preserve the 16 requested matrix components directly. Correct objects around scale 50–1000, and even scale-1 objects near Euler gimbal lock, could therefore fail the strict requested-basis-vs-readback-matrix gate.

v1.2.16 keeps the same `desired_world` and setter math but changes the blocking post-write verification to the actual RNA transform channels Blender stored immediately after the synchronous matrix_basis assignment. Those raw channels are frozen transiently and must remain stable after all writes/update. This preserves post-write corruption detection without comparing a recomposed matrix against the original double-precision matrix.

A second coarse world-material sanity check catches gross setter/prefix failures without serving as the precision gate. Only after both checks pass is the existing applied-world readback frozen for Finalize. Snapshot schema remains 6.


## v1.2.17 correction after the v1.2.16 economic HOLD

### N-47 HIGH — coarse world-sanity budgets could canonicalize a materially wrong world

The v1.2.16 raw-channel gate remains unchanged: Apply still freezes the actual RNA transform channels immediately after each `matrix_basis` write and later proves those channels stayed stable. That architecture is the N-45 correction and remains the primary precision gate.

The only functional change in v1.2.17 is the **secondary world-material sanity** policy. v1.2.16 used 64 ULP of the largest expected translation coordinate for every translation component and 256 ULP of a whole linear column for every element in that column. Independent auditors showed that a stable but wrong setter/prefix result could therefore pass, e.g. `(1e6,0,0) -> (1e6,3.5,0)` or linear column `(65536,1,0) -> (65536,2.9,0)`, and then be frozen as `applied_world_valid=True`.

v1.2.17 replaces those per-component aggregate budgets with geometric expected-only checks:

- translation is compared as one 3-vector, with `max(1e-4, 4 ULP(max expected coordinate))`;
- each linear 3-vector column is compared by Euclidean error against `max(1e-4, 2.5e-5 * max(1, expected column norm))`;
- the affine bottom row remains on the strict `2e-6` floor;
- NaN/Inf still fail closed.

This deliberately keeps the coupling that N-42/N-45 proved is legitimate (translation can mix across axes through rotated parents; rotation/scale error can move inside one linear column) while preventing the much larger 64/256-ULP masks that produced N-47. Snapshot schema remains 6.

## v1.2.18 correction after the v1.2.17 economic HOLD

### N-48 HIGH — column-norm sanity still masked a small sibling inside the same column

v1.2.17 substantially reduced the N-47 world-sanity envelope, but its linear check still used only one vector budget proportional to the full expected column norm. Independent auditors reproduced that expected `(65536,1,0)` could still accept `(65536,2.5,0)`: the large `65536` term produced a column budget of about `1.6384`, enough to hide a `+1.5` error in the sibling expected as `1`. The wrong world could then be frozen as `applied_world_valid=True`.

v1.2.18 keeps the raw-channel N-45 gate and the v1.2.17 translation sanity unchanged. Linear world sanity now requires **both**:

- the existing total column-vector error budget `max(1e-4, 2.5e-5 * max(1, ||expected_column||))`; and
- a new per-component expected-only cap `max(0.0125, 8 ULP(max(1, |expected_component|)))`.

The second cap cannot be enlarged by a sibling in the same or another column, nor by the divergent `actual` value. The `0.0125` floor is an empirical candidate chosen just above the worst Blender 5.0.0 p32 linear roundtrip component residual measured through scale 1000 (`~0.01031`) and below the historical N-38 `1 -> 1.02` drift. It must still be falsified by cheap audit and then validated in exact Blender 5.0.0; it is not treated as production proof.

Snapshot schema remains 6 and no persistence, G/R/S, modifier, N-35, N-24..N-32, geometry, N-29 or reference-cleanup architecture was redesigned in v1.2.18.

## v1.2.21 correction after the v1.2.20 runtime HOLD

### N-56 HIGH — singular Euler threshold too coarse after polar projection

The exact Blender 5.0.0 runtime audit of v1.2.20 proved that the polar projection itself works: N-54 closed across roots, children, parent chains and exact gimbal. However, after that projection the requested rotation is already orthonormal in Python double precision, so `EULER_SINGULAR_THRESHOLD = 1e-6` is unnecessarily coarse. In a narrow legitimate window only a few ten-thousandths of a degree from +/-90 degrees, the singular branch discards O(cy) information. At large world column magnitudes this can exceed the unchanged N-48 component cap and falsely reject an otherwise correct pose.

v1.2.21 changes only that numerical switch to `1e-12`. The v1.2.20 runtime counterfactual already showed that this threshold closes the N-56 reproduction while keeping the full, singular, child and large-scale batteries clean. The polar projection, shear guard, world-sanity budgets and N-48 cap are not weakened.

### N-52 MEDIUM — preserve the user's pre-write Euler branch

v1.2.20 fixed the branch-ranking rule itself, but still measured continuity against `rotation_euler` *after* Blender's native `matrix_basis` setter. Blender can already jump to an equivalent distant Euler branch during that setter, so the add-on could preserve the wrong representation even though the world pose remained correct.

v1.2.21 captures the base Euler channels immediately before `obj.matrix_basis = local` and passes that tuple only as the continuity reference for the compatible double-precision Euler selection. The requested transform, signed-scale/delta factoring and all downstream world/readback gates remain unchanged. Quaternion and Axis-Angle still use the historical setter path.

Snapshot schema remains 6. This candidate is not production GO until independent cheap audit and exact Blender 5.0.0 runtime validation.

## v1.2.20 correction after the v1.2.19 runtime HOLD

### N-54 HIGH — child/local float32 non-orthogonality amplified near gimbal

Runtime v1.2.19 proved that the v1.2.19 Euler-double refinement works for root objects but can fail badly for children of rotated parents. The requested `local` matrix can contain only ~1e-7 of non-orthogonality from float32 parent-prefix products; decomposing that matrix directly near +/-90 degrees amplifies the noise, and exact gimbal can select arbitrary Euler channels.

v1.2.20 keeps the same native `matrix_basis` setter and the same shear guard, but projects the normalized requested basis to the nearest proper rotation with a double-precision polar iteration before Euler decomposition. The projection is only reached after the existing shear check and refuses singular/reflected results. That candidate also raised the matrix->Euler singular threshold to `1e-6`; the later v1.2.20 runtime audit identified N-56 in that choice, and v1.2.21 supersedes it with a double-scale threshold.

### N-53 HIGH + N-51 — split direction/recomposition error from true scale drift

Runtime v1.2.19 showed that tightening the entire linear column vector budget to `1e-5` closed N-51 but rejected correct production children under the anisotropic `(12,12,1)` guide. v1.2.20 separates the two questions:

- total column-vector error returns to the previously proven `2.5e-5` expected-relative envelope;
- column **length** gets an independent strict `1e-5` expected-relative/absolute envelope;
- the N-48 per-component cap remains unchanged.

The intended distinction is geometric: small directional/recomposition noise may change components without materially changing the column length, while the N-51 `scale += 2e-5` fault changes the column length and must still be rejected.

### N-52 MEDIUM — equivalent Euler branch continuity

v1.2.19 ranked equivalent Euler branches lexicographically by reconstruction error before channel distance, so differences around 1e-16 could select a branch ~pi away. v1.2.20 treats reconstruction errors within `1e-12` as equivalent and then chooses the branch nearest the current Euler channels.

## v1.2.19 correction after the v1.2.18 runtime HOLD

### N-50 HIGH — Blender matrix_basis setter loses Euler precision near gimbal

The exact Blender 5.0.0 runtime audit proved that the v1.2.18 world-sanity gate was correctly rejecting some almost-gimbal cases because the pose had already been written incorrectly. Assigning `obj.matrix_basis = local` lets Blender decompose the requested matrix into float32 Euler channels; near the middle Euler axis at +/-90 degrees, the setter can introduce relative linear error up to about `5.3e-4`. A double-precision Euler computed from the same requested rotation and then stored as float32 channels reproduced the same pose orders of magnitude more accurately.

v1.2.19 keeps the native `matrix_basis` assignment first so Blender remains responsible for location, signed scale and delta factoring. For the six Euler rotation modes only, it then recomputes the requested total rotation from the requested basis using the signed scale chosen by Blender, removes `delta_rotation_euler` in Blender's `delta @ base` order, converts the base rotation to a compatible Euler using Python double-precision math, and writes only `rotation_euler`. Quaternion and Axis-Angle remain on the historical setter path. Genuine shear skips refinement and remains fail-closed under the existing world sanity.

### N-51 MEDIUM — mandatory unit 2e-5 fault was inside the old column budget

Because fault injection inside the setter occurs before the raw-channel snapshot, the world sanity remains responsible for catching that class. With N-50 addressed at the writer, v1.2.19 tightens only the linear column budget from `max(1e-4, 2.5e-5 * norm)` to `max(1e-5, 1e-5 * norm)`. Translation keeps the N-42 four-ULP vector budget and the N-48 per-component cap remains unchanged.

Snapshot schema remains 6. This candidate is not production GO until independent cheap audit and exact Blender 5.0.0 runtime validation.
