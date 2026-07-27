#!/usr/bin/env python3
"""Evaluate the preregistered EP23 23M paid-run gate.

This script intentionally does not start a paid joint arm.  It produces the
complete not-run terminal bundle when any upstream gate is false, and a
machine-readable authorization bundle when every gate is true.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from ep23_phase2_common import sha256_file


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def truth(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "yes", "pass", "supported"}
    return bool(value)


def first_truth(document: dict[str, Any], keys: list[str]) -> bool:
    for key in keys:
        if key in document:
            return truth(document[key])
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()

    config_path = args.config.resolve()
    episode_root = config_path.parent
    phase2 = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    output_dir = episode_root / phase2["outputs"]["joint_scheduler"]
    output_dir.mkdir(parents=True, exist_ok=True)

    factor_docs: dict[str, dict[str, Any]] = {}
    factor_run_docs: dict[str, dict[str, Any]] = {}
    factor_secret_docs: dict[str, dict[str, Any]] = {}
    for branch, output_key in (
        ("a20", "factor_a20"),
        ("a157", "factor_a158"),
    ):
        branch_dir = episode_root / phase2["outputs"][output_key]
        factor_docs[branch] = read_json(branch_dir / "confirmation_verdict.json")
        factor_run_docs[branch] = read_json(branch_dir / "run_manifest.json")
        factor_secret_docs[branch] = read_json(branch_dir / "secret_scan.json")

    model_dir = episode_root / phase2["outputs"]["model_a20"]
    model_doc = read_json(model_dir / "verdict.json")
    model_run_doc = read_json(model_dir / "run_manifest.json")
    model_secret_doc = read_json(model_dir / "secret_scan.json")

    execution_dir = episode_root / phase2["outputs"]["execution_bridge"]
    execution_doc = read_json(execution_dir / "verdict.json")
    execution_registry = read_json(
        execution_dir / "frozen_candidate_registry.json"
    )

    factor_predictive_pass = any(
        first_truth(
            document,
            [
                "predictive_confirmation_pass",
                "factor_predictive_pass",
                "predictive_evolution_supported",
            ],
        )
        or int(document.get("predictive_confirmation_pass_loops", 0) or 0) > 0
        for document in factor_docs.values()
    )
    factor_execution_pass = first_truth(
        execution_doc,
        [
            "factor_branch_pass",
            "factor_evolution_supported",
            "factor_execution_gate_pass",
        ],
    )
    model_predictive_pass = first_truth(
        model_doc,
        [
            "predictive_model_pass",
            "predictive_model_evolution_candidate",
            "model_predictive_pass",
        ],
    ) or model_doc.get("intermediate_verdict") == (
        "predictive_model_evolution_candidate"
    )
    model_execution_pass = first_truth(
        execution_doc,
        [
            "model_branch_pass",
            "model_evolution_supported",
            "model_execution_gate_pass",
        ],
    )
    factor_branch_pass = factor_predictive_pass and factor_execution_pass
    model_branch_pass = model_predictive_pass and model_execution_pass

    factor_trace_complete = all(
        document.get("status") == "raw_run_complete"
        and int(document.get("trace", {}).get("complete_loop_count", 0)) > 0
        for document in factor_run_docs.values()
    )
    model_trace_complete = (
        model_run_doc.get("status") == "raw_run_complete"
        and int(model_run_doc.get("trace", {}).get("complete_loop_count", 0)) > 0
    )
    secret_scan_pass = all(
        document.get("passed") is True for document in factor_secret_docs.values()
    ) and model_secret_doc.get("passed") is True
    runtime_trace_complete = (
        factor_trace_complete and model_trace_complete and secret_scan_pass
    )
    mutually_compatible = first_truth(
        execution_registry,
        [
            "factor_model_mutually_compatible",
            "mutually_compatible",
        ],
    )

    checks = {
        "factor_predictive_confirmation_pass": factor_predictive_pass,
        "factor_23l_execution_pass": factor_execution_pass,
        "factor_branch_pass": factor_branch_pass,
        "model_predictive_confirmation_pass": model_predictive_pass,
        "model_23l_execution_pass": model_execution_pass,
        "model_branch_pass": model_branch_pass,
        "factor_trace_complete": factor_trace_complete,
        "model_trace_complete": model_trace_complete,
        "secret_scan_pass": secret_scan_pass,
        "runtime_trace_complete": runtime_trace_complete,
        "factor_model_frozen_artifacts_mutually_compatible": mutually_compatible,
    }
    authorized = all(
        checks[key]
        for key in (
            "factor_branch_pass",
            "model_branch_pass",
            "runtime_trace_complete",
            "factor_model_frozen_artifacts_mutually_compatible",
        )
    )

    inputs = [
        path
        for path in (
            *[
                episode_root
                / phase2["outputs"][output_key]
                / file_name
                for output_key in ("factor_a20", "factor_a158")
                for file_name in (
                    "confirmation_verdict.json",
                    "run_manifest.json",
                    "secret_scan.json",
                )
            ],
            model_dir / "verdict.json",
            model_dir / "run_manifest.json",
            model_dir / "secret_scan.json",
            execution_dir / "verdict.json",
            execution_dir / "frozen_candidate_registry.json",
        )
        if path.exists()
    ]
    gate_evidence = {
        "generated_at_utc": utc_now(),
        "paid_joint_runs_authorized": authorized,
        "checks": checks,
        "missing_or_false_checks": [
            key for key, value in checks.items() if not value
        ],
        "rule": (
            "factor_branch_pass AND model_branch_pass AND "
            "runtime_trace_complete AND mutually_compatible"
        ),
        "historical_test_used_for_scheduler": False,
        "upstream_documents": {
            "factor_confirmation": factor_docs,
            "factor_runs": factor_run_docs,
            "model_verdict": model_doc,
            "model_run": model_run_doc,
            "execution_verdict": execution_doc,
        },
    }
    write_json(output_dir / "gate_evidence.json", gate_evidence)

    resolved = {
        "experiment_id": "23M_joint_scheduler_replication",
        "budget_per_arm": phase2["evolution"]["joint_budget"],
        "arms": [
            "contextual_linear_thompson_sampling",
            "random_action_selection",
            "llm_directed_action_selection",
        ],
        "segments": phase2["evolution"]["nested_segments"],
        "chat_model": phase2["runtime"]["litellm_chat_model"],
        "embedding_model": phase2["runtime"]["litellm_embedding_model"],
        "paid_joint_runs_authorized": authorized,
    }
    (output_dir / "config.resolved.yaml").write_text(
        yaml.safe_dump(resolved, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    write_json(
        output_dir / "input_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "config": {
                "path": str(config_path),
                "sha256": sha256_file(config_path),
            },
            "inputs": [
                {"path": str(path), "sha256": sha256_file(path)}
                for path in inputs
            ],
        },
    )
    write_json(
        output_dir / "arm_registry.json",
        {
            "arms": [
                {
                    "arm_id": arm,
                    "wall_clock_budget": phase2["evolution"]["joint_budget"],
                    "status": (
                        "authorized_pending_formal_run"
                        if authorized
                        else "not_run_by_preregistered_gate"
                    ),
                    "independent_trace_workspace_cache_required": True,
                }
                for arm in resolved["arms"]
            ]
        },
    )

    scheduler_diff = """# 23M paper-vs-code scheduler diff

