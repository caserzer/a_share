"""Private content-addressed source archive and immutable public receipts."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
TOPIC = EP.parents[2]
CACHE = Path(os.environ.get("EP30_CACHE", Path.home() / ".cache/a_share/ep30_d2"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str, allow_nan=False)
        + "\n"
    )


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def archive_bytes(body, root=None):
    root = Path(root or CACHE) / "raw/sha256"
    digest = hashlib.sha256(body).hexdigest()
    path = root / digest[:2] / digest
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as f:
            f.write(body)
        path.chmod(0o600)
    except FileExistsError:
        if sha(path) != digest:
            raise ValueError("content-addressed archive was modified")
    return path, digest


def verify_receipt(receipt):
    path = Path(receipt["archive_path"])
    return path.is_file() and sha(path) == receipt["sha256"]


def append_receipt(path, receipt):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a") as f:
        f.write(
            json.dumps(receipt, ensure_ascii=False, default=str, allow_nan=False) + "\n"
        )
