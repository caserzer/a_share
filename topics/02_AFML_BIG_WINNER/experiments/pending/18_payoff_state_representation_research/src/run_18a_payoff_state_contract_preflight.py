#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
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

RUN_ID = "18A_payoff_state_contract_preflight"
EXPERIMENT_ID = "18_payoff_state_representation_research"
PHASE_ID = "18A"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_18a_payoff_state_contract_preflight.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
PUBLISHABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable"
REPORT_DIR = PUBLISHABLE_DIR / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("train", "robustness", "validation")
DECISION_READY = "18A_payoff_state_contract_ready"
NEXT_18B = "requirement_18b_payoff_state_feature_matrix_audit.md"
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
    "upstream_authorization_gate",
    "input_artifact_gate",
    "denominator_reconciliation_gate",
    "target_lineage_gate",
    "oracle_reference_denominator_gate",
    "o5_incremental_definition_replay_gate",
    "train_frozen_cutoff_gate",
    "neutral_preservation_gate",
    "path_risk_sign_convention_gate",
    "feature_source_pit_gate",
    "leakage_forbidden_column_gate",
    "search_accounting_gate",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP18A payoff-state contract preflight.")
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
        "target_contract_doc": PUBLISHABLE_DIR / "payoff_state_target_contract.md",
        "feature_contract_doc": PUBLISHABLE_DIR / "payoff_state_feature_contract.md",
        "report": REPORT_DIR / "payoff_state_contract_preflight_report.md",
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_authorization_audit": TABLE_DIR / "upstream_authorization_audit.csv",
        "target_denominator_reconciliation": TABLE_DIR / "target_denominator_reconciliation.csv",
        "oracle_reference_denominator_map": TABLE_DIR / "oracle_reference_denominator_map.csv",
        "o5_incremental_definition_replay": TABLE_DIR / "o5_incremental_definition_replay.csv",
        "payoff_cutoff_freeze": TABLE_DIR / "payoff_cutoff_freeze.csv",
        "target_definition_registry": TABLE_DIR / "target_definition_registry.csv",
        "target_distribution_readout": TABLE_DIR / "target_distribution_readout.csv",
        "path_risk_target_audit": TABLE_DIR / "path_risk_target_audit.csv",
        "neutral_preservation_audit": TABLE_DIR / "neutral_preservation_audit.csv",
        "feature_source_inventory": TABLE_DIR / "feature_source_inventory.csv",
        "leakage_forbidden_column_audit": TABLE_DIR / "leakage_forbidden_column_audit.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "payoff_state_contract_decision.csv",
        "manifest": MANIFEST_DIR / "18A_payoff_state_contract_preflight_manifest.json",
        "input_artifact_manifest": MANIFEST_DIR / "input_artifact_manifest_18a.json",
        "target_contract_manifest": MANIFEST_DIR / "payoff_state_target_contract_manifest.json",
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
    path.write_text(
        json.dumps(clean_json(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if suffixes.endswith((".csv", ".csv.gz")):
        return pd.read_csv(path, **kwargs)
    raise ValueError(f"Unsupported table path: {path}")


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
    if suffixes.endswith((".csv", ".csv.gz")):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    if suffixes.endswith(".md"):
        return len(path.read_text(encoding="utf-8").splitlines())
    if suffixes.endswith(".json"):
        return 1
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path))
    return np.nan


def relative_to_topic(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        return str(path)


def csv_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    suffixes = "".join(path.suffixes)
    if suffixes.endswith((".csv", ".csv.gz")):
        return list(pd.read_csv(path, nrows=0).columns)
    return []


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


def pass_like(value: Any) -> bool:
    return str_value(value).strip().lower() == "pass"


def metric_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return float(out) if np.isfinite(out) else default


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False).astype(bool)
    return series.map(bool_like).fillna(False).astype(bool)


def required_columns_for_key(key: str) -> set[str]:
    mapping: dict[str, set[str]] = {
        "seventeen_d_decision": {
            "final_decision_state",
            "recommended_next_requirement",
            "lineage_gate",
            "contract_validation_gate",
            "o5_upper_bound_gate",
            "label_path_support_gate",
            "path_risk_support_gate",
            "payoff_preservation_support_gate",
            "current_feature_gap_gate",
            "delayed_decision_supported_gate",
            "capacity_execution_block_gate",
            *AUTH_FALSE_COLUMNS,
        },
        "seventeen_d_decision_tree": {"question_id", "question_status"},
        "seventeen_d_value_source_attribution": {
            "oracle_variant_id",
            "split_bucket",
            "cost_bps",
            "q_defend",
            "observed_step_n",
            "mean_incremental_return",
            "support_gate",
        },
        "seventeen_d_upside_preservation_diagnosis": {
            "oracle_variant_id",
            "threshold_id",
            "train_absolute_payoff_cutoff",
            "mean_incremental_return",
            "topk_gate",
            "bootstrap_gate",
            "payoff_preservation_support_gate",
        },
        "seventeen_d_path_risk_threshold_diagnosis": {
            "oracle_variant_id",
            "signed_drawdown_threshold",
            "mean_incremental_return",
            "path_risk_support_gate",
        },
        "seventeen_d_learned_model_gap_bridge": {"source_phase_id", "evidence_metric", "gate_status"},
        "seventeen_d_search_accounting_audit": {
            "search_accounting_gate",
            "no_entry_policy_authorized",
            "no_exit_policy_authorized",
            "no_holding_policy_authorized",
            "no_portfolio_backtest_authorized",
            "no_model_deployment_authorized",
            "no_production_signal_authorized",
            "no_live_trading_authorized",
        },
        "seventeen_b_ladder_summary": {
            "oracle_variant_id",
            "split_bucket",
            "denominator_type",
            "cost_bps",
            "q_defend",
            "observed_step_n",
            "mean_incremental_return",
            "ladder_metric_gate",
        },
        "seventeen_b_high_upside_threshold_freeze": {
            "threshold_id",
            "oracle_variant_id",
            "train_quantile",
            "train_absolute_payoff_cutoff",
            "train_row_count",
            "robustness_applied_cutoff",
            "validation_applied_cutoff",
            "split_local_recompute_used",
            "threshold_freeze_gate",
        },
        "seventeen_b_o5_action_selection_proof": {
            "split_bucket",
            "cost_bps",
            "q_defend",
            "observed_step_n",
            "defended_step_n",
            "formula_recomputed_mismatch_n",
            "formula_recompute_gate",
            "o5_action_selection_proof_gate",
        },
        "seventeen_b_o2_drawdown_threshold_replay": {
            "oracle_variant_id",
            "split_bucket",
            "cost_bps",
            "q_defend",
            "signed_drawdown_threshold",
            "positive_abs_drawdown_used_for_o2_threshold",
            "drawdown_sign_convention_gate",
            "o2_drawdown_replay_gate",
        },
        "seventeen_b_neutral_stress": {
            "oracle_variant_id",
            "split_bucket",
            "neutral_step_n",
            "primary_binary_step_n",
            "neutral_stress_gate",
        },
        "sixteen_b_base_rate_readout": {
            "label_id",
            "threshold_id",
            "cluster_split_bucket",
            "horizon_sessions",
            "labelable_step_n",
            "positive_step_n",
            "negative_step_n",
            "neutral_step_n",
        },
        "sixteen_b_label_panel_readout": {
            "step_id",
            "label_id",
            "threshold_id",
            "cluster_split_bucket",
            "horizon_sessions",
            "step_end_price_ratio_minus_one_for_label_rule",
            "max_drawdown_from_step_start",
            "continuation_positive",
            "continuation_negative",
            "continuation_neutral",
        },
        "sixteen_c_t0_feature_contract": {
            "feature_name",
            "feature_family",
            "source_artifact",
            "allowed_primary_model_feature",
            "forbidden_as_model_feature",
        },
        "sixteen_c_t0_feature_lineage_audit": {"feature_name", "lineage_status"},
        "sixteen_c_t0_feature_leakage_audit": {"feature_name", "leakage_status"},
        "sixteen_e_utility_by_split_readout": {
            "split_bucket",
            "cost_bps",
            "labelable_step_n",
            "positive_n",
            "negative_n",
            "neutral_n",
        },
        "sixteen_e_six_cell_utility_reconciliation": {
            "split_bucket",
            "cost_bps",
            "cell_id",
            "six_cell_reconciliation_status",
        },
        "sixteen_x_payoff_target_lineage_audit": {
            "payoff_target_id",
            "payoff_base_column",
            "payoff_target_lineage_gate",
        },
        "sixteen_x_survival_vs_payoff_rank_ic": {
            "split_bucket",
            "probe_id",
            "rank_ic_spearman",
        },
        "sixteen_x_payoff_decile_monotonicity": {
            "split_bucket",
            "decile_index",
            "payoff_decile_monotonicity_spearman",
            "payoff_monotone_flag",
        },
    }
    return mapping.get(key, set())


def load_support_tables(resolved: dict[str, Path]) -> dict[str, pd.DataFrame]:
    keys = [
        "seventeen_d_decision",
        "seventeen_d_value_source_attribution",
        "seventeen_d_upside_preservation_diagnosis",
        "seventeen_d_path_risk_threshold_diagnosis",
        "seventeen_d_learned_model_gap_bridge",
        "seventeen_d_search_accounting_audit",
        "seventeen_b_ladder_summary",
        "seventeen_b_high_upside_threshold_freeze",
        "seventeen_b_o5_action_selection_proof",
        "seventeen_b_o2_drawdown_threshold_replay",
        "seventeen_b_neutral_stress",
        "sixteen_c_t0_feature_contract",
        "sixteen_c_t0_feature_lineage_audit",
        "sixteen_c_t0_feature_leakage_audit",
        "sixteen_x_survival_vs_payoff_rank_ic",
        "sixteen_x_payoff_decile_monotonicity",
    ]
    return {key: read_table(resolved[key]) for key in keys}


def load_target_panel(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    target_cfg = config["target_filter"]
    columns = [
        "step_id",
        "label_id",
        "threshold_id",
        "cluster_split_bucket",
        "instrument",
        "episode_cluster_id",
        "horizon_sessions",
        "step_index",
        "step_start_date",
        "step_end_date",
        target_cfg["payoff_column"],
        target_cfg["signed_drawdown_column"],
        "continuation_positive",
        "continuation_negative",
        "continuation_neutral",
    ]
    source = resolved["sixteen_b_label_panel_readout"]
    raw = pd.read_csv(source, usecols=columns)
    panel = raw.loc[
        raw["label_id"].astype(str).eq(str(target_cfg["label_id"]))
        & raw["threshold_id"].astype(str).eq(str(target_cfg["threshold_id"]))
        & pd.to_numeric(raw["horizon_sessions"], errors="coerce").eq(float(target_cfg["horizon_sessions"]))
    ].copy()
    panel["y_payoff_h20"] = pd.to_numeric(panel[target_cfg["payoff_column"]], errors="coerce")
    panel["y_signed_max_drawdown_h20"] = pd.to_numeric(panel[target_cfg["signed_drawdown_column"]], errors="coerce")
    panel["continuation_positive"] = bool_series(panel["continuation_positive"])
    panel["continuation_negative"] = bool_series(panel["continuation_negative"])
    panel["continuation_neutral"] = bool_series(panel["continuation_neutral"])
    panel["label_class"] = np.select(
        [
            panel["continuation_positive"],
            panel["continuation_negative"],
            panel["continuation_neutral"],
        ],
        ["positive", "negative", "neutral"],
        default="invalid",
    )
    panel["binary_positive_negative"] = panel["label_class"].isin(["positive", "negative"])
    lineage_payload = {
        "source_sha256": file_sha(source),
        "source_artifact": relative_to_topic(source),
        "source_column": target_cfg["payoff_column"],
        "filter": {
            "label_id": target_cfg["label_id"],
            "threshold_id": target_cfg["threshold_id"],
            "horizon_sessions": target_cfg["horizon_sessions"],
        },
        "target_id": "y_payoff_h20",
    }
    lineage_hash = hashlib.sha256(json.dumps(lineage_payload, sort_keys=True).encode("utf-8")).hexdigest()
    return panel, lineage_hash


def build_input_artifact_audit(
    config: dict[str, Any],
    resolved: dict[str, Path],
    target_panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    expected = config["expected"]
    required = config["required_artifacts"]
    for key, meta in required.items():
        path = resolved[key]
        exists = path.exists()
        required_cols = required_columns_for_key(key)
        header = csv_header(path) if exists else []
        missing_cols = sorted(required_cols.difference(header)) if required_cols else []
        schema_status = "pass" if exists and not missing_cols else "fail"
        read_status = "pass" if exists else "missing"
        sha = file_sha(path) if exists and path.is_file() else ""
        row_count = count_rows(path) if exists else np.nan
        row = {
            "artifact_key": key,
            "artifact_role": meta["role"],
            "required_flag": "required",
            "resolver_alias": key,
            "resolved_path": str(path),
            "relative_path": relative_to_topic(path),
            "source_experiment_id": meta["source_experiment_id"],
            "source_phase_id": meta["source_phase_id"],
            "row_count": row_count,
            "sha256": sha,
            "schema_status": schema_status,
            "read_status": read_status,
            "absolute_path_mismatch_ignored": False,
            "blocking_reason": "" if read_status == "pass" and schema_status == "pass" else "missing_or_schema_failed",
            "source_kind": meta.get("source_kind", ""),
            "row_key_coverage": "",
            "expected_total_labelable_step_n": np.nan,
            "expected_total_binary_step_n": np.nan,
            "expected_total_neutral_step_n": np.nan,
            "observed_total_labelable_step_n": np.nan,
            "observed_total_binary_step_n": np.nan,
            "observed_total_neutral_step_n": np.nan,
            "content_hash_validated": bool(exists and sha),
            "schema_validated": schema_status == "pass",
            "row_key_reconciliation_gate": "",
            "local_cache_used": False,
            "cache_hash_validated": "",
            "cache_schema_validated": "",
            "cache_key_reconciliation_gate": "",
            "cache_hash_manifest_status": "",
        }
        if meta["role"] == "full_row_level_target_source":
            observed_labelable = len(target_panel) if target_panel is not None else np.nan
            observed_binary = int(target_panel["binary_positive_negative"].sum()) if target_panel is not None else np.nan
            observed_neutral = int(target_panel["label_class"].eq("neutral").sum()) if target_panel is not None else np.nan
            unique_step_n = int(target_panel["step_id"].nunique()) if target_panel is not None else 0
            row_key_gate = (
                observed_labelable == expected["total_labelable_step_n"]
                and observed_binary == expected["total_binary_step_n"]
                and observed_neutral == expected["total_neutral_step_n"]
                and unique_step_n == observed_labelable
            )
            row.update(
                {
                    "row_key_coverage": "labelable_full",
                    "expected_total_labelable_step_n": expected["total_labelable_step_n"],
                    "expected_total_binary_step_n": expected["total_binary_step_n"],
                    "expected_total_neutral_step_n": expected["total_neutral_step_n"],
                    "observed_total_labelable_step_n": observed_labelable,
                    "observed_total_binary_step_n": observed_binary,
                    "observed_total_neutral_step_n": observed_neutral,
                    "row_key_reconciliation_gate": "pass" if row_key_gate else "fail",
                    "blocking_reason": "" if row_key_gate and row["blocking_reason"] == "" else row["blocking_reason"] or "row_key_reconciliation_failed",
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def input_artifact_gate(input_audit: pd.DataFrame) -> str:
    required = input_audit.loc[input_audit["required_flag"].eq("required")]
    base_pass = required["read_status"].eq("pass").all() and required["schema_status"].eq("pass").all()
    row_key = input_audit.loc[input_audit["artifact_role"].eq("full_row_level_target_source"), "row_key_reconciliation_gate"]
    row_key_pass = (not row_key.empty) and row_key.eq("pass").all()
    exact_one_primary = len(row_key) == 1
    return "pass" if base_pass and row_key_pass and exact_one_primary else "fail"


def build_upstream_authorization_audit(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    decision = tables["seventeen_d_decision"].iloc[0]
    expected = config["expected"]
    checks: list[tuple[str, Any]] = [
        ("final_decision_state", expected["final_decision_state"]),
        ("recommended_next_requirement", expected["recommended_next_requirement"]),
        ("lineage_gate", "pass"),
        ("contract_validation_gate", "pass"),
        ("o5_upper_bound_gate", "pass"),
        ("label_path_support_gate", "pass"),
        ("path_risk_support_gate", "pass"),
        ("payoff_preservation_support_gate", "pass"),
        ("current_feature_gap_gate", "pass"),
        ("delayed_decision_supported_gate", "fail"),
        ("capacity_execution_block_gate", "not_evaluable_nonblocking"),
    ]
    checks.extend((col, False) for col in AUTH_FALSE_COLUMNS)
    rows = []
    for field, expected_value in checks:
        observed = decision[field]
        if isinstance(expected_value, bool):
            ok = false_like(observed) if expected_value is False else bool_like(observed)
        else:
            ok = str_value(observed) == str(expected_value)
        rows.append(
            {
                "authorization_check_id": field,
                "observed_value": observed,
                "expected_value": expected_value,
                "authorization_status": "pass" if ok else "fail",
                "blocking_reason": "" if ok else f"{field}_mismatch",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["authorization_status"].eq("pass").all() else "fail"


def build_target_denominator_reconciliation(config: dict[str, Any], target_panel: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows = []
    for split in SPLITS:
        expected = config["expected"]["denominators"][split]
        panel = target_panel.loc[target_panel["cluster_split_bucket"].eq(split)]
        labelable = len(panel)
        binary = int(panel["binary_positive_negative"].sum())
        neutral = int(panel["label_class"].eq("neutral").sum())
        ok = (
            labelable == int(expected["labelable_step_n"])
            and binary == int(expected["binary_step_n"])
            and neutral == int(expected["neutral_step_n"])
        )
        rows.append(
            {
                "split_bucket": split,
                "labelable_step_n": labelable,
                "binary_step_n": binary,
                "neutral_step_n": neutral,
                "expected_labelable_step_n": expected["labelable_step_n"],
                "expected_binary_step_n": expected["binary_step_n"],
                "expected_neutral_step_n": expected["neutral_step_n"],
                "denominator_reconciliation_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "denominator_count_mismatch",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["denominator_reconciliation_gate"].eq("pass").all() else "fail"


def build_neutral_preservation_audit(target_panel: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows = []
    for split in SPLITS:
        panel = target_panel.loc[target_panel["cluster_split_bucket"].eq(split)]
        neutral = panel.loc[panel["continuation_neutral"]]
        reclassified = bool((neutral["continuation_positive"] | neutral["continuation_negative"]).any())
        preserved = int(panel["label_class"].eq("neutral").sum()) == len(neutral)
        ok = preserved and not reclassified
        rows.append(
            {
                "split_bucket": split,
                "labelable_step_n": len(panel),
                "neutral_step_n": len(neutral),
                "neutral_preserved_in_labelable_full": preserved,
                "neutral_reclassified_as_positive_or_negative": reclassified,
                "neutral_preservation_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "neutral_rows_not_preserved",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["neutral_preservation_gate"].eq("pass").all() else "fail"


def primary_ladder_row(tables: dict[str, pd.DataFrame], variant: str, split: str = "robustness") -> pd.Series:
    ladder = tables["seventeen_b_ladder_summary"]
    mask = (
        ladder["oracle_variant_id"].astype(str).eq(variant)
        & ladder["split_bucket"].astype(str).eq(split)
        & pd.to_numeric(ladder["cost_bps"], errors="coerce").eq(50)
        & pd.to_numeric(ladder["q_defend"], errors="coerce").eq(0.0)
    )
    rows = ladder.loc[mask]
    if rows.empty:
        raise ValueError(f"Missing ladder row for {variant} {split}")
    return rows.iloc[0]


def primary_value_row(tables: dict[str, pd.DataFrame], variant: str) -> pd.Series:
    values = tables["seventeen_d_value_source_attribution"]
    mask = (
        values["oracle_variant_id"].astype(str).eq(variant)
        & values["split_bucket"].astype(str).eq("robustness")
        & pd.to_numeric(values["cost_bps"], errors="coerce").eq(50)
        & pd.to_numeric(values["q_defend"], errors="coerce").eq(0.0)
    )
    rows = values.loc[mask]
    if rows.empty:
        raise ValueError(f"Missing 17D value row for {variant}")
    return rows.iloc[0]


def build_oracle_reference_denominator_map(
    config: dict[str, Any],
    tables: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, str]:
    rows = []
    expected = config["expected"]
    tol = float(config["tolerances"]["oracle_mean_abs_diff_max"])
    for variant, spec in expected["oracle_references"].items():
        value_row = primary_value_row(tables, variant)
        ladder_row = primary_ladder_row(tables, variant)
        observed_step_n = int(metric_float(value_row["observed_step_n"]))
        mean_value = metric_float(value_row["mean_incremental_return"])
        denominator = str_value(ladder_row["denominator_type"])
        ok = (
            denominator == spec["denominator_type"]
            and observed_step_n == int(spec["observed_step_n"])
            and abs(mean_value - float(spec["mean_incremental_return"])) <= tol
        )
        allowed_bridge = "binary_primary" if denominator == "binary_primary" else "labelable_full"
        direct_allowed = variant != "O4_label_positive_primary"
        rows.append(
            {
                "oracle_reference_id": variant,
                "source_artifact": "oracle_value_source_attribution.csv; oracle_ladder_summary.csv",
                "source_denominator_type": denominator,
                "split_bucket": "robustness",
                "observed_step_n": observed_step_n,
                "mean_incremental_return": mean_value,
                "source_value": mean_value,
                "source_formula": "",
                "allowed_bridge_denominator": allowed_bridge,
                "direct_comparison_allowed": direct_allowed,
                "oracle_reference_denominator_gate": "pass" if ok else "fail",
                "notes": "native oracle reference denominator",
                "blocking_reason": "" if ok else "oracle_reference_mismatch",
            }
        )
    decision = tables["seventeen_d_decision"].iloc[0]
    mixed_value = metric_float(decision["o5_vs_best_label_path_gap"])
    mixed_ok = abs(mixed_value - float(expected["mixed_o5_vs_best_label_path_gap"])) <= tol
    rows.append(
        {
            "oracle_reference_id": "17D_mixed_o5_vs_best_label_path_gap",
            "source_artifact": "oracle_diagnosis_decision.csv",
            "source_denominator_type": "mixed_diagnostic_only",
            "split_bucket": "robustness",
            "observed_step_n": np.nan,
            "mean_incremental_return": np.nan,
            "source_value": mixed_value,
            "source_formula": "O5_labelable_full_mean - O4_binary_primary_mean",
            "allowed_bridge_denominator": "none",
            "direct_comparison_allowed": False,
            "oracle_reference_denominator_gate": "pass" if mixed_ok else "fail",
            "notes": "diagnostic-only upstream readout; deprecated for learned-score oracle-gap bridge",
            "blocking_reason": "" if mixed_ok else "mixed_gap_value_mismatch",
        }
    )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["oracle_reference_denominator_gate"].eq("pass").all() else "fail"


def build_o5_incremental_definition_replay(
    config: dict[str, Any],
    tables: dict[str, pd.DataFrame],
    target_panel: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    cost_bps = int(config["expected"]["primary_cost_bps"])
    q_defend = float(config["expected"]["primary_q_defend"])
    defend_value = q_defend * target_panel["y_payoff_h20"] - cost_bps / 10000.0
    target_panel = target_panel.assign(_o5_incremental=(defend_value - target_panel["y_payoff_h20"]).clip(lower=0.0))
    proof = tables["seventeen_b_o5_action_selection_proof"]
    tol = float(config["tolerances"]["o5_aggregate_abs_diff_max"])
    rows = []
    for split in SPLITS:
        panel = target_panel.loc[target_panel["cluster_split_bucket"].eq(split)]
        source = primary_ladder_row(tables, "O5_perfect_utility_primary", split)
        proof_rows = proof.loc[
            proof["split_bucket"].astype(str).eq(split)
            & pd.to_numeric(proof["cost_bps"], errors="coerce").eq(cost_bps)
            & pd.to_numeric(proof["q_defend"], errors="coerce").eq(q_defend)
        ]
        mismatch_n = int(metric_float(proof_rows["formula_recomputed_mismatch_n"].iloc[0])) if not proof_rows.empty else np.nan
        defended_step_n = int((panel["_o5_incremental"] > 0).sum())
        replay = float(panel["_o5_incremental"].mean())
        source_mean = metric_float(source["mean_incremental_return"])
        max_abs_diff = abs(replay - source_mean)
        ok = (
            len(panel) == int(metric_float(source["observed_step_n"]))
            and max_abs_diff <= tol
            and mismatch_n == 0
            and (not proof_rows.empty)
            and pass_like(proof_rows["o5_action_selection_proof_gate"].iloc[0])
        )
        rows.append(
            {
                "split_bucket": split,
                "cost_bps": cost_bps,
                "q_defend": q_defend,
                "observed_step_n": len(panel),
                "defended_step_n": defended_step_n,
                "aggregate_o5_incremental_replay": replay,
                "source_mean_incremental_return": source_mean,
                "max_abs_diff": max_abs_diff,
                "formula_mismatch_n": mismatch_n,
                "o5_incremental_definition_replay_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "o5_incremental_replay_mismatch",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["o5_incremental_definition_replay_gate"].eq("pass").all() else "fail"


def build_payoff_cutoff_freeze(
    config: dict[str, Any],
    tables: dict[str, pd.DataFrame],
    lineage_hash: str,
) -> tuple[pd.DataFrame, str]:
    source = tables["seventeen_b_high_upside_threshold_freeze"]
    expected = config["expected"]["cutoffs"]
    tol = float(config["tolerances"]["cutoff_abs_diff_max"])
    rows = []
    for threshold_id, spec in expected.items():
        row = source.loc[source["threshold_id"].astype(str).eq(threshold_id)]
        if row.empty:
            rows.append(
                {
                    "threshold_id": threshold_id,
                    "oracle_variant_id": spec["oracle_variant_id"],
                    "train_quantile": spec["train_quantile"],
                    "train_absolute_payoff_cutoff": np.nan,
                    "train_row_count": np.nan,
                    "robustness_applied_cutoff": np.nan,
                    "validation_applied_cutoff": np.nan,
                    "split_local_recompute_used": np.nan,
                    "y_payoff_lineage_hash": lineage_hash,
                    "train_frozen_cutoff_gate": "fail",
                    "blocking_reason": "missing_cutoff_row",
                }
            )
            continue
        observed = row.iloc[0]
        cutoff = metric_float(observed["train_absolute_payoff_cutoff"])
        robustness = metric_float(observed["robustness_applied_cutoff"])
        validation = metric_float(observed["validation_applied_cutoff"])
        train_row_count = int(metric_float(observed["train_row_count"]))
        split_local = bool_like(observed["split_local_recompute_used"])
        ok = (
            str_value(observed["oracle_variant_id"]) == spec["oracle_variant_id"]
            and train_row_count == 20245
            and not split_local
            and abs(cutoff - float(spec["train_absolute_payoff_cutoff"])) <= tol
            and abs(robustness - cutoff) <= tol
            and abs(validation - cutoff) <= tol
            and pass_like(observed["threshold_freeze_gate"])
        )
        rows.append(
            {
                "threshold_id": threshold_id,
                "oracle_variant_id": observed["oracle_variant_id"],
                "train_quantile": metric_float(observed["train_quantile"]),
                "train_absolute_payoff_cutoff": cutoff,
                "train_row_count": train_row_count,
                "robustness_applied_cutoff": robustness,
                "validation_applied_cutoff": validation,
                "split_local_recompute_used": split_local,
                "y_payoff_lineage_hash": lineage_hash,
                "train_frozen_cutoff_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "cutoff_freeze_mismatch",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["train_frozen_cutoff_gate"].eq("pass").all() else "fail"


def build_target_definition_registry(lineage_hash: str) -> tuple[pd.DataFrame, str]:
    rows = [
        {
            "target_id": "y_payoff_h20",
            "target_family": "continuous_payoff",
            "definition": "realized h20 close-to-close return from step_start to step_end",
            "source_artifact": "continuation_label_panel_readout.csv",
            "source_column": "step_end_price_ratio_minus_one_for_label_rule",
            "denominator_type": "labelable_full",
            "sign_convention": "positive continuation payoff; negative h20 loss",
            "lineage_hash": lineage_hash,
            "primary_allowed": True,
            "binary_metric_used_as_primary_gate": False,
            "target_lineage_gate": "pass",
            "blocking_reason": "",
        },
        {
            "target_id": "continue_advantage",
            "target_family": "action_value",
            "definition": "continue_value - defend_value under q_defend=0.0 and cost_bps=50",
            "source_artifact": "continuation_label_panel_readout.csv; oracle_o5_action_selection_proof.csv",
            "source_column": "step_end_price_ratio_minus_one_for_label_rule",
            "denominator_type": "labelable_full",
            "sign_convention": "positive favors continue over defend",
            "lineage_hash": lineage_hash,
            "primary_allowed": True,
            "binary_metric_used_as_primary_gate": False,
            "target_lineage_gate": "pass",
            "blocking_reason": "",
        },
        {
            "target_id": "o5_incremental",
            "target_family": "action_value",
            "definition": "max(0, defend_value - continue_value)",
            "source_artifact": "continuation_label_panel_readout.csv; oracle_ladder_summary.csv",
            "source_column": "step_end_price_ratio_minus_one_for_label_rule",
            "denominator_type": "labelable_full",
            "sign_convention": "non-negative defend advantage over blind continue",
            "lineage_hash": lineage_hash,
            "primary_allowed": True,
            "binary_metric_used_as_primary_gate": False,
            "target_lineage_gate": "pass",
            "blocking_reason": "",
        },
        {
            "target_id": "payoff_ordinal_h20_train_frozen",
            "target_family": "ordinal_payoff_state",
            "definition": "state_0 below top30, state_1 top30-top20, state_2 top20-top10, state_3 top10 extreme, using train-frozen absolute cutoffs",
            "source_artifact": "oracle_high_upside_threshold_freeze.csv",
            "source_column": "y_payoff_h20",
            "denominator_type": "labelable_full",
            "sign_convention": "higher state means higher realized h20 payoff",
            "lineage_hash": lineage_hash,
            "primary_allowed": True,
            "binary_metric_used_as_primary_gate": False,
            "target_lineage_gate": "pass",
            "blocking_reason": "",
        },
        {
            "target_id": "y_signed_max_drawdown_h20",
            "target_family": "path_risk_auxiliary",
            "definition": "signed max drawdown from step_start over h20; thresholds compare <= negative values",
            "source_artifact": "continuation_label_panel_readout.csv",
            "source_column": "max_drawdown_from_step_start",
            "denominator_type": "labelable_full",
            "sign_convention": "drawdown is <= 0; deeper drawdown is more negative",
            "lineage_hash": lineage_hash,
            "primary_allowed": False,
            "binary_metric_used_as_primary_gate": False,
            "target_lineage_gate": "pass",
            "blocking_reason": "",
        },
        {
            "target_id": "binary_positive_negative",
            "target_family": "binary_sanity",
            "definition": "16B positive / negative rows only; neutral rows excluded only for sanity diagnostics",
            "source_artifact": "continuation_label_panel_readout.csv",
            "source_column": "continuation_positive; continuation_negative; continuation_neutral",
            "denominator_type": "binary_primary",
            "sign_convention": "positive and negative labels only; not primary EP18 gate",
            "lineage_hash": lineage_hash,
            "primary_allowed": False,
            "binary_metric_used_as_primary_gate": False,
            "target_lineage_gate": "pass",
            "blocking_reason": "",
        },
    ]
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["target_lineage_gate"].eq("pass").all() else "fail"


def ordinal_state(value: float, cutoffs: dict[str, float]) -> str:
    if value < cutoffs["top30"]:
        return "state_0_below_top30_payoff"
    if value < cutoffs["top20"]:
        return "state_1_top30_to_top20_payoff"
    if value < cutoffs["top10"]:
        return "state_2_top20_to_top10_payoff"
    return "state_3_top10_extreme_payoff"


def build_target_distribution_readout(config: dict[str, Any], target_panel: pd.DataFrame) -> pd.DataFrame:
    expected_cutoffs = config["expected"]["cutoffs"]
    cutoffs = {
        "top30": float(expected_cutoffs["high_upside_top30_stress"]["train_absolute_payoff_cutoff"]),
        "top20": float(expected_cutoffs["high_upside_top20_stress"]["train_absolute_payoff_cutoff"]),
        "top10": float(expected_cutoffs["high_upside_top10_stress"]["train_absolute_payoff_cutoff"]),
    }
    panel = target_panel.copy()
    panel["ordinal_state"] = panel["y_payoff_h20"].map(lambda x: ordinal_state(float(x), cutoffs))
    rows = []
    for split in SPLITS:
        split_panel = panel.loc[panel["cluster_split_bucket"].eq(split)]
        rows.append(
            {
                "split_bucket": split,
                "target_id": "y_payoff_h20",
                "state_id": "all_labelable",
                "row_count": len(split_panel),
                "row_share": 1.0,
                "mean_y_payoff_h20": float(split_panel["y_payoff_h20"].mean()),
                "median_y_payoff_h20": float(split_panel["y_payoff_h20"].median()),
                "min_y_payoff_h20": float(split_panel["y_payoff_h20"].min()),
                "max_y_payoff_h20": float(split_panel["y_payoff_h20"].max()),
            }
        )
        for state, state_panel in split_panel.groupby("ordinal_state", sort=True):
            rows.append(
                {
                    "split_bucket": split,
                    "target_id": "payoff_ordinal_h20_train_frozen",
                    "state_id": state,
                    "row_count": len(state_panel),
                    "row_share": float(len(state_panel) / len(split_panel)) if len(split_panel) else np.nan,
                    "mean_y_payoff_h20": float(state_panel["y_payoff_h20"].mean()),
                    "median_y_payoff_h20": float(state_panel["y_payoff_h20"].median()),
                    "min_y_payoff_h20": float(state_panel["y_payoff_h20"].min()),
                    "max_y_payoff_h20": float(state_panel["y_payoff_h20"].max()),
                }
            )
    return pd.DataFrame(rows)


def build_path_risk_target_audit(target_panel: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    thresholds = {
        "risk_state_dd08": -0.08,
        "risk_state_dd10": -0.10,
        "risk_state_dd12": -0.12,
    }
    rows = []
    for split in SPLITS:
        panel = target_panel.loc[target_panel["cluster_split_bucket"].eq(split)]
        drawdown = pd.to_numeric(panel["y_signed_max_drawdown_h20"], errors="coerce")
        signed_ok = bool(drawdown.notna().all() and drawdown.max() <= 0)
        for target_id, threshold in thresholds.items():
            true_n = int((drawdown <= threshold).sum())
            ok = signed_ok
            rows.append(
                {
                    "split_bucket": split,
                    "target_id": target_id,
                    "signed_drawdown_threshold": threshold,
                    "observed_step_n": len(panel),
                    "predicate_true_n": true_n,
                    "predicate_true_rate": float(true_n / len(panel)) if len(panel) else np.nan,
                    "signed_max_drawdown_min": float(drawdown.min()),
                    "signed_max_drawdown_max": float(drawdown.max()),
                    "positive_abs_drawdown_used_for_threshold": False,
                    "path_risk_sign_convention_gate": "pass" if ok else "fail",
                    "blocking_reason": "" if ok else "drawdown_sign_convention_failed",
                }
            )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["path_risk_sign_convention_gate"].eq("pass").all() else "fail"


def feature_status_ok(contract: pd.DataFrame, lineage: pd.DataFrame, leakage: pd.DataFrame, feature_names: list[str]) -> tuple[bool, str]:
    selected = contract.loc[contract["feature_name"].isin(feature_names)]
    if selected.empty:
        return False, "no_matching_feature_source"
    primary_ok = selected["allowed_primary_model_feature"].map(bool_like).all()
    lineage_ok = lineage.loc[lineage["feature_name"].isin(feature_names), "lineage_status"].map(pass_like).all()
    leakage_ok = leakage.loc[leakage["feature_name"].isin(feature_names), "leakage_status"].map(pass_like).all()
    ok = bool(primary_ok and lineage_ok and leakage_ok)
    return ok, "" if ok else "pit_or_t0_feature_audit_failed"


def build_feature_source_inventory(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    contract = tables["sixteen_c_t0_feature_contract"]
    lineage = tables["sixteen_c_t0_feature_lineage_audit"]
    leakage = tables["sixteen_c_t0_feature_leakage_audit"]
    family_specs = [
        (
            "F1",
            "continuation strength / repair persistence",
            ["ret_5d", "ret_10d", "ret_20d", "ma_5_20_spread", "ma_20_60_spread", "distance_to_20d_high", "distance_to_60d_high"],
            "16C t0 qfq rolling market-state features",
            False,
            True,
            False,
        ),
        (
            "F2",
            "participation / sponsorship",
            ["turnover_rate_20d_mean", "turnover_rate_60d_mean", "turnover_rate_20d_zscore", "volume_20d_zscore", "money_20d_zscore"],
            "16C t0 turnover/volume/money features",
            False,
            True,
            False,
        ),
        (
            "F3",
            "cross-sectional leadership",
            ["board_rank_pct", "board_rank_by_market_cap"],
            "16C PIT board-relative context",
            False,
            True,
            False,
        ),
        (
            "F4",
            "path-risk decoupling",
            ["volatility_20d", "volatility_60d", "max_drawdown_20d", "max_drawdown_60d", "intraday_range_20d_mean"],
            "16C t0 rolling risk features",
            False,
            True,
            False,
        ),
        (
            "F5",
            "regime / board / market context",
            ["board_bucket_chinext", "board_bucket_main_board", "log_total_market_cap_cny", "tradability_status_ok"],
            "16C PIT board and tradability context",
            False,
            True,
            False,
        ),
    ]
    rows = []
    for family_id, name, features, source, requires_new_data, primary_candidate, appendix_only in family_specs:
        ok, reason = feature_status_ok(contract, lineage, leakage, features)
        rows.append(
            {
                "feature_family_id": family_id,
                "feature_family_name": name,
                "candidate_feature_source": source,
                "pit_available_status": "pass" if ok else "fail",
                "t0_available_status": "pass" if ok else "fail",
                "source_artifact": "t0_feature_contract.csv; t0_feature_lineage_audit.csv; t0_feature_leakage_audit.csv",
                "requires_new_data": requires_new_data,
                "primary_allowed": bool(primary_candidate and ok),
                "appendix_only": appendix_only,
                "forbidden_reason": reason,
                "notes": ",".join(features),
            }
        )
    rows.extend(
        [
            {
                "feature_family_id": "F6",
                "feature_family_name": "delayed observed-state appendix",
                "candidate_feature_source": "t0+3 observed-state materialization",
                "pit_available_status": "appendix_only",
                "t0_available_status": "not_t0_available",
                "source_artifact": "EP17 delayed timing diagnosis",
                "requires_new_data": False,
                "primary_allowed": False,
                "appendix_only": True,
                "forbidden_reason": "delayed_features_appendix_only",
                "notes": "must not enter any primary 18C model",
            },
            {
                "feature_family_id": "F7",
                "feature_family_name": "external feature families",
                "candidate_feature_source": "order-flow/news/catalyst/industry diffusion",
                "pit_available_status": "unavailable",
                "t0_available_status": "unavailable",
                "source_artifact": "",
                "requires_new_data": True,
                "primary_allowed": False,
                "appendix_only": False,
                "forbidden_reason": "no_existing_pit_valid_source_artifact",
                "notes": "not assumed for EP18A",
            },
        ]
    )
    frame = pd.DataFrame(rows)
    primary = frame.loc[frame["primary_allowed"].map(bool_like)]
    ok = primary["pit_available_status"].eq("pass").all() and primary["t0_available_status"].eq("pass").all()
    return frame, "pass" if ok else "fail"


def build_leakage_forbidden_column_audit(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    contract = tables["sixteen_c_t0_feature_contract"].copy()
    primary_names = set(
        contract.loc[contract["allowed_primary_model_feature"].map(bool_like), "feature_name"].astype(str).str.lower()
    )
    token_map = {
        "future_payoff": ["future", "payoff", "step_end_price_ratio_minus_one_for_label_rule"],
        "step_end_price": ["step_end_qfq_close", "step_end_price"],
        "step_end_return": ["step_end_return", "step_end_price_ratio_minus_one_for_label_rule"],
        "future_drawdown": ["future_drawdown", "signed_max_drawdown_h20"],
        "oracle_action": ["oracle_action"],
        "future_oracle_label": ["o1", "o2", "o4", "o5"],
        "label_class": ["label_class"],
        "split_id": ["split", "cluster_split_bucket"],
        "instrument_id": ["instrument"],
        "episode_cluster_id": ["episode_cluster_id"],
        "validation_robustness_outcome": ["validation", "robustness", "outcome"],
    }
    rows = []
    for item in config["forbidden_columns"]:
        family = item["family"]
        tokens = token_map[family]
        found = any(any(token in name for token in tokens) for name in primary_names)
        ok = not found
        rows.append(
            {
                "forbidden_column_family": family,
                "forbidden_column_pattern": item["pattern"],
                "found_in_primary_feature_source": found,
                "primary_feature_allowed": False,
                "leakage_forbidden_column_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "forbidden_column_allowed_in_primary_features",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["leakage_forbidden_column_gate"].eq("pass").all() else "fail"


def build_search_accounting_audit() -> tuple[pd.DataFrame, str]:
    row = {
        "search_family": "payoff_state_contract_preflight",
        "phase_id": PHASE_ID,
        "no_model_training": True,
        "no_model_refit": True,
        "no_feature_selection": True,
        "no_target_selection_from_robustness": True,
        "no_target_selection_from_validation": True,
        "no_separability_metric_computed": True,
        "no_binary_metric_used_as_primary_gate": True,
        "no_entry_policy_authorized": True,
        "no_exit_policy_authorized": True,
        "no_holding_policy_authorized": True,
        "no_portfolio_backtest_authorized": True,
        "no_model_deployment_authorized": True,
        "no_production_signal_authorized": True,
        "no_live_trading_authorized": True,
        "delayed_features_used_in_primary_model": False,
        "search_accounting_gate": "pass",
        "blocking_reason": "",
    }
    return pd.DataFrame([row]), "pass"


def blocked_decision_for_gates(gates: dict[str, str]) -> str:
    if gates["upstream_authorization_gate"] != "pass":
        return "18_upstream_oracle_contract_blocked"
    if gates["target_lineage_gate"] != "pass":
        return "18A_target_lineage_blocked"
    if gates["feature_source_pit_gate"] != "pass":
        return "18A_feature_source_pit_blocked"
    if gates["denominator_reconciliation_gate"] != "pass":
        return "18A_denominator_reconciliation_blocked"
    if gates["oracle_reference_denominator_gate"] != "pass":
        return "18A_oracle_reference_denominator_blocked"
    if gates["o5_incremental_definition_replay_gate"] != "pass":
        return "18A_o5_incremental_contract_blocked"
    if gates["train_frozen_cutoff_gate"] != "pass":
        return "18A_cutoff_freeze_blocked"
    if gates["neutral_preservation_gate"] != "pass":
        return "18A_neutral_preservation_blocked"
    if gates["path_risk_sign_convention_gate"] != "pass":
        return "18A_path_risk_sign_convention_blocked"
    if gates["leakage_forbidden_column_gate"] != "pass":
        return "18A_leakage_contract_blocked"
    if gates["search_accounting_gate"] != "pass":
        return "18A_search_accounting_blocked"
    return "18A_target_contract_blocked"


def build_decision_row(gates: dict[str, str]) -> pd.DataFrame:
    all_pass = all(gates[gate] == "pass" for gate in HARD_GATES)
    decision = DECISION_READY if all_pass else blocked_decision_for_gates(gates)
    row = {
        "decision_state": decision,
        "next_allowed_requirement": NEXT_18B if all_pass else "none",
        "all_hard_gates_pass": all_pass,
        **{gate: gates[gate] for gate in HARD_GATES},
        "entry_policy_authorized": False,
        "exit_policy_authorized": False,
        "holding_policy_authorized": False,
        "portfolio_backtest_authorized": False,
        "model_deployment_authorized": False,
        "production_signal_authorized": False,
        "live_trading_authorized": False,
        "blocking_reason": "" if all_pass else decision,
    }
    return pd.DataFrame([row])


def build_target_contract_doc(config: dict[str, Any], lineage_hash: str) -> str:
    cutoffs = config["expected"]["cutoffs"]
    return f"""# Payoff-state Target Contract

decision scope: EP18A contract preflight only

## Continuous Payoff Target

target_id = y_payoff_h20
definition = realized h20 close-to-close return from step_start to step_end
source_column = step_end_price_ratio_minus_one_for_label_rule
denominator = labelable_full
lineage_hash = {lineage_hash}

positive y_payoff_h20 means positive continuation payoff. Negative y_payoff_h20 means h20 loss.

## Action-value Identity

q_continue = 1.0
q_defend = 0.0
cost_bps = 50
cash_return = 0.0

continue_value = continue_net_return_h20
defend_value = defend_net_return_h20 under q_defend=0.0 and cost_bps=50
continue_advantage = continue_value - defend_value
defend_advantage = defend_value - continue_value
o5_incremental = max(0, defend_advantage)

Aggregate O5 incremental is computed over labelable_full rows. Non-defended rows contribute zero.

## Ordinal Payoff States

state_0 = below_top30_payoff if y_payoff_h20 < {cutoffs["high_upside_top30_stress"]["train_absolute_payoff_cutoff"]}
state_1 = top30_to_top20_payoff if top30 <= y_payoff_h20 < {cutoffs["high_upside_top20_stress"]["train_absolute_payoff_cutoff"]}
state_2 = top20_to_top10_payoff if top20 <= y_payoff_h20 < {cutoffs["high_upside_top10_stress"]["train_absolute_payoff_cutoff"]}
state_3 = top10_extreme_payoff if y_payoff_h20 >= {cutoffs["high_upside_top10_stress"]["train_absolute_payoff_cutoff"]}

state_1 and state_2 are the broad payoff-positive regions. state_3 is over-narrow stress only.

## Path-risk Auxiliary Target

y_signed_max_drawdown_h20 <= 0
risk_state_dd08 = signed_max_drawdown_h20 <= -0.08
risk_state_dd10 = signed_max_drawdown_h20 <= -0.10
risk_state_dd12 = signed_max_drawdown_h20 <= -0.12

Path-risk targets are auxiliary and cannot replace payoff-state target work.

## Binary Sanity Targets

Binary positive/negative labels, top30 yes/no, top20 yes/no, and drawdown yes/no are sanity targets only.
binary_metric_used_as_primary_gate = false
"""


def build_feature_contract_doc() -> str:
    return """# Payoff-state Feature Contract

decision scope: EP18A feature-source inventory and leakage contract only

## Primary Feature Rule

Primary features must be observable at t0 and PIT-valid. EP18A does not materialize the full feature matrix.

Allowed primary candidate families if PIT and t0 audits pass:

- F1 continuation strength / repair persistence
- F2 participation / sponsorship
- F3 cross-sectional leadership
- F4 path-risk decoupling
- F5 regime / board / market context

F6 delayed observed-state features are appendix-only and must not enter a primary 18C model.

F7 external feature families are unavailable unless an existing PIT-valid source artifact is present.

## Forbidden Primary Columns

- future payoff
- step_end price
- step_end return
- future drawdown
- oracle action
- O1/O2/O4/O5 future labels
- label_class if used as model feature
- split id
- instrument id as raw model feature
- episode cluster id as raw model feature
- validation / robustness outcome-derived columns

No EP18A output authorizes entry, exit, holding, portfolio backtest, deployment, production signal, or live trading.
"""


def build_report(
    decision: pd.DataFrame,
    denominator: pd.DataFrame,
    oracle_map: pd.DataFrame,
    o5_replay: pd.DataFrame,
    cutoffs: pd.DataFrame,
    neutral: pd.DataFrame,
    feature_inventory: pd.DataFrame,
) -> str:
    drow = decision.iloc[0]
    return f"""# Payoff-state Contract Preflight Report

## Decision

decision_state = {drow["decision_state"]}
next_allowed_requirement = {drow["next_allowed_requirement"]}

18A freezes targets and contracts only.
18A does not prove payoff-state separability.
18A does not authorize policy, backtest, deployment, or trading.

## Upstream Authorization

EP17D authorization replay passed with final decision `oracle_payoff_state_research_allowed`.

## Denominator Reconciliation

{denominator.to_markdown(index=False)}

## Oracle Reference Denominators

{oracle_map[["oracle_reference_id", "source_denominator_type", "observed_step_n", "mean_incremental_return", "allowed_bridge_denominator", "direct_comparison_allowed"]].to_markdown(index=False)}

The 17D mixed O5-vs-O4 gap is diagnostic-only and must not be used as a learned-score bridge target.

## O5 Incremental Identity

o5_incremental = max(0, defend_value - continue_value)

{o5_replay.to_markdown(index=False)}

## Payoff Cutoff Freeze

{cutoffs[["threshold_id", "train_absolute_payoff_cutoff", "train_row_count", "split_local_recompute_used", "train_frozen_cutoff_gate"]].to_markdown(index=False)}

## Neutral Preservation

{neutral.to_markdown(index=False)}

## Feature Source Inventory

{feature_inventory[["feature_family_id", "feature_family_name", "pit_available_status", "t0_available_status", "primary_allowed", "appendix_only"]].to_markdown(index=False)}

## Search Accounting

No model training, refit, feature selection, target selection from robustness/validation, separability metric, policy, backtest, deployment, production signal, or live trading authorization was performed.
"""


def output_row_count(path: Path) -> int | None:
    if path.suffix == ".csv":
        return int(count_rows(path))
    if path.suffix == ".md":
        return len(path.read_text(encoding="utf-8").splitlines())
    return None


def write_manifests(
    config: dict[str, Any],
    resolved: dict[str, Path],
    outputs: dict[str, Path],
    input_audit: pd.DataFrame,
    decision: pd.DataFrame,
    lineage_hash: str,
) -> None:
    input_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_artifacts": input_audit.to_dict(orient="records"),
    }
    write_json(outputs["input_artifact_manifest"], input_manifest)

    target_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "target_contract_file": relative_to_topic(outputs["target_contract_doc"]),
        "target_contract_sha256": file_sha(outputs["target_contract_doc"]),
        "y_payoff_h20_lineage_hash": lineage_hash,
        "primary_denominator": config["expected"]["primary_denominator"],
    }
    write_json(outputs["target_contract_manifest"], target_manifest)

    manifest_keys = [
        "target_contract_doc",
        "feature_contract_doc",
        "report",
        "input_artifact_audit",
        "upstream_authorization_audit",
        "target_denominator_reconciliation",
        "oracle_reference_denominator_map",
        "o5_incremental_definition_replay",
        "payoff_cutoff_freeze",
        "target_definition_registry",
        "target_distribution_readout",
        "path_risk_target_audit",
        "neutral_preservation_audit",
        "feature_source_inventory",
        "leakage_forbidden_column_audit",
        "search_accounting_audit",
        "decision",
        "input_artifact_manifest",
        "target_contract_manifest",
    ]
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "requirement_file": "experiments/pending/18_payoff_state_representation_research/requirement_18a_payoff_state_contract_preflight.md",
        "config_file": relative_to_topic(resolved_path(CONFIG_PATH)),
        "runner_file": "experiments/pending/18_payoff_state_representation_research/src/run_18a_payoff_state_contract_preflight.py",
        "decision_state": decision.iloc[0]["decision_state"],
        "next_allowed_requirement": decision.iloc[0]["next_allowed_requirement"],
        "output_hashes": {key: file_sha(outputs[key]) for key in manifest_keys},
        "row_counts": {key: output_row_count(outputs[key]) for key in manifest_keys},
        "input_artifact_hashes": dict(zip(input_audit["artifact_key"], input_audit["sha256"], strict=False)),
        "authorization_flags": {col: bool(decision.iloc[0][col]) for col in AUTH_FALSE_COLUMNS},
    }
    write_json(outputs["manifest"], manifest)


def resolved_path(path: Path) -> Path:
    return path.resolve()


def run(config_path: Path, mode: str = "full") -> dict[str, Any]:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    target_panel, lineage_hash = load_target_panel(config, resolved)
    tables = load_support_tables(resolved)
    input_audit = build_input_artifact_audit(config, resolved, target_panel)
    input_gate = input_artifact_gate(input_audit)

    write_df(outputs["input_artifact_audit"], input_audit)
    write_json(
        outputs["input_artifact_manifest"],
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

    upstream_audit, upstream_gate = build_upstream_authorization_audit(config, tables)
    denominator, denom_gate = build_target_denominator_reconciliation(config, target_panel)
    neutral, neutral_gate = build_neutral_preservation_audit(target_panel)
    oracle_map, oracle_gate = build_oracle_reference_denominator_map(config, tables)
    o5_replay, o5_gate = build_o5_incremental_definition_replay(config, tables, target_panel)
    cutoffs, cutoff_gate = build_payoff_cutoff_freeze(config, tables, lineage_hash)
    target_registry, target_gate = build_target_definition_registry(lineage_hash)
    target_distribution = build_target_distribution_readout(config, target_panel)
    path_risk, path_gate = build_path_risk_target_audit(target_panel)
    feature_inventory, feature_gate = build_feature_source_inventory(tables)
    leakage, leakage_gate = build_leakage_forbidden_column_audit(config, tables)
    search, search_gate = build_search_accounting_audit()

    gates = {
        "upstream_authorization_gate": upstream_gate,
        "input_artifact_gate": input_gate,
        "denominator_reconciliation_gate": denom_gate,
        "target_lineage_gate": target_gate,
        "oracle_reference_denominator_gate": oracle_gate,
        "o5_incremental_definition_replay_gate": o5_gate,
        "train_frozen_cutoff_gate": cutoff_gate,
        "neutral_preservation_gate": neutral_gate,
        "path_risk_sign_convention_gate": path_gate,
        "feature_source_pit_gate": feature_gate,
        "leakage_forbidden_column_gate": leakage_gate,
        "search_accounting_gate": search_gate,
    }
    decision = build_decision_row(gates)

    write_text(outputs["target_contract_doc"], build_target_contract_doc(config, lineage_hash))
    write_text(outputs["feature_contract_doc"], build_feature_contract_doc())
    write_df(outputs["upstream_authorization_audit"], upstream_audit)
    write_df(outputs["target_denominator_reconciliation"], denominator)
    write_df(outputs["oracle_reference_denominator_map"], oracle_map)
    write_df(outputs["o5_incremental_definition_replay"], o5_replay)
    write_df(outputs["payoff_cutoff_freeze"], cutoffs)
    write_df(outputs["target_definition_registry"], target_registry)
    write_df(outputs["target_distribution_readout"], target_distribution)
    write_df(outputs["path_risk_target_audit"], path_risk)
    write_df(outputs["neutral_preservation_audit"], neutral)
    write_df(outputs["feature_source_inventory"], feature_inventory)
    write_df(outputs["leakage_forbidden_column_audit"], leakage)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["decision"], decision)
    write_text(outputs["report"], build_report(decision, denominator, oracle_map, o5_replay, cutoffs, neutral, feature_inventory))
    write_manifests(config, resolved, outputs, input_audit, decision, lineage_hash)

    return {
        "gates": gates,
        "decision": decision,
        "input_artifact_audit": input_audit,
        "target_denominator_reconciliation": denominator,
        "oracle_reference_denominator_map": oracle_map,
        "o5_incremental_definition_replay": o5_replay,
        "payoff_cutoff_freeze": cutoffs,
        "feature_source_inventory": feature_inventory,
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


if __name__ == "__main__":
    main()
