bl_info = {
    "name": "T7 Statue Mover",
    "author": "T7 / OpenAI",
    "version": (1, 2, 21),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > T7 Statue",
    "description": "Persistent statue transform snapshots, G/R/S propagation, modifier safety, and fixed base/reference import for Blender 5.0.0",
    "category": "Object",
}

import bpy
import os
import json
import hashlib
import uuid
import tempfile
import sys
from array import array
from datetime import datetime, timezone
from math import atan2, degrees, frexp, isfinite, pi, sin, cos, sqrt
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    IntVectorProperty,
    PointerProperty,
    StringProperty,
)
from bpy.app.handlers import persistent
from bpy.types import Operator, Panel, PropertyGroup, AddonPreferences
from mathutils import Matrix


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

IDENTITY_MATRIX_FLAT = (
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 1.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
)

GEOMETRY_SAMPLE_TOLERANCE = 1.0e-6
ZERO_DELTA_TOLERANCE = 1.0e-10
IDENTITY_TOLERANCE = 1.0e-8
MATRIX_ABS_TOLERANCE = 2.0e-6
MATRIX_REL_TOLERANCE = 2.0e-6
MATRIX_LINEAR_APPLY_ABS_TOLERANCE = 1.6e-5
# v1.2.21: N-56 runtime showed that, after the v1.2.20 polar projection, the
# requested rotation is already orthonormal in Python double precision. A singular
# Euler threshold of 1e-6 is therefore too coarse and can enter the singular branch
# for a narrow but legitimate near-gimbal window, discarding O(cy) information and
# causing false rejects at large world scales. Use a double-scale threshold (1e-12)
# instead.
#
# N-52 also remained visible to the user because v1.2.20 compared equivalent Euler
# branches against the channels *after* Blender's matrix_basis setter, and that setter
# can itself jump to an equivalent branch. v1.2.21 captures the pre-write Euler
# channels and uses them only as the continuity reference for branch selection. The
# requested world transform, signed scale handling, deltas, and downstream sanity
# gates remain unchanged.
#
# v1.2.20: N-54 is fixed at the Euler write path by projecting the requested
# normalized linear basis onto the nearest proper rotation *before* matrix->Euler
# decomposition. Parent-chain float32 products can inject ~1e-7 non-orthogonality;
# near gimbal that tiny noise is otherwise amplified catastrophically. A polar
# orthonormalization in Python double precision removes only that numerical noise,
# while the pre-existing shear guard still refuses materially non-TRS inputs.
#
# N-53 showed that a single 1e-5 vector budget conflates two different questions:
# harmless directional/recomposition noise in a hierarchy, and real column-length
# (scale) drift such as N-51. v1.2.20 restores the proven 2.5e-5 vector envelope
# for direction/recomposition, but adds an independent 1e-5 expected-only column-
# length budget. Thus hierarchy noise can pass while a true unit +2e-5 scale drift
# remains rejectable. Translation and the N-48 per-component cap stay unchanged.
WORLD_SANITY_ABS_TOLERANCE = 1.0e-4
WORLD_SANITY_LINEAR_ABS_TOLERANCE = 2.5e-5
WORLD_SANITY_LINEAR_REL_TOLERANCE = 2.5e-5
WORLD_SANITY_LINEAR_LENGTH_ABS_TOLERANCE = 1.0e-5
WORLD_SANITY_LINEAR_LENGTH_REL_TOLERANCE = 1.0e-5
WORLD_SANITY_LINEAR_COMPONENT_ABS_TOLERANCE = 1.25e-2
WORLD_SANITY_LINEAR_COMPONENT_ULPS = 8.0
WORLD_SANITY_TRANSLATION_ULPS = 4.0
EULER_SINGULAR_THRESHOLD = 1.0e-12
EULER_BRANCH_ERROR_EQUIVALENCE = 1.0e-12
SIMILARITY_TOLERANCE = 2.0e-5

ADDON_VERSION = (1, 2, 21)
SUPPORTED_BLENDER_VERSION = (5, 0, 0)
SNAPSHOT_SCHEMA_VERSION = 6
SCENE_SNAPSHOT_KEY = "_t7sm_snapshot_v6"
REFERENCE_TAG_KEY = "_t7sm_reference_import_id"
REFERENCE_MASTER_TAG = "_t7sm_reference_master"
REFERENCE_MASTER_NAME = "T7_BASE_REFERENCIA"
BUNDLED_REFERENCE_RELATIVE = os.path.join("assets", "base_reference.blend")

FILE_HASH_CHUNK_SIZE = 8 * 1024 * 1024
_FILE_HASH_CACHE = {}

REFERENCE_DATASET_NAMES = (
    'objects', 'collections', 'scenes',
    'armatures', 'cameras', 'curves', 'fonts', 'grease_pencils', 'lattices',
    'lights', 'meshes', 'metaballs', 'pointclouds', 'speakers', 'volumes',
    'materials', 'node_groups', 'textures', 'images', 'actions', 'worlds', 'sounds', 'libraries',
)



# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------


def matrix_to_flat(matrix):
    return tuple(matrix[row][col] for row in range(4) for col in range(4))


def flat_to_matrix(values):
    return Matrix((
        values[0:4],
        values[4:8],
        values[8:12],
        values[12:16],
    ))


def object_pointer(obj):
    return obj.as_pointer() if obj is not None else 0


def scene_objects(scene):
    """Return a real list so later property changes never mutate an iterator."""
    return list(scene.collection.all_objects[:])


def collection_scene_objects(scene, collection):
    """Objects in collection + nested children, intersected with the current scene."""
    scene_by_ptr = {object_pointer(obj): obj for obj in scene_objects(scene)}
    result = []
    for obj in list(collection.all_objects[:]):
        ptr = object_pointer(obj)
        if ptr in scene_by_ptr:
            result.append(scene_by_ptr[ptr])
    return result


def object_descendants(root):
    if root is None:
        return set()

    result = set()
    stack = list(root.children)
    while stack:
        obj = stack.pop()
        ptr = object_pointer(obj)
        if ptr in result:
            continue
        result.add(ptr)
        stack.extend(list(obj.children))
    return result


def fixed_object_pointers(settings):
    fixed = set()
    base = settings.base_object
    if base is not None:
        fixed.add(object_pointer(base))
        fixed.update(object_descendants(base))

    # Imported base/reference assets are always fixed, regardless of visibility.
    reference_collection = getattr(settings, "reference_collection", None)
    if reference_collection is not None:
        for obj in list(reference_collection.all_objects[:]):
            fixed.add(object_pointer(obj))

    return fixed


def target_object_pointers(scene, settings):
    if settings.target_collection is not None:
        candidates = collection_scene_objects(scene, settings.target_collection)
    else:
        candidates = scene_objects(scene)

    fixed = fixed_object_pointers(settings)
    targets = {object_pointer(obj) for obj in candidates if object_pointer(obj) not in fixed}

    # The guide is always a target, unless it is (invalidly) inside the fixed hierarchy.
    if settings.guide_object is not None:
        guide_ptr = object_pointer(settings.guide_object)
        if guide_ptr not in fixed:
            targets.add(guide_ptr)

    return targets


def parent_depth(obj):
    depth = 0
    seen = set()
    current = obj.parent
    while current is not None:
        ptr = object_pointer(current)
        if ptr in seen:
            break
        seen.add(ptr)
        depth += 1
        current = current.parent
    return depth


def _digest_update_array(digest, values):
    """Hash an array in deterministic little-endian byte order."""
    if sys.byteorder != 'little':
        values = array(values.typecode, values)
        values.byteswap()
    digest.update(values.tobytes())


def _foreach_get_array(collection, attribute, typecode, item_count):
    values = array(typecode, [0]) * int(item_count)
    collection.foreach_get(attribute, values)
    return values


def mesh_geometry_sentinel(obj):
    """Return a complete raw-Mesh fingerprint without evaluating modifiers.

    The v1.2.8 sentinel sampled only four vertices, which allowed edits to an
    unsampled vertex or to topology to survive Restore while the add-on claimed
    exact verification.  This implementation hashes the complete base mesh:
    every vertex coordinate, edge endpoint, loop vertex index and polygon loop
    span.  Shape-key coordinates are included as local geometry as well.

    ``foreach_get`` keeps the scan linear and avoids building a giant JSON/list
    representation of dense statues.
    """
    if obj is None or obj.type != 'MESH' or obj.data is None:
        return False, ''
    mesh = obj.data
    vertices = getattr(mesh, 'vertices', None)
    edges = getattr(mesh, 'edges', None)
    loops = getattr(mesh, 'loops', None)
    polygons = getattr(mesh, 'polygons', None)
    if vertices is None or edges is None or loops is None or polygons is None:
        return False, ''

    digest = hashlib.sha256()
    digest.update(b'T7SM_MESH_GEOMETRY_V2\0')

    def mark(label, count):
        digest.update(label.encode('ascii'))
        digest.update(b'\0')
        digest.update(str(int(count)).encode('ascii'))
        digest.update(b'\0')

    try:
        vertex_count = len(vertices)
        edge_count = len(edges)
        loop_count = len(loops)
        polygon_count = len(polygons)
        mark('vertices', vertex_count)
        mark('edges', edge_count)
        mark('loops', loop_count)
        mark('polygons', polygon_count)

        if vertex_count:
            _digest_update_array(
                digest,
                _foreach_get_array(vertices, 'co', 'f', vertex_count * 3),
            )
        if edge_count:
            _digest_update_array(
                digest,
                _foreach_get_array(edges, 'vertices', 'i', edge_count * 2),
            )
        if loop_count:
            _digest_update_array(
                digest,
                _foreach_get_array(loops, 'vertex_index', 'i', loop_count),
            )
        if polygon_count:
            _digest_update_array(
                digest,
                _foreach_get_array(polygons, 'loop_start', 'i', polygon_count),
            )
            _digest_update_array(
                digest,
                _foreach_get_array(polygons, 'loop_total', 'i', polygon_count),
            )

        shape_keys = getattr(mesh, 'shape_keys', None)
        key_blocks = getattr(shape_keys, 'key_blocks', None) if shape_keys is not None else None
        if key_blocks is None:
            mark('shape_keys', 0)
        else:
            mark('shape_keys', len(key_blocks))
            for key_block in key_blocks:
                name = str(getattr(key_block, 'name', '') or '')
                relative = getattr(key_block, 'relative_key', None)
                relative_name = str(getattr(relative, 'name', '') or '') if relative is not None else ''
                digest.update(name.encode('utf-8', errors='surrogatepass'))
                digest.update(b'\0')
                digest.update(relative_name.encode('utf-8', errors='surrogatepass'))
                digest.update(b'\0')
                key_data = getattr(key_block, 'data', None)
                if key_data is None:
                    return False, ''
                mark('shape_key_points', len(key_data))
                if len(key_data):
                    _digest_update_array(
                        digest,
                        _foreach_get_array(key_data, 'co', 'f', len(key_data) * 3),
                    )
    except Exception:
        return False, ''

    return True, digest.hexdigest()


# Explicit allowlist for object types whose transform can be restored without
# any local geometry fingerprint. Every other target type must have a supported
# geometry_sentinel(), otherwise Prepare fails closed.
NON_GEOMETRY_OBJECT_TYPES = {
    'EMPTY', 'LIGHT', 'CAMERA', 'SPEAKER', 'LIGHT_PROBE',
}

GEOMETRY_TYPES_REQUIRING_SENTINEL = {
    'MESH', 'CURVE', 'SURFACE', 'FONT', 'ARMATURE', 'LATTICE', 'META',
    'POINTCLOUD', 'CURVES', 'GREASEPENCIL', 'VOLUME',
}


def _rounded_triplet(value):
    return [round(float(value[0]), 8), round(float(value[1]), 8), round(float(value[2]), 8)]


def geometry_sentinel(obj):
    """Return (supported, kind, sha256) for transform-relevant local geometry."""
    if obj is None:
        return False, '', ''
    kind = str(getattr(obj, 'type', '') or '')
    data = getattr(obj, 'data', None)
    try:
        payload = {'type': kind}
        if kind == 'MESH':
            valid, digest = mesh_geometry_sentinel(obj)
            if not valid:
                return False, kind, ''
            return True, kind, digest
        elif kind in {'CURVE', 'SURFACE'}:
            if data is None or not hasattr(data, 'splines'):
                return False, kind, ''
            splines = []
            for spline in data.splines:
                entry = {'type': spline.type, 'cyclic': bool(getattr(spline, 'use_cyclic_u', False))}
                if spline.type == 'BEZIER':
                    entry['points'] = [
                        {
                            'co': _rounded_triplet(point.co),
                            'hl': _rounded_triplet(point.handle_left),
                            'hr': _rounded_triplet(point.handle_right),
                        }
                        for point in spline.bezier_points
                    ]
                else:
                    entry['points'] = [
                        [round(float(v), 8) for v in point.co]
                        for point in spline.points
                    ]
                splines.append(entry)
            payload['splines'] = splines
        elif kind == 'FONT':
            if data is None:
                return False, kind, ''
            fields = (
                'body', 'size', 'shear', 'offset', 'extrude', 'bevel_depth',
                'offset_x', 'offset_y', 'space_character', 'space_word',
                'space_line', 'small_caps_scale', 'align_x', 'align_y',
            )
            payload['font'] = {name: getattr(data, name, None) for name in fields}
        elif kind == 'ARMATURE':
            if data is None or not hasattr(data, 'bones'):
                return False, kind, ''
            payload['bones'] = [
                {
                    'name': bone.name,
                    'parent': bone.parent.name if bone.parent else '',
                    'head': _rounded_triplet(bone.head_local),
                    'tail': _rounded_triplet(bone.tail_local),
                    'roll': round(float(getattr(bone, 'roll', 0.0)), 8),
                    'connect': bool(getattr(bone, 'use_connect', False)),
                }
                for bone in data.bones
            ]
        elif kind == 'LATTICE':
            if data is None or not hasattr(data, 'points'):
                return False, kind, ''
            payload['points'] = [_rounded_triplet(point.co_deform) for point in data.points]
        elif kind == 'META':
            if data is None or not hasattr(data, 'elements'):
                return False, kind, ''
            payload['elements'] = [
                {
                    'co': _rounded_triplet(element.co),
                    'radius': round(float(element.radius), 8),
                    'stiffness': round(float(element.stiffness), 8),
                    'type': element.type,
                }
                for element in data.elements
            ]
        elif kind == 'POINTCLOUD':
            if data is None or not hasattr(data, 'attributes'):
                return False, kind, ''
            position = data.attributes.get('position')
            if position is None or not hasattr(position, 'data'):
                return False, kind, ''
            payload['points'] = [
                _rounded_triplet(item.vector)
                for item in position.data
            ]
        elif kind in NON_GEOMETRY_OBJECT_TYPES:
            payload['no_local_geometry'] = True
        else:
            return False, kind, ''
        digest = hashlib.sha256(canonical_json(payload).encode('utf-8')).hexdigest()
        return True, kind, digest
    except Exception:
        return False, kind, ''


def values_close(a, b, tolerance):
    if len(a) != len(b):
        return False
    return all(abs(float(x) - float(y)) <= tolerance for x, y in zip(a, b))


def matrix_is_identity(matrix, tolerance=IDENTITY_TOLERANCE):
    identity = Matrix.Identity(4)
    for row in range(4):
        for col in range(4):
            if abs(float(matrix[row][col]) - float(identity[row][col])) > tolerance:
                return False
    return True


def guide_delta_matrix(saved_guide_world, current_guide_world):
    """
    Full world-space delta that maps the guide's saved transform to its current
    transform. Applying the same matrix to every saved object makes the entire
    statue behave as if it were temporarily parented to the guide, without
    creating or changing any parent relationships.
    """
    try:
        saved_inverse = saved_guide_world.inverted()
    except Exception as exc:
        raise ValueError(
            "A transformação inicial do objeto-guia não pode ser invertida. "
            "Verifique se a escala do guia possui algum eixo igual a zero."
        ) from exc
    return current_guide_world @ saved_inverse




def _matrix_component_close(a, b, abs_tol=MATRIX_ABS_TOLERANCE, rel_tol=MATRIX_REL_TOLERANCE):
    a = float(a)
    b = float(b)
    return abs(a - b) <= abs_tol + rel_tol * max(1.0, abs(a), abs(b))


def matrices_close(a, b, abs_tol=MATRIX_ABS_TOLERANCE, rel_tol=MATRIX_REL_TOLERANCE):
    for row in range(4):
        for col in range(4):
            if not _matrix_component_close(a[row][col], b[row][col], abs_tol, rel_tol):
                return False
    return True


def _float32_ulp(value):
    """Return the spacing of IEEE-754 float32 around ``value``.

    Blender transform channels are stored as float32.  World matrices rebuilt
    through parent chains can therefore differ from ideal double-precision math
    by a few float32 ulps even when the stored pose is exactly the one Blender
    can represent.
    """
    value = abs(float(value))
    if value == 0.0:
        return 2.0 ** -149
    if value != value or value == float('inf'):
        return float('inf')
    _mantissa, exponent = frexp(value)
    unbiased = exponent - 1
    if unbiased < -126:
        return 2.0 ** -149
    return 2.0 ** (unbiased - 23)


def _matrix_float32_linear_component_tolerance(
    _actual,
    expected,
    row,
    col,
    *,
    ulps=8.0,
    abs_tol=MATRIX_LINEAR_APPLY_ABS_TOLERANCE,
):
    """Per-component budget for one element of the affine 3x3 block.

    N-39/N-40 showed that any budget derived from a *different* 3x3 element
    can let a large sibling certify a materially wrong smaller component.
    The mismatching readback must not widen its own allowance either.  Apply
    therefore gives each linear element only:

    - a small absolute allowance covering the legitimate cross-component
      parent-chain roundoff measured in Blender 5.0.0 for N-36; and
    - a float32 ULP allowance derived from this expected component itself.

    No sibling component and no divergent actual value participates in the
    tolerance calculation.
    """
    scale = max(1.0, abs(float(expected[row][col])))
    return max(float(abs_tol), float(ulps) * _float32_ulp(scale))


def _matrix_float32_translation_tolerance(a, b, row, ulps=4.0, abs_tol=MATRIX_ABS_TOLERANCE):
    """ULP budget for one translation axis, isolated from all other axes."""
    scale = max(1.0, abs(float(a[row][3])), abs(float(b[row][3])))
    return max(float(abs_tol), float(ulps) * _float32_ulp(scale))


def _matrix_float32_expected_translation_tolerance(
    expected,
    row,
    *,
    ulps=4.0,
    abs_tol=MATRIX_ABS_TOLERANCE,
):
    """Expected-only float32 budget for one matrix_basis translation channel.

    N-42 showed that a world-space child translation can inherit rounding from
    a different, much larger world axis through a rotated parent.  Apply no
    longer uses reconstructed world components as its precision gate.  In the
    matrix_basis space written by Blender, each translation channel is stored
    directly, so its representable budget can be derived from that expected
    channel alone.  A divergent readback is never allowed to widen its budget.
    """
    scale = max(1.0, abs(float(expected[row][3])))
    return max(float(abs_tol), float(ulps) * _float32_ulp(scale))


def _matrix_float32_channel_component_tolerance(
    actual,
    expected,
    row,
    col,
    *,
    linear_ulps=8.0,
    translation_ulps=4.0,
    abs_tol=MATRIX_ABS_TOLERANCE,
):
    """Tolerance for the matrix_basis value actually written by Apply.

    Unlike the historical world-space verifier, this budget is intentionally
    local to the exact expected channel/basis component.  Parent rotation, a
    large sibling world axis, or a divergent actual value cannot enlarge it.
    """
    if row < 3 and col < 3:
        return _matrix_float32_linear_component_tolerance(
            actual,
            expected,
            row,
            col,
            ulps=linear_ulps,
            abs_tol=abs_tol,
        )
    if row < 3 and col == 3:
        return _matrix_float32_expected_translation_tolerance(
            expected, row, ulps=translation_ulps, abs_tol=abs_tol
        )
    return float(abs_tol)



def _expected_scalar_tolerance(expected, *, ulps=8.0, abs_tol=MATRIX_ABS_TOLERANCE):
    """Expected-only float32 budget for one directly stored transform channel."""
    value = float(expected)
    if not isfinite(value):
        return 0.0
    scale = max(1.0, abs(value))
    return max(float(abs_tol), float(ulps) * _float32_ulp(scale))


def capture_transform_channel_state(obj):
    """Capture the canonical transform channels Blender stored after matrix_basis assignment.

    Blender does not store ``matrix_basis`` as 16 independent floats.  It stores
    transform channels (location/rotation/scale plus deltas) in float32 and
    reconstructs matrix_basis from them.  N-45 showed that comparing that
    reconstructed matrix against the requested double-precision basis can reject
    a correct pose at large scale or near Euler gimbal configurations.

    Apply v1.2.19 therefore freezes the *actual representable channel state*
    immediately after the synchronous matrix_basis write, then verifies that the
    same channels remain unchanged after all target writes and the ViewLayer
    update.  A later mutation/fault cannot redefine its own expected state.
    """
    mode = str(obj.rotation_mode)
    if mode == 'QUATERNION':
        rotation_kind = 'rotation_quaternion'
        rotation = tuple(float(v) for v in obj.rotation_quaternion)
        delta_rotation_kind = 'delta_rotation_quaternion'
        delta_rotation = tuple(float(v) for v in obj.delta_rotation_quaternion)
    elif mode == 'AXIS_ANGLE':
        rotation_kind = 'rotation_axis_angle'
        rotation = tuple(float(v) for v in obj.rotation_axis_angle)
        # Blender has no delta axis-angle channel; non-quaternion delta rotation
        # is represented by delta_rotation_euler.
        delta_rotation_kind = 'delta_rotation_euler'
        delta_rotation = tuple(float(v) for v in obj.delta_rotation_euler)
    else:
        rotation_kind = 'rotation_euler'
        rotation = tuple(float(v) for v in obj.rotation_euler)
        delta_rotation_kind = 'delta_rotation_euler'
        delta_rotation = tuple(float(v) for v in obj.delta_rotation_euler)

    return {
        'rotation_mode': mode,
        'location': tuple(float(v) for v in obj.location),
        'rotation_kind': rotation_kind,
        'rotation': rotation,
        'scale': tuple(float(v) for v in obj.scale),
        'delta_location': tuple(float(v) for v in obj.delta_location),
        'delta_rotation_kind': delta_rotation_kind,
        'delta_rotation': delta_rotation,
        'delta_scale': tuple(float(v) for v in obj.delta_scale),
    }


def _channel_sequence_mismatch(actual, expected, *, ulps=8.0, abs_tol=MATRIX_ABS_TOLERANCE):
    """Return ``(index, diff, tolerance)`` for the worst failing raw channel."""
    if len(actual) != len(expected):
        return -1, float('inf'), 0.0
    worst = None
    for index, (av, ev) in enumerate(zip(actual, expected)):
        av = float(av)
        ev = float(ev)
        if not isfinite(av) or not isfinite(ev):
            return index, float('inf'), 0.0
        tolerance = _expected_scalar_tolerance(ev, ulps=ulps, abs_tol=abs_tol)
        diff = abs(av - ev)
        if diff > tolerance:
            ratio = diff / tolerance if tolerance > 0.0 else float('inf')
            if worst is None or ratio > worst[0]:
                worst = (ratio, index, diff, tolerance)
    if worst is None:
        return None
    return worst[1], worst[2], worst[3]


def verify_applied_transform_channels(expected_channel_states, tolerance=None):
    """Strictly verify raw transform channels before certifying world readbacks.

    ``expected_channel_states`` contains states captured immediately after each
    successful matrix_basis write.  This avoids N-45 matrix recomposition noise
    while still detecting N-38/N-39/N-40 style post-write corruption, including
    mutations injected between the setter and this verification step.
    """
    mismatches = []
    for obj, expected in expected_channel_states:
        if obj is None:
            mismatches.append('objeto ausente ao verificar canais aplicados')
            continue
        try:
            actual = capture_transform_channel_state(obj)
        except Exception as exc:
            mismatches.append(f"{getattr(obj, 'name', '<objeto>')}: canais indisponíveis ({exc})")
            continue

        if actual['rotation_mode'] != expected['rotation_mode']:
            mismatches.append(
                f"{obj.name}: rotation_mode mudou de {expected['rotation_mode']} para {actual['rotation_mode']}"
            )
            continue
        if actual['rotation_kind'] != expected['rotation_kind'] or actual['delta_rotation_kind'] != expected['delta_rotation_kind']:
            mismatches.append(f"{obj.name}: representação de rotação mudou durante Apply")
            continue

        checks = (
            ('location', actual['location'], expected['location'], 0.5),
            (expected['rotation_kind'], actual['rotation'], expected['rotation'], 0.5),
            ('scale', actual['scale'], expected['scale'], 0.5),
            ('delta_location', actual['delta_location'], expected['delta_location'], 0.5),
            (expected['delta_rotation_kind'], actual['delta_rotation'], expected['delta_rotation'], 0.5),
            ('delta_scale', actual['delta_scale'], expected['delta_scale'], 0.5),
        )
        for label, current, saved, ulps in checks:
            if tolerance is None:
                mismatch = _channel_sequence_mismatch(current, saved, ulps=ulps)
            else:
                mismatch = None
                for index, (av, ev) in enumerate(zip(current, saved)):
                    diff = abs(float(av) - float(ev))
                    if not isfinite(diff) or diff > float(tolerance):
                        mismatch = (index, diff, float(tolerance))
                        break
            if mismatch is not None:
                index, diff, component_tol = mismatch
                mismatches.append(
                    f"{obj.name}: canal {label}[{index}] mudou após escrita "
                    f"(diff={diff:.3e}, tol={component_tol:.3e})"
                )
                break
    return mismatches


