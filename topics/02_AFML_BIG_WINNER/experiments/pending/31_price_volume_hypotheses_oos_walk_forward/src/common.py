"""EP31 paths, deterministic serialization and immutable manifests."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

EP = Path(__file__).resolve().parents[1]
PREDECESSOR = EP.parent / "30_pit_data_foundation_v1"
REPO = EP.parents[4]
OUT = EP / "outputs"
EXPECTED_RELEASE = "9ba9324e4ff8f3a5db14c03893d76c77097855d3f83e9dde2b476f2760aec72e"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def json_default(value):
    if isinstance(value, (pd.Timestamp, datetime, Path)):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(value, ensure_ascii=False, indent=2, default=json_default, allow_nan=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(body)
    tmp.replace(path)


def config(name="preregistration"):
    return yaml.safe_load((EP / "configs" / (name + ".yaml")).read_text())


def frozen():
    f = json.loads((OUT / "manifests/preregistration.json").read_text())
    for relative, digest in f["files"].items():
        if sha(EP / relative) != digest:
            raise ValueError("preregistration changed: " + relative)
    return f


def cache():
    p = Path(frozen()["private_cache"])
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    return p


def source_manifest():
    return {str(p.relative_to(EP)): sha(p) for directory in ["src", "tests", "configs"]
            for p in sorted((EP / directory).glob("*")) if p.is_file() and p.suffix in {".py", ".yaml", ".json"}}


def freeze_preregistration():
    target = OUT / "manifests/preregistration.json"
    if target.exists():
        return frozen()
    files = {str(p.relative_to(EP)): sha(p) for p in [EP / "GOAL.md", EP / "research_plan.md", *sorted((EP / "configs").glob("*.yaml"))]}
    key = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    root = Path(os.environ.get("EP31_CACHE", str(Path.home() / ".cache/a_share/ep31"))) / key
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    value = dict(frozen_at=utc_now(), preregistration_id=key, files=files,
                 private_cache=str(root), before_first_EP31_outcome_score=True,
                 historical_data_previously_seen=True, no_independent_historical_holdout=True)
    write_json(target, value)
    return value
