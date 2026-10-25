# T7 Statue Mover v1.2.12-candidate — Audit Delta

Target runtime: **Blender 5.0.0 exactly**.

This is a narrow corrective delta over the frozen v1.2.11 candidate after the independent cheap-audit HOLD. Auditors must reproduce every claim against the ZIP.

## N-38 HIGH — matrix-wide ULP tolerance allowed cross-domain masking

### v1.2.11 failure

The Apply verifier used one float32 ULP tolerance derived from the largest absolute value among all 16 matrix components. With `translation.x = 100000`, that tolerance became `0.03125` for **every** component. A deliberately wrong 3x3 component `1.00 -> 1.02` was therefore accepted. Because Apply then captured the wrong readback as valid, Finalize later accepted the same incorrect pose.

This was reproduced without Blender and is sufficient for HOLD.

### v1.2.12 correction

The tolerance is now partitioned by affine domain:

1. **Linear 3x3 block:** one shared budget derived only from the largest magnitude inside the 3x3 block. Apply uses 8 float32 ULPs plus the existing absolute floor. This allows decomposition/recomposition roundoff to move between rotation/scale components without borrowing tolerance from translation.
2. **Translation:** each X/Y/Z axis receives its own budget derived only from that axis. Apply uses 4 ULPs plus the absolute floor. A huge X translation cannot inflate Y/Z or the linear block.
3. **Affine bottom row:** only the existing small absolute tolerance is permitted.
4. **Finalize readback gate:** uses the same domain isolation but a stricter 0.5-ULP budget (plus the absolute floor), because it compares a current readback to a previously captured Blender-representable readback rather than to ideal math.

### Mandatory cheap-audit vectors

Must accept:

- historical linear/block roundoff around `7.9e-6` when the 3x3 scale is around 24–48;
- translation error around `1.22e-4` at translation magnitude ~1000;
- translation error around `7.8e-3` at translation magnitude ~100000.

Must reject:

- historical macroscopic error around `0.78`;
- **N-38 exact reproduction:** `translation.x=100000`, expected `[0][0]=1.00`, actual `[0][0]=1.02`;
- same large X translation with a wrong Y translation around `0.02` when Y itself is near zero;
- a real linear drift of `1e-3` at ordinary scale.

The auditor should verify that a failed Apply verification never captures `applied_world_valid=True`.

## N-35 and historical fixes

No redesign is intended in N-35. The conservative rule remains: any pose-bone constraint in an Armature that is a target or provides BONE parenting to a target blocks the workflow. Preserve all runtime evidence for N-24..N-35, N-30/N-31/N-32, G/R/S, persistence, modifiers, hidden/excluded collections and stress.

## Known LOW items intentionally unchanged

- N-37: unexpected Prepare-preflight exception may surface a traceback but does not mutate state.
- N-33: `fsync` failure is tolerated.
- N-34: Library-cleanup fail-closed messaging remains generic.

## Version / persistence

- Add-on version: **1.2.12**
- Snapshot schema remains **6** (`_t7sm_snapshot_v6`).
- No new persistence fields were added in this delta.
