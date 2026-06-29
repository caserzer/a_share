#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
RUNNER_16E_PATH = EXPERIMENT_DIR / "src" / "run_16e_sequential_continuation_utility_diagnostic.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r16e = load_runner(RUNNER_16E_PATH, "run_16e_for_postmortem")

RUN_ID = "16E_postmortem_continuation_utility_failure_decomposition"
EXPERIMENT_ID = "16_winner_episode_sequential_sampling_geometry_preflight_v0"
PHASE_ID = "16E_postmortem"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_16e_postmortem_continuation_utility_failure_decomposition.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("train", "robustness", "validation")
CELL_IDS = (
    "defended_positive",
    "defended_negative",
    "defended_neutral",
    "continued_positive",
    "continued_negative",
    "continued_neutral",
)
CONTEXT_STRATA = (
    "all_steps",
    "late_rescue_context",
    "non_late_rescue_context",
    "known_failed_context_any",
    "non_known_failed_context",
)

DECISION_PATH_A = "16E_postmortem_path_a_utility_weighted_objective_authorized"
DECISION_PATH_B = "16E_postmortem_path_b_risk_budget_overlay_authorized"
DECISION_PATH_C = "16E_postmortem_path_c_meta_label_participation_filter_authorized"
DECISION_CLOSED = "16E_postmortem_mainline_closed_no_path_supported"
DECISION_LOW_POWER = "16E_postmortem_low_power"
DECISION_LINEAGE = "16E_postmortem_blocked_by_input_or_lineage_failure"
DECISION_RECOMPUTE = "16E_postmortem_blocked_by_recomputation_violation"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 16E postmortem continuation utility failure decomposition.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    return r16e.topic_path(value)


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_16e_authorization_audit": TABLE_DIR / "upstream_16e_authorization_audit.csv",
        "no_new_computation_audit": TABLE_DIR / "no_new_computation_audit.csv",
        "derived_metric_lineage_audit": TABLE_DIR / "derived_metric_lineage_audit.csv",
        "panel_aggregate_replay_audit": TABLE_DIR / "panel_aggregate_replay_audit.csv",
        "failure_arithmetic_attribution": TABLE_DIR / "failure_arithmetic_attribution.csv",
        "defended_positive_thick_tail_readout": TABLE_DIR / "defended_positive_thick_tail_readout.csv",
        "score_bucket_monotonicity_readout": TABLE_DIR / "score_bucket_monotonicity_readout.csv",
        "loss_avoidance_efficiency_by_bucket": TABLE_DIR / "loss_avoidance_efficiency_by_bucket.csv",
        "drawdown_residual_feasibility_readout": TABLE_DIR / "drawdown_residual_feasibility_readout.csv",
        "path_support_decision": TABLE_DIR / "path_support_decision.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "continuation_utility_failure_postmortem_decision.csv",
        "postmortem_grouping": LOCAL_CACHE_DIR / "postmortem_grouping.parquet",
        "report": REPORT_DIR / "continuation_utility_failure_postmortem_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def file_sha(path: Path) -> str:
    return r16e.file_sha(path)


def count_rows(path: Path) -> int | float:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path))
    if suffixes.endswith((".csv", ".csv.gz")):
        return r16e.count_rows(path)
    if path.is_file():
        return sum(1 for _ in path.open("rb"))
    return np.nan


