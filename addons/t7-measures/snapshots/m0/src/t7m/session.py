"""Synthetic state machine only. No RNA, BMesh, timers or actual event callbacks."""
from dataclasses import dataclass, replace
from fractions import Fraction as F
import struct
from .numeric import Refusal, number
from .resources import snapshot_plan, geometry_plan, SNAPSHOT_BYTES
from .kernel import Entity, Query, measure, I, matrix_and_unit, vector

@dataclass(frozen=True)
class Mesh:
    vertices: tuple
    edges: tuple = ()
    faces: tuple = ()  # tuple of loops: ((vertex occurrence, edge occurrence), ...)

def counts(mesh):
    if type(mesh) is not Mesh or any(type(x) is not tuple for x in (mesh.vertices,mesh.edges,mesh.faces)):
        raise Refusal('SYNTHETIC_MESH_TYPE')
    return len(mesh.vertices),len(mesh.edges),len(mesh.faces),sum(len(f) for f in mesh.faces)

def byte_count(mesh):
    v,e,f,l = counts(mesh)
    return 8 + 9*3 + 24*v + 16*e + 8*f + 24*l

def canonical(mesh):
    """Canonical synthetic mesh encoding, includes occurrence ordinals and loop.edge."""
    nv,ne,nf,nl = counts(mesh)
    size = byte_count(mesh)
    snapshot_plan(nv,ne,nf,nl,(0,size,size))
    if size>SNAPSHOT_BYTES: raise Refusal('SNAPSHOT_SIZE')
    out = bytearray(b'T7M0\x00\x01\x00\x00')
    out.extend(b'V'+struct.pack('<Q',nv))
    for p in mesh.vertices:
        if type(p) is not tuple or len(p)!=3: raise Refusal('SNAPSHOT_VERTEX')
        vals = tuple(number(x) for x in p)
        # Preserve observed -0 bits in freshness signatures; geometry may normalize zero.
        floats = tuple(raw if type(raw) is float else float(value) for raw,value in zip(p,vals))
        if any(F.from_float(y)!=x for x,y in zip(vals,floats)):
            raise Refusal('SYNTHETIC_BINARY64_REQUIRED')
        out.extend(struct.pack('<3d',*floats))
    out.extend(b'E'+struct.pack('<Q',ne))
    for e in mesh.edges:
        if type(e) is not tuple or len(e)!=2 or any(type(i) is not int or not 0<=i<nv for i in e):
            raise Refusal('SNAPSHOT_EDGE')
        out.extend(struct.pack('<2Q',*e))
    out.extend(b'F'+struct.pack('<Q',nf))
    for loops in mesh.faces:
        if type(loops) is not tuple or len(loops)<3: raise Refusal('SNAPSHOT_FACE')
        out.extend(struct.pack('<Q',len(loops)))
        for j,pair in enumerate(loops):
            if type(pair) is not tuple or len(pair)!=2: raise Refusal('SNAPSHOT_LOOP')
            v,e = pair
            if type(v) is not int or type(e) is not int or not 0<=v<nv or not 0<=e<ne:
                raise Refusal('SNAPSHOT_LOOP_INDEX')
            nxt = loops[(j+1)%len(loops)][0]
            if set(mesh.edges[e]) != {v,nxt} or v==nxt: raise Refusal('LOOP_EDGE_INCIDENCE')
            out.extend(struct.pack('<3Q',j,v,e))
    if len(out)!=size: raise Refusal('ENCODING_SIZE')
    return bytes(out)

@dataclass(frozen=True)
class Context:
    registration: str = 'synthetic-registration-1'
    generation: int = 0
    window: int = 1
    area: int = 1
    scene: int = 1
    view_layer: int = 1
    object: int = 1
    datablock: int = 1
    frame: int = 1
    temporal: tuple = ()
    matrix: tuple = I
    translation: tuple = (0,0,0)
    system: str = 'METRIC'
    scale_length: object = F(1,1000)
    mode: str = 'EDIT_MESH'
    objects_in_mode: int = 1

def frozen_context(ctx):
    if type(ctx) is not Context: raise Refusal('CONTEXT_TYPE')
    if type(ctx.registration) is not str or not 0<len(ctx.registration)<=128:
        raise Refusal('REGISTRATION_ID')
    ints = (ctx.generation,ctx.window,ctx.area,ctx.scene,ctx.view_layer,ctx.object,ctx.datablock,ctx.frame,ctx.objects_in_mode)
    if any(type(x) is not int or not 0<=x<2**63 for x in ints): raise Refusal('CONTEXT_ID')
    if ctx.mode!='EDIT_MESH' or ctx.objects_in_mode!=1: raise Refusal('CONTEXT_MODE')
    if type(ctx.temporal) is not tuple or len(ctx.temporal)>16:
        raise Refusal('TEMPORAL_TOKEN')
    if any(type(x) not in (int,str,bytes) or (type(x) in (str,bytes) and len(x)>256) or
           (type(x) is int and x.bit_length()>64) for x in ctx.temporal):
        raise Refusal('TEMPORAL_TOKEN')
    m,_ = matrix_and_unit(Query(Entity('V',((0,0,0),)),matrix=ctx.matrix,system=ctx.system,scale_length=ctx.scale_length))
    # Own immutable copies; retaining a dataclass containing caller lists is unsafe.
    return replace(ctx,matrix=m,translation=vector(ctx.translation),scale_length=number(ctx.scale_length))

