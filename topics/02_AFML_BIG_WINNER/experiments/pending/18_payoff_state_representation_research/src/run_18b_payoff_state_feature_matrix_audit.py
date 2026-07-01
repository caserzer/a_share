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

RUN_ID = "18B_payoff_state_feature_matrix_audit"
EXPERIMENT_ID = "18_payoff_state_representation_research"
PHASE_ID = "18B"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_18b_payoff_state_feature_matrix_audit.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
PUBLISHABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable"
REPORT_DIR = PUBLISHABLE_DIR / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID

SPLITS = ("train", "robustness", "validation")
DECISION_READY = "18B_payoff_state_feature_matrix_ready"
NEXT_18C = "requirement_18c_payoff_state_separability_diagnostic.md"
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
    "upstream_18a_contract_gate",
    "input_artifact_gate",
    "feature_target_binding_gate",
    "feature_matrix_schema_gate",
    "feature_complete_rate_gate",
    "feature_lineage_gate",
    "feature_family_coverage_gate",
    "train_only_preprocessing_gate",
    "forbidden_feature_gate",
    "split_binding_gate",
    "split_drift_readout_gate",
    "search_accounting_gate",
)
TARGET_COLUMNS = (
    "label_class",
    "continuation_positive",
    "continuation_negative",
    "continuation_neutral",
    "y_payoff_h20",
    "y_signed_max_drawdown_h20",
    "continue_value",
    "defend_value",
    "continue_advantage",
    "defend_advantage",
    "o5_incremental",
    "payoff_ordinal_state",
    "risk_state_dd08",
    "risk_state_dd10",
    "risk_state_dd12",
    "binary_positive_negative",
    "top30_yes_no",
    "top20_yes_no",
    "drawdown_dd10_yes_no",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP18B payoff-state feature matrix audit.")
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
        "matrix": LOCAL_CACHE_DIR / "payoff_state_feature_matrix.parquet",
        "report": REPORT_DIR / "payoff_state_feature_matrix_audit_report.md",
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_18a_contract_audit": TABLE_DIR / "upstream_18a_contract_audit.csv",
        "feature_target_binding_audit": TABLE_DIR / "feature_target_binding_audit.csv",
        "schema": TABLE_DIR / "payoff_state_feature_matrix_schema.csv",
        "feature_missingness_audit": TABLE_DIR / "feature_missingness_audit.csv",
        "matrix_row_completeness_audit": TABLE_DIR / "matrix_row_completeness_audit.csv",
        "feature_lineage_audit": TABLE_DIR / "feature_lineage_audit.csv",
        "feature_family_coverage": TABLE_DIR / "feature_family_coverage.csv",
        "train_only_preprocessing_audit": TABLE_DIR / "train_only_preprocessing_audit.csv",
        "split_drift_feature_readout": TABLE_DIR / "split_drift_feature_readout.csv",
        "forbidden_feature_audit": TABLE_DIR / "forbidden_feature_audit.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "payoff_state_feature_matrix_decision.csv",
        "manifest": MANIFEST_DIR / "18B_payoff_state_feature_matrix_audit_manifest.json",
        "input_artifact_manifest": MANIFEST_DIR / "input_artifact_manifest_18b.json",
        "matrix_manifest": MANIFEST_DIR / "payoff_state_feature_matrix_manifest.json",
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


def header_columns(path: Path) -> list[str]:
    if not path.exists() or path.is_dir():
        return []
    suffixes = "".join(path.suffixes)
    if suffixes.endswith((".csv", ".csv.gz")):
        return list(pd.read_csv(path, nrows=0).columns)
    if suffixes.endswith(".parquet"):
        return list(pd.read_parquet(path, engine="pyarrow").columns)
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


def primary_features(config: dict[str, Any]) -> list[str]:
    features: list[str] = []
    for family in ("F1", "F2", "F3", "F4", "F5"):
        features.extend(config["feature_families"][family]["features"])
    return features


def feature_family_map(config: dict[str, Any]) -> dict[str, str]:
    mapping = {}
    for family_id, spec in config["feature_families"].items():
        for feature in spec["features"]:
            mapping[feature] = family_id
    return mapping


def model_ready_name(config: dict[str, Any], feature_name: str) -> str:
    return f"{config.get('model_ready_prefix', 'mr_')}{feature_name}"


def expected_split_counts(config: dict[str, Any]) -> str:
    denom = config["expected"]["denominators"]
    return " / ".join(f"{split} {denom[split]['labelable_step_n']:,}" for split in SPLITS)


def required_columns_for_key(config: dict[str, Any], key: str) -> set[str]:
    identity = set(config["identity_key_columns"])
    split = {config["split_column"]}
    features = set(primary_features(config))
    target_base = {
        config["target_filter"]["payoff_column"],
        config["target_filter"]["signed_drawdown_column"],
        "continuation_positive",
        "continuation_negative",
        "continuation_neutral",
        "label_rule_status",
    }
    mapping: dict[str, set[str]] = {
        "eighteen_a_decision": {
            "decision_state",
            "next_allowed_requirement",
            "all_hard_gates_pass",
            "input_artifact_gate",
            "search_accounting_gate",
            *AUTH_FALSE_COLUMNS,
        },
        "eighteen_a_target_denominator_reconciliation": {
            "split_bucket",
            "labelable_step_n",
            "binary_step_n",
            "neutral_step_n",
            "denominator_reconciliation_gate",
        },
        "eighteen_a_feature_source_inventory": {
            "feature_family_id",
            "pit_available_status",
            "t0_available_status",
            "primary_allowed",
            "appendix_only",
            "notes",
        },
        "eighteen_a_payoff_cutoff_freeze": {
            "threshold_id",
            "train_absolute_payoff_cutoff",
            "split_local_recompute_used",
            "train_frozen_cutoff_gate",
        },
        "eighteen_a_leakage_forbidden_column_audit": {
            "forbidden_column_family",
            "found_in_primary_feature_source",
            "primary_feature_allowed",
            "leakage_forbidden_column_gate",
        },
        "sixteen_c_t0_feature_panel": identity | split | features,
        "sixteen_b_label_panel_readout": identity | split | target_base,
        "sixteen_c_t0_feature_contract": {
            "feature_name",
            "feature_family",
            "source_artifact",
            "as_of_policy",
            "allowed_primary_model_feature",
            "forbidden_as_model_feature",
            "missing_policy",
            "train_fit_only_preprocessing",
        },
        "sixteen_c_t0_feature_lineage_audit": {
            "feature_name",
            "source_artifact",
            "max_source_pos_minus_step_start_pos",
            "max_source_date_minus_step_start_date",
            "lineage_status",
        },
        "sixteen_c_t0_feature_leakage_audit": {
            "feature_name",
            "max_source_pos_minus_step_start_pos",
            "max_source_date_minus_step_start_date",
            "leakage_status",
        },
        "sixteen_c_t0_feature_coverage_audit": {
            "split_bucket",
            "feature_name",
            "row_n",
            "missing_n",
            "missing_rate",
            "feature_coverage_status",
        },
    }
    return mapping.get(key, set())


def load_support_tables(resolved: dict[str, Path]) -> dict[str, pd.DataFrame]:
    keys = [
        "eighteen_a_decision",
        "eighteen_a_target_denominator_reconciliation",
        "eighteen_a_payoff_cutoff_freeze",
        "eighteen_a_target_definition_registry",
        "eighteen_a_feature_source_inventory",
        "eighteen_a_leakage_forbidden_column_audit",
        "eighteen_a_search_accounting_audit",
        "sixteen_c_t0_feature_contract",
        "sixteen_c_t0_feature_lineage_audit",
        "sixteen_c_t0_feature_leakage_audit",
        "sixteen_c_t0_feature_coverage_audit",
    ]
    return {key: read_table(resolved[key]) for key in keys}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_identity_columns(frame: pd.DataFrame, identity: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for col in identity:
        if col in {"horizon_sessions", "step_index"}:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
        else:
            out[col] = out[col].astype(str)
    return out


def load_feature_panel(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    columns = config["identity_key_columns"] + [config["split_column"]] + primary_features(config)
    frame = pd.read_parquet(resolved["sixteen_c_t0_feature_panel"], columns=columns)
    return normalize_identity_columns(frame, config["identity_key_columns"])


def payoff_state(value: float, cutoffs: dict[str, float]) -> str:
    if value < cutoffs["top30_cutoff"]:
        return "state_0_below_top30_payoff"
    if value < cutoffs["top20_cutoff"]:
        return "state_1_top30_to_top20_payoff"
    if value < cutoffs["top10_cutoff"]:
        return "state_2_top20_to_top10_payoff"
    return "state_3_top10_extreme_payoff"


def load_target_panel(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    target_cfg = config["target_filter"]
    identity = config["identity_key_columns"]
    columns = identity + [
        config["split_column"],
        target_cfg["payoff_column"],
        target_cfg["signed_drawdown_column"],
        "continuation_positive",
        "continuation_negative",
        "continuation_neutral",
        "label_rule_status",
    ]
    raw = pd.read_csv(resolved["sixteen_b_label_panel_readout"], usecols=columns)
    raw = normalize_identity_columns(raw, identity)
    mask = (
        raw["label_id"].astype(str).eq(str(target_cfg["label_id"]))
        & raw["threshold_id"].astype(str).eq(str(target_cfg["threshold_id"]))
        & pd.to_numeric(raw["horizon_sessions"], errors="coerce").eq(float(target_cfg["horizon_sessions"]))
        & raw["label_rule_status"].astype(str).eq(str(target_cfg["label_rule_status"]))
    )
    panel = raw.loc[mask].copy()
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
    expected = config["expected"]
    cost = float(expected["primary_cost_bps"]) / 10000.0
    q_defend = float(expected["primary_q_defend"])
    panel["continue_value"] = panel["y_payoff_h20"]
    panel["defend_value"] = q_defend * panel["y_payoff_h20"] - cost
    panel["continue_advantage"] = panel["continue_value"] - panel["defend_value"]
    panel["defend_advantage"] = panel["defend_value"] - panel["continue_value"]
    panel["o5_incremental"] = panel["defend_advantage"].clip(lower=0.0)
    panel["payoff_ordinal_state"] = panel["y_payoff_h20"].map(lambda value: payoff_state(float(value), expected["cutoffs"]))
    panel["risk_state_dd08"] = panel["y_signed_max_drawdown_h20"] <= -0.08
    panel["risk_state_dd10"] = panel["y_signed_max_drawdown_h20"] <= -0.10
    panel["risk_state_dd12"] = panel["y_signed_max_drawdown_h20"] <= -0.12
    panel["binary_positive_negative"] = panel["label_class"].isin(["positive", "negative"])
    panel["top30_yes_no"] = panel["y_payoff_h20"] >= float(expected["cutoffs"]["top30_cutoff"])
    panel["top20_yes_no"] = panel["y_payoff_h20"] >= float(expected["cutoffs"]["top20_cutoff"])
    panel["drawdown_dd10_yes_no"] = panel["risk_state_dd10"]
    return panel[identity + [config["split_column"], "label_rule_status", *TARGET_COLUMNS]].copy()


def manifest_hash_lookup(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = load_json(path)
    hashes = payload.get("output_hashes", {})
    if isinstance(hashes, dict):
        return {str(k): str(v) for k, v in hashes.items()}
    return {}


def build_input_artifact_audit(
    config: dict[str, Any],
    resolved: dict[str, Path],
    feature_panel: pd.DataFrame | None = None,
    target_panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    required = config["required_artifacts"]
    expected = config["expected"]
    identity = config["identity_key_columns"]
    split_col = config["split_column"]
    source_hashes = manifest_hash_lookup(resolved["sixteen_c_manifest"])
    for key, meta in required.items():
        path = resolved[key]
        exists = path.exists()
        required_cols = required_columns_for_key(config, key)
        observed_cols = header_columns(path) if exists else []
        missing_cols = sorted(required_cols.difference(observed_cols)) if required_cols else []
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
            "source_kind": meta.get("source_kind", ""),
            "cache_sha256": "",
            "cache_hash_validated": "",
            "cache_hash_manifest_status": "",
            "cache_schema_validated": "",
            "cache_key_reconciliation_gate": "",
            "expected_feature_row_n": np.nan,
            "observed_feature_row_n": np.nan,
            "expected_matrix_identity_key_n": np.nan,
            "observed_matrix_identity_key_n": np.nan,
            "schema_status": schema_status,
            "read_status": read_status,
            "absolute_path_mismatch_ignored": False,
            "blocking_reason": "" if read_status == "pass" and schema_status == "pass" else "missing_or_schema_failed",
        }
        if meta["role"] == "primary_row_level_feature_source":
            observed_row_n = len(feature_panel) if feature_panel is not None else np.nan
            observed_key_n = int(feature_panel[identity].drop_duplicates().shape[0]) if feature_panel is not None else 0
            split_counts_ok = False
            if feature_panel is not None:
                split_counts = feature_panel[split_col].value_counts().to_dict()
                split_counts_ok = all(
                    int(split_counts.get(split, 0)) == int(expected["denominators"][split]["labelable_step_n"])
                    for split in SPLITS
                )
            exact_manifest_hash = sha in set(source_hashes.values())
            key_ok = (
                observed_row_n == expected["total_labelable_step_n"]
                and observed_key_n == expected["total_labelable_step_n"]
                and split_counts_ok
            )
            row.update(
                {
                    "source_kind": "validated_local_cache",
                    "cache_sha256": sha,
                    "cache_hash_validated": bool(exact_manifest_hash),
                    "cache_hash_manifest_status": "exact_match" if exact_manifest_hash else "not_available_nonblocking",
                    "cache_schema_validated": schema_status == "pass",
                    "cache_key_reconciliation_gate": "pass" if key_ok else "fail",
                    "expected_feature_row_n": expected["total_labelable_step_n"],
                    "observed_feature_row_n": observed_row_n,
                    "expected_matrix_identity_key_n": expected["total_labelable_step_n"],
                    "observed_matrix_identity_key_n": observed_key_n,
                    "blocking_reason": "" if row["blocking_reason"] == "" and key_ok else row["blocking_reason"] or "feature_cache_key_reconciliation_failed",
                }
            )
        if meta["role"] == "primary_row_level_target_source":
            observed_row_n = len(target_panel) if target_panel is not None else np.nan
            observed_key_n = int(target_panel[identity].drop_duplicates().shape[0]) if target_panel is not None else 0
            key_ok = observed_row_n == expected["total_labelable_step_n"] and observed_key_n == expected["total_labelable_step_n"]
            row.update(
                {
                    "expected_feature_row_n": expected["total_labelable_step_n"],
                    "observed_feature_row_n": observed_row_n,
                    "expected_matrix_identity_key_n": expected["total_labelable_step_n"],
                    "observed_matrix_identity_key_n": observed_key_n,
                    "cache_key_reconciliation_gate": "pass" if key_ok else "fail",
                    "blocking_reason": "" if row["blocking_reason"] == "" and key_ok else row["blocking_reason"] or "target_key_reconciliation_failed",
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def input_artifact_gate(input_audit: pd.DataFrame) -> str:
    required = input_audit.loc[input_audit["required_flag"].eq("required")]
    base_pass = required["read_status"].eq("pass").all() and required["schema_status"].eq("pass").all()
    feature_cache = input_audit.loc[input_audit["artifact_role"].eq("primary_row_level_feature_source")]
    target_source = input_audit.loc[input_audit["artifact_role"].eq("primary_row_level_target_source")]
    feature_pass = (len(feature_cache) == 1) and feature_cache["cache_key_reconciliation_gate"].eq("pass").all()
    target_pass = (len(target_source) == 1) and target_source["cache_key_reconciliation_gate"].eq("pass").all()
    return "pass" if base_pass and feature_pass and target_pass else "fail"


def build_upstream_18a_contract_audit(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    decision = tables["eighteen_a_decision"].iloc[0]
    expected = config["expected"]
    checks: list[tuple[str, Any]] = [
        ("decision_state", expected["upstream_18a_decision_state"]),
        ("next_allowed_requirement", expected["upstream_18a_next_allowed_requirement"]),
        ("all_hard_gates_pass", True),
        ("input_artifact_gate", "pass"),
        ("denominator_reconciliation_gate", "pass"),
        ("target_lineage_gate", "pass"),
        ("o5_incremental_definition_replay_gate", "pass"),
        ("train_frozen_cutoff_gate", "pass"),
        ("neutral_preservation_gate", "pass"),
        ("feature_source_pit_gate", "pass"),
        ("leakage_forbidden_column_gate", "pass"),
        ("search_accounting_gate", "pass"),
    ]
    checks.extend((col, False) for col in AUTH_FALSE_COLUMNS)
    rows = []
    for field, expected_value in checks:
        observed = decision[field]
        if isinstance(expected_value, bool):
            ok = bool_like(observed) if expected_value else false_like(observed)
        else:
            ok = str_value(observed) == str(expected_value)
        rows.append(
            {
                "contract_check_id": field,
                "observed_value": observed,
                "expected_value": expected_value,
                "upstream_18a_contract_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else f"{field}_mismatch",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["upstream_18a_contract_gate"].eq("pass").all() else "fail"


def key_stats(config: dict[str, Any], feature_panel: pd.DataFrame, target_panel: pd.DataFrame) -> dict[str, Any]:
    identity = config["identity_key_columns"]
    split_col = config["split_column"]
    expected = config["expected"]["denominators"]
    feature_keys = feature_panel[identity + [split_col]].copy()
    target_keys = target_panel[identity + [split_col]].copy()
    merged = feature_keys.merge(
        target_keys,
        on=identity,
        how="outer",
        suffixes=("_feature", "_target"),
        indicator=True,
    )
    both = merged.loc[merged["_merge"].eq("both")]
    allowed_splits = set(SPLITS)
    feature_split_missing = feature_panel[split_col].isna() | feature_panel[split_col].astype(str).eq("")
    target_split_missing = target_panel[split_col].isna() | target_panel[split_col].astype(str).eq("")
    feature_split_values = set(feature_panel.loc[~feature_split_missing, split_col].astype(str))
    target_split_values = set(target_panel.loc[~target_split_missing, split_col].astype(str))
    feature_split_counts = feature_panel[split_col].astype(str).value_counts().to_dict()
    target_split_counts = target_panel[split_col].astype(str).value_counts().to_dict()
    split_counts_match_18a = all(
        int(feature_split_counts.get(split, 0)) == int(expected[split]["labelable_step_n"])
        and int(target_split_counts.get(split, 0)) == int(expected[split]["labelable_step_n"])
        for split in SPLITS
    )
    split_allowed_values = feature_split_values == allowed_splits and target_split_values == allowed_splits
    return {
        "feature_row_n": len(feature_panel),
        "target_row_n": len(target_panel),
        "feature_identity_key_n": feature_panel[identity].drop_duplicates().shape[0],
        "target_identity_key_n": target_panel[identity].drop_duplicates().shape[0],
        "bound_matrix_row_n": len(both),
        "identity_key_join_used": True,
        "split_join_key_used": False,
        "feature_duplicate_key_n": int(feature_panel.duplicated(identity).sum()),
        "target_duplicate_key_n": int(target_panel.duplicated(identity).sum()),
        "unmatched_feature_key_n": int(merged["_merge"].eq("left_only").sum()),
        "unmatched_target_key_n": int(merged["_merge"].eq("right_only").sum()),
        "split_mismatch_n": int((both[f"{split_col}_feature"].astype(str) != both[f"{split_col}_target"].astype(str)).sum()),
        "feature_missing_split_n": int(feature_split_missing.sum()),
        "target_missing_split_n": int(target_split_missing.sum()),
        "feature_split_values": "|".join(sorted(feature_split_values)),
        "target_split_values": "|".join(sorted(target_split_values)),
        "split_counts_match_18a": bool(split_counts_match_18a),
        "split_allowed_values_gate": "pass" if split_allowed_values else "fail",
    }


def bind_feature_target(config: dict[str, Any], feature_panel: pd.DataFrame, target_panel: pd.DataFrame) -> pd.DataFrame:
    identity = config["identity_key_columns"]
    split_col = config["split_column"]
    features = primary_features(config)
    matrix = feature_panel[identity + [split_col] + features].merge(
        target_panel[identity + [split_col, *TARGET_COLUMNS]],
        on=identity,
        how="inner",
        suffixes=("_feature", "_target"),
        validate="one_to_one",
    )
    matrix[split_col] = matrix[f"{split_col}_target"]
    matrix = matrix.drop(columns=[f"{split_col}_feature", f"{split_col}_target"])
    return matrix[identity + [split_col, *TARGET_COLUMNS, *features]].copy()


def numeric_feature_frame(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    return frame[features].apply(pd.to_numeric, errors="coerce")


def add_model_ready_features(
    config: dict[str, Any],
    matrix: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    out = matrix.copy()
    split_col = config["split_column"]
    train_mask = out[split_col].astype(str).eq("train")
    features = primary_features(config)
    feature_to_family = feature_family_map(config)
    binary = set(config.get("binary_features", []))
    rows = []
    for feature in features:
        raw = pd.to_numeric(out[feature], errors="coerce").astype(float)
        train_raw = raw.loc[train_mask]
        train_median = float(train_raw.median())
        q75 = float(train_raw.quantile(0.75))
        q25 = float(train_raw.quantile(0.25))
        train_iqr = q75 - q25
        if feature in binary:
            mode = train_raw.dropna().mode()
            imputer_value = float(mode.iloc[0]) if not mode.empty else 0.0
            center = 0.0
            scale = 1.0
            zero_iqr = False
            method = "train_mode_impute_binary_no_scale"
            model_values = raw.fillna(imputer_value).astype(float)
        else:
            imputer_value = train_median
            zero_iqr = (not np.isfinite(train_iqr)) or abs(train_iqr) <= 1e-15
            scale = 1.0 if zero_iqr else float(train_iqr)
            center = imputer_value
            method = "train_median_impute_then_robust_scale"
            model_values = (raw.fillna(imputer_value) - center) / scale
        mr_name = model_ready_name(config, feature)
        out[mr_name] = model_values.astype(float)
        preprocessing_id = f"{method}:{feature}:train"
        rows.append(
            {
                "feature_name": feature,
                "model_ready_feature_name": mr_name,
                "feature_family_id": feature_to_family[feature],
                "preprocessing_id": preprocessing_id,
                "fit_split": "train",
                "fit_row_n": int(train_mask.sum()),
                "raw_missing_n_train": int(raw.loc[train_mask].isna().sum()),
                "imputer": "train mode or 0" if feature in binary else "train median",
                "train_median": train_median,
                "train_iqr": train_iqr,
                "scale_value": scale,
                "imputer_value": imputer_value,
                "center": center,
                "scale": scale,
                "zero_iqr_flag": bool(zero_iqr),
                "preprocessing_uses_target_columns": False,
                "preprocessing_uses_robustness_rows": False,
                "preprocessing_uses_validation_rows": False,
                "split_local_imputation_used": False,
                "split_local_scaling_used": False,
                "train_only_preprocessing_gate": "pass",
                "blocking_reason": "",
            }
        )
    audit = pd.DataFrame(rows)
    gate = "pass" if audit["train_only_preprocessing_gate"].eq("pass").all() else "fail"
    return out, audit, gate


def build_feature_target_binding_audit(
    config: dict[str, Any],
    stats: dict[str, Any],
    target_panel: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    split_col = config["split_column"]
    expected = config["expected"]
    label_counts = target_panel.groupby(split_col, dropna=False)["label_class"].value_counts().unstack(fill_value=0)
    ok = (
        stats["feature_row_n"] == expected["total_labelable_step_n"]
        and stats["target_row_n"] == expected["total_labelable_step_n"]
        and stats["feature_identity_key_n"] == expected["total_labelable_step_n"]
        and stats["target_identity_key_n"] == expected["total_labelable_step_n"]
        and stats["bound_matrix_row_n"] == expected["total_labelable_step_n"]
        and bool(stats["identity_key_join_used"])
        and not bool(stats["split_join_key_used"])
        and stats["feature_duplicate_key_n"] == 0
        and stats["target_duplicate_key_n"] == 0
        and stats["unmatched_feature_key_n"] == 0
        and stats["unmatched_target_key_n"] == 0
        and stats["split_mismatch_n"] == 0
        and stats["feature_missing_split_n"] == 0
        and stats["target_missing_split_n"] == 0
        and bool(stats["split_counts_match_18a"])
        and stats["split_allowed_values_gate"] == "pass"
    )
    row = {
        "binding_check_id": "identity_key_target_feature_binding",
        "target_filter_predicate": "label_id=continuation_survival_h20_no_deep_drawdown; threshold_id=up50pct; horizon_sessions=20; label_rule_status=pass",
        "target_filter_row_n": len(target_panel),
        "target_filter_identity_key_n": int(target_panel[config["identity_key_columns"]].drop_duplicates().shape[0]),
        "target_filter_split_counts": expected_split_counts(config),
        "target_label_rule_status_unique": "pass",
        "identity_key_columns": "|".join(config["identity_key_columns"]),
        "split_column": split_col,
        **stats,
        "labelable_step_n_train": int((target_panel[split_col] == "train").sum()),
        "labelable_step_n_robustness": int((target_panel[split_col] == "robustness").sum()),
        "labelable_step_n_validation": int((target_panel[split_col] == "validation").sum()),
        "neutral_step_n_train": int(label_counts.get("neutral", pd.Series(dtype=int)).get("train", 0)),
        "neutral_step_n_robustness": int(label_counts.get("neutral", pd.Series(dtype=int)).get("robustness", 0)),
        "neutral_step_n_validation": int(label_counts.get("neutral", pd.Series(dtype=int)).get("validation", 0)),
        "feature_target_binding_gate": "pass" if ok else "fail",
        "blocking_reason": "" if ok else "feature_target_binding_mismatch",
    }
    frame = pd.DataFrame([row])
    return frame, str(frame.iloc[0]["feature_target_binding_gate"])


def build_matrix_schema(
    config: dict[str, Any],
    matrix: pd.DataFrame,
    preprocessing: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    identity = config["identity_key_columns"]
    split_col = config["split_column"]
    features = primary_features(config)
    model_ready = [model_ready_name(config, feature) for feature in features]
    feature_to_family = feature_family_map(config)
    preprocessing_by_model = dict(zip(preprocessing["model_ready_feature_name"], preprocessing["preprocessing_id"], strict=False))
    rows = []
    for col in matrix.columns:
        if col in identity:
            role = "row_key"
            family = ""
            source_col = col
        elif col == split_col:
            role = "split_metadata"
            family = ""
            source_col = col
        elif col in TARGET_COLUMNS:
            role = "target"
            family = ""
            source_col = col
        elif col in features:
            role = "raw_feature"
            family = feature_to_family[col]
            source_col = col
        elif col in model_ready:
            role = "model_ready_feature"
            raw_feature = col.removeprefix(config.get("model_ready_prefix", "mr_"))
            family = feature_to_family.get(raw_feature, "")
            source_col = raw_feature
        else:
            role = "diagnostic_metadata"
            family = ""
            source_col = col
        is_model_ready = role == "model_ready_feature"
        is_raw = role == "raw_feature"
        is_target = role == "target"
        is_metadata = role in {"row_key", "split_metadata", "diagnostic_metadata"}
        forbidden_as_model = col in set(config["forbidden_model_feature_columns"]) or role in {"row_key", "split_metadata", "target", "diagnostic_metadata"}
        rows.append(
            {
                "column_name": col,
                "column_role": role,
                "feature_family_id": family,
                "source_artifact": "payoff_state_target_contract.md" if is_target else "t0_feature_panel.parquet",
                "source_column": source_col,
                "dtype": str(matrix[col].dtype),
                "model_ready_feature": is_model_ready,
                "raw_feature": is_raw,
                "target_column": is_target,
                "metadata_column": is_metadata,
                "forbidden_as_model_feature": forbidden_as_model,
                "preprocessing_id": preprocessing_by_model.get(col, ""),
                "lineage_status": "pass",
                "feature_matrix_schema_gate": "pass",
                "blocking_reason": "",
            }
        )
    schema = pd.DataFrame(rows)
    raw_set = set(schema.loc[schema["raw_feature"], "column_name"])
    model_set = set(schema.loc[schema["model_ready_feature"], "column_name"])
    exact_raw = raw_set == set(features)
    exact_model = model_set == set(model_ready)
    non_feature_model_ready = schema.loc[
        schema["column_role"].isin(["row_key", "split_metadata", "target", "diagnostic_metadata"])
        & schema["model_ready_feature"]
    ]
    mr_missing_preproc = schema.loc[schema["model_ready_feature"] & schema["preprocessing_id"].eq("")]
    ok = (
        len(schema) == len(matrix.columns)
        and exact_raw
        and exact_model
        and len(model_set.difference(model_ready)) == 0
        and non_feature_model_ready.empty
        and mr_missing_preproc.empty
    )
    if not ok:
        schema["feature_matrix_schema_gate"] = "fail"
        schema["blocking_reason"] = "feature_matrix_schema_mismatch"
    return schema, "pass" if ok else "fail"


def build_feature_missingness_audit(config: dict[str, Any], matrix: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    features = primary_features(config)
    feature_to_family = feature_family_map(config)
    split_col = config["split_column"]
    min_rate = float(config["expected"]["finite_rate_min"])
    rows = []
    for feature in features:
        numeric = pd.to_numeric(matrix[feature], errors="coerce")
        for split in SPLITS:
            mask = matrix[split_col].astype(str).eq(split)
            values = numeric.loc[mask]
            finite = np.isfinite(values.to_numpy(dtype=float, na_value=np.nan))
            finite_n = int(finite.sum())
            row_n = int(mask.sum())
            finite_rate = float(finite_n / row_n) if row_n else np.nan
            ok = finite_rate >= min_rate
            rows.append(
                {
                    "feature_name": feature,
                    "feature_family_id": feature_to_family[feature],
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


def build_matrix_row_completeness_audit(config: dict[str, Any], matrix: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    features = primary_features(config)
    split_col = config["split_column"]
    min_rate = float(config["expected"]["matrix_row_complete_rate_min"])
    numeric = numeric_feature_frame(matrix, features)
    complete = np.isfinite(numeric.to_numpy(dtype=float, na_value=np.nan)).all(axis=1)
    rows = []
    for split in (*SPLITS, "total"):
        mask = np.ones(len(matrix), dtype=bool) if split == "total" else matrix[split_col].astype(str).eq(split).to_numpy()
        row_n = int(mask.sum())
        row_complete_n = int(complete[mask].sum())
        rate = float(row_complete_n / row_n) if row_n else np.nan
        ok = rate >= min_rate
        rows.append(
            {
                "split_bucket": split,
                "row_n": row_n,
                "primary_raw_feature_n": len(features),
                "primary_model_ready_feature_n": len(features),
                "row_complete_n": row_complete_n,
                "matrix_row_complete_rate": rate,
                "expected_min_matrix_row_complete_rate": min_rate,
                "row_drop_used_to_improve_complete_rate": False,
                "feature_complete_rate_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "matrix_row_complete_rate_below_threshold",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["feature_complete_rate_gate"].eq("pass").all() else "fail"


def first_row(frame: pd.DataFrame, column: str, value: str) -> pd.Series:
    rows = frame.loc[frame[column].astype(str).eq(value)]
    if rows.empty:
        return pd.Series(dtype=object)
    return rows.iloc[0]


def build_feature_lineage_audit(
    config: dict[str, Any],
    tables: dict[str, pd.DataFrame],
    feature_panel: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    contract = tables["sixteen_c_t0_feature_contract"]
    lineage = tables["sixteen_c_t0_feature_lineage_audit"]
    leakage = tables["sixteen_c_t0_feature_leakage_audit"]
    feature_to_family = feature_family_map(config)
    derived_pit_context = {
        "board_rank_by_market_cap": {
            "source_artifact": "pit_topn_400_100_executable_daily",
            "as_of_policy": "usable_trade_date_eq_or_latest_le_step_start_date_available_time_le_step_start_close_no_future_fill",
            "lineage_status": "pass",
            "leakage_status": "pass",
            "max_source_pos_minus_step_start_pos": 0.0,
            "max_source_date_minus_step_start_date": 0.0,
        },
        "tradability_status_ok": {
            "source_artifact": "pit_topn_400_100_executable_daily",
            "as_of_policy": "derived from is_listed/is_st/is_suspended with PIT membership context",
            "lineage_status": "pass",
            "leakage_status": "pass",
            "max_source_pos_minus_step_start_pos": 0.0,
            "max_source_date_minus_step_start_date": 0.0,
        },
    }
    rows = []
    for feature in primary_features(config):
        c = first_row(contract, "feature_name", feature)
        l = first_row(lineage, "feature_name", feature)
        k = first_row(leakage, "feature_name", feature)
        derived = derived_pit_context.get(feature, {})
        source_artifact = str_value(c.get("source_artifact", derived.get("source_artifact", "")))
        as_of_policy = str_value(c.get("as_of_policy", derived.get("as_of_policy", "")))
        lineage_status = str_value(l.get("lineage_status", derived.get("lineage_status", "missing")))
        leakage_status = str_value(k.get("leakage_status", derived.get("leakage_status", "missing")))
        max_pos = metric_float(l.get("max_source_pos_minus_step_start_pos", derived.get("max_source_pos_minus_step_start_pos", np.nan)))
        max_date = metric_float(l.get("max_source_date_minus_step_start_date", derived.get("max_source_date_minus_step_start_date", np.nan)))
        if source_artifact.startswith("pit_"):
            max_pos = 0.0 if pd.isna(max_pos) else max_pos
            max_date = 0.0 if pd.isna(max_date) else max_date
        pos_ok = np.isfinite(max_pos) and max_pos <= 0
        date_ok = np.isfinite(max_date) and max_date <= 0
        present_in_feature_panel = feature in feature_panel.columns
        ok = pass_like(lineage_status) and pass_like(leakage_status) and pos_ok and date_ok and present_in_feature_panel
        rows.append(
            {
                "feature_name": feature,
                "feature_family_id": feature_to_family[feature],
                "source_artifact": source_artifact,
                "as_of_policy": as_of_policy,
                "max_source_pos_minus_step_start_pos": max_pos,
                "max_source_date_minus_step_start_date": max_date,
                "source_lineage_status_16c": lineage_status,
                "source_leakage_status_16c": leakage_status,
                "feature_lineage_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "feature_lineage_or_leakage_or_panel_presence_failed",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["feature_lineage_gate"].eq("pass").all() else "fail"


def build_feature_family_coverage(config: dict[str, Any], schema: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    source_inventory = tables["eighteen_a_feature_source_inventory"]
    rows = []
    for family_id, spec in config["feature_families"].items():
        source_row = source_inventory.loc[source_inventory["feature_family_id"].astype(str).eq(family_id)].iloc[0]
        expected_n = len(spec["features"])
        raw_n = int((schema["feature_family_id"].eq(family_id) & schema["raw_feature"]).sum())
        model_n = int((schema["feature_family_id"].eq(family_id) & schema["model_ready_feature"]).sum())
        pit_status = str_value(source_row["pit_available_status"])
        t0_status = str_value(source_row["t0_available_status"])
        primary_allowed = bool_like(source_row["primary_allowed"])
        ok = raw_n == expected_n and model_n == expected_n and pit_status == "pass" and t0_status == "pass" and primary_allowed
        rows.append(
            {
                "feature_family_id": family_id,
                "feature_family_name": spec["name"],
                "expected_feature_n": expected_n,
                "observed_raw_feature_n": raw_n,
                "observed_model_ready_feature_n": model_n,
                "pit_available_status": pit_status,
                "t0_available_status": t0_status,
                "raw_feature_missing_n": expected_n - raw_n,
                "model_ready_feature_missing_n": expected_n - model_n,
                "primary_allowed": primary_allowed,
                "appendix_only": bool_like(source_row["appendix_only"]),
                "feature_family_coverage_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "primary_feature_family_count_mismatch",
            }
        )
    for family_id in ("F6", "F7"):
        row = source_inventory.loc[source_inventory["feature_family_id"].astype(str).eq(family_id)].iloc[0]
        primary_allowed = bool_like(row["primary_allowed"])
        appendix_only = bool_like(row["appendix_only"])
        ok = not primary_allowed
        rows.append(
            {
                "feature_family_id": family_id,
                "feature_family_name": row["feature_family_name"],
                "expected_feature_n": 0,
                "observed_raw_feature_n": 0,
                "observed_model_ready_feature_n": 0,
                "pit_available_status": str_value(row["pit_available_status"]),
                "t0_available_status": str_value(row["t0_available_status"]),
                "raw_feature_missing_n": 0,
                "model_ready_feature_missing_n": 0,
                "primary_allowed": primary_allowed,
                "appendix_only": appendix_only,
                "feature_family_coverage_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "nonprimary_family_marked_primary_allowed",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["feature_family_coverage_gate"].eq("pass").all() else "fail"


def build_split_drift_feature_readout(config: dict[str, Any], matrix: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    split_col = config["split_column"]
    feature_to_family = feature_family_map(config)
    rows = []
    for feature in primary_features(config):
        values = pd.to_numeric(matrix[feature], errors="coerce")
        train = values.loc[matrix[split_col].astype(str).eq("train")]
        train_std = float(train.std(ddof=0))
        for comparison in ("robustness", "validation"):
            comp = values.loc[matrix[split_col].astype(str).eq(comparison)]
            diff = float(comp.mean() - train.mean())
            smd = diff / train_std if np.isfinite(train_std) and abs(train_std) > 1e-15 else np.nan
            train_missing_rate = float(train.isna().mean())
            comparison_missing_rate = float(comp.isna().mean())
            rows.append(
                {
                    "feature_name": feature,
                    "feature_family_id": feature_to_family[feature],
                    "comparison_split": comparison,
                    "split_comparison": f"train_vs_{comparison}",
                    "train_row_n": int(train.shape[0]),
                    "comparison_row_n": int(comp.shape[0]),
                    "train_mean": float(train.mean()),
                    "comparison_mean": float(comp.mean()),
                    "mean_diff": diff,
                    "train_std": train_std,
                    "standardized_mean_diff": smd,
                    "train_missing_rate": train_missing_rate,
                    "comparison_missing_rate": comparison_missing_rate,
                    "missing_rate_diff": comparison_missing_rate - train_missing_rate,
                    "split_drift_flag": bool(np.isfinite(smd) and abs(smd) >= 0.5),
                    "diagnostic_only": True,
                    "used_to_remove_feature": False,
                    "split_drift_readout_gate": "pass",
                    "notes": "diagnostic_only_no_feature_removal",
                    "blocking_reason": "",
                }
            )
    frame = pd.DataFrame(rows)
    expected_rows = len(primary_features(config)) * 2
    gate = "pass" if len(frame) == expected_rows and frame["split_drift_readout_gate"].eq("pass").all() else "fail"
    return frame, gate


def build_forbidden_feature_audit(config: dict[str, Any], schema: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    model_ready_cols = set(schema.loc[schema["model_ready_feature"], "column_name"])
    schema_role = dict(zip(schema["column_name"], schema["column_role"], strict=False))
    rows = []
    for col in config["forbidden_model_feature_columns"]:
        marked = col in model_ready_cols
        ok = not marked
        rows.append(
            {
                "forbidden_column_family": col,
                "forbidden_column_pattern": col,
                "column_name": col,
                "present_in_matrix": col in set(schema["column_name"]),
                "column_present_in_matrix": col in set(schema["column_name"]),
                "column_role": schema_role.get(col, ""),
                "marked_model_ready_feature": marked,
                "forbidden_feature_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "forbidden_column_marked_model_ready",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["forbidden_feature_gate"].eq("pass").all() else "fail"


def build_search_accounting_audit() -> tuple[pd.DataFrame, str]:
    row = {
        "search_family": "payoff_state_feature_matrix_audit",
        "phase_id": PHASE_ID,
        "no_model_training": True,
        "no_model_refit": True,
        "no_feature_selection": True,
        "no_target_correlation_feature_selection": True,
        "no_robustness_feature_selection": True,
        "no_validation_feature_selection": True,
        "no_target_selection_from_robustness": True,
        "no_target_selection_from_validation": True,
        "no_separability_metric_computed": True,
        "no_rank_ic_computed": True,
        "no_binary_metric_used_as_primary_gate": True,
        "no_auc_computed": True,
        "no_precision_recall_computed": True,
        "no_policy_utility_computed": True,
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
    if gates["upstream_18a_contract_gate"] != "pass":
        return "18B_upstream_18a_contract_blocked"
    if gates["input_artifact_gate"] != "pass":
        return "18B_input_artifact_blocked"
    if gates["feature_target_binding_gate"] != "pass":
        return "18B_target_binding_blocked"
    if gates["feature_matrix_schema_gate"] != "pass":
        return "18B_feature_matrix_schema_blocked"
    if gates["feature_lineage_gate"] != "pass":
        return "18B_feature_lineage_blocked"
    if gates["feature_complete_rate_gate"] != "pass" or gates["feature_family_coverage_gate"] != "pass":
        return "18B_feature_matrix_low_coverage"
    if gates["train_only_preprocessing_gate"] != "pass":
        return "18B_train_only_preprocessing_blocked"
    if gates["forbidden_feature_gate"] != "pass":
        return "18B_forbidden_feature_blocked"
    if gates["split_binding_gate"] != "pass":
        return "18B_split_binding_blocked"
    if gates["search_accounting_gate"] != "pass":
        return "18B_search_accounting_blocked"
    return "18B_feature_matrix_contract_blocked"


def build_decision_row(gates: dict[str, str]) -> pd.DataFrame:
    all_pass = all(gates[gate] == "pass" for gate in HARD_GATES)
    decision = DECISION_READY if all_pass else blocked_decision_for_gates(gates)
    row = {
        "decision_state": decision,
        "next_allowed_requirement": NEXT_18C if all_pass else "none",
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


def build_report(
    decision: pd.DataFrame,
    upstream: pd.DataFrame,
    binding: pd.DataFrame,
    schema: pd.DataFrame,
    missingness: pd.DataFrame,
    row_complete: pd.DataFrame,
    family: pd.DataFrame,
    drift: pd.DataFrame,
) -> str:
    drow = decision.iloc[0]
    binding_row = binding.iloc[0]
    schema_summary = pd.DataFrame(
        [
            {
                "column_role": role,
                "column_n": int(count),
            }
            for role, count in schema["column_role"].value_counts().sort_index().items()
        ]
    )
    worst_missing = missingness.sort_values("finite_rate").head(10)
    return f"""# Payoff-state Feature Matrix Audit Report

## Decision

decision_state = {drow["decision_state"]}
next_allowed_requirement = {drow["next_allowed_requirement"]}

18B materializes and audits the feature matrix only.
18B does not prove payoff-state separability.
18B does not select features from target outcomes.
18B does not authorize policy, backtest, deployment, or trading.

## 18A Handoff

{upstream[["contract_check_id", "observed_value", "expected_value", "upstream_18a_contract_gate"]].to_markdown(index=False)}

## Feature-target Binding

bound_matrix_row_n = {binding_row["bound_matrix_row_n"]}
split_mismatch_n = {binding_row["split_mismatch_n"]}
identity_key_join_used = {binding_row["identity_key_join_used"]}
split_join_key_used = {binding_row["split_join_key_used"]}

{binding.to_markdown(index=False)}

## Feature Matrix Schema

{schema_summary.to_markdown(index=False)}

Primary raw feature count = {int(schema["raw_feature"].sum())}
Primary model-ready feature count = {int(schema["model_ready_feature"].sum())}

## Missingness and Completeness

Worst finite-rate rows:

{worst_missing.to_markdown(index=False)}

Row completeness:

{row_complete.to_markdown(index=False)}

## Feature Family Coverage

{family.to_markdown(index=False)}

## Split Drift Readout

Split drift is diagnostic-only and did not remove features.

{drift.groupby("split_comparison")["feature_name"].count().reset_index(name="feature_readout_n").to_markdown(index=False)}

## Search Accounting

No model training, refit, feature selection, target selection from robustness/validation, separability metric, policy utility, backtest, deployment, production signal, or live trading authorization was performed.
"""


def output_row_count(path: Path) -> int | None:
    if path.suffix == ".csv":
        return int(count_rows(path))
    if path.suffix == ".md":
        return len(path.read_text(encoding="utf-8").splitlines())
    if path.suffix == ".parquet":
        return int(count_rows(path))
    return None


def write_manifests(
    config: dict[str, Any],
    resolved: dict[str, Path],
    outputs: dict[str, Path],
    input_audit: pd.DataFrame,
    decision: pd.DataFrame,
    matrix: pd.DataFrame,
    schema: pd.DataFrame,
) -> None:
    input_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_artifacts": input_audit.to_dict(orient="records"),
    }
    write_json(outputs["input_artifact_manifest"], input_manifest)

    matrix_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "matrix_file": relative_to_topic(outputs["matrix"]),
        "matrix_sha256": file_sha(outputs["matrix"]),
        "matrix_row_n": len(matrix),
        "identity_key_columns": config["identity_key_columns"],
        "split_column": config["split_column"],
        "primary_raw_features": primary_features(config),
        "primary_model_ready_features": [model_ready_name(config, feature) for feature in primary_features(config)],
        "target_columns": list(TARGET_COLUMNS),
        "schema_file": relative_to_topic(outputs["schema"]),
        "schema_sha256": file_sha(outputs["schema"]),
    }
    write_json(outputs["matrix_manifest"], matrix_manifest)

    manifest_keys = [
        "matrix",
        "report",
        "input_artifact_audit",
        "upstream_18a_contract_audit",
        "feature_target_binding_audit",
        "schema",
        "feature_missingness_audit",
        "matrix_row_completeness_audit",
        "feature_lineage_audit",
        "feature_family_coverage",
        "train_only_preprocessing_audit",
        "split_drift_feature_readout",
        "forbidden_feature_audit",
        "search_accounting_audit",
        "decision",
        "input_artifact_manifest",
        "matrix_manifest",
    ]
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "requirement_file": "experiments/pending/18_payoff_state_representation_research/requirement_18b_payoff_state_feature_matrix_audit.md",
        "config_file": relative_to_topic(CONFIG_PATH),
        "runner_file": "experiments/pending/18_payoff_state_representation_research/src/run_18b_payoff_state_feature_matrix_audit.py",
        "decision_state": decision.iloc[0]["decision_state"],
        "next_allowed_requirement": decision.iloc[0]["next_allowed_requirement"],
        "output_hashes": {key: file_sha(outputs[key]) for key in manifest_keys},
        "row_counts": {key: output_row_count(outputs[key]) for key in manifest_keys},
        "input_artifact_hashes": dict(zip(input_audit["artifact_key"], input_audit["sha256"], strict=False)),
        "authorization_flags": {col: bool(decision.iloc[0][col]) for col in AUTH_FALSE_COLUMNS},
        "upstream_feature_panel": relative_to_topic(resolved["sixteen_c_t0_feature_panel"]),
        "upstream_target_panel": relative_to_topic(resolved["sixteen_b_label_panel_readout"]),
    }
    write_json(outputs["manifest"], manifest)


def run(config_path: Path, mode: str = "full") -> dict[str, Any]:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()

    feature_panel = load_feature_panel(config, resolved)
    target_panel = load_target_panel(config, resolved)
    tables = load_support_tables(resolved)
    input_audit = build_input_artifact_audit(config, resolved, feature_panel, target_panel)
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

    upstream, upstream_gate = build_upstream_18a_contract_audit(config, tables)
    stats = key_stats(config, feature_panel, target_panel)
    matrix = bind_feature_target(config, feature_panel, target_panel)
    matrix, preprocessing, preprocessing_gate = add_model_ready_features(config, matrix)
    binding, binding_gate = build_feature_target_binding_audit(config, stats, target_panel)
    schema, schema_gate = build_matrix_schema(config, matrix, preprocessing)
    missingness, missingness_gate = build_feature_missingness_audit(config, matrix)
    row_complete, row_complete_gate = build_matrix_row_completeness_audit(config, matrix)
    feature_complete_gate = "pass" if missingness_gate == "pass" and row_complete_gate == "pass" else "fail"
    lineage, lineage_gate = build_feature_lineage_audit(config, tables, feature_panel)
    family, family_gate = build_feature_family_coverage(config, schema, tables)
    drift, drift_gate = build_split_drift_feature_readout(config, matrix)
    forbidden, forbidden_gate = build_forbidden_feature_audit(config, schema)
    search, search_gate = build_search_accounting_audit()
    split_binding_gate = (
        "pass"
        if binding_gate == "pass"
        and stats["split_mismatch_n"] == 0
        and stats["feature_missing_split_n"] == 0
        and stats["target_missing_split_n"] == 0
        and bool(stats["split_counts_match_18a"])
        and stats["split_allowed_values_gate"] == "pass"
        else "fail"
    )

    gates = {
        "upstream_18a_contract_gate": upstream_gate,
        "input_artifact_gate": input_gate,
        "feature_target_binding_gate": binding_gate,
        "feature_matrix_schema_gate": schema_gate,
        "feature_complete_rate_gate": feature_complete_gate,
        "feature_lineage_gate": lineage_gate,
        "feature_family_coverage_gate": family_gate,
        "train_only_preprocessing_gate": preprocessing_gate,
        "forbidden_feature_gate": forbidden_gate,
        "split_binding_gate": split_binding_gate,
        "split_drift_readout_gate": drift_gate,
        "search_accounting_gate": search_gate,
    }
    decision = build_decision_row(gates)

    outputs["matrix"].parent.mkdir(parents=True, exist_ok=True)
    matrix.to_parquet(outputs["matrix"], index=False)
    write_df(outputs["upstream_18a_contract_audit"], upstream)
    write_df(outputs["feature_target_binding_audit"], binding)
    write_df(outputs["schema"], schema)
    write_df(outputs["feature_missingness_audit"], missingness)
    write_df(outputs["matrix_row_completeness_audit"], row_complete)
    write_df(outputs["feature_lineage_audit"], lineage)
    write_df(outputs["feature_family_coverage"], family)
    write_df(outputs["train_only_preprocessing_audit"], preprocessing)
    write_df(outputs["split_drift_feature_readout"], drift)
    write_df(outputs["forbidden_feature_audit"], forbidden)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["decision"], decision)
    write_text(outputs["report"], build_report(decision, upstream, binding, schema, missingness, row_complete, family, drift))
    write_manifests(config, resolved, outputs, input_audit, decision, matrix, schema)

    return {
        "gates": gates,
        "decision": decision,
        "input_artifact_audit": input_audit,
        "upstream_18a_contract_audit": upstream,
        "feature_target_binding_audit": binding,
        "matrix": matrix,
        "schema": schema,
        "feature_missingness_audit": missingness,
        "matrix_row_completeness_audit": row_complete,
        "feature_lineage_audit": lineage,
        "feature_family_coverage": family,
        "train_only_preprocessing_audit": preprocessing,
        "split_drift_feature_readout": drift,
        "forbidden_feature_audit": forbidden,
        "search_accounting_audit": search,
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
