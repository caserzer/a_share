from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from afml_big_winner.config import stable_hash
from afml_big_winner.manifest import file_sha256


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PENDING_DIR = EXPERIMENT_DIR.parent
PIPELINE_04_PATH = (
    PENDING_DIR / "04_high_recall_repair_event_candidate_generator_v0" / "code" / "pipeline.py"
)

CHANNEL_E0 = "E0_setup_context"
CHANNEL_E1 = "E1_early_ema60_repair"
CHANNEL_E2 = "E2_money_vwap_repair_confirmation"
CHANNEL_E3 = "E3_rank_persistence"
CHANNEL_E6 = "E6_continuation_discriminator"
UNION_FAMILY = "recommended_union"
CANONICAL_SCOPE = "canonical_event"
INSTANCE_SCOPE = "event_instance"
UNION_EVENT_FAMILY = "E_union_topn_multichannel_recommended"

DECISION_INPUT_BLOCKED = "topn_multichannel_candidate_generator_input_blocked"
DECISION_TOTAL_RECALL_BLOCKED = "topn_multichannel_candidate_generator_total_recall_blocked"
DECISION_SPLIT_RECALL_BLOCKED = "topn_multichannel_candidate_generator_split_recall_blocked"
DECISION_DENSITY_BLOCKED = "topn_multichannel_candidate_generator_density_blocked"
DECISION_EXECUTION_LABEL_BLOCKED = (
    "topn_multichannel_candidate_generator_execution_label_blocked"
)
DECISION_RECALL_ONLY = (
    "topn_multichannel_candidate_generator_supported_recall_only_precision_unproven"
)
DECISION_HIGH_RECALL = "topn_multichannel_candidate_generator_supported_high_recall"
DECISION_DIAGNOSTIC_ONLY = "topn_multichannel_candidate_generator_diagnostic_only"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_p04 = _load_module("afml_bw_04_pipeline_for_07", PIPELINE_04_PATH)

NOT_MISSING = _p04.NOT_MISSING
CENSORED_INCOMPLETE_HORIZON = _p04.CENSORED_INCOMPLETE_HORIZON
NON_EXECUTABLE_NEXT_OPEN = _p04.NON_EXECUTABLE_NEXT_OPEN


@dataclass(frozen=True)
class SplitConfig:
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    robustness_start: str
    latest_main_label_complete_t0_date: str
    latest_120d_outcome_complete_t0_date: str


@dataclass(frozen=True)
class LabelConfig:
    confirm_horizon: int
    confirm_upper: float
    confirm_lower: float
    failure_horizon: int
    failure_lower: float
    continuous_horizons: tuple[int, ...]
    big_winner_mfe_120d: float
    super_winner_mfe_120d: float
    near_winner_mfe_lower: float
    near_winner_mfe_upper: float
    false_repair_drawdown: float


@dataclass(frozen=True)
class InputStatus:
    input_gate_status: str
    input_gate_failure_reason: str
    upstream_05_decision: str
    upstream_06_decision: str
    topn_candidate_gap_accepted: bool
    universe_precision_status: str
    latest_label_complete_low_date: str
    source_gap_count: int
    active_source_gap_count: int
    old_04_density_baseline_source: str
    old_04_setup_inclusive_events_per_instrument_year_mean: float
    old_04_setup_inclusive_events_per_instrument_year_p95: float
    old_04_reclaim_based_events_per_instrument_year_mean: float
    old_04_reclaim_based_events_per_instrument_year_p95: float


def topic_path(relative_or_absolute: str | Path) -> Path:
    path = Path(relative_or_absolute)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def git_revision(cwd: Path = PROJECT_ROOT) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def date_str(value: Any) -> str:
    return _p04.date_str(value)


def safe_rate(success: int | float, total: int | float) -> float:
    if total is None or pd.isna(total) or float(total) == 0:
        return np.nan
    return float(success) / float(total)


def safe_mean(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.mean()) if len(clean) else np.nan


def safe_pctl(values: pd.Series, q: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.quantile(q)) if len(clean) else np.nan


