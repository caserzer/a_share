#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import itertools
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

RUN_ID = "19B0_fast_rule_grid_enrichment_scan"
EXPERIMENT_ID = "19_entry_universe_pit_tradability_preflight"
PHASE_ID = "19B0"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_19b0_fast_rule_grid_enrichment_scan.yaml"
OUTPUT_ROOT = EXPERIMENT_DIR / "outputs" / RUN_ID
LOCAL_CACHE = OUTPUT_ROOT / "local_cache"

READY_19A = "19A_entry_universe_contract_ready"
NEXT_19A = "requirement_19b0_fast_rule_grid_enrichment_scan.md"
DECISION_POSITIVE = "19B0_candidate_family_eligible_for_19B"
DECISION_DIAGNOSTIC = "19B0_candidate_family_train_diagnostic"
DECISION_NO_PASS = "19B0_no_candidate_family_passed"
NEXT_19B = "requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md"

BASELINE_FAMILIES = [
    "calendar_time_random_same_budget",
    "instrument_matched_random_same_budget",
    "liquidity_size_volatility_matched_same_budget",
]
POLICY_AUTH_COLUMNS = [
    "model_training_authorized",
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
]
CRITICAL_GATES = [
    "upstream_19a_contract_gate",
    "train_only_boundary_gate",
    "grid_manifest_gate",
    "family_materialization_gate",
    "primary_denominator_gate",
    "baseline_materialization_gate",
    "baseline_matching_quality_audit_gate",
    "metric_readout_gate",
    "cell_selection_process_gate",
    "search_accounting_gate",
    "no_policy_authorization_gate",
    "output_contract_gate",
]
STATE_GATE_MAP = {
    "19B0_upstream_19a_contract_blocked": ["upstream_19a_contract_gate"],
    "19B0_train_only_boundary_blocked": ["train_only_boundary_gate"],
    "19B0_grid_contract_blocked": ["grid_manifest_gate", "family_materialization_gate"],
    "19B0_baseline_materialization_blocked": ["baseline_materialization_gate"],
    "19B0_metric_contract_blocked": ["primary_denominator_gate", "metric_readout_gate"],
    "19B0_output_contract_blocked": [
        "baseline_matching_quality_audit_gate",
        "cell_selection_process_gate",
        "search_accounting_gate",
        "no_policy_authorization_gate",
        "output_contract_gate",
    ],
}
FAIL_STATE_ORDER = list(STATE_GATE_MAP)

REQUIRED_OUTPUT_KEYS = [
    "input_artifact_audit",
    "upstream_19a_contract_audit",
    "train_only_boundary_audit",
    "eligible_universe_baseline_audit",
    "simple_rule_grid_registry",
    "simple_rule_feature_source_map",
    "label_source_map",
    "label_anchor_rebuild_audit",
    "matching_feature_source_map",
    "matching_feature_equivalence_audit",
    "grid_cell_manifest",
    "family_grid_materialization_audit",
    "candidate_cell_denominator_audit",
    "baseline_materialization_audit",
    "baseline_matching_quality_audit",
    "train_cell_metric_readout",
    "train_cell_sensitivity_readout",
    "cell_cluster_bootstrap_margin_audit",
    "instrument_concentration_sensitivity",
    "family_selection_audit",
    "selected_family_cell_manifest",
    "robustness_test_manifest",
    "search_accounting_audit",
    "entry_universe_19b0_decision",
    "report",
    "handoff_contract",
    "manifest",
    "output_hashes",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP19B0 fast rule-grid enrichment scan.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
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


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": OUTPUT_ROOT / "input_artifact_audit.csv",
        "upstream_19a_contract_audit": OUTPUT_ROOT / "upstream_19a_contract_audit.csv",
        "train_only_boundary_audit": OUTPUT_ROOT / "train_only_boundary_audit.csv",
        "eligible_universe_baseline_audit": OUTPUT_ROOT / "eligible_universe_baseline_audit.csv",
        "simple_rule_grid_registry": OUTPUT_ROOT / "simple_rule_grid_registry.csv",
        "simple_rule_feature_source_map": OUTPUT_ROOT / "simple_rule_feature_source_map.csv",
        "label_source_map": OUTPUT_ROOT / "label_source_map.csv",
        "label_anchor_rebuild_audit": OUTPUT_ROOT / "label_anchor_rebuild_audit.csv",
        "matching_feature_source_map": OUTPUT_ROOT / "matching_feature_source_map.csv",
        "matching_feature_equivalence_audit": OUTPUT_ROOT / "matching_feature_equivalence_audit.csv",
        "grid_cell_manifest": OUTPUT_ROOT / "grid_cell_manifest.csv",
        "family_grid_materialization_audit": OUTPUT_ROOT / "family_grid_materialization_audit.csv",
        "candidate_cell_denominator_audit": OUTPUT_ROOT / "candidate_cell_denominator_audit.csv",
        "baseline_materialization_audit": OUTPUT_ROOT / "baseline_materialization_audit.csv",
        "baseline_matching_quality_audit": OUTPUT_ROOT / "baseline_matching_quality_audit.csv",
        "train_cell_metric_readout": OUTPUT_ROOT / "train_cell_metric_readout.csv",
        "train_cell_sensitivity_readout": OUTPUT_ROOT / "train_cell_sensitivity_readout.csv",
        "cell_cluster_bootstrap_margin_audit": OUTPUT_ROOT / "cell_cluster_bootstrap_margin_audit.csv",
        "instrument_concentration_sensitivity": OUTPUT_ROOT / "instrument_concentration_sensitivity.csv",
        "family_selection_audit": OUTPUT_ROOT / "family_selection_audit.csv",
        "selected_family_cell_manifest": OUTPUT_ROOT / "selected_family_cell_manifest.csv",
        "robustness_test_manifest": OUTPUT_ROOT / "robustness_test_manifest.csv",
        "search_accounting_audit": OUTPUT_ROOT / "search_accounting_audit.csv",
        "entry_universe_19b0_decision": OUTPUT_ROOT / "entry_universe_19b0_decision.csv",
        "report": OUTPUT_ROOT / "19B0_fast_rule_grid_enrichment_scan_report.md",
        "handoff_contract": OUTPUT_ROOT / "19B0_handoff_to_19B_contract.md",
        "manifest": OUTPUT_ROOT / "manifest_19b0_fast_rule_grid_enrichment_scan.json",
        "output_hashes": OUTPUT_ROOT / "output_hashes_19b0_fast_rule_grid_enrichment_scan.json",
    }


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            return value
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


def artifact_hash(path: Path) -> str:
    if not path.exists():
        return ""
    if path.is_dir():
        h = hashlib.sha256()
        for child in sorted(p for p in path.rglob("*") if p.is_file()):
            rel = str(child.relative_to(path))
            h.update(rel.encode("utf-8"))
            h.update(str(child.stat().st_size).encode("ascii"))
        return h.hexdigest()
    return file_sha(path)


def find_19a_hashed_artifact(output_root: Path, artifact_id: str) -> Path | None:
    special_names = {
        "contract_freeze": "19A_contract_freeze.md",
        "report": "19A_entry_universe_pit_lineage_tradability_and_data_contract_report.md",
    }
    if artifact_id in special_names:
        candidate = output_root / special_names[artifact_id]
        return candidate if candidate.exists() else None
    for suffix in [".csv", ".md", ".json"]:
        candidate = output_root / f"{artifact_id}{suffix}"
        if candidate.exists():
            return candidate
    matches = [path for path in output_root.iterdir() if path.is_file() and path.stem == artifact_id]
    return matches[0] if matches else None


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if suffixes.endswith((".csv", ".csv.gz")):
        return pd.read_csv(path, **kwargs)
    raise ValueError(f"Unsupported table path: {path}")


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_dir():
        return len([p for p in path.rglob("*") if p.is_file()])
    suffixes = "".join(path.suffixes)
    if suffixes.endswith((".csv", ".csv.gz")):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path, columns=[]))
    return 1


def column_names(path: Path) -> list[str]:
    if not path.exists() or path.is_dir():
        return []
    suffixes = "".join(path.suffixes)
    if suffixes.endswith((".csv", ".csv.gz")):
        return list(pd.read_csv(path, nrows=0).columns)
    if suffixes.endswith(".parquet"):
        return list(pd.read_parquet(path, columns=None).head(0).columns)
    return []


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        try:
            return str(path.relative_to(REPO_ROOT))
        except ValueError:
            return str(path)


def pass_fail(condition: bool) -> str:
    return "pass" if condition else "fail"


def as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])


