#!/usr/bin/env python3
"""Valida hashes e espelhos da importacao Tiago Tools sem bpy/Blender ou rede."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

def check(cond: bool, message: str) -> None:
    if not cond:
        raise SystemExit('HOLD: ' + message)

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

root = Path(__file__).resolve().parent
manifest = json.loads((root/'GITHUB_MASTER_IMPORT_MANIFEST.json').read_text('utf8'))
expected = {entry['path']: entry for entry in manifest['files']}
check(len(expected)==len(manifest['files']), 'caminho duplicado no manifesto')
observed = {f.relative_to(root).as_posix() for f in root.rglob('*') if f.is_file()}
check(observed == set(expected) | {'GITHUB_MASTER_IMPORT_MANIFEST.json'},
      'inventario de arquivos divergente: ' + repr(sorted(observed ^ (set(expected)|{'GITHUB_MASTER_IMPORT_MANIFEST.json'}))))
for rel,item in expected.items():
    check(not rel.startswith('/') and '..' not in Path(rel).parts and not (root/rel).is_symlink(),
          'caminho inseguro: '+rel)
    actual = (root / rel).read_bytes()
    check(len(actual)==item['bytes'], 'tamanho inesperado: '+rel)
    check(digest(actual)==item['sha256'], 'SHA-256 divergente: '+rel)
print('PASS: '+str(len(expected))+'/'+str(len(expected))+' hashes de membros nao-manifesto')

prefix = 'handoff/E3/'
archive_bytes = (root/'handoff/ORIGINAL_MASTER_E3_CONSOLIDADO_2026-10-20.zip').read_bytes()
with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
    check(z.testzip() is None, 'CRC do ZIP E3 original')
    names = z.namelist()
    originals = {n[len(prefix):]: entry for n,entry in expected.items() if n.startswith(prefix)}
    check(set(names)==set(originals) and len(names)==23, 'membros do ZIP E3 inesperados')
    for n in names:
        check(z.read(n)==(root/prefix/n).read_bytes(), 'E3 extraido difere do ZIP original: '+n)
    records={}
    for l in z.read('MANIFESTO_SHA256.txt').decode('utf8').splitlines():
        if l and not l.startswith('#'):
            h,n=l.split('  ',1);check(n not in records, 'entrada E3 duplicada');records[n]=h
    check(len(records)==22 and set(records)==set(names)-{'MANIFESTO_SHA256.txt'},
          'manifesto E3 nao representa os 22 arquivos')
    for n,h in records.items():
        check(digest(z.read(n))==h,'hash do manifesto E3: '+n)
    candidate=z.read('06_CANDIDATA_E_BASELINES/tiago-tools-1.0.2.zip')
    check(digest(candidate)==manifest['candidate_zip_sha256'],'hash da candidata congelada')
print('PASS: ZIP E3 original e 23/23 copias extraidas; 22/22 manifestados')
with zipfile.ZipFile(io.BytesIO(candidate)) as z:
    check(z.testzip() is None, 'CRC candidata')
    check(len(z.namelist())==5 and set(z.namelist())==set(manifest['candidate_source_files']),
          'inventario candidata')
    for n in z.namelist():
        check(z.read(n)==(root/'snapshots/v1.0.2'/n).read_bytes(),
              'snapshot nao corresponde a candidata: '+n)
    records={}
    for l in z.read('SHA256SUMS.txt').decode('utf8').splitlines():
        if l:
            h,n=l.split('  ',1);records[n]=h
    check(len(records)==4 and set(records)==set(z.namelist())-{'SHA256SUMS.txt'},'manifesto interno')
    for n,h in records.items():
        check(digest(z.read(n))==h,'checksum interno: '+n)
print('PASS: ZIP candidata 1.0.2 e snapshot 5/5; checksums 4/4')
for n in ['05_ORIGINAIS_E3/BLENDER_5022_AUDITOR_A_E3_2026-10-20.zip',
          '05_ORIGINAIS_E3/TIAGO_TOOLS_V1_0_2_AUDITOR_B_E3_RESULTADO_2026-10-20.zip']:
    with zipfile.ZipFile(root/prefix/n) as z:
        check(z.testzip() is None, 'CRC do auditor: '+n)
print('PASS: ambos ZIPs dos auditores A e B validos')
print('PASS DOCUMENTAL: nenhum Blender, bpy, rede, instalacao ou teste funcional executado')
