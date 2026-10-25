#!/usr/bin/env python3
"""Verifica o SHA256 de todos os membros extraídos, somente leitura. Uso: python 11_VERIFICAR_BUNDLE.py"""
from pathlib import Path
from hashlib import sha256
root=Path(__file__).resolve().parent
records=[]
for line in (root/'MANIFESTO_SHA256.txt').read_text('utf-8').splitlines():
    if not line or line.startswith('#'):continue
    digest,relative=line.split('  ',1)
    path=Path(relative)
    assert not path.is_absolute() and '..' not in path.parts,relative
    source=(root/path).resolve()
    assert source.is_relative_to(root),relative
    assert source.is_file(),relative
    actual=sha256(source.read_bytes()).hexdigest()
    assert digest==actual,f'{relative} expected={digest} actual={actual}'
    records.append(relative)
missing={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}-set(records)-{'MANIFESTO_SHA256.txt'}
assert not missing,missing
print(f'PASS {len(records)}/{len(records)} hashes SHA256, sem itens não listados')
