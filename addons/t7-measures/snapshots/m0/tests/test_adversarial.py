"""Cross-component regressions and conservative negative controls."""
import unittest, random, struct, tracemalloc, sys
from unittest.mock import patch
from dataclasses import replace
from fractions import Fraction as F
from t7m import Entity as E, Query as Q, measure
from t7m import geometry as g
from t7m.numeric import Refusal, _meter, MAX_STEPS, WORK_BITS, number
from t7m.resources import geometry_plan
from t7m.presentation import Certificate as C, publish
from t7m.session import Instance,Context
from test_kernel import face, D
from test_session import click,sel
from oracle_active_sets import distance2

class AdversarialTests(unittest.TestCase):
    def test_only_total_area_gate_failure_keeps_distance_all_F_modes(self):
        original=g.face
        def coarse(*args,**kwargs):
            f=original(*args,**kwargs)
            if not f.approximate:return f
            # Widening an already proved reference enclosure is conservative.
            # This is an explicit injected uncertainty, not a naturally observed failure.
            delta,upper,total=g.proxy_area_gates(f.reference_lo,f.reference_hi+f.reference_lo/50,
                                                f.h,f.diameter_hi,len(f.points))
            self.assertFalse(total)
            return replace(f,area_hi=upper,area_nominal_allowed=total)
        p=face(twist=.0002,size=10)
        for a in (E('V',((0,0,5),)),E('E',((0,0,5),(1,0,5))),face(5,size=10)):
            with self.subTest(kind=a.kind),patch('t7m.geometry.face',coarse):
                r=measure(Q(a,p));self.assertEqual(r['status'],'COMPUTED_OFFLINE',r)
                self.assertGreater(r['distance']['certificate'].lo,F(4999,1000))
                affected=r['sizes'][-1]
                self.assertEqual(affected['display']['state'],'AREA_INDETERMINADA_POR_INCERTEZA_TOTAL')
                self.assertIsNone(affected['display']['nominal'])

    def test_area_retained_when_distance_certificate_unavailable(self):
        with patch('t7m.geometry.squared_distance',side_effect=Refusal('INJECTED_CERTIFICATE_FAILURE')):
            r=measure(Q(face(),face(5)))
        self.assertEqual(len(r['sizes']),2)
        self.assertIsNone(r['distance']['certificate'])
        self.assertEqual(r['distance']['display']['state'],'INDETERMINADO_SEM_FAIXA')

    def test_geometric_gate_failure_clears_entire_composite(self):
        p=face(size=.001,twist=.0003)
        for a in (E('V',((0,0,5),)),E('E',((0,0,5),(1,0,5))),face(5)):
            r=measure(Q(a,p))
            self.assertEqual(r['status'],'REFUSED');self.assertEqual(r['sizes'],())
            self.assertIsNone(r['distance'])

    def test_operation_and_bit_budget_fail_closed(self):
        token=_meter.set([MAX_STEPS])
        try:
            with self.assertRaises(Refusal):g.dot((F(1),)*3,(F(1),)*3)
        finally:_meter.reset(token)
        with self.assertRaises(Refusal):g.norm2((F(2)**WORK_BITS,F(0),F(0)))
        r=measure(Q(E('V',((2**2047,0,0),)),E('V',((-2**2047,0,0),))))
        self.assertEqual(r['distance']['display']['state'],'INDETERMINADO_SEM_FAIXA')
        self.assertIsNone(r['distance']['certificate'])
        self.assertEqual(r['sizes'],())

    def test_rigid_rational_rotation_scaling_and_affine_oracle(self):
        a=E('F',((0,0,0),(2,0,0),(0,2,0)))
        b=E('E',((3,0,2),(3,3,4)))
        rotation=((F(3,5),F(-4,5),0),(F(4,5),F(3,5),0),(0,0,1))
        c=D(a,b,matrix=rotation)
        original=D(a,b)
        self.assertEqual((c.lo,c.hi),(original.lo,original.hi))
        proxy=face(twist=.0002,size=10)
        rotated=measure(Q(proxy,matrix=rotation))['sizes'][0]['face']
        base=measure(Q(proxy))['sizes'][0]['face']
        self.assertEqual((rotated.area_lo,rotated.area_hi,rotated.h),(base.area_lo,base.area_hi,base.h))
        r=measure(Q(a,b,matrix=((2,1,0),(0,-3,0),(0,0,4))))
        transform=lambda pts:tuple((2*x+y,-3*y,4*z) for x,y,z in pts)
        expected=distance2(transform(a.points),transform(b.points))
        self.assertEqual(r['distance']['squared_proxy'],expected)

    def test_single_edge_and_ambiguous_order(self):
        r=measure(Q(E('E',((0,0,0),(3,4,0)))))
        self.assertEqual(r['sizes'][0]['certificate'].lo,5)
        r=measure(Q(E('E',((0,0,0),(0,0,0)))))
        self.assertEqual(r['sizes'][0]['display']['state'],'COMPRIMENTO_DEGENERADO')
        r=measure(Q(E('E',((0,0,0),(3,4,0))),E('E',((0,1,0),(3,5,0)))))
        self.assertIsNone(r['ordering']['order'])

    def test_mutable_context_is_copied_and_stale_value_removed(self):
        matrix=[[1,0,0],[0,1,0],[0,0,1]]
        ctx=Context(matrix=matrix)
        inst=Instance();self.assertEqual(inst.capture('A',click(context=ctx))['status'],'CAPTURED')
        self.assertIs(type(inst.owner.matrix),tuple)
        matrix[0][0]=2
        self.assertEqual(inst.capture('B',click(context=ctx,selection=sel('V',3)))['status'],'REFUSED')
        self.assertIsNone(inst.signature)
        self.assertEqual(Instance().capture('A',click(context=Context(temporal=([],))))['status'],'REFUSED')

    def test_positive_nominal_omission_if_rounding_uncertain(self):
        c=C(F(499,1000000),F(501,1000000),reference=(F(499,1000000),F(501,1000000)))
        r=publish(c)
        self.assertIsNone(r['nominal']);self.assertFalse(r['sub_q'])
        self.assertIsNone(publish(c,nominal=F(499,1000000))['nominal'])
        self.assertEqual(r['state'],'POSITIVO_CERTIFICADO')
        for invalid in (True,-1,7,'3'):
            self.assertEqual(publish(c,p=invalid)['state'],'INDETERMINADO_SEM_FAIXA')

    def test_proxy_boundary_reordering_and_large_translation_refusal(self):
        a=face(twist=.0002,size=10)
        reverse=E('F',tuple(reversed(a.points)))
        for p in (a,reverse):
            c=D(E('V',((5,5,5),)),p)
            self.assertGreater(c.lo,4);self.assertFalse(c.contact_proven)
        shifted=E('F',tuple((x+16384,y,z) for x,y,z in a.points))
        self.assertIn('P_STORED_RESOLUTION_GATE',measure(Q(shifted))['reason'])

    def test_preflight_runs_before_geometry(self):
        huge=E('F',((0,0,0),)*512)
        with patch('t7m.geometry.face',side_effect=AssertionError('must not enter')):
            self.assertEqual(measure(Q(huge))['status'],'REFUSED')

if __name__=='__main__':unittest.main()
