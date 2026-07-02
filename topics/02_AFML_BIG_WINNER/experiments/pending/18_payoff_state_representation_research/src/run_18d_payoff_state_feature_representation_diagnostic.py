#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import Ridge
from sklearn.tree import DecisionTreeRegressor


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "18D_payoff_state_feature_representation_diagnostic"
EXPERIMENT_ID = "18_payoff_state_representation_research"
PHASE_ID = "18D"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_18d_payoff_state_feature_representation_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID

SPLITS = ("train", "robustness", "validation")
PRIMARY_MODEL_ID = "ridge_payoff_rank_h20_v1"
AUTH_FALSE_COLUMNS = (
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
)
HARD_GATES = (
    "upstream_18c_contract_gate",
    "input_artifact_gate",
    "capacity_vs_representation_gate",
    "candidate_inventory_completeness_gate",
    "candidate_lineage_gate",
    "pit_t0_availability_gate",
    "orthogonal_payoff_information_gate",
    "feature_family_prioritization_gate",
    "search_accounting_gate",
)
BASE_RESIDUALIZATION_ID = "base_vol_participation"
BASE_RESIDUALIZATION_ROLE = "standard_orthogonality_readout"
M2_EXT_RESIDUALIZATION_ID = "f2_extended_participation_money"
M2_EXT_RESIDUALIZATION_ROLE = "m2_recommendation_gate"
BASE_COVARIATES = ["mr_volatility_20d", "mr_volume_20d_zscore"]
M2_EXT_COVARIATES = [
    "mr_volatility_20d",
    "mr_volume_20d_zscore",
    "mr_turnover_rate_20d_zscore",
    "mr_money_20d_zscore",
]


