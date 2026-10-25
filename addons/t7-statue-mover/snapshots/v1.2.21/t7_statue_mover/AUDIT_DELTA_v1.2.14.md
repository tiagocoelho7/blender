# T7 Statue Mover v1.2.14-candidate — Audit Delta

Target runtime: **Blender 5.0.0 exactly**.

This is a narrow corrective delta over the frozen v1.2.13 candidate after the independent cheap-audit HOLD. Auditors must reproduce every claim against the ZIP.

## N-40 HIGH — sibling masking remained possible between large linear components

### v1.2.13 failure

v1.2.13 fixed N-39 by using `min(shared_8ULP, local_128ULP)` per 3x3 element. That worked for a protected component near 1.0, but the local 128-ULP cap itself becomes large when the protected component is large.

The cheap auditor reproduced the full chain with the real helpers:

- sibling linear component: `65536`;
- protected expected component: `2048.000`;
- actual protected component: `2048.025`;
- error: `0.025` (~102.4 ULP of 2048);
- without the sibling, the natural 8-ULP budget of 2048 was `0.001953125` and the error was rejected;
- with the sibling, the shared 8-ULP block budget and local 128-ULP cap both reached `0.03125`, so the same error was accepted;
- Apply could then capture the wrong readback as `applied_world_valid=True` and Finalize would accept that frozen wrong pose.

Equivalent cases were reported for `1e6 / 32768 / drift 0.4` and `1e8 / 65536 / drift 0.8`.

### v1.2.14 correction

The Apply verifier no longer uses any sibling-derived linear budget.

For each 3x3 element independently:

`linear_tolerance = max(1.6e-5, 8 * ulp(expected_component))`

Key properties:

1. the only magnitude-dependent term is the **expected component itself**;
2. no sibling 3x3 element participates;
3. the divergent actual/readback value cannot inflate its own allowance;
4. the fixed `1.6e-5` Apply-only floor preserves the N-36 legitimate parent-chain errors observed around unit-scale components (~`7.9e-6`, ~`8.97e-6`, ~`1.15e-5`);
5. large components still receive their own ordinary float32 budget (8 ULP), rather than 128 ULP or a sibling-derived budget.

Translation remains isolated per axis under the existing v1.2.12 policy. Bottom row remains on `MATRIX_ABS_TOLERANCE`.

Finalize readback-vs-readback is intentionally stricter. For linear components it uses:

`max(2e-6, 0.5 * ulp(frozen_expected_readback_component))`

It does not use the Apply-only `1.6e-5` allowance.

## Mandatory cheap-audit vectors

### Must accept

- N-36 cross-component: sibling linear ~48, unit component error ~`7.9e-6`;
- stronger historical N-36 vector ~`8.97e-6`;
- stronger historical N-36 vector ~`1.15e-5`;
- error ~`7.9e-6` on the component around 48 itself;
- translation error ~`1.22e-4` at translation ~1000;
- translation error ~`7.8e-3` at translation ~100000;
- 4 ULP on the same large linear component at 32768;
- up to 8 ULP on the same large linear component where the fixed floor does not dominate.

### Must reject

- historical macroscopic error ~`0.78`;
- N-38: translation 100000 masking linear `1.00 -> 1.02`;
- N-39: sibling 32768 masking unit `1.00 -> 1.02`;
- N-39 sibling sweep `2048..1000000` masking unit `1.00 -> 1.02`;
- sibling 65536 masking unit `1.00 -> 1.001` and `1.00 -> 1.0001`;
- **N-40 exact:** sibling 65536 / target 2048 / drift `0.025`;
- **N-40:** sibling 1e6 / target 32768 / drift `0.4`;
- **N-40:** sibling 1e8 / target 65536 / drift `0.8`;
- any sibling-dependent change in the tolerance of a protected linear component;
- >8 local ULP on a large protected component (allow a small boundary margin when designing the test, but do not let a sibling change the result);
- near-zero/unit component drift `2e-5` while the historical <=`1.15e-5` N-36 envelope remains accepted;
- large linear masking translation;
- X translation masking Y/Z;
- large translation masking bottom row;
- NaN / +Inf / -Inf.

### Search for N-41

Try to find a new widening path, especially:

- the **actual mismatching value** inflating its own tolerance;
- powers-of-two boundaries;
- negative values;
- components near zero;
- very large/small finite magnitudes;
- mixtures of huge and moderate 3x3 components;
- argument-order dependence;
- any Apply mismatch that still leads to `applied_world_valid=True`.

## N-35 and historical fixes

No redesign is intended in N-35. Preserve the conservative Armature rule from v1.2.11. No intended functional rewrite exists in N-24..N-39 except the N-40 tolerance path described above.

## Known LOW items intentionally unchanged

- N-37: unexpected Prepare-preflight exception may surface a traceback but does not mutate state.
- N-33: `fsync` failure is tolerated.
- N-34: Library-cleanup fail-closed messaging remains generic.

## Version / persistence

- Add-on version: **1.2.14**
- Snapshot schema remains **6** (`_t7sm_snapshot_v6`).
- No persistence field was added or removed in this delta.
