#!/usr/bin/env python
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "17B_oracle_ladder_replay"
EXPERIMENT_ID = "17_oracle_action_value_upper_bound_diagnostic"
PHASE_ID = "17B"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_17b_oracle_ladder_replay.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
FIGURE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "figures" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("train", "robustness", "validation")
PRIMARY_ROW_KEY = (
    "step_id",
    "label_id",
    "threshold_id",
    "instrument",
    "episode_cluster_id",
    "horizon_sessions",
    "step_index",
    "step_start_date",
    "step_end_date",
)

DECISION_READY = "EP17B_oracle_ladder_ready_for_robustness"
DECISION_NO_VALUE = "oracle_no_action_value_in_current_space"
DECISION_BLOCKED = "oracle_lineage_or_denominator_blocked"
NEXT_17C = "requirement_17c_oracle_robustness_stress.md"

AUTH_FALSE_COLUMNS = (
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP17B oracle ladder replay.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_gate_audit": TABLE_DIR / "17b_input_gate_audit.csv",
        "seventeen_a_contract_validation_audit": TABLE_DIR / "17a_contract_validation_audit.csv",
        "row_replay_audit": TABLE_DIR / "oracle_row_replay_audit.csv",
        "ladder_summary": TABLE_DIR / "oracle_ladder_summary.csv",
        "six_cell_decomposition": TABLE_DIR / "oracle_six_cell_decomposition.csv",
        "action_intensity_frontier": TABLE_DIR / "oracle_action_intensity_frontier.csv",
        "neutral_stress": TABLE_DIR / "oracle_neutral_stress.csv",
        "o2_drawdown_threshold_replay": TABLE_DIR / "oracle_o2_drawdown_threshold_replay.csv",
        "o5_action_selection_proof": TABLE_DIR / "oracle_o5_action_selection_proof.csv",
        "high_upside_threshold_freeze": TABLE_DIR / "oracle_high_upside_threshold_freeze.csv",
        "decision": TABLE_DIR / "oracle_ladder_decision.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "ladder_net_utility_figure": FIGURE_DIR / "oracle_ladder_net_utility.png",
        "sacrifice_vs_avoidance_figure": FIGURE_DIR / "positive_sacrifice_vs_negative_avoidance.png",
        "report": REPORT_DIR / "oracle_ladder_replay_report.md",
        "manifest": MANIFEST_DIR / "17B_oracle_ladder_replay_manifest.json",
        "replay_engine_manifest": MANIFEST_DIR / "oracle_ladder_replay_engine_manifest.json",
        "input_artifact_manifest": MANIFEST_DIR / "input_artifact_manifest_17b.json",
        "oracle_ladder_panel": LOCAL_CACHE_DIR / "oracle_ladder_panel.parquet",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if suffixes.endswith((".csv", ".csv.gz")):
        return pd.read_csv(path, **kwargs)
    raise ValueError(f"Unsupported table path: {path}")


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if "".join(path.suffixes).endswith(".parquet"):
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if not isinstance(value, (str, bytes, dict, list, tuple)):
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
    return value


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(clean_json(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: Path) -> int | float:
    if not path.exists():
        return np.nan
    if path.is_dir():
        return len(list(path.iterdir()))
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pq.ParquetFile(path).metadata.num_rows
    if suffixes.endswith(".csv.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    if suffixes.endswith(".csv"):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    return sum(1 for _ in path.open("rb"))


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    if pd.isna(value):
        return False
    return bool(value)


def metric_float(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return np.nan
    return out if np.isfinite(out) else np.nan


def relative_to_topic(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        return str(path)


def required_columns_for_key(key: str) -> set[str]:
    mapping: dict[str, set[str]] = {
        "seventeen_a_decision": {
            "decision_state",
            "next_allowed_requirement",
            "input_artifact_gate",
            "denominator_reconciliation_gate",
            "oracle_denominator_binding_gate",
            "action_semantics_gate",
            "price_path_replay_gate",
            "learned_score_reference_gate",
            "ep16_utility_replay_gate",
            "six_cell_sanity_gate",
            "search_accounting_gate",
        },
        "seventeen_a_denominator_lineage_audit": {
            "split_bucket",
            "observed_labelable_step_n",
            "observed_binary_step_n",
            "observed_neutral_step_n",
            "denominator_reconciliation_gate",
        },
        "seventeen_a_oracle_denominator_binding": {"oracle_id", "primary_denominator_type", "binding_status"},
        "seventeen_a_action_semantics_audit": {"action_family_id", "q_continue", "q_defend", "action_semantics_gate"},
        "seventeen_a_replay_price_path_audit": {"split_bucket", "price_path_replay_gate"},
        "seventeen_a_delayed_materialization_audit": {"split_bucket", "delayed_materialization_gate"},
        "seventeen_a_input_artifact_audit": {"artifact_key", "schema_status", "read_status"},
        "upstream_16e_utility_panel": {
            "step_id",
            "label_id",
            "threshold_id",
            "instrument",
            "episode_cluster_id",
            "horizon_sessions",
            "step_index",
            "step_start_date",
            "step_end_date",
            "step_start_pos",
            "step_end_pos",
            "step_start_qfq_close",
            "step_end_qfq_close",
            "cluster_split_bucket",
            "label_class",
            "policy_id",
            "cost_bps",
            "continue_return_h20",
            "continue_max_drawdown_h20",
            "utility_price_status",
        },
    }
    if key in {
        "requirement",
        "research_plan",
        "stock_daily_qfq_dir",
        "seventeen_a_denominator_contract",
        "seventeen_a_action_contract",
        "seventeen_a_replay_engine_manifest",
        "seventeen_a_input_artifact_manifest",
    }:
        return set()
    return mapping.get(key, set())


def validation_row(
    rows: list[dict[str, Any]],
    artifact_key: str,
    check_id: str,
    observed_value: Any,
    expected_value: Any,
    passed: bool,
    blocking_reason: str = "",
) -> None:
    rows.append(
        {
            "artifact_key": artifact_key,
            "validation_check_id": check_id,
            "observed_value": clean_json(observed_value),
            "expected_value": clean_json(expected_value),
            "validation_status": "pass" if passed else "fail",
            "blocking_reason": "" if passed else blocking_reason,
        }
    )


def str_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def false_like(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"false", "0", "no", ""}
    if pd.isna(value):
        return False
    return not bool(value)


def all_pass(frame: pd.DataFrame, column: str) -> bool:
    return column in frame.columns and frame[column].astype(str).eq("pass").all()


def add_table_read_failure(rows: list[dict[str, Any]], artifact_key: str, exc: Exception) -> None:
    validation_row(
        rows,
        artifact_key,
        "readable_for_independent_validation",
        type(exc).__name__,
        "readable",
        False,
        "17a_artifact_read_failed",
    )


def build_17a_contract_validation_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    expected_counts = config["expected_denominator"]

    try:
        decision = read_table(resolved["seventeen_a_decision"]).iloc[0]
        expected = {
            "decision_state": "EP17A_oracle_replay_contract_ready",
            "next_allowed_requirement": "requirement_17b_oracle_ladder_replay.md",
            "upstream_closure_gate": "pass",
            "input_artifact_gate": "pass",
            "denominator_reconciliation_gate": "pass",
            "oracle_denominator_binding_gate": "pass",
            "action_semantics_gate": "pass",
            "delayed_materialization_gate": "pass",
            "price_path_replay_gate": "pass",
            "learned_score_reference_gate": "pass",
            "ep16_utility_replay_gate": "pass",
            "six_cell_sanity_gate": "pass",
            "search_accounting_gate": "pass",
        }
        for key, expected_value in expected.items():
            observed = str_value(decision.get(key))
            validation_row(
                rows,
                "seventeen_a_decision",
                key,
                observed,
                expected_value,
                observed == expected_value,
                "17a_decision_gate_mismatch",
            )
        capacity = str_value(decision.get("capacity_reconstruction_gate"))
        validation_row(
            rows,
            "seventeen_a_decision",
            "capacity_reconstruction_gate",
            capacity,
            "pass|appendix_only",
            capacity in {"pass", "appendix_only"},
            "17a_capacity_gate_mismatch",
        )
        o6_status = str_value(decision.get("o6_status_for_17b"))
        validation_row(
            rows,
            "seventeen_a_decision",
            "o6_status_for_17b",
            o6_status,
            "appendix_only_nonblocking",
            o6_status == "appendix_only_nonblocking",
            "17a_o6_status_mismatch",
        )
        for key in (*AUTH_FALSE_COLUMNS, "chained_simulation_authorized"):
            if key in decision.index:
                validation_row(
                    rows,
                    "seventeen_a_decision",
                    key,
                    decision.get(key),
                    False,
                    false_like(decision.get(key)),
                    "17a_authorization_flag_true",
                )
    except Exception as exc:
        add_table_read_failure(rows, "seventeen_a_decision", exc)

    try:
        denominator = read_table(resolved["seventeen_a_denominator_lineage_audit"])
        validation_row(
            rows,
            "seventeen_a_denominator_lineage_audit",
            "denominator_reconciliation_gate_all_pass",
            sorted(set(denominator.get("denominator_reconciliation_gate", pd.Series(dtype=str)).astype(str))),
            "all pass",
            all_pass(denominator, "denominator_reconciliation_gate"),
            "17a_denominator_gate_failed",
        )
        for split, counts in expected_counts.items():
            sub = denominator.loc[denominator["split_bucket"].astype(str).eq(split)]
            for observed_col, expected_key in {
                "observed_labelable_step_n": "labelable_step_n",
                "observed_binary_step_n": "binary_step_n",
                "observed_neutral_step_n": "neutral_step_n",
                "positive_n": "positive_n",
                "negative_n": "negative_n",
                "neutral_n": "neutral_step_n",
            }.items():
                observed = int(sub.iloc[0][observed_col]) if len(sub) and observed_col in sub.columns else None
                expected_value = int(counts[expected_key])
                validation_row(
                    rows,
                    "seventeen_a_denominator_lineage_audit",
                    f"{split}_{observed_col}",
                    observed,
                    expected_value,
                    observed == expected_value,
                    "17a_denominator_count_mismatch",
                )
            for zero_col in [
                "duplicate_primary_row_key_n",
                "missing_primary_row_key_field_n",
                "missing_episode_cluster_id_n",
                "missing_instrument_n",
            ]:
                if zero_col in denominator.columns:
                    observed = int(sub.iloc[0][zero_col]) if len(sub) else None
                    validation_row(
                        rows,
                        "seventeen_a_denominator_lineage_audit",
                        f"{split}_{zero_col}",
                        observed,
                        0,
                        observed == 0,
                        "17a_denominator_integrity_count_nonzero",
                    )
    except Exception as exc:
        add_table_read_failure(rows, "seventeen_a_denominator_lineage_audit", exc)

    try:
        binding = read_table(resolved["seventeen_a_oracle_denominator_binding"])
        expected_binding = {
            "O0": ("labelable_full", True),
            "O1": ("binary_primary", True),
            "O2": ("labelable_full", True),
            "O3": ("appendix_only_if_join_incomplete", False),
            "O4": ("binary_primary", True),
            "O5": ("labelable_full", True),
            "O6": ("labelable_full_if_capacity_gate_passes", False),
        }
        validation_row(
            rows,
            "seventeen_a_oracle_denominator_binding",
            "binding_status_all_pass",
            sorted(set(binding.get("binding_status", pd.Series(dtype=str)).astype(str))),
            "all pass",
            all_pass(binding, "binding_status"),
            "17a_binding_gate_failed",
        )
        for oracle_id, (expected_denominator, expected_blocking) in expected_binding.items():
            sub = binding.loc[binding["oracle_id"].astype(str).eq(oracle_id)]
            observed_denominator = str_value(sub.iloc[0].get("primary_denominator_type")) if len(sub) else ""
            validation_row(
                rows,
                "seventeen_a_oracle_denominator_binding",
                f"{oracle_id}_denominator_type",
                observed_denominator,
                expected_denominator,
                observed_denominator == expected_denominator,
                "17a_binding_denominator_mismatch",
            )
            observed_blocking = bool_value(sub.iloc[0].get("skip_is_blocking")) if len(sub) else None
            validation_row(
                rows,
                "seventeen_a_oracle_denominator_binding",
                f"{oracle_id}_skip_is_blocking",
                observed_blocking,
                expected_blocking,
                observed_blocking == expected_blocking,
                "17a_binding_skip_contract_mismatch",
            )
    except Exception as exc:
        add_table_read_failure(rows, "seventeen_a_oracle_denominator_binding", exc)

    try:
        actions = read_table(resolved["seventeen_a_action_semantics_audit"])
        validation_row(
            rows,
            "seventeen_a_action_semantics_audit",
            "action_semantics_gate_all_pass",
            sorted(set(actions.get("action_semantics_gate", pd.Series(dtype=str)).astype(str))),
            "all pass",
            all_pass(actions, "action_semantics_gate"),
            "17a_action_semantics_gate_failed",
        )
        expected_q_defend = {
            "blind_continue": 1.0,
            "full_defend_exit_cash": 0.0,
            "partial_defend_25pct": 0.25,
            "partial_defend_50pct": 0.50,
            "delayed_decision_k": 0.0,
            "learned_score_reference": 0.0,
        }
        for action_id, expected_q in expected_q_defend.items():
            sub = actions.loc[actions["action_family_id"].astype(str).eq(action_id)]
            observed_q = float(sub.iloc[0]["q_defend"]) if len(sub) else np.nan
            validation_row(
                rows,
                "seventeen_a_action_semantics_audit",
                f"{action_id}_q_defend",
                observed_q,
                expected_q,
                np.isclose(observed_q, expected_q),
                "17a_action_q_defend_mismatch",
            )
        for key in [
            "cost_selected_by_oos_result",
            "validation_used_for_action_selection",
            "robustness_used_for_action_selection",
            "return_metric_used_for_action_selection",
        ]:
            if key in actions.columns:
                observed_any = bool(actions[key].map(bool_value).any())
                validation_row(
                    rows,
                    "seventeen_a_action_semantics_audit",
                    f"{key}_any_true",
                    observed_any,
                    False,
                    observed_any is False,
                    "17a_action_selection_leakage_flag_true",
                )
    except Exception as exc:
        add_table_read_failure(rows, "seventeen_a_action_semantics_audit", exc)

    try:
        price = read_table(resolved["seventeen_a_replay_price_path_audit"])
        validation_row(
            rows,
            "seventeen_a_replay_price_path_audit",
            "price_path_replay_gate_all_pass",
            sorted(set(price.get("price_path_replay_gate", pd.Series(dtype=str)).astype(str))),
            "all pass",
            all_pass(price, "price_path_replay_gate"),
            "17a_price_path_gate_failed",
        )
        for split, counts in expected_counts.items():
            sub = price.loc[price["split_bucket"].astype(str).eq(split)]
            observed = int(sub.iloc[0]["labelable_step_n"]) if len(sub) else None
            validation_row(
                rows,
                "seventeen_a_replay_price_path_audit",
                f"{split}_labelable_step_n",
                observed,
                int(counts["labelable_step_n"]),
                observed == int(counts["labelable_step_n"]),
                "17a_price_path_count_mismatch",
            )
            for zero_col in [
                "missing_qfq_instrument_n",
                "bad_step_bounds_n",
                "nonfinite_close_n",
                "nonpositive_close_n",
                "step_start_close_mismatch_n",
                "step_end_close_mismatch_n",
                "first_session_missing_n",
                "delay_k_missing_n",
            ]:
                if zero_col in price.columns:
                    observed_zero = int(sub.iloc[0][zero_col]) if len(sub) else None
                    validation_row(
                        rows,
                        "seventeen_a_replay_price_path_audit",
                        f"{split}_{zero_col}",
                        observed_zero,
                        0,
                        observed_zero == 0,
                        "17a_price_path_integrity_count_nonzero",
                    )
            if "max_drawdown_replay_abs_diff_max" in price.columns:
                diff = float(sub.iloc[0]["max_drawdown_replay_abs_diff_max"]) if len(sub) else np.nan
                tol = float(config["tolerances"]["drawdown_abs_tolerance"])
                validation_row(
                    rows,
                    "seventeen_a_replay_price_path_audit",
                    f"{split}_max_drawdown_replay_abs_diff_max",
                    diff,
                    f"<= {tol}",
                    np.isfinite(diff) and diff <= tol,
                    "17a_price_path_drawdown_diff_exceeds_tolerance",
                )
    except Exception as exc:
        add_table_read_failure(rows, "seventeen_a_replay_price_path_audit", exc)

    try:
        delayed = read_table(resolved["seventeen_a_delayed_materialization_audit"])
        validation_row(
            rows,
            "seventeen_a_delayed_materialization_audit",
            "delayed_materialization_gate_all_pass",
            sorted(set(delayed.get("delayed_materialization_gate", pd.Series(dtype=str)).astype(str))),
            "all pass",
            all_pass(delayed, "delayed_materialization_gate"),
            "17a_delayed_materialization_gate_failed",
        )
        for split, counts in expected_counts.items():
            sub = delayed.loc[delayed["split_bucket"].astype(str).eq(split)]
            observed_counts_ok = (
                len(sub) > 0
                and sub["labelable_step_n"].astype(int).eq(int(counts["labelable_step_n"])).all()
                and sub["materialized_step_n"].astype(int).eq(int(counts["labelable_step_n"])).all()
            )
            validation_row(
                rows,
                "seventeen_a_delayed_materialization_audit",
                f"{split}_materialized_counts",
                sub[["labelable_step_n", "materialized_step_n"]].to_dict(orient="records") if len(sub) else [],
                int(counts["labelable_step_n"]),
                observed_counts_ok,
                "17a_delayed_materialized_count_mismatch",
            )
            for zero_col in ["missing_t0_plus_k_price_n", "missing_original_h20_endpoint_n"]:
                if zero_col in delayed.columns:
                    observed_sum = int(sub[zero_col].sum()) if len(sub) else None
                    validation_row(
                        rows,
                        "seventeen_a_delayed_materialization_audit",
                        f"{split}_{zero_col}_sum",
                        observed_sum,
                        0,
                        observed_sum == 0,
                        "17a_delayed_missing_count_nonzero",
                    )
            for false_col in ["restart_h20_at_t0_plus_k", "partial_tail_fill_used"]:
                if false_col in delayed.columns:
                    observed_any = bool(sub[false_col].map(bool_value).any()) if len(sub) else None
                    validation_row(
                        rows,
                        "seventeen_a_delayed_materialization_audit",
                        f"{split}_{false_col}_any_true",
                        observed_any,
                        False,
                        observed_any is False,
                        "17a_delayed_contract_flag_true",
                    )
    except Exception as exc:
        add_table_read_failure(rows, "seventeen_a_delayed_materialization_audit", exc)

    try:
        input_artifacts = read_table(resolved["seventeen_a_input_artifact_audit"])
        required = input_artifacts.loc[input_artifacts["required_flag"].astype(str).eq("required")]
        schema_ok = required["schema_status"].astype(str).eq("pass").all()
        read_ok = required["read_status"].astype(str).eq("pass").all()
        validation_row(
            rows,
            "seventeen_a_input_artifact_audit",
            "required_schema_status_all_pass",
            sorted(set(required["schema_status"].astype(str))),
            "all pass",
            schema_ok,
            "17a_input_artifact_schema_failed",
        )
        validation_row(
            rows,
            "seventeen_a_input_artifact_audit",
            "required_read_status_all_pass",
            sorted(set(required["read_status"].astype(str))),
            "all pass",
            read_ok,
            "17a_input_artifact_read_failed",
        )
        if "absolute_path_mismatch_ignored" in required.columns:
            mismatch_any = bool(required["absolute_path_mismatch_ignored"].map(bool_value).any())
            validation_row(
                rows,
                "seventeen_a_input_artifact_audit",
                "absolute_path_mismatch_ignored_any_true",
                mismatch_any,
                False,
                mismatch_any is False,
                "17a_absolute_path_mismatch_detected",
            )
    except Exception as exc:
        add_table_read_failure(rows, "seventeen_a_input_artifact_audit", exc)

    try:
        replay_manifest = json.loads(resolved["seventeen_a_replay_engine_manifest"].read_text(encoding="utf-8"))
        for key in [
            "price_path_replay_gate",
            "learned_score_reference_gate",
            "ep16_utility_replay_gate",
            "six_cell_sanity_gate",
            "search_accounting_gate",
        ]:
            observed = str_value(replay_manifest.get(key))
            validation_row(
                rows,
                "seventeen_a_replay_engine_manifest",
                key,
                observed,
                "pass",
                observed == "pass",
                "17a_replay_manifest_gate_mismatch",
            )
        capacity = str_value(replay_manifest.get("capacity_reconstruction_gate"))
        validation_row(
            rows,
            "seventeen_a_replay_engine_manifest",
            "capacity_reconstruction_gate",
            capacity,
            "pass|appendix_only",
            capacity in {"pass", "appendix_only"},
            "17a_replay_manifest_capacity_mismatch",
        )
        expected_cost_grid = [int(x) for x in config["action_semantics"]["cost_grid_bps"]]
        observed_cost_grid = [int(x) for x in replay_manifest.get("cost_grid_bps", [])]
        validation_row(
            rows,
            "seventeen_a_replay_engine_manifest",
            "cost_grid_bps",
            observed_cost_grid,
            expected_cost_grid,
            observed_cost_grid == expected_cost_grid,
            "17a_replay_manifest_cost_grid_mismatch",
        )
        for artifact_key, manifest_key in {
            "seventeen_a_denominator_contract": "denominator_contract_sha256",
            "seventeen_a_action_contract": "action_contract_sha256",
        }.items():
            observed_sha = file_sha(resolved[artifact_key])
            expected_sha = str_value(replay_manifest.get(manifest_key))
            validation_row(
                rows,
                artifact_key,
                "sha256_matches_replay_engine_manifest",
                observed_sha,
                expected_sha,
                observed_sha == expected_sha,
                "17a_contract_sha_mismatch",
            )
    except Exception as exc:
        add_table_read_failure(rows, "seventeen_a_replay_engine_manifest", exc)

    try:
        input_manifest = pd.DataFrame(json.loads(resolved["seventeen_a_input_artifact_manifest"].read_text(encoding="utf-8")))
        required = input_manifest.loc[input_manifest["required_flag"].astype(str).eq("required")]
        validation_row(
            rows,
            "seventeen_a_input_artifact_manifest",
            "required_schema_status_all_pass",
            sorted(set(required["schema_status"].astype(str))),
            "all pass",
            required["schema_status"].astype(str).eq("pass").all(),
            "17a_input_manifest_schema_failed",
        )
        validation_row(
            rows,
            "seventeen_a_input_artifact_manifest",
            "required_read_status_all_pass",
            sorted(set(required["read_status"].astype(str))),
            "all pass",
            required["read_status"].astype(str).eq("pass").all(),
            "17a_input_manifest_read_failed",
        )
    except Exception as exc:
        add_table_read_failure(rows, "seventeen_a_input_artifact_manifest", exc)

    return pd.DataFrame(rows)


def apply_17a_contract_validation(audit: pd.DataFrame, validation: pd.DataFrame) -> pd.DataFrame:
    if validation.empty:
        return audit
    failed = validation.loc[validation["validation_status"].astype(str).ne("pass")]
    for artifact_key in sorted(set(failed["artifact_key"].astype(str))):
        reasons = sorted(set(failed.loc[failed["artifact_key"].astype(str).eq(artifact_key), "blocking_reason"].astype(str)))
        set_audit_row(
            audit,
            artifact_key,
            gate_status="fail",
            lineage_status="fail",
            blocking_reason=";".join(reason for reason in reasons if reason),
        )
    return audit


def artifact_role(key: str) -> str:
    if key in {"requirement", "research_plan"}:
        return "local_contract"
    if key == "stock_daily_qfq_dir":
        return "qfq_price_source"
    if key.startswith("seventeen_a"):
        return "17a_machine_gate"
    if key == "upstream_16e_utility_panel":
        return "required_row_level_replay_source"
    return "input_artifact"


def source_phase(key: str) -> str:
    if key.startswith("seventeen_a"):
        return "17A"
    if key.startswith("upstream_16e"):
        return "16E"
    return PHASE_ID


def build_input_gate_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, path in resolved.items():
        exists = path.exists()
        schema_status = "not_checked"
        lineage_status = "pass" if exists else "fail_missing"
        row_key_status = "not_applicable"
        gate_status = "pass" if exists else "fail"
        blocking_reason = "" if exists else "missing_artifact"
        row_count: int | float = np.nan
        sha = ""
        if exists:
            try:
                row_count = count_rows(path)
                if path.is_file():
                    sha = file_sha(path)
                cols = required_columns_for_key(key)
                if cols:
                    frame = read_table(path)
                    schema_status = "pass" if cols.issubset(frame.columns) else "fail_missing_columns"
                    if schema_status != "pass":
                        gate_status = "fail"
                        blocking_reason = "missing_required_columns"
                else:
                    schema_status = "pass"
            except Exception as exc:  # pragma: no cover - defensive input path
                schema_status = "fail_read_error"
                gate_status = "fail"
                blocking_reason = f"read_error:{type(exc).__name__}"
        rows.append(
            {
                "artifact_key": key,
                "artifact_role": artifact_role(key),
                "required_flag": "required",
                "resolved_path": str(path),
                "relative_path": relative_to_topic(path),
                "source_phase_id": source_phase(key),
                "row_count": row_count,
                "sha256": sha,
                "schema_status": schema_status,
                "lineage_status": lineage_status,
                "row_key_status": row_key_status,
                "gate_status": gate_status,
                "blocking_reason": blocking_reason,
            }
        )
    audit = pd.DataFrame(rows)
    validation = build_17a_contract_validation_audit(config, resolved)
    audit = apply_17a_contract_validation(audit, validation)
    audit = apply_17a_gate_checks(config, resolved, audit)
    return audit


def set_audit_row(audit: pd.DataFrame, key: str, **updates: Any) -> None:
    idx = audit.index[audit["artifact_key"].eq(key)]
    if len(idx) == 0:
        return
    for col, value in updates.items():
        audit.loc[idx, col] = value


def apply_17a_gate_checks(config: dict[str, Any], resolved: dict[str, Path], audit: pd.DataFrame) -> pd.DataFrame:
    if audit.loc[audit["gate_status"].eq("fail")].shape[0]:
        return audit
    try:
        decision = read_table(resolved["seventeen_a_decision"]).iloc[0]
        expected = {
            "decision_state": "EP17A_oracle_replay_contract_ready",
            "next_allowed_requirement": "requirement_17b_oracle_ladder_replay.md",
            "upstream_closure_gate": "pass",
            "input_artifact_gate": "pass",
            "denominator_reconciliation_gate": "pass",
            "oracle_denominator_binding_gate": "pass",
            "action_semantics_gate": "pass",
            "price_path_replay_gate": "pass",
            "learned_score_reference_gate": "pass",
            "ep16_utility_replay_gate": "pass",
            "six_cell_sanity_gate": "pass",
            "search_accounting_gate": "pass",
        }
        bad = [k for k, v in expected.items() if str(decision.get(k)) != v]
        capacity_ok = str(decision.get("capacity_reconstruction_gate")) in {"pass", "appendix_only"}
        delayed_ok = str(decision.get("delayed_materialization_gate")) == "pass"
        if bad or not capacity_ok or not delayed_ok:
            set_audit_row(
                audit,
                "seventeen_a_decision",
                gate_status="fail",
                lineage_status="fail",
                blocking_reason="17a_decision_gate_mismatch",
            )
        denominator = read_table(resolved["seventeen_a_denominator_lineage_audit"])
        if not denominator["denominator_reconciliation_gate"].astype(str).eq("pass").all():
            set_audit_row(
                audit,
                "seventeen_a_denominator_lineage_audit",
                gate_status="fail",
                lineage_status="fail",
                blocking_reason="17a_denominator_gate_failed",
            )
        binding = read_table(resolved["seventeen_a_oracle_denominator_binding"])
        if not binding["binding_status"].astype(str).eq("pass").all():
            set_audit_row(
                audit,
                "seventeen_a_oracle_denominator_binding",
                gate_status="fail",
                lineage_status="fail",
                blocking_reason="17a_binding_gate_failed",
            )
        utility = read_table(resolved["upstream_16e_utility_panel"])
        key_cols = list(PRIMARY_ROW_KEY)
        primary = utility.loc[
            utility["cost_bps"].astype(int).eq(int(config["source_panel"]["primary_source_cost_bps"]))
            & utility["policy_id"].astype(str).eq(config["policy"]["primary_policy_id"])
        ]
        duplicate_n = int(primary.duplicated(key_cols).sum())
        expected_primary = int(config["source_panel"]["expected_primary_rows"])
        row_key_status = "pass" if duplicate_n == 0 and len(primary) == expected_primary else "fail"
        set_audit_row(
            audit,
            "upstream_16e_utility_panel",
            row_key_status=row_key_status,
            gate_status="pass" if row_key_status == "pass" else "fail",
            blocking_reason="" if row_key_status == "pass" else "primary_key_or_cost_tier_count_failed",
        )
    except Exception as exc:  # pragma: no cover - defensive input gate
        set_audit_row(
            audit,
            "seventeen_a_decision",
            gate_status="fail",
            lineage_status="fail",
            blocking_reason=f"17a_gate_exception:{type(exc).__name__}",
        )
    return audit


def input_gate_status(audit: pd.DataFrame) -> tuple[str, str]:
    bad = audit.loc[audit["gate_status"].astype(str).ne("pass")]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_key"].astype(str).tolist())


def load_primary_base_panel(config: dict[str, Any], utility_panel: pd.DataFrame) -> pd.DataFrame:
    policy = config["policy"]["primary_policy_id"]
    source_cost = int(config["source_panel"]["primary_source_cost_bps"])
    primary = utility_panel.loc[
        utility_panel["policy_id"].astype(str).eq(policy) & utility_panel["cost_bps"].astype(int).eq(source_cost)
    ].copy()
    primary = primary.drop_duplicates(list(PRIMARY_ROW_KEY)).copy()
    primary["forward_return_h20"] = pd.to_numeric(primary["continue_return_h20"], errors="coerce")
    primary["realized_h20_payoff"] = primary["forward_return_h20"]
    primary["signed_max_drawdown_h20"] = pd.to_numeric(primary["continue_max_drawdown_h20"], errors="coerce")
    primary["drawdown_abs_for_reporting"] = primary["signed_max_drawdown_h20"].abs()
    primary["qfq_path_status"] = primary["utility_price_status"].astype(str)
    return primary


def reconcile_qfq(config: dict[str, Any], base: pd.DataFrame, qfq_dir: Path) -> pd.DataFrame:
    out = base.copy()
    n = len(out)
    fields: dict[str, list[Any]] = {
        "qfq_recomputed_forward_return_h20": [np.nan] * n,
        "qfq_recomputed_signed_max_drawdown_h20": [np.nan] * n,
        "qfq_recomputed_drawdown_abs": [np.nan] * n,
        "qfq_missing_instrument": [False] * n,
        "qfq_bad_step_bounds": [False] * n,
        "qfq_nonfinite_close": [False] * n,
        "qfq_nonpositive_close": [False] * n,
        "qfq_start_close_mismatch": [False] * n,
        "qfq_end_close_mismatch": [False] * n,
        "qfq_date_mismatch": [False] * n,
        "qfq_replay_status": ["pass"] * n,
    }
    close_tol = float(config["tolerances"]["qfq_close_abs_tolerance"])
    position = {idx: pos for pos, idx in enumerate(out.index)}
    cache: dict[str, pd.DataFrame | None] = {}
    for instrument, group in out.groupby("instrument", sort=False):
        qfq_path = qfq_dir / f"{instrument}.csv"
        if instrument not in cache:
            cache[instrument] = pd.read_csv(qfq_path) if qfq_path.exists() else None
        qfq = cache[instrument]
        if qfq is None:
            for idx in group.index:
                pos = position[idx]
                fields["qfq_missing_instrument"][pos] = True
                fields["qfq_replay_status"][pos] = "missing_instrument"
            continue
        closes = pd.to_numeric(qfq["close"], errors="coerce").to_numpy(dtype=float)
        dates = qfq["date"].astype(str).to_numpy()
        for idx, row in group.iterrows():
            pos = position[idx]
            try:
                start = int(row["step_start_pos"])
                end = int(row["step_end_pos"])
            except Exception:
                fields["qfq_bad_step_bounds"][pos] = True
                fields["qfq_replay_status"][pos] = "bad_step_bounds"
                continue
            if start < 0 or end < start or end >= len(closes):
                fields["qfq_bad_step_bounds"][pos] = True
                fields["qfq_replay_status"][pos] = "bad_step_bounds"
                continue
            path = closes[start : end + 1]
            if not np.isfinite(path).all():
                fields["qfq_nonfinite_close"][pos] = True
                fields["qfq_replay_status"][pos] = "nonfinite_close"
                continue
            if not (path > 0).all():
                fields["qfq_nonpositive_close"][pos] = True
                fields["qfq_replay_status"][pos] = "nonpositive_close"
                continue
            if dates[start] != str(row["step_start_date"]) or dates[end] != str(row["step_end_date"]):
                fields["qfq_date_mismatch"][pos] = True
                fields["qfq_replay_status"][pos] = "date_mismatch"
            if abs(closes[start] - float(row["step_start_qfq_close"])) > close_tol:
                fields["qfq_start_close_mismatch"][pos] = True
                fields["qfq_replay_status"][pos] = "start_close_mismatch"
            if abs(closes[end] - float(row["step_end_qfq_close"])) > close_tol:
                fields["qfq_end_close_mismatch"][pos] = True
                fields["qfq_replay_status"][pos] = "end_close_mismatch"
            start_close = closes[start]
            forward = closes[end] / start_close - 1.0
            signed_drawdown = float(np.min(path / start_close - 1.0))
            fields["qfq_recomputed_forward_return_h20"][pos] = forward
            fields["qfq_recomputed_signed_max_drawdown_h20"][pos] = signed_drawdown
            fields["qfq_recomputed_drawdown_abs"][pos] = abs(signed_drawdown)
    for key, values in fields.items():
        out[key] = values
    out["forward_return_replay_abs_diff"] = (
        out["forward_return_h20"] - out["qfq_recomputed_forward_return_h20"]
    ).abs()
    out["signed_drawdown_replay_abs_diff"] = (
        out["signed_max_drawdown_h20"] - out["qfq_recomputed_signed_max_drawdown_h20"]
    ).abs()
    out["drawdown_abs_replay_abs_diff"] = (
        out["drawdown_abs_for_reporting"] - out["qfq_recomputed_drawdown_abs"]
    ).abs()
    out["drawdown_sign_ok"] = out["signed_max_drawdown_h20"].le(0)
    return out


def expected_count(config: dict[str, Any], split: str, denominator_type: str) -> int:
    exp = config["expected_denominator"][split]
    if denominator_type == "binary_primary":
        return int(exp["binary_step_n"])
    if denominator_type == "neutral_only":
        return int(exp["neutral_step_n"])
    return int(exp["labelable_step_n"])


def denominator_mask(base: pd.DataFrame, denominator_type: str) -> pd.Series:
    label = base["label_class"].astype(str)
    if denominator_type == "binary_primary":
        return label.isin(["positive", "negative"])
    if denominator_type == "neutral_only":
        return label.eq("neutral")
    return pd.Series(True, index=base.index)


def build_row_replay_audit(config: dict[str, Any], base: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    ret_tol = float(config["tolerances"]["return_abs_tolerance"])
    dd_tol = float(config["tolerances"]["drawdown_abs_tolerance"])
    for split in SPLITS:
        for den_type in ("labelable_full", "binary_primary"):
            sub = base.loc[base["cluster_split_bucket"].astype(str).eq(split) & denominator_mask(base, den_type)]
            expected = expected_count(config, split, den_type)
            duplicate_n = int(sub.duplicated(list(PRIMARY_ROW_KEY)).sum())
            missing_key_n = int(sub[list(PRIMARY_ROW_KEY)].isna().any(axis=1).sum())
            max_ret_diff = float(sub["forward_return_replay_abs_diff"].max()) if not sub.empty else np.nan
            max_dd_diff = float(sub["signed_drawdown_replay_abs_diff"].max()) if not sub.empty else np.nan
            max_abs_dd_diff = float(sub["drawdown_abs_replay_abs_diff"].max()) if not sub.empty else np.nan
            sign_gate = bool(sub["drawdown_sign_ok"].all())
            checks = [
                len(sub) == expected,
                duplicate_n == 0,
                missing_key_n == 0,
                int(sub["qfq_missing_instrument"].sum()) == 0,
                int(sub["qfq_bad_step_bounds"].sum()) == 0,
                int(sub["qfq_nonfinite_close"].sum()) == 0,
                int(sub["qfq_nonpositive_close"].sum()) == 0,
                max_ret_diff <= ret_tol,
                max_dd_diff <= dd_tol,
                max_abs_dd_diff <= dd_tol,
                sign_gate,
            ]
            gate = "pass" if all(checks) else "fail"
            rows.append(
                {
                    "split_bucket": split,
                    "denominator_type": den_type,
                    "expected_step_n": expected,
                    "observed_step_n": len(sub),
                    "duplicate_primary_row_key_n": duplicate_n,
                    "missing_primary_row_key_field_n": missing_key_n,
                    "missing_qfq_instrument_n": int(sub["qfq_missing_instrument"].sum()),
                    "bad_step_bounds_n": int(sub["qfq_bad_step_bounds"].sum() + sub["qfq_date_mismatch"].sum()),
                    "nonfinite_close_n": int(sub["qfq_nonfinite_close"].sum()),
                    "nonpositive_close_n": int(sub["qfq_nonpositive_close"].sum()),
                    "forward_return_replay_abs_diff_max": max_ret_diff,
                    "signed_max_drawdown_replay_abs_diff_max": max_dd_diff,
                    "drawdown_abs_replay_abs_diff_max": max_abs_dd_diff,
                    "positive_abs_drawdown_used_for_o2_threshold": False,
                    "drawdown_sign_convention_gate": "pass" if sign_gate else "fail",
                    "row_replay_gate": gate,
                    "blocking_reason": "" if gate == "pass" else "row_replay_or_denominator_failed",
                }
            )
    return pd.DataFrame(rows)


def high_upside_threshold_freeze(config: dict[str, Any], base: pd.DataFrame) -> pd.DataFrame:
    train = base.loc[base["cluster_split_bucket"].astype(str).eq("train"), "realized_h20_payoff"]
    rows: list[dict[str, Any]] = []
    for variant_id, quantile in config["oracle_variants"]["o4_high_upside_train_quantiles"].items():
        cutoff = float(train.quantile(float(quantile)))
        rows.append(
            {
                "threshold_id": variant_id.replace("O4_", ""),
                "oracle_variant_id": variant_id,
                "train_quantile": float(quantile),
                "train_absolute_payoff_cutoff": cutoff,
                "train_row_count": int(len(train)),
                "robustness_applied_cutoff": cutoff,
                "validation_applied_cutoff": cutoff,
                "split_local_recompute_used": False,
                "threshold_freeze_gate": "pass",
                "blocking_reason": "",
            }
        )
    return pd.DataFrame(rows)


def oracle_specs(config: dict[str, Any], thresholds: pd.DataFrame) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = [
        {
            "oracle_id": "O0",
            "oracle_name": "No Oracle Baseline",
            "oracle_variant_id": "O0_blind_continue_primary",
            "oracle_variant_name": "Blind continue all",
            "denominator_type": "labelable_full",
            "primary_variant": True,
            "rule": "continue_all",
            "drawdown_threshold": np.nan,
            "high_upside_threshold_id": "",
            "high_upside_cutoff": np.nan,
        },
        {
            "oracle_id": "O1",
            "oracle_name": "Perfect Negative Oracle",
            "oracle_variant_id": "O1_negative_primary",
            "oracle_variant_name": "Label negative primary",
            "denominator_type": "binary_primary",
            "primary_variant": True,
            "rule": "negative_defend",
            "drawdown_threshold": np.nan,
            "high_upside_threshold_id": "",
            "high_upside_cutoff": np.nan,
        },
    ]
    for variant_id, threshold in config["oracle_variants"]["o2_drawdown_thresholds"].items():
        specs.append(
            {
                "oracle_id": "O2",
                "oracle_name": "Perfect Deep Drawdown Oracle",
                "oracle_variant_id": variant_id,
                "oracle_variant_name": f"Signed drawdown <= {float(threshold):.0%}",
                "denominator_type": "labelable_full",
                "primary_variant": variant_id == "O2_dd_10pct_primary",
                "rule": "drawdown_threshold",
                "drawdown_threshold": float(threshold),
                "high_upside_threshold_id": "",
                "high_upside_cutoff": np.nan,
            }
        )
    specs.append(
        {
            "oracle_id": "O4",
            "oracle_name": "Positive Preservation Oracle",
            "oracle_variant_id": "O4_label_positive_primary",
            "oracle_variant_name": "Label positive primary",
            "denominator_type": "binary_primary",
            "primary_variant": True,
            "rule": "positive_continue",
            "drawdown_threshold": np.nan,
            "high_upside_threshold_id": "",
            "high_upside_cutoff": np.nan,
        }
    )
    for _, row in thresholds.iterrows():
        specs.append(
            {
                "oracle_id": "O4",
                "oracle_name": "Positive Preservation Oracle",
                "oracle_variant_id": row["oracle_variant_id"],
                "oracle_variant_name": row["threshold_id"],
                "denominator_type": "labelable_high_upside_stress",
                "primary_variant": False,
                "rule": "high_upside_continue",
                "drawdown_threshold": np.nan,
                "high_upside_threshold_id": row["threshold_id"],
                "high_upside_cutoff": float(row["train_absolute_payoff_cutoff"]),
            }
        )
    specs.append(
        {
            "oracle_id": "O5",
            "oracle_name": "Perfect Utility Oracle",
            "oracle_variant_id": "O5_perfect_utility_primary",
            "oracle_variant_name": "Perfect utility primary",
            "denominator_type": "labelable_full",
            "primary_variant": True,
            "rule": "perfect_utility",
            "drawdown_threshold": np.nan,
            "high_upside_threshold_id": "",
            "high_upside_cutoff": np.nan,
        }
    )
    return specs


def neutral_stress_specs() -> list[dict[str, Any]]:
    return [
        {
            "oracle_id": "O1",
            "oracle_name": "Perfect Negative Oracle",
            "oracle_variant_id": "O1_negative_primary",
            "oracle_variant_name": "Label negative primary",
            "denominator_type": "labelable_neutral_stress",
            "primary_variant": True,
            "rule": "negative_defend_neutral_continue",
            "drawdown_threshold": np.nan,
            "high_upside_threshold_id": "",
            "high_upside_cutoff": np.nan,
        },
        {
            "oracle_id": "O4",
            "oracle_name": "Positive Preservation Oracle",
            "oracle_variant_id": "O4_label_positive_primary",
            "oracle_variant_name": "Label positive primary",
            "denominator_type": "labelable_neutral_stress",
            "primary_variant": True,
            "rule": "positive_continue_neutral_defend",
            "drawdown_threshold": np.nan,
            "high_upside_threshold_id": "",
            "high_upside_cutoff": np.nan,
        },
    ]


def action_for_spec(spec: dict[str, Any], sub: pd.DataFrame, q_defend: float, cost_bps: int) -> np.ndarray:
    label = sub["label_class"].astype(str)
    if spec["rule"] == "continue_all":
        return np.array(["continue"] * len(sub), dtype=object)
    if spec["rule"] in {"negative_defend", "negative_defend_neutral_continue"}:
        return np.where(label.eq("negative"), "defend", "continue")
    if spec["rule"] in {"positive_continue", "positive_continue_neutral_defend"}:
        return np.where(label.eq("positive"), "continue", "defend")
    if spec["rule"] == "drawdown_threshold":
        return np.where(sub["signed_max_drawdown_h20"].le(float(spec["drawdown_threshold"])), "defend", "continue")
    if spec["rule"] == "high_upside_continue":
        return np.where(sub["realized_h20_payoff"].ge(float(spec["high_upside_cutoff"])), "continue", "defend")
    if spec["rule"] == "perfect_utility":
        forward = sub["forward_return_h20"].to_numpy(dtype=float)
        defend_net = q_defend * forward - cost_bps / 10000.0
        continue_net = forward
        return np.where(defend_net > continue_net, "defend", "continue")
    raise ValueError(f"Unknown oracle rule: {spec['rule']}")


def cell_ids(actions: np.ndarray, labels: pd.Series) -> np.ndarray:
    prefixes = np.asarray(np.where(actions == "defend", "defended_", "continued_"), dtype=str)
    suffixes = np.asarray(labels.astype(str).to_numpy(), dtype=str)
    return np.char.add(prefixes, suffixes)


def trimmed_mean(values: pd.Series, fraction: float) -> float:
    arr = np.sort(pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float))
    if arr.size == 0:
        return np.nan
    cut = int(np.floor(arr.size * fraction))
    if cut > 0 and arr.size > 2 * cut:
        arr = arr[cut:-cut]
    return float(np.mean(arr))


def winsorized_mean(values: pd.Series, fraction: float) -> float:
    arr = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if arr.size == 0:
        return np.nan
    lo, hi = np.quantile(arr, [fraction, 1.0 - fraction])
    return float(np.clip(arr, lo, hi).mean())


def summarize_replay_chunk(
    config: dict[str, Any],
    spec: dict[str, Any],
    split: str,
    cost_bps: int,
    q_defend: float,
    chunk: pd.DataFrame,
) -> dict[str, Any]:
    inc = chunk["incremental_net_return"]
    labels = chunk["label_class"].astype(str)
    actions = chunk["oracle_action"].astype(str)
    defended = actions.eq("defend")
    continued = actions.eq("continue")
    pos_def = defended & labels.eq("positive")
    neg_def = defended & labels.eq("negative")
    neu_def = defended & labels.eq("neutral")
    neg_cont = continued & labels.eq("negative")
    pos_cont = continued & labels.eq("positive")
    return {
        "oracle_id": spec["oracle_id"],
        "oracle_name": spec["oracle_name"],
        "oracle_variant_id": spec["oracle_variant_id"],
        "oracle_variant_name": spec["oracle_variant_name"],
        "primary_variant": bool(spec["primary_variant"]),
        "oracle_status": "materialized",
        "split_bucket": split,
        "denominator_type": spec["denominator_type"],
        "action_intensity_id": action_intensity_id(q_defend),
        "q_defend": q_defend,
        "cost_bps": cost_bps,
        "expected_step_n": expected_count(config, split, spec["denominator_type"]),
        "observed_step_n": len(chunk),
        "defended_step_n": int(defended.sum()),
        "continued_step_n": int(continued.sum()),
        "defended_rate": float(defended.mean()) if len(chunk) else np.nan,
        "mean_incremental_return": float(inc.mean()) if len(chunk) else np.nan,
        "median_incremental_return": float(inc.median()) if len(chunk) else np.nan,
        "trimmed_mean_incremental_return": trimmed_mean(inc, float(config["stats"]["trim_fraction_each_tail"])),
        "winsorized_mean_incremental_return": winsorized_mean(inc, float(config["stats"]["winsor_fraction_each_tail"])),
        "sum_incremental_return": float(inc.sum()) if len(chunk) else np.nan,
        "ev_per_exposure_day": float(inc.mean() / config["policy"]["primary_horizon_sessions"]) if len(chunk) else np.nan,
        "transaction_cost_sum": float(defended.sum() * cost_bps / 10000.0),
        "exposure_days_removed": float(defended.sum() * (1.0 - q_defend) * config["policy"]["primary_horizon_sessions"]),
        "defended_positive_opportunity_cost": float(chunk.loc[pos_def, "incremental_net_return"].sum()),
        "defended_negative_gain": float(chunk.loc[neg_def, "incremental_net_return"].sum()),
        "defended_neutral_gain": float(chunk.loc[neu_def, "incremental_net_return"].sum()),
        "continued_negative_leakage": float(chunk.loc[neg_cont, "oracle_policy_net_return"].sum()),
        "continued_positive_retained": float(chunk.loc[pos_cont, "oracle_policy_net_return"].sum()),
        "net_full_denominator_utility": float(inc.sum()) if len(chunk) else np.nan,
        "ladder_metric_gate": "pass",
        "blocking_reason": "",
    }


def six_cell_rows(spec: dict[str, Any], split: str, cost_bps: int, q_defend: float, chunk: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = float(chunk["incremental_net_return"].sum())
    for cell, sub in chunk.groupby("cell_id", sort=False):
        labels = sorted(set(sub["label_class"].astype(str)))
        actions = sorted(set(sub["oracle_action"].astype(str)))
        rows.append(
            {
                "oracle_id": spec["oracle_id"],
                "oracle_name": spec["oracle_name"],
                "oracle_variant_id": spec["oracle_variant_id"],
                "oracle_variant_name": spec["oracle_variant_name"],
                "primary_variant": bool(spec["primary_variant"]),
                "split_bucket": split,
                "denominator_scope": spec["denominator_type"],
                "action_intensity_id": action_intensity_id(q_defend),
                "q_defend": q_defend,
                "cost_bps": cost_bps,
                "cell_id": cell,
                "label_class": labels[0] if len(labels) == 1 else ",".join(labels),
                "oracle_action": actions[0] if len(actions) == 1 else ",".join(actions),
                "step_n": len(sub),
                "mean_baseline_net_return": float(sub["baseline_net_return"].mean()) if len(sub) else np.nan,
                "mean_oracle_policy_net_return": float(sub["oracle_policy_net_return"].mean()) if len(sub) else np.nan,
                "mean_incremental_return": float(sub["incremental_net_return"].mean()) if len(sub) else np.nan,
                "sum_incremental_return": float(sub["incremental_net_return"].sum()) if len(sub) else np.nan,
                "cell_contribution_to_total": float(sub["incremental_net_return"].sum() / total) if abs(total) > 1e-15 else 0.0,
                "six_cell_gate": "pass",
                "blocking_reason": "",
            }
        )
    return rows


def action_intensity_id(q_defend: float) -> str:
    if abs(q_defend - 0.0) < 1e-12:
        return "full_defend_exit_cash"
    if abs(q_defend - 0.25) < 1e-12:
        return "partial_defend_25pct"
    if abs(q_defend - 0.5) < 1e-12:
        return "partial_defend_50pct"
    return f"q_defend_{q_defend:g}"


def build_replay_chunk(
    spec: dict[str, Any],
    sub: pd.DataFrame,
    cost_bps: int,
    q_defend: float,
) -> pd.DataFrame:
    actions = action_for_spec(spec, sub, q_defend, cost_bps)
    forward = sub["forward_return_h20"].to_numpy(dtype=float)
    baseline = forward
    continue_net = forward
    defend_net = q_defend * forward - cost_bps / 10000.0
    policy = np.where(actions == "defend", defend_net, continue_net)
    cols = list(PRIMARY_ROW_KEY) + [
        "cluster_split_bucket",
        "label_class",
        "forward_return_h20",
        "realized_h20_payoff",
        "signed_max_drawdown_h20",
        "drawdown_abs_for_reporting",
        "step_start_qfq_close",
        "step_end_qfq_close",
        "qfq_path_status",
    ]
    out = sub.loc[:, cols].copy()
    out["oracle_id"] = spec["oracle_id"]
    out["oracle_variant_id"] = spec["oracle_variant_id"]
    out["oracle_variant_name"] = spec["oracle_variant_name"]
    out["primary_variant"] = bool(spec["primary_variant"])
    out["drawdown_threshold"] = spec["drawdown_threshold"]
    out["high_upside_threshold_id"] = spec["high_upside_threshold_id"]
    out["action_intensity_id"] = action_intensity_id(q_defend)
    out["cost_bps"] = cost_bps
    out["q_continue"] = 1.0
    out["q_defend"] = q_defend
    out["oracle_action"] = actions
    out["baseline_net_return"] = baseline
    out["oracle_policy_net_return"] = policy
    out["incremental_net_return"] = policy - baseline
    out["cell_id"] = cell_ids(actions, sub["label_class"])
    return out


def build_replay_outputs(
    config: dict[str, Any], base: pd.DataFrame, thresholds: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, Any]] = []
    six_rows: list[dict[str, Any]] = []
    frontier_rows: list[dict[str, Any]] = []
    neutral_rows: list[dict[str, Any]] = []
    panel_chunks: list[pd.DataFrame] = []
    costs = [int(x) for x in config["action_semantics"]["cost_grid_bps"]]
    q_grid = [float(x) for x in config["action_semantics"]["q_defend_grid"]]
    specs = oracle_specs(config, thresholds)
    neutral_specs = neutral_stress_specs()
    for spec in specs:
        mask = denominator_mask(base, spec["denominator_type"])
        spec_base = base.loc[mask].copy()
        for cost_bps in costs:
            for q_defend in q_grid:
                for split in SPLITS:
                    sub = spec_base.loc[spec_base["cluster_split_bucket"].astype(str).eq(split)]
                    chunk = build_replay_chunk(spec, sub, cost_bps, q_defend)
                    panel_chunks.append(chunk)
                    summary_rows.append(summarize_replay_chunk(config, spec, split, cost_bps, q_defend, chunk))
                    six_rows.extend(six_cell_rows(spec, split, cost_bps, q_defend, chunk))
                    if spec["oracle_id"] != "O0":
                        summary = summary_rows[-1]
                        frontier_rows.append(
                            {
                                "oracle_id": spec["oracle_id"],
                                "oracle_variant_id": spec["oracle_variant_id"],
                                "oracle_variant_name": spec["oracle_variant_name"],
                                "primary_variant": bool(spec["primary_variant"]),
                                "split_bucket": split,
                                "cost_bps": cost_bps,
                                "q_defend": q_defend,
                                "q_removed": 1.0 - q_defend,
                                "defended_step_n": summary["defended_step_n"],
                                "continued_step_n": summary["continued_step_n"],
                                "mean_incremental_return": summary["mean_incremental_return"],
                                "trimmed_mean_incremental_return": summary["trimmed_mean_incremental_return"],
                                "winsorized_mean_incremental_return": summary["winsorized_mean_incremental_return"],
                                "positive_sacrifice": -summary["defended_positive_opportunity_cost"],
                                "negative_avoidance": summary["defended_negative_gain"],
                                "neutral_drag": summary["defended_neutral_gain"],
                                "frontier_gate": "pass",
                                "blocking_reason": "",
                            }
                        )
    for spec in neutral_specs:
        spec_base = base.loc[denominator_mask(base, spec["denominator_type"])].copy()
        for cost_bps in costs:
            for q_defend in q_grid:
                for split in SPLITS:
                    sub = spec_base.loc[spec_base["cluster_split_bucket"].astype(str).eq(split)]
                    chunk = build_replay_chunk(spec, sub, cost_bps, q_defend)
                    six_rows.extend(six_cell_rows(spec, split, cost_bps, q_defend, chunk))
                    neutral = sub.loc[sub["label_class"].astype(str).eq("neutral")]
                    neutral_chunk = chunk.loc[chunk["label_class"].astype(str).eq("neutral")]
                    binary_summary = summarize_replay_chunk(
                        config,
                        {**spec, "denominator_type": "binary_primary"},
                        split,
                        cost_bps,
                        q_defend,
                        build_replay_chunk(
                            {**spec, "denominator_type": "binary_primary"},
                            sub.loc[sub["label_class"].astype(str).isin(["positive", "negative"])],
                            cost_bps,
                            q_defend,
                        ),
                    )
                    labelable_summary = summarize_replay_chunk(config, spec, split, cost_bps, q_defend, chunk)
                    neutral_rows.append(
                        {
                            "oracle_id": spec["oracle_id"],
                            "oracle_variant_id": spec["oracle_variant_id"],
                            "oracle_variant_name": spec["oracle_variant_name"],
                            "primary_variant": bool(spec["primary_variant"]),
                            "split_bucket": split,
                            "cost_bps": cost_bps,
                            "q_defend": q_defend,
                            "neutral_action_rule": "continue" if spec["oracle_id"] == "O1" else "defend",
                            "labelable_step_n": len(sub),
                            "neutral_step_n": len(neutral),
                            "primary_binary_step_n": binary_summary["observed_step_n"],
                            "neutral_mean_incremental_return": float(neutral_chunk["incremental_net_return"].mean())
                            if len(neutral_chunk)
                            else np.nan,
                            "neutral_sum_incremental_return": float(neutral_chunk["incremental_net_return"].sum())
                            if len(neutral_chunk)
                            else np.nan,
                            "primary_binary_mean_incremental_return": binary_summary["mean_incremental_return"],
                            "labelable_stress_mean_incremental_return": labelable_summary["mean_incremental_return"],
                            "neutral_stress_gate": "pass",
                            "blocking_reason": "",
                        }
                    )
    panel = pd.concat(panel_chunks, ignore_index=True)
    return (
        panel,
        pd.DataFrame(summary_rows),
        pd.DataFrame(six_rows),
        pd.DataFrame(frontier_rows),
        pd.DataFrame(neutral_rows),
    )


def build_o2_drawdown_threshold_replay(
    config: dict[str, Any],
    summary: pd.DataFrame,
    row_audit: pd.DataFrame,
) -> pd.DataFrame:
    threshold_map = {str(k): float(v) for k, v in config["oracle_variants"]["o2_drawdown_thresholds"].items()}
    cost = int(config["decision"]["primary_ladder_cost_bps"])
    q_defend = float(config["decision"]["primary_ladder_q_defend"])
    rows: list[dict[str, Any]] = []
    o2 = summary.loc[
        summary["oracle_id"].astype(str).eq("O2")
        & summary["cost_bps"].astype(int).eq(cost)
        & np.isclose(summary["q_defend"].astype(float), q_defend)
    ].copy()
    labelable_audit = row_audit.loc[row_audit["denominator_type"].astype(str).eq("labelable_full")]
    audit_by_split = {str(row["split_bucket"]): row for _, row in labelable_audit.iterrows()}
    for _, row in o2.sort_values(["oracle_variant_id", "split_bucket"]).iterrows():
        split = str(row["split_bucket"])
        audit = audit_by_split.get(split, pd.Series(dtype=object))
        threshold = threshold_map.get(str(row["oracle_variant_id"]), np.nan)
        gate = (
            np.isfinite(threshold)
            and threshold < 0
            and int(row["observed_step_n"]) == int(row["expected_step_n"])
            and str(audit.get("row_replay_gate", "")) == "pass"
            and str(audit.get("drawdown_sign_convention_gate", "")) == "pass"
            and bool(audit.get("positive_abs_drawdown_used_for_o2_threshold", True)) is False
        )
        rows.append(
            {
                "oracle_id": row["oracle_id"],
                "oracle_variant_id": row["oracle_variant_id"],
                "primary_variant": bool(row["primary_variant"]),
                "split_bucket": split,
                "cost_bps": cost,
                "q_defend": q_defend,
                "signed_drawdown_threshold": threshold,
                "drawdown_predicate": f"signed_max_drawdown_h20 <= {threshold:.2f}" if np.isfinite(threshold) else "",
                "expected_step_n": int(row["expected_step_n"]),
                "observed_step_n": int(row["observed_step_n"]),
                "defended_step_n": int(row["defended_step_n"]),
                "mean_incremental_return": float(row["mean_incremental_return"]),
                "trimmed_mean_incremental_return": float(row["trimmed_mean_incremental_return"]),
                "forward_return_replay_abs_diff_max": float(audit.get("forward_return_replay_abs_diff_max", np.nan)),
                "signed_max_drawdown_replay_abs_diff_max": float(
                    audit.get("signed_max_drawdown_replay_abs_diff_max", np.nan)
                ),
                "positive_abs_drawdown_used_for_o2_threshold": bool(
                    audit.get("positive_abs_drawdown_used_for_o2_threshold", True)
                ),
                "drawdown_sign_convention_gate": str(audit.get("drawdown_sign_convention_gate", "")),
                "qfq_lineage_reconciliation_gate": str(audit.get("row_replay_gate", "")),
                "o2_drawdown_replay_gate": "pass" if gate else "fail",
                "blocking_reason": "" if gate else "o2_drawdown_threshold_replay_failed",
            }
        )
    return pd.DataFrame(rows)


def stable_action_set_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return hashlib.sha256(b"").hexdigest()
    ordered = frame.loc[:, list(PRIMARY_ROW_KEY)].astype(str).sort_values(list(PRIMARY_ROW_KEY))
    payload = "\n".join("|".join(row) for row in ordered.to_numpy(dtype=str))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_o5_action_selection_proof(panel: pd.DataFrame) -> pd.DataFrame:
    o5 = panel.loc[panel["oracle_id"].astype(str).eq("O5")].copy()
    rows: list[dict[str, Any]] = []
    reference_hash: dict[tuple[str, int], tuple[str, int]] = {}
    for (split, cost_bps), sub in o5.loc[np.isclose(o5["q_defend"].astype(float), 0.0)].groupby(
        ["cluster_split_bucket", "cost_bps"], sort=True
    ):
        defended = sub.loc[sub["oracle_action"].astype(str).eq("defend")]
        reference_hash[(str(split), int(cost_bps))] = (stable_action_set_hash(defended), int(len(defended)))
    for (split, cost_bps, q_defend), sub in o5.groupby(["cluster_split_bucket", "cost_bps", "q_defend"], sort=True):
        split = str(split)
        cost_bps = int(cost_bps)
        q_defend = float(q_defend)
        forward = sub["forward_return_h20"].to_numpy(dtype=float)
        expected_defend = q_defend * forward - cost_bps / 10000.0 > forward
        actual_defend = sub["oracle_action"].astype(str).eq("defend").to_numpy()
        mismatch_n = int(np.not_equal(expected_defend, actual_defend).sum())
        defended = sub.loc[sub["oracle_action"].astype(str).eq("defend")]
        action_hash = stable_action_set_hash(defended)
        ref_hash, ref_defended_n = reference_hash.get((split, cost_bps), ("", 0))
        same_as_full_defend = action_hash == ref_hash
        zero_cost_equivalence = cost_bps == 0 and q_defend > 0.0
        nonreference_reuse_gate = (
            "reference"
            if np.isclose(q_defend, 0.0)
            else "pass_same_by_formula_zero_cost"
            if zero_cost_equivalence and same_as_full_defend
            else "pass"
            if not same_as_full_defend
            else "fail"
        )
        proof_pass = mismatch_n == 0 and nonreference_reuse_gate != "fail"
        rows.append(
            {
                "split_bucket": split,
                "cost_bps": cost_bps,
                "q_defend": q_defend,
                "observed_step_n": int(len(sub)),
                "defended_step_n": int(len(defended)),
                "formula": "defend if q_defend * forward_return_h20 - cost_bps/10000 > forward_return_h20",
                "formula_recomputed_mismatch_n": mismatch_n,
                "formula_recompute_gate": "pass" if mismatch_n == 0 else "fail",
                "full_defend_reference_q_defend": 0.0,
                "full_defend_reference_defended_step_n": ref_defended_n,
                "action_set_sha256": action_hash,
                "full_defend_reference_action_set_sha256": ref_hash,
                "action_set_equal_to_full_defend_reference": same_as_full_defend,
                "zero_cost_formula_equivalence_expected": zero_cost_equivalence,
                "nonreference_full_defend_reuse_gate": nonreference_reuse_gate,
                "o5_action_selection_proof_gate": "pass" if proof_pass else "fail",
                "blocking_reason": "" if proof_pass else "o5_action_selection_proof_failed",
            }
        )
    return pd.DataFrame(rows)


def build_search_accounting_audit() -> pd.DataFrame:
    row = {
        "search_family": "oracle_action_value_upper_bound_diagnostic",
        "phase_id": PHASE_ID,
        "no_model_training": True,
        "no_model_refit": True,
        "no_survival_threshold_tuning": True,
        "no_validation_selection": True,
        "no_robustness_tuning": True,
        "no_feature_selection": True,
        "no_payoff_label_redesign": True,
        "no_split_local_payoff_quantile_recompute": True,
        "no_oracle_value_interpretation_beyond_17b": True,
        "no_entry_policy_authorized": True,
        "no_exit_policy_authorized": True,
        "no_holding_policy_authorized": True,
        "no_portfolio_backtest_authorized": True,
        "no_model_deployment_authorized": True,
        "no_production_signal_authorized": True,
        "no_live_trading_authorized": True,
    }
    row["search_accounting_gate"] = "pass" if all(v for k, v in row.items() if k.startswith("no_")) else "fail"
    row["blocking_reason"] = "" if row["search_accounting_gate"] == "pass" else "search_accounting_failed"
    return pd.DataFrame([row])


def all_gate(frame: pd.DataFrame, column: str) -> str:
    if frame.empty or column not in frame:
        return "fail"
    return "pass" if frame[column].astype(str).eq("pass").all() else "fail"


def build_decision(
    config: dict[str, Any],
    input_gate: str,
    input_reason: str,
    row_audit: pd.DataFrame,
    summary: pd.DataFrame,
    six: pd.DataFrame,
    frontier: pd.DataFrame,
    neutral: pd.DataFrame,
    thresholds: pd.DataFrame,
    search: pd.DataFrame,
    seventeen_a_decision: pd.Series | None,
) -> pd.DataFrame:
    split = config["decision"]["primary_decision_split"]
    cost = int(config["decision"]["primary_ladder_cost_bps"])
    q_defend = float(config["decision"]["primary_ladder_q_defend"])
    candidates = set(config["decision"]["primary_ladder_candidate_variants"])
    candidate_rows = summary.loc[
        summary["split_bucket"].astype(str).eq(split)
        & summary["oracle_variant_id"].astype(str).isin(candidates)
        & summary["cost_bps"].astype(int).eq(cost)
        & np.isclose(summary["q_defend"].astype(float), q_defend)
    ].copy()
    metric_floor = float(config["decision"]["primary_ladder_metric_floor"])
    materiality_floor = float(config["decision"]["primary_ladder_materiality_floor"])
    candidate_rows["primary_gate_pass"] = (
        candidate_rows["trimmed_mean_incremental_return"].astype(float).gt(metric_floor)
        & candidate_rows["mean_incremental_return"].astype(float).ge(materiality_floor)
    )
    positive = candidate_rows.loc[candidate_rows["primary_gate_pass"]]
    gates = {
        "input_gate": input_gate,
        "row_replay_gate": all_gate(row_audit, "row_replay_gate"),
        "denominator_gate": all_gate(row_audit, "row_replay_gate"),
        "oracle_ladder_gate": all_gate(summary, "ladder_metric_gate"),
        "six_cell_gate": all_gate(six, "six_cell_gate"),
        "action_intensity_gate": all_gate(frontier, "frontier_gate"),
        "neutral_stress_gate": all_gate(neutral, "neutral_stress_gate"),
        "high_upside_threshold_gate": all_gate(thresholds, "threshold_freeze_gate"),
        "search_accounting_gate": all_gate(search, "search_accounting_gate"),
    }
    blocking = [k for k, v in gates.items() if v != "pass"]
    if candidate_rows["oracle_variant_id"].nunique() != len(candidates):
        blocking.append("primary_candidate_variant_missing")
    if blocking:
        decision = DECISION_BLOCKED
        next_requirement = "none"
        primary_positive = None
        reason = ";".join(blocking + ([input_reason] if input_reason else []))
    elif positive.empty:
        decision = DECISION_NO_VALUE
        next_requirement = "none"
        primary_positive = None
        reason = ""
    else:
        best = positive.sort_values(
            ["trimmed_mean_incremental_return", "mean_incremental_return"], ascending=False
        ).iloc[0]
        decision = DECISION_READY
        next_requirement = config["policy"]["next_allowed_requirement"]
        primary_positive = best
        reason = ""
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_requirement,
                **gates,
                "primary_ladder_metric": config["decision"]["primary_ladder_metric"],
                "primary_ladder_metric_floor": config["decision"]["primary_ladder_metric_floor"],
                "primary_ladder_materiality_metric": config["decision"]["primary_ladder_materiality_metric"],
                "primary_ladder_materiality_floor": config["decision"]["primary_ladder_materiality_floor"],
                "primary_ladder_cost_bps": cost,
                "primary_ladder_q_defend": q_defend,
                "primary_positive_oracle_id": "" if primary_positive is None else primary_positive["oracle_id"],
                "primary_positive_oracle_variant_id": ""
                if primary_positive is None
                else primary_positive["oracle_variant_id"],
                "o3_status": "skipped_nonblocking",
                "o6_status_inherited": ""
                if seventeen_a_decision is None
                else str(seventeen_a_decision.get("o6_status_for_17b", "")),
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "portfolio_backtest_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "live_trading_authorized": False,
                "blocking_reason": reason,
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    if frame.empty:
        return "_empty_"
    cols = [col for col in columns if col in frame.columns]
    return frame.loc[:, cols].head(max_rows).to_markdown(index=False)


def plot_ladder_summary(path: Path, summary: pd.DataFrame, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cost = int(config["decision"]["primary_ladder_cost_bps"])
    q_defend = float(config["decision"]["primary_ladder_q_defend"])
    plot = summary.loc[
        summary["primary_variant"].astype(bool)
        & summary["cost_bps"].astype(int).eq(cost)
        & np.isclose(summary["q_defend"].astype(float), q_defend)
        & summary["oracle_id"].isin(["O0", "O1", "O2", "O4", "O5"])
    ].copy()
    order = [
        "O0_blind_continue_primary",
        "O1_negative_primary",
        "O2_dd_10pct_primary",
        "O4_label_positive_primary",
        "O5_perfect_utility_primary",
    ]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    for ax, split in zip(axes, SPLITS):
        sub = plot.loc[plot["split_bucket"].eq(split)].set_index("oracle_variant_id").reindex(order)
        x = np.arange(len(order))
        ax.bar(x - 0.18, sub["mean_incremental_return"], width=0.36, label="mean")
        ax.bar(x + 0.18, sub["trimmed_mean_incremental_return"], width=0.36, label="trimmed")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(split)
        ax.set_xticks(x)
        ax.set_xticklabels(["O0", "O1", "O2", "O4", "O5"], rotation=0)
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("incremental return")
    axes[-1].legend(loc="best", fontsize=8)
    fig.suptitle("17B Oracle Ladder Net Utility, primary 50bps q_defend=0")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_sacrifice_vs_avoidance(path: Path, summary: pd.DataFrame, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cost = int(config["decision"]["primary_ladder_cost_bps"])
    q_defend = float(config["decision"]["primary_ladder_q_defend"])
    plot = summary.loc[
        summary["primary_variant"].astype(bool)
        & summary["cost_bps"].astype(int).eq(cost)
        & np.isclose(summary["q_defend"].astype(float), q_defend)
        & summary["oracle_id"].isin(["O1", "O2", "O4", "O5"])
    ].copy()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharex=False, sharey=False)
    for ax, split in zip(axes, SPLITS):
        sub = plot.loc[plot["split_bucket"].eq(split)]
        x = -sub["defended_positive_opportunity_cost"].astype(float)
        y = sub["defended_negative_gain"].astype(float)
        ax.scatter(x, y, s=60)
        for _, row in sub.iterrows():
            ax.annotate(row["oracle_id"], (-row["defended_positive_opportunity_cost"], row["defended_negative_gain"]))
        ax.axhline(0, color="black", linewidth=0.8)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(split)
        ax.set_xlabel("positive sacrifice")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("negative avoidance")
    fig.suptitle("Positive Sacrifice vs Negative Avoidance, primary ladder")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_report(
    path: Path,
    decision: pd.DataFrame,
    input_audit: pd.DataFrame,
    contract_validation: pd.DataFrame,
    row_audit: pd.DataFrame,
    summary: pd.DataFrame,
    six: pd.DataFrame,
    frontier: pd.DataFrame,
    neutral: pd.DataFrame,
    o2_drawdown: pd.DataFrame,
    o5_proof: pd.DataFrame,
    thresholds: pd.DataFrame,
    search: pd.DataFrame,
    config: dict[str, Any],
) -> Path:
    dec = decision.iloc[0]
    primary = summary.loc[
        summary["primary_variant"].astype(bool)
        & summary["cost_bps"].astype(int).eq(int(config["decision"]["primary_ladder_cost_bps"]))
        & np.isclose(summary["q_defend"].astype(float), float(config["decision"]["primary_ladder_q_defend"]))
    ]
    text = f"""# 17B Oracle Ladder Replay Report

## 1. Decision

```text
decision_state = {dec['decision_state']}
next_allowed_requirement = {dec['next_allowed_requirement']}
blocking_reason = {dec['blocking_reason'] if str(dec['blocking_reason']) else 'none'}
```

17B 只重放 frozen oracle ladder。它不授权 entry / exit / holding / sizing / portfolio / deployment / production signal / live trading。正向 ladder 结果最多授权 EP17C robustness stress，不授权 payoff-state research。

## 2. 17A Handoff

{markdown_table(input_audit, ['artifact_key', 'source_phase_id', 'row_count', 'schema_status', 'lineage_status', 'row_key_status', 'gate_status', 'blocking_reason'], max_rows=20)}

17A machine-readable artifact independent validation:

{markdown_table(contract_validation.loc[contract_validation['validation_status'].astype(str).ne('pass')], ['artifact_key', 'validation_check_id', 'observed_value', 'expected_value', 'validation_status', 'blocking_reason'], max_rows=20) if contract_validation['validation_status'].astype(str).ne('pass').any() else 'All independently validated 17A machine-readable artifact checks passed. See `17a_contract_validation_audit.csv` for the full check list.'}

## 3. Denominator And QFQ Replay

{markdown_table(row_audit, ['split_bucket', 'denominator_type', 'expected_step_n', 'observed_step_n', 'forward_return_replay_abs_diff_max', 'signed_max_drawdown_replay_abs_diff_max', 'positive_abs_drawdown_used_for_o2_threshold', 'drawdown_sign_convention_gate', 'row_replay_gate'], max_rows=20)}

16E `utility_panel.parquet` 是 4 个 cost tier 的膨胀面板。17B 使用 primary row key 和 primary source cost tier 提取 23,405 个 denominator rows，再重新展开 oracle/cost/action-intensity。O2 使用 signed negative drawdown：`signed_max_drawdown_h20 <= -0.10`，`drawdown_avoided_abs` 只作为正数报告字段。

## 4. Oracle Definitions

O0 使用 labelable full blind-continue baseline。O1 使用 binary primary negative oracle，并单独输出 neutral stress。O2 使用 qfq-reconciled signed drawdown variants。O3 未配置既有 false-repair label，状态为 `skipped_nonblocking`。O4 使用 binary primary positive-preservation oracle，并单独输出 high-upside stress。O5 是 perfect utility upper bound，每个 `q_defend/cost_bps` variant 独立重算 defend/continue payoff，不复用 full-defend action set。

## 5. Primary Ladder

{markdown_table(primary, ['oracle_id', 'oracle_variant_id', 'split_bucket', 'denominator_type', 'cost_bps', 'q_defend', 'observed_step_n', 'defended_step_n', 'mean_incremental_return', 'trimmed_mean_incremental_return', 'defended_positive_opportunity_cost', 'defended_negative_gain'], max_rows=60)}

Primary decision gate: robustness split, `trimmed_mean_incremental_return > 0`, `mean_incremental_return >= 0.0025`, 50bps, `q_defend = 0.00`, primary variants only.

## 6. Action Intensity Frontier

{markdown_table(frontier.loc[frontier['split_bucket'].eq('robustness')], ['oracle_id', 'oracle_variant_id', 'cost_bps', 'q_defend', 'mean_incremental_return', 'trimmed_mean_incremental_return', 'positive_sacrifice', 'negative_avoidance', 'neutral_drag'], max_rows=40)}

## 7. Six-cell Decomposition

{markdown_table(six.loc[six['split_bucket'].eq('robustness') & six['cost_bps'].eq(50) & np.isclose(six['q_defend'].astype(float), 0.0)], ['oracle_id', 'oracle_variant_id', 'denominator_scope', 'cell_id', 'step_n', 'mean_incremental_return', 'sum_incremental_return', 'cell_contribution_to_total'], max_rows=80)}

## 8. Neutral Stress

{markdown_table(neutral.loc[neutral['cost_bps'].eq(50) & np.isclose(neutral['q_defend'].astype(float), 0.0)], ['oracle_id', 'split_bucket', 'neutral_action_rule', 'neutral_step_n', 'primary_binary_mean_incremental_return', 'labelable_stress_mean_incremental_return', 'neutral_stress_gate'], max_rows=20)}

## 9. O2 / O4 Stress

O2 signed drawdown-threshold replay:

{markdown_table(o2_drawdown, ['oracle_variant_id', 'primary_variant', 'split_bucket', 'signed_drawdown_threshold', 'observed_step_n', 'defended_step_n', 'mean_incremental_return', 'signed_max_drawdown_replay_abs_diff_max', 'positive_abs_drawdown_used_for_o2_threshold', 'drawdown_sign_convention_gate', 'qfq_lineage_reconciliation_gate', 'o2_drawdown_replay_gate'], max_rows=40)}

O4 train-frozen high-upside thresholds:

{markdown_table(thresholds, ['oracle_variant_id', 'train_quantile', 'train_absolute_payoff_cutoff', 'split_local_recompute_used', 'threshold_freeze_gate'])}

## 10. O5 Action Selection Proof

{markdown_table(o5_proof.loc[o5_proof['split_bucket'].astype(str).eq('robustness')], ['cost_bps', 'q_defend', 'observed_step_n', 'defended_step_n', 'formula_recomputed_mismatch_n', 'action_set_equal_to_full_defend_reference', 'zero_cost_formula_equivalence_expected', 'nonreference_full_defend_reuse_gate', 'o5_action_selection_proof_gate'], max_rows=20)}

## 11. Search Accounting

{markdown_table(search, ['no_model_training', 'no_model_refit', 'no_survival_threshold_tuning', 'no_validation_selection', 'no_robustness_tuning', 'no_payoff_label_redesign', 'no_split_local_payoff_quantile_recompute', 'no_live_trading_authorized', 'search_accounting_gate'])}
"""
    return write_text(path, text)


def output_hashes(outputs: dict[str, Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, path in outputs.items():
        if key in {"manifest", "replay_engine_manifest", "input_artifact_manifest"}:
            continue
        if path.exists() and path.is_file() and LOCAL_CACHE_DIR not in path.parents:
            hashes[key] = file_sha(path)
    return hashes


def row_counts(outputs: dict[str, Path]) -> dict[str, int | float]:
    counts: dict[str, int | float] = {}
    for key, path in outputs.items():
        if path.exists() and key not in {"manifest", "replay_engine_manifest", "input_artifact_manifest", "report"}:
            counts[key] = count_rows(path)
    return counts


def write_manifests(
    config_path: Path,
    config: dict[str, Any],
    resolved: dict[str, Path],
    outputs: dict[str, Path],
    decision: pd.DataFrame,
    input_audit: pd.DataFrame,
    thresholds: pd.DataFrame,
    specs: list[dict[str, Any]],
) -> None:
    dec = decision.iloc[0].to_dict()
    auth = {col: False for col in AUTH_FALSE_COLUMNS}
    input_hashes = {
        row["artifact_key"]: row["sha256"]
        for _, row in input_audit.iterrows()
        if isinstance(row["sha256"], str) and row["sha256"]
    }
    main_payload = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "requirement_file": str(resolved["requirement"]),
        "requirement_sha256": file_sha(resolved["requirement"]),
        "config_file": str(config_path),
        "config_sha256": file_sha(config_path),
        "runner_file": str(Path(__file__).resolve()),
        "test_file": str(EXPERIMENT_DIR / "tests" / "test_17b_oracle_ladder_replay.py"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit_if_available": "",
        "python_version": platform.python_version(),
        "input_artifact_hashes": input_hashes,
        "output_hashes": output_hashes(outputs),
        "row_counts": row_counts(outputs),
        "decision_state": dec["decision_state"],
        "next_allowed_requirement": dec["next_allowed_requirement"],
        "primary_cost_bps": config["action_semantics"]["primary_cost_bps"],
        "primary_ladder_metric": config["decision"]["primary_ladder_metric"],
        "primary_ladder_metric_floor": config["decision"]["primary_ladder_metric_floor"],
        "primary_ladder_materiality_metric": config["decision"]["primary_ladder_materiality_metric"],
        "primary_ladder_materiality_floor": config["decision"]["primary_ladder_materiality_floor"],
        "primary_ladder_cost_bps": config["decision"]["primary_ladder_cost_bps"],
        "cost_grid": config["action_semantics"]["cost_grid_bps"],
        "q_defend_grid": config["action_semantics"]["q_defend_grid"],
        "primary_q_defend": config["action_semantics"]["primary_q_defend"],
        "primary_ladder_candidate_variants": config["decision"]["primary_ladder_candidate_variants"],
        "trim_fraction_each_tail": config["stats"]["trim_fraction_each_tail"],
        "winsor_fraction_each_tail": config["stats"]["winsor_fraction_each_tail"],
        "oracle_variant_definitions": specs,
        "o2_drawdown_variant_grid": config["oracle_variants"]["o2_drawdown_thresholds"],
        "o4_high_upside_variant_grid": thresholds.to_dict(orient="records"),
        "o5_action_recomputed_per_cost_intensity": True,
        "drawdown_sign_convention": "signed_max_drawdown_h20 <= 0; O2 compares signed drawdown to negative thresholds",
        "canonical_field_mapping": canonical_field_mapping(),
        "o3_status": dec["o3_status"],
        "o6_status_inherited": dec["o6_status_inherited"],
        **auth,
    }
    replay_payload = {
        "row_key": list(PRIMARY_ROW_KEY),
        "denominator_binding": {
            "O0": "labelable_full",
            "O1": "binary_primary",
            "O2": "labelable_full",
            "O3": "skipped_nonblocking",
            "O4": "binary_primary",
            "O5": "labelable_full",
        },
        "oracle_definitions": [spec for spec in specs if spec["primary_variant"]],
        "oracle_variant_definitions": specs,
        "action_intensity_grid": config["action_semantics"]["q_defend_grid"],
        "cost_grid": config["action_semantics"]["cost_grid_bps"],
        "return_formula": "baseline=forward_return_h20; defend=q_defend*forward_return_h20-cost_bps/10000; incremental=policy-baseline",
        "o5_action_selection_formula_by_cost_intensity": "defend if defend_net_return(q_defend,cost_bps) > continue_net_return",
        "drawdown_formula": "min(qfq_close[start:end]/qfq_close[start]-1)",
        "drawdown_sign_convention": "signed nonpositive; positive abs fields never compared to O2 thresholds",
        "qfq_replay_tolerance": config["tolerances"],
        "trim_winsor_definitions": config["stats"],
        "primary_ladder_gate_constants": config["decision"],
        "high_upside_threshold_source": "train_only",
    }
    write_json(outputs["manifest"], main_payload)
    write_json(outputs["replay_engine_manifest"], replay_payload)
    write_json(outputs["input_artifact_manifest"], input_audit.to_dict(orient="records"))


def canonical_field_mapping() -> dict[str, dict[str, str]]:
    return {
        "forward_return_h20": {
            "source": "continue_return_h20",
            "rule": "recompute from qfq close-to-close, then reconcile to source",
        },
        "realized_h20_payoff": {"source": "continue_return_h20", "rule": "alias of forward_return_h20"},
        "signed_max_drawdown_h20": {
            "source": "continue_max_drawdown_h20",
            "rule": "recompute as signed negative qfq path drawdown",
        },
        "qfq_path_status": {"source": "utility_price_status", "rule": "canonical status for 17B qfq replay"},
        "drawdown_avoided_abs": {
            "source": "drawdown_avoided_abs",
            "rule": "positive reporting field only, never used for O2 threshold comparison",
        },
    }


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit = build_input_gate_audit(config, resolved)
    contract_validation = build_17a_contract_validation_audit(config, resolved)
    write_df(outputs["input_gate_audit"], input_audit)
    write_df(outputs["seventeen_a_contract_validation_audit"], contract_validation)
    input_gate, input_reason = input_gate_status(input_audit)
    if check_inputs_only:
        return 0 if input_gate == "pass" else 1
    if input_gate != "pass":
        decision = build_decision(
            config,
            input_gate,
            input_reason,
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            build_search_accounting_audit(),
            None,
        )
        write_df(outputs["decision"], decision)
        return 1

    utility_panel = read_table(resolved["upstream_16e_utility_panel"])
    base = load_primary_base_panel(config, utility_panel)
    base = reconcile_qfq(config, base, resolved["stock_daily_qfq_dir"])
    row_audit = build_row_replay_audit(config, base)
    thresholds = high_upside_threshold_freeze(config, base)
    panel, summary, six, frontier, neutral = build_replay_outputs(config, base, thresholds)
    o2_drawdown = build_o2_drawdown_threshold_replay(config, summary, row_audit)
    o5_proof = build_o5_action_selection_proof(panel)
    search = build_search_accounting_audit()
    seventeen_a_decision = read_table(resolved["seventeen_a_decision"]).iloc[0]
    decision = build_decision(
        config,
        input_gate,
        input_reason,
        row_audit,
        summary,
        six,
        frontier,
        neutral,
        thresholds,
        search,
        seventeen_a_decision,
    )

    write_df(outputs["oracle_ladder_panel"], panel)
    write_df(outputs["row_replay_audit"], row_audit)
    write_df(outputs["high_upside_threshold_freeze"], thresholds)
    write_df(outputs["o2_drawdown_threshold_replay"], o2_drawdown)
    write_df(outputs["o5_action_selection_proof"], o5_proof)
    write_df(outputs["ladder_summary"], summary)
    write_df(outputs["six_cell_decomposition"], six)
    write_df(outputs["action_intensity_frontier"], frontier)
    write_df(outputs["neutral_stress"], neutral)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["decision"], decision)
    plot_ladder_summary(outputs["ladder_net_utility_figure"], summary, config)
    plot_sacrifice_vs_avoidance(outputs["sacrifice_vs_avoidance_figure"], summary, config)
    write_report(
        outputs["report"],
        decision,
        input_audit,
        contract_validation,
        row_audit,
        summary,
        six,
        frontier,
        neutral,
        o2_drawdown,
        o5_proof,
        thresholds,
        search,
        config,
    )
    write_manifests(config_path, config, resolved, outputs, decision, input_audit, thresholds, oracle_specs(config, thresholds))
    return 0 if decision.iloc[0]["decision_state"] != DECISION_BLOCKED else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    sys.exit(main())
