#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

try:  # pragma: no cover - exercised by availability tests via monkeypatch.
    from sklearn.ensemble import HistGradientBoostingClassifier
except Exception:  # pragma: no cover
    HistGradientBoostingClassifier = None


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUNNER_13C_PATH = EXPERIMENT_DIR / "src" / "run_13c_morphology_orthogonal_residual_importance_diagnostic.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r13c = load_runner(RUNNER_13C_PATH, "run_13c_morphology_orthogonal_residual_importance_diagnostic")
r13a = r13c.r13a
r13a3 = r13c.r13a3


RUN_ID = "13E_nonlinear_winner_train_kfold_feasibility_diagnostic"
EXPERIMENT_ID = "13_full_pit_native_event_discovery_v0"
PHASE_ID = "13E"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_13e_nonlinear_winner_train_kfold_feasibility_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
SELECTED_LABEL_ID = "vol20d_kup2p0_kdn1p0_H20"
MODEL_FAMILIES = ("logistic_l2", "sklearn_hgb_low_capacity")
FEATURE_SETS = ("baseline_feature_set", "augmented_feature_set")
METRICS = (
    "auc",
    "logloss",
    "winner_uplift_topN",
    "utility_proxy_0bps",
    "utility_proxy_50bps",
    "utility_proxy_100bps",
)
REPORT_INPUT_KEYS = {"upstream_report_13c"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run 13E nonlinear winner train-kfold feasibility diagnostic."
    )
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


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
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_13c_lineage_audit": TABLE_DIR / "upstream_13c_lineage_audit.csv",
        "row_level_rebuild_audit": TABLE_DIR / "row_level_rebuild_audit.csv",
        "train_kfold_fold_metrics": TABLE_DIR / "train_kfold_fold_metrics.csv",
        "nonlinear_vs_linear_comparison": TABLE_DIR / "nonlinear_vs_linear_comparison.csv",
        "train_kfold_uniqueness_audit": TABLE_DIR / "train_kfold_uniqueness_audit.csv",
        "search_multiplicity_audit": TABLE_DIR / "search_multiplicity_audit.csv",
        "nonlinear_winner_train_kfold_feasibility_decision": TABLE_DIR / "nonlinear_winner_train_kfold_feasibility_decision.csv",
        "report": REPORT_DIR / "nonlinear_winner_train_kfold_feasibility_diagnostic_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r13c.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r13c.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r13c.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r13c.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r13c.file_sha(path)


def count_rows(path: Path) -> int | float:
    return r13c.count_rows(path)


def stable_hash(value: Any) -> str:
    return r13c.stable_hash(value)


