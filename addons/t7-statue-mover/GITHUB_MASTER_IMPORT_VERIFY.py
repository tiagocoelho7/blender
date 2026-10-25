#!/usr/bin/env python3
"""Verify an exact imported plugin snapshot without executing untrusted addon code."""
import hashlib
import json
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
name="GITHUB_MASTER_IMPORT_MANIFEST.json"
manifest=json.loads((root/name).read_text(encoding="utf-8"))
expected=manifest["files"]
actual={str(p.relative_to(root)).replace("\\","/") for p in root.rglob("*") if p.is_file() and p.name!=name}
if set(expected)!=actual:
 print("MISSING:",sorted(set(expected)-actual),"UNEXPECTED:",sorted(actual-set(expected)))
 sys.exit(1)
for path,props in sorted(expected.items()):
 data=(root/path).read_bytes()
 if len(data)!=props["size"] or hashlib.sha256(data).hexdigest()!=props["sha256"]:
  print("HASH FAILURE:",path)
  sys.exit(1)
print("PASS",manifest["project"],f"{len(expected)}+manifest files verified")
