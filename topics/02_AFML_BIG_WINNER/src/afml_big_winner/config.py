"""Configuration helpers for experiment scripts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and always return a dictionary."""

    yaml_path = Path(path)
    with yaml_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise TypeError(f"Expected YAML mapping in {yaml_path}")
    return loaded


def stable_json(value: Any) -> str:
    """Serialize a value in a deterministic way for hashes and manifests."""

    return json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)


def stable_hash(value: Any) -> str:
    """Return a stable sha256 hash for a Python value."""

    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def project_root() -> Path:
    """Return the project root when called from an installed src layout."""

    return Path(__file__).resolve().parents[2]
