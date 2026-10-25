# T7 Statue Mover v1.2.13-candidate — Audit Delta

Target runtime: **Blender 5.0.0 exactly**.

This is a narrow corrective delta over the frozen v1.2.12 candidate after the independent cheap-audit HOLD. Auditors must reproduce every claim against the ZIP.

## N-39 HIGH — one extreme 3x3 component could mask another linear component

### v1.2.12 failure

v1.2.12 correctly separated translation, the affine 3x3 block and the bottom row, closing N-38. However, all nine 3x3 elements still shared one ULP budget derived from the largest linear component.

A cheap auditor reproduced:

- expected linear diagonal `(32768, 1.00, 1.00)`;
- actual linear diagonal `(32768, 1.02, 1.00)`;
- shared Apply tolerance `0.03125`;
- the real `0.02` error in the unit component was accepted;
- Apply could then capture that wrong matrix as `applied_world_valid=True`;
- Finalize would accept the same frozen wrong readback.

This was deterministic in the real helpers and is sufficient for HOLD.

### v1.2.13 correction

Apply now uses a **hybrid 3x3 tolerance** for every linear component:

1. keep the existing shared block budget (`8 ULP`) so legitimate parent-chain decomposition/recomposition can move a few ulps between linear components;
2. compute a second **local budget** from only the current component magnitude (`128 ULP`, plus the existing absolute floor);
3. the effective tolerance for that component is `min(shared_block_budget, local_component_budget)`.

The local cap is intentionally generous at ordinary magnitudes because the Blender 5.0.0 runtime evidence behind N-36 contained legitimate cross-component world-matrix differences around `7.9e-6` to `1.14e-5` near unit-scale components. At magnitude ~1, 128 float32 ULPs are about `1.53e-5`, which keeps those cases representable while still rejecting `1.00 -> 1.0001`, `1.001`, `1.02`, etc.

Translation remains isolated per axis with the v1.2.12 policy. The bottom row remains on the small absolute floor.

Finalize readback-vs-readback also uses the same component isolation, but with both shared and local linear budgets set to `0.5 ULP`, plus the absolute floor.

## Mandatory cheap-audit vectors

### Must accept

- N-36 cross-component case: another 3x3 element around `48`, unit component difference ~`7.9e-6`;
- stronger historical cross-component case around `1.15e-5` with another 3x3 element around `48`;
- local difference ~`7.9e-6` on a component around `48`;
- translation error ~`1.22e-4` at translation magnitude ~`1000`;
- translation error ~`7.8e-3` at translation magnitude ~`100000`;
- a few ULPs on the **same large component** itself, e.g. 4 ULP at 32768.

### Must reject

- historical macroscopic error ~`0.78`;
- N-38 cross-domain: `translation.x=100000`, expected linear `1.00`, actual `1.02`;
- N-39 exact: one linear component `32768`, another expected `1.00`, actual `1.02`;
- N-39 magnitude sweep with sibling `2048/4096/8192/16384/32768/65536/100000/1000000` masking `1.00 -> 1.02`;
- sibling `65536` masking `1.00 -> 1.001` and `1.00 -> 1.0001`;
- large linear component masking a translation drift;
- large translation masking another translation axis or the bottom row;
- NaN / +Inf / -Inf.

The auditor should also verify the full logical chain: if Apply verification rejects the N-39 matrix, the operator flow must not capture `applied_world_valid=True`.

## N-35 and historical fixes

No redesign is intended in N-35. Preserve the conservative Armature rule from v1.2.11. No intended functional rewrite exists in N-24..N-38 except the N-39 tolerance path described above.

## Known LOW items intentionally unchanged

- N-37: unexpected Prepare-preflight exception may surface a traceback but does not mutate state.
- N-33: `fsync` failure is tolerated.
- N-34: Library-cleanup fail-closed messaging remains generic.

## Version / persistence

- Add-on version: **1.2.13**
- Snapshot schema remains **6** (`_t7sm_snapshot_v6`).
- No persistence field was added or removed in this delta.
