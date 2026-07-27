#!/usr/bin/env python3
"""EP23 Phase 2 factor-library, runtime, and materialization preflight."""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import dotenv_values

from ep23_phase2_common import (
    canonical_json_sha256,
    get_library_definitions,
    library_as_dict,
    library_hashes,
    load_configs,
    materialization_summary,
    materialize_library,
    sha256_file,
)


def git_value(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def effective_rdagent_settings(repo: Path) -> dict[str, str]:
    code = """
import json
from dotenv import load_dotenv
load_dotenv('.env', override=False)
from rdagent.oai.backend.litellm import LITELLM_SETTINGS
print(json.dumps({
    'chat_model': LITELLM_SETTINGS.chat_model,
    'embedding_model': LITELLM_SETTINGS.embedding_model,
}))
"""
    result = subprocess.run(
        [str(repo / ".venv/bin/python"), "-c", code],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def safe_openrouter_smoke(env_path: Path, phase2: dict[str, Any]) -> dict[str, Any]:
    env = dotenv_values(env_path)
    key = env.get("OPENAI_API_KEY")
    base = (env.get("OPENAI_API_BASE") or "https://openrouter.ai/api/v1").rstrip("/")
    proxy = env.get("HTTP_PROXY") or env.get("HTTPS_PROXY")
    if not key or not proxy:
        return {
            "chat_status": "blocked",
            "embedding_status": "blocked",
            "reason": "missing_key_or_required_proxy",
        }
    proxies = {"http": proxy, "https": proxy}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    chat = requests.post(
        f"{base}/chat/completions",
        headers=headers,
        proxies=proxies,
        timeout=90,
        json={
            "model": phase2["runtime"]["chat_model"],
            "messages": [{"role": "user", "content": "Reply with exactly OK"}],
            "max_tokens": 8,
        },
    )
    chat_body = chat.json() if chat.headers.get("content-type", "").startswith("application/json") else {}
    chat_content = (
        (((chat_body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
        .strip()
    )

    embedding = requests.post(
        f"{base}/embeddings",
        headers=headers,
        proxies=proxies,
        timeout=90,
        json={
            "model": phase2["runtime"]["embedding_model"],
            "input": ["EP23 runtime smoke"],
        },
    )
    embedding_body = (
        embedding.json()
        if embedding.headers.get("content-type", "").startswith("application/json")
        else {}
    )
    vector = (
        ((embedding_body.get("data") or [{}])[0].get("embedding") or [])
        if embedding.ok
        else []
    )
    return {
        "chat_http_status": chat.status_code,
        "chat_status": "passed"
        if chat.ok
        and chat_body.get("model") == phase2["runtime"]["chat_model"]
        and chat_content == "OK"
        else "failed",
        "chat_resolved_model": chat_body.get("model"),
        "chat_response_contract": chat_content == "OK",
        "embedding_http_status": embedding.status_code,
        "embedding_status": "passed" if embedding.ok and len(vector) > 0 else "failed",
        "embedding_resolved_model": embedding_body.get("model"),
        "embedding_dimensions": len(vector),
        "proxy_configured": bool(proxy),
        "secrets_recorded": False,
    }


def scan_secret_prefixes(root: Path, prefixes: list[str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    excluded_parts = {"2505.15155v2.pdf", "__pycache__"}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in excluded_parts for part in path.parts):
            continue
        if path.suffix.lower() in {".parquet", ".pth", ".pkl", ".pdf", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for prefix in prefixes:
            for match in re.finditer(re.escape(prefix), text):
                hits.append(
                    {
                        "path": str(path.relative_to(root)),
                        "prefix": prefix,
                        "offset": match.start(),
                    }
                )
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--skip-network", action="store_true")
    args = parser.parse_args()

    started = time.monotonic()
    phase2_path = Path(args.config).resolve()
    episode_root = phase2_path.parent
    phase2, base = load_configs(phase2_path)
    topic_root = episode_root.parents[2]
    output_dir = episode_root / phase2["outputs"]["preflight"]
    output_dir.mkdir(parents=True, exist_ok=True)
    rdagent = Path(phase2["runtime"]["rdagent_checkout"])

    effective_settings = effective_rdagent_settings(rdagent)

    runtime = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "pyqlib": version("pyqlib"),
        "rdagent_commit": git_value(rdagent, "rev-parse", "HEAD"),
        "rdagent_dirty": bool(git_value(rdagent, "status", "--short")),
        "effective_litellm_chat_model": effective_settings["chat_model"],
        "effective_litellm_embedding_model": effective_settings["embedding_model"],
        "expected_litellm_chat_model": phase2["runtime"]["litellm_chat_model"],
        "expected_litellm_embedding_model": phase2["runtime"][
            "litellm_embedding_model"
        ],
        "network_smoke": (
            {"chat_status": "skipped", "embedding_status": "skipped"}
            if args.skip_network
            else safe_openrouter_smoke(rdagent / ".env", phase2)
        ),
    }
    (output_dir / "runtime_model_smoke.json").write_text(
        json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    libraries = get_library_definitions(base)
    registry: dict[str, Any] = {}
    lineage_rows: list[dict[str, Any]] = []
    hash_manifest: dict[str, Any] = {}
    for library_id, library in libraries.items():
        hashes = library_hashes(library)
        registry[library_id] = {
            "source": library["source"],
            "feature_count": len(library["names"]),
            "unique_name_count": len(set(library["names"])),
            **hashes,
        }
        hash_manifest[library_id] = hashes
        for ordinal, (name, expression) in enumerate(
            zip(library["names"], library["expressions"], strict=True), start=1
        ):
            lineage_rows.append(
                {
                    "library_id": library_id,
                    "ordinal": ordinal,
                    "feature_name": name,
                    "expression": expression,
                    "expression_sha256": canonical_json_sha256(expression),
                    "source": library["source"],
                    "status": "pinned",
                }
            )

    registry["A101_CANONICAL_REBUILT"] = {
        "source": "Kakushadze 2016, arXiv:1601.00991",
        "expected_feature_count": 101,
        "status": "replication_blocked",
        "reason": (
            "no pinned 101-of-101 local implementation with reference-value "
            "crosscheck; canonical formulas also depend on fields/operators not "
            "frozen in the M0 PIT contract"
        ),
    }
    registry["AUTOALPHA_EXACT_ARTIFACT"] = {
        "source": "Kou et al., arXiv:2409.06289",
        "status": "definition_blocked",
        "reason": (
            "no complete frozen factor artifact, multimodal input snapshot, "
            "generation trace, and content hash in the cited RD-Agent checkout"
        ),
    }
    (output_dir / "factor_library_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    pd.DataFrame(lineage_rows).to_csv(
        output_dir / "factor_library_lineage.csv", index=False
    )

    pd.DataFrame(
        [
            {
                "alpha_id": f"Alpha{index:03d}",
                "canonical_source": "arXiv:1601.00991",
                "formula_pinned": False,
                "operator_compatibility": "not_auditable",
                "reference_value_crosscheck": False,
                "status": "definition_or_implementation_blocked",
                "reason": (
                    "no 101-of-101 pinned implementation and reference panel; "
                    "partial or third-party approximations are excluded"
                ),
            }
            for index in range(1, 102)
        ]
    ).to_csv(output_dir / "alpha101_operator_compatibility.csv", index=False)

    autoalpha_audit = """# AutoAlpha artifact audit

## Verdict

```text
AUTOALPHA_DEFINITION_BLOCKED
```

The R&D-Agent-Quant paper cites Kou et al., arXiv:2409.06289. That system is a
dynamic LLM/multi-agent strategy process over multimodal inputs, not a fully
enumerated static OHLCV factor dictionary in the local RD-Agent checkout.

The local audit did not find a complete frozen factor artifact with all of:

- factor names and executable formulas/code;
- exact multimodal input snapshot and point-in-time availability;
- generation prompts/model versions and selection trace;
- output/library hash;
- reference predictions or values for cross-checking.

Therefore no local library is allowed to use the name AutoAlpha. A future local
agent-generated comparator must be named `LOCAL_AGENT_DYNAMIC_LIBRARY_SOLPRO`.
"""
    (output_dir / "autoalpha_artifact_audit.md").write_text(
        autoalpha_audit, encoding="utf-8"
    )

    labels = {
        name: base["labels"][name]["expression"]
        for name in ["paper_proxy", "executable_bridge"]
    }
    provider_path = topic_root / base["data"]["provider_uri"]
    smoke_start, smoke_end = phase2["preflight"]["materialization_smoke"]
    coverage_rows: list[dict[str, Any]] = []
    feature_coverage_rows: list[dict[str, Any]] = []
    for library_id, library in libraries.items():
        try:
            frame = materialize_library(
                provider_path=provider_path,
                market=base["data"]["market"],
                library=library,
                labels=labels,
                start_time=smoke_start,
                end_time=smoke_end,
            )
            summary = materialization_summary(
                library_id, frame, list(library["names"])
            )
            for name in library["names"]:
                series = frame[name]
                feature_coverage_rows.append(
                    {
                        "library_id": library_id,
                        "feature_name": name,
                        "finite_ratio": float(series.notna().mean()),
                        "unique_value_count": int(series.nunique(dropna=True)),
                        "empty": bool(series.notna().sum() == 0),
                        "constant": bool(series.nunique(dropna=True) <= 1),
                    }
                )
            summary["status"] = "passed"
            summary["error"] = ""
        except Exception as exc:
            summary = {
                "library_id": library_id,
                "feature_count": len(library["names"]),
                "rows": 0,
                "dates": 0,
                "instruments": 0,
                "finite_ratio": 0.0,
                "constant_or_empty_features": len(library["names"]),
                "unique_index": False,
                "status": "failed",
                "error": f"{type(exc).__name__}: {str(exc)[:500]}",
            }
        coverage_rows.append(summary)
    coverage = pd.DataFrame(coverage_rows)
    coverage.to_csv(output_dir / "library_materialization_coverage.csv", index=False)
    pd.DataFrame(feature_coverage_rows).to_csv(
        output_dir / "library_feature_coverage.csv", index=False
    )

    coverage_by_id = coverage.set_index("library_id")
    exact_library_blockers = {}
    for library_id, expected_vwap_empty in [
        ("A158_QLIB_PINNED", 1),
        ("A360_QLIB_PINNED", 60),
    ]:
        exact_library_blockers[library_id] = {
            "status": "replication_blocked_by_missing_vwap",
            "empty_vwap_features": expected_vwap_empty,
            "observed_minimum_feature_finite_ratio": float(
                coverage_by_id.loc[library_id, "minimum_feature_finite_ratio"]
            ),
        }
        registry[library_id]["replication_status"] = (
            "replication_blocked_by_missing_vwap"
        )
    registry["A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION"][
        "replication_status"
    ] = "registered_primary_route_adaptation"
    registry["A300_QLIB_NO_VWAP_REGISTERED_ADAPTATION"][
        "replication_status"
    ] = "registered_primary_route_adaptation"
    (output_dir / "factor_library_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    base_features_root = episode_root / "rdagent_base_features_phase2"
    for library_id, folder in [
        ("A20_RDAGENT_PINNED", "alpha20"),
        ("A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION", "alpha158"),
    ]:
        target = base_features_root / folder
        target.mkdir(parents=True, exist_ok=True)
        (target / "base_factors.json").write_text(
            json.dumps(
                library_as_dict(libraries[library_id]),
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    hash_manifest["files"] = {
        "config_phase2.yaml": sha256_file(phase2_path),
        "config.yaml": sha256_file(episode_root / phase2["base_config"]),
        "paper": sha256_file(episode_root / base["paper"]["path"].split("/")[-1]),
        "alpha20_base_factors": sha256_file(
            base_features_root / "alpha20/base_factors.json"
        ),
        "alpha158_base_factors": sha256_file(
            base_features_root / "alpha158/base_factors.json"
        ),
    }
    (output_dir / "library_hash_manifest.json").write_text(
        json.dumps(hash_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    preflight_cfg = phase2["preflight"]
    primary_counts_ok = all(
        registry[library_id]["feature_count"]
        == registry[library_id]["unique_name_count"]
        == expected
        for library_id, expected in [
            ("A20_RDAGENT_PINNED", 20),
            ("A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION", 157),
            ("A300_QLIB_NO_VWAP_REGISTERED_ADAPTATION", 300),
        ]
    )
    primary_library_ids = [
        "A20_RDAGENT_PINNED",
        "A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION",
        "A300_QLIB_NO_VWAP_REGISTERED_ADAPTATION",
    ]
    primary_coverage = coverage[coverage["library_id"].isin(primary_library_ids)]
    materialization_ok = bool(
        (
            (primary_coverage["status"] == "passed")
            & (primary_coverage["rows"] >= preflight_cfg["minimum_rows"])
            & (primary_coverage["dates"] >= preflight_cfg["minimum_dates"])
            & (
                primary_coverage["instruments"]
                >= preflight_cfg["minimum_instruments"]
            )
            & (
                primary_coverage["minimum_feature_finite_ratio"]
                >= preflight_cfg["minimum_finite_ratio"]
            )
            & primary_coverage["unique_index"].astype(bool)
        ).all()
    )
    runtime_config_ok = (
        runtime["effective_litellm_chat_model"]
        == phase2["runtime"]["litellm_chat_model"]
        and runtime["effective_litellm_embedding_model"]
        == phase2["runtime"]["litellm_embedding_model"]
    )
    network_ok = (
        args.skip_network
        or (
            runtime["network_smoke"].get("chat_status") == "passed"
            and runtime["network_smoke"].get("embedding_status") == "passed"
        )
    )
    secret_hits = scan_secret_prefixes(
        episode_root, ["sk-" + "or-v1-"]
    )
    secret_ok = not secret_hits
    ready = primary_counts_ok and materialization_ok and runtime_config_ok and network_ok and secret_ok
    if not secret_ok:
        terminal_state = "blocked_by_secret_leak"
    elif not runtime_config_ok or not network_ok:
        terminal_state = "blocked_by_runtime"
    elif not primary_counts_ok or not materialization_ok:
        terminal_state = "blocked_by_primary_library_materialization"
    else:
        terminal_state = "ready_for_primary_static_benchmark"
    verdict = {
        "stage": "23G_factor_library_preflight",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "terminal_state": terminal_state,
        "ready_for_primary_static_benchmark": ready,
        "gates": {
            "primary_counts_ok": primary_counts_ok,
            "primary_materialization_ok": materialization_ok,
            "runtime_config_ok": runtime_config_ok,
            "network_smoke_ok": network_ok,
            "secret_scan_ok": secret_ok,
        },
        "conditional_libraries": {
            **{
                key: value["status"]
                for key, value in exact_library_blockers.items()
            },
            "A101_CANONICAL_REBUILT": "A101_REPLICATION_BLOCKED",
            "AUTOALPHA_EXACT_ARTIFACT": "AUTOALPHA_DEFINITION_BLOCKED",
        },
        "secret_scan_hit_count": len(secret_hits),
        "secret_scan_hits_redacted": [
            {"path": hit["path"], "prefix": hit["prefix"]} for hit in secret_hits
        ],
        "elapsed_seconds": time.monotonic() - started,
    }
    (output_dir / "preflight_verdict.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    coverage_md = coverage.to_markdown(index=False)
    report = f"""# EP23 23G 因子库与运行时预检

## 裁决

```text
terminal_state = {terminal_state}
ready_for_primary_static_benchmark = {str(ready).lower()}
A101 = A101_REPLICATION_BLOCKED
AutoAlpha = AUTOALPHA_DEFINITION_BLOCKED
Alpha158 exact = replication_blocked_by_missing_vwap
Alpha360 exact = replication_blocked_by_missing_vwap
A157/A300 no-VWAP = registered_primary_route_adaptation
```

Alpha101/AutoAlpha 的定义阻塞不会被近似实现掩盖。完整 Alpha158/360 因当前
PIT provider 缺少经过审计的 `$vwap` 而阻塞；23H 使用显式命名的 A157/A300
no-VWAP adaptation，不把它们冒充完整 Alpha158/360。

## Primary library materialization

{coverage_md}

## Runtime

```text
effective chat     = {runtime["effective_litellm_chat_model"]}
effective embedding= {runtime["effective_litellm_embedding_model"]}
chat smoke         = {runtime["network_smoke"].get("chat_status")}
embedding smoke    = {runtime["network_smoke"].get("embedding_status")}
secret scan hits   = {len(secret_hits)}
```

## 解释边界

- 这里只做短窗口物化，不是因子有效性检验。
- Alpha101 需要 101/101 公式、实现和参考数值对拍；当前不满足。
- AutoAlpha 缺少完整动态 artifact 和 PIT 多模态数据快照；当前不满足。
- historical test 和 Big Winner 标签没有进入本阶段。
"""
    (output_dir / "23G_factor_library_preflight_report.md").write_text(
        report, encoding="utf-8"
    )
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
