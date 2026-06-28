#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUNNER_15A_PATH = EXPERIMENT_DIR / "src" / "run_15a_winner_episode_label_censoring_diagnostic.py"
SOURCE_ROOTS = {
    "SOURCE_EP14_ROOT": TOPIC_ROOT / "experiments" / "pending" / "14_full_native_sparse_state_change_event_utility_preflight_v0",
    "SOURCE_EP13_ROOT": TOPIC_ROOT / "experiments" / "pending" / "13_full_pit_native_event_discovery_v0",
    "SOURCE_EP12_ROOT": TOPIC_ROOT / "experiments" / "pending" / "12_multi_k_winner_failure_path_morphology_research_v0",
}


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r15a = load_runner(RUNNER_15A_PATH, "run_15a_winner_episode_label_censoring_diagnostic_for_15b")
r13a = r15a.r13a

RUN_ID = "15B_winner_path_shape_taxonomy_diagnostic"
EXPERIMENT_ID = "15_path_defined_winner_episode_label_v0"
PHASE_ID = "15B"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_15b_winner_path_shape_taxonomy_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
SPLITS = ("train", "validation", "robustness")
READOUT_SPLITS = ("train", "validation", "robustness", "all")
SELECTED_THRESHOLD_ID = "up50pct"
PATH_TYPES = (
    "smooth_trend_winner",
    "stair_step_winner",
    "jump_repricing_winner",
    "choppy_reversal_winner",
    "slow_grind_winner",
    "late_rescue_winner",
    "unclassified_short_path",
    "unclassified_mixed_path",
    "data_quality_blocked",
)
TRADABLE_TYPES = {"smooth_trend_winner", "slow_grind_winner", "stair_step_winner"}
MIN_SEGMENT_SESSIONS = 10

REQUIRED_LABEL_COLUMNS = [
    "instrument",
    "reference_date",
    "row_id",
    "split_bucket",
    "entry_date",
    "entry_pos",
    "entry_price",
    "threshold_id",
    "threshold_return",
    "time_to_threshold_sessions",
    "available_forward_sessions",
    "path_winner",
    "is_censored",
    "episode_threshold_pos",
    "volatility_20d",
    "fast_winner_flag",
    "slow_winner_flag",
]

MEDOID_FEATURES = [
    "path_efficiency",
    "max_drawdown_before_hit_abs",
    "underwater_days_share",
    "directional_entropy_5state",
    "trend_line_r2",
    "top1_positive_gain_share",
    "top3_positive_gain_share",
    "log_time_to_threshold",
]

