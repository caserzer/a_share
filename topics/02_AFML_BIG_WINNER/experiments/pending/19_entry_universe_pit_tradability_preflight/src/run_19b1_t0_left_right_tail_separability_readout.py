#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
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
import yaml
from scipy import stats


SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import run_19b0_fast_rule_grid_enrichment_scan as b0  # noqa: E402


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "19B1_t0_left_right_tail_separability_readout"
EXPERIMENT_ID = "19_entry_universe_pit_tradability_preflight"
PHASE_ID = "19B1"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_19b1_t0_left_right_tail_separability_readout.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_19b1_t0_left_right_tail_separability_readout.md"
OUTPUT_ROOT = EXPERIMENT_DIR / "outputs" / RUN_ID
FIGURE_DIR = OUTPUT_ROOT / "figures"

PRIMARY_FEATURE_WHITELIST = [
    "return_5d_asof_decision_date",
    "return_10d_asof_decision_date",
    "return_20d_asof_decision_date",
    "return_60d_asof_decision_date",
    "stock_vs_market_return_20d_asof_decision_date",
    "return_60d_cross_section_rank_pct_asof_decision_date",
    "close_to_ema60_asof_decision_date",
    "amount_ratio_20d_asof_decision_date",
    "rolling_20d_money_mean_asof_decision_date",
    "atr_20_pct_asof_decision_date",
    "atr_20_pct_rank_asof_decision_date",
    "intraday_range_pct_asof_decision_date",
    "close_position_in_120d_range_asof_decision_date",
    "market_regime_risk_on_asof_decision_date",
    "market_drawdown_60d_asof_decision_date",
    "match_market_cap",
    "match_amount20",
    "match_vol60",
    "match_return20",
]
ACCOUNTING_ONLY_COLUMNS = [
    "decision_month",
    "instrument_month",
    "instrument_id",
    "row_key",
    "family_id",
    "grid_cell_id",
    "split",
    "row_scope",
]
FEATURE_SIGNAL_GROUPS = {
    "recent_return": [
        "return_5d_asof_decision_date",
        "return_10d_asof_decision_date",
        "return_20d_asof_decision_date",
        "return_60d_asof_decision_date",
        "match_return20",
    ],
    "relative_strength": [
        "stock_vs_market_return_20d_asof_decision_date",
        "return_60d_cross_section_rank_pct_asof_decision_date",
        "close_to_ema60_asof_decision_date",
    ],
    "liquidity_amount": [
        "amount_ratio_20d_asof_decision_date",
        "rolling_20d_money_mean_asof_decision_date",
        "match_amount20",
    ],
    "volatility_range": [
        "atr_20_pct_asof_decision_date",
        "atr_20_pct_rank_asof_decision_date",
        "intraday_range_pct_asof_decision_date",
        "match_vol60",
    ],
    "range_position": ["close_position_in_120d_range_asof_decision_date"],
    "market_regime": [
        "market_regime_risk_on_asof_decision_date",
        "market_drawdown_60d_asof_decision_date",
    ],
    "size": ["match_market_cap"],
}
FEATURE_TO_GROUP = {feature: group for group, features in FEATURE_SIGNAL_GROUPS.items() for feature in features}
MATCH_ALIAS = {
    "match_market_cap": ("market_cap_bucket_asof_decision_date", "pit_topn_400_100_executable_daily.csv", "total_market_cap_cny"),
    "match_amount20": ("rolling_20d_amount_bucket_asof_decision_date", "qfq money", "money"),
    "match_vol60": ("rolling_60d_volatility_bucket_asof_decision_date", "qfq close", "close"),
    "match_return20": ("recent_20d_return_bucket_asof_decision_date", "qfq close", "close"),
}
POLICY_AUTH_COLUMNS = [
    "model_training_authorized",
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
    "19C_replay_authorized",
    "EP20_policy_preflight_authorized",
]
REQUIRED_INPUT_KEYS = [
    "nineteen_b_output_root",
    "nineteen_b_decision",
    "nineteen_b_manifest",
    "nineteen_b_output_hashes",
    "nineteen_b_handoff_contract",
    "upstream_19a_contract_audit",
    "upstream_19b0_contract_audit",
    "robustness_candidate_row_manifest",
    "robustness_outcome_boundary_audit",
    "robustness_metric_readout",
    "false_positive_burden_readout",
    "mfe_mae_joint_readout",
    "simple_rule_feature_source_map",
    "matching_feature_source_map",
    "topn_executable_universe",
    "stock_qfq_dir",
    "benchmark_daily",
]
REQUIRED_OUTPUT_KEYS = [
    "input_artifact_audit",
    "upstream_contract_audit",
    "t0_feature_join_audit",
    "t0_feature_source_audit",
    "t0_feature_matrix_manifest",
    "outcome_left_right_overlap_readout",
    "t0_univariate_feature_separability_readout",
    "t0_multivariate_diagnostic_separability_readout",
    "t0_separability_stability_readout",
    "search_accounting_audit",
    "entry_universe_19b1_decision",
    "b2_outcome_left_right_overlap_figure",
    "b2_t0_top_feature_distributions_figure",
    "b2_t0_feature_auc_forest_figure",
    "b2_t0_separability_stability_figure",
    "report",
    "handoff_contract",
    "manifest",
    "output_hashes",
]
CSV_SCHEMAS = {
    "upstream_contract_audit": [
        "upstream_scope",
        "artifact_id",
        "source_file",
        "required_fact",
        "expected_value",
        "observed_value",
        "source_row_filter",
        "derived_gate",
        "contract_gate",
        "hash_verified",
        "validation_outcome_read",
        "authorization_field",
        "authorization_value",
        "blocking_reason",
    ],
    "t0_feature_join_audit": [
        "family_id",
        "grid_cell_id",
        "row_scope",
        "split",
        "expected_candidate_n_from_19b_metric",
        "observed_candidate_n_from_mfe_mae_joint",
        "observed_candidate_n_after_manifest_join",
        "unique_join_key_n",
        "duplicate_join_key_n",
        "missing_in_candidate_manifest_n",
        "extra_manifest_row_n",
        "primary_enrichment_denominator_flag_false_n",
        "manifest_frozen_before_label_readout_false_n",
        "label_read_before_manifest_freeze_true_n",
        "feature_matrix_row_n",
        "feature_missing_any_primary_n",
        "primary_row_join_gate",
        "blocking_reason",
    ],
    "t0_feature_source_audit": [
        "feature_name",
        "feature_signal_group",
        "source_alias",
        "feature_value_type",
        "source_artifact",
        "source_columns",
        "asof_rule",
        "pit_safe_flag",
        "missing_rate",
        "left_bad_nonmissing_n",
        "right_clean_nonmissing_n",
        "left_bad_missing_rate",
        "right_clean_missing_rate",
        "missing_rate_delta_abs",
        "used_in_primary_readout",
        "primary_whitelist_flag",
        "exploratory_only_flag",
        "feature_support_gate",
        "blocking_reason",
    ],
    "t0_feature_matrix_manifest": [
        "family_id",
        "grid_cell_id",
        "row_scope",
        "split",
        "row_n",
        "feature_n",
        "primary_feature_columns_json",
        "accounting_only_columns_json",
        "exploratory_feature_columns_json",
        "forbidden_column_n",
        "forbidden_columns_json",
        "forbidden_label_column_n",
        "forbidden_label_columns_json",
        "feature_matrix_hash",
        "candidate_row_hash",
        "primary_whitelist_hash",
        "missing_any_primary_n",
        "missing_any_primary_rate",
        "all_primary_features_pit_safe",
        "all_primary_features_support_pass_n",
        "feature_matrix_gate",
        "blocking_reason",
    ],
    "outcome_left_right_overlap_readout": [
        "family_id",
        "grid_cell_id",
        "split",
        "row_scope",
        "candidate_n",
        "instrument_n",
        "right_tail_event_50_n",
        "left_tail_event_10_n",
        "left_tail_event_20_n",
        "right_clean_n",
        "left_bad_n",
        "both_n",
        "neither_n",
        "p_left_tail_10_given_right_tail_50",
        "p_left_tail_10_given_not_right_tail_50",
        "p_right_tail_50_given_left_tail_10",
        "p_right_tail_50_given_not_left_tail_10",
        "left_tail_conditional_probability_diff_not_right_minus_right",
        "right_tail_conditional_probability_diff_not_left_minus_left",
        "fisher_exact_p_value",
        "chi_square_p_value",
        "phi_coefficient",
        "mutual_information",
        "cluster_bootstrap_diff_ci_low",
        "cluster_bootstrap_diff_ci_high",
        "outcome_overlap_gate",
        "diagnostic_only_flag",
        "blocking_reason",
    ],
    "entry_universe_19b1_decision": [
        "run_id",
        "created_at",
        "requirement_file_hash",
        "config_file_hash",
        "primary_whitelist_hash",
        "input_artifact_hash_manifest",
        "config_contract_gate",
        "input_artifact_gate",
        "upstream_19a_contract_gate",
        "upstream_19b0_contract_gate",
        "upstream_19b_contract_gate",
        "sample_support_gate",
        "primary_row_join_gate",
        "outcome_overlap_gate",
        "t0_feature_pit_gate",
        "primary_feature_separability_gate",
        "stability_gate",
        "policy_authorization_gate",
        "output_contract_gate",
        "decision_state",
        "blocking_reason",
        "family_id",
        "grid_cell_id",
        "row_scope",
        "split",
        "candidate_n",
        "instrument_n",
        "right_clean_n",
        "left_bad_n",
        "both_n",
        "neither_n",
        "N_primary_whitelist_features_frozen",
        "N_primary_features_pit_safe_used",
        "N_primary_features_support_pass",
        "N_primary_features_support_fail",
        "N_primary_features_separability_pass",
        "N_distinct_passing_feature_signal_groups",
        "B5_negative_control_used",
        "B5_negative_control_support_gate",
        "B5_negative_control_skipped_reason",
        "validation_outcome_read",
        "max_ep19_terminal_state",
        "next_allowed_requirement",
        "next_research_suggestion",
        "model_training_authorized",
        "entry_policy_authorized",
        "exit_policy_authorized",
        "holding_policy_authorized",
        "portfolio_backtest_authorized",
        "model_deployment_authorized",
        "production_signal_authorized",
        "live_trading_authorized",
        "19C_replay_authorized",
        "EP20_policy_preflight_authorized",
    ],
}
FORBIDDEN_PREFIXES = ("forward_mfe_", "forward_mae_", "forward_return_", "forward_big_winner_")
FORBIDDEN_NAMES = {
    "fast_fail_flag",
    "false_repair_flag",
    "MFE_120",
    "MAE_20",
    "right_tail_event_50",
    "left_tail_event_10",
    "left_tail_event_20",
    "right_clean",
    "left_bad",
    "both",
    "neither",
}
B_HASH_KEY_MAP = {
    "nineteen_b_decision": ["entry_universe_19b_decision"],
    "robustness_candidate_row_manifest": ["robustness_candidate_row_manifest"],
    "robustness_outcome_boundary_audit": ["robustness_outcome_boundary_audit"],
    "robustness_metric_readout": ["robustness_metric_readout"],
    "false_positive_burden_readout": ["false_positive_burden_readout"],
    "mfe_mae_joint_readout": ["mfe_mae_joint_readout"],
    "nineteen_b_handoff_contract": ["19B_handoff_contract", "handoff_contract"],
}
SPECIAL_19B_OUTPUT_FILES = {
    "handoff_contract": "19B_handoff_contract.md",
    "19B_handoff_contract": "19B_handoff_contract.md",
    "report": "19B_robust_right_tail_enrichment_and_false_positive_burden_readout_report.md",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP19B1 diagnostic T0 left/right tail separability readout.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    return parser.parse_args(argv)


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("experiments/", "data/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_input_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("input_paths", {}).items()}


def resolve_output_root(config: dict[str, Any]) -> Path:
    return topic_path(config.get("output", {}).get("output_root", OUTPUT_ROOT))


def output_paths(output_root: Path | None = None) -> dict[str, Path]:
    root = output_root or OUTPUT_ROOT
    figures = root / "figures"
    return {
        "input_artifact_audit": root / "input_artifact_audit.csv",
        "upstream_contract_audit": root / "upstream_contract_audit.csv",
        "t0_feature_join_audit": root / "t0_feature_join_audit.csv",
        "t0_feature_source_audit": root / "t0_feature_source_audit.csv",
        "t0_feature_matrix_manifest": root / "t0_feature_matrix_manifest.csv",
        "outcome_left_right_overlap_readout": root / "outcome_left_right_overlap_readout.csv",
        "t0_univariate_feature_separability_readout": root / "t0_univariate_feature_separability_readout.csv",
        "t0_multivariate_diagnostic_separability_readout": root / "t0_multivariate_diagnostic_separability_readout.csv",
        "t0_separability_stability_readout": root / "t0_separability_stability_readout.csv",
        "search_accounting_audit": root / "search_accounting_audit.csv",
        "entry_universe_19b1_decision": root / "entry_universe_19b1_decision.csv",
        "b2_outcome_left_right_overlap_figure": figures / "b2_outcome_left_right_overlap.png",
        "b2_t0_top_feature_distributions_figure": figures / "b2_t0_top_feature_distributions.png",
        "b2_t0_feature_auc_forest_figure": figures / "b2_t0_feature_auc_forest.png",
        "b2_t0_separability_stability_figure": figures / "b2_t0_separability_stability.png",
        "report": root / "19B1_t0_left_right_tail_separability_readout_report.md",
        "handoff_contract": root / "19B1_handoff_contract.md",
        "manifest": root / "manifest_19b1_t0_left_right_tail_separability_readout.json",
        "output_hashes": root / "output_hashes_19b1_t0_left_right_tail_separability_readout.json",
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pass_fail(condition: bool) -> str:
    return "pass" if bool(condition) else "fail"


def as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if pd.isna(value):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y", "pass"}


def rel(path: Path) -> str:
    return b0.rel(path)


def safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def safe_div(num: float, den: float) -> float:
    return float(num / den) if den else float("nan")


def json_text(value: Any) -> str:
    return json.dumps(b0.clean_json(value), ensure_ascii=False, sort_keys=True)


def stable_hash_payload(payload: Any) -> str:
    text = json.dumps(b0.clean_json(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def frame_hash(frame: pd.DataFrame, columns: list[str]) -> str:
    existing = [col for col in columns if col in frame.columns]
    csv = frame[existing].sort_values(existing[: min(4, len(existing))]).to_csv(index=False)
    return hashlib.sha256(csv.encode("utf-8")).hexdigest()


def numeric_feature(frame: pd.DataFrame, feature: str) -> pd.Series:
    series = frame[feature]
    if series.dtype == bool:
        return series.astype(float)
    return pd.to_numeric(series, errors="coerce")


def validate_config_contract(config: dict[str, Any], paths: dict[str, Path], output_root: Path) -> tuple[str, str]:
    reasons: list[str] = []
    if config.get("run_id") != RUN_ID:
        reasons.append("run_id_mismatch")
    if config.get("experiment_id") != EXPERIMENT_ID:
        reasons.append("experiment_id_mismatch")
    if config.get("phase_id") != PHASE_ID:
        reasons.append("phase_id_mismatch")
    missing_inputs = sorted(set(REQUIRED_INPUT_KEYS) - set(config.get("input_paths", {})))
    if missing_inputs:
        reasons.append("missing_input_paths:" + "|".join(missing_inputs))
    if list(config.get("feature_contract", {}).get("primary_t0_feature_whitelist", [])) != PRIMARY_FEATURE_WHITELIST:
        reasons.append("primary_t0_feature_whitelist_not_frozen_or_expanded")
    if list(config.get("feature_contract", {}).get("accounting_only_columns", [])) != ACCOUNTING_ONLY_COLUMNS:
        reasons.append("accounting_only_columns_mismatch")
    expected_thresholds = {"right_tail_event_50": 0.50, "left_tail_event_10": -0.10, "left_tail_event_20": -0.20}
    for key, expected in expected_thresholds.items():
        if safe_float(config.get("thresholds", {}).get(key)) != expected:
            reasons.append(f"threshold_{key}_mismatch")
    expected_support = {
        "candidate_n_min": 300,
        "instrument_n_min": 30,
        "right_clean_n_min": 50,
        "left_bad_n_min": 50,
        "per_feature_left_bad_nonmissing_n_min": 50,
        "per_feature_right_clean_nonmissing_n_min": 50,
        "per_feature_max_group_missing_rate": 0.20,
        "per_feature_max_missing_rate_delta_abs": 0.10,
    }
    for key, expected in expected_support.items():
        if safe_float(config.get("support", {}).get(key)) != float(expected):
            reasons.append(f"support_{key}_mismatch")
    expected_bootstrap = {
        "bootstrap_resample_n": 2000,
        "bootstrap_seed": 20260709,
        "cluster_key": "instrument_id",
        "leave_one_month_min_effective_fold_n_for_reporting": 6,
        "leave_one_month_out_required_for_stability_gate": False,
        "stability_bootstrap_direction_stable_rate_min": 0.70,
    }
    for key, expected in expected_bootstrap.items():
        observed = config.get("bootstrap", {}).get(key)
        if isinstance(expected, bool):
            ok = bool(observed) is expected
        elif isinstance(expected, (int, float)):
            ok = safe_float(observed) == float(expected)
        else:
            ok = observed == expected
        if not ok:
            reasons.append(f"bootstrap_{key}_mismatch")
    expected_probe = {
        "multivariate_enabled": False,
        "logistic_regularization_C": 1.0,
        "rank_bin_count": 10,
        "decision_stump_max_depth": 1,
        "random_seed": 20260709,
    }
    for key, expected in expected_probe.items():
        observed = config.get("diagnostic_probe", {}).get(key)
        if isinstance(expected, bool):
            ok = bool(observed) is expected
        elif isinstance(expected, (int, float)):
            ok = safe_float(observed) == float(expected)
        else:
            ok = observed == expected
        if not ok:
            reasons.append(f"diagnostic_probe_{key}_mismatch")
    if config.get("diagnostic_probe", {}).get("crossfit_cluster_key") not in {"instrument_id", "instrument_month"}:
        reasons.append("diagnostic_probe_crossfit_cluster_key_mismatch")
    if config.get("output", {}).get("output_root_may_be_created") is not True:
        reasons.append("output_root_may_be_created_mismatch")
    if config.get("output", {}).get("output_root_parent_must_exist") is not True:
        reasons.append("output_root_parent_must_exist_mismatch")
    if not output_root.parent.exists():
        reasons.append("output_root_parent_missing")
    for key, path in paths.items():
        if key in REQUIRED_INPUT_KEYS and path.is_absolute() and not (
            str(path).startswith(str(REPO_ROOT)) or str(path).startswith(str(TOPIC_ROOT))
        ):
            reasons.append(f"input_path_outside_repo:{key}")
    return pass_fail(not reasons), ";".join(reasons)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_19b_output_hash_path(output_root: Path, artifact_id: str) -> Path:
    if artifact_id in SPECIAL_19B_OUTPUT_FILES:
        return output_root / SPECIAL_19B_OUTPUT_FILES[artifact_id]
    if artifact_id.endswith("_figure"):
        return output_root / "figures" / f"{artifact_id.removesuffix('_figure')}.png"
    for suffix in [".csv", ".md", ".json", ".png"]:
        candidate = output_root / f"{artifact_id}{suffix}"
        if candidate.exists():
            return candidate
    return output_root / artifact_id


def build_19b_output_hash_audit_rows(paths: dict[str, Path]) -> tuple[list[dict[str, Any]], str]:
    upstream_hashes = read_json(paths["nineteen_b_output_hashes"])
    rows: list[dict[str, Any]] = []
    for artifact_id, expected_hash in sorted(upstream_hashes.items()):
        path = resolve_19b_output_hash_path(paths["nineteen_b_output_root"], artifact_id)
        exists = path.exists()
        observed_hash = b0.artifact_hash(path) if exists else ""
        verified = exists and observed_hash == str(expected_hash)
        rows.append(
            contract_row(
                "19B_hash",
                artifact_id,
                path,
                "observed_hash_matches_19b_output_hashes",
                True,
                verified,
                hash_verified=verified,
                blocking_reason="upstream_19b_hash_mismatch",
            )
        )
    return rows, pass_fail(all(row["contract_gate"] == "pass" for row in rows))


def build_input_artifact_audit(paths: dict[str, Path]) -> tuple[pd.DataFrame, str, dict[str, str]]:
    try:
        upstream_hashes = read_json(paths["nineteen_b_output_hashes"]) if paths.get("nineteen_b_output_hashes", Path()).exists() else {}
    except Exception:  # noqa: BLE001
        upstream_hashes = {}
    input_hashes: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    for key in REQUIRED_INPUT_KEYS:
        path = paths.get(key, Path(""))
        exists = path.exists()
        observed_hash = b0.artifact_hash(path) if exists else ""
        input_hashes[key] = observed_hash
        cols = b0.column_names(path) if exists and path.is_file() else []
        expected_hash = ""
        hash_verified = True
        if key in B_HASH_KEY_MAP:
            for hash_key in B_HASH_KEY_MAP[key]:
                if hash_key in upstream_hashes:
                    expected_hash = str(upstream_hashes[hash_key])
                    break
            hash_verified = bool(expected_hash) and observed_hash == expected_hash
        gate = exists and bool(observed_hash) and hash_verified
        reason = "" if gate else ("missing_required_input_artifact" if not exists else "upstream_19b_hash_mismatch")
        rows.append(
            {
                "artifact_id": key,
                "relative_path": rel(path) if exists else str(path),
                "exists": exists,
                "artifact_type": "directory" if exists and path.is_dir() else path.suffix,
                "row_count": b0.row_count(path) if exists else 0,
                "column_count": len(cols),
                "columns": "|".join(cols[:80]),
                "observed_hash": observed_hash,
                "expected_hash": expected_hash,
                "hash_verified": hash_verified,
                "input_artifact_gate": pass_fail(gate),
                "blocking_reason": reason,
            }
        )
    frame = pd.DataFrame(rows)
    return frame, pass_fail(frame["input_artifact_gate"].eq("pass").all()), input_hashes


def contract_row(
    upstream_scope: str,
    artifact_id: str,
    source_file: Path,
    required_fact: str,
    expected_value: Any,
    observed_value: Any,
    source_row_filter: str = "",
    hash_verified: Any = "",
    validation_outcome_read: Any = False,
    authorization_field: str = "",
    authorization_value: Any = "",
    blocking_reason: str = "",
) -> dict[str, Any]:
    ok = expected_value == observed_value if not isinstance(expected_value, list) else observed_value in expected_value
    reason = blocking_reason if ok else (blocking_reason or "contract_fact_mismatch")
    return {
        "upstream_scope": upstream_scope,
        "artifact_id": artifact_id,
        "source_file": rel(source_file),
        "required_fact": required_fact,
        "expected_value": json_text(expected_value),
        "observed_value": json_text(observed_value),
        "source_row_filter": source_row_filter,
        "derived_gate": pass_fail(ok),
        "contract_gate": pass_fail(ok),
        "hash_verified": hash_verified,
        "validation_outcome_read": validation_outcome_read,
        "authorization_field": authorization_field,
        "authorization_value": authorization_value,
        "blocking_reason": "" if ok else reason,
    }


def build_upstream_contract_audit(paths: dict[str, Path], input_audit: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    rows: list[dict[str, Any]] = []
    upstream_19a = pd.read_csv(paths["upstream_19a_contract_audit"])
    upstream_19b0 = pd.read_csv(paths["upstream_19b0_contract_audit"])
    gate_19a = pass_fail(upstream_19a["contract_gate"].eq("pass").all())
    gate_19b0 = pass_fail(upstream_19b0["contract_gate"].eq("pass").all())
    rows.append(contract_row("19A", "upstream_19a_contract_audit", paths["upstream_19a_contract_audit"], "aggregate_contract_gate", "pass", gate_19a))
    rows.append(contract_row("19B0", "upstream_19b0_contract_audit", paths["upstream_19b0_contract_audit"], "aggregate_contract_gate", "pass", gate_19b0))

    decision = pd.read_csv(paths["nineteen_b_decision"]).iloc[0].to_dict()
    boundary = pd.read_csv(paths["robustness_outcome_boundary_audit"]).iloc[0].to_dict()
    metric = pd.read_csv(paths["robustness_metric_readout"])
    manifest = pd.read_csv(paths["robustness_candidate_row_manifest"])
    primary = config["primary_scope"]
    b2_metric = metric.loc[
        metric["family_id"].eq(primary["family_id"]) & metric["grid_cell_id"].eq(primary["grid_cell_id"])
    ].iloc[0].to_dict()
    allowed_states = [
        "19B_false_positive_burden_blocked",
        "19B_positive_exposure_persistent_enrichment_only_diagnostic",
        "19B_baseline_quality_blocked_enrichment_only_diagnostic_possible",
    ]
    facts = [
        ("decision_state", allowed_states, decision.get("decision_state")),
        ("validation_outcome_read", False, as_bool(decision.get("validation_outcome_read"))),
        ("N_family_brought_to_robustness", 2, int(decision.get("N_family_brought_to_robustness", -1))),
        ("N_tested_family_cell_pairs", 2, int(decision.get("N_tested_family_cell_pairs", -1))),
        ("positive_exposure_robustness_gate", "pass", decision.get("positive_exposure_robustness_gate")),
        ("matched_baseline_residual_gate", "fail", decision.get("matched_baseline_residual_gate")),
        (
            "max_ep19_terminal_state_if_no_residual_pass",
            "19_entry_universe_enrichment_only_diagnostic",
            decision.get("max_ep19_terminal_state_if_no_residual_pass"),
        ),
        ("robustness_candidate_manifest_gate", "pass", decision.get("robustness_candidate_manifest_gate")),
        ("outcome_boundary_gate", "pass", decision.get("outcome_boundary_gate")),
        ("B2_cell_decision_state", "false_positive_burden_blocked", b2_metric.get("cell_decision_state")),
    ]
    for fact, expected, observed in facts:
        rows.append(contract_row("19B", "entry_universe_19b_decision", paths["nineteen_b_decision"], fact, expected, observed))
    for column in b0.POLICY_AUTH_COLUMNS:
        rows.append(
            contract_row(
                "19B",
                "entry_universe_19b_decision",
                paths["nineteen_b_decision"],
                column,
                False,
                as_bool(decision.get(column)),
                authorization_field=column,
                authorization_value=as_bool(decision.get(column)),
            )
        )
    frozen = as_bool(boundary.get("robustness_candidate_manifest_frozen_before_label_readout")) and (
        manifest["manifest_frozen_before_label_readout"].fillna(False).astype(bool).all()
    )
    label_read_before_freeze = manifest["label_read_before_manifest_freeze"].fillna(False).astype(bool).any()
    boundary_gate = decision.get("outcome_boundary_gate") == "pass" and boundary.get("boundary_gate") == "pass"
    rows.extend(
        [
            contract_row("19B_boundary", "robustness_outcome_boundary_audit", paths["robustness_outcome_boundary_audit"], "outcome_boundary_gate", True, boundary_gate),
            contract_row(
                "19B_boundary",
                "robustness_candidate_row_manifest",
                paths["robustness_candidate_row_manifest"],
                "robustness_candidate_manifest_frozen_before_label_readout",
                True,
                frozen,
            ),
            contract_row(
                "19B_boundary",
                "robustness_candidate_row_manifest",
                paths["robustness_candidate_row_manifest"],
                "label_read_before_manifest_freeze",
                False,
                label_read_before_freeze,
            ),
        ]
    )
    hash_rows, hash_gate = build_19b_output_hash_audit_rows(paths)
    rows.extend(hash_rows)
    audit = pd.DataFrame(rows, columns=CSV_SCHEMAS["upstream_contract_audit"])
    gates = {
        "upstream_19a_contract_gate": gate_19a,
        "upstream_19b0_contract_gate": gate_19b0,
        "upstream_19b_contract_gate": pass_fail(
            hash_gate == "pass"
            and audit.loc[audit["upstream_scope"].isin(["19B", "19B_boundary", "19B_hash"]), "contract_gate"].eq("pass").all()
        ),
    }
    return audit, gates


def load_feature_panel(config: dict[str, Any], paths: dict[str, Path]) -> pd.DataFrame:
    panel_cols = ["instrument", "decision_date", "decision_month", "instrument_month", *PRIMARY_FEATURE_WHITELIST]
    cache = resolve_output_root(config) / "local_cache" / "t0_feature_panel_candidate_dates_v1.parquet"
    primary = config["primary_scope"]
    mfe = pd.read_csv(paths["mfe_mae_joint_readout"], usecols=["family_id", "grid_cell_id", "split", "row_scope", "instrument_id", "decision_date"])
    scopes = {
        (primary["family_id"], primary["grid_cell_id"]),
        ("B5_recent_high_close_plus_amount_expansion", "B5-recent-high-close-plus-amount-expansion__25d72c708fc1"),
    }
    scoped = mfe.loc[
        mfe["split"].eq(primary["split"])
        & mfe["row_scope"].eq(primary["row_scope"])
        & pd.MultiIndex.from_frame(mfe[["family_id", "grid_cell_id"]]).isin(scopes)
    ].copy()
    candidate_dates = sorted(pd.to_datetime(scoped["decision_date"]).dt.strftime("%Y-%m-%d").unique())
    if config.get("runtime", {}).get("cache_universe_feature_panel", True) and cache.exists():
        cached_dates = set(pd.read_parquet(cache, columns=["decision_date"])["decision_date"].astype(str).unique())
        if set(candidate_dates).issubset(cached_dates):
            return pd.read_parquet(cache, columns=panel_cols)

    universe_cols = [
        "usable_trade_date",
        "instrument",
        "total_market_cap_cny",
    ]
    universe = b0.read_table(paths["topn_executable_universe"], usecols=universe_cols)
    universe["usable_trade_date"] = pd.to_datetime(universe["usable_trade_date"]).dt.strftime("%Y-%m-%d")
    universe = universe.loc[universe["usable_trade_date"].isin(candidate_dates)].copy()
    benchmark = b0.load_benchmark_features(paths["benchmark_daily"])
    stock_dir = paths["stock_qfq_dir"]
    frames: list[pd.DataFrame] = []
    grouped = universe.groupby("instrument", sort=True)
    progress_every = int(config.get("runtime", {}).get("progress_every_instruments", 250))
    for idx, (instrument, group) in enumerate(grouped, start=1):
        qfq_path = stock_dir / f"{instrument}.csv"
        if not qfq_path.exists():
            continue
        feature = b0.compute_qfq_feature_frame(qfq_path, benchmark)
        close = pd.to_numeric(feature["close_asof_decision_date"], errors="coerce")
        feature["match_amount20"] = pd.to_numeric(feature["rolling_20d_money_mean_asof_decision_date"], errors="coerce")
        feature["match_return20"] = pd.to_numeric(feature["return_20d_asof_decision_date"], errors="coerce")
        feature["match_vol60"] = close.pct_change().rolling(60, min_periods=60).std()
        selected = group.merge(
            feature,
            left_on=["instrument", "usable_trade_date"],
            right_on=["instrument", "decision_date"],
            how="inner",
        )
        if not selected.empty:
            frames.append(selected)
        if progress_every and idx % progress_every == 0:
            print(f"[19B1] rebuilt PIT feature panel for {idx}/{len(grouped)} instruments")
    panel = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=panel_cols)
    if panel.empty:
        return panel
    panel["match_market_cap"] = pd.to_numeric(panel["total_market_cap_cny"], errors="coerce")
    panel["return_60d_cross_section_rank_pct_asof_decision_date"] = panel.groupby("decision_date")[
        "return_60d_asof_decision_date"
    ].rank(pct=True)
    panel["atr_20_pct_rank_asof_decision_date"] = panel.groupby("decision_date")["atr_20_pct_asof_decision_date"].rank(pct=True)
    panel["decision_month"] = pd.to_datetime(panel["decision_date"]).dt.to_period("M").astype(str)
    panel["instrument_month"] = panel["instrument"].astype(str) + "|" + panel["decision_month"].astype(str)
    cache.parent.mkdir(parents=True, exist_ok=True)
    panel[panel_cols].to_parquet(cache, index=False)
    return panel[panel_cols].copy()


def add_outcome_labels(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    out = frame.copy()
    thresholds = config["thresholds"]
    out["right_tail_event_50"] = pd.to_numeric(out["MFE_120"], errors="coerce") >= float(thresholds["right_tail_event_50"])
    out["left_tail_event_10"] = pd.to_numeric(out["MAE_20"], errors="coerce") <= float(thresholds["left_tail_event_10"])
    out["left_tail_event_20"] = pd.to_numeric(out["MAE_20"], errors="coerce") <= float(thresholds["left_tail_event_20"])
    out["right_clean"] = out["right_tail_event_50"] & ~out["left_tail_event_10"]
    out["left_bad"] = out["left_tail_event_10"] & ~out["right_tail_event_50"]
    out["both"] = out["right_tail_event_50"] & out["left_tail_event_10"]
    out["neither"] = ~out["right_tail_event_50"] & ~out["left_tail_event_10"]
    out["decision_month"] = pd.to_datetime(out["decision_date"]).dt.to_period("M").astype(str)
    out["instrument_month"] = out["instrument_id"].astype(str) + "|" + out["decision_month"].astype(str)
    return out


def build_primary_matrix(
    config: dict[str, Any],
    paths: dict[str, Path],
    panel: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    primary = config["primary_scope"]
    keys = ["family_id", "grid_cell_id", "row_key", "instrument_id", "decision_date"]
    mfe = pd.read_csv(paths["mfe_mae_joint_readout"])
    metric = pd.read_csv(paths["robustness_metric_readout"])
    manifest = pd.read_csv(paths["robustness_candidate_row_manifest"])
    mfe_primary = mfe.loc[
        mfe["family_id"].eq(primary["family_id"])
        & mfe["grid_cell_id"].eq(primary["grid_cell_id"])
        & mfe["split"].eq(primary["split"])
        & mfe["row_scope"].eq(primary["row_scope"])
        & ~mfe["diagnostic_only_flag"].fillna(False).astype(bool)
    ].copy()
    manifest_primary = manifest.loc[
        manifest["family_id"].eq(primary["family_id"])
        & manifest["grid_cell_id"].eq(primary["grid_cell_id"])
        & manifest["split"].eq(primary["split"])
        & manifest["primary_enrichment_denominator_flag"].fillna(False).astype(bool)
    ].copy()
    expected_n = int(
        metric.loc[
            metric["family_id"].eq(primary["family_id"]) & metric["grid_cell_id"].eq(primary["grid_cell_id"]),
            "candidate_n",
        ].iloc[0]
    )
    duplicate_join_key_n = int(mfe_primary.duplicated(keys).sum() + manifest_primary.duplicated(keys).sum())
    joined = mfe_primary.merge(
        manifest_primary[keys + ["candidate_flag", "primary_enrichment_denominator_flag", "manifest_frozen_before_label_readout", "label_read_before_manifest_freeze"]],
        on=keys,
        how="left",
        indicator=True,
    )
    missing_n = int(joined["_merge"].eq("left_only").sum())
    mfe_key = pd.MultiIndex.from_frame(mfe_primary[keys])
    manifest_key = pd.MultiIndex.from_frame(manifest_primary[keys])
    extra_manifest_row_n = int((~manifest_key.isin(mfe_key)).sum())
    false_primary_n = int((~joined["primary_enrichment_denominator_flag"].fillna(False).astype(bool)).sum())
    frozen_false_n = int((~joined["manifest_frozen_before_label_readout"].fillna(False).astype(bool)).sum())
    label_before_true_n = int(joined["label_read_before_manifest_freeze"].fillna(False).astype(bool).sum())

    panel_small = panel.rename(columns={"instrument": "instrument_id"})
    matrix = joined.drop(columns=["_merge"]).merge(panel_small, on=["instrument_id", "decision_date"], how="left", suffixes=("", "_panel"))
    matrix = add_outcome_labels(matrix, config)
    feature_missing_any_primary_n = int(matrix[PRIMARY_FEATURE_WHITELIST].isna().any(axis=1).sum())
    join_pass = (
        len(mfe_primary) == expected_n
        and len(joined) == expected_n
        and len(matrix) == expected_n
        and duplicate_join_key_n == 0
        and missing_n == 0
        and extra_manifest_row_n == 0
        and false_primary_n == 0
        and frozen_false_n == 0
        and label_before_true_n == 0
    )
    audit = pd.DataFrame(
        [
            {
                "family_id": primary["family_id"],
                "grid_cell_id": primary["grid_cell_id"],
                "row_scope": primary["row_scope"],
                "split": primary["split"],
                "expected_candidate_n_from_19b_metric": expected_n,
                "observed_candidate_n_from_mfe_mae_joint": len(mfe_primary),
                "observed_candidate_n_after_manifest_join": len(joined),
                "unique_join_key_n": int(mfe_primary[keys].drop_duplicates().shape[0]),
                "duplicate_join_key_n": duplicate_join_key_n,
                "missing_in_candidate_manifest_n": missing_n,
                "extra_manifest_row_n": extra_manifest_row_n,
                "primary_enrichment_denominator_flag_false_n": false_primary_n,
                "manifest_frozen_before_label_readout_false_n": frozen_false_n,
                "label_read_before_manifest_freeze_true_n": label_before_true_n,
                "feature_matrix_row_n": len(matrix),
                "feature_missing_any_primary_n": feature_missing_any_primary_n,
                "primary_row_join_gate": pass_fail(join_pass),
                "blocking_reason": "" if join_pass else "primary_candidate_row_scope_or_join_contract_failed",
            }
        ],
        columns=CSV_SCHEMAS["t0_feature_join_audit"],
    )
    return matrix, audit


def contingency_metrics(matrix: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    candidate_n = len(matrix)
    right = matrix["right_tail_event_50"].astype(bool)
    left = matrix["left_tail_event_10"].astype(bool)
    a = int((left & right).sum())
    b = int((~left & right).sum())
    c = int((left & ~right).sum())
    d = int((~left & ~right).sum())
    table = np.array([[a, b], [c, d]], dtype=float)
    fisher_p = float(stats.fisher_exact(table)[1]) if table.sum() else float("nan")
    try:
        chi_p = float(stats.chi2_contingency(table, correction=False)[1])
    except ValueError:
        chi_p = float("nan")
    denom = math.sqrt(float((a + b) * (c + d) * (a + c) * (b + d)))
    phi = float((a * d - b * c) / denom) if denom else float("nan")
    probs = table / max(float(table.sum()), 1.0)
    row = probs.sum(axis=1, keepdims=True)
    col = probs.sum(axis=0, keepdims=True)
    mi = 0.0
    for i in range(2):
        for j in range(2):
            if probs[i, j] > 0 and row[i, 0] > 0 and col[0, j] > 0:
                mi += float(probs[i, j] * math.log(probs[i, j] / (row[i, 0] * col[0, j])))
    p_left_given_right = safe_div(a, a + b)
    p_left_given_not_right = safe_div(c, c + d)
    p_right_given_left = safe_div(a, a + c)
    p_right_given_not_left = safe_div(b, b + d)
    diff = p_left_given_not_right - p_left_given_right
    rng = np.random.default_rng(int(config["bootstrap"]["bootstrap_seed"]))
    clusters = matrix[config["bootstrap"]["cluster_key"]].astype(str).unique()
    by_cluster = {cluster: matrix.index[matrix[config["bootstrap"]["cluster_key"]].astype(str).eq(cluster)].to_numpy() for cluster in clusters}
    draws = []
    for _ in range(int(config["bootstrap"]["bootstrap_resample_n"])):
        sampled = rng.choice(clusters, size=len(clusters), replace=True)
        idx = np.concatenate([by_cluster[item] for item in sampled])
        sample = matrix.loc[idx]
        s_right = sample["right_tail_event_50"].astype(bool)
        s_left = sample["left_tail_event_10"].astype(bool)
        sa = int((s_left & s_right).sum())
        sb = int((~s_left & s_right).sum())
        sc = int((s_left & ~s_right).sum())
        sd = int((~s_left & ~s_right).sum())
        draws.append(safe_div(sc, sc + sd) - safe_div(sa, sa + sb))
    ci_low, ci_high = np.nanpercentile(draws, [2.5, 97.5])
    support = config["support"]
    right_clean_n = int(matrix["right_clean"].sum())
    left_bad_n = int(matrix["left_bad"].sum())
    gate = diff > 0 and ci_low > 0
    row = {
        "family_id": config["primary_scope"]["family_id"],
        "grid_cell_id": config["primary_scope"]["grid_cell_id"],
        "split": config["primary_scope"]["split"],
        "row_scope": config["primary_scope"]["row_scope"],
        "candidate_n": candidate_n,
        "instrument_n": int(matrix["instrument_id"].nunique()),
        "right_tail_event_50_n": int(right.sum()),
        "left_tail_event_10_n": int(left.sum()),
        "left_tail_event_20_n": int(matrix["left_tail_event_20"].sum()),
        "right_clean_n": right_clean_n,
        "left_bad_n": left_bad_n,
        "both_n": int(matrix["both"].sum()),
        "neither_n": int(matrix["neither"].sum()),
        "p_left_tail_10_given_right_tail_50": p_left_given_right,
        "p_left_tail_10_given_not_right_tail_50": p_left_given_not_right,
        "p_right_tail_50_given_left_tail_10": p_right_given_left,
        "p_right_tail_50_given_not_left_tail_10": p_right_given_not_left,
        "left_tail_conditional_probability_diff_not_right_minus_right": diff,
        "right_tail_conditional_probability_diff_not_left_minus_left": p_right_given_not_left - p_right_given_left,
        "fisher_exact_p_value": fisher_p,
        "chi_square_p_value": chi_p,
        "phi_coefficient": phi,
        "mutual_information": mi,
        "cluster_bootstrap_diff_ci_low": ci_low,
        "cluster_bootstrap_diff_ci_high": ci_high,
        "outcome_overlap_gate": pass_fail(gate),
        "diagnostic_only_flag": True,
        "blocking_reason": "" if gate else "outcome_overlap_gate_failed",
    }
    sample_gate = pass_fail(
        candidate_n >= int(support["candidate_n_min"])
        and int(matrix["instrument_id"].nunique()) >= int(support["instrument_n_min"])
        and right_clean_n >= int(support["right_clean_n_min"])
        and left_bad_n >= int(support["left_bad_n_min"])
    )
    return pd.DataFrame([row], columns=CSV_SCHEMAS["outcome_left_right_overlap_readout"]), sample_gate


def auc_raw(left_values: pd.Series, right_values: pd.Series) -> float:
    left_values = pd.Series(left_values).dropna()
    right_values = pd.Series(right_values).dropna()
    if left_values.empty or right_values.empty:
        return float("nan")
    values = np.concatenate([left_values.to_numpy(dtype=float), right_values.to_numpy(dtype=float)])
    labels = np.concatenate([np.ones(len(left_values)), np.zeros(len(right_values))])
    ranks = stats.rankdata(values)
    sum_pos = ranks[labels == 1].sum()
    n_pos = len(left_values)
    n_neg = len(right_values)
    return float((sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def direction_from_median(diff: float, support_pass: bool) -> str:
    if not support_pass or not math.isfinite(diff) or diff == 0:
        return "flat"
    return "positive" if diff > 0 else "negative"


def bh_adjust(p_values: list[float]) -> list[float]:
    p = np.asarray([np.nan if pd.isna(value) else float(value) for value in p_values], dtype=float)
    out = np.full_like(p, np.nan)
    valid = np.isfinite(p)
    if not valid.any():
        return out.tolist()
    valid_p = p[valid]
    order = np.argsort(valid_p)
    ranked = valid_p[order]
    n = len(ranked)
    adj = np.minimum.accumulate((ranked * n / np.arange(1, n + 1))[::-1])[::-1]
    adj = np.clip(adj, 0, 1)
    restored = np.empty(n)
    restored[order] = adj
    out[valid] = restored
    return out.tolist()


def sidak_adjust(p: float, n: int) -> float:
    if not math.isfinite(p):
        return float("nan")
    return float(min(1.0, 1.0 - (1.0 - p) ** n))


def cluster_bootstrap_feature(
    matrix: pd.DataFrame,
    feature: str,
    direction: str,
    config: dict[str, Any],
) -> dict[str, float]:
    rng = np.random.default_rng(int(config["bootstrap"]["bootstrap_seed"]) + stable_int(feature))
    cluster_key = config["bootstrap"]["cluster_key"]
    clusters = matrix[cluster_key].astype(str).unique()
    by_cluster = {cluster: matrix.index[matrix[cluster_key].astype(str).eq(cluster)].to_numpy() for cluster in clusters}
    med_diffs: list[float] = []
    oriented_aucs: list[float] = []
    stable = 0
    for _ in range(int(config["bootstrap"]["bootstrap_resample_n"])):
        sampled = rng.choice(clusters, size=len(clusters), replace=True)
        idx = np.concatenate([by_cluster[item] for item in sampled])
        sample = matrix.loc[idx]
        left = numeric_feature(sample.loc[sample["left_bad"]], feature).dropna()
        right = numeric_feature(sample.loc[sample["right_clean"]], feature).dropna()
        if left.empty or right.empty:
            continue
        med_diff = float(left.median() - right.median())
        raw_auc = auc_raw(left, right)
        oriented = (1.0 - raw_auc) if direction == "negative" else raw_auc
        med_diffs.append(med_diff)
        oriented_aucs.append(oriented)
        check_direction = "positive" if med_diff > 0 else ("negative" if med_diff < 0 else "flat")
        if check_direction == direction:
            stable += 1
    if not med_diffs:
        return {
            "median_ci_low": float("nan"),
            "median_ci_high": float("nan"),
            "auc_ci_low": float("nan"),
            "auc_ci_high": float("nan"),
            "direction_stable_rate": float("nan"),
        }
    return {
        "median_ci_low": float(np.nanpercentile(med_diffs, 2.5)),
        "median_ci_high": float(np.nanpercentile(med_diffs, 97.5)),
        "auc_ci_low": float(np.nanpercentile(oriented_aucs, 2.5)),
        "auc_ci_high": float(np.nanpercentile(oriented_aucs, 97.5)),
        "direction_stable_rate": float(stable / len(med_diffs)),
    }


def stable_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def build_univariate_readout(matrix: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    support = config["support"]
    rows: list[dict[str, Any]] = []
    left_mask = matrix["left_bad"].astype(bool)
    right_mask = matrix["right_clean"].astype(bool)
    for feature in PRIMARY_FEATURE_WHITELIST:
        left = numeric_feature(matrix.loc[left_mask], feature)
        right = numeric_feature(matrix.loc[right_mask], feature)
        left_non = left.dropna()
        right_non = right.dropna()
        left_missing_rate = 1.0 - safe_div(len(left_non), len(left))
        right_missing_rate = 1.0 - safe_div(len(right_non), len(right))
        support_pass = (
            len(left_non) >= int(support["per_feature_left_bad_nonmissing_n_min"])
            and len(right_non) >= int(support["per_feature_right_clean_nonmissing_n_min"])
            and max(left_missing_rate, right_missing_rate) <= float(support["per_feature_max_group_missing_rate"])
            and abs(left_missing_rate - right_missing_rate) <= float(support["per_feature_max_missing_rate_delta_abs"])
        )
        left_median = float(left_non.median()) if not left_non.empty else float("nan")
        right_median = float(right_non.median()) if not right_non.empty else float("nan")
        med_diff = left_median - right_median
        direction = direction_from_median(med_diff, support_pass)
        raw_auc = auc_raw(left_non, right_non)
        oriented_auc = max(raw_auc, 1.0 - raw_auc) if math.isfinite(raw_auc) else float("nan")
        if len(left_non) and len(right_non):
            pooled_sd = math.sqrt((float(left_non.var(ddof=1)) + float(right_non.var(ddof=1))) / 2)
            smd = safe_div(float(left_non.mean() - right_non.mean()), pooled_sd)
            mw_p = float(stats.mannwhitneyu(left_non, right_non, alternative="two-sided").pvalue)
            ks_p = float(stats.ks_2samp(left_non, right_non, alternative="two-sided").pvalue)
        else:
            smd = mw_p = ks_p = float("nan")
        boot = cluster_bootstrap_feature(matrix, feature, direction, config) if support_pass else {
            "median_ci_low": float("nan"),
            "median_ci_high": float("nan"),
            "auc_ci_low": float("nan"),
            "auc_ci_high": float("nan"),
            "direction_stable_rate": float("nan"),
        }
        rows.append(
            {
                "family_id": config["primary_scope"]["family_id"],
                "grid_cell_id": config["primary_scope"]["grid_cell_id"],
                "split": config["primary_scope"]["split"],
                "row_scope": config["primary_scope"]["row_scope"],
                "feature_name": feature,
                "feature_signal_group": FEATURE_TO_GROUP[feature],
                "source_alias": MATCH_ALIAS.get(feature, ("", "", ""))[0],
                "left_bad_n": int(left_mask.sum()),
                "right_clean_n": int(right_mask.sum()),
                "left_bad_nonmissing_n": int(len(left_non)),
                "right_clean_nonmissing_n": int(len(right_non)),
                "left_bad_missing_rate": left_missing_rate,
                "right_clean_missing_rate": right_missing_rate,
                "missing_rate_delta_abs": abs(left_missing_rate - right_missing_rate),
                "left_bad_mean": float(left_non.mean()) if not left_non.empty else float("nan"),
                "left_bad_median": left_median,
                "left_bad_p25": float(left_non.quantile(0.25)) if not left_non.empty else float("nan"),
                "left_bad_p75": float(left_non.quantile(0.75)) if not left_non.empty else float("nan"),
                "right_clean_mean": float(right_non.mean()) if not right_non.empty else float("nan"),
                "right_clean_median": right_median,
                "right_clean_p25": float(right_non.quantile(0.25)) if not right_non.empty else float("nan"),
                "right_clean_p75": float(right_non.quantile(0.75)) if not right_non.empty else float("nan"),
                "standardized_mean_difference": smd,
                "median_difference": med_diff,
                "mann_whitney_u_p_value": mw_p,
                "kolmogorov_smirnov_p_value": ks_p,
                "feature_auc_raw_left_bad_positive": raw_auc,
                "feature_auc_oriented_left_bad_vs_right_clean": oriented_auc,
                "direction_for_left_bad": direction,
                "cluster_bootstrap_CI_for_median_difference": json_text([boot["median_ci_low"], boot["median_ci_high"]]),
                "cluster_bootstrap_median_difference_ci_low": boot["median_ci_low"],
                "cluster_bootstrap_median_difference_ci_high": boot["median_ci_high"],
                "cluster_bootstrap_oriented_auc_ci_low": boot["auc_ci_low"],
                "cluster_bootstrap_oriented_auc_ci_high": boot["auc_ci_high"],
                "cluster_bootstrap_direction_stable_rate": boot["direction_stable_rate"],
                "missing_rate_by_group": json_text({"left_bad": left_missing_rate, "right_clean": right_missing_rate}),
                "feature_support_gate": pass_fail(support_pass),
                "bh_fdr_adjusted_p": float("nan"),
                "bonferroni_sidak_adjusted_p": float("nan"),
                "separability_pass": False,
                "diagnostic_only_flag": True,
                "blocking_reason": "" if support_pass else "feature_support_gate_failed",
            }
        )
    frame = pd.DataFrame(rows)
    adjusted = bh_adjust(frame["mann_whitney_u_p_value"].tolist())
    frame["bh_fdr_adjusted_p"] = adjusted
    frame["bonferroni_sidak_adjusted_p"] = [sidak_adjust(p, len(frame)) for p in frame["mann_whitney_u_p_value"]]
    frame["separability_pass"] = (
        frame["feature_support_gate"].eq("pass")
        & frame["bh_fdr_adjusted_p"].le(0.10)
        & frame["standardized_mean_difference"].abs().ge(0.20)
        & frame["feature_auc_oriented_left_bad_vs_right_clean"].ge(0.57)
        & frame["cluster_bootstrap_oriented_auc_ci_low"].gt(0.50)
        & frame["direction_for_left_bad"].isin(["positive", "negative"])
    )
    return frame


def build_feature_source_audit(matrix: pd.DataFrame, univariate: pd.DataFrame, paths: dict[str, Path]) -> pd.DataFrame:
    simple = pd.read_csv(paths["simple_rule_feature_source_map"])
    simple_map = simple.set_index("feature_field").to_dict("index")
    rows: list[dict[str, Any]] = []
    for feature in PRIMARY_FEATURE_WHITELIST:
        uni = univariate.loc[univariate["feature_name"].eq(feature)].iloc[0].to_dict()
        if feature in MATCH_ALIAS:
            alias, artifact, columns = MATCH_ALIAS[feature]
            source_alias = alias
            source_artifact = artifact
            source_columns = columns
            asof_rule = "decision_date close"
        elif feature == "rolling_20d_money_mean_asof_decision_date":
            source_alias = ""
            source_artifact = "qfq money"
            source_columns = "money"
            asof_rule = "decision_date close"
        else:
            meta = simple_map.get(feature, {})
            source_alias = str(meta.get("candidate_column_alias_if_ep07", "") or "")
            source_artifact = str(meta.get("source_artifact", "") or "")
            source_columns = str(meta.get("source_columns", "") or "")
            asof_rule = str(meta.get("asof_rule", "decision_date close") or "decision_date close")
        rows.append(
            {
                "feature_name": feature,
                "feature_signal_group": FEATURE_TO_GROUP[feature],
                "source_alias": source_alias,
                "feature_value_type": "boolean" if matrix[feature].dtype == bool else "numeric",
                "source_artifact": source_artifact,
                "source_columns": source_columns,
                "asof_rule": asof_rule,
                "pit_safe_flag": True,
                "missing_rate": float(matrix[feature].isna().mean()),
                "left_bad_nonmissing_n": uni["left_bad_nonmissing_n"],
                "right_clean_nonmissing_n": uni["right_clean_nonmissing_n"],
                "left_bad_missing_rate": uni["left_bad_missing_rate"],
                "right_clean_missing_rate": uni["right_clean_missing_rate"],
                "missing_rate_delta_abs": uni["missing_rate_delta_abs"],
                "used_in_primary_readout": uni["feature_support_gate"] == "pass",
                "primary_whitelist_flag": True,
                "exploratory_only_flag": False,
                "feature_support_gate": uni["feature_support_gate"],
                "blocking_reason": "" if uni["feature_support_gate"] == "pass" else "feature_support_gate_failed",
            }
        )
    return pd.DataFrame(rows, columns=CSV_SCHEMAS["t0_feature_source_audit"])


def build_feature_only_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
    return matrix[ACCOUNTING_ONLY_COLUMNS + PRIMARY_FEATURE_WHITELIST].copy()


def build_feature_matrix_manifest(
    matrix: pd.DataFrame,
    source_audit: pd.DataFrame,
    univariate: pd.DataFrame,
    config: dict[str, Any],
    primary_whitelist_hash: str,
) -> pd.DataFrame:
    feature_matrix = build_feature_only_matrix(matrix)
    feature_matrix_cols = list(feature_matrix.columns)
    forbidden = [col for col in feature_matrix_cols if col in FORBIDDEN_NAMES or col.startswith(FORBIDDEN_PREFIXES)]
    forbidden_label = [col for col in feature_matrix_cols if col in FORBIDDEN_NAMES or "validation" in col]
    feature_missing_any = int(feature_matrix[PRIMARY_FEATURE_WHITELIST].isna().any(axis=1).sum())
    all_pit_safe = bool(source_audit["pit_safe_flag"].fillna(False).astype(bool).all())
    support_pass_n = int(univariate["feature_support_gate"].eq("pass").sum())
    gate = all_pit_safe and not forbidden and support_pass_n > 0
    row = {
        "family_id": config["primary_scope"]["family_id"],
        "grid_cell_id": config["primary_scope"]["grid_cell_id"],
        "row_scope": config["primary_scope"]["row_scope"],
        "split": config["primary_scope"]["split"],
        "row_n": len(feature_matrix),
        "feature_n": len(PRIMARY_FEATURE_WHITELIST),
        "primary_feature_columns_json": json_text(PRIMARY_FEATURE_WHITELIST),
        "accounting_only_columns_json": json_text(ACCOUNTING_ONLY_COLUMNS),
        "exploratory_feature_columns_json": json_text([]),
        "forbidden_column_n": len(forbidden),
        "forbidden_columns_json": json_text(forbidden),
        "forbidden_label_column_n": len(forbidden_label),
        "forbidden_label_columns_json": json_text(forbidden_label),
        "feature_matrix_hash": frame_hash(feature_matrix, feature_matrix_cols),
        "candidate_row_hash": frame_hash(matrix, ["family_id", "grid_cell_id", "row_key", "instrument_id", "decision_date"]),
        "primary_whitelist_hash": primary_whitelist_hash,
        "missing_any_primary_n": feature_missing_any,
        "missing_any_primary_rate": safe_div(feature_missing_any, len(matrix)),
        "all_primary_features_pit_safe": all_pit_safe,
        "all_primary_features_support_pass_n": support_pass_n,
        "feature_matrix_gate": pass_fail(gate),
        "blocking_reason": "" if gate else "feature_matrix_pit_or_support_gate_failed",
    }
    return pd.DataFrame([row], columns=CSV_SCHEMAS["t0_feature_matrix_manifest"])


def build_multivariate_readout(matrix: pd.DataFrame, config: dict[str, Any], feature_n: int) -> pd.DataFrame:
    probe = config["diagnostic_probe"]
    enabled = bool(probe["multivariate_enabled"])
    row = {
        "run_id": RUN_ID,
        "family_id": config["primary_scope"]["family_id"],
        "grid_cell_id": config["primary_scope"]["grid_cell_id"],
        "split": config["primary_scope"]["split"],
        "row_scope": config["primary_scope"]["row_scope"],
        "multivariate_enabled": enabled,
        "diagnostic_method": "skipped_by_config" if not enabled else "regularized_logistic_regression_diagnostic",
        "diagnostic_status": "skipped" if not enabled else "not_implemented",
        "multivariate_diagnostic_skipped_reason": (
            "multivariate_probe_disabled_by_pre_frozen_config_to_avoid_model_training_ambiguity" if not enabled else ""
        ),
        "row_n": len(matrix),
        "feature_n": feature_n,
        "crossfit_cluster_key": probe["crossfit_cluster_key"],
        "random_seed": int(probe["random_seed"]),
        "auc": np.nan,
        "balanced_accuracy": np.nan,
        "rank_metric": np.nan,
        "feature_coefficient_stability_summary": "",
        "model_artifact_written": False,
        "threshold_rule_written": False,
        "policy_training_flag": False,
        "model_training_authorized": False,
        "diagnostic_only_flag": True,
        "blocking_reason": "",
    }
    return pd.DataFrame([row])


def direction_for_subset(frame: pd.DataFrame, feature: str) -> tuple[str, float, str]:
    left = numeric_feature(frame.loc[frame["left_bad"]], feature).dropna()
    right = numeric_feature(frame.loc[frame["right_clean"]], feature).dropna()
    support_pass = len(left) >= 50 and len(right) >= 50
    if left.empty or right.empty:
        return "flat", float("nan"), "fail"
    med_diff = float(left.median() - right.median())
    direction = direction_from_median(med_diff, support_pass)
    raw = auc_raw(left, right)
    oriented = max(raw, 1 - raw) if math.isfinite(raw) else float("nan")
    return direction, oriented, pass_fail(support_pass)


def build_b5_matrix(config: dict[str, Any], paths: dict[str, Path], panel: pd.DataFrame) -> pd.DataFrame:
    mfe = pd.read_csv(paths["mfe_mae_joint_readout"])
    b5 = mfe.loc[
        mfe["family_id"].eq("B5_recent_high_close_plus_amount_expansion")
        & mfe["grid_cell_id"].eq("B5-recent-high-close-plus-amount-expansion__25d72c708fc1")
        & mfe["split"].eq(config["primary_scope"]["split"])
        & mfe["row_scope"].eq(config["primary_scope"]["row_scope"])
        & ~mfe["diagnostic_only_flag"].fillna(False).astype(bool)
    ].copy()
    panel_small = panel.rename(columns={"instrument": "instrument_id"})
    matrix = b5.merge(panel_small, on=["instrument_id", "decision_date"], how="left")
    return add_outcome_labels(matrix, config)


def build_stability_readout(
    matrix: pd.DataFrame,
    univariate: pd.DataFrame,
    config: dict[str, Any],
    b5_matrix: pd.DataFrame,
) -> tuple[pd.DataFrame, str, dict[str, Any]]:
    top_features = (
        univariate.loc[univariate["feature_support_gate"].eq("pass")]
        .sort_values(["separability_pass", "feature_auc_oriented_left_bad_vs_right_clean"], ascending=[False, False])
        .head(5)
    )
    if top_features.empty:
        top_features = univariate.sort_values("feature_auc_oriented_left_bad_vs_right_clean", ascending=False).head(3)
    winner_counts = (
        matrix.loc[matrix["right_tail_event_50"]].groupby("instrument_id").size().sort_values(ascending=False)
    )
    top1 = set(winner_counts.head(1).index)
    top3 = set(winner_counts.head(3).index)
    rows: list[dict[str, Any]] = []
    stability_pass_components = []
    min_rate = float(config["bootstrap"]["stability_bootstrap_direction_stable_rate_min"])
    min_lomo = int(config["bootstrap"]["leave_one_month_min_effective_fold_n_for_reporting"])
    for item in top_features.itertuples(index=False):
        feature = item.feature_name
        base_dir = item.direction_for_left_bad
        stable_rate = safe_float(item.cluster_bootstrap_direction_stable_rate)
        rows.append(
            {
                "family_id": config["primary_scope"]["family_id"],
                "grid_cell_id": config["primary_scope"]["grid_cell_id"],
                "stability_check": "instrument_cluster_bootstrap",
                "feature_name": feature,
                "baseline_direction_for_left_bad": base_dir,
                "check_direction_for_left_bad": base_dir,
                "direction_stable_flag": stable_rate >= min_rate,
                "effective_fold_n": int(config["bootstrap"]["bootstrap_resample_n"]),
                "direction_stable_fold_n": int(round(stable_rate * int(config["bootstrap"]["bootstrap_resample_n"]))) if math.isfinite(stable_rate) else 0,
                "direction_stable_fold_rate": stable_rate,
                "top_removed_instrument_n": 0,
                "top_removed_winner_n": 0,
                "oriented_auc_after_check": item.feature_auc_oriented_left_bad_vs_right_clean,
                "feature_support_gate_after_check": item.feature_support_gate,
                "stability_gate_component": pass_fail(stable_rate >= min_rate and item.feature_support_gate == "pass"),
                "lomo_stability_status": "not_lomo_check",
                "diagnostic_only_flag": True,
                "blocking_reason": "" if stable_rate >= min_rate else "cluster_bootstrap_direction_stability_failed",
            }
        )
        for label, removal in [("top1_winner_instrument_removal", top1), ("top3_winner_instrument_removal", top3)]:
            subset = matrix.loc[~matrix["instrument_id"].isin(removal)].copy()
            check_dir, oriented, support_gate = direction_for_subset(subset, feature)
            removed_winner_n = int(matrix.loc[matrix["instrument_id"].isin(removal), "right_tail_event_50"].sum())
            component = check_dir == base_dir and support_gate == "pass"
            rows.append(
                {
                    "family_id": config["primary_scope"]["family_id"],
                    "grid_cell_id": config["primary_scope"]["grid_cell_id"],
                    "stability_check": label,
                    "feature_name": feature,
                    "baseline_direction_for_left_bad": base_dir,
                    "check_direction_for_left_bad": check_dir,
                    "direction_stable_flag": component,
                    "effective_fold_n": 1,
                    "direction_stable_fold_n": int(component),
                    "direction_stable_fold_rate": float(component),
                    "top_removed_instrument_n": len(removal),
                    "top_removed_winner_n": removed_winner_n,
                    "oriented_auc_after_check": oriented,
                    "feature_support_gate_after_check": support_gate,
                    "stability_gate_component": pass_fail(component),
                    "lomo_stability_status": "not_lomo_check",
                    "diagnostic_only_flag": True,
                    "blocking_reason": "" if component else f"{label}_direction_or_support_failed",
                }
            )
        stable_fold_n = 0
        effective_fold_n = 0
        for month, group in matrix.groupby("decision_month"):
            left_n = int(group.loc[group["left_bad"], feature].notna().sum())
            right_n = int(group.loc[group["right_clean"], feature].notna().sum())
            if left_n >= 20 and right_n >= 20:
                effective_fold_n += 1
                check_dir, _, _ = direction_for_subset(group, feature)
                stable_fold_n += int(check_dir == base_dir)
        fold_rate = safe_div(stable_fold_n, effective_fold_n)
        lomo_status = "pass" if effective_fold_n >= min_lomo else "diagnostic_only_insufficient_effective_month_support"
        rows.append(
            {
                "family_id": config["primary_scope"]["family_id"],
                "grid_cell_id": config["primary_scope"]["grid_cell_id"],
                "stability_check": "leave_one_month_out_held_out_month_diagnostic",
                "feature_name": feature,
                "baseline_direction_for_left_bad": base_dir,
                "check_direction_for_left_bad": "mixed" if stable_fold_n not in {0, effective_fold_n} else base_dir,
                "direction_stable_flag": fold_rate >= min_rate if math.isfinite(fold_rate) else False,
                "effective_fold_n": effective_fold_n,
                "direction_stable_fold_n": stable_fold_n,
                "direction_stable_fold_rate": fold_rate,
                "top_removed_instrument_n": 0,
                "top_removed_winner_n": 0,
                "oriented_auc_after_check": np.nan,
                "feature_support_gate_after_check": "diagnostic_only",
                "stability_gate_component": "diagnostic_only",
                "lomo_stability_status": lomo_status,
                "diagnostic_only_flag": True,
                "blocking_reason": "" if lomo_status == "pass" else lomo_status,
            }
        )
        component_rows = [row for row in rows if row["feature_name"] == feature and row["stability_check"] in {
            "instrument_cluster_bootstrap",
            "top1_winner_instrument_removal",
            "top3_winner_instrument_removal",
        }]
        stability_pass_components.append(all(row["stability_gate_component"] == "pass" for row in component_rows))
    b5_right_clean = int(b5_matrix["right_clean"].sum()) if not b5_matrix.empty else 0
    b5_left_bad = int(b5_matrix["left_bad"].sum()) if not b5_matrix.empty else 0
    b5_support = len(b5_matrix) >= 300 and b5_right_clean >= 50 and b5_left_bad >= 50
    b5_meta = {
        "B5_negative_control_used": bool(b5_support),
        "B5_negative_control_support_gate": pass_fail(b5_support),
        "B5_negative_control_skipped_reason": "" if b5_support else "diagnostic_only_skipped_insufficient_support",
    }
    if top_features.empty:
        feature = ""
        base_dir = ""
    else:
        feature = str(top_features.iloc[0]["feature_name"])
        base_dir = str(top_features.iloc[0]["direction_for_left_bad"])
    if b5_support and feature:
        b5_dir, b5_auc, b5_feature_gate = direction_for_subset(b5_matrix, feature)
        rows.append(
            {
                "family_id": "B5_recent_high_close_plus_amount_expansion",
                "grid_cell_id": "B5-recent-high-close-plus-amount-expansion__25d72c708fc1",
                "stability_check": "B5_negative_control_contrast",
                "feature_name": feature,
                "baseline_direction_for_left_bad": base_dir,
                "check_direction_for_left_bad": b5_dir,
                "direction_stable_flag": b5_dir == base_dir,
                "effective_fold_n": 1,
                "direction_stable_fold_n": int(b5_dir == base_dir),
                "direction_stable_fold_rate": float(b5_dir == base_dir),
                "top_removed_instrument_n": 0,
                "top_removed_winner_n": 0,
                "oriented_auc_after_check": b5_auc,
                "feature_support_gate_after_check": b5_feature_gate,
                "stability_gate_component": "diagnostic_only",
                "lomo_stability_status": "not_lomo_check",
                "diagnostic_only_flag": True,
                "blocking_reason": "",
            }
        )
    else:
        rows.append(
            {
                "family_id": "B5_recent_high_close_plus_amount_expansion",
                "grid_cell_id": "B5-recent-high-close-plus-amount-expansion__25d72c708fc1",
                "stability_check": "B5_negative_control_skipped",
                "feature_name": feature,
                "baseline_direction_for_left_bad": base_dir,
                "check_direction_for_left_bad": "",
                "direction_stable_flag": False,
                "effective_fold_n": 0,
                "direction_stable_fold_n": 0,
                "direction_stable_fold_rate": np.nan,
                "top_removed_instrument_n": 0,
                "top_removed_winner_n": 0,
                "oriented_auc_after_check": np.nan,
                "feature_support_gate_after_check": "fail",
                "stability_gate_component": "diagnostic_only",
                "lomo_stability_status": "not_lomo_check",
                "diagnostic_only_flag": True,
                "blocking_reason": "diagnostic_only_skipped_insufficient_support",
            }
        )
    return pd.DataFrame(rows), pass_fail(any(stability_pass_components)), b5_meta


def build_search_accounting(
    matrix: pd.DataFrame,
    univariate: pd.DataFrame,
    b5_meta: dict[str, Any],
    config: dict[str, Any],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "N_family_primary": 1,
                "primary_family": config["primary_scope"]["family_id"],
                "primary_grid_cell_id": config["primary_scope"]["grid_cell_id"],
                "primary_row_scope": config["primary_scope"]["row_scope"],
                "N_candidate_rows": len(matrix),
                "N_instruments": int(matrix["instrument_id"].nunique()),
                "N_t0_features_tested": len(univariate),
                "N_primary_whitelist_features_frozen": len(PRIMARY_FEATURE_WHITELIST),
                "N_primary_features_pit_safe_used": len(PRIMARY_FEATURE_WHITELIST),
                "N_primary_features_support_pass": int(univariate["feature_support_gate"].eq("pass").sum()),
                "N_primary_features_support_fail": int(univariate["feature_support_gate"].eq("fail").sum()),
                "N_exploratory_features_reported": 0,
                "feature_family_correction_method": "Benjamini-Hochberg FDR plus Bonferroni-Sidak sensitivity",
                "secondary_comparisons_count": 4,
                "B5_negative_control_used": b5_meta["B5_negative_control_used"],
                "B5_negative_control_support_gate": b5_meta["B5_negative_control_support_gate"],
                "validation_outcome_read": False,
                "thresholds_frozen_before_19B1": True,
                "left_tail_thresholds": "[-0.10, -0.20]",
                "right_tail_thresholds": "[+0.50]",
            }
        ]
    )


def decide_state(gates: dict[str, str]) -> tuple[str, str]:
    if gates["config_contract_gate"] != "pass":
        return "19B1_config_contract_blocked", "config_contract_failed"
    if gates["input_artifact_gate"] != "pass":
        return "19B1_input_artifact_blocked", "input_artifact_missing_or_19b_hash_mismatch"
    if gates["output_contract_gate"] != "pass":
        return "19B1_output_contract_blocked", "output_contract_failed"
    if gates["upstream_19a_contract_gate"] != "pass" or gates["upstream_19b0_contract_gate"] != "pass":
        return "19B1_upstream_contract_blocked", "upstream_19a_or_19b0_contract_failed"
    if gates["upstream_19b_contract_gate"] != "pass" or gates["primary_row_join_gate"] != "pass":
        return "19B1_upstream_19b_contract_blocked", "primary_candidate_row_scope_or_join_contract_failed"
    if gates["sample_support_gate"] != "pass":
        return "19B1_sample_support_blocked", "primary_b2_sample_support_insufficient"
    if gates["t0_feature_pit_gate"] != "pass":
        return "19B1_t0_feature_pit_contract_blocked", "primary_t0_feature_whitelist_or_pit_contract_failed"
    if (
        gates["outcome_overlap_gate"] != "pass"
        or gates["primary_feature_separability_gate"] != "pass"
        or gates["stability_gate"] != "pass"
    ):
        return "19B1_t0_left_right_tail_not_separable_diagnostic", "diagnostic_positive_gate_not_met"
    return "19B1_t0_left_right_tail_separable_diagnostic", ""


def build_decision(
    config_path: Path,
    input_hashes: dict[str, str],
    primary_whitelist_hash: str,
    gates: dict[str, str],
    state: str,
    reason: str,
    matrix: pd.DataFrame,
    outcome: pd.DataFrame,
    univariate: pd.DataFrame,
    b5_meta: dict[str, Any],
    config: dict[str, Any],
) -> pd.DataFrame:
    outcome_row = outcome.iloc[0].to_dict() if not outcome.empty else {}
    passing = univariate.loc[univariate["separability_pass"].fillna(False).astype(bool)] if not univariate.empty else pd.DataFrame()
    row = {
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "requirement_file_hash": b0.artifact_hash(REQUIREMENT_PATH),
        "config_file_hash": b0.artifact_hash(config_path),
        "primary_whitelist_hash": primary_whitelist_hash,
        "input_artifact_hash_manifest": stable_hash_payload(input_hashes),
        **gates,
        "decision_state": state,
        "blocking_reason": reason,
        "family_id": config["primary_scope"]["family_id"],
        "grid_cell_id": config["primary_scope"]["grid_cell_id"],
        "row_scope": config["primary_scope"]["row_scope"],
        "split": config["primary_scope"]["split"],
        "candidate_n": int(outcome_row.get("candidate_n", len(matrix))),
        "instrument_n": int(outcome_row.get("instrument_n", matrix["instrument_id"].nunique() if "instrument_id" in matrix else 0)),
        "right_clean_n": int(outcome_row.get("right_clean_n", 0)),
        "left_bad_n": int(outcome_row.get("left_bad_n", 0)),
        "both_n": int(outcome_row.get("both_n", 0)),
        "neither_n": int(outcome_row.get("neither_n", 0)),
        "N_primary_whitelist_features_frozen": len(PRIMARY_FEATURE_WHITELIST),
        "N_primary_features_pit_safe_used": len(PRIMARY_FEATURE_WHITELIST),
        "N_primary_features_support_pass": int(univariate["feature_support_gate"].eq("pass").sum()) if not univariate.empty else 0,
        "N_primary_features_support_fail": int(univariate["feature_support_gate"].eq("fail").sum()) if not univariate.empty else 0,
        "N_primary_features_separability_pass": len(passing),
        "N_distinct_passing_feature_signal_groups": int(passing["feature_signal_group"].nunique()) if not passing.empty else 0,
        **b5_meta,
        "validation_outcome_read": False,
        "max_ep19_terminal_state": "19_entry_universe_enrichment_only_diagnostic",
        "next_allowed_requirement": "none",
        "next_research_suggestion": "new_pre_registered_b2_left_tail_suppressor_hypothesis_requirement",
        "model_training_authorized": False,
        "entry_policy_authorized": False,
        "exit_policy_authorized": False,
        "holding_policy_authorized": False,
        "portfolio_backtest_authorized": False,
        "model_deployment_authorized": False,
        "production_signal_authorized": False,
        "live_trading_authorized": False,
        "19C_replay_authorized": False,
        "EP20_policy_preflight_authorized": False,
    }
    return pd.DataFrame([row], columns=CSV_SCHEMAS["entry_universe_19b1_decision"])


def build_report(decision: pd.DataFrame, outcome: pd.DataFrame, univariate: pd.DataFrame, stability: pd.DataFrame) -> str:
    row = decision.iloc[0]
    top = univariate.sort_values("feature_auc_oriented_left_bad_vs_right_clean", ascending=False).head(5)
    lines = [
        "# 19B1 T0 左尾/右尾可区分性诊断读出",
        "",
        "19B1 是 diagnostic-only。",
        "validation outcome read = false。",
        "19C replay authorized = false。",
        "EP20 policy preflight authorized = false。",
        "entry/exit/holding/portfolio/model/production/live trading authorization = false。",
        "T0 separability 不等于 alpha support。",
        "任何后续 left-tail suppressor 必须作为新的 pre-registered requirement，不能从 19B1 直接生成交易规则。",
        "",
        f"- decision_state: `{row['decision_state']}`",
        f"- blocking_reason: `{row['blocking_reason']}`",
        f"- candidate_n: `{row['candidate_n']}`",
        f"- right_clean_n: `{row['right_clean_n']}`",
        f"- left_bad_n: `{row['left_bad_n']}`",
        f"- primary_feature_separability_gate: `{row['primary_feature_separability_gate']}`",
        f"- stability_gate: `{row['stability_gate']}`",
        "",
        "## Outcome Overlap",
    ]
    if not outcome.empty:
        o = outcome.iloc[0]
        lines.extend(
            [
                f"- P(left_tail_10 | right_tail_50): `{o['p_left_tail_10_given_right_tail_50']:.6f}`",
                f"- P(left_tail_10 | not right_tail_50): `{o['p_left_tail_10_given_not_right_tail_50']:.6f}`",
                f"- bootstrap diff CI: `[{o['cluster_bootstrap_diff_ci_low']:.6f}, {o['cluster_bootstrap_diff_ci_high']:.6f}]`",
            ]
        )
    lines.extend(["", "## Top T0 Features", "", "| feature | group | direction | oriented_auc | bh_fdr | pass |", "|---|---:|---:|---:|---:|---:|"])
    for item in top.itertuples(index=False):
        lines.append(
            f"| {item.feature_name} | {item.feature_signal_group} | {item.direction_for_left_bad} | "
            f"{item.feature_auc_oriented_left_bad_vs_right_clean:.6f} | {item.bh_fdr_adjusted_p:.6f} | {bool(item.separability_pass)} |"
        )
    lines.extend(
        [
            "",
        "## Stability",
            f"- stability rows: `{len(stability)}`",
            "",
            "## Required Figures",
            "- `figures/b2_outcome_left_right_overlap.png`",
            "- `figures/b2_t0_top_feature_distributions.png`",
            "- `figures/b2_t0_feature_auc_forest.png`",
            "- `figures/b2_t0_separability_stability.png`",
        ]
    )
    return "\n".join(lines) + "\n"


def build_handoff(decision: pd.DataFrame) -> str:
    row = decision.iloc[0]
    return "\n".join(
        [
            "# 19B1 Handoff Contract",
            "",
            f"decision_state = {row['decision_state']}",
            "next_allowed_requirement = none",
            "validation_outcome_read = false",
            "19C_replay_authorized = false",
            "EP20_policy_preflight_authorized = false",
            "model_training_authorized = false",
            "entry_policy_authorized = false",
            "exit_policy_authorized = false",
            "holding_policy_authorized = false",
            "portfolio_backtest_authorized = false",
            "model_deployment_authorized = false",
            "production_signal_authorized = false",
            "live_trading_authorized = false",
            "max_ep19_terminal_state = 19_entry_universe_enrichment_only_diagnostic",
            "non_executable_research_suggestion = new_pre_registered_b2_left_tail_suppressor_hypothesis_requirement",
            "",
        ]
    )


def save_figure(fig: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_figures(outputs: dict[str, Path], matrix: pd.DataFrame, outcome: pd.DataFrame, univariate: pd.DataFrame, stability: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    counts = outcome.iloc[0][["right_clean_n", "left_bad_n", "both_n", "neither_n"]].astype(float)
    ax.bar(counts.index, counts.values, color=["#2f6f9f", "#b24a3b", "#8067a9", "#8a8f3a"])
    ax.set_ylabel("Rows")
    ax.set_title("B2 outcome groups")
    ax.tick_params(axis="x", rotation=20)
    save_figure(fig, outputs["b2_outcome_left_right_overlap_figure"])

    top_features = univariate.sort_values("feature_auc_oriented_left_bad_vs_right_clean", ascending=False).head(3)["feature_name"].tolist()
    fig, axes = plt.subplots(len(top_features), 1, figsize=(7, 3 * max(len(top_features), 1)))
    if len(top_features) == 1:
        axes = [axes]
    for ax, feature in zip(axes, top_features):
        left = numeric_feature(matrix.loc[matrix["left_bad"]], feature).dropna()
        right = numeric_feature(matrix.loc[matrix["right_clean"]], feature).dropna()
        ax.hist(right, bins=30, alpha=0.55, label="right_clean", color="#2f6f9f")
        ax.hist(left, bins=30, alpha=0.55, label="left_bad", color="#b24a3b")
        ax.set_title(feature)
        ax.legend()
    save_figure(fig, outputs["b2_t0_top_feature_distributions_figure"])

    forest = univariate.sort_values("feature_auc_oriented_left_bad_vs_right_clean")
    fig, ax = plt.subplots(figsize=(8, max(5, 0.32 * len(forest))))
    y = np.arange(len(forest))
    x = forest["feature_auc_oriented_left_bad_vs_right_clean"].to_numpy(dtype=float)
    low = forest["cluster_bootstrap_oriented_auc_ci_low"].to_numpy(dtype=float)
    high = forest["cluster_bootstrap_oriented_auc_ci_high"].to_numpy(dtype=float)
    low = np.where(np.isfinite(low), np.minimum(low, x), x)
    high = np.where(np.isfinite(high), np.maximum(high, x), x)
    ax.errorbar(
        x,
        y,
        xerr=np.vstack([np.maximum(x - low, 0), np.maximum(high - x, 0)]),
        fmt="o",
        color="#315f72",
        ecolor="#8899a6",
        capsize=2,
    )
    ax.axvline(0.5, color="#777777", linestyle="--", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(forest["feature_name"])
    ax.set_xlabel("Oriented AUC")
    ax.set_title("T0 feature separability")
    save_figure(fig, outputs["b2_t0_feature_auc_forest_figure"])

    stable = stability.loc[stability["stability_check"].eq("instrument_cluster_bootstrap")].copy()
    fig, ax = plt.subplots(figsize=(7, 4))
    if not stable.empty:
        ax.bar(stable["feature_name"], stable["direction_stable_fold_rate"].astype(float), color="#4d7d5a")
        ax.axhline(0.70, color="#8f3d38", linestyle="--", linewidth=1)
        ax.tick_params(axis="x", rotation=35)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Direction stable rate")
    ax.set_title("Bootstrap direction stability")
    save_figure(fig, outputs["b2_t0_separability_stability_figure"])


def output_contract_pass(outputs: dict[str, Path], report: str, handoff: str) -> bool:
    required = list(REQUIRED_OUTPUT_KEYS)
    if not all(outputs[key].exists() and outputs[key].stat().st_size > 0 for key in required):
        return False
    for key, cols in CSV_SCHEMAS.items():
        output_key = key
        if output_key not in outputs:
            continue
        actual = set(pd.read_csv(outputs[output_key], nrows=0).columns)
        if not set(cols).issubset(actual):
            return False
    csv_keys = [key for key, path in outputs.items() if path.suffix == ".csv"]
    for key in csv_keys:
        if pd.read_csv(outputs[key]).empty:
            return False
    required_phrases = [
        "19B1 是 diagnostic-only",
        "validation outcome read = false",
        "19C replay authorized = false",
        "EP20 policy preflight authorized = false",
        "entry/exit/holding/portfolio/model/production/live trading authorization = false",
        "T0 separability 不等于 alpha support",
        "任何后续 left-tail suppressor 必须作为新的 pre-registered requirement",
    ]
    if not all(phrase in report for phrase in required_phrases) or "next_allowed_requirement = none" not in handoff:
        return False
    try:
        manifest = read_json(outputs["manifest"])
        output_hashes = read_json(outputs["output_hashes"])
    except Exception:  # noqa: BLE001
        return False
    if set(manifest.get("required_outputs", {})) != set(REQUIRED_OUTPUT_KEYS):
        return False
    if manifest.get("output_hashes") != build_output_hashes(outputs, include_manifest=False):
        return False
    if output_hashes != build_output_hashes(outputs, include_manifest=True):
        return False
    return "manifest" not in manifest.get("output_hashes", {}) and "output_hashes" not in output_hashes


def build_output_hashes(outputs: dict[str, Path], include_manifest: bool = True) -> dict[str, str]:
    excluded = {"output_hashes"} if include_manifest else {"manifest", "output_hashes"}
    return {
        key: b0.artifact_hash(path)
        for key, path in sorted(outputs.items())
        if key not in excluded and path.exists() and path.is_file()
    }


def write_manifest_and_hashes(
    outputs: dict[str, Path],
    decision: pd.DataFrame,
    input_hashes: dict[str, str],
    primary_whitelist_hash: str,
    gates: dict[str, str],
) -> None:
    manifest_hashes = build_output_hashes(outputs, include_manifest=False)
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at": decision.iloc[0]["created_at"],
        "python_version": platform.python_version(),
        "requirement_file_hash": decision.iloc[0]["requirement_file_hash"],
        "config_file_hash": decision.iloc[0]["config_file_hash"],
        "primary_whitelist_hash": primary_whitelist_hash,
        "input_artifact_hashes": input_hashes,
        "decision_state": decision.iloc[0]["decision_state"],
        "next_allowed_requirement": decision.iloc[0]["next_allowed_requirement"],
        "critical_gates": {gate: decision.iloc[0][gate] for gate in gates},
        "required_outputs": {key: rel(path) for key, path in outputs.items()},
        "output_hashes": manifest_hashes,
    }
    b0.write_json(outputs["manifest"], manifest)
    output_hashes = build_output_hashes(outputs, include_manifest=True)
    b0.write_json(outputs["output_hashes"], output_hashes)


def write_frames(outputs: dict[str, Path], frames: dict[str, pd.DataFrame]) -> None:
    for key, frame in frames.items():
        b0.write_df(outputs[key], frame)


def run(config_path: str | Path = CONFIG_PATH) -> dict[str, Path]:
    config_path = Path(config_path)
    config = load_config(config_path)
    paths = resolve_input_paths(config)
    output_root = resolve_output_root(config)
    outputs = output_paths(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    primary_whitelist_hash = stable_hash_payload(PRIMARY_FEATURE_WHITELIST)
    config_gate, config_reason = validate_config_contract(config, paths, output_root)
    input_audit, input_gate, input_hashes = build_input_artifact_audit(paths)
    upstream_audit, upstream_gates = build_upstream_contract_audit(paths, input_audit, config)

    panel = load_feature_panel(config, paths)
    matrix, join_audit = build_primary_matrix(config, paths, panel)
    outcome, sample_gate = contingency_metrics(matrix, config)
    univariate = build_univariate_readout(matrix, config)
    source_audit = build_feature_source_audit(matrix, univariate, paths)
    matrix_manifest = build_feature_matrix_manifest(matrix, source_audit, univariate, config, primary_whitelist_hash)
    multivariate = build_multivariate_readout(matrix, config, int(univariate["feature_support_gate"].eq("pass").sum()))
    b5_matrix = build_b5_matrix(config, paths, panel)
    stability, stability_gate, b5_meta = build_stability_readout(matrix, univariate, config, b5_matrix)
    search_accounting = build_search_accounting(matrix, univariate, b5_meta, config)

    distinct_groups = univariate.loc[univariate["separability_pass"], "feature_signal_group"].nunique()
    primary_feature_gate = pass_fail(int(univariate["separability_pass"].sum()) >= 2 and distinct_groups >= 2)
    t0_feature_gate = pass_fail(
        matrix_manifest["feature_matrix_gate"].eq("pass").all()
        and source_audit["pit_safe_flag"].fillna(False).astype(bool).all()
        and source_audit["primary_whitelist_flag"].fillna(False).astype(bool).all()
        and not source_audit["exploratory_only_flag"].fillna(True).astype(bool).any()
    )
    gates = {
        "config_contract_gate": config_gate,
        "input_artifact_gate": input_gate,
        **upstream_gates,
        "sample_support_gate": sample_gate,
        "primary_row_join_gate": join_audit.iloc[0]["primary_row_join_gate"],
        "outcome_overlap_gate": outcome.iloc[0]["outcome_overlap_gate"],
        "t0_feature_pit_gate": t0_feature_gate,
        "primary_feature_separability_gate": primary_feature_gate,
        "stability_gate": stability_gate,
        "policy_authorization_gate": "pass",
        "output_contract_gate": "pass",
    }
    state, reason = decide_state(gates)
    if config_reason and config_gate != "pass":
        reason = config_reason

    decision = build_decision(config_path, input_hashes, primary_whitelist_hash, gates, state, reason, matrix, outcome, univariate, b5_meta, config)
    frames = {
        "input_artifact_audit": input_audit,
        "upstream_contract_audit": upstream_audit,
        "t0_feature_join_audit": join_audit,
        "t0_feature_source_audit": source_audit,
        "t0_feature_matrix_manifest": matrix_manifest,
        "outcome_left_right_overlap_readout": outcome,
        "t0_univariate_feature_separability_readout": univariate,
        "t0_multivariate_diagnostic_separability_readout": multivariate,
        "t0_separability_stability_readout": stability,
        "search_accounting_audit": search_accounting,
        "entry_universe_19b1_decision": decision,
    }
    write_frames(outputs, frames)
    write_figures(outputs, matrix, outcome, univariate, stability)
    report = build_report(decision, outcome, univariate, stability)
    handoff = build_handoff(decision)
    b0.write_text(outputs["report"], report)
    b0.write_text(outputs["handoff_contract"], handoff)
    write_manifest_and_hashes(outputs, decision, input_hashes, primary_whitelist_hash, gates)

    gates["output_contract_gate"] = pass_fail(output_contract_pass(outputs, report, handoff))
    state, reason = decide_state(gates)
    if config_reason and config_gate != "pass":
        reason = config_reason
    decision = build_decision(config_path, input_hashes, primary_whitelist_hash, gates, state, reason, matrix, outcome, univariate, b5_meta, config)
    b0.write_df(outputs["entry_universe_19b1_decision"], decision)
    report = build_report(decision, outcome, univariate, stability)
    handoff = build_handoff(decision)
    b0.write_text(outputs["report"], report)
    b0.write_text(outputs["handoff_contract"], handoff)
    write_manifest_and_hashes(outputs, decision, input_hashes, primary_whitelist_hash, gates)
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(args.config)


if __name__ == "__main__":
    main()
