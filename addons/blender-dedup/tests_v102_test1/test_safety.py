"""Development safety inversions and extra synthetic boundaries. No bpy/Blender."""
import copy, importlib.util, json, subprocess, sys, time, unittest, threading
from pathlib import Path
from unittest.mock import patch
import numpy as np
from fixtures import f, d, ROOT

class Safety(unittest.TestCase):
    def assert_zero(self,b,callback=None):
        with self.assertRaises(d.PreflightAborted) as caught:
            d.execute(b,emit=callback or (lambda *_:None))
        self.assertEqual(b.objects.remove_calls,0)
        self.assertEqual(caught.exception.ledger['calls_attempted'],0)
        return caught.exception.ledger

    def test_A_REF01_B04_parent_after_ledger(self):
        b,o=f.basic();survivor=f.Obj('empty',None,kind='EMPTY');b.objects.append(survivor)
        def emit(label,payload):
            if label=='[T7-DEDUP-LEDGER-PRE]':survivor.parent=o[0]
        self.assert_zero(b,emit)

    def test_A_REF02_after_first_remove(self):
        b,o=f.basic();s=f.Obj('empty',None,kind='EMPTY');b.objects.append(s)
        original=b.objects.remove
        def remove(obj,do_unlink=False):
            original(obj,do_unlink=do_unlink);s.parent=o[2]
        b.objects.remove=remove
        with self.assertRaises(d.ExecutionFailure) as caught:d.execute(b,emit=lambda *_:None)
        self.assertEqual(b.objects.remove_calls,1)
        self.assertIn(o[0],b.objects)
        self.assertEqual(caught.exception.ledger['status'],'FALHA_PARCIAL_POSSIVEL')
        self.assertEqual(caught.exception.ledger['reconciliation']['removed_confirmed'],1)

    def test_mutation_after_first_remove_targets_next_drop(self):
        b,o=f.basic();survivor=f.Obj('empty',None,kind='EMPTY');b.objects.append(survivor)
        original=b.objects.remove
        def remove(obj,do_unlink=False):
            original(obj,do_unlink=do_unlink)
            if b.objects.remove_calls==1:survivor.parent=o[0]
        b.objects.remove=remove
        with self.assertRaises(d.ExecutionFailure):d.execute(b,emit=lambda *_:None)
        self.assertEqual(b.objects.remove_calls,1);self.assertIn(o[0],b.objects)

    def test_indirect_drop_key_and_abort_decisions(self):
        b,o=f.basic();instancer=f.Obj('instance',None,kind='EMPTY')
        instancer.instance_collection=b.collections[0];b.objects.append(instancer)
        ledger=self.assert_zero(b)
        refs=[r for r in ledger['inventory']['references'] if r['relation_category']=='FUNCIONAL_INDIRETA']
        self.assertEqual({r['drop_key']['pointer'] for r in refs},{d.stable_id(o[0]),d.stable_id(o[2])})
        self.assertEqual(len(ledger['plan']['decisions']),2)
        self.assertTrue(all(row['action']=='STOP_NO_MORE_REMOVALS' for row in ledger['decisions']))

    def test_B01_keep_edit(self):
        b,o=f.basic();o[1].mode='EDIT';self.assert_zero(b)

    def test_B02_geometry_after_ledger(self):
        b,o=f.basic()
        def emit(label,payload):
            if label=='[T7-DEDUP-LEDGER-PRE]':o[0].data.vertices.rows[0]['co']=(500.,500.,500.)
        self.assert_zero(b,emit)

    def test_B03_modifier_after_ledger(self):
        b,o=f.basic();s=f.Obj('empty',None,modifier_count=1,kind='EMPTY');b.objects.append(s)
        def emit(label,payload):
            if label=='[T7-DEDUP-LEDGER-PRE]':s.modifiers[0].object=o[0]
        self.assert_zero(b,emit)

    def test_aliases_A_REF03_REF04_B05_B06_B07_B09(self):
        scripts=["module=bpy.data\nref=module.objects.get('model.000')",
                 "from bpy import data\nref=data.objects.get('model.000')",
                 "ref=getattr(bpy.data,'objects').get('model.000')",
                 "from bpy import data as d\nname='model.'+str(0).zfill(3)\nobj=d.objects[name]",
                 "import bpy as b\nwhich='obj'+'ects'\nref=getattr(b.data,which)[name]",
                 "__import__('b'+'py').data.objects[key]", "exec(encoded)",
                 "lookup = resolver(name)", "from helper import lookup\nlookup(name)"]
        for script in scripts:
            for surface in ('Text','IDProperty'):
                with self.subTest(script=script,surface=surface):
                    b,o=f.basic()
                    self.assertTrue(d._text_lookup_risk(script,{o[0].name}))
                    if surface=='Text':b.texts.append(f.FakeText('code',script))
                    else:
                        m=f.Material('config');m.idprops={'nested':{'script':script}};b.materials.append(m)
                    self.assert_zero(b)

    def test_A_REF05_B08_user_map_undercount(self):
        for kind in ('empty','sets','partial'):
            b,o=f.basic()
            if kind=='empty':b.user_map=lambda **_:{}
            if kind=='sets':b.user_map=lambda *,subset:{x:set() for x in subset}
            if kind=='partial':b.extra_user_map[o[0]]={b.scenes[0]}
            with self.subTest(kind=kind):self.assert_zero(b)

    def test_B_control_direct_lookup(self):
        b,o=f.basic();b.texts.append(f.FakeText('code',"bpy.data.objects['model.000']"));self.assert_zero(b)

    def test_B_control_nested_idpointer(self):
        b,o=f.basic();m=f.Material('m');m.idprops={'idref':{'links':[o[0]]}};b.materials.append(m);self.assert_zero(b)

    def test_B_control_keep_readonly(self):
        b,o=f.basic();o[1].library='linked.blend';o[1].is_editable=False
        self.assertEqual(f.quick_execute(b)['status'],'REMOVOES_CONFIRMADAS')
        self.assertEqual(b.objects.remove_calls,2)

    def test_B_control_drop_edit(self):
        b,o=f.basic();o[0].mode='EDIT';self.assert_zero(b)

    def test_callbacks_at_every_label_geometry_and_flags(self):
        for label in ('[T7-DEDUP-LEDGER-PRE]','[T7-DEDUP-BEFORE-REMOVE]','[T7-DEDUP-AFTER-REMOVE]','[T7-DEDUP-RESULT]'):
            for mutation in ('raw_coordinate','mode','rank','topology','name','mesh_edit'):
                b,o=f.basic()
                def emit(tag,payload):
                    if tag!=label:return
                    keep=o[1]
                    if mutation=='raw_coordinate':keep.data.vertices.rows[0]['co']=(1e-8,0,0) # same quantization
                    if mutation=='mode':keep.mode='EDIT'
                    if mutation=='rank':keep.modifiers.append(f.NS(bl_rna=f.RNA('Modifier',object='POINTER'),object=None))
                    if mutation=='topology':keep.data.loops.rows[0]['vertex_index']=2
                    if mutation=='name':keep.name='renamed'
                    if mutation=='mesh_edit':keep.data.is_editmode=True
                with self.subTest(label=label,mutation=mutation):
                    if label in ('[T7-DEDUP-LEDGER-PRE]','[T7-DEDUP-BEFORE-REMOVE]'):self.assert_zero(b,emit)
                    else:
                        with self.assertRaises(d.ExecutionFailure):d.execute(b,emit=emit)
                        self.assertEqual(b.objects.remove_calls,1 if label=='[T7-DEDUP-AFTER-REMOVE]' else 2)

    def test_reentry_poison_even_if_caught(self):
        b,o=f.basic();other,_=f.basic()
        def emit(label,payload):
            if label=='[T7-DEDUP-LEDGER-PRE]':
                try:d.execute(other,emit=lambda *_:None)
                except d.PreflightAborted:pass
        ledger=self.assert_zero(b,emit)
        self.assertEqual(other.objects.remove_calls,0)
        self.assertEqual(ledger['status'],'ABORT_POR_MUTACAO_ZERO_REMOVOES')

    def test_concurrent_execute_fails_closed(self):
        b,o=f.basic();other,_=f.basic();outcome=[]
        def attempt():
            try:d.execute(other,emit=lambda *_:None)
            except d.PreflightAborted:outcome.append('blocked')
        def emit(label,payload):
            if label=='[T7-DEDUP-LEDGER-PRE]':
                thread=threading.Thread(target=attempt);thread.start();thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
        self.assert_zero(b,emit)
        self.assertEqual(outcome,['blocked']);self.assertEqual(other.objects.remove_calls,0)

    def test_offline_guard_active(self):
        with self.assertRaises(ImportError):__import__('bpy')
        with self.assertRaisesRegex(RuntimeError,'file access prohibited'):
            open(ROOT/'work/must_never_open.blend','rb')
        import socket
        with self.assertRaisesRegex(RuntimeError,'network prohibited'):
            socket.getaddrinfo('github.com',443)

    def test_logger_payload_is_detached(self):
        b,o=f.basic()
        def emit(label,payload):
            if label=='[T7-DEDUP-LEDGER-PRE]':payload['clusters'].clear();payload['drops_count']=0
        r=d.execute(b,emit=emit)
        self.assertEqual(r['plan']['drops_count'],2);self.assertEqual(b.objects.remove_calls,2)

    def test_failures_before_after_first_second_last(self):
        for at in (1,2,3):
            for after in (False,True):
                for exception in (RuntimeError,KeyboardInterrupt):
                    b,o=f.basic();extra=f.Obj('model.003',f.Mesh(*f.triangle()));b.objects.append(extra)
                    b.meshes.append(extra.data);b.collections[0].objects.append(extra);b.scenes[0].objects.append(extra)
                    original=b.objects.remove
                    def remove(obj,do_unlink=False):
                        if b.objects.remove_calls+1==at and not after:
                            b.objects.remove_calls+=1;raise exception('before')
                        original(obj,do_unlink=do_unlink)
                        if b.objects.remove_calls==at and after:raise exception('after')
                    b.objects.remove=remove
                    with self.subTest(at=at,after=after,exception=exception):
                        with self.assertRaises(d.ExecutionFailure) as caught:d.execute(b,emit=lambda *_:None)
                        self.assertEqual(b.objects.remove_calls,at)
                        self.assertEqual(caught.exception.ledger['reconciliation']['removed_confirmed'],at if after else at-1)

    def test_remove_returns_without_effect(self):
        b,o=f.basic()
        def remove(*args,**kwargs):b.objects.remove_calls+=1
        b.objects.remove=remove
        with self.assertRaises(d.ExecutionFailure):d.execute(b,emit=lambda *_:None)
        self.assertEqual(b.objects.remove_calls,1)

    def test_last_remove_mutates_keep(self):
        b,o=f.basic();original=b.objects.remove
        def remove(obj,do_unlink=False):
            original(obj,do_unlink=do_unlink)
            if b.objects.remove_calls==2:o[1].data.vertices.rows[0]['co']=(100,0,0)
        b.objects.remove=remove
        with self.assertRaises(d.ExecutionFailure):d.execute(b,emit=lambda *_:None)
        self.assertEqual(b.objects.remove_calls,2)

    def test_logger_errors_every_phase(self):
        for label in ('[T7-DEDUP-LEDGER-PRE]','[T7-DEDUP-BEFORE-REMOVE]','[T7-DEDUP-AFTER-REMOVE]','[T7-DEDUP-RESULT]'):
            b,o=f.basic()
            def emit(tag,payload):
                if tag==label:raise OSError('broken logger')
            with self.subTest(label=label):
                with self.assertRaises((d.PreflightAborted,d.ExecutionFailure)) as caught:d.execute(b,emit=emit)
                self.assertIsNotNone(caught.exception.ledger)
                self.assertEqual(b.objects.remove_calls,0 if label in ('[T7-DEDUP-LEDGER-PRE]','[T7-DEDUP-BEFORE-REMOVE]') else 1 if label=='[T7-DEDUP-AFTER-REMOVE]' else 2)

    def test_MC07_aggregate_blockers_and_fields(self):
        b,o=f.basic();s=f.Obj('child',None,parent=o[0],kind='EMPTY');b.objects.append(s)
        m=f.Material('bad');m.idprops={'target':o[2]};b.materials.append(m)
        ledger=self.assert_zero(b)
        inv=ledger['inventory']
        self.assertGreaterEqual(len(inv['blockers']),2)
        for row in inv['references']:
            self.assertTrue({'drop_key','owner_lifecycle','scan_status','action','evidence','surface','path','reason'}<=row.keys())
        self.assertTrue(any(x['owner_lifecycle']=='SURVIVE' for x in inv['references']))

    def test_scan_failure_exposes_uninspected(self):
        b,o=f.basic();m=f.Material('bad');m.bl_rna=None;b.materials.append(m)
        inv=self.assert_zero(b)['inventory'];self.assertTrue(inv['uninspected'])

    def test_user_map_normalization_scene_projection(self):
        b,o=f.basic()
        b.user_map=lambda *,subset:{x:{b.collections[0]} for x in subset}
        self.assertEqual(f.quick_execute(b)['status'],'REMOVOES_CONFIRMADAS')

    def test_orphan_zero_users_legitimate(self):
        b,o=f.basic();b.collections.clear();b.scenes.clear()
        b.user_map=lambda *,subset:{}
        self.assertEqual(f.quick_execute(b)['status'],'REMOVOES_CONFIRMADAS')

    def test_real_unlink_membership_indexes(self):
        b,o=f.basic();original=b.objects.remove
        def remove(obj,do_unlink=False):
            original(obj,do_unlink=do_unlink)
            for col in b.collections:
                if obj in col.objects:col.objects.remove(obj)
            for scene in b.scenes:
                if obj in scene.objects:scene.objects.remove(obj)
        b.objects.remove=remove
        self.assertEqual(f.quick_execute(b)['status'],'REMOVOES_CONFIRMADAS')

    def test_rename_uid_reuse_and_reconciliation_failure(self):
        b,o=f.basic();_,_,plan=d.preflight(b)
        o[0].name='renamed'
        self.assertEqual(next(row for row in d.reconcile(plan,b)['items'] if row['snapshot']['pointer']==d.stable_id(o[0]))['status'],'CONFIRMADO_PRESENTE')
        o[0].session_uid=o[1].session_uid
        self.assertEqual(next(row for row in d.reconcile(plan,b)['items'] if row['snapshot']['pointer']==d.stable_id(o[0]))['status'],'INDETERMINADO')
        with patch.object(d,'_enumerate_current_snapshots',side_effect=RuntimeError('enumeration failed')):
            self.assertTrue(all(x['status']=='INDETERMINADO' for x in d.reconcile(plan,b)['items']))

    def test_MC03_memory_preallocation_100_200_240(self):
        for n in (100,200,240):
            with self.subTest(n=n):
                mesh=f.Mesh([(0,0,0)]*n,[],[]);q=np.zeros((n,3),dtype=np.int64);order=np.arange(n)
                budget=d.BudgetContext(d.Limits(mem_pair_bytes=60_000,pair_seconds=4))
                with self.assertRaises(d.ComplexityBudgetExceeded), d.bound_budget(budget),budget.pair():
                    d._ambiguous_isomorphism(mesh,mesh,q,q,order,order)
                self.assertEqual(budget.total_states,0)

    def test_MC04_internal_deadline(self):
        n=200;mesh=f.Mesh([(0,0,0)]*n,[],[]);q=np.zeros((n,3),dtype=np.int64);order=np.arange(n)
        budget=d.BudgetContext(d.Limits(pair_seconds=.01,total_seconds=5))
        start=time.monotonic()
        with self.assertRaises(d.ComplexityBudgetExceeded),d.bound_budget(budget),budget.pair():
            d._ambiguous_isomorphism(mesh,mesh,q,q,order,order)
        elapsed=time.monotonic()-start
        print('DEADLINE_MEASURED',json.dumps({'n':n,'requested':.01,'elapsed':elapsed,'states':budget.total_states}))
        self.assertLess(elapsed,.15) # empirical QA bound, not an OS guarantee

    def test_deterministic_clock_checkpoint_inside_ranking(self):
        # Advance a synthetic clock only when internal ranking is reached.
        n=100;mesh=f.Mesh([(0,0,0)]*n,[],[]);q=np.zeros((n,3),dtype=np.int64);order=np.arange(n)
        budget=d.BudgetContext();original=budget.checkpoint;seen=[]
        def checkpoint(label='checkpoint'):
            seen.append(label)
            if label=='ranking-vertices':raise d.ComplexityBudgetExceeded('deterministic ranking deadline')
            return original(label)
        budget.checkpoint=checkpoint
        with self.assertRaisesRegex(d.ComplexityBudgetExceeded,'ranking deadline'),d.bound_budget(budget),budget.pair():
            d._ambiguous_isomorphism(mesh,mesh,q,q,order,order)
        self.assertIn('ranking-vertices',seen)

    def test_million_ambiguous_rejected_before_buffers(self):
        class CountOnly:
            def __len__(self):return 1_000_000
            def foreach_get(self,*_):raise AssertionError('must not allocate/read')
        mesh=f.NS(vertices=CountOnly(),edges=[],polygons=[],loops=[])
        q=f.NS(__len__=lambda:1_000_000)
        class Coords:
            def __len__(self):return 1_000_000
        budget=d.BudgetContext()
        with self.assertRaises(d.ComplexityBudgetExceeded),d.bound_budget(budget),budget.pair():
            d._ambiguous_isomorphism(mesh,mesh,Coords(),Coords(),None,None)

    def test_invalid_overlapping_faces(self):
        b,o=f.basic();mesh=o[0].data
        mesh.polygons.rows=[{'loop_start':0,'loop_total':3},{'loop_start':0,'loop_total':3}]
        mesh.loops.rows*=2
        self.assert_zero(b)

    def test_text_resource_budget(self):
        b,o=f.basic();b.texts.append(f.FakeText('huge','x'*1000))
        with self.assertRaises(d.PreflightAborted):d.execute(b,limits=d.Limits(text_bytes=10),emit=lambda *_:None)
        self.assertEqual(b.objects.remove_calls,0)

if __name__=='__main__':unittest.main(verbosity=2)
