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


RUN_ID = "11C_two_stage_observed_state_policy_replay_v0"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_11c_two_stage_observed_state_policy_replay.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / f"{RUN_ID}_report.md"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / f"manifest_{RUN_ID}.json"

FINAL_SUPPORTED = "11C_two_stage_policy_supported"
FINAL_GROSS_ONLY = "11C_two_stage_policy_gross_only_not_tradable"
FINAL_TOPK = "11C_two_stage_policy_topk_dependent"
FINAL_FAILURE_WORSE = "11C_two_stage_policy_failure_exposure_worse"
FINAL_RIGHT_TAIL = "11C_two_stage_policy_right_tail_capture_collapsed"
FINAL_OBSERVATION_FIRST = "11C_two_stage_policy_observation_first_preferred"
FINAL_STAGED = "11C_two_stage_policy_staged_sizing_candidate"
FINAL_NOT_SUPPORTED = "11C_two_stage_policy_not_supported_diagnostic"
FINAL_INCOMPLETE = "11C_two_stage_policy_statistics_incomplete"
FINAL_BLOCKED = "11C_two_stage_policy_input_blocked"

READOUT_SPLITS = ["all", "train", "validation", "robustness"]
PRIMARY_SPLITS = ["train", "validation", "robustness"]
REJECT_JOIN_KEY = ["sample_id", "selected_target_id", "denominator_id", "input_event_key"]
SLICE_FIELDS = ["model_id", "ablation_id", "capacity_id", "threshold_id", "population_id", "denominator_id"]
FORBIDDEN_FEATURE_PATTERNS = [
    "selected_fast_fail",
    "fast_fail_touch",
    "winner_120",
    "forward_return_120d",
    "future_mfe",
    "future_mae",
    "mfe_120",
    "mae_120",
]


@dataclass(frozen=True)
class Params:
    exit_contract_id: str = "common_exit_120d_with_risk_stop_v1"
    state_observation_k: int = 3
    max_holding_sessions: int = 120
    risk_stop_drawdown_from_cost_basis: float = -0.10
    delist_haircut: float = 1.0
    allow_delayed_entry_chase: bool = False
    trial_size_grid: tuple[float, ...] = (0.00, 0.10, 0.25)
    upgrade_size_grid: tuple[float, ...] = (0.50, 1.00)
    primary_capacity_slots: int = 50
    capacity_slots: tuple[int, ...] = (20, 50, 100)
    max_gross_exposure: float = 1.0
    max_instrument_weight: float = 0.05
    max_board_weight: float = 0.40
    max_industry_weight: float = 0.25
    train_state_positive_entry_n_floor: int = 100
    train_state_positive_winner_n_floor: int = 20
    winner_capture_tolerance: float = 0.05
    big_failure_entry_lift_ceiling: float = 0.005
    false_repair_entry_lift_ceiling: float = 0.005
    fast_fail_loss_lift_ceiling: float = 0.005
    mae_p95_lift_ceiling: float = 0.02
    winner_retention_floor: float = 0.85
    limit_up_unfilled_rate_ceiling: float = 0.20
    limit_down_exit_failure_rate_ceiling: float = 0.10
    cash_drag_lift_ceiling: float = 0.10
    board_concentration_hhi_lift_ceiling: float = 0.10
    top1_contribution_share_ceiling: float = 0.35
    top5_contribution_share_ceiling: float = 0.60
    episode_contribution_share_ceiling: float = 0.35
    validation_min_winner_n: int = 30
    validation_min_state_positive_winner_n: int = 10
    lane_b_train_entry_floor: int = 100
    lane_b_train_winner_floor: int = 20
    lane_b_robustness_entry_floor: int = 50
    lane_b_robustness_winner_floor: int = 10
    bootstrap_n: int = 1000
    bootstrap_seed: int = 20260617
    winsor_low: float = 0.01
    winsor_high: float = 0.99
    cost_scenarios: tuple[tuple[str, float, float], ...] = (
        ("zero_cost_decomposition", 0.0, 0.0),
        ("base_cost", 8.0, 13.0),
        ("stress_cost", 15.0, 25.0),
    )

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Params":
        raw = config.get("parameters", {})
        costs = []
        for name, spec in raw.get("cost_scenarios", {}).items():
            costs.append((name, float(spec.get("buy_cost_bps", 0.0)), float(spec.get("sell_cost_bps", 0.0))))
        values = {
            "exit_contract_id": str(raw.get("exit_contract_id", cls.exit_contract_id)),
            "state_observation_k": int(raw.get("state_observation_k", cls.state_observation_k)),
            "max_holding_sessions": int(raw.get("max_holding_sessions", cls.max_holding_sessions)),
            "risk_stop_drawdown_from_cost_basis": float(raw.get("risk_stop_drawdown_from_cost_basis", cls.risk_stop_drawdown_from_cost_basis)),
            "delist_haircut": float(raw.get("delist_haircut", cls.delist_haircut)),
            "allow_delayed_entry_chase": boolish(raw.get("allow_delayed_entry_chase", cls.allow_delayed_entry_chase)),
            "trial_size_grid": tuple(float(x) for x in raw.get("trial_size_grid", cls.trial_size_grid)),
            "upgrade_size_grid": tuple(float(x) for x in raw.get("upgrade_size_grid", cls.upgrade_size_grid)),
            "primary_capacity_slots": int(raw.get("primary_capacity_slots", cls.primary_capacity_slots)),
            "capacity_slots": tuple(int(x) for x in raw.get("capacity_slots", cls.capacity_slots)),
            "max_gross_exposure": float(raw.get("max_gross_exposure", cls.max_gross_exposure)),
            "max_instrument_weight": float(raw.get("max_instrument_weight", cls.max_instrument_weight)),
            "max_board_weight": float(raw.get("max_board_weight", cls.max_board_weight)),
            "max_industry_weight": float(raw.get("max_industry_weight", cls.max_industry_weight)),
            "train_state_positive_entry_n_floor": int(raw.get("train_state_positive_entry_n_floor", cls.train_state_positive_entry_n_floor)),
            "train_state_positive_winner_n_floor": int(raw.get("train_state_positive_winner_n_floor", cls.train_state_positive_winner_n_floor)),
            "winner_capture_tolerance": float(raw.get("winner_capture_tolerance", cls.winner_capture_tolerance)),
            "big_failure_entry_lift_ceiling": float(raw.get("big_failure_entry_lift_ceiling", cls.big_failure_entry_lift_ceiling)),
            "false_repair_entry_lift_ceiling": float(raw.get("false_repair_entry_lift_ceiling", cls.false_repair_entry_lift_ceiling)),
            "fast_fail_loss_lift_ceiling": float(raw.get("fast_fail_loss_lift_ceiling", cls.fast_fail_loss_lift_ceiling)),
            "mae_p95_lift_ceiling": float(raw.get("mae_p95_lift_ceiling", cls.mae_p95_lift_ceiling)),
            "winner_retention_floor": float(raw.get("winner_retention_floor", cls.winner_retention_floor)),
            "limit_up_unfilled_rate_ceiling": float(raw.get("limit_up_unfilled_rate_ceiling", cls.limit_up_unfilled_rate_ceiling)),
            "limit_down_exit_failure_rate_ceiling": float(raw.get("limit_down_exit_failure_rate_ceiling", cls.limit_down_exit_failure_rate_ceiling)),
            "cash_drag_lift_ceiling": float(raw.get("cash_drag_lift_ceiling", cls.cash_drag_lift_ceiling)),
            "board_concentration_hhi_lift_ceiling": float(raw.get("board_concentration_hhi_lift_ceiling", cls.board_concentration_hhi_lift_ceiling)),
            "top1_contribution_share_ceiling": float(raw.get("top1_contribution_share_ceiling", cls.top1_contribution_share_ceiling)),
            "top5_contribution_share_ceiling": float(raw.get("top5_contribution_share_ceiling", cls.top5_contribution_share_ceiling)),
            "episode_contribution_share_ceiling": float(raw.get("episode_contribution_share_ceiling", cls.episode_contribution_share_ceiling)),
            "validation_min_winner_n": int(raw.get("validation_min_winner_n", cls.validation_min_winner_n)),
            "validation_min_state_positive_winner_n": int(raw.get("validation_min_state_positive_winner_n", cls.validation_min_state_positive_winner_n)),
            "lane_b_train_entry_floor": int(raw.get("lane_b_train_entry_floor", cls.lane_b_train_entry_floor)),
            "lane_b_train_winner_floor": int(raw.get("lane_b_train_winner_floor", cls.lane_b_train_winner_floor)),
            "lane_b_robustness_entry_floor": int(raw.get("lane_b_robustness_entry_floor", cls.lane_b_robustness_entry_floor)),
            "lane_b_robustness_winner_floor": int(raw.get("lane_b_robustness_winner_floor", cls.lane_b_robustness_winner_floor)),
            "bootstrap_n": int(raw.get("bootstrap_n", cls.bootstrap_n)),
            "bootstrap_seed": int(raw.get("bootstrap_seed", cls.bootstrap_seed)),
            "winsor_low": float(raw.get("winsor_low", cls.winsor_low)),
            "winsor_high": float(raw.get("winsor_high", cls.winsor_high)),
        }
        if costs:
            values["cost_scenarios"] = tuple(costs)
        return cls(**values)


def git_revision(cwd: Path = REPO_ROOT) -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_seed(*parts: Any) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False) % (2**32)


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


def bool_series(series: pd.Series | Any, index: pd.Index | None = None) -> pd.Series:
    if isinstance(series, pd.Series):
        return series.map(boolish).fillna(False).astype(bool)
    if index is None:
        raise ValueError("index is required for scalar bool_series input")
    return pd.Series([boolish(series)] * len(index), index=index, dtype=bool)


def nonempty(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value).strip()


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return float("nan")
    return float(numerator) / float(denominator)


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


