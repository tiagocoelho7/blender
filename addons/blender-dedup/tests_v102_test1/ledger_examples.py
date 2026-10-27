"""Produce reproducible-schema ledgers exclusively from synthetic fixture data."""
from fixtures import f,d
from pathlib import Path
import json,os
examples={}
b,o=f.basic();examples['safe']=d.execute(b,emit=lambda *_:None)
b,o=f.basic();child=f.Obj('survivor',None,parent=o[0],kind='EMPTY');b.objects.append(child)
m=f.Material('dependency');m.idprops={'nested':{'target':o[2]}};b.materials.append(m)
try:d.execute(b,emit=lambda *_:None)
except d.PreflightAborted as ex:examples['blocked_zero_calls']=ex.ledger
assert b.objects.remove_calls==0
b,o=f.basic();b.objects.fail_at=1;b.objects.after_effect=True
try:d.execute(b,emit=lambda *_:None)
except d.ExecutionFailure as ex:examples['partial_after_effect']=ex.ledger
assert b.objects.remove_calls==1
p=Path(os.environ['DEDUP_RESULT_DIR'])/'LEDGER_EXEMPLOS.json'
p.write_text(json.dumps({'scope':'SYNTHETIC ONLY, no Blender/bpy/.blend','examples':examples},indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'safe':examples['safe']['status'],'blocked':examples['blocked_zero_calls']['status'],
    'partial':examples['partial_after_effect']['status'],'partial_calls':examples['partial_after_effect']['calls_attempted']},ensure_ascii=False))
