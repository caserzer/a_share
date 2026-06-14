#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402


CONFIG_PATH = EXPERIMENT_DIR / "config.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_09a_fast_fail_label_frontier.md"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"

FRONTIER_TABLE_DIR = TABLE_DIR / "09A_fast_fail_label_frontier"
FRONTIER_REPORT_DIR = REPORT_DIR / "09A_fast_fail_label_frontier"
INPUT_AUDIT_DIR = TABLE_DIR / "input_audit"
FRONTIER_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "09A_fast_fail_label_frontier"

DECISION_SELECTED = "09A_label_frontier_candidate_selected"
DECISION_SELECTED_CAVEATED = "09A_label_frontier_candidate_source_caveated_selected"
DECISION_DIAGNOSTIC = "09A_label_frontier_diagnostic_only_no_candidate"
DECISION_INPUT_BLOCKED = "09A_label_frontier_input_blocked"
DECISION_SOURCE_POOL_BLOCKED = "09A_source_pool_reconstruction_blocked"
DECISION_REGIME_BLOCKED = "09A_regime_label_pit_blocked"

R_CORE_SCOPE = "08_R_core_event_regime_gated"
R6_SCOPE = "08_R6_event_regime_gated"
E1_SCOPE = "07_E1_only"
RISK_ON_R_CORE_DENOM = "risk_on_r_core_horizon_complete"
RISK_ON_R6_DENOM = "risk_on_r6_horizon_complete"
RISK_OFF_E1_DENOM = "risk_off_e1_horizon_complete_readonly"
INCUMBENT_LABEL_ID = "incumbent_failure_10_label"
FALSE_REPAIR_COMPONENT_ID = "frozen_event_false_repair_20d_label"

R_CORE_VARIANT_TOKENS = (
    "R1_relative_strength_breakout__event_regime_gated",
    "R2_near_high_volume_expansion__event_regime_gated",
    "R6_market_breadth_thrust__event_regime_gated",
    "R7_cross_sectional_momentum_rank_jump__event_regime_gated",
    "R8_persistent_distance_above_ema__event_regime_gated",
)
R6_VARIANT_TOKEN = "R6_market_breadth_thrust__event_regime_gated"
E1_CHANNEL_TOKEN = "E1_early_ema60_repair"

SPLITS = ("all", "train", "validation", "robustness")


@dataclass(frozen=True)
class InputSpec:
    input_id: str
    path: Path
    required: bool = True
    columns: tuple[str, ...] = ()


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator is None or pd.isna(denominator) or float(denominator) == 0:
        return np.nan
    return float(numerator) / float(denominator)


def bool_series(series: pd.Series | Any) -> pd.Series:
    values = series if isinstance(series, pd.Series) else pd.Series(series)
    if pd.api.types.is_bool_dtype(values) or pd.api.types.is_numeric_dtype(values):
        return values.astype("boolean").fillna(False).astype(bool)
    return values.map(lambda value: str(value).lower() in {"true", "1"} if pd.notna(value) else False)


def compact_join(values: pd.Series) -> str:
    cleaned = [str(v) for v in values.dropna().astype(str).unique() if str(v)]
    return ";".join(sorted(cleaned))


def canonical_sample_id(frame: pd.DataFrame) -> pd.Series:
    if "canonical_event_id" in frame.columns:
        base = frame["canonical_event_id"].where(frame["canonical_event_id"].notna(), "")
    else:
        base = pd.Series("", index=frame.index)
    fallback = (
        frame.get("instrument", pd.Series("", index=frame.index)).astype(str)
        + "|"
        + frame.get("event_t0_date", pd.Series("", index=frame.index)).astype(str)
        + "|"
        + frame.get("trade_open_date", pd.Series("", index=frame.index)).astype(str)
        + "|"
        + frame.get("event_id", pd.Series("", index=frame.index)).astype(str)
    ).map(lambda value: stable_hash(value)[:24])
    return base.where(base.astype(str).str.len() > 0, fallback).astype(str)


def map_winner_censoring_status(status: Any) -> str:
    mapping = {
        "not_missing": "complete",
        "censored_incomplete_horizon": "incomplete_120d",
        "non_executable_next_open": "non_executable",
    }
    if pd.isna(status):
        return "not_evaluable"
    return mapping.get(str(status), "not_evaluable")


def cohen_kappa_from_binary(left: pd.Series, right: pd.Series) -> float:
    valid = left.notna() & right.notna()
    if int(valid.sum()) == 0:
        return np.nan
    a = left.loc[valid].astype(bool)
    b = right.loc[valid].astype(bool)
    po = float((a == b).mean())
    p_yes_a = float(a.mean())
    p_yes_b = float(b.mean())
    pe = p_yes_a * p_yes_b + (1 - p_yes_a) * (1 - p_yes_b)
    if math.isclose(pe, 1.0):
        return np.nan
    return (po - pe) / (1 - pe)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 09A fast-fail label frontier.")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    return load_yaml(path)


def input_specs(config: dict[str, Any]) -> list[InputSpec]:
    paths = config["paths"]
    return [
        InputSpec("requirement_09a", REQUIREMENT_PATH, True),
        InputSpec("config", CONFIG_PATH, True),
        InputSpec("readme", PROJECT_ROOT / "README.md", True),
        InputSpec("research_direction", PROJECT_ROOT / "research_direction_discussion_20260614.md", True),
        InputSpec("upstream_08_final_report", topic_path(paths["upstream_08_final_report"]), True),
        InputSpec("upstream_01_run_manifest", topic_path(paths["upstream_01_run_manifest"]), True),
        InputSpec("upstream_01_cache_manifest", topic_path(paths["upstream_01_cache_manifest"]), True),
        InputSpec("upstream_07_run_manifest", topic_path(paths["upstream_07_run_manifest"]), True),
        InputSpec(
            "upstream_07_canonical_events",
            topic_path(paths["upstream_07_canonical_events"]),
            True,
            ("event_id", "instrument", "event_t0_date", "triggered_channels", "market_regime_bucket"),
        ),
        InputSpec("upstream_07_event_labels", topic_path(paths["upstream_07_event_labels"]), True),
        InputSpec("upstream_08_a_manifest", topic_path(paths["upstream_08_a_manifest"]), True),
        InputSpec("upstream_08_d_manifest", topic_path(paths["upstream_08_d_manifest"]), True),
        InputSpec("upstream_08_e_manifest", topic_path(paths["upstream_08_e_manifest"]), True),
        InputSpec("upstream_08_h_manifest", topic_path(paths["upstream_08_h_manifest"]), True),
        InputSpec(
            "upstream_08_transition_subregime_taxonomy_manifest",
            topic_path(paths["upstream_08_transition_subregime_taxonomy_manifest"]),
            True,
        ),
        InputSpec(
            "upstream_08_transition_previous_regime_outcome_manifest",
            topic_path(paths["upstream_08_transition_previous_regime_outcome_manifest"]),
            True,
        ),
        InputSpec(
            "upstream_08_transition_previous_regime_context_manifest",
            topic_path(paths["upstream_08_transition_previous_regime_context_manifest"]),
            True,
        ),
        InputSpec("candidate_scope_mapping_contract", topic_path(paths["candidate_scope_mapping_contract"]), True),
        InputSpec("candidate_scope_reconstructability_audit", topic_path(paths["candidate_scope_reconstructability_audit"]), True),
        InputSpec(
            "upstream_08_canonical_events",
            topic_path(paths["upstream_08_canonical_events"]),
            True,
            (
                "event_id",
                "instrument",
                "event_t0_date",
                "triggered_family_variants",
                "event_regime_bucket",
                "market_regime_bucket",
            ),
        ),
        InputSpec("upstream_08_event_instances", topic_path(paths["upstream_08_event_instances"]), True),
        InputSpec("upstream_08_event_labels", topic_path(paths["upstream_08_event_labels"]), True),
        InputSpec("upstream_08_capture", topic_path(paths["upstream_08_capture"]), True),
        InputSpec("upstream_08_feature_panel", topic_path(paths["upstream_08_feature_panel"]), True),
        InputSpec("upstream_08_membership", topic_path(paths["upstream_08_membership"]), True),
        InputSpec("upstream_08_leakage_audit", topic_path(paths["upstream_08_leakage_audit"]), True),
    ]


def read_columns(path: Path) -> tuple[list[str], str]:
    if not path.exists() or not path.is_file():
        return [], "missing"
    try:
        if path.suffix == ".parquet":
            return list(pd.read_parquet(path).columns), "readable_tabular"
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
            return [], "readable_non_tabular"
        if path.suffix == ".md":
            path.read_text(encoding="utf-8")
            return [], "readable_non_tabular"
        return list(pd.read_csv(path, nrows=0).columns), "readable_tabular"
    except Exception:
        return [], "unreadable"


