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
RUNNER_16D_PATH = EXPERIMENT_DIR / "src" / "run_16d_sequential_continuation_policy_preflight.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r16d = load_runner(RUNNER_16D_PATH, "run_16d_for_16e")

RUN_ID = "16E_sequential_continuation_utility_diagnostic"
EXPERIMENT_ID = "16_winner_episode_sequential_sampling_geometry_preflight_v0"
PHASE_ID = "16E"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_16e_sequential_continuation_utility_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("train", "robustness", "validation")
CONTEXT_STRATA = (
    "all_steps",
    "late_rescue_context",
    "non_late_rescue_context",
    "known_failed_context_any",
    "non_known_failed_context",
)
CELL_IDS = (
    "defended_positive",
    "defended_negative",
    "defended_neutral",
    "continued_positive",
    "continued_negative",
    "continued_neutral",
)

DECISION_READY = "16E_utility_diagnostic_ready_for_chained_action_transition_freeze"
DECISION_LINEAGE = "16E_utility_diagnostic_blocked_by_input_or_lineage_failure"
DECISION_ACTION = "16E_utility_diagnostic_blocked_by_action_semantics_failure"
DECISION_SEARCH = "16E_utility_diagnostic_blocked_by_utility_search_or_leakage"
DECISION_LOW_POWER = "16E_utility_diagnostic_low_power"
DECISION_NOT_SUPPORTED = "16E_utility_diagnostic_not_supported"
DECISION_FRAGILE = "16E_utility_diagnostic_cost_or_execution_fragile"
DECISION_CONTEXT = "16E_utility_diagnostic_context_concentrated_only"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 16E sequential continuation utility diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    return r16d.topic_path(value)


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_16d_authorization_audit": TABLE_DIR / "upstream_16d_authorization_audit.csv",
        "full_action_panel_rebuild_audit": TABLE_DIR / "full_action_panel_rebuild_audit.csv",
        "single_step_action_semantics_audit": TABLE_DIR / "single_step_action_semantics_audit.csv",
        "utility_price_path_audit": TABLE_DIR / "utility_price_path_audit.csv",
        "policy_utility_binding_audit": TABLE_DIR / "policy_utility_binding_audit.csv",
        "six_cell_utility_reconciliation": TABLE_DIR / "six_cell_utility_reconciliation.csv",
        "utility_by_split_readout": TABLE_DIR / "utility_by_split_readout.csv",
        "utility_by_context_readout": TABLE_DIR / "utility_by_context_readout.csv",
        "positive_sacrifice_utility_readout": TABLE_DIR / "positive_sacrifice_utility_readout.csv",
        "negative_avoidance_utility_readout": TABLE_DIR / "negative_avoidance_utility_readout.csv",
        "continued_negative_leakage_utility_readout": TABLE_DIR / "continued_negative_leakage_utility_readout.csv",
        "neutral_utility_readout": TABLE_DIR / "neutral_utility_readout.csv",
        "cost_delay_stress_readout": TABLE_DIR / "cost_delay_stress_readout.csv",
        "validation_stress_utility_readout": TABLE_DIR / "validation_stress_utility_readout.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "sequential_continuation_utility_decision.csv",
        "utility_panel_sample": TABLE_DIR / "utility_panel_sample.csv.gz",
        "utility_panel": LOCAL_CACHE_DIR / "utility_panel.parquet",
        "report": REPORT_DIR / "sequential_continuation_utility_diagnostic_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r16d.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r16d.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r16d.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r16d.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r16d.file_sha(path)


def stable_hash(value: Any) -> str:
    return r16d.stable_hash(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r16d.bool_series(series)


def finite(series: pd.Series) -> pd.Series:
    return r16d.finite(series)


def safe_rate(num: Any, den: Any) -> float:
    return r16d.safe_rate(num, den)


def metric_float(value: Any) -> float:
    return r16d.metric_float(value)


def count_rows(path: Path) -> int | float:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path))
    if suffixes.endswith((".csv", ".csv.gz")):
        return r16d.count_rows(path)
    if path.is_file():
        return sum(1 for _ in path.open("rb"))
    if path.is_dir():
        return len(list(path.iterdir()))
    return np.nan


def required_columns_for_key(key: str) -> set[str]:
    if key == "upstream_16d_decision":
        return {
            "decision_state",
            "next_allowed_requirement",
            "primary_label_id",
            "selected_threshold_id",
            "primary_horizon_sessions",
            "primary_model_id",
            "primary_policy_id",
            "train_binary_step_n",
            "robustness_binary_step_n",
            "input_artifact_gate",
            "search_accounting_gate",
        }
    if key == "upstream_16d_policy_action_panel":
        return {
            "step_id",
            "policy_id",
            "candidate_action",
            "cluster_split_bucket",
            "instrument",
            "step_start_pos",
            "step_end_pos",
            "step_start_date",
            "step_end_date",
            "step_start_qfq_close",
            "step_end_qfq_close",
            "max_drawdown_from_step_start",
            "continuation_positive",
            "continuation_negative",
            "continuation_neutral",
            "known_failed_context_any",
            "late_rescue_context",
            "non_known_failed_context",
            "non_late_rescue_context",
        }
    if key.endswith("_policy_confusion_readout") or key.endswith("_policy_context_stratified_readout"):
        return {"policy_id", "split_bucket", "context_stratum", "binary_step_n", "positive_n", "negative_n", "defended_negative_n"}
    if key.endswith("_policy_threshold_freeze_audit"):
        return {"policy_id", "threshold_value", "threshold_freeze_status"}
    if key.endswith("_manifest"):
        return set()
    if key.endswith("_search_accounting_audit"):
        return {"search_accounting_gate"}
    return set()


