#!/usr/bin/env python3
"""Standalone offline replay. Writes only to the explicit evidence output directory."""
import argparse,ast,dataclasses,hashlib,io,json,math,os,platform,sys,time,tracemalloc,unittest
from pathlib import Path
from fractions import Fraction

ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]

def jsonable(value):
    if isinstance(value,Fraction): return str(value)
    if dataclasses.is_dataclass(value):return jsonable(dataclasses.asdict(value))
    if isinstance(value,dict):return {str(k):jsonable(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [jsonable(x) for x in value]
    return value

class Results(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.cases=[];self.subcases=[]
    def addSuccess(self,t):super().addSuccess(t);self.cases.append({'id':t.id(),'status':'PASS'})
    def addFailure(self,t,e):super().addFailure(t,e);self.cases.append({'id':t.id(),'status':'FAIL','error':self._exc_info_to_string(e,t)})
    def addError(self,t,e):super().addError(t,e);self.cases.append({'id':t.id(),'status':'ERROR','error':self._exc_info_to_string(e,t)})
    def addSubTest(self,t,sub,e):
        super().addSubTest(t,sub,e)
        self.subcases.append({'id':sub.id(),'status':'PASS' if e is None else 'FAIL'})

def integrity():
    manifest=ROOT/'SHA256_MANIFEST.txt'
    if not manifest.exists():return {'status':'NOT_YET_PACKAGED'}
    rows=[]
    for line in manifest.read_text().splitlines():
        if not line or line.startswith('#'):continue
        expected,name=line.split('  ',1)
        p=ROOT/name
        actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        rows.append({'path':name,'pass':actual==expected})
    return {'status':'PASS' if all(r['pass'] for r in rows) else 'FAIL','members':rows}

def static_inspection():
    forbidden={'bpy','bmesh','socket','subprocess','requests','urllib','http','ctypes'}
    calls={'open','exec','eval','compile','__import__'}
    rows=[]
    for p in sorted((ROOT/'src').rglob('*.py')):
        tree=ast.parse(p.read_text())
        imports=[];bad=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):imports.extend(x.name for x in n.names)
            if isinstance(n,ast.ImportFrom):imports.append(n.module or '')
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in calls:bad.append(n.func.id)
        bad += [i for i in imports if i.split('.')[0] in forbidden]
        rows.append({'file':str(p.relative_to(ROOT)),'imports':sorted(set(imports)),'forbidden':bad})
    return {'status':'PASS' if not any(r['forbidden'] for r in rows) else 'FAIL',
            'scope':'AST import/call scan only; not runtime no-write proof','files':rows}

def samples():
    from t7m import Entity as E,Query as Q,measure
    from test_kernel import face
    v=E('V',((0,0,5),));e=E('E',((0,0,5),(1,0,5)));f=face()
    fixtures={
      'V-V':Q(E('V',((0,0,0),)),E('V',((3,4,0),))),
      'V-E':Q(E('V',((1,1,0),)),E('E',((0,0,0),(10,0,0)))),
      'V-F':Q(v,f),'E-E':Q(e,E('E',((0,1,0),(1,1,0)))),
      'E-F':Q(e,f),'F-F':Q(f,face(5)),
      'E-length':Q(E('E',((0,0,0),(3,4,0)))), 'F-area':Q(f),
      'P-F-F-positive':Q(face(twist=.0002,size=10),face(5,twist=.0002,size=10)),
      'P-V-F-unknown-contact':Q(E('V',((0,0,0),)),face(twist=.0002,size=10)),
      'P-resolution-refusal':Q(E('F',((10000,0,0),(10010,0,0),(10010,10,0.00020000000949949026),(10000,10,0))))
    }
    return {name:{'input':jsonable(q),'result':jsonable(measure(q))} for name,q in fixtures.items()}

def allocation_samples():
    from t7m import Entity as E,Query as Q,measure
    out=[]
    for n in (8,16,24,30,32):
        poly=tuple((math.cos(2*math.pi*i/n),math.sin(2*math.pi*i/n),0.0) for i in range(n))
        tracemalloc.start()
        started=time.perf_counter()
        result=measure(Q(E('F',poly)))
        seconds=time.perf_counter()-started
        current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        out.append({'n':n,'status':result['status'],'reason':result.get('reason'),
                    'python_traced_peak_bytes':peak,'seconds':seconds,
                    'exact_steps':result.get('exact_steps'),'preflight':result.get('plan')})
    return {'scope':'Python tracemalloc only, fixtures prepared before tracing; NOT RSS, NOT Blender, NOT admission proof',
            'samples':out}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='replay_results');args=ap.parse_args()
    dest=Path(args.output).resolve()
    if dest==ROOT or ROOT/'src' in dest.parents or ROOT/'tests' in dest.parents:
        ap.error('output must not overwrite sources or tests')
    dest.mkdir(parents=True,exist_ok=True)
    def save(name,obj):(dest/name).write_text(json.dumps(jsonable(obj),ensure_ascii=False,indent=2)+'\n')
    checked=integrity();save('integrity.json',checked)
    if checked['status']=='FAIL':print('Manifest mismatch; refusing replay.');return 2
    scan=static_inspection();save('static_inspection.json',scan)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    stream=io.StringIO();start=time.perf_counter()
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Results).run(suite)
    (dest/'unittest.log').write_text(stream.getvalue())
    save('tests.json',{'methods_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                      'skipped':len(result.skipped),'elapsed_seconds':time.perf_counter()-start,
                      'methods':result.cases,'subcases':result.subcases,
                      'note':'Subcases are not additional test methods; no Blender tests.'})
    save('environment.json',{'python':sys.version,'implementation':platform.python_implementation(),
                             'platform':platform.platform(),'machine':platform.machine(),
                             'byteorder':sys.byteorder,'int_info':str(sys.int_info),'offline':True,
                             'no_Blender_run':True,'no_user_blend_access':True})
    save('samples.json',samples());save('allocation_samples.json',allocation_samples())
    print(f'{result.testsRun} test methods; failures={len(result.failures)} errors={len(result.errors)}; output={dest}')
    return 0 if result.wasSuccessful() and scan['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