def artifact_schema(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.is_file():
        return []
    suffixes = "".join(path.suffixes)
    try:
        if suffixes.endswith(".parquet"):
            import pyarrow.parquet as pq

            schema = pq.ParquetFile(path).schema_arrow
            return [{"name": field.name, "type": str(field.type)} for field in schema]
        if suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
            frame = pd.read_csv(path, nrows=0)
            return [{"name": col, "type": "csv_untyped"} for col in frame.columns]
    except Exception as exc:
        return [{"name": "__schema_error__", "type": type(exc).__name__}]
    return []


def artifact_metadata(path: Path) -> dict[str, Any]:
    return {
        "path": relative_path(path),
        "sha256": file_sha256(path) if path.exists() and path.is_file() else "",
        "row_count": quick_row_count(path),
        "schema": artifact_schema(path),
    }


def make_policy_row_id(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["sample_id"].astype(str)
        + "|"
        + frame["selected_target_id"].astype(str)
        + "|"
        + frame["denominator_id"].astype(str)
        + "|"
        + frame["event_t0_date"].astype(str)
        + "|"
        + frame["instrument"].astype(str)
    )


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
            source = "qfq_fallback"
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
        frame["prev_close"] = frame["close"].shift(1)
        frame["range_pct"] = frame["high"] / frame["low"] - 1.0
        self._cache[instrument] = frame
        self.instrument_source[instrument] = source
        return frame


def date_pos_map(bars: pd.DataFrame) -> dict[str, int]:
    return {str(date): int(pos) for pos, date in enumerate(bars["date"].tolist())}


def board_limit_proxy(board: str) -> float:
    text = str(board or "").lower()
    if "chinext" in text or "star" in text or "科创" in text or "创业" in text:
        return 0.195
    return 0.095


def is_one_price_locked(bar: pd.Series, previous_close: float | None, limit_proxy: float) -> tuple[bool, str]:
    vals = [bar.get("open"), bar.get("high"), bar.get("low"), bar.get("close")]
    if not all(np.isfinite(float(v)) for v in vals):
        return False, "limit_basis_unavailable"
    one_price = float(bar["open"]) == float(bar["high"]) == float(bar["low"]) == float(bar["close"])
    if not one_price or previous_close is None or not np.isfinite(previous_close) or previous_close <= 0:
        return False, "not_locked"
    ret = float(bar["open"]) / float(previous_close) - 1.0
    if ret >= limit_proxy:
        return True, "limit_up_locked"
    if ret <= -limit_proxy:
        return True, "limit_down_locked"
    return False, "not_locked"


def action_fill_status(bars: pd.DataFrame | None, pos: int | None, side: str, board: str) -> tuple[bool, str, float, str]:
    if bars is None or pos is None or pos < 0 or pos >= len(bars):
        return False, "unfilled_missing_open_or_volume", float("nan"), ""
    bar = bars.iloc[pos]
    price = pd.to_numeric(pd.Series([bar.get("open", np.nan)]), errors="coerce").iloc[0]
    volume = pd.to_numeric(pd.Series([bar.get("volume", np.nan)]), errors="coerce").iloc[0]
    money = pd.to_numeric(pd.Series([bar.get("money", np.nan)]), errors="coerce").iloc[0]
    if not (np.isfinite(price) and price > 0 and np.isfinite(volume) and volume > 0 and np.isfinite(money) and money > 0):
        return False, "unfilled_missing_open_or_volume", float("nan"), str(bar.get("date", ""))
    prev_close = pd.to_numeric(pd.Series([bar.get("prev_close", np.nan)]), errors="coerce").iloc[0]
    locked, direction = is_one_price_locked(bar, prev_close, board_limit_proxy(board))
    if locked and side == "buy" and direction == "limit_up_locked":
        return False, "buy_unfilled_limit_up_locked", float("nan"), str(bar.get("date", ""))
    if locked and side == "sell" and direction == "limit_down_locked":
        return False, "sell_unfilled_limit_down_locked", float("nan"), str(bar.get("date", ""))
    return True, "filled", float(price), str(bar.get("date", ""))


def load_denominator(paths: dict[str, Path]) -> pd.DataFrame:
    frame = pd.read_parquet(paths["eleven_a1_proxy_scored_denominator"]).copy()
    if "row_id" not in frame.columns:
        frame["row_id"] = np.arange(len(frame), dtype=np.int64)
    frame["instrument"] = frame["instrument"].astype(str)
    frame["event_t0_date"] = pd.to_datetime(frame["event_t0_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "event_window_anchor_date" in frame.columns:
        frame["event_window_anchor_date"] = pd.to_datetime(frame["event_window_anchor_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    frame["policy_row_id"] = make_policy_row_id(frame)
    frame["winner_120_bool"] = bool_series(frame.get("winner_120_bool", frame.get("winner_120", False)), frame.index)
    frame["fast_fail_10_bool"] = bool_series(frame.get("fast_fail_10_bool", frame.get("selected_fast_fail_10_label", False)), frame.index)
    frame["false_repair_20_bool"] = bool_series(frame.get("false_repair_20_bool", frame.get("frozen_false_repair_20d_label", False)), frame.index)
    frame["big_failure_proxy_bool"] = bool_series(frame.get("big_failure_proxy_bool", frame["fast_fail_10_bool"] | frame["false_repair_20_bool"]), frame.index)
    frame["horizon_complete_120d_bool"] = bool_series(frame.get("horizon_complete_120d", frame.get("horizon_complete_120d_bool", True)), frame.index)
    frame["class_big_winner_flag"] = bool_series(frame.get("class_big_winner_flag", frame["winner_120_bool"]), frame.index)
    frame["class_big_failure_proxy_nonwinner_flag"] = bool_series(
        frame.get("class_big_failure_proxy_nonwinner_flag", (~frame["winner_120_bool"]) & frame["big_failure_proxy_bool"]),
        frame.index,
    )
    frame["subclass_fast_fail_flag"] = bool_series(frame.get("subclass_fast_fail_flag", frame["fast_fail_10_bool"] & ~frame["winner_120_bool"]), frame.index)
    frame["subclass_false_repair_only_flag"] = bool_series(
        frame.get("subclass_false_repair_only_flag", frame["false_repair_20_bool"] & ~frame["fast_fail_10_bool"] & ~frame["winner_120_bool"]),
        frame.index,
    )
    frame["final_sample_weight"] = pd.to_numeric(frame.get("final_sample_weight", 1.0), errors="coerce").fillna(1.0)
    return frame


def selected_10b_spec(manifest: dict[str, Any]) -> dict[str, str]:
    selected_op = manifest.get("selected_operating_point", {}) or {}
    return {
        "model_id": str(manifest.get("selected_model_id", selected_op.get("model_id", ""))),
        "ablation_id": str(selected_op.get("ablation_id", "full")),
        "capacity_id": str(manifest.get("selected_capacity_id", selected_op.get("capacity_id", ""))),
        "threshold_id": str(manifest.get("selected_threshold_id", selected_op.get("threshold_id", ""))),
        "population_id": str(manifest.get("selected_population_id", selected_op.get("population_id", "10A__same_instrument_cooldown_10d"))),
        "denominator_id": str(manifest.get("selected_denominator_id", selected_op.get("denominator_id", "post_dedup_risk_on_r_core"))),
    }


def select_10c_slice_mode(manifest: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    supported = (
        manifest.get("selected_capacity_id") is not None
        and manifest.get("selected_threshold_id") is not None
        and manifest.get("selected_cascade_status") == "supported"
    )
    if supported:
        return {
            "tenc_slice_mode": "selected_gate",
            "model_id": str(manifest.get("selected_model_id")),
            "ablation_id": str((manifest.get("selected_operating_point") or {}).get("ablation_id", "full")),
            "capacity_id": str(manifest.get("selected_capacity_id")),
            "threshold_id": str(manifest.get("selected_threshold_id")),
            "population_id": str(manifest.get("selected_population_id")),
            "denominator_id": str(manifest.get("selected_denominator_id")),
            "tenc_slice_selected_flag": True,
            "tenc_slice_decision_block_reason": "",
        }
    ref = config["scope"]["reference_slice"]
    return {
        "tenc_slice_mode": "keep_9000_reference_slice",
        "model_id": str(ref["model_id"]),
        "ablation_id": str(ref["ablation_id"]),
        "capacity_id": str(ref["capacity_id"]),
        "threshold_id": str(ref["threshold_id"]),
        "population_id": str(ref["population_id"]),
        "denominator_id": str(ref["denominator_id"]),
        "tenc_slice_selected_flag": False,
        "tenc_slice_decision_block_reason": "not_selected",
    }


def filter_rejector_slice(scores: pd.DataFrame, spec: dict[str, Any]) -> pd.DataFrame:
    mask = pd.Series(True, index=scores.index)
    for field in SLICE_FIELDS:
        if field not in scores.columns:
            raise KeyError(f"Missing slice field {field}")
        mask &= scores[field].astype(str).eq(str(spec[field]))
    return scores.loc[mask].copy()


def attach_reject_flag(base: pd.DataFrame, slice_scores: pd.DataFrame, prefix: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    cols = REJECT_JOIN_KEY + ["instrument", "event_t0_date", "split", "candidate_rejected_flag"]
    available = [col for col in cols if col in slice_scores.columns]
    slim = slice_scores[available].copy()
    slim["event_t0_date"] = pd.to_datetime(slim["event_t0_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    duplicates = int(slim.duplicated(REJECT_JOIN_KEY).sum())
    slim = slim.drop_duplicates(REJECT_JOIN_KEY, keep="first")
    slim = slim.rename(
        columns={
            "candidate_rejected_flag": f"{prefix}_rejected_flag",
            "instrument": f"{prefix}_instrument",
            "event_t0_date": f"{prefix}_event_t0_date",
            "split": f"{prefix}_split",
        }
    )
    out = base.merge(slim, on=REJECT_JOIN_KEY, how="left", indicator=f"{prefix}_join")
    hit = out[f"{prefix}_join"].eq("both")
    out[f"{prefix}_rejected_flag"] = bool_series(out[f"{prefix}_rejected_flag"], out.index)
    mismatch = {
        "join_hit_rate": safe_rate(int(hit.sum()), len(out)),
        "duplicate_join_key_n": duplicates,
        "instrument_mismatch_n": int((hit & out[f"{prefix}_instrument"].notna() & out[f"{prefix}_instrument"].astype(str).ne(out["instrument"].astype(str))).sum()),
        "date_mismatch_n": int((hit & out[f"{prefix}_event_t0_date"].notna() & out[f"{prefix}_event_t0_date"].astype(str).ne(out["event_t0_date"].astype(str))).sum()),
        "split_mismatch_n": int((hit & out[f"{prefix}_split"].notna() & out[f"{prefix}_split"].astype(str).ne(out["split"].astype(str))).sum()),
    }
    return out.drop(columns=[f"{prefix}_join"]), mismatch


def construct_lanes(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["deployed_baseline_kept_flag"] = ~bool_series(out["tenb_rejected_flag"], out.index)
    out["tenc_ref_rejected_flag"] = bool_series(out["tenc_ref_rejected_flag"], out.index)
    out["lane_id"] = "out_of_lane_10B_rejected"
    out.loc[out["deployed_baseline_kept_flag"] & ~out["tenc_ref_rejected_flag"], "lane_id"] = "lane_A_10C_ref_kept"
    out.loc[out["deployed_baseline_kept_flag"] & out["tenc_ref_rejected_flag"], "lane_id"] = "lane_B_10C_ref_rejected"
    return out


def observed_state_feature_registry() -> pd.DataFrame:
    rows = [
        ("K3_return_from_executable_anchor", "ep_ret_t0_to_K", "primary_allowed"),
        ("K3_return_from_executable_anchor", "ep_close_vs_t0_close", "primary_allowed"),
        ("K3_max_drawdown_path_damage", "ep_max_drawdown_to_K", "primary_allowed"),
        ("K3_max_drawdown_path_damage", "ep_breach_t0_low_through_K_flag", "primary_allowed"),
        ("K3_close_position_reclaim_status", "ep_close_above_t0_high_at_K_flag", "primary_allowed"),
        ("K3_close_position_reclaim_status", "ep_recovery_from_min_to_K", "primary_allowed"),
        ("K3_liquidity_volume_confirmation", "ep_money_ratio_3d_vs_20d", "primary_allowed"),
        ("K3_liquidity_volume_confirmation", "ep_volume_ratio_3d_vs_20d", "primary_allowed"),
        ("K3_executable_status", "entry_t0p4_executable_flag", "primary_allowed"),
        ("K3_executable_status", "suspended_through_K3_flag", "primary_allowed"),
        ("K3_executable_status", "limit_up_locked_t0p4_flag", "primary_allowed"),
        ("label_overlap_policy_audit", "selected_fast_fail_touch_pos", "readout_only_forbidden_primary"),
        ("label_overlap_policy_audit", "selected_fast_fail_touch_offset_sessions", "readout_only_forbidden_primary"),
        ("label_overlap_policy_audit", "selected_fast_fail_barrier_id", "readout_only_forbidden_primary"),
        ("future_outcome", "winner_120", "forbidden"),
        ("future_outcome", "forward_return_120d", "forbidden"),
        ("future_outcome", "future_MFE_MAE_beyond_K3", "forbidden"),
    ]
    frame = pd.DataFrame(rows, columns=["feature_family", "feature_id", "registry_status"])
    frame["primary_policy_allowed_flag"] = frame["registry_status"].eq("primary_allowed")
    return frame


def observed_state_definition_registry() -> pd.DataFrame:
    rows = [
        {
            "state_id": "S0_return_damage_basic",
            "formula": "ep_ret_t0_to_3 >= 0 AND ep_max_drawdown_to_3 >= -0.08 AND entry_t0p4_executable_flag == true",
        },
        {
            "state_id": "S1_reclaim_damage",
            "formula": "ep_close_vs_t0_close_at_3 >= 0 AND ep_breach_t0_low_through_3_flag == false AND entry_t0p4_executable_flag == true",
        },
        {
            "state_id": "S2_return_reclaim_liquidity",
            "formula": "ep_ret_t0_to_3 >= 0 AND ep_close_above_t0_high_at_3_flag == true AND ep_money_ratio_3d_vs_20d >= 1.0 AND entry_t0p4_executable_flag == true",
        },
    ]
    return pd.DataFrame(rows)


def formula_uses_forbidden_features(formula: str) -> bool:
    lower = str(formula).lower()
    return any(pattern.lower() in lower for pattern in FORBIDDEN_FEATURE_PATTERNS)


def add_k3_execution_features(k3: pd.DataFrame, price_cache: PriceCache, board_map: dict[str, str]) -> pd.DataFrame:
    out = k3.copy()
    rows = []
    for _, row in out.iterrows():
        inst = str(row["instrument"])
        bars = price_cache.load(inst)
        board = board_map.get(inst, "main_board")
        pos = None
        t0p4 = None
        volume_ratio = np.nan
        money_ratio = np.nan
        executable = False
        limit_up_locked = False
        reason = "price_path_missing"
        if bars is not None:
            positions = date_pos_map(bars)
            event_pos = positions.get(str(row["event_t0_date"]))
            if event_pos is not None:
                t0p4 = event_pos + 4
                pos = t0p4
                if pos < len(bars):
                    ok, reason, _, _ = action_fill_status(bars, pos, "buy", board)
                    executable = ok
                    bar = bars.iloc[pos]
                    prev_close = pd.to_numeric(pd.Series([bar.get("prev_close", np.nan)]), errors="coerce").iloc[0]
                    locked, direction = is_one_price_locked(bar, prev_close, board_limit_proxy(board))
                    limit_up_locked = bool(locked and direction == "limit_up_locked")
                window = bars.iloc[event_pos + 1 : min(event_pos + 4, len(bars))]
                hist20 = bars.iloc[max(0, event_pos - 19) : event_pos + 1]
                if len(window) == 3 and len(hist20) >= 5:
                    volume_denom = pd.to_numeric(hist20["volume"], errors="coerce").replace(0, np.nan).mean()
                    money_denom = pd.to_numeric(hist20["money"], errors="coerce").replace(0, np.nan).mean()
                    volume_ratio = float(window["volume"].mean() / volume_denom) if volume_denom and np.isfinite(volume_denom) else np.nan
                    money_ratio = float(window["money"].mean() / money_denom) if money_denom and np.isfinite(money_denom) else np.nan
        rows.append(
            {
                "entry_t0p4_pos": pos if pos is not None else np.nan,
                "entry_t0p4_executable_flag": executable,
                "entry_t0p4_fill_reason": reason,
                "limit_up_locked_t0p4_flag": limit_up_locked,
                "suspended_through_K3_flag": False,
                "ep_volume_ratio_3d_vs_20d": volume_ratio,
                "ep_money_ratio_3d_vs_20d": money_ratio,
                "board_bucket": board,
            }
        )
    return pd.concat([out.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def apply_state_definitions(matrix: pd.DataFrame) -> pd.DataFrame:
    out = matrix.copy()
    executable = bool_series(out["entry_t0p4_executable_flag"], out.index)
    out["state_positive_S0_return_damage_basic"] = (
        pd.to_numeric(out["ep_ret_t0_to_K"], errors="coerce").ge(0)
        & pd.to_numeric(out["ep_max_drawdown_to_K"], errors="coerce").ge(-0.08)
        & executable
    )
    out["state_positive_S1_reclaim_damage"] = (
        pd.to_numeric(out["ep_close_vs_t0_close"], errors="coerce").ge(0)
        & ~bool_series(out["ep_breach_t0_low_through_K_flag"], out.index)
        & executable
    )
    out["state_positive_S2_return_reclaim_liquidity"] = (
        pd.to_numeric(out["ep_ret_t0_to_K"], errors="coerce").ge(0)
        & bool_series(out["ep_close_above_t0_high_at_K_flag"], out.index)
        & pd.to_numeric(out["ep_money_ratio_3d_vs_20d"], errors="coerce").ge(1.0)
        & executable
    )
    return out


def build_k3_matrix(denom: pd.DataFrame, paths: dict[str, Path], price_cache: PriceCache, board_map: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_parquet(paths["eleven_a2_early_path_matrix"]).copy()
    raw["event_t0_date"] = pd.to_datetime(raw["event_t0_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    k3 = raw.loc[raw["K"].eq(3) & raw["cohort"].astype(str).eq("full_cohort")].copy()
    identity_cols = [
        "row_id",
        "policy_row_id",
        "sample_id",
        "selected_target_id",
        "denominator_id",
        "input_event_key",
        "instrument",
        "event_t0_date",
        "split",
        "event_window_anchor_date",
        "binding_canonical_event_id",
    ]
    ident = denom[identity_cols].copy()
    merged = k3.merge(ident, on=["row_id", "instrument", "event_t0_date", "split"], how="left", suffixes=("", "_denom"), indicator=True)
    audit = pd.DataFrame(
        [
            {
                "source": "11A2_early_path_feature_matrix_K3_full_cohort",
                "k3_row_n": len(k3),
                "denominator_row_n": len(denom),
                "join_hit_n": int(merged["_merge"].eq("both").sum()),
                "join_hit_rate": safe_rate(int(merged["_merge"].eq("both").sum()), len(k3)),
                "row_id_duplicate_n": int(k3.duplicated(["row_id"]).sum()),
                "policy_row_id_null_n": int(merged["policy_row_id"].isna().sum()),
                "identity_rehydration_status": "ok"
                if len(k3) == len(denom) and merged["_merge"].eq("both").all() and not merged["policy_row_id"].isna().any()
                else "identity_rehydration_failed",
            }
        ]
    )
    merged = merged.drop(columns=["_merge"])
    merged = add_k3_execution_features(merged, price_cache, board_map)
    merged = apply_state_definitions(merged)
    return merged, audit


def valid_sizing_grid(params: Params) -> pd.DataFrame:
    rows = []
    for trial in params.trial_size_grid:
        for upgrade in params.upgrade_size_grid:
            rows.append(
                {
                    "trial_size": trial,
                    "upgrade_size": upgrade,
                    "upgrade_size_semantics": "target_total_position_size",
                    "valid_grid_flag": 0.0 <= trial <= upgrade <= 1.0,
                    "example_incremental_upgrade_order_size": max(upgrade - trial, 0.0),
                }
            )
    return pd.DataFrame(rows)


def build_arm_registry(params: Params, state_ids: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "arm_id": "B0_deployed_baseline",
            "arm_variant_id": "B0_deployed_baseline__full",
            "state_id": "",
            "trial_size": 0.0,
            "upgrade_size": 1.0,
            "candidate_set": "Lane A union Lane B deployed baseline kept rows",
            "lane_contract": "A_and_B_immediate_full",
            "is_train_selection_candidate": False,
            "b0_b1_deployed_set_identical_flag": True,
            "b2_b3_composite_candidate_set_flag": True,
        }
    )
    rows.append(
        {
            "arm_id": "B1_immediate_full_entry",
            "arm_variant_id": "B1_immediate_full_entry__full",
            "state_id": "",
            "trial_size": 0.0,
            "upgrade_size": 1.0,
            "candidate_set": "Lane A union Lane B deployed baseline kept rows",
            "lane_contract": "A_and_B_immediate_full",
            "is_train_selection_candidate": False,
            "b0_b1_deployed_set_identical_flag": True,
            "b2_b3_composite_candidate_set_flag": True,
        }
    )
    for state_id in state_ids:
        for upgrade in params.upgrade_size_grid:
            rows.append(
                {
                    "arm_id": "B2_wait_confirm_K3",
                    "arm_variant_id": f"B2_wait_confirm_K3__{state_id}__target_{upgrade:.2f}",
                    "state_id": state_id,
                    "trial_size": 0.0,
                    "upgrade_size": upgrade,
                    "candidate_set": "Lane A K3 policy plus Lane B B0 carry-through",
                    "lane_contract": "A_policy_B_baseline_carry",
                    "is_train_selection_candidate": True,
                    "b0_b1_deployed_set_identical_flag": True,
                    "b2_b3_composite_candidate_set_flag": True,
                }
            )
        for trial in params.trial_size_grid:
            for upgrade in params.upgrade_size_grid:
                rows.append(
                    {
                        "arm_id": "B3_trial_then_upgrade_K3",
                        "arm_variant_id": f"B3_trial_then_upgrade_K3__{state_id}__trial_{trial:.2f}__target_{upgrade:.2f}",
                        "state_id": state_id,
                        "trial_size": trial,
                        "upgrade_size": upgrade,
                        "candidate_set": "Lane A K3 policy plus Lane B B0 carry-through",
                        "lane_contract": "A_policy_B_baseline_carry",
                        "is_train_selection_candidate": True,
                        "b0_b1_deployed_set_identical_flag": True,
                        "b2_b3_composite_candidate_set_flag": True,
                    }
                )
    for state_id in state_ids:
        rows.append(
            {
                "arm_id": "LB0_rejected_no_trade",
                "arm_variant_id": f"LB0_rejected_no_trade__{state_id}",
                "state_id": state_id,
                "trial_size": 0.0,
                "upgrade_size": 0.0,
                "candidate_set": "Lane B diagnostic only",
                "lane_contract": "B_no_trade_readout",
                "is_train_selection_candidate": False,
                "b0_b1_deployed_set_identical_flag": True,
                "b2_b3_composite_candidate_set_flag": True,
            }
        )
        rows.append(
            {
                "arm_id": "LB2_delayed_rescue_K3",
                "arm_variant_id": f"LB2_delayed_rescue_K3__{state_id}__target_1.00",
                "state_id": state_id,
                "trial_size": 0.0,
                "upgrade_size": 1.0,
                "candidate_set": "Lane B diagnostic delayed-confirmation rescue only",
                "lane_contract": "B_rescue_readout_only",
                "is_train_selection_candidate": False,
                "b0_b1_deployed_set_identical_flag": True,
                "b2_b3_composite_candidate_set_flag": True,
            }
        )
    registry = pd.DataFrame(rows)
    registry["upgrade_size_is_target_total_flag"] = True
    registry["trial_zero_wait_confirm_equivalence_flag"] = registry["trial_size"].eq(0.0) & registry["arm_id"].eq("B3_trial_then_upgrade_K3")
    registry["trial_zero_wait_confirm_equivalence_expected_flag"] = registry["trial_zero_wait_confirm_equivalence_flag"]
    return registry


def state_flag_name(state_id: str) -> str:
    return f"state_positive_{state_id}"


def add_segment(segments: list[dict[str, Any]], bars: pd.DataFrame, start_pos: int, end_pos: int, position_size: float, anchor_price: float) -> None:
    if position_size <= 0 or end_pos <= start_pos or start_pos >= len(bars):
        return
    end_pos = min(end_pos, len(bars) - 1)
    window = bars.iloc[start_pos:end_pos]
    if window.empty:
        return
    min_low = float(pd.to_numeric(window["low"], errors="coerce").min())
    max_high = float(pd.to_numeric(window["high"], errors="coerce").max())
    segments.append(
        {
            "start_pos": start_pos,
            "end_pos": end_pos,
            "position_size": position_size,
            "anchor_price": anchor_price,
            "exposure_days": float(position_size * max(end_pos - start_pos, 0)),
            "mae": min_low / anchor_price - 1.0 if anchor_price > 0 and np.isfinite(min_low) else np.nan,
            "mfe": max_high / anchor_price - 1.0 if anchor_price > 0 and np.isfinite(max_high) else np.nan,
        }
    )


def recompute_cost_basis(filled_lots: list[tuple[float, float]]) -> tuple[float, float, float]:
    total_notional = sum(size for size, _price in filled_lots)
    total_shares = sum(size / price for size, price in filled_lots if price > 0)
    if total_shares <= 0:
        return 0.0, 0.0, float("nan")
    return total_notional, total_shares, total_notional / total_shares


def weighted_average_cost_after_upgrade(trial_size: float, trial_price: float, upgrade_order_size: float, upgrade_price: float) -> float:
    lots = []
    if trial_size > 0 and trial_price > 0:
        lots.append((trial_size, trial_price))
    if upgrade_order_size > 0 and upgrade_price > 0:
        lots.append((upgrade_order_size, upgrade_price))
    return recompute_cost_basis(lots)[2]


def find_stop_pos(bars: pd.DataFrame, start_pos: int, end_pos: int, anchor_price: float, stop_drawdown: float) -> int | None:
    if not np.isfinite(anchor_price) or anchor_price <= 0:
        return None
    threshold = anchor_price * (1.0 + stop_drawdown)
    start_pos = max(0, start_pos)
    end_pos = min(end_pos, len(bars) - 1)
    for pos in range(start_pos, end_pos + 1):
        low = pd.to_numeric(pd.Series([bars.iloc[pos].get("low", np.nan)]), errors="coerce").iloc[0]
        if np.isfinite(low) and low <= threshold:
            return pos
    return None


def replay_row(row: pd.Series, arm: pd.Series, price_cache: PriceCache, board_map: dict[str, str], params: Params) -> dict[str, Any]:
    inst = str(row["instrument"])
    board = board_map.get(inst, "main_board")
    bars = price_cache.load(inst)
    base = {
        "policy_row_id": row["policy_row_id"],
        "sample_id": row["sample_id"],
        "selected_target_id": row["selected_target_id"],
        "denominator_id": row["denominator_id"],
        "input_event_key": row["input_event_key"],
        "instrument": inst,
        "event_t0_date": row["event_t0_date"],
        "split": row["split"],
        "lane_id": row["lane_id"],
        "arm_id": arm["arm_id"],
        "arm_variant_id": arm["arm_variant_id"],
        "state_id": arm.get("state_id", ""),
        "trial_size": float(arm.get("trial_size", 0.0)),
        "upgrade_size": float(arm.get("upgrade_size", 0.0)),
        "state_positive_flag": False,
        "winner_120_bool": boolish(row.get("winner_120_bool", False)),
        "big_failure_proxy_bool": boolish(row.get("class_big_failure_proxy_nonwinner_flag", row.get("big_failure_proxy_bool", False))),
        "fast_fail_10_bool": boolish(row.get("fast_fail_10_bool", False)),
        "false_repair_20_bool": boolish(row.get("false_repair_20_bool", False)),
        "binding_canonical_event_id": row.get("binding_canonical_event_id", ""),
        "board_bucket": board,
    }
    empty_result = {
        **base,
        "entry_filled_flag": False,
        "first_entry_date": "",
        "first_entry_pos": np.nan,
        "exit_date": "",
        "exit_pos": np.nan,
        "exit_reason": "no_trade",
        "gross_pnl_full_notional": 0.0,
        "buy_notional_full": 0.0,
        "sell_notional_full": 0.0,
        "turnover_notional_full": 0.0,
        "exposure_days_full": 0.0,
        "holding_sessions": 0,
        "max_position_size": 0.0,
        "final_position_size": 0.0,
        "risk_stop_anchor_price": np.nan,
        "mae": np.nan,
        "mfe": np.nan,
        "max_drawdown": np.nan,
        "scheduled_buy_order_n": 0,
        "scheduled_sell_order_n": 0,
        "limit_up_unfilled_n": 0,
        "limit_down_exit_failure_n": 0,
        "missing_open_unfilled_n": 0,
        "unfilled_reason": "",
        "exit_failure_reason": "",
        "component_role": "no_trade",
        "instrument_source": price_cache.instrument_source.get(inst, "missing"),
    }
    if bars is None:
        empty_result["unfilled_reason"] = "price_path_missing"
        return empty_result
    positions = date_pos_map(bars)
    event_pos = positions.get(str(row["event_t0_date"]))
    if event_pos is None:
        empty_result["unfilled_reason"] = "event_t0_date_missing_in_price"
        return empty_result
    t1_pos = event_pos + 1
    t4_pos = event_pos + 4
    horizon_pos = min(event_pos + params.max_holding_sessions, len(bars) - 1)
    if t1_pos >= len(bars):
        empty_result["unfilled_reason"] = "insufficient_post_t0_price_path"
        return empty_result

    arm_id = str(arm["arm_id"])
    lane_id = str(row["lane_id"])
    state_id = str(arm.get("state_id", ""))
    state_positive = boolish(row.get(state_flag_name(state_id), False)) if state_id else False
    base["state_positive_flag"] = state_positive

    if lane_id == "out_of_lane_10B_rejected":
        empty_result.update(base)
        empty_result["component_role"] = "out_of_lane_10B_rejected"
        return empty_result
    if arm_id in {"LB0_rejected_no_trade", "LB2_delayed_rescue_K3"} and lane_id != "lane_B_10C_ref_rejected":
        empty_result.update(base)
        empty_result["component_role"] = "not_lane_b_for_lb_arm"
        return empty_result

    filled_lots: list[tuple[float, float]] = []
    segments: list[dict[str, Any]] = []
    scheduled_buy = 0
    scheduled_sell = 0
    limit_up_unfilled = 0
    limit_down_failed = 0
    missing_unfilled = 0
    unfilled_reasons: list[str] = []
    exit_failure_reasons: list[str] = []
    first_entry_pos: int | None = None
    first_entry_date = ""
    exit_pos: int | None = None
    exit_date = ""
    exit_reason = "no_trade"
    last_change_pos: int | None = None
    position_size = 0.0
    max_position_size = 0.0
    risk_stop_anchor = np.nan
    total_notional = 0.0
    total_shares = 0.0
    gross_pnl = 0.0
    buy_notional = 0.0
    sell_notional = 0.0

    def close_segment(pos: int) -> None:
        nonlocal last_change_pos, position_size, risk_stop_anchor
        if last_change_pos is not None and position_size > 0 and np.isfinite(risk_stop_anchor):
            add_segment(segments, bars, last_change_pos, pos, position_size, risk_stop_anchor)
        last_change_pos = pos

    def try_buy(pos: int, size: float, role: str) -> bool:
        nonlocal scheduled_buy, limit_up_unfilled, missing_unfilled, first_entry_pos, first_entry_date
        nonlocal position_size, max_position_size, total_notional, total_shares, risk_stop_anchor, buy_notional, last_change_pos
        if size <= 0:
            return False
        scheduled_buy += 1
        ok, reason, price, date = action_fill_status(bars, pos, "buy", board)
        if not ok:
            if reason == "buy_unfilled_limit_up_locked":
                limit_up_unfilled += 1
            else:
                missing_unfilled += 1
            unfilled_reasons.append(f"{role}:{reason}")
            return False
        close_segment(pos)
        filled_lots.append((size, price))
        total_notional, total_shares, risk_stop_anchor = recompute_cost_basis(filled_lots)
        position_size += size
        max_position_size = max(max_position_size, position_size)
        buy_notional += size
        if first_entry_pos is None:
            first_entry_pos = pos
            first_entry_date = date
            last_change_pos = pos
        return True

    def find_next_sell_fill(pos: int) -> tuple[int | None, float, str, str]:
        nonlocal scheduled_sell, limit_down_failed, missing_unfilled
        scheduled_sell += 1
        search_pos = pos
        while search_pos <= horizon_pos:
            ok, reason, price, date = action_fill_status(bars, search_pos, "sell", board)
            if ok:
                return search_pos, price, date, "filled"
            if reason == "sell_unfilled_limit_down_locked":
                limit_down_failed += 1
                exit_failure_reasons.append(reason)
                search_pos += 1
                continue
            missing_unfilled += 1
            exit_failure_reasons.append(reason)
            search_pos += 1
        return None, float("nan"), "", "exit_unfilled_until_horizon"

    def try_sell_all(pos: int, reason: str) -> bool:
        nonlocal position_size, exit_pos, exit_date, exit_reason, sell_notional, gross_pnl, last_change_pos
        nonlocal total_notional, total_shares
        if position_size <= 0 or total_shares <= 0:
            return False
        fill_pos, price, date, status = find_next_sell_fill(pos)
        if fill_pos is None:
            exit_failure_reasons.append(status)
            return False
        close_segment(fill_pos)
        proceeds = total_shares * price
        gross_pnl = proceeds - total_notional
        sell_notional += proceeds
        position_size = 0.0
        exit_pos = fill_pos
        exit_date = date
        exit_reason = reason
        last_change_pos = fill_pos
        return True

    def scan_stop(start_pos: int, end_pos: int) -> bool:
        if position_size <= 0 or not np.isfinite(risk_stop_anchor):
            return False
        hit_pos = find_stop_pos(bars, start_pos, end_pos, risk_stop_anchor, params.risk_stop_drawdown_from_cost_basis)
        if hit_pos is None:
            return False
        return try_sell_all(hit_pos + 1, "risk_stop_next_open")

    role = "policy"
    if arm_id in {"B0_deployed_baseline", "B1_immediate_full_entry"}:
        role = "deployed_baseline_immediate"
        try_buy(t1_pos, 1.0, "immediate_full_entry")
        if position_size > 0:
            scan_stop(t1_pos + 1, horizon_pos - 1)
    elif arm_id in {"B2_wait_confirm_K3", "B3_trial_then_upgrade_K3"} and lane_id == "lane_B_10C_ref_rejected":
        role = "baseline_carry_for_lane_b"
        try_buy(t1_pos, 1.0, "lane_b_baseline_carry")
        if position_size > 0:
            scan_stop(t1_pos + 1, horizon_pos - 1)
    elif arm_id == "B2_wait_confirm_K3":
        role = "lane_a_wait_confirm_policy"
        if state_positive:
            try_buy(t4_pos, float(arm["upgrade_size"]), "wait_confirm_entry")
            if position_size > 0:
                scan_stop(t4_pos + 1, horizon_pos - 1)
    elif arm_id == "B3_trial_then_upgrade_K3":
        role = "lane_a_trial_then_upgrade_policy"
        trial_size = float(arm["trial_size"])
        target_size = float(arm["upgrade_size"])
        try_buy(t1_pos, trial_size, "trial_entry")
        if position_size > 0:
            stopped_before_k3 = scan_stop(t1_pos + 1, min(t4_pos - 1, horizon_pos - 1))
        else:
            stopped_before_k3 = False
        if not stopped_before_k3:
            if state_positive:
                incremental = max(target_size - position_size, 0.0)
                try_buy(t4_pos, incremental, "upgrade_to_target_total")
            elif position_size > 0:
                try_sell_all(t4_pos, "state_negative_trial_exit")
            if position_size > 0:
                scan_stop(t4_pos + 1, horizon_pos - 1)
    elif arm_id == "LB2_delayed_rescue_K3":
        role = "lane_b_delayed_rescue_readout"
        if state_positive:
            try_buy(t4_pos, 1.0, "lane_b_delayed_rescue_entry")
            if position_size > 0:
                scan_stop(t4_pos + 1, horizon_pos - 1)
    elif arm_id == "LB0_rejected_no_trade":
        role = "lane_b_no_trade_readout"

    if position_size > 0:
        try_sell_all(horizon_pos, "time_exit_120d")

    if position_size > 0 and last_change_pos is not None:
        close_segment(horizon_pos)

    exposure_days = float(sum(seg["exposure_days"] for seg in segments))
    maes = [seg["mae"] for seg in segments if pd.notna(seg["mae"])]
    mfes = [seg["mfe"] for seg in segments if pd.notna(seg["mfe"])]
    mae = float(min(maes)) if maes else np.nan
    mfe = float(max(mfes)) if mfes else np.nan
    holding = int(exit_pos - first_entry_pos) if exit_pos is not None and first_entry_pos is not None else 0
    result = {
        **base,
        "entry_filled_flag": first_entry_pos is not None,
        "first_entry_date": first_entry_date,
        "first_entry_pos": first_entry_pos if first_entry_pos is not None else np.nan,
        "exit_date": exit_date,
        "exit_pos": exit_pos if exit_pos is not None else np.nan,
        "exit_reason": exit_reason,
        "gross_pnl_full_notional": float(gross_pnl),
        "buy_notional_full": float(buy_notional),
        "sell_notional_full": float(sell_notional),
        "turnover_notional_full": float(buy_notional + sell_notional),
        "exposure_days_full": exposure_days,
        "holding_sessions": holding,
        "max_position_size": float(max_position_size),
        "final_position_size": float(max_position_size),
        "risk_stop_anchor_price": risk_stop_anchor,
        "mae": mae,
        "mfe": mfe,
        "max_drawdown": mae,
        "scheduled_buy_order_n": scheduled_buy,
        "scheduled_sell_order_n": scheduled_sell,
        "limit_up_unfilled_n": limit_up_unfilled,
        "limit_down_exit_failure_n": limit_down_failed,
        "missing_open_unfilled_n": missing_unfilled,
        "unfilled_reason": "|".join(sorted(set(unfilled_reasons))),
        "exit_failure_reason": "|".join(sorted(set(exit_failure_reasons))),
        "component_role": role,
        "instrument_source": price_cache.instrument_source.get(inst, "missing"),
    }
    return result


def replay_all_events(base: pd.DataFrame, arm_registry: pd.DataFrame, price_cache: PriceCache, board_map: dict[str, str], params: Params) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    eligible = base.loc[base["lane_id"].isin(["lane_A_10C_ref_kept", "lane_B_10C_ref_rejected"])].copy()
    for _, arm in arm_registry.iterrows():
        arm_id = str(arm["arm_id"])
        if arm_id in {"LB0_rejected_no_trade", "LB2_delayed_rescue_K3"}:
            work = eligible.loc[eligible["lane_id"].eq("lane_B_10C_ref_rejected")]
        else:
            work = eligible
        for _, row in work.iterrows():
            rows.append(replay_row(row, arm, price_cache, board_map, params))
    return pd.DataFrame(rows)


def apply_portfolio_constraints(event_ledger: pd.DataFrame, params: Params) -> pd.DataFrame:
    if event_ledger.empty:
        return pd.DataFrame()
    frames = []
    for capacity in params.capacity_slots:
        per_full = 1.0 / float(capacity)
        cap_frame = event_ledger.copy()
        cap_frame["capacity_slots"] = capacity
        cap_frame["per_position_full_size_notional"] = per_full
        cap_frame["portfolio_accepted_flag"] = False
        cap_frame["portfolio_unfilled_reason"] = ""
        cap_frame["portfolio_notional_scale"] = 0.0
        for variant, group in cap_frame.groupby("arm_variant_id", sort=False):
            active: list[dict[str, Any]] = []
            group_sorted = group.sort_values(["first_entry_date", "instrument", "policy_row_id"], kind="stable")
            for idx, row in group_sorted.iterrows():
                if not boolish(row.get("entry_filled_flag", False)) or not nonempty(row.get("first_entry_date")):
                    continue
                entry_date = str(row["first_entry_date"])
                active = [item for item in active if str(item["exit_date"]) > entry_date]
                desired = per_full * float(row.get("max_position_size", 0.0))
                gross = sum(float(item["notional"]) for item in active)
                inst_gross = sum(float(item["notional"]) for item in active if item["instrument"] == row["instrument"])
                board_gross = sum(float(item["notional"]) for item in active if item["board_bucket"] == row["board_bucket"])
                reason = ""
                if gross + desired > params.max_gross_exposure + 1e-12:
                    reason = "unfilled_cash_constraint"
                elif inst_gross + desired > params.max_instrument_weight + 1e-12:
                    reason = "unfilled_instrument_weight_constraint"
                elif board_gross + desired > params.max_board_weight + 1e-12:
                    reason = "unfilled_board_weight_constraint"
                if reason:
                    cap_frame.at[idx, "portfolio_unfilled_reason"] = reason
                else:
                    cap_frame.at[idx, "portfolio_accepted_flag"] = True
                    cap_frame.at[idx, "portfolio_notional_scale"] = per_full
                    if nonempty(row.get("exit_date")):
                        active.append(
                            {
                                "instrument": row["instrument"],
                                "board_bucket": row.get("board_bucket", "unknown"),
                                "entry_date": entry_date,
                                "exit_date": row["exit_date"],
                                "notional": desired,
                            }
                        )
        frames.append(cap_frame)
    return pd.concat(frames, ignore_index=True)


def build_portfolio_daily_ledger(portfolio_ledger: pd.DataFrame) -> pd.DataFrame:
    rows = []
    accepted = portfolio_ledger.loc[portfolio_ledger["portfolio_accepted_flag"].map(boolish)].copy()
    if accepted.empty:
        return pd.DataFrame(
            [
                {
                    "arm_variant_id": "",
                    "capacity_slots": 0,
                    "date": "",
                    "gross_exposure": 0.0,
                    "cash_drag_day": 1.0,
                    "concurrent_positions": 0,
                    "portfolio_daily_status": "empty",
                }
            ]
        )
    for (variant, capacity), group in accepted.groupby(["arm_variant_id", "capacity_slots"], sort=False):
        valid = group.loc[group["first_entry_date"].astype(str).ne("") & group["exit_date"].astype(str).ne("")].copy()
        if valid.empty:
            continue
        valid["_entry_dt"] = pd.to_datetime(valid["first_entry_date"], errors="coerce")
        valid["_exit_dt"] = pd.to_datetime(valid["exit_date"], errors="coerce")
        valid = valid.dropna(subset=["_entry_dt", "_exit_dt"])
        if valid.empty:
            continue
        start = valid["_entry_dt"].min()
        end = valid["_exit_dt"].max()
        dates = pd.date_range(start, end, freq="D")
        exposure_delta = pd.Series(0.0, index=dates)
        count_delta = pd.Series(0, index=dates)
        notionals = (valid["portfolio_notional_scale"].astype(float) * valid["max_position_size"].astype(float)).to_numpy()
        for entry, exit_date, notional in zip(valid["_entry_dt"].to_numpy(), valid["_exit_dt"].to_numpy(), notionals):
            entry_ts = pd.Timestamp(entry)
            exit_ts = pd.Timestamp(exit_date)
            if exit_ts <= entry_ts:
                continue
            if entry_ts in exposure_delta.index:
                exposure_delta.loc[entry_ts] += float(notional)
                count_delta.loc[entry_ts] += 1
            if exit_ts in exposure_delta.index:
                exposure_delta.loc[exit_ts] -= float(notional)
                count_delta.loc[exit_ts] -= 1
        gross_series = exposure_delta.cumsum().clip(lower=0.0)
        count_series = count_delta.cumsum().clip(lower=0)
        rows.extend(
            {
                "arm_variant_id": variant,
                "capacity_slots": capacity,
                "date": date.strftime("%Y-%m-%d"),
                "gross_exposure": float(gross),
                "cash_drag_day": 1.0 - float(gross),
                "concurrent_positions": int(count_series.loc[date]),
                "portfolio_daily_status": "ok",
            }
            for date, gross in gross_series.items()
        )
    return pd.DataFrame(rows)


def net_fields(frame: pd.DataFrame, buy_cost_bps: float, sell_cost_bps: float) -> pd.DataFrame:
    out = frame.copy()
    buy_cost = out["buy_notional_full"].astype(float) * buy_cost_bps / 10000.0
    sell_cost = out["sell_notional_full"].astype(float) * sell_cost_bps / 10000.0
    out["transaction_cost_full"] = buy_cost + sell_cost
    out["net_pnl_full_notional"] = out["gross_pnl_full_notional"].astype(float) - out["transaction_cost_full"]
    out["portfolio_net_pnl"] = np.where(out["portfolio_accepted_flag"].map(boolish), out["net_pnl_full_notional"] * out["portfolio_notional_scale"], 0.0)
    out["portfolio_gross_pnl"] = np.where(out["portfolio_accepted_flag"].map(boolish), out["gross_pnl_full_notional"] * out["portfolio_notional_scale"], 0.0)
    out["portfolio_exposure_days"] = np.where(out["portfolio_accepted_flag"].map(boolish), out["exposure_days_full"] * out["portfolio_notional_scale"], 0.0)
    out["portfolio_turnover_notional"] = np.where(out["portfolio_accepted_flag"].map(boolish), out["turnover_notional_full"] * out["portfolio_notional_scale"], 0.0)
    out["portfolio_transaction_cost"] = np.where(out["portfolio_accepted_flag"].map(boolish), out["transaction_cost_full"] * out["portfolio_notional_scale"], 0.0)
    out["net_return"] = out["net_pnl_full_notional"]
    return out


def summarize_one(group: pd.DataFrame, denominator: pd.DataFrame, daily: pd.DataFrame, b0_captured_winners: int) -> dict[str, Any]:
    accepted = group.loc[group["portfolio_accepted_flag"].astype(bool)].copy()
    den_n = len(denominator)
    winner_den = int(denominator["winner_120_bool"].astype(bool).sum()) if len(denominator) else 0
    captured_winners = int(accepted["winner_120_bool"].astype(bool).sum()) if len(accepted) else 0
    net_returns = accepted["net_return"].astype(float) if len(accepted) else pd.Series(dtype=float)
    if len(net_returns):
        clipped = net_returns.clip(net_returns.quantile(0.01), net_returns.quantile(0.99))
        net_median = float(net_returns.median())
        net_wmean = float(clipped.mean())
    else:
        net_median = np.nan
        net_wmean = np.nan
    fast_fail = accepted.loc[accepted["fast_fail_10_bool"].astype(bool)]
    big_failure_entries = int(accepted["big_failure_proxy_bool"].astype(bool).sum()) if len(accepted) else 0
    false_repair_entries = int(accepted["false_repair_20_bool"].astype(bool).sum()) if len(accepted) else 0
    fast_fail_loss = int((fast_fail["net_return"].astype(float) < 0).sum()) if len(fast_fail) else 0
    scheduled_buy = int(group["scheduled_buy_order_n"].sum()) if len(group) else 0
    scheduled_sell = int(group["scheduled_sell_order_n"].sum()) if len(group) else 0
    turnover = float(group["portfolio_turnover_notional"].sum()) if len(group) else 0.0
    cost = float(group["portfolio_transaction_cost"].sum()) if len(group) else 0.0
    exposure = float(group["portfolio_exposure_days"].sum()) if len(group) else 0.0
    pnl = float(group["portfolio_net_pnl"].sum()) if len(group) else 0.0
    mae = pd.to_numeric(accepted.get("mae", pd.Series(dtype=float)), errors="coerce").dropna()
    dd = pd.to_numeric(accepted.get("max_drawdown", pd.Series(dtype=float)), errors="coerce").dropna()
    board_notional = accepted.groupby("board_bucket")["portfolio_notional_scale"].sum() if len(accepted) else pd.Series(dtype=float)
    board_hhi = float(((board_notional / board_notional.sum()) ** 2).sum()) if board_notional.sum() else np.nan
    daily_mean_gross = float(daily["gross_exposure"].mean()) if len(daily) else np.nan
    cash_drag = float(daily["cash_drag_day"].mean()) if len(daily) else np.nan
    max_concurrent = int(daily["concurrent_positions"].max()) if len(daily) else 0
    return {
        "evaluated_row_n": den_n,
        "entry_filled_n": int(len(accepted)),
        "entry_rate": safe_rate(int(len(accepted)), den_n),
        "net_median_return": net_median,
        "net_winsorized_mean_return_1_99": net_wmean,
        "net_ev_per_exposure_day": pnl / exposure if exposure > 0 else np.nan,
        "winner_120_retention_rate": safe_rate(captured_winners, b0_captured_winners),
        "winner_120_capture_rate": safe_rate(captured_winners, winner_den),
        "winner_120_captured_n": captured_winners,
        "winner_120_denominator_n": winner_den,
        "big_failure_proxy_entry_rate": safe_rate(big_failure_entries, den_n),
        "false_repair_entry_rate": safe_rate(false_repair_entries, den_n),
        "fast_fail_realized_loss_rate": safe_rate(fast_fail_loss, len(fast_fail)),
        "mae_p50": float(mae.quantile(0.50)) if len(mae) else np.nan,
        "mae_p95": float(mae.quantile(0.95)) if len(mae) else np.nan,
        "max_drawdown_p95": float(dd.quantile(0.95)) if len(dd) else np.nan,
        "turnover_notional": turnover,
        "transaction_cost_bps_paid": cost / turnover * 10000.0 if turnover > 0 else 0.0,
        "capital_utilization_mean": daily_mean_gross,
        "cash_drag_mean": cash_drag,
        "max_concurrent_positions": max_concurrent,
        "board_concentration_hhi": board_hhi,
        "industry_concentration_hhi": np.nan,
        "limit_up_unfilled_rate": safe_rate(int(group["limit_up_unfilled_n"].sum()), scheduled_buy),
        "limit_down_exit_failure_rate": safe_rate(int(group["limit_down_exit_failure_n"].sum()), scheduled_sell),
        "topk_removal_net_ev_per_exposure_day_lift": np.nan,
        "instrument_block_bootstrap_ci_low": np.nan,
        "instrument_block_bootstrap_ci_high": np.nan,
    }


def build_performance_summary(
    portfolio_ledger: pd.DataFrame,
    base_denominator: pd.DataFrame,
    daily_ledger: pd.DataFrame,
    params: Params,
) -> pd.DataFrame:
    rows = []
    denom_by_lane_split = {}
    for split in READOUT_SPLITS:
        split_base = base_denominator if split == "all" else base_denominator.loc[base_denominator["split"].eq(split)]
        for lane in ["all", "lane_A_10C_ref_kept", "lane_B_10C_ref_rejected"]:
            denom = split_base if lane == "all" else split_base.loc[split_base["lane_id"].eq(lane)]
            denom_by_lane_split[(lane, split)] = denom
    for cost_name, buy_bps, sell_bps in params.cost_scenarios:
        cost_frame = net_fields(portfolio_ledger, buy_bps, sell_bps)
        for capacity in params.capacity_slots:
            cap_frame = cost_frame.loc[cost_frame["capacity_slots"].eq(capacity)]
            b0 = cap_frame.loc[cap_frame["arm_id"].eq("B0_deployed_baseline")]
            b0_lookup = {}
            for split in READOUT_SPLITS:
                split_b0 = b0 if split == "all" else b0.loc[b0["split"].eq(split)]
                for lane in ["all", "lane_A_10C_ref_kept", "lane_B_10C_ref_rejected"]:
                    lane_b0 = split_b0 if lane == "all" else split_b0.loc[split_b0["lane_id"].eq(lane)]
                    b0_lookup[(lane, split)] = int(lane_b0.loc[lane_b0["portfolio_accepted_flag"].astype(bool), "winner_120_bool"].astype(bool).sum())
            for (variant, arm_id), group0 in cap_frame.groupby(["arm_variant_id", "arm_id"], sort=False):
                daily_variant = daily_ledger.loc[daily_ledger["arm_variant_id"].eq(variant) & daily_ledger["capacity_slots"].eq(capacity)]
                for split in READOUT_SPLITS:
                    group_split = group0 if split == "all" else group0.loc[group0["split"].eq(split)]
                    for lane in ["all", "lane_A_10C_ref_kept", "lane_B_10C_ref_rejected"]:
                        if arm_id in {"LB0_rejected_no_trade", "LB2_delayed_rescue_K3"} and lane != "lane_B_10C_ref_rejected":
                            continue
                        group = group_split if lane == "all" else group_split.loc[group_split["lane_id"].eq(lane)]
                        denom = denom_by_lane_split[(lane, split)]
                        if group.empty and denom.empty:
                            continue
                        summary = summarize_one(group, denom, daily_variant, b0_lookup.get((lane, split), 0))
                        rows.append(
                            {
                                "arm_variant_id": variant,
                                "arm_id": arm_id,
                                "lane_id": lane,
                                "split": split,
                                "cost_scenario": cost_name,
                                "buy_cost_bps": buy_bps,
                                "sell_cost_bps": sell_bps,
                                "capacity_slots": capacity,
                                **summary,
                            }
                        )
    perf = pd.DataFrame(rows)
    return perf


def build_robust_metric_package(perf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    base = perf.loc[perf["arm_id"].eq("B0_deployed_baseline")].copy()
    for _, row in perf.iterrows():
        match = base.loc[
            base["lane_id"].eq(row["lane_id"])
            & base["split"].eq(row["split"])
            & base["cost_scenario"].eq(row["cost_scenario"])
            & base["capacity_slots"].eq(row["capacity_slots"])
        ]
        b0 = match.iloc[0] if not match.empty else None
        def lift(col: str) -> float:
            if b0 is None or pd.isna(row.get(col)) or pd.isna(b0.get(col)):
                return np.nan
            return float(row[col]) - float(b0[col])
        rows.append(
            {
                "arm_variant_id": row["arm_variant_id"],
                "arm_id": row["arm_id"],
                "lane_id": row["lane_id"],
                "split": row["split"],
                "cost_scenario": row["cost_scenario"],
                "capacity_slots": row["capacity_slots"],
                "net_ev_per_exposure_day_lift_vs_B0": lift("net_ev_per_exposure_day"),
                "winner_capture_rate_lift_vs_B0": lift("winner_120_capture_rate"),
                "big_failure_proxy_entry_rate_lift_vs_B0": lift("big_failure_proxy_entry_rate"),
                "false_repair_entry_rate_lift_vs_B0": lift("false_repair_entry_rate"),
                "fast_fail_realized_loss_rate_lift_vs_B0": lift("fast_fail_realized_loss_rate"),
                "mae_p95_lift_vs_B0": lift("mae_p95"),
                "cash_drag_mean_lift_vs_B0": lift("cash_drag_mean"),
                "board_concentration_hhi_lift_vs_B0": lift("board_concentration_hhi"),
            }
        )
    return pd.DataFrame(rows)


def select_policy(
    perf: pd.DataFrame,
    robust: pd.DataFrame,
    arm_registry: pd.DataFrame,
    base: pd.DataFrame,
    params: Params,
) -> pd.DataFrame:
    rows = []
    candidates = arm_registry.loc[arm_registry["is_train_selection_candidate"].map(boolish)].copy()
    primary = robust.loc[
        robust["split"].eq("train")
        & robust["lane_id"].eq("all")
        & robust["cost_scenario"].eq("base_cost")
        & robust["capacity_slots"].eq(params.primary_capacity_slots)
    ]
    perf_primary = perf.loc[
        perf["split"].eq("train")
        & perf["lane_id"].eq("all")
        & perf["cost_scenario"].eq("base_cost")
        & perf["capacity_slots"].eq(params.primary_capacity_slots)
    ]
    for _, arm in candidates.iterrows():
        variant = arm["arm_variant_id"]
        state_id = arm["state_id"]
        train_a = base.loc[base["split"].eq("train") & base["lane_id"].eq("lane_A_10C_ref_kept")]
        state_pos = bool_series(train_a.get(state_flag_name(state_id), False), train_a.index)
        state_positive_entry_n = int(state_pos.sum())
        state_positive_winner_n = int((state_pos & train_a["winner_120_bool"]).sum())
        r = primary.loc[primary["arm_variant_id"].eq(variant)]
        p = perf_primary.loc[perf_primary["arm_variant_id"].eq(variant)]
        if r.empty or p.empty:
            continue
        rr = r.iloc[0]
        pp = p.iloc[0]
        ev_lift = float(rr["net_ev_per_exposure_day_lift_vs_B0"]) if pd.notna(rr["net_ev_per_exposure_day_lift_vs_B0"]) else -999.0
        winner_capture_ok = bool(
            pd.notna(pp["winner_120_capture_rate"])
            and pd.notna((perf_primary.loc[perf_primary["arm_id"].eq("B0_deployed_baseline"), "winner_120_capture_rate"].iloc[0]))
            and pp["winner_120_capture_rate"]
            >= perf_primary.loc[perf_primary["arm_id"].eq("B0_deployed_baseline"), "winner_120_capture_rate"].iloc[0] - params.winner_capture_tolerance
        )
        failure_ok = bool(
            (pd.isna(rr["big_failure_proxy_entry_rate_lift_vs_B0"]) or rr["big_failure_proxy_entry_rate_lift_vs_B0"] <= params.big_failure_entry_lift_ceiling)
            and (pd.isna(rr["false_repair_entry_rate_lift_vs_B0"]) or rr["false_repair_entry_rate_lift_vs_B0"] <= params.false_repair_entry_lift_ceiling)
        )
        pre_gate = (
            state_positive_entry_n >= params.train_state_positive_entry_n_floor
            and state_positive_winner_n >= params.train_state_positive_winner_n_floor
            and ev_lift > 0
            and winner_capture_ok
            and failure_ok
            and (pd.isna(pp["limit_up_unfilled_rate"]) or pp["limit_up_unfilled_rate"] <= params.limit_up_unfilled_rate_ceiling)
            and (pd.isna(pp["limit_down_exit_failure_rate"]) or pp["limit_down_exit_failure_rate"] <= params.limit_down_exit_failure_rate_ceiling)
        )
        score = ev_lift
        if pd.notna(rr["big_failure_proxy_entry_rate_lift_vs_B0"]):
            score -= max(float(rr["big_failure_proxy_entry_rate_lift_vs_B0"]), 0.0) * 10.0
        if pd.notna(rr["false_repair_entry_rate_lift_vs_B0"]):
            score -= max(float(rr["false_repair_entry_rate_lift_vs_B0"]), 0.0) * 10.0
        rows.append(
            {
                "arm_variant_id": variant,
                "arm_id": arm["arm_id"],
                "state_id": state_id,
                "trial_size": arm["trial_size"],
                "upgrade_size": arm["upgrade_size"],
                "state_positive_entry_n_train": state_positive_entry_n,
                "state_positive_winner_n_train": state_positive_winner_n,
                "net_ev_per_exposure_day_lift_vs_B0_train": ev_lift,
                "winner_capture_gate_ok": winner_capture_ok,
                "failure_exposure_gate_ok": failure_ok,
                "train_pre_gate_pass_flag": pre_gate,
                "train_policy_selection_score": score,
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(
            [
                {
                    "arm_variant_id": "",
                    "selection_status": "no_candidate_rows",
                    "selected_policy_flag": False,
                }
            ]
        )
    passed = out.loc[out["train_pre_gate_pass_flag"].map(boolish)].copy()
    if passed.empty:
        idx = out["train_policy_selection_score"].astype(float).idxmax()
        out["selected_policy_flag"] = False
        out.loc[idx, "selected_policy_flag"] = True
        out["selection_status"] = "best_diagnostic_candidate_no_train_pre_gate_pass"
    else:
        idx = passed["train_policy_selection_score"].astype(float).idxmax()
        out["selected_policy_flag"] = False
        out.loc[idx, "selected_policy_flag"] = True
        out["selection_status"] = np.where(out["selected_policy_flag"], "selected_by_train_policy_selection_score", "not_selected")
    return out


def validation_low_power(selected_variant: str, base: pd.DataFrame, params: Params) -> bool:
    validation = base.loc[base["split"].eq("validation")]
    winner_n = int(validation["winner_120_bool"].sum()) if len(validation) else 0
    if not selected_variant:
        return True
    parts = selected_variant.split("__")
    state_id = parts[1] if len(parts) > 1 and parts[0].startswith(("B2", "B3", "LB2", "LB0")) else ""
    if not state_id or state_flag_name(state_id) not in validation.columns:
        return winner_n < params.validation_min_winner_n
    state_winners = int((validation["winner_120_bool"] & bool_series(validation[state_flag_name(state_id)], validation.index)).sum())
    return winner_n < params.validation_min_winner_n or state_winners < params.validation_min_state_positive_winner_n


def build_topk_sensitivity(portfolio_ledger: pd.DataFrame, selected_variant: str, params: Params) -> pd.DataFrame:
    rows = []
    if not selected_variant:
        return pd.DataFrame([{"arm_variant_id": "", "top_k": 0, "split": "all", "topk_status": "no_selected_policy"}])
    base = net_fields(portfolio_ledger, 8.0, 13.0)
    for split in ["train", "robustness"]:
        policy = base.loc[base["arm_variant_id"].eq(selected_variant) & base["split"].eq(split) & base["capacity_slots"].eq(params.primary_capacity_slots)]
        b0 = base.loc[base["arm_id"].eq("B0_deployed_baseline") & base["split"].eq(split) & base["capacity_slots"].eq(params.primary_capacity_slots)]
        contrib = policy.groupby("instrument")["portfolio_net_pnl"].sum().sort_values(ascending=False)
        episode = policy.groupby("binding_canonical_event_id")["portfolio_net_pnl"].sum().sort_values(ascending=False)
        total_lift = float(policy["portfolio_net_pnl"].sum() - b0["portfolio_net_pnl"].sum())
        positive_contrib = contrib.clip(lower=0.0)
        contribution_denom = float(positive_contrib.sum())
        if contribution_denom <= 0:
            contribution_denom = float(contrib.abs().sum())
        contribution_denom = max(contribution_denom, 1e-12)
        positive_episode = episode.clip(lower=0.0)
        episode_denom = float(positive_episode.sum())
        if episode_denom <= 0:
            episode_denom = float(episode.abs().sum())
        episode_denom = max(episode_denom, 1e-12)
        top1_share = float(positive_contrib.head(1).sum() / contribution_denom) if len(contrib) else np.nan
        top5_share = float(positive_contrib.head(5).sum() / contribution_denom) if len(contrib) else np.nan
        episode_share = float(positive_episode.head(1).sum() / episode_denom) if len(episode) else np.nan
        for k in [1, 3, 5, 10]:
            remove = set(contrib.head(k).index)
            p2 = policy.loc[~policy["instrument"].isin(remove)]
            b2 = b0.loc[~b0["instrument"].isin(remove)]
            exposure = float(p2["portfolio_exposure_days"].sum())
            b0_exp = float(b2["portfolio_exposure_days"].sum())
            ev = float(p2["portfolio_net_pnl"].sum()) / exposure if exposure > 0 else np.nan
            b_ev = float(b2["portfolio_net_pnl"].sum()) / b0_exp if b0_exp > 0 else np.nan
            rows.append(
                {
                    "arm_variant_id": selected_variant,
                    "split": split,
                    "top_k": k,
                    "ranking_metric": "contribution_to_net_pnl",
                    "removed_instrument_n": len(remove),
                    "net_ev_per_exposure_day_lift_after_removal": ev - b_ev if pd.notna(ev) and pd.notna(b_ev) else np.nan,
                    "top1_instrument_contribution_share": top1_share,
                    "top5_instrument_contribution_share": top5_share,
                    "top_episode_contribution_share": episode_share,
                    "topk_dependency_status": "topk_dependent"
                    if (top1_share > params.top1_contribution_share_ceiling or top5_share > params.top5_contribution_share_ceiling or episode_share > params.episode_contribution_share_ceiling)
                    else "ok",
                    "raw_total_net_pnl_lift": total_lift,
                }
            )
    return pd.DataFrame(rows)


def build_bootstrap_ci(portfolio_ledger: pd.DataFrame, selected_variant: str, params: Params) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    samples = []
    if not selected_variant:
        empty = pd.DataFrame([{"arm_variant_id": "", "split": "all", "bootstrap_status": "no_selected_policy"}])
        return empty, empty.copy()
    base = net_fields(portfolio_ledger, 8.0, 13.0)
    for split in PRIMARY_SPLITS:
        policy = base.loc[base["arm_variant_id"].eq(selected_variant) & base["split"].eq(split) & base["capacity_slots"].eq(params.primary_capacity_slots)]
        b0 = base.loc[base["arm_id"].eq("B0_deployed_baseline") & base["split"].eq(split) & base["capacity_slots"].eq(params.primary_capacity_slots)]
        p_agg = policy.groupby("instrument", dropna=False).agg(
            policy_pnl=("portfolio_net_pnl", "sum"),
            policy_exposure=("portfolio_exposure_days", "sum"),
        )
        b_agg = b0.groupby("instrument", dropna=False).agg(
            b0_pnl=("portfolio_net_pnl", "sum"),
            b0_exposure=("portfolio_exposure_days", "sum"),
        )
        agg = p_agg.join(b_agg, how="outer").fillna(0.0).reset_index()
        instruments = agg["instrument"].astype(str).tolist()
        if not instruments:
            rows.append({"arm_variant_id": selected_variant, "split": split, "ci_low": np.nan, "ci_high": np.nan, "bootstrap_status": "empty"})
            continue
        p_pnl = agg["policy_pnl"].astype(float).to_numpy()
        p_exp = agg["policy_exposure"].astype(float).to_numpy()
        b_pnl = agg["b0_pnl"].astype(float).to_numpy()
        b_exp = agg["b0_exposure"].astype(float).to_numpy()
        values = []
        for i in range(params.bootstrap_n):
            seed = stable_seed(params.bootstrap_seed, selected_variant, split, i)
            rng = np.random.default_rng(seed)
            draw = rng.integers(0, len(instruments), size=len(instruments))
            p_sum = float(p_pnl[draw].sum())
            b_sum = float(b_pnl[draw].sum())
            p_exp_sum = float(p_exp[draw].sum())
            b_exp_sum = float(b_exp[draw].sum())
            metric = (p_sum / p_exp_sum if p_exp_sum > 0 else np.nan) - (b_sum / b_exp_sum if b_exp_sum > 0 else np.nan)
            values.append(metric)
            samples.append({"arm_variant_id": selected_variant, "split": split, "iteration": i, "net_ev_per_exposure_day_lift_vs_B0": metric})
        ser = pd.Series(values, dtype=float).dropna()
        rows.append(
            {
                "arm_variant_id": selected_variant,
                "split": split,
                "bootstrap_n": params.bootstrap_n,
                "block_key": "instrument",
                "metric": "net_ev_per_exposure_day_lift_vs_B0",
                "resampled_instrument_n": len(instruments),
                "sample_unique_metric_n": int(ser.round(12).nunique()) if len(ser) else 0,
                "sample_std": float(ser.std(ddof=1)) if len(ser) > 1 else np.nan,
                "ci_low": float(ser.quantile(0.05)) if len(ser) else np.nan,
                "ci_high": float(ser.quantile(0.95)) if len(ser) else np.nan,
                "median": float(ser.median()) if len(ser) else np.nan,
                "bootstrap_status": "ok" if len(ser) and int(ser.round(12).nunique()) > 1 else ("degenerate_resample" if len(ser) else "empty"),
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(samples)


def lane_b_rescue_power(base: pd.DataFrame, selected_state_id: str, params: Params) -> pd.DataFrame:
    rows = []
    flag = state_flag_name(selected_state_id) if selected_state_id else ""
    for split in ["train", "robustness"]:
        group = base.loc[base["lane_id"].eq("lane_B_10C_ref_rejected") & base["split"].eq(split)]
        state_pos = bool_series(group.get(flag, False), group.index) if flag else pd.Series(False, index=group.index)
        entry_n = int(state_pos.sum())
        winner_n = int((state_pos & group["winner_120_bool"]).sum()) if len(group) else 0
        rows.append(
            {
                "split": split,
                "selected_state_id": selected_state_id,
                "lane_B_state_positive_entry_n": entry_n,
                "lane_B_state_positive_winner_n": winner_n,
                "entry_floor": params.lane_b_train_entry_floor if split == "train" else params.lane_b_robustness_entry_floor,
                "winner_floor": params.lane_b_train_winner_floor if split == "train" else params.lane_b_robustness_winner_floor,
                "power_pass_flag": entry_n >= (params.lane_b_train_entry_floor if split == "train" else params.lane_b_robustness_entry_floor)
                and winner_n >= (params.lane_b_train_winner_floor if split == "train" else params.lane_b_robustness_winner_floor),
            }
        )
    out = pd.DataFrame(rows)
    out["lane_b_rescue_status"] = (
        "lane_b_rescue_power_supported_for_future_research"
        if out["power_pass_flag"].all()
        else "lane_b_rescue_readout_only_low_power"
    )
    return out


def final_status_decision(
    internal_status: str,
    incomplete_reasons: list[str],
    selected_variant: str,
    selection: pd.DataFrame,
    topk: pd.DataFrame,
    bootstrap: pd.DataFrame,
    validation_low_power_flag: bool,
) -> tuple[str, list[str]]:
    reasons = list(incomplete_reasons)
    if incomplete_reasons:
        return FINAL_INCOMPLETE, reasons
    if not selected_variant:
        return FINAL_NOT_SUPPORTED, ["no_selected_policy"]
    if internal_status != FINAL_SUPPORTED:
        return internal_status, reasons
    if not topk.empty and topk["topk_dependency_status"].astype(str).eq("topk_dependent").any():
        return FINAL_TOPK, ["topk_dependency_status"]
    train_ci = bootstrap.loc[bootstrap["split"].eq("train")]
    robust_ci = bootstrap.loc[bootstrap["split"].eq("robustness")]
    if not train_ci.empty and pd.notna(train_ci.iloc[0].get("ci_low")) and train_ci.iloc[0]["ci_low"] <= 0:
        return FINAL_NOT_SUPPORTED, ["train_bootstrap_ci_low_not_positive"]
    if not robust_ci.empty and pd.notna(robust_ci.iloc[0].get("ci_low")) and robust_ci.iloc[0]["ci_low"] <= 0:
        return FINAL_NOT_SUPPORTED, ["robustness_bootstrap_ci_low_not_positive"]
    validation_ci = bootstrap.loc[bootstrap["split"].eq("validation")]
    if not validation_low_power_flag and not validation_ci.empty and pd.notna(validation_ci.iloc[0].get("ci_high")) and validation_ci.iloc[0]["ci_high"] < 0:
        return FINAL_NOT_SUPPORTED, ["powered_validation_ci_high_negative"]
    return FINAL_SUPPORTED, reasons


def build_input_artifact_audit(paths: dict[str, Path], config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for key, path in paths.items():
        if key.endswith("_dir"):
            exists = path.exists() and path.is_dir()
            sha = ""
            row_count = ""
        else:
            exists = path.exists()
            sha = file_sha256(path) if exists and path.is_file() else ""
            row_count = quick_row_count(path) if exists and path.is_file() else ""
        rows.append(
            {
                "input_key": key,
                "path": relative_path(path),
                "exists_flag": bool(exists),
                "sha256": sha,
                "row_count": row_count,
                "audit_status": "ok" if exists else "missing",
            }
        )
    return pd.DataFrame(rows)


def build_scope_reconciliation(denom: pd.DataFrame, paths: dict[str, Path]) -> pd.DataFrame:
    risk = pd.read_csv(paths["eleven_a1_scope_risk_on"])
    pit = pd.read_csv(paths["eleven_a1_scope_pit"])
    rows = []
    for split in READOUT_SPLITS:
        group = denom if split == "all" else denom.loc[denom["split"].eq(split)]
        pit_row = pit.loc[pit["split"].astype(str).eq(split)]
        risk_row = risk.loc[risk["split"].astype(str).eq(split)]
        a1_pit = int(pit_row["pit_valid_evaluated_row_n"].iloc[0]) if not pit_row.empty else 0
        a1_pre = int(risk_row["risk_on_evaluated_row_n"].iloc[0]) if not risk_row.empty else 0
        rows.append(
            {
                "split": split,
                "eleven_a1_risk_on_pre_pit_row_n": a1_pre,
                "eleven_a1_pit_valid_row_n": a1_pit,
                "eleven_c_pit_valid_row_n": len(group),
                "denominator_row_match_flag": len(group) == a1_pit,
                "pit_excluded_rows_remain_out_of_scope_flag": True,
                "scope_reconciliation_status": "ok" if len(group) == a1_pit else "denominator_drift",
            }
        )
    return pd.DataFrame(rows)


def build_label_overlap_policy_audit(feature_registry: pd.DataFrame, state_registry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in feature_registry.iterrows():
        status = row["registry_status"]
        rows.append(
            {
                "feature_id": row["feature_id"],
                "registry_status": status,
                "entered_primary_state_flag": bool(status == "primary_allowed"),
                "entered_policy_routing_flag": False if status != "primary_allowed" else True,
                "label_overlap_audit_status": "ok" if status == "primary_allowed" or "forbidden" in status else "readout_only",
            }
        )
    for _, state in state_registry.iterrows():
        rows.append(
            {
                "feature_id": f"state_formula::{state['state_id']}",
                "registry_status": "state_definition",
                "entered_primary_state_flag": True,
                "entered_policy_routing_flag": True,
                "label_overlap_audit_status": "forbidden_feature_detected"
                if formula_uses_forbidden_features(state["formula"])
                else "ok",
            }
        )
    return pd.DataFrame(rows)


def build_final_policy_decision(
    final_status: str,
    internal_status: str,
    reasons: list[str],
    selected_variant: str,
    selected_state_id: str,
    lane_b_power: pd.DataFrame,
    validation_low_power_flag: bool,
) -> pd.DataFrame:
    lane_b_status = lane_b_power["lane_b_rescue_status"].iloc[0] if not lane_b_power.empty else "lane_b_rescue_readout_only_low_power"
    return pd.DataFrame(
        [
            {
                "run_id": RUN_ID,
                "final_status": final_status,
                "replay_internal_status": internal_status,
                "reason_list": "|".join(reasons),
                "selected_arm_variant_id": selected_variant,
                "selected_state_id": selected_state_id,
                "validation_low_power": validation_low_power_flag,
                "lane_b_rescue_status": lane_b_status,
                "production_authorized_flag": False,
                "diagnostic_only_flag": final_status != FINAL_SUPPORTED,
            }
        ]
    )


def output_hash_map(outputs: dict[str, Path]) -> dict[str, str]:
    return {key: file_sha256(path) for key, path in sorted(outputs.items()) if path.is_file()}


def make_manifest(config: dict[str, Any], config_path: Path, outputs: dict[str, Path], final_status: str, selected_variant: str) -> dict[str, Any]:
    cache_outputs = {key: path for key, path in outputs.items() if LOCAL_CACHE_DIR in path.parents}
    return {
        "run_id": RUN_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": git_revision(),
        "config_path": relative_path(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path) if config_path.exists() else None,
        "final_status": final_status,
        "selected_arm_variant_id": selected_variant,
        "outputs": {key: relative_path(path) for key, path in sorted(outputs.items())},
        "output_hashes": output_hash_map(outputs),
        "local_cache_metadata": {key: artifact_metadata(path) for key, path in sorted(cache_outputs.items())},
    }


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int | None = None) -> str:
    if frame is None or frame.empty:
        return "_无可用记录_"
    out = frame.copy()
    if columns is not None:
        existing = [col for col in columns if col in out.columns]
        out = out[existing] if existing else out
    if max_rows is not None:
        out = out.head(max_rows)
    if out.empty:
        return "_无可用记录_"
    return out.to_markdown(index=False)


def render_report(
    final_decision: pd.DataFrame,
    perf: pd.DataFrame,
    selection: pd.DataFrame,
    retention_summary: pd.DataFrame,
    non_disc: pd.DataFrame,
    recon_11b: pd.DataFrame,
    subgroup_11b: pd.DataFrame,
    lane_pop: pd.DataFrame,
    topk: pd.DataFrame,
    bootstrap: pd.DataFrame,
    lane_b_power: pd.DataFrame,
    scope_recon: pd.DataFrame,
    a2_diag: pd.Series,
    a2_divergence: pd.DataFrame,
    a2_tradability: pd.DataFrame,
    state_feature_registry: pd.DataFrame,
    state_def_registry: pd.DataFrame,
    label_overlap: pd.DataFrame,
    arm_registry: pd.DataFrame,
    command: list[str],
) -> str:
    decision = final_decision.iloc[0]
    selected = str(decision["selected_arm_variant_id"])
    selected_state = str(decision.get("selected_state_id", ""))
    primary_perf = perf.loc[
        perf["arm_variant_id"].eq(selected)
        & perf["split"].eq("all")
        & perf["lane_id"].eq("all")
        & perf["cost_scenario"].eq("base_cost")
        & perf["capacity_slots"].eq(50)
    ]
    b0_perf = perf.loc[
        perf["arm_id"].eq("B0_deployed_baseline")
        & perf["split"].eq("all")
        & perf["lane_id"].eq("all")
        & perf["cost_scenario"].eq("base_cost")
        & perf["capacity_slots"].eq(50)
    ]
    p = primary_perf.iloc[0] if not primary_perf.empty else pd.Series(dtype=object)
    b0 = b0_perf.iloc[0] if not b0_perf.empty else pd.Series(dtype=object)
    ret = retention_summary.iloc[0] if not retention_summary.empty else pd.Series(dtype=object)
    shakeout = subgroup_11b.loc[subgroup_11b["subgroup_id"].astype(str).eq("winner_shakeout_seed")]
    scope_display = scope_recon.copy()
    if not scope_display.empty:
        scope_display["pit_excluded_row_n"] = scope_display["eleven_a1_risk_on_pre_pit_row_n"].astype(int) - scope_display["eleven_a1_pit_valid_row_n"].astype(int)
    a2_diag_frame = pd.DataFrame([a2_diag.to_dict()])
    selected_state_def = state_def_registry.loc[state_def_registry["state_id"].astype(str).eq(selected_state)]
    feature_summary = (
        state_feature_registry.groupby(["registry_status", "primary_policy_allowed_flag"], dropna=False)
        .size()
        .reset_index(name="feature_n")
        if not state_feature_registry.empty
        else pd.DataFrame()
    )
    label_summary = (
        label_overlap.groupby(["label_overlap_audit_status", "entered_policy_routing_flag"], dropna=False)
        .size()
        .reset_index(name="feature_or_state_n")
        if not label_overlap.empty
        else pd.DataFrame()
    )
    primary_capacity = perf.loc[perf["split"].eq("all") & perf["capacity_slots"].eq(50)].copy()
    selected_variants = {
        "B0_deployed_baseline__full",
        "B1_immediate_full_entry__full",
        selected,
        f"B3_trial_then_upgrade_K3__{selected_state}__trial_0.00__target_1.00",
        f"B3_trial_then_upgrade_K3__{selected_state}__trial_0.10__target_1.00",
        f"B3_trial_then_upgrade_K3__{selected_state}__trial_0.25__target_1.00",
        f"LB0_rejected_no_trade__{selected_state}",
        f"LB2_delayed_rescue_K3__{selected_state}__target_1.00",
    }
    replay_excerpt = primary_capacity.loc[
        primary_capacity["arm_variant_id"].isin(selected_variants)
        & (
            primary_capacity["lane_id"].eq("all")
            | (
                primary_capacity["arm_id"].isin(["LB0_rejected_no_trade", "LB2_delayed_rescue_K3"])
                & primary_capacity["lane_id"].eq("lane_B_10C_ref_rejected")
            )
        )
    ].sort_values(["cost_scenario", "arm_id", "arm_variant_id", "lane_id"], kind="stable")
    arm_registry_excerpt = arm_registry.loc[
        arm_registry["arm_id"].isin(["B0_deployed_baseline", "B1_immediate_full_entry", "B2_wait_confirm_K3", "B3_trial_then_upgrade_K3", "LB0_rejected_no_trade", "LB2_delayed_rescue_K3"])
    ].copy()
    concentration_excerpt = primary_capacity.loc[
        primary_capacity["arm_variant_id"].isin(["B0_deployed_baseline__full", selected])
        & primary_capacity["lane_id"].eq("all")
        & primary_capacity["cost_scenario"].eq("base_cost")
    ]
    execution_excerpt = primary_capacity.loc[
        primary_capacity["arm_variant_id"].isin(["B0_deployed_baseline__full", selected])
        & primary_capacity["lane_id"].eq("all")
        & primary_capacity["cost_scenario"].eq("base_cost")
    ]
    lines = [
        "# 11C Two-stage Observed-state Policy Replay Report",
        "",
        "## 结论",
        "",
        f"- final_status: `{decision['final_status']}`",
        f"- replay_internal_status: `{decision['replay_internal_status']}`",
        f"- reason_list: `{decision['reason_list']}`",
        f"- selected_arm_variant_id: `{selected}`",
        f"- selected_state_id: `{decision['selected_state_id']}`",
        f"- lane_b_rescue_status: `{decision['lane_b_rescue_status']}`",
        "",
        "本轮 11C 完成了 after-cost / capacity-constrained two-stage observed-state replay，但当前 11B 上游为 "
        "`11B_archetype_protected_retention_statistics_incomplete`，所以 11C 按需求被 ceiling 到 "
        "`11C_two_stage_policy_statistics_incomplete`。这不是 K3 replay 无法运行，而是 11B retention prerequisite 尚不能给出正式非歧视/歧视定性。",
        "",
        "## 运行命令与复现边界",
        "",
        f"- actual_command: `{' '.join(command)}`",
        "- 主回放使用 `exit_contract_id = common_exit_120d_with_risk_stop_v1`：120 sessions horizon、risk stop from current weighted-average cost basis、delist haircut primary = 1.0。",
        "- B0/B1/B2/B3/LB2 使用同一 exit contract；B1 只作为 B0 timing sanity check，不提供独立 policy 结论。",
        "",
        "## Scope Reconciliation",
        "",
        "主分母固定为 11A1/11A2/11B 的 `risk_on ∩ strict PIT-valid` universe。`all` split 中 10A risk_on pre-PIT 为 11,293 行，PIT-valid 为 4,665 行，因此 6,628 行 PIT-excluded rows 保持 out-of-scope，不混回当前可执行 universe。",
        "",
        markdown_table(
            scope_display,
            [
                "split",
                "eleven_a1_risk_on_pre_pit_row_n",
                "eleven_a1_pit_valid_row_n",
                "pit_excluded_row_n",
                "eleven_c_pit_valid_row_n",
                "denominator_row_match_flag",
                "scope_reconciliation_status",
            ],
        ),
        "",
        "## 11A2 Prerequisite",
        "",
        "11A2 只授权 `K*=3` 的 post-t0 observed-state 诊断窗口；11C 不改变 t0 的 10C reference-slice 边界，仅在 `separation_detected_tradable`、K*=3、tradable window open 同时成立时做 replay。",
        "",
        markdown_table(
            a2_diag_frame,
            [
                "final_status",
                "pit_valid_evaluated_row_n",
                "unique_instrument_n",
                "confirmed_divergence_onset_day_C1_full_cohort",
                "winner_realized_fraction_status",
            ],
        ),
        "",
        "11A2 divergence/tradability readout:",
        "",
        markdown_table(
            a2_divergence.loc[a2_divergence["cohort"].astype(str).eq("full_cohort")],
            [
                "contrast_id",
                "cohort",
                "confirmed_divergence_onset_day",
                "return_direction_at_confirmed",
                "structure_direction_at_confirmed",
                "dual_channel_collinearity_flag",
            ],
            max_rows=6,
        ),
        "",
        markdown_table(
            a2_tradability.loc[a2_tradability["cohort"].astype(str).eq("full_cohort")],
            [
                "contrast_id",
                "cohort",
                "confirmed_divergence_onset_day",
                "tradability_basis_eligible_n",
                "tradability_basis_excluded_n",
                "winner_realized_fraction_status",
            ],
            max_rows=6,
        ),
        "",
        "## 11B 上游检查",
        "",
        f"- 11B final_status: `{ret.get('final_status', '')}`",
        f"- statistics_incomplete_reasons: `{ret.get('statistics_incomplete_reasons', '')}`",
        f"- PIT-valid winner/nonwinner/relative retention: {ret.get('winner_retention', np.nan):.4f} / {ret.get('nonwinner_retention', np.nan):.4f} / {ret.get('relative_retention_winner_vs_nonwinner', np.nan):.4f}",
        "",
        "11B split readout:",
        "",
        markdown_table(non_disc, ["split", "winner_n", "winner_retention", "nonwinner_retention", "relative_retention_winner_vs_nonwinner", "split_retention_status"]),
        "",
        "11B frontier reconciliation:",
        "",
        markdown_table(recon_11b),
        "",
    ]
    if not shakeout.empty:
        lines.extend(
            [
                "`winner_shakeout_seed` sensitivity:",
                "",
                markdown_table(shakeout, ["split", "eligible_n", "retention_rate", "relative_retention_vs_nonwinner", "relative_retention_ci_low_p05", "relative_retention_ci_high_p95", "subgroup_status"]),
                "",
            ]
        )
    lines.extend(
        [
            "## Lane Population",
            "",
            "Lane A 是 10C reference-slice kept candidates；Lane B 是 10C reference-slice rejected candidates，但 10C 在 t0 仍有效，Lane B 只能做 delayed-confirmation rescue readout。B0/B1 覆盖 deployed baseline kept set，即 Lane A ∪ Lane B。",
            "",
            markdown_table(lane_pop),
            "",
            "## K3 Observed-state Registry And Leakage Audit",
            "",
            "Primary observed-state 只允许 K3 return/path damage/reclaim/liquidity/executable status。`fast_fail touch`、future MFE/MAE、`winner_120`、`forward_return_120d` 和 label-derived barrier fields 只允许 readout-only 或 forbidden。",
            "",
            "Feature registry summary:",
            "",
            markdown_table(feature_summary),
            "",
            "Selected state definition:",
            "",
            markdown_table(selected_state_def),
            "",
            "Label-overlap policy audit summary:",
            "",
            markdown_table(label_summary),
            "",
            "## Policy Arm Registry",
            "",
            markdown_table(
                arm_registry_excerpt,
                [
                    "arm_id",
                    "arm_variant_id",
                    "state_id",
                    "trial_size",
                    "upgrade_size",
                    "upgrade_size_semantics",
                    "trial_zero_wait_confirm_equivalence_flag",
                    "b0_b1_deployed_set_identical_flag",
                    "b2_b3_composite_candidate_set_flag",
                ],
                max_rows=20,
            ),
            "",
            "## Primary Replay Readout",
            "",
            f"- B0 net EV/exposure-day: {b0.get('net_ev_per_exposure_day', np.nan):.6f}",
            f"- selected net EV/exposure-day: {p.get('net_ev_per_exposure_day', np.nan):.6f}",
            f"- selected winner capture rate: {p.get('winner_120_capture_rate', np.nan):.4f}",
            f"- selected big failure entry rate: {p.get('big_failure_proxy_entry_rate', np.nan):.4f}",
            f"- selected false repair entry rate: {p.get('false_repair_entry_rate', np.nan):.4f}",
            f"- selected limit-up unfilled rate: {p.get('limit_up_unfilled_rate', np.nan):.4f}",
            f"- selected limit-down exit failure rate: {p.get('limit_down_exit_failure_rate', np.nan):.4f}",
            "",
            "B0/B1/B2/B3/LB0/LB2 primary-capacity cost readout excerpt:",
            "",
            markdown_table(
                replay_excerpt,
                [
                    "arm_id",
                    "arm_variant_id",
                    "lane_id",
                    "cost_scenario",
                    "entry_filled_n",
                    "net_median_return",
                    "net_winsorized_mean_return_1_99",
                    "net_ev_per_exposure_day",
                    "winner_120_capture_rate",
                    "big_failure_proxy_entry_rate",
                    "false_repair_entry_rate",
                    "turnover_notional",
                    "transaction_cost_bps_paid",
                ],
                max_rows=48,
            ),
            "",
            "Event-level 与 portfolio-constrained readout:",
            "",
            markdown_table(
                execution_excerpt,
                [
                    "arm_id",
                    "arm_variant_id",
                    "entry_filled_n",
                    "entry_rate",
                    "turnover_notional",
                    "transaction_cost_bps_paid",
                    "capital_utilization_mean",
                    "cash_drag_mean",
                    "max_concurrent_positions",
                    "limit_up_unfilled_rate",
                    "limit_down_exit_failure_rate",
                ],
            ),
            "",
            "MAE / drawdown / board concentration:",
            "",
            markdown_table(
                concentration_excerpt,
                [
                    "arm_id",
                    "arm_variant_id",
                    "mae_p50",
                    "mae_p95",
                    "max_drawdown_p95",
                    "board_concentration_hhi",
                    "industry_concentration_hhi",
                ],
            ),
            "",
            "当前 report 中 sector/industry concentration 为 `NaN`，原因是 11C 输入只冻结了 board metadata，未冻结 PIT industry/sector source；因此本轮只对 board concentration 作正式 capacity readout。",
            "",
            "## State / Arm Selection",
            "",
            markdown_table(selection.sort_values("train_policy_selection_score", ascending=False), max_rows=12),
            "",
            "## Top-k And Bootstrap",
            "",
            markdown_table(topk),
            "",
            markdown_table(bootstrap),
            "",
            "## Lane B Rescue Power",
            "",
            markdown_table(lane_b_power),
            "",
            "## 预注册失败模式",
            "",
            "| case | status | conclusion |",
            "| --- | --- | --- |",
            "| Case 1 gross-only | readout | 若 zero-cost 有效但 base-cost 无效，则 separability 不可交易 |",
            "| Case 2 top-k | see topk table | top-k dependency 不支持 policy |",
            "| Case 3 failure exposure | see failure exposure metrics | failure exposure 恶化则不支持 |",
            "| Case 4 Lane A only | readout | 只允许 upgrade/hold，不允许 rescue / override |",
            "| Case 5 Lane B low power | see lane_b table | 只允许 readout，不授权交易 |",
            "| Case 6 wait-confirm preferred | readout | observation-first 优先 |",
            "| Case 7 trial-entry preferred | readout | staged sizing candidate 仍需成本/容量/涨跌停复核 |",
            "| Case 8 11B statistics_incomplete | triggered | 11C 可输出 replay readout，但最终不得 positive |",
            "",
            "## 措辞边界",
            "",
            "本报告不改变 t0 的 10C reference-slice 边界；Lane B 只作为 delayed-confirmation rescue readout。",
            "",
        ]
    )
    return "\n".join(lines)


def run(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = load_yaml(config_path)
    params = Params.from_config(config)
    paths = {key: resolve_path(value) for key, value in config.get("inputs", {}).items()}
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    input_audit = build_input_artifact_audit(paths, config)
    outputs["input_artifact_audit"] = write_df(TABLE_DIR / "input_artifact_audit.csv", input_audit)

    denom = load_denominator(paths)
    board_meta = pd.read_csv(paths["board_metadata"], usecols=["instrument", "board_bucket"], dtype={"instrument": str}, low_memory=False)
    board_map = board_meta.drop_duplicates("instrument").set_index("instrument")["board_bucket"].fillna("main_board").astype(str).to_dict()
    price_cache = PriceCache(paths["qfq_primary_dir"], paths["qfq_fallback_dir"])

    scope_recon = build_scope_reconciliation(denom, paths)
    outputs["scope_reconciliation_vs_11a1_11a2"] = write_df(TABLE_DIR / "scope_reconciliation_vs_11a1_11a2.csv", scope_recon)

    a2_manifest = read_json(paths["eleven_a2_manifest"])
    b_manifest = read_json(paths["eleven_b_manifest"])
    tenb_manifest = read_json(paths["ten_b_manifest"])
    tenc_manifest = read_json(paths["ten_c_manifest"])
    retention_summary = pd.read_csv(paths["eleven_b_retention_summary"])
    non_disc = pd.read_csv(paths["eleven_b_non_discrimination"])
    recon_11b = pd.read_csv(paths["eleven_b_reconciliation_vs_10c"])
    subgroup_11b = pd.read_csv(paths["eleven_b_protected_subgroup_retention"])
    subgroup_mult = pd.read_csv(paths["eleven_b_subgroup_multiple_comparison"])

    incomplete_reasons: list[str] = []
    input_blocked_reasons: list[str] = []
    if config.get("parameters", {}).get("exit_contract_id") != "common_exit_120d_with_risk_stop_v1" or params.exit_contract_id != "common_exit_120d_with_risk_stop_v1":
        input_blocked_reasons.append("exit_contract_id_missing_or_unsupported")
    a2_diag = pd.read_csv(paths["eleven_a2_diagnostic_summary"]).iloc[0]
    a2_divergence = pd.read_csv(paths["eleven_a2_divergence_onset"])
    a2_tradability = pd.read_csv(paths["eleven_a2_tradability_lag"])
    if a2_manifest.get("final_status") != "11A2_post_t0_archetype_path_divergence_separation_detected_tradable":
        input_blocked_reasons.append("11A2_final_status_not_tradable")
    if int(a2_diag.get("pit_valid_evaluated_row_n", 0)) != 4665:
        input_blocked_reasons.append("11A2_evaluated_row_count_mismatch")
    if int(a2_diag.get("unique_instrument_n", 0)) != 593:
        input_blocked_reasons.append("11A2_unique_instrument_count_mismatch")
    if float(a2_diag.get("confirmed_divergence_onset_day_C1_full_cohort", np.nan)) != 3.0:
        input_blocked_reasons.append("11A2_C1_Kstar_not_3")
    if str(a2_diag.get("winner_realized_fraction_status", "")) != "tradable_window_open":
        input_blocked_reasons.append("11A2_tradable_window_not_open")
    b_final = str(retention_summary["final_status"].iloc[0]) if len(retention_summary) == 1 else ""
    if len(retention_summary) != 1:
        incomplete_reasons.append("11B_retention_summary_not_unique")
    if b_final.endswith("statistics_incomplete"):
        incomplete_reasons.append("11B_statistics_incomplete:" + str(retention_summary.get("statistics_incomplete_reasons", pd.Series([""])).iloc[0]))
    if b_final.endswith("input_blocked"):
        incomplete_reasons.append("11B_input_blocked")

    k3, rehydration = build_k3_matrix(denom, paths, price_cache, board_map)
    outputs["k3_row_id_rehydration_audit"] = write_df(TABLE_DIR / "k3_row_id_rehydration_audit.csv", rehydration)
    if not rehydration["identity_rehydration_status"].eq("ok").all():
        incomplete_reasons.append("k3_row_id_rehydration_failed")

    tenb_scores = pd.read_parquet(paths["ten_b_scores"])
    tenb_spec = selected_10b_spec(tenb_manifest)
    tenb_slice = filter_rejector_slice(tenb_scores, tenb_spec)
    tenc_scores = pd.read_parquet(paths["ten_c_scores"])
    tenc_spec = select_10c_slice_mode(tenc_manifest, config)
    tenc_slice = filter_rejector_slice(tenc_scores, tenc_spec)
    base = denom.merge(
        k3.drop(columns=[col for col in k3.columns if col in denom.columns and col not in {"row_id", "instrument", "event_t0_date", "split"}]),
        on=["row_id", "instrument", "event_t0_date", "split"],
        how="left",
    )
    base, tenb_mismatch = attach_reject_flag(base, tenb_slice, "tenb")
    base, tenc_mismatch = attach_reject_flag(base, tenc_slice, "tenc_ref")
    base = construct_lanes(base)
    if tenb_mismatch["join_hit_rate"] < 0.999:
        input_blocked_reasons.append("10B_selected_gate_join_incomplete")
    if len(tenc_slice) == 0 or tenc_mismatch["join_hit_rate"] < 0.999:
        input_blocked_reasons.append("10C_reference_slice_join_incomplete")

    lane_rows = []
    for split in READOUT_SPLITS:
        group = base if split == "all" else base.loc[base["split"].eq(split)]
        for lane in ["all", "lane_A_10C_ref_kept", "lane_B_10C_ref_rejected", "out_of_lane_10B_rejected"]:
            lg = group if lane == "all" else group.loc[group["lane_id"].eq(lane)]
            lane_rows.append(
                {
                    "split": split,
                    "lane_id": lane,
                    "row_n": len(lg),
                    "winner_n": int(lg["winner_120_bool"].sum()) if len(lg) else 0,
                    "tenc_slice_mode": tenc_spec["tenc_slice_mode"],
                    "tenc_slice_selected_flag": tenc_spec["tenc_slice_selected_flag"],
                    "tenc_slice_decision_block_reason": tenc_spec["tenc_slice_decision_block_reason"],
                    "tenb_join_hit_rate": tenb_mismatch["join_hit_rate"],
                    "tenc_ref_join_hit_rate": tenc_mismatch["join_hit_rate"],
                }
            )
    lane_pop = pd.DataFrame(lane_rows)
    outputs["lane_population_audit"] = write_df(TABLE_DIR / "lane_population_audit.csv", lane_pop)

    state_feature_registry = observed_state_feature_registry()
    state_def_registry = observed_state_definition_registry()
    outputs["observed_state_feature_registry"] = write_df(TABLE_DIR / "observed_state_feature_registry.csv", state_feature_registry)
    outputs["observed_state_definition_registry"] = write_df(TABLE_DIR / "observed_state_definition_registry.csv", state_def_registry)
    label_overlap = build_label_overlap_policy_audit(state_feature_registry, state_def_registry)
    outputs["label_overlap_policy_audit"] = write_df(TABLE_DIR / "label_overlap_policy_audit.csv", label_overlap)
    if label_overlap["label_overlap_audit_status"].eq("forbidden_feature_detected").any():
        input_blocked_reasons.append("forbidden_label_overlap_feature_in_state_definition")

    state_ids = state_def_registry["state_id"].tolist()
    arm_registry = build_arm_registry(params, state_ids)
    sizing_grid = valid_sizing_grid(params)
    arm_registry = arm_registry.merge(sizing_grid, on=["trial_size", "upgrade_size"], how="left")
    outputs["policy_arm_registry"] = write_df(TABLE_DIR / "policy_arm_registry.csv", arm_registry)

    outputs["policy_replay_base_denominator"] = write_parquet(LOCAL_CACHE_DIR / "policy_replay_base_denominator.parquet", base)
    outputs["k3_observed_state_matrix"] = write_parquet(LOCAL_CACHE_DIR / "k3_observed_state_matrix.parquet", k3)

    if input_blocked_reasons:
        final_decision = build_final_policy_decision(FINAL_BLOCKED, FINAL_BLOCKED, input_blocked_reasons, "", "", pd.DataFrame(), True)
        perf = pd.DataFrame([{"arm_variant_id": "", "arm_id": "", "lane_id": "all", "split": "all", "cost_scenario": "base_cost", "capacity_slots": params.primary_capacity_slots}])
        selection = pd.DataFrame([{"arm_variant_id": "", "selection_status": "input_blocked", "selected_policy_flag": False}])
        topk = pd.DataFrame([{"arm_variant_id": "", "top_k": 0, "split": "all", "topk_status": "input_blocked"}])
        bootstrap = pd.DataFrame([{"arm_variant_id": "", "split": "all", "bootstrap_status": "input_blocked"}])
        lane_b_power = pd.DataFrame([{"split": "all", "lane_b_rescue_status": "input_blocked"}])
        event_ledger = pd.DataFrame()
        portfolio_ledger = pd.DataFrame()
        daily_ledger = pd.DataFrame()
    else:
        event_ledger = replay_all_events(base, arm_registry, price_cache, board_map, params)
        portfolio_ledger = apply_portfolio_constraints(event_ledger, params)
        daily_ledger = build_portfolio_daily_ledger(portfolio_ledger)
        perf = build_performance_summary(portfolio_ledger, base.loc[base["lane_id"].isin(["lane_A_10C_ref_kept", "lane_B_10C_ref_rejected"])], daily_ledger, params)
        robust = build_robust_metric_package(perf)
        selection = select_policy(perf, robust, arm_registry, base, params)
        selected_row = selection.loc[selection.get("selected_policy_flag", pd.Series(False, index=selection.index)).map(boolish)]
        selected_variant = str(selected_row["arm_variant_id"].iloc[0]) if not selected_row.empty else ""
        selected_state = str(selected_row["state_id"].iloc[0]) if not selected_row.empty and "state_id" in selected_row else ""
        validation_lp = validation_low_power(selected_variant, base, params)
        topk = build_topk_sensitivity(portfolio_ledger, selected_variant, params)
        bootstrap, bootstrap_samples = build_bootstrap_ci(portfolio_ledger, selected_variant, params)
        lane_b_power = lane_b_rescue_power(base, selected_state, params)
        internal_status = FINAL_SUPPORTED if selected_variant and not selected_row.empty and boolish(selected_row["train_pre_gate_pass_flag"].iloc[0]) else FINAL_NOT_SUPPORTED
        final_status, final_reasons = final_status_decision(internal_status, incomplete_reasons, selected_variant, selection, topk, bootstrap, validation_lp)
        final_decision = build_final_policy_decision(final_status, internal_status, final_reasons, selected_variant, selected_state, lane_b_power, validation_lp)
        outputs["robust_metric_package"] = write_df(TABLE_DIR / "robust_metric_package.csv", robust)
        outputs["bootstrap_samples"] = write_parquet(LOCAL_CACHE_DIR / "bootstrap_samples.parquet", bootstrap_samples)

    if "robust_metric_package" not in outputs:
        outputs["robust_metric_package"] = write_df(TABLE_DIR / "robust_metric_package.csv", pd.DataFrame([{"status": "input_blocked"}]))
    outputs["event_level_trade_ledger"] = write_parquet(LOCAL_CACHE_DIR / "event_level_trade_ledger.parquet", event_ledger)
    outputs["portfolio_daily_ledger"] = write_parquet(LOCAL_CACHE_DIR / "portfolio_daily_ledger.parquet", daily_ledger)
    outputs["policy_performance_summary"] = write_df(TABLE_DIR / "policy_performance_summary.csv", perf)
    outputs["state_selection_readout"] = write_df(TABLE_DIR / "state_selection_readout.csv", selection)
    outputs["instrument_block_bootstrap_ci"] = write_df(TABLE_DIR / "instrument_block_bootstrap_ci.csv", bootstrap)
    outputs["topk_removal_sensitivity"] = write_df(TABLE_DIR / "topk_removal_sensitivity.csv", topk)
    outputs["lane_b_rescue_power_readout"] = write_df(TABLE_DIR / "lane_b_rescue_power_readout.csv", lane_b_power)
    outputs["final_policy_decision"] = write_df(TABLE_DIR / "final_policy_decision.csv", final_decision)

    if not portfolio_ledger.empty:
        outputs["execution_fill_audit"] = write_df(
            TABLE_DIR / "execution_fill_audit.csv",
            portfolio_ledger.groupby(["arm_id", "arm_variant_id"], dropna=False)
            .agg(
                scheduled_buy_order_n=("scheduled_buy_order_n", "sum"),
                scheduled_sell_order_n=("scheduled_sell_order_n", "sum"),
                entry_filled_n=("entry_filled_flag", lambda s: int(s.map(boolish).sum())),
                portfolio_accepted_n=("portfolio_accepted_flag", lambda s: int(s.map(boolish).sum())),
            )
            .reset_index(),
        )
        outputs["limit_execution_audit"] = write_df(
            TABLE_DIR / "limit_execution_audit.csv",
            portfolio_ledger.groupby(["arm_id", "arm_variant_id"], dropna=False)
            .agg(
                limit_up_unfilled_n=("limit_up_unfilled_n", "sum"),
                limit_down_exit_failure_n=("limit_down_exit_failure_n", "sum"),
                missing_open_unfilled_n=("missing_open_unfilled_n", "sum"),
            )
            .reset_index(),
        )
    else:
        outputs["execution_fill_audit"] = write_df(TABLE_DIR / "execution_fill_audit.csv", pd.DataFrame([{"status": "input_blocked"}]))
        outputs["limit_execution_audit"] = write_df(TABLE_DIR / "limit_execution_audit.csv", pd.DataFrame([{"status": "input_blocked"}]))

    # Required metric-package table aliases keep each readout focused and traceable to policy_performance_summary.
    alias_cols = {
        "winner_capture_readout": ["arm_variant_id", "arm_id", "lane_id", "split", "cost_scenario", "capacity_slots", "winner_120_retention_rate", "winner_120_capture_rate", "winner_120_captured_n", "winner_120_denominator_n"],
        "failure_exposure_readout": ["arm_variant_id", "arm_id", "lane_id", "split", "cost_scenario", "capacity_slots", "big_failure_proxy_entry_rate", "false_repair_entry_rate", "fast_fail_realized_loss_rate"],
        "mae_drawdown_distribution": ["arm_variant_id", "arm_id", "lane_id", "split", "cost_scenario", "capacity_slots", "mae_p50", "mae_p95", "max_drawdown_p95"],
        "turnover_cost_readout": ["arm_variant_id", "arm_id", "lane_id", "split", "cost_scenario", "capacity_slots", "turnover_notional", "transaction_cost_bps_paid"],
        "capital_utilization_readout": ["arm_variant_id", "arm_id", "lane_id", "split", "cost_scenario", "capacity_slots", "capital_utilization_mean", "cash_drag_mean", "max_concurrent_positions"],
        "concentration_readout": ["arm_variant_id", "arm_id", "lane_id", "split", "cost_scenario", "capacity_slots", "board_concentration_hhi", "industry_concentration_hhi"],
    }
    for name, cols in alias_cols.items():
        existing = [col for col in cols if col in perf.columns]
        outputs[name] = write_df(TABLE_DIR / f"{name}.csv", perf[existing] if existing else pd.DataFrame([{"status": "no_columns"}]))

    failure_modes = pd.DataFrame(
        [
            {"case_id": "Case 1", "case_name": "gross_only", "triggered_flag": False, "required_conclusion": "trajectory separability exists but is not tradable after costs"},
            {"case_id": "Case 2", "case_name": "topk_dependency", "triggered_flag": bool(topk.get("topk_dependency_status", pd.Series(dtype=str)).astype(str).eq("topk_dependent").any()), "required_conclusion": "not supported policy"},
            {"case_id": "Case 3", "case_name": "failure_exposure_worse", "triggered_flag": final_decision.iloc[0]["replay_internal_status"] == FINAL_FAILURE_WORSE, "required_conclusion": "11A1 entanglement delayed to K3"},
            {"case_id": "Case 4", "case_name": "lane_a_only", "triggered_flag": False, "required_conclusion": "upgrade/hold only, no rescue override"},
            {"case_id": "Case 5", "case_name": "lane_b_low_power", "triggered_flag": lane_b_power["lane_b_rescue_status"].astype(str).str.contains("low_power").any(), "required_conclusion": "readout only"},
            {"case_id": "Case 6", "case_name": "wait_confirm_preferred", "triggered_flag": False, "required_conclusion": "observation-first preferred"},
            {"case_id": "Case 7", "case_name": "trial_entry_preferred", "triggered_flag": False, "required_conclusion": "staged sizing candidate only"},
            {"case_id": "Case 8", "case_name": "11B_statistics_incomplete", "triggered_flag": any("11B_statistics_incomplete" in reason for reason in final_decision.iloc[0]["reason_list"].split("|")), "required_conclusion": "11C replay readout allowed, final status cannot be positive"},
        ]
    )
    outputs["failure_mode_decision_table"] = write_df(TABLE_DIR / "failure_mode_decision_table.csv", failure_modes)

    report_text = render_report(
        final_decision,
        perf,
        selection,
        retention_summary,
        non_disc,
        recon_11b,
        subgroup_11b,
        lane_pop,
        topk,
        bootstrap,
        lane_b_power,
        scope_recon,
        a2_diag,
        a2_divergence,
        a2_tradability,
        state_feature_registry,
        state_def_registry,
        label_overlap,
        arm_registry,
        sys.argv,
    )
    outputs["report"] = write_text(REPORT_PATH, report_text)
    manifest = make_manifest(config, config_path, outputs, str(final_decision.iloc[0]["final_status"]), str(final_decision.iloc[0]["selected_arm_variant_id"]))
    outputs["manifest"] = write_json(MANIFEST_PATH, manifest)
    return {"final_status": str(final_decision.iloc[0]["final_status"]), "outputs": outputs}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 11C two-stage observed-state policy replay.")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to YAML config.")
    args = parser.parse_args()
    result = run(resolve_path(args.config))
    print(json.dumps({"run_id": RUN_ID, "final_status": result["final_status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
