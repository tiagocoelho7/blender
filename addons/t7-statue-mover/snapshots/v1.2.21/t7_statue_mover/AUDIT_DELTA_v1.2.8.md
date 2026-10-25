# T7 Statue Mover v1.2.8-candidate — Audit Delta

Target: **Blender 5.0.0 exactly**.

This candidate is a narrow corrective delta over v1.2.7. The v1.2.7 audit ran the original ZIP without patches and reported 761 PASS, with one blocking HIGH (N-25) and one persistent LOW (N-24). No persistence, transform, modifier, lifecycle, registration, geometry-sentinel, import, or security architecture is intentionally redesigned here.

## N-25 HIGH — linked user data deleted with Library cleanup

### Root cause

v1.2.7 correctly moved Library removal to the end, but the external-reuse preflight only scanned the add-on's fixed `REFERENCE_DATASET_NAMES`. `bpy.data.libraries.remove()` cascades to linked IDs, so untracked linked ID types such as Text, Brush, Palette, LineStyle, LightProbe and hair curves could be deleted with a false `cleanup completo` message.

### v1.2.8 correction

`reference_library_external_reuse_reasons()` no longer relies on `REFERENCE_DATASET_NAMES` for the Library safety boundary.

A new `_iter_all_bpy_data_ids()` dynamically walks all iterable ID-like collections exposed by `bpy.data`, de-duplicates datablocks by pointer, and checks every actual datablock for:

- `id.library == tagged_library`; or
- `id.override_library.reference.library == tagged_library`.

Any untagged linked/override ID blocks cleanup during the preflight, before imported Objects/Collections are deleted. Tagged IDs belonging to the same import remain internal.

Library removal itself remains last and is attempted only after all other tagged IDs are gone and this all-ID preflight is clean.

Mandatory regression: linked Text, Brush, Palette, LineStyle, LightProbe, hair_curves, CacheFile, MovieClip, Mask, Workspace and any additional linkable ID types available in Blender 5.0.0.

## N-24 LOW — crash candidate not cleaned

### Root cause

After a crash between `final -> previous` and `candidate -> final`, the `.previous` filename carries the *new transaction id*, while its payload is the *old snapshot*. v1.2.7 compared candidate payload `snapshot_id` to previous payload `snapshot_id`, which can never match in this crash window.

### v1.2.8 correction

Crash recovery now derives the 32-hex transaction id from the validated `.previous` **filename** and only considers the exact sibling:

`<canonical>.json.<transaction_id>.candidate`

Deletion still requires:

- regular file, not symlink;
- valid JSON/checksum;
- matching blend path + file SHA + Scene through the normal reader;
- candidate payload `snapshot_id` equals the filename transaction id.

Foreign candidates and symlinks remain untouched.

## Version / schema

- Add-on version: 1.2.8
- Snapshot schema remains 6 (`_t7sm_snapshot_v6`); no persisted payload format changed.

## Required non-regression

Re-run the complete v1.2.7 evidence bundle against the **original unpatched ZIP**. In particular preserve:

- N-01 P2/load_post including non-active Scenes;
- N-02 baseline immutability across Save Copy/autosave/register/re-enable;
- N-03 hidden/excluded channel-derived world transforms;
- N-04 safe deletion boundary;
- N-05 import;
- N-06/N-07 cleanup safety;
- N-08 lifecycle;
- N-09 multi-Scene baseline isolation;
- N-10 shear gate;
- N-21 honest external status;
- N-22 registration/static gate;
- N-23 geometry policy;
- H-01/R-01..R-04, F-01..F-05;
- modifiers, G/R/S, hierarchy/armature, P1/P2/P3 and stress.
