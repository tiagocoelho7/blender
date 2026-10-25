"""Finite geometric sets over exact rational coordinates, all computation copied."""
from dataclasses import dataclass
from itertools import combinations
from collections import Counter
from fractions import Fraction as F
from .numeric import check, root_bounds, f32_radius, Refusal

def add(a,b): return tuple(check(x+y) for x,y in zip(a,b))
def sub(a,b): return tuple(check(x-y) for x,y in zip(a,b))
def mul(a,s): return tuple(check(x*s) for x in a)
def dot(a,b):
    r = F(0)
    for x,y in zip(a,b): r = check(r+check(x*y))
    return r
def cross(a,b):
    return tuple(check(a[i]*b[j]-a[j]*b[i]) for i,j in ((1,2),(2,0),(0,1)))
def norm2(a): return dot(a,a)
def qsum(values):
    out=F(0)
    for x in values: out=check(out+check(x))
    return out
def clamp(x): return max(F(0),min(F(1),x))
def edges(t): return tuple(zip(t,t[1:]+t[:1]))

def point_segment(p,a,b):
    u,v = sub(b,a),sub(p,a)
    den = norm2(u)
    t = clamp(check(dot(v,u)/den)) if den else F(0)
    return norm2(sub(v,mul(u,t)))

def segment_segment(a,b,c,d):
    u,v,w = sub(b,a),sub(d,c),sub(a,c)
    aa,bb,cc,dd,ee = norm2(u),dot(u,v),norm2(v),dot(u,w),dot(v,w)
    candidates = [point_segment(a,c,d),point_segment(b,c,d),
                  point_segment(c,a,b),point_segment(d,a,b)]
    det = check(aa*cc-bb*bb)
    if det > 0:
        s,t = check((bb*ee-cc*dd)/det),check((aa*ee-bb*dd)/det)
        if 0 <= s <= 1 and 0 <= t <= 1:
            candidates.append(norm2(sub(add(w,mul(u,s)),mul(v,t))))
    return min(candidates)

def point_on_segment(p,a,b):
    u,w = sub(b,a),sub(p,a)
    return cross(u,w) == (0,0,0) and 0 <= dot(w,u) <= norm2(u) and (norm2(u)>0 or p==a)

def segment_contact(a,b,c,d):
    # Independent incidence predicate: solve line intersection with cross products.
    u,v,w = sub(b,a),sub(d,c),sub(c,a)
    n = cross(u,v)
    den = norm2(n)
    if not den:
        return any((point_on_segment(a,c,d), point_on_segment(b,c,d),
                    point_on_segment(c,a,b), point_on_segment(d,a,b)))
    if dot(w,n) != 0: return False
    s = check(dot(cross(w,v),n)/den)
    t = check(dot(cross(w,u),n)/den)
    return 0 <= s <= 1 and 0 <= t <= 1

def inside_triangle(p,t):
    a,b,c = t
    n = cross(sub(b,a),sub(c,a))
    return all(dot(cross(sub(y,x),sub(p,x)),n) >= 0 for x,y in edges(t))

def point_triangle(p,t):
    a,b,c = t
    n = cross(sub(b,a),sub(c,a))
    nn = norm2(n)
    if not nn: raise Refusal('DEGENERATE_TRIANGLE')
    signed = dot(sub(p,a),n)
    q = sub(p,mul(n,check(signed/nn)))
    if inside_triangle(q,t): return check(signed*signed/nn)
    return min(point_segment(p,x,y) for x,y in edges(t))

def point_triangle_contact(p,t):
    return dot(sub(p,t[0]),cross(sub(t[1],t[0]),sub(t[2],t[0]))) == 0 and inside_triangle(p,t)

def segment_triangle_contact(a,b,t):
    n = cross(sub(t[1],t[0]),sub(t[2],t[0]))
    da,db = dot(sub(a,t[0]),n),dot(sub(b,t[0]),n)
    if da == db == 0:
        return inside_triangle(a,t) or inside_triangle(b,t) or any(segment_contact(a,b,c,d) for c,d in edges(t))
    if (da>0 and db>0) or (da<0 and db<0): return False
    s = check(da/(da-db))
    return 0 <= s <= 1 and inside_triangle(add(a,mul(sub(b,a),s)),t)

def segment_triangle(a,b,t):
    if segment_triangle_contact(a,b,t): return F(0)
    return min([point_triangle(a,t),point_triangle(b,t)] +
               [segment_segment(a,b,c,d) for c,d in edges(t)])

