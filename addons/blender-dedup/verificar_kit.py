#!/usr/bin/env python3
"""Offline only: validates files belonging to this Codex Cloud input kit."""
from pathlib import Path
import hashlib
root = Path(__file__).resolve().parent
checks = root / "MANIFESTO_CODEX_SHA256.txt"
count = 0
for line in checks.read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    sha, relative = line.split("  ", 1)
    actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    if actual != sha:
        raise SystemExit(f"HASH MISMATCH: {relative}")
    count += 1
print(f"OK: {count}/{count} arquivos do kit verificados")
