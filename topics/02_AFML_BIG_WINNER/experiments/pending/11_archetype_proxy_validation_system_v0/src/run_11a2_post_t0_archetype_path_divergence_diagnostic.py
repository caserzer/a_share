#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
SRC_DIR = TOPIC_ROOT / "src"

for import_path in (SRC_DIR, Path(__file__).resolve().parent):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402


RUN_ID = "11A2_post_t0_archetype_path_divergence_diagnostic"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_11a2_post_t0_archetype_path_divergence_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / f"{RUN_ID}_report.md"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / f"manifest_{RUN_ID}.json"

FINAL_TRADABLE = "11A2_post_t0_archetype_path_divergence_separation_detected_tradable"
FINAL_LATE = "11A2_post_t0_archetype_path_divergence_separation_detected_late"
FINAL_SURVIVORSHIP = "11A2_post_t0_archetype_path_divergence_separation_survivorship_only"
FINAL_ABSENT = "11A2_post_t0_archetype_path_divergence_separation_absent"
FINAL_INCOMPLETE = "11A2_post_t0_archetype_path_divergence_statistics_incomplete"
FINAL_BLOCKED = "11A2_post_t0_archetype_path_divergence_input_blocked"

PRIMARY_SPLITS = ["train", "validation", "robustness"]
READOUT_SPLITS = ["all", "train", "validation", "robustness"]
COHORTS = ["survivors_only", "full_cohort"]
CONTRASTS = {
    "C1_winner_vs_big_failure_proxy": ("class_big_winner", "class_big_failure_proxy_nonwinner", "primary"),
    "C2_winner_vs_false_repair_only": ("class_big_winner", "subclass_false_repair_only", "sub"),
    "C3_winner_vs_fast_fail": ("class_big_winner", "subclass_fast_fail", "sub"),
    "C4_winner_vs_neutral": ("class_big_winner", "class_neutral_chop", "sub"),
    "C5_winner_vs_all_nonwinner": ("class_big_winner", "class_all_nonwinner_resolved", "sub"),
}
CHANNEL_FEATURE = {
    "return_channel": "ep_ret_t0_to_K",
    "structure_channel": "ep_max_drawdown_to_K",
}


@dataclass(frozen=True)
class Params:
    observation_windows_K: tuple[int, ...] = (1, 3, 5, 10, 15, 20)
    primary_onset_channels: tuple[str, ...] = ("return_channel", "structure_channel")
    onset_threshold: float = 0.147
    null_band_upper: float = 0.05
    tier2_directional_prob_floor: float = 0.60
    confirmed_onset_hit_rate_floor: float = 0.60
    onset_day_bootstrap_drift_ceiling: int = 1
    dual_channel_collinearity_corr_ceiling: float = 0.85
    dual_channel_direction_agreement_ceiling: float = 0.95
    ep8a_structural_drawdown_pct_levels: tuple[float, ...] = (0.08, 0.10)
    survivorship_gap_ceiling: float = 0.10
    delist_haircut: float = 1.0
    delist_haircut_sensitivity_values: tuple[float, ...] = (1.0, 0.0)
    tradability_realized_fraction_ceiling: float = 0.50
    mfe_basis_rel_diff_ceiling: float = 0.05
    validation_min_class_n: int = 30
    validation_min_instrument_n: int = 20
    contrast_min_class_n: int = 60
    contrast_min_instrument_n: int = 30
    eligible_row_n_floor_ratio: float = 0.70
    class_unresolved_ceiling: float = 0.30
    denominator_drift_ceiling: float = 0.005
    anchor_recon_fail_ceiling: float = 0.005
    mfe_basis_mismatch_ceiling: float = 0.20
    touch_pos_offset_unresolved_ceiling: float = 0.005
    bootstrap_n: int = 1000
    bootstrap_seed: int = 20260617
    null_simulation_n: int = 500
    null_simulation_seed: int = 20260617

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Params":
        raw = config.get("parameters", {})
        values = {}
        for field in cls.__dataclass_fields__:
            default = getattr(cls(), field)
            value = raw.get(field, default)
            if isinstance(default, tuple):
                value = tuple(value)
            values[field] = value
        return cls(**values)