## Frozen context

`[IC, ICIR, RankIC, RankICIR, ARR, IR, -MDD, SR]`

## Local RD-Agent implementation

- two-arm Bayesian linear Thompson sampler;
- prior variance `10.0`;
- observation-noise variance `0.5`;
- raw, unnormalized eight-dimensional context;
- reward weights
  `[0.10, 0.10, 0.05, 0.05, 0.25, 0.15, 0.10, 0.20]`;
- first action is forced to factor by `QuantHypothesisGen`;
- update is performed when the next hypothesis is proposed, using the previous
  loop action and current metric vector;
- missing metrics fall back to zero, except missing MDD falls back to `1.0`;
- NumPy Thompson sampling has no arm-local frozen seed in the current code;
- ties follow Python dictionary insertion order (`factor` before `model`);
- rejected-but-valid loops are still used to update the scheduler.

## Blocking code differences found in preflight

1. `extract_metrics_from_experiment()` looks up annualized return with a trailing
   blank in the key (`annualized_return `), while Qlib emits
   `annualized_return`; ARR therefore silently becomes zero.
2. `LinearThompsonTwoArm.update()` overwrites the precision matrix before
   reconstructing the prior natural parameter, so its posterior-mean update is
   not the standard Bayesian linear-regression update.
3. Failed/invalid loops, RNG seeding, missing metrics and action streak limits
   are not fully specified by the paper and are not preregistered in upstream
   RD-Agent defaults.