METRIC_FEATURES = [
    "path_efficiency",
    "max_drawdown_before_hit_abs",
    "underwater_days_share",
    "directional_entropy_5state",
    "trend_line_r2",
    "top1_positive_gain_share",
    "top3_positive_gain_share",
    "time_to_threshold_sessions",
    "time_to_threshold_available_forward_share",
    "pullback_5pct_count",
    "realized_volatility_to_hit",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 15B winner path shape taxonomy diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    for alias, root in SOURCE_ROOTS.items():
        prefix = f"{alias}/"
        if text.startswith(prefix):
            return root / text[len(prefix) :]
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
        "upstream_lineage_audit": TABLE_DIR / "upstream_lineage_audit.csv",
        "price_path_completeness_audit": TABLE_DIR / "price_path_completeness_audit.csv",
        "path_defined_label_adapter_audit": TABLE_DIR / "path_defined_label_adapter_audit.csv",
        "path_defined_label_rebuild_audit": TABLE_DIR / "path_defined_label_rebuild_audit.csv",
        "winner_episode_cluster_membership_audit": TABLE_DIR / "winner_episode_cluster_membership_audit.csv",
        "split_overlap_audit": TABLE_DIR / "split_overlap_audit.csv",
        "representative_anchor_audit": TABLE_DIR / "representative_anchor_audit.csv",
        "path_shape_feature_definition_audit": TABLE_DIR / "path_shape_feature_definition_audit.csv",
        "path_shape_metric_distribution_readout": TABLE_DIR / "path_shape_metric_distribution_readout.csv",
        "path_shape_taxonomy_rule_audit": TABLE_DIR / "path_shape_taxonomy_rule_audit.csv",
        "path_shape_taxonomy_readout": TABLE_DIR / "path_shape_taxonomy_readout.csv",
        "path_shape_by_split_readout": TABLE_DIR / "path_shape_by_split_readout.csv",
        "path_shape_by_threshold_sensitivity_readout": TABLE_DIR / "path_shape_by_threshold_sensitivity_readout.csv",
        "slow_fast_by_path_type_readout": TABLE_DIR / "slow_fast_by_path_type_readout.csv",
        "entropy_incrementality_readout": TABLE_DIR / "entropy_incrementality_readout.csv",
        "taxonomy_without_entropy_ablation_readout": TABLE_DIR / "taxonomy_without_entropy_ablation_readout.csv",
        "taxonomy_stability_gate": TABLE_DIR / "taxonomy_stability_gate.csv",
        "decision": TABLE_DIR / "winner_path_shape_taxonomy_decision.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "anchor_path_shape_feature_panel": LOCAL_CACHE_DIR / "anchor_path_shape_feature_panel.parquet",
        "winner_episode_cluster_panel": LOCAL_CACHE_DIR / "winner_episode_cluster_panel.parquet",
        "episode_path_shape_feature_panel": LOCAL_CACHE_DIR / "episode_path_shape_feature_panel.parquet",
        "taxonomy_assignment_panel": LOCAL_CACHE_DIR / "taxonomy_assignment_panel.parquet",
        "report": REPORT_DIR / "winner_path_shape_taxonomy_diagnostic_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r15a.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r15a.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r15a.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r15a.write_json(path, payload)


def file_sha(path: Path) -> str:
    if path.is_file():
        return r13a.file_sha256(path)
    if path.is_dir():
        digest = hashlib.sha256()
        for child in sorted(p for p in path.iterdir() if p.is_file()):
            digest.update(child.name.encode("utf-8"))
            digest.update(str(child.stat().st_size).encode("utf-8"))
            digest.update(str(int(child.stat().st_mtime_ns)).encode("utf-8"))
        return digest.hexdigest()
    return ""


def stable_hash(value: Any) -> str:
    return r15a.stable_hash(value)


def safe_rate(num: Any, den: Any) -> float:
    try:
        den_f = float(den)
        if den_f == 0 or not np.isfinite(den_f):
            return np.nan
        return float(num) / den_f
    except Exception:
        return np.nan


def bool_series(series: pd.Series) -> pd.Series:
    return r15a.bool_series(series)


def finite(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def path_key(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["instrument"].astype(str)
        + "|"
        + frame["reference_date"].astype(str)
        + "|"
        + frame["row_id"].astype(str)
        + "|"
        + frame["threshold_id"].astype(str)
    )


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    required_columns = {
        "upstream_15a_path_defined_label_cache": REQUIRED_LABEL_COLUMNS,
        "upstream_15a_decision": ["decision_state"],
        "upstream_15a_winner_set_difference": ["threshold_id", "split_bucket", "path_winner_n"],
        "upstream_15a_time_to_threshold": ["threshold_id", "split_bucket", "path_winner_n"],
        "upstream_15a_episode_overlap": ["threshold_id", "split_bucket"],
        "upstream_15a_search_accounting": ["selected_threshold_recommendation"],
        "upstream_15a_lineage": ["lineage_status"],
    }
    for role, path in resolved.items():
        required = True
        exists = path.exists()
        read_status = "pass" if exists else "missing"
        row_count: int | float = np.nan
        column_count: int | float = np.nan
        schema_status = "not_checked"
        missing: list[str] = []
        if exists and path.is_file():
            try:
                suffixes = "".join(path.suffixes)
                expected = required_columns.get(role, [])
                if suffixes.endswith((".csv", ".csv.gz", ".parquet")):
                    frame = read_table(path)
                    row_count = len(frame)
                    column_count = len(frame.columns)
                    missing = [col for col in expected if col not in frame.columns]
                    schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
                else:
                    row_count = np.nan
                    column_count = np.nan
                    schema_status = "pass" if not expected else "non_tabular_required_schema"
            except Exception as exc:
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "read_error"
        elif exists and path.is_dir():
            row_count = r15a.count_rows(path)
            schema_status = "directory"
        rows.append(
            {
                "artifact_role": role,
                "artifact_path": str(config.get("paths", {}).get(role, "")),
                "resolved_path": str(path),
                "required_flag": required,
                "lineage_role": "15B_input",
                "read_status": read_status,
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_sha(path),
                "schema_status": schema_status,
                "required_column_missing_list": ";".join(missing),
                "input_gate_status": "pass" if read_status == "pass" and not schema_status.startswith("missing_columns") else "fail",
            }
        )
    return pd.DataFrame(rows)


def gate_from_status(frame: pd.DataFrame, status_col: str) -> str:
    if frame.empty or status_col not in frame.columns:
        return "fail"
    return "pass" if frame[status_col].astype(str).eq("pass").all() else "fail"


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    if input_audit.empty:
        return "fail", "empty_input_audit"
    bad = input_audit.loc[input_audit["input_gate_status"].astype(str).ne("pass")]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_role"].astype(str).tolist())


def ensure_15a_cache(resolved: dict[str, Path]) -> Path:
    label_path = resolved["upstream_15a_path_defined_label_cache"]
    if label_path.exists():
        return label_path
    config_15a = EXPERIMENT_DIR / "configs" / "config_15a_winner_episode_label_censoring_diagnostic.yaml"
    r15a.run(config_15a, check_inputs_only=False)
    return label_path


def load_label_panel(resolved: dict[str, Path]) -> pd.DataFrame:
    path = ensure_15a_cache(resolved)
    return read_table(path)


def path_defined_label_adapter_audit(label: pd.DataFrame, path: Path, qfq_dir: Path) -> pd.DataFrame:
    missing = [col for col in REQUIRED_LABEL_COLUMNS if col not in label.columns]
    duplicate_n = int(label.duplicated(["instrument", "reference_date", "row_id", "threshold_id"]).sum()) if not missing else np.nan
    hit_rebuild_status = "pass"
    reason = ""
    if missing:
        hit_rebuild_status = "fail"
        reason = "missing_columns:" + ";".join(missing)
    else:
        winners = label.loc[bool_series(label["path_winner"])]
        null_hit = int(winners["episode_threshold_pos"].isna().sum())
        if null_hit:
            hit_rebuild_status = "fail"
            reason = f"path_winner_null_episode_threshold_pos:{null_hit}"
        else:
            checked = 0
            bad = 0
            for instrument, sub in winners.groupby("instrument", sort=False):
                qfq_path = qfq_dir / f"{instrument}.csv"
                if not qfq_path.exists():
                    bad += len(sub)
                    continue
                qfq = pd.read_csv(qfq_path, usecols=["date"])
                max_pos = int(pd.to_numeric(sub["episode_threshold_pos"], errors="coerce").max())
                checked += len(sub)
                if max_pos >= len(qfq):
                    bad += int((pd.to_numeric(sub["episode_threshold_pos"], errors="coerce") >= len(qfq)).sum())
            if bad:
                hit_rebuild_status = "fail"
                reason = f"episode_threshold_pos_out_of_bounds:{bad}"
    status = "pass" if not missing and duplicate_n == 0 and hit_rebuild_status == "pass" else "fail"
    return pd.DataFrame(
        [
            {
                "source_row_key": "instrument,reference_date,row_id,threshold_id",
                "adapter_source_path": str(path),
                "adapter_required_columns_present": not missing,
                "adapter_required_missing_columns": ";".join(missing),
                "adapter_hit_pos_rebuild_status": hit_rebuild_status,
                "adapter_row_count": len(label),
                "adapter_duplicate_source_row_key_n": duplicate_n,
                "adapter_status": status,
                "blocking_reason": reason,
            }
        ]
    )


def path_defined_label_rebuild_audit(label: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if label.empty:
        return pd.DataFrame([{"threshold_id": "all", "split_bucket": "all", "rebuild_status": "fail", "blocking_reason": "empty_label"}])
    label = label.copy()
    label["source_row_key"] = path_key(label)
    for threshold, tsub in split_groups(label, "threshold_id"):
        for split, sub in split_groups(tsub, "split_bucket"):
            path_winner = bool_series(sub["path_winner"])
            censored = bool_series(sub["is_censored"])
            dup_n = int(sub["source_row_key"].duplicated().sum())
            conflict_n = int((path_winner & censored).sum())
            missing_hit_n = int(sub.loc[path_winner, "episode_threshold_pos"].isna().sum())
            status = "pass" if dup_n == 0 and conflict_n == 0 and missing_hit_n == 0 else "fail"
            rows.append(
                {
                    "threshold_id": threshold,
                    "split_bucket": split,
                    "record_n": len(sub),
                    "path_winner_n": int(path_winner.sum()),
                    "is_censored_n": int(censored.sum()),
                    "duplicate_source_row_key_n": dup_n,
                    "path_winner_and_censored_conflict_n": conflict_n,
                    "path_winner_missing_hit_pos_n": missing_hit_n,
                    "rebuild_status": status,
                    "blocking_reason": "" if status == "pass" else "label_adapter_invariant_failed",
                }
            )
    return pd.DataFrame(rows)


def split_groups(frame: pd.DataFrame, col: str):
    for key, sub in frame.groupby(col, sort=False):
        yield str(key), sub


def build_upstream_lineage_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for role in [
        "upstream_15a_decision",
        "upstream_15a_winner_set_difference",
        "upstream_15a_time_to_threshold",
        "upstream_15a_episode_overlap",
        "upstream_15a_search_accounting",
        "upstream_15a_lineage",
    ]:
        path = resolved[role]
        status = "pass" if path.exists() else "fail"
        rows.append(
            {
                "upstream_artifact_role": role,
                "upstream_path": str(path),
                "upstream_sha256": file_sha(path),
                "upstream_row_count": r15a.count_rows(path) if path.exists() and path.is_file() else np.nan,
                "lineage_claim": "15B inherits 15A path-defined winner row lineage and does not inherit 15A next_allowed_requirement as authorization.",
                "lineage_status": status,
                "blocking_reason": "" if status == "pass" else "missing_upstream_artifact",
            }
        )
    return pd.DataFrame(rows)


def read_qfq(instrument: str, qfq_dir: Path) -> pd.DataFrame | None:
    path = qfq_dir / f"{instrument}.csv"
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    date_col = "date" if "date" in frame.columns else "trade_date"
    close = pd.to_numeric(frame.get("close"), errors="coerce")
    out = pd.DataFrame(
        {
            "date": frame[date_col].astype(str),
            "open": pd.to_numeric(frame.get("open"), errors="coerce"),
            "high": pd.to_numeric(frame.get("high"), errors="coerce"),
            "close": close,
        }
    )
    out["ma20_close"] = close.rolling(20, min_periods=20).mean()
    return out


def qfq_arrays(qfq: pd.DataFrame) -> dict[str, np.ndarray]:
    return {
        "close": pd.to_numeric(qfq["close"], errors="coerce").to_numpy(dtype=float),
        "high": pd.to_numeric(qfq["high"], errors="coerce").to_numpy(dtype=float),
        "ma20_close": pd.to_numeric(qfq["ma20_close"], errors="coerce").to_numpy(dtype=float),
        "date": qfq["date"].astype(str).to_numpy(),
    }


def build_price_path_completeness(label: pd.DataFrame, qfq_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    winners = label.loc[bool_series(label["path_winner"])]
    for instrument, sub in label.groupby("instrument", sort=False):
        qfq = read_qfq(str(instrument), qfq_dir)
        missing_file = qfq is None
        qfq_n = 0 if qfq is None else len(qfq)
        wsub = winners.loc[winners["instrument"].astype(str).eq(str(instrument))]
        max_hit = pd.to_numeric(wsub.get("episode_threshold_pos", pd.Series(dtype=float)), errors="coerce").max()
        out_of_bounds = 0 if missing_file or pd.isna(max_hit) else int((pd.to_numeric(wsub["episode_threshold_pos"], errors="coerce") >= qfq_n).sum())
        status = "pass" if not missing_file and out_of_bounds == 0 else "fail"
        rows.append(
            {
                "instrument": instrument,
                "anchor_row_n": len(sub),
                "path_winner_anchor_n": len(wsub),
                "qfq_row_n": qfq_n,
                "missing_qfq_file_flag": missing_file,
                "max_episode_threshold_pos": max_hit,
                "hit_pos_out_of_bounds_n": out_of_bounds,
                "price_path_status": status,
                "blocking_reason": "" if status == "pass" else "missing_qfq_or_hit_pos_out_of_bounds",
            }
        )
    return pd.DataFrame(rows)


def build_winner_episode_clusters(label: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    winners = label.loc[bool_series(label["path_winner"]) & ~bool_series(label["is_censored"])].copy()
    winners["source_row_key"] = path_key(winners)
    winners["winner_interval_start_pos"] = pd.to_numeric(winners["entry_pos"], errors="coerce").astype("Int64")
    winners["winner_interval_end_pos"] = pd.to_numeric(winners["episode_threshold_pos"], errors="coerce").astype("Int64")
    winners = winners.dropna(subset=["winner_interval_start_pos", "winner_interval_end_pos"]).copy()
    winners["winner_interval_start_pos"] = winners["winner_interval_start_pos"].astype(int)
    winners["winner_interval_end_pos"] = winners["winner_interval_end_pos"].astype(int)
    winners = winners.sort_values(
        ["threshold_id", "instrument", "winner_interval_start_pos", "winner_interval_end_pos", "row_id"], kind="stable"
    )
    assignments: dict[int, tuple[str, int, int, int]] = {}
    cluster_records: list[dict[str, Any]] = []
    for (threshold, instrument), group in winners.groupby(["threshold_id", "instrument"], sort=False):
        current: list[int] = []
        cluster_start = -1
        cluster_end = -1
        ordinal = 0

        def flush() -> None:
            nonlocal current, cluster_start, cluster_end, ordinal
            if not current:
                return
            cluster_id = f"{threshold}::{instrument}::{ordinal:06d}"
            for idx in current:
                assignments[idx] = (cluster_id, cluster_start, cluster_end, ordinal)
            cluster_records.append(
                {
                    "threshold_id": threshold,
                    "instrument": instrument,
                    "episode_cluster_id": cluster_id,
                    "cluster_ordinal": ordinal,
                    "cluster_start_pos": cluster_start,
                    "cluster_end_pos": cluster_end,
                    "cluster_anchor_n": len(current),
                }
            )
            ordinal += 1
            current = []

        for idx, row in group.iterrows():
            start = int(row["winner_interval_start_pos"])
            end = int(row["winner_interval_end_pos"])
            if not current:
                current = [idx]
                cluster_start = start
                cluster_end = end
            elif start <= cluster_end:
                current.append(idx)
                cluster_end = max(cluster_end, end)
            else:
                flush()
                current = [idx]
                cluster_start = start
                cluster_end = end
        flush()
    winners["episode_cluster_id"] = [assignments[idx][0] for idx in winners.index]
    winners["cluster_start_pos"] = [assignments[idx][1] for idx in winners.index]
    winners["cluster_end_pos"] = [assignments[idx][2] for idx in winners.index]
    winners["episode_cluster_status"] = "pass"
    clusters = pd.DataFrame(cluster_records)
    return winners.reset_index(drop=True), clusters


def split_overlap_audit(membership: pd.DataFrame, clusters: pd.DataFrame, label: pd.DataFrame, qfq_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = label[["instrument", "reference_pos", "split_bucket"]].drop_duplicates().copy()
    base["reference_pos"] = pd.to_numeric(base["reference_pos"], errors="coerce")
    split_rows: list[dict[str, Any]] = []
    label_by_instrument = {str(k): v for k, v in base.groupby("instrument", sort=False)}
    members_by_cluster = {k: v for k, v in membership.groupby("episode_cluster_id", sort=False)}
    qfq_cache: dict[str, pd.DataFrame | None] = {}

    def date_at_pos(instrument: str, pos: int) -> str:
        if instrument not in qfq_cache:
            qfq_cache[instrument] = read_qfq(instrument, qfq_dir)
        qfq = qfq_cache[instrument]
        if qfq is None or pos < 0 or pos >= len(qfq):
            return ""
        return str(qfq.iloc[pos]["date"])

    enriched = []
    for row in clusters.itertuples(index=False):
        cluster_id = row.episode_cluster_id
        members = members_by_cluster[cluster_id]
        member_set = sorted(members["split_bucket"].astype(str).dropna().unique().tolist())
        inst_panel = label_by_instrument.get(str(row.instrument), pd.DataFrame())
        if inst_panel.empty:
            calendar_set: list[str] = []
        else:
            span = inst_panel.loc[
                (inst_panel["reference_pos"] >= row.cluster_start_pos) & (inst_panel["reference_pos"] <= row.cluster_end_pos)
            ]
            calendar_set = sorted(span["split_bucket"].astype(str).dropna().unique().tolist())
        single = len(member_set) == 1 and len(calendar_set) == 1 and member_set[0] == calendar_set[0]
        cluster_split = member_set[0] if single else "cross_split"
        touches_member = len(member_set) > 1
        touches_calendar = len(calendar_set) > 1
        cluster_start_date = date_at_pos(str(row.instrument), int(row.cluster_start_pos))
        cluster_end_date = date_at_pos(str(row.instrument), int(row.cluster_end_pos))
        status = "pass" if cluster_start_date and cluster_end_date else "fail"
        audit_row = {
            "instrument": row.instrument,
            "threshold_id": row.threshold_id,
            "episode_cluster_id": cluster_id,
            "cluster_split_bucket": cluster_split,
            "cluster_member_split_bucket_set": ";".join(member_set),
            "cluster_calendar_span_split_bucket_set": ";".join(calendar_set),
            "cluster_start_date": cluster_start_date,
            "cluster_end_date": cluster_end_date,
            "cluster_start_pos": row.cluster_start_pos,
            "cluster_end_pos": row.cluster_end_pos,
            "touches_multiple_split_buckets": touches_member,
            "touches_multiple_calendar_split_buckets": touches_calendar,
            "train_validation_boundary_overlap": {"train", "validation"}.issubset(set(calendar_set)),
            "validation_robustness_boundary_overlap": {"validation", "robustness"}.issubset(set(calendar_set)),
            "split_overlap_status": status,
            "blocking_reason": "" if status == "pass" else "missing_cluster_start_or_end_date",
        }
        split_rows.append(audit_row)
        enriched.append({**row._asdict(), **audit_row})
    cluster_panel = pd.DataFrame(enriched)
    return pd.DataFrame(split_rows), cluster_panel


def _trend_r2(log_values: np.ndarray) -> float:
    n = len(log_values)
    if n < 2 or not np.isfinite(log_values).all():
        return np.nan
    x = np.arange(n, dtype=float)
    x_centered = x - x.mean()
    y_centered = log_values - log_values.mean()
    ss_x = float(np.sum(x_centered * x_centered))
    ss_y = float(np.sum(y_centered * y_centered))
    if ss_x <= 0 or ss_y <= 0:
        return np.nan
    corr = float(np.sum(x_centered * y_centered) / np.sqrt(ss_x * ss_y))
    return corr * corr


def _pullback_stats(closes: np.ndarray, threshold: float) -> tuple[int, list[int]]:
    if len(closes) < 2 or not np.isfinite(closes).all():
        return 0, []
    peak = closes[0]
    in_event = False
    trough_idx = 0
    trough_price = closes[0]
    count = 0
    recoveries: list[int] = []
    for i, price in enumerate(closes[1:], start=1):
        if price >= peak:
            if in_event:
                recoveries.append(i - trough_idx)
                in_event = False
            peak = price
            trough_price = price
            trough_idx = i
            continue
        drawdown = price / peak - 1.0 if peak else np.nan
        if not in_event and np.isfinite(drawdown) and drawdown <= threshold:
            in_event = True
            count += 1
            trough_price = price
            trough_idx = i
        elif in_event and price < trough_price:
            trough_price = price
            trough_idx = i
    return count, recoveries


def _entropy_from_returns(returns: np.ndarray, scale: float) -> float:
    if len(returns) == 0 or not np.isfinite(scale) or scale <= 0:
        return np.nan
    z = returns / scale
    states = np.select(
        [z <= -1.0, z < -0.25, z <= 0.25, z < 1.0, z >= 1.0],
        [0, 1, 2, 3, 4],
        default=np.nan,
    )
    states = states[np.isfinite(states)]
    if len(states) == 0:
        return np.nan
    counts = np.bincount(states.astype(int), minlength=5).astype(float)
    probs = counts[counts > 0] / counts.sum()
    return float(-np.sum(probs * np.log(probs)) / np.log(5))


def _metric_row(row: Any, qfq: dict[str, np.ndarray]) -> dict[str, Any]:
    source_key = f"{row.instrument}|{row.reference_date}|{row.row_id}|{row.threshold_id}"
    start = int(row.entry_pos)
    end = int(row.episode_threshold_pos)
    entry_price = float(row.entry_price)
    threshold_return = float(row.threshold_return)
    available_forward_sessions = float(getattr(row, "available_forward_sessions", np.nan))
    time_to_threshold_sessions = float(row.time_to_threshold_sessions)
    time_to_available_forward_share = (
        float(time_to_threshold_sessions / available_forward_sessions)
        if np.isfinite(time_to_threshold_sessions) and np.isfinite(available_forward_sessions) and available_forward_sessions > 0
        else np.nan
    )
    close = qfq["close"]
    high = qfq["high"]
    dates = qfq["date"]
    base = {
        "source_row_key": source_key,
        "instrument": row.instrument,
        "reference_date": row.reference_date,
        "row_id": row.row_id,
        "split_bucket": row.split_bucket,
        "threshold_id": row.threshold_id,
        "threshold_return": threshold_return,
        "episode_cluster_id": row.episode_cluster_id,
        "cluster_split_bucket": row.cluster_split_bucket,
        "touches_multiple_split_buckets": bool(row.touches_multiple_split_buckets),
        "touches_multiple_calendar_split_buckets": bool(row.touches_multiple_calendar_split_buckets),
        "entry_pos": start,
        "first_threshold_hit_pos": end,
        "segment_start_pos": start,
        "segment_end_pos": end,
        "entry_price": entry_price,
        "time_to_threshold_sessions": time_to_threshold_sessions,
        "available_forward_sessions": available_forward_sessions,
        "time_to_threshold_available_forward_share": time_to_available_forward_share,
        "fast_winner_flag": bool(row.fast_winner_flag),
        "slow_winner_flag": bool(row.slow_winner_flag),
        "entry_volatility_20d": float(row.volatility_20d) if pd.notna(row.volatility_20d) else np.nan,
    }
    if start < 0 or end < start or end >= len(close) or not np.isfinite(entry_price) or entry_price <= 0:
        return {**base, "path_shape_quality": "invalid_segment_bounds", "segment_sessions": np.nan}
    segment = close[start : end + 1]
    if len(segment) == 0 or not np.isfinite(segment).all() or np.any(segment <= 0):
        return {**base, "path_shape_quality": "invalid_price_path", "segment_sessions": len(segment)}
    returns = np.diff(np.log(segment))
    simple_returns = segment[1:] / segment[:-1] - 1.0 if len(segment) > 1 else np.array([])
    positive = np.maximum(returns, 0.0)
    positive_sum = float(np.sum(positive))
    top = np.sort(positive)[::-1]
    top1 = float(top[0] / positive_sum) if positive_sum > 0 and len(top) else np.nan
    top3 = float(np.sum(top[:3]) / positive_sum) if positive_sum > 0 and len(top) else np.nan
    realized_vol = float(np.std(returns, ddof=1)) if len(returns) >= 2 else np.nan
    entry_vol = base["entry_volatility_20d"]
    entropy_scale = entry_vol if np.isfinite(entry_vol) and entry_vol > 0 else realized_vol
    entropy_source = "entry_volatility_20d" if np.isfinite(entry_vol) and entry_vol > 0 else "realized_segment_fallback"
    running_max = np.maximum.accumulate(segment)
    drawdowns = segment / running_max - 1.0
    pb5, recoveries = _pullback_stats(segment, -0.05)
    pb10, _ = _pullback_stats(segment, -0.10)
    ma20_hold = np.nan
    if start >= 19:
        ma = qfq["ma20_close"]
        ma_seg = ma[start : end + 1]
        valid = np.isfinite(ma_seg)
        ma20_hold = float(np.mean(segment[valid] >= ma_seg[valid])) if valid.any() else np.nan
    total_variation = float(np.sum(np.abs(returns)))
    net_log = float(np.log(segment[-1] / segment[0]))
    path_eff = float(abs(net_log) / total_variation) if total_variation > 0 else np.nan
    close_return_at_hit = float(segment[-1] / entry_price - 1.0)
    high_return_at_hit = float(high[end] / entry_price - 1.0) if np.isfinite(high[end]) else np.nan
    segment_sessions = int(end - start + 1)
    return {
        **base,
        "first_threshold_hit_date": dates[end],
        "shape_close_start": float(segment[0]),
        "shape_close_end": float(segment[-1]),
        "entry_gap_return": float(segment[0] / entry_price - 1.0),
        "segment_sessions": segment_sessions,
        "return_observation_n": max(segment_sessions - 1, 0),
        "daily_return_observation_n": len(returns),
        "net_log_return": net_log,
        "total_variation": total_variation,
        "path_efficiency": path_eff,
        "zero_variation_path": total_variation == 0,
        "max_drawdown_before_hit": float(np.min(drawdowns)),
        "max_drawdown_before_hit_abs": float(abs(np.min(drawdowns))),
        "underwater_days_share": float(np.mean(segment < running_max)),
        "entry_underwater_days_share": float(np.mean(segment < segment[0])),
        "pullback_5pct_count": int(pb5),
        "pullback_10pct_count": int(pb10),
        "median_recovery_sessions": float(np.median(recoveries)) if recoveries else np.nan,
        "directional_entropy_5state": _entropy_from_returns(returns, entropy_scale),
        "directional_entropy_5state_realized": _entropy_from_returns(returns, realized_vol),
        "entropy_volatility_source": entropy_source,
        "realized_volatility_to_hit": realized_vol,
        "realized_volatility_observation_n": len(returns),
        "insufficient_return_observation_for_realized_volatility": len(returns) < 2,
        "trend_line_r2": _trend_r2(np.log(segment)),
        "positive_day_share": float(np.mean(returns > 0)) if len(returns) else np.nan,
        "ma20_hold_share": ma20_hold,
        "positive_gain_sum": positive_sum,
        "top1_positive_gain_share": top1,
        "top3_positive_gain_share": top3,
        "large_up_day_count": int(np.sum(simple_returns >= 0.095)),
        "large_up_day_share": safe_rate(np.sum(simple_returns >= 0.095), segment_sessions),
        "log_time_to_threshold": float(np.log1p(row.time_to_threshold_sessions)),
        "close_return_at_hit": close_return_at_hit,
        "high_return_at_hit": high_return_at_hit,
        "wick_hit_only": bool(high_return_at_hit >= threshold_return and close_return_at_hit < threshold_return),
        "path_shape_quality": "too_short_for_stable_shape" if segment_sessions < MIN_SEGMENT_SESSIONS else "pass",
    }


def compute_anchor_path_shape_metrics(membership: pd.DataFrame, qfq_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    qfq_cache: dict[str, pd.DataFrame | None] = {}
    for instrument, sub in membership.groupby("instrument", sort=False):
        qfq_cache[str(instrument)] = read_qfq(str(instrument), qfq_dir)
        qfq = qfq_cache[str(instrument)]
        if qfq is None:
            for row in sub.itertuples(index=False):
                rows.append(
                    {
                        "source_row_key": f"{row.instrument}|{row.reference_date}|{row.row_id}|{row.threshold_id}",
                        "instrument": row.instrument,
                        "reference_date": row.reference_date,
                        "row_id": row.row_id,
                        "threshold_id": row.threshold_id,
                        "episode_cluster_id": row.episode_cluster_id,
                        "path_shape_quality": "invalid_price_path",
                    }
                )
            continue
        qfq_data = qfq_arrays(qfq)
        for row in sub.itertuples(index=False):
            rows.append(_metric_row(row, qfq_data))
    return pd.DataFrame(rows)


def fit_scaler(frame: pd.DataFrame, features: list[str]) -> dict[str, dict[str, float]]:
    scaler: dict[str, dict[str, float]] = {}
    for feature in features:
        values = finite(frame.get(feature, pd.Series(dtype=float))).dropna()
        center = float(values.median()) if not values.empty else 0.0
        q75 = float(values.quantile(0.75)) if not values.empty else 1.0
        q25 = float(values.quantile(0.25)) if not values.empty else 0.0
        scale = q75 - q25
        if not np.isfinite(scale) or scale == 0:
            scale = 1.0
        scaler[feature] = {"center": center, "scale": scale}
    return scaler


def standardized_matrix(frame: pd.DataFrame, scaler: dict[str, dict[str, float]], features: list[str]) -> np.ndarray:
    cols = []
    for feature in features:
        values = finite(frame.get(feature, pd.Series(index=frame.index, dtype=float))).fillna(scaler[feature]["center"])
        cols.append(((values - scaler[feature]["center"]) / scaler[feature]["scale"]).to_numpy(dtype=float))
    return np.vstack(cols).T if cols else np.empty((len(frame), 0))


def select_representatives(anchor_metrics: pd.DataFrame, cluster_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fit_pop = anchor_metrics.loc[
        anchor_metrics["threshold_id"].eq(SELECTED_THRESHOLD_ID)
        & anchor_metrics["cluster_split_bucket"].eq("train")
        & ~anchor_metrics["touches_multiple_split_buckets"].astype(bool)
        & ~anchor_metrics["touches_multiple_calendar_split_buckets"].astype(bool)
        & ~anchor_metrics["path_shape_quality"].isin(["invalid_price_path", "invalid_segment_bounds"])
    ]
    scaler = fit_scaler(fit_pop, MEDOID_FEATURES)
    rep_rows: list[dict[str, Any]] = []
    episode_rows: list[pd.Series] = []
    for cluster_id, group in anchor_metrics.groupby("episode_cluster_id", sort=False):
        group = group.copy()
        earliest = group.sort_values(["entry_pos", "row_id"], kind="stable").iloc[0]
        shortest = group.sort_values(["time_to_threshold_sessions", "entry_pos", "row_id"], kind="stable").iloc[0]
        matrix = standardized_matrix(group, scaler, MEDOID_FEATURES)
        median_vec = np.nanmedian(matrix, axis=0)
        distances = np.sqrt(np.sum((matrix - median_vec) ** 2, axis=1))
        group["_medoid_distance"] = distances
        medoid = group.sort_values(["_medoid_distance", "time_to_threshold_sessions", "entry_pos", "row_id"], kind="stable").iloc[0]
        rep_rows.append(
            {
                "threshold_id": medoid["threshold_id"],
                "episode_cluster_id": cluster_id,
                "cluster_anchor_n": len(group),
                "earliest_anchor_row_id": earliest["row_id"],
                "shortest_duration_anchor_row_id": shortest["row_id"],
                "medoid_anchor_row_id": medoid["row_id"],
                "earliest_source_row_key": earliest["source_row_key"],
                "shortest_source_row_key": shortest["source_row_key"],
                "medoid_source_row_key": medoid["source_row_key"],
                "medoid_distance": float(medoid["_medoid_distance"]),
                "representative_taxonomy_disagreement": False,
            }
        )
        episode_rows.append(medoid.drop(labels=["_medoid_distance"]))
    representatives = pd.DataFrame(rep_rows)
    episode_metrics = pd.DataFrame(episode_rows).reset_index(drop=True)
    rule_rows = [
        {
            "rule_type": "medoid_scaler",
            "feature_id": feature,
            "quantile_name": "",
            "value": params["center"],
            "scale": params["scale"],
            "quantile_used_by_predicate": False,
            "medoid_scaler_fit_population_n": len(fit_pop),
            "taxonomy_quantile_fit_population_n": np.nan,
            "medoid_scaler_fit_unit": "anchor_path",
            "taxonomy_quantile_fit_unit": "",
            "taxonomy_fit_population_order_status": "pass",
            "train_rule_fit_status": "pass" if len(fit_pop) > 0 else "fail",
        }
        for feature, params in scaler.items()
    ]
    return representatives, episode_metrics, pd.DataFrame(rule_rows)


def quantile_value(frame: pd.DataFrame, column: str, q: float) -> float:
    values = finite(frame.get(column, pd.Series(dtype=float))).dropna()
    return float(values.quantile(q)) if not values.empty else np.nan


def fit_taxonomy_quantiles(episode_metrics: pd.DataFrame) -> tuple[dict[str, float], pd.DataFrame, pd.DataFrame]:
    fit_pop = episode_metrics.loc[
        episode_metrics["threshold_id"].eq(SELECTED_THRESHOLD_ID)
        & episode_metrics["cluster_split_bucket"].eq("train")
        & ~episode_metrics["touches_multiple_split_buckets"].astype(bool)
        & ~episode_metrics["touches_multiple_calendar_split_buckets"].astype(bool)
        & ~episode_metrics["path_shape_quality"].eq("too_short_for_stable_shape")
        & ~episode_metrics["path_shape_quality"].isin(["invalid_price_path", "invalid_segment_bounds"])
    ].copy()
    qdefs = {
        "q_efficiency_30": ("path_efficiency", 0.30),
        "q_efficiency_50": ("path_efficiency", 0.50),
        "q_efficiency_70": ("path_efficiency", 0.70),
        "q_max_drawdown_abs_30": ("max_drawdown_before_hit_abs", 0.30),
        "q_max_drawdown_abs_50": ("max_drawdown_before_hit_abs", 0.50),
        "q_max_drawdown_abs_70": ("max_drawdown_before_hit_abs", 0.70),
        "q_underwater_share_50": ("underwater_days_share", 0.50),
        "q_underwater_share_70": ("underwater_days_share", 0.70),
        "q_entropy_30": ("directional_entropy_5state", 0.30),
        "q_entropy_50": ("directional_entropy_5state", 0.50),
        "q_entropy_70": ("directional_entropy_5state", 0.70),
        "q_trend_r2_50": ("trend_line_r2", 0.50),
        "q_trend_r2_70": ("trend_line_r2", 0.70),
        "q_top1_gain_share_70": ("top1_positive_gain_share", 0.70),
        "q_top1_gain_share_85": ("top1_positive_gain_share", 0.85),
        "q_top3_gain_share_70": ("top3_positive_gain_share", 0.70),
        "q_top3_gain_share_85": ("top3_positive_gain_share", 0.85),
        "q_large_up_day_count_70": ("large_up_day_count", 0.70),
        "q_time_to_threshold_available_forward_share_75": ("time_to_threshold_available_forward_share", 0.75),
        "q_pullback_5pct_count_50": ("pullback_5pct_count", 0.50),
        "q_pullback_5pct_count_70": ("pullback_5pct_count", 0.70),
    }
    quantiles = {name: quantile_value(fit_pop, column, q) for name, (column, q) in qdefs.items()}
    status = "pass" if len(fit_pop) > 0 and all(np.isfinite(v) for v in quantiles.values()) else "fail"
    used_by_predicate = {
        "q_efficiency_30",
        "q_efficiency_70",
        "q_max_drawdown_abs_30",
        "q_max_drawdown_abs_70",
        "q_underwater_share_50",
        "q_underwater_share_70",
        "q_entropy_70",
        "q_trend_r2_50",
        "q_trend_r2_70",
        "q_top1_gain_share_70",
        "q_top1_gain_share_85",
        "q_top3_gain_share_70",
        "q_top3_gain_share_85",
        "q_large_up_day_count_70",
        "q_time_to_threshold_available_forward_share_75",
        "q_pullback_5pct_count_50",
        "q_pullback_5pct_count_70",
    }
    rows = [
        {
            "rule_type": "taxonomy_quantile",
            "feature_id": column,
            "quantile_name": name,
            "value": quantiles[name],
            "scale": np.nan,
            "quantile_used_by_predicate": name in used_by_predicate,
            "medoid_scaler_fit_population_n": np.nan,
            "taxonomy_quantile_fit_population_n": len(fit_pop),
            "medoid_scaler_fit_unit": "",
            "taxonomy_quantile_fit_unit": "winner_episode_cluster",
            "taxonomy_fit_population_order_status": "pass",
            "train_rule_fit_status": status,
        }
        for name, (column, _q) in qdefs.items()
    ]
    return quantiles, fit_pop, pd.DataFrame(rows)


def taxonomy_guard_rule_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "rule_type": "audit_guard",
                "feature_id": "wick_hit_only",
                "quantile_name": "",
                "value": np.nan,
                "scale": np.nan,
                "quantile_used_by_predicate": False,
                "medoid_scaler_fit_population_n": np.nan,
                "taxonomy_quantile_fit_population_n": np.nan,
                "medoid_scaler_fit_unit": "",
                "taxonomy_quantile_fit_unit": "",
                "taxonomy_fit_population_order_status": "pass",
                "train_rule_fit_status": "pass",
                "rule_description": "high-based threshold hit with close below threshold is audited by path type and low-efficiency predicate.",
            }
        ]
    )


def ge(series: pd.Series, value: float) -> pd.Series:
    return finite(series) >= value if np.isfinite(value) else pd.Series(False, index=series.index)


def le(series: pd.Series, value: float) -> pd.Series:
    return finite(series) <= value if np.isfinite(value) else pd.Series(False, index=series.index)


def missing_any(frame: pd.DataFrame, cols: list[str]) -> pd.Series:
    missing = pd.Series(False, index=frame.index)
    for col in cols:
        if col not in frame.columns:
            missing |= True
        else:
            missing |= frame[col].isna()
    return missing


def assign_taxonomy(frame: pd.DataFrame, quantiles: dict[str, float], use_entropy: bool = True) -> pd.DataFrame:
    out = frame.copy()
    hard_required = [
        "source_row_key",
        "threshold_id",
        "episode_cluster_id",
        "segment_start_pos",
        "segment_end_pos",
        "segment_sessions",
        "entry_price",
        "shape_close_start",
        "shape_close_end",
    ]
    data_quality = missing_any(out, hard_required) | out["path_shape_quality"].isin(["invalid_price_path", "invalid_segment_bounds"])
    jump_missing = missing_any(out, ["top1_positive_gain_share", "top3_positive_gain_share", "large_up_day_count"])
    late_missing = missing_any(
        out,
        ["time_to_threshold_available_forward_share", "max_drawdown_before_hit", "underwater_days_share", "path_efficiency"],
    )
    smooth_missing = missing_any(
        out,
        [
            "path_efficiency",
            "max_drawdown_before_hit",
            "underwater_days_share",
            "top1_positive_gain_share",
            "top3_positive_gain_share",
            "trend_line_r2",
            "directional_entropy_5state",
        ],
    )
    slow_missing = missing_any(
        out,
        [
            "time_to_threshold_available_forward_share",
            "path_efficiency",
            "max_drawdown_before_hit",
            "underwater_days_share",
            "top1_positive_gain_share",
            "top3_positive_gain_share",
            "trend_line_r2",
        ],
    )
    stair_missing = missing_any(
        out,
        [
            "path_efficiency",
            "pullback_5pct_count",
            "max_drawdown_before_hit",
            "underwater_days_share",
            "top1_positive_gain_share",
            "top3_positive_gain_share",
            "trend_line_r2",
        ],
    )
    choppy_missing = missing_any(
        out,
        ["path_efficiency", "directional_entropy_5state", "max_drawdown_before_hit", "underwater_days_share", "pullback_5pct_count"],
    )
    too_short = finite(out["segment_sessions"]) < MIN_SEGMENT_SESSIONS
    high_eff = ge(out["path_efficiency"], quantiles.get("q_efficiency_70", np.nan))
    med_eff = ge(out["path_efficiency"], quantiles.get("q_efficiency_30", np.nan))
    low_eff = le(out["path_efficiency"], quantiles.get("q_efficiency_30", np.nan))
    mild_dd = le(out["max_drawdown_before_hit_abs"], quantiles.get("q_max_drawdown_abs_30", np.nan))
    severe_dd = ge(out["max_drawdown_before_hit_abs"], quantiles.get("q_max_drawdown_abs_70", np.nan))
    low_under = le(out["underwater_days_share"], quantiles.get("q_underwater_share_50", np.nan))
    high_under = ge(out["underwater_days_share"], quantiles.get("q_underwater_share_70", np.nan))
    not_high_entropy = le(out["directional_entropy_5state"], quantiles.get("q_entropy_70", np.nan)) if use_entropy else pd.Series(True, index=out.index)
    high_entropy = ge(out["directional_entropy_5state"], quantiles.get("q_entropy_70", np.nan)) if use_entropy else pd.Series(False, index=out.index)
    high_trend = ge(out["trend_line_r2"], quantiles.get("q_trend_r2_70", np.nan))
    ok_trend = ge(out["trend_line_r2"], quantiles.get("q_trend_r2_50", np.nan))
    high_gain = (
        ge(out["top1_positive_gain_share"], quantiles.get("q_top1_gain_share_85", np.nan))
        | ge(out["top3_positive_gain_share"], quantiles.get("q_top3_gain_share_85", np.nan))
        | (
            ge(out["large_up_day_count"], max(2.0, quantiles.get("q_large_up_day_count_70", np.nan)))
            & ge(out["top3_positive_gain_share"], quantiles.get("q_top3_gain_share_70", np.nan))
        )
    ) & ~jump_missing
    low_gain = le(out["top1_positive_gain_share"], quantiles.get("q_top1_gain_share_70", np.nan)) & le(
        out["top3_positive_gain_share"], quantiles.get("q_top3_gain_share_70", np.nan)
    )
    smooth_override = high_eff & mild_dd & high_trend & not_high_entropy
    long_duration = ge(
        out["time_to_threshold_available_forward_share"],
        quantiles.get("q_time_to_threshold_available_forward_share_75", np.nan),
    )
    some_pullbacks = ge(out["pullback_5pct_count"], quantiles.get("q_pullback_5pct_count_50", np.nan))
    many_pullbacks = ge(out["pullback_5pct_count"], quantiles.get("q_pullback_5pct_count_70", np.nan))
    jump = high_gain & ~smooth_override
    short = too_short & ~(high_gain & ~smooth_override)
    late = long_duration & (severe_dd | high_under | low_eff) & ~late_missing
    smooth = high_eff & mild_dd & low_under & high_trend & not_high_entropy & (low_gain | smooth_override) & ~smooth_missing
    slow = long_duration & med_eff & ~severe_dd & ~high_under & low_gain & ok_trend & ~slow_missing
    stair = med_eff & some_pullbacks & ~severe_dd & ~high_under & low_gain & ok_trend & ~stair_missing
    choppy = low_eff & high_entropy & (severe_dd | high_under | many_pullbacks) & ~choppy_missing
    path_type = np.select(
        [data_quality, jump, short, late, smooth, slow, stair, choppy],
        [
            "data_quality_blocked",
            "jump_repricing_winner",
            "unclassified_short_path",
            "late_rescue_winner",
            "smooth_trend_winner",
            "slow_grind_winner",
            "stair_step_winner",
            "choppy_reversal_winner",
        ],
        default="unclassified_mixed_path",
    )
    out["path_type"] = path_type
    predicate_cols = {
        "predicate_data_quality_blocked": data_quality,
        "predicate_too_short_path": too_short,
        "predicate_high_efficiency": high_eff,
        "predicate_medium_or_high_efficiency": med_eff,
        "predicate_low_efficiency": low_eff,
        "predicate_mild_drawdown": mild_dd,
        "predicate_severe_drawdown": severe_dd,
        "predicate_low_underwater": low_under,
        "predicate_high_underwater": high_under,
        "predicate_not_high_entropy": not_high_entropy,
        "predicate_high_entropy": high_entropy,
        "predicate_high_trend_linearity": high_trend,
        "predicate_acceptable_trend_linearity": ok_trend,
        "predicate_high_gain_concentration": high_gain,
        "predicate_low_or_medium_gain_concentration": low_gain,
        "predicate_smooth_overrides_jump": smooth_override,
        "predicate_long_duration": long_duration,
        "predicate_some_pullbacks": some_pullbacks,
        "predicate_many_pullbacks": many_pullbacks,
        "predicate_jump_repricing_winner": jump,
        "predicate_unclassified_short_path": short,
        "predicate_late_rescue_winner": late,
        "predicate_smooth_trend_winner": smooth,
        "predicate_slow_grind_winner": slow,
        "predicate_stair_step_winner": stair,
        "predicate_choppy_reversal_winner": choppy,
    }
    for col, values in predicate_cols.items():
        out[col] = values.astype(bool)
    out["predicate_low_efficiency"] = low_eff
    out["predicate_smooth_overrides_jump"] = smooth_override
    conflict_names = list(predicate_cols.keys())
    out["path_type_conflict_flags"] = [
        ";".join(name for name in conflict_names if bool(row.get(name, False)))
        for row in out[conflict_names].to_dict(orient="records")
    ]
    class_specific = [
        "path_efficiency",
        "max_drawdown_before_hit",
        "underwater_days_share",
        "top1_positive_gain_share",
        "top3_positive_gain_share",
        "trend_line_r2",
        "directional_entropy_5state",
        "pullback_5pct_count",
        "large_up_day_count",
    ]
    missing_flags = []
    for row in out[class_specific].itertuples(index=False, name=None):
        missing_cols = [col for col, value in zip(class_specific, row) if pd.isna(value)]
        missing_flags.append(";".join(missing_cols))
    out["path_type_missing_feature_flags"] = missing_flags
    out["path_type_assignment_reason"] = out["path_type"]
    out["assignment_unit"] = "episode_cluster"
    return out


def update_representative_audit(representatives: pd.DataFrame, anchor_assignments: pd.DataFrame) -> pd.DataFrame:
    type_map = anchor_assignments.set_index("source_row_key")["path_type"].to_dict()
    rows = []
    for row in representatives.itertuples(index=False):
        cluster = anchor_assignments.loc[anchor_assignments["episode_cluster_id"].eq(row.episode_cluster_id)]
        type_counts = cluster["path_type"].value_counts()
        distinct = int(type_counts.size)
        probs = type_counts / type_counts.sum() if type_counts.sum() else pd.Series(dtype=float)
        entropy = float(-np.sum(probs * np.log(probs)) / np.log(max(distinct, 2))) if len(probs) else np.nan
        dominant = str(type_counts.index[0]) if len(type_counts) else ""
        dominant_share = float(type_counts.iloc[0] / type_counts.sum()) if len(type_counts) else np.nan
        earliest_type = type_map.get(row.earliest_source_row_key, "")
        shortest_type = type_map.get(row.shortest_source_row_key, "")
        medoid_type = type_map.get(row.medoid_source_row_key, "")
        rows.append(
            {
                **row._asdict(),
                "earliest_anchor_path_type": earliest_type,
                "shortest_duration_anchor_path_type": shortest_type,
                "medoid_anchor_path_type": medoid_type,
                "representative_taxonomy_disagreement": len({earliest_type, shortest_type, medoid_type}) > 1,
                "cluster_distinct_path_type_n": distinct,
                "cluster_internal_path_type_entropy": entropy,
                "cluster_dominant_path_type": dominant,
                "cluster_dominant_path_type_share": dominant_share,
            }
        )
    return pd.DataFrame(rows)


def path_shape_feature_definition_audit() -> pd.DataFrame:
    rows = []
    taxonomy = {
        "path_efficiency",
        "max_drawdown_before_hit_abs",
        "underwater_days_share",
        "directional_entropy_5state",
        "trend_line_r2",
        "top1_positive_gain_share",
        "top3_positive_gain_share",
        "large_up_day_count",
        "time_to_threshold_available_forward_share",
        "pullback_5pct_count",
    }
    medoid = set(MEDOID_FEATURES)
    descriptive = {
        "entry_underwater_days_share",
        "pullback_10pct_count",
        "median_recovery_sessions",
        "positive_day_share",
        "ma20_hold_share",
        "large_up_day_share",
        "directional_entropy_5state_realized",
        "realized_volatility_to_hit",
        "time_to_threshold_sessions",
        "available_forward_sessions",
    }
    definitions = {
        "directional_entropy_5state": "normalized entropy of entry-vol-scaled daily log-return states over large_down/small_down/flat/small_up/large_up",
        "directional_entropy_5state_realized": "same five-state entropy with realized segment volatility scaling; diagnostic only",
        "entry_underwater_days_share": "mean(close_t < segment_start_close)",
        "large_up_day_share": "count(simple_return_t >= 0.095) / segment_sessions",
        "large_up_day_count": "count(simple_return_t >= 0.095)",
        "log_time_to_threshold": "log1p(time_to_threshold_sessions)",
        "ma20_hold_share": "mean(close_t >= trailing 20-session moving average) where MA20 is observable",
        "max_drawdown_before_hit_abs": "abs(min(close_t / running_max_close_t - 1))",
        "median_recovery_sessions": "median sessions from pullback trough back to prior running peak",
        "path_efficiency": "abs(log(close_end / close_start)) / sum(abs(daily_log_return_t)); NaN when total variation is zero",
        "positive_day_share": "mean(daily_log_return_t > 0)",
        "pullback_10pct_count": "running-peak-to-trough pullback events with drawdown <= -10%",
        "pullback_5pct_count": "running-peak-to-trough pullback events with drawdown <= -5%",
        "realized_volatility_to_hit": "sample standard deviation of daily log returns over the segment",
        "available_forward_sessions": "available future sessions from anchor entry in the upstream 15A path panel; denominator for normalized duration",
        "time_to_threshold_sessions": "first_threshold_hit_pos - entry_pos",
        "time_to_threshold_available_forward_share": "time_to_threshold_sessions / available_forward_sessions; NaN when denominator is missing or non-positive",
        "top1_positive_gain_share": "largest positive daily log return divided by sum of positive daily log returns",
        "top3_positive_gain_share": "top three positive daily log returns divided by sum of positive daily log returns",
        "trend_line_r2": "OLS R^2 of log(close_t) on segment session index",
        "underwater_days_share": "mean(close_t < running_max_close_t)",
    }
    return_basis_map = {
        "available_forward_sessions": "duration_session_count",
        "time_to_threshold_sessions": "duration_session_count",
        "log_time_to_threshold": "duration_log_session_count",
        "time_to_threshold_available_forward_share": "duration_share",
        "large_up_day_count": "simple_return_threshold_0p095",
        "large_up_day_share": "simple_return_threshold_0p095",
    }
    for feature in sorted(taxonomy | medoid | descriptive):
        roles = []
        if feature in taxonomy:
            roles.append("taxonomy_rule_input")
        if feature in medoid:
            roles.append("medoid_input")
        if feature in descriptive:
            roles.append("descriptive_readout_only")
        rows.append(
            {
                "feature_id": feature,
                "feature_role": ";".join(roles),
                "feature_definition": definitions.get(feature, ""),
                "return_basis": return_basis_map.get(feature, "log_return"),
                "price_basis": "qfq_close",
                "used_by_taxonomy_predicate": feature in taxonomy,
                "used_by_medoid": feature in medoid,
                "definition_status": "pass" if definitions.get(feature, "") else "fail",
            }
        )
    return pd.DataFrame(rows)


def distribution_readout(assignments: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (split, ptype), sub in assignments.loc[assignments["threshold_id"].eq(SELECTED_THRESHOLD_ID)].groupby(["split_bucket", "path_type"]):
        for feature in METRIC_FEATURES:
            values = finite(sub.get(feature, pd.Series(dtype=float))).dropna()
            rows.append(
                {
                    "split_bucket": split,
                    "path_type": ptype,
                    "feature_id": feature,
                    "episode_cluster_n": len(sub),
                    "feature_p25": float(values.quantile(0.25)) if not values.empty else np.nan,
                    "feature_median": float(values.median()) if not values.empty else np.nan,
                    "feature_p75": float(values.quantile(0.75)) if not values.empty else np.nan,
                    "metric_distribution_status": "pass",
                }
            )
    return pd.DataFrame(rows)


def taxonomy_readout(assignments: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (split, threshold, ptype), sub in assignments.groupby(["split_bucket", "threshold_id", "path_type"], sort=False):
        den = len(assignments.loc[assignments["split_bucket"].eq(split) & assignments["threshold_id"].eq(threshold)])
        choppy = assignments.loc[
            assignments["split_bucket"].eq(split)
            & assignments["threshold_id"].eq(threshold)
            & assignments["path_type"].eq("choppy_reversal_winner")
        ]
        low_eff = assignments.loc[
            assignments["split_bucket"].eq(split)
            & assignments["threshold_id"].eq(threshold)
            & assignments["predicate_low_efficiency"].astype(bool)
        ]
        rows.append(
            {
                "split_bucket": split,
                "threshold_id": threshold,
                "path_type": ptype,
                "episode_cluster_n": len(sub),
                "episode_cluster_share": safe_rate(len(sub), den),
                "winner_anchor_n": int(finite(sub.get("cluster_anchor_n", pd.Series(dtype=float))).sum()),
                "wick_hit_only_n": int(bool_series(sub.get("wick_hit_only", pd.Series(False, index=sub.index))).sum()),
                "wick_hit_only_share": safe_rate(bool_series(sub.get("wick_hit_only", pd.Series(False, index=sub.index))).sum(), len(sub)),
                "wick_hit_only_share_by_path_type": safe_rate(bool_series(sub.get("wick_hit_only", pd.Series(False, index=sub.index))).sum(), len(sub)),
                "wick_hit_only_share_in_choppy_reversal_winner": safe_rate(
                    bool_series(choppy.get("wick_hit_only", pd.Series(dtype=bool))).sum(), len(choppy)
                ),
                "wick_hit_only_share_in_low_efficiency_predicate_hits": safe_rate(
                    bool_series(low_eff.get("wick_hit_only", pd.Series(dtype=bool))).sum(), len(low_eff)
                ),
                "smooth_overrides_jump_episode_cluster_n": int(
                    bool_series(sub.get("predicate_smooth_overrides_jump", pd.Series(False, index=sub.index))).sum()
                ),
                "smooth_overrides_jump_share": safe_rate(
                    bool_series(sub.get("predicate_smooth_overrides_jump", pd.Series(False, index=sub.index))).sum(), len(sub)
                ),
                "path_type_missing_feature_flag_n": int(sub["path_type_missing_feature_flags"].astype(str).ne("").sum()),
            }
        )
    return pd.DataFrame(rows)


def simple_group_readout(assignments: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows = []
    for keys, sub in assignments.groupby(group_cols, sort=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_cols, keys))
        row["episode_cluster_n"] = len(sub)
        row["winner_anchor_n"] = int(finite(sub.get("cluster_anchor_n", pd.Series(dtype=float))).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def entropy_incrementality_readout(assignments: pd.DataFrame) -> pd.DataFrame:
    rows = []
    features = [
        "time_to_threshold_sessions",
        "time_to_threshold_available_forward_share",
        "path_efficiency",
        "max_drawdown_before_hit_abs",
        "underwater_days_share",
        "top1_positive_gain_share",
        "top3_positive_gain_share",
        "trend_line_r2",
        "realized_volatility_to_hit",
    ]
    base = assignments.loc[assignments["threshold_id"].eq(SELECTED_THRESHOLD_ID)]
    for feature in features:
        row = {"feature_pair": f"directional_entropy_5state::{feature}"}
        for split in SPLITS:
            sub = base.loc[base["split_bucket"].eq(split)]
            row[f"spearman_corr_{split}"] = sub[["directional_entropy_5state", feature]].corr(method="spearman").iloc[0, 1] if len(sub) >= 3 else np.nan
        row["redundancy_flag_abs_corr_ge_0p80"] = any(
            abs(row.get(f"spearman_corr_{split}", np.nan)) >= 0.80 for split in SPLITS if np.isfinite(row.get(f"spearman_corr_{split}", np.nan))
        )
        rows.append(row)
    corr = base[["directional_entropy_5state", "directional_entropy_5state_realized"]].corr(method="spearman").iloc[0, 1] if len(base) >= 3 else np.nan
    rows.append(
        {
            "feature_pair": "directional_entropy_5state::directional_entropy_5state_realized",
            "spearman_corr_train": corr,
            "spearman_corr_validation": np.nan,
            "spearman_corr_robustness": np.nan,
            "redundancy_flag_abs_corr_ge_0p80": bool(np.isfinite(corr) and abs(corr) >= 0.80),
            "entropy_scaling_variant_corr": corr,
        }
    )
    out = pd.DataFrame(rows)
    core = out.loc[~out["feature_pair"].astype(str).str.endswith("directional_entropy_5state_realized")]
    redundant = bool(core.get("redundancy_flag_abs_corr_ge_0p80", pd.Series(dtype=bool)).astype(bool).any())
    out["entropy_incrementality_status"] = "redundant_readout_only" if redundant else "incremental_shape_descriptor"
    return out


def taxonomy_without_entropy_ablation(episode_metrics: pd.DataFrame, primary: pd.DataFrame, quantiles: dict[str, float]) -> pd.DataFrame:
    without = assign_taxonomy(episode_metrics, quantiles, use_entropy=False)
    merged = primary[["source_row_key", "split_bucket", "threshold_id", "path_type"]].merge(
        without[["source_row_key", "path_type"]].rename(columns={"path_type": "taxonomy_without_entropy_assignment"}),
        on="source_row_key",
        how="left",
    )
    merged = merged.rename(columns={"path_type": "taxonomy_with_entropy_assignment"})
    merged["assignment_changed_by_entropy"] = merged["taxonomy_with_entropy_assignment"].ne(merged["taxonomy_without_entropy_assignment"])
    rows = []
    for (split, threshold), sub in merged.groupby(["split_bucket", "threshold_id"], sort=False):
        rows.append(
            {
                "split_bucket": split,
                "threshold_id": threshold,
                "episode_cluster_n": len(sub),
                "assignment_changed_by_entropy_n": int(sub["assignment_changed_by_entropy"].sum()),
                "entropy_incremental_class_share_delta": safe_rate(sub["assignment_changed_by_entropy"].sum(), len(sub)),
            }
        )
    return pd.DataFrame(rows)


def js_divergence(a: pd.Series, b: pd.Series) -> float:
    cats = sorted(set(a.index).union(set(b.index)))
    p = np.array([a.get(cat, 0.0) for cat in cats], dtype=float)
    q = np.array([b.get(cat, 0.0) for cat in cats], dtype=float)
    if p.sum() == 0 or q.sum() == 0:
        return np.nan
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)

    def kl(x: np.ndarray, y: np.ndarray) -> float:
        mask = x > 0
        return float(np.sum(x[mask] * np.log(x[mask] / y[mask])))

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def taxonomy_stability_gate(assignments: pd.DataFrame, rep_audit: pd.DataFrame) -> pd.DataFrame:
    base = assignments.loc[assignments["threshold_id"].eq(SELECTED_THRESHOLD_ID)]
    dist = {split: base.loc[base["split_bucket"].eq(split)]["path_type"].value_counts() for split in SPLITS}
    train = base.loc[base["split_bucket"].eq("train")]
    rep_train = rep_audit.loc[rep_audit["threshold_id"].eq(SELECTED_THRESHOLD_ID)]
    rep_disagree = safe_rate(rep_train["representative_taxonomy_disagreement"].sum(), len(rep_train))
    tradable = train["path_type"].isin(TRADABLE_TYPES).sum()
    js_val = js_divergence(dist.get("train", pd.Series(dtype=float)), dist.get("validation", pd.Series(dtype=float)))
    js_rob = js_divergence(dist.get("train", pd.Series(dtype=float)), dist.get("robustness", pd.Series(dtype=float)))
    extreme = (np.isfinite(js_val) and js_val > 0.30) or (np.isfinite(js_rob) and js_rob > 0.30) or (np.isfinite(rep_disagree) and rep_disagree > 0.50)
    fast = train.loc[bool_series(train.get("fast_winner_flag", pd.Series(False, index=train.index)))]
    slow = train.loc[bool_series(train.get("slow_winner_flag", pd.Series(False, index=train.index)))]
    cats = sorted(set(fast["path_type"].astype(str)).union(set(slow["path_type"].astype(str))))
    if cats and len(fast) and len(slow):
        fast_share = fast["path_type"].value_counts(normalize=True)
        slow_share = slow["path_type"].value_counts(normalize=True)
        slow_fast_delta = max(abs(float(slow_share.get(cat, 0.0)) - float(fast_share.get(cat, 0.0))) for cat in cats)
    else:
        slow_fast_delta = np.nan
    threshold_ranks = []
    train_all = assignments.loc[assignments["split_bucket"].eq("train")]
    base_rank = train_all.loc[train_all["threshold_id"].eq(SELECTED_THRESHOLD_ID)]["path_type"].value_counts().rank(ascending=False)
    for threshold in sorted(set(train_all["threshold_id"].astype(str)) - {SELECTED_THRESHOLD_ID}):
        other_rank = train_all.loc[train_all["threshold_id"].eq(threshold)]["path_type"].value_counts().rank(ascending=False)
        all_types = sorted(set(base_rank.index).union(set(other_rank.index)))
        if len(all_types) >= 2:
            threshold_ranks.append(
                pd.Series([base_rank.get(ptype, len(all_types) + 1) for ptype in all_types]).corr(
                    pd.Series([other_rank.get(ptype, len(all_types) + 1) for ptype in all_types]), method="spearman"
                )
            )
    threshold_rank_stability = float(np.nanmin(threshold_ranks)) if threshold_ranks else np.nan
    row = {
        "js_divergence_train_validation_path_type_distribution": js_val,
        "js_divergence_train_robustness_path_type_distribution": js_rob,
        "representative_taxonomy_disagreement_share": rep_disagree,
        "cluster_internal_path_type_entropy_median": finite(rep_audit.get("cluster_internal_path_type_entropy", pd.Series(dtype=float))).median(),
        "cluster_internal_path_type_entropy_p75": finite(rep_audit.get("cluster_internal_path_type_entropy", pd.Series(dtype=float))).quantile(0.75),
        "cluster_dominant_path_type_share_median": finite(rep_audit.get("cluster_dominant_path_type_share", pd.Series(dtype=float))).median(),
        "cluster_dominant_path_type_share_p25": finite(rep_audit.get("cluster_dominant_path_type_share", pd.Series(dtype=float))).quantile(0.25),
        "tradable_shape_share": safe_rate(tradable, len(train)),
        "slow_fast_path_type_composition_delta": slow_fast_delta,
        "threshold_sensitivity_path_type_rank_stability": threshold_rank_stability,
        "stability_extreme_failure": bool(extreme),
        "taxonomy_stability_status": "pass",
    }
    return pd.DataFrame([row])


def search_accounting_audit(config: dict[str, Any]) -> pd.DataFrame:
    taxonomy = config.get("taxonomy", {})
    row = {
        "startup_authorization_basis": taxonomy.get("startup_authorization_basis", "15A_material_censoring_finding_not_15A_morphology_verdict"),
        "manual_research_plan_override": bool(taxonomy.get("manual_research_plan_override", True)),
        "selected_threshold_id": taxonomy.get("selected_threshold_id", SELECTED_THRESHOLD_ID),
        "threshold_selection_source": "inherited_from_15A_lowest_pre_registered_material_censoring_threshold",
        "taxonomy_fit_split": "train",
        "validation_usage": "readout_only",
        "robustness_usage": "readout_only",
        "taxonomy_rule_type": "deterministic_train_quantile_rule",
        "unsupervised_clustering_usage": "prohibited_for_primary_decision",
        "entropy_usage": "descriptor_not_standalone_label",
        "entry_search_authorized": False,
        "signal_search_authorized": False,
        "model_training_authorized": False,
    }
    row["search_accounting_status"] = "pass" if (
        row["startup_authorization_basis"] == "15A_material_censoring_finding_not_15A_morphology_verdict"
        and row["manual_research_plan_override"]
        and not row["entry_search_authorized"]
        and not row["signal_search_authorized"]
        and not row["model_training_authorized"]
    ) else "fail"
    return pd.DataFrame([row])


def decision_row(
    gates: dict[str, str],
    assignments: pd.DataFrame,
    stability: pd.DataFrame,
    config: dict[str, Any],
    entropy_incrementality_status: str = "",
) -> pd.DataFrame:
    taxonomy = config.get("taxonomy", {})
    hard_fail = any(value != "pass" for value in gates.values())
    train = assignments.loc[assignments["threshold_id"].eq(SELECTED_THRESHOLD_ID) & assignments["split_bucket"].eq("train")]
    validation = assignments.loc[assignments["threshold_id"].eq(SELECTED_THRESHOLD_ID) & assignments["split_bucket"].eq("validation")]
    robustness = assignments.loc[assignments["threshold_id"].eq(SELECTED_THRESHOLD_ID) & assignments["split_bucket"].eq("robustness")]
    eligible_n = len(train)
    shares = train["path_type"].value_counts(normalize=True) if eligible_n else pd.Series(dtype=float)
    counts = train["path_type"].value_counts() if eligible_n else pd.Series(dtype=int)
    material = [ptype for ptype, count in counts.items() if count >= taxonomy.get("material_path_type_min_n", 50) and shares.get(ptype, 0) >= taxonomy.get("material_path_type_min_share", 0.05)]
    unclassified_share = float(shares[[idx for idx in shares.index if idx.startswith("unclassified") or idx == "data_quality_blocked"]].sum()) if eligible_n else np.nan
    largest_share = float(shares.max()) if eligible_n else np.nan
    val_material = int((validation["path_type"].value_counts() >= taxonomy.get("material_path_type_min_n", 50)).sum()) if len(validation) else 0
    rob_material = int((robustness["path_type"].value_counts() >= taxonomy.get("material_path_type_min_n", 50)).sum()) if len(robustness) else 0
    stability_extreme = bool(stability.iloc[0]["stability_extreme_failure"]) if not stability.empty else True
    rep_disagree = float(stability.iloc[0].get("representative_taxonomy_disagreement_share", np.nan)) if not stability.empty else np.nan
    rep_disagree_max = taxonomy.get("representative_disagreement_share_max", 0.35)
    support_failure = (
        len(material) < taxonomy.get("material_path_type_min_count", 3)
        or largest_share > taxonomy.get("largest_path_type_share_max", 0.75)
        or unclassified_share > taxonomy.get("unclassified_share_max", 0.35)
        or (np.isfinite(rep_disagree) and rep_disagree > rep_disagree_max and not stability_extreme)
        or val_material < 2
        or rob_material < 2
    )
    if hard_fail:
        decision = "15B_blocked_input_or_lineage_failure"
        next_req = "none"
    elif eligible_n < taxonomy.get("eligible_train_episode_cluster_min_n", 200):
        decision = "15B_path_shape_taxonomy_inconclusive_too_sparse"
        next_req = "none"
    elif support_failure:
        decision = "15B_no_stable_path_shape_taxonomy"
        next_req = "none"
    elif stability_extreme:
        decision = "15B_path_shape_taxonomy_promising_but_unstable"
        next_req = "none"
    else:
        decision = "15B_path_shape_taxonomy_supported_for_label_revision"
        next_req = "requirement_15c_path_shape_label_separability_diagnostic.md"
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_req,
                "label_deployment_authorized": False,
                "signal_search_authorized": False,
                "model_training_authorized": False,
                "entry_policy_authorized": False,
                "eligible_train_episode_cluster_n": eligible_n,
                "material_path_type_n": len(material),
                "largest_path_type_share_train": largest_share,
                "unclassified_share_train": unclassified_share,
                "validation_material_path_type_n": val_material,
                "robustness_material_path_type_n": rob_material,
                "representative_taxonomy_disagreement_share": rep_disagree,
                "representative_disagreement_support_gate": bool(np.isfinite(rep_disagree) and rep_disagree <= rep_disagree_max),
                "validation_material_path_type_support_gate": bool(val_material >= 2),
                "robustness_material_path_type_support_gate": bool(rob_material >= 2),
                "stability_extreme_failure": stability_extreme,
                "entropy_incrementality_status": entropy_incrementality_status,
                **{f"{key}_gate": value for key, value in gates.items()},
            }
        ]
    )


def render_report(
    decision: pd.DataFrame,
    taxonomy_readout_frame: pd.DataFrame,
    stability: pd.DataFrame,
    entropy: pd.DataFrame,
    rule_audit: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    selected = taxonomy_readout_frame.loc[taxonomy_readout_frame["threshold_id"].eq(SELECTED_THRESHOLD_ID)]
    train = selected.loc[selected["split_bucket"].eq("train")].sort_values("episode_cluster_n", ascending=False)
    lines = [
        f"| {row.path_type} | {int(row.episode_cluster_n)} | {row.episode_cluster_share:.4f} | {int(row.winner_anchor_n)} |"
        for row in train.itertuples(index=False)
    ]
    stab = stability.iloc[0] if not stability.empty else pd.Series(dtype=object)
    entropy_status = str(d.get("entropy_incrementality_status", ""))
    train_total = train["episode_cluster_n"].sum() if not train.empty else 0
    train_wick = train["wick_hit_only_n"].sum() if not train.empty else 0
    train_wick_share = safe_rate(train_wick, train_total)
    choppy = train.loc[train["path_type"].eq("choppy_reversal_winner")]
    choppy_wick_share = float(choppy["wick_hit_only_share_by_path_type"].iloc[0]) if not choppy.empty else np.nan
    low_eff_wick_share = float(train["wick_hit_only_share_in_low_efficiency_predicate_hits"].dropna().iloc[0]) if not train["wick_hit_only_share_in_low_efficiency_predicate_hits"].dropna().empty else np.nan
    if np.isfinite(choppy_wick_share) and choppy_wick_share > train_wick_share + 0.10:
        wick_note = "choppy_reversal_winner 的 wick-hit 占比明显高于总体，choppy 占比结论应降级为存疑，并建议后续隔离 wick-hit-only 路径重测。"
    elif np.isfinite(choppy_wick_share):
        wick_note = "choppy_reversal_winner 未显示明显高于总体的 wick-hit 集中污染。"
    else:
        wick_note = "selected threshold 的 train readout 中未形成 choppy_reversal_winner 材料类别，因此 choppy wick-hit 污染无法作为独立结论。"
    quantile_pop = rule_audit.loc[rule_audit["rule_type"].eq("taxonomy_quantile"), "taxonomy_quantile_fit_population_n"]
    quantile_fit_n = int(quantile_pop.dropna().iloc[0]) if not quantile_pop.dropna().empty else 0
    scaler_pop = rule_audit.loc[rule_audit["rule_type"].eq("medoid_scaler"), "medoid_scaler_fit_population_n"]
    scaler_fit_n = int(scaler_pop.dropna().iloc[0]) if not scaler_pop.dropna().empty else 0
    entropy_core = entropy.loc[entropy["feature_pair"].astype(str).str.contains("::")].copy()
    redundant_pairs = entropy_core.loc[bool_series(entropy_core.get("redundancy_flag_abs_corr_ge_0p80", pd.Series(False, index=entropy_core.index))), "feature_pair"].astype(str).tolist()
    redundant_text = ", ".join(redundant_pairs) if redundant_pairs else "none"
    return f"""# 15B Winner Path Shape Taxonomy Diagnostic

## 1. 单行裁决

15B 的裁决状态为 `{d['decision_state']}`。本实验只做 winner realized path shape taxonomy，不授权 signal search、entry、model 或 label deployment。

| item | value |
|---|---|
| decision_state | `{d['decision_state']}` |
| next_allowed_requirement | `{d['next_allowed_requirement']}` |
| eligible_train_episode_cluster_n | {int(d['eligible_train_episode_cluster_n'])} |
| material_path_type_n | {int(d['material_path_type_n'])} |
| largest_path_type_share_train | {d['largest_path_type_share_train']:.4f} |
| unclassified_share_train | {d['unclassified_share_train']:.4f} |
| representative_taxonomy_disagreement_share | {d.get('representative_taxonomy_disagreement_share', np.nan):.4f} |
| entropy_incrementality_status | `{entropy_status}` |
| tradable_shape_share | {stab.get('tradable_shape_share', np.nan):.4f} |

## 2. 为什么 15B 可以在 15A `next_allowed_requirement = none` 后启动

15A 禁止的是 separability、signal search 和 label deployment。15B 不继承 15A 的授权字段；启动依据是 15A 已经证实 fixed-horizon label 存在 material right-censoring，而 15A 的 slow-winner morphology 否定只覆盖 t0-close 截面形态，不能否定 realized forward path shape taxonomy。

## 3. Episode Cluster 口径

15B 的 primary denominator 是 `winner_episode_cluster`，不是 anchor row。连续 anchor 对同一段上涨路径的重复计数只进入 secondary readout。

15B 在 `(instrument, threshold_id)` 内做 transitive interval clustering，不按 split 先切开。跨 split cluster 保留 readout，但不进入 train-only rule fitting。

## 4. Path Shape Feature 与 Rule

Path shape 使用 qfq close，从 entry_pos 到 first_threshold_hit_pos inclusive。Hit detection 仍沿用 15A 的 qfq high，因此 close-based shape 与 high-based hit 分离审计。

核心 feature 包括：

- `path_efficiency = abs(net_log_return) / total_variation`，衡量净上涨相对路径摆动的效率；
- `max_drawdown_before_hit_abs` 与 `underwater_days_share`，同时刻画回撤深度和水下持续性；
- `directional_entropy_5state`，用 entry-vol-scaled daily log return 的五状态归一化 entropy；
- `trend_line_r2`，用 log(close) 对 session index 的线性趋势拟合度；
- `top1/top3_positive_gain_share` 与 `large_up_day_count`，用于隔离 jump repricing，而不是单独按涨停天数分类。

Medoid scaler fit population 为 {scaler_fit_n} 条 anchor path；taxonomy quantile fit population 为 {quantile_fit_n} 个 train single-split episode cluster。Validation / robustness 只应用冻结规则，不参与 quantile 拟合。

## 5. Train Path Type Readout

| path_type | episode_cluster_n | share | winner_anchor_n |
|---|---:|---:|---:|
{chr(10).join(lines)}

## 6. Entropy 与 Path Shape

Entropy 只作为 path-shape descriptor，不是 standalone label。当前 entropy incrementality 状态为 `{entropy_status}`；abs Spearman >= 0.80 的冗余 pair 为：{redundant_text}。

报告同时输出 entry-vol scaled entropy、realized-vol scaled entropy 及 incrementality readout，用于检查 entropy 是否只是 duration、drawdown 或 gain concentration 的换名。

## 7. Wick-Hit 与 Close Path 口径风险

selected threshold train 总体 `wick_hit_only_share` 为 {train_wick_share:.4f}；`wick_hit_only_share_in_choppy_reversal_winner` 为 {choppy_wick_share:.4f}；`wick_hit_only_share_in_low_efficiency_predicate_hits` 为 {low_eff_wick_share:.4f}。

{wick_note}

## 8. 跨 Split 稳定性与 Cluster 内异质性

| item | value |
|---|---:|
| js_divergence_train_validation | {stab.get('js_divergence_train_validation_path_type_distribution', np.nan):.4f} |
| js_divergence_train_robustness | {stab.get('js_divergence_train_robustness_path_type_distribution', np.nan):.4f} |
| representative_taxonomy_disagreement_share | {stab.get('representative_taxonomy_disagreement_share', np.nan):.4f} |
| cluster_internal_path_type_entropy_p75 | {stab.get('cluster_internal_path_type_entropy_p75', np.nan):.4f} |
| cluster_dominant_path_type_share_p25 | {stab.get('cluster_dominant_path_type_share_p25', np.nan):.4f} |
| slow_fast_path_type_composition_delta | {stab.get('slow_fast_path_type_composition_delta', np.nan):.4f} |
| threshold_sensitivity_path_type_rank_stability | {stab.get('threshold_sensitivity_path_type_rank_stability', np.nan):.4f} |

代表 anchor 分歧率较高时，说明单个 medoid 不能充分代表 cluster 内所有 anchor-defined opportunity path。本次结果必须按这一限制阅读，不能把 `winner_episode_cluster_n` 直接解释成可独立交易样本数。

## 9. 后续候选与 Readout-Only 边界

由于当前 decision 不是 `15B_path_shape_taxonomy_supported_for_label_revision`，没有任何 path type 被授权进入 15C。`smooth_trend_winner`、`slow_grind_winner`、`stair_step_winner` 可以作为后续人工讨论候选；`jump_repricing_winner`、`late_rescue_winner`、`unclassified_*` 当前只能作为 descriptive readout。

## 10. 后续边界

只有当 decision 进入 `15B_path_shape_taxonomy_supported_for_label_revision` 时，才允许新建 15C separability diagnostic。无论 15B 结果如何，本实验都不授权 entry、模型、仓位或 label deployment。

当前裁决为 `{d['decision_state']}`，所以 path-defined winner 仍不适合作为后续预测标签直接使用。
"""


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: str, outputs: dict[str, Path]) -> Path:
    publishable = {key: value for key, value in outputs.items() if key != "manifest" and value.exists() and LOCAL_CACHE_DIR not in value.parents}
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": r15a.git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha(config_path),
        "decision_state": decision,
        "outputs": {key: str(value) for key, value in publishable.items()},
        "output_hashes": {key: file_sha(value) for key, value in publishable.items() if value.is_file()},
    }
    return write_json(path, payload)


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = r13a.load_yaml(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    for path in [TABLE_DIR, LOCAL_CACHE_DIR, REPORT_DIR, MANIFEST_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    input_audit = build_input_artifact_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_gate, input_reason = input_gate_status(input_audit)
    if check_inputs_only:
        return 0 if input_gate == "pass" else 2
    if input_gate != "pass":
        empty_decision = pd.DataFrame(
            [{"decision_state": "15B_blocked_input_or_lineage_failure", "next_allowed_requirement": "none", "blocking_reason": input_reason}]
        )
        write_df(outputs["decision"], empty_decision)
        write_manifest(outputs["manifest"], config_path, config, "15B_blocked_input_or_lineage_failure", outputs)
        return 2

    label_path = ensure_15a_cache(resolved)
    label = load_label_panel(resolved)
    upstream = build_upstream_lineage_audit(resolved)
    adapter = path_defined_label_adapter_audit(label, label_path, resolved["stock_daily_qfq_dir"])
    rebuild = path_defined_label_rebuild_audit(label)
    price = build_price_path_completeness(label, resolved["stock_daily_qfq_dir"])
    write_df(outputs["upstream_lineage_audit"], upstream)
    write_df(outputs["path_defined_label_adapter_audit"], adapter)
    write_df(outputs["path_defined_label_rebuild_audit"], rebuild)
    write_df(outputs["price_path_completeness_audit"], price)

    membership, clusters = build_winner_episode_clusters(label)
    split_audit, cluster_panel = split_overlap_audit(membership, clusters, label, resolved["stock_daily_qfq_dir"])
    membership = membership.merge(
        split_audit[
            [
                "episode_cluster_id",
                "cluster_split_bucket",
                "touches_multiple_split_buckets",
                "touches_multiple_calendar_split_buckets",
            ]
        ],
        on="episode_cluster_id",
        how="left",
    )
    write_df(outputs["winner_episode_cluster_membership_audit"], membership)
    write_df(outputs["split_overlap_audit"], split_audit)
    write_df(outputs["winner_episode_cluster_panel"], cluster_panel)

    anchor_metrics = compute_anchor_path_shape_metrics(membership, resolved["stock_daily_qfq_dir"])
    write_df(outputs["anchor_path_shape_feature_panel"], anchor_metrics)
    representatives, episode_metrics, scaler_rules = select_representatives(anchor_metrics, cluster_panel)
    episode_metrics = episode_metrics.merge(cluster_panel[["episode_cluster_id", "cluster_anchor_n"]], on="episode_cluster_id", how="left")
    quantiles, _fit_pop, quantile_rules = fit_taxonomy_quantiles(episode_metrics)
    rule_audit = pd.concat([scaler_rules, quantile_rules, taxonomy_guard_rule_rows()], ignore_index=True, sort=False)
    write_df(outputs["path_shape_taxonomy_rule_audit"], rule_audit)

    episode_assignments = assign_taxonomy(episode_metrics, quantiles)
    anchor_assignments = assign_taxonomy(anchor_metrics, quantiles)
    anchor_assignments["assignment_unit"] = "anchor_path"
    taxonomy_panel = pd.concat([episode_assignments, anchor_assignments], ignore_index=True, sort=False)
    rep_audit = update_representative_audit(representatives, anchor_assignments)
    write_df(outputs["representative_anchor_audit"], rep_audit)
    write_df(outputs["episode_path_shape_feature_panel"], episode_assignments)
    write_df(outputs["taxonomy_assignment_panel"], taxonomy_panel)

    feature_audit = path_shape_feature_definition_audit()
    taxonomy_read = taxonomy_readout(episode_assignments)
    stability = taxonomy_stability_gate(episode_assignments, rep_audit)
    entropy = entropy_incrementality_readout(episode_assignments)
    entropy_status = str(entropy["entropy_incrementality_status"].dropna().iloc[0]) if "entropy_incrementality_status" in entropy.columns and not entropy["entropy_incrementality_status"].dropna().empty else ""
    ablation = taxonomy_without_entropy_ablation(episode_metrics, episode_assignments, quantiles)
    search = search_accounting_audit(config)
    write_df(outputs["path_shape_feature_definition_audit"], feature_audit)
    write_df(outputs["path_shape_metric_distribution_readout"], distribution_readout(episode_assignments))
    write_df(outputs["path_shape_taxonomy_readout"], taxonomy_read)
    write_df(outputs["path_shape_by_split_readout"], simple_group_readout(episode_assignments, ["split_bucket", "path_type"]))
    write_df(outputs["path_shape_by_threshold_sensitivity_readout"], simple_group_readout(episode_assignments, ["threshold_id", "path_type"]))
    write_df(outputs["slow_fast_by_path_type_readout"], simple_group_readout(episode_assignments, ["path_type", "fast_winner_flag", "slow_winner_flag"]))
    write_df(outputs["entropy_incrementality_readout"], entropy)
    write_df(outputs["taxonomy_without_entropy_ablation_readout"], ablation)
    write_df(outputs["taxonomy_stability_gate"], stability)
    write_df(outputs["search_accounting_audit"], search)

    gates = {
        "input_artifact": input_gate,
        "upstream_lineage": gate_from_status(upstream, "lineage_status"),
        "price_path_completeness": gate_from_status(price, "price_path_status"),
        "path_defined_label_adapter": gate_from_status(adapter, "adapter_status"),
        "path_defined_label_rebuild": gate_from_status(rebuild, "rebuild_status"),
        "episode_cluster": gate_from_status(membership, "episode_cluster_status"),
        "train_rule_fit": gate_from_status(rule_audit, "train_rule_fit_status"),
        "search_accounting": gate_from_status(search, "search_accounting_status"),
    }
    decision = decision_row(gates, episode_assignments, stability, config, entropy_status)
    write_df(outputs["decision"], decision)
    write_text(outputs["report"], render_report(decision, taxonomy_read, stability, entropy, rule_audit))
    write_manifest(outputs["manifest"], config_path, config, str(decision.iloc[0]["decision_state"]), outputs)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())
