#!/usr/bin/env python3
"""Prepare and audit the two EP23 Phase-2 RD-Factor branches.

This controller deliberately does not call OpenRouter itself.  The formal
RD-Agent command is launched separately so the exact wall-clock process remains
visible and resumable.  No credential values are copied into EP23 artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ep23_phase2_common import canonical_json_sha256, load_configs, sha256_file


BRANCHES = {
    "a20": {
        "library_id": "A20_RDAGENT_PINNED",
        "feature_count": 20,
        "base_dir": "rdagent_base_features_phase2/alpha20",
        "output_key": "factor_a20",
    },
    "a157": {
        "library_id": "A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION",
        "feature_count": 157,
        "base_dir": "rdagent_base_features_phase2/alpha158",
        "output_key": "factor_a158",
    },
}

SECRET_MARKERS = (b"sk-or-v1-", b"OPENAI_API_KEY=", b"OPENROUTER_API_KEY=")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_yaml(path: Path, value: Any) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def git_text(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def git_diff_sha256(repo: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "--binary"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def write_adapter_patch(repo: Path, destination: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "--binary"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    destination.write_bytes(result.stdout)
    return hashlib.sha256(result.stdout).hexdigest()


def configured_env_names(dotenv_path: Path, names: tuple[str, ...]) -> dict[str, bool]:
    result = {name: bool(os.environ.get(name, "").strip()) for name in names}
    if not dotenv_path.exists():
        return result
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in result and value.strip().strip("'\""):
            result[key] = True
    return result


def secret_scan(root: Path) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    if root.exists():
        for path in sorted(
            p
            for p in root.rglob("*")
            if p.is_file() and p.name != "secret_scan.json"
        ):
            try:
                content = path.read_bytes()
            except OSError:
                continue
            matched = [
                marker.decode("ascii", errors="replace")
                for marker in SECRET_MARKERS
                if marker in content
            ]
            if matched:
                hits.append(
                    {
                        "path": str(path.relative_to(root)),
                        "markers": matched,
                    }
                )
    return {
        "scanned_at_utc": utc_now(),
        "root": str(root),
        "marker_policy": [
            "openrouter_key_prefix",
            "openai_dotenv_assignment",
            "openrouter_dotenv_assignment",
        ],
        "hit_count": len(hits),
        "hits": hits,
        "passed": not hits,
    }


def count_trace(trace_path: Path) -> dict[str, Any]:
    session_path = trace_path / "__session__"
    loops: list[dict[str, Any]] = []
    if session_path.is_dir():
        for loop_dir in sorted(
            (path for path in session_path.iterdir() if path.is_dir()),
            key=lambda path: int(path.name),
        ):
            checkpoints = sorted(path.name for path in loop_dir.iterdir() if path.is_file())
            loops.append(
                {
                    "loop_index": int(loop_dir.name),
                    "checkpoint_count": len(checkpoints),
                    "checkpoints": checkpoints,
                    "complete_five_step_loop": len(checkpoints) >= 5
                    and any(name.endswith("_record") for name in checkpoints),
                }
            )
    return {
        "trace_exists": trace_path.is_dir(),
        "loop_count": len(loops),
        "complete_loop_count": sum(row["complete_five_step_loop"] for row in loops),
        "loops": loops,
    }


def resolved_paths(
    config_path: Path, phase2: dict[str, Any], branch: str
) -> dict[str, Path]:
    episode_root = config_path.parent
    branch_spec = BRANCHES[branch]
    output_dir = episode_root / phase2["outputs"][branch_spec["output_key"]]
    return {
        "episode_root": episode_root,
        "output_dir": output_dir,
        "trace_path": output_dir / "raw_rdagent_trace",
        "workspace_path": output_dir / "workspaces",
        "cache_path": output_dir / "pickle_cache",
        "base_features_path": episode_root / branch_spec["base_dir"],
    }


def prepare(config_path: Path, branch: str, usage_start_usd: float | None) -> None:
    phase2, base = load_configs(config_path)
    branch_spec = BRANCHES[branch]
    paths = resolved_paths(config_path, phase2, branch)
    output_dir = paths["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    rdagent = Path(phase2["runtime"]["rdagent_checkout"]).resolve()
    base_factors = paths["base_features_path"] / "base_factors.json"
    features = json.loads(base_factors.read_text(encoding="utf-8"))
    if len(features) != branch_spec["feature_count"]:
        raise ValueError(
            f"{branch} feature count drift: {len(features)} != "
            f"{branch_spec['feature_count']}"
        )

    nested = phase2["evolution"]["nested_segments"]
    resolved = {
        "episode_id": phase2["episode_id"],
        "experiment_id": (
            "23I1_RDFactor_A20_solpro_6h"
            if branch == "a20"
            else "23I2_RDFactor_A157_solpro_6h"
        ),
        "branch": branch,
        "library_id": branch_spec["library_id"],
        "feature_count": branch_spec["feature_count"],
        "wall_clock_budget": phase2["evolution"]["factor_budget"],
        "segments": nested,
        "runtime": {
            "environment_manager": "uv",
            "chat_model": phase2["runtime"]["litellm_chat_model"],
            "embedding_model": phase2["runtime"]["litellm_embedding_model"],
            "provider": "openrouter",
            "proxy_required": True,
            "temperature": 0.5,
            "reasoning_effort": None,
            "stream": False,
            "response_schema_requested": True,
            "response_schema_runtime_fallback": "json_object",
            "implementation_attempts_per_task": phase2["evolution"][
                "implementation_attempts_per_task"
            ],
            "implementation_timeout_seconds": phase2["evolution"][
                "implementation_timeout_seconds"
            ],
            "factor_evolving_n": 1,
        },
        "paths": {key: str(value) for key, value in paths.items()},
        "evidence_policy": {
            "agent_feedback_visible_through": nested["agent_feedback"][1],
            "selection_confirmation_hidden_during_search": True,
            "historical_test_hidden_during_search": True,
            "smoke_runs_are_design_contaminated": True,
        },
    }
    write_yaml(output_dir / "config.resolved.yaml", resolved)

    library_hash = {
        "library_id": branch_spec["library_id"],
        "feature_count": len(features),
        "base_factors_file": str(base_factors),
        "base_factors_file_sha256": sha256_file(base_factors),
        "ordered_pairs_sha256": canonical_json_sha256(list(features.items())),
    }
    write_json(output_dir / "library_hash_manifest.json", library_hash)

    topic_root = config_path.parent.parents[2]
    input_manifest = {
        "created_at_utc": utc_now(),
        "config_phase2": {
            "path": str(config_path),
            "sha256": sha256_file(config_path),
        },
        "base_config": {
            "path": str(config_path.parent / phase2["base_config"]),
            "sha256": sha256_file(config_path.parent / phase2["base_config"]),
        },
        "paper": {
            "path": str(topic_root / base["paper"]["path"]),
            "sha256": base["paper"]["sha256"],
        },
        "library": library_hash,
    }
    write_json(output_dir / "input_manifest.json", input_manifest)

    credentials = configured_env_names(
        rdagent / ".env",
        (
            "OPENAI_API_KEY",
            "OPENROUTER_API_KEY",
            "CHAT_MODEL",
            "EMBEDDING_MODEL",
            "HTTP_PROXY",
            "HTTPS_PROXY",
        ),
    )
    environment_manifest = {
        "created_at_utc": utc_now(),
        "python": sys.version,
        "platform": platform.platform(),
        "rdagent_checkout": str(rdagent),
        "rdagent_commit": git_text(rdagent, "rev-parse", "--short=8", "HEAD"),
        "rdagent_adapter_diff_sha256": git_diff_sha256(rdagent),
        "uv_version": subprocess.run(
            ["uv", "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "configured_environment_names": credentials,
        "credential_values_recorded": False,
        "proxy_url_recorded": False,
    }
    write_json(output_dir / "environment_manifest.json", environment_manifest)
    patch_sha256 = write_adapter_patch(
        rdagent, output_dir / "rdagent_adapter.patch"
    )
    if patch_sha256 != environment_manifest["rdagent_adapter_diff_sha256"]:
        raise RuntimeError("RD-Agent patch snapshot hash mismatch")

    run_manifest = {
        "status": "prepared",
        "prepared_at_utc": utc_now(),
        "started_at_utc": None,
        "ended_at_utc": None,
        "exit_code": None,
        "openrouter_key_usage_start_usd": usage_start_usd,
        "openrouter_key_usage_end_usd": None,
        "openrouter_key_usage_delta_usd": None,
        "provider_reported_cost_available": usage_start_usd is not None,
        "trace": count_trace(paths["trace_path"]),
    }
    write_json(output_dir / "run_manifest.json", run_manifest)
    write_json(output_dir / "secret_scan.json", secret_scan(output_dir))


def audit(
    config_path: Path,
    branch: str,
    *,
    exit_code: int | None,
    usage_end_usd: float | None,
) -> None:
    phase2, _ = load_configs(config_path)
    paths = resolved_paths(config_path, phase2, branch)
    output_dir = paths["output_dir"]
    run_manifest_path = output_dir / "run_manifest.json"
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    rdagent = Path(phase2["runtime"]["rdagent_checkout"]).resolve()
    environment = json.loads(
        (output_dir / "environment_manifest.json").read_text(encoding="utf-8")
    )
    patch_sha256 = write_adapter_patch(
        rdagent, output_dir / "rdagent_adapter.patch"
    )
    if patch_sha256 != environment["rdagent_adapter_diff_sha256"]:
        raise RuntimeError("RD-Agent adapter drift before formal factor audit")
    usage_start = run_manifest.get("openrouter_key_usage_start_usd")
    usage_delta = (
        usage_end_usd - usage_start
        if usage_start is not None and usage_end_usd is not None
        else None
    )
    trace = count_trace(paths["trace_path"])
    run_manifest.update(
        {
            "status": (
                "raw_run_complete"
                if exit_code == 0 and trace["complete_loop_count"] > 0
                else "raw_run_failed_or_incomplete"
            ),
            "ended_at_utc": utc_now(),
            "exit_code": exit_code,
            "openrouter_key_usage_end_usd": usage_end_usd,
            "openrouter_key_usage_delta_usd": usage_delta,
            "trace": trace,
        }
    )
    write_json(run_manifest_path, run_manifest)
    scan = secret_scan(output_dir)
    write_json(output_dir / "secret_scan.json", scan)
    if not scan["passed"]:
        raise RuntimeError("secret marker found in formal output")


def mark_started(config_path: Path, branch: str) -> None:
    phase2, _ = load_configs(config_path)
    paths = resolved_paths(config_path, phase2, branch)
    run_manifest_path = paths["output_dir"] / "run_manifest.json"
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    run_manifest.update(
        {
            "status": "running",
            "started_at_utc": utc_now(),
            "trace": count_trace(paths["trace_path"]),
        }
    )
    write_json(run_manifest_path, run_manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--branch", required=True, choices=sorted(BRANCHES))
    parser.add_argument(
        "--action", required=True, choices=["prepare", "start", "audit"]
    )
    parser.add_argument("--usage-start-usd", type=float)
    parser.add_argument("--usage-end-usd", type=float)
    parser.add_argument("--exit-code", type=int)
    args = parser.parse_args()

    config_path = args.config.resolve()
    if args.action == "prepare":
        prepare(config_path, args.branch, args.usage_start_usd)
    elif args.action == "start":
        mark_started(config_path, args.branch)
    else:
        audit(
            config_path,
            args.branch,
            exit_code=args.exit_code,
            usage_end_usd=args.usage_end_usd,
        )


if __name__ == "__main__":
    main()
