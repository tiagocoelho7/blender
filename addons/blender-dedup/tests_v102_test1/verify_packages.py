"""Verify CRCs, internal manifests, blind separation and exact diff replay."""
from pathlib import Path
import hashlib,json,re,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'entrega_v102_test1'
def sha(data):return hashlib.sha256(data).hexdigest()

def replay_diff(old,patch):
    before=old.decode().splitlines(True);lines=patch.decode().splitlines(True)
    output=[];cursor=0;index=2
    while index<len(lines):
        m=re.match(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@',lines[index]);assert m,lines[index]
        start=int(m[1])-1;assert start>=cursor
        output.extend(before[cursor:start]);cursor=start;index+=1
        while index<len(lines) and not lines[index].startswith('@@ '):
            tag,line=lines[index][0],lines[index][1:]
            if tag in ' -':assert before[cursor]==line;cursor+=1
            if tag in ' +':output.append(line)
            assert tag in ' -+'
            index+=1
    output.extend(before[cursor:]);return ''.join(output).encode()

def main():
    index=OUT/'PACOTES_SHA256.json'
    records=json.loads((index if index.exists() else OUT/'AUDITOR_PACKAGES_SHA256.json').read_text());candidate=(ROOT/'src_v102_test1/remover_duplicatas_blend_v1_0_2_test1.py').read_bytes()
    public=[];blind_payloads=[]
    for record in records:
        p=ROOT/record['path'];assert p.stat().st_size==record['bytes'] and sha(p.read_bytes())==record['sha256']
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None
            payload={n:z.read(n) for n in z.namelist()};assert len(payload)==len(z.namelist())
            assert payload['src_v102_test1/remover_duplicatas_blend_v1_0_2_test1.py']==candidate
            checks=payload['SHA256SUMS.txt'].decode().splitlines()
            assert len(checks)==len(payload)-1
            for row in checks:
                expected,name=row.split('  ',1);assert sha(payload[name])==expected,name
            if 'AUDITOR_' in p.name:
                role='A' if 'AUDITOR_A_' in p.name else 'B'
                assert f'PROMPT_AUDITOR_{role}.md' in payload
                assert f'PROMPT_AUDITOR_{"B" if role=="A" else "A"}.md' not in payload
                assert not any('PARECER' in n or '/logs/' in n or 'MATRIZ_MC01_MC07' in n or '/ORIGINAIS/' in n for n in payload)
                provenance=json.loads(payload['REFERENCE_PROVENANCE.json'])
                for item in provenance:assert sha(payload[item['path']])==item['sha256']
                blind_payloads.append({n:data for n,data in payload.items() if not n.startswith('PROMPT_AUDITOR_') and n not in ('PACKAGE_META.json','SHA256SUMS.txt')})
            else:
                assert payload['handoff/CONGELADOS/remover_duplicatas_blend_v1_0_1.py']==(ROOT/'handoff/CONGELADOS/remover_duplicatas_blend_v1_0_1.py').read_bytes()
                for original in (ROOT/'handoff/ORIGINAIS').glob('*.zip'):assert payload[str(original.relative_to(ROOT))]==original.read_bytes()
            public.append({'path':record['path'],'members':len(payload),'manifest_verified':len(checks),'sha256':record['sha256']})
    if (ROOT/'SHA256SUMS.txt').exists():
        for row in (ROOT/'SHA256SUMS.txt').read_text().splitlines():
            expected,name=row.split('  ',1);assert sha((ROOT/name).read_bytes())==expected,name
    assert blind_payloads[0]==blind_payloads[1]
    assert replay_diff((ROOT/'handoff/CONGELADOS/remover_duplicatas_blend_v1_0_1.py').read_bytes(),(OUT/'DIFF_V101_V102_TEST1.patch').read_bytes())==candidate
    for row in (OUT/'SHA256SUMS_NOVA_ENTREGA.txt').read_text().splitlines():
        expected,name=row.split('  ',1);assert sha((ROOT/name).read_bytes())==expected,name
    print(json.dumps({'verified':public,'identical_blind_payload_except_role':True,'diff_reconstructed_byte_identical':True,'candidate_sha256':sha(candidate)},indent=2))
if __name__=='__main__':main()