def _world_sanity_vector_norm(values):
    """Euclidean norm for a finite 3-vector used by the secondary world gate."""
    return sum(float(value) ** 2 for value in values) ** 0.5


def _world_sanity_translation_tolerance(expected):
    """Cross-axis translation budget derived only from the expected world.

    N-42 proved that a large translated axis can legitimately leak float32
    roundoff into another world axis through a rotated parent.  Four ULPs of the
    largest expected coordinate covers the measured Blender 5.0.0 propagation
    through G=100000, while N-47 values such as 100000->100000.4 and
    (1e6,0,0)->(1e6,3.5,0) remain far outside the accepted vector error.
    """
    scale = max(
        1.0,
        abs(float(expected[0][3])),
        abs(float(expected[1][3])),
        abs(float(expected[2][3])),
    )
    return max(
        WORLD_SANITY_ABS_TOLERANCE,
        WORLD_SANITY_TRANSLATION_ULPS * _float32_ulp(scale),
    )


def _world_sanity_linear_column_tolerance(expected, col):
    """Total vector-error budget for one expected world linear column.

    N-45 requires some within-column coupling because Blender reconstructs a
    rotated/scaled basis from float32 transform channels.  This total norm budget
    remains expected-only and bounds the aggregate recomposition error.  It is
    *not* sufficient by itself: N-48 proved that a huge component can otherwise
    hide a material error in a tiny sibling of the same column.
    """
    column_norm = _world_sanity_vector_norm(expected[row][col] for row in range(3))
    return max(
        WORLD_SANITY_LINEAR_ABS_TOLERANCE,
        WORLD_SANITY_LINEAR_REL_TOLERANCE * max(1.0, column_norm),
    )


def _world_sanity_linear_length_tolerance(expected, col):
    """Strict expected-only tolerance for one world-column length.

    N-53 needs a wider vector envelope for harmless direction/recomposition noise
    propagated by anisotropic parent chains. N-51, however, is a true scale change:
    it changes the column length itself. Keep this scalar length budget at 1e-5 so
    a unit +2e-5 drift cannot hide inside the wider vector allowance.
    """
    column_norm = _world_sanity_vector_norm(expected[row][col] for row in range(3))
    if not isfinite(column_norm):
        return 0.0
    return max(
        WORLD_SANITY_LINEAR_LENGTH_ABS_TOLERANCE,
        WORLD_SANITY_LINEAR_LENGTH_REL_TOLERANCE * max(1.0, column_norm),
    )


def _world_sanity_linear_component_tolerance(expected, row, col):
    """Expected-only cap for one linear world component.

    This second limit closes N-48.  A large sibling in the same column cannot
    enlarge the allowance for this component: only the component's own expected
    magnitude participates in the ULP term.  The absolute floor is empirical,
    sized from Blender 5.0.0 p32 roundtrip evidence through scale 1000.
    """
    value = float(expected[row][col])
    if not isfinite(value):
        return 0.0
    scale = max(1.0, abs(value))
    return max(
        WORLD_SANITY_LINEAR_COMPONENT_ABS_TOLERANCE,
        WORLD_SANITY_LINEAR_COMPONENT_ULPS * _float32_ulp(scale),
    )


def verify_applied_world_material_sanity(settings, transform_delta):
    """Reject a materially wrong reconstructed world without re-opening N-42/N-45.

    This remains a *secondary* gate after raw RNA channels are proven stable.
    Translation is compared as one 3-vector with a four-ULP expected-world
    budget, allowing legitimate rotated-parent cross-axis propagation.  Each
    linear column is compared as one vector with a small relative expected-only
    budget, allowing legitimate within-column TRS recomposition noise without
    allowing a huge component to lend an unbounded absolute allowance to a
    smaller sibling.  The affine bottom row stays on the strict absolute floor.
    """
    mismatches = []
    for state in settings.object_states:
        if not state.is_target or state.object_ref is None:
            continue
        obj = state.object_ref
        expected = transform_delta @ flat_to_matrix(state.matrix_world)
        try:
            actual = channel_world_matrix(obj)
        except Exception as exc:
            mismatches.append(f"{obj.name}: world calculado indisponível ({exc})")
            continue

        finite = True
        for row in range(4):
            for col in range(4):
                if not isfinite(float(actual[row][col])) or not isfinite(float(expected[row][col])):
                    finite = False
                    break
            if not finite:
                break
        if not finite:
            mismatches.append(f"{obj.name}: world calculado contém NaN/Inf")
            continue

        # Translation is a coupled world vector under rotated parenting.  Judge
        # total translation error, but derive the allowance only from expected.
        translation_diff = _world_sanity_vector_norm(
            float(actual[row][3]) - float(expected[row][3]) for row in range(3)
        )
        translation_tol = _world_sanity_translation_tolerance(expected)
        if translation_diff > translation_tol:
            mismatches.append(
                f"{obj.name}: tradução world materialmente divergente "
                f"(norma_diff={translation_diff:.3e}, tol={translation_tol:.3e}, "
                f"razão={translation_diff / translation_tol:.2f})"
            )
            continue

        # Linear terms satisfy three independent questions:
        # 1) total vector error may use the wider N-53 hierarchy-safe envelope;
        # 2) column length/scale stays on the strict N-51 1e-5 envelope;
        # 3) each component stays capped independently to prevent N-48 masking.
        linear_failure = None
        for col in range(3):
            expected_column = tuple(float(expected[row][col]) for row in range(3))
            actual_column = tuple(float(actual[row][col]) for row in range(3))
            column_diff = _world_sanity_vector_norm(
                actual_column[row] - expected_column[row] for row in range(3)
            )
            column_tol = _world_sanity_linear_column_tolerance(expected, col)
            if column_diff > column_tol:
                ratio = column_diff / column_tol if column_tol > 0.0 else float('inf')
                candidate = (ratio, 'column', col, None, column_diff, column_tol)
                if linear_failure is None or ratio > linear_failure[0]:
                    linear_failure = candidate

            expected_length = _world_sanity_vector_norm(expected_column)
            actual_length = _world_sanity_vector_norm(actual_column)
            length_diff = abs(actual_length - expected_length)
            length_tol = _world_sanity_linear_length_tolerance(expected, col)
            if length_diff > length_tol:
                ratio = length_diff / length_tol if length_tol > 0.0 else float('inf')
                candidate = (ratio, 'length', col, None, length_diff, length_tol)
                if linear_failure is None or ratio > linear_failure[0]:
                    linear_failure = candidate

            for row in range(3):
                diff = abs(actual_column[row] - expected_column[row])
                component_tol = _world_sanity_linear_component_tolerance(expected, row, col)
                if diff > component_tol:
                    ratio = diff / component_tol if component_tol > 0.0 else float('inf')
                    candidate = (ratio, 'component', col, row, diff, component_tol)
                    if linear_failure is None or ratio > linear_failure[0]:
                        linear_failure = candidate

        if linear_failure is not None:
            ratio, kind, col, row, diff, tolerance = linear_failure
            if kind == 'component':
                mismatches.append(
                    f"{obj.name}: componente world [{row}][{col}] materialmente divergente "
                    f"(diff={diff:.3e}, tol={tolerance:.3e}, razão={ratio:.2f})"
                )
            elif kind == 'length':
                mismatches.append(
                    f"{obj.name}: comprimento da coluna world {col} materialmente divergente "
                    f"(diff={diff:.3e}, tol={tolerance:.3e}, razão={ratio:.2f})"
                )
            else:
                mismatches.append(
                    f"{obj.name}: coluna world {col} materialmente divergente "
                    f"(norma_diff={diff:.3e}, tol={tolerance:.3e}, razão={ratio:.2f})"
                )
            continue

        bottom_failure = None
        for col in range(4):
            diff = abs(float(actual[3][col]) - float(expected[3][col]))
            if diff > MATRIX_ABS_TOLERANCE:
                ratio = diff / MATRIX_ABS_TOLERANCE
                if bottom_failure is None or ratio > bottom_failure[0]:
                    bottom_failure = (ratio, col, diff)
        if bottom_failure is not None:
            ratio, col, diff = bottom_failure
            mismatches.append(
                f"{obj.name}: bottom row world divergente em [3][{col}] "
                f"(diff={diff:.3e}, tol={MATRIX_ABS_TOLERANCE:.3e}, razão={ratio:.2f})"
            )
    return mismatches


def matrices_close_channel_roundtrip(
    actual,
    expected,
    *,
    linear_ulps=8.0,
    translation_ulps=4.0,
    abs_tol=MATRIX_ABS_TOLERANCE,
):
    """Verify the representable matrix_basis written by Apply.

    Historical/diagnostic matrix_basis roundtrip comparator retained for audit
    vectors.  Since v1.2.16 the blocking Apply precision gate is raw RNA channel
    stability; v1.2.19 keeps this helper out of the success/failure path.
    """
    for row in range(4):
        for col in range(4):
            av = float(actual[row][col])
            ev = float(expected[row][col])
            if not isfinite(av) or not isfinite(ev):
                return False
            tolerance = _matrix_float32_channel_component_tolerance(
                actual,
                expected,
                row,
                col,
                linear_ulps=linear_ulps,
                translation_ulps=translation_ulps,
                abs_tol=abs_tol,
            )
            if abs(av - ev) > tolerance:
                return False
    return True


def _matrix_channel_max_ratio_detail(
    actual,
    expected,
    *,
    linear_ulps=8.0,
    translation_ulps=4.0,
    abs_tol=MATRIX_ABS_TOLERANCE,
):
    """Return the channel component with the largest diff/tolerance ratio."""
    best = (-1.0, 0.0, float(abs_tol), 0, 0)
    for row in range(4):
        for col in range(4):
            av = float(actual[row][col])
            ev = float(expected[row][col])
            if not isfinite(av) or not isfinite(ev):
                return float('inf'), float('inf'), 0.0, row, col
            tolerance = _matrix_float32_channel_component_tolerance(
                actual,
                expected,
                row,
                col,
                linear_ulps=linear_ulps,
                translation_ulps=translation_ulps,
                abs_tol=abs_tol,
            )
            diff = abs(av - ev)
            ratio = diff / tolerance if tolerance > 0.0 else float('inf')
            if ratio > best[0]:
                best = (ratio, diff, tolerance, row, col)
    return best


def _matrix_float32_component_tolerance(
    a,
    b,
    row,
    col,
    *,
    linear_ulps=8.0,
    linear_abs_tol=MATRIX_LINEAR_APPLY_ABS_TOLERANCE,
    translation_ulps=4.0,
    abs_tol=MATRIX_ABS_TOLERANCE,
):
    if row < 3 and col < 3:
        return _matrix_float32_linear_component_tolerance(
            a,
            b,
            row,
            col,
            ulps=linear_ulps,
            abs_tol=linear_abs_tol,
        )
    if row < 3 and col == 3:
        return _matrix_float32_translation_tolerance(
            a, b, row, ulps=translation_ulps, abs_tol=abs_tol
        )
    # The affine bottom row should stay (0, 0, 0, 1).  It is not allowed to
    # inherit tolerance from either a large translation or a large scale.
    return float(abs_tol)


def _matrix_float32_tolerance_summary(
    a,
    b,
    *,
    linear_ulps=8.0,
    linear_abs_tol=MATRIX_LINEAR_APPLY_ABS_TOLERANCE,
    translation_ulps=4.0,
    abs_tol=MATRIX_ABS_TOLERANCE,
):
    linear_components = tuple(
        _matrix_float32_linear_component_tolerance(
            a,
            b,
            row,
            col,
            ulps=linear_ulps,
            abs_tol=linear_abs_tol,
        )
        for row in range(3)
        for col in range(3)
    )
    translations = tuple(
        _matrix_float32_translation_tolerance(a, b, row, ulps=translation_ulps, abs_tol=abs_tol)
        for row in range(3)
    )
    return max(linear_components), translations, float(abs_tol)


def _matrix_float32_max_diff_detail(
    a,
    b,
    *,
    linear_ulps=8.0,
    linear_abs_tol=MATRIX_LINEAR_APPLY_ABS_TOLERANCE,
    translation_ulps=4.0,
    abs_tol=MATRIX_ABS_TOLERANCE,
):
    """Return max absolute diff and the tolerance of that exact component."""
    best = (-1.0, float(abs_tol), 0, 0)
    for row in range(4):
        for col in range(4):
            av = float(a[row][col])
            bv = float(b[row][col])
            if not isfinite(av) or not isfinite(bv):
                return float('inf'), 0.0, row, col
            diff = abs(av - bv)
            if diff > best[0]:
                tolerance = _matrix_float32_component_tolerance(
                    a,
                    b,
                    row,
                    col,
                    linear_ulps=linear_ulps,
                    linear_abs_tol=linear_abs_tol,
                    translation_ulps=translation_ulps,
                    abs_tol=abs_tol,
                )
                best = (diff, tolerance, row, col)
    return best


def matrices_close_float32_roundtrip(
    a,
    b,
    linear_ulps=8.0,
    translation_ulps=4.0,
    linear_abs_tol=MATRIX_LINEAR_APPLY_ABS_TOLERANCE,
):
    """Compare ideal D@M0 to channel readback with bounded float32 budgets.

    Every 3x3 element has an independent budget based on its own magnitude,
    plus the small fixed allowance required by the N-36 Blender 5.0.0 runtime
    evidence.  No other matrix element can widen that budget.  Translation is
    isolated per axis and the affine bottom row stays on the absolute floor.
    This closes N-38, N-39 and the large/unequal-linear N-40 masking class.
    """
    for row in range(4):
        for col in range(4):
            tolerance = _matrix_float32_component_tolerance(
                a,
                b,
                row,
                col,
                linear_ulps=linear_ulps,
                linear_abs_tol=linear_abs_tol,
                translation_ulps=translation_ulps,
            )
            av = float(a[row][col])
            bv = float(b[row][col])
            if not isfinite(av) or not isfinite(bv):
                return False
            if abs(av - bv) > tolerance:
                return False
    return True


def matrices_close_applied_readback(a, b):
    """Compare Finalize against the exact pose captured after Apply.

    Both matrices are Blender-representable readbacks, so Finalize uses a
    component-local half-ULP budget plus the original absolute floor.  The
    larger Apply-only N-36 absolute allowance is intentionally not used here.
    """
    for row in range(4):
        for col in range(4):
            tolerance = _matrix_float32_component_tolerance(
                a,
                b,
                row,
                col,
                linear_ulps=0.5,
                linear_abs_tol=MATRIX_ABS_TOLERANCE,
                translation_ulps=0.5,
            )
            av = float(a[row][col])
            bv = float(b[row][col])
            if not isfinite(av) or not isfinite(bv):
                return False
            if abs(av - bv) > tolerance:
                return False
    return True


def channel_world_matrix(obj, _seen=None):
    """World matrix from transform channels + parent chain, without depsgraph matrix_world.

    Blender can leave ``matrix_world`` stale for objects in collections excluded
    from the View Layer or disabled in viewports.  This helper deliberately
    follows the RNA transform channels instead.  OBJECT and BONE parenting are
    the two parenting modes supported by this add-on's production workflow.
    Unsupported parenting fails closed instead of silently using stale data.
    """
    if obj is None:
        raise ValueError('objeto ausente ao calcular matriz mundial')
    seen = set() if _seen is None else _seen
    ptr = object_pointer(obj)
    if ptr in seen:
        raise ValueError(f"ciclo de parenting detectado em '{obj.name}'")
    seen.add(ptr)
    try:
        local = obj.matrix_basis.copy()
        parent = obj.parent
        if parent is None:
            return local

        parent_world = channel_world_matrix(parent, seen)
        parent_type = getattr(obj, 'parent_type', 'OBJECT')
        if parent_type == 'OBJECT':
            return parent_world @ obj.matrix_parent_inverse @ local
        if parent_type == 'BONE':
            bone_name = getattr(obj, 'parent_bone', '')
            pose = getattr(parent, 'pose', None)
            bone = pose.bones.get(bone_name) if pose is not None and bone_name else None
            if bone is None:
                raise ValueError(f"bone parent '{bone_name}' ausente para '{obj.name}'")
            bone_tail = Matrix.Translation((0.0, float(bone.length), 0.0))
            return parent_world @ bone.matrix @ bone_tail @ obj.matrix_parent_inverse @ local
        raise ValueError(
            f"parent_type '{parent_type}' de '{obj.name}' não é suportado com segurança; "
            "use OBJECT ou BONE"
        )
    finally:
        seen.discard(ptr)


def channel_parent_prefix(obj):
    """Matrix that maps obj.matrix_basis into world space."""
    parent = obj.parent
    if parent is None:
        return Matrix.Identity(4)
    parent_world = channel_world_matrix(parent)
    parent_type = getattr(obj, 'parent_type', 'OBJECT')
    if parent_type == 'OBJECT':
        return parent_world @ obj.matrix_parent_inverse
    if parent_type == 'BONE':
        bone_name = getattr(obj, 'parent_bone', '')
        pose = getattr(parent, 'pose', None)
        bone = pose.bones.get(bone_name) if pose is not None and bone_name else None
        if bone is None:
            raise ValueError(f"bone parent '{bone_name}' ausente para '{obj.name}'")
        bone_tail = Matrix.Translation((0.0, float(bone.length), 0.0))
        return parent_world @ bone.matrix @ bone_tail @ obj.matrix_parent_inverse
    raise ValueError(
        f"parent_type '{parent_type}' de '{obj.name}' não é suportado com segurança; use OBJECT ou BONE"
    )


_EULER_ORDER_TUPLES = {
    'XYZ': (0, 0),
    'XZY': (0, 1),
    'YZX': (1, 0),
    'YXZ': (1, 1),
    'ZXY': (2, 0),
    'ZYX': (2, 1),
}
_EULER_NEXT_AXIS = (1, 2, 0, 1)
_AXIS_INDEX = {'X': 0, 'Y': 1, 'Z': 2}


def _double_mat3_mul(a, b):
    return tuple(
        tuple(sum(float(a[row][k]) * float(b[k][col]) for k in range(3)) for col in range(3))
        for row in range(3)
    )


def _double_mat3_transpose(matrix):
    return tuple(tuple(float(matrix[col][row]) for col in range(3)) for row in range(3))


def _double_mat3_det(matrix):
    a = matrix
    return (
        float(a[0][0]) * (float(a[1][1]) * float(a[2][2]) - float(a[1][2]) * float(a[2][1]))
        - float(a[0][1]) * (float(a[1][0]) * float(a[2][2]) - float(a[1][2]) * float(a[2][0]))
        + float(a[0][2]) * (float(a[1][0]) * float(a[2][1]) - float(a[1][1]) * float(a[2][0]))
    )


def _double_mat3_inverse(matrix):
    """Inverse of a finite 3x3 matrix in Python double precision."""
    a, b, c = (float(v) for v in matrix[0])
    d, e, f = (float(v) for v in matrix[1])
    g, h, i = (float(v) for v in matrix[2])
    det = _double_mat3_det(matrix)
    if not isfinite(det) or abs(det) <= 1.0e-18:
        return None
    inv_det = 1.0 / det
    return (
        ((e * i - f * h) * inv_det, (c * h - b * i) * inv_det, (b * f - c * e) * inv_det),
        ((f * g - d * i) * inv_det, (a * i - c * g) * inv_det, (c * d - a * f) * inv_det),
        ((d * h - e * g) * inv_det, (b * g - a * h) * inv_det, (a * e - b * d) * inv_det),
    )


def _double_nearest_proper_rotation(matrix):
    """Project a near-rotation onto the nearest proper orthogonal matrix.

    Newton's polar iteration X <- 0.5 * (X + X^-T) is stable for the near-
    orthogonal matrices admitted by the existing shear guard. It removes the
    ~float32 parent-chain non-orthogonality that caused N-54 without inventing
    a new rotation for materially sheared/singular inputs.
    """
    current = tuple(tuple(float(matrix[row][col]) for col in range(3)) for row in range(3))
    if any(not isfinite(value) for row in current for value in row):
        return None
    for _ in range(8):
        inverse = _double_mat3_inverse(current)
        if inverse is None:
            return None
        inverse_transpose = _double_mat3_transpose(inverse)
        updated = tuple(
            tuple(0.5 * (current[row][col] + inverse_transpose[row][col]) for col in range(3))
            for row in range(3)
        )
        delta = max(
            abs(updated[row][col] - current[row][col])
            for row in range(3)
            for col in range(3)
        )
        current = updated
        if delta <= 1.0e-15:
            break
    determinant = _double_mat3_det(current)
    if not isfinite(determinant) or determinant <= 0.0:
        return None
    orthogonality = _double_mat3_mul(_double_mat3_transpose(current), current)
    residual = max(
        abs(float(orthogonality[row][col]) - (1.0 if row == col else 0.0))
        for row in range(3)
        for col in range(3)
    )
    if not isfinite(residual) or residual > 1.0e-10:
        return None
    return current


def _double_euler_to_mat3(euler_xyz, order):
    """Blender-compatible Tait-Bryan Euler -> matrix using Python doubles."""
    if order not in _EULER_ORDER_TUPLES:
        raise ValueError(f"rotation_mode Euler não suportado: {order}")
    firstaxis, parity = _EULER_ORDER_TUPLES[order]
    i = firstaxis
    j = _EULER_NEXT_AXIS[i + parity]
    k = _EULER_NEXT_AXIS[i - parity + 1]
    angles = [float(euler_xyz[_AXIS_INDEX[axis]]) for axis in order]
    ai, aj, ak = angles
    if parity:
        ai, aj, ak = -ai, -aj, -ak
    si, sj, sk = sin(ai), sin(aj), sin(ak)
    ci, cj, ck = cos(ai), cos(aj), cos(ak)
    cc, cs = ci * ck, ci * sk
    sc, ss = si * ck, si * sk
    matrix = [[0.0] * 3 for _ in range(3)]
    matrix[i][i] = cj * ck
    matrix[i][j] = sj * sc - cs
    matrix[i][k] = sj * cc + ss
    matrix[j][i] = cj * sk
    matrix[j][j] = sj * ss + cc
    matrix[j][k] = sj * cs - sc
    matrix[k][i] = -sj
    matrix[k][j] = cj * si
    matrix[k][k] = cj * ci
    return tuple(tuple(row) for row in matrix)


def _double_mat3_to_euler_sequence(matrix, order):
    """Return Euler angles in *order sequence* using double-precision math.

    This is the non-repeating Shoemake/Tait-Bryan decomposition. For XYZ it is
    exactly Rz @ Ry @ Rx, matching Blender's Euler convention and the independent
    p42 control used to characterize N-50.
    """
    if order not in _EULER_ORDER_TUPLES:
        raise ValueError(f"rotation_mode Euler não suportado: {order}")
    firstaxis, parity = _EULER_ORDER_TUPLES[order]
    i = firstaxis
    j = _EULER_NEXT_AXIS[i + parity]
    k = _EULER_NEXT_AXIS[i - parity + 1]
    cy = sqrt(float(matrix[i][i]) ** 2 + float(matrix[j][i]) ** 2)
    if cy > EULER_SINGULAR_THRESHOLD:
        ax = atan2(float(matrix[k][j]), float(matrix[k][k]))
        ay = atan2(-float(matrix[k][i]), cy)
        az = atan2(float(matrix[j][i]), float(matrix[i][i]))
    else:
        ax = atan2(-float(matrix[j][k]), float(matrix[j][j]))
        ay = atan2(-float(matrix[k][i]), cy)
        az = 0.0
    if parity:
        ax, ay, az = -ax, -ay, -az
    return (ax, ay, az)


def _wrap_angle_near(value, reference):
    two_pi = 2.0 * pi
    return float(value) + round((float(reference) - float(value)) / two_pi) * two_pi


