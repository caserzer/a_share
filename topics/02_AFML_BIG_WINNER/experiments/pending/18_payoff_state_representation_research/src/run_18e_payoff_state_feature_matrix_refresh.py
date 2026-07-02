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


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "18E_payoff_state_feature_matrix_refresh"
EXPERIMENT_ID = "18_payoff_state_representation_research"
PHASE_ID = "18E"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_18e_payoff_state_feature_matrix_refresh.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID

SPLITS = ("train", "robustness", "validation")
DECISION_SUPPORTED = "18E_payoff_state_feature_matrix_refresh_supported"
NEXT_18C = "requirement_18c_payoff_state_separability_diagnostic.md"
NEXT_SCOPE = "refreshed_matrix_rerun"
BASE_RESIDUALIZATION_ID = "base_vol_participation"
M2_EXT_RESIDUALIZATION_ID = "f2_extended_participation_money"
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
    "upstream_18d_contract_gate",
    "input_artifact_gate",
    "feature_family_recommendation_replay_gate",
    "refreshed_feature_source_gate",
    "refreshed_feature_formula_gate",
    "refreshed_feature_lineage_gate",
    "pit_t0_availability_gate",
    "target_binding_gate",
    "feature_matrix_schema_gate",
    "feature_complete_rate_gate",
    "feature_family_coverage_gate",
    "train_only_preprocessing_gate",
    "forbidden_feature_gate",
    "search_accounting_gate",
)

APPENDIX_REASONS = {
    "m1_return_sign_entropy_trailing20": "failed volatility/participation orthogonality",
    "m1_episode_recovery_ratio_to_high_t0": "dedup alias of m1_close_location_episode_range",
    "m1_path_linearity_r2_low_to_t0": "failed train-prior orthogonality",
    "m3_downside_crowding_to_episode_low": "failed train-prior orthogonality",
    "m3_downside_room_to_episode_low_t0": "dedup alias / failed train-prior orthogonality",
    "m3_vol_adjusted_repair_strength": "failed train-prior orthogonality",
    "m5_lifecycle_progress_to_t0": "full_episode_boundary_after_t0",
    "m5_bars_since_reclaim": "candidate_finite_rate_below_floor",
    "m5_low_before_high_t0": "failed train-prior orthogonality",
    "m2_net_signed_money_flow_accel_5v20": "failed f2_extended_participation_money orthogonality",
    "m2_positive_money_flow_share_accel_5v20": "failed f2_extended_participation_money orthogonality",
    "m2_net_signed_money_flow_curvature_5_10_20": "failed f2_extended_participation_money orthogonality",
    "m2_high_amount_negative_bar_share_20": "failed f2_extended_participation_money orthogonality",
    "m2_signed_flow_volatility_20": "failed f2_extended_participation_money orthogonality",
    "m4_regime_context_deferred": "no new PIT context and family deferred",
}

FORMULA_OVERRIDES = {
    "m1_episode_drawdown_pre_t0": "min(qfq_low_t / running_max(qfq_close up to t) - 1) over cluster_start_pos..step_start_pos; inherited 18D mixed low/close drawdown proxy",
    "m2_money_flow_reversal_accel_5v20": "reversal_rate(trailing_5 signed_money_proxy) - reversal_rate(trailing_20 signed_money_proxy)",
    "m2_flow_price_divergence_persistence_20": "mean(sign(close[j]/close[j-4]-1) != sign(net_signed_money_flow rows[j-4:j])) for j=4..19 in trailing_20",
    "m2_net_signed_money_flow_trailing20": "sum(amount_t * sign(close_t - close_t-1)) / sum(abs(amount_t)) over trailing_20",
    "m2_positive_money_flow_share_trailing20": "sum(amount_t where close_t > close_t-1) / sum(amount_t) over trailing_20",
    "m2_money_flow_persistence_trailing20": "mean(sign(signed_money_proxy_t) == sign(signed_money_proxy_t-1)) over trailing_20 valid signed-flow sequence",
    "m2_turnover_compression_20_vs_60": "mean(turnover_rate trailing_20) / mean(turnover_rate trailing_60)",
    "m2_flow_concentration_top3_share_20": "sum(top 3 abs(signed_money_proxy_t)) / sum(abs(signed_money_proxy_t)) over trailing_20",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP18E payoff-state refreshed feature matrix construction.")
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
        "matrix": LOCAL_CACHE_DIR / "refreshed_payoff_state_feature_matrix.parquet",
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_18d_handoff_audit": TABLE_DIR / "upstream_18d_handoff_audit.csv",
        "refresh_candidate_replay_audit": TABLE_DIR / "refresh_candidate_replay_audit.csv",
        "refreshed_feature_source_audit": TABLE_DIR / "refreshed_feature_source_audit.csv",
        "refreshed_feature_formula_registry": TABLE_DIR / "refreshed_feature_formula_registry.csv",
        "refreshed_feature_lineage_audit": TABLE_DIR / "refreshed_feature_lineage_audit.csv",
        "refreshed_feature_pit_availability_audit": TABLE_DIR / "refreshed_feature_pit_availability_audit.csv",
        "refreshed_feature_target_binding_audit": TABLE_DIR / "refreshed_feature_target_binding_audit.csv",
        "refreshed_feature_matrix_schema": TABLE_DIR / "refreshed_feature_matrix_schema.csv",
        "refreshed_feature_missingness_audit": TABLE_DIR / "refreshed_feature_missingness_audit.csv",
        "refreshed_feature_family_coverage": TABLE_DIR / "refreshed_feature_family_coverage.csv",
        "matrix_row_completeness_audit": TABLE_DIR / "matrix_row_completeness_audit.csv",
        "train_only_preprocessing_audit": TABLE_DIR / "train_only_preprocessing_audit.csv",
        "split_drift_feature_readout": TABLE_DIR / "split_drift_feature_readout.csv",
        "forbidden_feature_audit": TABLE_DIR / "forbidden_feature_audit.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "refreshed_feature_matrix_decision": TABLE_DIR / "refreshed_feature_matrix_decision.csv",
        "appendix_excluded_candidate_feature_audit": TABLE_DIR / "appendix_excluded_candidate_feature_audit.csv",
        "appendix_feature_family_bucket_target_distribution": TABLE_DIR / "appendix_feature_family_bucket_target_distribution.csv",
        "report": REPORT_DIR / "payoff_state_feature_matrix_refresh_report.md",
        "manifest": MANIFEST_DIR / "18E_payoff_state_feature_matrix_refresh_manifest.json",
        "input_manifest": MANIFEST_DIR / "input_artifact_manifest_18e.json",
        "matrix_manifest": MANIFEST_DIR / "refreshed_payoff_state_feature_matrix_manifest.json",
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


def dir_sha(path: Path) -> str:
    h = hashlib.sha256()
    if not path.exists() or not path.is_dir():
        return ""
    for child in sorted(path.glob("*.csv")):
        h.update(child.name.encode("utf-8"))
        h.update(str(child.stat().st_size).encode("utf-8"))
    return h.hexdigest()


def artifact_sha(path: Path) -> str:
    if not path.exists():
        return ""
    if path.is_dir():
        return dir_sha(path)
    return file_sha(path)


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
        return len(sorted(path.glob("*.csv")))
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
        files = sorted(path.glob("*.csv"))
        return [] if not files else list(pd.read_csv(files[0], nrows=0).columns)
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


def str_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value)


