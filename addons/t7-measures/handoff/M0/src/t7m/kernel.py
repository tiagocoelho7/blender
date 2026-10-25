"""Eight M0 modalities over detached fixtures. No external file or Blender access."""
from dataclasses import dataclass
from fractions import Fraction as F
from .numeric import number, check, root_bounds, Refusal, _meter
from .resources import geometry_plan
from . import geometry as g
from .presentation import Certificate, publish, compare

I = ((1,0,0),(0,1,0),(0,0,1))

@dataclass(frozen=True)
class Entity:
    kind: str
    points: tuple

@dataclass(frozen=True)
class Query:
    a: Entity
    b: Entity | None = None
    matrix: tuple = I
    system: str = 'METRIC'
    scale_length: object = F(1,1000)
    precision: int = 3

def vector(p):
    if type(p) not in (tuple,list) or len(p)!=3: raise Refusal('VECTOR_ARITY')
    return tuple(number(x) for x in p)

def matrix_and_unit(q):
    if type(q.matrix) not in (tuple,list) or len(q.matrix)!=3: raise Refusal('MATRIX_ARITY')
    m = tuple(vector(row) for row in q.matrix)
    co = tuple(g.cross(m[(i+1)%3],m[(i+2)%3]) for i in range(3))
    det = g.dot(m[0],co[0])
    if det==0: raise Refusal('SINGULAR_TRANSFORM')
    # Exact Frobenius condition bound; a conservative experimental admission rule.
    nf = check(sum((g.norm2(row) for row in m),F(0)))
    ni = check(sum((g.norm2(row) for row in co),F(0))/(det*det))
    if check(nf*ni)>10**24: raise Refusal('ILL_CONDITIONED_TRANSFORM')
    if q.system not in ('METRIC','IMPERIAL','NONE'): raise Refusal('UNIT_SYSTEM')
    scale = number(q.scale_length)
    if q.system!='NONE' and scale<=0: raise Refusal('PHYSICAL_SCALE')
    return m, check(scale*1000) if q.system!='NONE' else F(1)

def measure(q):
    token = _meter.set([0])
    try:
        if type(q) is not Query or type(q.precision) is not int or not 0<=q.precision<=6:
            raise Refusal('QUERY_TYPE_OR_PRECISION')
        entities = (q.a,) if q.b is None else (q.a,q.b)
        for e in entities:
            if type(e) is not Entity or type(e.points) not in (tuple,list) or type(e.kind) is not str:
                raise Refusal('ENTITY_TYPE')
        plan = geometry_plan(tuple(e.kind for e in entities),tuple(len(e.points) for e in entities))
        if len(entities)==1 and q.a.kind not in ('E','F'): raise Refusal('SINGLE_MODALITY')
        m,unit = matrix_and_unit(q)
        originals = tuple(tuple(vector(p) for p in e.points) for e in entities)
        anchor = originals[0][0]
        transformed = tuple(tuple(g.mul(tuple(g.dot(row,g.sub(p,anchor)) for row in m),unit) for p in pts) for pts in originals)
        geometry = []
        sizes = []
        certs = []
        length_unit = 'BU' if q.system=='NONE' else 'mm'
        for i,(e,pts,orig) in enumerate(zip(entities,transformed,originals)):
            if e.kind=='F':
                item = g.face(pts,orig,m,unit,q.system!='NONE')
                c = Certificate(item.area_lo,item.area_hi,'area',item.approximate,False,
                                item.area_nominal_allowed,(item.reference_lo,item.reference_hi))
                sizes.append(dict(entity=i+1,kind='F',certificate=c,display=publish(c,q.precision,length_unit+'2'),
                                  face=item))
                certs.append(c)
            elif e.kind=='E':
                item = pts
                l,u = root_bounds(g.norm2(g.sub(pts[1],pts[0])))
                c = Certificate(l,u,'length',reference=(l,u))
                sizes.append(dict(entity=i+1,kind='E',certificate=c,display=publish(c,q.precision,length_unit),
                                  warning='DEGENERATE_EDGE_AS_POINT' if u==0 else None))
                certs.append(c)
            else: item=pts
            geometry.append(item)
        distance = None
        if len(entities)==2:
            try:
                sq = g.squared_distance(q.a.kind,geometry[0],q.b.kind,geometry[1])
                l,u = root_bounds(sq)
                H = sum((f.h for e,f in zip(entities,geometry) if e.kind=='F'),F(0))
                approx = any(e.kind=='F' and f.approximate for e,f in zip(entities,geometry))
                proof = False
                if not approx and sq==0:
                    proof = g.contact(q.a.kind,geometry[0],q.b.kind,geometry[1])
                    if not proof: raise Refusal('ZERO_WITHOUT_INCIDENCE_PROOF')
                c = Certificate(max(F(0),l-H),check(u+H),'distance',approx,proof,True,(l,u))
                distance = dict(certificate=c,display=publish(c,q.precision,length_unit),squared_proxy=sq)
            except (Refusal,ArithmeticError) as e:
                distance = dict(certificate=None,display=dict(state='INDETERMINADO_SEM_FAIXA',reason=str(e)))
        ordering = compare(certs[0],certs[1],q.precision) if len(certs)==2 and q.a.kind==q.b.kind else None
        return dict(status='COMPUTED_OFFLINE',distance=distance,sizes=tuple(sizes),ordering=ordering,
                    plan=plan,exact_steps=_meter.get()[0],anchor=anchor,unit=length_unit,
                    notice='Malha de edicao; modifiers nao considerados. Nao equivale a peca final do slicer.',
                    scale_notice='Escala fisica desconhecida' if q.system=='NONE' else None)
    except (Refusal,ArithmeticError,TypeError,ValueError,OverflowError,MemoryError) as e:
        return dict(status='REFUSED',reason=str(e),distance=None,sizes=(),ordering=None)
    finally:
        _meter.reset(token)
