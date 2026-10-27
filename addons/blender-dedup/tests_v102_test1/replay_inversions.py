"""Reexecute all 11+2 original B methods with explicit safety-only inversions.
No original file is written. Method fixtures and names are preserved in memory.
"""
from pathlib import Path
import json, re, sys, types, unittest, zipfile
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'work/replay/B'
sys.path.insert(0,str(BASE/'input/qa'))

def load(name, source):
    module=types.ModuleType(name);module.__file__=str(BASE/'tests'/(name+'.py'));sys.modules[name]=module
    exec(compile(source,str(module.__file__)+' [safety inversions in memory]','exec'),module.__dict__)
    return module

raw=(BASE/'tests/independent_B_adversarial.py').read_text()
parts=re.split(r'(?=  def test_)',raw)
changed=[]
for i,part in enumerate(parts):
    if not part.startswith('  def test_unsafe_'):continue
    method=part.split('(')[0].strip()[4:]
    part=part.replace("self.assertEqual(r['ret'],'REMOVOES_CONFIRMADAS',r)","self.assertIsNone(r['ret'],r)\n    self.assertIsNotNone(r['error'],r)")
    part=part.replace("self.assertEqual(r['calls'],2,r)","self.assertEqual(r['calls'],0,r)")
    part=part.replace('self.assertFalse(D._text_lookup_risk','self.assertTrue(D._text_lookup_risk')
    part=part.replace('self.assertNotIn(objs[0], b.objects)','self.assertIn(objs[0], b.objects)')
    parts[i]=part;changed.append(method)
assert len(changed)==7
b=load('B_original_11_safety_inverted',''.join(parts))
raw=(BASE/'tests/independent_B_crosscheck.py').read_text()
raw=raw.replace('actual=quick_execute(b)',"\n  with self.assertRaises(d.PreflightAborted):quick_execute(b)\n  actual={'status':'INCONCLUSIVO_ZERO_REMOVOES'}")
raw=raw.replace("assert actual['status']=='REMOVOES_CONFIRMADAS'", "assert actual['status']=='INCONCLUSIVO_ZERO_REMOVOES'")
raw=raw.replace('assert b.objects.remove_calls==2','assert b.objects.remove_calls==0')
c=load('B_original_2_crosscheck_safety_inverted',raw)
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(b),unittest.defaultTestLoader.loadTestsFromModule(c)])
print(json.dumps({'changed_unsafe_methods':changed,'controls_unchanged':4,'crosschecks_inverted':2}),flush=True)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