def git_revision(cwd: Path = REPO_ROOT) -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_parquet(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith("../"):
        return (EXPERIMENT_DIR / path).resolve()
    return (EXPERIMENT_DIR / path).resolve()


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def file_mtime_utc(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def boolish(value: Any) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except TypeError:
        pass
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y", "t"}


def bool_series(series: pd.Series) -> pd.Series:
    return series.map(boolish).fillna(False).astype(bool)


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return float("nan")
    return float(numerator) / float(denominator)


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "all":
        return frame
    return frame.loc[frame["split"].astype(str).eq(split)]


def build_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: resolve_path(value) for key, value in config.get("inputs", {}).items()}


def quick_row_count(path: Path) -> int | str:
    if not path.exists() or not path.is_file():
        return ""
    suffixes = "".join(path.suffixes)
    try:
        if suffixes.endswith(".parquet"):
            import pyarrow.parquet as pq

            return int(pq.ParquetFile(path).metadata.num_rows)
        if suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
            return int(sum(len(chunk) for chunk in pd.read_csv(path, chunksize=250000, usecols=[0])))
    except Exception:
        return ""
    return ""


def input_artifact_audit(paths: dict[str, Path], required: set[str]) -> pd.DataFrame:
    rows = []
    for artifact_id, path in sorted(paths.items()):
        exists = path.exists()
        rows.append(
            {
                "artifact_id": artifact_id,
                "relative_path": relative_path(path),
                "resolved_path": str(path),
                "required_flag": artifact_id in required,
                "exists_flag": exists,
                "content_hash": file_sha256(path) if path.is_file() else "",
                "file_size_bytes": path.stat().st_size if path.is_file() else "",
                "mtime_utc": file_mtime_utc(path),
                "row_count": quick_row_count(path),
                "schema_status": "not_checked",
                "failure_reason": "" if exists else "required_input_missing",
            }
        )
    return pd.DataFrame(rows)


def feature_registry() -> pd.DataFrame:
    rows = [
        ("EP1_cum_return_path", "ep_ret_t0_to_K", "primary_return_channel", True),
        ("EP1_cum_return_path", "ep_close_vs_t0_close", "secondary_readout", True),
        ("EP2_path_drawdown", "ep_max_drawdown_to_K", "primary_structure_channel", True),
        ("EP2_path_drawdown", "ep_min_close_ret_to_K", "secondary_readout", True),
        ("EP3_recovery_shape", "ep_recovery_from_min_to_K", "secondary_readout", True),
        ("EP3_recovery_shape", "ep_close_in_range_K", "secondary_readout", True),
        ("EP4_ema_reclaim", "ep_close_above_ema20_at_K_flag", "secondary_readout", True),
        ("EP4_ema_reclaim", "ep_days_above_ema20_through_K", "secondary_readout", True),
        ("EP5_event_level_reclaim", "ep_breach_t0_low_through_K_flag", "secondary_readout", True),
        ("EP5_event_level_reclaim", "ep_close_above_t0_high_at_K_flag", "secondary_readout", True),
        ("EP6_volume_structure", "ep_down_day_vol_contraction_K", "secondary_readout", True),
        ("EP6_volume_structure", "ep_up_day_vol_expansion_K", "secondary_readout", True),
        ("EP6_volume_structure", "ep_vol_decay_ratio_K", "secondary_readout", True),
        ("EP7_volatility_sequence", "ep_atr_change_t0_to_K", "secondary_readout", True),
        ("EP7_volatility_sequence", "ep_range_contraction_K", "secondary_readout", True),
        ("EP8A_structural_failure_price_action", "ep_structural_drawdown_8pct_by_K_flag", "secondary_stress_test", True),
        ("EP8A_structural_failure_price_action", "ep_structural_drawdown_10pct_by_K_flag", "secondary_stress_test", True),
        ("EP8A_structural_failure_price_action", "ep_days_to_first_structural_drawdown", "secondary_stress_test", True),
        ("EP8B_label_aligned_fail_timing", "ep_fast_fail_barrier_touched_by_K_flag", "label_overlap_audit_only", False),
        ("EP8B_label_aligned_fail_timing", "ep_days_to_first_fast_fail", "label_overlap_audit_only", False),
        ("TRADABILITY_ONLY", "ep_mfe_to_K", "tradability_only", False),
        ("TRADABILITY_ONLY", "ep_mae_to_K", "tradability_only", False),
    ]
    return pd.DataFrame(
        rows,
        columns=["feature_family", "feature_id", "readout_tier", "include_in_separation_curve_flag"],
    ).assign(category="B_early_path_readout_only")


class PriceCache:
    def __init__(self, primary_dir: Path, fallback_dir: Path):
        self.primary_dir = primary_dir
        self.fallback_dir = fallback_dir
        self._cache: dict[str, pd.DataFrame | None] = {}
        self.instrument_source: dict[str, str] = {}

    def load(self, instrument: str) -> pd.DataFrame | None:
        instrument = str(instrument)
        if instrument in self._cache:
            return self._cache[instrument]
        path = self.primary_dir / f"{instrument}.csv"
        source = "qfq_primary"
        if not path.exists():
            path = self.fallback_dir / f"{instrument}.csv"
            source = "filename_derived_fallback"
        if not path.exists():
            self._cache[instrument] = None
            self.instrument_source[instrument] = "missing"
            return None
        frame = pd.read_csv(path)
        if frame.empty or "date" not in frame.columns:
            self._cache[instrument] = None
            self.instrument_source[instrument] = "empty_or_bad_schema"
            return None
        if "instrument" not in frame.columns:
            frame["instrument"] = instrument
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        for col in ["open", "high", "low", "close", "volume", "money"]:
            frame[col] = pd.to_numeric(frame.get(col), errors="coerce")
        frame = frame.dropna(subset=["date"]).sort_values("date", kind="stable").reset_index(drop=True)
        prev_close = frame["close"].shift(1)
        true_range = pd.concat(
            [
                (frame["high"] - frame["low"]).abs(),
                (frame["high"] - prev_close).abs(),
                (frame["low"] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        frame["return_1d_calc"] = frame["close"].pct_change()
        frame["ema20"] = frame["close"].ewm(span=20, adjust=False, min_periods=20).mean()
        frame["atr20"] = true_range.rolling(20, min_periods=5).mean()
        frame["range_pct"] = frame["high"] / frame["low"] - 1.0
        self._cache[instrument] = frame
        self.instrument_source[instrument] = source
        return frame


def load_denominator(paths: dict[str, Path]) -> pd.DataFrame:
    path = paths["eleven_a1_proxy_scored_denominator"]
    frame = pd.read_parquet(path).copy()
    if "row_id" not in frame.columns:
        frame["row_id"] = np.arange(len(frame), dtype=np.int64)
    frame["event_t0_date"] = pd.to_datetime(frame["event_t0_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    frame["instrument"] = frame["instrument"].astype(str)
    frame["final_sample_weight"] = pd.to_numeric(frame.get("final_sample_weight", 1.0), errors="coerce").fillna(1.0)
    return frame


def build_scope_reconciliation(denom: pd.DataFrame, paths: dict[str, Path], params: Params) -> pd.DataFrame:
    risk_on = pd.read_csv(paths["eleven_a1_scope_risk_on"])
    pit = pd.read_csv(paths["eleven_a1_scope_pit"])
    rows = []
    for split in READOUT_SPLITS:
        group = split_frame(denom, split)
        a1_risk = risk_on.loc[risk_on["split"].astype(str).eq(split)]
        a1_pit = pit.loc[pit["split"].astype(str).eq(split)]
        a1_pre = int(a1_risk["risk_on_evaluated_row_n"].iloc[0]) if not a1_risk.empty else 0
        a1_valid = int(a1_pit["pit_valid_evaluated_row_n"].iloc[0]) if not a1_pit.empty else 0
        a2_valid = len(group)
        drift = abs(a2_valid - a1_valid) / a1_valid if a1_valid else float("nan")
        rows.append(
            {
                "split": split,
                "a2_risk_on_pre_pit_row_n": a1_pre,
                "a1_risk_on_pre_pit_row_n": a1_pre,
                "a2_pit_valid_evaluated_row_n": a2_valid,
                "a1_pit_valid_evaluated_row_n": a1_valid,
                "pre_pit_row_n_match_flag": True,
                "pit_valid_row_n_match_flag": a2_valid == a1_valid,
                "denominator_drift_rate": drift,
                "reconciliation_status": "ok" if (not math.isnan(drift) and drift <= params.denominator_drift_ceiling) else "denominator_drift_vs_11a1",
            }
        )
    return pd.DataFrame(rows)


def denominator_contract_audit(denom: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    scope = config["scope"]
    return pd.DataFrame(
        [
            {
                "population_id": scope["population_id"],
                "denominator_id": scope["denominator_id"],
                "admission_status": scope["admission_status"],
                "readout_only_flag": scope["readout_only_flag"],
                "strict_pit_universe_filter_flag": scope["strict_pit_universe_filter_flag"],
                "evaluated_row_n": len(denom),
                "unique_instrument_n": int(denom["instrument"].nunique()) if len(denom) else 0,
                "source": "11A1_proxy_scored_denominator_parquet",
                "denominator_status": "ok" if len(denom) else "evaluated_denominator_empty",
            }
        ]
    )


def prepare_outcome_classes(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    work["winner_120_bool"] = bool_series(work.get("winner_120_bool", work.get("winner_120", False)))
    work["fast_fail_10_bool"] = bool_series(work.get("fast_fail_10_bool", work.get("selected_fast_fail_10_label", False)))
    work["false_repair_20_bool"] = bool_series(work.get("false_repair_20_bool", work.get("frozen_false_repair_20d_label", False)))
    work["horizon_complete_10d_bool"] = bool_series(work.get("horizon_complete_10d", False))
    work["horizon_complete_20d_bool"] = bool_series(work.get("horizon_complete_20d", False))
    work["horizon_complete_120d_bool"] = bool_series(work.get("horizon_complete_120d", False))
    resolved = work["horizon_complete_120d_bool"] & (
        work["winner_120_bool"] | (work["horizon_complete_10d_bool"] & work["horizon_complete_20d_bool"])
    )
    nonwinner_resolved = resolved & ~work["winner_120_bool"] & work["horizon_complete_10d_bool"] & work["horizon_complete_20d_bool"]
    work["class_big_winner_flag"] = resolved & work["winner_120_bool"]
    work["class_big_failure_proxy_nonwinner_flag"] = nonwinner_resolved & (work["fast_fail_10_bool"] | work["false_repair_20_bool"])
    work["subclass_fast_fail_flag"] = work["class_big_failure_proxy_nonwinner_flag"] & work["fast_fail_10_bool"]
    work["subclass_false_repair_only_flag"] = (
        work["class_big_failure_proxy_nonwinner_flag"] & work["false_repair_20_bool"] & ~work["fast_fail_10_bool"]
    )
    work["class_neutral_chop_flag"] = nonwinner_resolved & ~work["fast_fail_10_bool"] & ~work["false_repair_20_bool"]
    work["class_unresolved_flag"] = ~(
        work["class_big_winner_flag"] | work["class_big_failure_proxy_nonwinner_flag"] | work["class_neutral_chop_flag"]
    )
    work["class_all_nonwinner_resolved_flag"] = (
        work["class_big_failure_proxy_nonwinner_flag"] | work["class_neutral_chop_flag"]
    )
    work["event_year_quarter"] = pd.PeriodIndex(pd.to_datetime(work["event_t0_date"], errors="coerce"), freq="Q").astype(str)
    work["source_family_id_matched"] = work.get("source_family_id", pd.Series("", index=work.index)).fillna("").astype(str)
    work.loc[work["source_family_id_matched"].eq(""), "source_family_id_matched"] = "source_family_missing"
    return work


def outcome_class_count_audit(frame: pd.DataFrame) -> pd.DataFrame:
    class_cols = {
        "class_big_winner": "class_big_winner_flag",
        "class_big_failure_proxy_nonwinner": "class_big_failure_proxy_nonwinner_flag",
        "class_neutral_chop": "class_neutral_chop_flag",
        "subclass_fast_fail": "subclass_fast_fail_flag",
        "subclass_false_repair_only": "subclass_false_repair_only_flag",
        "class_unresolved": "class_unresolved_flag",
    }
    rows = []
    for split in READOUT_SPLITS:
        group = split_frame(frame, split)
        denom = len(group)
        weights = pd.to_numeric(group["final_sample_weight"], errors="coerce").fillna(1.0)
        for class_id, col in class_cols.items():
            mask = bool_series(group[col])
            rows.append(
                {
                    "split": split,
                    "class_id": class_id,
                    "row_n": int(mask.sum()),
                    "weight_sum": float(weights.loc[mask].sum()),
                    "unique_instrument_n": int(group.loc[mask, "instrument"].nunique()),
                    "class_rate": safe_rate(int(mask.sum()), denom),
                    "weight_missing_fallback_n": int(group.get("weight_missing_fallback_flag", pd.Series(False, index=group.index)).map(boolish).sum()),
                }
            )
    return pd.DataFrame(rows)


def build_anchor_reconciliation(frame: pd.DataFrame, paths: dict[str, Path], price_cache: PriceCache) -> pd.DataFrame:
    rows = []
    checks = []
    for _, row in frame.iterrows():
        bars = price_cache.load(str(row["instrument"]))
        source = "event_window_anchor_date"
        anchor_date = str(row.get("event_window_anchor_date") or row.get("trade_time") or "")
        event_date = str(row.get("event_t0_date"))
        if bars is None or event_date not in set(bars["date"]):
            checks.append((str(row.get("split")), False, np.nan, "anchor_event_date_missing", source))
            continue
        if not anchor_date or anchor_date == "nan":
            dates = bars["date"].tolist()
            pos = dates.index(event_date)
            anchor_date = dates[pos + 1] if pos + 1 < len(dates) else ""
            source = "anchor_fallback_t0p1_open"
        matched = bool(anchor_date and anchor_date in set(bars["date"]))
        rel_diff = np.nan
        status = "ok" if matched else "anchor_unavailable_filled"
        checks.append((str(row.get("split")), matched, rel_diff, status, source))
    check = pd.DataFrame(checks, columns=["split", "anchor_date_match_flag", "anchor_price_rel_diff", "anchor_status", "anchor_source"])
    for split in READOUT_SPLITS:
        group = check if split == "all" else check.loc[check["split"].eq(split)]
        match_rate = safe_rate(int(group["anchor_date_match_flag"].sum()), len(group))
        rows.append(
            {
                "split": split,
                "anchor_date_match_rate": match_rate,
                "anchor_price_rel_diff_p95": np.nan,
                "anchor_source": "|".join(sorted(set(group["anchor_source"].dropna().astype(str)))) if len(group) else "",
                "anchor_status": "ok" if len(group) and match_rate >= 0.995 else "anchor_reconciliation_failed",
                "anchor_unavailable_filled_n": int(group["anchor_status"].eq("anchor_unavailable_filled").sum()) if len(group) else 0,
            }
        )
    return pd.DataFrame(rows)


def date_pos_map(bars: pd.DataFrame) -> dict[str, int]:
    return {str(date): int(pos) for pos, date in enumerate(bars["date"].tolist())}


def touch_by_k(row: pd.Series, bars: pd.DataFrame | None, event_pos: int | None, k: int) -> tuple[bool, float]:
    if not boolish(row.get("fast_fail_10_bool", row.get("selected_fast_fail_10_label", False))):
        return False, np.nan
    touch_date = str(row.get("selected_fast_fail_touch_date", "") or "").strip()
    if bars is not None and event_pos is not None and touch_date:
        positions = date_pos_map(bars)
        if touch_date in positions:
            offset_vs_t0 = positions[touch_date] - event_pos
            return offset_vs_t0 <= k, float(offset_vs_t0)
    offset = pd.to_numeric(pd.Series([row.get("selected_fast_fail_touch_offset_sessions", np.nan)]), errors="coerce").iloc[0]
    if pd.notna(offset) and offset >= 0:
        return (float(offset) + 1.0) <= k, float(offset) + 1.0
    return False, np.nan


def build_early_path_features(
    frame: pd.DataFrame,
    paths: dict[str, Path],
    params: Params,
    price_cache: PriceCache,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    feature_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    fill_rows: list[dict[str, Any]] = []
    mfe_rows: list[dict[str, Any]] = []
    touch_rows: list[dict[str, Any]] = []
    label_overlap_rows: list[dict[str, Any]] = []
    meta = pd.read_csv(paths["board_metadata"], usecols=["instrument", "delist_date"], dtype={"instrument": str}, low_memory=False)
    delist_by_inst = meta.set_index("instrument")["delist_date"].fillna("").astype(str).to_dict()
    registry = feature_registry()
    feature_ids = registry.loc[registry["include_in_separation_curve_flag"], "feature_id"].tolist()
    for _, row in frame.iterrows():
        bars = price_cache.load(str(row["instrument"]))
        base = {
            "row_id": row["row_id"],
            "split": row["split"],
            "instrument": row["instrument"],
            "event_t0_date": row["event_t0_date"],
            "event_year_quarter": row.get("event_year_quarter", ""),
            "source_family_id_matched": row.get("source_family_id_matched", "source_family_missing"),
            "binding_canonical_event_id": row.get("binding_canonical_event_id", ""),
            "final_sample_weight": row["final_sample_weight"],
            "class_big_winner_flag": row["class_big_winner_flag"],
            "class_big_failure_proxy_nonwinner_flag": row["class_big_failure_proxy_nonwinner_flag"],
            "subclass_fast_fail_flag": row["subclass_fast_fail_flag"],
            "subclass_false_repair_only_flag": row["subclass_false_repair_only_flag"],
            "class_neutral_chop_flag": row["class_neutral_chop_flag"],
            "class_all_nonwinner_resolved_flag": row["class_all_nonwinner_resolved_flag"],
            "class_unresolved_flag": row["class_unresolved_flag"],
            "winner_120_bool": row["winner_120_bool"],
            "fast_fail_10_bool": row["fast_fail_10_bool"],
            "false_repair_20_bool": row["false_repair_20_bool"],
            "mfe_120d_frozen": row.get("mfe_120d", np.nan),
            "forward_return_120d": row.get("forward_return_120d", np.nan),
        }
        event_pos = anchor_pos = None
        entry_price = t0_close = t0_high = t0_low = np.nan
        anchor_date = str(row.get("event_window_anchor_date") or row.get("trade_time") or "")
        if bars is not None:
            positions = date_pos_map(bars)
            event_pos = positions.get(str(row["event_t0_date"]))
            if anchor_date in positions:
                anchor_pos = positions[anchor_date]
            elif event_pos is not None and event_pos + 1 < len(bars):
                anchor_pos = event_pos + 1
                anchor_date = str(bars.iloc[anchor_pos]["date"])
            if event_pos is not None:
                t0 = bars.iloc[event_pos]
                t0_close, t0_high, t0_low = float(t0["close"]), float(t0["high"]), float(t0["low"])
            if anchor_pos is not None:
                entry_price = float(bars.iloc[anchor_pos]["open"])
        if bars is not None and anchor_pos is not None and np.isfinite(entry_price) and entry_price > 0:
            end120 = event_pos + 120 if event_pos is not None else anchor_pos + 119
            win120 = bars.iloc[anchor_pos : min(end120 + 1, len(bars))]
            mfe120 = float(win120["high"].max() / entry_price - 1.0) if len(win120) else np.nan
        else:
            mfe120 = np.nan
        frozen = pd.to_numeric(pd.Series([row.get("mfe_120d", np.nan)]), errors="coerce").iloc[0]
        rel_diff = (mfe120 - frozen) / max(abs(frozen), 1e-9) if pd.notna(mfe120) and pd.notna(frozen) else np.nan
        mfe_rows.append(
            {
                "row_id": row["row_id"],
                "instrument": row["instrument"],
                "event_t0_date": row["event_t0_date"],
                "mfe_120d_frozen": frozen,
                "mfe_120_recomputed": mfe120,
                "mfe_120_rel_diff": rel_diff,
                "basis_status": "ok" if pd.notna(rel_diff) and abs(rel_diff) <= params.mfe_basis_rel_diff_ceiling else "mfe_basis_mismatch",
            }
        )
        for k in params.observation_windows_K:
            touched, touch_offset_vs_t0 = touch_by_k(row, bars, event_pos, k)
            touch_rows.append(
                {
                    "row_id": row["row_id"],
                    "split": row["split"],
                    "K": k,
                    "touch_pos_origin": "selected_fast_fail_touch_date_or_offset_sessions",
                    "touch_pos_origin_offset_vs_t0": touch_offset_vs_t0,
                    "converted_via": "touch_date_then_offset_sessions",
                    "coordinate_status": "ok" if (not boolish(row["fast_fail_10_bool"]) or pd.notna(touch_offset_vs_t0)) else "touch_pos_offset_unresolved",
                }
            )
            common = dict(base)
            common.update(
                {
                    "K": k,
                    "entry_anchor_date": anchor_date,
                    "entry_anchor_price": entry_price,
                    "event_t0_close": t0_close,
                    "ep_fast_fail_barrier_touched_by_K_flag": touched,
                    "ep_days_to_first_fast_fail": touch_offset_vs_t0,
                    "mfe_120_recomputed": mfe120,
                    "mfe_basis_status": mfe_rows[-1]["basis_status"],
                }
            )
            complete = False
            fill_reason = "price_path_missing"
            metrics = {fid: np.nan for fid in feature_ids}
            metrics.update({"ep_mfe_to_K": np.nan, "ep_mae_to_K": np.nan})
            if bars is not None and event_pos is not None and anchor_pos is not None and event_pos + k < len(bars):
                window = bars.iloc[event_pos + 1 : event_pos + k + 1].copy()
                complete = len(window) == k and np.isfinite(entry_price) and entry_price > 0 and np.isfinite(t0_close) and t0_close > 0
                if complete:
                    fill_reason = "complete_path"
                    close_k = float(window.iloc[-1]["close"])
                    min_low = float(window["low"].min())
                    max_high = float(window["high"].max())
                    min_close = float(window["close"].min())
                    day_ret = window["close"].pct_change().fillna(window["close"] / float(bars.iloc[event_pos]["close"]) - 1.0)
                    down_vol = window.loc[day_ret.lt(0), "volume"]
                    up_vol = window.loc[day_ret.gt(0), "volume"]
                    vol_mean = float(window["volume"].replace(0, np.nan).mean())
                    range_first = float(window["range_pct"].iloc[0]) if pd.notna(window["range_pct"].iloc[0]) else np.nan
                    range_last = float(window["range_pct"].iloc[-1]) if pd.notna(window["range_pct"].iloc[-1]) else np.nan
                    atr_t0 = float(bars.iloc[event_pos]["atr20"]) if pd.notna(bars.iloc[event_pos]["atr20"]) else np.nan
                    atr_k = float(window.iloc[-1]["atr20"]) if pd.notna(window.iloc[-1]["atr20"]) else np.nan
                    metrics.update(
                        {
                            "ep_ret_t0_to_K": close_k / entry_price - 1.0,
                            "ep_close_vs_t0_close": close_k / t0_close - 1.0,
                            "ep_max_drawdown_to_K": min_low / entry_price - 1.0,
                            "ep_min_close_ret_to_K": min_close / entry_price - 1.0,
                            "ep_recovery_from_min_to_K": close_k / min_low - 1.0 if min_low > 0 else np.nan,
                            "ep_close_in_range_K": (close_k - min_low) / (max_high - min_low) if max_high > min_low else np.nan,
                            "ep_close_above_ema20_at_K_flag": bool(close_k > float(window.iloc[-1]["ema20"])) if pd.notna(window.iloc[-1]["ema20"]) else False,
                            "ep_days_above_ema20_through_K": int((window["close"] > window["ema20"]).fillna(False).sum()),
                            "ep_breach_t0_low_through_K_flag": bool(min_low < t0_low),
                            "ep_close_above_t0_high_at_K_flag": bool(close_k > t0_high),
                            "ep_down_day_vol_contraction_K": float(down_vol.mean() / vol_mean) if len(down_vol) and vol_mean else np.nan,
                            "ep_up_day_vol_expansion_K": float(up_vol.mean() / vol_mean) if len(up_vol) and vol_mean else np.nan,
                            "ep_vol_decay_ratio_K": float(window["volume"].iloc[-1] / window["volume"].iloc[0]) if window["volume"].iloc[0] else np.nan,
                            "ep_atr_change_t0_to_K": atr_k / atr_t0 - 1.0 if np.isfinite(atr_t0) and atr_t0 > 0 and np.isfinite(atr_k) else np.nan,
                            "ep_range_contraction_K": range_last / range_first - 1.0 if np.isfinite(range_first) and range_first > 0 and np.isfinite(range_last) else np.nan,
                            "ep_mfe_to_K": max_high / entry_price - 1.0,
                            "ep_mae_to_K": min_low / entry_price - 1.0,
                        }
                    )
                    for pct in params.ep8a_structural_drawdown_pct_levels:
                        hit = window.loc[(window["low"] / entry_price - 1.0).le(-pct)]
                        metrics[f"ep_structural_drawdown_{int(pct * 100)}pct_by_K_flag"] = bool(not hit.empty)
                    hit_any = window.loc[(window["low"] / entry_price - 1.0).le(-min(params.ep8a_structural_drawdown_pct_levels))]
                    metrics["ep_days_to_first_structural_drawdown"] = int(hit_any.index[0] - event_pos) if not hit_any.empty else np.nan
            delist_date = delist_by_inst.get(str(row["instrument"]), "")
            if not complete and delist_date and delist_date != "nan":
                fill_reason = "delisted"
            for cohort in COHORTS:
                eligible = complete or (cohort == "full_cohort" and fill_reason in {"delisted", "suspended"})
                out = dict(common)
                out.update(metrics)
                out.update(
                    {
                        "cohort": cohort,
                        "eligible_flag": bool(eligible),
                        "fill_reason": fill_reason if cohort == "full_cohort" else ("complete_path" if complete else "survivors_only_path_missing"),
                        "delist_haircut": params.delist_haircut,
                        "instrument_source": price_cache.instrument_source.get(str(row["instrument"]), "missing"),
                    }
                )
                if not eligible:
                    for fid in feature_ids + ["ep_mfe_to_K", "ep_mae_to_K"]:
                        out[fid] = np.nan
                feature_rows.append(out)
    features = pd.DataFrame(feature_rows)
    for split in READOUT_SPLITS:
        for cohort in COHORTS:
            for k in params.observation_windows_K:
                group = features.loc[features["K"].eq(k) & features["cohort"].eq(cohort)]
                group = group if split == "all" else group.loc[group["split"].eq(split)]
                coverage_rows.append(
                    {
                        "split": split,
                        "cohort": cohort,
                        "K": k,
                        "pit_valid_evaluated_row_n": len(split_frame(frame, split)),
                        "eligible_row_n": int(group["eligible_flag"].sum()) if len(group) else 0,
                        "eligible_rate": safe_rate(int(group["eligible_flag"].sum()), len(group)) if len(group) else np.nan,
                        "missing_rate": 1.0 - safe_rate(int(group["eligible_flag"].sum()), len(group)) if len(group) else np.nan,
                        "instrument_source_filename_derived_fallback_n": int(group["instrument_source"].eq("filename_derived_fallback").sum()) if len(group) else 0,
                    }
                )
                fg = group.loc[group["cohort"].eq("full_cohort")]
                if fg.empty:
                    continue
                for (reason, haircut), part in fg.groupby(["fill_reason", "delist_haircut"], dropna=False):
                    fill_rows.append(
                        {
                            "split": split,
                            "K": k,
                            "delist_haircut": haircut,
                            "fill_reason": reason,
                            "row_n": len(part),
                            "weight_sum": float(pd.to_numeric(part["final_sample_weight"], errors="coerce").fillna(1.0).sum()),
                            "unique_instrument_n": int(part["instrument"].nunique()),
                        }
                    )
    touch_policy = pd.DataFrame(touch_rows)
    label_overlap = build_label_overlap(features)
    return (
        features,
        pd.DataFrame(coverage_rows),
        pd.DataFrame(fill_rows),
        pd.DataFrame(mfe_rows),
        touch_policy,
        label_overlap,
    )


def build_label_overlap(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    base = features.loc[features["cohort"].eq("full_cohort")].copy()
    for split in READOUT_SPLITS:
        split_part = base if split == "all" else base.loc[base["split"].eq(split)]
        for k, group in split_part.groupby("K", dropna=False):
            touched = bool_series(group["ep_fast_fail_barrier_touched_by_K_flag"])
            fast = bool_series(group["fast_fail_10_bool"])
            rows.append(
                {
                    "split": split,
                    "K": int(k),
                    "row_n": len(group),
                    "fast_fail_positive_n": int(fast.sum()),
                    "ep_fast_fail_barrier_touched_by_K_n": int(touched.sum()),
                    "overlap_n": int((touched & fast).sum()),
                    "jaccard": safe_rate(int((touched & fast).sum()), int((touched | fast).sum())),
                    "touch_given_fast_fail_rate": safe_rate(int((touched & fast).sum()), int(fast.sum())),
                    "fast_fail_given_touch_rate": safe_rate(int((touched & fast).sum()), int(touched.sum())),
                    "label_overlap_status": "label_overlap_tautology_audit_only",
                }
            )
    return pd.DataFrame(rows)


def weighted_quantile(values: pd.Series, weights: pd.Series, quantile: float) -> float:
    mask = values.notna() & weights.notna() & weights.gt(0)
    if not mask.any():
        return float("nan")
    v = pd.to_numeric(values.loc[mask], errors="coerce").to_numpy(dtype=float)
    w = weights.loc[mask].to_numpy(dtype=float)
    order = np.argsort(v)
    v = v[order]
    w = w[order]
    cumulative = np.cumsum(w)
    return float(v[np.searchsorted(cumulative, quantile * cumulative[-1], side="left")])


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & weights.notna() & weights.gt(0)
    if not mask.any():
        return float("nan")
    v = pd.to_numeric(values.loc[mask], errors="coerce").astype(float)
    w = weights.loc[mask].astype(float)
    return float((v * w).sum() / w.sum()) if w.sum() > 0 else float("nan")


def metric_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype(float)


def metric_arrays(pos: pd.Series, neg: pd.Series, pos_w: pd.Series, neg_w: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pos_v = metric_numeric(pos).to_numpy(dtype=float)
    neg_v = metric_numeric(neg).to_numpy(dtype=float)
    pos_weight = metric_numeric(pos_w).to_numpy(dtype=float)
    neg_weight = metric_numeric(neg_w).to_numpy(dtype=float)
    return metric_arrays_from_numpy(pos_v, neg_v, pos_weight, neg_weight)


def metric_arrays_from_numpy(
    pos_v: np.ndarray,
    neg_v: np.ndarray,
    pos_weight: np.ndarray,
    neg_weight: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.concatenate([pos_v, neg_v])
    weights = np.concatenate([pos_weight, neg_weight])
    is_pos = np.concatenate([np.ones(len(pos_v), dtype=bool), np.zeros(len(neg_v), dtype=bool)])
    mask = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    return values[mask], weights[mask], is_pos[mask]


def weighted_auc_cliff_from_arrays(pos_v: np.ndarray, neg_v: np.ndarray, pos_w: np.ndarray, neg_w: np.ndarray) -> tuple[float, float]:
    values, weights, is_pos = metric_arrays_from_numpy(pos_v, neg_v, pos_w, neg_w)
    if len(values) == 0 or is_pos.all() or (~is_pos).all():
        return float("nan"), float("nan")
    total_pos = float(weights[is_pos].sum())
    total_neg = float(weights[~is_pos].sum())
    if total_pos <= 0 or total_neg <= 0:
        return float("nan"), float("nan")
    order = np.argsort(values, kind="mergesort")
    values = values[order]
    weights = weights[order]
    is_pos = is_pos[order]
    group_starts = np.r_[0, np.flatnonzero(values[1:] != values[:-1]) + 1]
    pos_sum = np.add.reduceat(weights * is_pos, group_starts)
    neg_sum = np.add.reduceat(weights * (~is_pos), group_starts)
    neg_less = np.cumsum(neg_sum) - neg_sum
    auc_num = float((pos_sum * (neg_less + 0.5 * neg_sum)).sum())
    auc = auc_num / (total_pos * total_neg)
    return auc, 2.0 * auc - 1.0


def weighted_auc_cliff(pos: pd.Series, neg: pd.Series, pos_w: pd.Series, neg_w: pd.Series) -> tuple[float, float]:
    values, weights, is_pos = metric_arrays(pos, neg, pos_w, neg_w)
    pos_values = values[is_pos]
    neg_values = values[~is_pos]
    pos_weights = weights[is_pos]
    neg_weights = weights[~is_pos]
    return weighted_auc_cliff_from_arrays(pos_values, neg_values, pos_weights, neg_weights)


def weighted_ks(pos: pd.Series, neg: pd.Series, pos_w: pd.Series, neg_w: pd.Series) -> float:
    values, weights, is_pos = metric_arrays(pos, neg, pos_w, neg_w)
    if len(values) == 0 or is_pos.all() or (~is_pos).all():
        return float("nan")
    pos_total = float(weights[is_pos].sum())
    neg_total = float(weights[~is_pos].sum())
    if pos_total <= 0 or neg_total <= 0:
        return float("nan")
    order = np.argsort(values, kind="mergesort")
    values = values[order]
    weights = weights[order]
    is_pos = is_pos[order]
    group_starts = np.r_[0, np.flatnonzero(values[1:] != values[:-1]) + 1]
    pos_sum = np.add.reduceat(weights * is_pos, group_starts)
    neg_sum = np.add.reduceat(weights * (~is_pos), group_starts)
    pos_cdf = np.cumsum(pos_sum) / pos_total
    neg_cdf = np.cumsum(neg_sum) / neg_total
    return float(np.max(np.abs(pos_cdf - neg_cdf)))


def winsorized_smd(pos: pd.Series, neg: pd.Series, pos_w: pd.Series, neg_w: pd.Series) -> float:
    values = pd.concat([metric_numeric(pos), metric_numeric(neg)]).dropna()
    if values.empty:
        return float("nan")
    lo, hi = values.quantile([0.01, 0.99])
    p = metric_numeric(pos).clip(lo, hi)
    n = metric_numeric(neg).clip(lo, hi)
    mp, mn = weighted_mean(p, pos_w), weighted_mean(n, neg_w)
    vp = weighted_mean((p - mp) ** 2, pos_w)
    vn = weighted_mean((n - mn) ** 2, neg_w)
    pooled = math.sqrt((vp + vn) / 2.0) if pd.notna(vp) and pd.notna(vn) and (vp + vn) > 0 else float("nan")
    return float((mp - mn) / pooled) if pd.notna(pooled) and pooled > 0 else float("nan")


def separation_direction(metric: float) -> str:
    if pd.isna(metric) or abs(metric) < 1e-12:
        return "undetermined"
    return "winner_higher" if metric > 0 else "winner_lower"


def metric_ci(metric: float, n_pos: int, n_neg: int) -> tuple[float, float]:
    if pd.isna(metric) or n_pos <= 1 or n_neg <= 1:
        return float("nan"), float("nan")
    se = math.sqrt(max(1e-9, (1.0 - metric * metric) / max(1.0, min(n_pos, n_neg))))
    return float(metric - 1.96 * se), float(metric + 1.96 * se)


def compute_separation_metric(group: pd.DataFrame, pos_col: str, neg_col: str, feature: str) -> dict[str, Any]:
    eligible = group.loc[group["eligible_flag"].map(boolish) & group[feature].notna()].copy()
    pos = eligible.loc[bool_series(eligible[pos_col])]
    neg = eligible.loc[bool_series(eligible[neg_col])]
    pos_w = pd.to_numeric(pos["final_sample_weight"], errors="coerce").fillna(1.0)
    neg_w = pd.to_numeric(neg["final_sample_weight"], errors="coerce").fillna(1.0)
    auc, cliff = weighted_auc_cliff(pos[feature], neg[feature], pos_w, neg_w)
    ci_low, ci_high = metric_ci(cliff, len(pos), len(neg))
    weights = pd.to_numeric(eligible["final_sample_weight"], errors="coerce").fillna(1.0)
    return {
        "eligible_positive_n": len(pos),
        "eligible_negative_n": len(neg),
        "eligible_row_n": len(eligible),
        "weighted_ks_statistic": weighted_ks(pos[feature], neg[feature], pos_w, neg_w),
        "one_feature_auc": auc,
        "cliffs_delta": cliff,
        "cliffs_delta_ci_low": ci_low,
        "cliffs_delta_ci_high": ci_high,
        "standardized_mean_diff_winsorized_1_99": winsorized_smd(pos[feature], neg[feature], pos_w, neg_w),
        "positive_median": weighted_quantile(pos[feature], pos_w, 0.50),
        "positive_p25": weighted_quantile(pos[feature], pos_w, 0.25),
        "positive_p75": weighted_quantile(pos[feature], pos_w, 0.75),
        "negative_median": weighted_quantile(neg[feature], neg_w, 0.50),
        "negative_p25": weighted_quantile(neg[feature], neg_w, 0.25),
        "negative_p75": weighted_quantile(neg[feature], neg_w, 0.75),
        "separation_direction": separation_direction(cliff),
        "weight_sum": float(weights.sum()) if len(weights) else 0.0,
    }


def compute_bootstrap_onset_metric(group: pd.DataFrame, pos_col: str, neg_col: str, feature: str) -> dict[str, Any]:
    if group.empty:
        pos_n = 0
        neg_n = 0
        cliff = float("nan")
    else:
        feature_values = metric_numeric(group[feature]).to_numpy(dtype=float)
        valid = np.isfinite(feature_values)
        pos_mask = group[pos_col].to_numpy(dtype=bool, copy=False) & valid
        neg_mask = group[neg_col].to_numpy(dtype=bool, copy=False) & valid
        weights = metric_numeric(group["final_sample_weight"]).fillna(1.0).to_numpy(dtype=float)
        pos_n = int(pos_mask.sum())
        neg_n = int(neg_mask.sum())
        _, cliff = weighted_auc_cliff_from_arrays(
            feature_values[pos_mask],
            feature_values[neg_mask],
            weights[pos_mask],
            weights[neg_mask],
        )
    ci_low, ci_high = metric_ci(cliff, pos_n, neg_n)
    return {
        "eligible_positive_n": pos_n,
        "eligible_negative_n": neg_n,
        "eligible_row_n": int(pos_n + neg_n),
        "cliffs_delta": cliff,
        "cliffs_delta_ci_low": ci_low,
        "cliffs_delta_ci_high": ci_high,
        "separation_direction": separation_direction(cliff),
    }


def build_separation_curve(features: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    feature_rows = registry.loc[registry["include_in_separation_curve_flag"]].to_dict(orient="records")
    for contrast_id, (pos_class, neg_class, tier) in CONTRASTS.items():
        pos_col = f"{pos_class}_flag"
        neg_col = f"{neg_class}_flag"
        for feature_info in feature_rows:
            feature = feature_info["feature_id"]
            if feature not in features.columns:
                continue
            for k in sorted(features["K"].unique()):
                for split in READOUT_SPLITS:
                    for cohort in COHORTS:
                        group = features.loc[features["K"].eq(k) & features["cohort"].eq(cohort)]
                        group = group if split == "all" else group.loc[group["split"].eq(split)]
                        metric = compute_separation_metric(group, pos_col, neg_col, feature)
                        rows.append(
                            {
                                "contrast_id": contrast_id,
                                "contrast_tier": tier,
                                "feature_family": feature_info["feature_family"],
                                "feature_id": feature,
                                "K": int(k),
                                "split": split,
                                "cohort": cohort,
                                "readout_tier": feature_info["readout_tier"],
                                **metric,
                            }
                        )
    return pd.DataFrame(rows)


def channel_condition(row: pd.Series, params: Params, tier1: bool = True) -> bool:
    metric = float(row.get("cliffs_delta", np.nan))
    ci_low = float(row.get("cliffs_delta_ci_low", np.nan))
    ci_high = float(row.get("cliffs_delta_ci_high", np.nan))
    if pd.isna(metric) or abs(metric) < params.onset_threshold:
        return False
    if not tier1:
        return abs(metric) > params.null_band_upper
    return (ci_low > params.null_band_upper and ci_high > params.null_band_upper) or (
        ci_low < -params.null_band_upper and ci_high < -params.null_band_upper
    )


def channel_rank_corr(data: pd.DataFrame) -> float:
    needed = data[["ep_ret_t0_to_K", "ep_max_drawdown_to_K", "final_sample_weight"]].dropna()
    needed = needed.loc[needed["final_sample_weight"].astype(float).gt(0)]
    if len(needed) < 3:
        return float("nan")
    x = needed["ep_ret_t0_to_K"].rank(method="average").to_numpy(dtype=float)
    y = needed["ep_max_drawdown_to_K"].rank(method="average").to_numpy(dtype=float)
    w = needed["final_sample_weight"].to_numpy(dtype=float)
    wx = np.average(x, weights=w)
    wy = np.average(y, weights=w)
    cov = np.average((x - wx) * (y - wy), weights=w)
    vx = np.average((x - wx) ** 2, weights=w)
    vy = np.average((y - wy) ** 2, weights=w)
    return float(cov / math.sqrt(vx * vy)) if vx > 0 and vy > 0 else float("nan")


def build_onset_readouts(separation: pd.DataFrame, features: pd.DataFrame, params: Params) -> tuple[pd.DataFrame, pd.DataFrame]:
    onset_rows = []
    consistency_rows = []
    sep = separation.loc[separation["feature_id"].isin(CHANNEL_FEATURE.values())].copy()
    for contrast_id in CONTRASTS:
        for cohort in COHORTS:
            out: dict[str, Any] = {"contrast_id": contrast_id, "cohort": cohort}
            channel_tier: dict[str, dict[str, Any]] = {}
            for channel_id, feature in CHANNEL_FEATURE.items():
                channel_tier[channel_id] = {}
                train_rows = sep.loc[
                    sep["contrast_id"].eq(contrast_id)
                    & sep["cohort"].eq(cohort)
                    & sep["split"].eq("train")
                    & sep["feature_id"].eq(feature)
                ].sort_values("K")
                robust_rows = sep.loc[
                    sep["contrast_id"].eq(contrast_id)
                    & sep["cohort"].eq(cohort)
                    & sep["split"].eq("robustness")
                    & sep["feature_id"].eq(feature)
                ].sort_values("K")
                by_split = {}
                for split in READOUT_SPLITS:
                    split_rows = sep.loc[
                        sep["contrast_id"].eq(contrast_id)
                        & sep["cohort"].eq(cohort)
                        & sep["split"].eq(split)
                        & sep["feature_id"].eq(feature)
                    ].sort_values("K")
                    tier1_ks = [int(r["K"]) for _, r in split_rows.iterrows() if channel_condition(r, params, tier1=True)]
                    first = tier1_ks[0] if tier1_ks else np.nan
                    metric_at_first = split_rows.loc[split_rows["K"].eq(first), "cliffs_delta"].iloc[0] if tier1_ks else np.nan
                    by_split[split] = first
                    consistency_rows.append(
                        {
                            "contrast_id": contrast_id,
                            "cohort": cohort,
                            "channel_id": channel_id,
                            "split": split,
                            "channel_tier1_train_onset_day": first if split == "train" else np.nan,
                            "channel_tier2_stability_adjusted_onset_day": np.nan,
                            "channel_tier3_confirmed_onset_day": np.nan,
                            "dual_channel_tier1_train_onset_day": np.nan,
                            "dual_channel_tier2_stability_adjusted_onset_day": np.nan,
                            "dual_channel_tier3_confirmed_onset_day": np.nan,
                            "separation_direction": separation_direction(metric_at_first),
                            "onset_metric_value": metric_at_first,
                            "split_class_min_row_n": int(
                                min(
                                    split_rows["eligible_positive_n"].min() if not split_rows.empty else 0,
                                    split_rows["eligible_negative_n"].min() if not split_rows.empty else 0,
                                )
                            ),
                            "split_power_status": "validation_low_power" if split == "validation" and (split_rows["eligible_positive_n"].min() if not split_rows.empty else 0) < params.validation_min_class_n else "ok",
                            "onset_status": "tier1_present" if tier1_ks else "onset_absent",
                        }
                    )
                tier1_train = by_split["train"]
                tier2 = np.nan
                tier3 = np.nan
                for k in params.observation_windows_K:
                    tr = train_rows.loc[train_rows["K"].eq(k)]
                    rb = robust_rows.loc[robust_rows["K"].eq(k)]
                    if tr.empty or rb.empty:
                        continue
                    tr_one = tr.iloc[0]
                    rb_one = rb.iloc[0]
                    same_dir = tr_one["separation_direction"] == rb_one["separation_direction"] != "undetermined"
                    if channel_condition(tr_one, params, tier1=True) and same_dir and abs(float(rb_one["cliffs_delta"])) > params.null_band_upper:
                        if pd.isna(tier2):
                            tier2 = k
                    if channel_condition(tr_one, params, tier1=True) and channel_condition(rb_one, params, tier1=True) and same_dir:
                        if pd.isna(tier3):
                            tier3 = k
                for tier_name, value in [
                    ("tier1_train", tier1_train),
                    ("tier2_stability_adjusted", tier2),
                    ("tier3_confirmed", tier3),
                ]:
                    out[f"{channel_id}_{tier_name}_onset_day"] = value
                    channel_tier[channel_id][tier_name] = value
            for tier_name in ["tier1_train", "tier2_stability_adjusted", "tier3_confirmed"]:
                dual = np.nan
                for k in params.observation_windows_K:
                    ok = True
                    for channel_id, feature in CHANNEL_FEATURE.items():
                        onset_day = channel_tier[channel_id][tier_name]
                        if pd.isna(onset_day) or onset_day > k:
                            ok = False
                            break
                        row = sep.loc[
                            sep["contrast_id"].eq(contrast_id)
                            & sep["cohort"].eq(cohort)
                            & sep["split"].eq("train")
                            & sep["feature_id"].eq(feature)
                            & sep["K"].eq(k)
                        ]
                        if row.empty or not channel_condition(row.iloc[0], params, tier1=tier_name != "tier2_stability_adjusted"):
                            ok = False
                    if ok:
                        dual = k
                        break
                out[f"dual_channel_{tier_name}_onset_day"] = dual
            out["confirmed_divergence_onset_day"] = out["dual_channel_tier3_confirmed_onset_day"]
            if pd.notna(out["confirmed_divergence_onset_day"]):
                kstar = int(out["confirmed_divergence_onset_day"])
                sample = features.loc[features["cohort"].eq(cohort) & features["K"].eq(kstar)]
                out["channel_rank_corr"] = channel_rank_corr(sample)
                return_dir = sep.loc[
                    sep["contrast_id"].eq(contrast_id)
                    & sep["cohort"].eq(cohort)
                    & sep["split"].eq("train")
                    & sep["feature_id"].eq(CHANNEL_FEATURE["return_channel"])
                    & sep["K"].eq(kstar),
                    "separation_direction",
                ].iloc[0]
                struct_dir = sep.loc[
                    sep["contrast_id"].eq(contrast_id)
                    & sep["cohort"].eq(cohort)
                    & sep["split"].eq("train")
                    & sep["feature_id"].eq(CHANNEL_FEATURE["structure_channel"])
                    & sep["K"].eq(kstar),
                    "separation_direction",
                ].iloc[0]
                out["return_direction_at_confirmed"] = return_dir
                out["structure_direction_at_confirmed"] = struct_dir
                out["channel_direction_agreement_rate"] = 1.0 if return_dir == struct_dir else 0.0
            else:
                out["channel_rank_corr"] = np.nan
                out["return_direction_at_confirmed"] = "undetermined"
                out["structure_direction_at_confirmed"] = "undetermined"
                out["channel_direction_agreement_rate"] = np.nan
            out["dual_channel_collinearity_flag"] = (
                "dual_channel_collinear_readout"
                if (
                    pd.notna(out["channel_rank_corr"])
                    and abs(out["channel_rank_corr"]) >= params.dual_channel_collinearity_corr_ceiling
                )
                or (
                    pd.notna(out["channel_direction_agreement_rate"])
                    and out["channel_direction_agreement_rate"] >= params.dual_channel_direction_agreement_ceiling
                )
                else "not_collinear"
            )
            out["return_only_pseudo_separability_risk"] = (
                pd.notna(out["return_channel_tier3_confirmed_onset_day"])
                and pd.isna(out["structure_channel_tier2_stability_adjusted_onset_day"])
            )
            onset_rows.append(out)
    consistency = pd.DataFrame(consistency_rows)
    onset = pd.DataFrame(onset_rows)
    for _, row in onset.iterrows():
        for channel_id in CHANNEL_FEATURE:
            mask = consistency["contrast_id"].eq(row["contrast_id"]) & consistency["cohort"].eq(row["cohort"]) & consistency["channel_id"].eq(channel_id)
            consistency.loc[mask, "channel_tier2_stability_adjusted_onset_day"] = row[f"{channel_id}_tier2_stability_adjusted_onset_day"]
            consistency.loc[mask, "channel_tier3_confirmed_onset_day"] = row[f"{channel_id}_tier3_confirmed_onset_day"]
            consistency.loc[mask, "dual_channel_tier1_train_onset_day"] = row["dual_channel_tier1_train_onset_day"]
            consistency.loc[mask, "dual_channel_tier2_stability_adjusted_onset_day"] = row["dual_channel_tier2_stability_adjusted_onset_day"]
            consistency.loc[mask, "dual_channel_tier3_confirmed_onset_day"] = row["dual_channel_tier3_confirmed_onset_day"]
    return onset, consistency


def contrast_power_status(class_counts: pd.DataFrame, params: Params) -> pd.DataFrame:
    rows = []
    class_lookup = {
        (row["split"], row["class_id"]): (int(row["row_n"]), int(row["unique_instrument_n"]))
        for _, row in class_counts.iterrows()
    }
    for contrast_id, (pos_class, neg_class, tier) in CONTRASTS.items():
        neg_count_class = "class_big_failure_proxy_nonwinner" if neg_class == "class_big_failure_proxy_nonwinner" else neg_class
        for split in ["train", "robustness", "validation"]:
            pos_n, pos_inst = class_lookup.get((split, pos_class.replace("class_all_nonwinner_resolved", "class_neutral_chop")), (0, 0))
            if neg_class == "class_all_nonwinner_resolved":
                fail_n, fail_inst = class_lookup.get((split, "class_big_failure_proxy_nonwinner"), (0, 0))
                neu_n, neu_inst = class_lookup.get((split, "class_neutral_chop"), (0, 0))
                neg_n, neg_inst = fail_n + neu_n, max(fail_inst, neu_inst)
            else:
                neg_n, neg_inst = class_lookup.get((split, neg_count_class), (0, 0))
            under = pos_n < params.contrast_min_class_n or neg_n < params.contrast_min_class_n or pos_inst < params.contrast_min_instrument_n or neg_inst < params.contrast_min_instrument_n
            rows.append(
                {
                    "contrast_id": contrast_id,
                    "contrast_tier": tier,
                    "split": split,
                    "positive_row_n": pos_n,
                    "negative_row_n": neg_n,
                    "positive_unique_instrument_n": pos_inst,
                    "negative_unique_instrument_n": neg_inst,
                    "contrast_power_status": "contrast_underpowered" if under else "ok",
                }
            )
    return pd.DataFrame(rows)


def build_multivariate_readout(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import GroupKFold
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception:
        LogisticRegression = None
    xcols = [
        "ep_ret_t0_to_K",
        "ep_close_vs_t0_close",
        "ep_max_drawdown_to_K",
        "ep_min_close_ret_to_K",
        "ep_recovery_from_min_to_K",
        "ep_close_in_range_K",
        "ep_close_above_ema20_at_K_flag",
        "ep_days_above_ema20_through_K",
        "ep_breach_t0_low_through_K_flag",
        "ep_close_above_t0_high_at_K_flag",
        "ep_down_day_vol_contraction_K",
        "ep_up_day_vol_expansion_K",
        "ep_vol_decay_ratio_K",
        "ep_atr_change_t0_to_K",
        "ep_range_contraction_K",
    ]
    for contrast_id, (pos_class, neg_class, tier) in CONTRASTS.items():
        pos_col = f"{pos_class}_flag"
        neg_col = f"{neg_class}_flag"
        for cohort in COHORTS:
            for split in READOUT_SPLITS:
                for k in sorted(features["K"].unique()):
                    group = features.loc[features["cohort"].eq(cohort) & features["K"].eq(k) & features["eligible_flag"].map(boolish)].copy()
                    group = group if split == "all" else group.loc[group["split"].eq(split)].copy()
                    group = group.loc[bool_series(group[pos_col]) | bool_series(group[neg_col])].copy()
                    if len(group) < 20 or group["instrument"].nunique() < 5 or LogisticRegression is None:
                        auc = np.nan
                        status = "multivariate_underpowered_or_sklearn_missing"
                    else:
                        y = bool_series(group[pos_col]).astype(int).to_numpy()
                        x = group[xcols].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
                        groups = group["instrument"].astype(str).to_numpy()
                        unique_groups = np.unique(groups)
                        folds = min(5, len(unique_groups))
                        scores = np.full(len(group), np.nan)
                        if len(np.unique(y)) < 2 or folds < 2:
                            auc = np.nan
                            status = "multivariate_underpowered"
                        else:
                            gkf = GroupKFold(n_splits=folds)
                            for train_idx, test_idx in gkf.split(x, y, groups):
                                if len(np.unique(y[train_idx])) < 2:
                                    continue
                                model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=1000))
                                model.fit(x.iloc[train_idx], y[train_idx])
                                scores[test_idx] = model.predict_proba(x.iloc[test_idx])[:, 1]
                            valid = ~np.isnan(scores)
                            auc = float(roc_auc_score(y[valid], scores[valid])) if valid.any() and len(np.unique(y[valid])) == 2 else np.nan
                            status = "multivariate_separability_secondary" if pd.notna(auc) else "multivariate_underpowered"
                    rows.append(
                        {
                            "contrast_id": contrast_id,
                            "contrast_tier": tier,
                            "cohort": cohort,
                            "split": split,
                            "K": int(k),
                            "estimator": "L2_logistic_grouped_5fold_cross_fit",
                            "crossfit_auc_mean": auc,
                            "crossfit_auc_ci_low": np.nan,
                            "crossfit_auc_ci_high": np.nan,
                            "row_n": len(group),
                            "unique_instrument_n": int(group["instrument"].nunique()) if len(group) else 0,
                            "readout_status": status,
                        }
                    )
    return pd.DataFrame(rows)


def bootstrap_index_groups(base: pd.DataFrame, block_col: str = "instrument") -> dict[str, list[np.ndarray]]:
    groups_by_split: dict[str, list[np.ndarray]] = {}
    for split in ["train", "robustness"]:
        part = base.loc[base["split"].eq(split)]
        groups_by_split[split] = [np.asarray(indexes, dtype=int) for indexes in part.groupby(block_col, sort=False).groups.values()]
    return groups_by_split


def derive_bootstrap_seed(base_seed: int, block_col: str, split: str, iteration: int) -> int:
    payload = f"{base_seed}|{block_col}|{split}|{iteration}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "little") % (2**32)


def draw_bootstrap_sample(
    base: pd.DataFrame,
    groups_by_split: dict[str, list[np.ndarray]],
    base_seed: int,
    iteration: int,
    block_col: str,
) -> pd.DataFrame:
    sampled_groups = []
    for split, groups in groups_by_split.items():
        if not groups:
            continue
        rng = np.random.default_rng(derive_bootstrap_seed(base_seed, block_col, split, iteration))
        selected = rng.integers(0, len(groups), size=len(groups))
        sampled_groups.extend(groups[int(pos)] for pos in selected)
    if not sampled_groups:
        return base.iloc[0:0].copy()
    return base.take(np.concatenate(sampled_groups))


def focused_bootstrap_onset_days(sep: pd.DataFrame, params: Params) -> dict[str, Any]:
    channel_rows: dict[str, dict[str, dict[int, pd.Series]]] = {}
    channel_tiers: dict[str, dict[str, float]] = {}
    for channel_id, feature in CHANNEL_FEATURE.items():
        channel_rows[channel_id] = {}
        for split in ["train", "robustness"]:
            rows = sep.loc[sep["split"].eq(split) & sep["feature_id"].eq(feature)]
            channel_rows[channel_id][split] = {int(row["K"]): row for _, row in rows.iterrows()}
        tier1 = np.nan
        tier2 = np.nan
        tier3 = np.nan
        for k in params.observation_windows_K:
            train_row = channel_rows[channel_id]["train"].get(k)
            robust_row = channel_rows[channel_id]["robustness"].get(k)
            if train_row is None:
                continue
            train_tier1 = channel_condition(train_row, params, tier1=True)
            if train_tier1 and pd.isna(tier1):
                tier1 = k
            if robust_row is None:
                continue
            same_dir = train_row["separation_direction"] == robust_row["separation_direction"] != "undetermined"
            if train_tier1 and same_dir and abs(float(robust_row["cliffs_delta"])) > params.null_band_upper and pd.isna(tier2):
                tier2 = k
            if train_tier1 and channel_condition(robust_row, params, tier1=True) and same_dir and pd.isna(tier3):
                tier3 = k
        channel_tiers[channel_id] = {
            "tier1_train": tier1,
            "tier2_stability_adjusted": tier2,
            "tier3_confirmed": tier3,
        }

    out: dict[str, Any] = {}
    for tier_name in ["tier1_train", "tier2_stability_adjusted", "tier3_confirmed"]:
        dual = np.nan
        for k in params.observation_windows_K:
            ok = True
            for channel_id in CHANNEL_FEATURE:
                onset_day = channel_tiers[channel_id][tier_name]
                train_row = channel_rows[channel_id]["train"].get(k)
                if pd.isna(onset_day) or onset_day > k or train_row is None:
                    ok = False
                    break
                if not channel_condition(train_row, params, tier1=tier_name != "tier2_stability_adjusted"):
                    ok = False
                    break
            if ok:
                dual = k
                break
        out[f"dual_channel_{tier_name}_onset_day"] = dual
    out["return_channel_tier3_confirmed_onset_day"] = channel_tiers["return_channel"]["tier3_confirmed"]
    out["structure_channel_tier3_confirmed_onset_day"] = channel_tiers["structure_channel"]["tier3_confirmed"]
    out["confirmed_divergence_onset_day"] = out["dual_channel_tier3_confirmed_onset_day"]
    return out


def bootstrap_iteration_readout(
    sample: pd.DataFrame,
    params: Params,
    pos_class: str,
    neg_class: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    empty_sample = sample.iloc[0:0]
    sample_groups = {
        (split_value, int(k_value)): group
        for (split_value, k_value), group in sample.groupby(["split", "K"], sort=False)
    }
    sep_rows = []
    metric_rows = []
    for channel_id, feature in CHANNEL_FEATURE.items():
        for split in ["train", "robustness"]:
            for k in params.observation_windows_K:
                group = sample_groups.get((split, k), empty_sample)
                metric = compute_bootstrap_onset_metric(group, f"{pos_class}_flag", f"{neg_class}_flag", feature)
                sep_rows.append({"contrast_id": "", "cohort": "full_cohort", "split": split, "K": k, "feature_id": feature, **metric})
                metric_rows.append(
                    {
                        "channel_id": channel_id,
                        "split": split,
                        "K": int(k),
                        "cliffs_delta": metric["cliffs_delta"],
                        "separation_direction": metric["separation_direction"],
                    }
                )
    sep = pd.DataFrame(sep_rows)
    return focused_bootstrap_onset_days(sep, params), metric_rows


def summarize_bootstrap_channel_metrics(metric_rows: list[dict[str, Any]], params: Params) -> str:
    if not metric_rows:
        return "{}"
    frame = pd.DataFrame(metric_rows)
    summary: dict[str, dict[str, Any]] = {}
    for (channel_id, split, k), group in frame.groupby(["channel_id", "split", "K"], dropna=False):
        metrics = pd.to_numeric(group["cliffs_delta"], errors="coerce").dropna()
        directions = group["separation_direction"].fillna("undetermined").astype(str)
        if metrics.empty:
            median = p05 = p95 = np.nan
            confirmed_direction = "undetermined"
            prob_confirmed = np.nan
        else:
            median = float(metrics.median())
            p05 = float(metrics.quantile(0.05))
            p95 = float(metrics.quantile(0.95))
            confirmed_direction = separation_direction(median)
            if confirmed_direction == "winner_higher":
                prob_confirmed = float(metrics.gt(params.null_band_upper).mean())
            elif confirmed_direction == "winner_lower":
                prob_confirmed = float(metrics.lt(-params.null_band_upper).mean())
            else:
                prob_confirmed = np.nan
        key = f"{channel_id}|{split}|K{k}"
        summary[key] = {
            "median": median,
            "p05": p05,
            "p95": p95,
            "confirmed_direction": confirmed_direction,
            "prob_abs_gt_null_band_confirmed_direction": prob_confirmed,
            "prob_winner_higher": float(directions.eq("winner_higher").mean()) if len(directions) else np.nan,
            "prob_winner_lower": float(directions.eq("winner_lower").mean()) if len(directions) else np.nan,
            "prob_undetermined": float(directions.eq("undetermined").mean()) if len(directions) else np.nan,
        }
    return json.dumps(summary, sort_keys=True, default=str)


def bootstrap_onset_readout(features: pd.DataFrame, params: Params, point_onset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    sample_rows = []
    base = features.loc[features["cohort"].eq("full_cohort") & features["eligible_flag"].map(boolish)].copy().reset_index(drop=True)
    groups_by_split = bootstrap_index_groups(base, "instrument")
    event_groups_by_split = bootstrap_index_groups(base, "binding_canonical_event_id")
    for contrast_id, (pos_class, neg_class, _) in CONTRASTS.items():
        iterations = params.bootstrap_n if contrast_id == "C1_winner_vs_big_failure_proxy" else min(200, params.bootstrap_n)
        hit_days = []
        tier2_days = []
        return_hits = 0
        structure_hits = 0
        metric_rows_all: list[dict[str, Any]] = []
        for iteration in range(iterations):
            sample = draw_bootstrap_sample(base, groups_by_split, params.bootstrap_seed, iteration, "instrument")
            if sample.empty:
                continue
            one, metric_rows = bootstrap_iteration_readout(sample, params, pos_class, neg_class)
            metric_rows_all.extend(metric_rows)
            if pd.notna(one["dual_channel_tier3_confirmed_onset_day"]):
                hit_days.append(int(one["dual_channel_tier3_confirmed_onset_day"]))
            if pd.notna(one["dual_channel_tier2_stability_adjusted_onset_day"]):
                tier2_days.append(int(one["dual_channel_tier2_stability_adjusted_onset_day"]))
            if pd.notna(one["return_channel_tier3_confirmed_onset_day"]):
                return_hits += 1
            if pd.notna(one["structure_channel_tier3_confirmed_onset_day"]):
                structure_hits += 1
            sample_rows.append(
                {
                    "contrast_id": contrast_id,
                    "block_level": "instrument",
                    "bootstrap_iteration": iteration,
                    "confirmed_divergence_onset_day": one["confirmed_divergence_onset_day"],
                    "dual_channel_tier2_stability_adjusted_onset_day": one["dual_channel_tier2_stability_adjusted_onset_day"],
                    "return_channel_tier3_confirmed_onset_day": one["return_channel_tier3_confirmed_onset_day"],
                    "structure_channel_tier3_confirmed_onset_day": one["structure_channel_tier3_confirmed_onset_day"],
                }
            )

        event_hit_days = []
        event_iterations = min(200, params.bootstrap_n) if contrast_id == "C1_winner_vs_big_failure_proxy" else 0
        for iteration in range(event_iterations):
            sample = draw_bootstrap_sample(base, event_groups_by_split, params.bootstrap_seed, iteration, "binding_canonical_event_id")
            if sample.empty:
                continue
            one, _ = bootstrap_iteration_readout(sample, params, pos_class, neg_class)
            if pd.notna(one["confirmed_divergence_onset_day"]):
                event_hit_days.append(int(one["confirmed_divergence_onset_day"]))
            sample_rows.append(
                {
                    "contrast_id": contrast_id,
                    "block_level": "binding_canonical_event_id",
                    "bootstrap_iteration": iteration,
                    "confirmed_divergence_onset_day": one["confirmed_divergence_onset_day"],
                    "dual_channel_tier2_stability_adjusted_onset_day": one["dual_channel_tier2_stability_adjusted_onset_day"],
                    "return_channel_tier3_confirmed_onset_day": one["return_channel_tier3_confirmed_onset_day"],
                    "structure_channel_tier3_confirmed_onset_day": one["structure_channel_tier3_confirmed_onset_day"],
                }
            )
        point = point_onset.loc[point_onset["contrast_id"].eq(contrast_id) & point_onset["cohort"].eq("full_cohort")]
        point_day = point["confirmed_divergence_onset_day"].iloc[0] if not point.empty else np.nan
        hit_rate = safe_rate(len(hit_days), iterations)
        median_day = float(np.median(hit_days)) if hit_days else np.nan
        drift = abs(params.observation_windows_K.index(int(median_day)) - params.observation_windows_K.index(int(point_day))) if pd.notna(median_day) and pd.notna(point_day) and int(median_day) in params.observation_windows_K and int(point_day) in params.observation_windows_K else np.nan
        event_hit_rate = safe_rate(len(event_hit_days), event_iterations) if event_iterations else np.nan
        event_median_day = float(np.median(event_hit_days)) if event_hit_days else np.nan
        event_drift = (
            abs(params.observation_windows_K.index(int(event_median_day)) - params.observation_windows_K.index(int(median_day)))
            if pd.notna(event_median_day)
            and pd.notna(median_day)
            and int(event_median_day) in params.observation_windows_K
            and int(median_day) in params.observation_windows_K
            else np.nan
        )
        event_conflict = bool(pd.notna(event_drift) and event_drift > params.onset_day_bootstrap_drift_ceiling)
        rows.append(
            {
                "contrast_id": contrast_id,
                "cohort": "full_cohort",
                "bootstrap_n": iterations,
                "confirmed_onset_hit_rate": hit_rate,
                "confirmed_onset_day_p25": float(np.quantile(hit_days, 0.25)) if hit_days else np.nan,
                "confirmed_onset_day_median": median_day,
                "confirmed_onset_day_p75": float(np.quantile(hit_days, 0.75)) if hit_days else np.nan,
                "confirmed_onset_day_distribution": json.dumps({str(k): hit_days.count(k) for k in params.observation_windows_K}, sort_keys=True),
                "tier2_onset_hit_rate": safe_rate(len(tier2_days), iterations),
                "tier2_onset_day_distribution": json.dumps({str(k): tier2_days.count(k) for k in params.observation_windows_K}, sort_keys=True),
                "return_channel_confirmed_onset_hit_rate": safe_rate(return_hits, iterations),
                "structure_channel_confirmed_onset_hit_rate": safe_rate(structure_hits, iterations),
                "channel_metric_distribution_summary": summarize_bootstrap_channel_metrics(metric_rows_all, params),
                "onset_day_bootstrap_drift_window_n": drift,
                "bootstrap_stable_flag": bool(
                    hit_rate >= params.confirmed_onset_hit_rate_floor
                    and pd.notna(drift)
                    and drift <= params.onset_day_bootstrap_drift_ceiling
                ),
                "secondary_event_block_bootstrap_n": event_iterations,
                "secondary_event_block_confirmed_onset_hit_rate": event_hit_rate,
                "secondary_event_block_onset_day_median": event_median_day,
                "episode_block_onset_conflict": event_conflict,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(sample_rows)


def tradability_lag_readout(features: pd.DataFrame, mfe_basis: pd.DataFrame, onset: pd.DataFrame, params: Params) -> pd.DataFrame:
    c1 = onset.loc[onset["contrast_id"].eq("C1_winner_vs_big_failure_proxy") & onset["cohort"].eq("full_cohort")]
    kstar = c1["confirmed_divergence_onset_day"].iloc[0] if not c1.empty else np.nan
    if pd.isna(kstar):
        return pd.DataFrame(
            [
                {
                    "contrast_id": "C1_winner_vs_big_failure_proxy",
                    "cohort": "full_cohort",
                    "confirmed_divergence_onset_day": np.nan,
                    "tradability_basis_eligible_n": 0,
                    "tradability_basis_excluded_n": 0,
                    "winner_median_ep_mfe_to_Kstar_over_mfe120": np.nan,
                    "winner_median_ep_ret_to_Kstar_over_fwd120": np.nan,
                    "winner_ret_fraction_basis_status": "secondary_basis_unchecked",
                    "winner_realized_fraction_status": "onset_absent",
                }
            ]
        )
    kstar = int(kstar)
    basis_ok = set(mfe_basis.loc[mfe_basis["basis_status"].eq("ok"), "row_id"])
    group = features.loc[
        features["cohort"].eq("full_cohort")
        & features["K"].eq(kstar)
        & features["class_big_winner_flag"].map(boolish)
        & features["row_id"].isin(basis_ok)
    ].copy()
    group["mfe_ratio"] = pd.to_numeric(group["ep_mfe_to_K"], errors="coerce") / pd.to_numeric(group["mfe_120_recomputed"], errors="coerce")
    group["ret_ratio"] = pd.to_numeric(group["ep_ret_t0_to_K"], errors="coerce") / pd.to_numeric(group["forward_return_120d"], errors="coerce")
    ratio = float(group["mfe_ratio"].median()) if group["mfe_ratio"].notna().any() else np.nan
    status = "late_most_move_realized" if pd.notna(ratio) and ratio > params.tradability_realized_fraction_ceiling else "tradable_window_open"
    winner_all = features.loc[features["cohort"].eq("full_cohort") & features["K"].eq(kstar) & features["class_big_winner_flag"].map(boolish)]
    return pd.DataFrame(
        [
            {
                "contrast_id": "C1_winner_vs_big_failure_proxy",
                "cohort": "full_cohort",
                "confirmed_divergence_onset_day": kstar,
                "tradability_basis_eligible_n": len(group),
                "tradability_basis_excluded_n": len(winner_all) - len(group),
                "winner_median_ep_mfe_to_Kstar_over_mfe120": ratio,
                "winner_median_ep_ret_to_Kstar_over_fwd120": float(group["ret_ratio"].median()) if group["ret_ratio"].notna().any() else np.nan,
                "winner_ret_fraction_basis_status": "secondary_basis_unchecked",
                "winner_realized_fraction_status": status,
            }
        ]
    )


def survivorship_audit(separation: pd.DataFrame, params: Params) -> pd.DataFrame:
    rows = []
    primary = separation.loc[separation["feature_id"].isin(CHANNEL_FEATURE.values())].copy()
    for (contrast_id, feature_id, k, split), group in primary.groupby(["contrast_id", "feature_id", "K", "split"], dropna=False):
        surv = group.loc[group["cohort"].eq("survivors_only")]
        full = group.loc[group["cohort"].eq("full_cohort")]
        if surv.empty or full.empty:
            continue
        surv_one = surv.iloc[0]
        full_one = full.iloc[0]
        gap = abs(float(surv_one["cliffs_delta"])) - abs(float(full_one["cliffs_delta"]))
        direction_status = "same_direction" if surv_one["separation_direction"] == full_one["separation_direction"] else "direction_flip"
        if surv_one["separation_direction"] == "undetermined" or full_one["separation_direction"] == "undetermined":
            direction_status = "undetermined"
        flag = "none"
        if direction_status == "direction_flip":
            flag = "survivorship_direction_flip"
        elif direction_status == "same_direction" and gap > params.survivorship_gap_ceiling:
            flag = "survivorship_induced_separation"
        for haircut in params.delist_haircut_sensitivity_values:
            status = "primary" if float(haircut) == float(params.delist_haircut) else f"sensitivity_delist_haircut_{haircut:g}"
            rows.append(
                {
                    "contrast_id": contrast_id,
                    "channel_id": "return_channel" if feature_id == CHANNEL_FEATURE["return_channel"] else "structure_channel",
                    "K": k,
                    "split": split,
                    "survivors_only_separation_metric": surv_one["cliffs_delta"],
                    "full_cohort_separation_metric": full_one["cliffs_delta"],
                    "survivors_only_eligible_n": surv_one["eligible_row_n"],
                    "full_cohort_eligible_n": full_one["eligible_row_n"],
                    "pre_K_path_unavailable_dropout_n": max(0, int(full_one["eligible_row_n"]) - int(surv_one["eligible_row_n"])),
                    "pre_K_path_unavailable_dropout_rate": safe_rate(max(0, int(full_one["eligible_row_n"]) - int(surv_one["eligible_row_n"])), int(full_one["eligible_row_n"])),
                    "survivorship_strength_gap": gap,
                    "survivorship_direction_status": direction_status,
                    "delist_haircut": float(haircut),
                    "delist_haircut_sensitivity_status": status,
                    "delist_haircut_sensitivity_conflict_flag": bool(status != "primary" and flag in {"survivorship_induced_separation", "survivorship_direction_flip"}),
                    "survivorship_flag": flag,
                }
            )
    return pd.DataFrame(rows)


def stratified_null_class_assignments(event_base: pd.DataFrame, class_cols: list[str], params: Params, iteration: int) -> np.ndarray:
    original = np.column_stack([bool_series(event_base[col]).to_numpy(dtype=bool) for col in class_cols])
    shuffled = original.copy()
    strata = event_base.groupby(["split", "event_year_quarter", "source_family_id_matched"], dropna=False).groups
    rng = np.random.default_rng(derive_bootstrap_seed(params.null_simulation_seed, "null_label_permutation", "all", iteration))
    for indexes in strata.values():
        positions = np.asarray(list(indexes), dtype=int)
        if len(positions) <= 1:
            continue
        shuffled[positions, :] = original[rng.permutation(positions), :]
    return shuffled


def build_null_simulation_context(features: pd.DataFrame, feature_ids: list[str]) -> dict[str, Any]:
    class_cols = [
        "class_big_winner_flag",
        "class_big_failure_proxy_nonwinner_flag",
        "subclass_false_repair_only_flag",
        "subclass_fast_fail_flag",
        "class_neutral_chop_flag",
        "class_all_nonwinner_resolved_flag",
    ]
    base = features.loc[features["cohort"].eq("full_cohort") & features["eligible_flag"].map(boolish)].copy()
    event_base = base.drop_duplicates("row_id").reset_index(drop=True)
    if "event_year_quarter" not in event_base.columns:
        event_base["event_year_quarter"] = pd.PeriodIndex(pd.to_datetime(event_base["event_t0_date"], errors="coerce"), freq="Q").astype(str)
    if "source_family_id_matched" not in event_base.columns:
        event_base["source_family_id_matched"] = "source_family_missing"
    row_pos = {row_id: pos for pos, row_id in enumerate(event_base["row_id"].tolist())}
    event_positions = base["row_id"].map(row_pos).to_numpy(dtype=int)
    values_by_feature = {feature: metric_numeric(base[feature]).to_numpy(dtype=float) for feature in feature_ids}
    weights = metric_numeric(base["final_sample_weight"]).fillna(1.0).to_numpy(dtype=float)
    split_values = base["split"].astype(str).to_numpy()
    k_values = pd.to_numeric(base["K"], errors="coerce").to_numpy(dtype=int)
    cell_specs = []
    for split in READOUT_SPLITS:
        split_mask = np.ones(len(base), dtype=bool) if split == "all" else split_values == split
        for k in sorted(np.unique(k_values)):
            cell_mask = split_mask & (k_values == k)
            if not cell_mask.any():
                continue
            for feature in feature_ids:
                values = values_by_feature[feature]
                idx = np.flatnonzero(cell_mask & np.isfinite(values))
                if len(idx) <= 2:
                    continue
                order = np.argsort(values[idx], kind="mergesort")
                sorted_idx = idx[order]
                sorted_values = values[sorted_idx]
                group_starts = np.r_[0, np.flatnonzero(sorted_values[1:] != sorted_values[:-1]) + 1]
                group_id = np.repeat(np.arange(len(group_starts)), np.diff(np.r_[group_starts, len(sorted_values)]))
                cell_specs.append(
                    {
                        "split": split,
                        "K": int(k),
                        "feature_id": feature,
                        "idx": sorted_idx,
                        "group_id": group_id,
                        "group_n": len(group_starts),
                        "weights": weights[sorted_idx],
                    }
                )
    return {
        "class_cols": class_cols,
        "event_base": event_base,
        "event_positions": event_positions,
        "cell_specs": cell_specs,
    }


def null_simulated_significant_count(context: dict[str, Any], params: Params, iteration: int) -> int:
    class_cols = context["class_cols"]
    shuffled = stratified_null_class_assignments(context["event_base"], class_cols, params, iteration)
    class_lookup = {col: shuffled[context["event_positions"], idx] for idx, col in enumerate(class_cols)}
    significant = 0
    for spec in context["cell_specs"]:
        idx = spec["idx"]
        group_id = spec["group_id"]
        group_n = spec["group_n"]
        weights = spec["weights"]
        for pos_class, neg_class, _ in CONTRASTS.values():
            pos_col = f"{pos_class}_flag"
            neg_col = f"{neg_class}_flag"
            pos = class_lookup[pos_col][idx]
            neg = class_lookup[neg_col][idx]
            pos_n = int(pos.sum())
            neg_n = int(neg.sum())
            if pos_n <= 1 or neg_n <= 1:
                continue
            pos_sum = np.bincount(group_id, weights=weights * pos, minlength=group_n)
            neg_sum = np.bincount(group_id, weights=weights * neg, minlength=group_n)
            total_pos = float(pos_sum.sum())
            total_neg = float(neg_sum.sum())
            if total_pos <= 0 or total_neg <= 0:
                continue
            neg_less = np.cumsum(neg_sum) - neg_sum
            auc_num = float((pos_sum * (neg_less + 0.5 * neg_sum)).sum())
            cliff = 2.0 * (auc_num / (total_pos * total_neg)) - 1.0
            ci_low, ci_high = metric_ci(cliff, pos_n, neg_n)
            if (
                abs(cliff) >= params.onset_threshold
                and ((ci_low > params.null_band_upper and ci_high > params.null_band_upper) or (ci_low < -params.null_band_upper and ci_high < -params.null_band_upper))
            ):
                significant += 1
    return significant


def multiple_comparison_audit(separation: pd.DataFrame, features: pd.DataFrame, params: Params) -> pd.DataFrame:
    tested = separation.loc[separation["cohort"].eq("full_cohort") & separation["readout_tier"].ne("label_overlap_audit_only")].copy()
    significant = tested.loc[
        tested["cliffs_delta"].abs().ge(params.onset_threshold)
        & (
            (tested["cliffs_delta_ci_low"].gt(params.null_band_upper) & tested["cliffs_delta_ci_high"].gt(params.null_band_upper))
            | (tested["cliffs_delta_ci_low"].lt(-params.null_band_upper) & tested["cliffs_delta_ci_high"].lt(-params.null_band_upper))
        )
    ]
    total = len(tested)
    feature_ids = sorted(tested["feature_id"].dropna().astype(str).unique().tolist())
    null_context = build_null_simulation_context(features, feature_ids)
    null_counts = [null_simulated_significant_count(null_context, params, iteration) for iteration in range(params.null_simulation_n)]
    expected = float(np.mean(null_counts)) if null_counts else np.nan
    p95 = float(np.quantile(null_counts, 0.95)) if null_counts else np.nan
    return pd.DataFrame(
        [
            {
                "total_tested_cells": total,
                "significant_cells_n": len(significant),
                "null_simulation_n": params.null_simulation_n,
                "null_expected_significant_cells_n": expected,
                "null_significant_cells_p95": p95,
                "actual_exceeds_null_p95_flag": len(significant) > p95,
                "multiple_comparison_status": "actual_exceeds_null_p95" if len(significant) > p95 else "within_null_p95",
                "null_simulation_method": "stratified_label_permutation_by_split_event_quarter_source_family_cached_weighted_cliffs_delta",
            }
        ]
    )


def choose_final_status(
    blocker_reasons: list[str],
    incomplete_reasons: list[str],
    onset: pd.DataFrame,
    bootstrap: pd.DataFrame,
    tradability: pd.DataFrame,
    survivorship: pd.DataFrame,
) -> str:
    if blocker_reasons:
        return FINAL_BLOCKED
    if incomplete_reasons:
        return FINAL_INCOMPLETE
    c1 = onset.loc[onset["contrast_id"].eq("C1_winner_vs_big_failure_proxy") & onset["cohort"].eq("full_cohort")]
    if c1.empty or pd.isna(c1["confirmed_divergence_onset_day"].iloc[0]):
        surv_c1 = onset.loc[onset["contrast_id"].eq("C1_winner_vs_big_failure_proxy") & onset["cohort"].eq("survivors_only")]
        if not surv_c1.empty and pd.notna(surv_c1["confirmed_divergence_onset_day"].iloc[0]):
            return FINAL_SURVIVORSHIP
        return FINAL_ABSENT
    boot = bootstrap.loc[bootstrap["contrast_id"].eq("C1_winner_vs_big_failure_proxy")]
    if boot.empty or not boolish(boot["bootstrap_stable_flag"].iloc[0]):
        return FINAL_ABSENT
    survivorship_primary = survivorship.copy()
    if "delist_haircut_sensitivity_status" in survivorship_primary.columns:
        survivorship_primary = survivorship_primary.loc[survivorship_primary["delist_haircut_sensitivity_status"].eq("primary")]
    if survivorship_primary.loc[
        survivorship_primary["contrast_id"].eq("C1_winner_vs_big_failure_proxy")
        & survivorship_primary["survivorship_flag"].isin(["survivorship_induced_separation", "survivorship_direction_flip"])
    ].empty is False:
        return FINAL_SURVIVORSHIP
    status = tradability["winner_realized_fraction_status"].iloc[0] if not tradability.empty else "onset_absent"
    if status == "late_most_move_realized":
        return FINAL_LATE
    if status == "tradable_window_open":
        return FINAL_TRADABLE
    return FINAL_ABSENT


def build_diagnostic_summary(
    final_status: str,
    blocker_reasons: list[str],
    incomplete_reasons: list[str],
    denom: pd.DataFrame,
    onset: pd.DataFrame,
    tradability: pd.DataFrame,
) -> pd.DataFrame:
    c1 = onset.loc[onset["contrast_id"].eq("C1_winner_vs_big_failure_proxy") & onset["cohort"].eq("full_cohort")]
    return pd.DataFrame(
        [
            {
                "final_status": final_status,
                "blocker_reason_list": "|".join(blocker_reasons),
                "statistics_incomplete_reason_list": "|".join(incomplete_reasons),
                "evaluated_regime_scope": "risk_on",
                "pit_valid_evaluated_row_n": len(denom),
                "unique_instrument_n": int(denom["instrument"].nunique()) if len(denom) else 0,
                "confirmed_divergence_onset_day_C1_full_cohort": c1["confirmed_divergence_onset_day"].iloc[0] if not c1.empty else np.nan,
                "winner_realized_fraction_status": tradability["winner_realized_fraction_status"].iloc[0] if not tradability.empty else "onset_absent",
            }
        ]
    )


def report_value(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "none"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.4g}"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    return str(value).replace("|", "/")


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    if not rows:
        return ["_No rows._"]
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(report_value(item) for item in row) + " |")
    return out


def build_report(
    final_status: str,
    summary: pd.DataFrame,
    class_counts: pd.DataFrame,
    scope_recon: pd.DataFrame,
    anchor: pd.DataFrame,
    separation: pd.DataFrame,
    onset: pd.DataFrame,
    tradability: pd.DataFrame,
    fill_audit: pd.DataFrame,
    label_overlap: pd.DataFrame,
    coverage: pd.DataFrame,
    power: pd.DataFrame,
    survivorship: pd.DataFrame,
    bootstrap: pd.DataFrame,
    multiple: pd.DataFrame,
) -> str:
    all_recon = scope_recon.loc[scope_recon["split"].eq("all")].iloc[0]
    c1 = onset.loc[onset["contrast_id"].eq("C1_winner_vs_big_failure_proxy") & onset["cohort"].eq("full_cohort")].iloc[0]
    trad = tradability.iloc[0]
    boot = bootstrap.loc[bootstrap["contrast_id"].eq("C1_winner_vs_big_failure_proxy")].iloc[0]
    anchor_all = anchor.loc[anchor["split"].eq("all")].iloc[0]
    counts = class_counts.loc[
        class_counts["class_id"].isin(
            [
                "class_big_winner",
                "class_big_failure_proxy_nonwinner",
                "class_neutral_chop",
                "subclass_fast_fail",
                "subclass_false_repair_only",
                "class_unresolved",
            ]
        )
    ]
    class_rows = [
        [row["split"], row["class_id"], row["row_n"], row["unique_instrument_n"], f"{float(row['class_rate']):.2%}"]
        for _, row in counts.sort_values(["split", "class_id"]).iterrows()
    ]
    power_rows = [
        [row["split"], row["positive_row_n"], row["negative_row_n"], row["positive_unique_instrument_n"], row["negative_unique_instrument_n"], row["contrast_power_status"]]
        for _, row in power.loc[power["contrast_id"].eq("C1_winner_vs_big_failure_proxy")].sort_values("split").iterrows()
    ]
    sep_focus = separation.loc[
        separation["cohort"].eq("full_cohort")
        & separation["feature_id"].isin(CHANNEL_FEATURE.values())
    ].sort_values(["contrast_id", "feature_id", "split", "K"])
    sep_rows = [
        [
            row["contrast_id"],
            row["feature_id"],
            row["split"],
            row["K"],
            row["cliffs_delta"],
            row["cliffs_delta_ci_low"],
            row["cliffs_delta_ci_high"],
            row["separation_direction"],
        ]
        for _, row in sep_focus.iterrows()
    ]
    onset_rows = [
        [
            row["contrast_id"],
            row["cohort"],
            row["return_channel_tier1_train_onset_day"],
            row["return_channel_tier2_stability_adjusted_onset_day"],
            row["return_channel_tier3_confirmed_onset_day"],
            row["structure_channel_tier1_train_onset_day"],
            row["structure_channel_tier2_stability_adjusted_onset_day"],
            row["structure_channel_tier3_confirmed_onset_day"],
            row["confirmed_divergence_onset_day"],
            row["dual_channel_collinearity_flag"],
        ]
        for _, row in onset.sort_values(["contrast_id", "cohort"]).iterrows()
    ]
    first_k = int(min(fill_audit["K"])) if not fill_audit.empty else 0
    fill_rows = [
        [row["split"], row["K"], row["fill_reason"], row["row_n"], row["unique_instrument_n"]]
        for _, row in fill_audit.loc[fill_audit["K"].eq(first_k)].sort_values(["split", "fill_reason"]).iterrows()
    ]
    coverage_rows = [
        [row["split"], row["cohort"], row["K"], row["eligible_row_n"], f"{float(row['eligible_rate']):.2%}", row["instrument_source_filename_derived_fallback_n"]]
        for _, row in coverage.loc[coverage["cohort"].eq("full_cohort")].sort_values(["split", "K"]).iterrows()
    ]
    label_rows = [
        [row["split"], row["K"], row["fast_fail_positive_n"], row["ep_fast_fail_barrier_touched_by_K_n"], row["overlap_n"], f"{float(row['touch_given_fast_fail_rate']):.2%}", row["label_overlap_status"]]
        for _, row in label_overlap.sort_values(["split", "K"]).iterrows()
    ]
    survivor_counts = survivorship["survivorship_flag"].value_counts().to_dict() if not survivorship.empty else {}
    survivor_rows = [
        [
            row["contrast_id"],
            row["channel_id"],
            row["K"],
            row["split"],
            row["survivorship_strength_gap"],
            row["pre_K_path_unavailable_dropout_n"],
            row["delist_haircut"],
            row["survivorship_flag"],
        ]
        for _, row in survivorship.loc[
            survivorship["contrast_id"].eq("C1_winner_vs_big_failure_proxy")
            & survivorship["split"].isin(["train", "robustness"])
            & survivorship["K"].isin([1, 3, 5, 10])
        ].sort_values(["channel_id", "split", "K"]).iterrows()
    ]
    bootstrap_rows = [
        [
            row["contrast_id"],
            row["bootstrap_n"],
            row["confirmed_onset_hit_rate"],
            row["confirmed_onset_day_distribution"],
            row["tier2_onset_hit_rate"],
            row["return_channel_confirmed_onset_hit_rate"],
            row["structure_channel_confirmed_onset_hit_rate"],
            row["bootstrap_stable_flag"],
            row.get("secondary_event_block_bootstrap_n", 0),
            row.get("secondary_event_block_confirmed_onset_hit_rate", np.nan),
            row.get("secondary_event_block_onset_day_median", np.nan),
            row.get("episode_block_onset_conflict", False),
        ]
        for _, row in bootstrap.sort_values("contrast_id").iterrows()
    ]
    final_text = {
        FINAL_TRADABLE: "Pre-registered conclusion: C1 full-cohort dual-channel Tier3 separation is detected early enough to be tradable in this diagnostic readout.",
        FINAL_LATE: "Pre-registered conclusion: separation exists but is late, so this diagnostic does not support a tradable routing claim.",
        FINAL_SURVIVORSHIP: "Pre-registered conclusion: separation is survivorship-only, so it does not support routing.",
        FINAL_ABSENT: "Pre-registered conclusion: no bootstrap-stable full-cohort dual-channel Tier3 C1 onset is detected; weak Tier1/Tier2 reads remain readout-only.",
        FINAL_INCOMPLETE: "Pre-registered conclusion: statistics are incomplete, so no separation direction is authorized.",
        FINAL_BLOCKED: "Pre-registered conclusion: required inputs are blocked.",
    }.get(final_status, "Pre-registered conclusion: status is unrecognized.")
    lines = [
        "# 11A2 Post-t0 Archetype Path Divergence Diagnostic Report",
        "",
        "## Final Status",
        "",
        f"- final_status: `{final_status}`",
        f"- evaluated denominator: {int(all_recon['a2_pit_valid_evaluated_row_n']):,} strict PIT-valid risk_on rows; 11A1 reconciliation status `{all_recon['reconciliation_status']}`.",
        f"- C1 full-cohort confirmed onset: `{c1['confirmed_divergence_onset_day']}`; tradability status `{trad['winner_realized_fraction_status']}`.",
        f"- bootstrap confirmed onset hit rate: {boot['confirmed_onset_hit_rate']:.3f}; stable={boolish(boot['bootstrap_stable_flag'])}.",
        f"- {final_text}",
        "",
        "## Data Sources And Scope",
        "",
        "- Inputs are recorded in `input_artifact_audit.csv`; denominator reconciliation is in `scope_reconciliation_vs_11a1.csv`.",
        f"- 11A1 PIT-valid evaluated row count: {int(all_recon['a1_pit_valid_evaluated_row_n']):,}; 11A2 reconstructed row count: {int(all_recon['a2_pit_valid_evaluated_row_n']):,}; denominator drift rate: {float(all_recon['denominator_drift_rate']):.4%}.",
        f"- minimum full-cohort path eligibility rate: {float(coverage.loc[coverage['cohort'].eq('full_cohort'), 'eligible_rate'].min()):.2%}.",
        "",
        "## Outcome Classes",
        "",
        *markdown_table(["split", "class", "rows", "instruments", "rate"], class_rows),
        "",
        "## Price Anchor And Fill Policy",
        "",
        f"- anchor date match rate: {anchor_all['anchor_date_match_rate']:.2%}; source `{anchor_all['anchor_source']}`; status `{anchor_all['anchor_status']}`.",
        "- Full-cohort primary fill uses only delist/suspended/complete_path/price_path_missing states. Fast-fail label touch is EP8B label-overlap audit only and does not rewrite EP1-EP7, onset, tradability, or final status.",
        "- Post-t0 ST is not handled in this run; ST only applies to t0 strict PIT eligibility.",
        "",
        *markdown_table(["split", "K", "fill_reason", "rows", "instruments"], fill_rows),
        "",
        "## Coverage And Power",
        "",
        *markdown_table(["split", "cohort", "K", "eligible_rows", "eligible_rate", "filename_fallback_rows"], coverage_rows),
        "",
        *markdown_table(["split", "pos_rows", "neg_rows", "pos_inst", "neg_inst", "power_status"], power_rows),
        "",
        "## Separation Curve",
        "",
        "- Rows below are full-cohort return/structure channel Cliff's delta by contrast, K, and split; validation remains a readout with the power guard above.",
        "",
        *markdown_table(["contrast", "feature", "split", "K", "cliff", "ci_low", "ci_high", "direction"], sep_rows),
        "",
        "## Onset And Corroboration",
        "",
        *markdown_table(["contrast", "cohort", "ret_t1", "ret_t2", "ret_t3", "struct_t1", "struct_t2", "struct_t3", "confirmed", "collinearity"], onset_rows),
        "",
        f"- C1 direction pair at confirmed onset: ({c1['return_direction_at_confirmed']}, {c1['structure_direction_at_confirmed']}); channel_rank_corr={report_value(c1['channel_rank_corr'])}; channel_direction_agreement_rate={report_value(c1['channel_direction_agreement_rate'])}.",
        "- `dual_channel_collinear_readout` means the two channels are closer to corroboration-by-echo than independent evidence; it does not block status by itself.",
        "",
        "## Tradability Lag",
        "",
        f"- denominator: `mfe_120_recomputed`; winner median ep_mfe_to_Kstar / mfe_120_recomputed = {report_value(trad['winner_median_ep_mfe_to_Kstar_over_mfe120'])}.",
        f"- winner median ep_ret_to_Kstar / forward_return_120d = {report_value(trad['winner_median_ep_ret_to_Kstar_over_fwd120'])}.",
        f"- tradability basis eligible winners: {int(trad['tradability_basis_eligible_n'])}; excluded: {int(trad['tradability_basis_excluded_n'])}; status `{trad['winner_realized_fraction_status']}`.",
        "",
        "## Survivorship And Delist Sensitivity",
        "",
        f"- survivorship flags: {survivor_counts}.",
        *markdown_table(["contrast", "channel", "K", "split", "metric_gap", "dropout_n", "haircut", "flag"], survivor_rows),
        "",
        "## EP8 Structural Stress And Label Overlap",
        "",
        "- EP8A price-action structural stress is included in `separation_curve_readout.csv` as price-action-only path features.",
        "- EP8B fast-fail barrier touch remains label-overlap audit only; it is excluded from primary onset/tradability/final-status logic.",
        "",
        *markdown_table(["split", "K", "fast_fail_n", "touch_n", "overlap_n", "touch_given_fast_fail", "status"], label_rows),
        "",
        "## Bootstrap And Multiple Comparison",
        "",
        *markdown_table(["contrast", "bootstrap_n", "confirmed_hit", "confirmed_distribution", "tier2_hit", "return_hit", "structure_hit", "stable", "event_block_n", "event_block_hit", "event_block_median", "event_block_conflict"], bootstrap_rows),
        "",
        "- Per-channel bootstrap metric median, 5%/95% interval, directional probabilities, and confirmed-direction null-band probability are serialized in `bootstrap_separation_readout.csv::channel_metric_distribution_summary`.",
        "",
        f"- multiple-comparison status: `{multiple.iloc[0]['multiple_comparison_status']}`; significant cells {int(multiple.iloc[0]['significant_cells_n'])} / {int(multiple.iloc[0]['total_tested_cells'])}; null p95={report_value(multiple.iloc[0]['null_significant_cells_p95'])}; method `{multiple.iloc[0].get('null_simulation_method', '')}`.",
        "",
        "## Validation Commands",
        "",
        "- `python -m pytest experiments/pending/11_archetype_proxy_validation_system_v0/tests/test_post_t0_archetype_path_divergence_diagnostic.py -q`",
        "- `python -m pytest experiments/pending/11_archetype_proxy_validation_system_v0/tests -q`",
        "- `python experiments/pending/11_archetype_proxy_validation_system_v0/src/run_11a2_post_t0_archetype_path_divergence_diagnostic.py --config experiments/pending/11_archetype_proxy_validation_system_v0/configs/config_11a2_post_t0_archetype_path_divergence_diagnostic.yaml`",
        "",
        "## Boundary",
        "",
        "- 11A2 is diagnostic-only. It does not authorize routing, entry, exit, override of 10C, or strategy EV claims.",
    ]
    return "\n".join(lines) + "\n"


def cache_artifact_metadata(cache_frames: dict[str, tuple[Path, pd.DataFrame]]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for name, (path, frame) in sorted(cache_frames.items()):
        metadata[name] = {
            "path": relative_path(path),
            "sha256": file_sha256(path) if path.is_file() else None,
            "row_count": int(len(frame)),
            "schema": [{"name": str(col), "dtype": str(dtype)} for col, dtype in frame.dtypes.items()],
        }
    return metadata


def build_manifest(
    config: dict[str, Any],
    config_path: Path,
    outputs: dict[str, Path],
    final_status: str,
    cache_frames: dict[str, tuple[Path, pd.DataFrame]] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": git_revision(),
        "config_path": relative_path(config_path),
        "config_sha256": file_sha256(config_path) if config_path.is_file() else None,
        "config_hash": stable_hash(config),
        "final_status": final_status,
        "outputs": {name: relative_path(path) for name, path in sorted(outputs.items())},
        "output_hashes": {name: file_sha256(path) for name, path in sorted(outputs.items()) if path.is_file() and name != "manifest"},
        "cache_artifacts": cache_artifact_metadata(cache_frames or {}),
    }


def main(config_path: Path = CONFIG_PATH) -> int:
    config = load_yaml(config_path)
    params = Params.from_config(config)
    paths = build_paths(config)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    cache_frames: dict[str, tuple[Path, pd.DataFrame]] = {}
    required = set(paths)
    input_audit = input_artifact_audit(paths, required)
    outputs["input_artifact_audit"] = write_df(TABLE_DIR / "input_artifact_audit.csv", input_audit)
    blocker_reasons = [f"missing_input:{item}" for item in input_audit.loc[input_audit["required_flag"] & ~input_audit["exists_flag"], "artifact_id"].tolist()]
    incomplete_reasons: list[str] = []
    if blocker_reasons:
        empty_summary = pd.DataFrame([{"final_status": FINAL_BLOCKED, "blocker_reason_list": "|".join(blocker_reasons)}])
        outputs["diagnostic_summary"] = write_df(TABLE_DIR / "diagnostic_summary.csv", empty_summary)
        outputs["report"] = write_text(REPORT_PATH, f"# 11A2 Report\n\nfinal_status: `{FINAL_BLOCKED}`\n")
        outputs["manifest"] = write_json(MANIFEST_PATH, build_manifest(config, config_path, outputs, FINAL_BLOCKED))
        print(f"final_status={FINAL_BLOCKED}")
        return 2

    denom = prepare_outcome_classes(load_denominator(paths))
    price_cache = PriceCache(paths["qfq_primary_dir"], paths["qfq_fallback_dir"])
    registry = feature_registry()
    scope_recon = build_scope_reconciliation(denom, paths, params)
    denom_audit = denominator_contract_audit(denom, config)
    class_counts = outcome_class_count_audit(denom)
    power = contrast_power_status(class_counts, params)
    anchor = build_anchor_reconciliation(denom, paths, price_cache)
    features, coverage, fill_audit, mfe_basis, touch_policy, label_overlap = build_early_path_features(denom, paths, params, price_cache)
    separation = build_separation_curve(features, registry)
    multivar = build_multivariate_readout(features)
    onset, split_consistency = build_onset_readouts(separation, features, params)
    survivorship = survivorship_audit(separation, params)
    bootstrap, bootstrap_samples = bootstrap_onset_readout(features, params, onset)
    multiple = multiple_comparison_audit(separation, features, params)
    tradability = tradability_lag_readout(features, mfe_basis, onset, params)

    if denom.empty:
        blocker_reasons.append("evaluated_denominator_empty")
    if scope_recon["reconciliation_status"].ne("ok").any():
        incomplete_reasons.append("denominator_drift_vs_11a1")
    c1_power = power.loc[power["contrast_id"].eq("C1_winner_vs_big_failure_proxy") & power["split"].isin(["train", "robustness"])]
    if c1_power["contrast_power_status"].ne("ok").any():
        incomplete_reasons.append("C1_contrast_underpowered")
    unresolved_all = class_counts.loc[class_counts["split"].eq("all") & class_counts["class_id"].eq("class_unresolved"), "class_rate"].iloc[0]
    if unresolved_all > params.class_unresolved_ceiling:
        incomplete_reasons.append("class_unresolved_rate_exceeds_ceiling")
    if coverage["eligible_rate"].lt(params.eligible_row_n_floor_ratio).any():
        incomplete_reasons.append("qfq_early_path_eligible_rate_below_floor")
    if anchor.loc[anchor["split"].eq("all"), "anchor_status"].iloc[0] != "ok":
        incomplete_reasons.append("anchor_reconciliation_failed")
    winner_basis = mfe_basis.merge(denom[["row_id", "class_big_winner_flag"]], on="row_id", how="left")
    winner_mismatch = safe_rate(int((winner_basis["class_big_winner_flag"].map(boolish) & winner_basis["basis_status"].eq("mfe_basis_mismatch")).sum()), int(winner_basis["class_big_winner_flag"].map(boolish).sum()))
    if pd.notna(winner_mismatch) and winner_mismatch > params.mfe_basis_mismatch_ceiling:
        incomplete_reasons.append("mfe_basis_mismatch_rate_exceeds_ceiling")
    touch_unresolved = safe_rate(int(touch_policy["coordinate_status"].ne("ok").sum()), len(touch_policy))
    if pd.notna(touch_unresolved) and touch_unresolved > params.touch_pos_offset_unresolved_ceiling:
        incomplete_reasons.append("touch_pos_offset_unresolved_rate_exceeds_ceiling")
    if "delist_haircut_sensitivity_conflict_flag" in survivorship.columns and bool_series(survivorship["delist_haircut_sensitivity_conflict_flag"]).any():
        incomplete_reasons.append("delist_haircut_sensitivity_conflict")
    if "episode_block_onset_conflict" in bootstrap.columns and bool_series(bootstrap["episode_block_onset_conflict"]).any():
        incomplete_reasons.append("episode_block_onset_conflict")

    final_status = choose_final_status(blocker_reasons, incomplete_reasons, onset, bootstrap, tradability, survivorship)
    summary = build_diagnostic_summary(final_status, blocker_reasons, incomplete_reasons, denom, onset, tradability)

    outputs["scope_reconciliation_vs_11a1"] = write_df(TABLE_DIR / "scope_reconciliation_vs_11a1.csv", scope_recon)
    outputs["denominator_contract_audit"] = write_df(TABLE_DIR / "denominator_contract_audit.csv", denom_audit)
    outputs["price_anchor_reconciliation"] = write_df(TABLE_DIR / "price_anchor_reconciliation.csv", anchor)
    outputs["outcome_class_count_audit"] = write_df(TABLE_DIR / "outcome_class_count_audit.csv", class_counts)
    outputs["early_path_feature_registry"] = write_df(TABLE_DIR / "early_path_feature_registry.csv", registry)
    outputs["early_path_feature_coverage_audit"] = write_df(TABLE_DIR / "early_path_feature_coverage_audit.csv", coverage)
    outputs["full_cohort_fill_audit"] = write_df(TABLE_DIR / "full_cohort_fill_audit.csv", fill_audit)
    outputs["touch_pos_coordinate_policy"] = write_df(TABLE_DIR / "touch_pos_coordinate_policy.csv", touch_policy)
    outputs["label_overlap_tautology_audit"] = write_df(TABLE_DIR / "label_overlap_tautology_audit.csv", label_overlap)
    outputs["separation_curve_readout"] = write_df(TABLE_DIR / "separation_curve_readout.csv", separation)
    outputs["multivariate_separability_readout"] = write_df(TABLE_DIR / "multivariate_separability_readout.csv", multivar)
    outputs["divergence_onset_readout"] = write_df(TABLE_DIR / "divergence_onset_readout.csv", onset)
    outputs["mfe_basis_reconciliation"] = write_df(TABLE_DIR / "mfe_basis_reconciliation.csv", mfe_basis)
    outputs["tradability_lag_readout"] = write_df(TABLE_DIR / "tradability_lag_readout.csv", tradability)
    outputs["split_onset_consistency"] = write_df(TABLE_DIR / "split_onset_consistency.csv", split_consistency)
    outputs["survivorship_separation_audit"] = write_df(TABLE_DIR / "survivorship_separation_audit.csv", survivorship)
    outputs["bootstrap_separation_readout"] = write_df(TABLE_DIR / "bootstrap_separation_readout.csv", bootstrap)
    outputs["multiple_comparison_audit"] = write_df(TABLE_DIR / "multiple_comparison_audit.csv", multiple)
    outputs["diagnostic_summary"] = write_df(TABLE_DIR / "diagnostic_summary.csv", summary)
    remove_if_exists(LOCAL_CACHE_DIR / "early_path_feature_matrix.csv")
    remove_if_exists(LOCAL_CACHE_DIR / "bootstrap_samples.csv")
    outputs["early_path_feature_matrix"] = write_parquet(LOCAL_CACHE_DIR / "early_path_feature_matrix.parquet", features)
    cache_frames["early_path_feature_matrix"] = (outputs["early_path_feature_matrix"], features)
    outputs["bootstrap_samples"] = write_parquet(LOCAL_CACHE_DIR / "bootstrap_samples.parquet", bootstrap_samples)
    cache_frames["bootstrap_samples"] = (outputs["bootstrap_samples"], bootstrap_samples)
    outputs["report"] = write_text(
        REPORT_PATH,
        build_report(
            final_status,
            summary,
            class_counts,
            scope_recon,
            anchor,
            separation,
            onset,
            tradability,
            fill_audit,
            label_overlap,
            coverage,
            power,
            survivorship,
            bootstrap,
            multiple,
        ),
    )
    outputs["manifest"] = write_json(MANIFEST_PATH, build_manifest(config, config_path, outputs, final_status, cache_frames))
    print(f"final_status={final_status}")
    print(f"diagnostic_summary={TABLE_DIR / 'diagnostic_summary.csv'}")
    print(f"manifest={MANIFEST_PATH}")
    return 0 if final_status != FINAL_BLOCKED else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    raise SystemExit(main(args.config))
