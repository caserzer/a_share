#!/usr/bin/env python3
"""Convert an RD-Agent factor trace into auditable EP23 tabular artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
TOKEN_RE = re.compile(r"Token count:\s*(\d+)")
RAW_REPLACE_DECISION_RE = re.compile(
    r'"Replace Best Result"\s*:\s*"(?P<value>yes|no)"',
    flags=re.IGNORECASE,
)
RAW_FALLBACK_DECISION_RE = re.compile(
    r'"Decision"\s*:\s*(?P<value>true|false|"yes"|"no"|"true"|"false")',
    flags=re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return cleaned or "unnamed"


def json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return str(value)


def metrics_dict(experiment: Any) -> dict[str, Any]:
    result = getattr(experiment, "result", None)
    if result is None:
        return {}
    if hasattr(result, "to_dict"):
        return {str(key): json_value(value) for key, value in result.to_dict().items()}
    if isinstance(result, dict):
        return {str(key): json_value(value) for key, value in result.items()}
    return {"raw_result": str(result)}


def last_baseline_metrics(experiment: Any) -> dict[str, Any]:
    based = getattr(experiment, "based_experiments", None) or []
    for candidate in reversed(based):
        result = metrics_dict(candidate)
        if result:
            return result
    return {}


def frame_inventory(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "result_h5_exists": False,
            "result_rows": 0,
            "result_date_start": None,
            "result_date_end": None,
            "result_columns": [],
            "result_h5_sha256": None,
        }
    frame = pd.read_hdf(path, key="data")
    dates = pd.to_datetime(frame.index.get_level_values("datetime"))
    return {
        "result_h5_exists": True,
        "result_rows": int(len(frame)),
        "result_date_start": dates.min().date().isoformat(),
        "result_date_end": dates.max().date().isoformat(),
        "result_columns": [str(column) for column in frame.columns],
        "result_h5_sha256": sha256_file(path),
    }


def read_checkpoint(path: Path, rdagent_path: Path) -> Any:
    os.environ.setdefault(
        "LOG_TRACE_PATH",
        str(Path("/tmp") / f"ep23_trace_reader_{os.getpid()}"),
    )
    sys.path.insert(0, str(rdagent_path))
    with path.open("rb") as handle:
        return pickle.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--branch", required=True, choices=["a20", "a157"])
    args = parser.parse_args()

    config_path = args.config.resolve()
    episode_root = config_path.parent
    phase2 = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    output_key = "factor_a20" if args.branch == "a20" else "factor_a158"
    output_dir = episode_root / phase2["outputs"][output_key]
    trace_path = output_dir / "raw_rdagent_trace"
    rdagent_path = Path(phase2["runtime"]["rdagent_checkout"]).resolve()
    session_path = trace_path / "__session__"
    if not session_path.is_dir():
        raise FileNotFoundError(f"missing RD-Agent session: {session_path}")

    record_paths = sorted(
        session_path.glob("*/*_record"),
        key=lambda path: int(path.parent.name),
    )
    if not record_paths:
        raise RuntimeError("no completed RD-Agent record checkpoints")

    code_root = output_dir / "candidate_code"
    code_root.mkdir(parents=True, exist_ok=True)
    retained_root = output_dir / "retained_library"
    retained_root.mkdir(parents=True, exist_ok=True)

    loop_rows: list[dict[str, Any]] = []
    hypothesis_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    feedback_rows: list[dict[str, Any]] = []
    attempt_rows: list[dict[str, Any]] = []
    final_state: Any = None

    for record_path in record_paths:
        loop_index = int(record_path.parent.name)
        state = read_checkpoint(record_path, rdagent_path)
        final_state = state
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
        start_mtime = min(
            path.stat().st_mtime
            for path in record_path.parent.iterdir()
            if path.is_file()
        )
        end_mtime = max(
            path.stat().st_mtime
            for path in record_path.parent.iterdir()
            if path.is_file()
        )
        tasks = list(getattr(experiment, "sub_tasks", None) or [])
        workspaces = list(getattr(experiment, "sub_workspace_list", None) or [])
        implementation_true = sum(
            bool(getattr(task, "factor_implementation", False)) for task in tasks
        )
        loop_rows.append(
            {
                "branch": args.branch,
                "loop_index": loop_index,
                "trace_index": trace_index,
                "decision": decision,
                "task_count": len(tasks),
                "implemented_task_count": implementation_true,
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
                "current_rank_ic": result.get("Rank IC"),
                "current_net_arr": result.get(
                    "1day.excess_return_with_cost.annualized_return"
                ),
                "current_max_drawdown": result.get(
                    "1day.excess_return_with_cost.max_drawdown"
                ),
                "baseline_ic": baseline.get("IC"),
                "baseline_rank_ic": baseline.get("Rank IC"),
                "baseline_net_arr": baseline.get(
                    "1day.excess_return_with_cost.annualized_return"
                ),
                "baseline_max_drawdown": baseline.get(
                    "1day.excess_return_with_cost.max_drawdown"
                ),
            }
        )
        hypothesis = getattr(experiment, "hypothesis", None)
        hypothesis_rows.append(
            {
                "branch": args.branch,
                "loop_index": loop_index,
                "hypothesis": getattr(hypothesis, "hypothesis", None),
                "reason": getattr(hypothesis, "reason", None),
                "decision": decision,
                "factor_names": [getattr(task, "factor_name", None) for task in tasks],
            }
        )
        feedback_rows.append(
            {
                "branch": args.branch,
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

        attempt_count = len(
            list(trace_path.glob(f"Loop_{loop_index}/coding/evo_loop_*"))
        )
        attempt_rows.append(
            {
                "branch": args.branch,
                "loop_index": loop_index,
                "observed_coding_evo_loop_directories": attempt_count,
                "task_count": len(tasks),
                "implemented_task_count": implementation_true,
                "decision": decision,
            }
        )

        workspace_by_name = {
            str(getattr(getattr(workspace, "target_task", None), "factor_name", "")): workspace
            for workspace in workspaces
        }
        for task in tasks:
            factor_name = str(getattr(task, "factor_name", "unnamed"))
            workspace = workspace_by_name.get(factor_name)
            file_dict = dict(getattr(workspace, "file_dict", {}) or {})
            factor_code = str(file_dict.get("factor.py", ""))
            factor_dir = code_root / f"loop_{loop_index:04d}" / safe_name(factor_name)
            factor_dir.mkdir(parents=True, exist_ok=True)
            code_path = factor_dir / "factor.py"
            code_path.write_text(factor_code, encoding="utf-8")
            workspace_path = Path(str(getattr(workspace, "workspace_path", "")))
            result_path = workspace_path / "result.h5"
            inventory = frame_inventory(result_path)
            try:
                result_h5_path = str(result_path.relative_to(output_dir))
            except ValueError:
                result_h5_path = str(result_path)
            candidate_rows.append(
                {
                    "branch": args.branch,
                    "loop_index": loop_index,
                    "decision": decision,
                    "factor_name": factor_name,
                    "description": getattr(task, "description", None),
                    "formulation": getattr(task, "factor_formulation", None),
                    "variables_json": json.dumps(
                        getattr(task, "variables", None),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "factor_implementation": bool(
                        getattr(task, "factor_implementation", False)
                    ),
                    "code_sha256": sha256_bytes(factor_code.encode("utf-8")),
                    "code_path": str(code_path.relative_to(output_dir)),
                    "source_workspace": str(workspace_path),
                    "result_h5_path": result_h5_path,
                    **inventory,
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
    with (output_dir / "hypothesis_trace.jsonl").open("w", encoding="utf-8") as handle:
        for row in hypothesis_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with (output_dir / "feedback_metrics.jsonl").open("w", encoding="utf-8") as handle:
        for row in feedback_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    pd.DataFrame(
        [
            {
                "branch": row["branch"],
                "loop_index": row["loop_index"],
                "decision": row["decision"],
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

    final_trace = final_state.trace
    accepted_indices = [
        index
        for index, (_, feedback) in enumerate(final_trace.hist)
        if bool(getattr(feedback, "decision", False))
    ]
    accepted_factors = [
        row for row in candidate_rows if row["decision"]
    ]
    base_features = dict(getattr(final_state, "plan", {}).get("features", {}))
    (retained_root / "base_factors.json").write_text(
        json.dumps(base_features, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for row in accepted_factors:
        source = output_dir / row["code_path"]
        destination = retained_root / (
            f"loop_{int(row['loop_index']):04d}_{safe_name(row['factor_name'])}.py"
        )
        shutil.copy2(source, destination)
    retained_manifest = {
        "generated_at_utc": utc_now(),
        "branch": args.branch,
        "base_expression_feature_count": len(base_features),
        "accepted_trace_indices": accepted_indices,
        "accepted_loop_count": len(accepted_indices),
        "accepted_factor_count": len(accepted_factors),
        "accepted_factors": [
            {
                key: row[key]
                for key in (
                    "loop_index",
                    "factor_name",
                    "formulation",
                    "code_sha256",
                    "code_path",
                    "result_h5_path",
                    "result_h5_sha256",
                )
            }
            for row in accepted_factors
        ],
        "rdagent_loader_path": str(retained_root),
    }
    (output_dir / "retained_library.json").write_text(
        json.dumps(retained_manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    console_path = output_dir / "console.log"
    console = (
        ANSI_RE.sub("", console_path.read_text(encoding="utf-8", errors="replace"))
        if console_path.exists()
        else ""
    )
    replace_decisions = [
        match.group("value").lower()
        for match in RAW_REPLACE_DECISION_RE.finditer(console)
    ]
    fallback_decisions = [
        match.group("value").strip('"').lower()
        for match in RAW_FALLBACK_DECISION_RE.finditer(console)
    ]
    # Formal factor prompts contain a non-matching "yes or no" example, so exact
    # yes/no matches correspond to actual responses.  If a provider ever falls
    # back to the model-style Decision field, use that stream instead.
    raw_decisions = (
        replace_decisions[-len(feedback_rows) :]
        if len(replace_decisions) >= len(feedback_rows)
        else fallback_decisions[-len(feedback_rows) :]
    )
    for index, row in enumerate(feedback_rows):
        raw_value = raw_decisions[index] if index < len(raw_decisions) else None
        parsed_value = raw_value in {"yes", "true"} if raw_value is not None else None
        row["llm_raw_decision_value"] = raw_value
        row["llm_raw_decision_parsed"] = parsed_value
        row["checkpoint_decision"] = bool(row["decision"])
        row["decision_reconciled"] = (
            parsed_value == bool(row["decision"])
            if parsed_value is not None
            else False
        )
    input_token_estimates = [int(value) for value in TOKEN_RE.findall(console)]
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
    # Rewrite after enriching rows with the raw-vs-checkpoint decision evidence.
    with (output_dir / "feedback_metrics.jsonl").open("w", encoding="utf-8") as handle:
        for row in feedback_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
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
    search_accounting = pd.DataFrame(
        [
            {
                "branch": args.branch,
                "completed_loops": len(loop_frame),
                "valid_result_loops": int(loop_frame["current_ic"].notna().sum()),
                "accepted_loops": int(loop_frame["decision"].sum()),
                "rejected_loops": int((~loop_frame["decision"]).sum()),
                "generated_factors": len(candidate_rows),
                "implemented_factors": int(
                    sum(row["factor_implementation"] for row in candidate_rows)
                ),
                "accepted_factors": len(accepted_factors),
                "checkpoint_complete_loops": int(
                    loop_frame["five_step_checkpoint_complete"].sum()
                ),
                "decision_reconciled_loops": int(
                    sum(bool(row["decision_reconciled"]) for row in feedback_rows)
                ),
                "logged_prompt_token_events": len(input_token_estimates),
                "logged_prompt_tokens_sum": sum(input_token_estimates),
                "output_tokens_available": False,
                "provider_cost_source": "OpenRouter key usage delta in run_manifest",
            }
        ]
    )
    search_accounting.to_csv(output_dir / "search_accounting.csv", index=False)
    print(json.dumps(search_accounting.iloc[0].to_dict(), indent=2))


if __name__ == "__main__":
    main()
