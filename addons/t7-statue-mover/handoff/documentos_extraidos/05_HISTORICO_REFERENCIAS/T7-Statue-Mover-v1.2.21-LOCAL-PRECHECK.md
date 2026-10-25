# T7 Statue Mover v1.2.21 — Local precheck (developer-side, NOT audit proof)

## Candidate tested

- ZIP: `t7-statue-mover-v1.2.21-candidate.zip`
- SHA-256: `7d475cfb4453ba3abc34da32a56274e4c296caebb614a78363c4c63edd57044f`
- `__init__.py` SHA-256: `3678a278f60afa84850167618d0e659359948cfc913e671101195963fc7c8a7e`
- Target: Blender 5.0.0 exactly
- Snapshot schema: 6

This precheck was executed against a **fresh extraction of the final ZIP**. It is developer-side corroboration only and must not be treated as an independent audit or runtime Blender proof.

## Result

**29 PASS / 0 FAIL**

## N-56 focal checks

The exact candidate helper code was extracted by AST.

- `EULER_SINGULAR_THRESHOLD == 1e-12`: PASS.
- Directed narrow-window cases across all six Euler orders: 216 cases, worst reconstruction error `1.110e-16`.
- The same helper code with the old `1e-6` threshold injected produced worst reconstruction error `1.236e-6`; 36 directed cases were large enough that `error * 16000 > 0.0125`, independently reproducing the mechanism that can trip the N-48 component cap at large world columns.
- Exact +90-degree gimbal reconstruction: worst `1.110e-16`.
- 6,000 noisy near/exact-gimbal polar cases: 6,000/6,000 projected.
- Worst polar->Euler reconstruction error: `9.992e-16`.
- Worst polar movement versus clean rotation: `9.591e-7`, consistent with injected 1e-8..1e-6 noise.

These are pure-math checks. They do **not** prove Blender's real setter/depsgraph path.

## N-52 focal checks

Structural AST inspection of `set_channel_world_matrix()` confirmed:

1. `continuity_reference` is captured from `obj.rotation_euler`;
2. capture occurs **before** `obj.matrix_basis = local`;
3. the same tuple is passed into `_refine_euler_after_matrix_basis_write()`.

The refinement helper retains a fallback to current/post-setter channels when no explicit continuity reference is supplied.

Pure helper checks:

- pre-write continuity: 0 failures / 1,200 cases across six Euler orders;
- fallback behavior: 0 failures / 1,200;
- +/-2pi wrapping/world reconstruction: worst `9.320e-14`.

Again, Blender 5.0.0 runtime is required to prove the actual N-52 user-facing result (`p58`/save-reopen).

## N-53 / N-51 / N-48 regression policy

Confirmed from candidate helpers/constants:

- vector envelope remains `2.5e-5`;
- column-length envelope remains `1e-5`;
- N-48 component floor remains `0.0125`;
- unit `+2e-5` and `+1.1e-5` remain outside the length budget;
- pure direction `1.7e-5` at unit norm remains eligible under vector+length policy;
- N-48 classical `1 -> 2.5` sibling drift remains outside the component cap.

## Integrity/static

- ZIP CRC: PASS.
- traversal: none.
- internal `SHA256SUMS.txt`: 24/24 OK after fresh extraction.
- `python -m py_compile`: PASS.
- top-level defs/classes: 168; duplicate top-level names: none.
- `ruff F821/F822/F823/F811`: unavailable in this environment; not counted as PASS.
- no `__pycache__` / `.pyc` is bundled.

## Mandatory next step

Two independent cheap audits first. If both return no HIGH/CRITICAL, then exact Blender/bpy 5.0.0 runtime on the same frozen candidate, specifically:

- p59 96/96;
- p50 window 0/1152 false rejects;
- p50 singular 1440/1440;
- p50 full 7560/7560;
- singbig no root regression;
- p58-like N-52 user-channel continuity target 0/300 branch swaps vs pre-write channels;
- p51 persistence;
- p52 59/59;
- t62/t63 N-51;
- full historical battery.

No production GO is claimed here.
