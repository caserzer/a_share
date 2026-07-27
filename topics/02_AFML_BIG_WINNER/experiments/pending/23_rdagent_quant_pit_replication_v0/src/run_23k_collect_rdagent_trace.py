#!/usr/bin/env python3
"""Convert a formal RD-Agent model trace into auditable EP23 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from run_23i_collect_rdagent_trace import (
    ANSI_RE,
    TOKEN_RE,
    json_value,
    last_baseline_metrics,
    metrics_dict,
    safe_name,
)


RAW_DECISION_RE = re.compile(
    r'"Decision"\s*:\s*(?P<value>true|false|"yes"|"no"|"true"|"false")',
    flags=re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_checkpoint(path: Path, rdagent_path: Path) -> Any:
    os.environ.setdefault(
        "LOG_TRACE_PATH",
        str(Path("/tmp") / f"ep23_model_trace_reader_{os.getpid()}"),
    )
    sys.path.insert(0, str(rdagent_path))
    with path.open("rb") as handle:
        return pickle.load(handle)


def model_runtime_inventory(task: Any, source: str) -> dict[str, Any]:
    lowered = source.lower()
    architecture_terms = [
        term
        for term in (
            "gru",
            "lstm",
            "transformer",
            "attention",
            "conv1d",
            "linear",
            "dropout",
            "layernorm",
            "batchnorm",
        )
        if term in lowered
    ]
    return {
        "task_name": getattr(task, "name", None),
        "model_type": getattr(task, "model_type", None),
        "architecture_declared": json_value(getattr(task, "architecture", None)),
        "hyperparameters_declared": getattr(task, "hyperparameters", None),
        "training_hyperparameters_declared": getattr(
            task, "training_hyperparameters", None
        ),
        "runtime_runner_contract": {
            "loss": "mse",
            "optimizer": "GeneralPTNN Adam",
            "scheduler": "GeneralPTNN ReduceLROnPlateau",
            "gradient_clip": "GeneralPTNN clip_grad_value_",
            "lookback_if_timeseries": 20,
            "provider_and_segments": "environment manifest and config.resolved.yaml",
        },
        "source_architecture_terms": architecture_terms,
        "source_line_count": len(source.splitlines()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()

    config_path = args.config.resolve()
    episode_root = config_path.parent
    phase2 = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    output_dir = episode_root / phase2["outputs"]["model_a20"]
    trace_path = output_dir / "raw_rdagent_trace"
    session_path = trace_path / "__session__"
    rdagent_path = Path(phase2["runtime"]["rdagent_checkout"]).resolve()
    if not session_path.is_dir():
        raise FileNotFoundError(f"missing model session: {session_path}")
    record_paths = sorted(
        session_path.glob("*/*_record"),
        key=lambda path: int(path.parent.name),
    )
    if not record_paths:
        raise RuntimeError("no completed model record checkpoint")

    code_root = output_dir / "model_code"
    code_root.mkdir(parents=True, exist_ok=True)
    loop_rows: list[dict[str, Any]] = []
    hypothesis_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    runtime_rows: list[dict[str, Any]] = []
    feedback_rows: list[dict[str, Any]] = []
    attempt_rows: list[dict[str, Any]] = []

    for record_path in record_paths:
        loop_index = int(record_path.parent.name)
        state = read_checkpoint(record_path, rdagent_path)
        trace = state.trace
        trace_index = next(
            (
                index
                for index, mapped_loop in trace.idx2loop_id.items()
                if int(mapped_loop) == loop_index
            ),
            len(trace.hist) - 1,
        )
        experiment, feedback = trace.hist[trace_index]
        decision = bool(getattr(feedback, "decision", False))
        result = metrics_dict(experiment)
        baseline = last_baseline_metrics(experiment)
        checkpoint_files = sorted(
            path.name for path in record_path.parent.iterdir() if path.is_file()
        )
        checkpoint_mtimes = [
            path.stat().st_mtime
            for path in record_path.parent.iterdir()
            if path.is_file()
        ]
        tasks = list(getattr(experiment, "sub_tasks", None) or [])
        workspaces = list(getattr(experiment, "sub_workspace_list", None) or [])
        start_mtime = min(checkpoint_mtimes)
        end_mtime = max(checkpoint_mtimes)
        loop_rows.append(
            {
                "branch": "a20_model",
                "loop_index": loop_index,
                "trace_index": trace_index,
                "decision": decision,
                "task_count": len(tasks),
                "checkpoint_count": len(checkpoint_files),
                "five_step_checkpoint_complete": (
                    len(checkpoint_files) >= 5
                    and any(name.endswith("_record") for name in checkpoint_files)
                ),
                "started_at_utc": datetime.fromtimestamp(
                    start_mtime, timezone.utc
                ).isoformat(),
                "ended_at_utc": datetime.fromtimestamp(
                    end_mtime, timezone.utc
                ).isoformat(),
                "wall_seconds": end_mtime - start_mtime,
                "current_ic": result.get("IC"),
                "current_icir": result.get("ICIR"),
                "current_rank_ic": result.get("Rank IC"),
                "current_rank_icir": result.get("Rank ICIR"),
                "current_net_arr": result.get(
                    "1day.excess_return_with_cost.annualized_return"
                ),
                "current_ir": result.get(
                    "1day.excess_return_with_cost.information_ratio"
                ),
                "current_max_drawdown": result.get(
                    "1day.excess_return_with_cost.max_drawdown"
                ),
                "baseline_ic": baseline.get("IC"),
                "baseline_rank_ic": baseline.get("Rank IC"),
                "baseline_net_arr": baseline.get(
                    "1day.excess_return_with_cost.annualized_return"
                ),
            }
        )
        hypothesis = getattr(experiment, "hypothesis", None)
        hypothesis_rows.append(
            {
                "branch": "a20_model",
                "loop_index": loop_index,
                "hypothesis": getattr(hypothesis, "hypothesis", None),
                "reason": getattr(hypothesis, "reason", None),
                "decision": decision,
                "model_names": [
                    getattr(task, "name", None) for task in tasks
                ],
            }
        )
        feedback_rows.append(
            {
                "branch": "a20_model",
                "loop_index": loop_index,
                "decision": decision,
                "observations": getattr(feedback, "observations", None),
                "hypothesis_evaluation": getattr(
                    feedback, "hypothesis_evaluation", None
                ),
                "new_hypothesis": getattr(feedback, "new_hypothesis", None),
                "reason": getattr(feedback, "reason", None),
                "exception": str(getattr(feedback, "exception", "") or ""),
                "current_metrics": result,
                "baseline_metrics": baseline,
            }
        )
        attempt_rows.append(
            {
                "branch": "a20_model",
                "loop_index": loop_index,
                "observed_coding_evo_loop_directories": len(
                    list(trace_path.glob(f"Loop_{loop_index}/coding/evo_loop_*"))
                ),
                "task_count": len(tasks),
                "model_code_present": bool(
                    workspaces
                    and dict(getattr(workspaces[0], "file_dict", {}) or {}).get(
                        "model.py"
                    )
                ),
                "decision": decision,
            }
        )
        for task_position, task in enumerate(tasks):
            workspace = (
                workspaces[task_position]
                if task_position < len(workspaces)
                else None
            )
            source = str(
                dict(getattr(workspace, "file_dict", {}) or {}).get(
                    "model.py", ""
                )
            )
            model_name = str(getattr(task, "name", f"model_{task_position}"))
            model_dir = (
                code_root / f"loop_{loop_index:04d}" / safe_name(model_name)
            )
            model_dir.mkdir(parents=True, exist_ok=True)
            code_path = model_dir / "model.py"
            code_path.write_text(source, encoding="utf-8")
            runtime = model_runtime_inventory(task, source)
            runtime.update(
                {
                    "loop_index": loop_index,
                    "decision": decision,
                    "code_sha256": sha256_bytes(source.encode("utf-8")),
                    "code_path": str(code_path.relative_to(output_dir)),
                }
            )
            runtime_rows.append(runtime)
            candidate_rows.append(
                {
                    "branch": "a20_model",
                    "loop_index": loop_index,
                    "decision": decision,
                    "model_name": model_name,
                    "model_type": getattr(task, "model_type", None),
                    "description": getattr(task, "description", None),
                    "formulation": getattr(task, "formulation", None),
                    "architecture_json": json.dumps(
                        getattr(task, "architecture", None),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "hyperparameters_json": json.dumps(
                        getattr(task, "hyperparameters", None),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "training_hyperparameters_json": json.dumps(
                        getattr(task, "training_hyperparameters", None),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "code_present": bool(source),
                    "code_sha256": runtime["code_sha256"],
                    "code_path": runtime["code_path"],
                    "source_workspace": str(
                        getattr(workspace, "workspace_path", "")
                    ),
                }
            )

    loop_frame = pd.DataFrame(loop_rows).sort_values("loop_index")
    loop_frame.to_csv(output_dir / "loop_trace.csv", index=False)
    pd.DataFrame(candidate_rows).to_csv(
        output_dir / "candidate_inventory.csv", index=False
    )
    pd.DataFrame(attempt_rows).to_csv(
        output_dir / "implementation_attempts.csv", index=False
    )
    with (output_dir / "hypothesis_trace.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in hypothesis_rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            )
    with (output_dir / "actual_runtime_configs.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in runtime_rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            )

    console_path = output_dir / "console.log"
    console = (
        ANSI_RE.sub(
            "",
            console_path.read_text(encoding="utf-8", errors="replace"),
        )
        if console_path.exists()
        else ""
    )
    raw_values = [
        match.group("value").strip('"').lower()
        for match in RAW_DECISION_RE.finditer(console)
    ]
    raw_values = raw_values[-len(feedback_rows) :]
    for index, row in enumerate(feedback_rows):
        raw_value = raw_values[index] if index < len(raw_values) else None
        raw_parsed = (
            raw_value in {"true", "yes"} if raw_value is not None else None
        )
        row["llm_raw_decision_value"] = raw_value
        row["llm_raw_decision_parsed"] = raw_parsed
        row["checkpoint_decision"] = bool(row["decision"])
        row["decision_reconciled"] = (
            raw_parsed == bool(row["decision"])
            if raw_parsed is not None
            else False
        )
    with (output_dir / "feedback_metrics.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in feedback_rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            )
    pd.DataFrame(
        [
            {
                "branch": row["branch"],
                "loop_index": row["loop_index"],
                "decision": row["decision"],
                "llm_raw_decision_value": row["llm_raw_decision_value"],
                "llm_raw_decision_parsed": row["llm_raw_decision_parsed"],
                "checkpoint_decision": row["checkpoint_decision"],
                "decision_reconciled": row["decision_reconciled"],
                "observations": row["observations"],
                "hypothesis_evaluation": row["hypothesis_evaluation"],
                "new_hypothesis": row["new_hypothesis"],
                "reason": row["reason"],
                "exception": row["exception"],
                "current_ic": row["current_metrics"].get("IC"),
                "current_rank_ic": row["current_metrics"].get("Rank IC"),
                "current_net_arr": row["current_metrics"].get(
                    "1day.excess_return_with_cost.annualized_return"
                ),
                "baseline_ic": row["baseline_metrics"].get("IC"),
                "baseline_rank_ic": row["baseline_metrics"].get("Rank IC"),
                "baseline_net_arr": row["baseline_metrics"].get(
                    "1day.excess_return_with_cost.annualized_return"
                ),
            }
            for row in feedback_rows
        ]
    ).to_csv(output_dir / "feedback_metrics.csv", index=False)
    pd.DataFrame(
        [
            {
                "branch": row["branch"],
                "loop_index": row["loop_index"],
                "llm_raw_decision_value": row["llm_raw_decision_value"],
                "llm_raw_decision_parsed": row["llm_raw_decision_parsed"],
                "checkpoint_decision": row["checkpoint_decision"],
                "decision_reconciled": row["decision_reconciled"],
            }
            for row in feedback_rows
        ]
    ).to_csv(output_dir / "decision_reconciliation.csv", index=False)

    tokens = [int(value) for value in TOKEN_RE.findall(console)]
    accounting = {
        "branch": "a20_model",
        "completed_loops": len(loop_frame),
        "valid_result_loops": int(loop_frame["current_ic"].notna().sum()),
        "accepted_loops": int(loop_frame["decision"].sum()),
        "rejected_loops": int((~loop_frame["decision"]).sum()),
        "generated_models": len(candidate_rows),
        "implemented_models": int(
            sum(bool(row["code_present"]) for row in candidate_rows)
        ),
        "accepted_models": int(
            sum(bool(row["decision"]) for row in candidate_rows)
        ),
        "checkpoint_complete_loops": int(
            loop_frame["five_step_checkpoint_complete"].sum()
        ),
        "decision_reconciled_loops": int(
            sum(bool(row["decision_reconciled"]) for row in feedback_rows)
        ),
        "logged_prompt_token_events": len(tokens),
        "logged_prompt_tokens_sum": sum(tokens),
        "provider_cost_source": "OpenRouter key usage delta in run_manifest",
    }
    pd.DataFrame([accounting]).to_csv(
        output_dir / "search_accounting.csv", index=False
    )
    print(json.dumps(accounting, indent=2))


if __name__ == "__main__":
    main()
