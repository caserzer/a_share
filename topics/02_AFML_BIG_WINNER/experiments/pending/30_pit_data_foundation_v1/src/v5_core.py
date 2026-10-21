"""Independent v5 inputs and byte-addressed evidence; frozen v4 stays unchanged."""
import json
import os
import shutil
from functools import lru_cache
from pathlib import Path

from archive import CACHE, EP, archive_bytes, sha, write_json

BASE_ID = "a209472223fad6252a410f6910e132f1baa08242f4bb82d7c8055a51119d01e6"
BASE = CACHE / "pit_v4/releases" / BASE_ID
V5 = Path(os.environ.get("EP30_V5_ROOT", CACHE / "pit_v5"))
PUBLIC = Path(os.environ.get("EP30_V5_PUBLIC", EP / "outputs/pit_v5"))


@lru_cache(maxsize=1)
def catalog():
    local = V5 / "baseline_catalog"
    root = local if local.exists() else BASE
    if root == BASE and os.environ.get("EP30_V5_OFFLINE"):
        raise ValueError("offline replay requires local baseline catalog")
    complete = json.loads((root / "COMPLETE.json").read_text())
    assert sha(root / "FULL_MANIFEST.json") == complete["full_manifest_sha256"]
    return {r["relative_path"]: r["sha256"] for r in json.loads((root / "FULL_MANIFEST.json").read_text())}


def baseline(name):
    target = V5 / "inputs" / name
    expected = catalog()[name]
    source = target if target.exists() else BASE / name
    if not target.exists() and os.environ.get("EP30_V5_OFFLINE"):
        raise ValueError("missing frozen offline input: " + name)
    if sha(source) != expected:
        raise ValueError("baseline hash mismatch: " + name)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return target


def price_input(sid):
    name = f"normalized/prices/{sid}.parquet"
    if name not in catalog():
        name = "inputs/baseline/" + name
    return baseline(name) if name in catalog() else None


def pin_sources():
    V5.mkdir(parents=True, exist_ok=True)
    V5.chmod(0o700)
    sources = {}
    for p in sorted((EP / "src").glob("v5_*.py")):
        sources[p.name] = archive_bytes(p.read_bytes(), root=V5)[1]
    for p in [EP / "src/archive.py", EP / "configs/pit_v5.json"]:
        sources[p.name] = archive_bytes(p.read_bytes(), root=V5)[1]
    return sources