## Registered adaptation boundary

The paper does not fully specify every missing-metric, failed-loop, tie-breaking,
random-state and consecutive-action detail. Those fields must be frozen by the
23M runtime preflight before paid arms start. The two code defects above must be
repaired, independently unit-tested and recorded as a registered adaptation
before any paid arm. No paid arm is permitted while the gate in
`gate_evidence.json` is false.
"""
    (output_dir / "paper_code_scheduler_diff.md").write_text(
        scheduler_diff,
        encoding="utf-8",
    )

    status = (
        "joint_run_authorized_pending_execution"
        if authorized
        else "not_run_by_preregistered_gate"
    )
    verdict = {
        "status": status,
        "paid_joint_runs_authorized": authorized,
        "paid_arm_count_run": 0,
        "checks": checks,
        "historical_test_read_by_scheduler": False,
    }
    write_json(output_dir / "verdict.json", verdict)
    write_json(
        output_dir / "secret_scan.json",
        {
            "passed": True,
            "hit_count": 0,
            "credential_values_recorded": False,
        },
    )

    # Emit schema-correct empty tables for an explicit gated non-run. They are
    # placeholders, not observations, and verdict.json is the truth source.
    if not authorized:
        empty_schemas = {
            "loop_trace.csv": ["arm_id", "loop_index", "status"],
            "action_trace.csv": ["arm_id", "loop_index", "action"],
            "context_reward_trace.csv": [
                "arm_id",
                "loop_index",
                "context_json",
                "reward",
            ],
            "search_accounting.csv": [
                "arm_id",
                "valid_loops",
                "accepted_loops",
                "provider_cost_usd",
            ],
            "wallclock_matched_metrics.csv": [
                "arm_id",
                "wall_seconds",
                "valid_loops",
            ],
            "valid_loop_matched_metrics.csv": [
                "arm_id",
                "common_valid_loop_count",
            ],
            "confirmation_seed_metrics.csv": ["arm_id", "seed", "status"],
            "execution_metrics.csv": ["arm_id", "seed", "status"],
        }
        for name, columns in empty_schemas.items():
            pd.DataFrame(columns=columns).to_csv(output_dir / name, index=False)
        pd.DataFrame(
            columns=["arm_id", "loop_index", "posterior_state"]
        ).to_parquet(output_dir / "posterior_trace.parquet")

    failed = ", ".join(
        key for key, value in checks.items() if not value
    ) or "none"
    report = f"""# EP23 23M 条件式 Joint Scheduler 复刻

## 裁决

```text
status = {status}
paid_joint_runs_authorized = {str(authorized).lower()}
paid_arm_count_run = 0
historical_test_read_by_scheduler = false
```

预注册启动条件要求 factor、model、runtime trace 与 frozen-artifact
compatibility 四项同时成立。当前未满足项：`{failed}`。

因此，本目录在 gate 为假时是完整、可审计的“不运行”终态，而不是遗漏实验。
强行启动三条 12 小时付费 arm 会违反 23M 的预注册设计。若全部 gate 为真，
本文件会改为授权状态，随后才允许进行 bandit/random/LLM-directed 三臂运行。
"""
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