def _double_mat3_to_compatible_euler(matrix, order, current_xyz):
    """Double-precision matrix->Euler, choosing the equivalent branch nearest current."""
    sequence = _double_mat3_to_euler_sequence(matrix, order)
    # Every non-repeating Euler solution has the companion branch
    # (a+pi, pi-b, c+pi). Try both and choose the representation closest to the
    # current channels, mirroring Blender's use_compat intent without its
    # float32 matrix->Euler decomposition.
    sequence_candidates = (
        sequence,
        (sequence[0] + pi, pi - sequence[1], sequence[2] + pi),
    )
    evaluated = []
    for candidate_sequence in sequence_candidates:
        xyz = [0.0, 0.0, 0.0]
        for axis, value in zip(order, candidate_sequence):
            xyz[_AXIS_INDEX[axis]] = float(value)
        xyz = tuple(_wrap_angle_near(xyz[index], current_xyz[index]) for index in range(3))
        rebuilt = _double_euler_to_mat3(xyz, order)
        max_error = max(
            abs(float(rebuilt[row][col]) - float(matrix[row][col]))
            for row in range(3)
            for col in range(3)
        )
        distance = sum((float(xyz[index]) - float(current_xyz[index])) ** 2 for index in range(3))
        evaluated.append((max_error, distance, xyz))

    # N-52: the two mathematically equivalent Tait-Bryan branches frequently
    # differ in reconstruction error only at ~1e-16. Such noise must not outrank
    # channel continuity. Treat errors within a tight double-precision window as
    # equivalent, then choose the representation nearest the current channels.
    min_error = min(item[0] for item in evaluated)
    equivalent = [
        item for item in evaluated
        if item[0] <= min_error + EULER_BRANCH_ERROR_EQUIVALENCE
    ]
    return min(equivalent, key=lambda item: (item[1], item[0]))[2]


def _requested_basis_rotation_from_setter_channels(obj, local):
    """Recover requested total rotation using Blender's own signed scale result.

    ``obj.matrix_basis = local`` already reproduces Blender's exact location,
    signed-scale and delta factoring semantics. N-50 is specifically the loss in
    the float32 matrix->Euler conversion. Use the signed total scales that the
    setter chose, but recompute only the Euler rotation from the original
    requested basis in Python double precision.
    """
    total_scale = tuple(float(obj.scale[index]) * float(obj.delta_scale[index]) for index in range(3))
    if any(not isfinite(value) or abs(value) <= ZERO_DELTA_TOLERANCE for value in total_scale):
        return None

    columns = []
    for col in range(3):
        vector = [float(local[row][col]) / total_scale[col] for row in range(3)]
        length = sqrt(sum(value * value for value in vector))
        if not isfinite(length) or length <= ZERO_DELTA_TOLERANCE:
            return None
        columns.append(tuple(value / length for value in vector))

    # Refuse to reinterpret genuine shear. The historical matrix_basis setter
    # remains in place in that case, so existing N-46 fail-closed behavior is
    # preserved instead of inventing a new decomposition.
    max_dot = max(
        abs(sum(columns[a][row] * columns[b][row] for row in range(3)))
        for a, b in ((0, 1), (0, 2), (1, 2))
    )
    if max_dot > 1.0e-4:
        return None

    rotation = tuple(tuple(columns[col][row] for col in range(3)) for row in range(3))
    if _double_mat3_det(rotation) <= 0.0:
        return None
    # N-54: normalized columns can still carry ~1e-7 non-orthogonality from
    # float32 parent-prefix products. Near gimbal that tiny defect is amplified
    # by matrix->Euler decomposition. Project to the nearest proper rotation first.
    return _double_nearest_proper_rotation(rotation)


def _refine_euler_after_matrix_basis_write(obj, requested_local, continuity_reference=None):
    """Replace Blender's lossy float32 matrix->Euler result with a double one.

    Blender 5.0.0's matrix_basis setter is retained first so location, signed
    scale and delta transforms keep Blender's native semantics. For Euler modes
    only, we then recover the requested total rotation, remove the existing
    delta rotation (delta @ base is Blender's order), and write a compatible
    base Euler computed in Python double precision. When supplied,
    ``continuity_reference`` is the pre-write Euler channel state, so branch
    continuity is measured against what the user actually had before Blender's
    matrix setter runs. Quaternion/Axis-Angle modes keep the proven historical
    setter path because N-50 is Euler-specific.
    """
    order = str(obj.rotation_mode)
    if order not in _EULER_ORDER_TUPLES:
        return False
    total_rotation = _requested_basis_rotation_from_setter_channels(obj, requested_local)
    if total_rotation is None:
        return False
    delta_rotation = _double_euler_to_mat3(tuple(float(v) for v in obj.delta_rotation_euler), order)
    base_rotation = _double_mat3_mul(_double_mat3_transpose(delta_rotation), total_rotation)
    if continuity_reference is None:
        current = tuple(float(v) for v in obj.rotation_euler)
    else:
        current = tuple(float(v) for v in continuity_reference)
    refined = _double_mat3_to_compatible_euler(base_rotation, order, current)
    if any(not isfinite(value) for value in refined):
        return False
    obj.rotation_euler = refined
    return True


def set_channel_world_matrix(obj, desired_world):
    """Set desired world transform and refine Euler decomposition for N-50/N-52.

    Blender's matrix_basis setter remains the authority for location, signed
    scale and delta factoring. In Euler modes, capture the user's pre-write base
    Euler channels for continuity, then run the native setter and replace only its
    lossy matrix->Euler result with the compatible double-precision decomposition
    of the same requested basis after near-rotation orthonormalization.
    """
    prefix = channel_parent_prefix(obj)
    try:
        local = prefix.inverted() @ desired_world
    except Exception as exc:
        raise ValueError(f"cadeia de parent de '{obj.name}' não é invertível") from exc
    continuity_reference = None
    if str(obj.rotation_mode) in _EULER_ORDER_TUPLES:
        continuity_reference = tuple(float(v) for v in obj.rotation_euler)
    obj.matrix_basis = local
    _refine_euler_after_matrix_basis_write(obj, local, continuity_reference)
    return local.copy()


def matrix_is_positive_uniform_similarity(matrix, tolerance=SIMILARITY_TOLERANCE):
    """Return True only for translation + rotation + positive uniform scale."""
    m = matrix.to_3x3()
    cols = [m.col[i] for i in range(3)]
    lengths2 = [float(v.dot(v)) for v in cols]
    if min(lengths2) <= ZERO_DELTA_TOLERANCE:
        return False
    ref = sum(lengths2) / 3.0
    scale = max(1.0, abs(ref))
    if max(abs(v - ref) for v in lengths2) > tolerance * scale:
        return False
    for i in range(3):
        for j in range(i + 1, 3):
            if abs(float(cols[i].dot(cols[j]))) > tolerance * scale:
                return False
    try:
        if float(m.determinant()) <= ZERO_DELTA_TOLERANCE:
            return False
    except Exception:
        return False
    return True

def guide_change_components(saved_guide_world, current_guide_world):
    """
    Human-readable change made directly to the guide: actual world-position
    difference, relative world rotation, and multiplicative world-scale ratio.
    These values are for display/logging; application uses guide_delta_matrix().
    """
    saved_location, saved_rotation, saved_scale = saved_guide_world.decompose()
    current_location, current_rotation, current_scale = current_guide_world.decompose()

    position_delta = current_location - saved_location
    rotation_delta = current_rotation @ saved_rotation.inverted()
    rotation_euler = rotation_delta.to_euler('XYZ')

    scale_ratio = current_scale.copy()
    for axis in range(3):
        if abs(saved_scale[axis]) <= ZERO_DELTA_TOLERANCE:
            raise ValueError(
                "A escala inicial do objeto-guia possui eixo igual a zero; "
                "não é possível calcular o fator de escala com segurança."
            )
        scale_ratio[axis] = current_scale[axis] / saved_scale[axis]

    return position_delta, rotation_euler, scale_ratio


def addon_module_id():
    return (__package__ or __name__).split('.')[0]


