#!/usr/bin/env python3
"""Audit the isolated one-loop 23K model feedback/runtime smoke."""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from pathlib import Path
from typing import Any

import yaml

from run_23i_factor_evolution_control import count_trace, secret_scan
from run_23k_collect_rdagent_trace import RAW_DECISION_RE


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    phase2 = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    rdagent = Path(phase2["runtime"]["rdagent_checkout"]).resolve()
    trace_path = output_dir / "raw_rdagent_trace"
    trace = count_trace(trace_path)
    records = sorted(
        (trace_path / "__session__").glob("*/*_record"),
        key=lambda path: int(path.parent.name),
    )
    if len(records) != 1:
        raise RuntimeError(f"expected exactly one smoke record, got {len(records)}")
    os.environ.setdefault(
        "LOG_TRACE_PATH", str(Path("/tmp") / "ep23_model_smoke_reader")
    )
    sys.path.insert(0, str(rdagent))
    with records[0].open("rb") as handle:
        state = pickle.load(handle)
    experiment, feedback = state.trace.hist[-1]
    tasks = list(experiment.sub_tasks or [])
    workspaces = list(experiment.sub_workspace_list or [])
    model_code = (
        str(workspaces[0].file_dict.get("model.py", ""))
        if workspaces
        else ""
    )
    console = (output_dir / "console.log").read_text(
        encoding="utf-8", errors="replace"
    )
    raw_values = [
        match.group("value").strip('"').lower()
        for match in RAW_DECISION_RE.finditer(console)
    ]
    raw_value = raw_values[-1] if raw_values else None
    raw_parsed = (
        raw_value in {"true", "yes"} if raw_value is not None else None
    )
    checkpoint_decision = bool(feedback.decision)
    scan = secret_scan(output_dir)
    write_json(output_dir / "secret_scan.json", scan)
    manifest = {
        "status": (
            "model_smoke_passed"
            if trace["complete_loop_count"] == 1
            and len(state.plan.get("features", {})) == 20
            and len(tasks) == 1
            and bool(model_code)
            and raw_parsed == checkpoint_decision
            and scan["passed"]
            else "model_smoke_failed"
        ),
        "base_feature_count": len(state.plan.get("features", {})),
        "task_count": len(tasks),
        "model_name": getattr(tasks[0], "name", None) if tasks else None,
        "model_type": getattr(tasks[0], "model_type", None) if tasks else None,
        "model_code_present": bool(model_code),
        "result_present": experiment.result is not None,
        "five_step_checkpoint_complete": trace["complete_loop_count"] == 1,
        "llm_raw_decision_value": raw_value,
        "llm_raw_decision_parsed": raw_parsed,
        "checkpoint_decision": checkpoint_decision,
        "decision_reconciled": raw_parsed == checkpoint_decision,
        "feedback_prompt_route": "model_feedback_generation.system",
        "dual_schema_parser_required": True,
        "secret_scan_hits": scan["hit_count"],
        "historical_test_read": False,
    }
    write_json(output_dir / "smoke_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    if manifest["status"] != "model_smoke_passed":
        raise RuntimeError("23K model smoke gate failed")


if __name__ == "__main__":
    main()