def triangle_triangle(a,b):
    return min([segment_triangle(x,y,b) for x,y in edges(a)] +
               [segment_triangle(x,y,a) for x,y in edges(b)])

def orient(a,b,c): return check((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
def on2(p,a,b):
    return orient(a,b,p)==0 and all(min(x,y)<=z<=max(x,y) for x,y,z in zip(a,b,p))
def intersects2(a,b,c,d):
    o1,o2,o3,o4 = orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
    if o1*o2<0 and o3*o4<0: return True
    return (o1==0 and on2(c,a,b)) or (o2==0 and on2(d,a,b)) or (o3==0 and on2(a,c,d)) or (o4==0 and on2(b,c,d))
def signed_area2(p): return qsum(check(a[0]*b[1]-a[1]*b[0]) for a,b in edges(p))

def simple_polygon(p):
    n = len(p)
    if len(set(p)) != n: raise Refusal('REPEATED_PROJECTED_VERTEX')
    for i in range(n):
        a,b,c = p[i-1],p[i],p[(i+1)%n]
        # Conservative M0 restriction: no redundant collinear boundary corners.
        if orient(a,b,c)==0: raise Refusal('COLLINEAR_BOUNDARY_CORNER')
    for i,j in combinations(range(n),2):
        if (i-j)%n in (1,n-1): continue
        if intersects2(p[i],p[(i+1)%n],p[j],p[(j+1)%n]):
            raise Refusal('NONSIMPLE_POLYGON')
    if signed_area2(p)==0: raise Refusal('ZERO_PROJECTED_AREA')

def triangulate(p):
    sign = 1 if signed_area2(p)>0 else -1
    ids = list(range(len(p)))
    out = []
    while len(ids)>3:
        for j in range(len(ids)):
            a,b,c = ids[j-1],ids[j],ids[(j+1)%len(ids)]
            if sign*orient(p[a],p[b],p[c])<=0: continue
            if any(all(sign*orient(p[x],p[y],p[k])>=0 for x,y in ((a,b),(b,c),(c,a)))
                   for k in ids if k not in (a,b,c)):
                continue
            out.append((a,b,c)); del ids[j]; break
        else: raise Refusal('EAR_CERTIFICATE_UNAVAILABLE')
    out.append(tuple(ids))
    validate_triangulation(p,tuple(out))
    return tuple(out)

def validate_triangulation(p,triangles):
    """Separate chain/incidence/area check; does not trust the ear selector."""
    n = len(p)
    if len(triangles)!=n-2: raise Refusal('TRIANGLE_COUNT')
    sign = 1 if signed_area2(p)>0 else -1
    directed = Counter()
    area = F(0)
    for t in triangles:
        if len(t)!=3 or any(type(i) is not int or not 0<=i<n for i in t) or len(set(t))!=3:
            raise Refusal('TRIANGLE_INDEX')
        v = orient(*(p[i] for i in t))
        if sign*v<=0: raise Refusal('TRIANGLE_ORIENTATION')
        area = check(area+v)
        directed.update(edges(t))
    boundary = Counter((i,(i+1)%n) for i in range(n))
    for a,b in set(directed)|set(boundary):
        if directed[a,b] - directed[b,a] != boundary[a,b]-boundary[b,a]:
            raise Refusal('TRIANGLE_CHAIN')
        if directed[a,b]>1: raise Refusal('TRIANGLE_MULTIPLICITY')
    if area!=signed_area2(p): raise Refusal('TRIANGLE_AREA_COVERAGE')
    # No crossings between internal or boundary edges, apart from common ends.
    undirected = sorted({tuple(sorted(e)) for e in directed})
    for (a,b),(c,d) in combinations(undirected,2):
        if len({a,b,c,d})<4: continue
        if intersects2(p[a],p[b],p[c],p[d]): raise Refusal('TRIANGLE_CROSSING')

@dataclass(frozen=True)
class Face:
    points: tuple
    triangles: tuple
    projected_2d: tuple
    triangle_indices: tuple
    approximate: bool
    area_lo: F
    area_hi: F
    reference_lo: F
    reference_hi: F
    area_nominal_allowed: bool
    h: F
    diameter_lo: F
    diameter_hi: F
    tau: F
    resolution: F
    delta_area: F

def proxy_area_gates(al,au,h,lu,n):
    """Inputs are already certified metric bounds; no geometric provenance inferred."""
    if not 0<al<=au or h<0 or lu<=0 or type(n) is not int or n<3:
        raise Refusal('P_AREA_CERTIFICATE')
    delta = check(2*h*lu*(n-2))
    if delta>al/100: raise Refusal('P_GEOMETRIC_AREA_GATE')
    upper = check(au+delta)
    return delta,upper,upper-al<=al/100

def face(points, original, matrix, unit, physical):
    n = len(points)
    center = tuple(check(qsum(p[j] for p in points)/n) for j in range(3))
    normal = (F(0),)*3
    for a,b in edges(points): normal = add(normal,cross(sub(a,center),sub(b,center)))
    nn = norm2(normal)
    if nn==0: raise Refusal('NEWELL_ZERO')
    heights = tuple(dot(sub(p,center),normal) for p in points)
    approximate = any(heights)
    projected = tuple(sub(p,mul(normal,check(h/nn))) for p,h in zip(points,heights))
    axis = max(range(3),key=lambda j:abs(normal[j]))
    p2 = tuple(tuple(x for j,x in enumerate(p) if j!=axis) for p in projected)
    simple_polygon(p2)
    indices = triangulate(p2)
    triangles = tuple(tuple(projected[i] for i in t) for t in indices)
    al,au = root_bounds(nn)
    al,au = al/2,au/2
    if al<=0: raise Refusal('AREA_LOWER_NOT_POSITIVE')
    if not approximate:
        return Face(projected,triangles,p2,indices,False,al,au,al,au,True,F(0),F(0),F(0),F(0),F(0),F(0))
    # q and N are rational: no unit-normal rounding or projected-point error.
    h = root_bounds(check(max(x*x for x in heights)/nn))[1]
    ll,lu = root_bounds(max(norm2(sub(a,b)) for a,b in combinations(points,2)))
    tau = min(F(1,100) if physical else F(1,100000),
              max(F(1,1000) if physical else F(1,1000000), ll/F(1000000)))
    if h>tau: raise Refusal('P_HEIGHT_GATE')
    frob2 = qsum(check(x*x) for row in matrix for x in row)
    r2 = max(qsum(check(f32_radius(x)**2) for x in p) for p in original)
    resolution = root_bounds(check(r2*frob2*unit*unit))[1]
    if resolution>tau/4: raise Refusal('P_STORED_RESOLUTION_GATE')
    delta,upper,total_ok = proxy_area_gates(al,au,h,lu,n)
    return Face(projected,triangles,p2,indices,True,al,upper,al,au,total_ok,h,ll,lu,tau,resolution,delta)

def squared_distance(ka,a,kb,b):
    if (ka,kb)==('V','V'): return norm2(sub(a[0],b[0]))
    if (ka,kb)==('V','E'): return point_segment(a[0],*b)
    if (ka,kb)==('E','V'): return point_segment(b[0],*a)
    if (ka,kb)==('E','E'): return segment_segment(*a,*b)
    if ka=='F' and kb!='F': return squared_distance(kb,b,ka,a)
    if (ka,kb)==('V','F'): return min(point_triangle(a[0],t) for t in b.triangles)
    if (ka,kb)==('E','F'): return min(segment_triangle(*a,t) for t in b.triangles)
    if (ka,kb)==('F','F'): return min(triangle_triangle(x,y) for x in a.triangles for y in b.triangles)
    raise Refusal('DISTANCE_MODALITY')

def contact(ka,a,kb,b):
    if (ka,kb)==('V','V'): return a[0]==b[0]
    if (ka,kb)==('V','E'): return point_on_segment(a[0],*b)
    if (ka,kb)==('E','V'): return point_on_segment(b[0],*a)
    if (ka,kb)==('E','E'): return segment_contact(*a,*b)
    if ka=='F' and kb!='F': return contact(kb,b,ka,a)
    if (ka,kb)==('V','F'): return any(point_triangle_contact(a[0],t) for t in b.triangles)
    if (ka,kb)==('E','F'): return any(segment_triangle_contact(*a,t) for t in b.triangles)
    return any(any(segment_triangle_contact(x,y,tb) for x,y in edges(ta)) or
               any(segment_triangle_contact(x,y,ta) for x,y in edges(tb))
               for ta in a.triangles for tb in b.triangles)
