"""Run manifest utilities used by experiment templates."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from afml_big_winner.config import stable_hash


def file_sha256(path: str | Path) -> str:
    """Compute sha256 for one file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision(cwd: str | Path) -> str | None:
    """Return the current git revision when available."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(cwd),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def write_run_manifest(
    *,
    manifest_path: str | Path,
    config_path: str | Path,
    config: dict[str, Any],
    command: list[str] | None = None,
    decision: str = "template_only",
    outputs: dict[str, str] | None = None,
    data_cutoff: str | None = None,
) -> Path:
    """Write a small JSON manifest for a completed or template run."""

    manifest_file = Path(manifest_path)
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    config_file = Path(config_path)
    output_hashes = {
        name: file_sha256(path)
        for name, path in sorted((outputs or {}).items())
        if Path(path).is_file()
    }
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": command or sys.argv,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": git_revision(Path.cwd()),
        "config_path": str(config_file),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_file) if config_file.is_file() else None,
        "data_cutoff": data_cutoff,
        "decision": decision,
        "outputs": outputs or {},
        "output_hashes": output_hashes,
    }
    manifest_file.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_file
