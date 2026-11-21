"""Compare the uploaded archive with cabal_main's Data tree, read-only."""
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

EXPECTED = "bbb59d24c23213c190a872c0a01d07ef5db100d7e80f0b1ea2d9293b8dbd3c36"
archive = Path("/tmp/Mandarat-Lv1-4379.zip").read_bytes()
if hashlib.sha256(archive).hexdigest() != EXPECTED:
    sys.exit("ZIP_HASH_DIFFERS")
with zipfile.ZipFile(io.BytesIO(archive)) as package:
    entries = json.loads(package.read("hashes.json"))
    name = "Data_World/world166-tmap.bin"
    entries[name] = {"before": None, "after": hashlib.sha256(package.read("Data/" + name)).hexdigest()}

reader = """
import hashlib, pathlib, sys
root = pathlib.Path('/etc/cabal/Data')
if not root.is_dir():
    sys.exit('DATA_DIRECTORY_MISSING')
for name in sys.argv[1:]:
    path = root / name
    try:
        print(hashlib.sha256(path.read_bytes()).hexdigest())
    except FileNotFoundError:
        print('MISSING')
"""
hashes = subprocess.check_output(["docker", "exec", "cabal_main", "python3", "-c", reader, *entries]).decode().splitlines()
if len(hashes) != len(entries):
    sys.exit("INCOMPLETE_RESULT")
conflicts = []
for (name, expected), current in zip(entries.items(), hashes):
    if current == expected["after"]:
        state = "ALREADY_MATCHES"
    elif current == (expected["before"] or "MISSING"):
        state = "BASELINE_OK"
    else:
        state = "DIFFERS"
        conflicts.append(name)
    print(state, name)
print("BASELINE_DIFFERS" if conflicts else "BASELINE_COMPATIBLE")
sys.exit(1 if conflicts else 0)