def boolish(value: Any) -> bool:
    return r13c.boolish(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r13c.bool_series(series)


def finite_numeric(series: pd.Series) -> pd.Series:
    return r13c.finite_numeric(series)


def auc_score(values: pd.Series, labels: pd.Series) -> float:
    return r13c.auc_score(values, labels)


def input_expected_columns() -> dict[str, tuple[str, ...]]:
    return {
        "requirement": (),
        "upstream_requirement_13c": (),
        "upstream_report_13c": (),
        "upstream_13c_manifest": (),
        "upstream_13c_decision": (
            "decision_state",
            "selected_state_id",
            "meta_labeling_authorized",
            "sequence_mining_authorized",
            "bet_sizing_authorized",
        ),
        "upstream_13c_feature_cluster_dictionary": (
            "cluster_id",
            "feature_id",
            "feature_status",
        ),
        "upstream_13c_sample_uniqueness_audit": (
            "state_id",
            "split_bucket",
            "sample_uniqueness_gate_status",
        ),
        "upstream_13c_incremental_model_comparison": ("target_id", "split_bucket"),
        "upstream_13c_clustered_mda_importance": ("target_id", "split_bucket"),
        "upstream_13c_morphology_residual_panel_cache": (
            "row_id",
            "split_bucket",
            "native_scope",
            "winner_positive",
        ),
        "pit_topn_400_100_executable_daily": ("usable_trade_date", "instrument"),
        "pit_topn_400_100_membership_daily": ("membership_date", "instrument"),
        "stock_daily_qfq_dir": (),
        "global_regime_calendar": ("date", "daily_regime_bucket"),
    }


def lineage_role_for_artifact(artifact_id: str) -> str:
    if artifact_id in REPORT_INPUT_KEYS:
        return "lineage_report_only_not_row_truth"
    if artifact_id.startswith("upstream_13c"):
        return "upstream_13c_lineage"
    if artifact_id.startswith("pit_") or artifact_id in {
        "stock_daily_qfq_dir",
        "global_regime_calendar",
    }:
        return "raw_pit_lineage_guard"
    return "run_config_input"


def build_input_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    expected = input_expected_columns()
    rows: list[dict[str, Any]] = []
    for artifact_id, path in resolved.items():
        required_cols = expected.get(artifact_id, ())
        read_status = "pass" if path.exists() else "missing"
        schema_status = "not_checked"
        column_count: int | float = np.nan
        row_count: int | float = np.nan
        if path.exists():
            try:
                if path.is_dir():
                    schema_status = "directory"
                    row_count = count_rows(path)
                else:
                    suffixes = "".join(path.suffixes)
                    if suffixes.endswith(".parquet"):
                        import pyarrow.parquet as pq

                        parquet_file = pq.ParquetFile(path)
                        columns = list(parquet_file.schema_arrow.names)
                        column_count = len(columns)
                        row_count = int(parquet_file.metadata.num_rows)
                        missing = sorted(set(required_cols) - set(columns)) if required_cols else []
                        schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
                        rows.append(
                            {
                                "artifact_id": artifact_id,
                                "resolved_path": str(path),
                                "row_count": row_count,
                                "column_count": column_count,
                                "sha256": file_sha(path),
                                "schema_status": schema_status,
                                "read_status": read_status,
                                "required_flag": True,
                                "lineage_role": lineage_role_for_artifact(artifact_id),
                            }
                        )
                        continue
                    elif suffixes.endswith((".csv", ".csv.gz")):
                        sample = pd.read_csv(path, nrows=5, low_memory=False)
                    else:
                        sample = pd.DataFrame()
                    if suffixes.endswith((".csv", ".csv.gz", ".parquet")):
                        column_count = len(sample.columns)
                    missing = sorted(set(required_cols) - set(sample.columns)) if required_cols else []
                    schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
                    row_count = count_rows(path)
            except Exception as exc:
                read_status = f"read_error:{type(exc).__name__}"
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_sha(path),
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": True,
                "lineage_role": lineage_role_for_artifact(artifact_id),
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    bad = input_audit.loc[
        input_audit["required_flag"].astype(bool)
        & (
            input_audit["read_status"].astype(str).ne("pass")
            | input_audit["schema_status"].astype(str).str.startswith("missing_columns")
        )
    ]
    if len(bad):
        return "fail", ";".join(bad["artifact_id"].astype(str).tolist())
    return "pass", ""


def lineage_row(
    check_id: str,
    observed: Any,
    expected: Any,
    ok: bool,
    artifact_key: str,
    resolved: dict[str, Path],
) -> dict[str, Any]:
    path = resolved.get(artifact_key, Path(""))
    return {
        "lineage_source_id": "13C",
        "lineage_check_id": check_id,
        "observed_value": observed,
        "expected_value": expected,
        "lineage_status": "pass" if ok else "fail",
        "artifact_path": str(path),
        "sha256": file_sha(path) if path and path.exists() else "",
    }


def build_upstream_lineage_audit(
    resolved: dict[str, Path],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, str, str]:
    rows: list[dict[str, Any]] = []
    status = "pass"
    reason: list[str] = []

    def add(check_id: str, observed: Any, expected: Any, ok: bool, artifact_key: str) -> None:
        nonlocal status
        rows.append(lineage_row(check_id, observed, expected, ok, artifact_key, resolved))
        if not ok and status == "pass":
            status = "fail"
        if not ok:
            reason.append(check_id)

    try:
        decision = read_table(resolved["upstream_13c_decision"]).iloc[0]
        if boolish(decision.get("meta_labeling_authorized", False)) or boolish(
            decision.get("sequence_mining_authorized", False)
        ):
            add(
                "13c_not_already_authorized",
                f"meta={decision.get('meta_labeling_authorized')};sequence={decision.get('sequence_mining_authorized')}",
                "False/False",
                False,
                "upstream_13c_decision",
            )
            return pd.DataFrame(rows), "fail_already_authorized", "upstream_13c_already_authorized"
        required = {
            "input_gate_status": "pass",
            "upstream_lineage_gate_status": "pass",
            "row_level_rebuild_gate_status": "pass",
            "decision_state": "13C_stop_residual_probability_only_no_utility",
            "selected_state_id": "repair_range_participation_core_30",
        }
        for key, expected in required.items():
            observed = str(decision.get(key, ""))
            add(key, observed, expected, observed == expected, "upstream_13c_decision")
        add(
            "sample_uniqueness_gate_status",
            decision.get("sample_uniqueness_gate_status", ""),
            "pass_with_exact_t1|pass_with_downstream_exact_t1_requirement",
            str(decision.get("sample_uniqueness_gate_status", ""))
            in {"pass_with_exact_t1", "pass_with_downstream_exact_t1_requirement"},
            "upstream_13c_decision",
        )
        for auth_col in [
            "sequence_mining_authorized",
            "meta_labeling_authorized",
            "bet_sizing_authorized",
        ]:
            add(
                auth_col,
                decision.get(auth_col, ""),
                "False",
                not boolish(decision.get(auth_col, False)),
                "upstream_13c_decision",
            )
    except Exception as exc:
        add(
            "decision_read",
            f"{type(exc).__name__}:{exc}",
            "readable",
            False,
            "upstream_13c_decision",
        )

    for key in [
        "upstream_13c_manifest",
        "upstream_13c_feature_cluster_dictionary",
        "upstream_13c_sample_uniqueness_audit",
        "upstream_13c_incremental_model_comparison",
        "upstream_13c_clustered_mda_importance",
        "upstream_13c_morphology_residual_panel_cache",
    ]:
        path = resolved[key]
        add(f"{key}.exists", path.exists(), True, path.exists(), key)

    try:
        manifest = json.loads(resolved["upstream_13c_manifest"].read_text(encoding="utf-8"))
        cache_rows = {
            str(row.get("artifact_id")): row
            for row in manifest.get("local_cache_audit", [])
        }
        panel_row = cache_rows.get("morphology_residual_panel", {})
        observed_schema = schema_hash(resolved["upstream_13c_morphology_residual_panel_cache"])
        expected_schema = str(panel_row.get("schema_hash", ""))
        add(
            "morphology_residual_panel.manifest_schema_hash",
            observed_schema,
            expected_schema,
            bool(expected_schema) and observed_schema == expected_schema,
            "upstream_13c_morphology_residual_panel_cache",
        )
        observed_rows = int(count_rows(resolved["upstream_13c_morphology_residual_panel_cache"]))
        expected_rows = int(panel_row.get("row_count", -1))
        add(
            "morphology_residual_panel.manifest_row_count",
            observed_rows,
            expected_rows,
            observed_rows == expected_rows,
            "upstream_13c_morphology_residual_panel_cache",
        )
    except Exception as exc:
        add(
            "morphology_residual_panel.manifest_cache_audit",
            f"{type(exc).__name__}:{exc}",
            "manifest schema/row_count comparable",
            False,
            "upstream_13c_manifest",
        )

    try:
        feature_dict = read_table(resolved["upstream_13c_feature_cluster_dictionary"])
        expected_pairs = {
            (cluster_id, feature)
            for cluster_id, features in config.get("feature_clusters", {}).items()
            for feature in features
        }
        observed_pairs = set(
            zip(
                feature_dict["cluster_id"].astype(str),
                feature_dict["feature_id"].astype(str),
            )
        )
        missing_pairs = sorted(expected_pairs - observed_pairs)
        add(
            "feature_cluster_dictionary.expected_pairs_present",
            len(missing_pairs),
            0,
            not missing_pairs,
            "upstream_13c_feature_cluster_dictionary",
        )
        required_features = required_feature_columns(config)
        required_rows = feature_dict.loc[
            feature_dict["feature_id"].astype(str).isin(required_features)
        ]
        bad_features = required_rows.loc[
            required_rows["feature_status"].astype(str).ne("pass")
        ]
        add(
            "feature_cluster_dictionary.required_features_pass",
            ";".join(bad_features["feature_id"].astype(str).tolist()),
            "",
            bad_features.empty,
            "upstream_13c_feature_cluster_dictionary",
        )
    except Exception as exc:
        add(
            "feature_cluster_dictionary.contract_read",
            f"{type(exc).__name__}:{exc}",
            "readable and comparable",
            False,
            "upstream_13c_feature_cluster_dictionary",
        )
    return pd.DataFrame(rows), status, ";".join(reason)


def required_feature_columns(config: dict[str, Any]) -> list[str]:
    clusters = config.get("feature_clusters", {})
    names: list[str] = []
    for cluster in [
        "cluster_drawdown_morphology",
        "cluster_denominator_controls",
        "cluster_compression",
        "cluster_position_strength",
        "cluster_participation",
    ]:
        names.extend(clusters.get(cluster, []))
    return list(dict.fromkeys(names))


def feature_columns_for_set(config: dict[str, Any], feature_set: str) -> list[str]:
    clusters = config.get("feature_clusters", {})
    names = clusters.get("cluster_drawdown_morphology", []) + clusters.get(
        "cluster_denominator_controls", []
    )
    if feature_set == "augmented_feature_set":
        names += (
            clusters.get("cluster_compression", [])
            + clusters.get("cluster_position_strength", [])
            + clusters.get("cluster_participation", [])
        )
    return list(dict.fromkeys(names))


def required_row_columns(config: dict[str, Any]) -> list[str]:
    return [
        "row_id",
        "instrument",
        "reference_date",
        "split_bucket",
        "board_bucket",
        "calendar_year",
        "calendar_month",
        "market_regime_bucket",
        "entry_date",
        "entry_price",
        "entry_pos",
        "winner_positive",
        "upper_first",
        "lower_first",
        "fast_fail",
        "neutral",
        "censored",
        "same_bar_conflict",
        "horizon_complete",
        "upper_barrier",
        "lower_barrier",
        "time_to_upper",
        "time_to_lower",
        "horizon_sessions",
        "row_utility_component_0bps",
        "row_utility_component_50bps",
        "row_utility_component_100bps",
        "utility_positive_50bps",
        *required_feature_columns(config),
    ]


def load_train_rows_only(panel_path: Path) -> pd.DataFrame:
    return pd.read_parquet(panel_path, filters=[("split_bucket", "==", "train")])


def add_global_calendar_session_pos(
    events: pd.DataFrame,
    calendar_source: pd.DataFrame | None = None,
) -> pd.DataFrame:
    out = events.copy()
    date_col = "entry_date" if "entry_date" in out.columns else "reference_date"
    dates = pd.to_datetime(out[date_col], errors="coerce")
    if calendar_source is not None and date_col in calendar_source.columns:
        source_dates = pd.to_datetime(calendar_source[date_col], errors="coerce")
        unique_dates = (
            pd.Series(source_dates.dropna().unique())
            .sort_values(kind="mergesort")
            .reset_index(drop=True)
        )
        date_to_pos = {date: int(pos) for pos, date in unique_dates.items()}
        out["global_calendar_session_pos"] = dates.map(date_to_pos)
    else:
        out["global_calendar_session_pos"] = dates.map(
            lambda x: x.toordinal() if pd.notna(x) else np.nan
        )
    return out


def prepare_train_event_panel(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    out = panel.copy()
    if "split_bucket" not in out.columns and "split" in out.columns:
        out["split_bucket"] = out["split"].astype(str)
    if "native_scope" not in out.columns:
        out["native_scope"] = True
    if selected not in out.columns:
        raise KeyError(f"missing selected_state column: {selected}")
    calendar_source = out
    out = out.loc[
        out["split_bucket"].astype(str).eq("train")
        & bool_series(out["native_scope"])
        & bool_series(out[selected])
    ].copy()
    out["event_start_pos"] = finite_numeric(out["entry_pos"])
    out["event_offset"] = r13c.event_touch_offsets(out)
    out["event_end_pos"] = out["event_start_pos"] + out["event_offset"]
    out = add_global_calendar_session_pos(out, calendar_source=calendar_source)
    return out


def build_row_level_rebuild_audit(
    train_events: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, str, str]:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    min_train = int(config.get("thresholds", {}).get("min_train_event_n", 1000))
    missing_cols = sorted(set(required_row_columns(config)) - set(train_events.columns))
    required_features = required_feature_columns(config)
    empty_features = [
        col
        for col in required_features
        if col in train_events.columns and train_events[col].notna().sum() == 0
    ]
    non_train_rows = int(train_events["split_bucket"].astype(str).ne("train").sum()) if "split_bucket" in train_events else len(train_events)
    bad_span = int(
        (
            finite_numeric(train_events.get("event_start_pos", pd.Series(np.nan, index=train_events.index))).isna()
            | finite_numeric(train_events.get("event_end_pos", pd.Series(np.nan, index=train_events.index))).isna()
            | finite_numeric(train_events.get("global_calendar_session_pos", pd.Series(np.nan, index=train_events.index))).isna()
        ).sum()
    )
    duplicate_key_n = (
        int(train_events.duplicated(["instrument", "reference_date"]).sum())
        if {"instrument", "reference_date"} <= set(train_events.columns)
        else len(train_events)
    )
    status = (
        "pass"
        if len(train_events) >= min_train
        and not missing_cols
        and not empty_features
        and non_train_rows == 0
        and bad_span == 0
        and duplicate_key_n == 0
        else "fail"
    )
    reason_parts = []
    if len(train_events) < min_train:
        reason_parts.append("train_event_n_below_min")
    if missing_cols:
        reason_parts.append("missing_columns:" + ";".join(missing_cols))
    if empty_features:
        reason_parts.append("empty_features:" + ";".join(empty_features))
    if non_train_rows:
        reason_parts.append("non_train_rows_present")
    if bad_span:
        reason_parts.append("event_span_unavailable")
    if duplicate_key_n:
        reason_parts.append("instrument_reference_date_not_unique")
    audit = pd.DataFrame(
        [
            {
                "audit_id": "13e_train_selected_event_panel",
                "selected_state_id": selected,
                "row_count": len(train_events),
                "unique_row_id_count": int(train_events["row_id"].nunique()) if "row_id" in train_events else 0,
                "non_train_row_count": non_train_rows,
                "required_column_missing_count": len(missing_cols),
                "missing_required_columns": ";".join(missing_cols),
                "empty_required_features": ";".join(empty_features),
                "event_span_unavailable_n": bad_span,
                "instrument_reference_date_duplicate_n": duplicate_key_n,
                "min_train_event_n": min_train,
                "membership_source": "13C_morphology_residual_panel_cache",
                "report_text_used_as_row_truth": False,
                "bucket_refit_in_13e": False,
                "validation_rows_used": False,
                "robustness_rows_used": False,
                "status": status,
            }
        ]
    )
    return audit, status, ";".join(reason_parts)


def label_lineage_status(train_events: pd.DataFrame, config: dict[str, Any]) -> tuple[str, str]:
    expected = config.get("selected_label", {})
    if train_events.empty:
        return "fail", "empty_train_events"
    checks: list[bool] = []
    reasons: list[str] = []
    if "label_id" in train_events.columns:
        ok = train_events["label_id"].astype(str).eq(str(expected.get("label_id", SELECTED_LABEL_ID))).all()
        checks.append(bool(ok))
        if not ok:
            reasons.append("label_id_mismatch")
    if "horizon_sessions" in train_events.columns:
        ok = finite_numeric(train_events["horizon_sessions"]).eq(
            float(expected.get("horizon_sessions", 20))
        ).all()
        checks.append(bool(ok))
        if not ok:
            reasons.append("horizon_sessions_mismatch")
    if "horizon_complete" in train_events.columns:
        ok = bool_series(train_events["horizon_complete"]).all()
        checks.append(bool(ok))
        if not ok:
            reasons.append("horizon_incomplete")
    if "same_bar_conflict" in train_events.columns and "lower_first" in train_events.columns:
        same = bool_series(train_events["same_bar_conflict"])
        ok = bool_series(train_events.loc[same, "lower_first"]).all() if bool(same.any()) else True
        checks.append(bool(ok))
        if not ok:
            reasons.append("same_bar_priority_not_lower_first")
    return ("pass", "") if checks and all(checks) else ("fail", ";".join(reasons) or "missing_label_checks")


def assign_chronological_folds(events: pd.DataFrame, fold_n: int) -> pd.DataFrame:
    out = events.copy()
    dates = pd.to_datetime(out["reference_date"], errors="coerce")
    ordered_dates = pd.Series(dates.dropna().unique()).sort_values(kind="mergesort").to_numpy()
    folds = np.array_split(ordered_dates, int(fold_n))
    out["fold_id"] = -1
    date_series = pd.Series(dates, index=out.index)
    for fold_id, fold_dates in enumerate(folds):
        out.loc[date_series.isin(fold_dates), "fold_id"] = fold_id
    return out


def purged_train_for_fold(
    events: pd.DataFrame,
    fold_id: int,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    protocol = config.get("fold_protocol", {})
    embargo = int(protocol.get("embargo_sessions", 20))
    events = add_global_calendar_session_pos(events) if "global_calendar_session_pos" not in events.columns else events.copy()
    test = events.loc[events["fold_id"].eq(fold_id)].copy()
    candidate = events.loc[~events["fold_id"].eq(fold_id)].copy()
    purged = pd.Series(False, index=candidate.index)
    for inst, test_g in test.groupby("instrument", dropna=False):
        train_idx = candidate.index[candidate["instrument"].astype(str).eq(str(inst))]
        if len(train_idx) == 0:
            continue
        starts = finite_numeric(candidate.loc[train_idx, "event_start_pos"]).to_numpy(dtype=float)
        ends = finite_numeric(candidate.loc[train_idx, "event_end_pos"]).to_numpy(dtype=float)
        test_starts = finite_numeric(test_g["event_start_pos"]).to_numpy(dtype=float)
        test_ends = finite_numeric(test_g["event_end_pos"]).to_numpy(dtype=float)
        overlap = ((starts[:, None] <= test_ends[None, :]) & (ends[:, None] >= test_starts[None, :])).any(axis=1)
        purged.loc[train_idx] = overlap
    after_purge = candidate.loc[~purged].copy()
    test_pos = finite_numeric(test["global_calendar_session_pos"])
    low = float(test_pos.min()) - embargo
    high = float(test_pos.max()) + embargo
    embargoed = finite_numeric(after_purge["global_calendar_session_pos"]).between(low, high, inclusive="both")
    train = after_purge.loc[~embargoed].copy()
    return train, test, int(purged.sum()), int(embargoed.sum())


def uniqueness_readout(events: pd.DataFrame) -> tuple[pd.Series, list[int], str]:
    avg, concurrency, status = r13c.exact_uniqueness(events)
    if status != "pass_with_exact_t1":
        return avg, concurrency, "exact_uniqueness_unavailable"
    return avg, concurrency, "pass_with_exact_t1"


def fold_sample_uniqueness_status(
    train: pd.DataFrame,
    test: pd.DataFrame,
    train_status: str,
    config: dict[str, Any],
) -> str:
    protocol = config.get("fold_protocol", {})
    min_train = int(protocol.get("min_effective_train_event_n_per_fold", 300))
    min_test = int(protocol.get("min_effective_test_event_n_per_fold", 50))
    if train_status != "pass_with_exact_t1":
        return "exact_uniqueness_unavailable"
    if len(train) < min_train or len(test) < min_test:
        return "purged_cv_integrity_caveat"
    return "pass_with_exact_t1"


@dataclass
class FoldModel:
    model_family: str
    feature_set: str
    spec: Any
    model: Any | None
    constant_probability: float | None


def fit_fold_model(
    model_family: str,
    feature_set: str,
    train: pd.DataFrame,
    features: list[str],
    sample_weight: pd.Series,
    config: dict[str, Any],
) -> FoldModel:
    spec = r13c.fit_design_spec(train, [f for f in features if f in train.columns])
    y = bool_series(train["winner_positive"]).astype(int).to_numpy()
    if len(np.unique(y)) < 2:
        return FoldModel(model_family, feature_set, spec, None, float(y.mean()) if len(y) else 0.0)
    x = r13c.transform_design(train, spec)
    weights = finite_numeric(sample_weight).fillna(1.0).to_numpy(dtype=float)
    if model_family == "logistic_l2":
        params = config.get("model", {}).get("logistic_l2", {})
        model = LogisticRegression(
            C=float(params.get("C", 0.5)),
            penalty=str(params.get("penalty", "l2")),
            solver=str(params.get("solver", "liblinear")),
            max_iter=int(params.get("max_iter", 200)),
        )
        model.fit(x, y, sample_weight=weights)
        return FoldModel(model_family, feature_set, spec, model, None)
    if HistGradientBoostingClassifier is None:
        raise RuntimeError("HistGradientBoostingClassifier unavailable")
    params = config.get("model", {}).get("sklearn_hgb_low_capacity", {})
    model = HistGradientBoostingClassifier(
        loss=str(params.get("loss", "log_loss")),
        max_iter=int(params.get("max_iter", 200)),
        learning_rate=float(params.get("learning_rate", 0.03)),
        max_leaf_nodes=int(params.get("max_leaf_nodes", 15)),
        max_depth=int(params.get("max_depth", 4)),
        min_samples_leaf=int(params.get("min_samples_leaf", 100)),
        l2_regularization=float(params.get("l2_regularization", 1.0)),
        random_state=int(params.get("random_state", 13050)),
        early_stopping=bool(params.get("early_stopping", False)),
    )
    model.fit(x, y, sample_weight=weights)
    return FoldModel(model_family, feature_set, spec, model, None)


def predict_fold_model(fit: FoldModel, frame: pd.DataFrame) -> np.ndarray:
    if fit.model is None:
        return np.full(len(frame), float(fit.constant_probability or 0.0), dtype=float)
    x = r13c.transform_design(frame, fit.spec)
    return fit.model.predict_proba(x)[:, 1]


def metric_readout(frame: pd.DataFrame, scores: np.ndarray, top_fraction: float) -> dict[str, float]:
    y = bool_series(frame["winner_positive"])
    auc = auc_score(pd.Series(scores, index=frame.index), y)
    if int(y.sum()) == 0 or int((~y).sum()) == 0:
        ll = np.nan
    else:
        ll = float(log_loss(y.astype(int).to_numpy(), np.clip(scores, 1e-6, 1 - 1e-6), labels=[0, 1]))
    top_n = max(1, int(round(float(top_fraction) * len(frame)))) if len(frame) else 0
    if len(frame) and top_n > 0:
        order = np.argsort(scores)[::-1][:top_n]
        top = frame.iloc[order]
        winner_uplift = float(bool_series(top["winner_positive"]).mean() - y.mean())
        u0 = float(finite_numeric(top["row_utility_component_0bps"]).mean())
        u50 = float(finite_numeric(top["row_utility_component_50bps"]).mean())
        u100 = float(finite_numeric(top["row_utility_component_100bps"]).mean())
    else:
        winner_uplift = np.nan
        u0 = u50 = u100 = np.nan
    return {
        "auc": auc,
        "logloss": ll,
        "winner_uplift_topN": winner_uplift,
        "utility_proxy_0bps": u0,
        "utility_proxy_50bps": u50,
        "utility_proxy_100bps": u100,
        "top_n": top_n,
        "test_winner_base_rate": float(y.mean()) if len(y) else np.nan,
    }


def build_train_kfold_outputs(
    train_events: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    protocol = config.get("fold_protocol", {})
    fold_n = int(protocol.get("fold_n", 5))
    top_fraction = float(config.get("model", {}).get("top_fraction", 0.20))
    state_id = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    folded = assign_chronological_folds(train_events, fold_n)
    metric_rows: list[dict[str, Any]] = []
    uniqueness_rows: list[dict[str, Any]] = []
    fold_payloads: list[tuple[int, pd.DataFrame, pd.DataFrame, pd.Series, int, int]] = []
    for fold_id in sorted(folded["fold_id"].unique()):
        train, test, purged_n, embargoed_n = purged_train_for_fold(folded, int(fold_id), config)
        train_uniqueness, train_concurrency, train_exact = uniqueness_readout(train)
        test_uniqueness, test_concurrency, test_exact = uniqueness_readout(test)
        sample_status = fold_sample_uniqueness_status(train, test, train_exact, config)
        uniqueness_rows.append(
            {
                "state_id": state_id,
                "fold_id": int(fold_id),
                "event_n": len(test),
                "t1_reconstruction_status": "exact_t1_reconstructed"
                if train_exact == "pass_with_exact_t1" and test_exact == "pass_with_exact_t1"
                else "t1_unavailable",
                "purged_rows_n": purged_n,
                "embargoed_rows_n": embargoed_n,
                "effective_train_event_n": len(train),
                "effective_test_event_n": len(test),
                "train_mean_average_uniqueness": float(train_uniqueness.mean())
                if len(train_uniqueness)
                else np.nan,
                "train_median_average_uniqueness": float(train_uniqueness.median())
                if len(train_uniqueness)
                else np.nan,
                "train_p10_average_uniqueness": float(train_uniqueness.quantile(0.10))
                if len(train_uniqueness)
                else np.nan,
                "train_mean_concurrency": float(np.mean(train_concurrency))
                if train_concurrency
                else np.nan,
                "train_p95_concurrency": float(np.quantile(train_concurrency, 0.95))
                if train_concurrency
                else np.nan,
                "test_mean_average_uniqueness": float(test_uniqueness.mean())
                if len(test_uniqueness)
                else np.nan,
                "test_mean_concurrency": float(np.mean(test_concurrency))
                if test_concurrency
                else np.nan,
                "sample_uniqueness_gate_status": sample_status,
            }
        )
        fold_payloads.append((int(fold_id), train, test, train_uniqueness, purged_n, embargoed_n))
    uniqueness = pd.DataFrame(uniqueness_rows)
    if sample_uniqueness_gate_status(uniqueness) != "pass_with_exact_t1":
        return pd.DataFrame(metric_rows), uniqueness
    for fold_id, train, test, train_uniqueness, purged_n, embargoed_n in fold_payloads:
        for feature_set in FEATURE_SETS:
            features = feature_columns_for_set(config, feature_set)
            for model_family in MODEL_FAMILIES:
                fit = fit_fold_model(
                    model_family,
                    feature_set,
                    train,
                    features,
                    train_uniqueness,
                    config,
                )
                scores = predict_fold_model(fit, test)
                metrics = metric_readout(test, scores, top_fraction)
                metric_rows.append(
                    {
                        "fold_id": int(fold_id),
                        "model_family": model_family,
                        "feature_set": feature_set,
                        "train_event_n": len(train),
                        "test_event_n": len(test),
                        "purged_rows_n": purged_n,
                        "embargoed_rows_n": embargoed_n,
                        "sample_weight_source": "fold_local_exact_event_span_average_uniqueness",
                        "validation_used_in_13e": False,
                        "robustness_used_in_13e": False,
                        **metrics,
                    }
                )
    return pd.DataFrame(metric_rows), uniqueness


def fold_std(values: pd.Series) -> float:
    numeric = finite_numeric(values).dropna()
    if len(numeric) <= 1:
        return 0.0 if len(numeric) == 1 else np.nan
    return float(numeric.std(ddof=1))


def build_nonlinear_vs_linear_comparison(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if fold_metrics.empty:
        return pd.DataFrame(
            columns=[
                "feature_set",
                "metric_id",
                "logistic_fold_mean",
                "logistic_fold_std",
                "sklearn_hgb_fold_mean",
                "sklearn_hgb_fold_std",
                "nonlinear_minus_linear_delta",
                "delta_fold_std",
                "delta_sign",
                "comparison_status",
            ]
        )
    for feature_set in FEATURE_SETS:
        sub = fold_metrics.loc[fold_metrics["feature_set"].eq(feature_set)]
        for metric_id in METRICS:
            logi = sub.loc[sub["model_family"].eq("logistic_l2"), ["fold_id", metric_id]]
            hgb = sub.loc[sub["model_family"].eq("sklearn_hgb_low_capacity"), ["fold_id", metric_id]]
            merged = logi.merge(hgb, on="fold_id", suffixes=("_logistic", "_hgb"))
            logistic_values = finite_numeric(logi[metric_id])
            hgb_values = finite_numeric(hgb[metric_id])
            logistic_mean = float(logistic_values.mean()) if logistic_values.notna().any() else np.nan
            hgb_mean = float(hgb_values.mean()) if hgb_values.notna().any() else np.nan
            delta = hgb_mean - logistic_mean if pd.notna(hgb_mean) and pd.notna(logistic_mean) else np.nan
            fold_delta = finite_numeric(merged[f"{metric_id}_hgb"]) - finite_numeric(
                merged[f"{metric_id}_logistic"]
            )
            delta_std = fold_std(fold_delta)
            if pd.isna(delta):
                sign = "missing"
                status = "missing"
            elif abs(delta) <= 1e-12:
                sign = "zero"
                status = "tie"
            else:
                sign = "positive" if delta > 0 else "negative"
                if metric_id == "logloss":
                    status = "nonlinear_better" if delta < 0 else "linear_better"
                else:
                    status = "nonlinear_better" if delta > 0 else "linear_better"
            rows.append(
                {
                    "feature_set": feature_set,
                    "metric_id": metric_id,
                    "logistic_fold_mean": logistic_mean,
                    "logistic_fold_std": fold_std(logistic_values),
                    "sklearn_hgb_fold_mean": hgb_mean,
                    "sklearn_hgb_fold_std": fold_std(hgb_values),
                    "nonlinear_minus_linear_delta": delta,
                    "delta_fold_std": delta_std,
                    "delta_sign": sign,
                    "comparison_status": status,
                }
            )
    return pd.DataFrame(rows)


def comparison_value(comparison: pd.DataFrame, metric_id: str, column: str) -> float:
    rows = comparison.loc[
        comparison["feature_set"].eq("augmented_feature_set")
        & comparison["metric_id"].eq(metric_id)
    ]
    if rows.empty:
        return np.nan
    return float(rows.iloc[0].get(column, np.nan))


def positive_fold_count(fold_metrics: pd.DataFrame, metric_id: str) -> int:
    sub = fold_metrics.loc[fold_metrics["feature_set"].eq("augmented_feature_set")]
    logi = sub.loc[sub["model_family"].eq("logistic_l2"), ["fold_id", metric_id]]
    hgb = sub.loc[sub["model_family"].eq("sklearn_hgb_low_capacity"), ["fold_id", metric_id]]
    merged = logi.merge(hgb, on="fold_id", suffixes=("_logistic", "_hgb"))
    delta = finite_numeric(merged[f"{metric_id}_hgb"]) - finite_numeric(merged[f"{metric_id}_logistic"])
    return int(delta.gt(0).sum())


def nonlinear_auc_gate_status(
    comparison: pd.DataFrame,
    fold_metrics: pd.DataFrame,
    config: dict[str, Any],
) -> str:
    auc_delta = comparison_value(comparison, "auc", "nonlinear_minus_linear_delta")
    min_delta = float(config.get("thresholds", {}).get("auc_improvement_min", 0.005))
    return "pass" if pd.notna(auc_delta) and auc_delta > min_delta and positive_fold_count(fold_metrics, "auc") >= 3 else "fail"


def nonlinear_uplift_gate_status(comparison: pd.DataFrame, fold_metrics: pd.DataFrame) -> str:
    uplift_delta = comparison_value(comparison, "winner_uplift_topN", "nonlinear_minus_linear_delta")
    return "pass" if pd.notna(uplift_delta) and uplift_delta > 0 and positive_fold_count(fold_metrics, "winner_uplift_topN") >= 3 else "fail"


def nonlinear_utility_gate_status(
    comparison: pd.DataFrame,
    auc_status: str,
    uplift_status: str,
) -> str:
    hgb_mean = comparison_value(comparison, "utility_proxy_50bps", "sklearn_hgb_fold_mean")
    hgb_std = comparison_value(comparison, "utility_proxy_50bps", "sklearn_hgb_fold_std")
    delta = comparison_value(comparison, "utility_proxy_50bps", "nonlinear_minus_linear_delta")
    hard = (
        pd.notna(hgb_mean)
        and pd.notna(hgb_std)
        and pd.notna(delta)
        and hgb_mean > 0
        and delta > 0
        and hgb_mean - hgb_std > 0
    )
    if hard:
        return "pass"
    if auc_status == "pass" and uplift_status == "pass":
        return "probability_only_no_utility"
    return "fail"


def sample_uniqueness_gate_status(uniqueness: pd.DataFrame) -> str:
    if uniqueness.empty or "sample_uniqueness_gate_status" not in uniqueness.columns:
        return "exact_uniqueness_unavailable"
    statuses = set(uniqueness["sample_uniqueness_gate_status"].astype(str).tolist())
    if "exact_uniqueness_unavailable" in statuses:
        return "exact_uniqueness_unavailable"
    if "purged_cv_integrity_caveat" in statuses:
        return "purged_cv_integrity_caveat"
    if statuses == {"pass_with_exact_t1"}:
        return "pass_with_exact_t1"
    return "exact_uniqueness_unavailable"


def purged_cv_integrity_gate_status(uniqueness: pd.DataFrame) -> str:
    return "pass" if sample_uniqueness_gate_status(uniqueness) == "pass_with_exact_t1" else "fail"


def nonlinear_model_availability_gate_status() -> str:
    return "pass" if HistGradientBoostingClassifier is not None else "fail"


def build_search_audit(config: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "selected_state_id": str(config.get("selected_state_id", "repair_range_participation_core_30")),
                "posthoc_after_13c_report": True,
                "validation_used_in_13e": False,
                "robustness_used_in_13e": False,
                "feature_set_n": 2,
                "model_family_n": 2,
                "target_n": 1,
                "fold_n": int(config.get("fold_protocol", {}).get("fold_n", 5)),
                "effective_search_space_n": 2 * 2 * 1,
                "hyperparameter_search_used": False,
                "fold_internal_tuning_used": False,
                "early_stopping_used": False,
                "oos_used_for_selection": False,
                "confirmatory_status": False,
                "search_accounting_status": "diagnostic_train_only_not_confirmatory",
            }
        ]
    )


def build_decision(
    input_status: str,
    upstream_status: str,
    label_status: str,
    row_status: str,
    model_status: str,
    purged_status: str,
    auc_status: str,
    uplift_status: str,
    utility_status: str,
    uniqueness_status: str,
    search: pd.DataFrame,
    config: dict[str, Any],
    primary_failure_reason: str = "",
) -> pd.DataFrame:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    decision_state = "13E_diagnostic_nonlinear_train_utility_signal_present"
    reason = "all_train_kfold_diagnostic_gates_pass"
    capacity = "nonlinear_train_utility_proxy_signal_present"
    if input_status != "pass":
        decision_state = "13E_blocked_input_or_lineage_failure"
        reason = primary_failure_reason or "input_or_lineage_failure"
        capacity = "nonlinear_capacity_signal_absent"
    elif upstream_status == "fail_already_authorized":
        decision_state = "13E_blocked_upstream_13c_already_authorized"
        reason = "upstream_13c_already_authorized"
        capacity = "nonlinear_capacity_signal_absent"
    elif upstream_status != "pass":
        decision_state = "13E_blocked_upstream_13c_lineage_failure"
        reason = primary_failure_reason or "upstream_13c_lineage_failure"
        capacity = "nonlinear_capacity_signal_absent"
    elif label_status != "pass":
        decision_state = "13E_blocked_label_lineage_failure"
        reason = primary_failure_reason or "label_lineage_failure"
        capacity = "nonlinear_capacity_signal_absent"
    elif row_status != "pass":
        decision_state = "13E_blocked_row_level_rebuild_failure"
        reason = primary_failure_reason or "row_level_rebuild_failure"
        capacity = "nonlinear_capacity_signal_absent"
    elif model_status != "pass":
        decision_state = "13E_blocked_nonlinear_model_unavailable"
        reason = "nonlinear_model_unavailable"
        capacity = "nonlinear_capacity_signal_absent"
    elif uniqueness_status == "exact_uniqueness_unavailable":
        decision_state = "13E_stop_uniqueness_unavailable_for_downstream"
        reason = "exact_t1_unavailable_for_fold_local_uniqueness"
        capacity = "nonlinear_capacity_signal_absent"
    elif purged_status != "pass":
        decision_state = "13E_blocked_purged_cv_integrity_failure"
        reason = "purged_cv_integrity_failure"
        capacity = "nonlinear_capacity_signal_absent"
    elif auc_status != "pass":
        decision_state = "13E_stop_no_nonlinear_auc_improvement"
        reason = "nonlinear_auc_improvement_gate_failed"
        capacity = "nonlinear_capacity_signal_absent"
    elif uplift_status != "pass":
        decision_state = "13E_stop_no_nonlinear_uplift_improvement"
        reason = "nonlinear_uplift_improvement_gate_failed"
        capacity = "nonlinear_capacity_signal_absent"
    elif utility_status != "pass":
        decision_state = "13E_stop_nonlinear_auc_improvement_no_utility"
        reason = "nonlinear_auc_uplift_improvement_without_utility_translation"
        capacity = "nonlinear_auc_only_signal"

    search_status = (
        str(search.iloc[0]["search_accounting_status"])
        if len(search)
        else "diagnostic_train_only_not_confirmatory"
    )
    positive = decision_state == "13E_diagnostic_nonlinear_train_utility_signal_present"
    return pd.DataFrame(
        [
            {
                "decision_state": decision_state,
                "next_allowed_requirement": "none",
                "sequence_mining_authorized": False,
                "meta_labeling_authorized": False,
                "bet_sizing_authorized": False,
                "selected_state_id": selected,
                "effect_interpretation": "train_kfold_nonlinear_diagnostic_only"
                if positive
                else "none",
                "confirmatory_status": False,
                "input_gate_status": input_status,
                "upstream_lineage_gate_status": upstream_status,
                "row_level_rebuild_gate_status": row_status,
                "nonlinear_model_availability_gate_status": model_status,
                "purged_cv_integrity_gate_status": purged_status,
                "nonlinear_auc_improvement_gate_status": auc_status,
                "nonlinear_uplift_improvement_gate_status": uplift_status,
                "nonlinear_utility_proxy_gate_status": utility_status,
                "sample_uniqueness_gate_status": uniqueness_status,
                "validation_used_in_13e": False,
                "robustness_used_in_13e": False,
                "search_accounting_status": search_status,
                "primary_failure_reason": reason,
                "train_kfold_capacity_readout": capacity,
            }
        ]
    )


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int = 20) -> str:
    if df.empty:
        return "_无记录_"
    existing = [c for c in cols if c in df.columns]
    return df[existing].head(max_rows).to_markdown(index=False)


def render_report(
    decision: pd.DataFrame,
    comparison: pd.DataFrame,
    fold_metrics: pd.DataFrame,
    uniqueness: pd.DataFrame,
    search: pd.DataFrame,
) -> str:
    dec = decision.iloc[0]
    state = str(dec["selected_state_id"])
    aug = comparison.loc[comparison["feature_set"].eq("augmented_feature_set")]
    aux = comparison.loc[comparison["feature_set"].eq("baseline_feature_set")]
    positive = dec["decision_state"] == "13E_diagnostic_nonlinear_train_utility_signal_present"
    verdict = "存在 train k-fold nonlinear utility proxy signal" if positive else "不存在可升级为推进依据的 nonlinear train-kfold signal"
    lines = [
        "# 13E Nonlinear Winner Train-KFold Feasibility Diagnostic Report",
        "",
        "## 裁决",
        "",
        f"单行裁决：selected state `{state}` 的非线性 train k-fold 读数 `{verdict}`；`decision_state = {dec['decision_state']}`。",
        "",
        f"- `train_kfold_capacity_readout`: `{dec['train_kfold_capacity_readout']}`",
        f"- `primary_failure_reason`: `{dec['primary_failure_reason']}`",
        f"- `next_allowed_requirement`: `{dec['next_allowed_requirement']}`",
        f"- `meta_labeling_authorized`: `{boolish(dec['meta_labeling_authorized'])}`",
        f"- `bet_sizing_authorized`: `{boolish(dec['bet_sizing_authorized'])}`",
        "",
        "13E 不推翻 13C。13C 否决的是 selected-state residual utility hard gate；13E 只检查把线性模型换成低容量 `sklearn_hgb` 后，在 train-only purged k-fold 内是否改善 AUC、winner uplift 与 after-cost utility proxy。validation / robustness 在 13E 中从未被读取，本结论不是 OOS 验证。",
        "",
        "## Train-Only 与 Multiplicity",
        "",
        md_table(
            search,
            [
                "selected_state_id",
                "validation_used_in_13e",
                "robustness_used_in_13e",
                "feature_set_n",
                "model_family_n",
                "fold_n",
                "hyperparameter_search_used",
                "fold_internal_tuning_used",
                "early_stopping_used",
                "search_accounting_status",
            ],
        ),
        "",
        "## Purged K-Fold / Sample Uniqueness",
        "",
        "Fold 按 train 内 reference_date chronological contiguous block 构造；同 instrument event-span overlap 从 train fold purge；test fold 全局 calendar-session 边界两侧各 20 sessions embargo。训练 sample weight 在每个 purged / embargoed train_k 内用 exact event-span average uniqueness 重算，test uniqueness 只做 audit。",
        "",
        md_table(
            uniqueness,
            [
                "fold_id",
                "event_n",
                "t1_reconstruction_status",
                "purged_rows_n",
                "embargoed_rows_n",
                "effective_train_event_n",
                "effective_test_event_n",
                "train_mean_average_uniqueness",
                "test_mean_average_uniqueness",
                "sample_uniqueness_gate_status",
            ],
            10,
        ),
        "",
        "## Logistic vs sklearn_hgb 主对照",
        "",
        "主对照固定为 augmented_feature_set。`utility_proxy` 是 test fold 内 top-N 排序的乐观上界；decision 只使用相对 delta、fold direction 与 fold-mean minus one fold-std，不把 absolute utility proxy 当作可部署 utility。",
        "",
        md_table(
            aug,
            [
                "metric_id",
                "logistic_fold_mean",
                "logistic_fold_std",
                "sklearn_hgb_fold_mean",
                "sklearn_hgb_fold_std",
                "nonlinear_minus_linear_delta",
                "delta_fold_std",
                "comparison_status",
            ],
            10,
        ),
        "",
        "## Baseline vs Augmented 辅对照",
        "",
        md_table(
            aux,
            [
                "metric_id",
                "logistic_fold_mean",
                "sklearn_hgb_fold_mean",
                "nonlinear_minus_linear_delta",
                "comparison_status",
            ],
            10,
        ),
        "",
        "## Fold-Level Readout",
        "",
        md_table(
            fold_metrics.loc[fold_metrics["feature_set"].eq("augmented_feature_set")],
            [
                "fold_id",
                "model_family",
                "train_event_n",
                "test_event_n",
                "auc",
                "winner_uplift_topN",
                "utility_proxy_0bps",
                "utility_proxy_50bps",
                "utility_proxy_100bps",
            ],
            20,
        ),
        "",
        "## Interpretation Boundary",
        "",
        "若本轮 negative，失败类型必须按 no nonlinear AUC improvement、no winner uplift improvement、AUC/uplift without after-cost utility translation、purged CV integrity failure、或 uniqueness/event-span 不可审计区分。若本轮 diagnostic positive，它仍不授权 regime-aware meta-labeling feasibility、不授权 13B、不授权 bet sizing、不产生任何 next requirement，只能作为人工讨论线索。",
    ]
    return "\n".join(lines)


def publishable_manifest_outputs(outputs: dict[str, Path]) -> dict[str, Path]:
    return {key: path for key, path in outputs.items() if key != "manifest"}


def schema_hash(path: Path) -> str:
    return r13a3.schema_hash(path)


def build_manifest(
    config_path: Path,
    config: dict[str, Any],
    outputs: dict[str, Path],
    input_audit: pd.DataFrame,
) -> dict[str, Any]:
    publishable = publishable_manifest_outputs(outputs)
    return {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": r13a.git_revision(REPO_ROOT),
        "python": sys.version,
        "platform": platform.platform(),
        "config_path": str(config_path),
        "config_sha256": file_sha(config_path),
        "config_hash": stable_hash(config),
        "input_artifacts": input_audit.to_dict(orient="records"),
        "output_hashes": {key: file_sha(path) for key, path in publishable.items()},
        "publishable_outputs": {key: str(path) for key, path in publishable.items()},
        "local_cache_outputs_excluded": [],
        "local_cache_audit": [],
    }


def empty_metric_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fold_metrics = pd.DataFrame()
    comparison = build_nonlinear_vs_linear_comparison(fold_metrics)
    uniqueness = pd.DataFrame(
        columns=[
            "state_id",
            "fold_id",
            "event_n",
            "t1_reconstruction_status",
            "purged_rows_n",
            "embargoed_rows_n",
            "effective_train_event_n",
            "effective_test_event_n",
            "train_mean_average_uniqueness",
            "train_median_average_uniqueness",
            "train_p10_average_uniqueness",
            "train_mean_concurrency",
            "train_p95_concurrency",
            "test_mean_average_uniqueness",
            "test_mean_concurrency",
            "sample_uniqueness_gate_status",
        ]
    )
    return fold_metrics, comparison, uniqueness


def run(config_path: Path, mode: str = "full", check_inputs_only: bool = False) -> dict[str, Path]:
    config = r13a.load_yaml(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit = build_input_audit(resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_status, input_reason = input_gate_status(input_audit)
    upstream, upstream_status, upstream_reason = build_upstream_lineage_audit(resolved, config)
    write_df(outputs["upstream_13c_lineage_audit"], upstream)
    search = build_search_audit(config)
    write_df(outputs["search_multiplicity_audit"], search)
    if check_inputs_only or mode == "check-inputs":
        fold_metrics, comparison, uniqueness = empty_metric_frames()
        decision = build_decision(
            input_status,
            upstream_status,
            "pass",
            "pass",
            nonlinear_model_availability_gate_status(),
            "pass",
            "fail",
            "fail",
            "fail",
            "pass_with_exact_t1",
            search,
            config,
            input_reason or upstream_reason,
        )
        write_df(outputs["train_kfold_fold_metrics"], fold_metrics)
        write_df(outputs["nonlinear_vs_linear_comparison"], comparison)
        write_df(outputs["train_kfold_uniqueness_audit"], uniqueness)
        write_df(outputs["nonlinear_winner_train_kfold_feasibility_decision"], decision)
        write_text(outputs["report"], render_report(decision, comparison, fold_metrics, uniqueness, search))
        write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit))
        return outputs

    fold_metrics, comparison, uniqueness = empty_metric_frames()
    row_status = "fail"
    row_reason = ""
    label_status = "fail"
    label_reason = ""
    if input_status == "pass" and upstream_status == "pass":
        raw_train = load_train_rows_only(resolved["upstream_13c_morphology_residual_panel_cache"])
        train_events = prepare_train_event_panel(raw_train, config)
        row_audit, row_status, row_reason = build_row_level_rebuild_audit(train_events, config)
        label_status, label_reason = label_lineage_status(train_events, config)
        write_df(outputs["row_level_rebuild_audit"], row_audit)
        if row_status == "pass" and label_status == "pass" and nonlinear_model_availability_gate_status() == "pass":
            fold_metrics, uniqueness = build_train_kfold_outputs(train_events, config)
            comparison = build_nonlinear_vs_linear_comparison(fold_metrics)
    else:
        row_audit = pd.DataFrame(
            [
                {
                    "audit_id": "13e_train_selected_event_panel",
                    "status": "not_run_due_to_input_or_upstream_failure",
                }
            ]
        )
        write_df(outputs["row_level_rebuild_audit"], row_audit)

    model_status = nonlinear_model_availability_gate_status()
    sample_status = sample_uniqueness_gate_status(uniqueness)
    purged_status = purged_cv_integrity_gate_status(uniqueness)
    auc_status = nonlinear_auc_gate_status(comparison, fold_metrics, config)
    uplift_status = nonlinear_uplift_gate_status(comparison, fold_metrics)
    utility_status = nonlinear_utility_gate_status(comparison, auc_status, uplift_status)
    reason = input_reason or upstream_reason or label_reason or row_reason
    decision = build_decision(
        input_status,
        upstream_status,
        label_status,
        row_status,
        model_status,
        purged_status,
        auc_status,
        uplift_status,
        utility_status,
        sample_status,
        search,
        config,
        reason,
    )

    write_df(outputs["train_kfold_fold_metrics"], fold_metrics)
    write_df(outputs["nonlinear_vs_linear_comparison"], comparison)
    write_df(outputs["train_kfold_uniqueness_audit"], uniqueness)
    write_df(outputs["nonlinear_winner_train_kfold_feasibility_decision"], decision)
    write_text(outputs["report"], render_report(decision, comparison, fold_metrics, uniqueness, search))
    write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit))
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(Path(args.config), mode=args.mode, check_inputs_only=args.check_inputs_only)


if __name__ == "__main__":
    main()