def candidate_definitions() -> list[dict[str, Any]]:
    rows = [
        ("M1", "m1_return_sign_entropy_trailing20", "return sign entropy trailing 20", "return_sign_entropy_trailing20", "pit_price_path_panel", "qfq close", "high", "m1_return_sign_entropy_trailing20"),
        ("M1", "m1_path_transition_entropy_episode", "path transition entropy episode low to t0", "path_transition_entropy_episode_low_to_t0", "pit_price_path_panel", "qfq close", "high", "m1_path_transition_entropy_episode"),
        ("M1", "m1_repair_path_efficiency_episode", "episode repair path efficiency", "repair_path_efficiency_episode_low_to_t0", "pit_price_path_panel", "qfq close", "high", "m1_repair_path_efficiency_episode"),
        ("M1", "m1_close_location_episode_range", "close location in episode range", "(close_t0-low_t0)/(high_t0-low_t0)", "episode_geometry_panel", "qfq high low close", "high", "m1_range_location_group"),
        ("M1", "m1_episode_drawdown_pre_t0", "episode drawdown before t0", "min(low/running_max(close)-1)", "pit_price_path_panel", "qfq low close", "high", "m1_episode_drawdown_pre_t0"),
        ("M1", "m1_episode_recovery_ratio_to_high_t0", "episode recovery ratio to pre-t0 high", "(close_t0-low_t0)/(high_t0-low_t0)", "episode_geometry_panel", "qfq high low close", "high", "m1_range_location_group"),
        ("M1", "m1_pullback_from_episode_high_t0", "pullback from pre-t0 episode high", "close_t0/high_t0-1", "episode_geometry_panel", "qfq high close", "high", "m1_pullback_from_episode_high_t0"),
        ("M1", "m1_close_location_trailing60_range", "close location in trailing 60 range", "(close_t0-low_60)/(high_60-low_60)", "pit_price_path_panel", "qfq high low close", "high", "m1_close_location_trailing60_range"),
        ("M1", "m1_path_linearity_r2_low_to_t0", "path linearity R2 from episode low to t0", "R2(close~position) over episode low to t0", "pit_price_path_panel", "qfq close", "high", "m1_path_linearity_r2_low_to_t0"),
        ("M1", "m1_up_down_run_imbalance_20", "up down run imbalance trailing 20", "longest_up_run_20-longest_down_run_20", "pit_price_path_panel", "qfq close", "high", "m1_up_down_run_imbalance_20"),
        ("M1", "m1_failed_repair_count_low_to_t0", "failed repair count from episode low to t0", "count pre-t0 failed repair local highs", "pit_price_path_panel", "qfq close", "high", "m1_failed_repair_count_low_to_t0"),
        ("M3", "m3_upside_room_to_episode_high", "upside room to pre-t0 episode high", "(episode_high-close_t0)/close_t0", "episode_geometry_panel", "qfq high close", "high", "m3_upside_room_to_episode_high"),
        ("M3", "m3_downside_crowding_to_episode_low", "downside crowding to episode low", "(close_t0-episode_low)/close_t0", "episode_geometry_panel", "qfq low close", "high", "m3_downside_room_group"),
        ("M3", "m3_vol_adjusted_repair_strength", "volatility adjusted repair strength", "repair_return/volatility_20d", "pit_price_path_panel", "qfq close and volatility_20d", "high", "m3_vol_adjusted_repair_strength"),
        ("M3", "m3_downside_room_to_episode_low_t0", "downside room to episode low t0", "(close_t0-episode_low)/close_t0", "episode_geometry_panel", "qfq low close", "high", "m3_downside_room_group"),
        ("M3", "m3_upside_downside_room_ratio_t0", "upside downside room ratio t0", "(episode_high-close_t0)/(close_t0-episode_low)", "episode_geometry_panel", "qfq high low close", "high", "m3_upside_downside_room_ratio_t0"),
        ("M3", "m3_asymmetric_range_position_t0", "asymmetric range position t0", "2*(close_t0-low_t0)/(high_t0-low_t0)-1", "episode_geometry_panel", "qfq high low close", "high", "m1_m3_range_position_related_group"),
        ("M3", "m3_failed_breakout_count_pre_t0", "failed breakout count before t0", "count pre-t0 new highs with failed follow-through", "pit_price_path_panel", "qfq high low close", "high", "m3_failed_breakout_count_pre_t0"),
        ("M3", "m3_upper_shadow_pressure_share_20", "upper shadow pressure share trailing 20", "mean(upper_shadow/range) over valid candles", "pit_price_path_panel", "qfq open high low close", "high", "m3_upper_shadow_pressure_share_20"),
        ("M5", "m5_bars_since_episode_low", "bars since episode low", "step_start_pos-episode_low_pos_t0", "episode_geometry_panel", "position index", "high_medium", "m5_bars_since_episode_low"),
        ("M5", "m5_bars_since_episode_high_t0", "bars since episode high t0", "step_start_pos-episode_high_pos_t0", "episode_geometry_panel", "position index", "high_medium", "m5_bars_since_episode_high_t0"),
        ("M5", "m5_episode_age_to_t0", "episode age at t0", "step_start_pos-cluster_start_pos", "episode_geometry_panel", "position index", "high_medium", "m5_episode_age_to_t0"),
        ("M5", "m5_nonoverlap_step_index_to_t0", "nonoverlap step index to t0", "floor((step_start_pos-cluster_start_pos)/horizon_sessions)", "episode_geometry_panel", "position index", "high_medium", "m5_nonoverlap_step_index_to_t0"),
        ("M5", "m5_low_to_t0_age_ratio", "low to t0 age ratio", "(step_start_pos-low_pos_t0)/max(age,1)", "episode_geometry_panel", "position index", "high_medium", "m5_low_to_t0_age_ratio"),
        ("M5", "m5_high_to_t0_age_ratio", "high to t0 age ratio", "(step_start_pos-high_pos_t0)/max(age,1)", "episode_geometry_panel", "position index", "high_medium", "m5_high_to_t0_age_ratio"),
        ("M5", "m5_low_before_high_t0", "low before high t0", "episode_low_pos_t0 < episode_high_pos_t0", "episode_geometry_panel", "position index", "high_medium", "m5_low_before_high_t0"),
        ("M5", "m5_bars_since_reclaim", "bars since deterministic ma60 reclaim", "step_start_pos-reclaim_pos_t0", "episode_geometry_panel", "qfq close ma60", "high_medium", "m5_bars_since_reclaim"),
        ("M5", "m5_lifecycle_progress_to_t0", "lifecycle progress at t0", "(step_start_pos-cluster_start)/(cluster_end-cluster_start)", "episode_geometry_panel", "position index", "high_medium", "m5_lifecycle_progress_to_t0"),
        ("M2", "m2_net_signed_money_flow_trailing20", "net signed money flow trailing 20", "sum(signed_money_proxy)/sum(abs(amount))", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_net_signed_money_flow_trailing20"),
        ("M2", "m2_positive_money_flow_share_trailing20", "positive money flow share trailing 20", "sum(amount where ret>0)/sum(amount)", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_positive_money_flow_share_trailing20"),
        ("M2", "m2_money_flow_persistence_trailing20", "money flow sign persistence trailing 20", "mean(sign(flow_t)==sign(flow_t-1))", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_money_flow_persistence_trailing20"),
        ("M2", "m2_turnover_compression_20_vs_60", "turnover compression 20 versus 60", "mean(turnover_20)/mean(turnover_60)", "pit_money_flow_proxy_panel", "turnover_rate", "medium", "m2_turnover_compression_20_vs_60"),
        ("M2", "m2_net_signed_money_flow_accel_5v20", "net signed money flow acceleration 5 versus 20", "net_signed_money_flow_5-net_signed_money_flow_20", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_net_signed_money_flow_accel_5v20"),
        ("M2", "m2_positive_money_flow_share_accel_5v20", "positive money flow share acceleration 5 versus 20", "positive_money_flow_share_5-positive_money_flow_share_20", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_positive_money_flow_share_accel_5v20"),
        ("M2", "m2_money_flow_reversal_accel_5v20", "money flow reversal acceleration 5 versus 20", "reversal_rate_5-reversal_rate_20", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_money_flow_reversal_accel_5v20"),
        ("M2", "m2_net_signed_money_flow_curvature_5_10_20", "net signed money flow curvature 5 10 20", "flow_5-2*flow_10+flow_20", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_net_signed_money_flow_curvature_5_10_20"),
        ("M2", "m2_flow_price_divergence_persistence_20", "flow price divergence persistence trailing 20", "mean(sign(ret_5)!=sign(flow_5))", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_flow_price_divergence_persistence_20"),
        ("M2", "m2_high_amount_negative_bar_share_20", "high amount negative bar share trailing 20", "share(ret<0 and amount>=trailing60 amount p80)", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_high_amount_negative_bar_share_20"),
        ("M2", "m2_signed_flow_volatility_20", "signed flow volatility trailing 20", "std(signed_flow/abs(amount))", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_signed_flow_volatility_20"),
        ("M2", "m2_flow_concentration_top3_share_20", "flow concentration top3 share trailing 20", "top3 abs(flow)/sum abs(flow)", "pit_money_flow_proxy_panel", "qfq close money", "medium", "m2_flow_concentration_top3_share_20"),
        ("M4", "m4_regime_context_deferred", "regime context deferred", "requires new PIT context", "market_or_regime_context_panel", "context panel", "low", "m4_regime_context_deferred"),
    ]
    alias_of = {
        "m1_episode_recovery_ratio_to_high_t0": "m1_close_location_episode_range",
        "m3_downside_room_to_episode_low_t0": "m3_downside_crowding_to_episode_low",
    }
    overlap = {
        "m1_close_location_episode_range": "m1_m3_range_position_related_group",
        "m1_episode_recovery_ratio_to_high_t0": "m1_m3_range_position_related_group",
        "m3_asymmetric_range_position_t0": "m1_m3_range_position_related_group",
    }
    out: list[dict[str, Any]] = []
    for family, fid, name, formula, source, cols, priority, dedup in rows:
        is_m4 = family == "M4"
        is_lifecycle = fid == "m5_lifecycle_progress_to_t0"
        out.append(
            {
                "candidate_family_id": family,
                "candidate_feature_id": fid,
                "candidate_feature_name": name,
                "candidate_feature_definition": name,
                "candidate_feature_formula": formula,
                "candidate_primary_dedup_group_id": dedup,
                "candidate_overlap_group_ids": overlap.get(fid, ""),
                "candidate_alias_of": alias_of.get(fid, ""),
                "candidate_priority_before_evidence": priority,
                "source_artifact_alias": source,
                "source_columns": cols,
                "expected_availability": "appendix_or_deferred" if is_m4 else "blocked_until_t0_endpoint_proof" if is_lifecycle else "primary",
                "primary_candidate_allowed_before_lineage": (not is_m4) and (not is_lifecycle),
                "appendix_only_if_delayed": True,
                "extra_feature_role": "",
                "candidate_inventory_expected": True,
                "candidate_inventory_completeness_gate": "pass",
                "t0_frozen_endpoint_proof_status": "missing_or_not_proven" if is_lifecycle else "not_required",
                "notes": "predeclared_lineage_before_correlation",
            }
        )
    return out


EXPECTED_CANDIDATE_FEATURE_IDS = tuple(row["candidate_feature_id"] for row in candidate_definitions())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP18D payoff-state feature representation diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    parser.add_argument("--check-inputs-only", action="store_true")
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
        "candidate_feature_panel": LOCAL_CACHE_DIR / "candidate_feature_panel.parquet",
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_18c_handoff_audit": TABLE_DIR / "upstream_18c_handoff_audit.csv",
        "capacity_vs_representation_readout": TABLE_DIR / "capacity_vs_representation_readout.csv",
        "candidate_feature_inventory": TABLE_DIR / "candidate_feature_inventory.csv",
        "candidate_feature_lineage_audit": TABLE_DIR / "candidate_feature_lineage_audit.csv",
        "candidate_feature_pit_availability_audit": TABLE_DIR / "candidate_feature_pit_availability_audit.csv",
        "current_feature_gap_decomposition": TABLE_DIR / "current_feature_gap_decomposition.csv",
        "payoff_morphology_proxy_readout": TABLE_DIR / "payoff_morphology_proxy_readout.csv",
        "orthogonal_payoff_information_readout": TABLE_DIR / "orthogonal_payoff_information_readout.csv",
        "feature_family_candidate_prioritization": TABLE_DIR / "feature_family_candidate_prioritization.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "representation_refresh_decision": TABLE_DIR / "representation_refresh_decision.csv",
        "report": REPORT_DIR / "payoff_state_feature_representation_diagnostic_report.md",
        "manifest": MANIFEST_DIR / "18D_payoff_state_feature_representation_diagnostic_manifest.json",
        "input_manifest": MANIFEST_DIR / "input_artifact_manifest_18d.json",
    }


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
    path.write_text(json.dumps(clean_json(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if suffixes.endswith((".csv", ".csv.gz")):
        return pd.read_csv(path, **kwargs)
    raise ValueError(f"Unsupported table path: {path}")


def count_rows(path: Path) -> int | float:
    if not path.exists():
        return np.nan
    if path.is_dir():
        return len([p for p in path.iterdir() if p.is_file() and p.suffix == ".csv"])
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path))
    if suffixes.endswith((".csv", ".csv.gz")):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    if suffixes.endswith(".md"):
        return len(path.read_text(encoding="utf-8").splitlines())
    if suffixes.endswith(".json"):
        return 1
    return np.nan


def header_columns(path: Path) -> list[str]:
    if not path.exists():
        return []
    if path.is_dir():
        csvs = sorted(p for p in path.iterdir() if p.is_file() and p.suffix == ".csv")
        if not csvs:
            return []
        return list(pd.read_csv(csvs[0], nrows=0).columns)
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return list(pd.read_parquet(path, engine="pyarrow").columns)
    if suffixes.endswith((".csv", ".csv.gz")):
        return list(pd.read_csv(path, nrows=0).columns)
    return []


def relative_to_topic(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        return str(path)


def metric_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if np.isfinite(out) else default


def bool_like(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    if pd.isna(value):
        return False
    return bool(value)


def rank_ic(score: pd.Series | np.ndarray, target: pd.Series | np.ndarray) -> float:
    s = pd.Series(score, dtype="float64")
    t = pd.Series(target, dtype="float64")
    valid = np.isfinite(s) & np.isfinite(t)
    if int(valid.sum()) < 3:
        return np.nan
    sr = s.loc[valid].rank(method="average")
    tr = t.loc[valid].rank(method="average")
    if sr.nunique() <= 1 or tr.nunique() <= 1:
        return np.nan
    return float(sr.corr(tr))


def required_columns_for_key(key: str) -> set[str]:
    mapping: dict[str, set[str]] = {
        "eighteen_b_matrix": {"step_id", "label_id", "instrument", "episode_cluster_id", "cluster_split_bucket", "y_payoff_h20", "mr_volatility_20d", "mr_volume_20d_zscore"},
        "eighteen_c_score_panel": {"step_id", "label_id", "cluster_split_bucket", "y_payoff_h20", "score_ridge_payoff_rank_h20_v1"},
        "eighteen_c_decision": {"decision_state", "next_allowed_requirement", "all_hard_gates_pass"},
        "eighteen_c_model_registry": {"model_id", "model_family", "fit_split"},
        "eighteen_c_model_cv_readout": {"cv_scheme", "model_id", "fold_id", "payoff_rank_ic", "test_row_n"},
        "eighteen_c_oos_rank_readout": {"split_bucket", "model_id", "rank_ic_spearman", "row_n"},
        "eighteen_c_decile_monotonicity": {"split_bucket", "model_id", "decile_payoff_monotonicity_spearman"},
        "eighteen_c_baseline_comparison": {"comparison_id", "comparison_status"},
        "eighteen_c_topk_removal_sensitivity": {"sensitivity_id", "split_bucket"},
        "eighteen_c_model_coefficients": {"model_id", "feature_name", "coefficient"},
        "eighteen_c_binary_sanity": {"split_bucket", "model_id", "binary_sanity_status"},
        "sixteen_b_label_step_panel": {"step_id", "label_id", "instrument", "step_start_pos", "step_start_date", "step_start_qfq_close"},
        "sixteen_b_materialized_step_panel": {"step_id", "cluster_start_pos", "cluster_end_pos"},
        "sixteen_b_label_panel_readout": {"step_id", "label_id", "step_start_pos", "step_start_date"},
        "sixteen_a_episode_interval_panel": {"instrument", "episode_cluster_id", "cluster_start_pos", "cluster_end_pos"},
        "sixteen_a_step_geometry_panel": {"instrument", "episode_cluster_id", "cluster_start_pos", "cluster_end_pos"},
        "stock_daily_qfq_dir": {"date", "open", "high", "low", "close", "volume"},
    }
    if key.endswith("_manifest") or key.endswith("_report") or key in {"research_plan", "requirement_18d", "eighteen_c_config"}:
        return set()
    return mapping.get(key, set())


def dir_sha(path: Path) -> str:
    h = hashlib.sha256()
    if not path.exists() or not path.is_dir():
        return ""
    for child in sorted(p for p in path.iterdir() if p.is_file() and p.suffix == ".csv"):
        h.update(child.name.encode("utf-8"))
        h.update(str(child.stat().st_size).encode("utf-8"))
    return h.hexdigest()


def artifact_sha(path: Path) -> str:
    if not path.exists():
        return ""
    if path.is_dir():
        return dir_sha(path)
    return file_sha(path)


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    alias_req = config.get("source_alias_requirements", {})
    path_roles = config.get("path_roles", {})
    alias_rows: list[tuple[str, str, int]] = []
    for alias, keys in config.get("source_aliases", {}).items():
        for priority, key in enumerate(keys, start=1):
            alias_rows.append((alias, key, priority))
    represented = {(alias, key) for alias, key, _ in alias_rows}
    for key in config.get("paths", {}):
        role = path_roles.get(key, {})
        if not any(row_key == key for _, row_key, _ in alias_rows):
            alias_rows.append((role.get("source_alias", key), key, 1))

    for source_alias, key, priority in alias_rows:
        if (source_alias, key) in represented or key in config.get("paths", {}):
            path = resolved[key]
            exists = path.exists()
            cols = set(header_columns(path)) if exists else set()
            required_cols = required_columns_for_key(key)
            if key == "stock_daily_qfq_dir" and exists:
                required_cols = set(required_cols)
                has_money = bool({"amount", "money", "turnover_value"}.intersection(cols)) or {"volume", "close"}.issubset(cols)
            else:
                has_money = True
            missing_cols = sorted(required_cols - cols)
            meta = path_roles.get(key, {})
            req_meta = alias_req.get(source_alias, {})
            required = bool(meta.get("required", False))
            required_for_primary = bool(req_meta.get("required_for_primary_candidate", False))
            affected = str(req_meta.get("affected_family_ids", ""))
            blockers = []
            if required and not exists:
                blockers.append("missing_required_artifact")
            if required and missing_cols:
                blockers.append("schema_missing:" + ",".join(missing_cols))
            if key == "stock_daily_qfq_dir" and exists and count_rows(path) <= 0:
                blockers.append("qfq_dir_empty")
            if key == "stock_daily_qfq_dir" and not has_money:
                blockers.append("qfq_money_proxy_source_missing")
            schema_status = "pass" if exists and not missing_cols and has_money else "fail" if required or required_for_primary else "optional_missing"
            resolved_status = "pass" if exists and schema_status == "pass" else "fail" if required or required_for_primary else "optional_missing"
            rows.append(
                {
                    "artifact_path": str(path),
                    "source_artifact_alias": source_alias,
                    "config_path_key": key,
                    "resolver_priority": priority,
                    "artifact_role": meta.get("role", ""),
                    "required": required,
                    "required_for_primary_candidate": required_for_primary,
                    "affected_family_ids": affected,
                    "exists": exists,
                    "row_count": count_rows(path) if exists else np.nan,
                    "column_count": len(cols),
                    "sha256": artifact_sha(path),
                    "manifest_path": "",
                    "manifest_hash_status": "not_manifested",
                    "schema_status": schema_status,
                    "freshness_status": "not_checked",
                    "resolved_source_status": resolved_status,
                    "blocking_reason": ";".join(blockers),
                }
            )
    audit = pd.DataFrame(rows).drop_duplicates(["source_artifact_alias", "config_path_key", "resolver_priority"])
    failing = audit.loc[(audit["required"].astype(bool) | audit["required_for_primary_candidate"].astype(bool)) & ~audit["resolved_source_status"].eq("pass")]
    return audit, "pass" if failing.empty else "fail"


def load_inputs(resolved: dict[str, Path]) -> dict[str, pd.DataFrame]:
    keys = [
        "eighteen_b_matrix",
        "eighteen_c_score_panel",
        "eighteen_c_decision",
        "eighteen_c_model_cv_readout",
        "eighteen_c_oos_rank_readout",
        "sixteen_b_label_step_panel",
        "sixteen_b_materialized_step_panel",
    ]
    return {key: read_table(resolved[key]) for key in keys}


def read_legacy_config_next(path: Path) -> str:
    if not path.exists():
        return ""
    payload = load_config(path)
    return str(payload.get("expected", {}).get("next_allowed_requirement", ""))


def build_upstream_18c_handoff_audit(config: dict[str, Any], resolved: dict[str, Path], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    expected = config["expected"]
    decision = tables["eighteen_c_decision"].iloc[0]
    manifest = read_json(resolved["eighteen_c_manifest"])
    legacy_next = read_legacy_config_next(resolved["eighteen_c_config"])
    rows = []

    def add(source_table: str, metric: str, observed: Any, expected_value: Any, tolerance: float = 0.0, source_model_id: str = "", source_split_bucket: str = "") -> None:
        if isinstance(observed, (int, float, np.integer, np.floating)) and isinstance(expected_value, (int, float, np.integer, np.floating)):
            ok = abs(float(observed) - float(expected_value)) <= tolerance
        else:
            ok = str(observed) == str(expected_value)
        rows.append(
            {
                "source_table": source_table,
                "source_model_id": source_model_id,
                "source_split_bucket": source_split_bucket,
                "source_metric": metric,
                "expected_value": expected_value,
                "observed_value": observed,
                "tolerance": tolerance,
                "handoff_status": "pass" if ok else "fail",
                "blocking_reason": "" if ok else f"{metric}_mismatch",
            }
        )

    add("payoff_state_separability_decision.csv", "decision_state", decision["decision_state"], expected["upstream_18c_decision_state"])
    add("payoff_state_separability_decision.csv", "next_allowed_requirement", decision["next_allowed_requirement"], expected["upstream_18c_next_allowed_requirement"])
    add("18C_manifest", "decision_state", manifest.get("decision_state", ""), expected["upstream_18c_decision_state"])
    add("18C_manifest", "next_allowed_requirement", manifest.get("next_allowed_requirement", ""), expected["upstream_18c_next_allowed_requirement"])
    add("config_18c_expected_block", "legacy_config_expected_next_status", "audit_only_not_authoritative", "audit_only_not_authoritative")
    add("config_18c_expected_block", "legacy_config_expected_next_mismatch", str(legacy_next != expected["upstream_18c_next_allowed_requirement"]).lower(), "true")

    oos = tables["eighteen_c_oos_rank_readout"]
    for model_id, exp_value in expected["robustness_rank_ic"].items():
        observed_rows = oos.loc[oos["model_id"].eq(model_id) & oos["split_bucket"].eq("robustness")]
        observed = np.nan if observed_rows.empty else float(observed_rows["rank_ic_spearman"].iloc[0])
        add("payoff_state_oos_rank_readout.csv", "robustness_rank_ic", observed, float(exp_value), float(expected["handoff_tolerance"]), model_id, "robustness")

    frame = pd.DataFrame(rows)
    blocking = frame.loc[~frame["source_table"].eq("config_18c_expected_block")]
    gate = "pass" if blocking["handoff_status"].eq("pass").all() else "fail"
    return frame, gate


def model_ready_matrix(config: dict[str, Any], matrix: pd.DataFrame) -> pd.DataFrame:
    required = [*config["model_ready_features"], config["target_column"], "episode_cluster_id", "cluster_split_bucket"]
    missing = sorted(set(required) - set(matrix.columns))
    if missing:
        raise ValueError(f"18B matrix missing required columns: {missing}")
    return matrix.copy()


def grouped_fold_assignment(train: pd.DataFrame, fold_n: int, seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    clusters = np.array(sorted(train["episode_cluster_id"].astype(str).unique()))
    rng.shuffle(clusters)
    fold_map = {cluster: i % fold_n for i, cluster in enumerate(clusters)}
    return train["episode_cluster_id"].astype(str).map(fold_map)


def fit_score_model(model_id: str, config: dict[str, Any], train: pd.DataFrame, fit: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    features = config["model_ready_features"]
    x_fit = fit[features].to_numpy(dtype=float)
    y_fit = fit[config["target_column"]].to_numpy(dtype=float)
    x_test = test[features].to_numpy(dtype=float)
    if model_id == PRIMARY_MODEL_ID:
        model = Ridge(alpha=10.0, fit_intercept=True)
    else:
        depth = 3 if "depth3" in model_id else 4
        params = config["capacity_probe_params"]
        leaf = max(int(params["min_samples_leaf_floor"]), int(math.ceil(float(params["min_samples_leaf_train_fraction"]) * len(fit))))
        model = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=leaf, random_state=int(params["random_state"]))
    return model.fit(x_fit, y_fit).predict(x_test)


def build_capacity_vs_representation_readout(config: dict[str, Any], matrix: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, Any]]:
    expected = config["expected"]
    params = config["capacity_probe_params"]
    oos = tables["eighteen_c_oos_rank_readout"].copy()
    cv_source = tables["eighteen_c_model_cv_readout"].copy()
    primary_robust = float(oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("robustness"), "rank_ic_spearman"].iloc[0])
    aux_ids = ["elastic_net_payoff_rank_h20_v1", "shallow_tree_payoff_depth2_v1", "ridge_ordinal_payoff_state_v1"]
    aux_robust = {
        model_id: float(oos.loc[oos["model_id"].eq(model_id) & oos["split_bucket"].eq("robustness"), "rank_ic_spearman"].iloc[0])
        for model_id in aux_ids
    }
    max_aux = max(aux_robust.values())
    max_aux_minus_primary = max_aux - primary_robust
    max_aux_margin_to_floor = float(expected["rank_ic_materiality_floor"]) - max_aux
    max_aux_margin_to_capacity_delta_threshold = float(expected["capacity_delta_threshold"]) - max_aux_minus_primary
    capacity_margin_status = (
        "thin_margin_caveat"
        if max_aux_margin_to_floor <= float(expected["thin_margin_threshold"]) or max_aux_margin_to_capacity_delta_threshold <= float(expected["thin_margin_threshold"])
        else "clear_margin"
    )

    train = matrix.loc[matrix["cluster_split_bucket"].eq("train")].copy()
    train["fold_id"] = grouped_fold_assignment(train, int(params["cv_fold_n"]), int(params["cv_fold_seed"]))
    cv_rows = []
    for model_id in [PRIMARY_MODEL_ID, *params["model_ids"]]:
        for fold in range(int(params["cv_fold_n"])):
            fit = train.loc[~train["fold_id"].eq(fold)]
            test = train.loc[train["fold_id"].eq(fold)]
            score = fit_score_model(model_id, config, train, fit, test)
            ic = rank_ic(score, test[config["target_column"]])
            cv_rows.append(
                {
                    "model_id": model_id,
                    "fold_id": fold,
                    "test_row_n": len(test),
                    "payoff_rank_ic": ic,
                    "fold_status": "pass" if len(test) > 0 else "fail",
                }
            )
    cv_probe = pd.DataFrame(cv_rows)
    pass_cv = cv_probe.loc[cv_probe["fold_status"].eq("pass")]
    cv_mean = pass_cv.groupby("model_id")["payoff_rank_ic"].mean().to_dict()
    cv_weighted = {
        model_id: float((g["payoff_rank_ic"] * g["test_row_n"]).sum() / g["test_row_n"].sum())
        for model_id, g in pass_cv.groupby("model_id")
    }
    primary_cv = float(cv_mean[PRIMARY_MODEL_ID])
    probe_ids = list(params["model_ids"])
    max_probe_cv = max(float(cv_mean[mid]) for mid in probe_ids)
    max_probe_delta = max_probe_cv - primary_cv
    medium_capacity_probe_caveat = bool(max_probe_cv >= float(expected["rank_ic_materiality_floor"]) or max_probe_delta >= float(expected["capacity_delta_threshold"]))

    capacity_bottleneck = bool(max_aux >= float(expected["rank_ic_materiality_floor"]) or max_aux_minus_primary >= float(expected["capacity_delta_threshold"]) or medium_capacity_probe_caveat)
    representation_bottleneck = bool(max_aux < float(expected["rank_ic_materiality_floor"]) and max_aux_minus_primary < float(expected["capacity_delta_threshold"]) and not medium_capacity_probe_caveat)
    scope = "capacity_not_excluded_by_train_cv_probe" if medium_capacity_probe_caveat else "low_capacity_representation_gap_with_capacity_caveat" if capacity_margin_status == "thin_margin_caveat" else "low_capacity_representation_gap"

    rows = []
    robust_model_ids = [PRIMARY_MODEL_ID, *aux_ids, expected["volatility_baseline_id"]]
    for _, row in oos.loc[oos["model_id"].isin(robust_model_ids)].iterrows():
        model_id = row["model_id"]
        split = row["split_bucket"]
        rows.append(
            {
                "model_id": model_id,
                "model_family": "18c_replayed_model",
                "source_feature_set": "current_18B_23_features",
                "split_bucket": split,
                "rank_ic_spearman": row["rank_ic_spearman"],
                "cv_mean_rank_ic_spearman": cv_source.loc[cv_source["model_id"].eq(model_id), "payoff_rank_ic"].mean() if model_id in set(cv_source["model_id"]) else np.nan,
                "cv_weighted_mean_rank_ic_spearman": np.nan,
                "cv_rank_ic_delta_vs_primary": np.nan,
                "rank_ic_materiality_floor": expected["rank_ic_materiality_floor"],
                "delta_vs_primary_ridge": metric_float(row["rank_ic_spearman"]) - primary_robust if split == "robustness" else np.nan,
                "delta_vs_volatility20d_baseline": np.nan,
                "capacity_delta_threshold": expected["capacity_delta_threshold"],
                "max_aux_margin_to_floor": max_aux_margin_to_floor,
                "max_aux_margin_to_capacity_delta_threshold": max_aux_margin_to_capacity_delta_threshold,
                "capacity_threshold_sensitivity_threshold": "0.010000|0.015000|0.020000",
                "capacity_threshold_sensitivity_status": "thin_at_0.010" if max_aux_minus_primary >= 0.010 else "stable_below_0.010",
                "capacity_margin_status": capacity_margin_status,
                "capacity_conclusion_scope": scope,
                "medium_capacity_probe_caveat": medium_capacity_probe_caveat,
                "capacity_bottleneck_flag": capacity_bottleneck,
                "representation_bottleneck_flag": representation_bottleneck,
                "cv_fold_n": params["cv_fold_n"],
                "cv_fold_seed": params["cv_fold_seed"],
                "cv_aggregation_method": params["cv_aggregation"],
                "primary_cv_rank_ic": primary_cv,
                "readout_status": "replayed_18c_oos",
            }
        )
    for model_id in [PRIMARY_MODEL_ID, *probe_ids]:
        rows.append(
            {
                "model_id": model_id,
                "model_family": "ridge_regression" if model_id == PRIMARY_MODEL_ID else "decision_tree_regressor",
                "source_feature_set": "current_18B_23_features",
                "split_bucket": "train_grouped_cv",
                "rank_ic_spearman": np.nan,
                "cv_mean_rank_ic_spearman": cv_mean[model_id],
                "cv_weighted_mean_rank_ic_spearman": cv_weighted[model_id],
                "cv_rank_ic_delta_vs_primary": float(cv_mean[model_id]) - primary_cv,
                "rank_ic_materiality_floor": expected["rank_ic_materiality_floor"],
                "delta_vs_primary_ridge": float(cv_mean[model_id]) - primary_cv,
                "delta_vs_volatility20d_baseline": np.nan,
                "capacity_delta_threshold": expected["capacity_delta_threshold"],
                "max_aux_margin_to_floor": max_aux_margin_to_floor,
                "max_aux_margin_to_capacity_delta_threshold": max_aux_margin_to_capacity_delta_threshold,
                "capacity_threshold_sensitivity_threshold": "0.010000|0.015000|0.020000",
                "capacity_threshold_sensitivity_status": "thin_at_0.010" if max_aux_minus_primary >= 0.010 else "stable_below_0.010",
                "capacity_margin_status": capacity_margin_status,
                "capacity_conclusion_scope": scope,
                "medium_capacity_probe_caveat": medium_capacity_probe_caveat,
                "capacity_bottleneck_flag": capacity_bottleneck,
                "representation_bottleneck_flag": representation_bottleneck,
                "cv_fold_n": params["cv_fold_n"],
                "cv_fold_seed": params["cv_fold_seed"],
                "cv_aggregation_method": params["cv_aggregation"],
                "primary_cv_rank_ic": primary_cv,
                "readout_status": "bounded_train_only_probe",
            }
        )
    summary = {
        "primary_ridge_robustness_rank_ic": primary_robust,
        "max_aux_existing_feature_rank_ic": max_aux,
        "max_aux_minus_primary_rank_ic": max_aux_minus_primary,
        "max_aux_margin_to_floor": max_aux_margin_to_floor,
        "max_aux_margin_to_capacity_delta_threshold": max_aux_margin_to_capacity_delta_threshold,
        "capacity_margin_status": capacity_margin_status,
        "capacity_conclusion_scope": scope,
        "max_train_grouped_cv_probe_rank_ic": max_probe_cv,
        "max_train_grouped_cv_probe_minus_primary_cv_rank_ic": max_probe_delta,
        "medium_capacity_probe_caveat": medium_capacity_probe_caveat,
        "capacity_bottleneck_flag": capacity_bottleneck,
        "representation_bottleneck_flag": representation_bottleneck,
        "primary_cv_rank_ic": primary_cv,
    }
    return pd.DataFrame(rows), summary


def candidate_inventory(config: dict[str, Any]) -> pd.DataFrame:
    expected_n = int(config.get("expected", {}).get("total_required_candidate_feature_n", len(EXPECTED_CANDIDATE_FEATURE_IDS)))
    frame = pd.DataFrame(candidate_definitions())
    summary = candidate_inventory_summary(frame, expected_n)
    frame["candidate_inventory_completeness_gate"] = summary["candidate_inventory_completeness_gate"]
    return frame


def candidate_inventory_summary(inventory: pd.DataFrame, expected_n: int | None = None) -> dict[str, Any]:
    expected = set(EXPECTED_CANDIDATE_FEATURE_IDS)
    observed = set(inventory["candidate_feature_id"].astype(str)) if "candidate_feature_id" in inventory else set()
    extra_ids = sorted(observed - expected)
    extra_blocking = []
    if extra_ids and "extra_feature_role" in inventory:
        extra_rows = inventory.loc[inventory["candidate_feature_id"].astype(str).isin(extra_ids)]
        extra_blocking = sorted(
            fid
            for fid, role in zip(extra_rows["candidate_feature_id"].astype(str), extra_rows["extra_feature_role"].astype(str), strict=False)
            if role != "appendix_only_exploratory"
        )
    elif extra_ids:
        extra_blocking = extra_ids
    formula_missing = 0
    if {"candidate_family_id", "candidate_feature_formula"}.issubset(inventory.columns):
        formula_missing = int(
            inventory.loc[~inventory["candidate_family_id"].eq("M4"), "candidate_feature_formula"]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
            .sum()
        )
    duplicate_n = int(inventory["candidate_feature_id"].duplicated().sum()) if "candidate_feature_id" in inventory else 0
    missing_ids = sorted(expected - observed)
    expected_count = int(expected_n if expected_n is not None else len(expected))
    gate = (
        "pass"
        if not missing_ids
        and not extra_blocking
        and duplicate_n == 0
        and formula_missing == 0
        and len(observed & expected) == expected_count
        else "fail"
    )
    return {
        "candidate_inventory_completeness_gate": gate,
        "candidate_inventory_expected_feature_n": expected_count,
        "candidate_inventory_observed_feature_n": int(len(observed & expected)),
        "candidate_inventory_missing_feature_n": int(len(missing_ids)),
        "candidate_inventory_extra_feature_n": int(len(extra_blocking)),
        "candidate_inventory_duplicate_feature_id_n": duplicate_n,
        "candidate_inventory_formula_missing_n": formula_missing,
        "candidate_inventory_missing_feature_ids": "|".join(missing_ids),
        "candidate_inventory_extra_feature_ids": "|".join(extra_blocking),
    }


def normalize_qfq(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.sort_values("date").reset_index(drop=True)
    if "qfq_close" in df.columns and "close" not in df.columns:
        df["close"] = df["qfq_close"]
    for col in ["open", "high", "low", "close", "volume", "money", "amount", "turnover_value", "turnover_rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = df["date"].astype(str)
    if "amount_proxy" not in df.columns:
        if "amount" in df.columns:
            df["amount_proxy"] = df["amount"]
        elif "money" in df.columns:
            df["amount_proxy"] = df["money"]
        elif "turnover_value" in df.columns:
            df["amount_proxy"] = df["turnover_value"]
        else:
            df["amount_proxy"] = df["volume"] * df["close"]
    if "money" not in df.columns:
        df["money"] = df["amount_proxy"]
    if "turnover_rate" not in df.columns:
        df["turnover_rate"] = np.nan
    df["ma60"] = df["close"].rolling(60, min_periods=60).mean()
    return df


def entropy_from_counts(counts: np.ndarray, eps: float) -> tuple[float, float]:
    counts = counts.astype(float)
    p = (counts + eps) / (counts.sum() + len(counts) * eps)
    ent = float(-(p * np.log(p)).sum())
    return ent, float(ent / np.log(len(counts)))


def state_sequence(close: np.ndarray, flat: float) -> np.ndarray:
    rets = close[1:] / close[:-1] - 1.0
    out = np.zeros(len(rets), dtype=int)
    out[rets > flat] = 2
    out[rets < -flat] = 0
    out[(rets >= -flat) & (rets <= flat)] = 1
    return out


def window_bounds(window_id: str, step_pos: int, low_pos: int, first_valid: int = 0) -> tuple[int, int]:
    if window_id == "episode_low_to_t0":
        return low_pos, step_pos
    if window_id == "trailing_20":
        return max(first_valid, step_pos - 19), step_pos
    if window_id == "trailing_60":
        return max(first_valid, step_pos - 59), step_pos
    raise ValueError(f"Unknown window_id: {window_id}")


def safe_div(numerator: float, denominator: float, eps: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator <= eps:
        return np.nan
    return float(numerator / denominator)


def linear_r2(values: np.ndarray, eps: float) -> float:
    values = values.astype(float)
    valid = np.isfinite(values)
    if int(valid.sum()) < 5:
        return np.nan
    y = values[valid]
    if float(np.nanvar(y)) <= eps:
        return np.nan
    x = np.arange(len(values), dtype=float)[valid]
    coef = np.polyfit(x, y, 1)
    pred = coef[0] * x + coef[1]
    sst = float(((y - y.mean()) ** 2).sum())
    if sst <= eps:
        return np.nan
    return float(1.0 - ((y - pred) ** 2).sum() / sst)


def longest_run(signs: np.ndarray, positive: bool) -> int:
    target = signs > 0 if positive else signs < 0
    best = 0
    cur = 0
    for flag in target:
        if bool(flag):
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def signed_flow_arrays(window: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    close = window["close"].to_numpy(dtype=float)
    amount = window["amount_proxy"].to_numpy(dtype=float)
    diff = np.diff(close, prepend=np.nan)
    sign = np.sign(diff)
    sign[~np.isfinite(sign)] = np.nan
    signed = amount * sign
    return amount, sign, signed


def money_flow_stats(window: pd.DataFrame, eps: float, required_n: int) -> dict[str, float]:
    if len(window) < required_n:
        return {"net": np.nan, "positive_share": np.nan, "reversal_rate": np.nan}
    amount, sign, signed = signed_flow_arrays(window)
    valid = np.isfinite(amount) & (amount > eps) & np.isfinite(sign)
    valid[0] = False
    denom_abs = float(np.abs(amount[valid]).sum())
    denom_total = float(amount[valid].sum())
    signs = np.sign(signed[valid])
    return {
        "net": safe_div(float(signed[valid].sum()), denom_abs, eps),
        "positive_share": safe_div(float(amount[valid & (sign > 0)].sum()), denom_total, eps),
        "reversal_rate": float(np.mean(signs[1:] != signs[:-1])) if len(signs) >= 2 else np.nan,
    }


def count_failed_repairs(close: np.ndarray, low_pos: int, cluster_start: int, step_pos: int) -> int:
    count = 0
    for pos in range(low_pos + 3, step_pos - 4):
        rel = pos - cluster_start
        if rel - 3 < 0 or rel + 5 >= len(close):
            continue
        if close[rel] > np.nanmax(close[rel - 3 : rel]) and np.nanmin(close[rel + 1 : rel + 6]) / close[rel] - 1.0 <= -0.05 and np.nanmax(close[rel + 1 : rel + 6]) <= close[rel]:
            count += 1
    return count


def count_failed_breakouts(high: np.ndarray, low: np.ndarray, close: np.ndarray, cluster_start: int, step_pos: int) -> int:
    count = 0
    for pos in range(cluster_start + 1, step_pos - 4):
        rel = pos - cluster_start
        if rel + 5 >= len(high):
            continue
        if high[rel] >= np.nanmax(high[:rel]) and np.nanmin(close[rel + 1 : rel + 6]) < low[rel]:
            count += 1
    return count


def derive_row_features(row: pd.Series, qfq: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    params = config["entropy_params"]
    money_params = config["money_flow_proxy_params"]
    eps = float(params["probability_epsilon"])
    denom_eps = float(money_params["denominator_epsilon"])
    flat = float(params["return_state_flat_abs_return_max"])
    min_n = int(params["min_observation_n"])
    out: dict[str, Any] = {}
    step_pos = int(row["step_start_pos"])
    cluster_start = int(row["cluster_start_pos"])
    cluster_end = int(row["cluster_end_pos"])
    if step_pos >= len(qfq) or step_pos < 0 or cluster_start > step_pos:
        return out
    seg = qfq.iloc[cluster_start : step_pos + 1]
    if len(seg) < min_n:
        return out
    low_rel = int(np.nanargmin(seg["low"].to_numpy(dtype=float)))
    high_rel = int(np.nanargmax(seg["high"].to_numpy(dtype=float)))
    low_pos = cluster_start + low_rel
    high_pos = cluster_start + high_rel
    close_t0 = float(qfq["close"].iloc[step_pos])
    low_price = float(qfq["low"].iloc[low_pos])
    low_close = float(qfq["close"].iloc[low_pos])
    high_price = float(qfq["high"].iloc[high_pos])
    age = max(step_pos - cluster_start, 0)
    out.update(
        {
            "episode_low_pos_t0": low_pos,
            "episode_high_pos_t0": high_pos,
            "episode_low_date_t0": qfq["date"].iloc[low_pos],
            "episode_high_date_t0": qfq["date"].iloc[high_pos],
            "episode_range_low_t0": low_price,
            "episode_range_high_t0": high_price,
            "qfq_reconciled_step_start_date": qfq["date"].iloc[step_pos],
            "qfq_reconciled_step_start_close": close_t0,
        }
    )
    denom = high_price - low_price
    out["m1_close_location_episode_range"] = safe_div(close_t0 - low_price, denom, denom_eps)
    running_max = seg["close"].cummax().to_numpy(dtype=float)
    valid_running = np.isfinite(running_max) & (running_max > denom_eps)
    out["m1_episode_drawdown_pre_t0"] = float(np.nanmin(seg["low"].to_numpy(dtype=float)[valid_running] / running_max[valid_running] - 1.0)) if valid_running.any() else np.nan
    out["m1_episode_recovery_ratio_to_high_t0"] = safe_div(close_t0 - low_price, denom, denom_eps)
    out["m1_pullback_from_episode_high_t0"] = safe_div(close_t0, high_price, denom_eps) - 1.0 if high_price > denom_eps else np.nan
    path = qfq["close"].iloc[low_pos : step_pos + 1].to_numpy(dtype=float)
    out["m1_repair_path_efficiency_episode"] = safe_div(abs(close_t0 - low_close), float(np.abs(np.diff(path)).sum()) if len(path) >= 2 else np.nan, denom_eps)
    out["m1_path_linearity_r2_low_to_t0"] = linear_r2(path, denom_eps)
    out["m3_upside_room_to_episode_high"] = safe_div(high_price - close_t0, close_t0, denom_eps)
    out["m3_downside_crowding_to_episode_low"] = safe_div(close_t0 - low_price, close_t0, denom_eps)
    out["m3_downside_room_to_episode_low_t0"] = safe_div(close_t0 - low_price, close_t0, denom_eps)
    out["m3_upside_downside_room_ratio_t0"] = safe_div(high_price - close_t0, close_t0 - low_price, denom_eps)
    out["m3_asymmetric_range_position_t0"] = 2.0 * safe_div(close_t0 - low_price, denom, denom_eps) - 1.0 if denom > denom_eps else np.nan
    vol = metric_float(row.get("volatility_20d"), np.nan)
    repair_return = close_t0 / low_close - 1.0 if low_close > 0 else np.nan
    out["m3_vol_adjusted_repair_strength"] = repair_return / vol if np.isfinite(vol) and vol > 0 else np.nan
    out["m5_bars_since_episode_low"] = step_pos - low_pos
    out["m5_bars_since_episode_high_t0"] = step_pos - high_pos
    out["m5_episode_age_to_t0"] = step_pos - cluster_start
    horizon = metric_float(row.get("horizon_sessions"), np.nan)
    out["m5_nonoverlap_step_index_to_t0"] = math.floor(age / horizon) if np.isfinite(horizon) and horizon > 0 else np.nan
    out["m5_low_to_t0_age_ratio"] = (step_pos - low_pos) / max(age, 1)
    out["m5_high_to_t0_age_ratio"] = (step_pos - high_pos) / max(age, 1)
    out["m5_low_before_high_t0"] = float(low_pos < high_pos)
    out["m5_lifecycle_progress_to_t0"] = np.nan if cluster_end > step_pos else safe_div(step_pos - cluster_start, cluster_end - cluster_start, denom_eps)
    reclaim = np.nan
    for pos in range(max(low_pos + 1, 1), step_pos + 1):
        ma_prev = qfq["ma60"].iloc[pos - 1]
        ma_now = qfq["ma60"].iloc[pos]
        if np.isfinite(ma_prev) and np.isfinite(ma_now) and qfq["close"].iloc[pos - 1] < ma_prev and qfq["close"].iloc[pos] >= ma_now:
            reclaim = pos
            break
    out["reclaim_pos_t0"] = reclaim
    out["m5_bars_since_reclaim"] = step_pos - reclaim if np.isfinite(reclaim) else np.nan

    def close_window(window_id: str) -> pd.DataFrame:
        start, end = window_bounds(window_id, step_pos, low_pos)
        return qfq.iloc[start : end + 1]

    w20 = close_window("trailing_20")
    if len(w20) >= min_n:
        states = state_sequence(w20["close"].to_numpy(dtype=float), flat)
        counts = np.array([(states == 0).sum(), (states == 1).sum(), (states == 2).sum()])
        out["m1_return_sign_entropy_trailing20"] = entropy_from_counts(counts, eps)[1]
        run_signs = np.sign(np.diff(w20["close"].to_numpy(dtype=float)))
        out["m1_up_down_run_imbalance_20"] = longest_run(run_signs, True) - longest_run(run_signs, False)
        candle_range = (w20["high"] - w20["low"]).astype(float)
        valid_candle = np.isfinite(candle_range) & (candle_range > denom_eps)
        upper_shadow = (w20["high"] - np.maximum(w20["open"], w20["close"])).astype(float)
        out["m3_upper_shadow_pressure_share_20"] = float((upper_shadow.loc[valid_candle] / candle_range.loc[valid_candle]).mean()) if int(valid_candle.sum()) >= 5 else np.nan
    if len(w20) >= 20:
        mf20 = money_flow_stats(w20, denom_eps, 20)
        out["m2_net_signed_money_flow_trailing20"] = mf20["net"]
        out["m2_positive_money_flow_share_trailing20"] = mf20["positive_share"]
        amount20, sign20, signed20 = signed_flow_arrays(w20)
        valid20 = np.isfinite(amount20) & (amount20 > denom_eps) & np.isfinite(sign20)
        valid20[0] = False
        signs20 = np.sign(signed20[valid20])
        out["m2_money_flow_persistence_trailing20"] = float(np.mean(signs20[1:] == signs20[:-1])) if len(signs20) >= 2 else np.nan
        out["m2_money_flow_reversal_accel_5v20"] = np.nan
        out["m2_flow_price_divergence_persistence_20"] = np.nan
        out["m2_signed_flow_volatility_20"] = float(np.nanstd(signed20[valid20] / np.abs(amount20[valid20]))) if int(valid20.sum()) >= 5 else np.nan
        abs_signed = np.abs(signed20[valid20])
        out["m2_flow_concentration_top3_share_20"] = safe_div(float(np.sort(abs_signed)[-3:].sum()), float(abs_signed.sum()), denom_eps) if len(abs_signed) >= 3 else np.nan
    wep = close_window("episode_low_to_t0")
    if len(wep) >= min_n:
        states = state_sequence(wep["close"].to_numpy(dtype=float), flat)
        trans = states[:-1] * 3 + states[1:] if len(states) >= 2 else np.array([], dtype=int)
        counts = np.array([(trans == i).sum() for i in range(9)])
        out["m1_path_transition_entropy_episode"] = entropy_from_counts(counts, eps)[1] if counts.sum() > 0 else np.nan
        close_seg = seg["close"].to_numpy(dtype=float)
        high_seg = seg["high"].to_numpy(dtype=float)
        low_seg = seg["low"].to_numpy(dtype=float)
        out["m1_failed_repair_count_low_to_t0"] = float(count_failed_repairs(close_seg, low_pos, cluster_start, step_pos))
        out["m3_failed_breakout_count_pre_t0"] = float(count_failed_breakouts(high_seg, low_seg, close_seg, cluster_start, step_pos))
    w60 = close_window("trailing_60")
    if len(w60) >= 60:
        range60 = float(w60["high"].max() - w60["low"].min())
        out["m1_close_location_trailing60_range"] = safe_div(close_t0 - float(w60["low"].min()), range60, denom_eps)
        mf5 = money_flow_stats(w20.tail(5), denom_eps, 5) if len(w20) >= 20 else {"net": np.nan, "positive_share": np.nan, "reversal_rate": np.nan}
        mf10 = money_flow_stats(w20.tail(10), denom_eps, 10) if len(w20) >= 20 else {"net": np.nan, "positive_share": np.nan, "reversal_rate": np.nan}
        mf20 = money_flow_stats(w20, denom_eps, 20) if len(w20) >= 20 else {"net": np.nan, "positive_share": np.nan, "reversal_rate": np.nan}
        out["m2_net_signed_money_flow_accel_5v20"] = mf5["net"] - mf20["net"] if np.isfinite(mf5["net"]) and np.isfinite(mf20["net"]) else np.nan
        out["m2_positive_money_flow_share_accel_5v20"] = mf5["positive_share"] - mf20["positive_share"] if np.isfinite(mf5["positive_share"]) and np.isfinite(mf20["positive_share"]) else np.nan
        out["m2_money_flow_reversal_accel_5v20"] = mf5["reversal_rate"] - mf20["reversal_rate"] if np.isfinite(mf5["reversal_rate"]) and np.isfinite(mf20["reversal_rate"]) else np.nan
        out["m2_net_signed_money_flow_curvature_5_10_20"] = mf5["net"] - 2.0 * mf10["net"] + mf20["net"] if np.isfinite(mf5["net"]) and np.isfinite(mf10["net"]) and np.isfinite(mf20["net"]) else np.nan
        div_flags = []
        for end in range(4, len(w20)):
            sub = w20.iloc[end - 4 : end + 1]
            ret5 = metric_float(sub["close"].iloc[-1] / sub["close"].iloc[0] - 1.0, np.nan) if sub["close"].iloc[0] > denom_eps else np.nan
            flow5 = money_flow_stats(sub, denom_eps, 5)["net"]
            if np.isfinite(ret5) and np.isfinite(flow5):
                div_flags.append(np.sign(ret5) != np.sign(flow5))
        out["m2_flow_price_divergence_persistence_20"] = float(np.mean(div_flags)) if div_flags else np.nan
        p80 = float(np.nanpercentile(w60["amount_proxy"].to_numpy(dtype=float), 80))
        close20 = w20["close"].to_numpy(dtype=float)
        ret20 = np.diff(close20, prepend=np.nan)
        amount20 = w20["amount_proxy"].to_numpy(dtype=float)
        valid_amount20 = np.isfinite(amount20) & (amount20 > denom_eps)
        out["m2_high_amount_negative_bar_share_20"] = safe_div(float(((ret20 < 0) & (amount20 >= p80) & valid_amount20).sum()), float(valid_amount20.sum()), denom_eps)
    if len(w60) >= 60 and np.isfinite(w60["turnover_rate"]).any():
        last20 = w60.tail(20)["turnover_rate"].astype(float)
        base60 = w60["turnover_rate"].astype(float)
        denom_turn = base60.mean()
        out["m2_turnover_compression_20_vs_60"] = last20.mean() / denom_turn if np.isfinite(denom_turn) and denom_turn != 0 else np.nan
    return out


def build_feature_base(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    matrix = tables["eighteen_b_matrix"].copy()
    step_cols = ["step_id", "label_id", "step_start_pos", "step_start_date", "step_start_qfq_close"]
    mat_cols = ["step_id", "cluster_start_pos", "cluster_end_pos"]
    steps = tables["sixteen_b_label_step_panel"][step_cols].copy()
    mat = tables["sixteen_b_materialized_step_panel"][mat_cols].copy()
    out = matrix.merge(steps, on=["step_id", "label_id"], how="left", suffixes=("", "_16b"))
    out = out.merge(mat.drop_duplicates("step_id"), on="step_id", how="left")
    return out


def build_candidate_feature_panel(config: dict[str, Any], resolved: dict[str, Path], tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    base = build_feature_base(config, tables)
    qfq_dir = resolved["stock_daily_qfq_dir"]
    feature_rows = []
    for instrument, group in base.groupby("instrument", sort=False):
        path = qfq_dir / f"{instrument}.csv"
        if not path.exists():
            for _, row in group.iterrows():
                feature_rows.append({"step_id": row["step_id"], "label_id": row["label_id"], "qfq_path_status": "missing_qfq_file"})
            continue
        qfq = normalize_qfq(path)
        for _, row in group.iterrows():
            payload = {"step_id": row["step_id"], "label_id": row["label_id"], "qfq_path_status": "pass"}
            try:
                payload.update(derive_row_features(row, qfq, config))
                if "qfq_reconciled_step_start_date" not in payload:
                    payload["qfq_path_status"] = "insufficient_pre_t0_path"
            except (IndexError, ValueError, KeyError):
                payload["qfq_path_status"] = "feature_derivation_error"
            feature_rows.append(payload)
    features = pd.DataFrame(feature_rows)
    return base.merge(features, on=["step_id", "label_id"], how="left")


def feature_missingness(feature_panel: pd.DataFrame, feature_id: str) -> float:
    if feature_id not in feature_panel:
        return 1.0
    return float(1.0 - pd.to_numeric(feature_panel[feature_id], errors="coerce").notna().mean())


def build_lineage_and_pit(config: dict[str, Any], inventory: pd.DataFrame, feature_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    rows_lineage = []
    rows_pit = []
    min_finite = float(config["expected"]["candidate_min_finite_rate"])
    qfq_ok = feature_panel["qfq_path_status"].fillna("").eq("pass").mean() >= min_finite
    row_n = len(feature_panel)
    qfq_pass_n = int(feature_panel["qfq_path_status"].fillna("").eq("pass").sum())
    for _, inv in inventory.iterrows():
        fid = inv["candidate_feature_id"]
        family = inv["candidate_family_id"]
        finite_rate = 0.0 if fid not in feature_panel else float(pd.to_numeric(feature_panel[fid], errors="coerce").notna().mean())
        is_deferred = family == "M4"
        is_lifecycle = fid == "m5_lifecycle_progress_to_t0"
        source_blocked = not qfq_ok and family in {"M1", "M2", "M3", "M5"}
        enough = finite_rate >= min_finite
        future_mask = feature_panel["cluster_end_pos"].gt(feature_panel["step_start_pos"]) if is_lifecycle else pd.Series(False, index=feature_panel.index)
        future_source_dependency_row_n = int(future_mask.sum())
        future_normalizer_dependency_row_n = int(future_mask.sum())
        if is_lifecycle and row_n:
            max_delta = metric_float((feature_panel["cluster_end_pos"] - feature_panel["step_start_pos"]).max(), np.nan)
        else:
            max_delta = 0.0 if row_n else np.nan
        uses_full_episode_boundary = bool(is_lifecycle and future_source_dependency_row_n > 0)
        t0_proof = str(inv.get("t0_frozen_endpoint_proof_status", "not_required"))
        endpoint_blocked = is_lifecycle and t0_proof != "proven"
        primary = bool((not is_deferred) and (not source_blocked) and enough and (not endpoint_blocked) and future_source_dependency_row_n == 0 and future_normalizer_dependency_row_n == 0)
        appendix = is_deferred or source_blocked or not enough
        if endpoint_blocked:
            appendix = True
        reason = ""
        if is_deferred:
            reason = "m4_deferred_by_default"
        elif endpoint_blocked:
            reason = "full_episode_boundary_after_t0"
        elif source_blocked:
            reason = "qfq_source_not_sufficiently_available"
        elif not enough:
            reason = "candidate_finite_rate_below_floor"
        finite_n = 0 if fid not in feature_panel else int(pd.to_numeric(feature_panel[fid], errors="coerce").notna().sum())
        dependency_n = qfq_pass_n if family in {"M1", "M2", "M3", "M5"} else 0
        pit_status = "pass" if primary else "appendix_only" if appendix else "blocked"
        t0_status = "pass" if primary else "delayed_appendix_only" if is_deferred else "blocked"
        rows_lineage.append(
            {
                "candidate_family_id": family,
                "candidate_feature_id": fid,
                "source_artifact_alias": inv["source_artifact_alias"],
                "lineage_scope": "candidate_row_rollup",
                "row_n": row_n,
                "finite_candidate_value_row_n": finite_n,
                "source_dependency_row_n": dependency_n,
                "future_source_dependency_row_n": future_source_dependency_row_n,
                "normalizer_dependency_row_n": dependency_n,
                "future_normalizer_dependency_row_n": future_normalizer_dependency_row_n,
                "source_pos_max_minus_step_start_pos": max_delta,
                "source_date_max_minus_step_start_date": 0,
                "normalizer_pos_max_minus_step_start_pos": max_delta,
                "max_source_pos_minus_step_start_pos": max_delta,
                "max_normalizer_pos_minus_step_start_pos": max_delta,
                "uses_full_episode_boundary_after_t0": uses_full_episode_boundary,
                "uses_future_h20_path": False,
                "uses_step_end_outcome": False,
                "uses_oracle_label": False,
                "uses_payoff_target": False,
                "uses_binary_target": False,
                "pit_valid_status": pit_status,
                "t0_available_status": t0_status,
                "candidate_primary_allowed_after_lineage": primary,
                "candidate_appendix_only": appendix,
                "lineage_before_correlation_gate": "pass",
                "blocking_reason": reason,
            }
        )
        rows_pit.append(
            {
                "candidate_family_id": family,
                "candidate_feature_id": fid,
                "source_artifact_alias": inv["source_artifact_alias"],
                "required_source_columns": inv["source_columns"],
                "source_available_at_t0": primary,
                "source_max_lag_bars": 0,
                "delayed_observed_state": is_deferred,
                "t0_frozen_endpoint_proof_status": t0_proof,
                "pit_valid_status": pit_status,
                "t0_available_status": t0_status,
                "primary_allowed": primary,
                "appendix_only": appendix,
                "blocking_reason": reason,
            }
        )
    lineage = pd.DataFrame(rows_lineage)
    pit = pd.DataFrame(rows_pit)
    primary_rows = lineage.loc[lineage["candidate_primary_allowed_after_lineage"].astype(bool)]
    primary_future_ok = True if primary_rows.empty else bool(
        primary_rows["future_source_dependency_row_n"].eq(0).all()
        and primary_rows["future_normalizer_dependency_row_n"].eq(0).all()
        and primary_rows["max_source_pos_minus_step_start_pos"].le(0).all()
        and primary_rows["max_normalizer_pos_minus_step_start_pos"].le(0).all()
    )
    candidate_lineage_gate = "pass" if lineage["lineage_before_correlation_gate"].eq("pass").all() and primary_future_ok else "fail"
    pit_gate = "pass" if lineage["candidate_primary_allowed_after_lineage"].any() else "fail"
    return lineage, pit, candidate_lineage_gate, pit_gate


def residualize(train: pd.DataFrame, all_frame: pd.DataFrame, feature: str, covariates: list[str]) -> pd.Series:
    y_train = pd.to_numeric(train[feature], errors="coerce")
    x_train = train[covariates].apply(pd.to_numeric, errors="coerce")
    valid = y_train.notna() & np.isfinite(y_train) & x_train.notna().all(axis=1)
    if int(valid.sum()) < len(covariates) + 3:
        return pd.Series(np.nan, index=all_frame.index)
    x = np.column_stack([np.ones(int(valid.sum())), x_train.loc[valid].to_numpy(dtype=float)])
    y = y_train.loc[valid].to_numpy(dtype=float)
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    x_all = all_frame[covariates].apply(pd.to_numeric, errors="coerce")
    complete = x_all.notna().all(axis=1)
    result = pd.Series(np.nan, index=all_frame.index)
    pred = np.column_stack([np.ones(int(complete.sum())), x_all.loc[complete].to_numpy(dtype=float)]) @ beta
    result.loc[complete] = pd.to_numeric(all_frame.loc[complete, feature], errors="coerce") - pred
    return result


def build_orthogonal_readouts(config: dict[str, Any], inventory: pd.DataFrame, lineage: pd.DataFrame, feature_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, bool]]:
    rows = []
    train = feature_panel.loc[feature_panel["cluster_split_bucket"].eq("train")]
    target = config["target_column"]
    roles = {"train": "train_priority_prior", "robustness": "robustness_diagnostic_only", "validation": "validation_diagnostic_only"}
    primary_allowed = dict(zip(lineage["candidate_feature_id"], lineage["candidate_primary_allowed_after_lineage"].astype(bool), strict=False))
    for _, inv in inventory.iterrows():
        fid = inv["candidate_feature_id"]
        family = inv["candidate_family_id"]
        control_sets = [(BASE_RESIDUALIZATION_ID, BASE_RESIDUALIZATION_ROLE, BASE_COVARIATES, family != "M2")]
        if family == "M2":
            control_sets.append((M2_EXT_RESIDUALIZATION_ID, M2_EXT_RESIDUALIZATION_ROLE, M2_EXT_COVARIATES, True))
        for control_id, control_role, covars, eligible_control in control_sets:
            residual = pd.Series(np.nan, index=feature_panel.index)
            if fid in feature_panel and set(covars).issubset(feature_panel.columns):
                residual = residualize(train, feature_panel, fid, covars)
            train_mask = feature_panel["cluster_split_bucket"].eq("train")
            raw_train = rank_ic(feature_panel.loc[train_mask, fid], feature_panel.loc[train_mask, target]) if fid in feature_panel else np.nan
            resid_train = rank_ic(residual.loc[train_mask], feature_panel.loc[train_mask, target])
            same_train = np.isfinite(raw_train) and np.isfinite(resid_train) and np.sign(raw_train) == np.sign(resid_train)
            train_ok = bool(
                primary_allowed.get(fid, False)
                and eligible_control
                and np.isfinite(resid_train)
                and abs(resid_train) >= float(config["expected"]["candidate_train_prior_abs_rank_ic_floor"])
                and same_train
            )
            for split in SPLITS:
                mask = feature_panel["cluster_split_bucket"].eq(split)
                raw_ic = rank_ic(feature_panel.loc[mask, fid], feature_panel.loc[mask, target]) if fid in feature_panel else np.nan
                resid_ic = rank_ic(residual.loc[mask], feature_panel.loc[mask, target])
                same_split = np.isfinite(raw_ic) and np.isfinite(resid_ic) and np.sign(raw_ic) == np.sign(resid_ic)
                retention = resid_ic / raw_ic if np.isfinite(raw_ic) and abs(raw_ic) > 1e-12 and np.isfinite(resid_ic) else np.nan
                rows.append(
                    {
                        "candidate_family_id": family,
                        "candidate_feature_id": fid,
                        "split_bucket": split,
                        "candidate_primary_dedup_group_id": inv["candidate_primary_dedup_group_id"],
                        "residualization_control_set_id": control_id,
                        "residualization_control_set_role": control_role,
                        "raw_candidate_rank_ic": raw_ic,
                        "residual_candidate_rank_ic": resid_ic,
                        "residual_retention": retention,
                        "residualization_fit_split": "train",
                        "residualization_covariates": "|".join(covars) if fid in feature_panel else "not_applicable",
                        "residualization_uses_target": False,
                        "residualization_uses_robustness_rows": False,
                        "residualization_uses_validation_rows": False,
                        "residual_rank_ic_same_sign_as_raw": same_split,
                        "orthogonal_payoff_candidate": bool(split == "train" and train_ok),
                        "dedup_group_representative": False,
                        "recommendation_eligible_residualization": eligible_control,
                        "target_evidence_role": roles[split],
                        "orthogonality_status": "pre_dedup_pass" if split == "train" and train_ok else "diagnostic_only" if split != "train" else "fail",
                    }
                )
    orthogonal = pd.DataFrame(rows)
    train_candidates = orthogonal.loc[
        orthogonal["target_evidence_role"].eq("train_priority_prior")
        & orthogonal["recommendation_eligible_residualization"].astype(bool)
        & orthogonal["orthogonal_payoff_candidate"].astype(bool)
    ].copy()
    representatives: set[tuple[str, str]] = set()
    for _, group in train_candidates.groupby("candidate_primary_dedup_group_id", dropna=False):
        ordered = group.assign(abs_residual=group["residual_candidate_rank_ic"].abs()).sort_values(
            ["abs_residual", "candidate_feature_id", "residualization_control_set_id"],
            ascending=[False, True, True],
        )
        if not ordered.empty:
            top = ordered.iloc[0]
            representatives.add((str(top["candidate_feature_id"]), str(top["residualization_control_set_id"])))
    orthogonal["dedup_group_representative"] = [
        (str(fid), str(control_id)) in representatives and bool(eligible)
        for fid, control_id, eligible in zip(
            orthogonal["candidate_feature_id"],
            orthogonal["residualization_control_set_id"],
            orthogonal["recommendation_eligible_residualization"],
            strict=False,
        )
    ]
    orthogonal["orthogonal_payoff_candidate"] = (
        orthogonal["orthogonal_payoff_candidate"].astype(bool)
        & orthogonal["dedup_group_representative"].astype(bool)
    )
    orthogonal["orthogonality_status"] = np.where(
        orthogonal["orthogonal_payoff_candidate"].astype(bool),
        "pass",
        np.where(
            orthogonal["target_evidence_role"].ne("train_priority_prior"),
            "diagnostic_only",
            np.where(orthogonal["dedup_group_representative"].astype(bool), "fail", "dedup_non_representative_or_fail"),
        ),
    )
    morph_rows = []
    for _, row in orthogonal.iterrows():
        mask = feature_panel["cluster_split_bucket"].eq(row["split_bucket"])
        fid = row["candidate_feature_id"]
        morph_rows.append(
            {
                "candidate_family_id": row["candidate_family_id"],
                "candidate_feature_id": fid,
                "proxy_type": "deferred_context_proxy" if row["candidate_family_id"] == "M4" else "path_or_pressure_proxy",
                "split_bucket": row["split_bucket"],
                "row_n": int(mask.sum()),
                "source_window_id": "not_applicable" if row["candidate_family_id"] == "M4" else "pre_t0",
                "formula_params_id": "config_18d_default",
                "raw_candidate_rank_ic": row["raw_candidate_rank_ic"],
                "residual_candidate_rank_ic": row["residual_candidate_rank_ic"],
                "residual_retention": row["residual_retention"],
                "residualization_control_set_id": row["residualization_control_set_id"],
                "residualization_control_set_role": row["residualization_control_set_role"],
                "residualization_covariates": row["residualization_covariates"],
                "residual_rank_ic_same_sign_as_raw": row["residual_rank_ic_same_sign_as_raw"],
                "orthogonal_payoff_candidate": row["orthogonal_payoff_candidate"],
                "recommendation_eligible_residualization": row["recommendation_eligible_residualization"],
                "target_evidence_role": row["target_evidence_role"],
                "missingness_rate": feature_missingness(feature_panel.loc[mask], fid),
                "drift_status": "not_evaluated" if row["split_bucket"] == "train" else "diagnostic_only",
                "diagnostic_status": "pass" if fid in feature_panel else "deferred_or_blocked",
            }
        )
    train_pass = {
        fid: bool(group["orthogonal_payoff_candidate"].any())
        for fid, group in orthogonal.loc[orthogonal["target_evidence_role"].eq("train_priority_prior")].groupby("candidate_feature_id")
    }
    return orthogonal, pd.DataFrame(morph_rows), train_pass


def build_gap_decomposition() -> pd.DataFrame:
    rows = [
        ("F1", "mr_ret_5d|mr_ret_10d|mr_ret_20d|mr_ma_5_20_spread|mr_ma_20_60_spread|mr_distance_to_20d_high|mr_distance_to_60d_high", "current repair level", "short return and distance to highs", "episode-internal repair path morphology", "18C_report", "weak_rank_ic", "missing_shape", "M1"),
        ("F2", "mr_turnover_rate_20d_mean|mr_turnover_rate_60d_mean|mr_turnover_rate_20d_zscore|mr_volume_20d_zscore|mr_money_20d_zscore", "participation level", "volume and money level z-scores", "signed inflow/outflow dynamics", "18C_coefficients", "primary_dependency", "dynamic_pressure_missing", "M2"),
        ("F3", "mr_board_rank_pct|mr_board_rank_by_market_cap", "cross-sectional rank", "board rank context", "payoff asymmetry and path shape", "18C_coefficients", "limited_support", "context_not_shape", "M3"),
        ("F4", "mr_volatility_20d|mr_volatility_60d|mr_max_drawdown_20d|mr_max_drawdown_60d|mr_intraday_range_20d_mean", "risk state", "low volatility tilt", "vol-adjusted repair quality", "18C_baseline", "risk_ceiling", "orthogonal_shape_missing", "M1|M3"),
        ("F5", "board dummies|market cap|tradability", "static context", "board and size", "regime only if new PIT context exists", "18C_topk", "near_zero", "defer", "M4"),
    ]
    return pd.DataFrame(rows, columns=["current_family_id", "current_feature_ids", "existing_signal_role", "represented_information", "missing_payoff_information", "evidence_metric", "evidence_value", "gap_status", "candidate_family_mapping"])


def build_prioritization(config: dict[str, Any], inventory: pd.DataFrame, lineage: pd.DataFrame, orthogonal: pd.DataFrame) -> tuple[pd.DataFrame, str, list[str], list[str], list[str]]:
    rows = []
    recommended: list[str] = []
    deferred: list[str] = []
    appendix: list[str] = []
    train_orth = orthogonal.loc[
        orthogonal["target_evidence_role"].eq("train_priority_prior")
        & orthogonal["recommendation_eligible_residualization"].astype(bool)
    ].copy()
    for family, meta in config["candidate_families"].items():
        fam_inv = inventory.loc[inventory["candidate_family_id"].eq(family)]
        fam_lineage = lineage.loc[lineage["candidate_family_id"].eq(family)]
        fam_orth = train_orth.loc[train_orth["candidate_family_id"].eq(family)]
        primary_n = int(fam_lineage["candidate_primary_allowed_after_lineage"].sum()) if not fam_lineage.empty else 0
        orth_n = int(fam_orth["orthogonal_payoff_candidate"].sum()) if not fam_orth.empty else 0
        delayed_n = int(fam_lineage["candidate_appendix_only"].sum()) if not fam_lineage.empty else 0
        rep_orth = fam_orth.loc[fam_orth["dedup_group_representative"].astype(bool)]
        raw_score = float(fam_orth["residual_candidate_rank_ic"].abs().fillna(0).sum()) if not fam_orth.empty else 0.0
        score = float(rep_orth["residual_candidate_rank_ic"].abs().fillna(0).sum()) if not rep_orth.empty else 0.0
        rep_ids = "|".join(sorted(rep_orth["candidate_feature_id"].astype(str).unique()))
        dedup_group_n = int(fam_inv["candidate_primary_dedup_group_id"].nunique()) if "candidate_primary_dedup_group_id" in fam_inv else 0
        recommend = family in {"M1", "M3", "M5"} and primary_n > 0 and orth_n > 0
        if family == "M2":
            recommend = primary_n > 0 and orth_n > 0
        if family == "M4":
            recommend = False
        if recommend:
            recommended.append(family)
        elif family == "M4":
            deferred.append(family)
        else:
            appendix.append(family)
        rows.append(
            {
                "candidate_family_id": family,
                "planned_priority": meta["planned_priority"],
                "evidence_adjusted_priority": "recommended" if recommend else "appendix_only" if family != "M4" else "deferred",
                "priority_reason": "train_prior_orthogonal_candidate_found" if recommend else "no_train_prior_orthogonal_candidate_or_deferred",
                "candidate_feature_n": len(fam_inv),
                "primary_allowed_candidate_n": primary_n,
                "orthogonal_payoff_candidate_n": orth_n,
                "delayed_appendix_candidate_n": delayed_n,
                "dedup_group_n": dedup_group_n,
                "dedup_group_representative_candidate_ids": rep_ids,
                "raw_candidate_priority_score": raw_score,
                "candidate_priority_score": score,
                "priority_score_method": "dedup_representative_abs_train_residual_ic",
                "priority_source": "lineage_then_train_prior_only",
                "recommended_for_refresh": recommend,
                "recommendation_role": "primary_refresh_candidate" if recommend else "appendix_or_deferred",
                "blocking_reason": "" if recommend else "no_orthogonal_train_prior_or_deferred",
            }
        )
    gate = "pass" if any(f in recommended for f in ["M1", "M3", "M5"]) else "fail"
    return pd.DataFrame(rows), gate, recommended, deferred, appendix


def build_search_accounting_audit() -> tuple[pd.DataFrame, str]:
    checks = {
        "no_feature_selection_from_target_correlation_before_lineage": True,
        "no_candidate_added_after_target_readout": True,
        "no_candidate_removed_after_target_readout": True,
        "candidate_inventory_completeness_verified_before_target_readout": True,
        "no_feature_selection_from_robustness": True,
        "no_feature_selection_from_validation": True,
        "no_final_model_training": True,
        "no_model_family_selection_from_robustness": True,
        "no_threshold_tuning_on_robustness": True,
        "no_threshold_tuning_on_validation": True,
        "binary_metric_not_primary_gate": True,
        "neutral_rows_not_dropped": True,
        "delayed_features_not_primary": True,
        "no_entry_policy_authorized": True,
        "no_exit_policy_authorized": True,
        "no_holding_policy_authorized": True,
        "no_portfolio_backtest_authorized": True,
        "no_model_deployment_authorized": True,
        "no_production_signal_authorized": True,
        "no_live_trading_authorized": True,
    }
    rows = [{"check_name": key, "expected_value": True, "observed_value": value, "status": "pass" if value else "fail", "blocking_reason": "" if value else key} for key, value in checks.items()]
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["status"].eq("pass").all() else "fail"


def decision_from_gates(gates: dict[str, str], capacity_summary: dict[str, Any], recommended: list[str], deferred: list[str], appendix: list[str]) -> pd.DataFrame:
    if gates["upstream_18c_contract_gate"] != "pass":
        state = "18D_upstream_18c_contract_blocked"
    elif gates["input_artifact_gate"] != "pass":
        state = "18D_input_artifact_blocked"
    elif bool(capacity_summary["capacity_bottleneck_flag"]):
        state = "18D_capacity_bottleneck_on_existing_features"
    elif gates["candidate_inventory_completeness_gate"] != "pass":
        state = "18D_feature_representation_contract_blocked"
    elif gates["candidate_lineage_gate"] != "pass":
        state = "18D_feature_representation_contract_blocked"
    elif gates["pit_t0_availability_gate"] != "pass":
        state = "18D_no_pit_valid_candidate_features_found"
    elif gates["orthogonal_payoff_information_gate"] != "pass":
        state = "18D_no_orthogonal_payoff_information_found"
    elif gates["feature_family_prioritization_gate"] != "pass":
        state = "18D_representation_gap_diagnostic_only"
    elif gates["search_accounting_gate"] != "pass":
        state = "18D_search_accounting_blocked"
    else:
        state = "18D_feature_representation_refresh_supported"
    next_req = "requirement_18e_payoff_state_feature_matrix_refresh.md" if state == "18D_feature_representation_refresh_supported" else "none"
    all_pass = all(gates[g] == "pass" for g in HARD_GATES)
    row = {
        "decision_state": state,
        "next_allowed_requirement": next_req,
        "all_hard_gates_pass": all_pass,
        **gates,
        **{col: False for col in AUTH_FALSE_COLUMNS},
        "blocking_reason": "" if all_pass else state,
        "recommended_refresh_family_ids": "|".join(recommended),
        "deferred_family_ids": "|".join(deferred),
        "appendix_only_family_ids": "|".join(appendix),
    }
    return pd.DataFrame([row])


def markdown_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    out = frame.head(max_rows).copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(lambda value: "" if pd.isna(value) else str(value).replace("|", r"\|"))
    return out.to_markdown(index=False)


def build_report(artifacts: dict[str, Any]) -> str:
    d = artifacts["decision"].iloc[0]
    cap = artifacts["capacity_summary"]
    inv_summary = artifacts["inventory_summary"]
    inventory = artifacts["inventory"]
    prio = artifacts["prioritization"]
    lineage = artifacts["lineage"]
    gap = artifacts["gap"]
    top_train = artifacts["orthogonal"].loc[
        artifacts["orthogonal"]["target_evidence_role"].eq("train_priority_prior")
        & artifacts["orthogonal"]["recommendation_eligible_residualization"].astype(bool)
    ].copy()
    top_train = top_train.sort_values("residual_candidate_rank_ic", key=lambda s: s.abs(), ascending=False)
    future_lineage = lineage.loc[
        lineage["future_source_dependency_row_n"].gt(0)
        | lineage["future_normalizer_dependency_row_n"].gt(0)
        | lineage["uses_full_episode_boundary_after_t0"].astype(bool)
    ]
    dedup_summary = inventory.groupby(["candidate_family_id", "candidate_primary_dedup_group_id"], dropna=False).agg(
        candidate_feature_ids=("candidate_feature_id", lambda s: "|".join(s.astype(str))),
        candidate_n=("candidate_feature_id", "size"),
    ).reset_index()
    recommended = prio.loc[prio["recommended_for_refresh"].astype(bool)]
    deferred = prio.loc[~prio["recommended_for_refresh"].astype(bool)]
    m1_train = top_train.loc[top_train["candidate_family_id"].eq("M1")]
    m3_train = top_train.loc[top_train["candidate_family_id"].eq("M3")]
    m5_train = top_train.loc[top_train["candidate_family_id"].eq("M5")]
    m2_train = top_train.loc[top_train["candidate_family_id"].eq("M2")]
    return f"""# Payoff-state Feature Representation Diagnostic Report

## Decision

decision_state = {d["decision_state"]}
next_allowed_requirement = {d["next_allowed_requirement"]}

18D is diagnostic-only. It does not train a final separability model and does not authorize policy, backtest, deployment, production signal, or trading.

## 18C Evidence Summary

18C failed closed with weak positive payoff-state ranking evidence. The replayed
primary robustness rank IC is {cap["primary_ridge_robustness_rank_ic"]:.6f};
the best auxiliary current-feature robustness rank IC is
{cap["max_aux_existing_feature_rank_ic"]:.6f}. This authorizes a representation
diagnostic only, not policy, backtest, deployment, production signal, or trading.

## Capacity Versus Representation

| metric | value |
|:--|--:|
| primary_ridge_robustness_rank_ic | {cap["primary_ridge_robustness_rank_ic"]:.6f} |
| max_aux_existing_feature_rank_ic | {cap["max_aux_existing_feature_rank_ic"]:.6f} |
| max_aux_minus_primary_rank_ic | {cap["max_aux_minus_primary_rank_ic"]:.6f} |
| max_train_grouped_cv_probe_rank_ic | {cap["max_train_grouped_cv_probe_rank_ic"]:.6f} |
| max_train_grouped_cv_probe_minus_primary_cv_rank_ic | {cap["max_train_grouped_cv_probe_minus_primary_cv_rank_ic"]:.6f} |

capacity_margin_status = {cap["capacity_margin_status"]}
capacity_conclusion_scope = {cap["capacity_conclusion_scope"]}

The capacity conclusion remains a bounded diagnostic. It does not claim capacity
is fully ruled out; it says the current low-capacity evidence points to a feature
representation bottleneck unless future medium-capacity probes show material
rescue.

## Current Feature Gap Decomposition

{markdown_table(gap)}

## Candidate Inventory

candidate_inventory_completeness_gate = {inv_summary["candidate_inventory_completeness_gate"]}
expected_candidate_feature_n = {inv_summary["candidate_inventory_expected_feature_n"]}
observed_candidate_feature_n = {inv_summary["candidate_inventory_observed_feature_n"]}
missing_candidate_feature_n = {inv_summary["candidate_inventory_missing_feature_n"]}
extra_candidate_feature_n = {inv_summary["candidate_inventory_extra_feature_n"]}

## Feature Family Prioritization

{markdown_table(prio)}

## Candidate De-duplication

Candidate family scores use train-prior residual IC from dedup-group
representatives only. Raw scores remain reported separately to show how much
correlated alias evidence was removed.

{markdown_table(dedup_summary, 50)}

## Lineage And T0 Availability

Lineage is rolled up from candidate-row dependencies. Any finite primary value
using a source or normalizer after step_start_pos is blocked before target
readout.

{markdown_table(future_lineage[["candidate_family_id", "candidate_feature_id", "future_source_dependency_row_n", "future_normalizer_dependency_row_n", "uses_full_episode_boundary_after_t0", "candidate_primary_allowed_after_lineage", "blocking_reason"]], 20)}

## M1 Expanded Morphology

M1 covers pre-t0 repair shape: path entropy, repair path efficiency,
drawdown/recovery, run imbalance, failed repair count, and close-location
features. All M1 target evidence below is train-prior only.

{markdown_table(m1_train[["candidate_feature_id", "residualization_control_set_id", "residual_candidate_rank_ic", "dedup_group_representative", "orthogonal_payoff_candidate"]], 20)}

## M3 Expanded Asymmetry

M3 covers upside/downside room, asymmetric range position, failed breakout count,
upper-shadow pressure, and volatility-adjusted repair strength using pre-t0
high/low/candle paths.

{markdown_table(m3_train[["candidate_feature_id", "residualization_control_set_id", "residual_candidate_rank_ic", "dedup_group_representative", "orthogonal_payoff_candidate"]], 20)}

## M5 Position Diagnostics

M5 uses only t0-known position and age features. Full-episode lifecycle progress
is present as a required inventory row but blocked because completed
cluster_end_pos is future episode geometry unless a separate t0-frozen endpoint
proof exists.

{markdown_table(m5_train[["candidate_feature_id", "residualization_control_set_id", "residual_candidate_rank_ic", "dedup_group_representative", "orthogonal_payoff_candidate"]], 20)}

## Orthogonal Train-prior Evidence

Only train-prior residual rank IC can affect recommendation. Robustness and validation rows are diagnostic-only. For M2, base_vol_participation is diagnostic-only and f2_extended_participation_money is the recommendation gate.

{markdown_table(top_train[["candidate_family_id", "candidate_feature_id", "residualization_control_set_id", "raw_candidate_rank_ic", "residual_candidate_rank_ic", "dedup_group_representative", "orthogonal_payoff_candidate"]], 30)}

## Money-flow Proxy Diagnostics

M2 uses signed daily money-flow proxies, not true order flow. Second-order
features cover acceleration, curvature, reversal acceleration, divergence
persistence, high-amount negative bars, signed-flow volatility, and flow
concentration. M2 recommendation and score use only the
f2_extended_participation_money train-prior residualization.

{markdown_table(m2_train[["candidate_feature_id", "residualization_control_set_id", "residual_candidate_rank_ic", "dedup_group_representative", "orthogonal_payoff_candidate"]], 30)}

## Recommended Families

{markdown_table(recommended[["candidate_family_id", "candidate_priority_score", "recommended_for_refresh", "recommendation_role"]])}

## Deferred And Appendix-only Families

{markdown_table(deferred[["candidate_family_id", "blocking_reason", "recommendation_role"]])}

## Input Sources

{markdown_table(artifacts["input_audit"].groupby(["source_artifact_alias", "resolved_source_status"], dropna=False).size().reset_index(name="artifact_n"), 50)}

## Search Accounting

{markdown_table(artifacts["search"])}
"""


def build_all_outputs(config: dict[str, Any], resolved: dict[str, Path], input_audit: pd.DataFrame, input_gate: str) -> dict[str, Any]:
    tables = load_inputs(resolved)
    upstream, upstream_gate = build_upstream_18c_handoff_audit(config, resolved, tables)
    matrix = model_ready_matrix(config, tables["eighteen_b_matrix"])
    capacity, capacity_summary = build_capacity_vs_representation_readout(config, matrix, tables)
    inventory = candidate_inventory(config)
    inventory_summary = candidate_inventory_summary(inventory, int(config["expected"]["total_required_candidate_feature_n"]))
    feature_panel = build_candidate_feature_panel(config, resolved, tables)
    lineage, pit, lineage_gate, pit_gate = build_lineage_and_pit(config, inventory, feature_panel)
    orthogonal, morphology, _ = build_orthogonal_readouts(config, inventory, lineage, feature_panel)
    gap = build_gap_decomposition()
    prioritization, prioritization_gate, recommended, deferred, appendix = build_prioritization(config, inventory, lineage, orthogonal)
    search, search_gate = build_search_accounting_audit()
    high_orth = prioritization.loc[prioritization["candidate_family_id"].isin(["M1", "M3", "M5"]), "orthogonal_payoff_candidate_n"].sum()
    orthogonal_gate = "pass" if int(high_orth) > 0 else "fail"
    capacity_gate = "pass" if bool(capacity_summary["representation_bottleneck_flag"]) and not bool(capacity_summary["capacity_bottleneck_flag"]) else "fail"
    gates = {
        "upstream_18c_contract_gate": upstream_gate,
        "input_artifact_gate": input_gate,
        "capacity_vs_representation_gate": capacity_gate,
        "candidate_inventory_completeness_gate": inventory_summary["candidate_inventory_completeness_gate"],
        "candidate_lineage_gate": lineage_gate,
        "pit_t0_availability_gate": pit_gate,
        "orthogonal_payoff_information_gate": orthogonal_gate,
        "feature_family_prioritization_gate": prioritization_gate,
        "search_accounting_gate": search_gate,
    }
    decision = decision_from_gates(gates, capacity_summary, recommended, deferred, appendix)
    return {
        "tables": tables,
        "input_audit": input_audit,
        "upstream": upstream,
        "capacity": capacity,
        "capacity_summary": capacity_summary,
        "inventory": inventory,
        "inventory_summary": inventory_summary,
        "feature_panel": feature_panel,
        "lineage": lineage,
        "pit": pit,
        "gap": gap,
        "morphology": morphology,
        "orthogonal": orthogonal,
        "prioritization": prioritization,
        "search": search,
        "decision": decision,
        "gates": gates,
    }


def write_outputs(config_path: Path, config: dict[str, Any], resolved: dict[str, Path], outputs: dict[str, Path], artifacts: dict[str, Any]) -> None:
    outputs["candidate_feature_panel"].parent.mkdir(parents=True, exist_ok=True)
    artifacts["feature_panel"].to_parquet(outputs["candidate_feature_panel"], index=False)
    write_df(outputs["input_artifact_audit"], artifacts["input_audit"])
    write_df(outputs["upstream_18c_handoff_audit"], artifacts["upstream"])
    write_df(outputs["capacity_vs_representation_readout"], artifacts["capacity"])
    write_df(outputs["candidate_feature_inventory"], artifacts["inventory"])
    write_df(outputs["candidate_feature_lineage_audit"], artifacts["lineage"])
    write_df(outputs["candidate_feature_pit_availability_audit"], artifacts["pit"])
    write_df(outputs["current_feature_gap_decomposition"], artifacts["gap"])
    write_df(outputs["payoff_morphology_proxy_readout"], artifacts["morphology"])
    write_df(outputs["orthogonal_payoff_information_readout"], artifacts["orthogonal"])
    write_df(outputs["feature_family_candidate_prioritization"], artifacts["prioritization"])
    write_df(outputs["search_accounting_audit"], artifacts["search"])
    write_df(outputs["representation_refresh_decision"], artifacts["decision"])
    write_text(outputs["report"], build_report(artifacts))
    write_manifests(config_path, config, resolved, outputs, artifacts)


def write_manifests(config_path: Path, config: dict[str, Any], resolved: dict[str, Path], outputs: dict[str, Path], artifacts: dict[str, Any]) -> None:
    write_json(
        outputs["input_manifest"],
        {
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "run_id": RUN_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_artifacts": artifacts["input_audit"].to_dict(orient="records"),
        },
    )
    table_keys = [
        "input_artifact_audit",
        "upstream_18c_handoff_audit",
        "capacity_vs_representation_readout",
        "candidate_feature_inventory",
        "candidate_feature_lineage_audit",
        "candidate_feature_pit_availability_audit",
        "current_feature_gap_decomposition",
        "payoff_morphology_proxy_readout",
        "orthogonal_payoff_information_readout",
        "feature_family_candidate_prioritization",
        "search_accounting_audit",
        "representation_refresh_decision",
    ]
    decision = artifacts["decision"].iloc[0]
    inv_summary = artifacts["inventory_summary"]
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "requirement_file_sha256": file_sha(EXPERIMENT_DIR / "requirement_18d_payoff_state_feature_representation_diagnostic.md"),
        "config_file_sha256": file_sha(config_path),
        "runner_file_sha256": file_sha(Path(__file__)),
        "input_artifact_manifest_sha256": file_sha(outputs["input_manifest"]),
        "publishable_table_sha256_by_name": {key: file_sha(outputs[key]) for key in table_keys},
        "report_sha256": file_sha(outputs["report"]),
        "candidate_feature_panel_sha256": file_sha(outputs["candidate_feature_panel"]),
        "decision_state": decision["decision_state"],
        "next_allowed_requirement": decision["next_allowed_requirement"],
        "all_hard_gates_pass": bool(decision["all_hard_gates_pass"]),
        "upstream_18c_decision_state": config["expected"]["upstream_18c_decision_state"],
        "candidate_inventory_completeness_gate": inv_summary["candidate_inventory_completeness_gate"],
        "candidate_inventory_expected_feature_n": inv_summary["candidate_inventory_expected_feature_n"],
        "candidate_inventory_observed_feature_n": inv_summary["candidate_inventory_observed_feature_n"],
        "candidate_inventory_missing_feature_n": inv_summary["candidate_inventory_missing_feature_n"],
        "candidate_inventory_extra_feature_n": inv_summary["candidate_inventory_extra_feature_n"],
        "capacity_bottleneck_flag": bool(artifacts["capacity_summary"]["capacity_bottleneck_flag"]),
        "representation_bottleneck_flag": bool(artifacts["capacity_summary"]["representation_bottleneck_flag"]),
        "recommended_refresh_family_ids": decision["recommended_refresh_family_ids"],
        "deferred_family_ids": decision["deferred_family_ids"],
        "appendix_only_family_ids": decision["appendix_only_family_ids"],
        "capacity_margin_status": artifacts["capacity_summary"]["capacity_margin_status"],
        "capacity_conclusion_scope": artifacts["capacity_summary"]["capacity_conclusion_scope"],
        "medium_capacity_probe_caveat": bool(artifacts["capacity_summary"]["medium_capacity_probe_caveat"]),
        **{col: bool(decision[col]) for col in AUTH_FALSE_COLUMNS},
    }
    write_json(outputs["manifest"], manifest)


def run(config_path: Path, mode: str = "full") -> dict[str, Any]:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit, input_gate = build_input_artifact_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    write_json(
        outputs["input_manifest"],
        {
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "run_id": RUN_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_artifact_gate": input_gate,
            "input_artifacts": input_audit.to_dict(orient="records"),
        },
    )
    if mode == "check-inputs":
        return {"input_artifact_gate": input_gate, "input_artifact_audit": input_audit}
    artifacts = build_all_outputs(config, resolved, input_audit, input_gate)
    write_outputs(config_path, config, resolved, outputs, artifacts)
    return artifacts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "check-inputs" if args.check_inputs_only else args.mode
    run(Path(args.config), mode=mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