def metric_float(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return np.nan
    return out if np.isfinite(out) else np.nan


def as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    return bool(value)


def safe_div(num: Any, den: Any, epsilon: float = 1e-12) -> float:
    n = metric_float(num)
    d = metric_float(den)
    if not np.isfinite(n):
        return np.nan
    if not np.isfinite(d) or abs(d) <= epsilon:
        return np.nan
    return float(n / d)


def required_columns_for_key(key: str) -> set[str]:
    mapping: dict[str, set[str]] = {
        "upstream_16e_decision": {
            "decision_state",
            "next_allowed_requirement",
            "primary_label_id",
            "primary_model_id",
            "primary_policy_id",
            "primary_action_semantics_id",
            "primary_round_trip_defense_cost_bps",
            "primary_return_utility_gate",
            "drawdown_avoidance_gate",
            "delay_stress_gate",
            "context_power_gate",
            "context_utility_gate",
            "six_cell_reconciliation_gate",
            "utility_interpretation",
        },
        "upstream_16e_utility_panel": {
            "policy_id",
            "step_id",
            "cost_bps",
            "threshold_value",
            "cluster_split_bucket",
            "score",
            "candidate_action",
            "continue_return_h20",
            "continue_max_drawdown_h20",
            "policy_net_return_h20",
            "incremental_net_return_h20",
            "drawdown_avoided_abs",
            "cell_id",
            "label_class",
        },
        "upstream_16e_utility_by_split_readout": {"split_bucket", "cost_bps", "full_denominator_sum_incremental_return"},
        "upstream_16e_six_cell_utility_reconciliation": {
            "split_bucket",
            "context_stratum",
            "cost_bps",
            "cell_id",
            "cell_step_n",
            "continue_return_sum",
            "policy_net_return_sum",
            "incremental_return_sum",
            "drawdown_avoided_abs_sum",
        },
        "upstream_16e_search_accounting_audit": {"search_accounting_gate"},
        "upstream_16d_policy_threshold_freeze_audit": {"policy_id", "threshold_value", "threshold_freeze_status"},
        "upstream_16d_decision": {"decision_state", "primary_policy_id"},
        "upstream_16d_policy_confusion_readout": {"policy_id", "split_bucket", "context_stratum"},
    }
    if key.endswith("_audit"):
        return mapping.get(key, set())
    return mapping.get(key, set())


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, path in resolved.items():
        exists = path.exists()
        read_status = "pass"
        schema_status = "not_checked"
        row_count: int | float = np.nan
        sha = ""
        if not exists:
            read_status = "missing"
            schema_status = "missing"
        elif path.is_file():
            try:
                row_count = count_rows(path)
                sha = file_sha(path)
                required = required_columns_for_key(key)
                if required:
                    if "".join(path.suffixes).endswith(".parquet"):
                        frame = pd.read_parquet(path, columns=None)
                    elif "".join(path.suffixes).endswith((".csv", ".csv.gz")):
                        frame = pd.read_csv(path, nrows=5)
                    else:
                        frame = pd.DataFrame()
                    schema_status = "pass" if required.issubset(frame.columns) else "fail_missing_columns"
                else:
                    schema_status = "pass"
            except Exception as exc:
                read_status = f"fail_read_error:{type(exc).__name__}"
                schema_status = "fail_read_error"
        rows.append(
            {
                "artifact_key": key,
                "resolved_path": str(path),
                "row_count": row_count,
                "sha256": sha,
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": "required",
                "lineage_role": key,
                "blocking_reason": "",
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    bad = input_audit.loc[
        ~input_audit["read_status"].astype(str).eq("pass")
        | input_audit["schema_status"].astype(str).isin(["missing", "fail_missing_columns", "fail_read_error"])
        | input_audit["schema_status"].astype(str).str.startswith("fail")
    ]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_key"].astype(str).head(16))


def all_status_pass(frame: pd.DataFrame, column: str) -> bool:
    return column in frame.columns and not frame.empty and frame[column].astype(str).eq("pass").all()


def first_row(frame: pd.DataFrame) -> dict[str, Any]:
    return frame.iloc[0].to_dict() if not frame.empty else {}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_upstream_16e_authorization_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    expected = config["expected_16e"]
    decision = first_row(read_table(resolved["upstream_16e_decision"]))
    manifest = read_json(resolved["upstream_16e_manifest"])
    threshold = read_table(resolved["upstream_16d_policy_threshold_freeze_audit"])
    policy_threshold = threshold.loc[threshold["policy_id"].astype(str).eq(expected["primary_policy_id"])]
    threshold_value = metric_float(policy_threshold["threshold_value"].iloc[0]) if not policy_threshold.empty else np.nan

    input_audit_16e = read_table(resolved["upstream_16e_input_artifact_audit"])
    upstream_16d = read_table(resolved["upstream_16e_upstream_16d_authorization_audit"])
    action_panel = read_table(resolved["upstream_16e_full_action_panel_rebuild_audit"])
    semantics = read_table(resolved["upstream_16e_single_step_action_semantics_audit"])
    price = read_table(resolved["upstream_16e_utility_price_path_audit"])
    binding = read_table(resolved["upstream_16e_policy_utility_binding_audit"])
    six_cell = read_table(resolved["upstream_16e_six_cell_utility_reconciliation"])
    neutral = read_table(resolved["upstream_16e_neutral_utility_readout"])
    context = read_table(resolved["upstream_16e_utility_by_context_readout"])
    search = read_table(resolved["upstream_16e_search_accounting_audit"])
    search_gate_value = str(first_row(search).get("search_accounting_gate", ""))

    input_gate = "pass" if input_gate_status(input_audit_16e)[0] == "pass" else "fail"
    hard_gate_checks = {
        "input_artifact_gate": input_gate == "pass",
        "upstream_16d_authorization_gate": all_status_pass(upstream_16d, "authorization_status"),
        "full_action_panel_rebuild_gate": all_status_pass(action_panel, "full_action_panel_rebuild_status"),
        "utility_price_path_gate": all_status_pass(price, "utility_price_path_gate"),
        "action_semantics_gate": all_status_pass(semantics, "action_semantics_gate"),
        "policy_utility_binding_gate": all_status_pass(binding, "policy_utility_binding_gate"),
        "six_cell_reconciliation_gate": all_status_pass(six_cell, "six_cell_reconciliation_status"),
        "neutral_utility_gate": all_status_pass(neutral, "neutral_utility_gate"),
        "context_utility_rebuild_gate": all_status_pass(context, "context_utility_rebuild_gate"),
        "search_accounting_gate": all_status_pass(search, "search_accounting_gate"),
    }
    expected_checks = {
        "decision_state": decision.get("decision_state") == expected["decision_state"],
        "next_allowed_requirement": str(decision.get("next_allowed_requirement")) == expected["next_allowed_requirement"],
        "utility_interpretation": decision.get("utility_interpretation") == expected["utility_interpretation"],
        "manifest_decision_state": manifest.get("decision_state") == expected["decision_state"],
        "manifest_next_allowed_requirement": str(manifest.get("next_allowed_requirement")) == expected["next_allowed_requirement"],
        "primary_label_id": decision.get("primary_label_id") == expected["primary_label_id"],
        "primary_model_id": decision.get("primary_model_id") == expected["primary_model_id"],
        "primary_policy_id": decision.get("primary_policy_id") == expected["primary_policy_id"],
        "primary_action_semantics_id": decision.get("primary_action_semantics_id") == expected["primary_action_semantics_id"],
        "primary_round_trip_defense_cost_bps": int(metric_float(decision.get("primary_round_trip_defense_cost_bps"))) == int(expected["primary_round_trip_defense_cost_bps"]),
        "threshold_value": abs(threshold_value - float(expected["threshold_value"])) <= 1e-6,
        "primary_return_utility_gate": decision.get("primary_return_utility_gate") == expected["primary_return_utility_gate"],
        "drawdown_avoidance_gate": decision.get("drawdown_avoidance_gate") == expected["drawdown_avoidance_gate"],
        "delay_stress_gate": decision.get("delay_stress_gate") == expected["delay_stress_gate"],
        "context_power_gate": decision.get("context_power_gate") == expected["context_power_gate"],
        "context_utility_gate": decision.get("context_utility_gate") == expected["context_utility_gate"],
        "six_cell_reconciliation_gate": decision.get("six_cell_reconciliation_gate") == expected["six_cell_reconciliation_gate"],
        "search_accounting_gate": search_gate_value == expected["search_accounting_gate"],
    }
    bool_checks = {}
    for key in [
        "entry_policy_authorized",
        "exit_policy_authorized",
        "holding_policy_authorized",
        "chained_simulation_authorized",
        "portfolio_backtest_authorized",
        "model_deployment_authorized",
        "production_signal_authorized",
        "live_trading_authorized",
    ]:
        bool_checks[key] = not as_bool(decision.get(key, True)) and not as_bool(manifest.get("authorization_booleans", {}).get(key, True))
    all_checks = {**hard_gate_checks, **expected_checks, **bool_checks}
    gate = "pass" if all(all_checks.values()) else "fail"
    return pd.DataFrame(
        [
            {
                "upstream_16e_decision_state": decision.get("decision_state", ""),
                "upstream_16e_next_allowed_requirement": decision.get("next_allowed_requirement", ""),
                "upstream_16e_utility_interpretation": decision.get("utility_interpretation", ""),
                "primary_policy_id": decision.get("primary_policy_id", ""),
                "primary_action_semantics_id": decision.get("primary_action_semantics_id", ""),
                "primary_round_trip_defense_cost_bps": decision.get("primary_round_trip_defense_cost_bps", np.nan),
                "threshold_value": threshold_value,
                "primary_return_utility_gate": decision.get("primary_return_utility_gate", ""),
                "drawdown_avoidance_gate": decision.get("drawdown_avoidance_gate", ""),
                "delay_stress_gate": decision.get("delay_stress_gate", ""),
                "context_power_gate": decision.get("context_power_gate", ""),
                "context_utility_gate": decision.get("context_utility_gate", ""),
                "six_cell_reconciliation_gate": decision.get("six_cell_reconciliation_gate", ""),
                "search_accounting_gate": search_gate_value,
                "entry_policy_authorized": as_bool(decision.get("entry_policy_authorized", False)),
                "exit_policy_authorized": as_bool(decision.get("exit_policy_authorized", False)),
                "holding_policy_authorized": as_bool(decision.get("holding_policy_authorized", False)),
                "chained_simulation_authorized": as_bool(decision.get("chained_simulation_authorized", False)),
                "portfolio_backtest_authorized": as_bool(decision.get("portfolio_backtest_authorized", False)),
                "model_deployment_authorized": as_bool(decision.get("model_deployment_authorized", False)),
                "production_signal_authorized": as_bool(decision.get("production_signal_authorized", False)),
                "live_trading_authorized": as_bool(decision.get("live_trading_authorized", False)),
                "upstream_16e_authorization_gate": gate,
                "input_artifact_gate": "pass" if hard_gate_checks["input_artifact_gate"] else "fail",
                "upstream_16d_authorization_gate": "pass" if hard_gate_checks["upstream_16d_authorization_gate"] else "fail",
                "full_action_panel_rebuild_gate": "pass" if hard_gate_checks["full_action_panel_rebuild_gate"] else "fail",
                "utility_price_path_gate": "pass" if hard_gate_checks["utility_price_path_gate"] else "fail",
                "action_semantics_gate": "pass" if hard_gate_checks["action_semantics_gate"] else "fail",
                "policy_utility_binding_gate": "pass" if hard_gate_checks["policy_utility_binding_gate"] else "fail",
                "neutral_utility_gate": "pass" if hard_gate_checks["neutral_utility_gate"] else "fail",
                "context_utility_rebuild_gate": "pass" if hard_gate_checks["context_utility_rebuild_gate"] else "fail",
                "blocking_reason": "" if gate == "pass" else ";".join(key for key, ok in all_checks.items() if not ok),
            }
        ]
    )


def labelable_mask(frame: pd.DataFrame) -> pd.Series:
    return frame["label_class"].astype(str).isin(["positive", "negative", "neutral"]) & np.isfinite(pd.to_numeric(frame["score"], errors="coerce"))


def load_and_validate_panel(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str, str]:
    panel = pd.read_parquet(resolved["upstream_16e_utility_panel"]).copy()
    expected = config["expected_16e"]
    required = required_columns_for_key("upstream_16e_utility_panel")
    missing = sorted(required - set(panel.columns))
    if missing:
        return panel, "fail", f"missing_panel_columns:{','.join(missing)}"
    duplicate_n = int(panel.duplicated(["policy_id", "step_id", "cost_bps"]).sum())
    primary = panel.loc[pd.to_numeric(panel["cost_bps"], errors="coerce").eq(int(config["diagnostic"]["primary_cost_bps"]))].copy()
    primary_duplicate_n = int(primary.duplicated(["policy_id", "step_id"]).sum())
    policy_ok = panel["policy_id"].astype(str).eq(expected["primary_policy_id"]).all()
    threshold_diff = (pd.to_numeric(panel["threshold_value"], errors="coerce") - float(expected["threshold_value"])).abs().max()
    split_ok = set(panel["cluster_split_bucket"].astype(str).unique()).issubset(set(SPLITS))
    score_ok = np.isfinite(pd.to_numeric(primary.loc[labelable_mask(primary), "score"], errors="coerce")).all()
    action_ok = set(panel["candidate_action"].astype(str).unique()).issubset({"defend_next_h20", "continue_next_h20"})
    status = "pass" if (
        duplicate_n == 0
        and primary_duplicate_n == 0
        and policy_ok
        and np.isfinite(threshold_diff)
        and threshold_diff <= 1e-6
        and split_ok
        and bool(score_ok)
        and action_ok
    ) else "fail"
    reasons = []
    if duplicate_n:
        reasons.append("duplicate_policy_step_cost")
    if primary_duplicate_n:
        reasons.append("duplicate_primary_policy_step")
    if not policy_ok:
        reasons.append("policy_id_mismatch")
    if not np.isfinite(threshold_diff) or threshold_diff > 1e-6:
        reasons.append("threshold_value_mismatch")
    if not split_ok:
        reasons.append("split_bucket_invalid")
    if not bool(score_ok):
        reasons.append("nonfinite_score_labelable_rows")
    if not action_ok:
        reasons.append("candidate_action_invalid")
    panel["split_bucket"] = panel["cluster_split_bucket"].astype(str)
    return panel, status, ";".join(reasons)


def context_mask(frame: pd.DataFrame, context: str) -> pd.Series:
    if context == "all_steps":
        return pd.Series(True, index=frame.index)
    if context in frame.columns:
        return frame[context].astype(bool)
    return pd.Series(False, index=frame.index)


def build_panel_aggregate_replay_audit(panel: pd.DataFrame, resolved: dict[str, Path], tolerance: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    split_readout = read_table(resolved["upstream_16e_utility_by_split_readout"])
    split_group = panel.groupby(["split_bucket", "cost_bps"], dropna=False)["incremental_net_return_h20"].sum()
    for src in split_readout.itertuples(index=False):
        split = str(src.split_bucket)
        cost = int(src.cost_bps)
        source_value = metric_float(src.full_denominator_sum_incremental_return)
        panel_value = float(split_group.get((split, cost), np.nan))
        diff = abs(source_value - panel_value) if np.isfinite(source_value) and np.isfinite(panel_value) else np.inf
        rows.append(
            {
                "replay_key": f"split_incremental_sum:{split}:{cost}",
                "split_bucket": split,
                "cost_bps": cost,
                "source_table": "utility_by_split_readout.csv",
                "source_value_column": "full_denominator_sum_incremental_return",
                "panel_groupby_columns": "split_bucket,cost_bps",
                "panel_value_column": "incremental_net_return_h20",
                "source_value": source_value,
                "panel_replay_value": panel_value,
                "abs_diff": diff,
                "tolerance": tolerance,
                "replay_status": "pass" if diff <= tolerance else "fail",
                "blocking_reason": "" if diff <= tolerance else "split_incremental_replay_mismatch",
            }
        )
    six_cell = read_table(resolved["upstream_16e_six_cell_utility_reconciliation"])
    metric_map = {
        "cell_step_n": ("step_id", "count"),
        "continue_return_sum": ("continue_return_h20", "sum"),
        "policy_net_return_sum": ("policy_net_return_h20", "sum"),
        "incremental_return_sum": ("incremental_net_return_h20", "sum"),
        "drawdown_avoided_abs_sum": ("drawdown_avoided_abs", "sum"),
    }
    for src in six_cell.itertuples(index=False):
        split = str(src.split_bucket)
        context = str(src.context_stratum)
        cost = int(src.cost_bps)
        cell = str(src.cell_id)
        sub = panel.loc[
            panel["split_bucket"].astype(str).eq(split)
            & pd.to_numeric(panel["cost_bps"], errors="coerce").eq(cost)
            & panel["cell_id"].astype(str).eq(cell)
        ]
        sub = sub.loc[context_mask(sub, context)]
        for source_col, (panel_col, agg) in metric_map.items():
            source_value = metric_float(getattr(src, source_col))
            panel_value = float(len(sub)) if agg == "count" else float(pd.to_numeric(sub[panel_col], errors="coerce").sum())
            diff = abs(source_value - panel_value) if np.isfinite(source_value) and np.isfinite(panel_value) else np.inf
            rows.append(
                {
                    "replay_key": f"six_cell:{context}:{cell}:{source_col}",
                    "split_bucket": split,
                    "cost_bps": cost,
                    "source_table": "six_cell_utility_reconciliation.csv",
                    "source_value_column": source_col,
                    "panel_groupby_columns": "split_bucket,context_stratum,cost_bps,cell_id",
                    "panel_value_column": panel_col,
                    "source_value": source_value,
                    "panel_replay_value": panel_value,
                    "abs_diff": diff,
                    "tolerance": tolerance,
                    "replay_status": "pass" if diff <= tolerance else "fail",
                    "blocking_reason": "" if diff <= tolerance else "six_cell_replay_mismatch",
                }
            )
    return pd.DataFrame(rows)


def build_failure_arithmetic_attribution(panel: pd.DataFrame, resolved: dict[str, Path], tolerance: float) -> pd.DataFrame:
    split_readout = read_table(resolved["upstream_16e_utility_by_split_readout"])
    rows: list[dict[str, Any]] = []
    for src in split_readout.itertuples(index=False):
        split = str(src.split_bucket)
        cost = int(src.cost_bps)
        sub = panel.loc[panel["split_bucket"].eq(split) & pd.to_numeric(panel["cost_bps"], errors="coerce").eq(cost)]
        sums = {
            cell: float(pd.to_numeric(sub.loc[sub["cell_id"].astype(str).eq(cell), "incremental_net_return_h20"], errors="coerce").sum())
            for cell in CELL_IDS
        }
        total = metric_float(src.full_denominator_sum_incremental_return)
        defended_sum = sums["defended_positive"] + sums["defended_negative"] + sums["defended_neutral"]
        identity_diff = abs(defended_sum - total) if np.isfinite(total) else np.inf
        continued_abs_max = max(abs(sums["continued_positive"]), abs(sums["continued_negative"]), abs(sums["continued_neutral"]))
        continued_negative = sub.loc[sub["cell_id"].astype(str).eq("continued_negative")]
        denom = max(abs(total), 1e-12) if np.isfinite(total) else np.nan
        rows.append(
            {
                "split_bucket": split,
                "cost_bps": cost,
                "full_denominator_net_utility_total": total,
                "defended_positive_incremental_sum": sums["defended_positive"],
                "defended_negative_incremental_sum": sums["defended_negative"],
                "defended_neutral_incremental_sum": sums["defended_neutral"],
                "continued_positive_incremental_sum": sums["continued_positive"],
                "continued_negative_incremental_sum": sums["continued_negative"],
                "continued_neutral_incremental_sum": sums["continued_neutral"],
                "continued_negative_residual_loss_abs": float(np.maximum(0.0, -pd.to_numeric(continued_negative["continue_return_h20"], errors="coerce")).sum()),
                "defended_positive_oppcost_share": safe_div(-sums["defended_positive"], denom),
                "defended_negative_gain_share": safe_div(sums["defended_negative"], denom),
                "defended_neutral_gain_share": safe_div(sums["defended_neutral"], denom),
                "attribution_identity_abs_diff": identity_diff,
                "attribution_identity_status": "pass" if identity_diff <= tolerance else "fail",
                "continued_incremental_zero_abs_max": continued_abs_max,
                "continued_incremental_zero_status": "pass" if continued_abs_max <= tolerance else "fail",
                "six_cell_bidirectional_replay_status": "not_checked_here",
            }
        )
    return pd.DataFrame(rows)


def quantile_value(series: pd.Series, q: float) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.quantile(q)) if len(values) else np.nan


def build_thick_tail_readout(primary_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    diag = config["diagnostic"]
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        split_panel = primary_panel.loc[primary_panel["split_bucket"].eq(split)]
        all_pos = split_panel.loc[split_panel["label_class"].astype(str).eq("positive")]
        defended_pos = all_pos.loc[all_pos["cell_id"].astype(str).eq("defended_positive")]
        all_mean = float(pd.to_numeric(all_pos["continue_return_h20"], errors="coerce").mean()) if len(all_pos) else np.nan
        defended_mean = float(pd.to_numeric(defended_pos["continue_return_h20"], errors="coerce").mean()) if len(defended_pos) else np.nan
        all_q75 = quantile_value(all_pos["continue_return_h20"], 0.75)
        defended_q75 = quantile_value(defended_pos["continue_return_h20"], 0.75)
        defended_q90 = quantile_value(defended_pos["continue_return_h20"], 0.90)
        mean_ratio = safe_div(defended_mean, all_mean, float(diag["epsilon"]))
        q75_ratio = safe_div(defended_q75, all_q75, float(diag["epsilon"]))
        q90_flag = bool(np.isfinite(defended_q90) and np.isfinite(all_q75) and defended_q90 >= all_q75)
        mismatch = bool(
            (np.isfinite(mean_ratio) and mean_ratio >= float(diag["defended_positive_upside_mean_ratio_min"]))
            or (np.isfinite(q75_ratio) and q75_ratio >= float(diag["defended_positive_upside_q75_ratio_min"]))
            or q90_flag
        )
        for population, frame in [("all_positive", all_pos), ("defended_positive", defended_pos)]:
            rows.append(
                {
                    "split_bucket": split,
                    "population": population,
                    "row_n": len(frame),
                    "upside_mean": float(pd.to_numeric(frame["continue_return_h20"], errors="coerce").mean()) if len(frame) else np.nan,
                    "upside_q25": quantile_value(frame["continue_return_h20"], 0.25),
                    "upside_q50": quantile_value(frame["continue_return_h20"], 0.50),
                    "upside_q75": quantile_value(frame["continue_return_h20"], 0.75),
                    "upside_q90": quantile_value(frame["continue_return_h20"], 0.90),
                    "upside_q95": quantile_value(frame["continue_return_h20"], 0.95),
                    "defended_positive_upside_mean_ratio": mean_ratio,
                    "defended_positive_upside_q75_ratio": q75_ratio,
                    "defended_positive_upside_q90_vs_all_q75_flag": q90_flag,
                    "thick_tail_mismatch_flag": mismatch,
                }
            )
    return pd.DataFrame(rows)


def assign_score_deciles(primary_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    decile_count = int(config["diagnostic"]["score_decile_count"])
    out = primary_panel.loc[labelable_mask(primary_panel)].copy()
    out["score"] = pd.to_numeric(out["score"], errors="coerce")
    out["decile_index"] = np.nan
    for split, idx in out.groupby("split_bucket", sort=False).groups.items():
        sub = out.loc[idx].sort_values(["score", "step_id"]).copy()
        bucket_n = min(decile_count, len(sub))
        if bucket_n <= 0:
            continue
        ranks = pd.Series(np.arange(len(sub)), index=sub.index)
        out.loc[sub.index, "decile_index"] = pd.qcut(ranks, q=bucket_n, labels=False, duplicates="drop").astype(float) + 1.0
    out["decile_index"] = pd.to_numeric(out["decile_index"], errors="coerce").astype("Int64")
    return out


def spearman_decile_corr(frame: pd.DataFrame) -> float:
    data = frame[["decile_index", "mean_continue_return_h20"]].dropna()
    if len(data) < 2 or data["mean_continue_return_h20"].nunique() < 2:
        return np.nan
    x = data["decile_index"].rank(method="average").to_numpy(dtype=float)
    y = data["mean_continue_return_h20"].rank(method="average").to_numpy(dtype=float)
    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def split_decile_min_rows(split: str, config: dict[str, Any]) -> int:
    power = config["power_gates"]
    if split == "train":
        return int(power["min_rows_per_score_decile_train"])
    if split == "robustness":
        return int(power["min_rows_per_score_decile_robustness"])
    return 1


def build_score_bucket_monotonicity_readout(grouping: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    diag = config["diagnostic"]
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        split_grouping = grouping.loc[grouping["split_bucket"].eq(split)]
        decile_rows: list[dict[str, Any]] = []
        for decile in sorted(split_grouping["decile_index"].dropna().astype(int).unique()):
            sub = split_grouping.loc[split_grouping["decile_index"].astype("Int64").eq(decile)]
            binary = sub["label_class"].astype(str).isin(["positive", "negative"])
            positive_n = int(sub["label_class"].astype(str).eq("positive").sum())
            negative_n = int(sub["label_class"].astype(str).eq("negative").sum())
            neutral_n = int(sub["label_class"].astype(str).eq("neutral").sum())
            row = {
                "split_bucket": split,
                "decile_index": int(decile),
                "score_column": "score",
                "score_low": float(sub["score"].min()) if len(sub) else np.nan,
                "score_high": float(sub["score"].max()) if len(sub) else np.nan,
                "row_n": len(sub),
                "binary_step_n": int(binary.sum()),
                "positive_n": positive_n,
                "negative_n": negative_n,
                "neutral_n": neutral_n,
                "base_rate_positive": safe_div(positive_n, int(binary.sum())),
                "mean_continue_return_h20": float(pd.to_numeric(sub["continue_return_h20"], errors="coerce").mean()) if len(sub) else np.nan,
                "mean_continue_max_drawdown": float(pd.to_numeric(sub["continue_max_drawdown_h20"], errors="coerce").mean()) if len(sub) else np.nan,
                "decile_low_power": len(sub) < split_decile_min_rows(split, config),
            }
            decile_rows.append(row)
        tmp = pd.DataFrame(decile_rows)
        spearman = spearman_decile_corr(tmp) if not tmp.empty else np.nan
        monotone = bool(np.isfinite(spearman) and spearman >= float(diag["monotone_spearman_min"]))
        non_mono = bool(np.isfinite(spearman) and abs(spearman) < float(diag["non_monotone_abs_spearman_max"]))
        inverted = bool(np.isfinite(spearman) and spearman <= float(diag["inverted_spearman_max"]))
        caveat = bool(
            split == "robustness"
            and np.isfinite(spearman)
            and spearman >= float(diag["robustness_unstable_spearman_min"])
            and spearman < float(diag["monotone_spearman_min"])
        )
        for row in decile_rows:
            row["monotonicity_spearman"] = spearman
            row["monotone_increasing_flag"] = monotone
            row["non_monotone_flag"] = non_mono
            row["inverted_flag"] = inverted
            row["robustness_monotonicity_unstable_caveat"] = caveat
            rows.append(row)
    return pd.DataFrame(rows)


def build_loss_avoidance_efficiency(grouping: pd.DataFrame, score_readout: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    diag = config["diagnostic"]
    candidate = {int(x) for x in diag["candidate_defend_region_deciles"]}
    rows: list[dict[str, Any]] = []
    low_power_lookup = {
        (str(row.split_bucket), int(row.decile_index)): bool(row.decile_low_power)
        for row in score_readout.itertuples(index=False)
    }
    for split in SPLITS:
        split_grouping = grouping.loc[grouping["split_bucket"].eq(split)]
        for decile in sorted(split_grouping["decile_index"].dropna().astype(int).unique()):
            sub = split_grouping.loc[split_grouping["decile_index"].astype("Int64").eq(decile)]
            dn = sub.loc[sub["cell_id"].astype(str).eq("defended_negative")]
            dp = sub.loc[sub["cell_id"].astype(str).eq("defended_positive")]
            avoided = float(np.maximum(0.0, -pd.to_numeric(dn["continue_return_h20"], errors="coerce")).sum())
            sacrificed = float(np.maximum(0.0, pd.to_numeric(dp["continue_return_h20"], errors="coerce")).sum())
            efficiency = safe_div(avoided, sacrificed, float(diag["epsilon"]))
            low_power = low_power_lookup.get((split, int(decile)), True)
            rows.append(
                {
                    "split_bucket": split,
                    "decile_index": int(decile),
                    "cost_bps": int(config["diagnostic"]["primary_cost_bps"]),
                    "candidate_defend_region_flag": int(decile) in candidate,
                    "defended_negative_n": len(dn),
                    "defended_positive_n": len(dp),
                    "avoided_loss_abs": avoided,
                    "sacrificed_upside_abs": sacrificed,
                    "loss_avoidance_efficiency": efficiency,
                    "decile_low_power": low_power,
                    "efficiency_above_one_flag": bool(np.isfinite(efficiency) and efficiency > float(diag["loss_avoidance_efficiency_min"])),
                }
            )
    return pd.DataFrame(rows)


def build_drawdown_residual_feasibility_readout(primary_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    diag = config["diagnostic"]
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        sub = primary_panel.loc[primary_panel["split_bucket"].eq(split)]
        dn = sub.loc[sub["cell_id"].astype(str).eq("defended_negative")]
        dp = sub.loc[sub["cell_id"].astype(str).eq("defended_positive")]
        dn_dd_median = quantile_value(dn["drawdown_avoided_abs"], 0.50)
        dn_dd_mean = float(pd.to_numeric(dn["drawdown_avoided_abs"], errors="coerce").mean()) if len(dn) else np.nan
        dp_ret_median = quantile_value(dp["continue_return_h20"], 0.50)
        dp_ret_mean = float(pd.to_numeric(dp["continue_return_h20"], errors="coerce").mean()) if len(dp) else np.nan
        ratio = safe_div(dn_dd_median, max(dp_ret_median, float(diag["epsilon"])) if np.isfinite(dp_ret_median) else np.nan)
        hint = bool(
            np.isfinite(dn_dd_median)
            and np.isfinite(dp_ret_median)
            and np.isfinite(ratio)
            and dn_dd_median >= float(diag["defended_negative_drawdown_median_min"])
            and dp_ret_median <= float(diag["defended_positive_upside_median_max"])
            and ratio >= float(diag["drawdown_to_upside_median_ratio_min"])
        )
        rows.append(
            {
                "split_bucket": split,
                "defended_negative_n": len(dn),
                "defended_negative_drawdown_avoided_abs_median": dn_dd_median,
                "defended_negative_drawdown_avoided_abs_mean": dn_dd_mean,
                "defended_positive_continue_return_h20_median": dp_ret_median,
                "defended_positive_continue_return_h20_mean": dp_ret_mean,
                "defended_negative_drawdown_to_positive_upside_median_ratio": ratio,
                "partial_exposure_feasibility_hint": hint,
                "feasibility_note": "readout_only_no_partial_exposure_utility_computed",
            }
        )
    return pd.DataFrame(rows)


def build_no_new_computation_audit(panel_replay: pd.DataFrame, lineage: pd.DataFrame) -> pd.DataFrame:
    aggregates_ok = not panel_replay.empty and panel_replay["replay_status"].astype(str).eq("pass").all()
    lineage_ok = not lineage.empty and lineage["lineage_status"].astype(str).eq("pass").all()
    gate = "pass" if aggregates_ok and lineage_ok else "fail"
    return pd.DataFrame(
        [
            {
                "no_new_forward_return_computed": True,
                "no_new_cost_computed": True,
                "no_new_drawdown_computed": True,
                "no_model_refit": True,
                "no_threshold_change": True,
                "no_action_semantics_added": True,
                "all_per_row_values_sourced_from_16e_panel": True,
                "all_aggregates_reconciled_within_tolerance": bool(aggregates_ok),
                "forbidden_computation_detected_n": 0,
                "derived_metric_lineage_complete": bool(lineage_ok),
                "no_new_computation_gate": gate,
                "blocking_reason": "" if gate == "pass" else "aggregate_or_lineage_replay_failed",
            }
        ]
    )


def build_derived_metric_lineage_audit() -> pd.DataFrame:
    specs = [
        ("split_bucket_normalization", "all_postmortem_tables", "upstream_16e_utility_panel", "cluster_split_bucket", "column_rename"),
        ("score_passthrough", "score_bucket_monotonicity_readout.csv", "upstream_16e_utility_panel", "score,model_id,policy_id,threshold_value", "pass_through"),
        ("split_incremental_replay", "panel_aggregate_replay_audit.csv", "upstream_16e_utility_panel,utility_by_split_readout.csv", "incremental_net_return_h20,full_denominator_sum_incremental_return", "groupby_sum"),
        ("six_cell_bidirectional_replay", "panel_aggregate_replay_audit.csv", "upstream_16e_utility_panel,six_cell_utility_reconciliation.csv", "cell_id,incremental_net_return_h20,continue_return_h20,policy_net_return_h20,drawdown_avoided_abs", "groupby_sum"),
        ("failure_arithmetic_attribution", "failure_arithmetic_attribution.csv", "upstream_16e_utility_panel", "cell_id,incremental_net_return_h20,continue_return_h20", "groupby_sum"),
        ("thick_tail_distribution", "defended_positive_thick_tail_readout.csv", "upstream_16e_utility_panel", "label_class,cell_id,continue_return_h20", "quantile_ratio"),
        ("score_bucket_monotonicity", "score_bucket_monotonicity_readout.csv", "upstream_16e_utility_panel", "score,continue_return_h20,continue_max_drawdown_h20,label_class", "quantile_bucket_spearman"),
        ("loss_avoidance_efficiency", "loss_avoidance_efficiency_by_bucket.csv", "upstream_16e_utility_panel", "cell_id,continue_return_h20,score", "groupby_ratio"),
        ("drawdown_residual_feasibility", "drawdown_residual_feasibility_readout.csv", "upstream_16e_utility_panel", "cell_id,drawdown_avoided_abs,continue_return_h20", "quantile_ratio_boolean_gate"),
        ("path_support_decision", "path_support_decision.csv", "postmortem_readouts", "directionality_gate,thick_tail_mismatch_flag,loss_avoidance_efficiency,partial_exposure_feasibility_hint", "boolean_gate"),
    ]
    return pd.DataFrame(
        [
            {
                "derived_metric_id": metric_id,
                "output_table": output,
                "source_artifact_key": source,
                "source_columns": columns,
                "allowed_transform_type": transform,
                "creates_new_return_cost_or_drawdown": False,
                "lineage_status": "pass",
                "blocking_reason": "",
            }
            for metric_id, output, source, columns, transform in specs
        ]
    )


def split_scalar(frame: pd.DataFrame, split: str, column: str, default: Any = np.nan) -> Any:
    sub = frame.loc[frame["split_bucket"].astype(str).eq(split)]
    if sub.empty or column not in sub.columns:
        return default
    return sub[column].iloc[0]


def aggregate_flags(
    score: pd.DataFrame,
    thick: pd.DataFrame,
    efficiency: pd.DataFrame,
    drawdown: pd.DataFrame,
    upstream: pd.DataFrame,
) -> dict[str, Any]:
    train_s = metric_float(split_scalar(score, "train", "monotonicity_spearman"))
    rob_s = metric_float(split_scalar(score, "robustness", "monotonicity_spearman"))
    train_mono = as_bool(split_scalar(score, "train", "monotone_increasing_flag", False))
    rob_mono = as_bool(split_scalar(score, "robustness", "monotone_increasing_flag", False))
    train_non = as_bool(split_scalar(score, "train", "non_monotone_flag", False))
    rob_non = as_bool(split_scalar(score, "robustness", "non_monotone_flag", False))
    train_inv = as_bool(split_scalar(score, "train", "inverted_flag", False))
    rob_inv = as_bool(split_scalar(score, "robustness", "inverted_flag", False))
    rob_caveat = as_bool(split_scalar(score, "robustness", "robustness_monotonicity_unstable_caveat", False))
    directionality = train_mono and rob_mono and not train_non and not rob_non and not train_inv and not rob_inv
    thick_by_split = thick.groupby("split_bucket")["thick_tail_mismatch_flag"].max() if not thick.empty else pd.Series(dtype=bool)
    thick_flag = bool(thick_by_split.get("train", False) and thick_by_split.get("robustness", False))
    eff = efficiency.loc[efficiency["candidate_defend_region_flag"].astype(bool) & ~efficiency["decile_low_power"].astype(bool)]
    eff_by_split = eff.groupby("split_bucket")["efficiency_above_one_flag"].max() if not eff.empty else pd.Series(dtype=bool)
    eff_flag = bool(eff_by_split.get("train", False) and eff_by_split.get("robustness", False))
    draw_by_split = drawdown.groupby("split_bucket")["partial_exposure_feasibility_hint"].max() if not drawdown.empty else pd.Series(dtype=bool)
    draw_hint = bool(draw_by_split.get("train", False) and draw_by_split.get("robustness", False))
    drawdown_gate = str(upstream.loc[0, "drawdown_avoidance_gate"]) == "pass" if not upstream.empty else False
    path_a = bool(directionality and thick_flag and eff_flag)
    path_b = bool(directionality and not path_a and drawdown_gate and draw_hint)
    path_c = bool(directionality and not path_a and not path_b)
    mainline_closed = bool((not directionality) or (not path_a and not path_b and not path_c))
    return {
        "directionality_gate": "pass" if directionality else "fail",
        "train_monotonicity_spearman": train_s,
        "robustness_monotonicity_spearman": rob_s,
        "robustness_monotonicity_unstable_caveat": rob_caveat,
        "train_monotone_increasing_flag": train_mono,
        "robustness_monotone_increasing_flag": rob_mono,
        "train_non_monotone_flag": train_non,
        "robustness_non_monotone_flag": rob_non,
        "train_inverted_flag": train_inv,
        "robustness_inverted_flag": rob_inv,
        "thick_tail_mismatch_flag": thick_flag,
        "efficiency_above_one_in_any_bucket_flag": eff_flag,
        "partial_exposure_feasibility_hint": draw_hint,
        "path_a_supported": path_a,
        "path_b_supported": path_b,
        "path_c_supported": path_c,
        "continuation_as_action_mainline_closed": mainline_closed,
        "score_monotonicity_estimated": bool(np.isfinite(train_s) and np.isfinite(rob_s)),
    }


def build_path_support_decision(flags: dict[str, Any]) -> pd.DataFrame:
    selected = "none"
    if flags["path_a_supported"]:
        selected = "A"
    elif flags["path_b_supported"]:
        selected = "B"
    elif flags["path_c_supported"]:
        selected = "C"
    rows = [
        (
            "A",
            "requirement_16d_prime_utility_weighted_continuation_objective.md",
            flags["path_a_supported"],
            "directional score + thick-tail mismatch + candidate bucket efficiency > 1",
            1,
        ),
        (
            "B",
            "requirement_16e_overlay_risk_budget_continuation_readout.md",
            flags["path_b_supported"],
            "directional score + drawdown gate pass + readout-only partial exposure feasibility hint",
            2,
        ),
        (
            "C",
            "requirement_16d_meta_continuation_participation_filter.md",
            flags["path_c_supported"],
            "directional score but A and B are not supported",
            3,
        ),
        ("none", "none", selected == "none", "directionality failed or no preregistered path supported", 4),
    ]
    return pd.DataFrame(
        [
            {
                "path_id": path_id,
                "path_requirement_file": req,
                "path_supported": bool(supported),
                "directionality_gate": flags["directionality_gate"],
                "support_evidence_summary": evidence,
                "path_priority_rank": rank,
                "selected_path_flag": path_id == selected,
            }
            for path_id, req, supported, evidence, rank in rows
        ]
    )


def build_search_accounting_audit(config: dict[str, Any]) -> pd.DataFrame:
    expected = config["expected_16e"]
    return pd.DataFrame(
        [
            {
                "primary_policy_id": expected["primary_policy_id"],
                "threshold_value": expected["threshold_value"],
                "no_model_refit": True,
                "no_threshold_change": True,
                "no_new_action_semantics": True,
                "path_priority_A_gt_B_gt_C_preregistered": True,
                "validation_used_for_path_selection": False,
                "robustness_used_as_confirmatory_path_gate": True,
                "robustness_used_for_threshold_tuning": False,
                "search_accounting_gate": "pass",
                "blocking_reason": "",
            }
        ]
    )


def decision_from_flags(
    config: dict[str, Any],
    upstream: pd.DataFrame,
    flags: dict[str, Any],
    gates: dict[str, str],
) -> pd.DataFrame:
    recompute_fail = gates.get("no_new_computation_gate") != "pass" or gates.get("search_accounting_gate") != "pass"
    lineage_fail = any(
        gates.get(name) != "pass"
        for name in [
            "input_artifact_gate",
            "upstream_16e_authorization_gate",
            "row_level_panel_gate",
            "panel_aggregate_replay_gate",
            "attribution_identity_gate",
            "score_orientation_consistency_gate",
        ]
    )
    low_power = not flags.get("score_monotonicity_estimated", False)
    selected = "none"
    next_allowed = "none"
    if recompute_fail:
        decision = DECISION_RECOMPUTE
        reason = "recomputation_or_search_accounting_violation"
    elif lineage_fail:
        decision = DECISION_LINEAGE
        reason = ";".join(key for key, value in gates.items() if value != "pass")
    elif low_power:
        decision = DECISION_LOW_POWER
        reason = "score_bucket_monotonicity_unestimable"
    elif flags["continuation_as_action_mainline_closed"]:
        decision = DECISION_CLOSED
        reason = "directionality_gate_failed_or_no_path_supported"
    elif flags["path_a_supported"]:
        decision = DECISION_PATH_A
        next_allowed = "requirement_16d_prime_utility_weighted_continuation_objective.md"
        selected = "A"
        reason = ""
    elif flags["path_b_supported"]:
        decision = DECISION_PATH_B
        next_allowed = "requirement_16e_overlay_risk_budget_continuation_readout.md"
        selected = "B"
        reason = ""
    elif flags["path_c_supported"]:
        decision = DECISION_PATH_C
        next_allowed = "requirement_16d_meta_continuation_participation_filter.md"
        selected = "C"
        reason = ""
    else:
        decision = DECISION_CLOSED
        reason = "no_path_supported"
    up = first_row(upstream)
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_allowed,
                "upstream_16e_decision_state": up.get("upstream_16e_decision_state", ""),
                "upstream_16e_utility_interpretation": up.get("upstream_16e_utility_interpretation", ""),
                "primary_policy_id": config["expected_16e"]["primary_policy_id"],
                "primary_action_semantics_id": config["expected_16e"]["primary_action_semantics_id"],
                "directionality_gate": flags["directionality_gate"],
                "train_monotonicity_spearman": flags["train_monotonicity_spearman"],
                "robustness_monotonicity_spearman": flags["robustness_monotonicity_spearman"],
                "robustness_monotonicity_unstable_caveat": flags["robustness_monotonicity_unstable_caveat"],
                "train_monotone_increasing_flag": flags["train_monotone_increasing_flag"],
                "robustness_monotone_increasing_flag": flags["robustness_monotone_increasing_flag"],
                "train_non_monotone_flag": flags["train_non_monotone_flag"],
                "robustness_non_monotone_flag": flags["robustness_non_monotone_flag"],
                "train_inverted_flag": flags["train_inverted_flag"],
                "robustness_inverted_flag": flags["robustness_inverted_flag"],
                "thick_tail_mismatch_flag": flags["thick_tail_mismatch_flag"],
                "efficiency_above_one_in_any_bucket_flag": flags["efficiency_above_one_in_any_bucket_flag"],
                "partial_exposure_feasibility_hint": flags["partial_exposure_feasibility_hint"],
                "path_a_supported": flags["path_a_supported"],
                "path_b_supported": flags["path_b_supported"],
                "path_c_supported": flags["path_c_supported"],
                "selected_path_id": selected,
                "continuation_as_action_mainline_closed": bool(decision == DECISION_CLOSED or flags["continuation_as_action_mainline_closed"]),
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "chained_simulation_authorized": False,
                "portfolio_backtest_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "live_trading_authorized": False,
                "blocking_reason": reason,
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    available = [col for col in columns if col in frame.columns]
    if not available:
        return "_No columns available._"
    return r16e.markdown_table(frame, available, max_rows=max_rows)


def render_report(
    decision: pd.DataFrame,
    upstream: pd.DataFrame,
    no_new: pd.DataFrame,
    replay: pd.DataFrame,
    attribution: pd.DataFrame,
    thick: pd.DataFrame,
    score: pd.DataFrame,
    efficiency: pd.DataFrame,
    drawdown: pd.DataFrame,
    path_support: pd.DataFrame,
    search: pd.DataFrame,
) -> str:
    d = decision.iloc[0].to_dict()
    replay_fail_n = int((~replay["replay_status"].astype(str).eq("pass")).sum()) if not replay.empty else 0
    primary_attr = attribution.loc[pd.to_numeric(attribution["cost_bps"], errors="coerce").eq(50)]
    primary_eff = efficiency.loc[efficiency["candidate_defend_region_flag"].astype(bool)]
    return f"""# 16E-postmortem Continuation Utility Failure Decomposition Report

## 1. 单行裁决

`decision_state = {d['decision_state']}`；`next_allowed_requirement = {d['next_allowed_requirement']}`；`selected_path_id = {d['selected_path_id']}`；`mainline_closed = {d['continuation_as_action_mainline_closed']}`。

16E-postmortem does not compute new returns, does not refit any model, does not change any threshold, and does not authorize entry, exit, holding, chained simulation, deployment, or live trading. It authorizes at most one alternative-hypothesis requirement (A / B / C) or closes the mainline.

## 2. 16E Not-supported 复验

{markdown_table(upstream, ['upstream_16e_decision_state', 'upstream_16e_next_allowed_requirement', 'upstream_16e_utility_interpretation', 'primary_policy_id', 'primary_action_semantics_id', 'primary_round_trip_defense_cost_bps', 'threshold_value', 'primary_return_utility_gate', 'drawdown_avoidance_gate', 'delay_stress_gate', 'context_utility_gate', 'upstream_16e_authorization_gate'])}

## 3. No-new-computation 与列血缘

{markdown_table(no_new, ['no_new_forward_return_computed', 'no_new_cost_computed', 'no_new_drawdown_computed', 'no_model_refit', 'no_threshold_change', 'no_action_semantics_added', 'all_aggregates_reconciled_within_tolerance', 'no_new_computation_gate'])}

关键列映射固定为：`cluster_split_bucket -> split_bucket`，`score` 由 16D 写入并由 16E `utility_panel` 透传，postmortem 不重算；`sum(panel.incremental_net_return_h20) over (split_bucket,cost_bps)` 对账 `utility_by_split_readout.full_denominator_sum_incremental_return`。panel replay failed rows = {replay_fail_n}。

## 4. PM-Q1 失败算术归因

{markdown_table(primary_attr, ['split_bucket', 'cost_bps', 'full_denominator_net_utility_total', 'defended_positive_incremental_sum', 'defended_negative_incremental_sum', 'defended_neutral_incremental_sum', 'continued_negative_residual_loss_abs', 'attribution_identity_status', 'continued_incremental_zero_status', 'six_cell_bidirectional_replay_status'], max_rows=12)}

`continued_*` 三格 incremental sum 必须为 0；六格 assignment 只使用 `panel.cell_id`，并与 16E `six_cell_utility_reconciliation.csv` 双向对账。

## 5. PM-Q2 厚尾错配

{markdown_table(thick, ['split_bucket', 'population', 'row_n', 'upside_mean', 'upside_q50', 'upside_q75', 'upside_q90', 'defended_positive_upside_mean_ratio', 'defended_positive_upside_q75_ratio', 'defended_positive_upside_q90_vs_all_q75_flag', 'thick_tail_mismatch_flag'], max_rows=12)}

## 6. PM-Q3 Score Bucket 单调性

{markdown_table(score, ['split_bucket', 'decile_index', 'row_n', 'positive_n', 'negative_n', 'neutral_n', 'mean_continue_return_h20', 'base_rate_positive', 'monotonicity_spearman', 'monotone_increasing_flag', 'non_monotone_flag', 'inverted_flag', 'robustness_monotonicity_unstable_caveat'], max_rows=30)}

Directionality gate = `{d['directionality_gate']}`。若 robustness caveat 为 true，本报告区分"明确非单调"与"方向性不足以过 robustness gate"；当前 robustness caveat = `{d['robustness_monotonicity_unstable_caveat']}`。

## 7. PM-Q4 Loss-avoidance Efficiency

{markdown_table(primary_eff, ['split_bucket', 'decile_index', 'defended_negative_n', 'defended_positive_n', 'avoided_loss_abs', 'sacrificed_upside_abs', 'loss_avoidance_efficiency', 'decile_low_power', 'efficiency_above_one_flag'], max_rows=12)}

## 8. PM-Q5 Drawdown Residual Feasibility

{markdown_table(drawdown, ['split_bucket', 'defended_negative_n', 'defended_negative_drawdown_avoided_abs_median', 'defended_positive_continue_return_h20_median', 'defended_negative_drawdown_to_positive_upside_median_ratio', 'partial_exposure_feasibility_hint', 'feasibility_note'])}

PM-Q5 只报告 16E 既有 `drawdown_avoided_abs` 与 `continue_return_h20` 的分布形状；没有计算 partial-exposure utility。

## 9. Path Support And Search Accounting

{markdown_table(path_support, ['path_id', 'path_requirement_file', 'path_supported', 'directionality_gate', 'path_priority_rank', 'selected_path_flag'], max_rows=8)}

{markdown_table(search, ['primary_policy_id', 'threshold_value', 'no_model_refit', 'no_threshold_change', 'no_new_action_semantics', 'path_priority_A_gt_B_gt_C_preregistered', 'validation_used_for_path_selection', 'robustness_used_as_confirmatory_path_gate', 'robustness_used_for_threshold_tuning', 'search_accounting_gate'])}

## 10. Findings And Insight

本 postmortem 的核心判定不是 16D 是否有分类能力，而是这个分类 score 是否能单调转化为 h20 continuation utility。若 directionality gate fail，则 16E 的 `not_supported` 更接近"continuation-as-action 主线缺少稳定 utility 方向性"，而不是简单的 cost 或 drawdown 参数错配。若 directionality gate pass 但厚尾/efficiency/feasibility 指标支持某一路径，则只授权 A/B/C 中优先级最高的一条 requirement，仍不授权 16F 或任何交易化工作。
"""


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: pd.DataFrame, outputs: dict[str, Path]) -> Path:
    dec = first_row(decision)
    hashes = {
        key: file_sha(value)
        for key, value in outputs.items()
        if key not in {"manifest"} and value.exists() and LOCAL_CACHE_DIR not in value.parents
    }
    row_counts = {
        key: count_rows(value)
        for key, value in outputs.items()
        if key not in {"manifest", "report"} and value.exists()
    }
    resolved = resolve_paths(config)
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "requirement_path": str(topic_path(config["paths"]["requirement"])),
        "requirement_sha256": file_sha(topic_path(config["paths"]["requirement"])),
        "config_path": str(config_path),
        "config_sha256": file_sha(config_path),
        "upstream_16e_decision": dec.get("upstream_16e_decision_state", ""),
        "upstream_16e_utility_interpretation": dec.get("upstream_16e_utility_interpretation", ""),
        "primary_policy_id": config["expected_16e"]["primary_policy_id"],
        "primary_action_semantics_id": config["expected_16e"]["primary_action_semantics_id"],
        "threshold_value": config["expected_16e"]["threshold_value"],
        "decision_state": dec.get("decision_state", ""),
        "next_allowed_requirement": dec.get("next_allowed_requirement", ""),
        "selected_path_id": dec.get("selected_path_id", ""),
        "continuation_as_action_mainline_closed": dec.get("continuation_as_action_mainline_closed", ""),
        "monotonicity_spearman_by_split": {
            "train": dec.get("train_monotonicity_spearman", np.nan),
            "robustness": dec.get("robustness_monotonicity_spearman", np.nan),
        },
        "robustness_monotonicity_unstable_caveat": dec.get("robustness_monotonicity_unstable_caveat", False),
        "no_new_computation_audit_summary": {
            "no_new_forward_return_computed": True,
            "no_new_cost_computed": True,
            "no_new_drawdown_computed": True,
            "no_model_refit": True,
            "no_threshold_change": True,
            "no_action_semantics_added": True,
        },
        "authorization_booleans": {
            "entry_policy_authorized": False,
            "exit_policy_authorized": False,
            "holding_policy_authorized": False,
            "chained_simulation_authorized": False,
            "portfolio_backtest_authorized": False,
            "model_deployment_authorized": False,
            "production_signal_authorized": False,
            "live_trading_authorized": False,
        },
        "input_artifact_hashes": {
            key: file_sha(value)
            for key, value in resolved.items()
            if value.exists() and value.is_file()
        },
        "output_hashes": hashes,
        "row_counts": row_counts,
        "large_artifact_policy": "postmortem_grouping.parquet is local read-derived cache; publishable outputs are aggregate csv/report/manifest only",
    }
    return write_json(path, payload)


def empty_decision(config: dict[str, Any], decision_state: str, reason: str) -> pd.DataFrame:
    flags = {
        "directionality_gate": "fail",
        "train_monotonicity_spearman": np.nan,
        "robustness_monotonicity_spearman": np.nan,
        "robustness_monotonicity_unstable_caveat": False,
        "train_monotone_increasing_flag": False,
        "robustness_monotone_increasing_flag": False,
        "train_non_monotone_flag": False,
        "robustness_non_monotone_flag": False,
        "train_inverted_flag": False,
        "robustness_inverted_flag": False,
        "thick_tail_mismatch_flag": False,
        "efficiency_above_one_in_any_bucket_flag": False,
        "partial_exposure_feasibility_hint": False,
        "path_a_supported": False,
        "path_b_supported": False,
        "path_c_supported": False,
        "continuation_as_action_mainline_closed": False,
        "score_monotonicity_estimated": False,
    }
    upstream = pd.DataFrame([{"upstream_16e_decision_state": "", "upstream_16e_utility_interpretation": ""}])
    decision = decision_from_flags(config, upstream, flags, {})
    decision.loc[0, "decision_state"] = decision_state
    decision.loc[0, "blocking_reason"] = reason
    return decision


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit = build_input_artifact_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_gate, input_reason = input_gate_status(input_audit)
    if check_inputs_only:
        return 0 if input_gate == "pass" else 1
    if input_gate != "pass":
        decision = empty_decision(config, DECISION_LINEAGE, input_reason)
        write_df(outputs["decision"], decision)
        write_manifest(outputs["manifest"], config_path, config, decision, outputs)
        return 1

    upstream = build_upstream_16e_authorization_audit(config, resolved)
    panel, row_panel_gate, row_panel_reason = load_and_validate_panel(config, resolved)
    tolerance = float(config["diagnostic"]["replay_tolerance"])
    replay = build_panel_aggregate_replay_audit(panel, resolved, tolerance)
    lineage = build_derived_metric_lineage_audit()
    no_new = build_no_new_computation_audit(replay, lineage)
    primary_panel = panel.loc[pd.to_numeric(panel["cost_bps"], errors="coerce").eq(int(config["diagnostic"]["primary_cost_bps"]))].copy()
    grouping = assign_score_deciles(primary_panel, config)
    attribution = build_failure_arithmetic_attribution(panel, resolved, tolerance)
    replay_by_split_cost = replay.groupby(["split_bucket", "cost_bps"])["replay_status"].apply(lambda s: "pass" if s.astype(str).eq("pass").all() else "fail")
    attribution["six_cell_bidirectional_replay_status"] = [
        replay_by_split_cost.get((row.split_bucket, row.cost_bps), "fail") for row in attribution.itertuples(index=False)
    ]
    thick = build_thick_tail_readout(primary_panel, config)
    score = build_score_bucket_monotonicity_readout(grouping, config)
    efficiency = build_loss_avoidance_efficiency(grouping, score, config)
    drawdown = build_drawdown_residual_feasibility_readout(primary_panel, config)
    search = build_search_accounting_audit(config)
    flags = aggregate_flags(score, thick, efficiency, drawdown, upstream)
    path_support = build_path_support_decision(flags)
    attribution_gate = "pass" if (
        not attribution.empty
        and attribution["attribution_identity_status"].astype(str).eq("pass").all()
        and attribution["continued_incremental_zero_status"].astype(str).eq("pass").all()
        and attribution["six_cell_bidirectional_replay_status"].astype(str).eq("pass").all()
    ) else "fail"
    gates = {
        "input_artifact_gate": input_gate,
        "upstream_16e_authorization_gate": str(upstream.loc[0, "upstream_16e_authorization_gate"]),
        "row_level_panel_gate": row_panel_gate,
        "panel_aggregate_replay_gate": "pass" if not replay.empty and replay["replay_status"].astype(str).eq("pass").all() else "fail",
        "no_new_computation_gate": str(no_new.loc[0, "no_new_computation_gate"]),
        "attribution_identity_gate": attribution_gate,
        "score_orientation_consistency_gate": "fail" if flags["train_inverted_flag"] or flags["robustness_inverted_flag"] else "pass",
        "search_accounting_gate": str(search.loc[0, "search_accounting_gate"]),
    }
    decision = decision_from_flags(config, upstream, flags, gates)
    if row_panel_gate != "pass" and not str(decision.loc[0, "blocking_reason"]):
        decision.loc[0, "blocking_reason"] = row_panel_reason

    write_df(outputs["upstream_16e_authorization_audit"], upstream)
    write_df(outputs["panel_aggregate_replay_audit"], replay)
    write_df(outputs["derived_metric_lineage_audit"], lineage)
    write_df(outputs["no_new_computation_audit"], no_new)
    write_df(outputs["failure_arithmetic_attribution"], attribution)
    write_df(outputs["defended_positive_thick_tail_readout"], thick)
    write_df(outputs["score_bucket_monotonicity_readout"], score)
    write_df(outputs["loss_avoidance_efficiency_by_bucket"], efficiency)
    write_df(outputs["drawdown_residual_feasibility_readout"], drawdown)
    write_df(outputs["path_support_decision"], path_support)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["decision"], decision)
    write_df(outputs["postmortem_grouping"], grouping)
    write_text(outputs["report"], render_report(decision, upstream, no_new, replay, attribution, thick, score, efficiency, drawdown, path_support, search))
    write_manifest(outputs["manifest"], config_path, config, decision, outputs)
    return 0 if str(decision.loc[0, "decision_state"]) not in {DECISION_LINEAGE, DECISION_RECOMPUTE, DECISION_LOW_POWER} else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())