def artifact_required_flag(key: str) -> str:
    optional = {"upstream_16d_policy_action_panel"}
    return "optional_cache" if key in optional else "required"


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, path in resolved.items():
        flag = artifact_required_flag(key)
        exists = path.exists()
        read_status = "pass"
        schema_status = "not_checked"
        row_count: int | float = np.nan
        sha = ""
        if exists and path.is_file():
            try:
                row_count = count_rows(path)
                sha = file_sha(path)
                required = required_columns_for_key(key)
                if required and "".join(path.suffixes).endswith((".csv", ".csv.gz")):
                    frame = read_table(path, nrows=5)
                    schema_status = "pass" if required.issubset(frame.columns) else "fail_missing_columns"
                elif required and path.suffix == ".parquet":
                    frame = pd.read_parquet(path, columns=None)
                    schema_status = "pass" if required.issubset(frame.columns) else "fail_missing_columns"
                else:
                    schema_status = "pass"
            except Exception as exc:
                read_status = f"fail_read_error:{type(exc).__name__}"
                schema_status = "fail_read_error"
        elif exists and path.is_dir():
            row_count = count_rows(path)
            if key == "stock_daily_qfq_dir":
                schema_status = r16d.qfq_dir_schema_status(path)
                read_status = "pass" if schema_status == "pass" else schema_status
            else:
                schema_status = "pass" if row_count else "fail_empty_dir"
                read_status = "pass" if row_count else "fail_empty_dir"
        else:
            read_status = "missing"
            schema_status = "missing"
        rows.append(
            {
                "artifact_key": key,
                "resolved_path": str(path),
                "row_count": row_count,
                "sha256": sha,
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": flag,
                "lineage_role": key,
                "blocking_reason": "",
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    required = input_audit.loc[input_audit["required_flag"].astype(str).eq("required")]
    bad = required.loc[
        ~required["read_status"].astype(str).eq("pass")
        | required["schema_status"].astype(str).isin(["missing", "fail_missing_columns", "fail_read_error"])
        | required["schema_status"].astype(str).str.startswith("fail")
    ]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_key"].astype(str).head(12))


def as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    return bool(value)


def build_upstream_16d_authorization_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    decision = read_table(resolved["upstream_16d_decision"])
    row = decision.iloc[0].to_dict() if not decision.empty else {}
    manifest = json.loads(resolved["upstream_16d_manifest"].read_text(encoding="utf-8"))
    policy = config["policy"]
    expected_int = {
        "train_binary_step_n": 14962,
        "train_positive_n": 10078,
        "train_negative_n": 4884,
        "train_defended_binary_step_n": 4489,
        "train_defended_negative_n": 2299,
        "robustness_binary_step_n": 1872,
        "robustness_positive_n": 1346,
        "robustness_negative_n": 526,
        "robustness_defended_binary_step_n": 397,
        "robustness_defended_negative_n": 196,
        "non_known_failed_robustness_binary_step_n": 907,
        "non_known_failed_robustness_negative_n": 224,
        "non_known_failed_robustness_defended_negative_n": 83,
    }
    expected_float = {
        "train_defense_negative_capture_rate": 0.470721,
        "train_positive_sacrifice_rate": 0.217305,
        "train_continue_negative_leakage_rate": 0.529279,
        "robustness_defense_negative_capture_rate": 0.372624,
        "robustness_defense_precision_lift_vs_binary_negative_base": 0.212720,
        "robustness_positive_sacrifice_rate": 0.149331,
        "robustness_continue_negative_leakage_rate": 0.627376,
        "non_known_failed_robustness_defense_precision_lift": 0.253032,
    }
    hard_gates = [
        "input_artifact_gate",
        "upstream_16c_authorization_gate",
        "upstream_16b_label_rebuild_gate",
        "score_rebuild_lineage_gate",
        "feature_contract_replay_gate",
        "score_orientation_gate",
        "threshold_freeze_gate",
        "neutral_handling_gate",
        "policy_action_binding_gate",
        "known_failed_context_rebuild_gate",
        "search_accounting_gate",
        "power_gate",
        "primary_policy_usefulness_gate",
        "context_independence_gate",
    ]
    checks: dict[str, bool] = {
        "decision_state": row.get("decision_state") == policy["required_16d_decision"],
        "next_allowed_requirement": row.get("next_allowed_requirement") == policy["required_16d_next_allowed"],
        "manifest_decision": manifest.get("decision_state") == policy["required_16d_decision"],
        "primary_label_id": row.get("primary_label_id") == policy["primary_label_id"],
        "selected_threshold_id": row.get("selected_threshold_id") == policy["selected_threshold_id"],
        "primary_horizon_sessions": int(metric_float(row.get("primary_horizon_sessions"))) == int(policy["primary_horizon_sessions"]),
        "primary_model_id": row.get("primary_model_id") == policy["primary_model_id"],
        "primary_policy_id": row.get("primary_policy_id") == policy["primary_policy_id"],
    }
    for key, expected in expected_int.items():
        checks[key] = int(metric_float(row.get(key))) == expected
    for key, expected in expected_float.items():
        checks[key] = abs(metric_float(row.get(key)) - expected) <= 1e-6
    for key in hard_gates:
        checks[key] = row.get(key) == "pass"
    for key in [
        "entry_policy_authorized",
        "exit_policy_authorized",
        "holding_policy_authorized",
        "return_backtest_authorized",
        "cost_model_authorized",
        "model_deployment_authorized",
        "production_signal_authorized",
    ]:
        checks[key] = not as_bool(row.get(key, True))
    status = "pass" if all(checks.values()) else "fail"
    out = {
        "upstream_decision_state": row.get("decision_state", ""),
        "upstream_next_allowed_requirement": row.get("next_allowed_requirement", ""),
        "primary_label_id": row.get("primary_label_id", ""),
        "selected_threshold_id": row.get("selected_threshold_id", ""),
        "primary_horizon_sessions": row.get("primary_horizon_sessions", np.nan),
        "primary_model_id": row.get("primary_model_id", ""),
        "primary_policy_id": row.get("primary_policy_id", ""),
    }
    for key in [*expected_int.keys(), *expected_float.keys()]:
        out[key] = row.get(key, np.nan)
    for key in [
        "soft_overlap_partial_coverage_caveat",
        "known_failed_context_exposure_caveat",
        "entry_policy_authorized",
        "exit_policy_authorized",
        "holding_policy_authorized",
        "return_backtest_authorized",
        "cost_model_authorized",
        "model_deployment_authorized",
        "production_signal_authorized",
    ]:
        out[key] = as_bool(row.get(key, False))
    for key in hard_gates:
        out[key] = row.get(key, "")
    out["authorization_status"] = status
    out["blocking_reason"] = "" if status == "pass" else ";".join(key for key, ok in checks.items() if not ok)
    return pd.DataFrame([out])


def rebuild_action_panel_from_16d(resolved: dict[str, Path]) -> pd.DataFrame:
    config_16d = r16d.load_config(resolved["upstream_16d_config"])
    resolved_16d = r16d.resolve_paths(config_16d)
    labels, _label_audit = r16d.load_primary_labels_with_rebuild(config_16d, resolved_16d)
    feature_panel, _feature_cache_audit = r16d.load_or_build_feature_panel(labels, config_16d, resolved_16d)
    scored, _preprocessing_hash = r16d.build_policy_score_panel(feature_panel, config_16d)
    thresholds = r16d.build_policy_threshold_freeze_audit(scored, config_16d)
    actions = r16d.apply_policy_actions(scored, thresholds)
    context_flags, _context_audit = r16d.context_flags_from_overlap(labels, config_16d, resolved_16d)
    return r16d.enrich_actions_with_context(actions, context_flags)


def validate_action_panel(action_panel: pd.DataFrame, config: dict[str, Any], resolved: dict[str, Path], source: str, cache_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    policy = config["policy"]
    primary = action_panel.loc[action_panel["policy_id"].astype(str).eq(policy["primary_policy_id"])].copy()
    decision = read_table(resolved["upstream_16d_decision"]).iloc[0].to_dict()
    confusion = read_table(resolved["upstream_16d_policy_confusion_readout"])
    context = read_table(resolved["upstream_16d_policy_context_stratified_readout"])
    threshold = read_table(resolved["upstream_16d_policy_threshold_freeze_audit"])
    expected_threshold = float(
        threshold.loc[threshold["policy_id"].astype(str).eq(policy["primary_policy_id"]), "threshold_value"].iloc[0]
    )
    binary = bool_series(primary["is_binary_target"])
    neutral = bool_series(primary["continuation_neutral"])
    duplicate_n = int(primary.duplicated(["policy_id", "step_id"]).sum())
    threshold_abs_diff = float((finite(primary["threshold_value"]) - expected_threshold).abs().max()) if not primary.empty else np.nan
    missing_context_cols = [
        col
        for col in ["known_failed_context_any", "late_rescue_context", "non_known_failed_context", "non_late_rescue_context"]
        if col not in primary.columns
    ]
    split_count_ok = True
    for split in SPLITS:
        sub = primary.loc[primary["cluster_split_bucket"].astype(str).eq(split)]
        src = confusion.loc[
            confusion["policy_id"].astype(str).eq(policy["primary_policy_id"])
            & confusion["split_bucket"].astype(str).eq(split)
            & confusion["context_stratum"].astype(str).eq("all_steps")
        ]
        if src.empty:
            split_count_ok = False
            continue
        src_row = src.iloc[0]
        split_count_ok &= int(bool_series(sub["is_binary_target"]).sum()) == int(src_row["binary_step_n"])
        split_count_ok &= int(bool_series(sub["continuation_neutral"]).sum()) == int(src_row["neutral_step_n"])
        split_count_ok &= int((sub["candidate_action"].astype(str).eq("defend_next_h20") & bool_series(sub["is_binary_target"])).sum()) == int(src_row["defended_binary_step_n"])
    context_ok = not missing_context_cols
    if context_ok:
        for split in SPLITS:
            sub = primary.loc[primary["cluster_split_bucket"].astype(str).eq(split) & bool_series(primary["non_known_failed_context"])]
            src = context.loc[
                context["policy_id"].astype(str).eq(policy["primary_policy_id"])
                & context["split_bucket"].astype(str).eq(split)
                & context["context_stratum"].astype(str).eq("non_known_failed_context")
            ]
            if src.empty:
                context_ok = False
                continue
            src_row = src.iloc[0]
            context_ok &= int(bool_series(sub["is_binary_target"]).sum()) == int(src_row["binary_step_n"])
    status = "pass" if (
        not primary.empty
        and duplicate_n == 0
        and len(primary) == 23405
        and int(binary.sum()) == 17339
        and int(neutral.sum()) == 6066
        and split_count_ok
        and abs(threshold_abs_diff) <= 1e-6
        and int(primary["candidate_action"].isna().sum()) == 0
        and context_ok
    ) else "fail"
    audit = pd.DataFrame(
        [
            {
                "action_panel_source": source,
                "cache_path": str(cache_path),
                "rebuild_config_path": str(resolved["upstream_16d_config"]),
                "rebuild_runner_path": str(resolved["upstream_16d_runner"]),
                "primary_policy_id": policy["primary_policy_id"],
                "primary_policy_row_count": len(primary),
                "binary_step_count": int(binary.sum()),
                "neutral_step_count": int(neutral.sum()),
                "unique_policy_key_status": "pass" if duplicate_n == 0 else "fail",
                "candidate_action_missing_n": int(primary["candidate_action"].isna().sum()) if "candidate_action" in primary else len(primary),
                "threshold_value_replayed": float(primary["threshold_value"].dropna().iloc[0]) if "threshold_value" in primary and not primary["threshold_value"].dropna().empty else np.nan,
                "threshold_value_expected": expected_threshold,
                "threshold_value_abs_diff": threshold_abs_diff,
                "split_label_count_replay_status": "pass" if split_count_ok else "fail",
                "known_failed_context_replay_status": "pass" if context_ok else "fail",
                "cache_validation_status": "pass" if source == "optional_16d_cache_used" and status == "pass" else "not_applicable" if source != "optional_16d_cache_used" else "fail",
                "full_action_panel_rebuild_status": status,
                "blocking_reason": "" if status == "pass" else "primary_policy_action_panel_validation_failed",
            }
        ]
    )
    return primary, audit, status


def load_or_rebuild_primary_action_panel(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cache_path = resolved["upstream_16d_policy_action_panel"]
    if cache_path.exists():
        cached = pd.read_parquet(cache_path)
        primary, audit, status = validate_action_panel(cached, config, resolved, "optional_16d_cache_used", cache_path)
        if status == "pass":
            return primary, audit
    rebuilt = rebuild_action_panel_from_16d(resolved)
    primary, audit, status = validate_action_panel(rebuilt, config, resolved, "rebuilt_in_memory_from_16d_helpers", cache_path)
    if status == "pass":
        out_path = LOCAL_CACHE_DIR / "rebuilt_primary_action_panel.parquet"
        write_df(out_path, primary)
        audit["rebuilt_primary_action_panel_path"] = str(out_path)
    return primary, audit


def build_single_step_action_semantics_audit(config: dict[str, Any]) -> pd.DataFrame:
    sem = config["action_semantics"]
    checks = {
        "primary_action_semantics_id": sem["primary_action_semantics_id"] == "full_avoidance_cash_h20_close_to_close_v1",
        "primary_round_trip_defense_cost_bps": int(sem["primary_round_trip_defense_cost_bps"]) in sem["round_trip_defense_cost_bps_grid"],
        "delay_stress_id": sem["delay_stress_id"] == "one_session_delay_close_to_close_v1",
        "validation": not as_bool(sem["validation_used_for_action_semantics_selection"]),
        "robustness": not as_bool(sem["robustness_used_for_action_semantics_selection"]),
        "return_metric": not as_bool(sem["return_metric_used_for_action_semantics_selection"]),
        "cost_metric": not as_bool(sem["cost_metric_used_for_action_semantics_selection"]),
    }
    status = "pass" if all(checks.values()) else "fail"
    return pd.DataFrame(
        [
            {
                "primary_action_semantics_id": sem["primary_action_semantics_id"],
                "decision_time": sem["decision_time"],
                "baseline_action": sem["baseline_action"],
                "continue_exposure": sem["continue_exposure"],
                "defend_exposure": sem["defend_exposure"],
                "defend_cash_return_h20": sem["defend_cash_return_h20"],
                "round_trip_defense_cost_bps_grid": ",".join(str(x) for x in sem["round_trip_defense_cost_bps_grid"]),
                "primary_round_trip_defense_cost_bps": sem["primary_round_trip_defense_cost_bps"],
                "delay_stress_id": sem["delay_stress_id"],
                "validation_used_for_action_semantics_selection": sem["validation_used_for_action_semantics_selection"],
                "robustness_used_for_action_semantics_selection": sem["robustness_used_for_action_semantics_selection"],
                "return_metric_used_for_action_semantics_selection": sem["return_metric_used_for_action_semantics_selection"],
                "cost_metric_used_for_action_semantics_selection": sem["cost_metric_used_for_action_semantics_selection"],
                "action_semantics_gate": status,
                "blocking_reason": "" if status == "pass" else ";".join(key for key, ok in checks.items() if not ok),
            }
        ]
    )


def load_qfq(instrument: str, qfq_dir: Path) -> pd.DataFrame | None:
    path = qfq_dir / f"{instrument}.csv"
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, usecols=["date", "close"])
    except Exception:
        return None


def label_class(frame: pd.DataFrame) -> pd.Series:
    return pd.Series(
        np.select(
            [bool_series(frame["continuation_positive"]), bool_series(frame["continuation_negative"]), bool_series(frame["continuation_neutral"])],
            ["positive", "negative", "neutral"],
            default="unknown",
        ),
        index=frame.index,
    )


def compute_base_price_utility(action_panel: pd.DataFrame, qfq_dir: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    tol_close = float(config["price_validation"]["close_abs_tolerance"])
    tol_dd = float(config["price_validation"]["max_drawdown_abs_tolerance"])
    rows: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    for split, split_panel in action_panel.groupby("cluster_split_bucket", sort=False):
        labelable_n = len(split_panel)
        valid_n = 0
        missing_instrument_n = 0
        bad_bounds_n = 0
        nonfinite_close_n = 0
        nonpositive_close_n = 0
        start_mismatch_n = 0
        end_mismatch_n = 0
        dd_diffs: list[float] = []
        delay_missing_n = 0
        split_rows = []
        for instrument, sub in split_panel.groupby("instrument", sort=False):
            qfq = load_qfq(str(instrument), qfq_dir)
            if qfq is None:
                missing_instrument_n += len(sub)
                continue
            close = finite(qfq["close"]).to_numpy(dtype=float)
            dates = qfq["date"].astype(str).to_numpy()
            for step in sub.itertuples(index=False):
                start = int(step.step_start_pos)
                end = int(step.step_end_pos)
                status = "pass"
                if start < 0 or end >= len(close) or end < start:
                    bad_bounds_n += 1
                    status = "fail_bad_bounds"
                elif start + 1 >= len(close):
                    delay_missing_n += 1
                    status = "fail_delay_row_missing"
                else:
                    window = close[start : end + 1]
                    if not np.isfinite(window).all():
                        nonfinite_close_n += 1
                        status = "fail_nonfinite_close"
                    elif (window <= 0).any():
                        nonpositive_close_n += 1
                        status = "fail_nonpositive_close"
                    elif str(step.step_start_date) != str(dates[start]) or str(step.step_end_date) != str(dates[end]):
                        bad_bounds_n += 1
                        status = "fail_date_mismatch"
                    else:
                        start_close = float(close[start])
                        end_close = float(close[end])
                        max_dd = float(np.nanmin(window / start_close - 1.0))
                        first_session_return = float(close[start + 1] / start_close - 1.0)
                        start_diff = abs(start_close - float(step.step_start_qfq_close))
                        end_diff = abs(end_close - float(step.step_end_qfq_close))
                        dd_diff = abs(max_dd - float(step.max_drawdown_from_step_start))
                        start_mismatch_n += int(start_diff > tol_close)
                        end_mismatch_n += int(end_diff > tol_close)
                        dd_diffs.append(dd_diff)
                        if start_diff > tol_close or end_diff > tol_close or dd_diff > tol_dd:
                            status = "fail_price_replay_mismatch"
                        else:
                            valid_n += 1
                            split_rows.append(
                                {
                                    **step._asdict(),
                                    "label_class": "positive"
                                    if bool(step.continuation_positive)
                                    else "negative"
                                    if bool(step.continuation_negative)
                                    else "neutral"
                                    if bool(step.continuation_neutral)
                                    else "unknown",
                                    "continue_return_h20": end_close / start_close - 1.0,
                                    "continue_max_drawdown_h20": max_dd,
                                    "first_session_return": first_session_return,
                                    "utility_price_status": status,
                                }
                            )
        base = pd.DataFrame(split_rows)
        if not base.empty:
            rows.append(base)
        gate = "pass" if valid_n == labelable_n and not any([missing_instrument_n, bad_bounds_n, nonfinite_close_n, nonpositive_close_n, start_mismatch_n, end_mismatch_n, delay_missing_n]) and (not dd_diffs or max(dd_diffs) <= tol_dd) else "fail"
        audit_rows.append(
            {
                "split_bucket": split,
                "labelable_step_n": labelable_n,
                "price_path_valid_step_n": valid_n,
                "missing_qfq_instrument_n": missing_instrument_n,
                "bad_step_bounds_n": bad_bounds_n,
                "nonfinite_close_n": nonfinite_close_n,
                "nonpositive_close_n": nonpositive_close_n,
                "step_start_close_mismatch_n": start_mismatch_n,
                "step_end_close_mismatch_n": end_mismatch_n,
                "max_drawdown_replay_abs_diff_max": float(max(dd_diffs)) if dd_diffs else np.nan,
                "delay_row_missing_n": delay_missing_n,
                "utility_price_path_gate": gate,
                "blocking_reason": "" if gate == "pass" else "qfq_price_replay_failed",
            }
        )
    return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), pd.DataFrame(audit_rows)


def expand_utility_panel(base: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    costs = [int(x) for x in config["action_semantics"]["round_trip_defense_cost_bps_grid"]]
    parts = []
    defend = base["candidate_action"].astype(str).eq("defend_next_h20")
    for cost in costs:
        out = base.copy()
        out["cost_bps"] = cost
        out["policy_gross_return_h20"] = np.where(defend, 0.0, out["continue_return_h20"].astype(float))
        out["policy_max_drawdown_h20"] = np.where(defend, 0.0, out["continue_max_drawdown_h20"].astype(float))
        out["policy_net_return_h20"] = np.where(defend, -cost / 10000.0, out["continue_return_h20"].astype(float))
        out["incremental_net_return_h20"] = np.where(defend, out["policy_net_return_h20"] - out["continue_return_h20"], 0.0)
        out["drawdown_avoided_abs"] = np.where(defend, np.maximum(0.0, -out["continue_max_drawdown_h20"].astype(float)), 0.0)
        out["delayed_policy_net_return_h20"] = np.where(defend, out["first_session_return"].astype(float) - cost / 10000.0, out["continue_return_h20"].astype(float))
        out["delayed_incremental_net_return_h20"] = np.where(defend, out["delayed_policy_net_return_h20"] - out["continue_return_h20"], 0.0)
        action_prefix = np.where(defend, "defended", "continued")
        out["cell_id"] = pd.Series(action_prefix, index=out.index).astype(str) + "_" + out["label_class"].astype(str)
        parts.append(out)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def stratum_mask(frame: pd.DataFrame, stratum: str) -> pd.Series:
    if stratum == "all_steps":
        return pd.Series(True, index=frame.index)
    if stratum == "late_rescue_context":
        return bool_series(frame["late_rescue_context"])
    if stratum == "non_late_rescue_context":
        return bool_series(frame["non_late_rescue_context"])
    if stratum == "known_failed_context_any":
        return bool_series(frame["known_failed_context_any"])
    if stratum == "non_known_failed_context":
        return bool_series(frame["non_known_failed_context"])
    return pd.Series(False, index=frame.index)


def summarize_utility(sub: pd.DataFrame) -> dict[str, Any]:
    if sub.empty:
        return {
            "labelable_step_n": 0,
            "positive_n": 0,
            "negative_n": 0,
            "neutral_n": 0,
            "defended_labelable_step_n": 0,
            "continued_labelable_step_n": 0,
            "full_denominator_sum_incremental_return": 0.0,
            "full_denominator_mean_incremental_return": np.nan,
            "full_denominator_mean_drawdown_avoided_abs": np.nan,
            "defended_positive_incremental_return_sum": 0.0,
            "defended_negative_incremental_return_sum": 0.0,
            "defended_neutral_incremental_return_sum": 0.0,
            "continued_negative_return_sum": 0.0,
            "continued_negative_max_drawdown_mean": np.nan,
            "defended_negative_drawdown_avoided_abs_mean": np.nan,
        }
    defend = sub["candidate_action"].astype(str).eq("defend_next_h20")
    continued = ~defend
    pos = bool_series(sub["continuation_positive"])
    neg = bool_series(sub["continuation_negative"])
    neutral = bool_series(sub["continuation_neutral"])
    n = len(sub)
    return {
        "labelable_step_n": n,
        "positive_n": int(pos.sum()),
        "negative_n": int(neg.sum()),
        "neutral_n": int(neutral.sum()),
        "defended_labelable_step_n": int(defend.sum()),
        "continued_labelable_step_n": int(continued.sum()),
        "full_denominator_sum_incremental_return": float(sub["incremental_net_return_h20"].sum()),
        "full_denominator_mean_incremental_return": float(sub["incremental_net_return_h20"].sum() / n),
        "full_denominator_mean_drawdown_avoided_abs": float(sub["drawdown_avoided_abs"].sum() / n),
        "defended_positive_incremental_return_sum": float(sub.loc[defend & pos, "incremental_net_return_h20"].sum()),
        "defended_negative_incremental_return_sum": float(sub.loc[defend & neg, "incremental_net_return_h20"].sum()),
        "defended_neutral_incremental_return_sum": float(sub.loc[defend & neutral, "incremental_net_return_h20"].sum()),
        "continued_negative_return_sum": float(sub.loc[continued & neg, "continue_return_h20"].sum()),
        "continued_negative_max_drawdown_mean": float(sub.loc[continued & neg, "continue_max_drawdown_h20"].mean()) if int((continued & neg).sum()) else np.nan,
        "defended_negative_drawdown_avoided_abs_mean": float(sub.loc[defend & neg, "drawdown_avoided_abs"].mean()) if int((defend & neg).sum()) else np.nan,
    }


def build_six_cell_utility_reconciliation(panel: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows = []
    gate = "pass"
    for split in SPLITS:
        split_panel = panel.loc[panel["cluster_split_bucket"].astype(str).eq(split)]
        if split_panel.empty:
            continue
        for context in CONTEXT_STRATA:
            ctx = split_panel.loc[stratum_mask(split_panel, context)]
            for cost, cost_panel in ctx.groupby("cost_bps", sort=False):
                expected = float(cost_panel["incremental_net_return_h20"].sum())
                cell_sum = 0.0
                for cell in CELL_IDS:
                    sub = cost_panel.loc[cost_panel["cell_id"].astype(str).eq(cell)]
                    cell_sum += float(sub["incremental_net_return_h20"].sum())
                    rows.append(
                        {
                            "split_bucket": split,
                            "context_stratum": context,
                            "cost_bps": int(cost),
                            "cell_id": cell,
                            "candidate_action": cell.split("_", 1)[0].replace("defended", "defend_next_h20").replace("continued", "continue_next_h20"),
                            "label_class": cell.split("_", 1)[1],
                            "cell_step_n": len(sub),
                            "continue_return_sum": float(sub["continue_return_h20"].sum()) if not sub.empty else 0.0,
                            "continue_return_mean": float(sub["continue_return_h20"].mean()) if not sub.empty else np.nan,
                            "continue_max_drawdown_mean": float(sub["continue_max_drawdown_h20"].mean()) if not sub.empty else np.nan,
                            "policy_net_return_sum": float(sub["policy_net_return_h20"].sum()) if not sub.empty else 0.0,
                            "policy_net_return_mean": float(sub["policy_net_return_h20"].mean()) if not sub.empty else np.nan,
                            "incremental_return_sum": float(sub["incremental_net_return_h20"].sum()) if not sub.empty else 0.0,
                            "incremental_return_mean": float(sub["incremental_net_return_h20"].mean()) if not sub.empty else np.nan,
                            "drawdown_avoided_abs_sum": float(sub["drawdown_avoided_abs"].sum()) if not sub.empty else 0.0,
                            "drawdown_avoided_abs_mean": float(sub["drawdown_avoided_abs"].mean()) if not sub.empty else np.nan,
                            "six_cell_reconciliation_status": "pass",
                        }
                    )
                if abs(cell_sum - expected) > 1e-10:
                    gate = "fail"
    out = pd.DataFrame(rows)
    if gate == "fail" and not out.empty:
        out["six_cell_reconciliation_status"] = "fail"
    return out, gate


def build_utility_by_split_readout(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    dd_min = float(config["utility_gates"]["defended_negative_drawdown_avoided_abs_mean_min"])
    for (split, cost), sub in panel.groupby(["cluster_split_bucket", "cost_bps"], sort=False):
        metrics = summarize_utility(sub)
        rows.append(
            {
                "split_bucket": split,
                "cost_bps": int(cost),
                **metrics,
                "primary_return_utility_gate": "pass"
                if metrics["full_denominator_mean_incremental_return"] > 0 and metrics["full_denominator_sum_incremental_return"] > 0
                else "fail",
                "drawdown_avoidance_gate": "pass"
                if metrics["defended_negative_drawdown_avoided_abs_mean"] >= dd_min and metrics["full_denominator_mean_drawdown_avoided_abs"] > 0
                else "fail",
            }
        )
    return pd.DataFrame(rows)


def build_utility_by_context_readout(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    gates = config["context_gates"]
    dd_min = float(config["utility_gates"]["defended_negative_drawdown_avoided_abs_mean_min"])
    for split in SPLITS:
        split_panel = panel.loc[panel["cluster_split_bucket"].astype(str).eq(split)]
        if split_panel.empty:
            continue
        for context in CONTEXT_STRATA:
            ctx = split_panel.loc[stratum_mask(split_panel, context)]
            for cost, sub in ctx.groupby("cost_bps", sort=False):
                metrics = summarize_utility(sub)
                valid_power = True
                if context == "non_known_failed_context" and split == "train":
                    valid_power = (
                        metrics["labelable_step_n"] >= gates["non_known_failed_train_labelable_step_n_min"]
                        and metrics["defended_labelable_step_n"] >= gates["non_known_failed_train_defended_labelable_step_n_min"]
                    )
                elif context == "non_known_failed_context" and split == "robustness":
                    valid_power = (
                            metrics["labelable_step_n"] >= gates["non_known_failed_robustness_labelable_step_n_min"]
                            and metrics["defended_labelable_step_n"] >= gates["non_known_failed_robustness_defended_labelable_step_n_min"]
                        )
                primary_return_gate = (
                    "pass"
                    if metrics["full_denominator_mean_incremental_return"] > 0
                    and metrics["full_denominator_sum_incremental_return"] > 0
                    else "fail"
                )
                drawdown_gate = (
                    "pass"
                    if metrics["defended_negative_drawdown_avoided_abs_mean"] >= dd_min
                    and metrics["full_denominator_mean_drawdown_avoided_abs"] > 0
                    else "fail"
                )
                status = "readout"
                if context == "non_known_failed_context" and split in {"train", "robustness"}:
                    if not valid_power:
                        status = "context_power_inconclusive"
                    elif metrics["full_denominator_mean_incremental_return"] > 0 and metrics["full_denominator_mean_drawdown_avoided_abs"] > 0:
                        status = "pass"
                    else:
                        status = "fail"
                elif split == "validation":
                    status = "stress_readout"
                rows.append(
                    {
                        "split_bucket": split,
                        "cost_bps": int(cost),
                        **metrics,
                        "primary_return_utility_gate": primary_return_gate,
                        "drawdown_avoidance_gate": drawdown_gate,
                        "context_stratum": context,
                        "valid_context_power": bool(valid_power),
                        "context_utility_rebuild_gate": "pass",
                        "context_utility_status": status,
                        "context_caveat": "low_power_readout_only" if not valid_power else "",
                    }
                )
    return pd.DataFrame(rows)


def build_neutral_utility_readout(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    neutral = bool_series(panel["continuation_neutral"])
    for (split, cost), sub in panel.loc[neutral].groupby(["cluster_split_bucket", "cost_bps"], sort=False):
        defend = sub["candidate_action"].astype(str).eq("defend_next_h20")
        rows.append(
            {
                "split_bucket": split,
                "cost_bps": int(cost),
                "neutral_step_n": len(sub),
                "neutral_defended_n": int(defend.sum()),
                "neutral_continued_n": int((~defend).sum()),
                "neutral_continue_return_mean": float(sub["continue_return_h20"].mean()) if not sub.empty else np.nan,
                "neutral_policy_net_return_mean": float(sub["policy_net_return_h20"].mean()) if not sub.empty else np.nan,
                "neutral_incremental_return_sum": float(sub["incremental_net_return_h20"].sum()) if not sub.empty else 0.0,
                "neutral_incremental_return_mean": float(sub["incremental_net_return_h20"].mean()) if not sub.empty else np.nan,
                "neutral_drawdown_avoided_abs_mean": float(sub["drawdown_avoided_abs"].mean()) if not sub.empty else np.nan,
                "neutral_utility_gate": "pass",
                "neutral_utility_caveat": "",
            }
        )
    return pd.DataFrame(rows)


def build_positive_sacrifice_readout(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pos = bool_series(panel["continuation_positive"])
    defend = panel["candidate_action"].astype(str).eq("defend_next_h20")
    for split in SPLITS:
        split_panel = panel.loc[panel["cluster_split_bucket"].astype(str).eq(split) & pos & defend]
        if split_panel.empty:
            continue
        for context in CONTEXT_STRATA:
            ctx = split_panel.loc[stratum_mask(split_panel, context)]
            for cost, sub in ctx.groupby("cost_bps", sort=False):
                sacrificed = np.maximum(0.0, sub["continue_return_h20"].astype(float) - sub["policy_net_return_h20"].astype(float))
                rows.append(
                    {
                        "split_bucket": split,
                        "context_stratum": context,
                        "cost_bps": int(cost),
                        "defended_positive_n": len(sub),
                        "defended_positive_continue_return_sum": float(sub["continue_return_h20"].sum()),
                        "defended_positive_continue_return_mean": float(sub["continue_return_h20"].mean()) if not sub.empty else np.nan,
                        "defended_positive_policy_net_return_sum": float(sub["policy_net_return_h20"].sum()),
                        "defended_positive_policy_net_return_mean": float(sub["policy_net_return_h20"].mean()) if not sub.empty else np.nan,
                        "defended_positive_incremental_return_sum": float(sub["incremental_net_return_h20"].sum()),
                        "defended_positive_incremental_return_mean": float(sub["incremental_net_return_h20"].mean()) if not sub.empty else np.nan,
                        "positive_upside_sacrificed_abs_sum": float(sacrificed.sum()),
                        "positive_upside_sacrificed_abs_mean": float(sacrificed.mean()) if len(sacrificed) else np.nan,
                        "positive_sacrifice_status": "readout",
                        "positive_sacrifice_caveat": "",
                    }
                )
    return pd.DataFrame(rows)


def build_negative_avoidance_readout(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    neg = bool_series(panel["continuation_negative"])
    defend = panel["candidate_action"].astype(str).eq("defend_next_h20")
    for split in SPLITS:
        split_panel = panel.loc[panel["cluster_split_bucket"].astype(str).eq(split) & neg & defend]
        if split_panel.empty:
            continue
        for context in CONTEXT_STRATA:
            ctx = split_panel.loc[stratum_mask(split_panel, context)]
            for cost, sub in ctx.groupby("cost_bps", sort=False):
                avoided_loss = np.maximum(0.0, -sub["continue_return_h20"].astype(float))
                rows.append(
                    {
                        "split_bucket": split,
                        "context_stratum": context,
                        "cost_bps": int(cost),
                        "defended_negative_n": len(sub),
                        "defended_negative_continue_return_sum": float(sub["continue_return_h20"].sum()),
                        "defended_negative_continue_return_mean": float(sub["continue_return_h20"].mean()) if not sub.empty else np.nan,
                        "defended_negative_policy_net_return_sum": float(sub["policy_net_return_h20"].sum()),
                        "defended_negative_policy_net_return_mean": float(sub["policy_net_return_h20"].mean()) if not sub.empty else np.nan,
                        "defended_negative_incremental_return_sum": float(sub["incremental_net_return_h20"].sum()),
                        "defended_negative_incremental_return_mean": float(sub["incremental_net_return_h20"].mean()) if not sub.empty else np.nan,
                        "defended_negative_drawdown_avoided_abs_sum": float(sub["drawdown_avoided_abs"].sum()),
                        "defended_negative_drawdown_avoided_abs_mean": float(sub["drawdown_avoided_abs"].mean()) if not sub.empty else np.nan,
                        "defended_negative_avoided_loss_abs_sum": float(avoided_loss.sum()),
                        "negative_avoidance_status": "readout",
                        "negative_avoidance_caveat": "",
                    }
                )
    return pd.DataFrame(rows)


def build_continued_negative_leakage_readout(panel: pd.DataFrame, split_readout: pd.DataFrame) -> pd.DataFrame:
    rows = []
    neg = bool_series(panel["continuation_negative"])
    defend = panel["candidate_action"].astype(str).eq("defend_next_h20")
    split_gate = {
        (str(row["split_bucket"]), int(row["cost_bps"])): str(row["primary_return_utility_gate"])
        for _, row in split_readout.iterrows()
    }
    for split in SPLITS:
        split_panel = panel.loc[panel["cluster_split_bucket"].astype(str).eq(split) & neg]
        if split_panel.empty:
            continue
        for context in CONTEXT_STRATA:
            ctx = split_panel.loc[stratum_mask(split_panel, context)]
            for cost, sub in ctx.groupby("cost_bps", sort=False):
                continued = sub.loc[~defend.loc[sub.index]]
                defended = sub.loc[defend.loc[sub.index]]
                residual_loss = float(np.maximum(0.0, -continued["continue_return_h20"].astype(float)).sum())
                avoided_loss = float(np.maximum(0.0, -defended["continue_return_h20"].astype(float)).sum())
                share = residual_loss / max(avoided_loss, 1e-12)
                primary_gate_pass = split_gate.get((str(split), int(cost))) == "pass"
                rows.append(
                    {
                        "split_bucket": split,
                        "context_stratum": context,
                        "cost_bps": int(cost),
                        "continued_negative_n": len(continued),
                        "continued_negative_continue_return_sum": float(continued["continue_return_h20"].sum()) if not continued.empty else 0.0,
                        "continued_negative_continue_return_mean": float(continued["continue_return_h20"].mean()) if not continued.empty else np.nan,
                        "continued_negative_max_drawdown_mean": float(continued["continue_max_drawdown_h20"].mean()) if not continued.empty else np.nan,
                        "continued_negative_max_drawdown_worst": float(continued["continue_max_drawdown_h20"].min()) if not continued.empty else np.nan,
                        "continued_negative_residual_loss_abs": residual_loss,
                        "defended_negative_avoided_loss_abs": avoided_loss,
                        "continued_negative_residual_loss_share": share,
                        "continued_negative_leakage_status": "readout",
                        "continued_negative_leakage_caveat": "utility_positive_but_leaky" if primary_gate_pass and share > 1.0 else "",
                    }
                )
    return pd.DataFrame(rows)


def build_cost_delay_stress_readout(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    delay_id = config["action_semantics"]["delay_stress_id"]
    for (split, cost), sub in panel.groupby(["cluster_split_bucket", "cost_bps"], sort=False):
        defend = sub["candidate_action"].astype(str).eq("defend_next_h20")
        labelable = len(sub)
        primary_mean = float(sub["incremental_net_return_h20"].sum() / labelable) if labelable else np.nan
        delay_mean = float(sub["delayed_incremental_net_return_h20"].sum() / labelable) if labelable else np.nan
        rows.append(
            {
                "split_bucket": split,
                "cost_bps": int(cost),
                "delay_stress_id": delay_id,
                "labelable_step_n": labelable,
                "defended_labelable_step_n": int(defend.sum()),
                "delay_stress_denominator_type": "full_labelable_denominator",
                "delay_stress_labelable_denominator": labelable,
                "delay_stress_continued_zero_incremental_n": int((~defend).sum()),
                "primary_close_to_close_mean_incremental_return": primary_mean,
                "delay_stress_mean_incremental_return": delay_mean,
                "primary_minus_delay_delta": primary_mean - delay_mean if np.isfinite(primary_mean) and np.isfinite(delay_mean) else np.nan,
                "cost_delay_stress_status": "pass" if delay_mean > 0 else "fail",
            }
        )
    return pd.DataFrame(rows)


def build_validation_stress_utility_readout(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    validation = panel.loc[panel["cluster_split_bucket"].astype(str).eq("validation")]
    for cost, sub in validation.groupby("cost_bps", sort=False):
        metrics = summarize_utility(sub)
        rows.append(
            {
                "stress_split_id": "validation",
                "cost_bps": int(cost),
                **metrics,
                "delay_stress_mean_incremental_return": float(sub["delayed_incremental_net_return_h20"].sum() / len(sub)) if len(sub) else np.nan,
                "validation_used_for_selection": False,
                "validation_blocks_decision": False,
                "validation_stress_status": "stress_readout",
                "validation_stress_caveat": "",
            }
        )
    return pd.DataFrame(rows)


def build_policy_utility_binding_audit(action_panel: pd.DataFrame, utility_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    policy = config["policy"]
    sem = config["action_semantics"]
    dup = int(action_panel.duplicated(["policy_id", "step_id"]).sum())
    missing_action = int(action_panel["candidate_action"].isna().sum())
    primary_cost = int(sem["primary_round_trip_defense_cost_bps"])
    primary_utility = utility_panel.loc[finite(utility_panel["cost_bps"]).eq(primary_cost)]
    missing_price = int(len(action_panel) - primary_utility["step_id"].nunique())
    neutral_dropped = int(bool_series(action_panel["continuation_neutral"]).sum() - bool_series(primary_utility["continuation_neutral"]).sum())
    status = "pass" if not any([dup, missing_action, missing_price, neutral_dropped]) else "fail"
    defend = action_panel["candidate_action"].astype(str).eq("defend_next_h20")
    return pd.DataFrame(
        [
            {
                "primary_policy_id": policy["primary_policy_id"],
                "primary_action_semantics_id": sem["primary_action_semantics_id"],
                "label_id": policy["primary_label_id"],
                "threshold_id": policy["selected_threshold_id"],
                "horizon_sessions": policy["primary_horizon_sessions"],
                "labelable_step_n": len(action_panel),
                "binary_step_n": int(bool_series(action_panel["is_binary_target"]).sum()),
                "neutral_step_n": int(bool_series(action_panel["continuation_neutral"]).sum()),
                "defended_labelable_step_n": int(defend.sum()),
                "continued_labelable_step_n": int((~defend).sum()),
                "duplicate_step_policy_key_n": dup,
                "missing_candidate_action_n": missing_action,
                "missing_utility_price_n": missing_price,
                "neutral_dropped_from_denominator_n": neutral_dropped,
                "policy_utility_binding_gate": status,
                "blocking_reason": "" if status == "pass" else "policy_utility_binding_failed",
            }
        ]
    )


def build_search_accounting(config: dict[str, Any]) -> pd.DataFrame:
    sem = config["action_semantics"]
    policy = config["policy"]
    row = {
        "search_family": "sequential_continuation_utility_diagnostic",
        "primary_policy_id": policy["primary_policy_id"],
        "primary_action_semantics_id": sem["primary_action_semantics_id"],
        "primary_round_trip_defense_cost_bps": sem["primary_round_trip_defense_cost_bps"],
        "primary_horizon_sessions": policy["primary_horizon_sessions"],
        "selected_threshold_id": policy["selected_threshold_id"],
        "primary_label_id": policy["primary_label_id"],
        "validation_used_for_selection": False,
        "robustness_used_for_selection": False,
        "return_metric_used_for_selection": False,
        "cost_metric_used_for_selection": False,
        "context_filter_used_for_selection": False,
        "threshold_changed_after_16d": False,
        "model_refit_after_16d": False,
        "entry_rule_defined": False,
        "chained_policy_simulated": False,
        "portfolio_metric_computed": False,
        "deployment_metric_computed": False,
    }
    bad = any(as_bool(row[key]) for key in [
        "validation_used_for_selection",
        "robustness_used_for_selection",
        "return_metric_used_for_selection",
        "cost_metric_used_for_selection",
        "context_filter_used_for_selection",
        "threshold_changed_after_16d",
        "model_refit_after_16d",
        "entry_rule_defined",
        "chained_policy_simulated",
        "portfolio_metric_computed",
        "deployment_metric_computed",
    ])
    row["search_accounting_gate"] = "fail" if bad else "pass"
    row["blocking_reason"] = "" if not bad else "utility_search_or_leakage_detected"
    return pd.DataFrame([row])


def readout_row(frame: pd.DataFrame, split: str, cost: int, context: str | None = None) -> pd.Series:
    mask = frame["split_bucket"].astype(str).eq(split) & finite(frame["cost_bps"]).eq(cost)
    if context is not None:
        mask &= frame["context_stratum"].astype(str).eq(context)
    sub = frame.loc[mask]
    return sub.iloc[0] if not sub.empty else pd.Series(dtype=object)


def compute_power_gates(action_panel: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    gates = config["power_gates"]
    out: dict[str, Any] = {}
    for split in ("train", "robustness"):
        sub = action_panel.loc[action_panel["cluster_split_bucket"].astype(str).eq(split)]
        defend = sub["candidate_action"].astype(str).eq("defend_next_h20")
        out[f"{split}_labelable_step_n"] = len(sub)
        out[f"{split}_defended_labelable_step_n"] = int(defend.sum())
        out[f"{split}_defended_positive_n"] = int((defend & bool_series(sub["continuation_positive"])).sum())
        out[f"{split}_defended_negative_n"] = int((defend & bool_series(sub["continuation_negative"])).sum())
        out[f"{split}_defended_neutral_n"] = int((defend & bool_series(sub["continuation_neutral"])).sum())
        out[f"{split}_episode_cluster_n"] = int(sub["episode_cluster_id"].nunique())
    train_ok = (
        out["train_labelable_step_n"] >= gates["train_labelable_step_n_min"]
        and out["train_defended_labelable_step_n"] >= gates["train_defended_labelable_step_n_min"]
        and out["train_defended_positive_n"] >= gates["train_defended_positive_n_min"]
        and out["train_defended_negative_n"] >= gates["train_defended_negative_n_min"]
        and out["train_defended_neutral_n"] >= gates["train_defended_neutral_n_min"]
        and out["train_episode_cluster_n"] >= gates["train_episode_cluster_n_min"]
    )
    rob_ok = (
        out["robustness_labelable_step_n"] >= gates["robustness_labelable_step_n_min"]
        and out["robustness_defended_labelable_step_n"] >= gates["robustness_defended_labelable_step_n_min"]
        and out["robustness_defended_positive_n"] >= gates["robustness_defended_positive_n_min"]
        and out["robustness_defended_negative_n"] >= gates["robustness_defended_negative_n_min"]
        and out["robustness_defended_neutral_n"] >= gates["robustness_defended_neutral_n_min"]
        and out["robustness_episode_cluster_n"] >= gates["robustness_episode_cluster_n_min"]
    )
    val = action_panel.loc[action_panel["cluster_split_bucket"].astype(str).eq("validation")]
    val_defend = val["candidate_action"].astype(str).eq("defend_next_h20") if not val.empty else pd.Series(dtype=bool)
    out["validation_stress_low_power_caveat"] = not (
        len(val) >= gates["validation_labelable_step_n_min"]
        and int(val_defend.sum()) >= gates["validation_defended_labelable_step_n_min"]
    )
    out["primary_power_gate"] = "pass" if train_ok and rob_ok else "fail"
    return out


def compute_context_power_gate(context_readout: pd.DataFrame, config: dict[str, Any], cost: int) -> str:
    train = readout_row(context_readout, "train", cost, "non_known_failed_context")
    rob = readout_row(context_readout, "robustness", cost, "non_known_failed_context")
    return "pass" if as_bool(train.get("valid_context_power", False)) and as_bool(rob.get("valid_context_power", False)) else "fail"


def build_decision(
    config: dict[str, Any],
    gates: dict[str, str],
    action_panel: pd.DataFrame,
    split_readout: pd.DataFrame,
    context_readout: pd.DataFrame,
    delay_readout: pd.DataFrame,
    leakage: pd.DataFrame,
) -> pd.DataFrame:
    policy = config["policy"]
    sem = config["action_semantics"]
    primary_cost = int(sem["primary_round_trip_defense_cost_bps"])
    zero_cost = int(config["utility_gates"]["zero_cost_bps"])
    power = compute_power_gates(action_panel, config)
    context_power_gate = compute_context_power_gate(context_readout, config, primary_cost)
    train_0 = readout_row(split_readout, "train", zero_cost)
    rob_0 = readout_row(split_readout, "robustness", zero_cost)
    train_50 = readout_row(split_readout, "train", primary_cost)
    rob_50 = readout_row(split_readout, "robustness", primary_cost)
    train_delay = readout_row(delay_readout, "train", primary_cost)
    rob_delay = readout_row(delay_readout, "robustness", primary_cost)
    train_non = readout_row(context_readout, "train", primary_cost, "non_known_failed_context")
    rob_non = readout_row(context_readout, "robustness", primary_cost, "non_known_failed_context")
    train_known = readout_row(context_readout, "train", primary_cost, "known_failed_context_any")
    rob_known = readout_row(context_readout, "robustness", primary_cost, "known_failed_context_any")
    zero_pass = train_0.get("full_denominator_mean_incremental_return", np.nan) > 0 and rob_0.get("full_denominator_mean_incremental_return", np.nan) > 0
    primary_return_pass = (
        train_50.get("full_denominator_mean_incremental_return", np.nan) > 0
        and rob_50.get("full_denominator_mean_incremental_return", np.nan) > 0
        and rob_50.get("full_denominator_sum_incremental_return", np.nan) > 0
    )
    drawdown_pass = train_50.get("drawdown_avoidance_gate") == "pass" and rob_50.get("drawdown_avoidance_gate") == "pass"
    delay_pass = (
        train_delay.get("delay_stress_mean_incremental_return", np.nan) > 0
        and rob_delay.get("delay_stress_mean_incremental_return", np.nan) > 0
    )
    non_known_utility_pass = (
        train_non.get("context_utility_status") == "pass"
        and rob_non.get("context_utility_status") == "pass"
    )
    known_utility_pass = (
        train_known.get("full_denominator_mean_incremental_return", np.nan) > 0
        and rob_known.get("full_denominator_mean_incremental_return", np.nan) > 0
        and train_known.get("full_denominator_mean_drawdown_avoided_abs", np.nan) > 0
        and rob_known.get("full_denominator_mean_drawdown_avoided_abs", np.nan) > 0
    )
    hard_gate_names = [
        "input_artifact_gate",
        "upstream_16d_authorization_gate",
        "full_action_panel_rebuild_gate",
        "utility_price_path_gate",
        "policy_utility_binding_gate",
        "six_cell_reconciliation_gate",
        "neutral_utility_gate",
        "context_utility_rebuild_gate",
        "search_accounting_gate",
    ]
    hard_fail = any(gates.get(name, "fail") != "pass" for name in hard_gate_names)
    if gates.get("search_accounting_gate") == "fail":
        decision = DECISION_SEARCH
        next_allowed = "none"
        interpretation = "blocked_by_utility_search_or_leakage"
    elif gates.get("action_semantics_gate") != "pass":
        decision = DECISION_ACTION
        next_allowed = "none"
        interpretation = "blocked_by_action_semantics_failure"
    elif hard_fail:
        decision = DECISION_LINEAGE
        next_allowed = "none"
        interpretation = "blocked_by_input_or_lineage_failure"
    elif power["primary_power_gate"] != "pass" or context_power_gate != "pass":
        decision = DECISION_LOW_POWER
        next_allowed = "none"
        interpretation = "low_power"
    elif zero_pass and not primary_return_pass:
        decision = DECISION_FRAGILE
        next_allowed = "none"
        interpretation = "positive_before_primary_cost_only"
    elif primary_return_pass and not delay_pass:
        decision = DECISION_FRAGILE
        next_allowed = "none"
        interpretation = "positive_close_to_close_but_delay_fragile"
    elif not primary_return_pass and drawdown_pass:
        decision = DECISION_NOT_SUPPORTED
        next_allowed = "none"
        interpretation = "drawdown_reduction_only_return_not_supported"
    elif not primary_return_pass:
        decision = DECISION_NOT_SUPPORTED
        next_allowed = "none"
        interpretation = "return_utility_not_supported"
    elif not non_known_utility_pass and known_utility_pass:
        decision = DECISION_CONTEXT
        next_allowed = "none"
        interpretation = "utility_concentrated_in_known_failed_context"
    elif not non_known_utility_pass:
        decision = DECISION_NOT_SUPPORTED
        next_allowed = "none"
        interpretation = "non_known_failed_context_utility_not_supported"
    else:
        decision = DECISION_READY
        next_allowed = policy["next_allowed_requirement"]
        interpretation = "single_step_utility_supports_chained_transition_freeze"
    primary_leak = leakage.loc[
        leakage["split_bucket"].astype(str).eq("robustness")
        & leakage["context_stratum"].astype(str).eq("all_steps")
        & finite(leakage["cost_bps"]).eq(primary_cost)
    ]
    leakage_caveat = ""
    if primary_return_pass and not primary_leak.empty:
        leakage_caveat = str(primary_leak.iloc[0].get("continued_negative_leakage_caveat", ""))
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_allowed,
                "primary_label_id": policy["primary_label_id"],
                "primary_model_id": policy["primary_model_id"],
                "primary_policy_id": policy["primary_policy_id"],
                "primary_action_semantics_id": sem["primary_action_semantics_id"],
                "primary_round_trip_defense_cost_bps": primary_cost,
                "primary_return_utility_gate": "pass" if primary_return_pass else "fail",
                "drawdown_avoidance_gate": "pass" if drawdown_pass else "fail",
                "delay_stress_gate": "pass" if delay_pass else "fail",
                "context_power_gate": context_power_gate,
                "context_utility_gate": "pass" if non_known_utility_pass else "fail",
                "six_cell_reconciliation_gate": gates.get("six_cell_reconciliation_gate", "fail"),
                "continued_negative_leakage_caveat": leakage_caveat,
                "utility_interpretation": interpretation,
                **power,
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "chained_simulation_authorized": False,
                "portfolio_backtest_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "live_trading_authorized": False,
                "blocking_reason": "" if decision == DECISION_READY else interpretation,
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    return r16d.markdown_table(frame, columns, max_rows=max_rows)


def render_report(
    decision: pd.DataFrame,
    upstream: pd.DataFrame,
    action_audit: pd.DataFrame,
    semantics: pd.DataFrame,
    price_audit: pd.DataFrame,
    split_readout: pd.DataFrame,
    context_readout: pd.DataFrame,
    six_cell: pd.DataFrame,
    positive: pd.DataFrame,
    negative: pd.DataFrame,
    leakage: pd.DataFrame,
    neutral: pd.DataFrame,
    delay: pd.DataFrame,
    validation: pd.DataFrame,
    search: pd.DataFrame,
) -> str:
    d = decision.iloc[0].to_dict()
    primary_cost = int(d["primary_round_trip_defense_cost_bps"])
    split_primary = split_readout.loc[finite(split_readout["cost_bps"]).eq(primary_cost)]
    context_primary = context_readout.loc[finite(context_readout["cost_bps"]).eq(primary_cost)]
    positive_primary = positive.loc[finite(positive["cost_bps"]).eq(primary_cost) & positive["context_stratum"].astype(str).eq("all_steps")]
    negative_primary = negative.loc[finite(negative["cost_bps"]).eq(primary_cost) & negative["context_stratum"].astype(str).eq("all_steps")]
    leakage_primary = leakage.loc[finite(leakage["cost_bps"]).eq(primary_cost) & leakage["context_stratum"].astype(str).eq("all_steps")]
    neutral_primary = neutral.loc[finite(neutral["cost_bps"]).eq(primary_cost)]
    delay_primary = delay.loc[finite(delay["cost_bps"]).eq(primary_cost)]
    validation_primary = validation.loc[finite(validation["cost_bps"]).eq(primary_cost)]
    return f"""# 16E Sequential Continuation Utility Diagnostic Report

## 1. 单行裁决

`decision_state = {d['decision_state']}`；`next_allowed_requirement = {d['next_allowed_requirement']}`。

16E does not authorize entry, exit, holding, chained simulation, deployment, or live trading.

## 2. 16D Authorization Replay

{markdown_table(upstream, ['authorization_status', 'upstream_decision_state', 'upstream_next_allowed_requirement', 'primary_policy_id', 'train_binary_step_n', 'train_defended_negative_n', 'robustness_binary_step_n', 'robustness_defended_negative_n', 'robustness_positive_sacrifice_rate', 'robustness_continue_negative_leakage_rate'])}

16E 复验 16D publishable decision、hard gates、authorization booleans 和 primary bottom-30% action rule；`policy_action_sample.csv.gz` 没有作为 row-level truth 使用。

## 3. Action Panel And Semantics

{markdown_table(action_audit, ['action_panel_source', 'primary_policy_row_count', 'binary_step_count', 'neutral_step_count', 'threshold_value_replayed', 'split_label_count_replay_status', 'known_failed_context_replay_status', 'full_action_panel_rebuild_status'])}

{markdown_table(semantics, ['primary_action_semantics_id', 'decision_time', 'baseline_action', 'primary_round_trip_defense_cost_bps', 'delay_stress_id', 'action_semantics_gate'])}

Primary semantics 是单步 h20 diagnostic：continue 保持 h20 exposure，defend 在本 h20 block 内以 cash return 0 表示 full avoidance，并扣除 diagnostic round-trip defense cost。它不是卖出、减仓、止损或交易建议。

## 4. Price Path Replay

{markdown_table(price_audit, ['split_bucket', 'labelable_step_n', 'price_path_valid_step_n', 'step_start_close_mismatch_n', 'step_end_close_mismatch_n', 'max_drawdown_replay_abs_diff_max', 'delay_row_missing_n', 'utility_price_path_gate'])}

Return、max drawdown 和 one-session delay stress 均从 qfq close path 重算。

## 5. Primary Utility By Split

{markdown_table(split_primary, ['split_bucket', 'labelable_step_n', 'defended_labelable_step_n', 'positive_n', 'negative_n', 'neutral_n', 'full_denominator_mean_incremental_return', 'full_denominator_sum_incremental_return', 'full_denominator_mean_drawdown_avoided_abs', 'primary_return_utility_gate', 'drawdown_avoidance_gate'])}

Utility 使用 full labelable denominator，neutral rows 留在分母内，不用 defended-only denominator。

## 6. Six-cell Reconciliation

{markdown_table(six_cell.loc[finite(six_cell['cost_bps']).eq(primary_cost) & six_cell['context_stratum'].astype(str).eq('all_steps')], ['split_bucket', 'cell_id', 'cell_step_n', 'continue_return_sum', 'policy_net_return_sum', 'incremental_return_sum', 'drawdown_avoided_abs_sum', 'six_cell_reconciliation_status'], max_rows=24)}

六格 reconciliation 覆盖 defended/continued x positive/negative/neutral，并按 `(split, context, cost)` 独立核对总 incremental utility。

## 7. Positive Sacrifice And Negative Avoidance

{markdown_table(positive_primary, ['split_bucket', 'defended_positive_n', 'defended_positive_continue_return_mean', 'defended_positive_incremental_return_sum', 'positive_upside_sacrificed_abs_sum'])}

{markdown_table(negative_primary, ['split_bucket', 'defended_negative_n', 'defended_negative_continue_return_mean', 'defended_negative_incremental_return_sum', 'defended_negative_drawdown_avoided_abs_mean', 'defended_negative_avoided_loss_abs_sum'])}

## 8. Continued Negative Leakage And Neutral Rows

{markdown_table(leakage_primary, ['split_bucket', 'continued_negative_n', 'continued_negative_residual_loss_abs', 'defended_negative_avoided_loss_abs', 'continued_negative_residual_loss_share', 'continued_negative_leakage_caveat'])}

{markdown_table(neutral_primary, ['split_bucket', 'neutral_step_n', 'neutral_defended_n', 'neutral_continued_n', 'neutral_continue_return_mean', 'neutral_incremental_return_mean', 'neutral_utility_gate'])}

## 9. Context Utility

{markdown_table(context_primary, ['split_bucket', 'context_stratum', 'labelable_step_n', 'defended_labelable_step_n', 'full_denominator_mean_incremental_return', 'full_denominator_mean_drawdown_avoided_abs', 'valid_context_power', 'context_utility_status'], max_rows=20)}

Non-known-failed context 是 primary context gate；known-failed context 只能解释集中性，不能 rescue 非 known-failed 失败。

## 10. Cost And Delay Stress

{markdown_table(delay_primary, ['split_bucket', 'labelable_step_n', 'defended_labelable_step_n', 'primary_close_to_close_mean_incremental_return', 'delay_stress_mean_incremental_return', 'primary_minus_delay_delta', 'cost_delay_stress_status'])}

## 11. Validation Stress Caveat

{markdown_table(validation_primary, ['stress_split_id', 'labelable_step_n', 'defended_labelable_step_n', 'full_denominator_mean_incremental_return', 'delay_stress_mean_incremental_return', 'validation_used_for_selection', 'validation_blocks_decision', 'validation_stress_status', 'validation_stress_caveat'])}

Validation stress 只作 out-of-sample stress readout；不参与 16E action semantics、cost、context 或 threshold selection，也不单独阻塞裁决。

## 12. Search Accounting

{markdown_table(search, ['search_family', 'primary_policy_id', 'primary_action_semantics_id', 'primary_round_trip_defense_cost_bps', 'validation_used_for_selection', 'robustness_used_for_selection', 'return_metric_used_for_selection', 'cost_metric_used_for_selection', 'context_filter_used_for_selection', 'search_accounting_gate'])}

## 13. Findings And Insight

16E 只回答单个 h20 block 内 defend-vs-continue 的 utility 是否足以进入 16F transition freeze。若裁决不是 ready，后续不得把 16D/16E 的 action 解释成完整 exit、holding、portfolio backtest 或 deployment policy。
"""


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: pd.DataFrame, outputs: dict[str, Path]) -> Path:
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
    dec = decision.iloc[0].to_dict() if not decision.empty else {}
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
        "upstream_16d_decision": config["policy"]["required_16d_decision"],
        "primary_label_id": config["policy"]["primary_label_id"],
        "selected_threshold_id": config["policy"]["selected_threshold_id"],
        "primary_horizon_sessions": config["policy"]["primary_horizon_sessions"],
        "primary_model_id": config["policy"]["primary_model_id"],
        "primary_policy_id": config["policy"]["primary_policy_id"],
        "primary_action_semantics_id": config["action_semantics"]["primary_action_semantics_id"],
        "primary_round_trip_defense_cost_bps": config["action_semantics"]["primary_round_trip_defense_cost_bps"],
        "decision_state": dec.get("decision_state", ""),
        "next_allowed_requirement": dec.get("next_allowed_requirement", ""),
        "continued_negative_leakage_caveat": dec.get("continued_negative_leakage_caveat", ""),
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
            key: file_sha(path_value)
            for key, path_value in resolve_paths(config).items()
            if path_value.exists() and path_value.is_file()
        },
        "output_hashes": hashes,
        "row_counts": row_counts,
        "large_artifact_policy": "full utility panel is local parquet; publishable utility panel is sampled csv.gz",
    }
    return write_json(path, payload)


def initial_blocked_decision(config: dict[str, Any], reason: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "decision_state": DECISION_LINEAGE,
                "next_allowed_requirement": "none",
                "primary_label_id": config["policy"]["primary_label_id"],
                "primary_model_id": config["policy"]["primary_model_id"],
                "primary_policy_id": config["policy"]["primary_policy_id"],
                "primary_action_semantics_id": config["action_semantics"]["primary_action_semantics_id"],
                "primary_round_trip_defense_cost_bps": config["action_semantics"]["primary_round_trip_defense_cost_bps"],
                "primary_return_utility_gate": "fail",
                "drawdown_avoidance_gate": "fail",
                "delay_stress_gate": "fail",
                "context_power_gate": "fail",
                "context_utility_gate": "fail",
                "six_cell_reconciliation_gate": "fail",
                "continued_negative_leakage_caveat": "",
                "utility_interpretation": "blocked_by_input_or_lineage_failure",
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
        decision = initial_blocked_decision(config, input_reason)
        write_df(outputs["decision"], decision)
        write_manifest(outputs["manifest"], config_path, config, decision, outputs)
        return 1

    upstream = build_upstream_16d_authorization_audit(config, resolved)
    action_panel, action_audit = load_or_rebuild_primary_action_panel(config, resolved)
    semantics = build_single_step_action_semantics_audit(config)
    base_utility, price_audit = compute_base_price_utility(action_panel, resolved["stock_daily_qfq_dir"], config)
    utility_panel = expand_utility_panel(base_utility, config)
    policy_binding = build_policy_utility_binding_audit(action_panel, utility_panel, config)
    six_cell, six_gate = build_six_cell_utility_reconciliation(utility_panel)
    split_readout = build_utility_by_split_readout(utility_panel, config)
    context_readout = build_utility_by_context_readout(utility_panel, config)
    positive = build_positive_sacrifice_readout(utility_panel)
    negative = build_negative_avoidance_readout(utility_panel)
    leakage = build_continued_negative_leakage_readout(utility_panel, split_readout)
    neutral = build_neutral_utility_readout(utility_panel)
    delay = build_cost_delay_stress_readout(utility_panel, config)
    validation = build_validation_stress_utility_readout(utility_panel)
    search = build_search_accounting(config)
    gates = {
        "input_artifact_gate": input_gate,
        "upstream_16d_authorization_gate": upstream.loc[0, "authorization_status"],
        "full_action_panel_rebuild_gate": action_audit.loc[0, "full_action_panel_rebuild_status"],
        "utility_price_path_gate": "pass" if price_audit["utility_price_path_gate"].astype(str).eq("pass").all() else "fail",
        "action_semantics_gate": semantics.loc[0, "action_semantics_gate"],
        "policy_utility_binding_gate": policy_binding.loc[0, "policy_utility_binding_gate"],
        "six_cell_reconciliation_gate": six_gate,
        "neutral_utility_gate": "pass" if not neutral.empty and neutral["neutral_utility_gate"].astype(str).eq("pass").all() else "fail",
        "context_utility_rebuild_gate": "pass" if not context_readout.empty and context_readout["context_utility_rebuild_gate"].astype(str).eq("pass").all() else "fail",
        "search_accounting_gate": search.loc[0, "search_accounting_gate"],
    }
    decision = build_decision(config, gates, action_panel, split_readout, context_readout, delay, leakage)
    sample_n = int(config["policy"]["max_publishable_utility_panel_sample_rows"])
    sample = utility_panel.head(sample_n).copy()

    write_df(outputs["upstream_16d_authorization_audit"], upstream)
    write_df(outputs["full_action_panel_rebuild_audit"], action_audit)
    write_df(outputs["single_step_action_semantics_audit"], semantics)
    write_df(outputs["utility_price_path_audit"], price_audit)
    write_df(outputs["policy_utility_binding_audit"], policy_binding)
    write_df(outputs["six_cell_utility_reconciliation"], six_cell)
    write_df(outputs["utility_by_split_readout"], split_readout)
    write_df(outputs["utility_by_context_readout"], context_readout)
    write_df(outputs["positive_sacrifice_utility_readout"], positive)
    write_df(outputs["negative_avoidance_utility_readout"], negative)
    write_df(outputs["continued_negative_leakage_utility_readout"], leakage)
    write_df(outputs["neutral_utility_readout"], neutral)
    write_df(outputs["cost_delay_stress_readout"], delay)
    write_df(outputs["validation_stress_utility_readout"], validation)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["decision"], decision)
    write_df(outputs["utility_panel_sample"], sample)
    write_df(outputs["utility_panel"], utility_panel)
    write_text(
        outputs["report"],
        render_report(
            decision,
            upstream,
            action_audit,
            semantics,
            price_audit,
            split_readout,
            context_readout,
            six_cell,
            positive,
            negative,
            leakage,
            neutral,
            delay,
            validation,
            search,
        ),
    )
    write_manifest(outputs["manifest"], config_path, config, decision, outputs)
    return 0 if decision.loc[0, "decision_state"] != DECISION_LINEAGE else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())
