import unittest
from fractions import Fraction as F
from decimal import Decimal, localcontext
import random, struct, math
from dataclasses import replace
from t7m import Entity as E, Query as Q, measure
from t7m.numeric import root_bounds, number, f32_radius, Refusal
from t7m.geometry import validate_triangulation
from t7m.presentation import Certificate as C, publish, compare
from t7m.resources import geometry_plan, snapshot_plan
from oracle_active_sets import distance2

def f32(x): return struct.unpack('>f',struct.pack('>f',x))[0]
def face(z=0,x=0,twist=0,size=2):
    return E('F',tuple(tuple(f32(v) for v in p) for p in
             ((x,0,z),(x+size,0,z),(x+size,size,z+twist),(x,size,z))))
def D(a,b,**kw):
    r = measure(Q(a,b,**kw))
    assert r['status']=='COMPUTED_OFFLINE',r
    assert r['distance']['certificate'] is not None,r
    return r['distance']['certificate']

class GeometryTests(unittest.TestCase):
    def exact_distance(self,a,b,sq,**kw):
        r=measure(Q(a,b,**kw))
        self.assertEqual(r['status'],'COMPUTED_OFFLINE',r)
        self.assertEqual(r['distance']['squared_proxy'],sq,r)
        c=r['distance']['certificate']
        self.assertLessEqual(c.lo*c.lo,sq)
        self.assertGreaterEqual(c.hi*c.hi,sq)
        self.assertEqual(c.contact_proven,sq==0)
        return r

    def test_G01_G03(self):
        self.exact_distance(E('V',((0,0,0),)),E('V',((3,4,0),)),25)
        edge=E('E',((0,0,0),(10,0,0)))
        self.exact_distance(E('V',((1,1,0),)),edge,1)
        self.exact_distance(E('V',((15,4,0),)),edge,41)

    def test_G04_G08_G05bc(self):
        cases=[(((-1,0,0),(1,0,0)),((0,-1,0),(0,1,0)),0),
               (((0,0,0),(5,0,0)),((2,0,0),(7,0,0)),0),
               (((0,0,0),(2,0,0)),((5,0,0),(7,0,0)),9),
               (((3,3,3),(3,3,3)),((0,0,0),(3,0,0)),18),
               (((0,0,0),(1000000,0,0)),((0,1,0),(1000000,F(1001,1000),0)),1),
               (((0,0,0),(1000000,0,0)),((0,F(-1,2000),0),(1000000,F(1,2000),0)),0),
               (((0,0,0),(1000000,0,0)),((0,F(-1,2000),F(1,500)),(1000000,F(1,2000),F(1,500))),F(1,250000))]
        for a,b,sq in cases:
            with self.subTest(a=a,b=b): self.exact_distance(E('E',a),E('E',b),sq)

    def test_G09_G12_area(self):
        tri=E('F',((0,0,0),(30,0,0),(0,40,0)))
        for matrix in (((1,0,0),(0,1,0),(0,0,1)),((0,-1,0),(1,0,0),(0,0,1))):
            c=measure(Q(tri,matrix=matrix))['sizes'][0]['certificate']
            self.assertEqual((c.lo,c.hi),(600,600))
        t=E('F',((0,0,0),(1,0,0),(0,1,1)))
        c=measure(Q(t,matrix=((2,0,0),(0,3,0),(0,0,4))))['sizes'][0]['certificate']
        self.assertEqual((c.lo,c.hi),(5,5))
        c=measure(Q(t,matrix=((1,0,0),(0,1,0),(2,0,1))))['sizes'][0]['certificate']
        self.assertLessEqual(c.lo*c.lo,F(3,2));self.assertGreaterEqual(c.hi*c.hi,F(3,2))

    def test_G13_G17_G24(self):
        self.exact_distance(face(),face(5),25)
        self.exact_distance(face(),face(4,5),25)
        a=E('F',((-2,-2,0),(2,-2,0),(0,2,0)))
        b=E('F',((0,-1,-1),(0,1,1),(0,2,-1)))
        self.exact_distance(a,b,0)
        a=E('F',((0,2,0),(-2,-1,0),(2,-1,0)))
        b=E('F',((0,-2,0),(-2,1,0),(2,1,0)))
        self.exact_distance(a,b,0)
        a=E('F',((0,0,0),(10,0,0),(0,10,0)))
        b=E('F',((1,1,0),(2,1,0),(1,2,0)))
        self.exact_distance(a,b,0)
        self.exact_distance(a,E('F',((0,0,0),(0,-1,0),(10,0,0))),0)

    def test_G18_G20_G25(self):
        tri=E('F',((0,0,0),(2,0,0),(0,2,0)))
        self.exact_distance(E('V',((2,2,3),)),tri,11)
        big=E('F',((0,0,0),(10,0,0),(0,10,0)))
        self.exact_distance(E('E',((2,2,-3),(2,2,4))),big,0)
        high=E('F',((-1,-1,2),(1,-1,2),(0,1,2)))
        self.exact_distance(E('E',((0,0,0),(0,0,1))),high,1)
        for z in (F(0),F(1,100)):
            self.exact_distance(E('E',((F(1,4),F(1,4),z),(F(1,2),F(1,4),z))),tri,z*z)
        self.exact_distance(E('E',((0,0,-1),(0,0,0))),tri,0)

    def test_G21_concave_rotated_reflected(self):
        poly=E('F',tuple((x,y,0) for x,y in ((0,0),(4,0),(4,1),(1,1),(1,4),(0,4))))
        p=E('V',((2,2,1),))
        for m in (((1,0,0),(0,1,0),(0,0,1)),((0,-1,0),(1,0,0),(0,0,1)),((-1,0,0),(0,1,0),(0,0,1))):
            r=self.exact_distance(p,poly,2,matrix=m)
            self.assertEqual(r['sizes'][0]['certificate'].lo,7)

    def test_G22_G23_invalid(self):
        cases=[((0,0,0),(1,0,0),(1,1,1),(0,1,0)),
               ((0,0,0),(1,0,0),(1,0,0)),
               ((0,0,0),(1,1,0),(0,1,0),(1,0,0)),
               ((0,0,0),(2,0,0),(1,0,0),(1,1,0)),
               ((0,0,0),(2,0,0),(1,1,0),(1,0,0),(0,1,0))]
        for pts in cases:
            with self.subTest(pts=pts): self.assertEqual(measure(Q(E('F',pts)))['status'],'REFUSED')

    def test_G26_G30_small_positive(self):
        c=D(E('V',((0,0,0),)),E('V',((F(49,100000),0,0),)))
        self.assertTrue(publish(c)['sub_q'])
        c=measure(Q(E('F',((0,0,0),(1,0,0),(2,F(1,10**12),0)))))['sizes'][0]['certificate']
        self.assertEqual(c.lo,F(1,2*10**12));self.assertTrue(publish(c,unit='mm2')['sub_q'])

    def test_shared_anchor_large_offsets_units(self):
        a=E('V',((F(10**20),0,0),)); b=E('V',((F(10**20)+F(1,1000),0,0),))
        self.exact_distance(a,b,F(1,1000000))
        self.assertEqual(D(a,b,system='NONE').lo,F(1,1000))
        self.assertEqual(D(a,b,system='IMPERIAL',scale_length=1).lo,1)
        self.assertEqual(D(E('V',((0,0,5),)),face()).lo,5)
        self.assertEqual(D(face(),E('E',((0,0,5),(1,0,5)))).lo,5)

    def test_singular_near_singular_bad_types(self):
        a=E('V',((0,0,0),));b=E('V',((1,0,0),))
        for m in (((1,0,0),(0,1,0),(0,0,0)),((1,0,0),(0,1,0),(0,0,F(1,10**20)))):
            self.assertEqual(measure(Q(a,b,matrix=m))['status'],'REFUSED')
        for v in (float('nan'),float('inf'),True,'1',None,Decimal('NaN'),Decimal('1e999999')):
            self.assertEqual(measure(Q(a,E('V',((v,0,0),))))['status'],'REFUSED')

    def test_random_convex_KKT_oracle(self):
        rng=random.Random(73181)
        for i in range(36):
            na,nb=1+i%3,1+(i//3)%3
            a=tuple(tuple(F(rng.randrange(-15,16),8) for _ in range(3)) for _ in range(na))
            b=tuple(tuple(F(rng.randrange(-15,16),8) for _ in range(3)) for _ in range(nb))
            ka,kb={1:'V',2:'E',3:'F'}[na],{1:'V',2:'E',3:'F'}[nb]
            with self.subTest(seed=73181,index=i,modalities=(ka,kb)):
                r=self.exact_distance(E(ka,a),E(kb,b),distance2(a,b))
                reverse=measure(Q(E(kb,b),E(ka,a)))
                self.assertEqual(r['distance']['squared_proxy'],reverse['distance']['squared_proxy'])

class ProxyTests(unittest.TestCase):
    def test_P_positive_uncertain_and_symmetry(self):
        a=face(twist=.0002,size=10); b=face(5,twist=.0002,size=10)
        c=D(a,b)
        self.assertTrue(c.approximate);self.assertGreater(c.lo,F(4999,1000));self.assertFalse(c.contact_proven)
        rev=D(b,a)
        self.assertEqual((c.lo,c.hi),(rev.lo,rev.hi))
        d=D(E('V',((0,0,0),)),a)
        self.assertEqual(d.lo,0);self.assertFalse(d.contact_proven)
        self.assertEqual(publish(d)['state'],'INDETERMINADO_COM_FAIXA')
        for x in (E('V',((0,0,5),)),E('E',((0,0,5),(1,0,5)))):
            self.assertGreater(D(x,a).lo,F(4999,1000))

    def test_P_two_diagonals_area_distance_oracle(self):
        a=face(twist=.0002,size=10)
        r=measure(Q(a));self.assertEqual(r['status'],'COMPUTED_OFFLINE',r)
        f=r['sizes'][0]['face']
        self.assertTrue(f.approximate);self.assertTrue(f.area_nominal_allowed)
        p=E('V',((5,5,5),)); c=D(p,a)
        diagonals=(((0,1,2),(0,2,3)),((0,1,3),(1,2,3)))
        with localcontext() as ctx:
            ctx.prec=100
            dec=lambda x: Decimal(x.numerator)/Decimal(x.denominator)
            original=[tuple(F(x) for x in v) for v in a.points]
            for triangles in diagonals:
                sq=min(distance2(p.points,tuple(original[i] for i in t)) for t in triangles)
                self.assertLessEqual(c.lo*c.lo,sq);self.assertGreaterEqual(c.hi*c.hi,sq)
                area=Decimal(0)
                for i,j,k in triangles:
                    u=[original[j][d]-original[i][d] for d in range(3)]
                    v=[original[k][d]-original[i][d] for d in range(3)]
                    cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                    area+=dec(sum(x*x for x in cross)).sqrt()/2
                self.assertLessEqual(dec(f.area_lo),area);self.assertGreaterEqual(dec(f.area_hi),area)

    def test_P_failures(self):
        self.assertEqual(measure(Q(face(twist=.05,size=10)))['status'],'REFUSED')
        self.assertIn('P_GEOMETRIC_AREA_GATE',measure(Q(face(twist=.0003,size=.001)))['reason'])
        high=E('F',tuple(tuple(f32(v) for v in p) for p in ((10000,0,0),(10010,0,0),(10010,10,.0002),(10000,10,0))))
        self.assertIn('P_STORED_RESOLUTION_GATE',measure(Q(high))['reason'])
        rational=E('F',((0,0,0),(1,0,0),(1,1,F(1,100000)),(0,1,0)))
        self.assertIn('BINARY32_SOURCE_REQUIRED',measure(Q(rational))['reason'])

    def test_P_rotation_shear_and_NONE(self):
        a=face(twist=.0002,size=10)
        c=math.sqrt(.5)
        for matrix in (((0,-1,0),(1,0,0),(0,0,1)),((-1,0,0),(0,1,0),(0,0,1)),((1,0,0),(0,1,0),(1,0,1)),((c,-c,0),(c,c,0),(0,0,1))):
            r=measure(Q(a,matrix=matrix));self.assertEqual(r['status'],'COMPUTED_OFFLINE',r)
            self.assertTrue(r['sizes'][0]['face'].approximate)
        tiny=face(twist=f32(1e-8),size=1)
        r=measure(Q(tiny,system='NONE'));self.assertEqual(r['unit'],'BU')
        self.assertEqual(r['sizes'][0]['display']['unit'],'BU2')

    def test_tessellation_negative_controls(self):
        p=((F(0),F(0)),(F(2),F(0)),(F(2),F(2)),(F(0),F(2)))
        validate_triangulation(p,((0,1,2),(0,2,3)))
        for tris in (((0,1,2),),((0,1,2),(0,1,2)),((0,1,2),(0,3,2)),((0,1,4),(0,2,3))):
            with self.assertRaises(Refusal):validate_triangulation(p,tris)

class NumericPolicyTests(unittest.TestCase):
    def test_root_extremes_and_strict_bounds(self):
        for x in (F(2),F(1,2**2148),F(2)**2046,F(3,2**2000),F(0),F(25)):
            l,u=root_bounds(x);self.assertLessEqual(l*l,x);self.assertGreaterEqual(u*u,x)
            if x:self.assertGreater(l,0)
        for value in (Decimal('NaN'),Decimal('Infinity'),float('inf'),'2',True):
            with self.assertRaises(Refusal):number(value)

    def test_binary32_zero_subnormal_bits(self):
        self.assertEqual(f32_radius(F(0)),F(1,2**150))
        self.assertEqual(f32_radius(F(1,2**149)),F(1,2**150))
        self.assertEqual(f32_radius(F(1)),F(1,2**24))
        self.assertEqual(number(-0.0),0)
        self.assertEqual(f32(10000.0004),10000)
        with self.assertRaises(Refusal):f32_radius(F.from_float(0.1))

    def test_HALF_EVEN_actual_bits_all_units(self):
        from t7m.numeric import half_even
        for p in (0,3,6):
            tie=F(1,2*10**p)
            self.assertEqual(half_even(tie,p),0)
            for v in (math.nextafter(float(tie),-math.inf),float(tie),math.nextafter(float(tie),math.inf)):
                actual=F.from_float(v)
                with localcontext() as ctx:
                    ctx.prec=120
                    expected=int((Decimal.from_float(v)*Decimal(10)**p).to_integral_value(rounding='ROUND_HALF_EVEN'))
                self.assertEqual(half_even(actual,p),expected)
                for unit in ('mm','BU','mm2','BU2'):
                    c=C(actual,actual,'area' if unit.endswith('2') else 'distance')
                    result=publish(c,p,unit,nominal=v)
                    self.assertNotEqual(result['state'],'INDETERMINADO_SEM_FAIXA')

    def test_R81_bounds_nominal_invalid(self):
        for bad in (float('nan'),float('inf'),Decimal('NaN'),'1',True,None):
            self.assertEqual(publish(C(bad,1))['state'],'INDETERMINADO_SEM_FAIXA')
        self.assertEqual(publish(C(2,1))['state'],'INDETERMINADO_SEM_FAIXA')
        self.assertEqual(publish(C(1,2),nominal=3)['state'],'INDETERMINADO_SEM_FAIXA')
        self.assertEqual(publish(C(1,2),nominal=float('nan'))['state'],'INDETERMINADO_SEM_FAIXA')
        self.assertEqual(publish(C(1,2))['state'],'POSITIVO_CERTIFICADO')
        self.assertIsNone(publish(C(1,2))['nominal'])
        self.assertEqual(publish(C(0,0))['state'],'INDETERMINADO_COM_FAIXA')
        self.assertEqual(publish(C(1,2,contact_proven=True))['state'],'INDETERMINADO_SEM_FAIXA')

    def test_UX_subq_total_gate_independence(self):
        for p in (0,3,6):
            q=F(1,10**p)
            for hi,allowed in ((q*F(135,100),False),(q,False),(q*F(9,10),True)):
                r=publish(C(q/4,hi),p,nominal=q*F(4,10));self.assertEqual(r['sub_q'],allowed)
            r=publish(C(0,q*F(4,10)),p,nominal=0)
            self.assertEqual(r['state'],'INDETERMINADO_COM_FAIXA');self.assertIsNone(r['nominal'])
            c=C(q/4,q*F(9,10),'area',True,False,False)
            r=publish(c,p,'BU2',nominal=q*F(4,10))
            self.assertFalse(r['sub_q']);self.assertIsNone(r['nominal'])
        a=C(F(10001,10000),F(1004,1000),'area');b=C(F(10041,10000),F(1008,1000),'area')
        self.assertEqual(compare(a,b,2),dict(order=-1,rounded_overlap_warning=True))
        self.assertIsNone(compare(C(1,2),C(2,3))['order'])
        self.assertIsNone(compare(C(1,F(1005,1000)),C(F(1004,1000),F(1006,1000)))['order'])

    def test_resource_refusal_preflight(self):
        for n in (448,512,513):
            with self.assertRaises(Refusal):geometry_plan(('F',),(n,))
        with self.assertRaises(Refusal):geometry_plan(('F','F'),(226,226))
        with self.assertRaises(Refusal):snapshot_plan(1,0,0,0,(45*1024**2,)*3)
        with self.assertRaises(Refusal):snapshot_plan(500001,0,0,0,(0,0,0))
        with self.assertRaises(Refusal):snapshot_plan(1,0,0,1000001,(0,0,0))
        with self.assertRaises(Refusal):geometry_plan(('F','F'),(4,4),retained=50*1024**2)
        self.assertLessEqual(geometry_plan(('F',),(4,))['total'],200000)

if __name__=='__main__':unittest.main()
