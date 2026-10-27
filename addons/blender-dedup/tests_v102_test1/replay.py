"""Offline replay. Original ZIPs are read-only; all adaptations use work/replay/."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys, time, zipfile
ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
SOURCE = ROOT/'src_v102_test1/remover_duplicatas_blend_v1_0_2_test1.py'

def prepare():
    dest = ROOT/'work/replay'
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for who in 'AB':
        archives=list((ROOT/'handoff/ORIGINAIS').glob('*AUDITOR_'+who+'*zip'))
        if archives:
            with zipfile.ZipFile(archives[0]) as z:
                assert z.testzip() is None
                for name in z.namelist():
                    if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe archive path')
                z.extractall(dest/who)
        else:
            shutil.copytree(ROOT/'reference_tests'/who,dest/who)
        base = dest/who/('CANDIDATA_EXTRAIDA' if who=='A' else 'input')
        (base/'src').mkdir(exist_ok=True)
        shutil.copyfile(SOURCE, base/'src/remover_duplicatas_blend_v1_0_1.py')
        (base/'evidencias').mkdir(exist_ok=True)
    return dest

def run(name, args, cwd, timeout=180):
    logs=ROOT/'entrega_v102_test1/logs'; logs.mkdir(parents=True,exist_ok=True)
    result_dir=logs/name; result_dir.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', DEDUP_RESULT_DIR=str(result_dir),
               PYTHONPATH=str(ROOT/'tests_v102_test1/offline_guard'))
    start=time.monotonic()
    try:
        p = subprocess.run([PYTHON,*map(str,args)],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        output=p.stdout; rc=p.returncode
    except subprocess.TimeoutExpired as e:
        output=(e.stdout or b'')+b'\nEXTERNAL RUNNER TIMEOUT\n';rc=124
    (logs/(name+'.log')).write_bytes(output)
    if name.endswith('benchmark1M') and (cwd/'evidencias/benchmark_v101.json').exists():
        shutil.copyfile(cwd/'evidencias/benchmark_v101.json',result_dir/'benchmark.json')
    if name.endswith('graph32'):
        for file in (cwd/'evidencias').glob('B_graph32*'):shutil.copyfile(file,result_dir/file.name)
    rec={'name':name,'returncode':rc,'seconds':round(time.monotonic()-start,4),'command':[PYTHON,*map(str,args)],'cwd':str(cwd)}
    print(json.dumps(rec),flush=True)
    return rec

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--original',action='store_true');a=ap.parse_args()
    dest=prepare()
    if a.original:
        for who in 'AB':
            base=dest/who/('CANDIDATA_EXTRAIDA' if who=='A' else 'input')
            shutil.copyfile(ROOT/'handoff/CONGELADOS/remover_duplicatas_blend_v1_0_1.py',base/'src/remover_duplicatas_blend_v1_0_1.py')
    qa=dest/'A/CANDIDATA_EXTRAIDA'
    jobs=[('qa57',['-m','unittest','discover','-s','qa','-p','test_candidate_v101.py','-v'],qa),
        ('oracle266',[ROOT/'tests_v102_test1/oracle266_adapter.py',qa/'qa/oracle_A_adapted_to_candidate.py',qa/'src/remover_duplicatas_blend_v1_0_1.py',ROOT/('entrega_v102_test1/logs/'+('original_' if a.original else '')+'oracle266/results.json')],qa),
        ('geometry2649',['qa/audit_A_geometry_adapted.py','src/remover_duplicatas_blend_v1_0_1.py'],qa),
        ('graph32',['qa/verify_B_graph32_on_candidate.py'],qa),
        ('oracle400',['HARNESSES/independent_geometry_oracle.py'],dest/'A'),
        ('oracle160',['tests/independent_B_geometry_oracle.py'],dest/'B'),
        ('benchmark1M',['qa/benchmark_v101.py'],qa)]
    if a.original:
        if (dest/'A/ORIGINAIS').exists():
            jobs = [('custody_A',['HARNESSES/verify_originals.py'],dest/'A'),
                    ('custody_B',['tests/verify_custody.py'],dest/'B')] + jobs
        jobs += [('historical_A_refs',['HARNESSES/adversarial_references.py'],dest/'A'),
                 ('historical_B_adversarial',['-m','unittest','discover','-s','tests','-p','independent_B_adversarial.py','-v'],dest/'B'),
                 ('historical_B_crosscheck',['-m','unittest','discover','-s','tests','-p','independent_B_crosscheck.py','-v'],dest/'B'),
                 ('historical_deadline',['HARNESSES/adversarial_deadline.py'],dest/'A')]
        jobs += [(f'historical_memory{n}',['HARNESSES/adversarial_memory.py',n],dest/'A') for n in (100,200,240)]
    else:
        jobs += [('B_inversions',[ROOT/'tests_v102_test1/replay_inversions.py'],ROOT),
                 ('cost_probes',[ROOT/'tests_v102_test1/probe_cost.py'],ROOT),
                 ('ledger_examples',[ROOT/'tests_v102_test1/ledger_examples.py'],ROOT),
                 ('safety',['-m','unittest','discover','-s',ROOT/'tests_v102_test1','-p','test_safety.py','-v'],ROOT)]
    result=[]
    for name,args,cwd in jobs:
        rec=run(('original_' if a.original else '')+name,args,cwd,8 if name.startswith('historical_memory') else 180)
        rec['target_sha256']=hashlib.sha256((ROOT/'handoff/CONGELADOS/remover_duplicatas_blend_v1_0_1.py' if a.original else SOURCE).read_bytes()).hexdigest()
        result.append(rec)
    (ROOT/'entrega_v102_test1'/('replay_original.json' if a.original else 'replay_candidate.json')).write_text(json.dumps(result,indent=2)+'\n')
    return int(any(x['returncode'] for x in result))
if __name__=='__main__':raise SystemExit(main())