@dataclass(frozen=True)
class Selection:
    kind: str
    occurrences: tuple # ((ordinal, select:bool, hide:bool),...)

def selected(mesh,s):
    if type(s) is not Selection or s.kind not in ('V','E','F') or type(s.occurrences) is not tuple:
        raise Refusal('SELECTION_MODE')
    chosen = []
    seen = set()
    limit = dict(V=len(mesh.vertices),E=len(mesh.edges),F=len(mesh.faces))[s.kind]
    for entry in s.occurrences:
        if type(entry) is not tuple or len(entry)!=3: raise Refusal('SELECTION_ENTRY')
        idx,sel,hidden = entry
        if type(idx) is not int or not 0<=idx<limit or idx in seen or type(sel) is not bool or type(hidden) is not bool:
            raise Refusal('SELECTION_ENTRY')
        seen.add(idx)
        if sel and not hidden: chosen.append(idx)
    if len(chosen)!=1: raise Refusal('CAPTURE_CARDINALITY')
    idx = chosen[0]
    count = 1 if s.kind=='V' else (2 if s.kind=='E' else len(mesh.faces[idx]))
    geometry_plan((s.kind,),(count,))
    if s.kind=='V': ids=(idx,)
    elif s.kind=='E': ids=mesh.edges[idx]
    else: ids=tuple(v for v,e in mesh.faces[idx])
    return Entity(s.kind,tuple(tuple(number(x) for x in mesh.vertices[i]) for i in ids))

@dataclass(frozen=True)
class Click:
    context1: Context
    mesh1: Mesh
    selection1: Selection
    context2: Context
    mesh2: Mesh
    selection2: Selection

class Instance:
    """One slot in one simulated addon instance; two Instances model two processes."""
    def __init__(self):
        self.clear()

    def clear(self):
        self.owner = self.a = self.b = self.signature = self.last = None

    def active_in(self,context):
        try: return self.owner==frozen_context(context) and self.a is not None
        except (Refusal,ArithmeticError,TypeError,ValueError): return False

    def invalidate(self,event):
        # Event identity supplied by offline driver; real event detection is M1/M2.
        self.clear()
        return dict(status='INVALIDATED',event=event)

    def _prepare(self,c):
        if type(c) is not Click or type(c.context1) is not Context or type(c.context2) is not Context:
            raise Refusal('CLICK_CONTEXT')
        ctx,ctx2 = frozen_context(c.context1),frozen_context(c.context2)
        if ctx!=ctx2: raise Refusal('CONTEXT_CHANGED_DURING_CLICK')
        if c.selection1!=c.selection2: raise Refusal('SELECTION_CHANGED_DURING_CLICK')
        v,e,f,l = counts(c.mesh1)
        sizes = (len(self.signature) if self.signature else 0,byte_count(c.mesh1),byte_count(c.mesh2))
        snapshot_plan(v,e,f,l,sizes)
        v2,e2,f2,l2 = counts(c.mesh2)
        snapshot_plan(v2,e2,f2,l2,sizes)
        a,b = selected(c.mesh1,c.selection1),selected(c.mesh2,c.selection2)
        if a!=b: raise Refusal('OCCURRENCE_CHANGED_DURING_CLICK')
        s1,s2 = canonical(c.mesh1),canonical(c.mesh2)
        if s1!=s2: raise Refusal('GEOMETRY_CHANGED_DURING_CLICK')
        return ctx,s1,a

    def capture(self,which,c):
        if which=='A': self.clear() # discard old cycle before any new allocation
        self.last = None
        try:
            if which not in ('A','B'): raise Refusal('CAPTURE_KIND')
            ctx,sig,item = self._prepare(c)
            if which=='A':
                self.owner,self.signature,self.a = ctx,sig,item
            else:
                if self.a is None or self.owner!=ctx or self.signature!=sig:
                    raise Refusal('A_CONTEXT_OR_BYTES_MISMATCH')
                self.b = item
            return dict(status='CAPTURED',slot=which)
        except (Refusal,ArithmeticError,TypeError,ValueError,IndexError,MemoryError) as e:
            self.clear()
            return dict(status='REFUSED',reason=str(e))

    def calculate(self,c):
        self.last = None
        try:
            ctx,sig,_ = self._prepare(c)
            if self.a is None or self.b is None or self.owner!=ctx or self.signature!=sig:
                raise Refusal('CALCULATE_CONTEXT_OR_BYTES_MISMATCH')
            # Compose geometry working reserve with all snapshot/global-map charges.
            nv,ne,nf,nl = counts(c.mesh1)
            retained = len(self.signature)+byte_count(c.mesh1)+byte_count(c.mesh2)+(nv+ne+nf+nl)*512
            geometry_plan((self.a.kind,self.b.kind),(len(self.a.points),len(self.b.points)),retained=retained)
            result = measure(Query(self.a,self.b,ctx.matrix,ctx.system,ctx.scale_length))
            if result['status']=='REFUSED': raise Refusal(result['reason'])
            # In this static model S2 is supplied immutable input; no runtime callback claim.
            self.clear()
            self.last = result
            return result
        except (Refusal,ArithmeticError,TypeError,ValueError,IndexError,MemoryError) as e:
            self.clear()
            return dict(status='REFUSED',reason=str(e))
