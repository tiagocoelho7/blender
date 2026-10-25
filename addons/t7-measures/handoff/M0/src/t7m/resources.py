"""Conservative *experimental* admission model, not a process RSS certificate."""
from .numeric import Refusal
from fractions import Fraction
import struct,sys

MEMORY = 128*1024**2
FACE_LOOPS = 32  # Reduced experimental envelope, below approved maximum 512.
SNAPSHOT_BYTES = 2*1024**2

def platform_gate():
    # Explicit admission hypotheses for the object-size reserve; no RSS assertion.
    if (sys.implementation.name!='cpython' or struct.calcsize('P')!=8 or
        sys.int_info.bits_per_digit<30 or sys.int_info.sizeof_digit>4 or
        sys.getsizeof(0)>32 or sys.getsizeof(Fraction(0))>64 or sys.getsizeof(())>64):
        raise Refusal('EXPERIMENTAL_PLATFORM_UNBUDGETED')

def geometry_plan(kinds, counts, retained=0):
    platform_gate()
    if type(retained) is not int or retained<0:
        raise Refusal('RETAINED_MEMORY_COUNT')
    if len(kinds) not in (1,2) or len(kinds) != len(counts):
        raise Refusal('ARITY')
    for k,n in zip(kinds,counts):
        if type(n) is not int or n < 1 or k not in ('V','E','F'):
            raise Refusal('ENTITY_COUNT')
        if (k == 'V' and n != 1) or (k == 'E' and n != 2) or (k == 'F' and not 3 <= n <= 512):
            raise Refusal('ENTITY_COUNT')
    faces = [n for k,n in zip(kinds,counts) if k == 'F']
    pair = (faces[0]-2)*(faces[1]-2) if len(faces)==2 else 0
    contour = sum(n*(n-3)//2 for n in faces)
    diameter = sum(n*(n-1)//2 for n in faces) # charge P worst case before coordinates
    # Covers ear search O(n^3), independent triangle validation O(n^2),
    # adjacency, projection, and up to 32 candidate tests per triangle pair.
    other = sum(4*n**3+64*n*n+128*n for n in faces) + 32*max(pair, sum(n-2 for n in faces),1)
    total = contour + diameter + pair + other
    if pair > 50000 or total > 200000:
        raise Refusal('PAIR_PREFLIGHT')
    if any(n > FACE_LOOPS for n in faces):
        raise Refusal('EXPERIMENTAL_FACE_LIMIT')
    nv, nf = sum(counts), len(faces)
    nt = sum(n-2 for n in faces)
    minimum = 8*1024**2 + nv*512 + nf*384 + sum(faces)*384 + nt*1024 + pair*32 + contour*32
    # Rational working reserve: 4096 scalar slots at <=4k bits each with
    # up to 8x expression temporaries plus headers; this is a design reserve.
    peak = max(minimum, 80*1024**2 + nv*65536 + nt*65536 + retained)
    if peak > MEMORY:
        raise Refusal('MEMORY_PREFLIGHT')
    return dict(contour=contour, diameter=diameter, triangle_pairs=pair,
                other=other, total=total, estimated_peak_bytes=peak)

def snapshot_plan(nv, ne, nf, loops, sizes):
    platform_gate()
    values = (nv,ne,nf,loops,*sizes)
    if any(type(n) is not int or n < 0 for n in values) or len(sizes) != 3:
        raise Refusal('SNAPSHOT_COUNTS')
    if nv+ne+nf > 500000 or loops > 1000000:
        raise Refusal('GLOBAL_MESH_LIMIT')
    minimum = 8*1024**2 + nv*512 + ne*384 + nf*384 + loops*384
    # bytearray -> bytes conversion briefly coexists with the finished signature.
    peak = max(minimum,80*1024**2 + (nv+ne+nf+loops)*512) + sum(sizes) + max(sizes[1:])
    if peak > MEMORY:
        raise Refusal('AGGREGATE_MEMORY')
    if any(s > SNAPSHOT_BYTES for s in sizes):
        raise Refusal('EXPERIMENTAL_SNAPSHOT_LIMIT')
    return peak