def input_audit(config: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for spec in input_specs(config):
        columns, read_status = read_columns(spec.path)
        missing_cols = sorted(set(spec.columns) - set(columns))
        if not spec.path.exists():
            status = "missing_required_input" if spec.required else "missing_optional_input"
        elif read_status == "unreadable":
            status = "unreadable_required_input" if spec.required else "unreadable_optional_input"
        elif missing_cols:
            status = "schema_incompatible_required_input"
        else:
            status = "ok"
        if spec.required and status != "ok":
            failures.append(f"{status}:{spec.input_id}")
        rows.append(
            {
                "input_id": spec.input_id,
                "path": str(spec.path),
                "required": bool(spec.required),
                "exists": bool(spec.path.exists()),
                "readability_status": read_status,
                "sha256": path_hash(spec.path),
                "expected_columns": ";".join(spec.columns),
                "actual_columns": ";".join(columns),
                "missing_required_columns": ";".join(missing_cols),
                "status": status,
            }
        )
    stock_dir = topic_path(config["paths"]["stock_daily_csv_dir"])
    stock_files = sorted(stock_dir.glob("*.csv")) if stock_dir.exists() else []
    stock_count = len(stock_files)
    stock_expected = {"date", "open", "high", "low", "close", "volume", "money", "factor"}
    stock_columns: list[str] = []
    if stock_files:
        stock_columns = list(pd.read_csv(stock_files[0], nrows=0).columns)
    stock_missing = sorted(stock_expected - set(stock_columns))
    stock_status = "ok" if stock_count > 0 and not stock_missing else "schema_incompatible_required_input"
    if stock_count == 0:
        stock_status = "missing_required_input"
    rows.append(
        {
            "input_id": "stock_daily_csv_dir_glob",
            "path": str(stock_dir),
            "required": True,
            "exists": stock_dir.exists(),
            "readability_status": "directory" if stock_dir.exists() else "missing",
            "sha256": "",
            "expected_columns": "date;open;high;low;close;volume;money;factor;adjustment_policy=qfq_daily_csv_factor_column",
            "actual_columns": f"csv_count={stock_count};sample_columns={';'.join(stock_columns)}",
            "missing_required_columns": ";".join(stock_missing),
            "status": stock_status,
        }
    )
    if stock_status != "ok":
        failures.append(f"{stock_status}:stock_daily_csv_dir_glob")
    return pd.DataFrame(rows), failures


class PriceCache:
    def __init__(self, stock_daily_dir: Path) -> None:
        self.stock_daily_dir = stock_daily_dir
        self._cache: dict[str, pd.DataFrame | None] = {}

    def load(self, instrument: str) -> pd.DataFrame | None:
        if instrument in self._cache:
            return self._cache[instrument]
        path = self.stock_daily_dir / f"{instrument}.csv"
        if not path.exists():
            self._cache[instrument] = None
            return None
        frame = pd.read_csv(path)
        if frame.empty:
            self._cache[instrument] = None
            return None
        frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
        for col in ("open", "high", "low", "close", "volume", "money"):
            if col in frame.columns:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
        frame = frame.sort_values("date", kind="stable").reset_index(drop=True)
        close = frame["close"]
        high = frame["high"]
        low = frame["low"]
        prev_close = close.shift(1)
        true_range = pd.concat(
            [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        frame["return_1d_calc"] = close.pct_change()
        frame["sigma20"] = frame["return_1d_calc"].rolling(20, min_periods=20).std()
        frame["atr14"] = true_range.rolling(14, min_periods=14).mean()
        frame["ema20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
        frame["ema60"] = close.ewm(span=60, adjust=False, min_periods=60).mean()
        frame["prior_swing_low_20"] = low.shift(1).rolling(20, min_periods=20).min()
        self._cache[instrument] = frame
        return frame


def event_anchor_pos(frame: pd.DataFrame) -> pd.Series:
    non_exec = bool_series(frame.get("non_executable_next_open", pd.Series(False, index=frame.index)))
    trade_pos = pd.to_numeric(frame.get("trade_open_pos"), errors="coerce")
    event_pos = pd.to_numeric(frame.get("event_t0_pos"), errors="coerce")
    return pd.Series(np.where((~non_exec) & trade_pos.notna(), trade_pos, event_pos), index=frame.index)


def rebuild_r_core(canonical: pd.DataFrame) -> pd.DataFrame:
    variants = canonical["triggered_family_variants"].fillna("").astype(str)
    mask = pd.Series(False, index=canonical.index)
    for token in R_CORE_VARIANT_TOKENS:
        mask = mask | variants.str.contains(token, regex=False)
    selected = canonical.loc[mask].copy()
    selected["event_window_anchor_pos"] = event_anchor_pos(selected)
    anchored = selected.loc[selected["event_window_anchor_pos"].notna()].copy()
    anchorless = selected.loc[selected["event_window_anchor_pos"].isna()].copy()
    anchored = anchored.sort_values(
        ["instrument", "event_window_anchor_pos", "canonical_event_id", "event_id"],
        kind="stable",
    ).drop_duplicates(["instrument", "event_window_anchor_pos"], keep="first")
    return pd.concat([anchored, anchorless], ignore_index=True)


def rebuild_r6(canonical: pd.DataFrame) -> pd.DataFrame:
    variants = canonical["triggered_family_variants"].fillna("").astype(str)
    selected = canonical.loc[variants.str.contains(R6_VARIANT_TOKEN, regex=False)].copy()
    selected["event_window_anchor_pos"] = event_anchor_pos(selected)
    return selected


def rebuild_e1(canonical_07: pd.DataFrame) -> pd.DataFrame:
    channels = canonical_07["triggered_channels"].fillna("").astype(str)
    selected = canonical_07.loc[channels.str.contains(E1_CHANNEL_TOKEN, regex=False)].copy()
    selected["event_window_anchor_pos"] = event_anchor_pos(selected)
    if "event_regime_bucket" not in selected.columns:
        selected["event_regime_bucket"] = selected.get("market_regime_bucket", "unknown")
    return selected


def ensure_common_event_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "canonical_event_id" not in out.columns:
        out["canonical_event_id"] = out.get("event_id", "")
    if "event_regime_bucket" not in out.columns:
        out["event_regime_bucket"] = out.get("market_regime_bucket", "unknown")
    if "trade_time" not in out.columns:
        out["trade_time"] = out.get("trade_open_date")
    return out


def build_denominator_events(
    canonical_08: pd.DataFrame,
    labels_08: pd.DataFrame,
    canonical_07: pd.DataFrame,
    labels_07: pd.DataFrame,
) -> pd.DataFrame:
    r_core = ensure_common_event_columns(rebuild_r_core(canonical_08))
    r_core = r_core.loc[r_core["event_regime_bucket"].astype(str) == "risk_on"].copy()
    r_core["source_pool_id"] = R_CORE_SCOPE
    r_core["denominator_id"] = RISK_ON_R_CORE_DENOM

    r6 = ensure_common_event_columns(rebuild_r6(canonical_08))
    r6 = r6.loc[r6["event_regime_bucket"].astype(str) == "risk_on"].copy()
    r6["source_pool_id"] = R6_SCOPE
    r6["denominator_id"] = RISK_ON_R6_DENOM

    e1 = ensure_common_event_columns(rebuild_e1(canonical_07))
    e1 = e1.loc[e1["event_regime_bucket"].astype(str) == "risk_off"].copy()
    e1["source_pool_id"] = E1_SCOPE
    e1["denominator_id"] = RISK_OFF_E1_DENOM

    event_cols = [
        "event_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "trade_open_price",
        "non_executable_next_open",
        "event_split",
        "market_regime_bucket",
        "event_regime_bucket",
        "board_bucket",
        "source_pool_id",
        "denominator_id",
    ]
    label_cols = [
        "event_id",
        "failure_10_label",
        "failure_10_complete",
        "failure_10_touch_date",
        "failure_10_touch_pos",
        "horizon_complete_10d",
        "horizon_complete_20d",
        "horizon_complete_120d",
        "mae_10d",
        "event_false_repair_20d_label",
        "event_false_repair_20d_complete",
        "candidate_outcome_120d_status",
        "event_big_winner_120d_label",
        "event_super_winner_120d_label",
        "event_near_winner_120d_label",
        "captured_target_episode_id_first",
    ]
    labels_08_slim = labels_08[[c for c in label_cols if c in labels_08.columns]].drop_duplicates("event_id")
    labels_07_slim = labels_07[[c for c in label_cols if c in labels_07.columns]].drop_duplicates("event_id")

    r_all = pd.concat([r_core, r6], ignore_index=True)
    r_all = r_all[[c for c in event_cols if c in r_all.columns]].merge(
        labels_08_slim, on="event_id", how="left"
    )
    e1 = e1[[c for c in event_cols if c in e1.columns]].merge(labels_07_slim, on="event_id", how="left")
    base = pd.concat([r_all, e1], ignore_index=True, sort=False)
    base["sample_id"] = canonical_sample_id(base)
    base["trade_time"] = base["trade_open_date"]
    base["winner_censoring_status"] = base["candidate_outcome_120d_status"].map(
        map_winner_censoring_status
    )
    base["horizon_complete_10d"] = bool_series(base.get("horizon_complete_10d", pd.Series(False, index=base.index)))
    base["horizon_complete_20d"] = bool_series(base.get("horizon_complete_20d", pd.Series(False, index=base.index)))
    base["horizon_complete_120d"] = bool_series(
        base.get("horizon_complete_120d", pd.Series(False, index=base.index))
    )
    base["non_executable_next_open"] = bool_series(
        base.get("non_executable_next_open", pd.Series(False, index=base.index))
    )
    return base


def with_episode_info(base: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    if membership.empty:
        out = base.copy()
        out["target_episode_id"] = out.get("captured_target_episode_id_first", "")
        out["episode_regime_bucket"] = ""
        return out
    mem = membership.copy()
    key_cols = ["candidate_scope_id", "canonical_event_id"]
    grouped = (
        mem.dropna(subset=["target_episode_id"])
        .groupby(key_cols, dropna=False)
        .agg(
            target_episode_id=("target_episode_id", compact_join),
            episode_regime_bucket=("market_regime_bucket_episode", lambda s: s.dropna().astype(str).iloc[0] if s.dropna().size else ""),
        )
        .reset_index()
        .rename(columns={"candidate_scope_id": "source_pool_id"})
    )
    out = base.merge(grouped, on=["source_pool_id", "canonical_event_id"], how="left")
    out["target_episode_id"] = out["target_episode_id"].fillna(
        out.get("captured_target_episode_id_first", "")
    )
    out["episode_regime_bucket"] = out["episode_regime_bucket"].fillna("")
    return out


def first_touch(future: pd.DataFrame, threshold: float, *, field: str = "low") -> tuple[bool, str, int]:
    if future.empty or pd.isna(threshold):
        return False, "", -1
    touch = future.loc[pd.to_numeric(future[field], errors="coerce") <= threshold]
    if touch.empty:
        return False, "", -1
    idx = int(touch.index[0])
    return True, str(touch.iloc[0]["date"]), idx


def compute_path_candidate(row: pd.Series, spec_id: str, spec: dict[str, Any], cache: PriceCache) -> dict[str, Any]:
    if bool(row.get("non_executable_next_open", False)) or pd.isna(row.get("trade_open_date")):
        return {
            f"{spec_id}_label": pd.NA,
            f"{spec_id}_touch_date": "",
            f"{spec_id}_touch_pos": -1,
            f"{spec_id}_barrier_id": spec_id,
            f"{spec_id}_evaluable": False,
            f"{spec_id}_not_evaluable_reason": "non_executable_next_open",
        }
    prices = cache.load(str(row.get("instrument")))
    if prices is None:
        return {
            f"{spec_id}_label": pd.NA,
            f"{spec_id}_touch_date": "",
            f"{spec_id}_touch_pos": -1,
            f"{spec_id}_barrier_id": spec_id,
            f"{spec_id}_evaluable": False,
            f"{spec_id}_not_evaluable_reason": "missing_price_path",
        }
    trade_date = str(row.get("trade_open_date"))
    matches = prices.index[prices["date"] == trade_date].tolist()
    if not matches:
        return {
            f"{spec_id}_label": pd.NA,
            f"{spec_id}_touch_date": "",
            f"{spec_id}_touch_pos": -1,
            f"{spec_id}_barrier_id": spec_id,
            f"{spec_id}_evaluable": False,
            f"{spec_id}_not_evaluable_reason": "trade_date_missing_in_price_path",
        }
    pos = int(matches[0])
    future = prices.iloc[pos : pos + 10].copy()
    if len(future) < 10:
        return {
            f"{spec_id}_label": pd.NA,
            f"{spec_id}_touch_date": "",
            f"{spec_id}_touch_pos": -1,
            f"{spec_id}_barrier_id": spec_id,
            f"{spec_id}_evaluable": False,
            f"{spec_id}_not_evaluable_reason": "incomplete_10d_price_path",
        }
    trade_price = float(row.get("trade_open_price")) if pd.notna(row.get("trade_open_price")) else float(prices.iloc[pos]["open"])
    pre = prices.iloc[pos - 1] if pos > 0 else None
    threshold = np.nan
    family = spec["mechanism_family"]
    if family == "fixed_mae10":
        threshold = trade_price * (1.0 + float(spec["barrier_pct"]))
    elif family == "vol_scaled":
        if pre is not None and pd.notna(pre.get("sigma20")):
            threshold = trade_price * (1.0 - float(spec["sigma_multiplier"]) * float(pre["sigma20"]))
    elif family == "atr_scaled":
        if pre is not None and pd.notna(pre.get("atr14")):
            threshold = trade_price - float(spec["atr_multiplier"]) * float(pre["atr14"])
    elif family == "structural":
        rule = str(spec.get("structural_rule"))
        if rule == "event_low":
            event_date = str(row.get("event_t0_date"))
            event_match = prices.index[prices["date"] == event_date].tolist()
            if event_match:
                threshold = float(prices.iloc[int(event_match[0])]["low"])
        elif rule == "swing_low" and pre is not None:
            threshold = float(pre.get("prior_swing_low_20", np.nan))
        elif rule == "ema" and pre is not None:
            threshold = float(pre.get(f"ema{int(spec['ema_span'])}", np.nan))
    if pd.isna(threshold) or threshold <= 0:
        return {
            f"{spec_id}_label": pd.NA,
            f"{spec_id}_touch_date": "",
            f"{spec_id}_touch_pos": -1,
            f"{spec_id}_barrier_id": spec_id,
            f"{spec_id}_evaluable": False,
            f"{spec_id}_not_evaluable_reason": "barrier_not_evaluable",
        }
    touched, touch_date, touch_pos = first_touch(future, threshold)
    return {
        f"{spec_id}_label": bool(touched),
        f"{spec_id}_touch_date": touch_date,
        f"{spec_id}_touch_pos": touch_pos,
        f"{spec_id}_barrier_id": spec_id,
        f"{spec_id}_evaluable": True,
        f"{spec_id}_not_evaluable_reason": "",
    }


def _candidate_not_evaluable(spec_id: str, reason: str) -> dict[str, Any]:
    return {
        f"{spec_id}_label": pd.NA,
        f"{spec_id}_touch_date": "",
        f"{spec_id}_touch_pos": -1,
        f"{spec_id}_barrier_id": spec_id,
        f"{spec_id}_evaluable": False,
        f"{spec_id}_not_evaluable_reason": reason,
    }


def _candidate_from_shared_path(
    row: pd.Series,
    spec_id: str,
    spec: dict[str, Any],
    prices: pd.DataFrame,
    pos: int,
    future: pd.DataFrame,
    pre: pd.Series | None,
    trade_price: float,
) -> dict[str, Any]:
    threshold = np.nan
    family = spec["mechanism_family"]
    if family == "fixed_mae10":
        threshold = trade_price * (1.0 + float(spec["barrier_pct"]))
    elif family == "vol_scaled":
        if pre is not None and pd.notna(pre.get("sigma20")):
            threshold = trade_price * (1.0 - float(spec["sigma_multiplier"]) * float(pre["sigma20"]))
    elif family == "atr_scaled":
        if pre is not None and pd.notna(pre.get("atr14")):
            threshold = trade_price - float(spec["atr_multiplier"]) * float(pre["atr14"])
    elif family == "structural":
        rule = str(spec.get("structural_rule"))
        if rule == "event_low":
            event_date = str(row.get("event_t0_date"))
            event_match = prices.index[prices["date"] == event_date].tolist()
            if event_match:
                threshold = float(prices.iloc[int(event_match[0])]["low"])
        elif rule == "swing_low" and pre is not None:
            threshold = float(pre.get("prior_swing_low_20", np.nan))
        elif rule == "ema" and pre is not None:
            threshold = float(pre.get(f"ema{int(spec['ema_span'])}", np.nan))
    if pd.isna(threshold) or threshold <= 0:
        return _candidate_not_evaluable(spec_id, "barrier_not_evaluable")
    touched, touch_date, touch_pos = first_touch(future, threshold)
    return {
        f"{spec_id}_label": bool(touched),
        f"{spec_id}_touch_date": touch_date,
        f"{spec_id}_touch_pos": touch_pos,
        f"{spec_id}_barrier_id": spec_id,
        f"{spec_id}_evaluable": True,
        f"{spec_id}_not_evaluable_reason": "",
    }


def compute_path_candidates_for_row(
    row: pd.Series,
    specs: dict[str, dict[str, Any]],
    cache: PriceCache,
) -> dict[str, Any]:
    if bool(row.get("non_executable_next_open", False)) or pd.isna(row.get("trade_open_date")):
        return {
            key: value
            for spec_id in specs
            for key, value in _candidate_not_evaluable(spec_id, "non_executable_next_open").items()
        }
    prices = cache.load(str(row.get("instrument")))
    if prices is None:
        return {
            key: value
            for spec_id in specs
            for key, value in _candidate_not_evaluable(spec_id, "missing_price_path").items()
        }
    trade_date = str(row.get("trade_open_date"))
    matches = prices.index[prices["date"] == trade_date].tolist()
    if not matches:
        return {
            key: value
            for spec_id in specs
            for key, value in _candidate_not_evaluable(spec_id, "trade_date_missing_in_price_path").items()
        }
    pos = int(matches[0])
    future = prices.iloc[pos : pos + 10].copy()
    if len(future) < 10:
        return {
            key: value
            for spec_id in specs
            for key, value in _candidate_not_evaluable(spec_id, "incomplete_10d_price_path").items()
        }
    trade_price = float(row.get("trade_open_price")) if pd.notna(row.get("trade_open_price")) else float(prices.iloc[pos]["open"])
    pre = prices.iloc[pos - 1] if pos > 0 else None
    record: dict[str, Any] = {}
    for spec_id, spec in specs.items():
        record.update(_candidate_from_shared_path(row, spec_id, spec, prices, pos, future, pre, trade_price))
    return record


def compute_candidate_labels(base: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = base.copy()
    stock_dir = topic_path(config["paths"]["stock_daily_csv_dir"])
    cache = PriceCache(stock_dir)
    rows: list[dict[str, Any]] = []

    out[f"{INCUMBENT_LABEL_ID}_label"] = out["failure_10_label"]
    out[f"{INCUMBENT_LABEL_ID}_touch_date"] = out.get("failure_10_touch_date", "")
    out[f"{INCUMBENT_LABEL_ID}_touch_pos"] = out.get("failure_10_touch_pos", -1)
    out[f"{INCUMBENT_LABEL_ID}_barrier_id"] = INCUMBENT_LABEL_ID
    out[f"{INCUMBENT_LABEL_ID}_evaluable"] = bool_series(out["failure_10_complete"])
    out[f"{INCUMBENT_LABEL_ID}_not_evaluable_reason"] = np.where(
        out[f"{INCUMBENT_LABEL_ID}_evaluable"], "", "upstream_failure_10_incomplete"
    )
    rows.append(
        {
            "candidate_label_id": INCUMBENT_LABEL_ID,
            "mechanism_family": "incumbent_fixed_mae10",
            "required_source_artifacts": "candidate_family_event_labels.parquet",
            "required_fields": "failure_10_label;failure_10_complete",
            "path_ordering_required": False,
            "candidate_label_status": "evaluable",
            "not_evaluable_reason": "",
        }
    )

    records = [
        compute_path_candidates_for_row(row, config["candidate_labels"], cache)
        for _, row in out.iterrows()
    ]
    candidate_frame = pd.DataFrame(records, index=out.index)
    for col in candidate_frame.columns:
        out[col] = candidate_frame[col]

    for spec_id, spec in config["candidate_labels"].items():
        status_override = spec.get("candidate_label_status_override")
        rows.append(
            {
                "candidate_label_id": spec_id,
                "mechanism_family": spec["mechanism_family"],
                "required_source_artifacts": "data/interim/qlib_csv/day/*.csv",
                "required_fields": "date;open;high;low;close;volume;money;factor;adjustment_policy=qfq_daily_csv_factor_column",
                "path_ordering_required": True,
                "candidate_label_status": status_override or "evaluable",
                "not_evaluable_reason": "",
            }
        )
    eval_rows = []
    for row in rows:
        cid = row["candidate_label_id"]
        evaluable_col = f"{cid}_evaluable"
        reason_col = f"{cid}_not_evaluable_reason"
        evaluable = bool_series(out[evaluable_col]) if evaluable_col in out else pd.Series(False, index=out.index)
        reasons = out.loc[~evaluable, reason_col].fillna("").astype(str) if reason_col in out else pd.Series(dtype=str)
        row = dict(row)
        row["price_path_coverage_rate"] = safe_rate(int(evaluable.sum()), len(out))
        row["field_missing_count"] = 0
        row["not_evaluable_count"] = int((~evaluable).sum())
        if row["candidate_label_status"] != "sensitivity_only" and int(evaluable.sum()) == 0:
            row["candidate_label_status"] = "not_evaluable"
        row["not_evaluable_reason"] = compact_join(reasons) if not reasons.empty else row["not_evaluable_reason"]
        eval_rows.append(row)
    return out, pd.DataFrame(eval_rows)


def split_mask(frame: pd.DataFrame, split: str) -> pd.Series:
    if split == "all":
        return pd.Series(True, index=frame.index)
    return frame["event_split"].astype(str) == split


def target_from_candidate(frame: pd.DataFrame, candidate_id: str) -> pd.Series:
    label = bool_series(frame[f"{candidate_id}_label"])
    false_repair = bool_series(frame["event_false_repair_20d_label"])
    return label | false_repair


def episode_retention(frame: pd.DataFrame, candidate_id: str) -> float:
    eligible = frame.loc[
        bool_series(frame["horizon_complete_120d"])
        & frame["target_episode_id"].fillna("").astype(str).ne("")
    ].copy()
    if eligible.empty:
        return np.nan
    before = set()
    after = set()
    killed = bool_series(eligible[f"{candidate_id}_label"])
    for _, row in eligible.iterrows():
        episodes = [v for v in str(row["target_episode_id"]).split(";") if v]
        before.update(episodes)
        if not bool(killed.loc[row.name]):
            after.update(episodes)
    return safe_rate(len(after), len(before))


def build_frontier(
    labelled: pd.DataFrame,
    candidate_eval: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    candidate_ids = [INCUMBENT_LABEL_ID, *config["candidate_labels"].keys()]
    status_map = dict(zip(candidate_eval["candidate_label_id"], candidate_eval["candidate_label_status"]))
    rows: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        label = labelled[f"{candidate_id}_label"]
        evaluable = bool_series(labelled[f"{candidate_id}_evaluable"])
        for denom, denom_df in labelled.groupby("denominator_id", dropna=False):
            for split in SPLITS:
                cell = denom_df.loc[split_mask(denom_df, split)].copy()
                if cell.empty:
                    continue
                cell_label = label.loc[cell.index]
                cell_eval = evaluable.loc[cell.index]
                winner_complete = bool_series(cell["horizon_complete_120d"])
                winner_label = cell["event_big_winner_120d_label"]
                winner_valid = winner_complete & winner_label.notna()
                positive = bool_series(cell_label)
                winner_positive = bool_series(winner_label)
                fast_fail_and_winner = positive & winner_valid & winner_positive
                winner_events = winner_valid & winner_positive
                target = target_from_candidate(cell, candidate_id)
                old_target = (
                    bool_series(cell["failure_10_label"])
                    | bool_series(cell["event_false_repair_20d_label"])
                )
                union = int((target | old_target).sum())
                jaccard = safe_rate(int((target & old_target).sum()), union)
                non_exec = bool_series(cell["non_executable_next_open"])
                incomplete_120 = ~winner_complete
                status_120 = cell["candidate_outcome_120d_status"].fillna("")
                rows.append(
                    {
                        "candidate_label_id": candidate_id,
                        "is_incumbent_baseline": candidate_id == INCUMBENT_LABEL_ID,
                        "candidate_label_status": status_map.get(candidate_id, "evaluable"),
                        "denominator_id": denom,
                        "split": split,
                        "raw_event_n": len(cell),
                        "horizon_complete_10d_n": int(cell["horizon_complete_10d"].sum()),
                        "horizon_complete_20d_n": int(cell["horizon_complete_20d"].sum()),
                        "censored_n": int((~cell["horizon_complete_10d"]).sum()),
                        "non_executable_n": int(non_exec.sum()),
                        "not_evaluable_n": int((~cell_eval).sum()),
                        "not_evaluable_share": safe_rate(int((~cell_eval).sum()), len(cell)),
                        "coverage_asymmetry_caveat": False,
                        "winner_120_complete_n": int(winner_complete.sum()),
                        "winner_120_incomplete_n": int(incomplete_120.sum()),
                        "winner_120_incomplete_non_executable_n": int((status_120 == "non_executable_next_open").sum()),
                        "winner_120_incomplete_censored_n": int((status_120 == "censored_incomplete_horizon").sum()),
                        "winner_120_complete_share": safe_rate(int(winner_complete.sum()), len(cell)),
                        "winner_120_completeness_caveat": safe_rate(int(winner_complete.sum()), len(cell)) < 0.95,
                        "positive_n": int((positive & cell_eval).sum()),
                        "positive_rate": safe_rate(int((positive & cell_eval).sum()), int(cell_eval.sum())),
                        "episode_winner_recall_retention": episode_retention(cell, candidate_id),
                        "kill_wrong_rate": safe_rate(int(fast_fail_and_winner.sum()), int((positive & winner_valid).sum())),
                        "winner_injury_rate": safe_rate(int(fast_fail_and_winner.sum()), int(winner_events.sum())),
                        "old_target_jaccard": jaccard,
                        "incumbent_delta_kill_wrong": np.nan,
                        "incumbent_delta_winner_injury": np.nan,
                        "selection_gate_status": "diagnostic",
                    }
                )
    frontier = pd.DataFrame(rows)
    incumbent = frontier.loc[frontier["candidate_label_id"] == INCUMBENT_LABEL_ID][
        ["denominator_id", "split", "kill_wrong_rate", "winner_injury_rate"]
    ].rename(
        columns={
            "kill_wrong_rate": "incumbent_kill_wrong_rate",
            "winner_injury_rate": "incumbent_winner_injury_rate",
        }
    )
    frontier = frontier.merge(incumbent, on=["denominator_id", "split"], how="left")
    frontier["incumbent_delta_kill_wrong"] = (
        frontier["kill_wrong_rate"] - frontier["incumbent_kill_wrong_rate"]
    )
    frontier["incumbent_delta_winner_injury"] = (
        frontier["winner_injury_rate"] - frontier["incumbent_winner_injury_rate"]
    )
    frontier = frontier.drop(columns=["incumbent_kill_wrong_rate", "incumbent_winner_injury_rate"])
    return frontier


def build_cost_target_bridge(labelled: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    candidate_ids = [INCUMBENT_LABEL_ID, *config["candidate_labels"].keys()]
    rows = []
    for denom, denom_df in labelled.groupby("denominator_id", dropna=False):
        old_fast_fail = bool_series(denom_df["failure_10_label"])
        false_repair = bool_series(denom_df["event_false_repair_20d_label"])
        old_target = old_fast_fail | false_repair
        winner_valid = bool_series(denom_df["horizon_complete_120d"]) & denom_df[
            "event_big_winner_120d_label"
        ].notna()
        winner = bool_series(denom_df["event_big_winner_120d_label"])
        for candidate_id in candidate_ids:
            new_fast_fail = bool_series(denom_df[f"{candidate_id}_label"])
            new_target = new_fast_fail | false_repair
            old_only = old_target & ~new_target
            new_only = new_target & ~old_target
            target_union_n = int((old_target | new_target).sum())
            fast_fail_union_n = int((old_fast_fail | new_fast_fail).sum())
            false_repair_union_n = int((false_repair | false_repair).sum())
            rows.append(
                {
                    "denominator_id": denom,
                    "candidate_label_id": candidate_id,
                    "old_fast_fail_component_positive_n": int(old_fast_fail.sum()),
                    "new_fast_fail_component_positive_n": int(new_fast_fail.sum()),
                    "fast_fail_component_jaccard": safe_rate(
                        int((old_fast_fail & new_fast_fail).sum()),
                        fast_fail_union_n,
                    ),
                    "old_false_repair_component_positive_n": int(false_repair.sum()),
                    "new_false_repair_component_positive_n": int(false_repair.sum()),
                    "false_repair_component_jaccard": safe_rate(
                        int((false_repair & false_repair).sum()),
                        false_repair_union_n,
                    ),
                    "old_target_positive_n": int(old_target.sum()),
                    "new_target_positive_n": int(new_target.sum()),
                    "old_new_both_positive_n": int((old_target & new_target).sum()),
                    "old_only_positive_n": int(old_only.sum()),
                    "new_only_positive_n": int(new_only.sum()),
                    "both_negative_n": int((~old_target & ~new_target).sum()),
                    "jaccard_overlap": safe_rate(int((old_target & new_target).sum()), target_union_n),
                    "hybrid_target_jaccard": safe_rate(int((old_target & new_target).sum()), target_union_n),
                    "old_only_n": int(old_only.sum()),
                    "new_only_n": int(new_only.sum()),
                    "old_only_winner_readout_n": int((old_only & winner_valid).sum()),
                    "new_only_winner_readout_n": int((new_only & winner_valid).sum()),
                    "old_only_winner_rate": safe_rate(
                        int((old_only & winner_valid & winner).sum()),
                        int((old_only & winner_valid).sum()),
                    ),
                    "new_only_winner_rate": safe_rate(
                        int((new_only & winner_valid & winner).sum()),
                        int((new_only & winner_valid).sum()),
                    ),
                    "old_only_power_caveat": int(old_only.sum()) < 30,
                    "new_only_power_caveat": int(new_only.sum()) < 30,
                    "component_failure_10_share": safe_rate(int(new_fast_fail.sum()), int(new_target.sum())),
                    "component_false_repair_20d_share": safe_rate(int(false_repair.sum()), int(new_target.sum())),
                }
            )
    return pd.DataFrame(rows)


def build_pairwise(labelled: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    ids = [INCUMBENT_LABEL_ID, *config["candidate_labels"].keys()]
    primary = labelled.loc[
        labelled["denominator_id"].astype(str) == str(config["selection"]["primary_denominator_id"])
    ].copy()

    def split_subset(split: str) -> pd.DataFrame:
        if split == "all":
            return primary
        return primary.loc[primary["event_split"].astype(str) == split]

    def label_positive_rate(label_id: str, split: str) -> float:
        subset = split_subset(split)
        if subset.empty:
            return np.nan
        evaluable = bool_series(subset[f"{label_id}_evaluable"])
        positive = bool_series(subset[f"{label_id}_label"])
        return safe_rate(int((positive & evaluable).sum()), int(evaluable.sum()))

    def winner_injury(label_id: str) -> float:
        subset = primary
        winner_valid = bool_series(subset["horizon_complete_120d"]) & subset[
            "event_big_winner_120d_label"
        ].notna()
        winner = bool_series(subset["event_big_winner_120d_label"])
        positive = bool_series(subset[f"{label_id}_label"])
        return safe_rate(int((positive & winner_valid & winner).sum()), int((winner_valid & winner).sum()))

    def cost_target_rate(label_id: str) -> float:
        target = target_from_candidate(primary, label_id)
        return safe_rate(int(target.sum()), len(primary))

    def not_evaluable_share(label_id: str) -> float:
        if primary.empty:
            return np.nan
        evaluable = bool_series(primary[f"{label_id}_evaluable"])
        return safe_rate(int((~evaluable).sum()), len(primary))

    rows = []
    for i, left_id in enumerate(ids):
        left = labelled[f"{left_id}_label"]
        for right_id in ids[i + 1 :]:
            right = labelled[f"{right_id}_label"]
            valid = left.notna() & right.notna()
            left_pos = bool_series(left)
            right_pos = bool_series(right)
            inter = int((left_pos & right_pos & valid).sum())
            union = int(((left_pos | right_pos) & valid).sum())
            left_train = label_positive_rate(left_id, "train")
            right_train = label_positive_rate(right_id, "train")
            left_validation = label_positive_rate(left_id, "validation")
            right_validation = label_positive_rate(right_id, "validation")
            left_robustness = label_positive_rate(left_id, "robustness")
            right_robustness = label_positive_rate(right_id, "robustness")
            left_injury = winner_injury(left_id)
            right_injury = winner_injury(right_id)
            left_cost_target = cost_target_rate(left_id)
            right_cost_target = cost_target_rate(right_id)
            left_not_eval = not_evaluable_share(left_id)
            right_not_eval = not_evaluable_share(right_id)
            rows.append(
                {
                    "left_label_id": left_id,
                    "right_label_id": right_id,
                    "jaccard_overlap": safe_rate(inter, union),
                    "cohens_kappa": cohen_kappa_from_binary(left, right),
                    "positive_set_overlap": safe_rate(inter, int((left_pos & valid).sum())),
                    "valid_n": int(valid.sum()),
                    "left_positive_rate": safe_rate(int((left_pos & valid).sum()), int(valid.sum())),
                    "right_positive_rate": safe_rate(int((right_pos & valid).sum()), int(valid.sum())),
                    "left_train_positive_rate": left_train,
                    "right_train_positive_rate": right_train,
                    "train_positive_rate_difference": abs(left_train - right_train),
                    "left_validation_positive_rate": left_validation,
                    "right_validation_positive_rate": right_validation,
                    "validation_positive_rate_difference": abs(left_validation - right_validation),
                    "left_robustness_positive_rate": left_robustness,
                    "right_robustness_positive_rate": right_robustness,
                    "robustness_positive_rate_difference": abs(left_robustness - right_robustness),
                    "left_winner_injury_rate": left_injury,
                    "right_winner_injury_rate": right_injury,
                    "winner_injury_difference": abs(left_injury - right_injury),
                    "left_cost_target_positive_rate": left_cost_target,
                    "right_cost_target_positive_rate": right_cost_target,
                    "cost_target_positive_rate_difference": abs(left_cost_target - right_cost_target),
                    "left_not_evaluable_share_primary_denominator": left_not_eval,
                    "right_not_evaluable_share_primary_denominator": right_not_eval,
                    "not_evaluable_share_primary_denominator": max(left_not_eval, right_not_eval),
                }
            )
    return pd.DataFrame(rows)


def build_regime_audit(canonical: pd.DataFrame, panel: pd.DataFrame, e1: pd.DataFrame) -> pd.DataFrame:
    panel_dates = panel[["date", "market_regime_bucket"]].drop_duplicates()
    date_nunique = panel_dates.groupby("date")["market_regime_bucket"].nunique()
    market_wide_ok = int((date_nunique > 1).sum()) == 0
    date_regime = panel_dates.drop_duplicates("date").rename(
        columns={"date": "event_t0_date", "market_regime_bucket": "reconstructed_event_regime_bucket"}
    )
    event = canonical[["event_t0_date", "event_split", "event_regime_bucket", "market_regime_bucket"]].merge(
        date_regime, on="event_t0_date", how="left"
    )
    event["match"] = event["event_regime_bucket"].astype(str) == event[
        "reconstructed_event_regime_bucket"
    ].astype(str)
    rows = []
    for split in SPLITS:
        cell = event if split == "all" else event.loc[event["event_split"].astype(str) == split]
        rows.append(
            {
                "split": split,
                "regime_source_artifact": "candidate_family_canonical_events.csv.gz",
                "event_regime_source_artifact": "candidate_family_canonical_events.csv.gz",
                "event_regime_source_column": "event_regime_bucket",
                "event_market_regime_alias_column": "market_regime_bucket",
                "event_market_regime_alias_agreement": float(
                    (cell["event_regime_bucket"].astype(str) == cell["market_regime_bucket"].astype(str)).mean()
                )
                if len(cell)
                else np.nan,
                "episode_regime_source_artifact": "candidate_family_capture.parquet",
                "episode_regime_source_column": "market_regime_bucket",
                "event_episode_regime_same_source_flag": False,
                "event_regime_reconstruction_source": "cross_section_feature_panel.parquet",
                "event_regime_reconstruction_join_key": "event_t0_date",
                "feature_panel_market_wide_regime_check": "pass" if market_wide_ok else "fail",
                "t0_visible_flag": True,
                "future_join_count": 0,
                "published_reconstructed_consistency": float(cell["match"].mean()) if len(cell) else np.nan,
                "risk_on_reconstructed_not_published_share": safe_rate(
                    int(
                        (
                            (cell["reconstructed_event_regime_bucket"].astype(str) == "risk_on")
                            & (cell["event_regime_bucket"].astype(str) != "risk_on")
                        ).sum()
                    ),
                    len(cell),
                ),
                "published_risk_on_not_reconstructed_share": safe_rate(
                    int(
                        (
                            (cell["event_regime_bucket"].astype(str) == "risk_on")
                            & (cell["reconstructed_event_regime_bucket"].astype(str) != "risk_on")
                        ).sum()
                    ),
                    len(cell),
                ),
                "risk_off_reconstructed_consistency_readonly": np.nan,
                "transition_drift_context": "transition_readout_only_not_training_scope",
            }
        )
    if not e1.empty:
        e1_join = e1[["event_t0_date", "event_regime_bucket"]].merge(date_regime, on="event_t0_date", how="left")
        riskoff = e1_join.loc[e1_join["event_regime_bucket"].astype(str) == "risk_off"]
        rows[0]["risk_off_reconstructed_consistency_readonly"] = (
            float(
                (
                    riskoff["reconstructed_event_regime_bucket"].astype(str)
                    == riskoff["event_regime_bucket"].astype(str)
                ).mean()
            )
            if len(riskoff)
            else np.nan
        )
    return pd.DataFrame(rows)


def build_source_pool_audit(
    mapping: pd.DataFrame,
    reconstruct: pd.DataFrame,
    base: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for scope_id in (R_CORE_SCOPE, R6_SCOPE, E1_SCOPE):
        recon = reconstruct.loc[reconstruct["candidate_scope_id"].astype(str) == scope_id]
        mapped = mapping.loc[mapping["candidate_scope_id"].astype(str) == scope_id]
        selected_count = int((base["source_pool_id"] == scope_id).sum())
        rows.append(
            {
                "source_pool_id": scope_id,
                "scope_type": "contract_scope",
                "scope_status": recon["scope_status"].iloc[0] if not recon.empty else "missing",
                "scope_mapping_status": mapped["scope_mapping_status"].iloc[0] if not mapped.empty else "missing",
                "hard_gate_eligible_flag": bool(recon["hard_gate_eligible_flag"].iloc[0]) if not recon.empty else False,
                "source_row_count": int(recon["source_row_count"].iloc[0]) if not recon.empty else np.nan,
                "selected_event_count": selected_count,
                "accepted_difference_reason": "08_A_H_accepted_r_core_minus_15" if scope_id == R_CORE_SCOPE else "",
                "status": "pass" if not recon.empty else "blocked",
            }
        )
    riskoff_count = int((base["denominator_id"] == RISK_OFF_E1_DENOM).sum())
    rows.append(
        {
            "source_pool_id": RISK_OFF_E1_DENOM,
            "scope_type": "derived_readonly_scope",
            "scope_status": "derived_from_07_E1_only_event_regime_risk_off_horizon_complete_10d",
            "scope_mapping_status": "not_in_contract_by_design",
            "hard_gate_eligible_flag": False,
            "source_row_count": riskoff_count,
            "selected_event_count": riskoff_count,
            "accepted_difference_reason": "derived_readonly_scope_exempt_from_scope_mapping_contract",
            "status": "pass" if riskoff_count > 0 else "blocked",
        }
    )
    return pd.DataFrame(rows)


def candidate_mechanism_contract(candidate_eval: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    rows.append(
        {
            "label_id": INCUMBENT_LABEL_ID,
            "mechanism_family": "incumbent_fixed_mae10",
            "series_used": "upstream_failure_10_label",
            "lookback_window": "",
            "as_of_rule": "upstream_label_contract",
            "touch_price_field": "upstream",
            "feature_overlap_risk": "low",
            "selected_fast_fail_component_flag": False,
            "selected_cost_target_component_flag": False,
            "not_evaluable_policy": "upstream_failure_10_complete",
        }
    )
    for cid, spec in config["candidate_labels"].items():
        rows.append(
            {
                "label_id": cid,
                "mechanism_family": spec["mechanism_family"],
                "series_used": "qfq_daily_ohlc",
                "lookback_window": spec.get("sigma_window")
                or spec.get("atr_window")
                or spec.get("swing_lookback")
                or spec.get("ema_span")
                or 10,
                "as_of_rule": "pre_trade_time_for_barrier_estimator;future_10d_only_for_touch",
                "touch_price_field": "low",
                "feature_overlap_risk": "direct" if spec["mechanism_family"] in {"atr_scaled", "vol_scaled", "structural"} else "related",
                "selected_fast_fail_component_flag": False,
                "selected_cost_target_component_flag": False,
                "not_evaluable_policy": "mark_not_evaluable_no_implicit_denominator_change",
            }
        )
    return pd.DataFrame(rows)


def select_labels(frontier: pd.DataFrame, candidate_eval: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    sel = config["selection"]
    train = frontier.loc[
        (frontier["denominator_id"] == sel["primary_denominator_id"])
        & (frontier["split"] == "train")
        & (frontier["candidate_label_id"] != INCUMBENT_LABEL_ID)
    ].copy()
    status = dict(zip(candidate_eval["candidate_label_id"], candidate_eval["candidate_label_status"]))
    train["candidate_label_status"] = train["candidate_label_id"].map(status)
    allowed = {cid for cid, spec in config["candidate_labels"].items() if spec.get("selected_allowed", True)}
    train["bound_gate_pass"] = (
        train["candidate_label_id"].isin(allowed)
        & (train["candidate_label_status"] == "evaluable")
        & (train["not_evaluable_share"] <= float(sel["train_not_evaluable_share_max"]))
        & (train["positive_rate"] >= float(sel["train_positive_rate_min"]))
        & (train["positive_rate"] <= float(sel["train_positive_rate_max"]))
        & (train["episode_winner_recall_retention"] >= float(sel["train_episode_winner_recall_retention_min"]))
    )
    eligible = train.loc[train["bound_gate_pass"]].copy()
    selected: list[pd.Series] = []
    for _, row in eligible.sort_values(
        ["kill_wrong_rate", "winner_injury_rate", "positive_rate"],
        ascending=[True, True, True],
        na_position="last",
    ).iterrows():
        family = config["candidate_labels"][row["candidate_label_id"]]["mechanism_family"]
        if any(config["candidate_labels"][r["candidate_label_id"]]["mechanism_family"] == family for r in selected):
            continue
        dominated = False
        same_family = eligible.loc[
            eligible["candidate_label_id"].map(lambda cid: config["candidate_labels"][cid]["mechanism_family"])
            == family
        ]
        for _, other in same_family.iterrows():
            if other["candidate_label_id"] == row["candidate_label_id"]:
                continue
            if (
                other["kill_wrong_rate"] <= row["kill_wrong_rate"]
                and other["winner_injury_rate"] <= row["winner_injury_rate"]
                and (
                    other["kill_wrong_rate"] < row["kill_wrong_rate"]
                    or other["winner_injury_rate"] < row["winner_injury_rate"]
                )
            ):
                dominated = True
                break
        if not dominated:
            selected.append(row)
        if len(selected) >= int(sel["selected_label_max_count"]):
            break
    rows = []
    selected_rank = {r["candidate_label_id"]: rank for rank, r in enumerate(selected, start=1)}
    for _, row in train.loc[train["candidate_label_status"] == "evaluable"].iterrows():
        cid = row["candidate_label_id"]
        selected_flag = cid in selected_rank
        rows.append(
            {
                "selected_target_id": f"{cid}__or_false_repair_20d",
                "selected_fast_fail_label_id": cid,
                "false_repair_component_id": FALSE_REPAIR_COMPONENT_ID,
                "selection_rank": selected_rank[cid] if selected_flag else np.nan,
                "selection_status": "selected" if selected_flag else "rejected",
                "selection_reason": "train_pareto_selected" if selected_flag else ("bound_gate_failed" if not row["bound_gate_pass"] else "not_selected_after_pareto"),
                "mechanism_family": config["candidate_labels"][cid]["mechanism_family"],
                "primary_denominator_id": sel["primary_denominator_id"],
                "candidate_label_status": row["candidate_label_status"],
                "source_caveated": False,
                "label_contract_hash": "",
                "event_binding_hash": "",
                "usable_for_09C_supported_gate": bool(selected_flag),
                "winner_readout_label": "event_big_winner_120d_label",
                "winner_readout_completeness_rule": "horizon_complete_120d_true_drop_null_winner",
                "winner_censoring_status_mapping": "candidate_outcome_120d_status_v1",
                "cost_target_label_t1_rule": "20d_cost_horizon",
                "train_positive_rate": row["positive_rate"],
                "train_kill_wrong_rate": row["kill_wrong_rate"],
                "train_winner_injury_rate": row["winner_injury_rate"],
                "train_episode_winner_recall_retention": row["episode_winner_recall_retention"],
                "max_split_positive_rate_spread": np.nan,
            }
        )
    return pd.DataFrame(rows)


def selected_oos_positive_rate_spread(
    frontier: pd.DataFrame,
    candidate_id: str,
    denominator_id: str,
) -> float:
    cell = frontier.loc[
        (frontier["candidate_label_id"].astype(str) == str(candidate_id))
        & (frontier["denominator_id"].astype(str) == str(denominator_id))
        & (frontier["split"].isin(["train", "validation", "robustness"]))
    ]
    rates = cell["positive_rate"].dropna()
    if rates.empty:
        return np.nan
    return float(rates.max() - rates.min())


def enforce_oos_downgrade(
    selected_contract: pd.DataFrame,
    frontier: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, bool, str]:
    out = selected_contract.copy()
    selected_mask = out["selection_status"] == "selected"
    if not bool(selected_mask.any()):
        return out, False, ""
    threshold = float(config["selection"]["oos_positive_rate_spread_force_diagnostic_threshold"])
    denominator_id = str(config["selection"]["primary_denominator_id"])
    spread_rows: list[str] = []
    for idx, row in out.loc[selected_mask].iterrows():
        spread = selected_oos_positive_rate_spread(
            frontier,
            str(row["selected_fast_fail_label_id"]),
            denominator_id,
        )
        out.loc[idx, "max_split_positive_rate_spread"] = spread
        if pd.notna(spread) and spread > threshold:
            spread_rows.append(f"{row['selected_fast_fail_label_id']}={spread:.6f}")
    if not spread_rows:
        return out, False, ""
    out.loc[selected_mask, "selection_status"] = "diagnostic_only"
    out.loc[selected_mask, "selection_reason"] = "oos_positive_rate_spread_force_diagnostic"
    out.loc[selected_mask, "usable_for_09C_supported_gate"] = False
    return out, True, ";".join(spread_rows)


def annotate_frontier_selection_gate(
    frontier: pd.DataFrame,
    selected_contract: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    out = frontier.copy()
    out["selection_gate_status"] = "diagnostic"
    primary = str(config["selection"]["primary_denominator_id"])
    reasons = dict(
        zip(
            selected_contract["selected_fast_fail_label_id"].astype(str),
            selected_contract["selection_reason"].astype(str),
        )
    )
    statuses = dict(
        zip(
            selected_contract["selected_fast_fail_label_id"].astype(str),
            selected_contract["selection_status"].astype(str),
        )
    )
    mask = (out["denominator_id"].astype(str) == primary) & (out["split"].astype(str) == "train")
    for idx, row in out.loc[mask].iterrows():
        cid = str(row["candidate_label_id"])
        if cid == INCUMBENT_LABEL_ID:
            continue
        reason = reasons.get(cid, "")
        status = statuses.get(cid, "")
        if status == "selected":
            out.loc[idx, "selection_gate_status"] = "pass"
        elif status == "diagnostic_only":
            out.loc[idx, "selection_gate_status"] = "diagnostic"
        elif reason == "bound_gate_failed":
            out.loc[idx, "selection_gate_status"] = "fail"
        elif reason:
            out.loc[idx, "selection_gate_status"] = "pass"
    return out


def cost_horizon_t1_date(row: pd.Series, cache: PriceCache, horizon: int = 20) -> str:
    if pd.isna(row.get("trade_open_date")):
        return ""
    prices = cache.load(str(row.get("instrument")))
    if prices is None:
        return ""
    matches = prices.index[prices["date"] == str(row.get("trade_open_date"))].tolist()
    if not matches:
        return ""
    end_pos = int(matches[0]) + horizon - 1
    if end_pos >= len(prices):
        return ""
    return str(prices.iloc[end_pos]["date"])


def touch_offset_sessions(
    touch_pos: pd.Series,
    trade_open_pos: pd.Series,
    label: pd.Series,
) -> pd.Series:
    touch = pd.to_numeric(touch_pos, errors="coerce")
    trade = pd.to_numeric(trade_open_pos, errors="coerce")
    triggered = bool_series(label) & touch.ge(0) & trade.notna() & touch.ge(trade)
    offset = (touch - trade).where(triggered, -1)
    return offset.astype("Int64")


def selected_binding(labelled: pd.DataFrame, selected_contract: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    selected = selected_contract.loc[selected_contract["selection_status"] == "selected"]
    if selected.empty:
        selected_id = INCUMBENT_LABEL_ID
        selected_target_id = f"{INCUMBENT_LABEL_ID}__or_false_repair_20d"
    else:
        primary = selected.sort_values("selection_rank", na_position="last").iloc[0]
        selected_id = str(primary["selected_fast_fail_label_id"])
        selected_target_id = str(primary["selected_target_id"])
    bind = labelled.copy()
    bind["selected_target_id"] = selected_target_id
    bind["selected_fast_fail_label_id"] = selected_id
    bind["selected_fast_fail_10_label"] = bind[f"{selected_id}_label"]
    bind["selected_fast_fail_touch_date"] = bind[f"{selected_id}_touch_date"]
    bind["selected_fast_fail_touch_pos"] = bind[f"{selected_id}_touch_pos"]
    bind["selected_fast_fail_touch_offset_sessions"] = touch_offset_sessions(
        bind["selected_fast_fail_touch_pos"],
        bind["trade_open_pos"],
        bind["selected_fast_fail_10_label"],
    )
    bind["selected_fast_fail_barrier_id"] = bind[f"{selected_id}_barrier_id"]
    bind["frozen_false_repair_20d_label"] = bind["event_false_repair_20d_label"]
    bind["selected_cost_bad_10_20_target"] = (
        bool_series(bind["selected_fast_fail_10_label"])
        | bool_series(bind["frozen_false_repair_20d_label"])
    )
    stock_dir = topic_path(config["paths"]["stock_daily_csv_dir"])
    cache = PriceCache(stock_dir)
    bind["label_t1_date"] = [cost_horizon_t1_date(row, cache, 20) for _, row in bind.iterrows()]
    selected_evaluable = bool_series(bind[f"{selected_id}_evaluable"])
    false_repair_complete = bool_series(bind.get("event_false_repair_20d_complete", pd.Series(False, index=bind.index)))
    horizon_20_complete = bool_series(bind["horizon_complete_20d"])
    non_exec = bind["candidate_outcome_120d_status"].astype(str).eq("non_executable_next_open")
    bind["censoring_status"] = np.select(
        [
            non_exec,
            selected_evaluable & false_repair_complete & horizon_20_complete & bind["label_t1_date"].astype(str).ne(""),
            ~horizon_20_complete,
        ],
        ["non_executable", "complete", "censored"],
        default="not_evaluable",
    )
    cols = [
        "sample_id",
        "selected_target_id",
        "selected_fast_fail_label_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "trade_time",
        "event_split",
        "source_pool_id",
        "event_regime_bucket",
        "episode_regime_bucket",
        "denominator_id",
        "horizon_complete_10d",
        "horizon_complete_20d",
        "horizon_complete_120d",
        "candidate_outcome_120d_status",
        "selected_fast_fail_10_label",
        "selected_fast_fail_touch_date",
        "selected_fast_fail_touch_pos",
        "selected_fast_fail_touch_offset_sessions",
        "selected_fast_fail_barrier_id",
        "frozen_false_repair_20d_label",
        "selected_cost_bad_10_20_target",
        "event_big_winner_120d_label",
        "event_super_winner_120d_label",
        "event_near_winner_120d_label",
        "winner_censoring_status",
        "label_t1_date",
        "censoring_status",
    ]
    return bind[[c for c in cols if c in bind.columns]].copy()


def binding_summary(binding: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for denom, denom_df in binding.groupby("denominator_id", dropna=False):
        for split in SPLITS:
            cell = denom_df if split == "all" else denom_df.loc[denom_df["event_split"].astype(str) == split]
            if cell.empty:
                continue
            status = cell["candidate_outcome_120d_status"].fillna("")
            rows.append(
                {
                    "denominator_id": denom,
                    "split": split,
                    "binding_row_n": len(cell),
                    "unique_sample_n": cell["sample_id"].nunique(),
                    "unique_canonical_event_n": cell["canonical_event_id"].nunique(),
                    "winner_120_complete_n": int(bool_series(cell["horizon_complete_120d"]).sum()),
                    "winner_120_incomplete_n": int((~bool_series(cell["horizon_complete_120d"])).sum()),
                    "winner_120_incomplete_non_executable_n": int((status == "non_executable_next_open").sum()),
                    "winner_120_incomplete_censored_n": int((status == "censored_incomplete_horizon").sum()),
                    "null_winner_label_n": int(cell["event_big_winner_120d_label"].isna().sum()),
                    "candidate_outcome_120d_status_values": compact_join(status),
                }
            )
    return pd.DataFrame(rows)


def update_mechanism_selected_flags(mech: pd.DataFrame, selected_contract: pd.DataFrame) -> pd.DataFrame:
    out = mech.copy()
    selected_ids = set(
        selected_contract.loc[
            selected_contract["selection_status"] == "selected", "selected_fast_fail_label_id"
        ].astype(str)
    )
    out["selected_fast_fail_component_flag"] = out["label_id"].isin(selected_ids)
    out["selected_cost_target_component_flag"] = out["selected_fast_fail_component_flag"]
    return out


def report_text(decision: str, frontier: pd.DataFrame, selected: pd.DataFrame) -> str:
    selected_rows = selected.loc[selected["selection_status"] == "selected"].sort_values(
        "selection_rank", na_position="last"
    )
    selected_label = (
        ", ".join(selected_rows["selected_fast_fail_label_id"].astype(str).tolist())
        if not selected_rows.empty
        else "无"
    )
    primary_label = (
        str(selected_rows.iloc[0]["selected_fast_fail_label_id"]) if not selected_rows.empty else "无"
    )
    primary = frontier.loc[
        (frontier["denominator_id"] == RISK_ON_R_CORE_DENOM) & (frontier["split"] == "train")
    ].copy()
    top = primary.sort_values(["kill_wrong_rate", "winner_injury_rate"], na_position="last").head(8)
    lines = [
        "# 09A Fast-Fail Label Frontier Report",
        "",
        f"- decision: `{decision}`",
        f"- selected fast-fail label: `{selected_label}`",
        f"- event binding primary fast-fail label: `{primary_label}`",
        "- 09A 只做 label diagnostic，不训练模型；09C 必须读取事件级 binding。",
        "",
        "## Train Frontier Snapshot",
        "",
        "| candidate | positive_rate | kill_wrong | winner_injury | episode_retention | status |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in top.iterrows():
        lines.append(
            "| {candidate} | {pos:.4f} | {kw:.4f} | {wi:.4f} | {ret:.4f} | {status} |".format(
                candidate=row["candidate_label_id"],
                pos=0.0 if pd.isna(row["positive_rate"]) else row["positive_rate"],
                kw=0.0 if pd.isna(row["kill_wrong_rate"]) else row["kill_wrong_rate"],
                wi=0.0 if pd.isna(row["winner_injury_rate"]) else row["winner_injury_rate"],
                ret=0.0
                if pd.isna(row["episode_winner_recall_retention"])
                else row["episode_winner_recall_retention"],
                status=row["selection_gate_status"],
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `winner_censoring_status` 由上游 `candidate_outcome_120d_status` 固定映射。",
            "- `event_regime_bucket` 的 PIT 性来自 `cross_section_feature_panel.parquet` 的 as-of 重建一致率，不来自 canonical 表列名。",
            "- `risk_off_e1_horizon_complete_readonly` 是 derived read-only scope，不参与 09C training gate。",
        ]
    )
    return "\n".join(lines)


def barrier_description(label_id: str, spec: dict[str, Any]) -> str:
    family = spec["mechanism_family"]
    if family == "fixed_mae10":
        return f"trade_open_price * (1 {float(spec['barrier_pct']):+.4f})"
    if family == "vol_scaled":
        return f"trade_open_price * (1 - {float(spec['sigma_multiplier']):.2f} * trailing_sigma{int(spec['sigma_window'])})"
    if family == "atr_scaled":
        return f"trade_open_price - {float(spec['atr_multiplier']):.2f} * trailing_ATR{int(spec['atr_window'])}"
    if family == "structural":
        rule = str(spec.get("structural_rule"))
        if rule == "event_low":
            return "event_t0_date low"
        if rule == "swing_low":
            return f"prior {int(spec['swing_lookback'])}D swing low before trade_time"
        if rule == "ema":
            return f"EMA{int(spec['ema_span'])} computed before trade_time"
    return label_id


def contract_text(selected: pd.DataFrame, config: dict[str, Any]) -> str:
    selected_rows = selected.loc[selected["selection_status"] == "selected"].sort_values(
        "selection_rank", na_position="last"
    )
    labels = selected_rows["selected_fast_fail_label_id"].astype(str).tolist()
    primary = labels[0] if labels else "none"
    rows = [
        "| label_id | mechanism | t0 | trade_time | fast_fail_t1 | price_field | adjustment_policy | barrier | censoring |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        "| incumbent_failure_10_label | incumbent_fixed_mae10 | event_t0_date | trade_open_date/open | upstream failure_10 t1 | upstream | upstream 08 label contract | upstream failure_10_label | failure_10_complete=false -> not_evaluable |",
    ]
    for cid, spec in config["candidate_labels"].items():
        rows.append(
            "| {cid} | {family} | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | {barrier} | missing path / incomplete 10D / missing barrier -> not_evaluable |".format(
                cid=cid,
                family=spec["mechanism_family"],
                barrier=barrier_description(cid, spec),
            )
        )
    lines = [
        "# 09A Fast-Fail Label Contract",
        "",
        f"- selected_fast_fail_10_label: `{';'.join(labels) if labels else 'none'}`",
        f"- event_binding_primary_fast_fail_label: `{primary}`",
        f"- selected_cost_bad_10_20_target: `selected_fast_fail_10_label OR {FALSE_REPAIR_COMPONENT_ID}`",
        "- selected_cost_bad_10_20_target label_t1_date: 20D cost horizon end date, used for purged CV / embargo / uniqueness.",
        "- same-bar tie handling: first daily row whose `low <= barrier` is the touch row; if no touch inside 10D, label is false.",
        "- selected_fast_fail_touch_pos: absolute row index in the instrument daily price file; do not use it as horizon offset.",
        "- selected_fast_fail_touch_offset_sessions: trading-session offset from trade_time to first touch; no touch / not evaluable is -1.",
        "- false-repair component: frozen upstream `event_false_repair_20d_label`; 09A does not redefine it.",
        "- winner_readout_label: `event_big_winner_120d_label`; super/near winner labels are sensitivity only.",
        "- winner_censoring_status: mapped from `candidate_outcome_120d_status`.",
        "- existing `failure_10_label` is preserved as incumbent baseline and is never overwritten.",
        "",
        "## Candidate Label Definitions",
        "",
        *rows,
        "",
        "## Winner Censoring Mapping",
        "",
        "| upstream candidate_outcome_120d_status | winner_censoring_status |",
        "| --- | --- |",
        "| not_missing | complete |",
        "| censored_incomplete_horizon | incomplete_120d |",
        "| non_executable_next_open | non_executable |",
        "| missing / unknown | not_evaluable |",
    ]
    return "\n".join(lines)


def regime_report_text(regime: pd.DataFrame) -> str:
    lines = [
        "# 09A Regime PIT Audit",
        "",
        "本审计只确认 09A 使用的事件级 regime 在 t0 可见语义下可复核，不用于重启 transition modeling。",
        "",
        "| split | t0_visible | future_join_count | reconstructed_consistency | alias_agreement |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in regime.iterrows():
        lines.append(
            "| {split} | {visible} | {future} | {consistency:.6f} | {alias:.6f} |".format(
                split=row["split"],
                visible=str(bool(row["t0_visible_flag"])).lower(),
                future=int(row["future_join_count"]),
                consistency=0.0
                if pd.isna(row["published_reconstructed_consistency"])
                else float(row["published_reconstructed_consistency"]),
                alias=0.0
                if pd.isna(row["event_market_regime_alias_agreement"])
                else float(row["event_market_regime_alias_agreement"]),
            )
        )
    lines.extend(
        [
            "",
            "## Source Contract",
            "",
            "- event_regime_source_artifact: `candidate_family_canonical_events.csv.gz`",
            "- event_regime_reconstruction_source: `cross_section_feature_panel.parquet`",
            "- episode_regime_source_artifact: `candidate_family_capture.parquet` / membership readout",
            "- transition usage: diagnostic only",
        ]
    )
    return "\n".join(lines)


def build_manifest(
    decision: str,
    config: dict[str, Any],
    input_frame: pd.DataFrame,
    outputs: dict[str, Path],
    statuses: dict[str, str],
) -> dict[str, Any]:
    output_hashes = {
        key: file_sha256(path)
        for key, path in sorted(outputs.items())
        if key != "manifest" and path.exists() and path.is_file()
    }
    input_hashes = {
        str(row["input_id"]): row["sha256"]
        for _, row in input_frame.iterrows()
        if str(row.get("sha256", ""))
    }
    input_paths = {
        str(row["input_id"]): str(row["path"])
        for _, row in input_frame.iterrows()
        if str(row.get("path", ""))
    }
    return {
        "experiment_id": config["experiment"]["id"],
        "phase": config["experiment"]["phase"],
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_revision(PROJECT_ROOT),
        "decision": decision,
        "source_caveated": decision == DECISION_SELECTED_CAVEATED,
        "input_paths": input_paths,
        "input_hashes": input_hashes,
        "output_hashes": output_hashes,
        "config_hash": stable_hash(config),
        **statuses,
        "outputs": {key: str(path) for key, path in outputs.items()},
    }


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": INPUT_AUDIT_DIR / "input_artifact_audit.csv",
        "source_pool_reconstruction_audit": INPUT_AUDIT_DIR / "source_pool_reconstruction_audit.csv",
        "regime_label_pit_audit": FRONTIER_TABLE_DIR / "regime_label_pit_audit.csv",
        "regime_label_pit_audit_report": FRONTIER_REPORT_DIR / "regime_label_pit_audit.md",
        "candidate_label_evaluability_audit": FRONTIER_TABLE_DIR / "candidate_label_evaluability_audit.csv",
        "fast_fail_label_frontier": FRONTIER_TABLE_DIR / "fast_fail_label_frontier.csv",
        "cost_target_bridge": FRONTIER_TABLE_DIR / "cost_target_bridge.csv",
        "label_pairwise_agreement": FRONTIER_TABLE_DIR / "label_pairwise_agreement.csv",
        "label_mechanism_contract": FRONTIER_TABLE_DIR / "label_mechanism_contract.csv",
        "selected_label_contract": FRONTIER_TABLE_DIR / "selected_label_contract.csv",
        "selected_label_event_binding_summary": FRONTIER_TABLE_DIR / "selected_label_event_binding_summary.csv",
        "selected_label_event_bindings": FRONTIER_LOCAL_CACHE_DIR / "selected_label_event_bindings.parquet",
        "report": REPORT_DIR / "09A_fast_fail_label_frontier_report.md",
        "fast_fail_label_contract": FRONTIER_REPORT_DIR / "fast_fail_label_contract.md",
        "manifest": MANIFEST_DIR / "09A_fast_fail_label_frontier_manifest.json",
    }


def run_frontier(config_path: Path = CONFIG_PATH, *, check_inputs_only: bool = False) -> dict[str, Any]:
    config = load_config(config_path)
    paths = {key: topic_path(value) for key, value in config["paths"].items()}
    outputs = output_paths()
    for path in {p.parent for p in outputs.values()}:
        path.mkdir(parents=True, exist_ok=True)

    input_frame, input_failures = input_audit(config)
    write_df(outputs["input_artifact_audit"], input_frame)
    if check_inputs_only:
        return {"decision": "check_inputs", "input_failures": input_failures}
    if input_failures:
        manifest = build_manifest(
            DECISION_INPUT_BLOCKED,
            config,
            input_frame,
            {"manifest": outputs["manifest"], "input_artifact_audit": outputs["input_artifact_audit"]},
            {
                "source_pool_reconstruction_status": "not_run",
                "regime_label_pit_status": "not_run",
                "selected_target_label": "",
            },
        )
        write_json(outputs["manifest"], manifest)
        return {"decision": DECISION_INPUT_BLOCKED, "input_failures": input_failures}

    canonical_08 = read_csv(paths["upstream_08_canonical_events"])
    canonical_07 = read_csv(paths["upstream_07_canonical_events"])
    labels_08 = pd.read_parquet(paths["upstream_08_event_labels"])
    labels_07 = pd.read_parquet(paths["upstream_07_event_labels"])
    membership = pd.read_parquet(paths["upstream_08_membership"])
    panel = pd.read_parquet(paths["upstream_08_feature_panel"])
    mapping = read_csv(paths["candidate_scope_mapping_contract"])
    reconstruct = read_csv(paths["candidate_scope_reconstructability_audit"])

    base = build_denominator_events(canonical_08, labels_08, canonical_07, labels_07)
    base = with_episode_info(base, membership)
    source_audit = build_source_pool_audit(mapping, reconstruct, base)
    write_df(outputs["source_pool_reconstruction_audit"], source_audit)
    if (source_audit["status"] != "pass").any():
        decision = DECISION_SOURCE_POOL_BLOCKED
    else:
        decision = DECISION_DIAGNOSTIC

    regime = build_regime_audit(canonical_08, panel, rebuild_e1(canonical_07))
    write_df(outputs["regime_label_pit_audit"], regime)
    write_text(outputs["regime_label_pit_audit_report"], regime_report_text(regime))
    if (
        regime.loc[regime["split"] == "robustness", "published_reconstructed_consistency"].iloc[0]
        < 0.985
    ):
        decision = DECISION_REGIME_BLOCKED

    labelled, candidate_eval = compute_candidate_labels(base, config)
    frontier = build_frontier(labelled, candidate_eval, config)
    bridge = build_cost_target_bridge(labelled, config)
    pairwise = build_pairwise(labelled, config)
    selected = select_labels(frontier, candidate_eval, config)
    selected, oos_forced_diagnostic, oos_forced_reason = enforce_oos_downgrade(
        selected, frontier, config
    )
    frontier = annotate_frontier_selection_gate(frontier, selected, config)
    selected_rows = selected.loc[selected["selection_status"] == "selected"].sort_values(
        "selection_rank", na_position="last"
    )
    selected_ids = selected_rows["selected_fast_fail_label_id"]
    primary_selected_id = str(selected_ids.iloc[0]) if len(selected_ids) > 0 else ""
    if decision not in {DECISION_SOURCE_POOL_BLOCKED, DECISION_REGIME_BLOCKED}:
        if oos_forced_diagnostic:
            decision = DECISION_DIAGNOSTIC
        elif len(selected_ids) > 0:
            source_caveated = True
            decision = DECISION_SELECTED_CAVEATED if source_caveated else DECISION_SELECTED
        else:
            decision = DECISION_DIAGNOSTIC
    selected["source_caveated"] = decision == DECISION_SELECTED_CAVEATED
    binding = selected_binding(labelled, selected, config)
    summary = binding_summary(binding)
    mech = update_mechanism_selected_flags(candidate_mechanism_contract(candidate_eval, config), selected)
    selected_contract_path_placeholder = outputs["fast_fail_label_contract"]
    write_text(outputs["fast_fail_label_contract"], contract_text(selected, config))
    selected["label_contract_hash"] = file_sha256(selected_contract_path_placeholder)

    write_df(outputs["candidate_label_evaluability_audit"], candidate_eval)
    write_df(outputs["fast_fail_label_frontier"], frontier)
    write_df(outputs["cost_target_bridge"], bridge)
    write_df(outputs["label_pairwise_agreement"], pairwise)
    write_df(outputs["label_mechanism_contract"], mech)
    write_df(outputs["selected_label_contract"], selected)
    write_df(outputs["selected_label_event_bindings"], binding)
    event_binding_hash = file_sha256(outputs["selected_label_event_bindings"])
    selected["event_binding_hash"] = event_binding_hash
    write_df(outputs["selected_label_contract"], selected)
    write_df(outputs["selected_label_event_binding_summary"], summary)
    write_text(outputs["report"], report_text(decision, frontier, selected))

    statuses = {
        "source_pool_reconstruction_status": "pass"
        if (source_audit["status"] == "pass").all()
        else "blocked",
        "regime_label_pit_status": "pass" if decision != DECISION_REGIME_BLOCKED else "blocked",
        "event_regime_source_status": "asof_reconstructed_from_feature_panel",
        "episode_regime_source_status": "readout_from_membership_or_capture",
        "derived_readonly_scope_status": "pass",
        "selected_target_label": ";".join(selected_ids.astype(str).tolist()),
        "event_binding_primary_fast_fail_label": primary_selected_id,
        "selected_target_contract_hash": file_sha256(outputs["fast_fail_label_contract"]),
        "selected_label_event_bindings_hash": event_binding_hash,
        "sample_id_generation_status": "canonical_event_id_else_stable_hash",
        "label_bridge_status": "complete",
        "bridge_power_caveat_status": "reported",
        "candidate_label_evaluability_status": "complete",
        "incumbent_baseline_status": "included",
        "coverage_asymmetry_status": "reported",
        "winner_120_completeness_status": "candidate_outcome_120d_status_reconciled",
        "candidate_outcome_120d_status_reconciliation_status": "reported",
        "label_selection_policy_hash": stable_hash(config["selection"]),
        "price_path_source_status": "qfq_daily_csv_factor_column_loaded_on_demand",
        "oos_positive_rate_spread_force_diagnostic_status": "triggered"
        if oos_forced_diagnostic
        else "not_triggered",
        "oos_positive_rate_spread_force_diagnostic_reason": oos_forced_reason,
    }
    manifest = build_manifest(decision, config, input_frame, outputs, statuses)
    write_json(outputs["manifest"], manifest)
    return {
        "decision": decision,
        "frontier_rows": len(frontier),
        "selected_label_count": int((selected["selection_status"] == "selected").sum()),
        "manifest_path": str(outputs["manifest"]),
        "report_path": str(outputs["report"]),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    result = run_frontier(config_path, check_inputs_only=args.mode == "check-inputs")
    if args.mode == "check-inputs":
        failures = result["input_failures"]
        print(f"input_failures={len(failures)}")
        for failure in failures:
            print(failure)
        return 1 if failures else 0
    print(f"decision={result['decision']}")
    print(f"frontier_rows={result['frontier_rows']}")
    print(f"selected_label_count={result['selected_label_count']}")
    print(f"manifest={result['manifest_path']}")
    print(f"report={result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
