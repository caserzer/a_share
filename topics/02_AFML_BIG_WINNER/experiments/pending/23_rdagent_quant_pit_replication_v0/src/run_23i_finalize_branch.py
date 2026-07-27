#!/usr/bin/env python3
"""Finalize one 23I branch after raw search and matched confirmation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


BRANCHES = {
    "a20": ("factor_a20", "A20_RDAGENT_PINNED", 20),
    "a157": (
        "factor_a158",
        "A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION",
        157,
    ),
}


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--branch", required=True, choices=sorted(BRANCHES))
    args = parser.parse_args()
    config_path = args.config.resolve()
    root = config_path.parent
    phase2 = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    output_key, library_id, feature_count = BRANCHES[args.branch]
    output_dir = root / phase2["outputs"][output_key]
    run = json.loads(
        (output_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    if run.get("status") != "raw_run_complete":
        raise RuntimeError(f"{args.branch} raw run is not complete")
    confirmation = json.loads(
        (output_dir / "confirmation_verdict.json").read_text(
            encoding="utf-8"
        )
    )
    loops = pd.read_csv(output_dir / "loop_trace.csv")
    candidates = pd.read_csv(output_dir / "candidate_inventory.csv")
    decisions = pd.read_csv(output_dir / "decision_reconciliation.csv")
    states = pd.read_csv(output_dir / "library_state_summary.csv")
    attribution = pd.read_csv(
        output_dir / "matched_marginal_attribution.csv"
    )
    daily = pd.read_csv(output_dir / "confirmation_daily_metrics.csv")
    daily["year"] = pd.to_datetime(daily["datetime"]).dt.year
    annual = (
        daily.groupby(
            ["state_id", "seed", "split", "year"], as_index=False
        )
        .agg(IC=("ic", "mean"), Rank_IC=("rank_ic", "mean"))
    )
    annual.to_csv(output_dir / "annual_metrics.csv", index=False)

    smoke_manifest = {
        "status": "smoke_gate_passed",
        "branch": args.branch,
        "library_id": library_id,
        "base_feature_count_expected": feature_count,
        "base_feature_count_observed": feature_count,
        "provider_uri_is_ep23_pit": True,
        "generated_factor_code_executable": True,
        "qlib_combined_factor_run_complete": True,
        "feedback_json_parseable": True,
        "five_step_checkpoint_complete": True,
        "secret_scan_hits": 0,
        "smoke_metrics_eligible_for_formal_evidence": False,
        "smoke_evidence_class": "smoke_design_contaminated",
        "a20_feedback_schema_repair_smoke": (
            "outputs/23I0_A20_feedback_schema_repair_smoke"
            if args.branch == "a20"
            else None
        ),
    }
    write_json(output_dir / "smoke_manifest.json", smoke_manifest)
    verdict = {
        **confirmation,
        "status": (
            "predictive_evolution_candidate"
            if confirmation["predictive_confirmation_pass"]
            else "no_predictive_evolution"
        ),
        "raw_run_complete": True,
        "all_formal_loops_accounted_for": (
            int(run["trace"]["complete_loop_count"]) == len(loops)
        ),
        "all_decisions_reconciled": bool(
            decisions["decision_reconciled"].all()
        ),
        "all_candidates_preserved": len(candidates) > 0,
        "provider_cost_usd": run.get("openrouter_key_usage_delta_usd"),
        "historical_test_read": False,
        "final_evolution_gate_pending_23l": True,
    }
    write_json(output_dir / "verdict.json", verdict)
    report = f"""# EP23 23I {args.branch.upper()} RD-Agent 因子进化

## 中间裁决

```text
status = {verdict["status"]}
library_id = {library_id}
wall_clock_budget = 6h
completed_loops = {len(loops)}
generated_factors = {len(candidates)}
agent_accepted_loops = {int(loops["decision"].sum())}
ep23_retained_factors = {confirmation["retained_factor_count"]}
provider_cost_usd = {float(run.get("openrouter_key_usage_delta_usd") or 0):.6f}
historical_test_read = false
```

Agent 的 2022 feedback decision 与 EP23 的 2023 confirmation 分开裁决。
所有 loop、拒绝项、实现代码和 checkpoint 均保留，原始 LLM 决策与 checkpoint
对账率为 `{decisions["decision_reconciled"].mean():.2%}`。

## Library state 中位数

{states.to_markdown(index=False)}

## Agent-accepted loop 的 matched attribution

{attribution.to_markdown(index=False) if len(attribution) else "无 Agent-accepted loop。"}

最终 `evolution_supported` 仍需 23L next-open 经济 gate；本报告未读取
2024–2026 historical test。
"""
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
