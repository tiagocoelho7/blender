"""Unmodified original mock classes loaded from verified A archive, candidate path adapted."""
from pathlib import Path
import importlib.util, sys, types, zipfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'src_v102_test1/remover_duplicatas_blend_v1_0_2_test1.py'
archives=list((ROOT/'handoff/ORIGINAIS').glob('*AUDITOR_A*zip'))
if archives:
    with zipfile.ZipFile(archives[0]) as z:
        data=z.read('CANDIDATA_EXTRAIDA/qa/test_candidate_v101.py').decode()
else:
    data=(ROOT/'reference_tests/A/CANDIDATA_EXTRAIDA/qa/test_candidate_v101.py').read_text()
old="SRC=Path(__file__).resolve().parents[1]/'src'/'remover_duplicatas_blend_v1_0_1.py'"
assert old in data
f=types.ModuleType('fixtures_v101_for_v102');sys.modules[f.__name__]=f
f.__file__=str(Path(__file__))
exec(compile(data.replace(old,'SRC=Path('+repr(str(SOURCE))+')'), '<original_mock_fixture_path_adapted>', 'exec'), f.__dict__)
d=f.d
