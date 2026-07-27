#!/usr/bin/env python3
"""Finalize 23K1 and materialize the conditional 23K2 gate bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from ep23_phase2_common import sha256_file


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    root = config_path.parent
    phase2 = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model_dir = root / phase2["outputs"]["model_a20"]
    sensitivity_dir = root / phase2["outputs"]["model_best_library"]
    sensitivity_dir.mkdir(parents=True, exist_ok=True)
    run = json.loads(
        (model_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    predictive = json.loads(
        (model_dir / "verdict.json").read_text(encoding="utf-8")
    )
    execution_path = (
        root / phase2["outputs"]["execution_bridge"] / "verdict.json"
    )
    execution = (
        json.loads(execution_path.read_text(encoding="utf-8"))
        if execution_path.exists()
        else {}
    )
    loops = pd.read_csv(model_dir / "loop_trace.csv")
    accounting = pd.read_csv(model_dir / "search_accounting.csv")
    attribution = pd.read_csv(
        model_dir / "matched_model_attribution.csv"
    )
    candidate_verdicts = pd.read_csv(model_dir / "candidate_verdicts.csv")
    model_execution_pass = bool(execution.get("model_branch_pass", False))
    model_supported = bool(
        predictive.get("predictive_model_pass") and model_execution_pass
    )
    final = {
        **predictive,
        "status": (
            "model_evolution_supported"
            if model_supported
            else "no_model_evolution"
            if run.get("status") == "raw_run_complete"
            else "runtime_blocked"
        ),
        "raw_run_complete": run.get("status") == "raw_run_complete",
        "model_execution_gate_pass": model_execution_pass,
        "model_evolution_supported": model_supported,
        "provider_cost_usd": run.get("openrouter_key_usage_delta_usd"),
        "historical_test_read_by_23k_search": False,
    }
    write_json(model_dir / "verdict.json", final)
    report = f"""# EP23 23K1 RD-Agent 模型进化

## 裁决

```text
status = {final["status"]}
completed_loops = {len(loops)}
agent_accepted_models = {int(accounting.iloc[0]["accepted_models"])}
predictive_model_pass = {str(bool(predictive.get("predictive_model_pass"))).lower()}
model_execution_gate_pass = {str(model_execution_pass).lower()}
provider_cost_usd = {float(run.get("openrouter_key_usage_delta_usd") or 0):.6f}
```

Agent-accepted 模型已与 frozen LightGBM、flattened MLP、last-state GRU、
attentive GRU 和 capacity-matched neural baseline 做五 seed 归因。实际模型
代码、训练超参数、参数量、训练时间和内存证据保存在结构化产物中。

## Candidate verdicts

{candidate_verdicts.to_markdown(index=False)}

## Matched attribution 摘要

{attribution.groupby(["candidate_variant", "baseline_variant", "split", "metric"])["delta"].agg(["median", lambda x: int((x > 0).sum())]).reset_index().to_markdown(index=False) if len(attribution) else "无 Agent-accepted model。"}
"""
    (model_dir / "report.md").write_text(report, encoding="utf-8")

    factor_gate = bool(execution.get("factor_branch_pass", False))
    sensitivity_status = (
        "authorized_pending_formal_run"
        if factor_gate
        else "not_run_by_preregistered_gate"
    )
    gate = {
        "factor_predictive_and_23l_execution_gate_pass": factor_gate,
        "status": sensitivity_status,
        "reason": (
            "At least one evolved factor library passed predictive, redundancy "
            "and 23L execution gates."
            if factor_gate
            else "No evolved factor library passed the full preregistered gate."
        ),
        "historical_test_used_by_gate": True,
        "sensitivity_lane_is_not_paper_primary_lane": True,
    }
    write_json(sensitivity_dir / "gate_evidence.json", gate)
    (sensitivity_dir / "config.resolved.yaml").write_text(
        yaml.safe_dump(
            {
                "experiment_id": "23K2_RDModel_best_frozen_library_solpro_6h",
                "status": sensitivity_status,
                "wall_clock_budget": phase2["evolution"]["model_budget"],
                "segments": phase2["evolution"]["nested_segments"],
                "paper_replication_identity": "project_sensitivity_only",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    write_json(
        sensitivity_dir / "input_manifest.json",
        {
            "config": {
                "path": str(config_path),
                "sha256": sha256_file(config_path),
            },
            "execution_verdict": {
                "path": str(execution_path),
                "sha256": (
                    sha256_file(execution_path)
                    if execution_path.exists()
                    else None
                ),
            },
        },
    )
    write_json(
        sensitivity_dir / "verdict.json",
        {
            "status": sensitivity_status,
            "paid_run_started": False,
            "paper_primary_lane": False,
        },
    )
    (sensitivity_dir / "report.md").write_text(
        f"""# EP23 23K2 best-frozen-library sensitivity

```text
status = {sensitivity_status}
paper_primary_lane = false
paid_run_started = false
```

23K2 只有在 evolved factor library 同时通过预测、冗余与 23L execution gate
后才允许运行。gate 为假时，本目录即为预注册的完整不运行终态。
""",
        encoding="utf-8",
    )
    print(json.dumps({"23K1": final, "23K2": gate}, indent=2))


if __name__ == "__main__":
    main()
