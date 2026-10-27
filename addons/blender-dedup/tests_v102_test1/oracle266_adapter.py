"""Bind the immutable original oracle to a new target identity, in memory only.
The 266 cases, witnesses, seed and assertions are unchanged. Original PIN checked.
"""
from pathlib import Path
import hashlib, runpy, sys
script, source, output = map(Path,sys.argv[1:])
ns=runpy.run_path(str(script),run_name='oracle266_reference')
assert ns['PIN']=='1d4175b1190732ea6077232b32d4fd632021f99c9ccb80e5ba15dd5e4dcb9956'
new_pin=hashlib.sha256(source.read_bytes()).hexdigest()
print('TARGET_BINDING_ONLY',new_pin,flush=True)
ns['main'].__globals__['PIN']=new_pin
output.parent.mkdir(parents=True,exist_ok=True)
sys.argv=[str(script),str(source),str(output)]
ns['main']()
