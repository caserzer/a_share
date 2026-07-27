#!/usr/bin/env python3
"""Prepare, mark and audit the formal EP23 23K RD-Model lane."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ep23_phase2_common import canonical_json_sha256, load_configs, sha256_file
from run_23i_factor_evolution_control import (
    configured_env_names,
    count_trace,
    git_diff_sha256,
    git_text,
    secret_scan,
    write_adapter_patch,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def paths(config_path: Path, phase2: dict[str, Any]) -> dict[str, Path]:
    root = config_path.parent
    output = root / phase2["outputs"]["model_a20"]
    return {
        "episode_root": root,
        "output_dir": output,
        "trace_path": output / "raw_rdagent_trace",
        "workspace_path": output / "workspaces",
        "cache_path": output / "pickle_cache",
        "base_features_path": root / "rdagent_base_features_phase2/alpha20",
    }


def prepare(config_path: Path, usage_start_usd: float | None) -> None:
    phase2, base = load_configs(config_path)
    resolved_paths = paths(config_path, phase2)
    output_dir = resolved_paths["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    rdagent = Path(phase2["runtime"]["rdagent_checkout"]).resolve()
    base_factors = resolved_paths["base_features_path"] / "base_factors.json"
    factors = json.loads(base_factors.read_text(encoding="utf-8"))
    if len(factors) != 20:
        raise RuntimeError(f"A20 base factor count drift: {len(factors)}")

    nested = phase2["evolution"]["nested_segments"]
    resolved = {
        "experiment_id": "23K1_RDModel_A20_solpro_6h",
        "library_id": "A20_RDAGENT_PINNED",
        "feature_count": 20,
        "wall_clock_budget": phase2["evolution"]["model_budget"],
        "segments": nested,
        "runtime": {
            "environment_manager": "uv",
            "chat_model": phase2["runtime"]["litellm_chat_model"],
            "embedding_model": phase2["runtime"]["litellm_embedding_model"],
            "provider": "openrouter",
            "proxy_required": True,
            "model_evolving_n": 1,
            "implementation_attempts_per_task": phase2["evolution"][
                "implementation_attempts_per_task"
            ],
        },
        "paths": {key: str(value) for key, value in resolved_paths.items()},
        "evidence_policy": {
            "agent_feedback_visible_through": nested["agent_feedback"][1],
            "selection_confirmation_hidden_during_search": True,
            "historical_test_hidden_during_search": True,
        },
    }
    (output_dir / "config.resolved.yaml").write_text(
        yaml.safe_dump(resolved, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    library_hash = {
        "library_id": "A20_RDAGENT_PINNED",
        "feature_count": len(factors),
        "base_factors_file": str(base_factors),
        "base_factors_file_sha256": sha256_file(base_factors),
        "ordered_pairs_sha256": canonical_json_sha256(list(factors.items())),
    }
    write_json(output_dir / "library_hash_manifest.json", library_hash)
    topic_root = config_path.parent.parents[2]
    write_json(
        output_dir / "input_manifest.json",
        {
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
        },
    )
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
    write_json(
        output_dir / "environment_manifest.json",
        {
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
        },
    )
    environment = json.loads(
        (output_dir / "environment_manifest.json").read_text(encoding="utf-8")
    )
    patch_sha256 = write_adapter_patch(
        rdagent, output_dir / "rdagent_adapter.patch"
    )
    if patch_sha256 != environment["rdagent_adapter_diff_sha256"]:
        raise RuntimeError("RD-Agent model patch snapshot hash mismatch")
    write_json(
        output_dir / "run_manifest.json",
        {
            "status": "prepared",
            "prepared_at_utc": utc_now(),
            "started_at_utc": None,
            "ended_at_utc": None,
            "exit_code": None,
            "openrouter_key_usage_start_usd": usage_start_usd,
            "openrouter_key_usage_end_usd": None,
            "openrouter_key_usage_delta_usd": None,
            "trace": count_trace(resolved_paths["trace_path"]),
        },
    )
    write_json(output_dir / "secret_scan.json", secret_scan(output_dir))


def mark_started(config_path: Path) -> None:
    phase2, _ = load_configs(config_path)
    resolved_paths = paths(config_path, phase2)
    manifest_path = resolved_paths["output_dir"] / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "status": "running",
            "started_at_utc": utc_now(),
            "trace": count_trace(resolved_paths["trace_path"]),
        }
    )
    write_json(manifest_path, manifest)


def audit(
    config_path: Path, exit_code: int | None, usage_end_usd: float | None
) -> None:
    phase2, _ = load_configs(config_path)
    resolved_paths = paths(config_path, phase2)
    output_dir = resolved_paths["output_dir"]
    rdagent = Path(phase2["runtime"]["rdagent_checkout"]).resolve()
    environment = json.loads(
        (output_dir / "environment_manifest.json").read_text(encoding="utf-8")
    )
    patch_sha256 = write_adapter_patch(
        rdagent, output_dir / "rdagent_adapter.patch"
    )
    if patch_sha256 != environment["rdagent_adapter_diff_sha256"]:
        raise RuntimeError("RD-Agent adapter drift before model audit")
    manifest_path = output_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    usage_start = manifest.get("openrouter_key_usage_start_usd")
    trace = count_trace(resolved_paths["trace_path"])
    manifest.update(
        {
            "status": (
                "raw_run_complete"
                if exit_code == 0 and trace["complete_loop_count"] > 0
                else "raw_run_failed_or_incomplete"
            ),
            "ended_at_utc": utc_now(),
            "exit_code": exit_code,
            "openrouter_key_usage_end_usd": usage_end_usd,
            "openrouter_key_usage_delta_usd": (
                usage_end_usd - usage_start
                if usage_end_usd is not None and usage_start is not None
                else None
            ),
            "trace": trace,
        }
    )
    write_json(manifest_path, manifest)
    scan = secret_scan(output_dir)
    write_json(output_dir / "secret_scan.json", scan)
    if not scan["passed"]:
        raise RuntimeError("secret marker found in formal model output")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--action", required=True, choices=["prepare", "start", "audit"]
    )
    parser.add_argument("--usage-start-usd", type=float)
    parser.add_argument("--usage-end-usd", type=float)
    parser.add_argument("--exit-code", type=int)
    args = parser.parse_args()
    config_path = args.config.resolve()
    if args.action == "prepare":
        prepare(config_path, args.usage_start_usd)
    elif args.action == "start":
        mark_started(config_path)
    else:
        audit(config_path, args.exit_code, args.usage_end_usd)


if __name__ == "__main__":
    main()
