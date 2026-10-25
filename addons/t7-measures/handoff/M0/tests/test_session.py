import unittest
from dataclasses import replace
from fractions import Fraction as F
from t7m.session import Mesh,Context,Selection,Click,Instance,canonical,byte_count
from t7m.numeric import Refusal

BASE = Mesh(((0,0,0),(1,0,0),(0,1,0),(0,0,5)),
            ((0,1),(1,2),(2,0),(0,3)),
            (((0,0),(1,1),(2,2)),))

def sel(kind='V',idx=0,hidden=False):return Selection(kind,((idx,True,hidden),))
def click(context=Context(),mesh=BASE,selection=sel()):
    return Click(context,mesh,selection,context,mesh,selection)

class SessionTests(unittest.TestCase):
    def test_V_to_FACE_between_clicks_allowed_mixed_measure(self):
        inst=Instance()
        self.assertEqual(inst.capture('A',click(selection=sel('V',3)))['status'],'CAPTURED')
        signature=inst.signature
        self.assertIs(type(signature),bytes)
        self.assertEqual(inst.capture('B',click(selection=sel('F',0)))['status'],'CAPTURED')
        self.assertEqual(inst.signature,signature)
        r=inst.calculate(click(selection=sel('F',0)))
        self.assertEqual(r['distance']['certificate'].lo,5)
        self.assertIsNone(inst.signature);self.assertIsNone(inst.a);self.assertIsNone(inst.b)
        self.assertEqual(inst.last,r)
        self.assertEqual(inst.calculate(click())['status'],'REFUSED')
        self.assertIsNone(inst.last)

    def test_new_A_replaces_entire_cycle_and_owner(self):
        inst=Instance()
        inst.capture('A',click());inst.capture('B',click(selection=sel('E',0)))
        other=Context(area=2,window=2)
        inst.capture('A',click(context=other,selection=sel('V',3)))
        self.assertIsNone(inst.b);self.assertFalse(inst.active_in(Context()))
        self.assertTrue(inst.active_in(other))
        self.assertEqual(inst.capture('B',click())['status'],'REFUSED')
        self.assertIsNone(inst.signature)

    def test_many_areas_one_slot(self):
        inst=Instance()
        for area in range(1,31):inst.capture('A',click(context=Context(area=area)))
        self.assertEqual(inst.owner.area,30)
        self.assertEqual(sum(inst.active_in(Context(area=a)) for a in range(1,31)),1)

    def test_context_identity_generation_and_units(self):
        for changed in (Context(generation=1),Context(scene=2),Context(view_layer=2),Context(object=2),
                        Context(datablock=2),Context(registration='new-registration'),Context(frame=2),
                        Context(temporal=('new-evaluation',)),Context(scale_length=1),Context(system='NONE'),
                        Context(translation=(1,0,0)),Context(matrix=((2,0,0),(0,1,0),(0,0,1)))):
            with self.subTest(context=changed):
                inst=Instance();inst.capture('A',click())
                self.assertEqual(inst.capture('B',click(context=changed))['status'],'REFUSED')
                self.assertIsNone(inst.a)

    def test_events_clear_captures_and_last(self):
        for event in ('Undo','Redo','load','unregister','frame','session'):
            inst=Instance();inst.capture('A',click());inst.capture('B',click(selection=sel('V',3)))
            inst.calculate(click());self.assertIsNotNone(inst.last)
            inst.invalidate(event)
            self.assertIsNone(inst.last);self.assertIsNone(inst.signature)

    def test_global_revision_changes_even_with_same_digest(self):
        # No digest is consulted at all: synthetic equal digest would be irrelevant.
        changed=replace(BASE,vertices=BASE.vertices[:3]+((0,0,6),))
        self.assertNotEqual(canonical(BASE),canonical(changed))
        inst=Instance();inst.capture('A',click())
        self.assertEqual(inst.capture('B',click(mesh=changed))['status'],'REFUSED')
        inst.capture('A',click());inst.capture('B',click(selection=sel('V',3)))
        self.assertEqual(inst.calculate(click(mesh=changed))['status'],'REFUSED')
        self.assertIsNone(inst.last)

    def test_silent_occurrence_coordinate_swap(self):
        changed=replace(BASE,vertices=(BASE.vertices[1],BASE.vertices[0])+BASE.vertices[2:])
        self.assertNotEqual(canonical(BASE),canonical(changed))
        inst=Instance();inst.capture('A',click())
        self.assertEqual(inst.capture('B',click(mesh=changed))['status'],'REFUSED')
        self.assertNotEqual(canonical(Mesh(((0.0,0.0,0.0),))),canonical(Mesh(((-0.0,0.0,0.0),))))

    def test_loop_edge_occurrences_are_authoritative(self):
        duplicated=replace(BASE,edges=BASE.edges+((0,1),))
        changed=replace(duplicated,faces=(((0,4),(1,1),(2,2)),))
        self.assertNotEqual(canonical(duplicated),canonical(changed))
        inst=Instance();inst.capture('A',click(mesh=duplicated))
        self.assertEqual(inst.capture('B',click(mesh=changed))['status'],'REFUSED')
        broken=replace(BASE,faces=(((0,1),(1,1),(2,2)),))
        with self.assertRaises(Refusal):canonical(broken)

    def test_double_check_mutation_and_flags(self):
        mutations=(dict(context2=Context(generation=1)),
                   dict(mesh2=replace(BASE,vertices=BASE.vertices[:3]+((0,0,6),))),
                   dict(selection2=sel('V',1)),dict(selection2=sel('V',0,True)),
                   dict(selection2=Selection('V',((0,False,False),))))
        for patch in mutations:
            with self.subTest(patch=patch):
                inst=Instance();inst.last={'old':5}
                self.assertEqual(inst.capture('A',replace(click(),**patch))['status'],'REFUSED')
                self.assertIsNone(inst.last);self.assertIsNone(inst.signature)

    def test_hiding_A_between_clicks_not_in_signature(self):
        inst=Instance();inst.capture('A',click())
        selection=Selection('V',((0,True,True),(3,True,False)))
        self.assertEqual(inst.capture('B',click(selection=selection))['status'],'CAPTURED')
        self.assertEqual(inst.calculate(click(selection=selection))['distance']['certificate'].lo,5)

    def test_selection_modes_visibility_and_multi_edit(self):
        bads=(Selection('VERT_EDGE',((0,True,False),)),Selection('V',()),
              Selection('V',((0,True,False),(1,True,False))),Selection('V',((0,True,True),)))
        for bad in bads:
            self.assertEqual(Instance().capture('A',click(selection=bad))['status'],'REFUSED')
        for ctx in (Context(mode='OBJECT'),Context(objects_in_mode=2)):
            self.assertEqual(Instance().capture('A',click(context=ctx))['status'],'REFUSED')

    def test_new_A_failure_discards_old_and_encoding_size(self):
        inst=Instance();inst.capture('A',click())
        inst.capture('A',click(selection=Selection('V',())))
        self.assertIsNone(inst.signature)
        self.assertEqual(len(canonical(BASE)),byte_count(BASE))
        # Canonical data intentionally cannot silently convert a rational not in binary64.
        with self.assertRaises(Refusal):canonical(Mesh(((F(1,3),0,0),)))

if __name__=='__main__':unittest.main()
