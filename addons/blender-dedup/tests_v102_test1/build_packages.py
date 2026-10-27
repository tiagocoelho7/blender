"""Build three deterministic delivery archives without changing frozen inputs."""
from pathlib import Path
import difflib, hashlib, json, zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'entrega_v102_test1'
CANDIDATE='src_v102_test1/remover_duplicatas_blend_v1_0_2_test1.py'
FROZEN=ROOT/'handoff/CONGELADOS/remover_duplicatas_blend_v1_0_1.py'

def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(obj):return (json.dumps(obj,indent=2,ensure_ascii=False,sort_keys=True)+'\n').encode()
def files_under(path):
    return sorted(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')

def seal(payload):
    sums=''.join(f'{sha(data)}  {name}\n' for name,data in sorted(payload.items()))
    return {**payload,'SHA256SUMS.txt':sums.encode()}

def archive(path,payload):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(seal(payload).items()):
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            assert not name.lower().endswith('.blend')
            info=zipfile.ZipInfo(name,(2026,10,27,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,data,compresslevel=9)
    with zipfile.ZipFile(path) as z:assert z.testzip() is None
    return {'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}

def reference_tests():
    payload={};provenance=[]
    a_harness={'independent_geometry_oracle.py','adversarial_references.py','adversarial_deadline.py','adversarial_memory.py','run_memory_samples.py'}
    for who in 'AB':
        p=next((ROOT/'handoff/ORIGINAIS').glob('*AUDITOR_'+who+'*zip'))
        zip_sha=sha(p.read_bytes())
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():
                keep=False
                if who=='A':
                    keep=(name.startswith('CANDIDATA_EXTRAIDA/qa/') and name.endswith('.py') or
                          name.startswith('CANDIDATA_EXTRAIDA/originais/master_r2/QA_REFERENCIA/') and name.endswith(('.py','.json')) or
                          name.startswith('HARNESSES/') and Path(name).name in a_harness)
                else:
                    keep=(name.startswith('input/qa/') and name.endswith('.py') or
                          name.startswith('input/originais/master_r2/QA_REFERENCIA/') and name.endswith(('.py','.json')) or
                          name.startswith('tests/independent_B_') and name.endswith('.py'))
                if not keep:continue
                data=z.read(name);target='reference_tests/'+who+'/'+name
                payload[target]=data
                provenance.append({'path':target,'source_archive':p.name,'source_archive_sha256':zip_sha,'member':name,'bytes':len(data),'sha256':sha(data)})
    payload['REFERENCE_PROVENANCE.json']=encoded(provenance)
    return payload

def main():
    OUT.mkdir(exist_ok=True);packages=OUT/'pacotes';packages.mkdir(exist_ok=True)
    source=(ROOT/CANDIDATE).read_bytes()
    diff=''.join(difflib.unified_diff(FROZEN.read_text().splitlines(True),source.decode().splitlines(True),
                fromfile='a/remover_duplicatas_blend_v1_0_1.py',tofile='b/remover_duplicatas_blend_v1_0_2_test1.py'))
    (OUT/'DIFF_V101_V102_TEST1.patch').write_text(diff)
    (OUT/'CANDIDATA_SHA256.txt').write_text(sha(source)+'  '+CANDIDATE+'\n')
    common={CANDIDATE:source,'DIFF_V101_V102_TEST1.patch':diff.encode(),**reference_tests()}
    for p in files_under(ROOT/'tests_v102_test1'):
        if p.name in ('build_packages.py','verify_packages.py'):continue
        common[str(p.relative_to(ROOT))]=p.read_bytes()
    for p in files_under(ROOT/'handoff/CONGELADOS'):
        if p.name in ('remover_duplicatas_blend_v1.py','remover_duplicatas_blend_v1_0_1.py','ESPECIFICACAO_R1_R5.md','ADENDO_MASTER_R2.md'):
            common[str(p.relative_to(ROOT))]=p.read_bytes()
    # Include historical plan and contract definitions, no audit conclusions.
    with zipfile.ZipFile(next((ROOT/'handoff/ORIGINAIS').glob('*AUDITOR_A*zip'))) as z:
        prefix='CANDIDATA_EXTRAIDA/originais/master_r2/CONGELADOS/'
        for name in ('PLANO_R1.md','MATRIZ_G01_G14_R2.md'):
            common['reference_contract/'+name]=z.read(prefix+name)
    common['REPLAY.txt']=('Offline only. CPython 3.12, NumPy 2.4.2, NetworkX 3.6.1 already available.\n'
        'Run: python tests_v102_test1/replay.py\n'
        'Original case logic preserved; oracle266 target identity rebound in memory.\n'
        'B unsafe assertions inverted; four controls unchanged. Source provenance: REFERENCE_PROVENANCE.json.\n'
        'No developer logs/verdicts or peer audit reports are included. Do not access MASTER before sealing your audit.\n').encode()
    package_records=[]
    for who in 'AB':
        focus=('Geometria/topologia exata, bijeção global, multiplicidades, winding/SEM-01, quantização, classes ambíguas, '
               'oráculos independentes, Rook/Shrikhande, memória/deadlines e 1M vértices.' if who=='A' else
               'Incoming diretas/indiretas, Text/IDProps e aliases, owners/lifecycle, instancing/closure, user_map, '
               'KEEP/DROP e modos, TOCTOU/reentrância, falhas de logger/remove e ledger parcial.')
        prompt=f'''# Auditor {who} — reauditoria cega v1.0.2-test1

Audite independentemente esta candidata congelada. Você é auditor, não desenvolvedor nem homologador de produção.
SHA-256 da candidata: {sha(source)}
Baseline v1.0.1: 1d4175b1190732ea6077232b32d4fd632021f99c9ccb80e5ba15dd5e4dcb9956.
Base Git do desenvolvimento: 828aeab4280f650d3d2786d75eee55634b728736.

Leia R1–R5, adendo R2, plano R1, diff e testes. Foque em: {focus}

Reproduza 57/57, 266/266, 2649/2649, 32/32, oráculos 400/400 e 160/160; verifique o adapter do PIN do oráculo e as inversões de asserções B.
Revise MC01–MC07 integralmente e crie contraprovas próprias. Teste incerteza antes da primeira remoção = zero chamadas do executor;
erro depois = parar e conciliar sem rollback. Exercite mutação de geometria/refs em emit e remove, inclusive último remove,
falhas antes/depois do efeito e logger quebrado. Não aceite hash/refinamento como prova positiva geométrica.
Questione o domínio de exclusividade, getters/handlers, normalização user_map e legalidade das fixtures.
O callback final recebe PENDING_FINAL_VALIDATION; REMOVOES_CONFIRMADAS só pode vir no retorno após novo check.

Use somente Python offline com mocks/dados sintéticos. Não execute Blender real, importe bpy real, abra/crie/salve .blend,
use ChatGPT Work, instale a candidata, publique release, faça merge/PR ou altere código/inputs. NÃO leia MASTER,
parecer do outro auditor, resultados do desenvolvedor ou da rodada atual antes de entregar seu selo independente.
Este pacote deliberadamente não contém esses pareceres nem o prompt do outro auditor. Nenhum auditor atual foi acionado pelo executor.

Com dependências previamente disponíveis: python tests_v102_test1/replay.py
Os scripts históricos têm nomes/rótulos v1.0.1; o runner vincula o alvo novo somente nas cópias de work/ e em memória.
Não trate PASS de contraprovas históricas sobre v1.0.1 como correção. Não confunda mocks com API Blender 5.0.

Entregue ZIP autônomo com seu parecer, achados por severidade e IDs, matriz MC01–MC07 e G01–G14,
logs/comandos, testes próprios, hashes e declaração de independência. Informe precisamente testes não reproduzidos.
Veredito apenas sobre código offline: GO/HOLD/INCONCLUSIVO; nenhum GO de Blender real ou produção.
'''
        payload={**common,f'PROMPT_AUDITOR_{who}.md':prompt.encode(),
            'PACKAGE_META.json':encoded({'audience':'Auditor '+who,'candidate_sha256':sha(source),'status':'independent audit input only','peer_reports_included':False,'developer_results_included':False})}
        package_records.append(archive(packages/f'BLENDER_DEDUP_V102_TEST1_AUDITOR_{who}_2026-10-27.zip',payload))
    (OUT/'AUDITOR_PACKAGES_SHA256.json').write_bytes(encoded(package_records))
    # New manifest excludes packages, self and the external complete package index.
    manifest=[]
    for folder in ('src_v102_test1','tests_v102_test1','entrega_v102_test1'):
        for p in files_under(ROOT/folder):
            rel=p.relative_to(ROOT)
            if 'pacotes' in rel.parts or p.name in ('SHA256SUMS_NOVA_ENTREGA.txt','PACOTES_SHA256.json','PACOTES_SHA256.txt'):continue
            manifest.append((str(rel),sha(p.read_bytes())))
    (OUT/'SHA256SUMS_NOVA_ENTREGA.txt').write_text(''.join(f'{h}  {n}\n' for n,h in sorted(manifest)))
    master={}
    for p in sorted(ROOT.iterdir()):
        if p.is_file() and p.name not in ('.DS_Store',):master[p.name]=p.read_bytes()
    for folder in ('handoff','src_v102_test1','tests_v102_test1','entrega_v102_test1'):
        for p in files_under(ROOT/folder):
            rel=p.relative_to(ROOT)
            if p.name in ('PACOTES_SHA256.json','PACOTES_SHA256.txt') or p.name.startswith('BLENDER_DEDUP_V102_TEST1_MASTER_'):continue
            master[str(rel)]=p.read_bytes()
    master['PACKAGE_META.json']=encoded({'audience':'MASTER','base_commit':'828aeab4280f650d3d2786d75eee55634b728736',
        'candidate_sha256':sha(source),'status':'candidate for independent audit; production HOLD','original_kit_preserved':True})
    package_records.append(archive(packages/'BLENDER_DEDUP_V102_TEST1_MASTER_2026-10-27.zip',master))
    (OUT/'PACOTES_SHA256.json').write_bytes(encoded(package_records))
    (OUT/'PACOTES_SHA256.txt').write_text(''.join(f"{r['sha256']}  {r['path']}  ({r['bytes']} bytes)\n" for r in package_records))
    print(json.dumps({'candidate_sha256':sha(source),'packages':package_records},indent=2))
if __name__=='__main__':main()