def get_addon_preferences(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(addon_module_id())
    return addon.preferences if addon is not None else None


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def current_blend_path():
    path = bpy.data.filepath
    return os.path.normcase(os.path.abspath(path)) if path else ""


def snapshots_directory():
    return bpy.utils.user_resource(
        'CONFIG',
        path=os.path.join('t7_statue_mover', 'snapshots'),
        create=True,
    )


def blend_file_sha256(blend_path=None):
    blend_path = blend_path if blend_path is not None else current_blend_path()
    if not blend_path or not os.path.isfile(blend_path):
        return ""

    normalized = os.path.normcase(os.path.abspath(blend_path))
    try:
        stat = os.stat(normalized)
        cache_key = (normalized, int(stat.st_size), int(getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1e9))))
    except OSError:
        return ""

    cached = _FILE_HASH_CACHE.get(cache_key)
    if cached:
        return cached

    digest = hashlib.sha256()
    try:
        with open(normalized, 'rb') as handle:
            while True:
                chunk = handle.read(FILE_HASH_CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        return ""

    value = digest.hexdigest()
    _FILE_HASH_CACHE.clear()
    _FILE_HASH_CACHE[cache_key] = value
    return value


def blend_file_sha256_fresh(blend_path=None):
    """Hash the actual bytes on disk without consulting the in-process cache.

    Prepare uses this as a second read immediately before committing the first
    external baseline, so a cached hash can never substitute for proof that the
    saved .blend still exists and is readable.
    """
    blend_path = blend_path if blend_path is not None else current_blend_path()
    if not blend_path or not os.path.isfile(blend_path):
        return ""

    normalized = os.path.normcase(os.path.abspath(blend_path))
    digest = hashlib.sha256()
    try:
        with open(normalized, 'rb') as handle:
            while True:
                chunk = handle.read(FILE_HASH_CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def valid_sha256_hex(value):
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def saved_blend_identity_preflight():
    """Return (path, sha256) only for a real readable saved .blend on disk."""
    blend_path = current_blend_path()
    if not blend_path:
        raise ValueError("Salve o .blend antes de Preparar Estátua.")
    if not os.path.isfile(blend_path):
        raise ValueError("O caminho do .blend existe na sessão, mas o arquivo não existe mais em disco.")

    # Keep the regular helper in the gate so fault injection / production hash
    # failures are treated exactly as failure, never as an embedded-only success.
    cached_or_first_sha = blend_file_sha256(blend_path)
    if not valid_sha256_hex(cached_or_first_sha):
        raise ValueError("O .blend salvo não pôde ser lido/hashado para criar o checkpoint externo.")

    # Prove readability from the bytes again without the cache.
    fresh_sha = blend_file_sha256_fresh(blend_path)
    if not valid_sha256_hex(fresh_sha):
        raise ValueError("O .blend salvo deixou de estar legível antes da preparação.")
    if fresh_sha != cached_or_first_sha:
        raise ValueError("O .blend em disco mudou durante o preflight. Salve/reabra e tente novamente.")
    return blend_path, fresh_sha


def external_snapshot_path(scene=None, blend_path=None, file_sha256_value=None, scene_name=None):
    """Return the external checkpoint path for an ON-DISK identity.

    `scene_name` is explicit so a frozen baseline can keep pointing at the Scene
    name that actually exists in the last saved .blend even if the live Scene is
    renamed later without saving.
    """
    blend_path = blend_path if blend_path is not None else current_blend_path()
    if not blend_path:
        return ""
    if scene_name is None:
        scene_name = getattr(scene, 'name', '') if scene is not None else ''
    if not scene_name:
        return ""
    file_sha256_value = file_sha256_value if file_sha256_value is not None else blend_file_sha256(blend_path)
    if not file_sha256_value:
        return ""
    identity = '\0'.join((
        os.path.normcase(os.path.abspath(blend_path)),
        file_sha256_value,
        scene_name,
    ))
    digest = hashlib.sha256(identity.encode('utf-8', errors='surrogatepass')).hexdigest()
    return os.path.join(snapshots_directory(), f"{digest}.json")


def _snapshot_dir_realpath():
    return os.path.realpath(os.path.abspath(snapshots_directory()))


def _canonical_snapshot_path_for_identity(blend_path, file_sha256_value, scene_name):
    path = external_snapshot_path(
        scene=None,
        blend_path=blend_path,
        file_sha256_value=file_sha256_value,
        scene_name=scene_name,
    )
    if not path:
        return ''
    root = _snapshot_dir_realpath()
    real = os.path.realpath(os.path.abspath(path))
    if os.path.dirname(real) != root:
        return ''
    base = os.path.basename(path)
    if len(base) != 69 or not base.endswith('.json') or not valid_sha256_hex(base[:-5]):
        return ''
    return path


def _load_valid_external_identity(blend_path, file_sha256_value, scene_name, snapshot_id=''):
    path = _canonical_snapshot_path_for_identity(blend_path, file_sha256_value, scene_name)
    if not path or not os.path.isfile(path):
        return None, ''
    # Symlinks are never accepted for a file that may later be removed.
    if os.path.islink(path):
        return None, ''
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            payload = json.load(handle)
    except Exception:
        return None, ''
    if not verify_payload_checksum(payload):
        return None, ''
    if payload.get('blend_path', '') != blend_path:
        return None, ''
    if payload.get('file_sha256', '') != file_sha256_value:
        return None, ''
    if payload.get('scene_name', '') != scene_name:
        return None, ''
    if snapshot_id and payload.get('snapshot_id', '') != snapshot_id:
        return None, ''
    return payload, path


def safe_delete_external_identity(blend_path, file_sha256_value, scene_name, snapshot_id):
    """Delete only a validated snapshot file derived from an identity.

    No path stored inside a .blend is ever passed to os.remove().
    """
    payload, path = _load_valid_external_identity(
        blend_path, file_sha256_value, scene_name, snapshot_id
    )
    if payload is None or not path:
        return False
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def object_disk_state(obj):
    try:
        world = list(matrix_to_flat(channel_world_matrix(obj)))
        world_verified = True
    except Exception:
        # File SHA-256 still binds the full .blend. Unsupported parent modes on
        # unrelated/non-target objects must not prevent baseline promotion.
        world = []
        world_verified = False
    return {
        'object_name': obj.name,
        'object_type': obj.type,
        'data_name': getattr(getattr(obj, 'data', None), 'name', '') or '',
        'parent_name': obj.parent.name if obj.parent is not None else '',
        'parent_type': obj.parent_type,
        'parent_bone': obj.parent_bone,
        'parent_vertices': list(obj.parent_vertices),
        'matrix_parent_inverse': list(matrix_to_flat(obj.matrix_parent_inverse)),
        'matrix_world': world,
        'world_verified': world_verified,
    }


def modifier_disk_state(obj, index, modifier):
    return {
        'object_name': obj.name,
        'modifier_name': modifier.name,
        'modifier_type': modifier.type,
        'modifier_index': int(index),
        'show_viewport': bool(modifier.show_viewport),
    }


def capture_disk_state(scene):
    objects = scene_objects(scene)
    return {
        'objects': [object_disk_state(obj) for obj in objects],
        'modifiers': [
            modifier_disk_state(obj, index, modifier)
            for obj in objects
            for index, modifier in enumerate(obj.modifiers)
        ],
    }


def original_disk_state_from_snapshot(settings):
    objects = []
    for item in settings.object_states:
        objects.append({
            'object_name': item.object_name,
            'object_type': item.object_type,
            'data_name': item.data_name,
            'parent_name': item.parent_name if item.had_parent else '',
            'parent_type': item.parent_type,
            'parent_bone': item.parent_bone,
            'parent_vertices': list(item.parent_vertices),
            'matrix_parent_inverse': list(item.matrix_parent_inverse),
            'matrix_world': list(item.matrix_world),
            'world_verified': bool(item.world_matrix_verified),
        })
    modifiers = [
        {
            'object_name': item.object_name,
            'modifier_name': item.modifier_name,
            'modifier_type': item.modifier_type,
            'modifier_index': int(item.modifier_index),
            'show_viewport': bool(item.show_viewport),
        }
        for item in settings.modifier_states
    ]
    return {'objects': objects, 'modifiers': modifiers}


def canonical_json(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def payload_with_checksum(payload):
    base = dict(payload)
    base.pop('checksum_sha256', None)
    checksum = hashlib.sha256(canonical_json(base).encode('utf-8')).hexdigest()
    base['checksum_sha256'] = checksum
    return base


def verify_payload_checksum(payload):
    expected = payload.get('checksum_sha256', '')
    if not expected:
        return False
    base = dict(payload)
    base.pop('checksum_sha256', None)
    actual = hashlib.sha256(canonical_json(base).encode('utf-8')).hexdigest()
    return actual == expected


def object_state_to_dict(item, live_identity=False):
    obj = item.object_ref
    if live_identity and obj is not None:
        object_name = obj.name
        data_name = getattr(getattr(obj, 'data', None), 'name', '') or ''
        parent_name = item.parent_ref.name if item.had_parent and item.parent_ref is not None else ''
    else:
        object_name = item.object_name
        data_name = item.data_name
        parent_name = getattr(item, 'parent_name', '') or ''

    return {
        'object_name': object_name,
        'object_type': item.object_type,
        'data_name': data_name,
        'is_target': bool(item.is_target),
        'had_parent': bool(item.had_parent),
        'parent_name': parent_name,
        'parent_type': item.parent_type,
        'parent_bone': item.parent_bone,
        'parent_vertices': list(item.parent_vertices),
        'matrix_parent_inverse': list(item.matrix_parent_inverse),
        'location': list(item.location),
        'rotation_mode': item.rotation_mode,
        'rotation_euler': list(item.rotation_euler),
        'rotation_quaternion': list(item.rotation_quaternion),
        'rotation_axis_angle': list(item.rotation_axis_angle),
        'scale': list(item.scale),
        'delta_location': list(item.delta_location),
        'delta_rotation_euler': list(item.delta_rotation_euler),
        'delta_rotation_quaternion': list(item.delta_rotation_quaternion),
        'delta_scale': list(item.delta_scale),
        'matrix_world': list(item.matrix_world),
        'world_matrix_verified': bool(item.world_matrix_verified),
        'applied_world_valid': bool(item.applied_world_valid),
        'applied_matrix_world': list(item.applied_matrix_world),
        'mesh_sentinel_valid': bool(item.mesh_sentinel_valid),
        'mesh_vertex_count': int(item.mesh_vertex_count),
        'mesh_sample_indices': list(item.mesh_sample_indices),
        'mesh_sample_coords': list(item.mesh_sample_coords),
        'geometry_sentinel_supported': bool(item.geometry_sentinel_supported),
        'geometry_sentinel_kind': item.geometry_sentinel_kind,
        'geometry_sentinel_hash': item.geometry_sentinel_hash,
    }


def modifier_state_to_dict(item, live_identity=False):
    object_name = item.object_name
    modifier_name = item.modifier_name
    obj = item.object_ref
    if live_identity and obj is not None:
        object_name = obj.name
        index = int(item.modifier_index)
        if 0 <= index < len(obj.modifiers):
            candidate = obj.modifiers[index]
            if candidate.type == item.modifier_type:
                modifier_name = candidate.name
    return {
        'object_name': object_name,
        'modifier_name': modifier_name,
        'modifier_type': item.modifier_type,
        'modifier_index': int(item.modifier_index),
        'show_viewport': bool(item.show_viewport),
        'is_managed': bool(item.is_managed),
    }


def _frozen_or_live_name(frozen_value, live_value, live_identity):
    if live_identity:
        return live_value or ''
    return frozen_value or live_value or ''


def snapshot_payload(
    scene,
    settings,
    file_sha256_value=None,
    live_identity=False,
    blend_path_override=None,
    disk_state_override=None,
):
    """Build a schema-v6 snapshot payload.

    ``objects``/``modifiers`` are the ORIGINAL state used for Restore.
    ``disk_state`` describes what is actually stored in the .blend identity
    bound to this external JSON.  Keeping them separate is required after a
    save performed while modifiers are disabled or after Apply.
    """
    blend_path = blend_path_override if blend_path_override is not None else current_blend_path()
    if file_sha256_value is None:
        file_sha256_value = blend_file_sha256(blend_path) if blend_path else ""

    scene_name = _frozen_or_live_name(
        getattr(settings, 'snapshot_scene_name', ''),
        getattr(scene, 'name', ''),
        live_identity,
    )
    guide_name = _frozen_or_live_name(
        getattr(settings, 'snapshot_guide_name', ''),
        settings.guide_object.name if settings.guide_object is not None else '',
        live_identity,
    )
    base_name = _frozen_or_live_name(
        getattr(settings, 'snapshot_base_name', ''),
        settings.base_object.name if settings.base_object is not None else '',
        live_identity,
    )
    target_collection_name = _frozen_or_live_name(
        getattr(settings, 'snapshot_target_collection_name', ''),
        settings.target_collection.name if settings.target_collection is not None else '',
        live_identity,
    )
    reference_collection_name = _frozen_or_live_name(
        getattr(settings, 'snapshot_reference_collection_name', ''),
        settings.reference_collection.name if settings.reference_collection is not None else '',
        live_identity,
    )

    payload = {
        'schema_version': SNAPSHOT_SCHEMA_VERSION,
        'addon_version': list(ADDON_VERSION),
        'blender_version': list(bpy.app.version[:3]),
        'snapshot_id': settings.snapshot_id,
        'created_utc': settings.snapshot_created_utc or utc_now_iso(),
        'updated_utc': utc_now_iso(),
        'blend_path': blend_path,
        'file_sha256': file_sha256_value,
        'scene_name': scene_name,
        'guide_name': guide_name,
        'base_name': base_name,
        'target_collection_name': target_collection_name,
        'reference_collection_name': reference_collection_name,
        'snapshot_active': bool(settings.snapshot_active),
        'displacement_applied': bool(settings.displacement_applied),
        'modifiers_currently_disabled': bool(settings.modifiers_currently_disabled),
        'counts': {
            'objects': int(settings.object_count),
            'targets': int(settings.target_count),
            'modifiers': int(settings.modifier_count),
            'disabled_modifiers': int(settings.disabled_modifier_count),
        },
        'last_transform': {
            'translation': [settings.last_delta_x, settings.last_delta_y, settings.last_delta_z],
            'rotation_deg': [settings.last_rotation_x, settings.last_rotation_y, settings.last_rotation_z],
            'scale_ratio': [settings.last_scale_x, settings.last_scale_y, settings.last_scale_z],
        },
        'objects': [object_state_to_dict(item, live_identity=live_identity) for item in settings.object_states],
        'modifiers': [modifier_state_to_dict(item, live_identity=live_identity) for item in settings.modifier_states],
        'disk_state': disk_state_override if disk_state_override is not None else capture_disk_state(scene),
    }
    return payload_with_checksum(payload)

def atomic_write_text(path, text):
    """Atomically write text without following a predictable temporary symlink.

    The temporary file is created with ``mkstemp`` (exclusive creation) in the
    destination directory.  A pre-created ``<path>.tmp`` symlink therefore has
    no influence on the write, and ``os.replace`` replaces the destination
    directory entry rather than following it.
    """
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    prefix = f".{os.path.basename(path)}."
    fd = None
    temp = ''
    try:
        fd, temp = tempfile.mkstemp(prefix=prefix, suffix='.tmp', dir=directory, text=True)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            fd = None
            handle.write(text)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(temp, path)
        temp = ''
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if temp:
            try:
                os.remove(temp)
            except OSError:
                pass

def _validate_written_external_payload(path, expected_payload):
    """Read back a just-written external checkpoint before it may replace baseline."""
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            loaded = json.load(handle)
    except Exception as exc:
        raise ValueError(f'backup externo não pôde ser relido: {exc}')

    if not verify_payload_checksum(loaded):
        raise ValueError('backup externo recém-gravado falhou no checksum')
    for key in ('schema_version', 'snapshot_id', 'blend_path', 'file_sha256', 'scene_name'):
        if loaded.get(key) != expected_payload.get(key):
            raise ValueError(f"backup externo recém-gravado diverge em '{key}'")
    return True


def _commit_external_payload(payload, settings, replace_old=False):
    """Write/verify one external payload without trusting any path from .blend."""
    blend_path = payload.get('blend_path', '')
    file_sha = payload.get('file_sha256', '')
    scene_name = payload.get('scene_name', '')
    snapshot_id = payload.get('snapshot_id', '')
    if not blend_path or not valid_sha256_hex(file_sha) or not scene_name or not snapshot_id:
        return False, ''

    # Capture the previous identity as DATA, never as an executable path.
    old_identity = (
        str(getattr(settings, 'snapshot_blend_path', '') or ''),
        str(getattr(settings, 'snapshot_file_sha256', '') or ''),
        str(getattr(settings, 'snapshot_scene_name', '') or ''),
        str(getattr(settings, 'snapshot_id', '') or ''),
    )

    if not replace_old:
        existing, existing_path = _load_valid_external_identity(
            old_identity[0], old_identity[1], old_identity[2], old_identity[3]
        )
        if existing is not None:
            settings.snapshot_backup_path = existing_path
            settings.snapshot_external_ok = True
            return True, existing_path

    path = _canonical_snapshot_path_for_identity(blend_path, file_sha, scene_name)
    if not path:
        return False, ''

    atomic_write_text(path, canonical_json(payload))
    _validate_written_external_payload(path, payload)

    # New baseline is valid. Only now publish its identity in runtime settings.
    settings.snapshot_backup_path = path
    settings.snapshot_external_ok = True
    settings.snapshot_blend_path = blend_path
    settings.snapshot_file_sha256 = file_sha
    settings.snapshot_scene_name = scene_name

    # For a normal save of the SAME file, the former SHA/name identity is now
    # stale and may be deleted, but only through the validated identity helper.
    # Save As intentionally preserves the original file's recoverable baseline.
    if replace_old and old_identity[0] and os.path.normcase(old_identity[0]) == os.path.normcase(blend_path):
        if old_identity[:3] != (blend_path, file_sha, scene_name):
            safe_delete_external_identity(*old_identity)
    return True, path

def _remove_embedded_snapshot_key(scene):
    if SCENE_SNAPSHOT_KEY in scene:
        try:
            del scene[SCENE_SNAPSHOT_KEY]
        except Exception:
            pass


def establish_initial_external_baseline(scene, settings, expected_blend_path, expected_file_sha):
    """Transactionally establish the FIRST recoverable external baseline.

    Unlike normal persist_snapshot(), this function is strict: embedded-only is
    never success. It re-reads the saved .blend bytes, writes a candidate JSON,
    validates checksum/identity, promotes it atomically, validates the promoted
    file again, and only then marks snapshot_external_ok.
    """
    if not settings.snapshot_active or not settings.snapshot_id:
        raise ValueError("snapshot inicial inativo/incompleto")

    current_path = current_blend_path()
    if not current_path or os.path.normcase(current_path) != os.path.normcase(expected_blend_path):
        raise ValueError("o caminho do .blend mudou durante Preparar")
    if not os.path.isfile(expected_blend_path):
        raise ValueError("o .blend salvo desapareceu antes da criação da baseline externa")

    fresh_sha = blend_file_sha256_fresh(expected_blend_path)
    if not valid_sha256_hex(fresh_sha):
        raise ValueError("o .blend salvo não pôde ser relido antes da criação da baseline externa")
    if fresh_sha != expected_file_sha:
        raise ValueError("os bytes do .blend mudaram durante Preparar")

    payload = snapshot_payload(
        scene,
        settings,
        expected_file_sha,
        live_identity=False,
        blend_path_override=expected_blend_path,
        disk_state_override=original_disk_state_from_snapshot(settings),
    )
    text = canonical_json(payload)
    final_path = external_snapshot_path(
        scene=None,
        blend_path=expected_blend_path,
        file_sha256_value=expected_file_sha,
        scene_name=payload.get('scene_name', ''),
    )
    if not final_path:
        raise ValueError("não foi possível calcular o path da baseline externa")

    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    candidate_path = final_path + f".{settings.snapshot_id}.candidate"
    previous_path = final_path + f".{settings.snapshot_id}.previous"
    had_previous = os.path.isfile(final_path)
    promoted = False

    try:
        # Build and validate away from the canonical baseline path first.
        atomic_write_text(candidate_path, text)
        _validate_written_external_payload(candidate_path, payload)

        # Preserve any older baseline at the same disk identity until the new
        # candidate has already passed readback validation.
        if had_previous:
            if os.path.isfile(previous_path):
                os.remove(previous_path)
            os.replace(final_path, previous_path)

        os.replace(candidate_path, final_path)
        promoted = True
        _validate_written_external_payload(final_path, payload)

        # Only now expose the embedded copy and mark external persistence OK.
        scene[SCENE_SNAPSHOT_KEY] = text
        settings.snapshot_checksum = payload['checksum_sha256']
        settings.snapshot_created_utc = payload['created_utc']
        settings.snapshot_blend_path = expected_blend_path
        settings.snapshot_file_sha256 = expected_file_sha
        settings.snapshot_backup_path = final_path
        settings.snapshot_external_ok = True
        settings.snapshot_persistence_warning = ''

        if had_previous and os.path.isfile(previous_path):
            try:
                os.remove(previous_path)
            except OSError:
                pass
        return True, final_path

    except Exception:
        # Never leave a failed candidate advertised as the baseline. Restore a
        # pre-existing file if there was one; otherwise remove our partial file.
        try:
            if os.path.isfile(candidate_path):
                os.remove(candidate_path)
        except OSError:
            pass
        if promoted:
            try:
                if os.path.isfile(final_path):
                    os.remove(final_path)
            except OSError:
                pass
        if had_previous and os.path.isfile(previous_path):
            try:
                os.replace(previous_path, final_path)
            except OSError:
                pass
        settings.snapshot_external_ok = False
        settings.snapshot_backup_path = ''
        raise


def persist_snapshot(scene, settings):
    """Refresh only the in-session embedded checkpoint.

    External baselines are immutable between real saves.  This function never
    promotes, replaces or deletes an external JSON.
    """
    if not settings.snapshot_active:
        return False, 'snapshot inactive'
    if not settings.snapshot_id:
        settings.snapshot_id = uuid.uuid4().hex

    payload = snapshot_payload(
        scene,
        settings,
        settings.snapshot_file_sha256 or blend_file_sha256(current_blend_path()),
        live_identity=False,
        blend_path_override=settings.snapshot_blend_path or current_blend_path(),
    )
    text = canonical_json(payload)
    scene[SCENE_SNAPSHOT_KEY] = text
    settings.snapshot_checksum = payload['checksum_sha256']
    settings.snapshot_created_utc = payload['created_utc']

    # External redundancy is valid only if the frozen baseline still belongs
    # to the bytes currently on disk.  This prevents an old baseline from being
    # advertised as current after a real save whose promotion failed.
    current_path = current_blend_path()
    current_sha = blend_file_sha256_fresh(current_path) if current_path else ''
    same_disk_identity = bool(
        current_path
        and valid_sha256_hex(current_sha)
        and os.path.normcase(current_path) == os.path.normcase(settings.snapshot_blend_path or '')
        and current_sha == settings.snapshot_file_sha256
    )
    if same_disk_identity:
        existing, path = _load_valid_external_identity(
            settings.snapshot_blend_path,
            settings.snapshot_file_sha256,
            settings.snapshot_scene_name,
            settings.snapshot_id,
        )
    else:
        existing, path = None, ''
    settings.snapshot_external_ok = existing is not None
    settings.snapshot_backup_path = path if existing is not None else ''
    if existing is None and current_path:
        settings.snapshot_persistence_warning = (
            "Backup externo não corresponde aos bytes atualmente salvos; usando somente o snapshot embutido."
        )
    elif existing is not None:
        settings.snapshot_persistence_warning = ''
    return True, path or 'embedded-only'

def persist_external_snapshot_postsave(scene, settings, saved_path=''):
    """Promote a baseline only after a real save of bpy.data.filepath."""
    if not settings.snapshot_active or not settings.snapshot_id:
        return False, ''
    if int(settings.snapshot_schema_version) != SNAPSHOT_SCHEMA_VERSION:
        return False, ''

    blend_path = current_blend_path()
    if not blend_path:
        return False, ''
    if saved_path:
        saved_path = os.path.abspath(bpy.path.abspath(saved_path))
        # File > Save Copy fires save handlers for another target while
        # bpy.data.filepath remains the original. Never promote in that case.
        if os.path.normcase(saved_path) != os.path.normcase(blend_path):
            return False, ''

    file_sha = blend_file_sha256_fresh(blend_path)
    if not valid_sha256_hex(file_sha):
        return False, ''

    disk_state = capture_disk_state(scene)
    payload = snapshot_payload(
        scene,
        settings,
        file_sha,
        live_identity=True,
        blend_path_override=blend_path,
        disk_state_override=disk_state,
    )
    # Prove the candidate describes the just-saved in-memory file before it can
    # replace the previous baseline.
    validate_recovery_payload(scene, payload, 'external')
    ok, path = _commit_external_payload(payload, settings, replace_old=True)
    if ok:
        settings.snapshot_checksum = payload['checksum_sha256']
        settings.snapshot_persistence_warning = ''
        settings.snapshot_blend_path = blend_path
        settings.snapshot_file_sha256 = file_sha
        settings.snapshot_scene_name = scene.name
        settings.snapshot_guide_name = settings.guide_object.name if settings.guide_object else ''
        settings.snapshot_base_name = settings.base_object.name if settings.base_object else ''
        settings.snapshot_target_collection_name = settings.target_collection.name if settings.target_collection else ''
        settings.snapshot_reference_collection_name = settings.reference_collection.name if settings.reference_collection else ''
    return ok, path

def delete_external_snapshot(settings=None, scene=None, blend_path=None):
    """Delete only the baseline derived from validated frozen identity fields."""
    if settings is None:
        return False
    return safe_delete_external_identity(
        str(getattr(settings, 'snapshot_blend_path', '') or ''),
        str(getattr(settings, 'snapshot_file_sha256', '') or ''),
        str(getattr(settings, 'snapshot_scene_name', '') or ''),
        str(getattr(settings, 'snapshot_id', '') or ''),
    )

def delete_persistent_snapshot(scene, settings):
    if SCENE_SNAPSHOT_KEY in scene:
        try:
            del scene[SCENE_SNAPSHOT_KEY]
        except Exception:
            pass
    delete_external_snapshot(settings=settings)

def resolve_scene_object(scene, name):
    if not name:
        return None
    obj = bpy.data.objects.get(name)
    if obj is None:
        return None
    scene_ptrs = {object_pointer(item) for item in scene_objects(scene)}
    return obj if object_pointer(obj) in scene_ptrs else None


def hydrate_snapshot(scene, settings, payload):
    if payload.get('schema_version') != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError('schema de snapshot incompatível')
    if not verify_payload_checksum(payload):
        raise ValueError('checksum do snapshot inválido')

    settings.object_states.clear()
    settings.modifier_states.clear()

    settings.guide_object = resolve_scene_object(scene, payload.get('guide_name', ''))
    settings.base_object = resolve_scene_object(scene, payload.get('base_name', ''))
    target_name = payload.get('target_collection_name', '')
    reference_name = payload.get('reference_collection_name', '')
    settings.target_collection = bpy.data.collections.get(target_name) if target_name else None
    settings.reference_collection = bpy.data.collections.get(reference_name) if reference_name else None
    settings.snapshot_scene_name = payload.get('scene_name', '')
    settings.snapshot_guide_name = payload.get('guide_name', '')
    settings.snapshot_base_name = payload.get('base_name', '')
    settings.snapshot_target_collection_name = target_name
    settings.snapshot_reference_collection_name = reference_name

    for src in payload.get('objects', []):
        item = settings.object_states.add()
        item.object_name = src.get('object_name', '')
        item.object_type = src.get('object_type', '')
        item.data_name = src.get('data_name', '')
        item.object_ref = resolve_scene_object(scene, item.object_name)
        item.is_target = bool(src.get('is_target', False))
        item.had_parent = bool(src.get('had_parent', False))
        parent_name = src.get('parent_name', '')
        item.parent_name = parent_name
        item.parent_ref = resolve_scene_object(scene, parent_name) if parent_name else None
        item.parent_type = src.get('parent_type', 'OBJECT')
        item.parent_bone = src.get('parent_bone', '')
        item.parent_vertices = tuple(src.get('parent_vertices', [0, 0, 0]))
        item.matrix_parent_inverse = tuple(src.get('matrix_parent_inverse', IDENTITY_MATRIX_FLAT))
        item.location = tuple(src.get('location', [0.0, 0.0, 0.0]))
        item.rotation_mode = src.get('rotation_mode', 'XYZ')
        item.rotation_euler = tuple(src.get('rotation_euler', [0.0, 0.0, 0.0]))
        item.rotation_quaternion = tuple(src.get('rotation_quaternion', [1.0, 0.0, 0.0, 0.0]))
        item.rotation_axis_angle = tuple(src.get('rotation_axis_angle', [0.0, 0.0, 1.0, 0.0]))
        item.scale = tuple(src.get('scale', [1.0, 1.0, 1.0]))
        item.delta_location = tuple(src.get('delta_location', [0.0, 0.0, 0.0]))
        item.delta_rotation_euler = tuple(src.get('delta_rotation_euler', [0.0, 0.0, 0.0]))
        item.delta_rotation_quaternion = tuple(src.get('delta_rotation_quaternion', [1.0, 0.0, 0.0, 0.0]))
        item.delta_scale = tuple(src.get('delta_scale', [1.0, 1.0, 1.0]))
        item.matrix_world = tuple(src.get('matrix_world', IDENTITY_MATRIX_FLAT))
        item.world_matrix_verified = bool(src.get('world_matrix_verified', True))
        item.applied_world_valid = bool(src.get('applied_world_valid', False))
        item.applied_matrix_world = tuple(src.get('applied_matrix_world', IDENTITY_MATRIX_FLAT))
        item.mesh_sentinel_valid = bool(src.get('mesh_sentinel_valid', False))
        item.mesh_vertex_count = int(src.get('mesh_vertex_count', 0))
        item.mesh_sample_indices = tuple(src.get('mesh_sample_indices', [0, 0, 0, 0]))
        item.mesh_sample_coords = tuple(src.get('mesh_sample_coords', [0.0] * 12))
        item.geometry_sentinel_supported = bool(src.get('geometry_sentinel_supported', False))
        item.geometry_sentinel_kind = src.get('geometry_sentinel_kind', '')
        item.geometry_sentinel_hash = src.get('geometry_sentinel_hash', '')

    for src in payload.get('modifiers', []):
        item = settings.modifier_states.add()
        item.object_name = src.get('object_name', '')
        item.object_ref = resolve_scene_object(scene, item.object_name)
        item.modifier_name = src.get('modifier_name', '')
        item.modifier_type = src.get('modifier_type', '')
        item.modifier_index = int(src.get('modifier_index', -1))
        item.show_viewport = bool(src.get('show_viewport', True))
        item.is_managed = bool(src.get('is_managed', False))

    counts = payload.get('counts', {})
    settings.object_count = int(counts.get('objects', len(settings.object_states)))
    settings.target_count = int(counts.get('targets', sum(1 for item in settings.object_states if item.is_target)))
    settings.modifier_count = int(counts.get('modifiers', len(settings.modifier_states)))
    settings.disabled_modifier_count = int(counts.get('disabled_modifiers', 0))
    settings.snapshot_schema_version = int(payload.get('schema_version', 0))
    settings.snapshot_active = bool(payload.get('snapshot_active', True))
    settings.displacement_applied = bool(payload.get('displacement_applied', False))
    settings.modifiers_currently_disabled = bool(payload.get('modifiers_currently_disabled', False))
    transform = payload.get('last_transform', {})
    t = transform.get('translation', [0.0, 0.0, 0.0])
    r = transform.get('rotation_deg', [0.0, 0.0, 0.0])
    sc = transform.get('scale_ratio', [1.0, 1.0, 1.0])
    settings.last_delta_x, settings.last_delta_y, settings.last_delta_z = t
    settings.last_rotation_x, settings.last_rotation_y, settings.last_rotation_z = r
    settings.last_scale_x, settings.last_scale_y, settings.last_scale_z = sc
    settings.snapshot_id = payload.get('snapshot_id', '')
    settings.snapshot_created_utc = payload.get('created_utc', '')
    settings.snapshot_blend_path = payload.get('blend_path', '')
    settings.snapshot_file_sha256 = payload.get('file_sha256', '')
    settings.snapshot_checksum = payload.get('checksum_sha256', '')
    settings.snapshot_external_ok = False
    return True


def load_snapshot_payload_from_scene(scene):
    text = scene.get(SCENE_SNAPSHOT_KEY, '')
    if not isinstance(text, str) or not text:
        return None
    return json.loads(text)


def load_snapshot_payload_external(scene):
    blend_path = current_blend_path()
    file_sha = blend_file_sha256(blend_path) if blend_path else ""
    if not blend_path or not valid_sha256_hex(file_sha):
        return None, ''
    path = _canonical_snapshot_path_for_identity(blend_path, file_sha, scene.name)
    if not path:
        return None, ''

    def read_candidate(candidate):
        if not os.path.isfile(candidate) or os.path.islink(candidate):
            return None
        try:
            with open(candidate, 'r', encoding='utf-8') as handle:
                payload = json.load(handle)
        except Exception:
            return None
        if not verify_payload_checksum(payload):
            return None
        if (
            payload.get('blend_path', '') != blend_path
            or payload.get('file_sha256', '') != file_sha
            or payload.get('scene_name', '') != scene.name
        ):
            return None
        return payload

    def _transaction_id_from_aux_path(aux_path, suffix):
        base = os.path.basename(path) + '.'
        name = os.path.basename(aux_path)
        if not name.startswith(base) or not name.endswith(suffix):
            return ''
        transaction_id = name[len(base):-len(suffix)]
        if len(transaction_id) != 32 or any(ch not in '0123456789abcdef' for ch in transaction_id.lower()):
            return ''
        return transaction_id.lower()

    def cleanup_orphan_candidates_for_transaction(transaction_id):
        """Remove only a validated candidate from the recovered transaction.

        In the crash window, the .previous *filename* carries the new Prepare's
        transaction id, while its payload still contains the old snapshot_id.
        Matching payload ids therefore cannot work.  The auxiliary filename is
        the transaction binding; checksum + blend/SHA/Scene + candidate payload
        snapshot_id are revalidated before deletion.
        """
        if not transaction_id:
            return
        candidate_path = path + f'.{transaction_id}.candidate'
        if not os.path.isfile(candidate_path) or os.path.islink(candidate_path):
            return
        candidate_payload = read_candidate(candidate_path)
        if candidate_payload is None:
            return
        if str(candidate_payload.get('snapshot_id', '') or '').lower() != transaction_id:
            return
        try:
            os.remove(candidate_path)
        except OSError:
            pass

    payload = read_candidate(path)
    if payload is not None:
        return payload, path

    # Crash recovery for the narrow initial-promotion window: if canonical is
    # absent but exactly one validated .previous remains, restore it.
    directory = os.path.dirname(path)
    prefix = os.path.basename(path) + '.'
    previous = []
    try:
        for name in os.listdir(directory):
            if not name.startswith(prefix) or not name.endswith('.previous'):
                continue
            candidate = os.path.join(directory, name)
            candidate_payload = read_candidate(candidate)
            if candidate_payload is not None:
                previous.append((candidate, candidate_payload))
    except OSError:
        previous = []
    if len(previous) == 1:
        previous_path, payload = previous[0]
        transaction_id = _transaction_id_from_aux_path(previous_path, '.previous')
        try:
            os.replace(previous_path, path)
            cleanup_orphan_candidates_for_transaction(transaction_id)
            return payload, path
        except OSError:
            cleanup_orphan_candidates_for_transaction(transaction_id)
            return payload, previous_path
    return None, '' 

def scene_collection_names(scene):
    names = set()
    stack = [scene.collection]
    seen = set()
    while stack:
        col = stack.pop()
        ptr = object_pointer(col)
        if ptr in seen:
            continue
        seen.add(ptr)
        names.add(col.name)
        stack.extend(list(col.children))
    return names


def _payload_target_names(scene, payload):
    by_name = {obj.name: obj for obj in scene_objects(scene)}
    target_collection_name = payload.get('target_collection_name', '')
    if target_collection_name:
        collection = bpy.data.collections.get(target_collection_name)
        if collection is None or target_collection_name not in scene_collection_names(scene):
            raise ValueError('target collection do snapshot não pertence à Scene atual')
        candidates = {obj.name for obj in collection_scene_objects(scene, collection)}
    else:
        candidates = set(by_name)

    fixed = set()
    base_name = payload.get('base_name', '')
    if base_name:
        base = by_name.get(base_name)
        if base is None:
            raise ValueError('base do snapshot não existe na Scene atual')
        fixed.add(base.name)
        stack = list(base.children)
        while stack:
            obj = stack.pop()
            if obj.name in fixed:
                continue
            fixed.add(obj.name)
            stack.extend(list(obj.children))

    reference_name = payload.get('reference_collection_name', '')
    if reference_name:
        reference = bpy.data.collections.get(reference_name)
        if reference is None or reference_name not in scene_collection_names(scene):
            raise ValueError('reference collection do snapshot não pertence à Scene atual')
        fixed.update(obj.name for obj in collection_scene_objects(scene, reference))

    candidates.difference_update(fixed)
    guide_name = payload.get('guide_name', '')
    if guide_name:
        if guide_name not in by_name:
            raise ValueError('guia do snapshot não existe na Scene atual')
        if guide_name in fixed:
            raise ValueError('guia do snapshot está dentro do conjunto fixo')
        candidates.add(guide_name)
    return candidates, fixed


def _matrix_values_close(a, b, tolerance=None):
    if len(a) != len(b):
        return False
    # Relative tolerance avoids false failures for models far from the origin.
    return all(_matrix_component_close(x, y) for x, y in zip(a, b))

def validate_external_disk_state(scene, payload):
    disk_state = payload.get('disk_state')
    if not isinstance(disk_state, dict):
        raise ValueError('snapshot externo não possui disk_state schema 6')

    current_objects = {obj.name: obj for obj in scene_objects(scene)}
    disk_objects = disk_state.get('objects', [])
    names = [item.get('object_name', '') for item in disk_objects]
    if len(names) != len(set(names)) or set(names) != set(current_objects):
        raise ValueError('disk_state de objetos diverge do .blend em disco')

    for src in disk_objects:
        name = src.get('object_name', '')
        obj = current_objects[name]
        if src.get('object_type', '') != obj.type:
            raise ValueError(f"tipo salvo de '{name}' diverge do .blend")
        data_name = getattr(getattr(obj, 'data', None), 'name', '') or ''
        if src.get('data_name', '') != data_name:
            raise ValueError(f"datablock salvo de '{name}' diverge do .blend")
        parent_name = obj.parent.name if obj.parent is not None else ''
        if src.get('parent_name', '') != parent_name:
            raise ValueError(f"parent salvo de '{name}' diverge do .blend")
        if src.get('parent_type', 'OBJECT') != obj.parent_type:
            raise ValueError(f"parent_type salvo de '{name}' diverge do .blend")
        if src.get('parent_bone', '') != obj.parent_bone:
            raise ValueError(f"parent_bone salvo de '{name}' diverge do .blend")
        if tuple(src.get('parent_vertices', [0, 0, 0])) != tuple(obj.parent_vertices):
            raise ValueError(f"parent_vertices salvo de '{name}' diverge do .blend")
        if not _matrix_values_close(src.get('matrix_parent_inverse', []), matrix_to_flat(obj.matrix_parent_inverse)):
            raise ValueError(f"matrix_parent_inverse salvo de '{name}' diverge do .blend")
        if bool(src.get('world_verified', True)):
            try:
                current_world = matrix_to_flat(channel_world_matrix(obj))
            except Exception as exc:
                raise ValueError(f"world por canais indisponível para '{name}': {exc}") from exc
            if not _matrix_values_close(src.get('matrix_world', []), current_world):
                raise ValueError(f"transform salvo de '{name}' não coincide com o .blend em disco")

    disk_mods = disk_state.get('modifiers', [])
    by_object = {}
    for mod in disk_mods:
        by_object.setdefault(mod.get('object_name', ''), []).append(mod)
    for name, obj in current_objects.items():
        saved = sorted(by_object.get(name, []), key=lambda item: int(item.get('modifier_index', -1)))
        current = list(obj.modifiers)
        if len(saved) != len(current):
            raise ValueError(f"topologia salva de modifiers de '{name}' diverge do .blend")
        for index, (src, modifier) in enumerate(zip(saved, current)):
            if (
                int(src.get('modifier_index', -1)) != index
                or src.get('modifier_name', '') != modifier.name
                or src.get('modifier_type', '') != modifier.type
            ):
                raise ValueError(f"topologia salva de modifiers de '{name}' diverge do .blend")
            if bool(src.get('show_viewport', True)) != bool(modifier.show_viewport):
                raise ValueError(f"show_viewport salvo de '{name}' diverge do .blend")
    return True


def validate_recovery_payload(scene, payload, source_kind):
    if not isinstance(payload, dict):
        raise ValueError('payload de snapshot inválido')
    if payload.get('schema_version') != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError('schema de snapshot incompatível')
    if not verify_payload_checksum(payload):
        raise ValueError('checksum do snapshot inválido')
    if tuple(payload.get('blender_version', ())) != SUPPORTED_BLENDER_VERSION:
        raise ValueError('snapshot não foi criado no Blender 5.0.0')
    if not payload.get('snapshot_id'):
        raise ValueError('snapshot sem identidade persistente')
    if payload.get('scene_name', '') != scene.name:
        raise ValueError('snapshot pertence a outra Scene')

    blend_path = current_blend_path()
    if source_kind == 'external':
        payload_path = payload.get('blend_path', '')
        if not blend_path or not payload_path or os.path.normcase(payload_path) != os.path.normcase(blend_path):
            raise ValueError('snapshot externo pertence a outro caminho de .blend')
        current_sha = blend_file_sha256(blend_path)
        if not valid_sha256_hex(current_sha) or payload.get('file_sha256', '') != current_sha:
            raise ValueError('snapshot externo pertence a outra identidade binária do .blend')

    current_objects = {obj.name: obj for obj in scene_objects(scene)}
    saved_objects = payload.get('objects', [])
    saved_names = [item.get('object_name', '') for item in saved_objects]
    if len(saved_names) != len(set(saved_names)) or set(saved_names) != set(current_objects):
        raise ValueError('conjunto de objetos da Scene diverge do snapshot')

    expected_targets, fixed_names = _payload_target_names(scene, payload)
    saved_target_names = {item.get('object_name', '') for item in saved_objects if item.get('is_target', False)}
    if saved_target_names != expected_targets:
        raise ValueError('target set do snapshot não corresponde à Scene atual')

    saved_by_name = {item.get('object_name', ''): item for item in saved_objects}
    for name, src in saved_by_name.items():
        obj = current_objects[name]
        if src.get('object_type', '') and src.get('object_type') != getattr(obj, 'type', ''):
            raise ValueError(f"tipo do objeto '{name}' diverge do snapshot")
        data_name = getattr(getattr(obj, 'data', None), 'name', '') or ''
        if src.get('data_name', '') != data_name:
            raise ValueError(f"datablock do objeto '{name}' diverge do snapshot")
        # The original parent is restoration intent. An external baseline may
        # legitimately describe a file saved after a temporary reparent, so
        # current parent/world are checked against disk_state instead.
        if source_kind != 'external':
            current_parent_name = obj.parent.name if obj.parent is not None else ''
            if src.get('parent_name', '') != current_parent_name:
                raise ValueError(f"parent de '{name}' diverge do snapshot")

    saved_mods = payload.get('modifiers', [])
    saved_by_object = {}
    for mod in saved_mods:
        saved_by_object.setdefault(mod.get('object_name', ''), []).append(mod)
    for name, obj in current_objects.items():
        saved = sorted(saved_by_object.get(name, []), key=lambda item: int(item.get('modifier_index', -1)))
        current = list(obj.modifiers)
        if len(saved) != len(current):
            raise ValueError(f"topologia de modifiers de '{name}' diverge do snapshot")
        for index, (src, modifier) in enumerate(zip(saved, current)):
            if int(src.get('modifier_index', -1)) != index or src.get('modifier_name', '') != modifier.name or src.get('modifier_type', '') != modifier.type:
                raise ValueError(f"topologia de modifiers de '{name}' diverge do snapshot")
            expected_managed = bool(
                name in expected_targets
                and name != payload.get('guide_name', '')
                and name not in fixed_names
            )
            if bool(src.get('is_managed', False)) != expected_managed:
                raise ValueError(f"escopo congelado de modifier de '{name}' é inconsistente")

    if source_kind == 'external':
        validate_external_disk_state(scene, payload)
    return True

def recover_snapshot_for_scene(scene):
    settings = getattr(scene, 't7sm_settings', None)
    if settings is None:
        return False

    # A saved PropertyGroup is primary. Recovery must NEVER promote or delete
    # an external baseline from load_post/register; those events are not saves.
    if settings.snapshot_active and len(settings.object_states) > 0:
        if not snapshot_runtime_compatible(settings):
            print(
                f"[T7 Statue Mover] active snapshot for {scene.name} uses an incompatible/legacy schema; "
                "no automatic mutation or migration was performed"
            )
            return False
        blend_path = current_blend_path()
        file_sha = blend_file_sha256(blend_path) if blend_path else ''
        payload, path = _load_valid_external_identity(
            blend_path, file_sha, scene.name, settings.snapshot_id
        ) if blend_path and file_sha else (None, '')
        if payload is not None:
            try:
                validate_recovery_payload(scene, payload, 'external')
            except Exception as exc:
                print(f"[T7 Statue Mover] external redundancy invalid for active snapshot in {scene.name}: {exc}")
                payload, path = None, ''
        settings.snapshot_external_ok = payload is not None
        settings.snapshot_backup_path = path if payload is not None else ''
        settings.snapshot_persistence_warning = '' if payload is not None else (
            "Backup externo não validou para o arquivo atual; usando somente o snapshot embutido."
        )
        # Bind runtime deletion/promotion identity to the file that is actually
        # open, never to serialized path strings from a Save Copy or foreign .blend.
        settings.snapshot_blend_path = blend_path
        settings.snapshot_file_sha256 = file_sha
        settings.snapshot_scene_name = scene.name
        return True

    payload = None
    external_path = ''
    source_kind = ''
    try:
        candidate = load_snapshot_payload_from_scene(scene)
        if candidate is not None:
            validate_recovery_payload(scene, candidate, 'embedded')
            payload = candidate
            source_kind = 'embedded'
    except Exception as exc:
        print(f"[T7 Statue Mover] embedded snapshot refused for {scene.name}: {exc}")
        payload = None

    if payload is None:
        try:
            candidate, external_path = load_snapshot_payload_external(scene)
            if candidate is not None:
                validate_recovery_payload(scene, candidate, 'external')
                payload = candidate
                source_kind = 'external'
        except Exception as exc:
            print(f"[T7 Statue Mover] external snapshot refused for {scene.name}: {exc}")
            payload = None
            external_path = ''

    if payload is None:
        return False

    hydrate_snapshot(scene, settings, payload)
    if settings.modifiers_currently_disabled:
        _disabled, missing = disable_modifiers_from_snapshot(settings)
        if missing:
            clear_snapshot_data(settings, scene=None, delete_persistent=False)
            raise ValueError(f'recovery aborted: {missing} managed modifier(s) unavailable')

    if external_path:
        settings.snapshot_backup_path = external_path
        settings.snapshot_external_ok = True
        settings.snapshot_persistence_warning = ''
    elif source_kind == 'embedded':
        # Embedded snapshots belong to the file that contains them now. A Save
        # Copy must never inherit deletion authority over the original file's JSON.
        blend_path = current_blend_path()
        file_sha = blend_file_sha256(blend_path) if blend_path else ''
        settings.snapshot_blend_path = blend_path
        settings.snapshot_file_sha256 = file_sha
        settings.snapshot_scene_name = scene.name
        settings.snapshot_backup_path = ''
        settings.snapshot_external_ok = False
        settings.snapshot_persistence_warning = (
            "Snapshot recuperado do .blend; backup externo não validou para esta identidade."
        )
    print(f"[T7 Statue Mover] recovered {source_kind} snapshot for {scene.name}")
    return True

def reference_source_path(context=None):
    bundled = os.path.join(os.path.dirname(__file__), BUNDLED_REFERENCE_RELATIVE)
    if os.path.isfile(bundled):
        return bundled
    prefs = get_addon_preferences(context)
    if prefs is None:
        return ''
    path = bpy.path.abspath(prefs.reference_blend_path) if prefs.reference_blend_path else ''
    return os.path.abspath(path) if path else ''


def iter_collection_tree(root):
    stack = [root]
    seen = set()
    while stack:
        col = stack.pop()
        ptr = col.as_pointer()
        if ptr in seen:
            continue
        seen.add(ptr)
        yield col
        stack.extend(list(col.children))


def _reference_dataset_items():
    for name in REFERENCE_DATASET_NAMES:
        collection = getattr(bpy.data, name, None)
        if collection is not None:
            yield name, collection


def _reference_datablock_pointer(block):
    try:
        return block.as_pointer()
    except Exception:
        return id(block)


def capture_reference_datablocks():
    return {
        name: {_reference_datablock_pointer(block) for block in collection}
        for name, collection in _reference_dataset_items()
    }


def tag_new_reference_datablocks(before, import_id):
    tagged = 0
    for name, collection in _reference_dataset_items():
        previous = before.get(name, set())
        for block in list(collection):
            if _reference_datablock_pointer(block) in previous:
                continue
            try:
                block[REFERENCE_TAG_KEY] = import_id
                tagged += 1
            except Exception:
                pass
    return tagged


def tagged_reference_datablocks(import_id):
    result = []
    if not import_id:
        return result
    for name, collection in _reference_dataset_items():
        for block in list(collection):
            try:
                if block.get(REFERENCE_TAG_KEY, '') == import_id:
                    result.append((name, collection, block))
            except Exception:
                continue
    return result


def tagged_reference_import_ids():
    ids = set()
    for _name, collection in _reference_dataset_items():
        for block in list(collection):
            try:
                import_id = str(block.get(REFERENCE_TAG_KEY, '') or '')
            except Exception:
                import_id = ''
            if import_id:
                ids.add(import_id)
    return ids


def find_reference_master(import_id=''):
    for collection in getattr(bpy.data, 'collections', []):
        try:
            is_master = bool(collection.get(REFERENCE_MASTER_TAG, False))
            tagged_id = str(collection.get(REFERENCE_TAG_KEY, '') or '')
        except Exception:
            continue
        if is_master and (not import_id or tagged_id == import_id):
            return collection
    return None


def _block_reference_id(block):
    try:
        return str(block.get(REFERENCE_TAG_KEY, '') or '')
    except Exception:
        return ''


def _collection_parent_links(target):
    parents = []
    for parent in getattr(bpy.data, 'collections', []):
        try:
            if target.name in parent.children:
                parents.append(parent)
        except Exception:
            continue
    return parents


def _collection_scene_root_links(target):
    scenes = []
    for candidate_scene in getattr(bpy.data, 'scenes', []):
        try:
            if target.name in candidate_scene.collection.children:
                scenes.append(candidate_scene)
        except Exception:
            continue
    return scenes


def _collection_instance_users(target):
    users = []
    for obj in getattr(bpy.data, 'objects', []):
        try:
            if getattr(obj, 'instance_collection', None) == target:
                users.append(obj)
        except Exception:
            continue
    return users


def reference_priority_external_reuse_reasons(scene, import_id, dataset_name, block, master):
    """Return external reuse that makes destructive cleanup unsafe.

    For Objects, only collection links owned by the same import are considered
    internal. For Collections, parent-collection links owned by the same import
    are internal; the master collection's link to the current Scene root is also
    internal. Any other link/use is treated conservatively as external reuse.
    """
    reasons = []

    # Blender can expose the exact ID datablocks that use another ID through
    # BlendData.user_map(). This catches external constraints/modifiers/parents
    # without confusing legitimate internal parent-child references. The manual
    # link scans below remain as a conservative fallback and make the logic
    # independently testable in lightweight harnesses.
    user_map_fn = getattr(bpy.data, 'user_map', None)
    if callable(user_map_fn):
        try:
            direct_users = user_map_fn(subset={block}).get(block, set())
        except Exception:
            direct_users = set()
        for user in direct_users:
            if _block_reference_id(user) == import_id:
                continue
            # The current Scene is an expected indirect user of every object
            # and collection linked under the imported master. Other Scenes are external.
            if user == scene:
                continue
            if dataset_name == 'collections' and block == master and user == getattr(scene, 'collection', None):
                continue
            reasons.append(f"external ID user '{getattr(user, 'name', type(user).__name__)}'")

    if dataset_name == 'objects':
        users_collection = list(getattr(block, 'users_collection', ()) or ())
        for collection in users_collection:
            if _block_reference_id(collection) != import_id:
                reasons.append(f"external collection '{getattr(collection, 'name', '?')}'")

        # External parenting would be modified by Object removal as well.
        for other in getattr(bpy.data, 'objects', []):
            try:
                if getattr(other, 'parent', None) == block and _block_reference_id(other) != import_id:
                    reasons.append(f"external child '{getattr(other, 'name', '?')}'")
            except Exception:
                continue

        if bool(getattr(block, 'use_fake_user', False)):
            reasons.append('fake user enabled')

    elif dataset_name == 'collections':
        for parent in _collection_parent_links(block):
            if _block_reference_id(parent) != import_id:
                reasons.append(f"external parent collection '{getattr(parent, 'name', '?')}'")

        for linked_scene in _collection_scene_root_links(block):
            allowed_master_link = block == master and linked_scene == scene
            if not allowed_master_link:
                reasons.append(f"external Scene root '{getattr(linked_scene, 'name', '?')}'")

        for obj in _collection_instance_users(block):
            if _block_reference_id(obj) != import_id:
                reasons.append(f"external collection instance '{getattr(obj, 'name', '?')}'")

        # Never delete an imported container that now contains user-owned data.
        for obj in list(getattr(block, 'objects', ()) or ()):
            if _block_reference_id(obj) != import_id:
                reasons.append(f"untagged/user object inside collection '{getattr(obj, 'name', '?')}'")
        for child in list(getattr(block, 'children', ()) or ()):
            if _block_reference_id(child) != import_id:
                reasons.append(f"untagged/user child collection '{getattr(child, 'name', '?')}'")

        if bool(getattr(block, 'use_fake_user', False)):
            reasons.append('fake user enabled')

    elif dataset_name == 'scenes':
        if block == scene:
            reasons.append('current Scene')

    # Deduplicate while preserving order for deterministic diagnostics.
    return list(dict.fromkeys(reasons))


def _iter_all_bpy_data_ids():
    """Yield every ID-like datablock exposed by bpy.data, without a fixed allowlist.

    This is intentionally broader than REFERENCE_DATASET_NAMES.  Library removal
    can delete linked IDs of types the importer never manages (Text, Brush,
    Palette, LineStyle, LightProbe, hair curves, MovieClip, Mask, Workspace,
    etc.), so a fixed dataset list is not a sufficient safety boundary.
    """
    seen = set()
    for attr_name in dir(bpy.data):
        if attr_name.startswith('_'):
            continue
        try:
            collection = getattr(bpy.data, attr_name)
        except Exception:
            continue
        if callable(collection) or isinstance(collection, (str, bytes)):
            continue
        try:
            items = list(collection)
        except Exception:
            continue
        for block in items:
            # Ignore scalar/tuple-like attributes that happen to be iterable.
            if not hasattr(block, 'as_pointer') and not hasattr(block, 'bl_rna'):
                continue
            ptr = _reference_datablock_pointer(block)
            if ptr in seen:
                continue
            seen.add(ptr)
            yield attr_name, block


def reference_library_external_reuse_reasons(import_id, block):
    """Return any untagged linked/override ID that makes Library removal unsafe.

    Blender's bpy.data.libraries.remove() is cascading: removing one Library can
    also remove every linked ID that points at it.  Therefore the preflight must
    inspect *all* bpy.data ID collections, not only datasets managed by this
    add-on.  Any untagged linked/override ID blocks cleanup before destructive
    removal begins.
    """
    reasons = []

    def uses_library(user):
        try:
            if getattr(user, 'library', None) == block:
                return True
        except Exception:
            pass
        try:
            override = getattr(user, 'override_library', None)
            reference = getattr(override, 'reference', None) if override is not None else None
            if reference is not None and getattr(reference, 'library', None) == block:
                return True
        except Exception:
            pass
        return False

    for dataset_name, user in _iter_all_bpy_data_ids():
        if user == block or not uses_library(user):
            continue
        if _block_reference_id(user) == import_id:
            continue
        reasons.append(
            f"external linked/override {dataset_name}:'{getattr(user, 'name', type(user).__name__)}'"
        )

    if bool(getattr(block, 'use_fake_user', False)):
        reasons.append('fake user enabled')
    return list(dict.fromkeys(reasons))


def reference_import_state_blockers(settings):
    reasons = []
    if getattr(settings, 'reference_collection', None) is not None:
        reasons.append('reference_collection ativa')
    if str(getattr(settings, 'reference_import_id', '') or ''):
        reasons.append('reference_import_id pendente')
    residual_ids = tagged_reference_import_ids()
    if residual_ids:
        reasons.append('datablocks tagged pendentes: ' + ', '.join(sorted(residual_ids)))
    if find_reference_master() is not None:
        reasons.append('master T7_BASE_REFERENCIA pendente')
    return reasons


def remove_reference_import(scene, settings):
    master = settings.reference_collection
    import_id = str(getattr(settings, 'reference_import_id', '') or '')

    if master is None and import_id:
        master = find_reference_master(import_id)
    if master is None:
        master = find_reference_master()

    if not import_id and master is not None:
        import_id = _block_reference_id(master)

    discovered_ids = tagged_reference_import_ids()
    if not import_id:
        if len(discovered_ids) == 1:
            import_id = next(iter(discovered_ids))
            master = master or find_reference_master(import_id)
        elif len(discovered_ids) > 1:
            return {
                'removed_objects': 0,
                'removed_total': 0,
                'failures': ['multiple residual reference import ids: ' + ', '.join(sorted(discovered_ids))],
                'residual': sum(len(tagged_reference_datablocks(item)) for item in discovered_ids),
            }
        elif master is None:
            return {'removed_objects': 0, 'removed_total': 0, 'failures': [], 'residual': 0}
        else:
            return {'removed_objects': 0, 'removed_total': 0, 'failures': ['import id ausente'], 'residual': 0}

    # Preflight destructive priority datablocks before deleting anything. If an
    # imported Object/Collection has been reused outside this import, fail
    # closed and preserve every tagged datablock and the import identity.
    priority = ('objects', 'collections', 'scenes')
    priority_blocks = []
    preflight_failures = []
    for dataset_name in priority:
        collection = getattr(bpy.data, dataset_name, None)
        if collection is None:
            continue
        for block in list(collection):
            if _block_reference_id(block) != import_id:
                continue
            priority_blocks.append((dataset_name, collection, block))
            reasons = reference_priority_external_reuse_reasons(
                scene, import_id, dataset_name, block, master
            )
            if reasons:
                preflight_failures.append(
                    f"external reuse {dataset_name}:{getattr(block, 'name', '?')}: " + '; '.join(reasons)
                )

    # A tagged Library can also be reused by an untagged/linked ID. Detect
    # that before deleting any imported Object/Collection so cleanup remains
    # all-or-nothing with respect to user-owned external reuse.
    libraries_collection = getattr(bpy.data, 'libraries', None)
    if libraries_collection is not None:
        for block in list(libraries_collection):
            if _block_reference_id(block) != import_id:
                continue
            reasons = reference_library_external_reuse_reasons(import_id, block)
            if reasons:
                preflight_failures.append(
                    f"external reuse libraries:{getattr(block, 'name', '?')}: " + '; '.join(reasons)
                )

    if preflight_failures:
        residual = len(tagged_reference_datablocks(import_id))
        return {
            'removed_objects': 0,
            'removed_total': 0,
            'failures': preflight_failures,
            'residual': residual,
        }

    removed_objects = 0
    removed_total = 0
    failures = []

    for dataset_name, collection, block in priority_blocks:
        try:
            try:
                collection.remove(block, do_unlink=True)
            except TypeError:
                collection.remove(block)
            removed_total += 1
            if dataset_name == 'objects':
                removed_objects += 1
        except Exception as exc:
            failures.append(f"{dataset_name}:{getattr(block, 'name', '?')}: {exc}")

    # Data datablocks are removed only when no user remains. This is fail-closed:
    # if somebody manually reused an imported mesh/material elsewhere, cleanup
    # refuses to destroy it and the reference state remains marked as partial.
    for _pass in range(4):
        progress = False
        for dataset_name, collection, block in list(tagged_reference_datablocks(import_id)):
            if dataset_name in priority or dataset_name == 'libraries':
                continue
            users = int(getattr(block, 'users', 0))
            if users != 0:
                continue
            try:
                try:
                    collection.remove(block, do_unlink=True)
                except TypeError:
                    collection.remove(block)
                removed_total += 1
                progress = True
            except Exception as exc:
                failures.append(f"{dataset_name}:{getattr(block, 'name', '?')}: {exc}")
        if not progress:
            break

    # Libraries are a Blender-specific special case: after append, Blender 5.0
    # can keep Library.users == 1 even after every imported local ID is gone.
    # Remove tagged Libraries last, but only after all other tagged IDs are gone
    # and user_map proves no external/untagged ID still uses them.
    remaining_before_libraries = [
        item for item in tagged_reference_datablocks(import_id)
        if item[0] != 'libraries'
    ]
    if not remaining_before_libraries:
        for dataset_name, collection, block in list(tagged_reference_datablocks(import_id)):
            if dataset_name != 'libraries':
                continue
            reasons = reference_library_external_reuse_reasons(import_id, block)
            if reasons:
                failures.append(
                    f"external reuse libraries:{getattr(block, 'name', '?')}: " + '; '.join(reasons)
                )
                continue
            try:
                collection.remove(block)
                removed_total += 1
            except Exception as exc:
                failures.append(f"libraries:{getattr(block, 'name', '?')}: {exc}")

    residual_blocks = tagged_reference_datablocks(import_id)
    residual = len(residual_blocks)
    if residual:
        for dataset_name, _collection, block in residual_blocks[:12]:
            failures.append(
                f"residual {dataset_name}:{getattr(block, 'name', '?')} users={getattr(block, 'users', '?')}"
            )

    # Also refuse to declare global cleanup complete if another older tagged
    # import is still present. Keep one residual identity reachable for retry.
    other_ids = sorted(tagged_reference_import_ids() - {import_id})
    if other_ids:
        failures.append('other residual reference import ids: ' + ', '.join(other_ids))
        residual += sum(len(tagged_reference_datablocks(item)) for item in other_ids)
        settings.reference_import_id = other_ids[0]
        settings.reference_collection = find_reference_master(other_ids[0])

    if not failures and residual == 0:
        settings.reference_collection = None
        settings.reference_source_path = ''
        settings.reference_import_id = ''
        settings.reference_imported_count = 0
        settings.reference_unit_system = ''
        settings.reference_scale_length = 1.0
    else:
        # Preserve/adopt the identity needed for a future cleanup retry.
        if not str(getattr(settings, 'reference_import_id', '') or ''):
            settings.reference_import_id = import_id
        if getattr(settings, 'reference_collection', None) is None:
            settings.reference_collection = find_reference_master(settings.reference_import_id)

    return {
        'removed_objects': removed_objects,
        'removed_total': removed_total,
        'failures': failures,
        'residual': residual,
    }


def find_object_state(settings, obj):
    ptr = object_pointer(obj)
    for item in settings.object_states:
        if item.object_ref is not None and object_pointer(item.object_ref) == ptr:
            return item
    return None


def clear_snapshot_data(settings, scene=None, delete_persistent=True):
    if delete_persistent and scene is not None:
        delete_persistent_snapshot(scene, settings)

    settings.object_states.clear()
    settings.modifier_states.clear()
    settings.snapshot_schema_version = 0
    settings.snapshot_active = False
    settings.displacement_applied = False
    settings.modifiers_currently_disabled = False
    settings.object_count = 0
    settings.target_count = 0
    settings.modifier_count = 0
    settings.disabled_modifier_count = 0
    settings.last_delta_x = 0.0
    settings.last_delta_y = 0.0
    settings.last_delta_z = 0.0
    settings.last_rotation_x = 0.0
    settings.last_rotation_y = 0.0
    settings.last_rotation_z = 0.0
    settings.last_scale_x = 1.0
    settings.last_scale_y = 1.0
    settings.last_scale_z = 1.0
    settings.snapshot_id = ''
    settings.snapshot_created_utc = ''
    settings.snapshot_scene_name = ''
    settings.snapshot_guide_name = ''
    settings.snapshot_base_name = ''
    settings.snapshot_target_collection_name = ''
    settings.snapshot_reference_collection_name = ''
    settings.snapshot_blend_path = ''
    settings.snapshot_file_sha256 = ''
    settings.snapshot_backup_path = ''
    settings.snapshot_checksum = ''
    settings.snapshot_external_ok = False
    settings.snapshot_persistence_warning = ''


def snapshot_runtime_compatible(settings):
    return bool(
        settings.snapshot_active
        and int(getattr(settings, 'snapshot_schema_version', 0)) == SNAPSHOT_SCHEMA_VERSION
        and bool(getattr(settings, 'snapshot_id', ''))
    )


def is_managed_transform_state(state):
    return bool(state.is_target and state.object_ref is not None)


def is_managed_modifier_state(settings, state):
    # Scope is immutable: it is frozen at Prepare and serialized in the snapshot.
    # Never recalculate it from the current base/reference/collection state.
    return bool(state.is_managed)


def find_saved_modifier(state):
    obj = state.object_ref
    if obj is None:
        return None
    if 0 <= state.modifier_index < len(obj.modifiers):
        candidate = obj.modifiers[state.modifier_index]
        if candidate.name == state.modifier_name and candidate.type == state.modifier_type:
            return candidate
    for candidate in obj.modifiers:
        if candidate.name == state.modifier_name and candidate.type == state.modifier_type:
            return candidate
    return None


def disable_modifiers_from_snapshot(settings):
    disabled = 0
    missing = 0
    for state in settings.modifier_states:
        if not state.is_managed:
            continue
        if state.object_ref is None:
            missing += 1
            continue
        modifier = find_saved_modifier(state)
        if modifier is None:
            missing += 1
            continue
        if not state.show_viewport:
            continue
        try:
            if modifier.show_viewport:
                modifier.show_viewport = False
                disabled += 1
        except Exception:
            missing += 1
    return disabled, missing


def restore_modifier_states(settings):
    missing = 0
    failed = 0
    restored = 0

    for state in settings.modifier_states:
        if not state.is_managed:
            continue
        if state.object_ref is None:
            missing += 1
            continue
        modifier = find_saved_modifier(state)
        if modifier is None:
            missing += 1
            continue
        try:
            modifier.show_viewport = state.show_viewport
            restored += 1
        except Exception:
            failed += 1
    return restored, missing, failed


def verify_modifier_states(settings):
    mismatches = []
    for state in settings.modifier_states:
        if not state.is_managed:
            continue
        if state.object_ref is None:
            mismatches.append(f"{state.object_name}/{state.modifier_name}: objeto ausente")
            continue
        modifier = find_saved_modifier(state)
        if modifier is None:
            mismatches.append(f"{state.object_name}/{state.modifier_name}: modifier ausente")
            continue
        try:
            current = bool(modifier.show_viewport)
        except Exception as exc:
            mismatches.append(f"{state.object_name}/{state.modifier_name}: leitura falhou ({exc})")
            continue
        if current != bool(state.show_viewport):
            mismatches.append(
                f"{state.object_name}/{state.modifier_name}: show_viewport={current}, esperado={bool(state.show_viewport)}"
            )
    return mismatches


def _object_transform_influence_reasons(obj):
    """Return dynamic influences that make channel-only world math unsafe.

    T7 intentionally computes world transforms from RNA channels instead of the
    depsgraph so hidden/excluded objects remain deterministic.  Therefore an
    object in a managed target's parent chain must not have constraints or
    animation that can rewrite those channels behind the add-on's back.

    Animation is blocked conservatively at the Object level: any Action, NLA
    track or driver on a target/ancestor makes exact transform preservation
    unverifiable.  This may reject animation of unrelated object properties, but
    failing closed is preferable to Finalize deleting the only checkpoint after
    a frame change silently moves part of the statue.
    """
    reasons = []
    try:
        constraints = list(getattr(obj, 'constraints', ()))
    except Exception as exc:
        return [f"constraints indisponíveis ({exc})"]
    if constraints:
        names = ', '.join(str(getattr(item, 'name', '?')) for item in constraints[:4])
        if len(constraints) > 4:
            names += ', …'
        reasons.append(f"{len(constraints)} constraint(s) ({names})")

    try:
        animation_data = getattr(obj, 'animation_data', None)
    except Exception as exc:
        reasons.append(f"animation_data indisponível ({exc})")
        return reasons
    if animation_data is not None:
        action = getattr(animation_data, 'action', None)
        if action is not None:
            reasons.append(f"Action '{getattr(action, 'name', '?')}'")
        try:
            nla_tracks = list(getattr(animation_data, 'nla_tracks', ()))
        except Exception:
            nla_tracks = [object()]
        if nla_tracks:
            reasons.append(f"{len(nla_tracks)} NLA track(s)")
        try:
            drivers = list(getattr(animation_data, 'drivers', ()))
        except Exception:
            drivers = [object()]
        if drivers:
            reasons.append(f"{len(drivers)} driver(s)")
    return reasons


def _armature_pose_constraint_reasons(armature_obj):
    """Return pose-bone constraints that can make BONE-parent math unsafe.

    Determining the exact dependency graph of IK/constraint chains is complex
    and easy to get wrong.  For a relevant Armature (it is itself a target or
    provides BONE parenting to one), v1.2.11 therefore fails closed if *any*
    pose bone has a constraint.  This covers ancestors, IK children and target
    armatures without pretending to solve Blender's pose dependency graph.
    """
    if getattr(armature_obj, 'type', '') != 'ARMATURE':
        return []
    try:
        pose = getattr(armature_obj, 'pose', None)
        bones = list(getattr(pose, 'bones', ())) if pose is not None else []
    except Exception as exc:
        return [f"pose bones indisponíveis ({exc})"]

    reasons = []
    for bone in bones:
        try:
            constraints = list(getattr(bone, 'constraints', ()))
        except Exception as exc:
            reasons.append(f"pose bone '{getattr(bone, 'name', '?')}': constraints indisponíveis ({exc})")
            continue
        if not constraints:
            continue
        names = ', '.join(str(getattr(item, 'name', '?')) for item in constraints[:4])
        if len(constraints) > 4:
            names += ', …'
        reasons.append(
            f"pose bone '{getattr(bone, 'name', '?')}': {len(constraints)} constraint(s) ({names})"
        )
    return reasons


def target_transform_influence_mismatches(target_objects):
    """Validate each target and its complete Object parent chain.

    N-31 showed that checking constraints only on targets is insufficient: an
    external parent constraint changes the evaluated world matrix while
    ``channel_world_matrix`` intentionally ignores it.  N-32 showed the same
    class of problem for animation.  Scan ancestors at every gate so influences
    added after Prepare are also caught before mutation/checkpoint deletion.
    """
    mismatches = []
    reported = set()
    for target in target_objects:
        if target is None:
            continue
        current = target
        chain_seen = set()
        child = None
        while current is not None:
            ptr = object_pointer(current)
            if ptr in chain_seen:
                mismatches.append(f"{target.name}: ciclo de parenting detectado")
                break
            chain_seen.add(ptr)

            reasons = _object_transform_influence_reasons(current)
            if reasons and ptr not in reported:
                relation = "alvo" if current == target else f"ancestral de '{target.name}'"
                mismatches.append(f"{current.name} ({relation}): " + '; '.join(reasons))
                reported.add(ptr)

            # N-35: a direct parent-bone-only scan misses constraints on bone
            # ancestors, IK descendants, and constraints elsewhere on an
            # Armature that is itself a managed target.  For a relevant
            # Armature, fail closed on any pose-bone constraint.
            armature_relevant = (
                getattr(current, 'type', '') == 'ARMATURE'
                and (
                    current == target
                    or (child is not None and getattr(child, 'parent_type', 'OBJECT') == 'BONE')
                )
            )
            if armature_relevant:
                key = ('armature_pose_constraints', ptr)
                if key not in reported:
                    pose_reasons = _armature_pose_constraint_reasons(current)
                    if pose_reasons:
                        relation = 'alvo' if current == target else f"armature BONE-parent de '{child.name}'"
                        mismatches.append(
                            f"{current.name} ({relation}): " + '; '.join(pose_reasons[:4])
                        )
                        reported.add(key)

            child = current
            current = current.parent
    return mismatches


def verify_target_transform_influences(settings):
    targets = [
        state.object_ref
        for state in settings.object_states
        if state.is_target and state.object_ref is not None
    ]
    return target_transform_influence_mismatches(targets)


def verify_target_constraints(settings):
    """Compatibility wrapper for older audit harnesses.

    v1.2.19 retains the broadened dynamic-influence check across each target's
    complete ancestry and relevant Armature pose constraints.
    """
    return verify_target_transform_influences(settings)


def clear_applied_pose_readbacks(settings):
    for state in settings.object_states:
        if not state.is_target:
            continue
        state.applied_world_valid = False
        state.applied_matrix_world = IDENTITY_MATRIX_FLAT


def capture_applied_pose_readbacks(settings):
    """Freeze the pose Blender actually stored after a verified Apply."""
    captured = []
    errors = []
    for state in settings.object_states:
        if not state.is_target or state.object_ref is None:
            continue
        try:
            actual = channel_world_matrix(state.object_ref)
            captured.append((state, matrix_to_flat(actual)))
        except Exception as exc:
            errors.append(f"{state.object_name}: pose aplicada não pôde ser relida ({exc})")
    if errors:
        clear_applied_pose_readbacks(settings)
        return errors
    for state, flat in captured:
        state.applied_matrix_world = flat
        state.applied_world_valid = True
    return []


def verify_current_applied_pose(settings):
    """Prove Finalize still sees the exact pose captured after Apply.

    v1.2.10 recomputed an ideal D@M0 matrix and compared it with Blender's
    float32 channel readback.  That rejected correct poses at production scale.
    v1.2.19 retains the *actual verified readback* after Apply and later
    compares Finalize against that representable pose.
    """
    if not bool(getattr(settings, 'displacement_applied', False)):
        return []

    mismatches = []
    for state in settings.object_states:
        if not state.is_target:
            continue
        obj = state.object_ref
        if obj is None:
            mismatches.append(f"{state.object_name}: objeto ausente ao verificar a pose aplicada")
            continue
        if not bool(getattr(state, 'applied_world_valid', False)):
            mismatches.append(
                f"{state.object_name}: readback da última transformação aplicada não está disponível; "
                "Finalize bloqueado para preservar o checkpoint"
            )
            continue
        expected = flat_to_matrix(state.applied_matrix_world)
        try:
            actual = channel_world_matrix(obj)
        except Exception as exc:
            mismatches.append(f"{obj.name}: pose atual não pôde ser relida ({exc})")
            continue
        if not matrices_close_applied_readback(actual, expected):
            max_diff, component_tol, diff_row, diff_col = _matrix_float32_max_diff_detail(
                actual,
                expected,
                linear_ulps=0.5,
                linear_abs_tol=MATRIX_ABS_TOLERANCE,
                translation_ulps=0.5,
            )
            mismatches.append(
                f"{obj.name}: pose atual diverge do readback aplicado "
                f"(diferença={max_diff:.3e} em [{diff_row}][{diff_col}], "
                f"tol_componente={component_tol:.3e})"
            )
    return mismatches


def verify_geometry_sentinels(settings):
    mismatches = []
    for state in settings.object_states:
        if not state.is_target:
            continue
        obj = state.object_ref
        if obj is None:
            mismatches.append(f"{state.object_name}: objeto ausente para sentinel de geometria")
            continue

        if state.geometry_sentinel_supported:
            supported, kind, digest = geometry_sentinel(obj)
            if not supported:
                mismatches.append(f"{obj.name}: sentinel {state.geometry_sentinel_kind} indisponível")
                continue
            if kind != state.geometry_sentinel_kind or digest != state.geometry_sentinel_hash:
                mismatches.append(f"{obj.name}: origin/geometria local divergente")
            continue

        # Schema v6 never claims exact geometry verification for an unsupported
        # geometry-bearing target.  Only the explicit no-local-geometry allowlist
        # may legitimately have no fingerprint.
        if obj.type not in NON_GEOMETRY_OBJECT_TYPES:
            mismatches.append(f"{obj.name}: tipo {obj.type} sem sentinel verificável")
    return mismatches

def restore_hierarchy_and_transforms(settings):
    """Restore the exact frozen hierarchy and transform channels."""
    failed = []
    missing = []
    valid_states = []
    for state in settings.object_states:
        if not state.is_target:
            continue
        obj = state.object_ref
        if obj is None:
            missing.append(state.object_name)
            continue
        valid_states.append(state)

    for state in valid_states:
        obj = state.object_ref
        desired_parent = state.parent_ref if state.had_parent else None
        try:
            if state.had_parent and desired_parent is None:
                raise RuntimeError('original parent no longer exists')
            obj.parent = desired_parent
            # These fields are frozen even when parent is None. Restore them
            # unconditionally so a later parent assignment cannot inherit stale
            # metadata that differs from the Prepare checkpoint.
            obj.parent_type = state.parent_type
            obj.parent_bone = state.parent_bone
            obj.parent_vertices = tuple(state.parent_vertices)
            obj.matrix_parent_inverse = flat_to_matrix(state.matrix_parent_inverse)
        except Exception as exc:
            failed.append(f"{obj.name}: parent ({exc})")

    for state in valid_states:
        obj = state.object_ref
        try:
            obj.rotation_mode = state.rotation_mode
            obj.location = tuple(state.location)
            obj.scale = tuple(state.scale)
            obj.delta_location = tuple(state.delta_location)
            obj.delta_scale = tuple(state.delta_scale)

            # Restore inactive rotation representations first and the active one
            # last, so the active representation controls the final transform.
            if state.rotation_mode == 'QUATERNION':
                obj.rotation_euler = tuple(state.rotation_euler)
                obj.rotation_axis_angle = tuple(state.rotation_axis_angle)
                obj.rotation_quaternion = tuple(state.rotation_quaternion)
            elif state.rotation_mode == 'AXIS_ANGLE':
                obj.rotation_euler = tuple(state.rotation_euler)
                obj.rotation_quaternion = tuple(state.rotation_quaternion)
                obj.rotation_axis_angle = tuple(state.rotation_axis_angle)
            else:
                obj.rotation_quaternion = tuple(state.rotation_quaternion)
                obj.rotation_axis_angle = tuple(state.rotation_axis_angle)
                obj.rotation_euler = tuple(state.rotation_euler)

            if state.rotation_mode == 'QUATERNION':
                obj.delta_rotation_euler = tuple(state.delta_rotation_euler)
                obj.delta_rotation_quaternion = tuple(state.delta_rotation_quaternion)
            else:
                obj.delta_rotation_quaternion = tuple(state.delta_rotation_quaternion)
                obj.delta_rotation_euler = tuple(state.delta_rotation_euler)
        except Exception as exc:
            failed.append(f"{obj.name}: transform ({exc})")
    return missing, failed


def verify_applied_channel_matrices(expected_local_matrices, tolerance=None):
    """Historical/diagnostic matrix_basis verifier retained for audits.

    v1.2.19 no longer uses recomposed matrix_basis as the blocking Apply gate
    because Blender stores TRS channels and can legitimately recompose a matrix
    outside this per-element budget at large scale or near gimbal lock (N-45).

    ``expected_local_matrices`` is a sequence of ``(object, expected_basis)``
    captured from the same parent prefix used by ``set_channel_world_matrix``.
    This is intentionally independent of reconstructed world components: large
    translated/rotated parent chains can redistribute normal float32 error
    across world axes (N-42), while the stored matrix_basis is the value Blender
    directly quantizes.
    """
    mismatches = []
    for obj, expected in expected_local_matrices:
        if obj is None:
            mismatches.append("objeto ausente ao verificar matrix_basis aplicada")
            continue
        try:
            actual = obj.matrix_basis.copy()
        except Exception as exc:
            mismatches.append(f"{getattr(obj, 'name', '<objeto>')}: matrix_basis indisponível ({exc})")
            continue

        if tolerance is None:
            close = matrices_close_channel_roundtrip(actual, expected)
        else:
            close = matrices_close(actual, expected, abs_tol=float(tolerance), rel_tol=0.0)

        if close:
            continue

        if tolerance is None:
            ratio, diff, component_tol, row, col = _matrix_channel_max_ratio_detail(
                actual, expected
            )
        else:
            diffs = [
                (
                    abs(float(actual[row][col]) - float(expected[row][col])),
                    row,
                    col,
                )
                for row in range(4)
                for col in range(4)
            ]
            diff, row, col = max(diffs, key=lambda item: item[0])
            component_tol = float(tolerance)
            ratio = diff / component_tol if component_tol > 0.0 else float('inf')

        mismatches.append(
            f"{obj.name}: diferença matrix_basis={diff:.3e} em [{row}][{col}] "
            f"(tol_componente={component_tol:.3e}, razão={ratio:.2f})"
        )
    return mismatches


def verify_applied_world_matrices(settings, transform_delta, tolerance=None):
    """Diagnostic comparison of reconstructed world against ideal D@M0.

    v1.2.19 deliberately does **not** use this function as the blocking Apply
    precision gate.  Blender stores float32 transform channels; multiplying a
    large translated child through a 3D-rotated parent can move legitimate
    rounding from one world axis into another (N-42).  This helper remains for
    audits/diagnostics and historical N-38/N-39/N-40 probes only.
    """
    mismatches = []
    for state in settings.object_states:
        if not state.is_target or state.object_ref is None:
            continue
        expected = transform_delta @ flat_to_matrix(state.matrix_world)
        try:
            actual = channel_world_matrix(state.object_ref)
        except Exception as exc:
            mismatches.append(f"{state.object_ref.name}: world por canais indisponível ({exc})")
            continue
        if tolerance is None:
            close = matrices_close_float32_roundtrip(
                actual,
                expected,
                linear_ulps=8.0,
                translation_ulps=4.0,
                linear_abs_tol=MATRIX_LINEAR_APPLY_ABS_TOLERANCE,
            )
        else:
            close = matrices_close(actual, expected, abs_tol=float(tolerance), rel_tol=0.0)
        if not close:
            if tolerance is None:
                max_diff, component_tol, diff_row, diff_col = _matrix_float32_max_diff_detail(
                    actual,
                    expected,
                    linear_ulps=8.0,
                    linear_abs_tol=MATRIX_LINEAR_APPLY_ABS_TOLERANCE,
                    translation_ulps=4.0,
                )
            else:
                diffs = [
                    (
                        abs(float(actual[row][col]) - float(expected[row][col])),
                        row,
                        col,
                    )
                    for row in range(4)
                    for col in range(4)
                ]
                max_diff, diff_row, diff_col = max(diffs, key=lambda item: item[0])
                component_tol = float(tolerance)
            mismatches.append(
                f"{state.object_ref.name}: diferença world calculada={max_diff:.3e} "
                f"em [{diff_row}][{diff_col}] (tol_componente={component_tol:.3e})"
            )
    return mismatches

def _seq_close(actual, expected, tolerance=None):
    try:
        if len(actual) != len(expected):
            return False
        return all(_matrix_component_close(a, e) for a, e in zip(actual, expected))
    except Exception:
        return False

def verify_restored_snapshot_fields(settings, tolerance=None):
    mismatches = []
    for state in settings.object_states:
        if not state.is_target:
            continue
        obj = state.object_ref
        if obj is None:
            mismatches.append(f"{state.object_name}: objeto ausente")
            continue

        expected_parent = state.parent_ref if state.had_parent else None
        if obj.parent != expected_parent:
            mismatches.append(f"{obj.name}: parent divergente")
        if obj.parent_type != state.parent_type:
            mismatches.append(f"{obj.name}: parent_type divergente")
        if obj.parent_bone != state.parent_bone:
            mismatches.append(f"{obj.name}: parent_bone divergente")
        if tuple(obj.parent_vertices) != tuple(state.parent_vertices):
            mismatches.append(f"{obj.name}: parent_vertices divergente")

        if not _seq_close(matrix_to_flat(obj.matrix_parent_inverse), state.matrix_parent_inverse):
            mismatches.append(f"{obj.name}: matrix_parent_inverse divergente")
        if obj.rotation_mode != state.rotation_mode:
            mismatches.append(f"{obj.name}: rotation_mode divergente")
        checks = (
            ('location', obj.location, state.location),
            ('rotation_euler', obj.rotation_euler, state.rotation_euler),
            ('rotation_quaternion', obj.rotation_quaternion, state.rotation_quaternion),
            ('rotation_axis_angle', obj.rotation_axis_angle, state.rotation_axis_angle),
            ('scale', obj.scale, state.scale),
            ('delta_location', obj.delta_location, state.delta_location),
            ('delta_rotation_euler', obj.delta_rotation_euler, state.delta_rotation_euler),
            ('delta_rotation_quaternion', obj.delta_rotation_quaternion, state.delta_rotation_quaternion),
            ('delta_scale', obj.delta_scale, state.delta_scale),
        )
        for label, actual, expected in checks:
            if not _seq_close(actual, expected):
                mismatches.append(f"{obj.name}: {label} divergente")
        try:
            actual_world = matrix_to_flat(channel_world_matrix(obj))
            if not _seq_close(actual_world, state.matrix_world):
                mismatches.append(f"{obj.name}: matrix_world calculada divergente")
        except Exception as exc:
            mismatches.append(f"{obj.name}: matrix_world calculada indisponível ({exc})")
    return mismatches

def verify_restored_world_matrices(settings, tolerance=1.0e-5):
    # Compatibility wrapper retained for older audit harnesses.
    return [item for item in verify_restored_snapshot_fields(settings, tolerance) if 'matrix_world' in item]


def validate_snapshot_for_apply(scene, settings):
    errors = []

    guide = settings.guide_object
    if guide is None:
        errors.append("Objeto-guia não definido.")
        return errors

    guide_state = find_object_state(settings, guide)
    if guide_state is None:
        errors.append("O objeto-guia não existe no snapshot.")
        return errors

    saved_target_ptrs = {
        object_pointer(item.object_ref)
        for item in settings.object_states
        if item.is_target and item.object_ref is not None
    }
    current_target_ptrs = target_object_pointers(scene, settings)
    if saved_target_ptrs != current_target_ptrs:
        errors.append(
            "A lista de objetos-alvo mudou desde o snapshot (objeto/collection adicionado, removido ou hierarquia da base alterada)."
        )

    influence_errors = verify_target_transform_influences(settings)
    if influence_errors:
        errors.extend(
            "Influência dinâmica em alvo/ancestral: " + message
            for message in influence_errors[:12]
        )
        return errors

    for item in settings.object_states:
        if not item.is_target:
            continue
        obj = item.object_ref
        if obj is None:
            errors.append(f"Objeto do snapshot foi removido: {item.object_name}")
            continue

        expected_parent = item.parent_ref if item.had_parent else None
        if item.had_parent and expected_parent is None:
            errors.append(f"Parent original de '{item.object_name}' não existe mais.")
            continue
        if obj.parent != expected_parent:
            errors.append(f"Parent de '{obj.name}' foi alterado.")
        if obj.parent_type != item.parent_type or obj.parent_bone != item.parent_bone:
            errors.append(f"Tipo/bone parent de '{obj.name}' foi alterado.")
        if tuple(obj.parent_vertices) != tuple(item.parent_vertices):
            errors.append(f"Parent vertices de '{obj.name}' foram alterados.")
        if not _seq_close(matrix_to_flat(obj.matrix_parent_inverse), item.matrix_parent_inverse):
            errors.append(f"matrix_parent_inverse de '{obj.name}' foi alterada.")
        try:
            channel_world_matrix(obj)
        except Exception as exc:
            errors.append(f"Transformação por canais de '{obj.name}' indisponível: {exc}")

        if len(errors) >= 12:
            errors.append("Há mais alterações; validação interrompida para manter a mensagem curta.")
            break

    if errors:
        return errors

    geometry_errors = verify_geometry_sentinels(settings)
    if geometry_errors:
        errors.extend(geometry_errors[:12])
        return errors

    saved_mods_by_ptr = {}
    for mod_state in settings.modifier_states:
        if mod_state.object_ref is None:
            continue
        ptr = object_pointer(mod_state.object_ref)
        saved_mods_by_ptr.setdefault(ptr, []).append((mod_state.modifier_name, mod_state.modifier_type))

    for item in settings.object_states:
        if not item.is_target or item.object_ref is None:
            continue
        obj = item.object_ref
        saved_signatures = sorted(saved_mods_by_ptr.get(object_pointer(obj), []))
        current_signatures = sorted((modifier.name, modifier.type) for modifier in obj.modifiers)
        if saved_signatures != current_signatures:
            errors.append(f"A lista de modifiers de '{obj.name}' mudou desde Preparar.")
            if len(errors) >= 12:
                break

    if errors:
        return errors

    saved_guide_world = flat_to_matrix(guide_state.matrix_world)
    try:
        current_guide_world = channel_world_matrix(guide)
        delta = guide_delta_matrix(saved_guide_world, current_guide_world)
        if not matrix_is_positive_uniform_similarity(delta) and not matrix_is_identity(delta):
            errors.append(
                "A transformação relativa do guia contém shear/escala não uniforme, possivelmente herdada de um parent."
            )
    except ValueError as exc:
        errors.append(str(exc))

    return errors

def disable_modifiers_after_snapshot(settings):
    disabled, _missing = disable_modifiers_from_snapshot(settings)
    return disabled


# -----------------------------------------------------------------------------
# Snapshot data
# -----------------------------------------------------------------------------


class T7SM_ModifierState(PropertyGroup):
    is_managed: BoolProperty(default=False)
    object_ref: PointerProperty(type=bpy.types.Object)
    object_name: StringProperty()
    modifier_name: StringProperty()
    modifier_type: StringProperty()
    modifier_index: IntProperty(default=-1)
    show_viewport: BoolProperty(default=True)


class T7SM_ObjectState(PropertyGroup):
    object_ref: PointerProperty(type=bpy.types.Object)
    object_name: StringProperty()
    object_type: StringProperty(default="")
    data_name: StringProperty(default="")
    is_target: BoolProperty(default=False)

    had_parent: BoolProperty(default=False)
    parent_ref: PointerProperty(type=bpy.types.Object)
    parent_name: StringProperty(default="")
    parent_type: StringProperty(default="OBJECT")
    parent_bone: StringProperty(default="")
    parent_vertices: IntVectorProperty(size=3, default=(0, 0, 0))
    matrix_parent_inverse: FloatVectorProperty(size=16, default=IDENTITY_MATRIX_FLAT)

    location: FloatVectorProperty(size=3)
    rotation_mode: StringProperty(default="XYZ")
    rotation_euler: FloatVectorProperty(size=3)
    rotation_quaternion: FloatVectorProperty(size=4, default=(1, 0, 0, 0))
    rotation_axis_angle: FloatVectorProperty(size=4, default=(0, 0, 1, 0))
    scale: FloatVectorProperty(size=3, default=(1, 1, 1))

    delta_location: FloatVectorProperty(size=3)
    delta_rotation_euler: FloatVectorProperty(size=3)
    delta_rotation_quaternion: FloatVectorProperty(size=4, default=(1, 0, 0, 0))
    delta_scale: FloatVectorProperty(size=3, default=(1, 1, 1))

    matrix_world: FloatVectorProperty(size=16, default=IDENTITY_MATRIX_FLAT)
    world_matrix_verified: BoolProperty(default=True)
    applied_world_valid: BoolProperty(default=False)
    applied_matrix_world: FloatVectorProperty(size=16, default=IDENTITY_MATRIX_FLAT)

    mesh_sentinel_valid: BoolProperty(default=False)
    mesh_vertex_count: IntProperty(default=0)
    mesh_sample_indices: IntVectorProperty(size=4, default=(0, 0, 0, 0))
    mesh_sample_coords: FloatVectorProperty(size=12, default=(0.0,) * 12)
    geometry_sentinel_supported: BoolProperty(default=False)
    geometry_sentinel_kind: StringProperty(default="")
    geometry_sentinel_hash: StringProperty(default="")


class T7SM_AddonPreferences(AddonPreferences):
    bl_idname = addon_module_id()

    reference_blend_path: StringProperty(
        name="Arquivo-base / referência",
        description="Arquivo .blend fixo que contém a base católica e o modelo de referência",
        subtype='FILE_PATH',
        default="",
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Compatibilidade alvo: Blender 5.0.0")
        layout.prop(self, "reference_blend_path")
        bundled = os.path.join(os.path.dirname(__file__), BUNDLED_REFERENCE_RELATIVE)
        if os.path.isfile(bundled):
            layout.label(text="Um arquivo-base embutido no addon terá prioridade.", icon='CHECKMARK')


class T7SM_Settings(PropertyGroup):
    guide_object: PointerProperty(
        name="Objeto-guia",
        description="Corpo final que será movido manualmente até a base",
        type=bpy.types.Object,
    )
    base_object: PointerProperty(
        name="Base / objeto fixo",
        description="Este objeto e seus filhos não serão movidos nem terão modifiers desligados",
        type=bpy.types.Object,
    )
    target_collection: PointerProperty(
        name="Collection da estátua",
        description="Collection cujos objetos serão movidos, incluindo subcollections desativadas. Vazio = cena inteira",
        type=bpy.types.Collection,
    )
    reference_collection: PointerProperty(
        name="Base/Referência importada",
        description="Collection fixa criada pelo addon ao importar o arquivo-base",
        type=bpy.types.Collection,
    )

    snapshot_schema_version: IntProperty(default=0)
    snapshot_active: BoolProperty(default=False)
    displacement_applied: BoolProperty(default=False)
    modifiers_currently_disabled: BoolProperty(default=False)

    object_states: CollectionProperty(type=T7SM_ObjectState)
    modifier_states: CollectionProperty(type=T7SM_ModifierState)

    object_count: IntProperty(default=0)
    target_count: IntProperty(default=0)
    modifier_count: IntProperty(default=0)
    disabled_modifier_count: IntProperty(default=0)

    snapshot_id: StringProperty(default="")
    snapshot_created_utc: StringProperty(default="")
    snapshot_scene_name: StringProperty(default="")
    snapshot_guide_name: StringProperty(default="")
    snapshot_base_name: StringProperty(default="")
    snapshot_target_collection_name: StringProperty(default="")
    snapshot_reference_collection_name: StringProperty(default="")
    snapshot_blend_path: StringProperty(default="")
    snapshot_file_sha256: StringProperty(default="")
    snapshot_backup_path: StringProperty(default="")
    snapshot_checksum: StringProperty(default="")
    snapshot_external_ok: BoolProperty(default=False)
    snapshot_persistence_warning: StringProperty(default="")

    reference_source_path: StringProperty(default="")
    reference_import_id: StringProperty(default="")
    reference_imported_count: IntProperty(default=0)
    reference_unit_system: StringProperty(default="")
    reference_scale_length: FloatProperty(default=1.0)

    last_delta_x: FloatProperty(default=0.0)
    last_delta_y: FloatProperty(default=0.0)
    last_delta_z: FloatProperty(default=0.0)
    last_rotation_x: FloatProperty(default=0.0)
    last_rotation_y: FloatProperty(default=0.0)
    last_rotation_z: FloatProperty(default=0.0)
    last_scale_x: FloatProperty(default=1.0)
    last_scale_y: FloatProperty(default=1.0)
    last_scale_z: FloatProperty(default=1.0)


# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------


class T7SM_OT_ChooseReferenceBlend(Operator):
    bl_idname = "t7sm.choose_reference_blend"
    bl_label = "Escolher arquivo-base"
    bl_description = "Seleciona o .blend fixo que contém a base católica e o modelo de referência"

    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default="*.blend", options={'HIDDEN'})

    def invoke(self, context, event):
        prefs = get_addon_preferences(context)
        if prefs is not None and prefs.reference_blend_path:
            self.filepath = bpy.path.abspath(prefs.reference_blend_path)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        path = os.path.abspath(bpy.path.abspath(self.filepath))
        if not os.path.isfile(path) or not path.lower().endswith('.blend'):
            self.report({'ERROR'}, "Selecione um arquivo .blend válido.")
            return {'CANCELLED'}
        prefs = get_addon_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Preferências do addon não estão disponíveis.")
            return {'CANCELLED'}
        prefs.reference_blend_path = path
        self.report({'INFO'}, "Arquivo-base configurado.")
        return {'FINISHED'}


class T7SM_OT_ImportReference(Operator):
    bl_idname = "t7sm.import_reference"
    bl_label = "Importar Base + Referência"
    bl_description = "Anexa o arquivo-base como uma collection fixa, preservando as transformações originais"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        settings = scene.t7sm_settings
        if settings.snapshot_active:
            self.report({'ERROR'}, "Finalize ou restaure o snapshot antes de importar/remover a referência.")
            return {'CANCELLED'}
        blockers = reference_import_state_blockers(settings)
        if blockers:
            self.report(
                {'ERROR'},
                "Existe uma importação/cleanup de referência pendente. Use 'Remover Base + Referência' "
                "e resolva todos os resíduos antes de importar novamente. " + blockers[0]
            )
            return {'CANCELLED'}

        path = reference_source_path(context)
        if not path or not os.path.isfile(path):
            self.report({'ERROR'}, "Configure um arquivo-base .blend nas preferências/ botão Escolher arquivo-base.")
            return {'CANCELLED'}
        if current_blend_path() and os.path.normcase(path) == os.path.normcase(current_blend_path()):
            self.report({'ERROR'}, "O arquivo-base não pode ser o mesmo .blend que está aberto.")
            return {'CANCELLED'}

        loaded_scene = None
        master = None
        import_id = hashlib.sha256((path + utc_now_iso()).encode('utf-8')).hexdigest()[:20]
        settings.reference_import_id = import_id
        before_datablocks = capture_reference_datablocks()
        try:
            with bpy.data.libraries.load(path, link=False) as (data_from, data_to):
                if not data_from.scenes:
                    raise RuntimeError("o arquivo-base não contém Scene")
                if len(data_from.scenes) != 1:
                    raise RuntimeError(
                        "o arquivo-base contém múltiplas Scenes; mantenha exatamente uma Scene para uma importação determinística"
                    )
                data_to.scenes = [data_from.scenes[0]]

            loaded_scene = data_to.scenes[0] if data_to.scenes else None
            if loaded_scene is None:
                raise RuntimeError("não foi possível anexar a Scene do arquivo-base")

            # Tag every newly appended ID datablock immediately, before any other
            # operation can fail. Cleanup can therefore be precise and observable.
            tag_new_reference_datablocks(before_datablocks, import_id)

            source_unit_system = loaded_scene.unit_settings.system
            source_scale_length = float(loaded_scene.unit_settings.scale_length)
            source_objects = list(loaded_scene.objects)
            source_children = list(loaded_scene.collection.children)
            source_direct_objects = list(loaded_scene.collection.objects)

            master = bpy.data.collections.new(REFERENCE_MASTER_NAME)
            master[REFERENCE_MASTER_TAG] = True
            master[REFERENCE_TAG_KEY] = import_id
            master["t7sm_source_blend"] = path
            master.hide_render = True
            scene.collection.children.link(master)

            for obj in source_direct_objects:
                if obj.name not in master.objects:
                    master.objects.link(obj)

            imported_collections = []
            for child in source_children:
                if child.name not in master.children:
                    master.children.link(child)
                imported_collections.extend(list(iter_collection_tree(child)))

            for col in imported_collections:
                col[REFERENCE_TAG_KEY] = import_id
            for obj in source_objects:
                obj[REFERENCE_TAG_KEY] = import_id
                obj.hide_select = True

            settings.reference_collection = master
            settings.reference_source_path = path
            settings.reference_imported_count = len(source_objects)
            settings.reference_unit_system = source_unit_system
            settings.reference_scale_length = source_scale_length

            bpy.data.scenes.remove(loaded_scene)
            loaded_scene = None

            mismatch = (
                scene.unit_settings.system != source_unit_system
                or abs(float(scene.unit_settings.scale_length) - source_scale_length) > 1.0e-9
            )
            if mismatch:
                self.report(
                    {'WARNING'},
                    f"Base/referência importada ({len(source_objects)} objetos), mas as unidades da Scene atual diferem do arquivo-base."
                )
            else:
                self.report({'INFO'}, f"Base/referência importada: {len(source_objects)} objetos fixos.")
            return {'FINISHED'}

        except Exception as exc:
            if loaded_scene is not None:
                try:
                    bpy.data.scenes.remove(loaded_scene)
                except Exception:
                    pass
            if master is not None:
                settings.reference_collection = master
            cleanup = remove_reference_import(scene, settings)
            if cleanup['failures'] or cleanup['residual']:
                self.report(
                    {'ERROR'},
                    f"Falha ao importar base/referência: {exc}. Cleanup PARCIAL; "
                    f"resíduos={cleanup['residual']}, falhas={len(cleanup['failures'])}. Estado preservado para nova tentativa."
                )
            else:
                self.report({'ERROR'}, f"Falha ao importar base/referência: {exc}. Cleanup concluído.")
            return {'CANCELLED'}


class T7SM_OT_RemoveReference(Operator):
    bl_idname = "t7sm.remove_reference"
    bl_label = "Remover Base + Referência"
    bl_description = "Remove somente os objetos/collections importados pelo T7 Statue Mover"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.t7sm_settings
        if settings.snapshot_active:
            self.report({'ERROR'}, "Finalize ou restaure o snapshot antes de remover a referência.")
            return {'CANCELLED'}
        result = remove_reference_import(context.scene, settings)
        if result['failures'] or result['residual']:
            self.report(
                {'ERROR'},
                f"Remoção incompleta: {result['removed_objects']} objetos removidos, "
                f"resíduos={result['residual']}, falhas={len(result['failures'])}. Marcadores preservados."
            )
            return {'CANCELLED'}
        if result['removed_objects'] <= 0:
            self.report({'WARNING'}, "Nenhuma base/referência do addon foi encontrada.")
        else:
            self.report({'INFO'}, f"Base/referência removida: {result['removed_objects']} objetos; cleanup completo.")
        return {'FINISHED'}


class T7SM_OT_Prepare(Operator):
    bl_idname = "t7sm.prepare"
    bl_label = "Preparar Estátua"
    bl_description = "Salva o estado inicial e desliga temporariamente os modifiers da viewport"

    def execute(self, context):
        scene = context.scene
        settings = scene.t7sm_settings

        if settings.snapshot_active:
            self.report({'ERROR'}, "Já existe um snapshot ativo. Finalize ou restaure antes de preparar novamente.")
            return {'CANCELLED'}

        # Cross-session recovery is a hard requirement. Prepare only from a
        # real, already-saved and clean .blend whose bytes can be read/hash-
        # verified BEFORE any modifier or snapshot state is mutated.
        if bool(getattr(bpy.data, 'is_dirty', False)):
            self.report({'ERROR'}, "O .blend possui alterações não salvas. Salve o arquivo antes de Preparar Estátua para criar um baseline externo recuperável.")
            return {'CANCELLED'}
        try:
            prepared_blend_path, prepared_file_sha = saved_blend_identity_preflight()
        except Exception as exc:
            self.report({'ERROR'}, f"Preparação recusada: {exc}")
            return {'CANCELLED'}

        guide = settings.guide_object
        if guide is None:
            self.report({'ERROR'}, "Defina o objeto-guia primeiro.")
            return {'CANCELLED'}
        if guide.mode != 'OBJECT':
            self.report({'ERROR'}, "O objeto-guia precisa estar em Object Mode antes de preparar.")
            return {'CANCELLED'}

        objs = scene_objects(scene)
        scene_ptrs = {object_pointer(obj) for obj in objs}
        if object_pointer(guide) not in scene_ptrs:
            self.report({'ERROR'}, "O objeto-guia não pertence à cena atual.")
            return {'CANCELLED'}

        fixed = fixed_object_pointers(settings)
        if object_pointer(guide) in fixed:
            self.report({'ERROR'}, "O objeto-guia está dentro da hierarquia fixa da base. Escolha objetos diferentes.")
            return {'CANCELLED'}

        targets = target_object_pointers(scene, settings)
        if not targets:
            self.report({'ERROR'}, "Nenhum objeto-alvo encontrado.")
            return {'CANCELLED'}

        # Fail before any mutation if a target or any of its ancestors has a
        # dynamic transform influence (constraint/animation), cannot be
        # represented without depsgraph matrix_world, or cannot be geometry-
        # verified later.
        by_ptr = {object_pointer(obj): obj for obj in objs}
        target_objects = []
        for ptr in targets:
            obj = by_ptr.get(ptr)
            if obj is None:
                self.report({'ERROR'}, "Objeto-alvo desapareceu antes do snapshot.")
                return {'CANCELLED'}
            target_objects.append(obj)

        influence_errors = target_transform_influence_mismatches(target_objects)
        if influence_errors:
            self.report(
                {'ERROR'},
                "Preparação recusada: alvo/ancestral possui constraint ou animação que torna a transformação não verificável. "
                + influence_errors[0]
            )
            return {'CANCELLED'}

        for obj in target_objects:
            try:
                channel_world_matrix(obj)
            except Exception as exc:
                self.report({'ERROR'}, f"Não é possível calcular a transformação segura de '{obj.name}': {exc}")
                return {'CANCELLED'}
            supported, kind, _digest = geometry_sentinel(obj)
            if not supported and obj.type not in NON_GEOMETRY_OBJECT_TYPES:
                self.report(
                    {'ERROR'},
                    f"O tipo geométrico {obj.type} de '{obj.name}' ainda não possui fingerprint seguro nesta versão. "
                    "Preparação cancelada para não prometer restauração exata."
                )
                return {'CANCELLED'}

        # Reset only runtime snapshot fields. Do not delete any older external
        # file before the replacement baseline is fully committed and validated.
        _remove_embedded_snapshot_key(scene)
        clear_snapshot_data(settings, scene, delete_persistent=False)
        settings.snapshot_id = uuid.uuid4().hex
        settings.snapshot_created_utc = utc_now_iso()
        settings.snapshot_scene_name = scene.name
        settings.snapshot_guide_name = guide.name
        settings.snapshot_base_name = settings.base_object.name if settings.base_object is not None else ''
        settings.snapshot_target_collection_name = settings.target_collection.name if settings.target_collection is not None else ''
        settings.snapshot_reference_collection_name = settings.reference_collection.name if settings.reference_collection is not None else ''

        # Freeze all current-scene object transform states, including objects in
        # hidden/excluded child collections.  This capture phase itself is
        # transactional: no modifier has been changed yet, so any unexpected
        # exception must leave no partial object_states/snapshot_id behind.
        try:
            for obj in objs:
                item = settings.object_states.add()
                item.object_ref = obj
                item.object_name = obj.name
                item.object_type = obj.type
                item.data_name = getattr(getattr(obj, "data", None), "name", "") or ""
                item.is_target = object_pointer(obj) in targets

                item.had_parent = obj.parent is not None
                if obj.parent is not None:
                    item.parent_ref = obj.parent
                    item.parent_name = obj.parent.name
                else:
                    item.parent_name = ''
                item.parent_type = obj.parent_type
                item.parent_bone = obj.parent_bone
                item.parent_vertices = tuple(obj.parent_vertices)
                item.matrix_parent_inverse = matrix_to_flat(obj.matrix_parent_inverse)

                item.location = tuple(obj.location)
                item.rotation_mode = obj.rotation_mode
                item.rotation_euler = tuple(obj.rotation_euler)
                item.rotation_quaternion = tuple(obj.rotation_quaternion)
                item.rotation_axis_angle = tuple(obj.rotation_axis_angle)
                item.scale = tuple(obj.scale)

                item.delta_location = tuple(obj.delta_location)
                item.delta_rotation_euler = tuple(obj.delta_rotation_euler)
                item.delta_rotation_quaternion = tuple(obj.delta_rotation_quaternion)
                item.delta_scale = tuple(obj.delta_scale)

                try:
                    frozen_world = channel_world_matrix(obj)
                    item.world_matrix_verified = True
                except Exception:
                    # Only targets are required to be channel-verifiable (preflight
                    # above guarantees that). Unrelated Scene objects are retained
                    # for identity/topology but must not break Prepare.
                    frozen_world = obj.matrix_world.copy()
                    item.world_matrix_verified = False
                item.matrix_world = matrix_to_flat(frozen_world)
                item.applied_world_valid = False
                item.applied_matrix_world = IDENTITY_MATRIX_FLAT

                # N-30: mesh_geometry_sentinel() has returned (valid, digest)
                # since v1.2.9.  The old four-sample properties remain only for
                # schema-v6 compatibility; derive neutral legacy metadata from
                # the already-computed full geometry sentinel instead of calling
                # the old four-value API.
                geom_supported, geom_kind, geom_hash = geometry_sentinel(obj)
                is_mesh_sentinel = bool(geom_supported and geom_kind == 'MESH')
                item.mesh_sentinel_valid = is_mesh_sentinel
                item.mesh_vertex_count = (
                    len(obj.data.vertices)
                    if is_mesh_sentinel and getattr(obj, 'data', None) is not None
                    else 0
                )
                item.mesh_sample_indices = (0, 0, 0, 0)
                item.mesh_sample_coords = (0.0,) * 12
                item.geometry_sentinel_supported = geom_supported
                item.geometry_sentinel_kind = geom_kind
                item.geometry_sentinel_hash = geom_hash

                for index, modifier in enumerate(obj.modifiers):
                    mod_state = settings.modifier_states.add()
                    mod_state.object_ref = obj
                    mod_state.object_name = obj.name
                    mod_state.modifier_name = modifier.name
                    mod_state.modifier_type = modifier.type
                    mod_state.modifier_index = index
                    mod_state.show_viewport = modifier.show_viewport
                    mod_state.is_managed = bool(
                        item.is_target
                        and object_pointer(obj) != object_pointer(guide)
                        and object_pointer(obj) not in fixed
                    )
        except Exception as exc:
            _remove_embedded_snapshot_key(scene)
            clear_snapshot_data(settings, scene, delete_persistent=False)
            self.report(
                {'ERROR'},
                f"Falha inesperada ao capturar o snapshot; preparação revertida sem alterar modifiers: {exc}"
            )
            return {'CANCELLED'}

        settings.object_count = len(settings.object_states)
        settings.target_count = sum(1 for item in settings.object_states if item.is_target)
        settings.modifier_count = len(settings.modifier_states)
        settings.snapshot_schema_version = SNAPSHOT_SCHEMA_VERSION
        settings.snapshot_active = True
        settings.displacement_applied = False

        try:
            disabled_count, disable_failures = disable_modifiers_from_snapshot(settings)
            settings.disabled_modifier_count = disabled_count
            settings.modifiers_currently_disabled = disabled_count > 0
            if disable_failures:
                raise ValueError(f"{disable_failures} modifier(s) gerenciado(s) não puderam ser desligados")

            external_ok, persistence_target = establish_initial_external_baseline(
                scene,
                settings,
                prepared_blend_path,
                prepared_file_sha,
            )
            if (
                not external_ok
                or not settings.snapshot_external_ok
                or not settings.snapshot_backup_path
                or not os.path.isfile(settings.snapshot_backup_path)
            ):
                raise ValueError("a primeira baseline externa não foi confirmada após a gravação")
        except Exception as exc:
            restored, missing, failed = restore_modifier_states(settings)
            mismatches = verify_modifier_states(settings)
            rollback_ok = (missing == 0 and failed == 0 and not mismatches)

            # Remove only the partial in-session snapshot. The strict baseline
            # helper already restores any pre-existing external file on failure.
            _remove_embedded_snapshot_key(scene)
            if rollback_ok:
                clear_snapshot_data(settings, scene, delete_persistent=False)
                self.report({'ERROR'}, f"Falha ao criar/validar a baseline externa; preparação revertida: {exc}")
            else:
                # If modifier rollback itself fails, preserving the in-memory
                # snapshot is safer than destroying the only restoration data.
                settings.modifiers_currently_disabled = True
                self.report(
                    {'ERROR'},
                    f"Falha ao criar baseline externa E rollback incompleto "
                    f"(restaurados={restored}, ausentes={missing}, falhas={failed}, divergências={len(mismatches)}). "
                    f"Snapshot mantido apenas nesta sessão; NÃO feche o Blender. Erro original: {exc}"
                )
            return {'CANCELLED'}

        self.report(
            {'INFO'},
            f"Snapshot salvo: {settings.object_count} objetos, {settings.target_count} alvos, "
            f"{settings.disabled_modifier_count} modifiers desligados; baseline externa gravada e validada."
        )
        return {'FINISHED'}


class T7SM_OT_ApplyDisplacement(Operator):
    bl_idname = "t7sm.apply_displacement"
    bl_label = "Aplicar Transformação"
    bl_description = "Faz todos os alvos seguirem a posição, rotação e escala atuais do objeto-guia, sempre a partir do snapshot original"

    def execute(self, context):
        scene = context.scene
        settings = scene.t7sm_settings

        if not settings.snapshot_active:
            self.report({'ERROR'}, "Nenhum snapshot ativo. Use Preparar Estátua primeiro.")
            return {'CANCELLED'}
        if not snapshot_runtime_compatible(settings):
            self.report({'ERROR'}, "Snapshot ativo usa schema antigo/incompatível. Não é seguro aplicar com esta versão.")
            return {'CANCELLED'}

        guide = settings.guide_object
        if guide is None or guide.mode != 'OBJECT':
            self.report({'ERROR'}, "O objeto-guia precisa estar em Object Mode.")
            return {'CANCELLED'}

        errors = validate_snapshot_for_apply(scene, settings)
        if errors:
            for message in errors[:8]:
                self.report({'ERROR'}, message)
            return {'CANCELLED'}

        guide_state = find_object_state(settings, guide)
        saved_guide_world = flat_to_matrix(guide_state.matrix_world)
        current_guide_world = channel_world_matrix(guide)

        try:
            transform_delta = guide_delta_matrix(saved_guide_world, current_guide_world)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

        if matrix_is_identity(transform_delta):
            self.report({'WARNING'}, "O objeto-guia ainda não teve posição, rotação ou escala alterada.")
            return {'CANCELLED'}

        delta_location, delta_rotation, delta_scale = guide_change_components(saved_guide_world, current_guide_world)

        # Production workflow uses normal uniform S. Non-uniform or negative
        # scale combined with rotation can introduce shear into child/object
        # transforms, so block it rather than silently deforming a statue.
        scale_values = [float(delta_scale.x), float(delta_scale.y), float(delta_scale.z)]
        if min(scale_values) <= ZERO_DELTA_TOLERANCE:
            self.report({'ERROR'}, "Scale negativa/zero não é permitida. Use S com fator positivo.")
            return {'CANCELLED'}
        scale_spread = max(scale_values) - min(scale_values)
        if scale_spread > 1.0e-5 * max(1.0, max(abs(v) for v in scale_values)):
            self.report({'ERROR'}, "Use escala uniforme no guia (tecla S). S X/Y/Z não é permitido neste workflow.")
            return {'CANCELLED'}

        if not matrix_is_positive_uniform_similarity(transform_delta):
            self.report(
                {'ERROR'},
                "A transformação relativa do guia contém shear/escala não uniforme (possível parent com escala não uniforme). "
                "Operação cancelada antes de mover qualquer peça."
            )
            return {'CANCELLED'}

        target_states = [
            item for item in settings.object_states
            if item.is_target and item.object_ref is not None
        ]
        target_states.sort(key=lambda item: parent_depth(item.object_ref))

        clear_applied_pose_readbacks(settings)
        failed = []
        moved = 0
        expected_local_matrices = []
        expected_channel_states = []
        for item in target_states:
            obj = item.object_ref
            try:
                original_world = flat_to_matrix(item.matrix_world)
                # Full affine delta: translation + rotation + multiplicative scale.
                # For the guide itself this resolves exactly to current_guide_world.
                # For every other object it preserves the object's original offset
                # from the guide and transforms that offset together with the guide.
                desired_world = transform_delta @ original_world
                expected_local = set_channel_world_matrix(obj, desired_world)
                if expected_local is None:
                    raise ValueError("set_channel_world_matrix não retornou a matrix_basis esperada")
                expected_local_matrices.append((obj, expected_local.copy()))
                # N-45: freeze the actual representable RNA transform channels
                # immediately after Blender decomposes the requested basis.
                expected_channel_states.append((obj, capture_transform_channel_state(obj)))
                moved += 1
            except Exception as exc:
                failed.append(f"{obj.name}: {exc}")

        settings.last_delta_x = delta_location.x
        settings.last_delta_y = delta_location.y
        settings.last_delta_z = delta_location.z
        settings.last_rotation_x = degrees(delta_rotation.x)
        settings.last_rotation_y = degrees(delta_rotation.y)
        settings.last_rotation_z = degrees(delta_rotation.z)
        settings.last_scale_x = delta_scale.x
        settings.last_scale_y = delta_scale.y
        settings.last_scale_z = delta_scale.z
        settings.displacement_applied = True

        try:
            context.view_layer.update()
        except Exception:
            pass

        # N-45: strict certification is now done in the raw transform channels
        # Blender actually stores, not in recomposed matrix_basis components.
        # This preserves post-write fault detection without rejecting correct
        # large-scale / near-gimbal poses solely due TRS recomposition noise.
        channel_mismatches = verify_applied_transform_channels(expected_channel_states)
        if channel_mismatches:
            failed.extend(channel_mismatches)

        # N-47/N-48: secondary world-space gate is geometric and expected-only.
        # Translation keeps the coupled vector budget required by N-42. Linear
        # sanity requires both a column-vector budget and an independent local
        # component cap so a huge sibling cannot canonicalize a small-component
        # setter/prefix error as a valid applied world.
        if not failed:
            world_sanity_mismatches = verify_applied_world_material_sanity(settings, transform_delta)
            if world_sanity_mismatches:
                failed.extend(world_sanity_mismatches)

        if not failed:
            readback_errors = capture_applied_pose_readbacks(settings)
            if readback_errors:
                failed.extend(readback_errors)
        else:
            clear_applied_pose_readbacks(settings)

        try:
            persist_snapshot(scene, settings)
        except Exception as exc:
            self.report({'WARNING'}, f"Transformação aplicada, mas o backup persistente não pôde ser atualizado: {exc}")

        if failed:
            self.report({'ERROR'}, f"Transformação não pôde ser verificada em {len(failed)} caso(s). Snapshot preservado; use Restaurar Estado Inicial.")
        else:
            self.report({'INFO'}, f"Transformação aplicada a {moved} objetos.")

        return {'FINISHED'}


class T7SM_OT_RestoreModifiers(Operator):
    bl_idname = "t7sm.restore_modifiers"
    bl_label = "Restaurar Modifiers"
    bl_description = "Restaura somente o show_viewport de cada modifier para o valor original; mantém a nova posição, rotação e escala"

    def execute(self, context):
        settings = context.scene.t7sm_settings
        if not settings.snapshot_active:
            self.report({'ERROR'}, "Nenhum snapshot ativo.")
            return {'CANCELLED'}
        if not snapshot_runtime_compatible(settings):
            self.report({'ERROR'}, "Snapshot ativo usa schema antigo/incompatível; restauração/finalização bloqueada para preservar evidência.")
            return {'CANCELLED'}

        geometry_mismatches = verify_geometry_sentinels(settings)
        if geometry_mismatches:
            try:
                persist_snapshot(context.scene, settings)
            except Exception:
                pass
            self.report(
                {'ERROR'},
                "Finalização bloqueada: origin/geometria de alvo mudou desde Preparar; snapshot preservado. "
                + geometry_mismatches[0]
            )
            return {'CANCELLED'}

        restored, missing, failed = restore_modifier_states(settings)
        modifier_mismatches = verify_modifier_states(settings)
        settings.modifiers_currently_disabled = bool(missing or failed or modifier_mismatches)
        try:
            persist_snapshot(context.scene, settings)
        except Exception as exc:
            self.report({'WARNING'}, f"Modifiers restaurados, mas o backup persistente não pôde ser atualizado: {exc}")
        if missing or failed or modifier_mismatches:
            self.report({'WARNING'}, f"Modifiers restaurados: {restored}; ausentes: {missing}; falhas: {failed}; divergências: {len(modifier_mismatches)}.")
        else:
            self.report({'INFO'}, f"{restored} modifiers restaurados ao estado original.")
        return {'FINISHED'}


class T7SM_OT_Finalize(Operator):
    bl_idname = "t7sm.finalize"
    bl_label = "Finalizar / Manter Nova Posição"
    bl_description = "Mantém a nova posição/rotação/escala, restaura os modifiers e apaga o snapshot"

    def execute(self, context):
        settings = context.scene.t7sm_settings
        if not settings.snapshot_active:
            self.report({'ERROR'}, "Nenhum snapshot ativo.")
            return {'CANCELLED'}
        if not snapshot_runtime_compatible(settings):
            self.report({'ERROR'}, "Snapshot ativo usa schema antigo/incompatível; restauração/finalização bloqueada para preservar evidência.")
            return {'CANCELLED'}

        # Finalize destroys the checkpoint, so any constraint/animation added
        # to a target or ancestor after Prepare must block before any mutation.
        influence_mismatches = verify_target_transform_influences(settings)
        if influence_mismatches:
            try:
                persist_snapshot(context.scene, settings)
            except Exception:
                pass
            self.report(
                {'ERROR'},
                "Finalização bloqueada ANTES de qualquer mutação: influência dinâmica em alvo/ancestral; "
                "snapshot preservado. " + influence_mismatches[0]
            )
            return {'CANCELLED'}

        # Before touching even modifier visibility, verify that target raw
        # origin/geometry still matches Prepare.
        geometry_mismatches = verify_geometry_sentinels(settings)
        if geometry_mismatches:
            try:
                persist_snapshot(context.scene, settings)
            except Exception:
                pass
            self.report(
                {'ERROR'},
                "Finalização bloqueada ANTES de qualquer mutação: origin/geometria de alvo mudou desde Preparar; "
                "snapshot preservado. " + geometry_mismatches[0]
            )
            return {'CANCELLED'}

        # N-32 second line of defense: even if a dynamic influence was added,
        # evaluated, and later removed, Finalize must prove that every target is
        # still at the pose implied by the current guide before deleting the
        # snapshot.
        applied_pose_mismatches = verify_current_applied_pose(settings)
        if applied_pose_mismatches:
            try:
                persist_snapshot(context.scene, settings)
            except Exception:
                pass
            self.report(
                {'ERROR'},
                "Finalização bloqueada: a pose atual diverge da última transformação aplicada; "
                "snapshot preservado. " + applied_pose_mismatches[0]
            )
            return {'CANCELLED'}

        restored, missing, failed = restore_modifier_states(settings)
        modifier_mismatches = verify_modifier_states(settings)
        if missing or failed or modifier_mismatches:
            settings.modifiers_currently_disabled = True
            try:
                persist_snapshot(context.scene, settings)
            except Exception:
                pass
            self.report(
                {'ERROR'},
                f"Finalização NÃO concluída: modifiers ausentes {missing}, falhas {failed}, divergências {len(modifier_mismatches)}. Snapshot preservado."
            )
            return {'CANCELLED'}

        settings.modifiers_currently_disabled = False
        clear_snapshot_data(settings, context.scene)
        self.report({'INFO'}, f"Nova transformação mantida. {restored} modifiers restaurados; snapshot removido.")
        return {'FINISHED'}


class T7SM_OT_RestoreInitial(Operator):
    bl_idname = "t7sm.restore_initial"
    bl_label = "Restaurar Estado Inicial"
    bl_description = "Restaura hierarchy/transformações e modifiers exatamente ao estado salvo, depois remove o snapshot"

    def execute(self, context):
        settings = context.scene.t7sm_settings
        if not settings.snapshot_active:
            self.report({'ERROR'}, "Nenhum snapshot ativo.")
            return {'CANCELLED'}
        if not snapshot_runtime_compatible(settings):
            self.report({'ERROR'}, "Snapshot ativo usa schema antigo/incompatível; restauração bloqueada para preservar evidência.")
            return {'CANCELLED'}

        # Fail BEFORE mutating transforms/modifiers if a constraint/animation
        # appeared on any target or ancestor after Prepare.
        influence_preflight = verify_target_transform_influences(settings)
        if influence_preflight:
            try:
                persist_snapshot(context.scene, settings)
            except Exception:
                pass
            self.report(
                {'ERROR'},
                "Restauração bloqueada ANTES de qualquer mutação: influência dinâmica em alvo/ancestral; "
                "snapshot preservado. " + influence_preflight[0]
            )
            return {'CANCELLED'}

        # Fail BEFORE mutating transforms/modifiers if local origin/geometry no
        # longer matches the checkpoint.
        geometry_preflight = verify_geometry_sentinels(settings)
        if geometry_preflight:
            try:
                persist_snapshot(context.scene, settings)
            except Exception:
                pass
            self.report(
                {'ERROR'},
                "Restauração bloqueada ANTES de qualquer mutação: origin/geometria de alvo mudou; "
                "snapshot preservado. " + geometry_preflight[0]
            )
            return {'CANCELLED'}

        missing_objects, transform_failures = restore_hierarchy_and_transforms(settings)
        restored_mods, missing_mods, failed_mods = restore_modifier_states(settings)

        try:
            context.view_layer.update()
        except Exception:
            pass

        influence_postflight = verify_target_transform_influences(settings)
        geometry_postflight = verify_geometry_sentinels(settings)
        field_mismatches = verify_restored_snapshot_fields(settings)
        modifier_mismatches = verify_modifier_states(settings)
        has_failure = bool(
            missing_objects or transform_failures or missing_mods or failed_mods
            or influence_postflight or geometry_postflight or field_mismatches or modifier_mismatches
        )

        if has_failure:
            settings.modifiers_currently_disabled = bool(missing_mods or failed_mods or modifier_mismatches)
            try:
                persist_snapshot(context.scene, settings)
            except Exception:
                pass
            details = field_mismatches[0] if field_mismatches else (modifier_mismatches[0] if modifier_mismatches else "")
            self.report(
                {'ERROR'},
                f"Restauração incompleta; snapshot PRESERVADO. Objetos ausentes {len(missing_objects)}, "
                f"falhas de transform {len(transform_failures)}, influências dinâmicas divergentes {len(influence_postflight)}, "
                f"divergências de geometria {len(geometry_postflight)}, divergências de campos {len(field_mismatches)}, modifiers ausentes {missing_mods}, "
                f"falhas de modifier {failed_mods}, divergências de modifier {len(modifier_mismatches)}. {details}"
            )
            return {'CANCELLED'}

        settings.modifiers_currently_disabled = False
        clear_snapshot_data(settings, context.scene)
        self.report({'INFO'}, f"Estado inicial restaurado e verificado. {restored_mods} modifiers restaurados; snapshot removido.")
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------


class T7SM_PT_Panel(Panel):
    bl_label = "T7 Statue Mover"
    bl_idname = "T7SM_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "T7 Statue"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.t7sm_settings

        version_row = layout.row()
        version_row.label(text="Blender 5.0.0 | Addon v1.2.21", icon='INFO')

        ref_box = layout.box()
        ref_box.label(text="Base católica + modelo de referência", icon='FILE_BLEND')
        if settings.reference_collection is not None:
            ref_box.label(text=f"Importados: {settings.reference_imported_count} objetos", icon='CHECKMARK')
            if settings.reference_source_path:
                ref_box.label(text=os.path.basename(settings.reference_source_path))
            ref_box.label(
                text=f"Unidades fonte: {settings.reference_unit_system or 'NONE'} / scale {settings.reference_scale_length:g}"
            )
            mismatch = (
                scene.unit_settings.system != settings.reference_unit_system
                or abs(float(scene.unit_settings.scale_length) - float(settings.reference_scale_length)) > 1.0e-9
            )
            if mismatch:
                ref_box.label(text="ATENÇÃO: unidades da Scene atual diferem da referência.", icon='ERROR')
            row = ref_box.row()
            row.enabled = not settings.snapshot_active
            row.operator("t7sm.remove_reference", icon='TRASH')
        else:
            source = reference_source_path(context)
            source_exists = bool(source) and os.path.isfile(source)
            if source_exists:
                ref_box.label(text=f"Arquivo: {os.path.basename(source)}")
            elif source:
                ref_box.label(text=f"Arquivo não encontrado: {os.path.basename(source)}", icon='ERROR')
            else:
                ref_box.label(text="Nenhum arquivo-base configurado.", icon='ERROR')
            row = ref_box.row(align=True)
            row.enabled = not settings.snapshot_active
            row.operator("t7sm.choose_reference_blend", icon='FILE_FOLDER')
            import_row = ref_box.row()
            import_row.enabled = source_exists and not settings.snapshot_active
            import_row.operator("t7sm.import_reference", icon='IMPORT')

        layout.separator()

        config = layout.column(align=True)
        config.enabled = not settings.snapshot_active
        config.prop(settings, "guide_object")
        config.prop(settings, "base_object")
        config.prop(settings, "target_collection")

        if settings.reference_collection is not None:
            layout.label(text="Base/referência importada é sempre fixa.", icon='LOCKED')
        if settings.target_collection is None:
            box = layout.box()
            box.label(text="Collection vazia = cena inteira", icon='INFO')
            box.label(text="Base, filhos e referência importada ficam fixos.")

        layout.separator()

        if not settings.snapshot_active:
            row = layout.row()
            row.scale_y = 1.4
            row.operator("t7sm.prepare", icon='REC')
            layout.label(text="Inclui collections ocultas/excluídas.", icon='CHECKMARK')
            layout.label(text="Desliga modifiers dos alvos, exceto o guia.")
            layout.label(text="Preparar grava um checkpoint persistente.")
            return

        status = layout.box()
        status.label(text="SNAPSHOT ATIVO", icon='LOCKED')
        status.label(text=f"Objetos registrados: {settings.object_count}")
        status.label(text=f"Objetos que acompanham: {settings.target_count}")
        status.label(text=f"Modifiers registrados: {settings.modifier_count}")
        status.label(text=f"Modifiers desligados no preparo: {settings.disabled_modifier_count}")
        if settings.snapshot_external_ok:
            status.label(text="Persistência: .blend + backup externo", icon='CHECKMARK')
        elif current_blend_path():
            status.label(text="Persistência: embutida; backup externo indisponível", icon='ERROR')
        else:
            status.label(text="Salve o .blend para persistência entre sessões.", icon='ERROR')
        if settings.snapshot_persistence_warning:
            status.label(text=settings.snapshot_persistence_warning, icon='ERROR')
        if settings.snapshot_created_utc:
            status.label(text=f"Criado: {settings.snapshot_created_utc}")
        if settings.snapshot_checksum:
            status.label(text=f"SHA-256 snapshot: {settings.snapshot_checksum[:16]}…")

        guide = settings.guide_object
        guide_state = find_object_state(settings, guide) if guide is not None else None
        if guide is not None and guide_state is not None:
            saved_world = flat_to_matrix(guide_state.matrix_world)
            try:
                dloc, drot, dscale = guide_change_components(saved_world, channel_world_matrix(guide))
                delta_box = layout.box()
                delta_box.label(text="Transformação atual do guia")
                delta_box.label(text=f"Pos: X {dloc.x:.4f}  Y {dloc.y:.4f}  Z {dloc.z:.4f}")
                delta_box.label(text=f"Rot: X {degrees(drot.x):.2f}°  Y {degrees(drot.y):.2f}°  Z {degrees(drot.z):.2f}°")
                delta_box.label(text=f"Scale: X {dscale.x:.4f}  Y {dscale.y:.4f}  Z {dscale.z:.4f}")
            except Exception:
                delta_box = layout.box()
                delta_box.label(text="Não foi possível calcular o delta do guia.", icon='ERROR')

        layout.separator()
        layout.label(text="Use G / R / S SOMENTE no objeto-guia.", icon='INFO')
        layout.label(text="A base e a referência permanecem fixas.")

        row = layout.row()
        row.scale_y = 1.5
        row.operator("t7sm.apply_displacement", icon='CON_TRACKTO')

        layout.separator()
        layout.operator("t7sm.restore_modifiers", icon='MODIFIER')

        if settings.displacement_applied:
            box = layout.box()
            box.label(text="Última transformação aplicada")
            box.label(text=f"Pos X {settings.last_delta_x:.4f}  Y {settings.last_delta_y:.4f}  Z {settings.last_delta_z:.4f}")
            box.label(text=f"Rot X {settings.last_rotation_x:.2f}°  Y {settings.last_rotation_y:.2f}°  Z {settings.last_rotation_z:.2f}°")
            box.label(text=f"Scale X {settings.last_scale_x:.4f}  Y {settings.last_scale_y:.4f}  Z {settings.last_scale_z:.4f}")

        layout.separator()

        finish = layout.row()
        finish.scale_y = 1.2
        finish.operator("t7sm.finalize", icon='CHECKMARK')

        restore = layout.row()
        restore.scale_y = 1.2
        restore.operator("t7sm.restore_initial", icon='LOOP_BACK')


# -----------------------------------------------------------------------------
# Registration / persistent handlers
# -----------------------------------------------------------------------------


CLASSES = (
    T7SM_ModifierState,
    T7SM_ObjectState,
    T7SM_Settings,
    T7SM_AddonPreferences,
    T7SM_OT_ChooseReferenceBlend,
    T7SM_OT_ImportReference,
    T7SM_OT_RemoveReference,
    T7SM_OT_Prepare,
    T7SM_OT_ApplyDisplacement,
    T7SM_OT_RestoreModifiers,
    T7SM_OT_Finalize,
    T7SM_OT_RestoreInitial,
    T7SM_PT_Panel,
)


@persistent
def t7sm_load_post(_dummy):
    for scene in list(bpy.data.scenes):
        try:
            recover_snapshot_for_scene(scene)
        except Exception as exc:
            print(f"[T7 Statue Mover] snapshot recovery failed for {scene.name}: {exc}")


@persistent
def t7sm_save_pre(_filepath):
    # v1.2.19 intentionally performs no identity mutation in save_pre.
    # A failed save must leave the frozen/recoverable identity untouched.
    return None

@persistent
def t7sm_save_post(_filepath):
    saved_path = str(_filepath or '')
    current_path = current_blend_path()
    # Save Copy: handlers may fire for another destination while bpy.data.filepath
    # remains the original. Never promote in that case.
    if saved_path and current_path:
        try:
            if os.path.normcase(os.path.abspath(bpy.path.abspath(saved_path))) != os.path.normcase(current_path):
                return
        except Exception:
            return
    for scene in list(bpy.data.scenes):
        settings = getattr(scene, 't7sm_settings', None)
        if settings is None or not settings.snapshot_active:
            continue
        if int(settings.snapshot_schema_version) != SNAPSHOT_SCHEMA_VERSION:
            print(f"[T7 Statue Mover] save-post ignored incompatible snapshot in {scene.name}")
            continue
        try:
            ok, _path = persist_external_snapshot_postsave(scene, settings, saved_path=saved_path)
            if not ok:
                settings.snapshot_external_ok = False
                settings.snapshot_backup_path = ''
                settings.snapshot_persistence_warning = (
                    "Backup externo não foi atualizado após o último save; o snapshot embutido foi preservado."
                )
                print(f"[T7 Statue Mover] snapshot save-post refresh did not produce a valid baseline for {scene.name}")
        except Exception as exc:
            settings.snapshot_external_ok = False
            settings.snapshot_backup_path = ''
            settings.snapshot_persistence_warning = (
                "Backup externo falhou após o último save; o snapshot embutido foi preservado."
            )
            print(f"[T7 Statue Mover] snapshot save-post refresh failed for {scene.name}: {exc}")

def _remove_handlers():
    for handler_list, fn in (
        (bpy.app.handlers.load_post, t7sm_load_post),
        (bpy.app.handlers.save_pre, t7sm_save_pre),
        (bpy.app.handlers.save_post, t7sm_save_post),
    ):
        for existing in list(handler_list):
            same_identity = existing is fn
            same_stale_symbol = (
                getattr(existing, '__name__', None) == fn.__name__
                and getattr(existing, '__module__', None) == __name__
            )
            if same_identity or same_stale_symbol:
                try:
                    handler_list.remove(existing)
                except ValueError:
                    pass

def _cleanup_stale_registration():
    if hasattr(bpy.types.Scene, "t7sm_settings"):
        try:
            del bpy.types.Scene.t7sm_settings
        except Exception:
            pass

    for cls in reversed(CLASSES):
        # Normal case: same module/class object.
        try:
            bpy.utils.unregister_class(cls)
            continue
        except Exception:
            pass

        bl_idname = getattr(cls, 'bl_idname', '') or ''
        candidates = [cls.__name__]
        base_types = []
        if issubclass(cls, Operator):
            base_types.append(bpy.types.Operator)
            if '.' in bl_idname:
                prefix, opname = bl_idname.split('.', 1)
                candidates.append(f"{prefix.upper()}_OT_{opname}")
        elif issubclass(cls, Panel):
            base_types.append(bpy.types.Panel)
            if bl_idname:
                candidates.append(bl_idname)
        elif issubclass(cls, AddonPreferences):
            base_types.append(bpy.types.AddonPreferences)
            if bl_idname:
                candidates.append(bl_idname)
        elif issubclass(cls, PropertyGroup):
            base_types.append(bpy.types.PropertyGroup)

        stale = None
        # RNA lookup can recover PropertyGroup subclasses that are not exposed
        # as bpy.types.<python class name> after an interrupted/old unregister.
        for base in base_types:
            getter = getattr(base, 'bl_rna_get_subclass_py', None)
            if not callable(getter):
                continue
            for identifier in candidates:
                try:
                    stale = getter(identifier, None)
                except Exception:
                    stale = None
                if stale is not None:
                    break
            if stale is not None:
                break

        if stale is None:
            for identifier in candidates:
                stale = getattr(bpy.types, identifier, None)
                if stale is not None:
                    break
        if stale is not None:
            try:
                bpy.utils.unregister_class(stale)
            except Exception:
                pass

def _initial_recovery_timer():
    """Recover snapshots only after Blender releases addon_utils._RestrictData."""
    if not hasattr(bpy.types.Scene, "t7sm_settings"):
        return None
    try:
        scenes = list(bpy.data.scenes)
    except Exception:
        # During normal addon_utils.enable() Blender deliberately restricts
        # bpy.data while register() is executing. Retry after the next event
        # loop tick rather than touching restricted data in register().
        return 0.05

    for scene in scenes:
        try:
            recover_snapshot_for_scene(scene)
        except Exception as exc:
            print(f"[T7 Statue Mover] deferred snapshot recovery failed for {scene.name}: {exc}")
    return None


def _remove_initial_recovery_timer():
    timers = getattr(bpy.app, 'timers', None)
    if timers is None:
        return
    try:
        if timers.is_registered(_initial_recovery_timer):
            timers.unregister(_initial_recovery_timer)
    except Exception:
        pass


def _schedule_initial_recovery():
    timers = getattr(bpy.app, 'timers', None)
    if timers is None or not callable(getattr(timers, 'register', None)):
        return False
    _remove_initial_recovery_timer()
    timers.register(_initial_recovery_timer, first_interval=0.0)
    return True


def register():
    if tuple(bpy.app.version[:3]) != SUPPORTED_BLENDER_VERSION:
        raise RuntimeError(
            f"T7 Statue Mover v{'.'.join(map(str, ADDON_VERSION))} foi congelado para Blender 5.0.0; "
            f"versão detectada: {bpy.app.version_string}."
        )

    _remove_handlers()
    _remove_initial_recovery_timer()
    _cleanup_stale_registration()

    registered = []
    try:
        for cls in CLASSES:
            bpy.utils.register_class(cls)
            registered.append(cls)
        bpy.types.Scene.t7sm_settings = PointerProperty(type=T7SM_Settings)
        bpy.app.handlers.load_post.append(t7sm_load_post)
        bpy.app.handlers.save_post.append(t7sm_save_post)

        # addon_utils.enable() runs register() under bpy.data _RestrictData.
        # Never touch bpy.data.scenes here. Defer recovery until Blender has
        # returned from registration and normal RNA data access is available.
        _schedule_initial_recovery()
    except Exception:
        _remove_handlers()
        _remove_initial_recovery_timer()
        if hasattr(bpy.types.Scene, "t7sm_settings"):
            try:
                del bpy.types.Scene.t7sm_settings
            except Exception:
                pass
        for cls in reversed(registered):
            try:
                bpy.utils.unregister_class(cls)
            except Exception:
                pass
        raise


def unregister():
    _remove_handlers()
    _remove_initial_recovery_timer()
    if hasattr(bpy.types.Scene, "t7sm_settings"):
        try:
            del bpy.types.Scene.t7sm_settings
        except Exception:
            pass
    # Use the exact class objects registered by this module. Looking them up via
    # cls.__name__ is incorrect for Blender operators/panels in 5.0.0.
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