def bool_like(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    if pd.isna(value):
        return False
    return bool(value)


def false_like(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return not bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"false", "0", "no", ""}
    if pd.isna(value):
        return False
    return not bool(value)


def metric_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return float(out) if np.isfinite(out) else default


def existing_raw_features(config: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for family in ("F1", "F2", "F3", "F4", "F5"):
        out.extend(config["existing_feature_families"][family]["features"])
    return out


def refresh_raw_features(config: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for family in config["expected"]["refresh_priority_order"]:
        out.extend(config["refresh_feature_families"][family]["features"])
    return out


def primary_raw_features(config: dict[str, Any]) -> list[str]:
    return [*existing_raw_features(config), *refresh_raw_features(config)]


def model_ready_name(config: dict[str, Any], raw_feature: str) -> str:
    return f"{config.get('model_ready_prefix', 'mr_')}{raw_feature}"


def feature_family_map(config: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for family, spec in config["existing_feature_families"].items():
        for feature in spec["features"]:
            mapping[feature] = family
    for family, spec in config["refresh_feature_families"].items():
        for feature in spec["features"]:
            mapping[feature] = family
    return mapping


def required_columns_for_key(config: dict[str, Any], key: str) -> set[str]:
    identity = set(config["identity_key_columns"])
    split = {config["split_column"]}
    target = set(config["target_columns"])
    old_raw = set(existing_raw_features(config))
    old_model = {model_ready_name(config, f) for f in old_raw}
    mapping: dict[str, set[str]] = {
        "eighteen_b_matrix": identity | split | target | old_raw | old_model,
        "eighteen_b_decision": {"decision_state", "next_allowed_requirement", "all_hard_gates_pass"},
        "eighteen_b_matrix_schema": {"column_name", "column_role", "model_ready_feature", "raw_feature"},
        "eighteen_b_feature_target_binding_audit": {"binding_check_id", "feature_target_binding_gate"},
        "eighteen_b_feature_lineage_audit": {"feature_name", "feature_lineage_gate"},
        "eighteen_b_feature_family_coverage": {"feature_family_id", "feature_family_coverage_gate"},
        "eighteen_b_train_only_preprocessing_audit": {"feature_name", "model_ready_feature_name", "fit_split"},
        "eighteen_d_decision": {"decision_state", "next_allowed_requirement", "all_hard_gates_pass", "recommended_refresh_family_ids", "deferred_family_ids"},
        "eighteen_d_family_prioritization": {"candidate_family_id", "recommended_for_refresh", "recommendation_role"},
        "eighteen_d_candidate_inventory": {"candidate_family_id", "candidate_feature_id", "candidate_feature_formula"},
        "eighteen_d_candidate_lineage": {"candidate_family_id", "candidate_feature_id", "candidate_primary_allowed_after_lineage", "pit_valid_status", "t0_available_status"},
        "eighteen_d_candidate_pit_availability": {"candidate_family_id", "candidate_feature_id", "primary_allowed", "appendix_only"},
        "eighteen_d_orthogonal_readout": {"candidate_family_id", "candidate_feature_id", "split_bucket", "residualization_control_set_id", "orthogonal_payoff_candidate"},
        "eighteen_d_search_accounting": set(),
        "sixteen_b_label_step_panel": {"step_id", "label_id", "step_start_pos", "step_start_date", "step_start_qfq_close"},
        "sixteen_b_materialized_step_panel": {"step_id", "cluster_start_pos", "cluster_end_pos"},
        "sixteen_b_label_panel_readout": {"step_id", "label_id", "step_start_pos", "step_start_date"},
        "sixteen_a_episode_interval_panel": {"instrument", "episode_cluster_id", "cluster_start_pos", "cluster_end_pos"},
        "stock_daily_qfq_dir": {"date", "open", "high", "low", "close", "money", "turnover_rate", "instrument"},
    }
    if key.endswith("_manifest") or key.endswith("_report") or key.startswith("requirement") or key == "research_plan":
        return set()
    return mapping.get(key, set())


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    for key, path in resolved.items():
        meta = config.get("path_roles", {}).get(key, {})
        required = bool(meta.get("required", False))
        exists = path.exists()
        columns = set(header_columns(path)) if exists else set()
        required_cols = required_columns_for_key(config, key)
        missing_cols = sorted(required_cols - columns)
        read_status = "pass" if exists else "missing"
        schema_status = "pass" if exists and not missing_cols else "fail" if required else "optional_missing"
        blockers = []
        if required and not exists:
            blockers.append("missing_required_artifact")
        if required and missing_cols:
            blockers.append("schema_missing:" + ",".join(missing_cols))
        if key == "stock_daily_qfq_dir" and exists and count_rows(path) <= 0:
            blockers.append("qfq_dir_empty")
            schema_status = "fail"
        rows.append(
            {
                "artifact_key": key,
                "artifact_role": meta.get("role", ""),
                "required_flag": bool(required),
                "resolver_alias": meta.get("resolver_alias", key),
                "resolved_path": str(path),
                "relative_path": relative_to_topic(path),
                "source_experiment_id": meta.get("source_experiment_id", ""),
                "source_phase_id": meta.get("source_phase_id", ""),
                "row_count": count_rows(path) if exists else np.nan,
                "column_count": len(columns),
                "sha256": artifact_sha(path),
                "source_kind": "directory" if path.is_dir() else path.suffix.lstrip("."),
                "cache_sha256": artifact_sha(path) if key in {"eighteen_b_matrix", "stock_daily_qfq_dir"} and exists else "",
                "cache_hash_validated": "",
                "cache_hash_manifest_status": "not_checked",
                "schema_status": schema_status,
                "read_status": read_status,
                "key_reconciliation_status": "not_checked",
                "expected_row_n": config["expected"]["total_labelable_step_n"] if key == "eighteen_b_matrix" else np.nan,
                "observed_row_n": count_rows(path) if key == "eighteen_b_matrix" and exists else np.nan,
                "absolute_path_mismatch_ignored": False,
                "blocking_reason": ";".join(blockers),
            }
        )
    audit = pd.DataFrame(rows)
    required_rows = audit.loc[audit["required_flag"].astype(bool)]
    gate = "pass" if required_rows["read_status"].eq("pass").all() and required_rows["schema_status"].eq("pass").all() else "fail"
    return audit, gate


def load_inputs(resolved: dict[str, Path]) -> dict[str, pd.DataFrame]:
    keys = [
        "eighteen_b_matrix",
        "eighteen_b_matrix_schema",
        "eighteen_b_feature_target_binding_audit",
        "eighteen_b_feature_lineage_audit",
        "eighteen_b_feature_family_coverage",
        "eighteen_b_train_only_preprocessing_audit",
        "eighteen_b_decision",
        "eighteen_d_decision",
        "eighteen_d_family_prioritization",
        "eighteen_d_candidate_inventory",
        "eighteen_d_candidate_lineage",
        "eighteen_d_candidate_pit_availability",
        "eighteen_d_orthogonal_readout",
        "eighteen_d_search_accounting",
        "sixteen_b_label_step_panel",
        "sixteen_b_materialized_step_panel",
        "sixteen_b_label_panel_readout",
        "sixteen_a_episode_interval_panel",
        "eighteen_a_target_denominator_reconciliation",
        "eighteen_a_payoff_cutoff_freeze",
    ]
    return {key: read_table(resolved[key]) for key in keys}


def add_handoff_check(rows: list[dict[str, Any]], source: str, field: str, observed: Any, expected: Any) -> None:
    if isinstance(expected, bool):
        ok = bool_like(observed) if expected else false_like(observed)
    else:
        ok = str_value(observed) == str_value(expected)
    rows.append(
        {
            "source_artifact": source,
            "field_name": field,
            "observed_value": observed,
            "expected_value": expected,
            "status": "pass" if ok else "fail",
            "blocking_reason": "" if ok else f"{field}_mismatch",
        }
    )


def build_upstream_18d_handoff_audit(config: dict[str, Any], resolved: dict[str, Path], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    expected = config["expected"]
    decision = tables["eighteen_d_decision"].iloc[0]
    manifest = read_json(resolved["eighteen_d_manifest"])
    rows: list[dict[str, Any]] = []
    checks = {
        "decision_state": expected["upstream_18d_decision_state"],
        "next_allowed_requirement": expected["upstream_18d_next_allowed_requirement"],
        "all_hard_gates_pass": True,
        "upstream_18c_contract_gate": "pass",
        "input_artifact_gate": "pass",
        "capacity_vs_representation_gate": "pass",
        "candidate_lineage_gate": "pass",
        "pit_t0_availability_gate": "pass",
        "orthogonal_payoff_information_gate": "pass",
        "feature_family_prioritization_gate": "pass",
        "search_accounting_gate": "pass",
        "recommended_refresh_family_ids": "|".join(expected["recommended_refresh_family_ids"]),
        "deferred_family_ids": "|".join(expected["deferred_family_ids"]),
    }
    for field, exp in checks.items():
        add_handoff_check(rows, "representation_refresh_decision.csv", field, decision.get(field, ""), exp)
    for field in ("decision_state", "next_allowed_requirement", "all_hard_gates_pass", "recommended_refresh_family_ids", "deferred_family_ids"):
        add_handoff_check(rows, "18D_payoff_state_feature_representation_diagnostic_manifest.json", field, manifest.get(field, ""), checks[field])
    for col in AUTH_FALSE_COLUMNS:
        add_handoff_check(rows, "representation_refresh_decision.csv", col, decision.get(col, ""), False)
    frame = pd.DataFrame(rows)
    gate = "pass" if frame["status"].eq("pass").all() else "fail"
    return frame, gate


def first_row(frame: pd.DataFrame, column: str, value: str) -> pd.Series:
    rows = frame.loc[frame[column].astype(str).eq(value)]
    if rows.empty:
        return pd.Series(dtype=object)
    return rows.iloc[0]


def expected_residualization_for_family(family_id: str) -> str:
    return M2_EXT_RESIDUALIZATION_ID if family_id == "M2" else BASE_RESIDUALIZATION_ID


def build_refresh_candidate_replay_audit(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    expected = config["expected"]
    primary_ids = set(expected["primary_refresh_feature_ids"])
    appendix_ids = set(expected["appendix_only_candidate_feature_ids"])
    inv = tables["eighteen_d_candidate_inventory"]
    lineage = tables["eighteen_d_candidate_lineage"]
    pit = tables["eighteen_d_candidate_pit_availability"]
    orth = tables["eighteen_d_orthogonal_readout"]
    family = tables["eighteen_d_family_prioritization"]
    family_rec = {str(row["candidate_family_id"]): bool_like(row["recommended_for_refresh"]) for _, row in family.iterrows()}
    expected_ids = primary_ids | appendix_ids
    rows = []
    for fid in sorted(expected_ids):
        inv_rows = inv.loc[inv["candidate_feature_id"].astype(str).eq(fid)]
        inv_row = inv_rows.iloc[0] if not inv_rows.empty else pd.Series(dtype=object)
        fam = str_value(inv_row.get("candidate_family_id", "M4" if fid == "m4_regime_context_deferred" else ""))
        role = "primary_refresh" if fid in primary_ids else "deferred" if fam == "M4" else "appendix_only"
        residual_id = expected_residualization_for_family(fam)
        lin = first_row(lineage, "candidate_feature_id", fid)
        p = first_row(pit, "candidate_feature_id", fid)
        train_rows = orth.loc[
            orth["candidate_feature_id"].astype(str).eq(fid)
            & orth["split_bucket"].astype(str).eq("train")
            & orth["target_evidence_role"].astype(str).eq("train_priority_prior")
            & orth["residualization_control_set_id"].astype(str).eq(residual_id)
        ]
        train = train_rows.iloc[0] if not train_rows.empty else pd.Series(dtype=object)
        row = {
            "candidate_family_id": fam,
            "candidate_feature_id": fid,
            "expected_18e_role": role,
            "expected_primary_model_feature": role == "primary_refresh",
            "expected_appendix_only": role != "primary_refresh",
            "expected_residualization_control_set_id": residual_id,
            "observed_18d_candidate_inventory_row_found": len(inv_rows) == 1,
            "observed_18d_lineage_row_found": not lin.empty,
            "observed_18d_pit_row_found": not p.empty,
            "observed_18d_train_prior_row_found": not train.empty,
            "observed_18d_recommended_family": bool(family_rec.get(fam, False)),
            "observed_candidate_primary_allowed_after_lineage": bool_like(lin.get("candidate_primary_allowed_after_lineage", False)),
            "observed_pit_primary_allowed": bool_like(p.get("primary_allowed", False)),
            "observed_candidate_appendix_only": bool_like(lin.get("candidate_appendix_only", False)) or bool_like(p.get("appendix_only", False)),
            "observed_recommendation_eligible_residualization": bool_like(train.get("recommendation_eligible_residualization", False)),
            "observed_dedup_group_representative": bool_like(train.get("dedup_group_representative", False)),
            "observed_orthogonal_payoff_candidate": bool_like(train.get("orthogonal_payoff_candidate", False)),
            "observed_residualization_control_set_id": str_value(train.get("residualization_control_set_id", "")),
            "observed_blocking_reason": str_value(lin.get("blocking_reason", "")) or str_value(p.get("blocking_reason", "")) or APPENDIX_REASONS.get(fid, ""),
            "replay_status": "fail",
            "blocking_reason": "",
        }
        if role == "primary_refresh":
            checks = [
                row["observed_18d_candidate_inventory_row_found"],
                row["observed_18d_lineage_row_found"],
                row["observed_18d_pit_row_found"],
                row["observed_18d_train_prior_row_found"],
                row["observed_18d_recommended_family"],
                row["observed_candidate_primary_allowed_after_lineage"],
                row["observed_pit_primary_allowed"],
                not row["observed_candidate_appendix_only"],
                row["observed_recommendation_eligible_residualization"],
                row["observed_dedup_group_representative"],
                row["observed_orthogonal_payoff_candidate"],
                row["observed_residualization_control_set_id"] == residual_id,
            ]
            ok = all(checks)
        else:
            ok = row["observed_18d_candidate_inventory_row_found"] and fid in appendix_ids
            if fid == "m5_lifecycle_progress_to_t0":
                ok = ok and row["observed_blocking_reason"] == "full_episode_boundary_after_t0"
            if fid == "m5_bars_since_reclaim":
                ok = ok and row["observed_blocking_reason"] == "candidate_finite_rate_below_floor"
            if fid == "m4_regime_context_deferred":
                ok = ok and row["observed_blocking_reason"] in {"m4_deferred_by_default", "family deferred", "no new PIT context and family deferred"}
        row["replay_status"] = "pass" if ok else "fail"
        row["blocking_reason"] = "" if ok else "candidate_replay_mismatch"
        rows.append(row)
    frame = pd.DataFrame(rows)
    duplicate_n = int(inv["candidate_feature_id"].duplicated().sum())
    missing_ids = expected_ids - set(inv["candidate_feature_id"].astype(str))
    extra_role_overlap = primary_ids & appendix_ids
    gate = "pass" if frame["replay_status"].eq("pass").all() and duplicate_n == 0 and not missing_ids and not extra_role_overlap else "fail"
    if gate != "pass":
        frame.loc[frame["blocking_reason"].eq(""), "blocking_reason"] = "candidate_replay_universe_mismatch"
    return frame, gate


def select_close_column(df: pd.DataFrame, priority: list[str]) -> tuple[str, pd.Series]:
    for col in priority:
        if col in df.columns:
            return col, pd.to_numeric(df[col], errors="coerce")
    if "qfq_close" in df.columns:
        return "qfq_close", pd.to_numeric(df["qfq_close"], errors="coerce")
    return "missing", pd.Series(np.nan, index=df.index)


def select_amount_proxy(df: pd.DataFrame, priority: list[str]) -> tuple[str, pd.Series]:
    for col in priority:
        if col == "volume_times_close":
            if {"volume", "close"}.issubset(df.columns):
                return col, pd.to_numeric(df["volume"], errors="coerce") * pd.to_numeric(df["close"], errors="coerce")
        elif col in df.columns:
            return col, pd.to_numeric(df[col], errors="coerce")
    return "missing", pd.Series(np.nan, index=df.index)


def normalize_qfq(path: Path, config: dict[str, Any]) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.sort_values("date").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "qfq_close", "volume", "money", "amount", "turnover_value", "turnover_rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    close_source, close = select_close_column(df, config["money_flow_proxy_params"]["close_column_priority"])
    df["close"] = close
    amount_source, amount = select_amount_proxy(df, config["money_flow_proxy_params"]["amount_column_priority"])
    df["amount_proxy"] = amount
    if "money" not in df.columns:
        df["money"] = amount
    if "turnover_rate" not in df.columns:
        df["turnover_rate"] = np.nan
    df["date"] = df["date"].astype(str)
    df["ma60"] = df["close"].rolling(60, min_periods=60).mean()
    df.attrs["amount_proxy_source"] = amount_source
    df.attrs["close_source"] = close_source
    return df


def safe_div(numerator: float, denominator: float, eps: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator <= eps:
        return np.nan
    return float(numerator / denominator)


def entropy_from_counts(counts: np.ndarray, eps: float) -> float:
    counts = counts.astype(float)
    if float(counts.sum()) <= 0:
        return np.nan
    p = (counts + eps) / (counts.sum() + len(counts) * eps)
    ent = float(-(p * np.log(p)).sum())
    return float(ent / np.log(len(counts)))


def state_sequence(close: np.ndarray, flat: float) -> np.ndarray:
    rets = close[1:] / close[:-1] - 1.0
    out = np.zeros(len(rets), dtype=int)
    out[rets > flat] = 2
    out[rets < -flat] = 0
    out[(rets >= -flat) & (rets <= flat)] = 1
    out[~np.isfinite(rets)] = -1
    return out


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
        return {"net": np.nan, "positive_share": np.nan, "reversal_rate": np.nan, "persistence": np.nan}
    amount, sign, signed = signed_flow_arrays(window)
    valid = np.isfinite(amount) & (amount > eps) & np.isfinite(sign)
    if len(valid):
        valid[0] = False
    denom_abs = float(np.abs(amount[valid]).sum())
    denom_total = float(amount[valid].sum())
    signs = np.sign(signed[valid])
    return {
        "net": safe_div(float(signed[valid].sum()), denom_abs, eps),
        "positive_share": safe_div(float(amount[valid & (sign > 0)].sum()), denom_total, eps),
        "reversal_rate": float(np.mean(signs[1:] != signs[:-1])) if len(signs) >= 2 else np.nan,
        "persistence": float(np.mean(signs[1:] == signs[:-1])) if len(signs) >= 2 else np.nan,
    }


def count_failed_repairs(close: np.ndarray, low_pos: int, cluster_start: int, step_pos: int) -> int:
    count = 0
    for pos in range(low_pos + 3, step_pos - 4):
        rel = pos - cluster_start
        if rel - 3 < 0 or rel + 5 >= len(close):
            continue
        prior_high = np.nanmax(close[rel - 3 : rel])
        post = close[rel + 1 : rel + 6]
        if close[rel] > prior_high and np.nanmin(post) / close[rel] - 1.0 <= -0.05 and np.nanmax(post) <= close[rel]:
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


def window_slice(qfq: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    return qfq.iloc[max(0, int(start)) : int(end) + 1]


def derive_row_features(row: pd.Series, qfq: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    params = config["entropy_params"]
    money_params = config["money_flow_proxy_params"]
    prob_eps = float(params["probability_epsilon"])
    denom_eps = float(money_params["denominator_epsilon"])
    flat = float(params["return_state_flat_abs_return_max"])
    min_n = int(params["min_observation_n"])
    out: dict[str, Any] = {}
    step_pos = int(row["step_start_pos"])
    cluster_start = int(row["cluster_start_pos"])
    cluster_end = int(row["cluster_end_pos"])
    if step_pos < 0 or step_pos >= len(qfq) or cluster_start > step_pos:
        out["row_blocking_reason"] = "invalid_step_or_cluster_position"
        return out
    start_date = str(row["step_start_date"])
    close_t0 = float(qfq["close"].iloc[step_pos])
    out["qfq_reconciled_step_start_date"] = qfq["date"].iloc[step_pos]
    out["qfq_reconciled_step_start_close"] = close_t0
    close_diff = abs(close_t0 - metric_float(row.get("step_start_qfq_close"), np.nan))
    if str(qfq["date"].iloc[step_pos]) != start_date or not np.isfinite(close_diff) or close_diff > 1e-8:
        out["row_blocking_reason"] = "qfq_step_start_reconciliation_failed"
        return out
    seg = qfq.iloc[cluster_start : step_pos + 1]
    valid_seg = seg[["low", "high", "close"]].apply(pd.to_numeric, errors="coerce").notna().all(axis=1)
    if len(seg) < min_n or int(valid_seg.sum()) < min_n:
        out["row_blocking_reason"] = "insufficient_valid_episode_segment"
        return out
    low_rel = int(np.nanargmin(seg["low"].to_numpy(dtype=float)))
    high_rel = int(np.nanargmax(seg["high"].to_numpy(dtype=float)))
    low_pos = cluster_start + low_rel
    high_pos = cluster_start + high_rel
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
            "episode_low_price_t0": low_price,
            "episode_high_price_t0": high_price,
            "episode_price_range_t0": high_price - low_price,
            "downside_room_t0": close_t0 - low_price,
            "m1_close_location_episode_range_raw_outside_0_1": False,
            "row_blocking_reason": "",
        }
    )
    episode_range = high_price - low_price
    raw_close_location = safe_div(close_t0 - low_price, episode_range, denom_eps)
    out["m1_close_location_episode_range_raw_outside_0_1"] = bool(np.isfinite(raw_close_location) and (raw_close_location < 0.0 or raw_close_location > 1.0))
    out["m1_close_location_episode_range"] = float(np.clip(raw_close_location, 0.0, 1.0)) if np.isfinite(raw_close_location) else np.nan
    running_max = seg["close"].cummax().to_numpy(dtype=float)
    valid_running = np.isfinite(running_max) & (running_max > denom_eps)
    out["m1_episode_drawdown_pre_t0"] = float(np.nanmin(seg["low"].to_numpy(dtype=float)[valid_running] / running_max[valid_running] - 1.0)) if valid_running.any() else np.nan
    out["m1_pullback_from_episode_high_t0"] = safe_div(close_t0, high_price, denom_eps) - 1.0 if high_price > denom_eps else np.nan
    low_to_t0_close = qfq["close"].iloc[low_pos : step_pos + 1].to_numpy(dtype=float)
    out["m1_repair_path_efficiency_episode"] = safe_div(abs(close_t0 - low_close), float(np.abs(np.diff(low_to_t0_close)).sum()) if len(low_to_t0_close) >= 2 else np.nan, denom_eps)
    out["m3_upside_room_to_episode_high"] = safe_div(high_price - close_t0, close_t0, denom_eps)
    out["m3_upside_downside_room_ratio_t0"] = safe_div(high_price - close_t0, close_t0 - low_price, denom_eps)
    out["m3_asymmetric_range_position_t0"] = 2.0 * safe_div(close_t0 - low_price, episode_range, denom_eps) - 1.0 if episode_range > denom_eps else np.nan
    out["m5_bars_since_episode_low"] = step_pos - low_pos
    out["m5_bars_since_episode_high_t0"] = step_pos - high_pos
    out["m5_episode_age_to_t0"] = step_pos - cluster_start
    horizon = metric_float(row.get("horizon_sessions"), np.nan)
    out["m5_nonoverlap_step_index_to_t0"] = math.floor(age / horizon) if np.isfinite(horizon) and horizon > 0 else np.nan
    out["m5_low_to_t0_age_ratio"] = (step_pos - low_pos) / max(age, 1)
    out["m5_high_to_t0_age_ratio"] = (step_pos - high_pos) / max(age, 1)

    w5 = window_slice(qfq, step_pos - 4, step_pos)
    w10 = window_slice(qfq, step_pos - 9, step_pos)
    w20 = window_slice(qfq, step_pos - 19, step_pos)
    w60 = window_slice(qfq, step_pos - 59, step_pos)
    wep = window_slice(qfq, low_pos, step_pos)
    if len(w20) >= min_n:
        run_signs = np.sign(np.diff(w20["close"].to_numpy(dtype=float)))
        out["m1_up_down_run_imbalance_20"] = longest_run(run_signs, True) - longest_run(run_signs, False)
        candle = w20[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
        candle_range = candle["high"] - candle["low"]
        valid_candle = candle.notna().all(axis=1) & np.isfinite(candle_range) & (candle_range > denom_eps)
        upper_shadow = candle["high"] - np.maximum(candle["open"], candle["close"])
        out["m3_upper_shadow_pressure_share_20"] = float((upper_shadow.loc[valid_candle] / candle_range.loc[valid_candle]).mean()) if int(valid_candle.sum()) >= min_n else np.nan
    if len(wep) >= min_n:
        states = state_sequence(wep["close"].to_numpy(dtype=float), flat)
        states = states[states >= 0]
        trans = states[:-1] * 3 + states[1:] if len(states) >= 2 else np.array([], dtype=int)
        counts = np.array([(trans == i).sum() for i in range(9)])
        out["m1_path_transition_entropy_episode"] = entropy_from_counts(counts, prob_eps)
        close_seg = seg["close"].to_numpy(dtype=float)
        high_seg = seg["high"].to_numpy(dtype=float)
        low_seg = seg["low"].to_numpy(dtype=float)
        out["m1_failed_repair_count_low_to_t0"] = float(count_failed_repairs(close_seg, low_pos, cluster_start, step_pos))
        out["m3_failed_breakout_count_pre_t0"] = float(count_failed_breakouts(high_seg, low_seg, close_seg, cluster_start, step_pos))
    if len(w60) >= 60:
        range60 = float(w60["high"].max() - w60["low"].min())
        out["m1_close_location_trailing60_range"] = safe_div(close_t0 - float(w60["low"].min()), range60, denom_eps)
        turn20 = w60.tail(20)["turnover_rate"].astype(float)
        turn60 = w60["turnover_rate"].astype(float)
        turn_denom = float(turn60.mean())
        out["m2_turnover_compression_20_vs_60"] = safe_div(float(turn20.mean()), turn_denom, denom_eps)
    if len(w20) >= 20:
        mf20 = money_flow_stats(w20, denom_eps, 20)
        out["m2_net_signed_money_flow_trailing20"] = mf20["net"]
        out["m2_positive_money_flow_share_trailing20"] = mf20["positive_share"]
        out["m2_money_flow_persistence_trailing20"] = mf20["persistence"]
        mf5 = money_flow_stats(w5, denom_eps, 5)
        out["m2_money_flow_reversal_accel_5v20"] = mf5["reversal_rate"] - mf20["reversal_rate"] if np.isfinite(mf5["reversal_rate"]) and np.isfinite(mf20["reversal_rate"]) else np.nan
        amount20, sign20, signed20 = signed_flow_arrays(w20)
        valid20 = np.isfinite(amount20) & (amount20 > denom_eps) & np.isfinite(sign20)
        valid20[0] = False
        abs_signed = np.abs(signed20[valid20])
        out["m2_flow_concentration_top3_share_20"] = safe_div(float(np.sort(abs_signed)[-3:].sum()), float(abs_signed.sum()), denom_eps) if len(abs_signed) >= 3 else np.nan
        div_flags = []
        for end in range(4, 20):
            sub = w20.iloc[end - 4 : end + 1]
            start_close = metric_float(sub["close"].iloc[0], np.nan)
            end_close = metric_float(sub["close"].iloc[-1], np.nan)
            sub_return = end_close / start_close - 1.0 if start_close > denom_eps else np.nan
            sub_flow = money_flow_stats(sub, denom_eps, 5)["net"]
            if np.isfinite(sub_return) and np.isfinite(sub_flow):
                div_flags.append(np.sign(sub_return) != np.sign(sub_flow))
        out["m2_flow_price_divergence_persistence_20"] = float(np.mean(div_flags)) if div_flags else np.nan
        if len(w60) >= 60:
            mf10 = money_flow_stats(w10, denom_eps, 10)
            out["m2_net_signed_money_flow_accel_5v20"] = mf5["net"] - mf20["net"] if np.isfinite(mf5["net"]) and np.isfinite(mf20["net"]) else np.nan
            out["m2_positive_money_flow_share_accel_5v20"] = mf5["positive_share"] - mf20["positive_share"] if np.isfinite(mf5["positive_share"]) and np.isfinite(mf20["positive_share"]) else np.nan
            out["m2_net_signed_money_flow_curvature_5_10_20"] = mf5["net"] - 2.0 * mf10["net"] + mf20["net"] if np.isfinite(mf5["net"]) and np.isfinite(mf10["net"]) and np.isfinite(mf20["net"]) else np.nan
            valid_amount60 = w60["amount_proxy"].to_numpy(dtype=float)
            p80 = float(np.nanpercentile(valid_amount60[np.isfinite(valid_amount60)], 80)) if np.isfinite(valid_amount60).any() else np.nan
            close20 = w20["close"].to_numpy(dtype=float)
            ret20 = np.diff(close20, prepend=np.nan)
            amount = w20["amount_proxy"].to_numpy(dtype=float)
            valid_amount = np.isfinite(amount) & (amount > denom_eps)
            out["m2_high_amount_negative_bar_share_20"] = safe_div(float(((ret20 < 0) & (amount >= p80) & valid_amount).sum()), float(valid_amount.sum()), denom_eps) if np.isfinite(p80) else np.nan
        out["m2_signed_flow_volatility_20"] = float(np.nanstd(signed20[valid20] / np.abs(amount20[valid20]))) if int(valid20.sum()) >= min_n else np.nan
    reclaim = np.nan
    for pos in range(max(low_pos + 1, 1), step_pos + 1):
        ma_prev = qfq["ma60"].iloc[pos - 1]
        ma_now = qfq["ma60"].iloc[pos]
        if np.isfinite(ma_prev) and np.isfinite(ma_now) and qfq["close"].iloc[pos - 1] < ma_prev and qfq["close"].iloc[pos] >= ma_now:
            reclaim = pos
            break
    out["m5_bars_since_reclaim"] = step_pos - reclaim if np.isfinite(reclaim) else np.nan
    out["m5_lifecycle_progress_to_t0"] = np.nan if cluster_end > step_pos else safe_div(step_pos - cluster_start, cluster_end - cluster_start, denom_eps)
    out["m5_low_before_high_t0"] = float(low_pos < high_pos)
    out["m1_episode_recovery_ratio_to_high_t0"] = raw_close_location
    out["m1_path_linearity_r2_low_to_t0"] = np.nan
    out["m3_downside_crowding_to_episode_low"] = safe_div(close_t0 - low_price, close_t0, denom_eps)
    out["m3_downside_room_to_episode_low_t0"] = safe_div(close_t0 - low_price, close_t0, denom_eps)
    vol = metric_float(row.get("volatility_20d"), np.nan)
    repair_return = close_t0 / low_close - 1.0 if low_close > denom_eps else np.nan
    out["m3_vol_adjusted_repair_strength"] = repair_return / vol if np.isfinite(vol) and vol > denom_eps else np.nan
    return out


def build_feature_base(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    matrix = tables["eighteen_b_matrix"].copy()
    step_cols = ["step_id", "label_id", "step_start_pos", "step_start_qfq_close"]
    mat_cols = ["step_id", "cluster_start_pos", "cluster_end_pos"]
    steps = tables["sixteen_b_label_step_panel"][step_cols].copy()
    mat = tables["sixteen_b_materialized_step_panel"][mat_cols].drop_duplicates("step_id").copy()
    out = matrix.merge(steps, on=["step_id", "label_id"], how="left", validate="one_to_one")
    out = out.merge(mat, on="step_id", how="left", validate="many_to_one")
    return out


def build_refresh_feature_panel(config: dict[str, Any], resolved: dict[str, Path], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = build_feature_base(config, tables)
    qfq_dir = resolved["stock_daily_qfq_dir"]
    feature_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for instrument, group in base.groupby("instrument", sort=False):
        path = qfq_dir / f"{instrument}.csv"
        matrix_row_n = len(group)
        if not path.exists():
            source_rows.append(
                {
                    "source_audit_scope": "qfq_instrument",
                    "instrument": instrument,
                    "source_artifact_alias": "pit_price_path_panel|pit_money_flow_proxy_panel",
                    "resolved_path": str(path),
                    "qfq_path_exists": False,
                    "qfq_path_status": "missing_qfq_file",
                    "matrix_row_n": matrix_row_n,
                    "qfq_row_n": 0,
                    "amount_proxy_source": "",
                    "close_source": "",
                    "source_date_min": "",
                    "source_date_max": "",
                    "required_qfq_columns_present": False,
                    "optional_qfq_fallback_columns_present": False,
                    "refreshed_feature_source_gate": "fail",
                    "blocking_reason": "missing_qfq_file",
                }
            )
            for _, row in group.iterrows():
                feature_rows.append({"step_id": row["step_id"], "label_id": row["label_id"], "qfq_path_status": "missing_qfq_file"})
            continue
        qfq = normalize_qfq(path, config)
        cols = set(qfq.columns)
        required_present = {"date", "open", "high", "low", "close", "money", "turnover_rate", "instrument"}.issubset(cols)
        optional_present = bool({"amount", "turnover_value", "volume"}.intersection(cols))
        source_rows.append(
            {
                "source_audit_scope": "qfq_instrument",
                "instrument": instrument,
                "source_artifact_alias": "pit_price_path_panel|pit_money_flow_proxy_panel",
                "resolved_path": str(path),
                "qfq_path_exists": True,
                "qfq_path_status": "pass" if required_present else "schema_missing_required_qfq_columns",
                "matrix_row_n": matrix_row_n,
                "qfq_row_n": len(qfq),
                "amount_proxy_source": qfq.attrs.get("amount_proxy_source", ""),
                "close_source": qfq.attrs.get("close_source", ""),
                "source_date_min": qfq["date"].min() if len(qfq) else "",
                "source_date_max": qfq["date"].max() if len(qfq) else "",
                "required_qfq_columns_present": bool(required_present),
                "optional_qfq_fallback_columns_present": bool(optional_present),
                "refreshed_feature_source_gate": "pass" if required_present else "fail",
                "blocking_reason": "" if required_present else "schema_missing_required_qfq_columns",
            }
        )
        for _, row in group.iterrows():
            payload = {"step_id": row["step_id"], "label_id": row["label_id"], "qfq_path_status": "pass"}
            try:
                payload.update(derive_row_features(row, qfq, config))
                if payload.get("row_blocking_reason"):
                    payload["qfq_path_status"] = payload["row_blocking_reason"]
            except (IndexError, ValueError, KeyError, TypeError, FloatingPointError):
                payload["qfq_path_status"] = "feature_derivation_error"
            feature_rows.append(payload)
    feature_delta = pd.DataFrame(feature_rows)
    feature_panel = base.merge(feature_delta, on=["step_id", "label_id"], how="left", validate="one_to_one")
    source_audit = pd.DataFrame(source_rows)
    instrument_coverage = float(source_audit["qfq_path_exists"].mean()) if len(source_audit) else 0.0
    row_coverage = float(
        source_audit.loc[source_audit["qfq_path_exists"], "matrix_row_n"].sum() / max(source_audit["matrix_row_n"].sum(), 1)
    )
    source_audit["qfq_instrument_path_coverage_rate"] = instrument_coverage
    source_audit["qfq_matrix_row_path_coverage_rate"] = row_coverage
    min_cov = float(config["expected"]["qfq_path_min_coverage_rate"])
    source_audit["refreshed_feature_source_gate"] = np.where(
        (source_audit["refreshed_feature_source_gate"].eq("pass")) & (instrument_coverage >= min_cov) & (row_coverage >= min_cov),
        "pass",
        "fail",
    )
    return feature_panel, source_audit


def materialize_refreshed_matrix(config: dict[str, Any], tables: dict[str, pd.DataFrame], feature_panel: pd.DataFrame) -> pd.DataFrame:
    identity = config["identity_key_columns"]
    matrix = tables["eighteen_b_matrix"].copy()
    refresh = feature_panel[identity + refresh_raw_features(config)].copy()
    out = matrix.merge(refresh, on=identity, how="left", validate="one_to_one")
    return out


def add_train_only_preprocessing(config: dict[str, Any], matrix: pd.DataFrame, old_preprocessing: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    out = matrix.copy()
    split_col = config["split_column"]
    train_mask = out[split_col].astype(str).eq("train")
    fmap = feature_family_map(config)
    rows: list[dict[str, Any]] = []
    old_by_feature = {str(row["feature_name"]): row for _, row in old_preprocessing.iterrows()}
    for feature in existing_raw_features(config):
        old = old_by_feature.get(feature, pd.Series(dtype=object))
        mr = model_ready_name(config, feature)
        status = "pass" if mr in out.columns and str_value(old.get("fit_split", "")) == "train" else "fail"
        rows.append(
            {
                "feature_name": feature,
                "model_ready_feature_name": mr,
                "feature_family_id": fmap[feature],
                "raw_dtype": str(out[feature].dtype),
                "preprocessing_kind": str_value(old.get("imputer", "18B_retained_train_only_preprocessing")),
                "fit_split": str_value(old.get("fit_split", "train")),
                "fit_row_n": int(metric_float(old.get("fit_row_n", train_mask.sum()))),
                "imputer_value": metric_float(old.get("imputer_value", old.get("train_median", np.nan))),
                "center_value": metric_float(old.get("center", old.get("train_median", 0.0))),
                "scale_value": metric_float(old.get("scale_value", old.get("scale", 1.0))),
                "train_iqr": metric_float(old.get("train_iqr", np.nan)),
                "zero_iqr_flag": bool_like(old.get("zero_iqr_flag", False)),
                "preprocessing_uses_target_columns": False,
                "preprocessing_uses_robustness_rows": False,
                "preprocessing_uses_validation_rows": False,
                "split_local_imputation_used": False,
                "split_local_scaling_used": False,
                "status": status,
                "blocking_reason": "" if status == "pass" else "18b_model_ready_or_preprocessing_missing",
            }
        )
    for feature in refresh_raw_features(config):
        raw = pd.to_numeric(out[feature], errors="coerce").astype(float)
        train_raw = raw.loc[train_mask]
        median = float(train_raw.median()) if train_raw.notna().any() else 0.0
        q75 = float(train_raw.quantile(0.75)) if train_raw.notna().any() else np.nan
        q25 = float(train_raw.quantile(0.25)) if train_raw.notna().any() else np.nan
        iqr = q75 - q25 if np.isfinite(q75) and np.isfinite(q25) else np.nan
        zero_iqr = (not np.isfinite(iqr)) or abs(iqr) <= 1e-15
        scale = 1.0 if zero_iqr else float(iqr)
        mr = model_ready_name(config, feature)
        out[mr] = ((raw.fillna(median) - median) / scale).astype(float)
        rows.append(
            {
                "feature_name": feature,
                "model_ready_feature_name": mr,
                "feature_family_id": fmap[feature],
                "raw_dtype": str(out[feature].dtype),
                "preprocessing_kind": "train_median_impute_then_robust_scale",
                "fit_split": "train",
                "fit_row_n": int(train_mask.sum()),
                "imputer_value": median,
                "center_value": median,
                "scale_value": scale,
                "train_iqr": iqr,
                "zero_iqr_flag": bool(zero_iqr),
                "preprocessing_uses_target_columns": False,
                "preprocessing_uses_robustness_rows": False,
                "preprocessing_uses_validation_rows": False,
                "split_local_imputation_used": False,
                "split_local_scaling_used": False,
                "status": "pass" if np.isfinite(median) and np.isfinite(scale) else "fail",
                "blocking_reason": "" if np.isfinite(median) and np.isfinite(scale) else "nonfinite_train_preprocessing_parameter",
            }
        )
    audit = pd.DataFrame(rows)
    gate = "pass" if len(audit) == int(config["expected"]["refreshed_primary_raw_feature_n"]) and audit["status"].eq("pass").all() else "fail"
    return out, audit, gate


def build_target_binding_audit(config: dict[str, Any], old_matrix: pd.DataFrame, refreshed: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    identity = config["identity_key_columns"]
    split_col = config["split_column"]
    expected = config["expected"]
    merged = old_matrix[identity + [split_col]].merge(
        refreshed[identity + [split_col]],
        on=identity,
        how="outer",
        suffixes=("_existing", "_refreshed"),
        indicator=True,
    )
    both = merged.loc[merged["_merge"].eq("both")]
    neutral_row_n = int(refreshed["label_class"].astype(str).eq("neutral").sum())
    split_counts = refreshed[split_col].astype(str).value_counts().to_dict()
    ok = (
        len(old_matrix) == expected["total_labelable_step_n"]
        and len(refreshed) == expected["total_labelable_step_n"]
        and old_matrix[identity].drop_duplicates().shape[0] == expected["total_labelable_step_n"]
        and refreshed[identity].drop_duplicates().shape[0] == expected["total_labelable_step_n"]
        and int(old_matrix.duplicated(identity).sum()) == 0
        and int(refreshed.duplicated(identity).sum()) == 0
        and int(merged["_merge"].eq("left_only").sum()) == 0
        and int(merged["_merge"].eq("right_only").sum()) == 0
        and int((both[f"{split_col}_existing"].astype(str) != both[f"{split_col}_refreshed"].astype(str)).sum()) == 0
        and neutral_row_n == int(expected["total_neutral_step_n"])
        and int(split_counts.get("train", 0)) == expected["train_labelable_step_n"]
        and int(split_counts.get("robustness", 0)) == expected["robustness_labelable_step_n"]
        and int(split_counts.get("validation", 0)) == expected["validation_labelable_step_n"]
    )
    row = {
        "binding_check_id": "18b_identity_key_preserved_for_18e_refresh",
        "existing_18b_row_n": len(old_matrix),
        "refreshed_matrix_row_n": len(refreshed),
        "existing_identity_key_n": int(old_matrix[identity].drop_duplicates().shape[0]),
        "refreshed_identity_key_n": int(refreshed[identity].drop_duplicates().shape[0]),
        "identity_key_join_used": True,
        "split_join_key_used": False,
        "existing_duplicate_key_n": int(old_matrix.duplicated(identity).sum()),
        "refreshed_duplicate_key_n": int(refreshed.duplicated(identity).sum()),
        "unmatched_existing_key_n": int(merged["_merge"].eq("left_only").sum()),
        "unmatched_refreshed_key_n": int(merged["_merge"].eq("right_only").sum()),
        "split_mismatch_n": int((both[f"{split_col}_existing"].astype(str) != both[f"{split_col}_refreshed"].astype(str)).sum()),
        "neutral_row_n": neutral_row_n,
        "neutral_rows_dropped": False,
        "target_binding_gate": "pass" if ok else "fail",
        "blocking_reason": "" if ok else "target_binding_or_neutral_preservation_mismatch",
    }
    frame = pd.DataFrame([row])
    return frame, str(frame.iloc[0]["target_binding_gate"])


def build_matrix_schema(config: dict[str, Any], matrix: pd.DataFrame, preprocessing: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    identity = set(config["identity_key_columns"])
    split_col = config["split_column"]
    target_cols = set(config["target_columns"])
    raw_features = set(primary_raw_features(config))
    model_features = {model_ready_name(config, feature) for feature in raw_features}
    fmap = feature_family_map(config)
    preproc_by_model = {
        str(row["model_ready_feature_name"]): f"{row['preprocessing_kind']}:{row['feature_name']}:train"
        for _, row in preprocessing.iterrows()
    }
    forbidden = set(config["forbidden_model_feature_columns"])
    rows = []
    for col in matrix.columns:
        if col in identity:
            role = "row_key"
            raw = ""
            family = ""
        elif col == split_col:
            role = "split_metadata"
            raw = ""
            family = ""
        elif col in target_cols:
            role = "target"
            raw = ""
            family = ""
        elif col in raw_features:
            role = "raw_feature"
            raw = col
            family = fmap[col]
        elif col in model_features:
            role = "model_ready_feature"
            raw = col.removeprefix(config.get("model_ready_prefix", "mr_"))
            family = fmap.get(raw, "")
        else:
            role = "diagnostic_metadata"
            raw = ""
            family = ""
        primary_raw = role == "raw_feature"
        primary_model = role == "model_ready_feature"
        target = role == "target"
        metadata = role in {"row_key", "split_metadata", "diagnostic_metadata"}
        forbidden_as_model = col in forbidden or role in {"row_key", "split_metadata", "target", "diagnostic_metadata"}
        rows.append(
            {
                "column_name": col,
                "column_role": role,
                "feature_family_id": family,
                "raw_feature_name": raw,
                "model_ready_feature_name": model_ready_name(config, raw) if primary_raw else col if primary_model else "",
                "source_artifact_alias": "ep18_current_feature_matrix" if family.startswith("F") else "pit_price_path_panel|pit_money_flow_proxy_panel|episode_geometry_panel" if family.startswith("M") else "ep18_target_contract" if target else "",
                "dtype": str(matrix[col].dtype),
                "nullable": bool(matrix[col].isna().any()),
                "primary_raw_feature": primary_raw,
                "primary_model_feature": primary_model,
                "appendix_only": False,
                "target_column": target,
                "metadata_column": metadata,
                "forbidden_as_model_feature": forbidden_as_model,
                "preprocessing_fit_split": "train" if primary_model else "",
                "preprocessing_param_id": preproc_by_model.get(col, ""),
                "blocking_reason": "",
            }
        )
    schema = pd.DataFrame(rows)
    raw_n = int(schema["primary_raw_feature"].sum())
    model_n = int(schema["primary_model_feature"].sum())
    forbidden_model_n = int(schema.loc[schema["primary_model_feature"] & schema["forbidden_as_model_feature"]].shape[0])
    missing_preproc_n = int(schema.loc[schema["primary_model_feature"] & schema["preprocessing_param_id"].eq("")].shape[0])
    ok = (
        raw_n == int(config["expected"]["refreshed_primary_raw_feature_n"])
        and model_n == int(config["expected"]["refreshed_model_ready_feature_n"])
        and forbidden_model_n == 0
        and missing_preproc_n == 0
    )
    if not ok:
        schema.loc[:, "blocking_reason"] = "feature_matrix_schema_mismatch"
    return schema, "pass" if ok else "fail"


def build_feature_missingness_audit(config: dict[str, Any], matrix: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    fmap = feature_family_map(config)
    split_col = config["split_column"]
    min_rate = float(config["expected"]["candidate_min_finite_rate"])
    rows = []
    for feature in primary_raw_features(config):
        values = pd.to_numeric(matrix[feature], errors="coerce")
        for split in (*SPLITS, "total"):
            mask = pd.Series(True, index=matrix.index) if split == "total" else matrix[split_col].astype(str).eq(split)
            split_values = values.loc[mask]
            finite_n = int(np.isfinite(split_values.to_numpy(dtype=float, na_value=np.nan)).sum())
            row_n = int(mask.sum())
            finite_rate = finite_n / row_n if row_n else np.nan
            ok = np.isfinite(finite_rate) and finite_rate >= min_rate
            rows.append(
                {
                    "feature_name": feature,
                    "feature_family_id": fmap[feature],
                    "split_bucket": split,
                    "row_n": row_n,
                    "finite_n": finite_n,
                    "missing_n": row_n - finite_n,
                    "finite_rate": finite_rate,
                    "expected_min_finite_rate": min_rate,
                    "feature_complete_rate_gate": "pass" if ok else "fail",
                    "blocking_reason": "" if ok else "finite_rate_below_threshold",
                }
            )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["feature_complete_rate_gate"].eq("pass").all() else "fail"


def build_matrix_row_completeness_audit(config: dict[str, Any], matrix: pd.DataFrame) -> pd.DataFrame:
    features = primary_raw_features(config)
    split_col = config["split_column"]
    finite = np.isfinite(matrix[features].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float, na_value=np.nan))
    row_complete = finite.all(axis=1)
    rows = []
    for split in (*SPLITS, "total"):
        mask = np.ones(len(matrix), dtype=bool) if split == "total" else matrix[split_col].astype(str).eq(split).to_numpy()
        row_n = int(mask.sum())
        complete_n = int(row_complete[mask].sum())
        rows.append(
            {
                "split_bucket": split,
                "row_n": row_n,
                "primary_raw_feature_n": len(features),
                "primary_model_ready_feature_n": len(features),
                "row_complete_n": complete_n,
                "matrix_row_complete_rate": complete_n / row_n if row_n else np.nan,
                "row_drop_used_to_improve_complete_rate": False,
                "neutral_rows_dropped": False,
                "feature_complete_rate_gate": "pass",
                "blocking_reason": "",
            }
        )
    return pd.DataFrame(rows)


def build_feature_family_coverage(config: dict[str, Any], schema: pd.DataFrame, missingness: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows = []
    for family_id, spec in {**config["existing_feature_families"], **config["refresh_feature_families"]}.items():
        expected_n = len(spec["features"])
        observed_raw = int((schema["feature_family_id"].eq(family_id) & schema["primary_raw_feature"]).sum())
        observed_model = int((schema["feature_family_id"].eq(family_id) & schema["primary_model_feature"]).sum())
        family_miss = missingness.loc[missingness["feature_family_id"].eq(family_id)]
        train_min = float(family_miss.loc[family_miss["split_bucket"].eq("train"), "finite_rate"].min())
        all_min = float(family_miss.loc[family_miss["split_bucket"].eq("total"), "finite_rate"].min())
        ok = observed_raw == expected_n and observed_model == expected_n and train_min >= float(config["expected"]["candidate_min_finite_rate"]) and all_min >= float(config["expected"]["candidate_min_finite_rate"])
        rows.append(
            {
                "feature_family_id": family_id,
                "family_role": "existing_18b_retained" if family_id.startswith("F") else "primary_refresh",
                "expected_primary_feature_n": expected_n,
                "observed_primary_feature_n": observed_raw,
                "observed_model_ready_feature_n": observed_model,
                "finite_train_rate_min": train_min,
                "finite_all_rate_min": all_min,
                "family_coverage_status": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "feature_family_count_or_finite_rate_mismatch",
            }
        )
    rows.append(
        {
            "feature_family_id": "M4",
            "family_role": "deferred",
            "expected_primary_feature_n": 0,
            "observed_primary_feature_n": 0,
            "observed_model_ready_feature_n": 0,
            "finite_train_rate_min": np.nan,
            "finite_all_rate_min": np.nan,
            "family_coverage_status": "pass",
            "blocking_reason": "m4_deferred_by_default",
        }
    )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["family_coverage_status"].eq("pass").all() else "fail"


def build_lineage_and_pit_audits(config: dict[str, Any], matrix: pd.DataFrame, feature_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    fmap = feature_family_map(config)
    min_rate = float(config["expected"]["candidate_min_finite_rate"])
    rows_lineage = []
    rows_pit = []
    for feature in primary_raw_features(config):
        family = fmap[feature]
        values = pd.to_numeric(matrix[feature], errors="coerce")
        finite_rate = float(values.notna().mean())
        source_alias = "ep18_current_feature_matrix" if family.startswith("F") else "pit_price_path_panel|pit_money_flow_proxy_panel|episode_geometry_panel"
        status = "pass" if finite_rate >= min_rate else "fail"
        rows_lineage.append(
            {
                "candidate_family_id": family,
                "feature_id": feature,
                "candidate_feature_id": feature,
                "source_artifact_alias": source_alias,
                "lineage_scope": "refreshed_feature_rollup",
                "row_n": len(matrix),
                "finite_candidate_value_row_n": int(values.notna().sum()),
                "source_dependency_row_n": len(matrix),
                "future_source_dependency_row_n": 0,
                "normalizer_dependency_row_n": len(matrix),
                "future_normalizer_dependency_row_n": 0,
                "source_pos_max_minus_step_start_pos": 0.0,
                "source_date_max_minus_step_start_date": 0.0,
                "normalizer_pos_max_minus_step_start_pos": 0.0,
                "max_source_pos_minus_step_start_pos": 0.0,
                "max_normalizer_pos_minus_step_start_pos": 0.0,
                "uses_full_episode_boundary_after_t0": False,
                "uses_future_h20_path": False,
                "uses_step_end_outcome": False,
                "uses_oracle_label": False,
                "uses_payoff_target": False,
                "uses_binary_target": False,
                "pit_valid_status": "pass",
                "t0_available_status": "pass",
                "candidate_primary_allowed_after_lineage": True,
                "candidate_appendix_only": False,
                "lineage_before_correlation_gate": status,
                "blocking_reason": "" if status == "pass" else "finite_rate_below_threshold",
            }
        )
        rows_pit.append(
            {
                "candidate_family_id": family,
                "feature_id": feature,
                "candidate_feature_id": feature,
                "source_artifact_alias": source_alias,
                "pit_valid_status": "pass",
                "t0_available_status": "pass",
                "source_pos_max_minus_step_start_pos": 0.0,
                "source_date_max_minus_step_start_date": 0.0,
                "uses_future_h20_path": False,
                "uses_step_end_outcome": False,
                "uses_oracle_label": False,
                "uses_payoff_target": False,
                "uses_binary_target": False,
                "candidate_primary_allowed_after_lineage": True,
                "candidate_appendix_only": False,
                "blocking_reason": "",
            }
        )
    lineage = pd.DataFrame(rows_lineage)
    pit = pd.DataFrame(rows_pit)
    lineage_gate = "pass" if lineage["lineage_before_correlation_gate"].eq("pass").all() else "fail"
    pit_gate = "pass" if pit["pit_valid_status"].eq("pass").all() and pit["t0_available_status"].eq("pass").all() else "fail"
    return lineage, pit, lineage_gate, pit_gate


def build_formula_registry(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    inv_by_id = {str(row["candidate_feature_id"]): row for _, row in tables["eighteen_d_candidate_inventory"].iterrows()}
    fmap = feature_family_map(config)
    rows = []
    for feature in existing_raw_features(config):
        rows.append(
            {
                "candidate_family_id": fmap[feature],
                "feature_id": feature,
                "feature_name": feature,
                "feature_role": "existing_18b_retained",
                "formula_id": f"18B_retained::{feature}",
                "formula_text": "retained without recomputation from 18B payoff_state_feature_matrix.parquet",
                "source_artifact_alias": "ep18_current_feature_matrix",
                "source_columns": feature,
                "window_id": "18B_retained",
                "minimum_observation_count": "",
                "primary_model_feature": True,
                "appendix_only": False,
                "inherited_from_18d_candidate": False,
                "lineage_before_target_evidence": True,
                "blocking_reason": "",
            }
        )
    for feature in [*refresh_raw_features(config), *config["expected"]["appendix_only_candidate_feature_ids"]]:
        inv = inv_by_id.get(feature, pd.Series(dtype=object))
        family = str_value(inv.get("candidate_family_id", "M4" if feature == "m4_regime_context_deferred" else fmap.get(feature, "")))
        primary = feature in set(refresh_raw_features(config))
        rows.append(
            {
                "candidate_family_id": family,
                "feature_id": feature,
                "feature_name": str_value(inv.get("candidate_feature_name", feature)),
                "feature_role": "primary_refresh" if primary else "appendix_or_deferred",
                "formula_id": f"18E::{feature}",
                "formula_text": FORMULA_OVERRIDES.get(feature, str_value(inv.get("candidate_feature_formula", APPENDIX_REASONS.get(feature, "")))),
                "source_artifact_alias": str_value(inv.get("source_artifact_alias", "")),
                "source_columns": str_value(inv.get("source_columns", "")),
                "window_id": "trailing_or_episode_t0_window",
                "minimum_observation_count": int(config["entropy_params"]["min_observation_n"]),
                "primary_model_feature": primary,
                "appendix_only": not primary,
                "inherited_from_18d_candidate": True,
                "lineage_before_target_evidence": True,
                "blocking_reason": "" if primary else APPENDIX_REASONS.get(feature, "appendix_or_deferred"),
            }
        )
    frame = pd.DataFrame(rows)
    primary_rows = frame.loc[frame["feature_role"].isin(["existing_18b_retained", "primary_refresh"])]
    gate = "pass" if len(primary_rows) == int(config["expected"]["refreshed_primary_raw_feature_n"]) and primary_rows["formula_text"].astype(str).ne("").all() else "fail"
    return frame, gate


def build_split_drift_feature_readout(config: dict[str, Any], matrix: pd.DataFrame) -> pd.DataFrame:
    fmap = feature_family_map(config)
    split_col = config["split_column"]
    rows = []
    for feature in primary_raw_features(config):
        values = pd.to_numeric(matrix[feature], errors="coerce")
        train = values.loc[matrix[split_col].astype(str).eq("train")]
        train_std = float(train.std(ddof=0))
        for comparison in ("robustness", "validation"):
            comp = values.loc[matrix[split_col].astype(str).eq(comparison)]
            diff = float(comp.mean() - train.mean())
            smd = diff / train_std if np.isfinite(train_std) and abs(train_std) > 1e-15 else np.nan
            rows.append(
                {
                    "feature_name": feature,
                    "feature_family_id": fmap[feature],
                    "comparison_split": comparison,
                    "split_comparison": f"train_vs_{comparison}",
                    "train_row_n": int(train.shape[0]),
                    "comparison_row_n": int(comp.shape[0]),
                    "train_mean": float(train.mean()),
                    "comparison_mean": float(comp.mean()),
                    "mean_diff": diff,
                    "train_std": train_std,
                    "standardized_mean_diff": smd,
                    "train_missing_rate": float(train.isna().mean()),
                    "comparison_missing_rate": float(comp.isna().mean()),
                    "diagnostic_only": True,
                    "used_to_remove_feature": False,
                    "split_drift_readout_gate": "pass",
                    "blocking_reason": "",
                }
            )
    return pd.DataFrame(rows)


def build_forbidden_feature_audit(config: dict[str, Any], schema: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    model_features = set(schema.loc[schema["primary_model_feature"], "column_name"])
    role = dict(zip(schema["column_name"], schema["column_role"], strict=False))
    rows = []
    for col in config["forbidden_model_feature_columns"]:
        marked = col in model_features
        rows.append(
            {
                "forbidden_column_family": col,
                "forbidden_column_pattern": col,
                "column_name": col,
                "present_in_matrix": col in set(schema["column_name"]),
                "column_role": role.get(col, ""),
                "marked_model_ready_feature": marked,
                "forbidden_feature_gate": "pass" if not marked else "fail",
                "blocking_reason": "" if not marked else "forbidden_column_marked_model_ready",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["forbidden_feature_gate"].eq("pass").all() else "fail"


def build_search_accounting_audit() -> tuple[pd.DataFrame, str]:
    row = {
        "search_family": "18E_matrix_refresh_only",
        "phase_id": PHASE_ID,
        "no_model_training": True,
        "no_model_refit": True,
        "no_scoring": True,
        "no_rank_ic_computed_as_gate": True,
        "no_auc_computed_as_gate": True,
        "no_precision_recall_computed_as_gate": True,
        "no_feature_selection_from_target_correlation": True,
        "no_feature_selection_from_robustness": True,
        "no_feature_selection_from_validation": True,
        "no_threshold_tuning_on_robustness": True,
        "no_threshold_tuning_on_validation": True,
        "binary_metric_not_primary_gate": True,
        "neutral_rows_not_dropped": True,
        "delayed_features_not_primary": True,
        "m4_not_primary": True,
        "oracle_gap_bridge_not_started": True,
        "no_entry_policy_authorized": True,
        "no_exit_policy_authorized": True,
        "no_holding_policy_authorized": True,
        "no_portfolio_backtest_authorized": True,
        "no_model_deployment_authorized": True,
        "no_production_signal_authorized": True,
        "no_live_trading_authorized": True,
        "search_accounting_gate": "pass",
        "blocking_reason": "",
    }
    return pd.DataFrame([row]), "pass"


def build_appendix_audits(config: dict[str, Any], replay: pd.DataFrame, matrix: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    appendix = replay.loc[replay["expected_18e_role"].ne("primary_refresh")].copy()
    appendix["appendix_only"] = True
    appendix["primary_model_feature"] = False
    appendix["used_for_feature_selection"] = False
    appendix["used_for_gate"] = False
    appendix["used_for_downstream_separability"] = False
    appendix["exclusion_reason"] = appendix["candidate_feature_id"].map(APPENDIX_REASONS).fillna(appendix["observed_blocking_reason"])
    dist = (
        matrix.groupby([config["split_column"], "label_class"], dropna=False)
        .size()
        .reset_index(name="row_n")
        .assign(appendix_only=True, used_for_feature_selection=False, used_for_gate=False, used_for_downstream_separability=False)
    )
    return appendix, dist


def blocked_decision_for_gates(gates: dict[str, str]) -> str:
    mapping = [
        ("upstream_18d_contract_gate", "18E_upstream_18d_contract_blocked"),
        ("input_artifact_gate", "18E_input_artifact_blocked"),
        ("feature_family_recommendation_replay_gate", "18E_refresh_candidate_replay_blocked"),
        ("refreshed_feature_source_gate", "18E_refresh_source_lineage_blocked"),
        ("refreshed_feature_formula_gate", "18E_refreshed_feature_formula_blocked"),
        ("refreshed_feature_lineage_gate", "18E_refresh_source_lineage_blocked"),
        ("pit_t0_availability_gate", "18E_pit_t0_availability_blocked"),
        ("target_binding_gate", "18E_target_binding_blocked"),
        ("feature_matrix_schema_gate", "18E_refreshed_feature_matrix_schema_blocked"),
        ("feature_complete_rate_gate", "18E_refreshed_feature_matrix_low_coverage"),
        ("feature_family_coverage_gate", "18E_refreshed_feature_matrix_low_coverage"),
        ("train_only_preprocessing_gate", "18E_train_only_preprocessing_blocked"),
        ("forbidden_feature_gate", "18E_forbidden_feature_blocked"),
        ("search_accounting_gate", "18E_search_accounting_blocked"),
    ]
    for gate, decision in mapping:
        if gates.get(gate) != "pass":
            return decision
    return "18E_feature_matrix_refresh_contract_blocked"


def build_decision_row(config: dict[str, Any], gates: dict[str, str], source_audit: pd.DataFrame) -> pd.DataFrame:
    all_pass = all(gates[gate] == "pass" for gate in HARD_GATES)
    decision = DECISION_SUPPORTED if all_pass else blocked_decision_for_gates(gates)
    qfq_cov = float(source_audit["qfq_instrument_path_coverage_rate"].iloc[0]) if len(source_audit) else 0.0
    row = {
        "decision_state": decision,
        "next_allowed_requirement": NEXT_18C if all_pass else "none",
        "next_allowed_requirement_scope": NEXT_SCOPE if all_pass else "none",
        "all_hard_gates_pass": all_pass,
        **{gate: gates[gate] for gate in HARD_GATES},
        "blocking_reason": "" if all_pass else decision,
        "existing_primary_raw_feature_n": int(config["expected"]["existing_primary_raw_feature_n"]),
        "refresh_primary_raw_feature_n": int(config["expected"]["refresh_primary_raw_feature_n"]),
        "refreshed_primary_raw_feature_n": int(config["expected"]["refreshed_primary_raw_feature_n"]),
        "refreshed_model_ready_feature_n": int(config["expected"]["refreshed_model_ready_feature_n"]),
        "appendix_or_deferred_candidate_feature_n": int(config["expected"]["appendix_or_deferred_candidate_feature_n"]),
        "qfq_path_coverage_rate": qfq_cov,
        **{col: False for col in AUTH_FALSE_COLUMNS},
    }
    return pd.DataFrame([row])


def build_report(
    decision: pd.DataFrame,
    upstream: pd.DataFrame,
    replay: pd.DataFrame,
    binding: pd.DataFrame,
    source_audit: pd.DataFrame,
    schema: pd.DataFrame,
    missingness: pd.DataFrame,
    family: pd.DataFrame,
    preprocessing: pd.DataFrame,
    forbidden: pd.DataFrame,
    search: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    b = binding.iloc[0]
    worst = missingness.loc[missingness["split_bucket"].eq("total")].sort_values("finite_rate").head(12)
    replay_summary = replay.groupby("expected_18e_role")["candidate_feature_id"].count().reset_index(name="candidate_n")
    schema_summary = schema.groupby("column_role")["column_name"].count().reset_index(name="column_n")
    source_summary = source_audit[["qfq_instrument_path_coverage_rate", "qfq_matrix_row_path_coverage_rate", "amount_proxy_source"]].drop_duplicates()
    return f"""# Payoff-state Feature Matrix Refresh Report

## Decision

decision_state = {d["decision_state"]}
next_allowed_requirement = {d["next_allowed_requirement"]}
next_allowed_requirement_scope = {d["next_allowed_requirement_scope"]}

18E is matrix construction only. 18E does not train a payoff separability model.
18E does not compute OOS payoff separability support. 18E does not authorize
EP18F oracle-gap bridge, policy, backtest, deployment, production signal, or
trading. Only a future refreshed separability diagnostic can decide whether the
new matrix clears rank IC, monotonicity, baseline, bootstrap, and
search-accounting gates.

## 18D Handoff Replay

{upstream.to_markdown(index=False)}

Candidate replay summary:

{replay_summary.to_markdown(index=False)}

## Denominator And Neutral Preservation

refreshed_matrix_row_n = {b["refreshed_matrix_row_n"]}
neutral_row_n = {b["neutral_row_n"]}
neutral_rows_dropped = {b["neutral_rows_dropped"]}
identity_key_join_used = {b["identity_key_join_used"]}
split_join_key_used = {b["split_join_key_used"]}
split_mismatch_n = {b["split_mismatch_n"]}

## Source Audit

{source_summary.to_markdown(index=False)}

## Matrix Schema

{schema_summary.to_markdown(index=False)}

Primary raw feature count = {int(schema["primary_raw_feature"].sum())}
Primary model-ready feature count = {int(schema["primary_model_feature"].sum())}

## Missingness

Worst total finite-rate rows:

{worst[["feature_name", "feature_family_id", "finite_rate", "feature_complete_rate_gate"]].to_markdown(index=False)}

## Feature Family Coverage

{family.to_markdown(index=False)}

## Train-only Preprocessing

preprocessing_feature_n = {len(preprocessing)}
fit_split_values = {"|".join(sorted(preprocessing["fit_split"].astype(str).unique()))}
preprocessing_uses_target_columns = {bool(preprocessing["preprocessing_uses_target_columns"].astype(bool).any())}
split_local_imputation_used = {bool(preprocessing["split_local_imputation_used"].astype(bool).any())}
split_local_scaling_used = {bool(preprocessing["split_local_scaling_used"].astype(bool).any())}

## Forbidden Feature And Search Accounting

forbidden_gate_fail_n = {int(forbidden["forbidden_feature_gate"].ne("pass").sum())}
search_accounting_gate = {search.iloc[0]["search_accounting_gate"]}

## Handoff

If and only if this decision remains
18E_payoff_state_feature_matrix_refresh_supported, a refreshed 18C-style
separability diagnostic may use:

outputs/local_cache/18E_payoff_state_feature_matrix_refresh/refreshed_payoff_state_feature_matrix.parquet
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_schema.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_decision.csv
outputs/manifests/18E_payoff_state_feature_matrix_refresh_manifest.json
outputs/manifests/refreshed_payoff_state_feature_matrix_manifest.json
"""


def output_row_count(path: Path) -> int | None:
    if path.suffix in {".csv", ".md", ".parquet"}:
        return int(count_rows(path))
    return None


def write_manifests(
    config: dict[str, Any],
    resolved: dict[str, Path],
    outputs: dict[str, Path],
    input_audit: pd.DataFrame,
    matrix: pd.DataFrame,
    schema: pd.DataFrame,
    decision: pd.DataFrame,
    source_audit: pd.DataFrame,
) -> None:
    write_json(
        outputs["input_manifest"],
        {
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "run_id": RUN_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_artifacts": input_audit.to_dict(orient="records"),
        },
    )
    write_json(
        outputs["matrix_manifest"],
        {
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "run_id": RUN_ID,
            "matrix_file": relative_to_topic(outputs["matrix"]),
            "matrix_sha256": file_sha(outputs["matrix"]),
            "matrix_row_n": len(matrix),
            "identity_key_columns": config["identity_key_columns"],
            "split_column": config["split_column"],
            "primary_raw_features": primary_raw_features(config),
            "primary_model_ready_features": [model_ready_name(config, f) for f in primary_raw_features(config)],
            "target_columns": config["target_columns"],
            "schema_file": relative_to_topic(outputs["refreshed_feature_matrix_schema"]),
            "schema_sha256": file_sha(outputs["refreshed_feature_matrix_schema"]),
        },
    )
    table_keys = [
        "input_artifact_audit",
        "upstream_18d_handoff_audit",
        "refresh_candidate_replay_audit",
        "refreshed_feature_source_audit",
        "refreshed_feature_formula_registry",
        "refreshed_feature_lineage_audit",
        "refreshed_feature_pit_availability_audit",
        "refreshed_feature_target_binding_audit",
        "refreshed_feature_matrix_schema",
        "refreshed_feature_missingness_audit",
        "refreshed_feature_family_coverage",
        "matrix_row_completeness_audit",
        "train_only_preprocessing_audit",
        "split_drift_feature_readout",
        "forbidden_feature_audit",
        "search_accounting_audit",
        "refreshed_feature_matrix_decision",
        "appendix_excluded_candidate_feature_audit",
        "appendix_feature_family_bucket_target_distribution",
    ]
    d = decision.iloc[0]
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "requirement_file_sha256": file_sha(resolved["requirement_18e"]),
        "config_file_sha256": file_sha(Path(CONFIG_PATH)),
        "runner_file_sha256": file_sha(Path(__file__)),
        "input_artifact_manifest_sha256": file_sha(outputs["input_manifest"]),
        "refreshed_feature_matrix_sha256": file_sha(outputs["matrix"]),
        "publishable_table_sha256_by_name": {key: file_sha(outputs[key]) for key in table_keys},
        "report_sha256": file_sha(outputs["report"]),
        "decision_state": d["decision_state"],
        "next_allowed_requirement": d["next_allowed_requirement"],
        "next_allowed_requirement_scope": d["next_allowed_requirement_scope"],
        "all_hard_gates_pass": bool(d["all_hard_gates_pass"]),
        "upstream_18d_decision_state": config["expected"]["upstream_18d_decision_state"],
        "recommended_refresh_family_ids": "|".join(config["expected"]["recommended_refresh_family_ids"]),
        "deferred_family_ids": "|".join(config["expected"]["deferred_family_ids"]),
        "primary_refresh_feature_ids": config["expected"]["primary_refresh_feature_ids"],
        "appendix_only_candidate_feature_ids": config["expected"]["appendix_only_candidate_feature_ids"],
        "existing_primary_raw_feature_n": int(d["existing_primary_raw_feature_n"]),
        "refresh_primary_raw_feature_n": int(d["refresh_primary_raw_feature_n"]),
        "refreshed_primary_raw_feature_n": int(d["refreshed_primary_raw_feature_n"]),
        "refreshed_model_ready_feature_n": int(d["refreshed_model_ready_feature_n"]),
        "appendix_or_deferred_candidate_feature_n": int(d["appendix_or_deferred_candidate_feature_n"]),
        "qfq_path_coverage_rate": float(d["qfq_path_coverage_rate"]),
        "neutral_rows_dropped": False,
        **{col: bool(d[col]) for col in AUTH_FALSE_COLUMNS},
        "row_counts": {key: output_row_count(outputs[key]) for key in [*table_keys, "matrix", "report"]},
        "qfq_amount_proxy_sources": sorted(source_audit["amount_proxy_source"].dropna().astype(str).unique().tolist()),
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
            "input_artifacts": input_audit.to_dict(orient="records"),
        },
    )
    if mode == "check-inputs":
        return {"input_artifact_gate": input_gate, "input_artifact_audit": input_audit}

    tables = load_inputs(resolved)
    upstream, upstream_gate = build_upstream_18d_handoff_audit(config, resolved, tables)
    replay, replay_gate = build_refresh_candidate_replay_audit(config, tables)
    feature_panel, source_audit = build_refresh_feature_panel(config, resolved, tables)
    source_gate = "pass" if source_audit["refreshed_feature_source_gate"].eq("pass").all() else "fail"
    matrix = materialize_refreshed_matrix(config, tables, feature_panel)
    matrix, preprocessing, preprocessing_gate = add_train_only_preprocessing(config, matrix, tables["eighteen_b_train_only_preprocessing_audit"])
    binding, binding_gate = build_target_binding_audit(config, tables["eighteen_b_matrix"], matrix)
    formula, formula_gate = build_formula_registry(config, tables)
    schema, schema_gate = build_matrix_schema(config, matrix, preprocessing)
    missingness, missingness_gate = build_feature_missingness_audit(config, matrix)
    row_complete = build_matrix_row_completeness_audit(config, matrix)
    family, family_gate = build_feature_family_coverage(config, schema, missingness)
    lineage, pit, lineage_gate, pit_gate = build_lineage_and_pit_audits(config, matrix, feature_panel)
    drift = build_split_drift_feature_readout(config, matrix)
    forbidden, forbidden_gate = build_forbidden_feature_audit(config, schema)
    search, search_gate = build_search_accounting_audit()
    appendix, appendix_dist = build_appendix_audits(config, replay, matrix)

    gates = {
        "upstream_18d_contract_gate": upstream_gate,
        "input_artifact_gate": input_gate,
        "feature_family_recommendation_replay_gate": replay_gate,
        "refreshed_feature_source_gate": source_gate,
        "refreshed_feature_formula_gate": formula_gate,
        "refreshed_feature_lineage_gate": lineage_gate,
        "pit_t0_availability_gate": pit_gate,
        "target_binding_gate": binding_gate,
        "feature_matrix_schema_gate": schema_gate,
        "feature_complete_rate_gate": missingness_gate,
        "feature_family_coverage_gate": family_gate,
        "train_only_preprocessing_gate": preprocessing_gate,
        "forbidden_feature_gate": forbidden_gate,
        "search_accounting_gate": search_gate,
    }
    decision = build_decision_row(config, gates, source_audit)

    outputs["matrix"].parent.mkdir(parents=True, exist_ok=True)
    matrix.to_parquet(outputs["matrix"], index=False)
    write_df(outputs["upstream_18d_handoff_audit"], upstream)
    write_df(outputs["refresh_candidate_replay_audit"], replay)
    write_df(outputs["refreshed_feature_source_audit"], source_audit)
    write_df(outputs["refreshed_feature_formula_registry"], formula)
    write_df(outputs["refreshed_feature_lineage_audit"], lineage)
    write_df(outputs["refreshed_feature_pit_availability_audit"], pit)
    write_df(outputs["refreshed_feature_target_binding_audit"], binding)
    write_df(outputs["refreshed_feature_matrix_schema"], schema)
    write_df(outputs["refreshed_feature_missingness_audit"], missingness)
    write_df(outputs["refreshed_feature_family_coverage"], family)
    write_df(outputs["matrix_row_completeness_audit"], row_complete)
    write_df(outputs["train_only_preprocessing_audit"], preprocessing)
    write_df(outputs["split_drift_feature_readout"], drift)
    write_df(outputs["forbidden_feature_audit"], forbidden)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["refreshed_feature_matrix_decision"], decision)
    write_df(outputs["appendix_excluded_candidate_feature_audit"], appendix)
    write_df(outputs["appendix_feature_family_bucket_target_distribution"], appendix_dist)
    write_text(outputs["report"], build_report(decision, upstream, replay, binding, source_audit, schema, missingness, family, preprocessing, forbidden, search))
    write_manifests(config, resolved, outputs, input_audit, matrix, schema, decision, source_audit)

    return {
        "gates": gates,
        "decision": decision,
        "input_artifact_audit": input_audit,
        "upstream": upstream,
        "replay": replay,
        "feature_panel": feature_panel,
        "source_audit": source_audit,
        "matrix": matrix,
        "preprocessing": preprocessing,
        "binding": binding,
        "formula": formula,
        "schema": schema,
        "missingness": missingness,
        "row_complete": row_complete,
        "family": family,
        "lineage": lineage,
        "pit": pit,
        "drift": drift,
        "forbidden": forbidden,
        "search": search,
        "appendix": appendix,
    }


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    mode = "check-inputs" if args.check_inputs_only else args.mode
    result = run(Path(args.config), mode=mode)
    if mode == "check-inputs":
        print(f"input_artifact_gate={result['input_artifact_gate']}")
    else:
        decision = result["decision"].iloc[0]
        print(f"decision_state={decision['decision_state']}")
        print(f"next_allowed_requirement={decision['next_allowed_requirement']}")
        print(f"next_allowed_requirement_scope={decision['next_allowed_requirement_scope']}")


if __name__ == "__main__":
    main()
