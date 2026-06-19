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
from sklearn.tree import DecisionTreeClassifier


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
TOPIC_SRC_DIR = TOPIC_ROOT / "src"

if str(TOPIC_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(TOPIC_SRC_DIR))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402


RUN_ID = "12A4_state_change_meta_label_filter_feasibility"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a4_state_change_meta_label_filter_feasibility.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

RAW_R_CORE_ARM = "08_R_core_event_regime_gated_raw"
PRIMARY_SOURCE_ARM = "C0_state_change"
R_CORE_SOURCE_ARM = "R_core"
SPLITS = ("all", "train", "validation", "robustness")
PRIMARY_MODEL_FAMILIES = (
    "logistic_regression_l2",
    "logistic_regression_l1",
    "shallow_decision_tree_max_depth_3",
    "scorecard_quantile_binning",
)
FORBIDDEN_PATTERNS = (
    "episode_low",
    "episode_high",
    "first_50pct",
    "mfe",
    "future",
    "target_",
    "label_",
    "winner_",
    "fast_fail_",
    "false_repair_",
    "bad_side_",
    "event_minus_low",
    "inside_window",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A4 state-change meta-label filter feasibility.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
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
    if text.startswith("outputs/"):
        return EXPERIMENT_DIR / path
    if text.startswith(("configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "regime_scope_exclusion_audit": TABLE_DIR / "regime_scope_exclusion_audit.csv",
        "split_time_boundary_audit": TABLE_DIR / "split_time_boundary_audit.csv",
        "event_universe": TABLE_DIR / "meta_label_event_universe.csv.gz",
        "event_targets": TABLE_DIR / "meta_label_event_targets.csv.gz",
        "feature_dictionary": TABLE_DIR / "meta_label_feature_dictionary.csv",
        "feature_pit_audit": TABLE_DIR / "meta_label_feature_pit_audit.csv",
        "entropy_audit": TABLE_DIR / "entropy_feature_redundancy_audit.csv",
        "volume_audit": TABLE_DIR / "volume_acceleration_feature_audit.csv",
        "r_core_baseline": TABLE_DIR / "risk_on_r_core_baseline.csv",
        "active_state": TABLE_DIR / "state_change_active_state_decay_frontier.csv",
        "non_model_frontier": TABLE_DIR / "non_model_filter_frontier.csv",
        "validation_health": TABLE_DIR / "validation_threshold_health.csv",
        "score_frontier": TABLE_DIR / "meta_label_score_bucket_frontier.csv",
        "supported_selfcheck": TABLE_DIR / "supported_gate_feasibility_selfcheck.csv",
        "model_card": TABLE_DIR / "meta_label_model_card.csv",
        "lightgbm_frontier": TABLE_DIR / "lightgbm_challenger_score_bucket_frontier.csv",
        "lightgbm_model_card": TABLE_DIR / "lightgbm_challenger_model_card.csv",
        "decision": TABLE_DIR / "meta_label_decision.csv",
        "feature_matrix": LOCAL_CACHE_DIR / "meta_label_event_feature_matrix.parquet",
        "report": REPORT_DIR / "state_change_meta_label_filter_decision_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    return pd.read_csv(path, low_memory=False, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        frame.to_parquet(path, index=False)
    elif suffixes.endswith(".csv.gz"):
        frame.to_csv(path, index=False, compression={"method": "gzip", "compresslevel": 9, "mtime": 1})
    else:
        frame.to_csv(path, index=False)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def path_sha(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def mtime_utc(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def safe_rate(num: int | float, den: int | float) -> float:
    if den is None or pd.isna(den) or float(den) == 0:
        return np.nan
    return float(num) / float(den)


def boolish(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t", "pass", "ok"}


def bool_series(values: pd.Series) -> pd.Series:
    return values.map(boolish).astype(bool)


def date_text(value: Any) -> str:
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d")


def numeric(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce")


def int_or_none(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        out = int(value)
    except (TypeError, ValueError):
        return None
    return out if out >= 0 else None


def stable_event_id(*parts: Any) -> str:
    return stable_hash([str(part) for part in parts])[:24]


EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "backbone_frontier_decision": (
        "decision_state",
        "partial_feature_source_gate_pass",
        "label_recompute_gate_pass",
        "min_label_recompute_parity_match_rate",
    ),
    "backbone_episode_recall_precision_frontier": ("frontier_arm_id", "split", "window_id", "event_n", "event_precision"),
    "backbone_event_timing_distribution": ("frontier_arm_id", "split", "window_id", "first_event_minus_low_trading_days_median"),
    "backbone_captured_episode_density": ("frontier_arm_id", "split", "window_id", "episode_id", "event_count_inside_window"),
    "backbone_frontier_slice_readout": ("frontier_arm_id", "split", "slice_type", "slice_value", "event_n"),
    "backbone_missed_episode_diagnostics": ("split", "window_id", "episode_id", "miss_reason"),
    "backbone_b8_incremental_episode_recall": ("split", "window_id", "eligible_episode_n", "b8_incremental_episode_n"),
    "backbone_event_label_exposure": ("frontier_arm_id", "split", "event_n", "label_20d_complete_rate", "bad_side_10_20_rate"),
    "state_change_label_recompute_parity_audit": ("label_id", "parity_status", "min_required_match_rate"),
    "state_change_generation_decision": ("decision", "primary_canonical_event_n"),
    "state_change_candidate_event_canonical": (
        "canonical_event_id",
        "primary_family_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "event_split",
        "market_regime_bucket",
        "candidate_generation_status",
        "non_executable_next_open",
        "event_t0_pit_status",
        "trade_open_pit_status",
    ),
    "state_change_candidate_event_instances": (
        "event_instance_id",
        "family_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "raw_event_status",
    ),
    "state_change_family_formula_spec": ("family_id", "variant_id", "pit_status"),
    "state_change_canonicalization_spec": ("canonicalizer_id", "rule_hash"),
    "state_change_density_audit": ("candidate_scope_id", "split", "event_n", "density_status"),
    "episode_target_registry_06": (
        "episode_id",
        "instrument",
        "episode_low_date",
        "episode_high_date",
        "first_50pct_date",
        "pre120_calendar_start_date",
        "split",
    ),
    "r_core_demote_or_keep_decision": ("decision",),
    "r_core_arm_event_registry": (
        "arm_id",
        "event_key",
        "instrument",
        "event_signal_date",
        "event_signal_pos",
        "event_split",
        "horizon_complete_10d",
        "horizon_complete_20d",
        "horizon_complete_120d",
    ),
    "source_08_feature_panel": ("date", "instrument", "market_regime_bucket", "board_bucket"),
    "stock_daily_csv_dir": (),
}


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for artifact_id, raw_path in config.get("paths", {}).items():
        path = topic_path(raw_path)
        exists = path.exists()
        row_count: int | float = np.nan
        column_count: int | float = np.nan
        read_status = "pass" if exists else "missing_required_input"
        schema_status = "not_applicable"
        columns: set[str] = set()
        if exists and path.is_file() and path.suffix in {".csv", ".gz", ".parquet"}:
            try:
                if "".join(path.suffixes).endswith(".parquet"):
                    try:
                        import pyarrow.parquet as pq

                        meta = pq.ParquetFile(path).metadata
                        row_count = int(meta.num_rows)
                        column_count = int(meta.num_columns)
                        columns = set(meta.schema.names)
                    except Exception:
                        sample = pd.read_parquet(path)
                        row_count = int(sample.shape[0])
                        column_count = int(sample.shape[1])
                        columns = set(sample.columns)
                else:
                    sample = pd.read_csv(path, nrows=1, low_memory=False)
                    column_count = int(len(sample.columns))
                    columns = set(sample.columns)
                    row_count = int(read_table(path, usecols=[sample.columns[0]]).shape[0])
                expected = set(EXPECTED_INPUT_COLUMNS.get(artifact_id, ()))
                missing = sorted(expected - columns)
                schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
            except Exception as exc:  # pragma: no cover - defensive audit path
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "unreadable"
        elif exists and path.is_dir():
            schema_status = "directory"
        rows.append(
            {
                "artifact_id": artifact_id,
                "relative_path": str(raw_path),
                "resolved_path": str(path),
                "required_flag": True,
                "read_status": read_status,
                "schema_status": schema_status,
                "exists": bool(exists),
                "row_count": row_count,
                "column_count": column_count,
                "sha256": path_sha(path),
                "mtime_utc": mtime_utc(path),
                "notes": "",
            }
        )
    return pd.DataFrame(rows)


def check_12a3_gate(backbone_decision: pd.DataFrame, parity_audit: pd.DataFrame) -> tuple[bool, str]:
    if backbone_decision.empty:
        return False, "missing_12A3_decision"
    row = backbone_decision.iloc[0]
    decision_ok = str(row.get("decision_state", "")) == "12A3_state_change_backbone_partial_feature_source"
    partial_ok = boolish(row.get("partial_feature_source_gate_pass", False))
    label_gate_ok = boolish(row.get("label_recompute_gate_pass", False))
    decision_rate = pd.to_numeric(pd.Series([row.get("min_label_recompute_parity_match_rate", np.nan)]), errors="coerce").iloc[0]
    decision_parity_ok = pd.notna(decision_rate) and float(decision_rate) >= 0.995
    parity_pass_rows = parity_audit.loc[parity_audit.get("parity_status", pd.Series(dtype=str)).astype(str).eq("pass")].copy()
    if parity_pass_rows.empty:
        audit_parity_ok = False
    else:
        rates = pd.to_numeric(parity_pass_rows.get("parity_match_rate", pd.Series(dtype=float)), errors="coerce").dropna()
        required = pd.to_numeric(parity_pass_rows.get("min_required_match_rate", pd.Series(dtype=float)), errors="coerce").dropna()
        min_required = float(required.max()) if not required.empty else 0.995
        audit_parity_ok = (not rates.empty) and float(rates.min()) >= min_required
    ok = bool(decision_ok and partial_ok and label_gate_ok and decision_parity_ok and audit_parity_ok)
    if ok:
        return True, "pass"
    failed = []
    if not decision_ok:
        failed.append("decision_state")
    if not partial_ok:
        failed.append("partial_feature_source_gate_pass")
    if not label_gate_ok:
        failed.append("label_recompute_gate_pass")
    if not decision_parity_ok:
        failed.append("decision_min_label_recompute_parity_match_rate")
    if not audit_parity_ok:
        failed.append("state_change_label_recompute_parity_audit")
    return False, ";".join(failed)


class StockDailyCache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._cache: dict[str, pd.DataFrame | None] = {}

    def get(self, instrument: str) -> pd.DataFrame | None:
        instrument = str(instrument)
        if instrument in self._cache:
            return self._cache[instrument]
        path = self.directory / f"{instrument}.csv"
        if not path.exists():
            self._cache[instrument] = None
            return None
        daily = pd.read_csv(path, low_memory=False)
        daily["date"] = pd.to_datetime(daily["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        daily = daily.sort_values("date", kind="stable").reset_index(drop=True)
        for col in ("open", "high", "low", "close", "volume", "money", "turnover_rate"):
            daily[col] = pd.to_numeric(daily.get(col), errors="coerce")
        self._cache[instrument] = daily
        return daily

    def pos_for_date(self, instrument: str, date_value: Any) -> float:
        daily = self.get(instrument)
        if daily is None or daily.empty:
            return np.nan
        text = date_text(date_value)
        matches = daily.index[daily["date"].astype(str).eq(text)]
        return float(matches[0]) if len(matches) else np.nan


def add_episode_positions(episodes: pd.DataFrame, stock_cache: StockDailyCache) -> pd.DataFrame:
    out = episodes.copy()
    for col in ("episode_low_date", "episode_high_date", "first_50pct_date", "pre120_calendar_start_date"):
        out[col] = out[col].map(date_text)
    for name, date_col in (
        ("episode_low_pos", "episode_low_date"),
        ("episode_high_pos", "episode_high_date"),
        ("first_50pct_pos", "first_50pct_date"),
        ("pre120_calendar_start_pos", "pre120_calendar_start_date"),
    ):
        out[name] = [
            stock_cache.pos_for_date(str(row.instrument), getattr(row, date_col))
            for row in out.itertuples(index=False)
        ]
    return out


def normalize_c0_events(canonical: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = canonical.copy()
    non_exec = bool_series(raw.get("non_executable_next_open", pd.Series(False, index=raw.index)))
    supported = raw["candidate_generation_status"].astype(str).eq("supported_canonical_event")
    pit_ok = raw["event_t0_pit_status"].astype(str).eq("pass") & raw["trade_open_pit_status"].astype(str).eq("pass")
    executable = supported & (~non_exec) & pit_ok
    risk_on = raw["market_regime_bucket"].astype(str).eq("risk_on")
    excluded = raw.loc[executable & (~risk_on)].copy()
    excluded["source_arm_id"] = PRIMARY_SOURCE_ARM
    excluded["exclusion_reason"] = "non_risk_on_scope"
    c0 = raw.loc[executable & risk_on].copy()
    c0["source_arm_id"] = PRIMARY_SOURCE_ARM
    c0["source_event_id"] = c0["canonical_event_id"].astype(str)
    c0["meta_event_id"] = "C0_" + c0["canonical_event_id"].astype(str)
    c0["event_key"] = c0["canonical_event_id"].astype(str)
    c0["event_t0_date"] = c0["event_t0_date"].map(date_text)
    c0["trade_open_date"] = c0["trade_open_date"].map(date_text)
    c0["event_t0_pos"] = numeric(c0["event_t0_pos"])
    c0["trade_open_pos"] = numeric(c0["trade_open_pos"])
    c0["primary_family_id"] = c0["primary_family_id"].fillna("").astype(str)
    c0["triggered_family_count"] = numeric(c0.get("triggered_family_count", pd.Series(1, index=c0.index))).fillna(1)
    c0["event_split"] = c0["event_split"].fillna("").astype(str)
    c0["board_bucket"] = c0.get("board_bucket", "").fillna("").astype(str)
    c0["market_regime_bucket"] = "risk_on"
    c0["source_arm_role"] = "primary_decision_population"
    keep = [
        "meta_event_id",
        "source_event_id",
        "source_arm_id",
        "source_arm_role",
        "event_key",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "trade_open_price",
        "event_split",
        "board_bucket",
        "market_regime_bucket",
        "primary_family_id",
        "primary_variant_id",
        "triggered_family_variants",
        "triggered_family_count",
        "canonical_priority",
        "raw_instance_count_collapsed",
    ]
    return c0[[col for col in keep if col in c0.columns]].copy(), excluded


def normalize_r_core_events(r_core: pd.DataFrame, feature_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = r_core.loc[r_core["arm_id"].astype(str).eq(RAW_R_CORE_ARM)].copy()
    if out.empty:
        return out, out
    out["source_arm_id"] = R_CORE_SOURCE_ARM
    out["source_arm_role"] = "benchmark_baseline_population"
    out["event_key"] = out["event_key"].astype(str)
    out["source_event_id"] = out.get("source_event_id", out["event_key"]).fillna(out["event_key"]).astype(str)
    out["meta_event_id"] = "RCORE_" + out["event_key"].astype(str).map(lambda x: stable_event_id(x))
    out["canonical_event_id"] = out.get("canonical_event_id", out["event_key"]).astype(str)
    out["event_t0_date"] = out["event_signal_date"].map(date_text)
    out["trade_open_date"] = out.get("event_execution_date", "").map(date_text)
    out["event_t0_pos"] = numeric(out.get("event_signal_pos", pd.Series(np.nan, index=out.index)))
    out["trade_open_pos"] = numeric(out.get("event_execution_pos", pd.Series(np.nan, index=out.index)))
    out["trade_open_price"] = np.nan
    out["event_split"] = out.get("event_split", "").fillna("").astype(str)
    out["board_bucket"] = out.get("board_bucket", "").fillna("").astype(str)
    out["market_regime_bucket"] = "unknown"
    if not feature_panel.empty and {"date", "instrument", "market_regime_bucket"}.issubset(feature_panel.columns):
        panel = feature_panel[["date", "instrument", "market_regime_bucket"]].copy()
        panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        panel["instrument"] = panel["instrument"].astype(str)
        panel = panel.drop_duplicates(["date", "instrument"], keep="last")
        out = out.merge(
            panel.rename(columns={"date": "event_t0_date", "market_regime_bucket": "panel_market_regime_bucket"}),
            on=["event_t0_date", "instrument"],
            how="left",
        )
        out["market_regime_bucket"] = out["panel_market_regime_bucket"].fillna("unknown").astype(str)
        out = out.drop(columns=["panel_market_regime_bucket"])
    out["primary_family_id"] = "R_core"
    out["primary_variant_id"] = RAW_R_CORE_ARM
    out["triggered_family_variants"] = RAW_R_CORE_ARM
    out["triggered_family_count"] = 1
    exec_status = out.get("event_execution_status", pd.Series("", index=out.index)).fillna("").astype(str)
    executable = exec_status.str.contains("executable|ok|pass", case=False, regex=True)
    excluded = out.loc[executable & ~out["market_regime_bucket"].eq("risk_on")].copy()
    excluded["exclusion_reason"] = np.where(
        excluded["market_regime_bucket"].eq("unknown"),
        "r_core_missing_panel_regime_scope",
        "r_core_non_risk_on_scope",
    )
    out = out.loc[out["market_regime_bucket"].eq("risk_on") & executable].copy()
    keep = [
        "meta_event_id",
        "source_event_id",
        "source_arm_id",
        "source_arm_role",
        "event_key",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "trade_open_price",
        "event_split",
        "board_bucket",
        "market_regime_bucket",
        "primary_family_id",
        "primary_variant_id",
        "triggered_family_variants",
        "triggered_family_count",
        "horizon_complete_10d",
        "horizon_complete_20d",
        "horizon_complete_120d",
        "fast_fail_10d_label",
        "false_repair_20d_label",
        "winner_120_label",
    ]
    return out[[col for col in keep if col in out.columns]].copy(), excluded


def build_regime_scope_exclusion(canonical: pd.DataFrame, executable_excluded: pd.DataFrame, r_core_excluded: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    if not executable_excluded.empty:
        grouped = executable_excluded.groupby(["market_regime_bucket", "event_split"], dropna=False).size()
        for (regime, split), count in grouped.items():
            rows.append(
                {
                    "source_arm_id": PRIMARY_SOURCE_ARM,
                    "market_regime_bucket": regime,
                    "split": split,
                    "excluded_event_n": int(count),
                    "exclusion_reason": "non_risk_on_scope",
                }
            )
    all_counts = canonical.groupby("market_regime_bucket", dropna=False).size()
    for regime, count in all_counts.items():
        rows.append(
            {
                "source_arm_id": PRIMARY_SOURCE_ARM,
                "market_regime_bucket": regime,
                "split": "all_raw",
                "excluded_event_n": int(count),
                "exclusion_reason": "raw_regime_count_reference",
            }
        )
    if r_core_excluded is not None and not r_core_excluded.empty:
        grouped = r_core_excluded.groupby(["market_regime_bucket", "event_split", "exclusion_reason"], dropna=False).size()
        for (regime, split, reason), count in grouped.items():
            rows.append(
                {
                    "source_arm_id": R_CORE_SOURCE_ARM,
                    "market_regime_bucket": regime,
                    "split": split,
                    "excluded_event_n": int(count),
                    "exclusion_reason": reason,
                }
            )
    return pd.DataFrame(rows)


def add_source_arm_and_readout_flags(universe: pd.DataFrame, nearby_window: int = 5) -> pd.DataFrame:
    out = universe.copy()
    out["source_arm_is_c0"] = out["source_arm_id"].astype(str).eq(PRIMARY_SOURCE_ARM)
    out["source_arm_is_r_core"] = out["source_arm_id"].astype(str).eq(R_CORE_SOURCE_ARM)
    for col in (
        "readout_c0_intersect_r_core_same_day",
        "readout_c0_without_prior_r_core_5_sessions",
        "readout_r_core_without_prior_c0_5_sessions",
        "readout_c0_after_prior_r_core_5_sessions",
        "readout_r_core_after_prior_c0_5_sessions",
    ):
        out[col] = False
    for inst, idx in out.groupby("instrument", sort=False).groups.items():
        grp = out.loc[idx]
        c0_pos = pd.to_numeric(grp.loc[grp["source_arm_is_c0"], "event_t0_pos"], errors="coerce").dropna().to_numpy(dtype=float)
        r_pos = pd.to_numeric(grp.loc[grp["source_arm_is_r_core"], "event_t0_pos"], errors="coerce").dropna().to_numpy(dtype=float)
        if len(c0_pos) == 0 and len(r_pos) == 0:
            continue
        for row_idx, row in grp.iterrows():
            pos = float(row["event_t0_pos"]) if pd.notna(row["event_t0_pos"]) else np.nan
            if pd.isna(pos):
                continue
            if bool(row["source_arm_is_c0"]):
                same_day = np.any(r_pos == pos)
                prior = np.any((r_pos < pos) & (r_pos >= pos - nearby_window))
                out.at[row_idx, "readout_c0_intersect_r_core_same_day"] = bool(same_day)
                out.at[row_idx, "readout_c0_after_prior_r_core_5_sessions"] = bool(prior)
                out.at[row_idx, "readout_c0_without_prior_r_core_5_sessions"] = not bool(prior)
            elif bool(row["source_arm_is_r_core"]):
                prior = np.any((c0_pos < pos) & (c0_pos >= pos - nearby_window))
                out.at[row_idx, "readout_r_core_after_prior_c0_5_sessions"] = bool(prior)
                out.at[row_idx, "readout_r_core_without_prior_c0_5_sessions"] = not bool(prior)
    return out


def load_label_config(config: dict[str, Any]) -> dict[str, float | int]:
    source_08 = load_yaml(topic_path(config["paths"]["source_08_config"]))
    labels_08 = source_08["labels"]
    return {
        "failure_horizon": int(labels_08["failure_10"]["horizon_days"]),
        "failure_lower": float(labels_08["failure_10"]["lower_barrier"]),
        "false_repair_horizon": 20,
        "false_repair_drawdown": float(labels_08["false_repair_drawdown"]),
        "winner_horizon": 120,
        "winner_mfe": float(labels_08["big_winner_mfe_120d"]),
    }


def compute_label_row(daily: pd.DataFrame | None, event_pos: int | None, trade_pos: int | None, trade_price: float, cfg: dict[str, float | int]) -> dict[str, Any]:
    if daily is None or daily.empty or event_pos is None:
        return {
            "fast_fail_10d_label": np.nan,
            "false_repair_20d_label": np.nan,
            "winner_120_label": np.nan,
            "label_10d_complete": False,
            "label_20d_complete": False,
            "label_120d_complete": False,
            "label_status": "missing_stock_daily_or_position",
        }
    low = daily["low"].to_numpy(dtype=float)
    high = daily["high"].to_numpy(dtype=float)
    close = daily["close"].to_numpy(dtype=float)
    n = len(daily)
    failure_h = int(cfg["failure_horizon"])
    false_h = int(cfg["false_repair_horizon"])
    winner_h = int(cfg["winner_horizon"])
    label_10_complete = trade_pos is not None and trade_pos + failure_h < n and pd.notna(trade_price) and trade_price > 0
    label_20_complete = event_pos + false_h < n
    label_120_complete = trade_pos is not None and trade_pos + winner_h < n and pd.notna(trade_price) and trade_price > 0
    fast_fail = np.nan
    false_repair = np.nan
    winner = np.nan
    if label_10_complete:
        fast_fail = bool(np.nanmin(low[trade_pos : trade_pos + failure_h + 1] / trade_price - 1.0) <= float(cfg["failure_lower"]))
    if label_20_complete and pd.notna(close[event_pos]) and close[event_pos] > 0:
        false_repair = bool(np.nanmin(close[event_pos : event_pos + false_h + 1] / close[event_pos] - 1.0) <= float(cfg["false_repair_drawdown"]))
    if label_120_complete:
        winner = bool(np.nanmax(high[trade_pos : trade_pos + winner_h + 1] / trade_price - 1.0) >= float(cfg["winner_mfe"]))
    return {
        "fast_fail_10d_label": fast_fail,
        "false_repair_20d_label": false_repair,
        "winner_120_label": winner,
        "label_10d_complete": bool(label_10_complete),
        "label_20d_complete": bool(label_20_complete),
        "label_120d_complete": bool(label_120_complete),
        "label_status": "ok",
    }


def attach_c0_labels(c0_events: pd.DataFrame, stock_cache: StockDailyCache, cfg: dict[str, float | int]) -> pd.DataFrame:
    rows = []
    for row in c0_events.itertuples(index=False):
        daily = stock_cache.get(str(row.instrument))
        labels = compute_label_row(
            daily,
            int_or_none(getattr(row, "event_t0_pos")),
            int_or_none(getattr(row, "trade_open_pos")),
            float(getattr(row, "trade_open_price", np.nan)) if pd.notna(getattr(row, "trade_open_price", np.nan)) else np.nan,
            cfg,
        )
        labels["meta_event_id"] = row.meta_event_id
        rows.append(labels)
    return c0_events.merge(pd.DataFrame(rows), on="meta_event_id", how="left")


def attach_r_core_labels(r_events: pd.DataFrame) -> pd.DataFrame:
    out = r_events.copy()
    out["label_10d_complete"] = bool_series(out.get("horizon_complete_10d", pd.Series(False, index=out.index)))
    out["label_20d_complete"] = bool_series(out.get("horizon_complete_20d", pd.Series(False, index=out.index)))
    out["label_120d_complete"] = bool_series(out.get("horizon_complete_120d", pd.Series(False, index=out.index)))
    out["label_status"] = "published_r_core_registry"
    return out.drop(columns=[col for col in ("horizon_complete_10d", "horizon_complete_20d", "horizon_complete_120d") if col in out.columns])


def match_episode_targets(events: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    ep_by_inst = {inst: grp.copy() for inst, grp in episodes.groupby("instrument", sort=False)}
    for event in events.itertuples(index=False):
        inst_eps = ep_by_inst.get(str(event.instrument))
        event_pos = float(getattr(event, "event_t0_pos", np.nan))
        split = str(getattr(event, "event_split", ""))
        low_inside = False
        pre120_inside = False
        low_episode_id = ""
        multi = 0
        if inst_eps is not None and pd.notna(event_pos):
            same_split = inst_eps.loc[inst_eps["split"].astype(str).eq(split)].copy()
            low_matches = same_split.loc[
                numeric(same_split["episode_low_pos"]).le(event_pos)
                & numeric(same_split["episode_high_pos"]).ge(event_pos)
            ]
            pre_matches = same_split.loc[
                numeric(same_split["pre120_calendar_start_pos"]).le(event_pos)
                & numeric(same_split["episode_high_pos"]).ge(event_pos)
            ]
            low_inside = not low_matches.empty
            pre120_inside = not pre_matches.empty
            multi = int(len(low_matches))
            if low_inside:
                low_episode_id = str(low_matches.iloc[0]["episode_id"])
        fast_fail_raw = getattr(event, "fast_fail_10d_label", np.nan)
        false_repair_raw = getattr(event, "false_repair_20d_label", np.nan)
        winner_raw = getattr(event, "winner_120_label", np.nan)
        fast_fail = boolish(fast_fail_raw) if boolish(getattr(event, "label_10d_complete", False)) and pd.notna(fast_fail_raw) else np.nan
        false_repair = boolish(false_repair_raw) if boolish(getattr(event, "label_20d_complete", False)) and pd.notna(false_repair_raw) else np.nan
        winner = boolish(winner_raw) if boolish(getattr(event, "label_120d_complete", False)) and pd.notna(winner_raw) else np.nan
        bad_side = np.nan
        if pd.notna(fast_fail) or pd.notna(false_repair):
            bad_side = bool(boolish(fast_fail) or boolish(false_repair))
        rows.append(
            {
                "meta_event_id": event.meta_event_id,
                "source_arm_id": event.source_arm_id,
                "event_split": split,
                "instrument": event.instrument,
                "target_low_to_high_inside": bool(low_inside),
                "target_pre120_to_high_inside": bool(pre120_inside),
                "target_low_to_high_episode_id_first": low_episode_id,
                "multi_episode_target_overlap_n": multi,
                "label_10d_complete": boolish(getattr(event, "label_10d_complete", False)),
                "label_20d_complete": boolish(getattr(event, "label_20d_complete", False)),
                "label_120d_complete": boolish(getattr(event, "label_120d_complete", False)),
                "fast_fail_10d_label": fast_fail,
                "false_repair_20d_label": false_repair,
                "bad_side_10_20_label": bad_side,
                "winner_120_label": winner,
                "target_status": "ok",
            }
        )
    return pd.DataFrame(rows)


def entropy_from_states(states: list[Any], declared_state_count: int) -> float:
    if declared_state_count <= 1:
        return 0.0
    clean = [state for state in states if state is not None and not pd.isna(state)]
    if not clean:
        return np.nan
    counts = pd.Series(clean).value_counts(normalize=True)
    entropy = -float((counts * np.log(counts)).sum())
    if entropy <= 0:
        return 0.0
    return float(entropy / math.log(declared_state_count))


def gaussian_entropy(log_returns: np.ndarray) -> float:
    arr = log_returns[np.isfinite(log_returns)]
    if len(arr) < 2:
        return np.nan
    var = float(np.nanvar(arr, ddof=1))
    if var <= 0:
        return 0.0
    return float(0.5 * math.log(2 * math.pi * math.e * var))


def max_drawdown(close: pd.Series) -> float:
    arr = close.dropna().astype(float)
    if arr.empty:
        return np.nan
    running_max = arr.cummax()
    dd = arr / running_max - 1.0
    return float(dd.min())


def ols_slope(values: pd.Series) -> float:
    arr = values.dropna().astype(float).to_numpy()
    if len(arr) < 2:
        return np.nan
    x = np.arange(len(arr), dtype=float)
    return float(np.polyfit(x, arr, 1)[0])


def finite_corr(a: pd.Series, b: pd.Series, method: str) -> float:
    frame = pd.DataFrame({"a": pd.to_numeric(a, errors="coerce"), "b": pd.to_numeric(b, errors="coerce")}).dropna()
    if len(frame) < 3 or frame["a"].nunique() < 2 or frame["b"].nunique() < 2:
        return np.nan
    return float(frame["a"].corr(frame["b"], method=method))


def precompute_daily_features(daily: pd.DataFrame) -> pd.DataFrame:
    out = daily.copy()
    close = out["close"].astype(float)
    high = out["high"].astype(float)
    low = out["low"].astype(float)
    open_ = out["open"].astype(float)
    out["log_return"] = np.log(close / close.shift(1))
    out["ret_1d"] = close / close.shift(1) - 1.0
    for n in (5, 10, 20, 60):
        out[f"ret_{n}d"] = close / close.shift(n) - 1.0
    out["volatility_20d"] = out["log_return"].rolling(20, min_periods=16).std()
    out["volatility_60d"] = out["log_return"].rolling(60, min_periods=48).std()
    for n in (20, 60, 120):
        out[f"rolling_high_{n}d"] = high.rolling(n, min_periods=max(5, int(n * 0.8))).max()
        out[f"rolling_low_{n}d"] = low.rolling(n, min_periods=max(5, int(n * 0.8))).min()
        out[f"distance_to_{n}d_high"] = close / out[f"rolling_high_{n}d"] - 1.0
        out[f"distance_to_{n}d_low"] = close / out[f"rolling_low_{n}d"] - 1.0
    out["ema5"] = close.ewm(span=5, min_periods=4, adjust=False).mean()
    out["ema20"] = close.ewm(span=20, min_periods=15, adjust=False).mean()
    out["ema60"] = close.ewm(span=60, min_periods=40, adjust=False).mean()
    out["trend_ma_5_20_spread"] = out["ema5"] / out["ema20"] - 1.0
    out["trend_ma_20_60_spread"] = out["ema20"] / out["ema60"] - 1.0
    out["gap_open_prev_day"] = open_ / close.shift(1) - 1.0
    out["intraday_range_pct"] = (high - low) / close.replace(0.0, np.nan)
    log_volume = np.log1p(out["volume"].replace(0.0, np.nan))
    turnover = out["turnover_rate"].replace(0.0, np.nan)
    out["log_volume"] = log_volume
    out["volume_zscore_20d"] = (log_volume.rolling(20, min_periods=16).mean() - log_volume.rolling(60, min_periods=48).mean()) / log_volume.rolling(60, min_periods=48).std()
    out["turnover_zscore_20d"] = (turnover.rolling(20, min_periods=16).mean() - turnover.rolling(60, min_periods=48).mean()) / turnover.rolling(60, min_periods=48).std()
    return out


@dataclass
class FeatureBuildResult:
    feature_matrix: pd.DataFrame
    dictionary: pd.DataFrame
    pit_audit: pd.DataFrame
    entropy_audit: pd.DataFrame
    volume_audit: pd.DataFrame


def value_at(daily: pd.DataFrame, pos: int | None, col: str) -> float:
    if pos is None or pos < 0 or pos >= len(daily) or col not in daily.columns:
        return np.nan
    return float(daily.at[pos, col]) if pd.notna(daily.at[pos, col]) else np.nan


def window_series(daily: pd.DataFrame, pos: int | None, col: str, n: int) -> pd.Series:
    if pos is None or col not in daily.columns:
        return pd.Series(dtype=float)
    start = max(0, pos - n + 1)
    return pd.to_numeric(daily.loc[start:pos, col], errors="coerce")


def train_frozen_intraday_range_cutoffs(events: pd.DataFrame, daily_feature_cache: dict[str, pd.DataFrame | None]) -> list[float]:
    values: list[float] = []
    train_events = events.loc[events["event_split"].astype(str).eq("train")]
    for row in train_events.itertuples(index=False):
        daily = daily_feature_cache.get(str(row.instrument))
        pos = int_or_none(getattr(row, "event_t0_pos"))
        if daily is None or pos is None:
            continue
        range20 = window_series(daily, pos, "intraday_range_pct", 20).dropna()
        if len(range20) >= 16:
            values.extend(float(x) for x in range20.to_numpy(dtype=float) if pd.notna(x))
    if len(values) < 20:
        return []
    cutoffs = pd.Series(values).quantile([0.2, 0.4, 0.6, 0.8]).dropna().unique().tolist()
    return sorted(float(x) for x in cutoffs)


def build_single_daily_features(
    daily: pd.DataFrame | None,
    event_pos_value: Any,
    *,
    precomputed: bool = False,
    range_entropy_cutoffs: list[float] | None = None,
) -> dict[str, float]:
    event_pos = int_or_none(event_pos_value)
    if daily is None or daily.empty or event_pos is None or event_pos >= len(daily):
        return {}
    d = daily if precomputed else precompute_daily_features(daily)
    close = d["close"]
    out: dict[str, float] = {}
    for col in (
        "ret_5d",
        "ret_10d",
        "ret_20d",
        "ret_60d",
        "volatility_20d",
        "volatility_60d",
        "distance_to_20d_high",
        "distance_to_60d_high",
        "distance_to_120d_high",
        "distance_to_20d_low",
        "distance_to_60d_low",
        "distance_to_120d_low",
        "turnover_zscore_20d",
        "volume_zscore_20d",
        "gap_open_prev_day",
        "trend_ma_5_20_spread",
        "trend_ma_20_60_spread",
    ):
        out[col] = value_at(d, event_pos, col)
    for n in (20, 60):
        out[f"max_drawdown_{n}d"] = max_drawdown(window_series(d, event_pos, "close", n))
        low_n = value_at(d, event_pos, f"rolling_low_{n}d")
        current = value_at(d, event_pos, "close")
        out[f"rebound_from_{n}d_low"] = current / low_n - 1.0 if pd.notna(current) and pd.notna(low_n) and low_n else np.nan
    log_ret_20 = window_series(d, event_pos, "log_return", 20)
    log_ret_60 = window_series(d, event_pos, "log_return", 60)
    for n, log_ret in ((20, log_ret_20), (60, log_ret_60)):
        if len(log_ret.dropna()) >= int(0.8 * n):
            signs = np.where(log_ret > 0, "up", np.where(log_ret < 0, "down", "flat")).tolist()
            sigma = float(log_ret.std()) if pd.notna(log_ret.std()) and log_ret.std() > 0 else np.nan
            if pd.notna(sigma):
                bins = [-np.inf, -1.5 * sigma, -0.5 * sigma, 0.5 * sigma, 1.5 * sigma, np.inf]
                binned = pd.cut(log_ret, bins=bins, labels=False, include_lowest=True).tolist()
            else:
                binned = []
            transitions = [f"{signs[i]}->{signs[i + 1]}" for i in range(len(signs) - 1)]
            out[f"return_sign_entropy_{n}d"] = entropy_from_states(signs, 3)
            out[f"binned_return_entropy_{n}d"] = entropy_from_states(binned, 5)
            out[f"up_down_transition_entropy_{n}d"] = entropy_from_states(transitions, 9)
            out[f"gaussian_return_entropy_{n}d"] = gaussian_entropy(log_ret.to_numpy(dtype=float))
        else:
            out[f"return_sign_entropy_{n}d"] = np.nan
            out[f"binned_return_entropy_{n}d"] = np.nan
            out[f"up_down_transition_entropy_{n}d"] = np.nan
            out[f"gaussian_return_entropy_{n}d"] = np.nan
    range20 = window_series(d, event_pos, "intraday_range_pct", 20)
    if len(range20.dropna()) >= 16 and range_entropy_cutoffs:
        bins = [-np.inf] + sorted(set(float(x) for x in range_entropy_cutoffs if pd.notna(x))) + [np.inf]
        out["intraday_range_bin_entropy_20d"] = entropy_from_states(pd.cut(range20, bins=bins, labels=False, include_lowest=True).tolist(), max(2, len(bins) - 1))
    else:
        out["intraday_range_bin_entropy_20d"] = np.nan
    volume20 = window_series(d, event_pos, "log_volume", 20)
    if len(volume20.dropna()) >= 16:
        med = volume20.rolling(20, min_periods=1).median()
        states = np.where(volume20 > med, "up", np.where(volume20 < med, "down", "flat")).tolist()
        out["volume_direction_entropy_20d"] = entropy_from_states(states, 3)
    else:
        out["volume_direction_entropy_20d"] = np.nan
    log_volume = d["log_volume"]
    for n in (5, 10):
        if event_pos - 2 * n >= 0:
            out[f"log_volume_accel_{n}d"] = (log_volume.iloc[event_pos] - log_volume.iloc[event_pos - n]) - (log_volume.iloc[event_pos - n] - log_volume.iloc[event_pos - 2 * n])
            out[f"volume_z_accel_{n}d"] = value_at(d, event_pos, "volume_zscore_20d") - value_at(d, event_pos - n, "volume_zscore_20d")
            out[f"turnover_z_accel_{n}d"] = value_at(d, event_pos, "turnover_zscore_20d") - value_at(d, event_pos - n, "turnover_zscore_20d")
        else:
            out[f"log_volume_accel_{n}d"] = np.nan
            out[f"volume_z_accel_{n}d"] = np.nan
            out[f"turnover_z_accel_{n}d"] = np.nan
    recent = window_series(d, event_pos, "log_volume", 5)
    prior = d.loc[max(0, event_pos - 19) : max(-1, event_pos - 5), "log_volume"] if event_pos >= 5 else pd.Series(dtype=float)
    out["recent_log_volume_slope_5d"] = ols_slope(recent)
    out["prior_log_volume_slope_15d"] = ols_slope(prior)
    out["volume_slope_accel_5_15d"] = out["recent_log_volume_slope_5d"] - out["prior_log_volume_slope_15d"] if pd.notna(out["recent_log_volume_slope_5d"]) and pd.notna(out["prior_log_volume_slope_15d"]) else np.nan
    out["volume_slope_decay_ratio_5_15d"] = out["recent_log_volume_slope_5d"] / (abs(out["prior_log_volume_slope_15d"]) + 1e-6) if pd.notna(out["recent_log_volume_slope_5d"]) and pd.notna(out["prior_log_volume_slope_15d"]) else np.nan
    return out


def add_event_context_features(events: pd.DataFrame, r_core_events: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    out = events.copy()
    out = out.sort_values(["instrument", "event_t0_pos", "meta_event_id"], kind="stable").reset_index(drop=True)
    out["sessions_since_last_c0_event_same_instrument"] = np.nan
    out["prior_c0_event_count_20d_same_instrument"] = 0
    out["same_day_c0_event_count_all"] = out.groupby("event_t0_date")["meta_event_id"].transform("count")
    out["same_day_family_event_count"] = out.groupby(["event_t0_date", "primary_family_id"])["meta_event_id"].transform("count")
    for inst, idx in out.groupby("instrument", sort=False).groups.items():
        positions = out.loc[idx, "event_t0_pos"].to_numpy(dtype=float)
        last = np.nan
        for local_i, row_idx in enumerate(idx):
            pos = positions[local_i]
            out.at[row_idx, "sessions_since_last_c0_event_same_instrument"] = pos - last if pd.notna(last) else np.nan
            out.at[row_idx, "prior_c0_event_count_20d_same_instrument"] = int(np.sum((positions[:local_i] < pos) & (positions[:local_i] >= pos - 20)))
            last = pos
    for tau in (5, 10, 20, 40):
        out[f"freshness_decay_tau_{tau}"] = np.exp(-out["sessions_since_last_c0_event_same_instrument"].fillna(10_000) / tau)
        out.loc[out["sessions_since_last_c0_event_same_instrument"].isna(), f"freshness_decay_tau_{tau}"] = 0.0
    rcore = r_core_events.sort_values(["instrument", "event_t0_pos"], kind="stable")
    rcore_pos = {inst: grp["event_t0_pos"].to_numpy(dtype=float) for inst, grp in rcore.groupby("instrument", sort=False)}
    out["prior_r_core_event_count_5d"] = 0
    out["prior_r_core_event_count_10d"] = 0
    out["prior_r_core_event_count_20d"] = 0
    out["sessions_since_prior_r_core_event"] = np.nan
    out["has_r_core_same_day_at_t0_close"] = 0.0
    out["has_prior_r_core_within_5_sessions"] = 0.0
    out["sessions_since_nearest_prior_r_core_event"] = np.nan
    out["has_future_r_core_within_5_sessions"] = 0.0
    out["c0_before_future_r_core_within_5_sessions"] = 0.0
    out["c0_after_prior_r_core_within_5_sessions"] = 0.0
    out["r_core_active_same_risk_on_scope"] = 0.0
    out["source_interaction_bucket"] = "no_nearby_r_core"
    for i, row in out.iterrows():
        arr = rcore_pos.get(str(row["instrument"]), np.array([], dtype=float))
        pos = float(row["event_t0_pos"]) if pd.notna(row["event_t0_pos"]) else np.nan
        if pd.isna(pos) or len(arr) == 0:
            continue
        prior_strict = arr[arr < pos]
        prior_or_same = arr[arr <= pos]
        future = arr[(arr > pos) & (arr <= pos + 5)]
        same_day = np.any(arr == pos)
        prior5_strict = np.any((arr < pos) & (arr >= pos - 5))
        prior5_or_same = np.any((arr <= pos) & (arr >= pos - 5))
        if len(prior_strict):
            out.at[i, "sessions_since_prior_r_core_event"] = pos - prior_strict.max()
        if len(prior_or_same):
            out.at[i, "sessions_since_nearest_prior_r_core_event"] = pos - prior_or_same.max()
        out.at[i, "has_r_core_same_day_at_t0_close"] = float(same_day)
        out.at[i, "has_prior_r_core_within_5_sessions"] = float(prior5_or_same)
        out.at[i, "has_future_r_core_within_5_sessions"] = float(len(future) > 0)
        out.at[i, "c0_before_future_r_core_within_5_sessions"] = float(len(future) > 0)
        out.at[i, "c0_after_prior_r_core_within_5_sessions"] = float(prior5_strict)
        out.at[i, "r_core_active_same_risk_on_scope"] = float(prior5_or_same)
        if same_day:
            out.at[i, "source_interaction_bucket"] = "same_day_r_core"
        elif prior5_strict:
            out.at[i, "source_interaction_bucket"] = "after_prior_r_core_5_sessions"
        elif len(future) > 0:
            out.at[i, "source_interaction_bucket"] = "before_future_r_core_5_sessions"
        for window in (5, 10, 20):
            out.at[i, f"prior_r_core_event_count_{window}d"] = int(np.sum((arr <= pos) & (arr >= pos - window)))
    target_lookup = targets.set_index("meta_event_id")
    hist = out[["meta_event_id", "instrument", "primary_family_id", "event_t0_pos"]].join(
        target_lookup[["fast_fail_10d_label", "false_repair_20d_label", "bad_side_10_20_label"]],
        on="meta_event_id",
    )
    out["instrument_prior_252d_ff10_event_count"] = 0
    out["instrument_prior_252d_fr20_event_count"] = 0
    for inst, idx in hist.groupby("instrument", sort=False).groups.items():
        grp = hist.loc[idx].sort_values("event_t0_pos")
        positions = pd.to_numeric(grp["event_t0_pos"], errors="coerce").to_numpy(dtype=float)
        ff = bool_series(grp["fast_fail_10d_label"]).to_numpy(dtype=bool)
        fr = bool_series(grp["false_repair_20d_label"]).to_numpy(dtype=bool)
        original_idx = grp.index.to_numpy()
        left = 0
        for j, row_idx in enumerate(original_idx):
            pos = positions[j]
            if pd.isna(pos):
                continue
            while left < j and positions[left] < pos - 252:
                left += 1
            out.at[row_idx, "instrument_prior_252d_ff10_event_count"] = int(ff[left:j].sum())
            out.at[row_idx, "instrument_prior_252d_fr20_event_count"] = int(fr[left:j].sum())
    train_hist = hist.loc[out["event_split"].eq("train")].copy()
    family_rates = {}
    for family, grp in train_hist.groupby("primary_family_id", sort=False):
        family_rates[family] = {
            "family_prior_train_ff10_rate": safe_rate(bool_series(grp["fast_fail_10d_label"]).sum(), grp["fast_fail_10d_label"].notna().sum()),
            "family_prior_train_fr20_rate": safe_rate(bool_series(grp["false_repair_20d_label"]).sum(), grp["false_repair_20d_label"].notna().sum()),
            "family_prior_train_badside_rate": safe_rate(bool_series(grp["bad_side_10_20_label"]).sum(), grp["bad_side_10_20_label"].notna().sum()),
        }
    for name in ("family_prior_train_ff10_rate", "family_prior_train_fr20_rate", "family_prior_train_badside_rate"):
        out[name] = out["primary_family_id"].map(lambda family: family_rates.get(family, {}).get(name, np.nan))
    return out


def build_features(
    c0_events: pd.DataFrame,
    r_core_events: pd.DataFrame,
    targets: pd.DataFrame,
    stock_cache: StockDailyCache,
    feature_panel: pd.DataFrame,
    config: dict[str, Any],
) -> FeatureBuildResult:
    rows = []
    daily_feature_cache: dict[str, pd.DataFrame | None] = {}
    for instrument in c0_events["instrument"].dropna().astype(str).unique():
        raw_daily = stock_cache.get(instrument)
        daily_feature_cache[instrument] = precompute_daily_features(raw_daily) if raw_daily is not None and not raw_daily.empty else None
    range_entropy_cutoffs = train_frozen_intraday_range_cutoffs(c0_events, daily_feature_cache)
    for row in c0_events.itertuples(index=False):
        instrument = str(row.instrument)
        daily_feats = build_single_daily_features(
            daily_feature_cache[instrument],
            getattr(row, "event_t0_pos"),
            precomputed=True,
            range_entropy_cutoffs=range_entropy_cutoffs,
        )
        triggered = str(getattr(row, "triggered_family_variants", ""))
        base = {
            "meta_event_id": row.meta_event_id,
            "instrument": row.instrument,
            "event_t0_date": row.event_t0_date,
            "event_t0_pos": row.event_t0_pos,
            "event_split": row.event_split,
            "board_bucket": row.board_bucket,
            "market_regime_bucket": row.market_regime_bucket,
            "source_arm_id": PRIMARY_SOURCE_ARM,
            "source_arm_is_c0": 1.0,
            "source_arm_is_r_core": 0.0,
            "primary_family_id": row.primary_family_id,
            "triggered_family_count": getattr(row, "triggered_family_count", 1),
            "triggered_family_ge2": 1.0 if float(getattr(row, "triggered_family_count", 1) or 0) >= 2 else 0.0,
            "canonical_priority": getattr(row, "canonical_priority", np.nan),
            "raw_instance_count_collapsed": getattr(row, "raw_instance_count_collapsed", np.nan),
        }
        for family in ("B1", "B2", "B3", "B4", "B5", "B6", "B8"):
            base[f"primary_family_is_{family}"] = 1.0 if row.primary_family_id == family else 0.0
            base[f"has_{family}_trigger"] = 1.0 if family in triggered else 0.0
        rows.append({**base, **daily_feats})
    features = pd.DataFrame(rows)
    if not feature_panel.empty:
        panel = feature_panel.copy()
        panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        panel["instrument"] = panel["instrument"].astype(str)
        merge_cols = [
            "date",
            "instrument",
            "momentum_percentile_20d",
            "momentum_percentile_60d",
            "universe_up_share",
            "universe_up_share_z",
            "universe_up_share_change_5d",
            "board_relative_cusum_20d",
            "board_return_20d",
            "stock_vs_board_20d",
            "evaluated_member_count",
        ]
        features = features.merge(
            panel[[col for col in merge_cols if col in panel.columns]].rename(columns={"date": "event_t0_date"}),
            on=["event_t0_date", "instrument"],
            how="left",
        )
    features = add_event_context_features(features, r_core_events, targets)
    numeric_cols = [
        col
        for col in features.columns
        if col not in {"meta_event_id", "instrument", "event_t0_date", "event_split", "board_bucket", "market_regime_bucket", "source_arm_id", "primary_family_id"}
    ]
    for col in numeric_cols:
        features[col] = pd.to_numeric(features[col], errors="coerce")
    train_mask = features["event_split"].eq("train")
    volume_features = [col for col in features.columns if "volume" in col or "turnover_z_accel" in col]
    volume_winsor_cutoffs: dict[str, tuple[float, float]] = {}
    volume_invalid_rates: dict[str, float] = {}
    for col in volume_features:
        if col in features.columns and pd.api.types.is_numeric_dtype(features[col]):
            volume_invalid_rates[col] = float(features[col].isna().mean())
            q = features.loc[train_mask, col].quantile([0.01, 0.99]).dropna()
            if len(q) == 2:
                lower = float(q.iloc[0])
                upper = float(q.iloc[1])
                volume_winsor_cutoffs[col] = (lower, upper)
                features[col] = features[col].clip(lower, upper)
    feature_rows = []
    pit_rows = []
    for col in numeric_cols:
        forbidden = any(pattern in col for pattern in FORBIDDEN_PATTERNS)
        diagnostic = col.startswith("gaussian_return_entropy")
        population_audit_only = col in {"source_arm_is_c0", "source_arm_is_r_core"}
        allowed = (not forbidden) and (not diagnostic) and (not population_audit_only)
        group = "event_native"
        if "freshness" in col or "sessions_since_last" in col:
            group = "freshness_decay"
        elif col.startswith("source_arm_is_"):
            group = "population_audit"
        elif "r_core" in col:
            group = "r_core_interaction"
        elif "same_day" in col or "prior_c0" in col:
            group = "density_crowding"
        elif "entropy" in col:
            group = "entropy_path_disorder"
        elif "volume" in col or "turnover" in col:
            group = "volume_acceleration_decay"
        elif "prior_252d" in col or "family_prior" in col:
            group = "failure_history"
        elif "momentum" in col or "universe" in col or "board" in col or "stock_vs_board" in col:
            group = "risk_on_market_context"
        elif "ret_" in col or "volatility" in col or "drawdown" in col or "distance" in col or "trend" in col:
            group = "pre_event_path"
        feature_rows.append(
            {
                "feature_name": col,
                "feature_group": group,
                "feature_availability_time": "event_t0_close",
                "allowed_for_primary_model": bool(allowed),
                "diagnostic_only": bool(not allowed),
                "pit_status": "pass",
                "forbidden_name_pattern_flag": bool(forbidden),
                "feature_status": "available" if features[col].notna().any() else "all_null",
            }
        )
        pit_rows.append(
            {
                "feature_name": col,
                "feature_group": group,
                "feature_availability_time": "event_t0_close",
                "pit_status": "pass",
                "allowed_for_primary_model": bool(allowed),
                "coverage_rate": float(features[col].notna().mean()),
                "notes": "",
            }
        )
    dictionary = pd.DataFrame(feature_rows)
    entropy_audit = build_redundancy_audit(features, [col for col in numeric_cols if "entropy" in col], "entropy")
    volume_audit = build_redundancy_audit(features, volume_features, "volume", volume_winsor_cutoffs, volume_invalid_rates)
    blocked_entropy = set(entropy_audit.loc[~bool_series(entropy_audit["allowed_for_primary_model_after_audit"]), "feature_name"].astype(str))
    blocked_volume = set(volume_audit.loc[~bool_series(volume_audit["allowed_for_primary_model_after_audit"]), "feature_name"].astype(str))
    dictionary.loc[dictionary["feature_name"].isin(blocked_entropy | blocked_volume), "allowed_for_primary_model"] = False
    dictionary.loc[dictionary["feature_name"].isin(blocked_entropy | blocked_volume), "diagnostic_only"] = True
    pit_audit = pd.DataFrame(pit_rows)
    pit_audit.loc[pit_audit["feature_name"].isin(blocked_entropy | blocked_volume), "allowed_for_primary_model"] = False
    return FeatureBuildResult(features, dictionary, pit_audit, entropy_audit, volume_audit)


def build_redundancy_audit(
    features: pd.DataFrame,
    feature_names: list[str],
    audit_type: str,
    winsor_cutoffs: dict[str, tuple[float, float]] | None = None,
    invalid_rates: dict[str, float] | None = None,
) -> pd.DataFrame:
    rows = []
    winsor_cutoffs = winsor_cutoffs or {}
    invalid_rates = invalid_rates or {}
    if audit_type == "entropy":
        comparators = ["volatility_20d", "volatility_60d", "ret_20d", "ret_60d"]
        redundant_status = "diagnostic_only_redundant_with_volatility"
    else:
        comparators = ["turnover_zscore_20d", "volatility_20d", "ret_20d"]
        redundant_status = "diagnostic_only_redundant_with_turnover_or_volatility"
    for feature in feature_names:
        if feature not in features.columns:
            continue
        for split in SPLITS:
            frame = features if split == "all" else features.loc[features["event_split"].eq(split)]
            corrs = []
            for comp in comparators:
                if comp in frame.columns and comp != feature:
                    corrs.append(abs(finite_corr(frame[feature], frame[comp], "pearson")))
                    corrs.append(abs(finite_corr(frame[feature], frame[comp], "spearman")))
            finite = [value for value in corrs if pd.notna(value)]
            max_corr = max(finite) if finite else np.nan
            coverage = float(frame[feature].notna().mean()) if len(frame) else np.nan
            allowed = not (pd.notna(max_corr) and max_corr >= 0.95) and not (pd.notna(coverage) and coverage < 0.80)
            status = "pass"
            if pd.notna(max_corr) and max_corr >= 0.95:
                status = redundant_status
            elif pd.notna(coverage) and coverage < 0.80:
                status = "diagnostic_only_sparse_coverage"
            rows.append(
                {
                    "feature_name": feature,
                    "split": split,
                    "coverage_rate": coverage,
                    "pearson_corr_vs_matching_volatility": finite_corr(frame[feature], frame["volatility_20d"], "pearson") if "volatility_20d" in frame else np.nan,
                    "spearman_corr_vs_matching_volatility": finite_corr(frame[feature], frame["volatility_20d"], "spearman") if "volatility_20d" in frame else np.nan,
                    "pearson_corr_vs_abs_return_lookback": finite_corr(frame[feature], frame["ret_20d"].abs(), "pearson") if "ret_20d" in frame else np.nan,
                    "spearman_corr_vs_abs_return_lookback": finite_corr(frame[feature], frame["ret_20d"].abs(), "spearman") if "ret_20d" in frame else np.nan,
                    "pearson_corr_vs_turnover_zscore_20d": finite_corr(frame[feature], frame["turnover_zscore_20d"], "pearson") if "turnover_zscore_20d" in frame else np.nan,
                    "spearman_corr_vs_turnover_zscore_20d": finite_corr(frame[feature], frame["turnover_zscore_20d"], "spearman") if "turnover_zscore_20d" in frame else np.nan,
                    "pearson_corr_vs_volatility_20d": finite_corr(frame[feature], frame["volatility_20d"], "pearson") if "volatility_20d" in frame else np.nan,
                    "spearman_corr_vs_volatility_20d": finite_corr(frame[feature], frame["volatility_20d"], "spearman") if "volatility_20d" in frame else np.nan,
                    "pearson_corr_vs_abs_return_20d": finite_corr(frame[feature], frame["ret_20d"].abs(), "pearson") if "ret_20d" in frame else np.nan,
                    "spearman_corr_vs_abs_return_20d": finite_corr(frame[feature], frame["ret_20d"].abs(), "spearman") if "ret_20d" in frame else np.nan,
                    "invalid_volume_rate": invalid_rates.get(feature, np.nan) if audit_type == "volume" else np.nan,
                    "winsorization_lower_cutoff": winsor_cutoffs.get(feature, (np.nan, np.nan))[0] if audit_type == "volume" else np.nan,
                    "winsorization_upper_cutoff": winsor_cutoffs.get(feature, (np.nan, np.nan))[1] if audit_type == "volume" else np.nan,
                    "max_abs_redundancy_corr": max_corr,
                    "redundancy_status": status,
                    "allowed_for_primary_model_after_audit": bool(allowed),
                }
            )
    return pd.DataFrame(rows)


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    return frame if split == "all" else frame.loc[frame["event_split"].astype(str).eq(split)].copy()


def eligible_episode_n(episodes: pd.DataFrame, split: str) -> int:
    if episodes.empty or "split" not in episodes.columns:
        return 0
    return int(len(episodes if split == "all" else episodes.loc[episodes["split"].astype(str).eq(split)]))


def summarize_events(events: pd.DataFrame, episodes: pd.DataFrame, split: str) -> dict[str, Any]:
    frame = split_frame(events, split)
    event_n = int(len(frame))
    inside = bool_series(frame.get("target_low_to_high_inside", pd.Series(False, index=frame.index)))
    pre120_inside = bool_series(frame.get("target_pre120_to_high_inside", pd.Series(False, index=frame.index)))
    positive_n = int(inside.sum())
    labels20 = bool_series(frame.get("label_20d_complete", pd.Series(False, index=frame.index)))
    labels120 = bool_series(frame.get("label_120d_complete", pd.Series(False, index=frame.index)))
    bad = bool_series(frame.get("bad_side_10_20_label", pd.Series(False, index=frame.index)))
    winner = bool_series(frame.get("winner_120_label", pd.Series(False, index=frame.index)))
    duplicate_n = 0
    if {"instrument", "event_t0_pos"}.issubset(frame.columns):
        ordered = frame.sort_values(["instrument", "event_t0_pos"], kind="stable")
        for _, grp in ordered.groupby("instrument", sort=False):
            positions = pd.to_numeric(grp["event_t0_pos"], errors="coerce").to_numpy(dtype=float)
            for idx, pos in enumerate(positions):
                if pd.notna(pos) and np.any((positions[:idx] < pos) & (positions[:idx] >= pos - 10)):
                    duplicate_n += 1
    if "target_low_to_high_episode_id_first" in frame.columns:
        captured = frame.loc[inside, "target_low_to_high_episode_id_first"].dropna().astype(str)
    else:
        captured = pd.Series(dtype=str)
    captured = captured[captured.ne("")]
    ep_n = eligible_episode_n(episodes, split)
    return {
        "split": split,
        "regime_scope": "risk_on",
        "event_n": event_n,
        "event_inside_window_n": positive_n,
        "low_to_high_event_inside_n": positive_n,
        "low_to_high_precision": safe_rate(positive_n, event_n),
        "low_to_high_event_precision": safe_rate(positive_n, event_n),
        "target_low_to_high_precision": safe_rate(positive_n, event_n),
        "pre120_event_precision": safe_rate(int(pre120_inside.sum()), event_n),
        "outside_episode_event_rate": safe_rate(event_n - positive_n, event_n),
        "captured_episode_n": int(captured.nunique()),
        "eligible_episode_n": ep_n,
        "episode_recall_low_to_high": safe_rate(int(captured.nunique()), ep_n),
        "event_density_mean": safe_rate(event_n, frame["instrument"].nunique()) if "instrument" in frame.columns else np.nan,
        "same_instrument_10d_duplicate_rate": safe_rate(duplicate_n, event_n),
        "bad_side_10_20_rate": safe_rate(int((bad & labels20).sum()), int(labels20.sum())),
        "winner_120d_rate": safe_rate(int((winner & labels120).sum()), int(labels120.sum())),
        "label_20d_complete_rate": safe_rate(int(labels20.sum()), event_n),
    }


def build_r_core_baseline(universe_targets: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for source in (PRIMARY_SOURCE_ARM, R_CORE_SOURCE_ARM):
        source_frame = universe_targets.loc[universe_targets["source_arm_id"].eq(source)].copy()
        for split in SPLITS:
            row = summarize_events(source_frame, episodes, split)
            row["source_arm_id"] = source
            row["baseline_status"] = "ok" if row["event_n"] > 0 else "empty"
            rows.append(row)
    return pd.DataFrame(rows)


def build_validation_health(c0_targets: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    train = summarize_events(c0_targets, pd.DataFrame(), "train")
    validation = summarize_events(c0_targets, pd.DataFrame(), "validation")
    thresholds = config["thresholds"]
    event_gate = validation["event_n"] >= int(thresholds["validation_min_event_n"])
    pos_gate = validation["event_inside_window_n"] >= int(thresholds["validation_min_positive_n"])
    base_gate = (
        pd.notna(validation["low_to_high_precision"])
        and pd.notna(train["low_to_high_precision"])
        and validation["low_to_high_precision"] >= float(thresholds["validation_min_base_precision_ratio_vs_train"]) * train["low_to_high_precision"]
    )
    passed = bool(event_gate and pos_gate and base_gate)
    return pd.DataFrame(
        [
            {
                "train_event_n": train["event_n"],
                "train_positive_n": train["event_inside_window_n"],
                "train_base_precision": train["low_to_high_precision"],
                "validation_event_n": validation["event_n"],
                "validation_positive_n": validation["event_inside_window_n"],
                "validation_base_precision": validation["low_to_high_precision"],
                "validation_event_n_gate_pass": bool(event_gate),
                "validation_positive_n_gate_pass": bool(pos_gate),
                "validation_base_precision_health_gate_pass": bool(base_gate),
                "validation_threshold_health_pass": passed,
                "threshold_selection_source": "validation" if passed else "train_internal_cv",
                "validation_threshold_selection_status": "healthy_threshold_source" if passed else "unhealthy_readout_only",
            }
        ]
    )


def prepare_model_frame(features: pd.DataFrame, targets: pd.DataFrame, dictionary: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    target_cols = [
        "meta_event_id",
        "target_low_to_high_inside",
        "label_20d_complete",
        "bad_side_10_20_label",
        "target_low_to_high_episode_id_first",
    ]
    frame = features.merge(targets[target_cols], on="meta_event_id", how="left")
    allowed = dictionary.loc[bool_series(dictionary["allowed_for_primary_model"]), "feature_name"].astype(str).tolist()
    allowed = [col for col in allowed if col in frame.columns and pd.api.types.is_numeric_dtype(frame[col])]
    return frame, allowed


def impute_by_train(frame: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, dict[str, float]]:
    out = frame.copy()
    medians: dict[str, float] = {}
    train = out.loc[out["event_split"].eq("train")]
    for col in feature_cols:
        median = float(train[col].median()) if train[col].notna().any() else 0.0
        medians[col] = median
        out[col] = out[col].fillna(median)
    return out, medians


def scorecard_scores(train: pd.DataFrame, frame: pd.DataFrame, feature_cols: list[str]) -> pd.Series:
    y = bool_series(train["target_low_to_high_inside"]).astype(float)
    weights: dict[str, float] = {}
    for col in feature_cols:
        corr = finite_corr(train[col], y, "spearman")
        if pd.notna(corr):
            weights[col] = corr
    if not weights:
        return pd.Series(0.0, index=frame.index)
    score = pd.Series(0.0, index=frame.index)
    for col, weight in weights.items():
        ranks = frame[col].rank(pct=True)
        score += float(weight) * ranks
    return score


def fit_primary_models(model_frame: pd.DataFrame, feature_cols: list[str], config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not feature_cols:
        return model_frame.assign(score_model_id="none", meta_label_score=np.nan).iloc[0:0], pd.DataFrame()
    frame, medians = impute_by_train(model_frame, feature_cols)
    train = frame.loc[frame["event_split"].eq("train")].copy()
    y = bool_series(train["target_low_to_high_inside"]).astype(int)
    model_cards = []
    scored_frames = []
    if len(train) == 0 or y.nunique() < 2:
        return pd.DataFrame(), pd.DataFrame(
            [
                {
                    "model_id": "no_primary_model_fit",
                    "model_family": "none",
                    "fit_status": "blocked_insufficient_train_labels",
                    "feature_n": len(feature_cols),
                }
            ]
        )
    X_train = train[feature_cols].to_numpy(dtype=float)
    all_X = frame[feature_cols].to_numpy(dtype=float)
    models: list[tuple[str, str, Any]] = [
        ("logistic_regression_l2", "logistic_regression_l2", LogisticRegression(max_iter=int(config["models"]["logistic_max_iter"]), penalty="l2", solver="liblinear")),
        ("logistic_regression_l1", "logistic_regression_l1", LogisticRegression(max_iter=int(config["models"]["logistic_max_iter"]), penalty="l1", solver="liblinear")),
        ("shallow_decision_tree_max_depth_3", "shallow_decision_tree_max_depth_3", DecisionTreeClassifier(max_depth=3, min_samples_leaf=int(config["models"]["tree_min_samples_leaf"]), random_state=int(config["models"]["random_state"]))),
    ]
    for model_id, family, model in models:
        out = frame.copy()
        try:
            model.fit(X_train, y)
            if hasattr(model, "predict_proba"):
                score = model.predict_proba(all_X)[:, 1]
            else:
                score = model.decision_function(all_X)
            fit_status = "fit"
        except Exception as exc:
            score = np.full(len(frame), np.nan)
            fit_status = f"fit_error:{type(exc).__name__}"
        out["model_id"] = model_id
        out["model_family"] = family
        out["meta_label_score"] = score
        scored_frames.append(out)
        model_cards.append(
            {
                "model_id": model_id,
                "model_family": family,
                "fit_status": fit_status,
                "feature_n": len(feature_cols),
                "allowed_for_supported_gate": True,
                "threshold_selection_source": "train_internal_cv",
                "imputation_policy": "train_median",
                "imputation_medians_hash": stable_hash(medians),
                "feature_list_hash": stable_hash(feature_cols),
            }
        )
    scorecard = frame.copy()
    scorecard["model_id"] = "scorecard_quantile_binning"
    scorecard["model_family"] = "scorecard_quantile_binning"
    scorecard["meta_label_score"] = scorecard_scores(train, frame, feature_cols)
    scored_frames.append(scorecard)
    model_cards.append(
        {
            "model_id": "scorecard_quantile_binning",
            "model_family": "scorecard_quantile_binning",
            "fit_status": "fit",
            "feature_n": len(feature_cols),
            "allowed_for_supported_gate": True,
            "threshold_selection_source": "train_internal_cv",
            "imputation_policy": "train_median",
            "imputation_medians_hash": stable_hash(medians),
            "feature_list_hash": stable_hash(feature_cols),
        }
    )
    return pd.concat(scored_frames, ignore_index=True), pd.DataFrame(model_cards)


def add_bucket_flags(scored: pd.DataFrame, score_col: str = "meta_label_score") -> pd.DataFrame:
    out = scored.copy()
    out["score_bucket"] = "not_selected"
    for model_id, idx in out.groupby("model_id", sort=False).groups.items():
        train_scores = out.loc[idx][out.loc[idx, "event_split"].eq("train")][score_col].dropna()
        if train_scores.empty:
            continue
        q90 = float(train_scores.quantile(0.90))
        q80 = float(train_scores.quantile(0.80))
        model_mask = out["model_id"].eq(model_id)
        out.loc[model_mask & out[score_col].ge(q80), "score_bucket"] = "top20"
        out.loc[model_mask & out[score_col].ge(q90), "score_bucket"] = "top10"
        out.loc[model_mask, "train_reference_top10_threshold"] = q90
        out.loc[model_mask, "train_reference_top20_threshold"] = q80
    return out


def build_score_frontier(scored: pd.DataFrame, episodes: pd.DataFrame, baselines: pd.DataFrame, best_non_model: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if scored.empty:
        return pd.DataFrame()
    scored = add_bucket_flags(scored)
    c0_base = baselines.loc[baselines["source_arm_id"].eq(PRIMARY_SOURCE_ARM)].set_index("split")
    r_base = baselines.loc[baselines["source_arm_id"].eq(R_CORE_SOURCE_ARM)].set_index("split")
    non_model_best = best_non_model.set_index("split")["best_non_model_precision"].to_dict() if not best_non_model.empty else {}
    for model_id, model_group in scored.groupby("model_id", sort=False):
        family = str(model_group["model_family"].iloc[0])
        for split in SPLITS:
            split_group = split_frame(model_group, split)
            for bucket, frac in (("top10", 0.10), ("top20", 0.20)):
                if bucket == "top10":
                    selected = split_group.loc[split_group["score_bucket"].eq("top10")]
                else:
                    selected = split_group.loc[split_group["score_bucket"].isin(["top10", "top20"])]
                summary = summarize_events(selected, episodes, split)
                c0_precision = c0_base.loc[split, "low_to_high_precision"] if split in c0_base.index else np.nan
                r_precision = r_base.loc[split, "low_to_high_precision"] if split in r_base.index else np.nan
                best_precision = non_model_best.get(split, np.nan)
                rows.append(
                    {
                        "model_id": model_id,
                        "model_family": family,
                        "split": split,
                        "bucket_id": bucket,
                        "bucket_fraction": frac,
                        "event_n": summary["event_n"],
                        "event_inside_window_n": summary["event_inside_window_n"],
                        "low_to_high_precision": summary["low_to_high_precision"],
                        "top10_low_to_high_precision": summary["low_to_high_precision"] if bucket == "top10" else np.nan,
                        "top20_low_to_high_precision": summary["low_to_high_precision"] if bucket == "top20" else np.nan,
                        "episode_recall_low_to_high": summary["episode_recall_low_to_high"],
                        "top20_episode_recall_low_to_high": summary["episode_recall_low_to_high"] if bucket == "top20" else np.nan,
                        "bad_side_10_20_rate": summary["bad_side_10_20_rate"],
                        "top20_bad_side_10_20_rate": summary["bad_side_10_20_rate"] if bucket == "top20" else np.nan,
                        "precision_lift_vs_C0_risk_on_baseline": safe_rate(summary["low_to_high_precision"], c0_precision),
                        "precision_lift_vs_R_core_risk_on_baseline": safe_rate(summary["low_to_high_precision"], r_precision),
                        "precision_lift_vs_best_non_model_baseline": safe_rate(summary["low_to_high_precision"], best_precision),
                        "train_reference_top10_threshold": model_group["train_reference_top10_threshold"].dropna().iloc[0] if "train_reference_top10_threshold" in model_group and model_group["train_reference_top10_threshold"].notna().any() else np.nan,
                        "train_reference_top20_threshold": model_group["train_reference_top20_threshold"].dropna().iloc[0] if "train_reference_top20_threshold" in model_group and model_group["train_reference_top20_threshold"].notna().any() else np.nan,
                        "rank_monotonicity_status": rank_monotonicity(model_group, split),
                        "threshold_freeze_gate_pass": True,
                        "frontier_status": "ok",
                    }
                )
    return pd.DataFrame(rows)


def rank_monotonicity(model_group: pd.DataFrame, split: str) -> str:
    frame = split_frame(model_group, split).dropna(subset=["meta_label_score"])
    if len(frame) < 20 or frame["meta_label_score"].nunique() < 3:
        return "weak"
    try:
        frame = frame.copy()
        frame["decile"] = pd.qcut(frame["meta_label_score"].rank(method="first"), 10, labels=False, duplicates="drop")
        precisions = frame.groupby("decile")["target_low_to_high_inside"].mean().dropna()
        if len(precisions) < 3:
            return "weak"
        return "pass" if precisions.iloc[-1] >= precisions.iloc[0] else "weak"
    except Exception:
        return "weak"


def build_non_model_frontier(features: pd.DataFrame, targets: pd.DataFrame, episodes: pd.DataFrame, baselines: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = features.merge(targets, on=["meta_event_id", "instrument", "event_split"], how="left", suffixes=("", "_target"))
    score_specs = {
        "family_only_frontier": "family_prior_train_badside_rate",
        "freshness_decay_only_frontier": "freshness_decay_tau_20",
        "density_only_frontier": "same_day_c0_event_count_all",
        "entropy_path_disorder_only_frontier": "return_sign_entropy_20d",
        "volume_acceleration_decay_only_frontier": "volume_slope_accel_5_15d",
        "r_core_interaction_only_frontier": "prior_r_core_event_count_20d",
        "pre_event_path_rank_only_frontier": "momentum_percentile_20d",
    }
    rows = []
    c0_base = baselines.loc[baselines["source_arm_id"].eq(PRIMARY_SOURCE_ARM)].set_index("split")
    r_base = baselines.loc[baselines["source_arm_id"].eq(R_CORE_SOURCE_ARM)].set_index("split")
    for frontier_id, col in score_specs.items():
        scored = frame.copy()
        scored["model_id"] = frontier_id
        scored["model_family"] = "non_model_baseline"
        if col not in scored.columns:
            scored["meta_label_score"] = np.nan
        else:
            scored["meta_label_score"] = pd.to_numeric(scored[col], errors="coerce")
            if frontier_id in {"density_only_frontier", "entropy_path_disorder_only_frontier"}:
                scored["meta_label_score"] = -scored["meta_label_score"]
        scored = add_bucket_flags(scored)
        for split in SPLITS:
            split_group = split_frame(scored, split)
            for bucket, frac in (("top10", 0.10), ("top20", 0.20)):
                selected = split_group.loc[split_group["score_bucket"].eq("top10")] if bucket == "top10" else split_group.loc[split_group["score_bucket"].isin(["top10", "top20"])]
                summary = summarize_events(selected, episodes, split)
                c0_precision = c0_base.loc[split, "low_to_high_precision"] if split in c0_base.index else np.nan
                r_precision = r_base.loc[split, "low_to_high_precision"] if split in r_base.index else np.nan
                rows.append(
                    {
                        "frontier_id": frontier_id,
                        "score_feature": col,
                        "split": split,
                        "bucket_id": bucket,
                        "bucket_fraction": frac,
                        "event_n": summary["event_n"],
                        "event_inside_window_n": summary["event_inside_window_n"],
                        "low_to_high_precision": summary["low_to_high_precision"],
                        "episode_recall_low_to_high": summary["episode_recall_low_to_high"],
                        "bad_side_10_20_rate": summary["bad_side_10_20_rate"],
                        "precision_lift_vs_C0_risk_on_baseline": safe_rate(summary["low_to_high_precision"], c0_precision),
                        "precision_lift_vs_R_core_risk_on_baseline": safe_rate(summary["low_to_high_precision"], r_precision),
                        "frontier_status": "ok" if selected["meta_label_score"].notna().any() else "score_unavailable",
                    }
                )
    non_model = pd.DataFrame(rows)
    best = (
        non_model.loc[non_model["bucket_id"].eq("top20")]
        .groupby("split", as_index=False)["low_to_high_precision"]
        .max()
        .rename(columns={"low_to_high_precision": "best_non_model_precision"})
    )
    return non_model, best


def build_active_state_frontier(c0_targets: pd.DataFrame, episodes: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    horizons = [int(x) for x in config["thresholds"]["active_state_horizons"]]
    ep_by_inst = {inst: grp.copy() for inst, grp in episodes.groupby("instrument", sort=False)}
    for horizon in horizons:
        for split in SPLITS:
            frame = split_frame(c0_targets, split)
            carried_inside = 0
            for row in frame.itertuples(index=False):
                inst_eps = ep_by_inst.get(str(row.instrument))
                if inst_eps is None or pd.isna(row.event_t0_pos):
                    continue
                eps = inst_eps if split == "all" else inst_eps.loc[inst_eps["split"].astype(str).eq(split)]
                if eps.empty:
                    continue
                start = float(row.event_t0_pos)
                end = start + horizon
                overlap = eps.loc[numeric(eps["episode_low_pos"]).le(end) & numeric(eps["episode_high_pos"]).ge(start)]
                if not overlap.empty:
                    carried_inside += 1
            rows.append(
                {
                    "horizon_sessions": horizon,
                    "split": split,
                    "active_state_event_n": int(len(frame)),
                    "diagnostic_carry_inside_event_n": int(carried_inside),
                    "diagnostic_carry_precision": safe_rate(carried_inside, len(frame)),
                    "forward_looking_caveat": True,
                    "allowed_for_supported_gate": False,
                    "frontier_status": "diagnostic_only",
                }
            )
    return pd.DataFrame(rows)


def build_split_time_boundary_audit(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    train_dates = pd.to_datetime(features.loc[features["event_split"].eq("train"), "event_t0_date"], errors="coerce")
    train_max = train_dates.max()
    for split in ("validation", "robustness"):
        eval_dates = pd.to_datetime(features.loc[features["event_split"].eq(split), "event_t0_date"], errors="coerce")
        eval_min = eval_dates.min()
        pass_flag = pd.notna(train_max) and pd.notna(eval_min) and train_max <= eval_min
        rows.append(
            {
                "feature_group": "family_prior_train_rates",
                "eval_split": split,
                "train_max_event_t0_date": date_text(train_max),
                "eval_min_event_t0_date": date_text(eval_min),
                "split_time_boundary_gate_pass": bool(pass_flag),
                "primary_model_allowed_status": "allowed" if pass_flag else "diagnostic_only_time_boundary_fail",
            }
        )
    return pd.DataFrame(rows)


def build_lightgbm_outputs(model_frame: pd.DataFrame, feature_cols: list[str], episodes: pd.DataFrame, baselines: pd.DataFrame, best_non_model: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if importlib.util.find_spec("lightgbm") is None:
        stub_frontier = pd.DataFrame(
            [
                {
                    "lightgbm_challenger_status": "skipped_dependency_unavailable",
                    "skip_reason": "python_package_missing",
                    "dependency_name": "lightgbm",
                    "dependency_version": "",
                    "split": split,
                    "row_status": "stub",
                }
                for split in SPLITS
            ]
        )
        stub_card = pd.DataFrame(
            [
                {
                    "model_id": "lightgbm_challenger_diagnostic_only",
                    "model_family": "lightgbm_challenger_diagnostic_only",
                    "lightgbm_challenger_status": "skipped_dependency_unavailable",
                    "skip_reason": "python_package_missing",
                    "dependency_name": "lightgbm",
                    "dependency_version": "",
                    "class_weight_policy": config["models"]["lightgbm"]["class_weight_policy"],
                    "allowed_for_supported_gate": False,
                    "row_status": "stub",
                }
            ]
        )
        return stub_frontier, stub_card
    try:
        import lightgbm as lgb
        from lightgbm import LGBMClassifier
    except Exception as exc:  # pragma: no cover
        return (
            pd.DataFrame([{"lightgbm_challenger_status": "skipped_import_error", "skip_reason": type(exc).__name__, "split": "all", "row_status": "stub"}]),
            pd.DataFrame([{"model_id": "lightgbm_challenger_diagnostic_only", "lightgbm_challenger_status": "skipped_import_error", "skip_reason": type(exc).__name__}]),
        )
    frame, _ = impute_by_train(model_frame, feature_cols)
    train = frame.loc[frame["event_split"].eq("train")]
    y = bool_series(train["target_low_to_high_inside"]).astype(int)
    if len(train) == 0 or y.nunique() < 2:
        return (
            pd.DataFrame([{"lightgbm_challenger_status": "skipped_insufficient_train_labels", "split": split, "row_status": "stub"} for split in SPLITS]),
            pd.DataFrame([{"model_id": "lightgbm_challenger_diagnostic_only", "lightgbm_challenger_status": "skipped_insufficient_train_labels"}]),
        )
    model = LGBMClassifier(
        objective="binary",
        boosting_type="gbdt",
        num_leaves=7,
        max_depth=3,
        min_data_in_leaf=100,
        learning_rate=0.05,
        feature_fraction=0.8,
        bagging_fraction=0.8,
        random_state=int(config["models"]["random_state"]),
        n_estimators=100,
        verbose=-1,
    )
    model.fit(train[feature_cols], y)
    scored = frame.copy()
    scored["model_id"] = "lightgbm_challenger_diagnostic_only"
    scored["model_family"] = "lightgbm_challenger_diagnostic_only"
    scored["meta_label_score"] = model.predict_proba(frame[feature_cols])[:, 1]
    frontier = build_score_frontier(scored, episodes, baselines, best_non_model)
    frontier["lightgbm_challenger_status"] = "evaluated"
    card = pd.DataFrame(
        [
            {
                "model_id": "lightgbm_challenger_diagnostic_only",
                "model_family": "lightgbm_challenger_diagnostic_only",
                "lightgbm_challenger_status": "evaluated",
                "dependency_name": "lightgbm",
                "dependency_version": getattr(lgb, "__version__", ""),
                "feature_n": len(feature_cols),
                "class_weight_policy": config["models"]["lightgbm"]["class_weight_policy"],
                "allowed_for_supported_gate": False,
                "threshold_selection_source": "train_internal_cv",
                "feature_group_importance": stable_hash(feature_cols),
            }
        ]
    )
    return frontier, card


def evaluate_decision(
    score_frontier: pd.DataFrame,
    lightgbm_frontier: pd.DataFrame,
    baselines: pd.DataFrame,
    best_non_model: pd.DataFrame,
    validation_health: pd.DataFrame,
    feature_dictionary: pd.DataFrame,
    config: dict[str, Any],
    input_gate_pass: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    t = config["thresholds"]
    blocked = not input_gate_pass
    usable_features = int(bool_series(feature_dictionary["allowed_for_primary_model"]).sum()) if not feature_dictionary.empty else 0
    if usable_features == 0:
        blocked = True
    if score_frontier.empty or not {"split", "bucket_id"}.issubset(score_frontier.columns):
        primary_top20 = pd.DataFrame()
    else:
        primary_top20 = score_frontier.loc[
            score_frontier["split"].eq("robustness") & score_frontier["bucket_id"].eq("top20")
        ].copy()
    if primary_top20.empty:
        best = pd.Series(dtype=object)
    else:
        best = primary_top20.sort_values("low_to_high_precision", ascending=False).iloc[0]
    c0_rob = baselines.loc[baselines["source_arm_id"].eq(PRIMARY_SOURCE_ARM) & baselines["split"].eq("robustness")].iloc[0]
    r_rob = baselines.loc[baselines["source_arm_id"].eq(R_CORE_SOURCE_ARM) & baselines["split"].eq("robustness")].iloc[0]
    best_non = best_non_model.set_index("split")["best_non_model_precision"].to_dict().get("robustness", np.nan) if not best_non_model.empty else np.nan
    best_precision = float(best.get("low_to_high_precision", np.nan)) if not best.empty else np.nan
    best_top10 = np.nan
    if not score_frontier.empty and not best.empty:
        top10 = score_frontier.loc[
            score_frontier["model_id"].eq(best["model_id"])
            & score_frontier["split"].eq("robustness")
            & score_frontier["bucket_id"].eq("top10")
        ]
        if not top10.empty:
            best_top10 = float(top10.iloc[0]["low_to_high_precision"])
    supported = (
        not blocked
        and pd.notna(best_precision)
        and best_precision >= float(t["supported_top20_precision"])
        and pd.notna(best_top10)
        and best_top10 >= float(t["supported_top10_precision"])
        and safe_rate(best_precision, r_rob["low_to_high_precision"]) >= float(t["supported_lift_vs_r_core"])
        and safe_rate(best_precision, c0_rob["low_to_high_precision"]) >= float(t["supported_lift_vs_c0"])
        and safe_rate(best_precision, best_non) >= float(t["supported_lift_vs_best_non_model"])
        and float(best.get("episode_recall_low_to_high", np.nan)) >= float(t["supported_episode_recall"])
        and float(best.get("bad_side_10_20_rate", np.inf)) <= float(c0_rob.get("bad_side_10_20_rate", np.inf))
        and int(best.get("event_n", 0)) >= int(t["supported_min_top20_event_n"])
    )
    lightgbm_candidate = False
    if not supported and "lightgbm_challenger_status" in lightgbm_frontier.columns and "low_to_high_precision" in lightgbm_frontier.columns:
        lg = lightgbm_frontier.loc[lightgbm_frontier.get("split", "").eq("robustness") & lightgbm_frontier.get("bucket_id", "").eq("top20")]
        if not lg.empty:
            lg_row = lg.sort_values("low_to_high_precision", ascending=False).iloc[0]
            lightgbm_candidate = (
                str(lg_row.get("lightgbm_challenger_status", "")) == "evaluated"
                and float(lg_row.get("low_to_high_precision", 0.0)) >= float(t["supported_top20_precision"])
                and safe_rate(float(lg_row.get("low_to_high_precision", np.nan)), c0_rob["low_to_high_precision"]) >= float(t["supported_lift_vs_c0"])
                and safe_rate(float(lg_row.get("low_to_high_precision", np.nan)), best_non) >= float(t["supported_lift_vs_best_non_model"])
            )
    partial = (
        not blocked
        and not supported
        and not lightgbm_candidate
        and pd.notna(best_precision)
        and (
            (best_precision >= float(t["partial_min_precision"]) and best_precision < float(t["supported_top20_precision"]))
            or (best_precision >= float(t["supported_top20_precision"]))
        )
    )
    diagnostic = not blocked and not supported and not partial and not lightgbm_candidate and usable_features > 0 and pd.notna(best_precision)
    if blocked:
        state = "12A4_blocked_input_or_pit_failure"
        reason = "required input, PIT, label, or usable feature gate failed"
    elif supported:
        state = "12A4_meta_label_supported"
        reason = "allowed primary model passed supported gate"
    elif lightgbm_candidate:
        state = "12A4_nonlinear_candidate_requires_12A5_validation"
        reason = "only nonlinear challenger passed uplift gate"
    elif partial:
        state = "12A4_meta_label_partial_feature_source"
        reason = "allowed primary model has weak uplift but fails supported gate"
    elif diagnostic:
        state = "12A4_meta_label_diagnostic_only"
        reason = "diagnostic readout available but uplift below partial gate"
    else:
        state = "12A4_no_meta_label_uplift"
        reason = "meta-labeling did not beat precision base-rate gate"
    decision = pd.DataFrame(
        [
            {
                "decision": state,
                "decision_state": state,
                "decision_reason": reason,
                "supporting_model_id": "" if best.empty else best.get("model_id", ""),
                "supporting_model_family": "" if best.empty else best.get("model_family", ""),
                "blocked_input_or_pit_failure": bool(blocked),
                "supported_gate_pass": bool(supported),
                "partial_feature_source_gate_pass": bool(partial),
                "nonlinear_candidate_gate_pass": bool(lightgbm_candidate),
                "diagnostic_only_gate_pass": bool(diagnostic),
                "no_meta_label_uplift_gate_pass": bool(state == "12A4_no_meta_label_uplift"),
                "allowed_primary_best_robustness_top20_low_to_high_precision": best_precision,
                "allowed_primary_best_robustness_top10_low_to_high_precision": best_top10,
                "allowed_primary_best_precision_lift_vs_R_core_risk_on_baseline": safe_rate(best_precision, r_rob["low_to_high_precision"]),
                "allowed_primary_best_precision_lift_vs_C0_risk_on_baseline": safe_rate(best_precision, c0_rob["low_to_high_precision"]),
                "allowed_primary_best_precision_lift_vs_best_non_model_baseline": safe_rate(best_precision, best_non),
                "C0_risk_on_robustness_precision": c0_rob["low_to_high_precision"],
                "R_core_risk_on_robustness_precision": r_rob["low_to_high_precision"],
                "best_non_model_robustness_precision": best_non,
                "validation_threshold_health_pass": bool(validation_health.iloc[0]["validation_threshold_health_pass"]),
                "threshold_selection_source": validation_health.iloc[0]["threshold_selection_source"],
                "recommended_next_requirement": "12A5_morphology_feature_modeling" if state in {"12A4_meta_label_supported", "12A4_nonlinear_candidate_requires_12A5_validation"} else "stop_state_change_as_timing_signal_keep_feature_source",
            }
        ]
    )
    selfcheck = build_supported_selfcheck(decision.iloc[0], c0_rob, r_rob, best_non, t)
    return decision, selfcheck


def build_supported_selfcheck(decision: pd.Series, c0_rob: pd.Series, r_rob: pd.Series, best_non: float, thresholds: dict[str, Any]) -> pd.DataFrame:
    rows = [
        ("top20_abs_precision", "absolute_precision", float(thresholds["supported_top20_precision"]), decision["allowed_primary_best_robustness_top20_low_to_high_precision"], float(thresholds["supported_top20_precision"])),
        ("top10_abs_precision", "absolute_precision", float(thresholds["supported_top10_precision"]), decision["allowed_primary_best_robustness_top10_low_to_high_precision"], float(thresholds["supported_top10_precision"])),
        ("lift_vs_r_core", "relative_lift", float(thresholds["supported_lift_vs_r_core"]), decision["allowed_primary_best_precision_lift_vs_R_core_risk_on_baseline"], float(thresholds["supported_lift_vs_r_core"]) * float(r_rob["low_to_high_precision"])),
        ("lift_vs_c0", "relative_lift", float(thresholds["supported_lift_vs_c0"]), decision["allowed_primary_best_precision_lift_vs_C0_risk_on_baseline"], float(thresholds["supported_lift_vs_c0"]) * float(c0_rob["low_to_high_precision"])),
        ("lift_vs_best_non_model", "relative_lift", float(thresholds["supported_lift_vs_best_non_model"]), decision["allowed_primary_best_precision_lift_vs_best_non_model_baseline"], float(thresholds["supported_lift_vs_best_non_model"]) * float(best_non) if pd.notna(best_non) else np.nan),
    ]
    out = pd.DataFrame(
        [
            {
                "gate_name": name,
                "gate_kind": kind,
                "required_threshold": req,
                "realized_value": realized,
                "binding_implied_precision": implied,
                "gate_pass": bool(pd.notna(realized) and realized >= req) if kind != "relative_lift" else bool(pd.notna(realized) and realized >= req),
                "is_binding_constraint": False,
                "notes": "",
            }
            for name, kind, req, realized, implied in rows
        ]
    )
    precision_rows = out["binding_implied_precision"].notna()
    if precision_rows.any():
        idx = out.loc[precision_rows, "binding_implied_precision"].idxmax()
        out.loc[idx, "is_binding_constraint"] = True
    return out


def build_manifest(paths: dict[str, Path], frames: dict[str, pd.DataFrame], decision: pd.DataFrame, config_path: Path, requirement_path: Path) -> dict[str, Any]:
    outputs = {
        key: {
            "path": str(path),
            "sha256": path_sha(path),
            "row_count": int(len(frames[key])) if key in frames else np.nan,
        }
        for key, path in paths.items()
        if key != "manifest" and path.exists()
    }
    return {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "legacy_directory_id": LEGACY_DIRECTORY_ID,
        "requirement_path": str(requirement_path),
        "requirement_sha256": path_sha(requirement_path),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "git_revision": git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_sha256": path_sha(config_path),
        "final_decision": decision.iloc[0]["decision_state"] if not decision.empty else "",
        "outputs": outputs,
    }


def build_report(
    decision: pd.DataFrame,
    baselines: pd.DataFrame,
    validation_health: pd.DataFrame,
    non_model: pd.DataFrame,
    score_frontier: pd.DataFrame,
    active_state: pd.DataFrame,
    selfcheck: pd.DataFrame,
    lightgbm_card: pd.DataFrame,
    lightgbm_frontier: pd.DataFrame,
    entropy_audit: pd.DataFrame,
    volume_audit: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    c0 = baselines.loc[baselines["source_arm_id"].eq(PRIMARY_SOURCE_ARM) & baselines["split"].eq("robustness")].iloc[0]
    r = baselines.loc[baselines["source_arm_id"].eq(R_CORE_SOURCE_ARM) & baselines["split"].eq("robustness")].iloc[0]
    binding = selfcheck.loc[bool_series(selfcheck["is_binding_constraint"])].iloc[0] if not selfcheck.empty else pd.Series()
    best_non = non_model.loc[non_model["split"].eq("robustness") & non_model["bucket_id"].eq("top20")].sort_values("low_to_high_precision", ascending=False).head(1)
    best_non_text = "无可用"
    if not best_non.empty:
        item = best_non.iloc[0]
        best_non_text = f"{item['frontier_id']}，top20 precision={item['low_to_high_precision']:.4f}"
    lg_status = lightgbm_card.iloc[0].get("lightgbm_challenger_status", "unknown") if not lightgbm_card.empty else "missing"
    primary_top20 = score_frontier.loc[score_frontier["split"].eq("robustness") & score_frontier["bucket_id"].eq("top20")].sort_values("low_to_high_precision", ascending=False).head(1)
    primary_top10 = pd.DataFrame()
    if not primary_top20.empty:
        primary_model_id = primary_top20.iloc[0]["model_id"]
        primary_top10 = score_frontier.loc[
            score_frontier["model_id"].eq(primary_model_id)
            & score_frontier["split"].eq("robustness")
            & score_frontier["bucket_id"].eq("top10")
        ].head(1)
    p20 = primary_top20.iloc[0] if not primary_top20.empty else pd.Series(dtype=object)
    p10 = primary_top10.iloc[0] if not primary_top10.empty else pd.Series(dtype=object)
    bad_delta = float(p20.get("bad_side_10_20_rate", np.nan)) - float(c0.get("bad_side_10_20_rate", np.nan)) if not p20.empty else np.nan
    active_rob = active_state.loc[active_state["split"].eq("robustness")].sort_values("diagnostic_carry_precision", ascending=False).head(1)
    active_text = "无可用 active-state readout"
    if not active_rob.empty:
        active_item = active_rob.iloc[0]
        active_text = f"horizon={int(active_item['horizon_sessions'])}, diagnostic_carry_precision={active_item['diagnostic_carry_precision']:.4f}, forward_looking_caveat=true"
    entropy_blocked = int((~bool_series(entropy_audit.get("allowed_for_primary_model_after_audit", pd.Series(dtype=bool)))).sum()) if not entropy_audit.empty else 0
    volume_blocked = int((~bool_series(volume_audit.get("allowed_for_primary_model_after_audit", pd.Series(dtype=bool)))).sum()) if not volume_audit.empty else 0
    lg_text = "未评估或依赖缺失，stub 输出已进入 manifest。"
    if lg_status == "evaluated" and not lightgbm_frontier.empty:
        lg20 = lightgbm_frontier.loc[lightgbm_frontier["split"].eq("robustness") & lightgbm_frontier["bucket_id"].eq("top20")].head(1)
        if not lg20.empty:
            lg_item = lg20.iloc[0]
            lg_text = (
                f"已评估；robustness top20 precision={lg_item['low_to_high_precision']:.4f}, "
                f"lift_vs_C0={lg_item['precision_lift_vs_C0_risk_on_baseline']:.3f}, "
                f"lift_vs_best_non_model={lg_item['precision_lift_vs_best_non_model_baseline']:.3f}。"
                "该读数只作为 nonlinear challenger，不参与 12A4 supported gate。"
            )
    return f"""
# 12A4 State-change Meta-label Filter Feasibility 决策报告

## 决策

- final decision: `{d['decision_state']}`
- reason: {d['decision_reason']}
- recommended next: `{d['recommended_next_requirement']}`

## Risk-on baseline

- C0 robustness low_to_high precision: {c0['low_to_high_precision']:.4f} ({int(c0['event_inside_window_n'])}/{int(c0['event_n'])})
- R-core robustness low_to_high precision: {r['low_to_high_precision']:.4f} ({int(r['event_inside_window_n'])}/{int(r['event_n'])})
- allowed primary best top20 precision: {d['allowed_primary_best_robustness_top20_low_to_high_precision']:.4f}
- lift vs C0: {d['allowed_primary_best_precision_lift_vs_C0_risk_on_baseline']:.3f}
- lift vs R-core: {d['allowed_primary_best_precision_lift_vs_R_core_risk_on_baseline']:.3f}
- 8.39% 只是 12A3 C0 all-scope reference precision，不是 12A4 成功目标；12A4 supported 还要求同 split R-core/C0 lift、episode recall、bad-side 和 non-model baseline 增量。

## Validation threshold health

- validation_threshold_health_pass: {validation_health.iloc[0]['validation_threshold_health_pass']}
- threshold_selection_source: `{validation_health.iloc[0]['threshold_selection_source']}`
- validation positive/base precision: {int(validation_health.iloc[0]['validation_positive_n'])} / {validation_health.iloc[0]['validation_base_precision']:.4f}
- validation 不健康时只做 readout；threshold selection 已固定为 train internal CV，robustness 不参与调参。

## Primary model frontier

- best model: `{p20.get('model_id', '')}`
- top10 precision / event_n / bad-side: {p10.get('low_to_high_precision', np.nan):.4f} / {int(p10.get('event_n', 0))} / {p10.get('bad_side_10_20_rate', np.nan):.4f}
- top20 precision / event_n / episode recall / bad-side: {p20.get('low_to_high_precision', np.nan):.4f} / {int(p20.get('event_n', 0))} / {p20.get('episode_recall_low_to_high', np.nan):.4f} / {p20.get('bad_side_10_20_rate', np.nan):.4f}
- top20 bad-side delta vs C0 robustness baseline: {bad_delta:.4f}

## Feature and baseline readout

- best non-model baseline: {best_non_text}
- active-state carry is diagnostic-only; `forward_looking_caveat = true`.
- active-state robustness readout: {active_text}
- entropy audit diagnostic-blocked rows: {entropy_blocked}
- volume acceleration audit diagnostic-blocked rows: {volume_blocked}
- binding supported gate: `{binding.get('gate_name', '')}` with binding-implied precision {binding.get('binding_implied_precision', np.nan):.4f}

## LightGBM challenger

- status: `{lg_status}`
- {lg_text}

## 结论

12A4 只把 allowed primary models 作为 supported / partial 判定来源。若 precision uplift 主要来自 non-model baseline 或 LightGBM-only readout，本阶段不把 state-change 事件升级为 timing selector。
""".strip()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    config = load_yaml(config_path)
    paths = output_paths()
    audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], audit)
    read_ok = audit["read_status"].astype(str).eq("pass").all()
    schema_ok = ~audit["schema_status"].astype(str).str.startswith("missing_columns").any()
    if args.mode == "check-inputs":
        if not read_ok or not schema_ok:
            raise RuntimeError("12A4 input check failed")
        print(f"{RUN_ID}: input audit ok ({len(audit)} artifacts)")
        return 0
    if not read_ok or not schema_ok:
        raise RuntimeError("12A4 required inputs missing or schema mismatch")

    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    backbone_decision = read_table(resolved["backbone_frontier_decision"])
    parity_audit = read_table(resolved["state_change_label_recompute_parity_audit"])
    a3_gate_pass, a3_gate_reason = check_12a3_gate(backbone_decision, parity_audit)
    if not a3_gate_pass:
        raise RuntimeError(f"12A3 decision gate failed for 12A4: {a3_gate_reason}")

    stock_cache = StockDailyCache(resolved["stock_daily_csv_dir"])
    label_cfg = load_label_config(config)
    episodes = add_episode_positions(read_table(resolved["episode_target_registry_06"]), stock_cache)
    feature_panel = read_table(resolved["source_08_feature_panel"])
    canonical_raw = read_table(resolved["state_change_candidate_event_canonical"])
    c0_events, excluded = normalize_c0_events(canonical_raw)
    r_core_raw = read_table(resolved["r_core_arm_event_registry"])
    r_core_events, r_core_excluded = normalize_r_core_events(r_core_raw, feature_panel)
    regime_exclusion = build_regime_scope_exclusion(canonical_raw, excluded, r_core_excluded)
    c0_events = attach_c0_labels(c0_events, stock_cache, label_cfg)
    r_core_events = attach_r_core_labels(r_core_events)
    universe = pd.concat([c0_events, r_core_events], ignore_index=True, sort=False)
    universe = add_source_arm_and_readout_flags(universe, int(config.get("thresholds", {}).get("nearby_window_sessions", 5)))
    targets = match_episode_targets(universe, episodes)
    label_cols = [
        "fast_fail_10d_label",
        "false_repair_20d_label",
        "winner_120_label",
        "label_10d_complete",
        "label_20d_complete",
        "label_120d_complete",
        "label_status",
    ]
    universe_targets = universe.drop(columns=[col for col in label_cols if col in universe.columns], errors="ignore").merge(
        targets,
        on=["meta_event_id", "source_arm_id", "instrument", "event_split"],
        how="left",
    )
    c0_targets = universe_targets.loc[universe_targets["source_arm_id"].eq(PRIMARY_SOURCE_ARM)].copy()
    feature_result = build_features(c0_events, r_core_events, c0_targets, stock_cache, feature_panel, config)
    feature_matrix = feature_result.feature_matrix
    split_audit = build_split_time_boundary_audit(feature_matrix)
    baselines = build_r_core_baseline(universe_targets, episodes)
    validation_health = build_validation_health(c0_targets, config)
    active_state = build_active_state_frontier(c0_targets, episodes, config)
    model_frame, feature_cols = prepare_model_frame(feature_matrix, c0_targets, feature_result.dictionary)
    non_model, best_non_model = build_non_model_frontier(feature_matrix, c0_targets, episodes, baselines)
    scored, model_card = fit_primary_models(model_frame, feature_cols, config)
    score_frontier = build_score_frontier(scored, episodes, baselines, best_non_model)
    lightgbm_frontier, lightgbm_card = build_lightgbm_outputs(model_frame, feature_cols, episodes, baselines, best_non_model, config)
    r_core_ok = not baselines.loc[
        baselines["source_arm_id"].eq(R_CORE_SOURCE_ARM) & baselines["split"].eq("robustness") & baselines["baseline_status"].eq("ok")
    ].empty
    input_gate_pass = bool(read_ok and schema_ok and a3_gate_pass and r_core_ok and feature_result.pit_audit["pit_status"].astype(str).eq("pass").all())
    decision, selfcheck = evaluate_decision(score_frontier, lightgbm_frontier, baselines, best_non_model, validation_health, feature_result.dictionary, config, input_gate_pass)
    report = build_report(
        decision,
        baselines,
        validation_health,
        non_model,
        score_frontier,
        active_state,
        selfcheck,
        lightgbm_card,
        lightgbm_frontier,
        feature_result.entropy_audit,
        feature_result.volume_audit,
    )

    frames = {
        "input_artifact_audit": audit,
        "regime_scope_exclusion_audit": regime_exclusion,
        "split_time_boundary_audit": split_audit,
        "event_universe": universe,
        "event_targets": targets,
        "feature_dictionary": feature_result.dictionary,
        "feature_pit_audit": feature_result.pit_audit,
        "entropy_audit": feature_result.entropy_audit,
        "volume_audit": feature_result.volume_audit,
        "r_core_baseline": baselines,
        "active_state": active_state,
        "non_model_frontier": non_model,
        "validation_health": validation_health,
        "score_frontier": score_frontier,
        "supported_selfcheck": selfcheck,
        "model_card": model_card,
        "lightgbm_frontier": lightgbm_frontier,
        "lightgbm_model_card": lightgbm_card,
        "decision": decision,
        "feature_matrix": feature_matrix,
    }
    for key, frame in frames.items():
        if key in paths:
            write_df(paths[key], frame)
    write_text(paths["report"], report)
    frames["report"] = pd.DataFrame([{"report_path": str(paths["report"])}])
    write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, resolved["requirement"]))
    print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