def ensure_dirs(paths: list[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def write_dataframe(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def latest_complete_t0_date(calendar: list[str], horizon_sessions: int) -> str:
    sessions = sorted(date_str(value) for value in calendar)
    if len(sessions) <= horizon_sessions:
        raise ValueError("calendar is shorter than requested horizon")
    return sessions[-horizon_sessions - 1]


def split_for_date(value: Any, split: SplitConfig, *, label_horizon_120: bool = False) -> str:
    text = date_str(value)
    if split.train_start <= text <= split.train_end:
        return "train"
    if split.validation_start <= text <= split.validation_end:
        return "validation"
    robustness_end = (
        split.latest_120d_outcome_complete_t0_date
        if label_horizon_120
        else split.latest_main_label_complete_t0_date
    )
    if split.robustness_start <= text <= robustness_end:
        return "robustness"
    return "outside_split"


def split_series_for_dates(dates: pd.Series, split: SplitConfig) -> pd.Series:
    text = dates.astype(str)
    out = pd.Series("outside_split", index=dates.index, dtype="object")
    out.loc[(text >= split.train_start) & (text <= split.train_end)] = "train"
    out.loc[(text >= split.validation_start) & (text <= split.validation_end)] = "validation"
    out.loc[
        (text >= split.robustness_start)
        & (text <= split.latest_120d_outcome_complete_t0_date)
    ] = "robustness"
    return out


def add_topn_evaluated_universe_flags(
    universe: pd.DataFrame,
    split: SplitConfig,
    config: dict[str, Any],
) -> pd.DataFrame:
    out = universe.copy()
    for column in ["usable_trade_date", "source_membership_date"]:
        if column in out.columns:
            out[column] = pd.to_datetime(out[column], errors="coerce").dt.strftime("%Y-%m-%d")
    expected_available = out["source_membership_date"].astype(str) + " close"
    out["pit_clock_valid"] = (
        out["source_membership_date"].astype(str) < out["usable_trade_date"].astype(str)
    ) & (out["membership_available_time"].astype(str) == expected_available)
    observed = pd.to_numeric(
        out["history_observed_sessions_before_usable_date"], errors="coerce"
    )
    out["history_ready_250d_flag"] = observed >= int(
        config["event_generation"]["prior_lookback_sessions"]
    )
    out["label_complete_120d_flag"] = (
        out["usable_trade_date"].astype(str)
        <= split.latest_120d_outcome_complete_t0_date
    )
    out["split"] = split_series_for_dates(out["usable_trade_date"], split)
    out["evaluated_flag"] = (
        out["pit_clock_valid"].fillna(False).astype(bool)
        & out["history_ready_250d_flag"].fillna(False).astype(bool)
        & out["label_complete_120d_flag"].fillna(False).astype(bool)
        & (out["split"] != "outside_split")
    )
    return out


def validate_config(config: dict[str, Any]) -> None:
    required_sections = {
        "experiment",
        "paths",
        "outputs",
        "splits",
        "event_generation",
        "quality_flags",
        "channels",
        "density",
        "labels",
        "gates",
    }
    missing = required_sections.difference(config)
    if missing:
        raise ValueError(f"config missing sections: {sorted(missing)}")
    for key in [
        "stock_daily_csv_dir",
        "benchmark_daily_csv",
        "topn_executable_universe_csv",
        "topn_membership_universe_csv",
        "upstream_05_run_manifest_json",
        "upstream_05_data_source_coverage_audit_csv",
        "upstream_06_run_manifest_json",
        "upstream_06_episode_reference_parquet",
        "upstream_06_denominator_summary_csv",
        "upstream_04_run_manifest_json",
        "upstream_04_event_density_audit_csv",
    ]:
        path = topic_path(config["paths"][key])
        if not path.exists():
            raise FileNotFoundError(f"missing path {key}: {path}")


def parse_label_config(config: dict[str, Any]) -> LabelConfig:
    labels = config["labels"]
    return LabelConfig(
        confirm_horizon=int(labels["confirm_20"]["horizon_days"]),
        confirm_upper=float(labels["confirm_20"]["upper_barrier"]),
        confirm_lower=float(labels["confirm_20"]["lower_barrier"]),
        failure_horizon=int(labels["failure_10"]["horizon_days"]),
        failure_lower=float(labels["failure_10"]["lower_barrier"]),
        continuous_horizons=tuple(int(v) for v in labels["continuous_horizons"]),
        big_winner_mfe_120d=float(labels["big_winner_mfe_120d"]),
        super_winner_mfe_120d=float(labels["super_winner_mfe_120d"]),
        near_winner_mfe_lower=float(labels["near_winner_mfe_lower"]),
        near_winner_mfe_upper=float(labels["near_winner_mfe_upper"]),
        false_repair_drawdown=float(labels["false_repair_drawdown"]),
    )


def parse_split_config(
    config: dict[str, Any],
    benchmark_daily: pd.DataFrame,
    *,
    latest_label_complete_low_date: str | None = None,
) -> SplitConfig:
    label_cfg = parse_label_config(config)
    calendar = (
        benchmark_daily.loc[benchmark_daily["index_alias"] == "all_a", "trade_date"]
        .dropna()
        .map(date_str)
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    raw = config["splits"]
    return SplitConfig(
        train_start=raw["train_start"],
        train_end=raw["train_end"],
        validation_start=raw["validation_start"],
        validation_end=raw["validation_end"],
        robustness_start=raw["robustness_start"],
        latest_main_label_complete_t0_date=(
            latest_label_complete_low_date
            if latest_label_complete_low_date
            else latest_complete_t0_date(calendar, label_cfg.confirm_horizon)
        ),
        latest_120d_outcome_complete_t0_date=(
            latest_label_complete_low_date
            if latest_label_complete_low_date
            else latest_complete_t0_date(calendar, 120)
        ),
    )


def load_old_04_density_baseline(config: dict[str, Any]) -> dict[str, Any]:
    manifest_path = topic_path(config["paths"]["upstream_04_run_manifest_json"])
    density_path = topic_path(config["paths"]["upstream_04_event_density_audit_csv"])
    baseline = {
        "old_04_density_baseline_source": "unavailable",
        "old_04_setup_inclusive_events_per_instrument_year_mean": np.nan,
        "old_04_setup_inclusive_events_per_instrument_year_p95": np.nan,
        "old_04_reclaim_based_events_per_instrument_year_mean": np.nan,
        "old_04_reclaim_based_events_per_instrument_year_p95": np.nan,
    }
    if manifest_path.is_file():
        manifest = load_json(manifest_path)
        gate = manifest.get("gate_summary", {}) or {}
        baseline.update(
            {
                "old_04_density_baseline_source": "04_manifest_gate_summary",
                "old_04_setup_inclusive_events_per_instrument_year_mean": float(
                    gate.get("setup_inclusive_events_per_instrument_year_mean", np.nan)
                ),
                "old_04_setup_inclusive_events_per_instrument_year_p95": float(
                    gate.get("setup_inclusive_events_per_instrument_year_p95", np.nan)
                ),
                "old_04_reclaim_based_events_per_instrument_year_mean": float(
                    gate.get("reclaim_based_events_per_instrument_year_mean", np.nan)
                ),
                "old_04_reclaim_based_events_per_instrument_year_p95": float(
                    gate.get("reclaim_based_events_per_instrument_year_p95", np.nan)
                ),
            }
        )
    if density_path.is_file():
        baseline["old_04_event_density_audit_hash"] = file_sha256(density_path)
    return baseline


def validate_input_status(config: dict[str, Any]) -> InputStatus:
    m05 = load_json(topic_path(config["paths"]["upstream_05_run_manifest_json"]))
    m06 = load_json(topic_path(config["paths"]["upstream_06_run_manifest_json"]))
    gate05 = m05.get("gate_summary", {}) or {}
    old04 = load_old_04_density_baseline(config)
    upstream_05_decision = str(m05.get("decision", ""))
    upstream_06_decision = str(m06.get("decision", ""))
    topn_candidate_gap_accepted = bool(m06.get("topn_candidate_gap_accepted", False))
    universe_precision_status = str(m06.get("universe_precision_status", ""))
    latest_label_complete_low_date = str(m06.get("latest_label_complete_low_date", "") or "")
    failures: list[str] = []
    if upstream_06_decision != "topn_reverse_lifecycle_sequence_supported_universal_dominance":
        failures.append("upstream_06_decision_not_supported")
    if not latest_label_complete_low_date:
        failures.append("upstream_06_latest_label_complete_low_date_missing")
    if upstream_05_decision == "topn_universe_candidate_panel_blocked":
        if not topn_candidate_gap_accepted:
            failures.append("05_blocked_without_06_gap_acceptance")
        if universe_precision_status != "available_source_topn_candidate_gap":
            failures.append("05_blocked_without_06_available_source_caveat")
    elif upstream_05_decision != "topn_universe_supported":
        failures.append(f"unsupported_05_decision:{upstream_05_decision}")
    return InputStatus(
        input_gate_status="pass" if not failures else "blocked",
        input_gate_failure_reason=";".join(failures),
        upstream_05_decision=upstream_05_decision,
        upstream_06_decision=upstream_06_decision,
        topn_candidate_gap_accepted=topn_candidate_gap_accepted,
        universe_precision_status=universe_precision_status,
        latest_label_complete_low_date=latest_label_complete_low_date,
        source_gap_count=int(gate05.get("source_gap_count", 0) or 0),
        active_source_gap_count=int(gate05.get("active_source_gap_count", 0) or 0),
        old_04_density_baseline_source=str(old04["old_04_density_baseline_source"]),
        old_04_setup_inclusive_events_per_instrument_year_mean=float(
            old04["old_04_setup_inclusive_events_per_instrument_year_mean"]
        ),
        old_04_setup_inclusive_events_per_instrument_year_p95=float(
            old04["old_04_setup_inclusive_events_per_instrument_year_p95"]
        ),
        old_04_reclaim_based_events_per_instrument_year_mean=float(
            old04["old_04_reclaim_based_events_per_instrument_year_mean"]
        ),
        old_04_reclaim_based_events_per_instrument_year_p95=float(
            old04["old_04_reclaim_based_events_per_instrument_year_p95"]
        ),
    )


def make_event_config(config: dict[str, Any]) -> Any:
    event = config["event_generation"]
    return _p04.EventConfig(
        prior_lookback_sessions=int(event["prior_lookback_sessions"]),
        seed_low_lookback_sessions=int(event["seed_low_lookback_sessions"]),
        anchor_search_horizon_sessions=int(event["anchor_search_horizon_sessions"]),
        e2_quality_window=int(event["e2_quality_window"]),
        e4_relative_strength_window=int(event["e6_continuation_window"]),
        e3_false_repair_drawdown=float(event["false_repair_drawdown"]),
        e3_variants=(5, 10),
    )


def event_priority(channel: str, config: dict[str, Any]) -> int:
    order = list(config["channels"].get("primary_channel_order", []))
    if channel == CHANNEL_E0:
        return 0
    return order.index(channel) + 1 if channel in order else 99


def channel_row(
    *,
    instrument: str,
    daily: pd.DataFrame,
    membership: pd.DataFrame,
    channel: str,
    pos: int,
    split: str,
    config: dict[str, Any],
    source_seed_low_pos: int = -1,
    first_reclaim_pos: int = -1,
    seed_cluster_id: str = "",
    reclaim_cluster_id: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = _p04.make_raw_event_row(
        instrument=instrument,
        daily=daily,
        membership=membership,
        event_family=channel,
        event_t0_pos=pos,
        source_seed_low_pos=source_seed_low_pos,
        first_reclaim_pos=first_reclaim_pos,
        seed_cluster_id=seed_cluster_id,
        reclaim_cluster_id=reclaim_cluster_id,
        event_split=split,
        quality_cfg=config["quality_flags"],
        priority=event_priority(channel, config),
        extra=extra or {},
    )
    base["channel_id"] = channel
    base["channel_family"] = channel
    base["is_setup_context"] = channel == CHANNEL_E0
    base["recommended_union_included"] = channel in set(config["channels"]["recommended"])
    base["canonical_event_scope"] = INSTANCE_SCOPE
    base["event_executable_date"] = base.get("trade_open_date", "")
    base["symbol"] = instrument
    return base


def rank_persistence_pos(
    daily: pd.DataFrame,
    reclaim_pos: int,
    config: dict[str, Any],
) -> int | None:
    event = config["event_generation"]
    window = int(event["e3_rank_persistence_window"])
    end = reclaim_pos + window
    if reclaim_pos < 0 or end >= len(daily):
        return None
    segment = daily.loc[reclaim_pos + 1 : end].copy()
    if segment.empty:
        return None
    rs = pd.to_numeric(segment.get("stock_vs_market_20d"), errors="coerce")
    ema = pd.to_numeric(segment.get("close_to_ema60"), errors="coerce")
    valid = rs.notna() & ema.notna()
    if not bool(valid.any()):
        return None
    state = (rs >= float(event["e3_rank_persistence_floor"])) & (ema >= 0.0) & valid
    if safe_rate(int(state.sum()), int(valid.sum())) >= float(
        event["e3_rank_persistence_coverage"]
    ):
        return end
    return None


def continuation_pos(
    daily: pd.DataFrame,
    reclaim_pos: int,
    config: dict[str, Any],
) -> int | None:
    event = config["event_generation"]
    start = reclaim_pos + int(event["e6_min_days_after_reclaim"])
    end = min(len(daily) - 1, reclaim_pos + int(event["e6_continuation_window"]))
    if start < 0 or end < start:
        return None
    for pos in range(start, end + 1):
        if not _p04.no_false_repair_between(
            daily,
            reclaim_pos=reclaim_pos,
            horizon=min(pos - reclaim_pos, 10),
            drawdown=float(event["false_repair_drawdown"]),
        ):
            continue
        rs = daily.at[pos, "stock_vs_market_20d"] if "stock_vs_market_20d" in daily else np.nan
        ema = daily.at[pos, "close_to_ema60"] if "close_to_ema60" in daily else np.nan
        amount = daily.at[pos, "amount_ratio_20d"] if "amount_ratio_20d" in daily else np.nan
        close_pos = (
            daily.at[pos, "close_position_in_range"]
            if "close_position_in_range" in daily
            else np.nan
        )
        if pd.isna(rs) or pd.isna(ema):
            continue
        quality = (
            (pd.notna(amount) and float(amount) >= float(event["e6_amount_ratio_20d"]))
            or (
                pd.notna(close_pos)
                and float(close_pos) >= float(event["e6_close_position_in_range"])
            )
        )
        if (
            float(rs) >= float(event["e6_stock_vs_market_20d"])
            and float(ema) >= 0.0
            and quality
        ):
            return pos
    return None


def generate_events_for_instrument(
    *,
    instrument: str,
    daily: pd.DataFrame,
    membership: pd.DataFrame,
    split_config: SplitConfig,
    config: dict[str, Any],
) -> pd.DataFrame:
    membership_dates = set(membership["usable_trade_date"].astype(str))
    if not membership_dates:
        return pd.DataFrame()
    event_cfg = make_event_config(config)
    seed_params = _p04.observable_seed_params(event_cfg)
    density_params = _p04._observable.DensityParams(
        seed_density_window=int(config["density"]["seed_density_window"]),
        reclaim_density_window=int(config["density"]["reclaim_density_window"]),
        event_density_window=1,
    )
    seeds = _p04._observable.extract_candidate_seed_lows(
        daily, membership_dates=membership_dates, params=seed_params
    )
    if not seeds.empty:
        seeds = _p04._observable.apply_position_density(
            seeds,
            pos_col="candidate_seed_low_pos",
            date_col="candidate_seed_low_date",
            cluster_col="seed_cluster_id",
            stage="seed",
            window=density_params.seed_density_window,
        )
    reclaims = _p04._observable.build_reclaim_rows(
        instrument, daily, seeds, params=seed_params, density_params=density_params
    )
    rows: list[dict[str, Any]] = []
    for seed in seeds.to_dict("records"):
        split = split_for_date(seed["candidate_seed_low_date"], split_config)
        if split == "outside_split":
            continue
        rows.append(
            channel_row(
                instrument=instrument,
                daily=daily,
                membership=membership,
                channel=CHANNEL_E0,
                pos=int(seed["candidate_seed_low_pos"]),
                source_seed_low_pos=int(seed["candidate_seed_low_pos"]),
                seed_cluster_id=str(seed.get("seed_cluster_id", "")),
                split=split,
                config=config,
                extra={"setup_context_density_kept": bool(seed.get("density_kept", False))},
            )
        )
    if reclaims.empty:
        return pd.DataFrame(rows)
    present = reclaims.loc[
        reclaims.get("first_ema60_reclaim_missing_reason", pd.Series(dtype=str))
        == NOT_MISSING
    ].copy()
    for reclaim in present.to_dict("records"):
        r0 = int(reclaim["first_ema60_reclaim_pos"])
        seed_pos = int(reclaim["candidate_seed_low_pos"])
        reclaim_date = str(reclaim["first_ema60_reclaim_date"])
        split = split_for_date(reclaim_date, split_config)
        if split != "outside_split" and reclaim_date in membership_dates:
            rows.append(
                channel_row(
                    instrument=instrument,
                    daily=daily,
                    membership=membership,
                    channel=CHANNEL_E1,
                    pos=r0,
                    source_seed_low_pos=seed_pos,
                    first_reclaim_pos=r0,
                    seed_cluster_id=str(reclaim.get("seed_cluster_id", "")),
                    reclaim_cluster_id=str(reclaim.get("reclaim_cluster_id", "")),
                    split=split,
                    config=config,
                    extra={"reclaim_density_kept": bool(reclaim.get("density_kept", False))},
                )
            )
        if bool(reclaim.get("density_kept", False)):
            e2_pos, e2_flags = _p04.first_quality_pos(
                daily,
                start_pos=r0,
                end_pos=r0 + int(config["event_generation"]["e2_quality_window"]),
                quality_cfg=config["quality_flags"],
            )
            if e2_pos is not None:
                event_date = str(daily.at[e2_pos, "date"])
                split = split_for_date(event_date, split_config)
                if split != "outside_split" and event_date in membership_dates:
                    rows.append(
                        channel_row(
                            instrument=instrument,
                            daily=daily,
                            membership=membership,
                            channel=CHANNEL_E2,
                            pos=e2_pos,
                            source_seed_low_pos=seed_pos,
                            first_reclaim_pos=r0,
                            seed_cluster_id=str(reclaim.get("seed_cluster_id", "")),
                            reclaim_cluster_id=str(reclaim.get("reclaim_cluster_id", "")),
                            split=split,
                            config=config,
                            extra=e2_flags,
                        )
                    )
        e3_pos = rank_persistence_pos(daily, r0, config)
        if e3_pos is not None:
            event_date = str(daily.at[e3_pos, "date"])
            split = split_for_date(event_date, split_config)
            if split != "outside_split" and event_date in membership_dates:
                rows.append(
                    channel_row(
                        instrument=instrument,
                        daily=daily,
                        membership=membership,
                        channel=CHANNEL_E3,
                        pos=e3_pos,
                        source_seed_low_pos=seed_pos,
                        first_reclaim_pos=r0,
                        seed_cluster_id=str(reclaim.get("seed_cluster_id", "")),
                        reclaim_cluster_id=str(reclaim.get("reclaim_cluster_id", "")),
                        split=split,
                        config=config,
                        extra={
                            "rank_persistence_window": int(
                                config["event_generation"]["e3_rank_persistence_window"]
                            )
                        },
                    )
                )
        e6_pos = continuation_pos(daily, r0, config)
        if e6_pos is not None:
            event_date = str(daily.at[e6_pos, "date"])
            split = split_for_date(event_date, split_config)
            if split != "outside_split" and event_date in membership_dates:
                rows.append(
                    channel_row(
                        instrument=instrument,
                        daily=daily,
                        membership=membership,
                        channel=CHANNEL_E6,
                        pos=e6_pos,
                        source_seed_low_pos=seed_pos,
                        first_reclaim_pos=r0,
                        seed_cluster_id=str(reclaim.get("seed_cluster_id", "")),
                        reclaim_cluster_id=str(reclaim.get("reclaim_cluster_id", "")),
                        split=split,
                        config=config,
                        extra={"continuation_proxy_status": NOT_MISSING},
                    )
                )
    return pd.DataFrame(rows)


def feature_snapshot_hash(row: pd.Series) -> str:
    fields = {
        key: row.get(key)
        for key in _p04.SNAPSHOT_COLUMNS
        if key in row.index and pd.notna(row.get(key))
    }
    text = json.dumps(fields, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_canonical_events(instances: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if instances.empty:
        return pd.DataFrame()
    recommended = set(config["channels"]["recommended"])
    eligible = instances.loc[instances["channel_id"].isin(recommended)].copy()
    if eligible.empty:
        return pd.DataFrame(columns=list(instances.columns))
    rows: list[dict[str, Any]] = []
    for (instrument, event_date), group in eligible.groupby(
        ["instrument", "event_t0_date"], sort=True
    ):
        ordered = group.sort_values(["event_family_priority", "event_id"]).copy()
        primary = ordered.iloc[0].copy()
        row = primary.to_dict()
        triggered = list(dict.fromkeys(ordered["channel_id"].astype(str).tolist()))
        event_id = f"{instrument}_{event_date.replace('-', '')}_recommended_union"
        row.update(
            {
                "event_id": event_id,
                "canonical_event_id": event_id,
                "symbol": instrument,
                "event_family": UNION_EVENT_FAMILY,
                "channel_id": UNION_EVENT_FAMILY,
                "channel_family": UNION_EVENT_FAMILY,
                "union_family": UNION_FAMILY,
                "canonical_event_scope": CANONICAL_SCOPE,
                "triggered_channels": ";".join(triggered),
                "primary_channel": str(primary["channel_id"]),
                "channel_count": int(len(triggered)),
                "raw_source_event_ids": ";".join(ordered["event_id"].astype(str)),
                "raw_cluster_event_count": int(len(ordered)),
                "recommended_union_included": True,
                "is_setup_context": False,
                "event_executable_date": primary.get("trade_open_date", ""),
                "episode_link_status": "not_linked_yet",
                "asof_feature_snapshot_hash": feature_snapshot_hash(primary),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def first_touch_from_daily(
    daily: pd.DataFrame,
    *,
    low_date: str,
    low_price: float,
    threshold: float,
    horizon: int,
) -> tuple[str, int]:
    matches = daily.index[daily["date"].astype(str) == low_date].tolist()
    if not matches or pd.isna(low_price) or float(low_price) <= 0:
        return "", -1
    low_pos = int(matches[0])
    end = min(len(daily) - 1, low_pos + horizon)
    for pos in range(low_pos, end + 1):
        high = daily.at[pos, "high"]
        if pd.notna(high) and float(high) / float(low_price) - 1.0 >= threshold:
            return str(daily.at[pos, "date"]), int(pos)
    return "", -1


def reconcile_first_touch(
    episodes: pd.DataFrame, daily_by_instrument: dict[str, pd.DataFrame]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    out = episodes.copy()
    effective_50: list[str] = []
    effective_50_pos: list[int] = []
    effective_100: list[str] = []
    effective_100_pos: list[int] = []
    for episode in out.to_dict("records"):
        instrument = str(episode["instrument"])
        daily = daily_by_instrument.get(instrument)
        low_date = str(episode["episode_low_date"])
        low_price = float(episode["qfq_low_at_low_date"])
        horizon = int(episode.get("forward_horizon_days", 120))
        recomputed_50, recomputed_50_pos = (
            first_touch_from_daily(
                daily, low_date=low_date, low_price=low_price, threshold=0.50, horizon=horizon
            )
            if daily is not None
            else ("", -1)
        )
        recomputed_100, recomputed_100_pos = (
            first_touch_from_daily(
                daily, low_date=low_date, low_price=low_price, threshold=1.00, horizon=horizon
            )
            if daily is not None
            else ("", -1)
        )
        src_50 = str(episode.get("first_50pct_touch_date", "") or "")
        src_100 = str(episode.get("first_100pct_touch_date", "") or "")
        final_50 = src_50 if src_50 and src_50 != "nan" else recomputed_50
        final_100 = src_100 if src_100 and src_100 != "nan" else recomputed_100
        source_50_pos = -1
        source_100_pos = -1
        if daily is not None and src_50 and src_50 != "nan":
            matches = daily.index[daily["date"].astype(str) == src_50].tolist()
            source_50_pos = int(matches[0]) if matches else -1
        if daily is not None and src_100 and src_100 != "nan":
            matches = daily.index[daily["date"].astype(str) == src_100].tolist()
            source_100_pos = int(matches[0]) if matches else -1
        effective_50.append(final_50)
        effective_50_pos.append(
            recomputed_50_pos if final_50 == recomputed_50 else source_50_pos
        )
        effective_100.append(final_100)
        effective_100_pos.append(
            recomputed_100_pos if final_100 == recomputed_100 else source_100_pos
        )
        rows.append(
            {
                "target_episode_id": episode["episode_id"],
                "instrument": instrument,
                "symbol": instrument,
                "episode_low_date": low_date,
                "source_first_50pct_touch_date": src_50,
                "source_first_50pct_touch_pos": source_50_pos,
                "recomputed_first_50pct_touch_date": recomputed_50,
                "recomputed_first_50pct_touch_pos": recomputed_50_pos,
                "effective_first_50pct_touch_date": final_50,
                "first_50pct_difference_sessions": (
                    source_50_pos - recomputed_50_pos
                    if source_50_pos >= 0 and recomputed_50_pos >= 0
                    else np.nan
                ),
                "source_first_100pct_touch_date": src_100,
                "source_first_100pct_touch_pos": source_100_pos,
                "recomputed_first_100pct_touch_date": recomputed_100,
                "recomputed_first_100pct_touch_pos": recomputed_100_pos,
                "effective_first_100pct_touch_date": final_100,
                "first_100pct_difference_sessions": (
                    source_100_pos - recomputed_100_pos
                    if source_100_pos >= 0 and recomputed_100_pos >= 0
                    else np.nan
                ),
                "source": "06_reference"
                if src_50 and src_50 != "nan"
                else "derived_in_07",
                "reconciliation_status": "match_or_derived"
                if not src_50 or src_50 == "nan" or src_50 == recomputed_50
                else "mismatch",
            }
        )
    out["effective_first_50pct_touch_date"] = effective_50
    out["effective_first_50pct_touch_pos"] = effective_50_pos
    out["effective_first_100pct_touch_date"] = effective_100
    out["effective_first_100pct_touch_pos"] = effective_100_pos
    return out, pd.DataFrame(rows)


def window_bounds(episode: dict[str, Any], daily: pd.DataFrame, window: str) -> tuple[int, int, str]:
    low_date = str(episode["episode_low_date"])
    high_date = str(episode["episode_high_date"])
    low_matches = daily.index[daily["date"].astype(str) == low_date].tolist()
    high_matches = daily.index[daily["date"].astype(str) == high_date].tolist()
    if not low_matches:
        return -1, -1, "missing_low_date"
    low_pos = int(low_matches[0])
    high_pos = int(high_matches[0]) if high_matches else -1
    first50_pos = int(episode.get("effective_first_50pct_touch_pos", -1))
    if first50_pos < 0 and str(episode.get("effective_first_50pct_touch_date", "")):
        matches = daily.index[
            daily["date"].astype(str)
            == str(episode.get("effective_first_50pct_touch_date", ""))
        ].tolist()
        first50_pos = int(matches[0]) if matches else -1
    if window == "low_to_high":
        return low_pos, high_pos, "" if high_pos >= low_pos else "missing_high_date"
    if window == "low_to_first_50pct":
        return low_pos, first50_pos, "" if first50_pos >= low_pos else "missing_first_50pct"
    if window.startswith("low_plus_"):
        sessions = int(window.split("_")[-1])
        return low_pos, low_pos + sessions, ""
    if window == "before_first_50pct":
        return low_pos, first50_pos - 1, "" if first50_pos > low_pos else "missing_first_50pct"
    if window == "before_episode_high":
        return low_pos, high_pos - 1, "" if high_pos > low_pos else "missing_high_date"
    raise ValueError(f"unknown capture window: {window}")


def build_episode_capture_audit(
    episodes: pd.DataFrame,
    canonical: pd.DataFrame,
    labels: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    label_map = labels.set_index("event_id").to_dict("index") if not labels.empty else {}
    windows = [
        "low_to_high",
        "low_to_first_50pct",
        "low_plus_20",
        "low_plus_30",
        "low_plus_60",
        "low_plus_120",
        "before_first_50pct",
        "before_episode_high",
    ]
    rows: list[dict[str, Any]] = []
    for episode in episodes.to_dict("records"):
        instrument = str(episode["instrument"])
        daily = daily_by_instrument.get(instrument)
        if daily is None:
            continue
        events_i = canonical.loc[canonical["instrument"] == instrument].copy()
        pos = pd.to_numeric(events_i.get("event_t0_pos"), errors="coerce")
        for window in windows:
            start, end, exclusion = window_bounds(episode, daily, window)
            hits = events_i.loc[(pos >= start) & (pos <= end)].copy() if not exclusion else events_i.iloc[0:0].copy()
            hits = hits.sort_values(["event_t0_pos", "event_family_priority", "event_id"])
            label_complete = 0
            label_incomplete = 0
            positive_hits: list[str] = []
            for event_id in hits["event_id"].astype(str).tolist():
                label = label_map.get(event_id, {})
                complete = bool(label.get("horizon_complete_120d", False))
                if complete:
                    label_complete += 1
                    if bool(label.get("event_big_winner_120d_label", False)):
                        positive_hits.append(event_id)
                else:
                    label_incomplete += 1
            bridge_denominator = not bool(exclusion)
            bridge_exclusion = exclusion
            if not exclusion and not hits.empty and label_complete == 0:
                bridge_denominator = False
                bridge_exclusion = "bridge_forward_120_incomplete"
            first = hits.iloc[0].to_dict() if not hits.empty else {}
            first_positive = positive_hits[0] if positive_hits else ""
            rows.append(
                {
                    "target_episode_id": episode["episode_id"],
                    "instrument": instrument,
                    "symbol": instrument,
                    "episode_low_date": episode["episode_low_date"],
                    "episode_high_date": episode["episode_high_date"],
                    "first_50pct_touch_date": episode.get("effective_first_50pct_touch_date", ""),
                    "episode_split": episode.get("split", episode.get("episode_split", "")),
                    "board_bucket": episode.get("board_bucket", ""),
                    "market_regime_bucket": episode.get("market_regime_bucket", ""),
                    "window": window,
                    "window_start_pos": start,
                    "window_end_pos": end,
                    "any_event_denominator_included": not bool(exclusion),
                    "any_event_exclusion_reason": exclusion,
                    "bridge_positive_denominator_included": bridge_denominator,
                    "bridge_positive_exclusion_reason": bridge_exclusion,
                    "any_event_captured": bool(len(hits) > 0),
                    "bridge_positive_captured": bool(first_positive),
                    "any_event_count": int(len(hits)),
                    "bridge_label_complete_event_count": int(label_complete),
                    "bridge_label_incomplete_event_count": int(label_incomplete),
                    "first_event_id": first.get("event_id", ""),
                    "first_event_t0_date": first.get("event_t0_date", ""),
                    "first_positive_event_id": first_positive,
                    "lead_time_to_first_50pct_sessions": (
                        int(episode.get("effective_first_50pct_touch_pos", -1))
                        - int(first.get("event_t0_pos", -1))
                        if first and int(episode.get("effective_first_50pct_touch_pos", -1)) >= 0
                        else np.nan
                    ),
                    "lead_time_to_episode_high_sessions": (
                        end - int(first.get("event_t0_pos", -1))
                        if first and window == "before_episode_high"
                        else np.nan
                    ),
                }
            )
    return pd.DataFrame(rows)


def group_contexts(frame: pd.DataFrame) -> list[tuple[dict[str, str], pd.DataFrame]]:
    contexts: list[tuple[dict[str, str], pd.DataFrame]] = [(
        {"episode_split": "all", "market_regime_bucket": "all", "board_bucket": "all"},
        frame,
    )]
    for split, group in frame.groupby("episode_split", dropna=False, sort=True):
        contexts.append(
            (
                {
                    "episode_split": str(split),
                    "market_regime_bucket": "all",
                    "board_bucket": "all",
                },
                group,
            )
        )
    for cols in [["episode_split", "market_regime_bucket"], ["episode_split", "board_bucket"]]:
        for keys, group in frame.groupby(cols, dropna=False, sort=True):
            key_tuple = keys if isinstance(keys, tuple) else (keys,)
            ctx = {
                "episode_split": str(key_tuple[0]),
                "market_regime_bucket": "all",
                "board_bucket": "all",
            }
            ctx[cols[1]] = str(key_tuple[1])
            contexts.append((ctx, group))
    return contexts


def build_recall_table(capture: pd.DataFrame, *, bridge: bool) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ctx, group in group_contexts(capture):
        for window, wgroup in group.groupby("window", sort=True):
            denom_col = (
                "bridge_positive_denominator_included"
                if bridge
                else "any_event_denominator_included"
            )
            hit_col = "bridge_positive_captured" if bridge else "any_event_captured"
            denom_frame = wgroup.loc[wgroup[denom_col].fillna(False).astype(bool)]
            numerator = int(denom_frame[hit_col].fillna(False).astype(bool).sum())
            rows.append(
                {
                    **ctx,
                    "window": window,
                    "metric_basis": "bridge_positive_event" if bridge else "capture_any_event",
                    "numerator": numerator,
                    "denominator": int(len(denom_frame)),
                    "excluded_count": int(len(wgroup) - len(denom_frame)),
                    "recall": safe_rate(numerator, len(denom_frame)),
                }
            )
    return pd.DataFrame(rows)


def before_first_episode_hits(
    episodes: pd.DataFrame,
    instances: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    channels: list[str],
) -> dict[str, set[str]]:
    hits = {channel: set() for channel in channels}
    for episode in episodes.to_dict("records"):
        instrument = str(episode["instrument"])
        daily = daily_by_instrument.get(instrument)
        if daily is None:
            continue
        start, end, exclusion = window_bounds(episode, daily, "before_first_50pct")
        if exclusion:
            continue
        frame = instances.loc[
            (instances["instrument"] == instrument)
            & (instances["channel_id"].isin(channels))
        ].copy()
        pos = pd.to_numeric(frame["event_t0_pos"], errors="coerce")
        captured = set(frame.loc[(pos >= start) & (pos <= end), "channel_id"].astype(str))
        for channel in captured:
            hits[channel].add(str(episode["episode_id"]))
    return hits


def build_channel_recall_contribution(
    episodes: pd.DataFrame,
    instances: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    config: dict[str, Any],
) -> pd.DataFrame:
    channels = list(config["channels"]["recommended"])
    hits = before_first_episode_hits(episodes, instances, daily_by_instrument, channels)
    all_ids = set(episodes["episode_id"].astype(str))
    union_seen: set[str] = set()
    rows = []
    for channel in channels:
        channel_hits = hits[channel]
        unique_hits = channel_hits.difference(
            set().union(*(hits[other] for other in channels if other != channel))
        )
        incremental = channel_hits.difference(union_seen)
        union_seen.update(channel_hits)
        rows.append(
            {
                "channel_id": channel,
                "target_episode_count": len(all_ids),
                "captured_episode_count": len(channel_hits),
                "recall": safe_rate(len(channel_hits), len(all_ids)),
                "unique_captured_episode_count": len(unique_hits),
                "unique_recall": safe_rate(len(unique_hits), len(all_ids)),
                "incremental_captured_episode_count": len(incremental),
                "incremental_recall": safe_rate(len(incremental), len(all_ids)),
            }
        )
    return pd.DataFrame(rows)


def build_channel_overlap_matrix(
    episodes: pd.DataFrame,
    instances: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    config: dict[str, Any],
) -> pd.DataFrame:
    channels = list(config["channels"]["recommended"])
    hits = before_first_episode_hits(episodes, instances, daily_by_instrument, channels)
    rows = []
    for left in channels:
        for right in channels:
            overlap = hits[left].intersection(hits[right])
            rows.append(
                {
                    "left_channel": left,
                    "right_channel": right,
                    "left_episode_count": len(hits[left]),
                    "right_episode_count": len(hits[right]),
                    "overlap_episode_count": len(overlap),
                    "overlap_share_of_left": safe_rate(len(overlap), len(hits[left])),
                }
            )
    return pd.DataFrame(rows)


def event_density_metrics(events: pd.DataFrame) -> tuple[float, float]:
    if events.empty:
        return np.nan, np.nan
    frame = events.copy()
    frame["year"] = frame["event_t0_date"].astype(str).str[:4]
    per_inst_year = frame.groupby(["instrument", "year"]).size()
    return safe_mean(per_inst_year), safe_pctl(per_inst_year, 0.95)


def build_density_summary(
    instances: pd.DataFrame,
    canonical: pd.DataFrame,
    universe_years: float,
    channel_contrib: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    total_canonical = len(canonical)
    mean_density, p95_density = event_density_metrics(canonical)
    rows.append(
        {
            "scope": "recommended_union",
            "channel_id": UNION_EVENT_FAMILY,
            "event_count": total_canonical,
            "events_per_100_universe_years": total_canonical / universe_years * 100
            if universe_years
            else np.nan,
            "events_per_instrument_year_mean": mean_density,
            "events_per_instrument_year_p95": p95_density,
            "density_share": 1.0,
            "incremental_recall": np.nan,
            "density_drag_flag": False,
        }
    )
    total_channel_events = int(
        instances.loc[instances["channel_id"].isin(config["channels"]["recommended"])].shape[0]
    )
    contrib = channel_contrib.set_index("channel_id") if not channel_contrib.empty else pd.DataFrame()
    for channel, group in instances.loc[
        instances["channel_id"].isin(config["channels"]["recommended"])
    ].groupby("channel_id", sort=True):
        triggered = canonical.loc[
            canonical["triggered_channels"]
            .fillna("")
            .astype(str)
            .str.split(";")
            .map(lambda values: channel in values)
        ].copy()
        mean, p95 = event_density_metrics(triggered)
        instance_mean, instance_p95 = event_density_metrics(group)
        incremental = (
            float(contrib.at[channel, "incremental_recall"])
            if not contrib.empty and channel in contrib.index
            else np.nan
        )
        share = safe_rate(len(triggered), total_canonical)
        instance_share = safe_rate(len(group), total_channel_events)
        rows.append(
            {
                "scope": "channel_instance",
                "channel_id": channel,
                "event_count": int(len(triggered)),
                "channel_instance_event_count": int(len(group)),
                "canonical_triggered_event_count": int(len(triggered)),
                "events_per_100_universe_years": len(triggered) / universe_years * 100
                if universe_years
                else np.nan,
                "events_per_instrument_year_mean": mean,
                "events_per_instrument_year_p95": p95,
                "density_share": share,
                "event_instance_density_share": instance_share,
                "instance_events_per_instrument_year_mean": instance_mean,
                "instance_events_per_instrument_year_p95": instance_p95,
                "incremental_recall": incremental,
                "density_drag_flag": bool(
                    pd.notna(incremental)
                    and incremental <= float(config["gates"]["density_drag_incremental_recall_threshold"])
                    and share >= float(config["gates"]["max_density_drag_channel_share"])
                ),
            }
        )
    return pd.DataFrame(rows)


def build_event_precision_readout(canonical: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if canonical.empty or labels.empty:
        return pd.DataFrame()
    frame = labels.merge(
        canonical[
            [
                "event_id",
                "event_split",
                "market_regime_bucket",
                "board_bucket",
                "primary_channel",
                "triggered_channels",
            ]
        ],
        on=["event_id", "event_split"],
        how="left",
    )
    rows = []
    group_cols = ["event_split", "market_regime_bucket", "board_bucket", "primary_channel"]
    for keys, group in frame.groupby(group_cols, dropna=False, sort=True):
        complete120 = group.loc[group["candidate_outcome_120d_status"] == NOT_MISSING]
        confirm = group.loc[group["confirm_20_complete"].fillna(False).astype(bool)]
        failure = group.loc[group["failure_10_complete"].fillna(False).astype(bool)]
        rows.append(
            {
                **dict(zip(group_cols, keys)),
                "event_count": int(len(group)),
                "executable_event_count": int(
                    (~group["non_executable_next_open"].fillna(False).astype(bool)).sum()
                ),
                "outcome_complete_120d_count": int(len(complete120)),
                "label_completeness_rate": safe_rate(len(complete120), len(group)),
                "event_big_winner_120d_rate": safe_rate(
                    int(complete120["event_big_winner_120d_label"].fillna(False).astype(bool).sum()),
                    len(complete120),
                ),
                "near_winner_rate": safe_rate(
                    int(complete120["event_near_winner_120d_label"].fillna(False).astype(bool).sum()),
                    len(complete120),
                ),
                "confirm_20_rate": safe_rate(
                    int((confirm["confirm_20_label"] == 1).sum()), len(confirm)
                ),
                "failure_10_rate": safe_rate(
                    int((failure["failure_10_label"] == 1).sum()), len(failure)
                ),
                "forward_20_return_mean": safe_mean(group["forward_return_20d"]),
                "forward_60_return_mean": safe_mean(group["forward_return_60d"]),
            }
        )
    return pd.DataFrame(rows)


def build_lead_time_distribution(capture: pd.DataFrame) -> pd.DataFrame:
    rows = []
    captured = capture.loc[capture["any_event_captured"].fillna(False).astype(bool)].copy()
    for keys, group in captured.groupby(["episode_split", "window"], dropna=False, sort=True):
        lead = pd.to_numeric(group["lead_time_to_first_50pct_sessions"], errors="coerce").dropna()
        rows.append(
            {
                "episode_split": keys[0],
                "window": keys[1],
                "captured_episode_count": int(len(group)),
                "lead_time_mean": safe_mean(lead),
                "lead_time_median": float(lead.median()) if len(lead) else np.nan,
                "lead_time_p25": float(lead.quantile(0.25)) if len(lead) else np.nan,
                "lead_time_p75": float(lead.quantile(0.75)) if len(lead) else np.nan,
                "late_continuation_event_share": safe_rate(
                    int((lead < 0).sum()), len(lead)
                ),
            }
        )
    return pd.DataFrame(rows)


def build_false_repair_diagnostic(canonical: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if canonical.empty or labels.empty:
        return pd.DataFrame()
    frame = labels.merge(
        canonical[["event_id", "event_split", "market_regime_bucket", "primary_channel"]],
        on=["event_id", "event_split"],
        how="left",
    )
    rows = []
    for keys, group in frame.groupby(["event_split", "market_regime_bucket", "primary_channel"], dropna=False, sort=True):
        false10 = group["event_false_repair_10d_label"].fillna(False).astype(bool)
        false20 = group["event_false_repair_20d_label"].fillna(False).astype(bool)
        rows.append(
            {
                "event_split": keys[0],
                "market_regime_bucket": keys[1],
                "primary_channel": keys[2],
                "event_count": int(len(group)),
                "false_repair_10d_count": int(false10.sum()),
                "false_repair_20d_count": int(false20.sum()),
                "false_repair_10d_rate": safe_rate(int(false10.sum()), len(group)),
                "false_repair_20d_rate": safe_rate(int(false20.sum()), len(group)),
                "clean_baseline_match_coverage": np.nan,
                "precision_claim_status": "precision_unproven_no_clean_baseline",
            }
        )
    return pd.DataFrame(rows)


def build_execution_label_audit(canonical: pd.DataFrame, labels: pd.DataFrame, capture: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, group in canonical.groupby("event_split", dropna=False, sort=True):
        label_group = labels.loc[labels["event_id"].isin(group["event_id"])]
        capture_group = capture.loc[capture["episode_split"] == split]
        rows.append(
            {
                "scope": "event_split",
                "split": split,
                "event_count": int(len(group)),
                "next_open_executable_rate": safe_rate(
                    int((~group["non_executable_next_open"].fillna(False).astype(bool)).sum()),
                    len(group),
                ),
                "event_precision_label_complete_rate": safe_rate(
                    int((label_group["candidate_outcome_120d_status"] == NOT_MISSING).sum()),
                    len(label_group),
                ),
                "capture_label_complete_rate": safe_rate(
                    int(
                        capture_group["bridge_positive_denominator_included"]
                        .fillna(False)
                        .astype(bool)
                        .sum()
                    ),
                    len(capture_group),
                ),
            }
        )
    rows.append(
        {
            "scope": "all",
            "split": "all",
            "event_count": int(len(canonical)),
            "next_open_executable_rate": safe_rate(
                int((~canonical["non_executable_next_open"].fillna(False).astype(bool)).sum()),
                len(canonical),
            ),
            "event_precision_label_complete_rate": safe_rate(
                int((labels["candidate_outcome_120d_status"] == NOT_MISSING).sum()),
                len(labels),
            ),
            "capture_label_complete_rate": safe_rate(
                int(capture["bridge_positive_denominator_included"].fillna(False).astype(bool).sum()),
                len(capture),
            ),
        }
    )
    return pd.DataFrame(rows)


def build_event_generation_universe_audit(
    universe: pd.DataFrame,
    processed_instruments: list[str],
    split_config: SplitConfig,
    denominator_summary: pd.DataFrame,
) -> pd.DataFrame:
    frame = universe.copy()
    frame["has_stock_daily_csv"] = frame["instrument"].isin(processed_instruments)
    frame["event_generation_evaluated_flag"] = (
        frame["evaluated_flag"].fillna(False).astype(bool)
        & frame["has_stock_daily_csv"].fillna(False).astype(bool)
    )
    rows = []
    expected = int(denominator_summary.iloc[0]["evaluated_instrument_days"]) if not denominator_summary.empty else 0
    for split, group in frame.groupby("split", dropna=False, sort=True):
        evaluated = group["evaluated_flag"].fillna(False).astype(bool)
        generated = group["event_generation_evaluated_flag"].fillna(False).astype(bool)
        rows.append(
            {
                "split": split,
                "raw_topn_instrument_days": int(len(group)),
                "evaluated_instrument_days": int(evaluated.sum()),
                "event_generation_instrument_days": int(generated.sum()),
                "history_ready_instrument_days": int(group["history_ready_240d_flag"].fillna(False).astype(bool).sum())
                if "history_ready_240d_flag" in group.columns
                else np.nan,
                "history_ready_250d_instrument_days": int(
                    group["history_ready_250d_flag"].fillna(False).astype(bool).sum()
                ),
                "label_complete_120d_instrument_days": int(
                    group["label_complete_120d_flag"].fillna(False).astype(bool).sum()
                ),
                "pit_clock_valid_instrument_days": int(
                    group["pit_clock_valid"].fillna(False).astype(bool).sum()
                ),
                "stock_daily_available_instrument_days": int(group["has_stock_daily_csv"].sum()),
                "processed_instrument_count": int(group.loc[group["has_stock_daily_csv"], "instrument"].nunique()),
                "excluded_instrument_days": int(len(group) - generated.sum()),
                "excluded_symbol_count": int(
                    group.loc[~generated, "instrument"].nunique()
                ),
                "pit_clock_violation_days": int(
                    (~group["pit_clock_valid"].fillna(False).astype(bool)).sum()
                ),
                "history_not_ready_250d_days": int(
                    (~group["history_ready_250d_flag"].fillna(False).astype(bool)).sum()
                ),
                "label_incomplete_120d_days": int(
                    (~group["label_complete_120d_flag"].fillna(False).astype(bool)).sum()
                ),
                "outside_split_days": int((group["split"] == "outside_split").sum()),
                "missing_stock_daily_csv_days": int((~group["has_stock_daily_csv"]).sum()),
                "exclusion_reason": ";".join(
                    reason
                    for reason, count in [
                        ("pit_clock_violation", int((~group["pit_clock_valid"].fillna(False).astype(bool)).sum())),
                        ("history_not_ready_250d", int((~group["history_ready_250d_flag"].fillna(False).astype(bool)).sum())),
                        ("label_incomplete_120d", int((~group["label_complete_120d_flag"].fillna(False).astype(bool)).sum())),
                        ("outside_split", int((group["split"] == "outside_split").sum())),
                        ("missing_stock_daily_csv", int((~group["has_stock_daily_csv"]).sum())),
                    ]
                    if count
                ),
                "expected_06_evaluated_instrument_days_all": expected if split == "all" else np.nan,
                "matches_06_evaluated_instrument_days_all": (
                    bool(int(generated.sum()) == expected) if split == "all" else np.nan
                ),
            }
        )
    evaluated_all = frame["evaluated_flag"].fillna(False).astype(bool)
    generated_all = frame["event_generation_evaluated_flag"].fillna(False).astype(bool)
    rows.append(
        {
            "split": "all",
            "raw_topn_instrument_days": int(len(frame)),
            "evaluated_instrument_days": int(evaluated_all.sum()),
            "event_generation_instrument_days": int(generated_all.sum()),
            "history_ready_instrument_days": int(frame["history_ready_240d_flag"].fillna(False).astype(bool).sum())
            if "history_ready_240d_flag" in frame.columns
            else np.nan,
            "history_ready_250d_instrument_days": int(
                frame["history_ready_250d_flag"].fillna(False).astype(bool).sum()
            ),
            "label_complete_120d_instrument_days": int(
                frame["label_complete_120d_flag"].fillna(False).astype(bool).sum()
            ),
            "pit_clock_valid_instrument_days": int(
                frame["pit_clock_valid"].fillna(False).astype(bool).sum()
            ),
            "stock_daily_available_instrument_days": int(frame["has_stock_daily_csv"].sum()),
            "processed_instrument_count": int(len(processed_instruments)),
            "excluded_instrument_days": int(len(frame) - generated_all.sum()),
            "excluded_symbol_count": int(frame.loc[~generated_all, "instrument"].nunique()),
            "pit_clock_violation_days": int(
                (~frame["pit_clock_valid"].fillna(False).astype(bool)).sum()
            ),
            "history_not_ready_250d_days": int(
                (~frame["history_ready_250d_flag"].fillna(False).astype(bool)).sum()
            ),
            "label_incomplete_120d_days": int(
                (~frame["label_complete_120d_flag"].fillna(False).astype(bool)).sum()
            ),
            "outside_split_days": int((frame["split"] == "outside_split").sum()),
            "missing_stock_daily_csv_days": int((~frame["has_stock_daily_csv"]).sum()),
            "exclusion_reason": ";".join(
                reason
                for reason, count in [
                    ("pit_clock_violation", int((~frame["pit_clock_valid"].fillna(False).astype(bool)).sum())),
                    ("history_not_ready_250d", int((~frame["history_ready_250d_flag"].fillna(False).astype(bool)).sum())),
                    ("label_incomplete_120d", int((~frame["label_complete_120d_flag"].fillna(False).astype(bool)).sum())),
                    ("outside_split", int((frame["split"] == "outside_split").sum())),
                    ("missing_stock_daily_csv", int((~frame["has_stock_daily_csv"]).sum())),
                ]
                if count
            ),
            "expected_06_evaluated_instrument_days_all": expected,
            "matches_06_evaluated_instrument_days_all": bool(int(generated_all.sum()) == expected),
        }
    )
    return pd.DataFrame(rows)


def build_vs_04_recall_comparison(any_recall: pd.DataFrame, bridge_recall: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for basis, table in [("capture_any_event", any_recall), ("bridge_positive_event", bridge_recall)]:
        selected = table.loc[
            (table["episode_split"] == "all")
            & (table["market_regime_bucket"] == "all")
            & (table["board_bucket"] == "all")
            & (table["window"] == "before_first_50pct")
        ]
        value = float(selected.iloc[0]["recall"]) if not selected.empty else np.nan
        rows.append(
            {
                "metric_basis": basis,
                "window": "before_first_50pct",
                "topn_07_recall": value,
                "old_04_reference_recall": 0.352 if basis == "bridge_positive_event" else np.nan,
                "comparison_status": "diagnostic_denominator_differs",
                "notes": "Old 04 baseline uses fixed-cap denominator; not a 07 pass/fail gate.",
            }
        )
    return pd.DataFrame(rows)


def build_vs_04_density_comparison(density: pd.DataFrame, input_status: InputStatus, config: dict[str, Any]) -> pd.DataFrame:
    union = density.loc[density["scope"] == "recommended_union"].iloc[0].to_dict() if not density.empty else {}
    return pd.DataFrame(
        [
            {
                "metric": "events_per_instrument_year_mean",
                "topn_07_recommended_union": union.get("events_per_instrument_year_mean", np.nan),
                "old_04_setup_inclusive": input_status.old_04_setup_inclusive_events_per_instrument_year_mean,
                "old_04_reclaim_based": input_status.old_04_reclaim_based_events_per_instrument_year_mean,
                "density_gate_limit": float(config["gates"]["max_recommended_union_canonical_events_per_instrument_year_mean"]),
                "comparison_status": "diagnostic_denominator_differs",
            },
            {
                "metric": "events_per_instrument_year_p95",
                "topn_07_recommended_union": union.get("events_per_instrument_year_p95", np.nan),
                "old_04_setup_inclusive": input_status.old_04_setup_inclusive_events_per_instrument_year_p95,
                "old_04_reclaim_based": input_status.old_04_reclaim_based_events_per_instrument_year_p95,
                "density_gate_limit": float(config["gates"]["max_recommended_union_canonical_events_per_instrument_year_p95"]),
                "comparison_status": "diagnostic_denominator_differs",
            },
        ]
    )


def build_input_manifest_audit(input_status: InputStatus, config: dict[str, Any]) -> pd.DataFrame:
    gates = config["gates"]
    return pd.DataFrame(
        [
            {
                "upstream_05_decision": input_status.upstream_05_decision,
                "upstream_06_decision": input_status.upstream_06_decision,
                "topn_candidate_gap_accepted": input_status.topn_candidate_gap_accepted,
                "universe_precision_status": input_status.universe_precision_status,
                "latest_label_complete_low_date": input_status.latest_label_complete_low_date,
                "source_gap_count": input_status.source_gap_count,
                "active_source_gap_count": input_status.active_source_gap_count,
                "old_04_density_baseline_source": input_status.old_04_density_baseline_source,
                "old_04_setup_inclusive_events_per_instrument_year_mean": input_status.old_04_setup_inclusive_events_per_instrument_year_mean,
                "old_04_setup_inclusive_events_per_instrument_year_p95": input_status.old_04_setup_inclusive_events_per_instrument_year_p95,
                "old_04_reclaim_based_events_per_instrument_year_mean": input_status.old_04_reclaim_based_events_per_instrument_year_mean,
                "old_04_reclaim_based_events_per_instrument_year_p95": input_status.old_04_reclaim_based_events_per_instrument_year_p95,
                "density_gate_config_source": "07_config_predeclared",
                "max_recommended_union_canonical_events_per_instrument_year_mean": gates["max_recommended_union_canonical_events_per_instrument_year_mean"],
                "max_recommended_union_canonical_events_per_instrument_year_p95": gates["max_recommended_union_canonical_events_per_instrument_year_p95"],
                "max_single_channel_density_share": gates["max_single_channel_density_share"],
                "max_density_drag_channel_share": gates["max_density_drag_channel_share"],
                "input_gate_status": input_status.input_gate_status,
                "input_gate_failure_reason": input_status.input_gate_failure_reason,
            }
        ]
    )


def gate_value(table: pd.DataFrame, split: str, basis_window: str = "before_first_50pct") -> float:
    row = table.loc[
        (table["episode_split"] == split)
        & (table["market_regime_bucket"] == "all")
        & (table["board_bucket"] == "all")
        & (table["window"] == basis_window)
    ]
    return float(row.iloc[0]["recall"]) if not row.empty else np.nan


def decide(
    *,
    input_status: InputStatus,
    any_recall: pd.DataFrame,
    density: pd.DataFrame,
    channel_contrib: pd.DataFrame,
    execution: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    gates = config["gates"]
    summary: dict[str, Any] = {
        "input_gate_status": input_status.input_gate_status,
        "input_gate_failure_reason": input_status.input_gate_failure_reason,
        "capture_any_event_before_first_50pct_all": gate_value(any_recall, "all"),
        "capture_any_event_before_first_50pct_validation": gate_value(any_recall, "validation"),
        "capture_any_event_before_first_50pct_robustness": gate_value(any_recall, "robustness"),
    }
    unique_positive_channels = int(
        (
            pd.to_numeric(channel_contrib.get("unique_recall", pd.Series(dtype=float)), errors="coerce")
            > 0
        ).sum()
    )
    summary["non_e0_positive_unique_recall_channels"] = unique_positive_channels
    union_density = density.loc[density["scope"] == "recommended_union"] if not density.empty else pd.DataFrame()
    summary["recommended_union_canonical_events_per_instrument_year_mean"] = (
        float(union_density.iloc[0]["events_per_instrument_year_mean"]) if not union_density.empty else np.nan
    )
    summary["recommended_union_canonical_events_per_instrument_year_p95"] = (
        float(union_density.iloc[0]["events_per_instrument_year_p95"]) if not union_density.empty else np.nan
    )
    summary["max_single_channel_density_share"] = safe_pctl(
        density.loc[density["scope"] == "channel_instance", "density_share"], 1.0
    )
    summary["density_drag_channel_count"] = int(
        density.get("density_drag_flag", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()
    ) if not density.empty else 0
    exec_all = execution.loc[execution["scope"] == "all"]
    if not exec_all.empty:
        for key in [
            "next_open_executable_rate",
            "event_precision_label_complete_rate",
            "capture_label_complete_rate",
        ]:
            summary[key] = float(exec_all.iloc[0][key])
    summary["gates"] = gates
    if input_status.input_gate_status != "pass":
        return DECISION_INPUT_BLOCKED, summary
    all_ok = summary["capture_any_event_before_first_50pct_all"] >= float(
        gates["min_capture_any_event_before_first_50pct_all"]
    )
    val_ok = summary["capture_any_event_before_first_50pct_validation"] >= float(
        gates["min_capture_any_event_before_first_50pct_validation"]
    )
    rob_ok = summary["capture_any_event_before_first_50pct_robustness"] >= float(
        gates["min_capture_any_event_before_first_50pct_robustness"]
    )
    channels_ok = unique_positive_channels >= int(gates["min_non_e0_positive_unique_recall_channels"])
    if not all_ok or not channels_ok:
        return DECISION_TOTAL_RECALL_BLOCKED, summary
    if not val_ok or not rob_ok:
        return DECISION_SPLIT_RECALL_BLOCKED, summary
    density_ok = (
        summary["recommended_union_canonical_events_per_instrument_year_mean"]
        <= float(gates["max_recommended_union_canonical_events_per_instrument_year_mean"])
        and summary["recommended_union_canonical_events_per_instrument_year_p95"]
        <= float(gates["max_recommended_union_canonical_events_per_instrument_year_p95"])
        and summary["max_single_channel_density_share"]
        <= float(gates["max_single_channel_density_share"])
        and summary["density_drag_channel_count"] == 0
    )
    if not density_ok:
        return DECISION_DENSITY_BLOCKED, summary
    execution_ok = (
        summary.get("next_open_executable_rate", np.nan)
        >= float(gates["min_next_open_executable_rate"])
        and summary.get("event_precision_label_complete_rate", np.nan)
        >= float(gates["min_event_precision_label_complete_rate"])
        and summary.get("capture_label_complete_rate", np.nan)
        >= float(gates["min_capture_label_complete_rate"])
    )
    if not execution_ok:
        return DECISION_EXECUTION_LABEL_BLOCKED, summary
    summary["precision_claim_status"] = "precision_unproven_no_clean_baseline"
    return DECISION_RECALL_ONLY, summary


def pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.1%}"


def fmt(value: Any, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 16) -> list[str]:
    if frame.empty:
        return ["| empty |", "|:--|", "| no rows |"]
    view = frame.loc[:, [col for col in columns if col in frame.columns]].head(max_rows).copy()
    view = view.astype(object).where(pd.notna(view), "NA")
    header = "| " + " | ".join(view.columns) + " |"
    align = "| " + " | ".join(":--" for _ in view.columns) + " |"
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in view.to_numpy()]
    return [header, align, *rows]


def write_report(
    path: Path,
    *,
    decision: str,
    gate_summary: dict[str, Any],
    input_status: InputStatus,
    denominator_summary: pd.DataFrame,
    split_summary: pd.DataFrame,
    any_recall: pd.DataFrame,
    bridge_recall: pd.DataFrame,
    channel_contrib: pd.DataFrame,
    density: pd.DataFrame,
    precision: pd.DataFrame,
    false_repair: pd.DataFrame,
    execution: pd.DataFrame,
    vs04_recall: pd.DataFrame,
    vs04_density: pd.DataFrame,
) -> Path:
    headline_any = any_recall.loc[
        (any_recall["market_regime_bucket"] == "all")
        & (any_recall["board_bucket"] == "all")
        & (any_recall["window"] == "before_first_50pct")
    ].copy()
    headline_any["recall"] = headline_any["recall"].map(pct)
    headline_bridge = bridge_recall.loc[
        (bridge_recall["market_regime_bucket"] == "all")
        & (bridge_recall["board_bucket"] == "all")
        & (bridge_recall["window"] == "before_first_50pct")
    ].copy()
    headline_bridge["recall"] = headline_bridge["recall"].map(pct)
    density_view = density.copy()
    for col in [
        "events_per_100_universe_years",
        "events_per_instrument_year_mean",
        "events_per_instrument_year_p95",
        "density_share",
        "event_instance_density_share",
        "instance_events_per_instrument_year_mean",
        "instance_events_per_instrument_year_p95",
        "incremental_recall",
    ]:
        if col in density_view:
            density_view[col] = density_view[col].map(lambda v: fmt(v, 4) if col == "incremental_recall" else fmt(v, 2))
    precision_view = precision.copy()
    for col in ["label_completeness_rate", "event_big_winner_120d_rate", "near_winner_rate", "confirm_20_rate", "failure_10_rate", "forward_20_return_mean", "forward_60_return_mean"]:
        if col in precision_view:
            precision_view[col] = precision_view[col].map(pct)
    lines = [
        "# Top-N 多通道修复事件候选生成器报告（07）",
        "",
        f"最终决策：`{decision}`",
        "",
        "## 1. 结论摘要",
        "",
        "本实验在 06 冻结的 PIT Top-N/proxy denominator 上重新实现 04 的候选事件生成器。事件先在完整 Top-N/proxy evaluated instrument-days 上生成，再事后 link 到 target big-winner episodes；因此不是 target-only search，也不是交易信号或回测。",
        "",
        f"- universe precision status：`{input_status.universe_precision_status}`。",
        f"- 06 evaluated universe cutoff：`{input_status.latest_label_complete_low_date}`；07 event generation 只使用 06 evaluated instrument-days。",
        f"- upstream 05 decision：`{input_status.upstream_05_decision}`；06 gap accepted：`{input_status.topn_candidate_gap_accepted}`。",
        f"- all before-first-50pct any-event recall：{pct(gate_summary.get('capture_any_event_before_first_50pct_all'))}。",
        f"- validation / robustness before-first-50pct any-event recall：{pct(gate_summary.get('capture_any_event_before_first_50pct_validation'))} / {pct(gate_summary.get('capture_any_event_before_first_50pct_robustness'))}。",
        f"- recommended union density mean / p95：{fmt(gate_summary.get('recommended_union_canonical_events_per_instrument_year_mean'))} / {fmt(gate_summary.get('recommended_union_canonical_events_per_instrument_year_p95'))} events per instrument-year。",
        f"- density drag channel count：{gate_summary.get('density_drag_channel_count', 'NA')}。",
        f"- execution / 120d label / capture label completeness：{pct(gate_summary.get('next_open_executable_rate'))} / {pct(gate_summary.get('event_precision_label_complete_rate'))} / {pct(gate_summary.get('capture_label_complete_rate'))}。",
        "",
        "## 2. Denominator",
        "",
        *markdown_table(denominator_summary, list(denominator_summary.columns)),
        "",
        *markdown_table(split_summary, list(split_summary.columns)),
        "",
        "## 3. Recall：Any Event 与 +50 Bridge 分开",
        "",
        "Any-event capture 只要求 before-first-50pct 窗口内出现 recommended canonical event；bridge-positive 还要求该 event 从 next-open basis 往后 120 日 MFE 达到 +50%。`0.55 / 0.45 / 0.45` 是针对 06 Top-N/proxy denominator 的预声明硬目标，不是旧 denominator 的可达性证据。旧 04 的 35.2% 只对应 bridge-positive 口径，且 denominator 不同，所以这里只做诊断对照。",
        "",
        "Bridge-positive 口径只用 forward-120 label complete 的 event 判定；如果某 episode 的 bridge window 内 event 全部 forward-120 不完整，该 episode 从 bridge-positive denominator 排除并写入 `bridge_forward_120_incomplete` audit。",
        "",
        "### Any-event before-first-50pct",
        "",
        *markdown_table(headline_any, ["episode_split", "numerator", "denominator", "excluded_count", "recall"]),
        "",
        "### Bridge-positive before-first-50pct",
        "",
        *markdown_table(headline_bridge, ["episode_split", "numerator", "denominator", "excluded_count", "recall"]),
        "",
        "### 与旧 04 对照",
        "",
        *markdown_table(vs04_recall, list(vs04_recall.columns)),
        "",
        "## 4. Channel Contribution",
        "",
        *markdown_table(channel_contrib, list(channel_contrib.columns)),
        "",
        "## 5. Density",
        "",
        "Density gate 使用 07 config 中预声明的 mean / p95 / channel-share 上限。旧 04 density baseline 从 manifest 与 event_density_audit 读取，只作为上限来源说明和 sensitivity 对照。",
        "",
        *markdown_table(density_view, list(density_view.columns)),
        "",
        *markdown_table(vs04_density, list(vs04_density.columns)),
        "",
        "## 6. Event Precision Readout",
        "",
        "这些是 event-anchored 指标，不与 episode-anchored recall 混算。由于本实验没有建立 clean matched baseline，precision claim 默认不授权。",
        "",
        *markdown_table(
            precision_view,
            [
                "event_split",
                "market_regime_bucket",
                "board_bucket",
                "primary_channel",
                "event_count",
                "label_completeness_rate",
                "event_big_winner_120d_rate",
                "near_winner_rate",
                "confirm_20_rate",
                "failure_10_rate",
                "forward_20_return_mean",
                "forward_60_return_mean",
            ],
        ),
        "",
        "## 7. False Repair / Execution",
        "",
        *markdown_table(false_repair, list(false_repair.columns)),
        "",
        *markdown_table(execution, list(execution.columns)),
        "",
        "## 8. Decision Replay",
        "",
        "```json",
        json.dumps(gate_summary, ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## 9. 下一步",
        "",
        "如果 decision 为 recall-only supported，下一步应在 recommended canonical pool 上做 entry contract 或 meta-label，而不是把本实验直接解释成交易信号。如果被 recall 或 density block，应优先检查 channel overlap、density drag 与 risk_off/ChiNext 分层，而不是在 validation/robustness 上回调阈值。",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def collect_hashes(paths: dict[str, Path]) -> dict[str, str]:
    return {
        name: file_sha256(path)
        for name, path in sorted(paths.items())
        if path.is_file()
    }


def write_manifest(
    path: Path,
    *,
    config: dict[str, Any],
    config_path: Path,
    decision: str,
    gate_summary: dict[str, Any],
    input_paths: dict[str, Path],
    output_paths: dict[str, Path],
    run_scope: str,
) -> Path:
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "experiment_name": config["experiment"]["name"],
        "run_scope": run_scope,
        "source_git_revision": git_revision(),
        "config_path": str(config_path.resolve()),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path),
        "decision": decision,
        "gate_summary": gate_summary,
        "input_paths": {k: str(v.resolve()) for k, v in sorted(input_paths.items())},
        "input_hashes": collect_hashes(input_paths),
        "output_paths": {k: str(v.resolve()) for k, v in sorted(output_paths.items())},
        "output_hashes": collect_hashes(output_paths),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_output_paths(config: dict[str, Any], *, debug: bool) -> dict[str, Path]:
    outputs = config["outputs"]
    if debug:
        base = topic_path(outputs["local_cache_dir"]) / "debug_subset"
        table_dir = base / "tables"
        report_dir = base / "reports"
        manifest_dir = base / "manifests"
    else:
        table_dir = topic_path(outputs["publishable_tables_dir"])
        report_dir = topic_path(outputs["publishable_reports_dir"])
        manifest_dir = topic_path(outputs["manifests_dir"])
    large_raw_dir = topic_path(outputs["large_raw_dir"])
    local_cache_dir = topic_path(outputs["local_cache_dir"])
    ensure_dirs([table_dir, report_dir, manifest_dir, local_cache_dir, large_raw_dir])
    return {
        "event_instances": table_dir / "topn_multichannel_candidate_event_instances.csv",
        "event_canonical": table_dir / "topn_multichannel_candidate_event_canonical.csv",
        "channel_density_summary": table_dir / "topn_channel_density_summary.csv",
        "episode_capture_audit": table_dir / "topn_episode_capture_audit.csv",
        "any_event_recall": table_dir / "topn_any_event_recall_by_split_regime_board.csv",
        "bridge_positive_recall": table_dir / "topn_bridge_positive_recall_by_split_regime_board.csv",
        "channel_recall_contribution": table_dir / "topn_channel_recall_contribution.csv",
        "channel_overlap_matrix": table_dir / "topn_channel_overlap_matrix.csv",
        "event_precision_label_readout": table_dir / "topn_event_precision_label_readout.csv",
        "event_lead_time_distribution": table_dir / "topn_event_lead_time_distribution.csv",
        "false_repair_diagnostic": table_dir / "topn_false_repair_diagnostic.csv",
        "execution_and_label_completeness_audit": table_dir / "topn_execution_and_label_completeness_audit.csv",
        "event_generation_universe_audit": table_dir / "topn_event_generation_universe_audit.csv",
        "first_touch_reconciliation_audit": table_dir / "topn_first_touch_reconciliation_audit.csv",
        "vs_04_recall": table_dir / "topn_vs_04_baseline_recall_comparison.csv",
        "vs_04_density": table_dir / "topn_vs_04_baseline_density_comparison.csv",
        "input_manifest_audit": table_dir / "topn_input_manifest_audit.csv",
        "report": report_dir / "topn_multichannel_candidate_generator_report.md",
        "manifest": manifest_dir / ("debug_metadata.json" if debug else "run_manifest.json"),
        "canonical_labels_local": local_cache_dir / ("debug_topn_canonical_event_labels.parquet" if debug else "topn_canonical_event_labels.parquet"),
    }


def build_input_paths(config: dict[str, Any]) -> dict[str, Path]:
    keys = [
        "stock_daily_csv_dir",
        "benchmark_daily_csv",
        "topn_executable_universe_csv",
        "topn_membership_universe_csv",
        "upstream_05_run_manifest_json",
        "upstream_05_data_source_coverage_audit_csv",
        "upstream_06_run_manifest_json",
        "upstream_06_episode_reference_parquet",
        "upstream_06_denominator_summary_csv",
        "upstream_06_split_denominator_summary_csv",
        "upstream_03_report_md",
        "upstream_04_run_manifest_json",
        "upstream_04_event_density_audit_csv",
        "upstream_04_report2_md",
    ]
    return {key: topic_path(config["paths"][key]) for key in keys}


def run_pipeline(
    config: dict[str, Any],
    *,
    config_path: Path,
    mode: str = "full",
    max_instruments: int | None = None,
) -> dict[str, Any]:
    validate_config(config)
    if mode == "validate-config":
        input_status = validate_input_status(config)
        return {
            "decision": input_status.input_gate_status,
            "run_scope": "validate_config",
            "input_gate_failure_reason": input_status.input_gate_failure_reason,
        }
    debug = max_instruments is not None
    run_scope = "debug_subset" if debug else "full"
    log_progress = bool(config.get("runtime", {}).get("log_progress", True))

    def progress(message: str) -> None:
        if log_progress:
            print(f"[07] {message}", file=sys.stderr, flush=True)

    input_paths = build_input_paths(config)
    output_paths = build_output_paths(config, debug=debug)
    input_status = validate_input_status(config)

    progress("loading benchmark, universe, and upstream metadata")
    benchmark_daily = pd.read_csv(input_paths["benchmark_daily_csv"])
    market_features = _p04._reverse.compute_market_features(benchmark_daily)
    benchmark_returns = _p04.compute_benchmark_returns(benchmark_daily)
    split_config = parse_split_config(
        config,
        benchmark_daily,
        latest_label_complete_low_date=input_status.latest_label_complete_low_date,
    )
    label_cfg_04 = _p04.LabelConfig(
        confirm_horizon=int(config["labels"]["confirm_20"]["horizon_days"]),
        confirm_upper=float(config["labels"]["confirm_20"]["upper_barrier"]),
        confirm_lower=float(config["labels"]["confirm_20"]["lower_barrier"]),
        failure_horizon=int(config["labels"]["failure_10"]["horizon_days"]),
        failure_lower=float(config["labels"]["failure_10"]["lower_barrier"]),
        continuous_horizons=tuple(int(v) for v in config["labels"]["continuous_horizons"]),
        big_winner_mfe_120d=float(config["labels"]["big_winner_mfe_120d"]),
        super_winner_mfe_120d=float(config["labels"]["super_winner_mfe_120d"]),
        near_winner_mfe_lower=float(config["labels"]["near_winner_mfe_lower"]),
        near_winner_mfe_upper=float(config["labels"]["near_winner_mfe_upper"]),
        false_repair_drawdown=float(config["labels"]["false_repair_drawdown"]),
    )
    source_audit = pd.read_csv(input_paths["upstream_05_data_source_coverage_audit_csv"])
    vwap_policy = _p04._observable.resolve_vwap_source_policy(source_audit)
    universe = pd.read_csv(input_paths["topn_executable_universe_csv"])
    universe["usable_trade_date"] = pd.to_datetime(universe["usable_trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    universe = add_topn_evaluated_universe_flags(universe, split_config, config)
    universe = universe.sort_values(["instrument", "usable_trade_date"]).reset_index(drop=True)
    evaluated_universe = universe.loc[universe["evaluated_flag"].fillna(False).astype(bool)].copy()
    membership_by_instrument = {
        instrument: group.reset_index(drop=True)
        for instrument, group in evaluated_universe.groupby("instrument", sort=True)
    }
    stock_dir = input_paths["stock_daily_csv_dir"]
    instruments = [
        instrument
        for instrument in sorted(membership_by_instrument)
        if (stock_dir / f"{instrument}.csv").is_file()
    ]
    if max_instruments is not None:
        instruments = instruments[: int(max_instruments)]
    progress_every = int(config.get("runtime", {}).get("progress_every_instruments", 100))
    if debug:
        progress_every = min(progress_every, 5)

    daily_by_instrument: dict[str, pd.DataFrame] = {}
    instance_parts: list[pd.DataFrame] = []
    for processed_no, instrument in enumerate(instruments, start=1):
        daily = pd.read_csv(stock_dir / f"{instrument}.csv")
        membership = membership_by_instrument[instrument]
        features = _p04.enrich_stock_features(
            daily,
            instrument=instrument,
            membership=membership,
            market_features=market_features,
            benchmark_returns=benchmark_returns,
            vwap_source_units_compatible=bool(vwap_policy.get("compatible", False)),
        )
        daily_by_instrument[instrument] = features
        events = generate_events_for_instrument(
            instrument=instrument,
            daily=features,
            membership=membership,
            split_config=split_config,
            config=config,
        )
        if not events.empty:
            instance_parts.append(events)
        if progress_every > 0 and (
            processed_no == 1
            or processed_no == len(instruments)
            or processed_no % progress_every == 0
        ):
            current_events = int(sum(len(part) for part in instance_parts))
            progress(
                f"processed {processed_no}/{len(instruments)} instruments; "
                f"event_instances={current_events}"
            )
    instances = pd.concat(instance_parts, ignore_index=True) if instance_parts else pd.DataFrame()
    progress(f"building canonical events from {len(instances)} event instances")
    canonical = build_canonical_events(instances, config)
    progress(f"labeling {len(canonical)} canonical events")
    labels = _p04.label_events(canonical, daily_by_instrument=daily_by_instrument, label_cfg=label_cfg_04)

    progress("loading and reconciling 06 target episodes")
    episodes = pd.read_parquet(input_paths["upstream_06_episode_reference_parquet"])
    episodes = episodes.loc[episodes["instrument"].isin(daily_by_instrument)].copy()
    episodes, first_touch = reconcile_first_touch(episodes, daily_by_instrument)
    progress(f"building capture audit for {episodes['episode_id'].nunique()} target episodes")
    capture = build_episode_capture_audit(episodes, canonical, labels, daily_by_instrument)
    progress("building recall, density, label, and comparison tables")
    any_recall = build_recall_table(capture, bridge=False)
    bridge_recall = build_recall_table(capture, bridge=True)
    channel_contrib = build_channel_recall_contribution(episodes, instances, daily_by_instrument, config)
    overlap = build_channel_overlap_matrix(episodes, instances, daily_by_instrument, config)
    denominator_summary = pd.read_csv(input_paths["upstream_06_denominator_summary_csv"])
    split_denominator = pd.read_csv(input_paths["upstream_06_split_denominator_summary_csv"])
    universe_years = float(denominator_summary.iloc[0]["universe_years_252"])
    density = build_density_summary(instances, canonical, universe_years, channel_contrib, config)
    precision = build_event_precision_readout(canonical, labels)
    lead_time = build_lead_time_distribution(capture)
    false_repair = build_false_repair_diagnostic(canonical, labels)
    execution = build_execution_label_audit(canonical, labels, capture)
    generation_audit = build_event_generation_universe_audit(
        universe, instruments, split_config, denominator_summary
    )
    vs04_recall = build_vs_04_recall_comparison(any_recall, bridge_recall)
    vs04_density = build_vs_04_density_comparison(density, input_status, config)
    input_audit = build_input_manifest_audit(input_status, config)
    decision, gate_summary = decide(
        input_status=input_status,
        any_recall=any_recall,
        density=density,
        channel_contrib=channel_contrib,
        execution=execution,
        config=config,
    )
    gate_summary.update(
        {
            "run_scope": run_scope,
            "target_episode_count": int(episodes["episode_id"].nunique()),
            "event_instance_count": int(len(instances)),
            "canonical_event_count": int(len(canonical)),
            "universe_precision_status": input_status.universe_precision_status,
            "latest_label_complete_low_date": input_status.latest_label_complete_low_date,
            "old_04_density_baseline_source": input_status.old_04_density_baseline_source,
        }
    )

    progress("writing tables")
    output_frames = {
        "event_instances": instances,
        "event_canonical": canonical,
        "channel_density_summary": density,
        "episode_capture_audit": capture,
        "any_event_recall": any_recall,
        "bridge_positive_recall": bridge_recall,
        "channel_recall_contribution": channel_contrib,
        "channel_overlap_matrix": overlap,
        "event_precision_label_readout": precision,
        "event_lead_time_distribution": lead_time,
        "false_repair_diagnostic": false_repair,
        "execution_and_label_completeness_audit": execution,
        "event_generation_universe_audit": generation_audit,
        "first_touch_reconciliation_audit": first_touch,
        "vs_04_recall": vs04_recall,
        "vs_04_density": vs04_density,
        "input_manifest_audit": input_audit,
    }
    for key, frame in output_frames.items():
        write_dataframe(output_paths[key], frame)
    write_dataframe(output_paths["canonical_labels_local"], labels)
    progress("writing report and manifest")
    write_report(
        output_paths["report"],
        decision=decision,
        gate_summary=gate_summary,
        input_status=input_status,
        denominator_summary=denominator_summary,
        split_summary=split_denominator,
        any_recall=any_recall,
        bridge_recall=bridge_recall,
        channel_contrib=channel_contrib,
        density=density,
        precision=precision,
        false_repair=false_repair,
        execution=execution,
        vs04_recall=vs04_recall,
        vs04_density=vs04_density,
    )
    manifest_outputs = {k: v for k, v in output_paths.items() if k != "manifest"}
    if not debug:
        write_manifest(
            output_paths["manifest"],
            config=config,
            config_path=config_path,
            decision=decision,
            gate_summary=gate_summary,
            input_paths=input_paths,
            output_paths=manifest_outputs,
            run_scope=run_scope,
        )
    else:
        output_paths["manifest"].write_text(
            json.dumps(
                {
                    "run_scope": run_scope,
                    "decision": decision,
                    "gate_summary": gate_summary,
                    "note": "debug subset; not a publishable manifest",
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    progress(f"completed run_scope={run_scope}; decision={decision}")
    return {
        "decision": decision,
        "run_scope": run_scope,
        "event_instance_count": int(len(instances)),
        "canonical_event_count": int(len(canonical)),
        "target_episode_count": int(episodes["episode_id"].nunique()),
        "manifest_path": str(output_paths["manifest"]),
        "report_path": str(output_paths["report"]),
    }