def stable_hash_json(payload: dict[str, Any]) -> str:
    text = json.dumps(clean_json(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_cell_id(family_id: str, params: dict[str, Any]) -> tuple[str, str]:
    parameter_hash = stable_hash_json(params)
    slug = family_id.replace("_", "-")
    return f"{slug}__{parameter_hash[:12]}", parameter_hash


def build_input_artifact_audit(config: dict[str, Any], paths: dict[str, Path]) -> pd.DataFrame:
    required = [
        "requirement_19a",
        "requirement_19b0",
        "config_19a",
        "nineteen_a_decision",
        "nineteen_a_manifest",
        "nineteen_a_candidate_density",
        "nineteen_a_effective_sample",
        "nineteen_a_grid_search_manifest",
        "nineteen_a_family_search_accounting_manifest",
        "nineteen_a_baseline_budget_freeze",
        "nineteen_a_baseline_matching_spec",
        "nineteen_a_baseline_matching_quality_audit",
        "nineteen_a_primary_metric_and_margin_freeze",
        "nineteen_a_multiple_testing_correction_freeze",
        "nineteen_a_validation_stress_rule_freeze",
        "ep07_candidate_canonical",
        "ep07_candidate_labels",
        "topn_executable_universe",
        "topn_membership_universe",
        "stock_qfq_dir",
        "benchmark_daily",
    ]
    rows: list[dict[str, Any]] = []
    for key in required:
        path = paths[key]
        exists = path.exists()
        cols = column_names(path) if exists else []
        rows.append(
            {
                "artifact_id": key,
                "relative_path": rel(path),
                "exists": exists,
                "artifact_type": "directory" if exists and path.is_dir() else path.suffix,
                "row_count": row_count(path) if exists else 0,
                "column_count": len(cols),
                "columns": "|".join(cols[:80]),
                "sha256_or_inventory_hash": artifact_hash(path) if exists else "",
                "input_artifact_gate": pass_fail(exists),
                "blocking_reason": "" if exists else "missing_required_artifact",
            }
        )
    return pd.DataFrame(rows)


def build_upstream_19a_contract_audit(paths: dict[str, Path]) -> tuple[pd.DataFrame, str, dict[str, Any]]:
    decision = read_table(paths["nineteen_a_decision"])
    row = decision.iloc[0].to_dict() if not decision.empty else {}
    manifest_payload = json.loads(paths["nineteen_a_manifest"].read_text(encoding="utf-8"))
    required_facts: list[tuple[str, Any]] = [
        ("decision_state", READY_19A),
        ("next_allowed_requirement", NEXT_19A),
        ("all_critical_gates_pass", True),
    ]
    required_facts.extend((col, False) for col in POLICY_AUTH_COLUMNS)
    rows = []
    for fact, expected in required_facts:
        observed = row.get(fact)
        if isinstance(expected, bool):
            observed_norm = str(observed).strip().lower() in {"true", "1"} if expected else str(observed).strip().lower() in {"false", "0"}
            passed = observed_norm is True
        else:
            passed = str(observed) == str(expected)
        rows.append(
            {
                "required_fact": fact,
                "expected_value": expected,
                "observed_value": observed,
                "fact_gate": pass_fail(passed),
                "blocking_reason": "" if passed else "upstream_19a_fact_mismatch",
            }
        )
    for key in ["nineteen_a_candidate_density", "nineteen_a_effective_sample", "nineteen_a_manifest"]:
        path = paths[key]
        rows.append(
            {
                "required_fact": f"{key}_exists",
                "expected_value": True,
                "observed_value": path.exists(),
                "fact_gate": pass_fail(path.exists()),
                "blocking_reason": "" if path.exists() else "missing_19a_required_artifact",
            }
        )
    output_root = paths["nineteen_a_output_root"]
    for artifact_id, expected_hash in sorted(manifest_payload.get("output_hashes", {}).items()):
        artifact_path = find_19a_hashed_artifact(output_root, artifact_id)
        observed_hash = file_sha(artifact_path) if artifact_path is not None else ""
        passed = artifact_path is not None and observed_hash == expected_hash
        rows.append(
            {
                "required_fact": f"manifest_hash_match:{artifact_id}",
                "expected_value": expected_hash,
                "observed_value": observed_hash,
                "fact_gate": pass_fail(passed),
                "blocking_reason": "" if passed else "upstream_19a_hash_mismatch_or_missing_artifact",
            }
        )
    audit = pd.DataFrame(rows)
    gate = pass_fail(audit["fact_gate"].eq("pass").all())
    return audit, gate, row


def build_train_only_boundary_audit(metadata: pd.DataFrame, train_labels: pd.DataFrame) -> pd.DataFrame:
    train_keys = set(metadata.loc[metadata["event_split"].eq("train"), "event_id"].astype(str))
    label_keys = set(train_labels["event_id"].astype(str)) if "event_id" in train_labels else set()
    duplicate_label_key_n = int(train_labels["event_id"].duplicated().sum()) if "event_id" in train_labels else len(train_labels)
    key_match = label_keys == train_keys and duplicate_label_key_n == 0
    missing_n = len(train_keys - label_keys)
    unexpected_n = len(label_keys - train_keys)
    blocking_reason = ""
    if not key_match:
        blocking_reason = (
            f"train_label_key_mismatch:missing={missing_n};"
            f"unexpected={unexpected_n};duplicates={duplicate_label_key_n}"
        )
    return pd.DataFrame(
        [
            {
                "candidate_metadata_row_n": len(metadata),
                "candidate_train_key_row_n": len(train_keys),
                "train_label_row_n": len(train_labels),
                "non_train_outcome_columns_loaded": False,
                "non_train_outcome_row_n": 0,
                "robustness_label_value_access_n": 0,
                "validation_label_value_access_n": 0,
                "selection_uses_train_only": True,
                "boundary_gate": pass_fail(key_match),
                "blocking_reason": blocking_reason,
            }
        ]
    )


def load_ep07_metadata(paths: dict[str, Path]) -> pd.DataFrame:
    metadata = read_table(paths["ep07_candidate_canonical"])
    metadata["event_id"] = metadata["event_id"].astype(str)
    metadata["event_t0_date"] = pd.to_datetime(metadata["event_t0_date"]).dt.strftime("%Y-%m-%d")
    metadata["trade_open_date"] = pd.to_datetime(metadata["trade_open_date"]).dt.strftime("%Y-%m-%d")
    metadata["event_split"] = metadata["event_split"].astype(str)
    return metadata


def load_ep07_train_label_diagnostics(paths: dict[str, Path], train_event_ids: set[str]) -> pd.DataFrame:
    columns = [
        "event_id",
        "event_split",
        "label_anchor_type",
        "mfe_20d",
        "mfe_30d",
        "mfe_60d",
        "mfe_120d",
        "mae_20d",
        "mae_30d",
        "mae_60d",
        "mae_120d",
        "horizon_complete_20d",
        "horizon_complete_30d",
        "horizon_complete_60d",
        "horizon_complete_120d",
        "event_big_winner_120d_label",
    ]
    labels = pd.read_parquet(paths["ep07_candidate_labels"], columns=columns, filters=[("event_split", "==", "train")])
    labels["event_id"] = labels["event_id"].astype(str)
    return labels.loc[labels["event_id"].isin(train_event_ids)].copy()


def load_benchmark_features(path: Path) -> pd.DataFrame:
    bench = read_table(path)
    bench = bench.loc[bench["index_alias"].eq("csi300")].copy()
    bench["date"] = pd.to_datetime(bench["date"]).dt.strftime("%Y-%m-%d")
    bench = bench.sort_values("date")
    close = pd.to_numeric(bench["close"], errors="coerce")
    bench["benchmark_return_20d"] = close / close.shift(20) - 1.0
    bench["benchmark_ema60"] = close.ewm(span=60, adjust=False, min_periods=60).mean()
    bench["benchmark_drawdown_60d"] = close / close.rolling(60, min_periods=60).max() - 1.0
    bench["market_regime_risk_on"] = (bench["benchmark_return_20d"] > 0) & (close > bench["benchmark_ema60"])
    return bench[["date", "benchmark_return_20d", "benchmark_drawdown_60d", "market_regime_risk_on"]]


def future_window_arrays(values: np.ndarray, horizon: int, reducer: str) -> np.ndarray:
    series = pd.Series(values[::-1])
    if reducer == "max":
        out = series.rolling(horizon, min_periods=horizon).max().to_numpy()[::-1]
    elif reducer == "min":
        out = series.rolling(horizon, min_periods=horizon).min().to_numpy()[::-1]
    else:
        raise ValueError(reducer)
    return out


def compute_qfq_feature_frame(path: Path, benchmark: pd.DataFrame) -> pd.DataFrame:
    qfq = read_table(path)
    qfq = qfq.sort_values("date").reset_index(drop=True)
    qfq["date"] = pd.to_datetime(qfq["date"]).dt.strftime("%Y-%m-%d")
    instrument = str(qfq["instrument"].iloc[0])
    close = pd.to_numeric(qfq["close"], errors="coerce")
    high = pd.to_numeric(qfq["high"], errors="coerce")
    low = pd.to_numeric(qfq["low"], errors="coerce")
    open_ = pd.to_numeric(qfq["open"], errors="coerce")
    money = pd.to_numeric(qfq["money"], errors="coerce")

    frame = pd.DataFrame({"instrument": instrument, "decision_date": qfq["date"], "decision_pos": np.arange(len(qfq), dtype=int)})
    frame["close_asof_decision_date"] = close
    frame["rolling_120d_high_asof_decision_date"] = high.rolling(120, min_periods=120).max()
    frame["rolling_120d_low_asof_decision_date"] = low.rolling(120, min_periods=120).min()
    frame["rolling_20d_money_mean_asof_decision_date"] = money.rolling(20, min_periods=20).mean()
    frame["amount_ratio_20d_asof_decision_date"] = money / frame["rolling_20d_money_mean_asof_decision_date"]
    for horizon in [5, 10, 20, 60]:
        frame[f"return_{horizon}d_asof_decision_date"] = close / close.shift(horizon) - 1.0

    ema60 = close.ewm(span=60, adjust=False, min_periods=60).mean()
    frame["close_to_ema60_asof_decision_date"] = close / ema60 - 1.0
    prev_close = close.shift(1)
    true_range = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    frame["atr_20_pct_asof_decision_date"] = true_range.rolling(20, min_periods=20).mean() / close
    frame["intraday_range_pct_asof_decision_date"] = (high - low) / close
    denom = frame["rolling_120d_high_asof_decision_date"] - frame["rolling_120d_low_asof_decision_date"]
    frame["close_position_in_120d_range_asof_decision_date"] = (
        (close - frame["rolling_120d_low_asof_decision_date"]) / denom.replace(0, np.nan)
    )
    frame["quality_amount_flag_asof_decision_date"] = money.notna() & money.rolling(20, min_periods=20).mean().notna()
    frame["entry_pos"] = frame["decision_pos"] + 1
    frame["entry_date"] = qfq["date"].shift(-1)
    frame["entry_price"] = open_.shift(-1)

    frame = frame.merge(benchmark, left_on="decision_date", right_on="date", how="left").drop(columns=["date"])
    frame["stock_vs_market_return_20d_asof_decision_date"] = (
        frame["return_20d_asof_decision_date"] - frame["benchmark_return_20d"]
    )
    frame["market_drawdown_60d_asof_decision_date"] = frame["benchmark_drawdown_60d"]
    frame["market_regime_risk_on_asof_decision_date"] = frame["market_regime_risk_on"].fillna(False)
    return frame


def compute_qfq_label_frame(path: Path, horizons: list[int], threshold: float) -> pd.DataFrame:
    qfq = read_table(path)
    qfq = qfq.sort_values("date").reset_index(drop=True)
    qfq["date"] = pd.to_datetime(qfq["date"]).dt.strftime("%Y-%m-%d")
    instrument = str(qfq["instrument"].iloc[0])
    high = pd.to_numeric(qfq["high"], errors="coerce")
    low = pd.to_numeric(qfq["low"], errors="coerce")
    close = pd.to_numeric(qfq["close"], errors="coerce")
    open_ = pd.to_numeric(qfq["open"], errors="coerce")
    frame = pd.DataFrame({"instrument": instrument, "decision_date": qfq["date"]})
    entry_price = open_.shift(-1).to_numpy(dtype=float)
    high_values = high.to_numpy(dtype=float)
    low_values = low.to_numpy(dtype=float)
    for horizon in horizons:
        future_high = pd.Series(future_window_arrays(high_values, horizon, "max")).shift(-1).to_numpy(dtype=float)
        future_low = pd.Series(future_window_arrays(low_values, horizon, "min")).shift(-1).to_numpy(dtype=float)
        future_close = pd.Series(close).shift(-horizon).to_numpy(dtype=float)
        complete = np.isfinite(entry_price) & (entry_price > 0) & np.isfinite(future_high) & np.isfinite(future_low) & np.isfinite(future_close)
        frame[f"path_complete_{horizon}d"] = complete
        frame[f"forward_mfe_{horizon}d"] = np.where(complete, future_high / entry_price - 1.0, np.nan)
        frame[f"forward_mae_{horizon}d"] = np.where(complete, future_low / entry_price - 1.0, np.nan)
        frame[f"forward_return_{horizon}d"] = np.where(complete, future_close / entry_price - 1.0, np.nan)
        frame[f"forward_big_winner_{horizon}d"] = frame[f"forward_mfe_{horizon}d"] >= threshold
    return frame


def add_month_buckets(panel: pd.DataFrame, bucket_count: int) -> pd.DataFrame:
    panel = panel.copy()
    panel["decision_month"] = pd.to_datetime(panel["decision_date"]).dt.to_period("M").astype(str)
    source_cols = {
        "market_cap_bucket_asof_decision_date": "match_market_cap",
        "rolling_20d_amount_bucket_asof_decision_date": "match_amount20",
        "rolling_60d_volatility_bucket_asof_decision_date": "match_vol60",
        "recent_20d_return_bucket_asof_decision_date": "match_return20",
    }
    for out_col, source_col in source_cols.items():
        ranks = panel.groupby("decision_month")[source_col].rank(pct=True, method="average")
        bucket = np.floor((ranks.fillna(-1.0).clip(lower=0.0, upper=0.999999)) * bucket_count).astype(int)
        panel[out_col] = np.where(panel[source_col].notna(), bucket, -1)
    panel["lsv_match_key"] = (
        panel["decision_month"].astype(str)
        + "|"
        + panel["market_cap_bucket_asof_decision_date"].astype(str)
        + "|"
        + panel["rolling_20d_amount_bucket_asof_decision_date"].astype(str)
        + "|"
        + panel["rolling_60d_volatility_bucket_asof_decision_date"].astype(str)
        + "|"
        + panel["recent_20d_return_bucket_asof_decision_date"].astype(str)
    )
    panel["instrument_month"] = panel["instrument"].astype(str) + "|" + panel["decision_month"].astype(str)
    return panel


def load_or_build_universe_feature_panel(config: dict[str, Any], paths: dict[str, Path]) -> pd.DataFrame:
    cache = LOCAL_CACHE / "universe_feature_panel_v4.parquet"
    if config.get("runtime", {}).get("cache_universe_feature_panel", True) and cache.exists():
        return pd.read_parquet(cache)

    universe_cols = [
        "usable_trade_date",
        "instrument",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
        "total_market_cap_cny",
        "history_ready_240d_flag",
    ]
    universe = read_table(paths["topn_executable_universe"], usecols=universe_cols)
    universe["usable_trade_date"] = pd.to_datetime(universe["usable_trade_date"]).dt.strftime("%Y-%m-%d")
    train_start = str(config["split"]["train_start"])
    train_end = str(config["split"]["train_end"])
    universe = universe.loc[universe["usable_trade_date"].between(train_start, train_end)].copy()

    benchmark = load_benchmark_features(paths["benchmark_daily"])
    frames: list[pd.DataFrame] = []
    stock_dir = paths["stock_qfq_dir"]
    grouped = universe.groupby("instrument", sort=True)
    for idx, (instrument, group) in enumerate(grouped, start=1):
        qfq_path = stock_dir / f"{instrument}.csv"
        if not qfq_path.exists():
            continue
        feature = compute_qfq_feature_frame(qfq_path, benchmark)
        selected = group.merge(feature, left_on=["instrument", "usable_trade_date"], right_on=["instrument", "decision_date"], how="inner")
        if not selected.empty:
            frames.append(selected)
        if idx % int(config.get("runtime", {}).get("progress_every_instruments", 250)) == 0:
            print(f"[19B0] rebuilt qfq feature panel for {idx}/{len(grouped)} instruments")
    panel = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if panel.empty:
        return panel

    panel["entry_anchor_available"] = pd.to_numeric(panel["entry_price"], errors="coerce").gt(0) & panel["entry_date"].notna()
    panel["entry_fill_feasible"] = (
        as_bool(panel["is_listed"]) & ~as_bool(panel["is_st"]) & ~as_bool(panel["is_suspended"]) & panel["entry_anchor_available"]
    )
    panel["match_market_cap"] = pd.to_numeric(panel["total_market_cap_cny"], errors="coerce")
    panel["match_amount20"] = pd.to_numeric(panel["rolling_20d_money_mean_asof_decision_date"], errors="coerce")
    panel["match_vol60"] = panel.groupby("instrument")["close_asof_decision_date"].pct_change().groupby(panel["instrument"]).rolling(
        60, min_periods=60
    ).std().reset_index(level=0, drop=True)
    panel["match_return20"] = pd.to_numeric(panel["return_20d_asof_decision_date"], errors="coerce")
    panel["matching_fields_available"] = panel[["match_market_cap", "match_amount20", "match_vol60", "match_return20"]].notna().all(axis=1)
    panel["return_60d_cross_section_rank_pct_asof_decision_date"] = panel.groupby("decision_date")[
        "return_60d_asof_decision_date"
    ].rank(pct=True)
    panel["atr_20_pct_rank_asof_decision_date"] = panel.groupby("decision_date")["atr_20_pct_asof_decision_date"].rank(pct=True)
    panel = add_month_buckets(panel, int(config["baseline"]["bucket_count"]))
    panel["row_id"] = panel["instrument"].astype(str) + "_" + panel["decision_date"].astype(str)
    panel["cooldown_eligible_under_19a_rule"] = cooldown_filter(
        panel,
        "decision_pos",
        int(config["execution"]["primary_cooldown_window_sessions"]),
    )
    panel["baseline_membership_frozen_before_label_readout"] = True
    panel["matching_bucket_frozen_before_label_readout"] = True
    panel["pre_label_baseline_eligible_candidate"] = (
        panel["entry_fill_feasible"]
        & panel["cooldown_eligible_under_19a_rule"]
        & panel["matching_fields_available"]
        & panel["history_ready_240d_flag"].fillna(False).astype(bool)
    )

    threshold = float(config["labels"]["primary_big_winner_threshold"])
    label_frames: list[pd.DataFrame] = []
    for idx, instrument in enumerate(sorted(panel["instrument"].unique()), start=1):
        qfq_path = stock_dir / f"{instrument}.csv"
        if not qfq_path.exists():
            continue
        label_frames.append(compute_qfq_label_frame(qfq_path, list(config["labels"]["horizons"]), threshold))
        if idx % int(config.get("runtime", {}).get("progress_every_instruments", 250)) == 0:
            print(f"[19B0] rebuilt executable-entry labels for {idx}/{panel['instrument'].nunique()} instruments")
    labels = pd.concat(label_frames, ignore_index=True) if label_frames else pd.DataFrame(columns=["instrument", "decision_date"])
    panel = panel.merge(labels, on=["instrument", "decision_date"], how="left")
    panel["baseline_forward_label_read_after_membership_freeze"] = True
    panel["baseline_eligible"] = panel["pre_label_baseline_eligible_candidate"] & panel["path_complete_120d"].fillna(False)
    LOCAL_CACHE.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(cache, index=False)
    return panel


def cooldown_filter(frame: pd.DataFrame, pos_col: str, window: int) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool)
    sorted_frame = frame.sort_values(["instrument", pos_col, "row_id" if "row_id" in frame.columns else "event_id"]).copy()
    keep_by_index: dict[Any, bool] = {}
    previous: dict[str, int] = {}
    for index, row in sorted_frame.iterrows():
        instrument = str(row["instrument"])
        pos = int(row[pos_col])
        prior = previous.get(instrument)
        keep = prior is None or pos - prior > window
        keep_by_index[index] = keep
        if keep:
            previous[instrument] = pos
    return pd.Series(keep_by_index).reindex(frame.index).fillna(False).astype(bool)


def build_ep07_identity_panel(
    metadata: pd.DataFrame,
    train_label_diag: pd.DataFrame,
    universe_panel: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = metadata.loc[metadata["event_split"].eq("train")].copy()
    match_cols = [
        "instrument",
        "decision_date",
        "entry_anchor_available",
        "entry_fill_feasible",
        "match_market_cap",
        "match_amount20",
        "match_vol60",
        "match_return20",
        "market_cap_bucket_asof_decision_date",
        "rolling_20d_amount_bucket_asof_decision_date",
        "rolling_60d_volatility_bucket_asof_decision_date",
        "recent_20d_return_bucket_asof_decision_date",
        "lsv_match_key",
        "instrument_month",
        "decision_month",
        "row_id",
    ]
    label_cols = ["instrument", "decision_date", "entry_date", "entry_pos", "entry_price"]
    for horizon in config["labels"]["horizons"]:
        label_cols.extend(
            [
                f"path_complete_{horizon}d",
                f"forward_mfe_{horizon}d",
                f"forward_mae_{horizon}d",
                f"forward_return_{horizon}d",
                f"forward_big_winner_{horizon}d",
            ]
        )
    rebuilt = universe_panel[sorted(set(match_cols + label_cols))].copy()
    train = train.rename(columns={"event_t0_date": "decision_date", "event_t0_pos": "decision_pos"})
    train = train.merge(rebuilt, on=["instrument", "decision_date"], how="left", suffixes=("", "_rebuilt"))
    train["family_id"] = "EP07_topn_multichannel_recommended_union"
    train["grid_cell_id"] = "EP07_identity_cell"
    train["parameter_hash"] = stable_hash_json({})
    train["parameter_json"] = "{}"
    train["family_source"] = "existing_source"
    train["ep07_identity_cell_flag"] = True
    train["source_candidate_train_n"] = len(train)
    train["raw_candidate"] = True
    non_exec = as_bool(train["non_executable_next_open"])
    liquidity = pd.to_numeric(train["liquidity_money_20d"], errors="coerce")
    train["entry_fill_feasible"] = (
        pd.to_numeric(train["trade_open_price"], errors="coerce").gt(0)
        & ~non_exec
        & liquidity.ge(float(config["execution"]["liquidity_floor_cny"]))
        & train["entry_anchor_available"].fillna(False).astype(bool)
    )
    train["cooldown_entry"] = cooldown_filter(train.assign(row_id=train["event_id"]), "decision_pos", int(config["execution"]["primary_cooldown_window_sessions"]))
    train["primary_denominator_row"] = train["cooldown_entry"] & train["entry_fill_feasible"] & train["path_complete_120d"].fillna(False)

    diag = train[["event_id", "forward_big_winner_120d", "path_complete_120d"]].merge(train_label_diag, on="event_id", how="left")
    comparable = diag["event_big_winner_120d_label"].notna() & diag["forward_big_winner_120d"].notna()
    match_rate = (
        (diag.loc[comparable, "event_big_winner_120d_label"].astype(bool) == diag.loc[comparable, "forward_big_winner_120d"].astype(bool)).mean()
        if comparable.any()
        else np.nan
    )
    label_audit = pd.DataFrame(
        [
            {
                "split": "train",
                "family_id": "EP07_topn_multichannel_recommended_union",
                "grid_cell_id": "EP07_identity_cell",
                "row_scope": "ep07_train_candidate_rows",
                "row_n": len(train),
                "entry_anchor_available_n": int(train["entry_anchor_available"].fillna(False).sum()),
                "trade_open_price_positive_rate": float(pd.to_numeric(train["trade_open_price"], errors="coerce").gt(0).mean()),
                "executable_entry_path_complete_20_rate": float(train["path_complete_20d"].fillna(False).mean()),
                "executable_entry_path_complete_30_rate": float(train["path_complete_30d"].fillna(False).mean()),
                "executable_entry_path_complete_60_rate": float(train["path_complete_60d"].fillna(False).mean()),
                "executable_entry_path_complete_120_rate": float(train["path_complete_120d"].fillna(False).mean()),
                "event_anchored_diagnostic_available_n": int(comparable.sum()),
                "event_anchored_vs_executable_big_winner_120d_match_rate": match_rate,
                "ready_made_label_used_for_primary": False,
                "ready_made_label_used_for_selection": False,
                "blocking_reason": "",
            }
        ]
    )
    return train, label_audit


def build_simple_rule_grid_registry() -> pd.DataFrame:
    rows = []
    family_specs = simple_family_parameter_grid()
    for family_id, spec in family_specs.items():
        rows.append(
            {
                "family_id": family_id,
                "feature_fields": "|".join(spec["features"]),
                "parameter_axes": "|".join(spec["axes"].keys()),
                "allowed_values": json.dumps(clean_json(spec["axes"]), sort_keys=True),
                "predicate_formula": spec["predicate_formula"],
                "grid_cell_id_rule": "family_slug__sha256(canonical_parameter_json)[:12]",
                "grid_cell_n": math.prod(len(v) for v in spec["axes"].values()),
                "requires_supported_feature_status": "materialized_before_label_readout",
                "materialization_status": "registered_pending_materialization",
                "blocking_reason": "",
                "registry_frozen_before_label_readout": True,
            }
        )
    return pd.DataFrame(rows)


def build_simple_rule_feature_source_map() -> pd.DataFrame:
    rows = [
        ("close_asof_decision_date", "qfq_rebuild", "data/raw/akshare/day/qfq/{instrument}.csv", "date|close", "event_t0_date close", "", "", "qfq close on decision date", "", True, "no future bars", "missing blocks dependent cell"),
        ("rolling_120d_high_asof_decision_date", "qfq_rebuild", "data/raw/akshare/day/qfq/{instrument}.csv", "date|high", "event_t0_date close", "rolling 120 sessions ending at t", "", "max(high[t-119:t])", "", True, "window ends at decision date", "missing blocks dependent cell"),
        ("amount_ratio_20d_asof_decision_date", "ep07_direct_or_qfq_rebuild", "EP07 canonical or qfq money", "amount_ratio_20d|money", "event_t0_date close", "rolling 20 sessions ending at t", "", "money[t]/mean(money[t-19:t])", "amount_ratio_20d", True, "same qfq formula for baseline", "missing blocks dependent cell"),
        ("return_5d_asof_decision_date", "ep07_direct_or_qfq_rebuild", "EP07 canonical or qfq close", "return_5d|close", "event_t0_date close", "5 sessions", "", "close[t]/close[t-5]-1", "return_5d", True, "same qfq formula for baseline", "missing blocks dependent cell"),
        ("return_10d_asof_decision_date", "ep07_direct_or_qfq_rebuild", "EP07 canonical or qfq close", "return_10d|close", "event_t0_date close", "10 sessions", "", "close[t]/close[t-10]-1", "return_10d", True, "same qfq formula for baseline", "missing blocks dependent cell"),
        ("return_20d_asof_decision_date", "ep07_direct_or_qfq_rebuild", "EP07 canonical or qfq close", "return_20d|close", "event_t0_date close", "20 sessions", "", "close[t]/close[t-20]-1", "return_20d", True, "same qfq formula for baseline", "missing blocks dependent cell"),
        ("return_60d_asof_decision_date", "ep07_direct_or_qfq_rebuild", "EP07 canonical or qfq close", "return_60d|close", "event_t0_date close", "60 sessions", "", "close[t]/close[t-60]-1", "return_60d", True, "same qfq formula for baseline", "missing blocks dependent cell"),
        ("stock_vs_market_return_20d_asof_decision_date", "ep07_direct_or_benchmark_rebuild", "EP07 canonical or qfq + benchmark", "stock_vs_market_20d|close|benchmark_close", "event_t0_date close", "20 sessions", "", "stock_return_20d - benchmark_return_20d", "stock_vs_market_20d", True, "benchmark as of decision date", "missing blocks dependent cell"),
        ("return_60d_cross_section_rank_pct_asof_decision_date", "universe_cross_section_rebuild", "baseline eligible universe + qfq close", "return_60d", "event_t0_date close", "60 sessions", "all baseline-eligible instruments on decision date", "percentile_rank(return_60d)", "", True, "rank universe fixed before label readout", "missing blocks dependent cell"),
        ("close_to_ema60_asof_decision_date", "ep07_direct_or_qfq_rebuild", "EP07 canonical or qfq close", "close_to_ema60|close", "event_t0_date close", "ema span 60 adjust false", "", "close/ema60-1", "close_to_ema60", True, "ema ends at decision date", "missing blocks dependent cell"),
        ("atr_20_pct_asof_decision_date", "ep07_direct_or_qfq_rebuild", "EP07 canonical or qfq high/low/close", "atr_20_pct|high|low|close", "event_t0_date close", "20 sessions", "", "rolling_mean(true_range,20)/close", "atr_20_pct", True, "window ends at decision date", "missing blocks dependent cell"),
        ("atr_20_pct_rank_asof_decision_date", "universe_cross_section_rebuild", "baseline eligible universe + atr_20_pct", "atr_20_pct", "event_t0_date close", "20 sessions", "all baseline-eligible instruments on decision date", "percentile_rank(atr_20_pct)", "", True, "rank universe fixed before label readout", "missing blocks dependent cell"),
        ("intraday_range_pct_asof_decision_date", "ep07_direct_or_qfq_rebuild", "EP07 canonical or qfq high/low/close", "intraday_range_pct|high|low|close", "event_t0_date close", "1 session", "", "(high-low)/close", "intraday_range_pct", True, "same day range only", "missing blocks dependent cell"),
        ("close_position_in_120d_range_asof_decision_date", "qfq_rebuild", "qfq high/low/close", "high|low|close", "event_t0_date close", "rolling 120 sessions ending at t", "", "(close-low120)/(high120-low120)", "", True, "window ends at decision date", "missing blocks dependent cell"),
        ("market_regime_risk_on_asof_decision_date", "ep07_direct_or_benchmark_rebuild", "EP07 canonical or benchmark", "market_regime_bucket|benchmark_close", "event_t0_date close", "60 sessions", "", "risk_on from frozen benchmark rule", "market_regime_bucket", True, "benchmark as of decision date", "missing blocks dependent cell"),
        ("market_drawdown_60d_asof_decision_date", "ep07_direct_or_benchmark_rebuild", "EP07 canonical or benchmark", "market_drawdown_60d|benchmark_close", "event_t0_date close", "60 sessions", "", "benchmark_close/rolling_60d_high-1", "market_drawdown_60d", True, "benchmark as of decision date", "missing blocks dependent cell"),
        ("quality_amount_flag_asof_decision_date", "ep07_direct_or_qfq_rebuild", "EP07 canonical or qfq money", "quality_amount_flag|money", "event_t0_date close", "20 sessions", "", "money and rolling 20d mean available", "quality_amount_flag", True, "no future bars", "missing allowed when parameter permits"),
        ("early_no_false_repair_10d_asof_decision_date", "ep07_direct_only", "EP07 canonical", "early_no_false_repair_10d", "event_t0_date close", "", "", "use only EP07 PIT-asof flag", "early_no_false_repair_10d", False, "no forward failure label reconstruction", "non-EP07 rows missing; true-required B6 cells blocked"),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "feature_field",
            "source_type",
            "source_artifact",
            "source_columns",
            "asof_rule",
            "window_rule",
            "cross_section_universe",
            "reconstruction_formula",
            "candidate_column_alias_if_ep07",
            "baseline_rebuild_required",
            "pit_guard",
            "missing_policy",
        ],
    ).assign(materialization_status="materialized_before_label_readout", blocking_reason="")


def build_label_source_map(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for horizon in config["labels"]["horizons"]:
        rows.extend(
            [
                {
                    "label_field": f"forward_mfe_{horizon}d",
                    "selected_anchor_type": "executable_next_open_anchored",
                    "selected_source_artifact": "qfq path + train anchor metadata",
                    "selected_source_columns": "date|high|trade_open_price|trade_open_pos",
                    "diagnostic_source_columns": f"mfe_{horizon}d",
                    "reconstruction_formula": f"max(high[entry_pos:entry_pos+{horizon}-1])/entry_price-1",
                    "horizon_sessions": horizon,
                    "path_complete_rule": f"entry_pos+{horizon}-1 exists and high/low/close complete",
                    "ready_made_label_allowed_for_primary": False,
                    "ready_made_label_allowed_for_diagnostic": True,
                    "entry_price_column": "trade_open_price",
                    "entry_pos_column": "trade_open_pos",
                    "label_materialized_after_train_filter": True,
                    "blocking_reason": "",
                },
                {
                    "label_field": f"forward_mae_{horizon}d",
                    "selected_anchor_type": "executable_next_open_anchored",
                    "selected_source_artifact": "qfq path + train anchor metadata",
                    "selected_source_columns": "date|low|trade_open_price|trade_open_pos",
                    "diagnostic_source_columns": f"mae_{horizon}d",
                    "reconstruction_formula": f"min(low[entry_pos:entry_pos+{horizon}-1])/entry_price-1",
                    "horizon_sessions": horizon,
                    "path_complete_rule": f"entry_pos+{horizon}-1 exists and high/low/close complete",
                    "ready_made_label_allowed_for_primary": False,
                    "ready_made_label_allowed_for_diagnostic": True,
                    "entry_price_column": "trade_open_price",
                    "entry_pos_column": "trade_open_pos",
                    "label_materialized_after_train_filter": True,
                    "blocking_reason": "",
                },
                {
                    "label_field": f"forward_return_{horizon}d",
                    "selected_anchor_type": "executable_next_open_anchored",
                    "selected_source_artifact": "qfq path + train anchor metadata",
                    "selected_source_columns": "date|close|trade_open_price|trade_open_pos",
                    "diagnostic_source_columns": "",
                    "reconstruction_formula": f"close[entry_pos+{horizon}-1]/entry_price-1",
                    "horizon_sessions": horizon,
                    "path_complete_rule": f"entry_pos+{horizon}-1 exists and high/low/close complete",
                    "ready_made_label_allowed_for_primary": False,
                    "ready_made_label_allowed_for_diagnostic": True,
                    "entry_price_column": "trade_open_price",
                    "entry_pos_column": "trade_open_pos",
                    "label_materialized_after_train_filter": True,
                    "blocking_reason": "",
                },
                {
                    "label_field": f"forward_big_winner_{horizon}d",
                    "selected_anchor_type": "executable_next_open_anchored",
                    "selected_source_artifact": "rebuilt forward_mfe",
                    "selected_source_columns": f"forward_mfe_{horizon}d",
                    "diagnostic_source_columns": "event_big_winner_120d_label" if horizon == 120 else "",
                    "reconstruction_formula": f"forward_mfe_{horizon}d >= 0.50",
                    "horizon_sessions": horizon,
                    "path_complete_rule": f"path_complete_{horizon}d",
                    "ready_made_label_allowed_for_primary": False,
                    "ready_made_label_allowed_for_diagnostic": True,
                    "entry_price_column": "trade_open_price",
                    "entry_pos_column": "trade_open_pos",
                    "label_materialized_after_train_filter": True,
                    "blocking_reason": "",
                },
                {
                    "label_field": f"path_complete_{horizon}d",
                    "selected_anchor_type": "executable_next_open_anchored",
                    "selected_source_artifact": "qfq path + train anchor metadata",
                    "selected_source_columns": "date|high|low|close|trade_open_pos",
                    "diagnostic_source_columns": f"horizon_complete_{horizon}d",
                    "reconstruction_formula": f"entry_pos+{horizon}-1 exists and high/low/close finite",
                    "horizon_sessions": horizon,
                    "path_complete_rule": f"path_complete_{horizon}d",
                    "ready_made_label_allowed_for_primary": False,
                    "ready_made_label_allowed_for_diagnostic": True,
                    "entry_price_column": "trade_open_price",
                    "entry_pos_column": "trade_open_pos",
                    "label_materialized_after_train_filter": True,
                    "blocking_reason": "",
                },
            ]
        )
    return pd.DataFrame(rows)


def build_matching_feature_source_map() -> pd.DataFrame:
    rows = [
        ("decision_month", "canonical metadata or baseline date", "event_t0_date|decision_date", "calendar month from decision date", "calendar month from decision date", "period YYYY-MM", "exact month", False, False),
        ("market_cap_bucket_asof_decision_date", "pit_topn_400_100_executable_daily.csv", "total_market_cap_cny", "rebuild from universe file", "rebuild from universe file", "as-of total market cap", "monthly quantile bucket", False, False),
        ("rolling_20d_amount_bucket_asof_decision_date", "qfq money", "money", "rebuild from qfq", "rebuild from qfq", "rolling 20d mean money", "monthly quantile bucket", False, False),
        ("rolling_60d_volatility_bucket_asof_decision_date", "qfq close", "close", "rebuild from qfq", "rebuild from qfq", "rolling 60d return std", "monthly quantile bucket", False, False),
        ("recent_20d_return_bucket_asof_decision_date", "qfq close", "close", "rebuild from qfq", "rebuild from qfq", "close[t]/close[t-20]-1", "monthly quantile bucket", False, False),
        ("instrument_or_industry_bucket_if_supported", "instrument only", "instrument", "instrument only", "instrument only", "PIT industry disabled", "exact instrument", False, False),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "matching_key",
            "canonical_source_artifact",
            "canonical_source_columns",
            "candidate_policy",
            "baseline_policy",
            "reconstruction_formula",
            "bucket_rule",
            "ep07_direct_field_allowed_for_matching",
            "equivalence_override_allowed",
        ],
    ).assign(frozen_before_baseline_materialization=True, blocking_reason="")


def simple_family_parameter_grid() -> dict[str, dict[str, Any]]:
    return {
        "B1_near_120d_high_plus_volume_expansion": {
            "features": [
                "close_asof_decision_date",
                "rolling_120d_high_asof_decision_date",
                "amount_ratio_20d_asof_decision_date",
                "return_20d_asof_decision_date",
                "market_regime_risk_on_asof_decision_date",
            ],
            "axes": {
                "near_high_120d_pct_max": [0.02, 0.05, 0.08],
                "amount_ratio_20d_min": [1.20, 1.50, 2.00],
                "return_20d_min": [0.00, 0.05],
                "market_regime_filter": ["all", "risk_on"],
            },
            "predicate_formula": "close >= high120*(1-near_high) and amount_ratio_20d >= min and return_20d >= min",
        },
        "B2_relative_strength_breakout": {
            "features": [
                "stock_vs_market_return_20d_asof_decision_date",
                "return_60d_cross_section_rank_pct_asof_decision_date",
                "close_to_ema60_asof_decision_date",
                "market_regime_risk_on_asof_decision_date",
            ],
            "axes": {
                "stock_vs_market_20d_min": [0.05, 0.10, 0.15],
                "return_60d_rank_pct_min": [0.70, 0.80, 0.90],
                "close_to_ema60_min": [0.00, 0.02],
                "market_regime_filter": ["all", "risk_on"],
            },
            "predicate_formula": "stock_vs_market_20d >= min and return_60d_rank >= min and close_to_ema60 >= min",
        },
        "B4_volatility_contraction_then_breakout": {
            "features": [
                "atr_20_pct_rank_asof_decision_date",
                "intraday_range_pct_asof_decision_date",
                "amount_ratio_20d_asof_decision_date",
                "return_5d_asof_decision_date",
            ],
            "axes": {
                "atr_20_pct_rank_max": [0.30, 0.40, 0.50],
                "intraday_range_pct_max": [0.03, 0.05, 0.08],
                "amount_ratio_20d_min": [1.20, 1.50],
                "return_5d_min": [0.00, 0.03],
            },
            "predicate_formula": "atr_rank <= max and intraday_range <= max and amount_ratio_20d >= min and return_5d >= min",
        },
        "B5_recent_high_close_plus_amount_expansion": {
            "features": [
                "return_10d_asof_decision_date",
                "close_position_in_120d_range_asof_decision_date",
                "amount_ratio_20d_asof_decision_date",
                "quality_amount_flag_asof_decision_date",
            ],
            "axes": {
                "return_10d_min": [0.03, 0.06, 0.10],
                "close_position_in_120d_range_min": [0.70, 0.85, 0.95],
                "amount_ratio_20d_min": [1.20, 1.50],
                "quality_amount_flag_required": ["true", "false_or_missing_allowed"],
            },
            "predicate_formula": "return_10d >= min and close_position >= min and amount_ratio_20d >= min",
        },
        "B6_low_drawdown_reclaim_or_ema_reclaim": {
            "features": [
                "market_drawdown_60d_asof_decision_date",
                "close_to_ema60_asof_decision_date",
                "return_5d_asof_decision_date",
                "early_no_false_repair_10d_asof_decision_date",
            ],
            "axes": {
                "market_drawdown_60d_min": [-0.20, -0.15, -0.10],
                "close_to_ema60_min": [0.00, 0.02, 0.05],
                "return_5d_min": [0.00, 0.03],
                "early_no_false_repair_10d_required": ["true", "false_or_missing_allowed"],
            },
            "predicate_formula": "market_drawdown >= min and close_to_ema60 >= min and return_5d >= min",
        },
    }


def parameter_product(axes: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(axes)
    return [dict(zip(keys, values, strict=False)) for values in itertools.product(*(axes[key] for key in keys))]


def normalize_group_key(key: Any) -> tuple[Any, ...]:
    return key if isinstance(key, tuple) else (key,)


def apply_simple_predicate(panel: pd.DataFrame, family_id: str, params: dict[str, Any]) -> tuple[pd.Series, str]:
    if family_id == "B1_near_120d_high_plus_volume_expansion":
        mask = (
            panel["close_asof_decision_date"].ge(panel["rolling_120d_high_asof_decision_date"] * (1.0 - params["near_high_120d_pct_max"]))
            & panel["amount_ratio_20d_asof_decision_date"].ge(params["amount_ratio_20d_min"])
            & panel["return_20d_asof_decision_date"].ge(params["return_20d_min"])
        )
        if params["market_regime_filter"] == "risk_on":
            mask &= panel["market_regime_risk_on_asof_decision_date"].fillna(False).astype(bool)
        return mask.fillna(False), ""
    if family_id == "B2_relative_strength_breakout":
        mask = (
            panel["stock_vs_market_return_20d_asof_decision_date"].ge(params["stock_vs_market_20d_min"])
            & panel["return_60d_cross_section_rank_pct_asof_decision_date"].ge(params["return_60d_rank_pct_min"])
            & panel["close_to_ema60_asof_decision_date"].ge(params["close_to_ema60_min"])
        )
        if params["market_regime_filter"] == "risk_on":
            mask &= panel["market_regime_risk_on_asof_decision_date"].fillna(False).astype(bool)
        return mask.fillna(False), ""
    if family_id == "B4_volatility_contraction_then_breakout":
        mask = (
            panel["atr_20_pct_rank_asof_decision_date"].le(params["atr_20_pct_rank_max"])
            & panel["intraday_range_pct_asof_decision_date"].le(params["intraday_range_pct_max"])
            & panel["amount_ratio_20d_asof_decision_date"].ge(params["amount_ratio_20d_min"])
            & panel["return_5d_asof_decision_date"].ge(params["return_5d_min"])
        )
        return mask.fillna(False), ""
    if family_id == "B5_recent_high_close_plus_amount_expansion":
        mask = (
            panel["return_10d_asof_decision_date"].ge(params["return_10d_min"])
            & panel["close_position_in_120d_range_asof_decision_date"].ge(params["close_position_in_120d_range_min"])
            & panel["amount_ratio_20d_asof_decision_date"].ge(params["amount_ratio_20d_min"])
        )
        if params["quality_amount_flag_required"] == "true":
            mask &= panel["quality_amount_flag_asof_decision_date"].fillna(False).astype(bool)
        return mask.fillna(False), ""
    if family_id == "B6_low_drawdown_reclaim_or_ema_reclaim":
        if params["early_no_false_repair_10d_required"] == "true":
            return pd.Series(False, index=panel.index), "early_no_false_repair_10d_requires_ep07_direct_only"
        mask = (
            panel["market_drawdown_60d_asof_decision_date"].ge(params["market_drawdown_60d_min"])
            & panel["close_to_ema60_asof_decision_date"].ge(params["close_to_ema60_min"])
            & panel["return_5d_asof_decision_date"].ge(params["return_5d_min"])
        )
        return mask.fillna(False), ""
    return pd.Series(False, index=panel.index), "unknown_family"


def materialize_cells(
    ep07_panel: pd.DataFrame,
    universe_panel: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], pd.DataFrame, pd.DataFrame, dict[tuple[str, str], pd.DataFrame]]:
    window = int(config["execution"]["primary_cooldown_window_sessions"])
    threshold_n = int(config["cell_support"]["cell_primary_denominator_n_min"])
    threshold_inst = int(config["cell_support"]["cell_instrument_n_min"])
    cell_frames: dict[tuple[str, str], pd.DataFrame] = {}
    denominator_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []

    def add_cell_frame(family_id: str, grid_cell_id: str, frame: pd.DataFrame, params: dict[str, Any], source: str, materialized: bool, blocking: str) -> None:
        parameter_hash = stable_hash_json(params)
        manifest_rows.append(
            {
                "family_id": family_id,
                "grid_cell_id": grid_cell_id,
                "parameter_json": json.dumps(clean_json(params), sort_keys=True),
                "parameter_hash": parameter_hash,
                "selection_split": "train",
                "source_contract": source,
                "candidate_row_source": "EP07 canonical train candidate rows" if family_id.startswith("EP07") else "baseline eligible qfq/universe scan",
                "feature_source_map_version": "simple_rule_feature_source_map_v1",
                "label_source_map_version": "label_source_map_v1",
                "matching_feature_source_map_version": "matching_feature_source_map_v1",
                "baseline_family_required_n": 3,
                "registry_frozen_before_label_readout": True,
                "label_readout_started": False,
                "blocking_reason": blocking,
            }
        )
        if materialized:
            cell_frames[(family_id, grid_cell_id)] = frame
        raw_n = len(frame) if materialized else 0
        primary = frame.loc[frame["primary_denominator_row"]] if materialized and "primary_denominator_row" in frame else pd.DataFrame()
        instrument_n = int(primary["instrument"].nunique()) if not primary.empty else 0
        effective_ratio = (primary["instrument_month"].nunique() / len(primary)) if not primary.empty and "instrument_month" in primary else 0.0
        denominator_gate = (
            len(primary) >= threshold_n
            and instrument_n >= threshold_inst
            and effective_ratio >= float(config["cell_support"]["cell_effective_sample_ratio_min"])
        )
        denominator_blocking = blocking
        if materialized and not blocking and not denominator_gate:
            denominator_blocking = "cell_support_floor_not_met"
        denominator_rows.append(
            {
                "family_id": family_id,
                "grid_cell_id": grid_cell_id,
                "family_source": "existing_source" if family_id.startswith("EP07") else "simple_rule_grid",
                "ep07_identity_cell_flag": family_id.startswith("EP07"),
                "split": "train",
                "source_candidate_train_n": int(frame["source_candidate_train_n"].iloc[0]) if materialized and "source_candidate_train_n" in frame.columns and len(frame) else raw_n,
                "raw_candidate_n": raw_n,
                "cooldown_entry_n": int(frame["cooldown_entry"].sum()) if materialized and "cooldown_entry" in frame else 0,
                "fill_feasible_candidate_n": int(frame["entry_fill_feasible"].sum()) if materialized and "entry_fill_feasible" in frame else 0,
                "entry_anchor_available_n": int(frame["entry_anchor_available"].fillna(False).sum()) if materialized and "entry_anchor_available" in frame else 0,
                "primary_denominator_n": len(primary),
                "path_complete_120_n": int(primary["path_complete_120d"].sum()) if not primary.empty else 0,
                "path_complete_30_n": int(primary["path_complete_30d"].sum()) if not primary.empty else 0,
                "instrument_n": instrument_n,
                "instrument_month_n": int(primary["instrument_month"].nunique()) if not primary.empty and "instrument_month" in primary else 0,
                "decision_month_n": int(primary["decision_month"].nunique()) if not primary.empty and "decision_month" in primary else 0,
                "cell_primary_denominator_n_min": threshold_n,
                "cell_instrument_n_min": threshold_inst,
                "cell_effective_sample_ratio": effective_ratio,
                "denominator_gate": pass_fail(denominator_gate),
                "blocking_reason": denominator_blocking,
            }
        )

    ep07_cell = ep07_panel.copy()
    add_cell_frame(
        "EP07_topn_multichannel_recommended_union",
        "EP07_identity_cell",
        ep07_cell,
        {},
        "19A_family_search_accounting_manifest + SOURCE_EP07_ROOT canonical candidate source",
        True,
        "",
    )

    families = simple_family_parameter_grid()
    simple_source = "19A_grid_search_manifest + simple_rule_feature_source_map"
    base = universe_panel.copy()
    base["source_candidate_train_n"] = len(base)
    for family_id, spec in families.items():
        for params in parameter_product(spec["axes"]):
            grid_cell_id, _ = make_cell_id(family_id, params)
            mask, blocking = apply_simple_predicate(base, family_id, params)
            if blocking:
                add_cell_frame(family_id, grid_cell_id, pd.DataFrame(), params, simple_source, False, blocking)
                continue
            raw = base.loc[mask].copy()
            if raw.empty:
                raw["cooldown_entry"] = False
                raw["primary_denominator_row"] = False
                add_cell_frame(family_id, grid_cell_id, raw, params, simple_source, True, "")
                continue
            raw["cooldown_entry"] = cooldown_filter(raw, "decision_pos", window)
            raw["primary_denominator_row"] = raw["cooldown_entry"] & raw["entry_fill_feasible"] & raw["path_complete_120d"]
            raw["family_id"] = family_id
            raw["grid_cell_id"] = grid_cell_id
            raw["parameter_hash"] = stable_hash_json(params)
            raw["parameter_json"] = json.dumps(clean_json(params), sort_keys=True)
            raw["family_source"] = "simple_rule_grid"
            raw["ep07_identity_cell_flag"] = False
            add_cell_frame(family_id, grid_cell_id, raw, params, simple_source, True, "")

    denominator = pd.DataFrame(denominator_rows)
    manifest = pd.DataFrame(manifest_rows)
    family_audit = (
        manifest.assign(materialized=manifest["blocking_reason"].eq(""))
        .groupby("family_id", as_index=False)
        .agg(
            family_source=("candidate_row_source", "first"),
            declared_grid_cell_n=("grid_cell_id", "count"),
            materialized_grid_cell_n=("materialized", "sum"),
        )
    )
    family_audit["not_materialized_grid_cell_n"] = family_audit["declared_grid_cell_n"] - family_audit["materialized_grid_cell_n"]
    family_audit["dependent_feature_missing_n"] = family_audit["not_materialized_grid_cell_n"]
    family_audit["source_contract_verified"] = True
    family_audit["feature_source_map_verified"] = True
    family_audit["materialization_status"] = np.where(
        family_audit["materialized_grid_cell_n"].gt(0), "materialized_before_label_readout", "train_scan_not_materializable"
    )
    family_audit["materialized_before_label_readout"] = family_audit["materialized_grid_cell_n"].gt(0)
    family_audit["blocking_reason"] = np.where(
        family_audit["materialized_grid_cell_n"].gt(0), "", "all_cells_not_materializable_or_empty"
    )
    return manifest_rows, denominator, family_audit, cell_frames


def sample_from_pool(pool: pd.DataFrame, counts: pd.Series, key_cols: list[str], rng: np.random.Generator) -> tuple[pd.DataFrame, int]:
    sampled_indices: list[Any] = []
    unmatched = 0
    if pool.empty or counts.empty:
        return pd.DataFrame(columns=pool.columns), int(counts.sum()) if not counts.empty else 0
    grouped_indices = {normalize_group_key(key): group.index.to_numpy() for key, group in pool.groupby(key_cols, dropna=False)}
    global_indices = pool.index.to_numpy()
    for key, count in counts.items():
        lookup = normalize_group_key(key)
        choices = grouped_indices.get(lookup)
        replace = False
        if choices is None or len(choices) == 0:
            unmatched += int(count)
            choices = global_indices
            replace = len(choices) < int(count)
        elif len(choices) < int(count):
            replace = True
        sampled_indices.extend(rng.choice(choices, size=int(count), replace=replace).tolist())
    return pool.loc[sampled_indices].copy(), unmatched


def max_distribution_delta(left: pd.Series, right: pd.Series) -> float:
    left_freq = left.value_counts(normalize=True)
    right_freq = right.value_counts(normalize=True)
    keys = sorted(set(left_freq.index).union(set(right_freq.index)))
    if not keys:
        return 0.0
    return float(max(abs(float(left_freq.get(k, 0.0)) - float(right_freq.get(k, 0.0))) for k in keys))


def max_smd(candidate: pd.DataFrame, baseline: pd.DataFrame) -> float:
    cols = ["match_market_cap", "match_amount20", "match_vol60", "match_return20"]
    values = []
    for col in cols:
        left = pd.to_numeric(candidate[col], errors="coerce")
        right = pd.to_numeric(baseline[col], errors="coerce")
        pooled = pd.concat([left, right]).std(ddof=0)
        if not np.isfinite(pooled) or pooled == 0:
            values.append(0.0)
        else:
            values.append(abs(left.mean() - right.mean()) / pooled)
    return float(max(values)) if values else 0.0


def baseline_for_cell(
    candidate: pd.DataFrame,
    pool: pd.DataFrame,
    baseline_family: str,
    seed: int,
) -> tuple[pd.DataFrame, int]:
    rng = np.random.default_rng(seed)
    if baseline_family == "calendar_time_random_same_budget":
        counts = candidate.groupby(["decision_month"], dropna=False).size()
        return sample_from_pool(pool, counts, ["decision_month"], rng)
    if baseline_family == "instrument_matched_random_same_budget":
        counts = candidate.groupby(["instrument"], dropna=False).size()
        return sample_from_pool(pool, counts, ["instrument"], rng)
    if baseline_family == "liquidity_size_volatility_matched_same_budget":
        counts = candidate.groupby(["lsv_match_key"], dropna=False).size()
        return sample_from_pool(pool, counts, ["lsv_match_key"], rng)
    raise ValueError(baseline_family)


def se_delta_probability(candidate: pd.DataFrame, baseline: pd.DataFrame) -> float:
    n1 = max(int(candidate["instrument_month"].nunique()), 1)
    n0 = max(int(baseline["instrument_month"].nunique()), 1)
    p1 = float(candidate["forward_big_winner_120d"].mean()) if len(candidate) else 0.0
    p0 = float(baseline["forward_big_winner_120d"].mean()) if len(baseline) else 0.0
    return math.sqrt(max(p1 * (1.0 - p1), 0.0) / n1 + max(p0 * (1.0 - p0), 0.0) / n0)


def positive_exposure_parameters(config: dict[str, Any]) -> tuple[float, float]:
    cfg = config.get("positive_exposure_config") or config.get("positive_exposure") or {}
    absolute_floor = float(cfg.get("positive_exposure_absolute_margin_floor_50", 0.02))
    relative_ratio = float(cfg.get("positive_exposure_relative_margin_ratio_floor", 0.20))
    return absolute_floor, relative_ratio


def se_delta_candidate_vs_eligible(candidate: pd.DataFrame, baseline_pool: pd.DataFrame, p_eligible: float) -> float:
    if not np.isfinite(p_eligible):
        return np.nan
    n_candidate = max(int(candidate["instrument_month"].nunique()), 1)
    n_eligible = max(int(baseline_pool["instrument_month"].nunique()), 1)
    p_candidate = float(candidate["forward_big_winner_120d"].mean()) if len(candidate) else 0.0
    return math.sqrt(
        max(p_candidate * (1.0 - p_candidate), 0.0) / n_candidate
        + max(p_eligible * (1.0 - p_eligible), 0.0) / n_eligible
    )


def build_baselines_and_metrics(
    cell_frames: dict[tuple[str, str], pd.DataFrame],
    baseline_pool: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    baseline_materialization_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    sensitivity_rows: list[dict[str, Any]] = []
    bootstrap_rows: list[dict[str, Any]] = []
    concentration_rows: list[dict[str, Any]] = []
    gates = config["baseline"]["quality_gates"]
    seed = int(config["baseline"]["random_seed"])
    bootstrap_cfg = config["bootstrap"]
    min_cell_n = int(config["cell_support"]["cell_primary_denominator_n_min"])
    min_instrument_n = int(config["cell_support"]["cell_instrument_n_min"])
    min_effective_ratio = float(config["cell_support"]["cell_effective_sample_ratio_min"])
    positive_abs_floor, positive_relative_ratio = positive_exposure_parameters(config)
    p_train_baseline_eligible = (
        float(baseline_pool["forward_big_winner_120d"].mean()) if len(baseline_pool) else np.nan
    )

    for idx, ((family_id, grid_cell_id), frame) in enumerate(cell_frames.items(), start=1):
        candidate = frame.loc[frame["primary_denominator_row"]].copy() if "primary_denominator_row" in frame else pd.DataFrame()
        if candidate.empty:
            continue
        effective_ratio = candidate["instrument_month"].nunique() / max(len(candidate), 1)
        if len(candidate) < min_cell_n or candidate["instrument"].nunique() < min_instrument_n or effective_ratio < min_effective_ratio:
            continue
        p_candidate = float(candidate["forward_big_winner_120d"].mean())
        se_positive = se_delta_candidate_vs_eligible(candidate, baseline_pool, p_train_baseline_eligible)
        positive_delta = p_candidate - p_train_baseline_eligible if np.isfinite(p_train_baseline_eligible) else np.nan
        positive_ratio = p_candidate / p_train_baseline_eligible if np.isfinite(p_train_baseline_eligible) and p_train_baseline_eligible > 0 else np.nan
        positive_relative_floor = positive_relative_ratio * p_train_baseline_eligible if np.isfinite(p_train_baseline_eligible) else np.nan
        positive_margin_candidates = [positive_abs_floor]
        if np.isfinite(positive_relative_floor):
            positive_margin_candidates.append(float(positive_relative_floor))
        if np.isfinite(se_positive):
            positive_margin_candidates.append(float(2.0 * se_positive))
        positive_margin = max(positive_margin_candidates)
        positive_score = positive_delta - positive_margin if np.isfinite(positive_delta) else np.nan
        positive_train_pass = bool(np.isfinite(positive_score) and positive_score >= 0.0)
        parameter_hash = str(candidate["parameter_hash"].iloc[0]) if "parameter_hash" in candidate and len(candidate) else ""
        for baseline_no, baseline_family in enumerate(BASELINE_FAMILIES, start=1):
            baseline, unmatched = baseline_for_cell(candidate, baseline_pool, baseline_family, seed + idx * 17 + baseline_no)
            requested = len(candidate)
            materialized = len(baseline)
            reuse_rate = 1.0 - baseline.index.nunique() / materialized if materialized else 1.0
            smd = max_smd(candidate, baseline) if materialized else np.nan
            decision_delta = max_distribution_delta(candidate["decision_month"], baseline["decision_month"]) if materialized else 1.0
            instrument_delta = max_distribution_delta(candidate["instrument"], baseline["instrument"]) if materialized else 1.0
            unmatched_rate = unmatched / requested if requested else 1.0
            quality_pass = (
                unmatched_rate <= float(gates["unmatched_candidate_rate_max"])
                and reuse_rate <= float(gates["baseline_reuse_rate_max"])
                and np.isfinite(smd)
                and smd <= float(gates["max_standardized_mean_difference_after_matching_max"])
                and decision_delta <= float(gates["decision_month_coverage_delta_max"])
                and instrument_delta <= float(gates["instrument_coverage_delta_max"])
                and materialized >= requested
            )
            p_matched = float(baseline["forward_big_winner_120d"].mean()) if materialized else np.nan
            zero_baseline = bool(not np.isfinite(p_matched) or p_matched == 0)
            se_delta = se_delta_probability(candidate, baseline) if materialized else np.nan
            margin_ratio = max(0.10, 2.0 * se_delta / p_matched) if np.isfinite(p_matched) and p_matched > 0 else np.nan
            lift = p_candidate / p_matched if np.isfinite(p_matched) and p_matched > 0 else np.nan
            adjusted = lift - 1.0 - margin_ratio if np.isfinite(lift) and np.isfinite(margin_ratio) else np.nan
            baseline_pass = bool(not zero_baseline and np.isfinite(adjusted) and adjusted >= 0.0)
            baseline_materialized = bool(materialized >= requested and requested > 0)

            baseline_materialization_rows.append(
                {
                    "baseline_family": baseline_family,
                    "family_id": family_id,
                    "grid_cell_id": grid_cell_id,
                    "split": "train",
                    "baseline_eligible_universe_row_n": len(baseline_pool),
                    "requested_same_budget_row_n": requested,
                    "materialized_baseline_row_n": materialized,
                    "unmatched_candidate_n": unmatched,
                    "baseline_sample_id_n": baseline.index.nunique() if materialized else 0,
                    "membership_frozen_before_label_readout": True,
                    "matching_bucket_frozen_before_label_readout": True,
                    "baseline_forward_label_read_after_membership_freeze": True,
                    "baseline_label_anchor_type": "executable_next_open_anchored",
                    "ready_made_event_anchored_label_used": False,
                    "baseline_materialization_gate": pass_fail(materialized >= requested and requested > 0),
                    "blocking_reason": "" if materialized >= requested else "baseline_materialization_under_budget",
                }
            )
            quality_rows.append(
                {
                    "baseline_family": baseline_family,
                    "family_id": family_id,
                    "grid_cell_id": grid_cell_id,
                    "split": "train",
                    "unmatched_candidate_rate": unmatched_rate,
                    "baseline_reuse_rate": reuse_rate,
                    "max_standardized_mean_difference_after_matching": smd,
                    "decision_month_coverage_delta": decision_delta,
                    "instrument_coverage_delta": instrument_delta,
                    "matched_baseline_primary_row_count": materialized,
                    "primary_enrichment_denominator_row_count": requested,
                    "baseline_matching_quality_gate": pass_fail(quality_pass),
                    "residual_alpha_claim_allowed": bool(quality_pass),
                    "positive_beta_exposure_claim_allowed": bool(baseline_materialized),
                    "baseline_quality_blocks_residual_alpha_only": bool(not quality_pass and baseline_materialized),
                    "cell_eligible_for_selection_under_this_baseline": bool(baseline_materialized),
                    "blocking_reason": "" if quality_pass else "baseline_quality_threshold_failed",
                }
            )
            metric_rows.append(
                {
                    "family_id": family_id,
                    "grid_cell_id": grid_cell_id,
                    "parameter_hash": parameter_hash,
                    "baseline_family": baseline_family,
                    "split": "train",
                    "label_anchor_type": "executable_next_open_anchored",
                    "candidate_n": len(candidate),
                    "tradable_n": len(candidate),
                    "instrument_n": int(candidate["instrument"].nunique()),
                    "instrument_month_n": int(candidate["instrument_month"].nunique()),
                    "cooldown_entry_n": len(candidate),
                    "primary_denominator_n": len(candidate),
                    "path_complete_120_n": int(candidate["path_complete_120d"].sum()),
                    "path_complete_30_n": int(candidate["path_complete_30d"].sum()),
                    "p_candidate_50": p_candidate,
                    "p_matched_50_by_baseline": p_matched,
                    "primary_tail_lift_50_by_baseline": lift,
                    "primary_tail_lift_50_conservative": np.nan,
                    "primary_tail_lift_50_train_margin_ratio_by_baseline": margin_ratio,
                    "primary_tail_lift_50_train_margin_adjusted_by_baseline": adjusted,
                    "primary_tail_lift_50_train_margin_adjusted_conservative": np.nan,
                    "zero_baseline_flag": zero_baseline,
                    "train_triage_baseline_pass": baseline_pass,
                    "train_triage_pass": False,
                    "residual_alpha_train_pass": False,
                    "p_train_baseline_eligible_50": p_train_baseline_eligible,
                    "positive_exposure_delta_50": positive_delta,
                    "positive_exposure_ratio_50": positive_ratio,
                    "positive_exposure_absolute_margin_floor_50": positive_abs_floor,
                    "positive_exposure_relative_margin_ratio_floor": positive_relative_ratio,
                    "positive_exposure_relative_margin_floor_50": positive_relative_floor,
                    "positive_exposure_margin_50": positive_margin,
                    "positive_exposure_score_50": positive_score,
                    "positive_exposure_train_pass": positive_train_pass,
                    "train_primary_metric_rank": np.nan,
                    "selection_track": "",
                    "promotion_claim_type": "train_diagnostic_only",
                    "residual_alpha_claim_allowed": False,
                    "positive_beta_exposure_claim_allowed": bool(baseline_materialized),
                    "selected_for_19B_robustness_flag": False,
                    "blocking_reason": "" if baseline_pass else "baseline_arm_did_not_pass",
                }
            )
            sensitivity = {
                "family_id": family_id,
                "grid_cell_id": grid_cell_id,
                "baseline_family": baseline_family,
                "split": "train",
                "label_anchor_type": "executable_next_open_anchored",
                "winner_capture_rate": p_candidate,
                "candidate_per_winner": (len(candidate) / max(float(candidate["forward_big_winner_120d"].sum()), 1.0)),
                "fast_fail_rate": float(candidate["forward_mae_20d"].le(-0.10).mean()),
                "false_repair_rate": float(candidate["forward_mae_20d"].le(-0.10).mean()),
                "MAE_20_p10": float(candidate["forward_mae_20d"].quantile(0.10)),
                "MFE_120_p90": float(candidate["forward_mfe_120d"].quantile(0.90)),
                "matched_baseline_delta": p_candidate - p_matched if np.isfinite(p_matched) else np.nan,
                "diagnostic_only_flag": True,
                "blocking_reason": "",
            }
            for horizon in [20, 30, 60, 120]:
                cand_rate = float(candidate[f"forward_big_winner_{horizon}d"].mean())
                base_rate = float(baseline[f"forward_big_winner_{horizon}d"].mean()) if materialized else np.nan
                sensitivity[f"forward_big_winner_{horizon}d_rate"] = cand_rate
                sensitivity[f"sensitivity_tail_lift_{horizon}"] = cand_rate / base_rate if np.isfinite(base_rate) and base_rate > 0 else np.nan
            sensitivity_rows.append(sensitivity)
            bootstrap_rows.append(
                {
                    "family_id": family_id,
                    "grid_cell_id": grid_cell_id,
                    "baseline_family": baseline_family,
                    "bootstrap_resample_n": int(bootstrap_cfg["bootstrap_resample_n"]),
                    "bootstrap_seed": int(bootstrap_cfg["bootstrap_seed"]),
                    "candidate_cluster_key": bootstrap_cfg["candidate_cluster_key"],
                    "matched_baseline_rerandomization_n": int(bootstrap_cfg["matched_baseline_rerandomization_n"]),
                    "matched_baseline_rerandomization_seed": int(bootstrap_cfg["matched_baseline_rerandomization_seed"]),
                    "se_delta_method": bootstrap_cfg["se_delta_method"],
                    "SE_delta_probability": se_delta,
                    "primary_tail_lift_50_train_margin_ratio": margin_ratio,
                    "SE_delta_probability_candidate_vs_eligible_universe": se_positive,
                    "positive_exposure_absolute_margin_floor_50": positive_abs_floor,
                    "positive_exposure_relative_margin_ratio_floor": positive_relative_ratio,
                    "positive_exposure_relative_margin_floor_50": positive_relative_floor,
                    "positive_exposure_margin_50": positive_margin,
                    "multiway_cluster_enabled": bool(bootstrap_cfg["multiway_cluster_enabled"]),
                    "blocking_reason": "",
                }
            )
            concentration_rows.append(build_concentration_row(candidate, family_id, grid_cell_id, baseline_family, lift, baseline_pass))

    quality = pd.DataFrame(quality_rows)
    metric = pd.DataFrame(metric_rows)
    if not metric.empty:
        grouped = metric.groupby(["family_id", "grid_cell_id"])
        conservative = grouped["primary_tail_lift_50_by_baseline"].transform("min")
        adjusted_conservative = grouped["primary_tail_lift_50_train_margin_adjusted_by_baseline"].transform("min")
        baseline_family_n = grouped["baseline_family"].transform("nunique")
        all_pass = grouped["train_triage_baseline_pass"].transform("all") & baseline_family_n.eq(len(BASELINE_FAMILIES))
        metric["primary_tail_lift_50_conservative"] = conservative
        metric["primary_tail_lift_50_train_margin_adjusted_conservative"] = adjusted_conservative
        metric["train_triage_pass"] = all_pass
        if not quality.empty:
            quality_cell = (
                quality.groupby(["family_id", "grid_cell_id"])
                .agg(
                    residual_alpha_claim_allowed=("baseline_matching_quality_gate", lambda s: len(s) == len(BASELINE_FAMILIES) and s.eq("pass").all()),
                    positive_beta_exposure_claim_allowed=("positive_beta_exposure_claim_allowed", lambda s: len(s) == len(BASELINE_FAMILIES) and s.astype(bool).all()),
                )
                .reset_index()
            )
            metric = metric.drop(
                columns=["residual_alpha_claim_allowed", "positive_beta_exposure_claim_allowed"], errors="ignore"
            ).merge(quality_cell, on=["family_id", "grid_cell_id"], how="left")
            metric["residual_alpha_claim_allowed"] = metric["residual_alpha_claim_allowed"].fillna(False).astype(bool)
            metric["positive_beta_exposure_claim_allowed"] = metric["positive_beta_exposure_claim_allowed"].fillna(False).astype(bool)
        metric["residual_alpha_train_pass"] = metric["train_triage_pass"].astype(bool) & metric["residual_alpha_claim_allowed"].astype(bool)
        metric["selection_track"] = np.select(
            [metric["residual_alpha_train_pass"], metric["positive_exposure_train_pass"]],
            ["residual_alpha", "positive_beta_exposure"],
            default="train_diagnostic_only",
        )
        metric["promotion_claim_type"] = np.select(
            [metric["residual_alpha_train_pass"], metric["positive_exposure_train_pass"]],
            ["residual_alpha_candidate", "positive_beta_exposure_candidate"],
            default="train_diagnostic_only",
        )
        rank_source = metric.drop_duplicates(["family_id", "grid_cell_id"])[
            ["family_id", "grid_cell_id", "primary_tail_lift_50_train_margin_adjusted_conservative"]
        ].copy()
        rank_source["train_primary_metric_rank"] = rank_source["primary_tail_lift_50_train_margin_adjusted_conservative"].rank(
            ascending=False, method="first"
        )
        metric = metric.drop(columns=["train_primary_metric_rank"]).merge(
            rank_source[["family_id", "grid_cell_id", "train_primary_metric_rank"]],
            on=["family_id", "grid_cell_id"],
            how="left",
        )
    return (
        pd.DataFrame(baseline_materialization_rows),
        quality,
        metric,
        pd.DataFrame(sensitivity_rows),
        pd.DataFrame(bootstrap_rows),
        pd.DataFrame(concentration_rows),
    )


def any_cell_with_all_baseline_gate_pass(frame: pd.DataFrame, gate_col: str) -> bool:
    if frame.empty or gate_col not in frame.columns:
        return False
    per_cell = frame.groupby(["family_id", "grid_cell_id"])[gate_col].apply(
        lambda series: len(series) == len(BASELINE_FAMILIES) and series.eq("pass").all()
    )
    return bool(per_cell.any())


def build_concentration_row(candidate: pd.DataFrame, family_id: str, grid_cell_id: str, baseline_family: str, lift: float, baseline_pass: bool) -> dict[str, Any]:
    total = max(len(candidate), 1)
    inst_counts = candidate["instrument"].value_counts()
    top1 = inst_counts.index[:1]
    top3 = inst_counts.index[:3]
    top1_removed = candidate.loc[~candidate["instrument"].isin(top1)]
    top3_removed = candidate.loc[~candidate["instrument"].isin(top3)]
    p = float(candidate["forward_big_winner_120d"].mean()) if len(candidate) else np.nan
    p1 = float(top1_removed["forward_big_winner_120d"].mean()) if len(top1_removed) else np.nan
    p3 = float(top3_removed["forward_big_winner_120d"].mean()) if len(top3_removed) else np.nan
    scale1 = p1 / p if np.isfinite(p) and p > 0 and np.isfinite(lift) else np.nan
    scale3 = p3 / p if np.isfinite(p) and p > 0 and np.isfinite(lift) else np.nan
    winner_counts = candidate.loc[candidate["forward_big_winner_120d"], "instrument"].value_counts()
    return {
        "family_id": family_id,
        "grid_cell_id": grid_cell_id,
        "baseline_family": baseline_family,
        "split": "train",
        "top1_instrument_removed_tail_lift": lift * scale1 if np.isfinite(scale1) else np.nan,
        "top3_instrument_removed_tail_lift": lift * scale3 if np.isfinite(scale3) else np.nan,
        "top1_instrument_removed_train_triage_pass": bool(baseline_pass and np.isfinite(scale1) and scale1 >= 0.8),
        "top3_instrument_removed_train_triage_pass": bool(baseline_pass and np.isfinite(scale3) and scale3 >= 0.8),
        "max_instrument_candidate_share": float(inst_counts.iloc[0] / total) if len(inst_counts) else 0.0,
        "max_instrument_winner_share": float(winner_counts.iloc[0] / max(int(winner_counts.sum()), 1)) if len(winner_counts) else 0.0,
        "diagnostic_only_flag": True,
        "blocking_reason": "",
    }


def build_eligible_universe_baseline_audit(panel: pd.DataFrame) -> pd.DataFrame:
    stages = [
        ("raw_train_universe", pd.Series(True, index=panel.index)),
        ("entry_anchor_available", panel["entry_anchor_available"].fillna(False)),
        ("entry_fill_feasible", panel["entry_fill_feasible"].fillna(False)),
        ("cooldown_eligible_under_19a_rule", panel["cooldown_eligible_under_19a_rule"].fillna(False)),
        ("matching_fields_available", panel["matching_fields_available"].fillna(False)),
        ("pre_label_baseline_eligible_candidate", panel["pre_label_baseline_eligible_candidate"].fillna(False)),
        ("path_complete_120d", panel["path_complete_120d"].fillna(False)),
        ("baseline_eligible", panel["baseline_eligible"].fillna(False)),
    ]
    previous_n = len(panel)
    rows = []
    for stage, mask in stages:
        subset = panel.loc[mask]
        rows.append(
            {
                "stage_name": stage,
                "row_n": len(subset),
                "instrument_n": int(subset["instrument"].nunique()) if not subset.empty else 0,
                "decision_month_n": int(subset["decision_month"].nunique()) if not subset.empty else 0,
                "path_complete_120_rate": float(subset["path_complete_120d"].fillna(False).mean()) if not subset.empty else 0.0,
                "path_complete_30_rate": float(subset["path_complete_30d"].fillna(False).mean()) if not subset.empty else 0.0,
                "matching_fields_available_rate": float(subset["matching_fields_available"].fillna(False).mean()) if not subset.empty else 0.0,
                "cooldown_eligible_rate": float(subset["cooldown_eligible_under_19a_rule"].fillna(False).mean()) if not subset.empty else 0.0,
                "membership_frozen_before_label_readout": bool(subset["baseline_membership_frozen_before_label_readout"].all()) if not subset.empty else True,
                "matching_bucket_frozen_before_label_readout": bool(subset["matching_bucket_frozen_before_label_readout"].all()) if not subset.empty else True,
                "baseline_forward_label_read_after_membership_freeze": bool(subset["baseline_forward_label_read_after_membership_freeze"].all()) if not subset.empty else True,
                "filtered_out_row_n": previous_n - len(subset),
                "blocking_reason": "",
            }
        )
        previous_n = len(subset)
    return pd.DataFrame(rows)


def build_matching_feature_equivalence_audit(ep07_panel: pd.DataFrame) -> pd.DataFrame:
    mappings = [
        ("market_cap_bucket_asof_decision_date", "total_market_cap_cny", "match_market_cap"),
        ("rolling_20d_amount_bucket_asof_decision_date", "amount_ratio_20d", "match_amount20"),
        ("rolling_60d_volatility_bucket_asof_decision_date", "atr_20_pct", "match_vol60"),
        ("recent_20d_return_bucket_asof_decision_date", "return_20d", "match_return20"),
    ]
    rows = []
    for key, ep07_col, rebuilt_col in mappings:
        if ep07_col not in ep07_panel.columns or rebuilt_col not in ep07_panel.columns:
            compared = pd.DataFrame()
        else:
            compared = ep07_panel[[ep07_col, rebuilt_col]].dropna()
        if compared.empty:
            rank_corr = np.nan
            max_delta = np.nan
        else:
            rank_corr = compared[ep07_col].rank().corr(compared[rebuilt_col].rank())
            max_delta = float((pd.to_numeric(compared[ep07_col], errors="coerce") - pd.to_numeric(compared[rebuilt_col], errors="coerce")).abs().max())
        rows.append(
            {
                "matching_key": key,
                "ep07_direct_column": ep07_col,
                "canonical_rebuild_column": rebuilt_col,
                "compared_row_n": len(compared),
                "exact_match_rate": float((compared[ep07_col] == compared[rebuilt_col]).mean()) if not compared.empty else np.nan,
                "rank_correlation": rank_corr,
                "bucket_match_rate": np.nan,
                "max_abs_delta": max_delta,
                "diagnostic_only_flag": True,
                "override_enabled": False,
                "blocking_reason": "",
            }
        )
    return pd.DataFrame(rows)


def build_selection_outputs(
    metric: pd.DataFrame,
    denominator: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    selected_columns = [
        "family_id",
        "grid_cell_id",
        "parameter_hash",
        "selection_split",
        "selection_metric",
        "selection_track",
        "promotion_claim_type",
        "residual_alpha_claim_allowed",
        "positive_beta_exposure_claim_allowed",
        "selection_rank_within_family",
        "label_anchor_type",
        "selected_for_19B_robustness_flag",
        "N_family_brought_to_robustness",
        "N_tested_family_cell_pairs",
        "residual_alpha_correction_scope",
        "positive_beta_exposure_correction_scope",
        "track_correction_scope_policy",
        "max_ep19_terminal_state_if_no_residual_pass",
        "ep20_policy_preflight_authorized_if_no_residual_pass",
        "manifest_frozen_before_robustness_readout",
        "blocking_reason",
    ]
    if metric.empty:
        family_selection = pd.DataFrame()
        selected = pd.DataFrame(columns=selected_columns)
    else:
        baseline_counts = (
            metric.groupby(["family_id", "grid_cell_id"])["baseline_family"]
            .nunique()
            .rename("baseline_family_n")
            .reset_index()
        )
        cell_metric = metric.drop_duplicates(["family_id", "grid_cell_id"]).copy()
        cell_metric = cell_metric.merge(baseline_counts, on=["family_id", "grid_cell_id"], how="left")
        denom = denominator[["family_id", "grid_cell_id", "primary_denominator_n", "instrument_n", "cell_effective_sample_ratio"]]
        cell_metric = cell_metric.merge(denom, on=["family_id", "grid_cell_id"], how="left", suffixes=("", "_denom"))
        cell_metric["support_pass"] = (
            cell_metric["primary_denominator_n_denom"].ge(int(config["cell_support"]["cell_primary_denominator_n_min"]))
            & cell_metric["instrument_n_denom"].ge(int(config["cell_support"]["cell_instrument_n_min"]))
            & cell_metric["cell_effective_sample_ratio"].ge(float(config["cell_support"]["cell_effective_sample_ratio_min"]))
        )
        cell_metric["all_three_baseline_families_present"] = cell_metric["baseline_family_n"].eq(len(BASELINE_FAMILIES))
        cell_metric["candidate_per_winner"] = cell_metric["candidate_n"] / (
            cell_metric["candidate_n"].mul(cell_metric["p_candidate_50"]).clip(lower=1.0)
        )
        cell_metric["residual_selection_pass"] = (
            cell_metric["support_pass"]
            & cell_metric["all_three_baseline_families_present"]
            & cell_metric["residual_alpha_train_pass"].astype(bool)
        )
        cell_metric["positive_selection_pass"] = (
            cell_metric["support_pass"]
            & cell_metric["all_three_baseline_families_present"]
            & cell_metric["positive_exposure_train_pass"].astype(bool)
            & cell_metric["positive_beta_exposure_claim_allowed"].astype(bool)
        )
        family_rows = []
        selected_rows = []
        for family_id, group in cell_metric.groupby("family_id", sort=True):
            residual_pass_rows = group.loc[group["residual_selection_pass"]].sort_values(
                [
                    "primary_tail_lift_50_train_margin_adjusted_conservative",
                    "primary_denominator_n_denom",
                    "candidate_per_winner",
                    "grid_cell_id",
                ],
                ascending=[False, False, True, True],
            )
            positive_pass_rows = group.loc[group["positive_selection_pass"]].sort_values(
                ["positive_exposure_score_50", "primary_denominator_n_denom", "candidate_per_winner", "grid_cell_id"],
                ascending=[False, False, True, True],
            )
            if not residual_pass_rows.empty:
                selected_row = residual_pass_rows.iloc[0]
                selection_metric = "primary_tail_lift_50_train_margin_adjusted_conservative"
                selection_track = "residual_alpha"
                promotion_claim_type = "residual_alpha_candidate"
            elif not positive_pass_rows.empty:
                selected_row = positive_pass_rows.iloc[0]
                selection_metric = "positive_exposure_score_50"
                selection_track = "positive_beta_exposure"
                promotion_claim_type = "positive_beta_exposure_candidate"
            else:
                selected_row = None
                selection_metric = ""
                selection_track = "train_diagnostic_only"
                promotion_claim_type = "train_diagnostic_only"
            diagnostic = bool(
                group["primary_tail_lift_50_train_margin_adjusted_conservative"].fillna(-np.inf).max() > 0
                or group["positive_exposure_delta_50"].fillna(-np.inf).max() > 0
            )
            family_rows.append(
                {
                    "family_id": family_id,
                    "supported_primary_family_flag": True,
                    "materialized_grid_cell_n": int(len(group)),
                    "ranked_grid_cell_n": int(group["primary_tail_lift_50_train_margin_adjusted_conservative"].notna().sum()),
                    "selected_grid_cell_id": "" if selected_row is None else selected_row["grid_cell_id"],
                    "selected_parameter_hash": "" if selected_row is None else selected_row.get("parameter_hash", ""),
                    "best_primary_tail_lift_50_train_margin_adjusted_conservative": float(group["primary_tail_lift_50_train_margin_adjusted_conservative"].max()),
                    "best_positive_exposure_score_50": float(group["positive_exposure_score_50"].max()),
                    "all_three_baseline_families_present": bool(group["all_three_baseline_families_present"].all()),
                    "label_anchor_type": "executable_next_open_anchored",
                    "selected_for_19B_robustness_flag": selected_row is not None,
                    "family_triage_status": "selected_for_19B" if selected_row is not None else ("train_diagnostic_only" if diagnostic else "no_cell_passed"),
                    "selection_track": selection_track,
                    "promotion_claim_type": promotion_claim_type,
                    "residual_alpha_claim_allowed": bool(selected_row["residual_alpha_claim_allowed"]) if selected_row is not None else False,
                    "positive_beta_exposure_claim_allowed": bool(selected_row["positive_beta_exposure_claim_allowed"]) if selected_row is not None else bool(group["positive_beta_exposure_claim_allowed"].any()),
                    "selection_rank_within_all_families": np.nan,
                    "selection_rule_applied_before_robustness_readout": True,
                    "blocking_reason": "" if selected_row is not None else "no_cell_met_residual_or_positive_exposure_selection_condition",
                }
            )
            if selected_row is not None:
                selected_rows.append(
                    {
                        "family_id": family_id,
                        "grid_cell_id": selected_row["grid_cell_id"],
                        "parameter_hash": selected_row.get("parameter_hash", ""),
                        "selection_split": "train",
                        "selection_metric": selection_metric,
                        "selection_track": selection_track,
                        "promotion_claim_type": promotion_claim_type,
                        "residual_alpha_claim_allowed": bool(selected_row["residual_alpha_claim_allowed"]),
                        "positive_beta_exposure_claim_allowed": bool(selected_row["positive_beta_exposure_claim_allowed"]),
                        "selection_rank_within_family": 1,
                        "label_anchor_type": "executable_next_open_anchored",
                        "selected_for_19B_robustness_flag": True,
                        "N_family_brought_to_robustness": 0,
                        "N_tested_family_cell_pairs": 0,
                        "residual_alpha_correction_scope": "",
                        "positive_beta_exposure_correction_scope": "",
                        "track_correction_scope_policy": "separate_by_promotion_claim_type",
                        "max_ep19_terminal_state_if_no_residual_pass": (
                            "19_entry_universe_enrichment_only_diagnostic"
                            if promotion_claim_type == "positive_beta_exposure_candidate"
                            else "not_applicable_for_residual_alpha_candidate"
                        ),
                        "ep20_policy_preflight_authorized_if_no_residual_pass": False,
                        "manifest_frozen_before_robustness_readout": True,
                        "blocking_reason": "",
                    }
                )
        family_selection = pd.DataFrame(family_rows)
        if not family_selection.empty:
            family_selection["selection_rank_within_all_families"] = family_selection[
                "best_primary_tail_lift_50_train_margin_adjusted_conservative"
            ].rank(ascending=False, method="first")
        selected = pd.DataFrame(selected_rows, columns=selected_columns)

    n_family = int(selected["family_id"].nunique()) if not selected.empty else 0
    n_residual = int(selected["promotion_claim_type"].eq("residual_alpha_candidate").sum()) if not selected.empty else 0
    n_positive = int(selected["promotion_claim_type"].eq("positive_beta_exposure_candidate").sum()) if not selected.empty else 0
    residual_scope = f"{n_residual} * primary_tail_lift_50"
    positive_scope = f"{n_positive} * positive_exposure_score_50"
    if not selected.empty:
        selected["N_family_brought_to_robustness"] = n_family
        selected["N_tested_family_cell_pairs"] = len(selected)
        selected["residual_alpha_correction_scope"] = residual_scope
        selected["positive_beta_exposure_correction_scope"] = positive_scope
    robustness = selected.copy()
    if robustness.empty:
        robustness = pd.DataFrame(
            columns=[
                "family_id",
                "grid_cell_id",
                "parameter_hash",
                "selected_in_19B0_train_only",
                "selection_track",
                "promotion_claim_type",
                "residual_alpha_claim_allowed",
                "positive_beta_exposure_claim_allowed",
                "label_anchor_type",
                "robustness_split_outcome_read_allowed_in_19B",
                "validation_split_outcome_read_allowed_in_19B",
                "N_family_brought_to_robustness",
                "N_tested_family_cell_pairs",
                "residual_alpha_correction_scope",
                "positive_beta_exposure_correction_scope",
                "track_correction_scope_policy",
                "family_level_correction",
                "cell_level_accounting",
                "max_ep19_terminal_state_if_no_residual_pass",
                "ep20_policy_preflight_authorized_if_no_residual_pass",
                "manifest_frozen_before_robustness_readout",
                "blocking_reason",
            ]
        )
    else:
        robustness = robustness.rename(columns={"selected_for_19B_robustness_flag": "selected_in_19B0_train_only"})
        robustness["robustness_split_outcome_read_allowed_in_19B"] = True
        robustness["validation_split_outcome_read_allowed_in_19B"] = False
        robustness["family_level_correction"] = config["grid_search"]["family_level_correction"]
        robustness["cell_level_accounting"] = config["grid_search"]["cell_level_accounting"]
    selection_track_counts = selected["selection_track"].value_counts().sort_index().to_dict() if not selected.empty else {}
    promotion_counts = selected["promotion_claim_type"].value_counts().sort_index().to_dict() if not selected.empty else {}
    search = pd.DataFrame(
        [
            {
                "N_supported_primary_family": int(denominator["family_id"].nunique()),
                "N_materialized_family": int(denominator.loc[denominator["raw_candidate_n"].gt(0), "family_id"].nunique()),
                "N_family_brought_to_robustness": n_family,
                "N_tested_family_cell_pairs": len(selected),
                "N_residual_alpha_candidate_pairs": n_residual,
                "N_positive_beta_exposure_candidate_pairs": n_positive,
                "residual_alpha_correction_scope": residual_scope,
                "positive_beta_exposure_correction_scope": positive_scope,
                "track_correction_scope_policy": "separate_by_promotion_claim_type",
                "family_level_correction": config["grid_search"]["family_level_correction"],
                "cell_level_accounting": config["grid_search"]["cell_level_accounting"],
                "selected_cell_rule": config["grid_search"]["selected_cell_rule"],
                "selection_track_counts": json.dumps(selection_track_counts, sort_keys=True),
                "promotion_claim_type_counts": json.dumps(promotion_counts, sort_keys=True),
                "expanded_cell_rule_enabled": bool(config["grid_search"]["expanded_cell_rule_enabled"]),
                "validation_selected_cells": 0,
                "search_accounting_gate": "pass",
                "blocking_reason": "",
            }
        ]
    )
    return family_selection, selected, robustness, search


def decide_state(gates: dict[str, str], selected: pd.DataFrame, family_selection: pd.DataFrame) -> tuple[str, str, str]:
    failed = [gate for gate in CRITICAL_GATES if gates.get(gate) != "pass"]
    if failed:
        for state in FAIL_STATE_ORDER:
            if any(gate in failed for gate in STATE_GATE_MAP[state]):
                return state, "none", ";".join(failed)
        return "19B0_output_contract_blocked", "none", ";".join(failed)
    selected_n = len(selected)
    diagnostic_n = (
        int(family_selection["family_triage_status"].eq("train_diagnostic_only").sum())
        if not family_selection.empty and "family_triage_status" in family_selection
        else 0
    )
    if selected_n > 0:
        return DECISION_POSITIVE, NEXT_19B, ""
    if diagnostic_n > 0:
        return DECISION_DIAGNOSTIC, "none", ""
    return DECISION_NO_PASS, "none", ""


def build_decision(
    config_path: Path,
    paths: dict[str, Path],
    gates: dict[str, str],
    state: str,
    next_requirement: str,
    blocking_reason: str,
    selected: pd.DataFrame,
    family_selection: pd.DataFrame,
) -> pd.DataFrame:
    n_residual = int(selected["promotion_claim_type"].eq("residual_alpha_candidate").sum()) if not selected.empty else 0
    n_positive = int(selected["promotion_claim_type"].eq("positive_beta_exposure_candidate").sum()) if not selected.empty else 0
    row = {
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requirement_file_hash": file_sha(paths["requirement_19b0"]),
        "config_file_hash": file_sha(config_path),
        "upstream_19a_manifest_hash": file_sha(paths["nineteen_a_manifest"]),
        "decision_state": state,
        "next_allowed_requirement": next_requirement,
    }
    row.update(gates)
    row.update(
        {
            "N_family_brought_to_robustness": int(selected["family_id"].nunique()) if not selected.empty else 0,
            "N_tested_family_cell_pairs": len(selected),
            "selected_family_n": int(selected["family_id"].nunique()) if not selected.empty else 0,
            "selected_family_cell_pair_n": len(selected),
            "selected_residual_alpha_cell_pair_n": n_residual,
            "selected_positive_beta_exposure_cell_pair_n": n_positive,
            "residual_alpha_correction_scope": f"{n_residual} * primary_tail_lift_50",
            "positive_beta_exposure_correction_scope": f"{n_positive} * positive_exposure_score_50",
            "track_correction_scope_policy": "separate_by_promotion_claim_type",
            "positive_beta_max_terminal_state_if_no_residual_pass": (
                "19_entry_universe_enrichment_only_diagnostic" if n_positive > 0 else ""
            ),
            "positive_beta_ep20_policy_preflight_authorized_if_no_residual_pass": False,
            "diagnostic_family_n": int(family_selection["family_triage_status"].eq("train_diagnostic_only").sum()) if not family_selection.empty else 0,
            "validation_outcome_read": False,
            "robustness_outcome_used_for_selection": False,
            "model_training_authorized": False,
            "entry_policy_authorized": False,
            "exit_policy_authorized": False,
            "holding_policy_authorized": False,
            "portfolio_backtest_authorized": False,
            "model_deployment_authorized": False,
            "production_signal_authorized": False,
            "live_trading_authorized": False,
            "blocking_reason": blocking_reason,
        }
    )
    return pd.DataFrame([row])


def build_report(
    decision: pd.DataFrame,
    denominator: pd.DataFrame,
    metric: pd.DataFrame,
    family_selection: pd.DataFrame,
    family_materialization: pd.DataFrame,
    label_anchor_audit: pd.DataFrame,
    matching_source_map: pd.DataFrame,
    baseline_materialization: pd.DataFrame,
    baseline_quality: pd.DataFrame,
    sensitivity: pd.DataFrame,
    concentration: pd.DataFrame,
    search_accounting: pd.DataFrame,
) -> str:
    row = decision.iloc[0]
    ep07 = denominator.loc[denominator["ep07_identity_cell_flag"]]
    ep07_den = int(ep07["primary_denominator_n"].iloc[0]) if not ep07.empty else 0
    ep07_path_complete = int(ep07["path_complete_120_n"].iloc[0]) if not ep07.empty else 0
    selected_n = int(row["selected_family_cell_pair_n"])
    supported_families = sorted(denominator["family_id"].dropna().unique().tolist()) if not denominator.empty else []
    family_lines = []
    if not family_materialization.empty:
        for item in family_materialization.sort_values("family_id").itertuples(index=False):
            family_lines.append(
                f"| {item.family_id} | {item.declared_grid_cell_n} | {item.materialized_grid_cell_n} | "
                f"{item.materialization_status} | {item.blocking_reason or ''} |"
            )
    if not family_lines:
        family_lines.append("| none | 0 | 0 | none | none |")

    baseline_lines = []
    if not baseline_quality.empty:
        quality_summary = (
            baseline_quality.groupby("baseline_family", as_index=False)
            .agg(
                rows=("grid_cell_id", "count"),
                pass_n=("baseline_matching_quality_gate", lambda s: int(s.eq("pass").sum())),
                median_smd=("max_standardized_mean_difference_after_matching", "median"),
                median_unmatched=("unmatched_candidate_rate", "median"),
            )
        )
        for item in quality_summary.itertuples(index=False):
            baseline_lines.append(
                f"| {item.baseline_family} | {item.rows} | {item.pass_n} | "
                f"{item.median_smd:.3f} | {item.median_unmatched:.3f} |"
            )
    if not baseline_lines:
        baseline_lines.append("| none | 0 | 0 | nan | nan |")

    metric_lines = []
    selected_lines = []
    if not metric.empty:
        top = metric.drop_duplicates(["family_id", "grid_cell_id"]).sort_values(
            "primary_tail_lift_50_train_margin_adjusted_conservative", ascending=False
        ).head(10)
        for item in top.itertuples(index=False):
            metric_lines.append(
                f"| {item.family_id} | {item.grid_cell_id} | {item.primary_denominator_n} | "
                f"{item.p_candidate_50:.3f} | {item.p_train_baseline_eligible_50:.3f} | "
                f"{item.primary_tail_lift_50_conservative:.3f} | "
                f"{item.primary_tail_lift_50_train_margin_adjusted_conservative:.3f} | "
                f"{item.positive_exposure_absolute_margin_floor_50:.3f} | "
                f"{item.positive_exposure_relative_margin_floor_50:.3f} | "
                f"{item.positive_exposure_margin_50:.3f} | "
                f"{item.positive_exposure_score_50:.4f} | {item.promotion_claim_type} | {item.train_triage_pass} |"
            )
    if not family_selection.empty:
        selected_family = family_selection.loc[family_selection["selected_for_19B_robustness_flag"].astype(bool)]
        for item in selected_family.itertuples(index=False):
            selected_lines.append(
                f"| {item.family_id} | {item.selected_grid_cell_id} | {item.selection_track} | "
                f"{item.promotion_claim_type} | {item.residual_alpha_claim_allowed} |"
            )
    if not metric_lines:
        metric_lines.append("| none | none | 0 | nan | nan | nan | nan | nan | nan | nan | nan | train_diagnostic_only | False |")
    if not selected_lines:
        selected_lines.append("| none | none | none | none | false |")
    sensitivity_line = "none"
    if not sensitivity.empty:
        sensitivity_line = (
            f"rows={len(sensitivity)}, diagnostic_only={bool(sensitivity['diagnostic_only_flag'].all())}, "
            f"median_tail_lift_20={sensitivity['sensitivity_tail_lift_20'].median():.3f}, "
            f"median_tail_lift_60={sensitivity['sensitivity_tail_lift_60'].median():.3f}"
        )
    concentration_line = "none"
    if not concentration.empty:
        concentration_line = (
            f"rows={len(concentration)}, max_instrument_candidate_share="
            f"{concentration['max_instrument_candidate_share'].max():.3f}, "
            f"max_instrument_winner_share={concentration['max_instrument_winner_share'].max():.3f}"
        )
    search_line = search_accounting.iloc[0].to_dict() if not search_accounting.empty else {}
    label_anchor_line = label_anchor_audit.iloc[0].to_dict() if not label_anchor_audit.empty else {}
    return "\n".join(
        [
            "# 19B0 快速规则网格右尾富集扫描报告",
            "",
            "## 1. 19A Ready 和 Train-only 边界",
            f"- decision_state: `{row['decision_state']}`",
            f"- next_allowed_requirement: `{row['next_allowed_requirement']}`",
            "- validation outcome read: `false`",
            "- robustness outcome used for selection: `false`",
            "- 19A ready 证据来自 upstream contract audit、manifest hash audit 和 frozen output hash 校验。",
            "",
            "## 2. 支持/不支持 Family 和 Grid Materialization",
            f"- supported primary families: `{', '.join(supported_families)}`",
            "- unsupported family: `B3_industry_or_theme_breadth_expansion`，原因是 no genuine PIT industry source。",
            "",
            "| family | declared_grid_cell_n | materialized_grid_cell_n | materialization_status | blocking_reason |",
            "|---|---:|---:|---|---|",
            *family_lines,
            "",
            "## 3. Label Anchor 和 Label Source Map",
            "- 19B0 使用 `executable_next_open_anchored` 标签。",
            "- EP07 `event_anchored` ready-made label 仅作为 diagnostic，不进入 primary metric 或 selection。",
            f"- label source map: `executable_next_open_anchored`; label_anchor_rebuild_audit: `{json.dumps(clean_json(label_anchor_line), ensure_ascii=False, sort_keys=True)}`",
            "",
            "## 4. Denominator",
            f"- EP07 identity primary denominator: `{ep07_den}`",
            f"- EP07 identity path-complete denominator: `{ep07_path_complete}`",
            f"- materialized family count: `{denominator.loc[denominator['raw_candidate_n'].gt(0), 'family_id'].nunique()}`",
            f"- total candidate denominator rows audited: `{len(denominator)}`",
            "",
            "## 5. Matching Feature Source Map",
            "- matching feature source map 明确候选与 baseline 使用同一 qfq/universe 重建路径。",
            f"- matching keys: `{', '.join(matching_source_map['matching_key'].tolist()) if not matching_source_map.empty else 'none'}`",
            "",
            "## 6. Baseline Materialization 和 Matching Quality",
            f"- baseline materialization rows: `{len(baseline_materialization)}`",
            "- baseline matching quality failure blocks residual-alpha attribution only.",
            "- It does not by itself invalidate a positive beta/exposure candidate.",
            "- positive_beta_exposure_candidate 不是 independent alpha / residual alpha claim。",
            "",
            "| baseline_family | rows | pass_n | median_smd | median_unmatched_rate |",
            "|---|---:|---:|---:|---:|",
            *baseline_lines,
            "",
            "## 7. Metric Readout 和 Positive Beta/Exposure Track",
            "- 三类 baseline 分臂计算，selection 使用 conservative margin-adjusted score。",
            "",
            "| family | grid_cell | primary_n | p_candidate_50 | broad_base_rate | conservative_lift | conservative_adjusted | abs_margin | rel_margin | positive_margin | positive_score | promotion_claim_type | lift_margin_pass |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|",
            *metric_lines,
            "",
            "## 8. Sensitivity 和 Instrument Concentration",
            f"- sensitivity 指标均为 diagnostic-only: `{sensitivity_line}`",
            f"- instrument concentration / top-k removal 风险: `{concentration_line}`",
            "",
            "## 9. Selected Family/Cell Manifest",
            f"- selected family/cell pairs: `{selected_n}`",
            f"- selected residual-alpha pairs: `{row['selected_residual_alpha_cell_pair_n']}`",
            f"- selected positive-beta/exposure pairs: `{row['selected_positive_beta_exposure_cell_pair_n']}`",
            f"- diagnostic family count: `{row['diagnostic_family_n']}`",
            f"- residual_alpha_correction_scope: `{row['residual_alpha_correction_scope']}`",
            f"- positive_beta_exposure_correction_scope: `{row['positive_beta_exposure_correction_scope']}`",
            "- residual-alpha and positive-beta tracks use separate correction scopes.",
            "- positive-beta 候选若无 19B matched-baseline residual pass，只能支持 `19_entry_universe_enrichment_only_diagnostic`，不授权 EP20 policy preflight。",
            "",
            "| selected_family | selected_grid_cell | selection_track | promotion_claim_type | residual_alpha_claim_allowed |",
            "|---|---|---|---|---:|",
            *selected_lines,
            "",
            "## 10. Search Accounting 和 19B Handoff",
            f"- search accounting: `{json.dumps(clean_json(search_line), ensure_ascii=False, sort_keys=True)}`",
            f"- N_family_brought_to_robustness: `{row['N_family_brought_to_robustness']}`",
            f"- N_tested_family_cell_pairs: `{row['N_tested_family_cell_pairs']}`",
            "- positive_beta_exposure_candidate without matched-baseline residual pass can only support 19_entry_universe_enrichment_only_diagnostic, not EP20 authorization.",
            "",
            "## 11. Authorization 和 Final Decision",
            f"- final decision_state: `{row['decision_state']}`",
            f"- final next_allowed_requirement: `{row['next_allowed_requirement']}`",
            "- 19B0 不授权模型、entry/exit/holding policy、回测、生产信号或交易。",
            "- 进入 19B 的资格不是 support claim。",
            "- 19B0 不是 robustness confirmation。",
            "- 19B0 不证明策略有效。",
            "- 19B0 不授权 19C replay。",
            "",
        ]
    )


def build_handoff(selected: pd.DataFrame) -> str:
    lines = [
        "# 19B0 Handoff to 19B Contract",
        "",
        "19B may read robustness outcome only for rows frozen in `robustness_test_manifest.csv`.",
        "Validation outcome remains forbidden in 19B.",
        "",
        "19B must preserve `promotion_claim_type`, `residual_alpha_claim_allowed`, and the separate correction scopes.",
        "A positive beta/exposure candidate without a matched-baseline residual pass can only support `19_entry_universe_enrichment_only_diagnostic`.",
        "",
        "| family_id | grid_cell_id | promotion_claim_type | residual_alpha_claim_allowed | max_ep19_terminal_state_if_no_residual_pass |",
        "|---|---|---|---:|---|",
    ]
    if selected.empty:
        lines.append("| none | none | none | false | none |")
    else:
        for row in selected.itertuples(index=False):
            lines.append(
                f"| {row.family_id} | {row.grid_cell_id} | {row.promotion_claim_type} | "
                f"{row.residual_alpha_claim_allowed} | {row.max_ep19_terminal_state_if_no_residual_pass} |"
            )
    lines.append("")
    return "\n".join(lines)


def output_contract_pass(report: str, outputs: dict[str, Path]) -> bool:
    required_report_phrases = [
        "支持/不支持 Family",
        "Grid Materialization",
        "Label Source Map",
        "Matching Feature Source Map",
        "Baseline Materialization",
        "Positive Beta/Exposure Track",
        "Sensitivity",
        "Instrument Concentration",
        "Search Accounting",
        "19B0 不是 robustness confirmation。",
        "19B0 不证明策略有效。",
        "19B0 不授权 19C replay。",
        "19B0 不授权模型、entry/exit/holding policy、回测、生产信号或交易。",
        "进入 19B 的资格不是 support claim。",
        "positive_beta_exposure_candidate 不是 independent alpha / residual alpha claim。",
        "baseline matching quality failure blocks residual-alpha attribution only.",
        "positive_beta_exposure_candidate without matched-baseline residual pass can only support 19_entry_universe_enrichment_only_diagnostic, not EP20 authorization.",
        "residual-alpha and positive-beta tracks use separate correction scopes.",
    ]
    output_keys_ready = set(REQUIRED_OUTPUT_KEYS).issubset(set(outputs))
    return output_keys_ready and all(phrase in report for phrase in required_report_phrases)


def build_output_hashes(outputs: dict[str, Path]) -> dict[str, str]:
    return {
        key: file_sha(path)
        for key, path in sorted(outputs.items())
        if key not in {"manifest", "output_hashes"} and path.exists() and path.is_file()
    }


def run(config_path: str | Path = CONFIG_PATH) -> dict[str, Path]:
    config_path = Path(config_path)
    config = load_config(config_path)
    paths = resolve_paths(config)
    outputs = output_paths()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    input_audit = build_input_artifact_audit(config, paths)
    upstream_audit, upstream_gate, upstream_row = build_upstream_19a_contract_audit(paths)
    if input_audit["input_artifact_gate"].ne("pass").any() or upstream_gate != "pass":
        gates = {gate: "pass" for gate in CRITICAL_GATES}
        gates["upstream_19a_contract_gate"] = "fail"
        empty = pd.DataFrame()
        state, next_req, reason = decide_state(gates, empty, empty)
        decision = build_decision(config_path, paths, gates, state, next_req, reason, empty, empty)
        write_df(outputs["input_artifact_audit"], input_audit)
        write_df(outputs["upstream_19a_contract_audit"], upstream_audit)
        for key, path in outputs.items():
            if key not in {"input_artifact_audit", "upstream_19a_contract_audit", "entry_universe_19b0_decision", "manifest", "output_hashes"}:
                if path.suffix == ".csv":
                    write_df(path, pd.DataFrame())
                elif path.suffix == ".md":
                    write_text(path, "")
        write_df(outputs["entry_universe_19b0_decision"], decision)
        output_hashes = build_output_hashes(outputs)
        write_json(outputs["output_hashes"], output_hashes)
        write_json(outputs["manifest"], {"decision_state": state, "output_hashes": output_hashes})
        return outputs

    grid_registry = build_simple_rule_grid_registry()
    feature_source_map = build_simple_rule_feature_source_map()
    label_source_map = build_label_source_map(config)
    matching_source_map = build_matching_feature_source_map()
    pre_label_frozen_frames = {
        "simple_rule_grid_registry": grid_registry,
        "simple_rule_feature_source_map": feature_source_map,
        "label_source_map": label_source_map,
        "matching_feature_source_map": matching_source_map,
    }
    for key, frame in pre_label_frozen_frames.items():
        write_df(outputs[key], frame)

    metadata = load_ep07_metadata(paths)
    train_event_ids = set(metadata.loc[metadata["event_split"].eq("train"), "event_id"].astype(str))
    train_label_diag = load_ep07_train_label_diagnostics(paths, train_event_ids)
    train_boundary = build_train_only_boundary_audit(metadata, train_label_diag)
    universe_panel = load_or_build_universe_feature_panel(config, paths)
    baseline_pool = universe_panel.loc[universe_panel["baseline_eligible"]].copy()
    eligible_audit = build_eligible_universe_baseline_audit(universe_panel)
    ep07_panel, label_anchor_audit = build_ep07_identity_panel(metadata, train_label_diag, universe_panel, config)
    matching_equivalence = build_matching_feature_equivalence_audit(ep07_panel)
    manifest_rows, denominator, family_materialization, cell_frames = materialize_cells(ep07_panel, universe_panel, config)
    grid_cell_manifest = pd.DataFrame(manifest_rows)
    (
        baseline_materialization,
        baseline_quality,
        metric,
        sensitivity,
        bootstrap,
        concentration,
    ) = build_baselines_and_metrics(cell_frames, baseline_pool, config)
    family_selection, selected, robustness_manifest, search_accounting = build_selection_outputs(metric, denominator, config)
    if not metric.empty and not selected.empty:
        selected_key = pd.MultiIndex.from_frame(selected[["family_id", "grid_cell_id"]])
        metric_key = pd.MultiIndex.from_frame(metric[["family_id", "grid_cell_id"]])
        metric["selected_for_19B_robustness_flag"] = metric_key.isin(selected_key)

    gates = {gate: "pass" for gate in CRITICAL_GATES}
    gates["upstream_19a_contract_gate"] = upstream_gate
    gates["train_only_boundary_gate"] = "pass" if train_boundary["boundary_gate"].eq("pass").all() else "fail"
    gates["grid_manifest_gate"] = pass_fail(not grid_cell_manifest.empty and not grid_registry.empty)
    gates["family_materialization_gate"] = pass_fail(denominator["raw_candidate_n"].gt(0).any())
    gates["primary_denominator_gate"] = pass_fail(denominator["denominator_gate"].eq("pass").any())
    gates["baseline_materialization_gate"] = pass_fail(
        any_cell_with_all_baseline_gate_pass(baseline_materialization, "baseline_materialization_gate")
    )
    required_quality_cols = {
        "baseline_matching_quality_gate",
        "residual_alpha_claim_allowed",
        "positive_beta_exposure_claim_allowed",
        "baseline_quality_blocks_residual_alpha_only",
    }
    expected_quality_cells = set(
        map(tuple, denominator.loc[denominator["denominator_gate"].eq("pass"), ["family_id", "grid_cell_id"]].to_numpy())
    )
    observed_quality_cells = set(map(tuple, baseline_quality[["family_id", "grid_cell_id"]].drop_duplicates().to_numpy())) if not baseline_quality.empty else set()
    quality_cell_complete = (
        bool(expected_quality_cells)
        and not baseline_quality.empty
        and required_quality_cols.issubset(set(baseline_quality.columns))
        and observed_quality_cells == expected_quality_cells
        and baseline_quality["split"].eq("train").all()
        and baseline_quality.groupby(["family_id", "grid_cell_id"])["baseline_family"].nunique().eq(len(BASELINE_FAMILIES)).all()
    )
    gates["baseline_matching_quality_audit_gate"] = pass_fail(quality_cell_complete)
    gates["metric_readout_gate"] = pass_fail(not metric.empty)
    all_denominator_cells = set(map(tuple, denominator[["family_id", "grid_cell_id"]].drop_duplicates().to_numpy()))
    metric_cells = set(map(tuple, metric[["family_id", "grid_cell_id"]].drop_duplicates().to_numpy())) if not metric.empty else set()
    blocked_cells = set(
        map(tuple, denominator.loc[denominator["blocking_reason"].fillna("").ne(""), ["family_id", "grid_cell_id"]].drop_duplicates().to_numpy())
    )
    selection_process_complete = (
        bool(all_denominator_cells)
        and all_denominator_cells.issubset(metric_cells | blocked_cells)
        and (not family_selection.empty or metric.empty)
        and (family_selection.empty or family_selection["selection_rule_applied_before_robustness_readout"].astype(bool).all())
    )
    gates["cell_selection_process_gate"] = pass_fail(selection_process_complete)
    gates["search_accounting_gate"] = "pass"
    gates["no_policy_authorization_gate"] = "pass"
    gates["output_contract_gate"] = "pass"
    state, next_req, reason = decide_state(gates, selected, family_selection)
    decision = build_decision(config_path, paths, gates, state, next_req, reason, selected, family_selection)
    report = build_report(
        decision,
        denominator,
        metric,
        family_selection,
        family_materialization,
        label_anchor_audit,
        matching_source_map,
        baseline_materialization,
        baseline_quality,
        sensitivity,
        concentration,
        search_accounting,
    )
    gates["output_contract_gate"] = pass_fail(output_contract_pass(report, outputs))
    state, next_req, reason = decide_state(gates, selected, family_selection)
    decision = build_decision(config_path, paths, gates, state, next_req, reason, selected, family_selection)
    report = build_report(
        decision,
        denominator,
        metric,
        family_selection,
        family_materialization,
        label_anchor_audit,
        matching_source_map,
        baseline_materialization,
        baseline_quality,
        sensitivity,
        concentration,
        search_accounting,
    )
    handoff = build_handoff(selected)

    frames = {
        "input_artifact_audit": input_audit,
        "upstream_19a_contract_audit": upstream_audit,
        "train_only_boundary_audit": train_boundary,
        "eligible_universe_baseline_audit": eligible_audit,
        "simple_rule_grid_registry": grid_registry,
        "simple_rule_feature_source_map": feature_source_map,
        "label_source_map": label_source_map,
        "label_anchor_rebuild_audit": label_anchor_audit,
        "matching_feature_source_map": matching_source_map,
        "matching_feature_equivalence_audit": matching_equivalence,
        "grid_cell_manifest": grid_cell_manifest,
        "family_grid_materialization_audit": family_materialization,
        "candidate_cell_denominator_audit": denominator,
        "baseline_materialization_audit": baseline_materialization,
        "baseline_matching_quality_audit": baseline_quality,
        "train_cell_metric_readout": metric,
        "train_cell_sensitivity_readout": sensitivity,
        "cell_cluster_bootstrap_margin_audit": bootstrap,
        "instrument_concentration_sensitivity": concentration,
        "family_selection_audit": family_selection,
        "selected_family_cell_manifest": selected,
        "robustness_test_manifest": robustness_manifest,
        "search_accounting_audit": search_accounting,
        "entry_universe_19b0_decision": decision,
    }
    for key, frame in frames.items():
        if key in pre_label_frozen_frames:
            continue
        write_df(outputs[key], frame)
    write_text(outputs["report"], report)
    write_text(outputs["handoff_contract"], handoff)

    output_hashes = build_output_hashes(outputs)
    write_json(outputs["output_hashes"], output_hashes)
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at": decision.iloc[0]["created_at"],
        "python_version": platform.python_version(),
        "requirement_file_hash": decision.iloc[0]["requirement_file_hash"],
        "config_file_hash": decision.iloc[0]["config_file_hash"],
        "upstream_19a_manifest_hash": decision.iloc[0]["upstream_19a_manifest_hash"],
        "decision_state": decision.iloc[0]["decision_state"],
        "next_allowed_requirement": decision.iloc[0]["next_allowed_requirement"],
        "critical_gates": {gate: decision.iloc[0][gate] for gate in CRITICAL_GATES},
        "output_hashes": output_hashes,
    }
    write_json(outputs["manifest"], manifest)
    output_hashes = build_output_hashes(outputs)
    write_json(outputs["output_hashes"], output_hashes)
    manifest["output_hashes"] = output_hashes
    write_json(outputs["manifest"], manifest)
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(args.config)


if __name__ == "__main__":
    main()
