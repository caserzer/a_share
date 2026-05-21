#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import r01_common as r01


SCRIPT_DIR = Path(__file__).resolve().parent
EP5_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP5_DIR.parent
DEFAULT_CONFIG = EP5_DIR / "configs" / "r03_downside_volatility_shock_rebound_natural_exit_v0.yaml"

REQUIREMENT_ID = "ep5_r03_downside_volatility_shock_rebound_natural_exit_v0"
PLAN_ID = "ep5_e03_downside_volatility_shock_rebound_v0"

PRIMARY_UNIT = "r03_downside_volatility_shock_rebound_natural_exit_v0"
BASELINE_UNIT = "r03_weekly_downside_nonselected_liquid_baseline_v0"
CANONICAL_UNITS = [PRIMARY_UNIT, BASELINE_UNIT]

HORIZONS = [5, 10, 20]
HORIZON_LABELS = [f"H{h}" for h in HORIZONS]
SPLITS = ["train", "validation", "robustness"]

FINAL_DECISIONS = [
    "r03_downside_volatility_shock_rebound_supported_continue_research",
    "r03_unstable_validation_only_lead",
    "r03_unstable_horizon_shape_no_search_allowed",
    "r03_adjacent_horizon_not_evaluable_validation_lead",
    "r03_relative_rebound_edge_only_hedged_or_regime_audit_required",
    "r03_downside_beta_or_market_rebound_only_no_selection_pass",
    "r03_absolute_rebound_only_baseline_lift_no_relative_pass",
    "r03_baseline_not_evaluable_validation_lead",
    "r03_horizon_specific_lead_only_no_search_allowed",
    "r03_sample_limited_primary_lead_only",
    "r03_no_downside_rebound_support",
    "r03_blocked_data_or_execution_contract",
]

PRIORITY_RULES = [
    "rule_01_blocked_data_or_execution_contract",
    "rule_02_downside_volatility_shock_rebound_supported",
    "rule_03_baseline_not_evaluable_validation_lead",
    "rule_04_downside_beta_or_market_rebound_only",
    "rule_05_unstable_validation_only_lead",
    "rule_06_unstable_horizon_shape",
    "rule_07_adjacent_horizon_not_evaluable",
    "rule_08_relative_rebound_edge_only",
    "rule_09_relative_only_baseline_not_evaluable",
    "rule_10_absolute_only_baseline_not_evaluable",
    "rule_11_absolute_only_beta_or_market_rebound",
    "rule_12_absolute_rebound_only_baseline_lift_no_relative_pass",
    "rule_13_horizon_specific_lead_only",
    "rule_14_sample_limited_primary_lead_only",
    "rule_15_no_downside_rebound_support",
]

BLOCKED_REASONS = r01.BLOCKED_REASONS
EXECUTION_STATUSES = r01.EXECUTION_STATUSES
RIGHT_TAIL_PATH_STATUSES = r01.RIGHT_TAIL_PATH_STATUSES
RIGHT_TAIL_STATUSES = r01.RIGHT_TAIL_STATUSES

CACHE_FILES = [
    "r03_daily_feature_panel.parquet",
    "r03_primary_event_panel.parquet",
    "r03_execution_event_panel.parquet",
    "r03_matched_comparator_panel.parquet",
    "r03_baseline_constituent_panel.parquet",
    "r03_right_tail_diagnostic_panel.parquet",
]

RUNNER_REPORTS = [
    "r03_artifact_authority.csv",
    "r03_input_data_audit.csv",
    "r03_provider_field_audit.csv",
    "r03_formula_input_coverage_audit.csv",
    "r03_formula_freeze_audit.csv",
    "r03_canonical_unit_registry.csv",
    "r03_vol_rank_cross_section_audit.csv",
    "r03_event_generation_audit.csv",
    "r03_execution_block_audit.csv",
    "r03_denominator_audit.csv",
    "r03_comparator_scope_audit.csv",
    "r03_relative_denominator_audit.csv",
    "r03_comparator_fallback_quality_audit.csv",
    "r03_baseline_date_comparison.csv",
    "r03_baseline_lift_audit.csv",
    "r03_event_summary_by_unit_horizon_split.csv",
    "r03_event_summary_by_unit_horizon_year.csv",
    "r03_date_independence_audit.csv",
    "r03_sample_gate_audit.csv",
    "r03_concentration_gate_audit.csv",
    "r03_absolute_gate_audit.csv",
    "r03_relative_gate_audit.csv",
    "r03_robustness_confirmation_audit.csv",
    "r03_horizon_shape_audit.csv",
    "r03_multi_comparator_relative_audit.csv",
    "r03_regime_beta_decomposition.csv",
    "r03_shock_state_decomposition.csv",
    "r03_right_tail_readout.csv",
    "r03_right_tail_censoring_audit.csv",
    "r03_final_decision.csv",
    "r03_final_decision_inputs.csv",
]

RUNNER_MANIFESTS = [
    "r03_run_manifest.json",
    "r03_artifact_hashes.json",
]

VALIDATOR_REPORTS = [
    "r03_validation_gate_audit.csv",
    "r03_schema_validation_audit.csv",
    "r03_final_decision_replay_audit.csv",
    "r03_final_report.md",
]


class R03Error(RuntimeError):
    pass


def parse_config_arg(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], r01.Paths]:
    return r01.load_config(path)


def finite(value: Any) -> bool:
    return r01.finite(value)


def safe_mean(values: pd.Series) -> float:
    return r01.safe_mean(values)


def safe_quantile(values: pd.Series, q: float) -> float:
    return r01.safe_quantile(values, q)


def safe_share(numerator: float, denominator: float) -> float:
    return r01.safe_share(numerator, denominator)


def bool_value(value: Any) -> bool:
    return r01.bool_value(value)


def split_for_date(config: dict[str, Any], value: Any) -> str:
    return r01.split_for_date(config, value)


def formula_spec(config: dict[str, Any]) -> dict[str, Any]:
    constants = config["frozen_formula_constants"]
    return {
        "primary": {
            "ret5_window_trading_days": constants["ret5_window_trading_days"],
            "realized_vol10_window_trading_days": constants["realized_vol10_window_trading_days"],
            "realized_vol10_ddof": constants["realized_vol10_ddof"],
            "realized_vol10_rank_pct_threshold": constants["realized_vol10_rank_pct_threshold"],
            "avg_money20_window_trading_days": constants["avg_money20_window_trading_days"],
            "avg_money20_floor_cny": constants["avg_money20_floor_cny"],
            "money_ma20_prev_window_trading_days": constants["money_ma20_prev_window_trading_days"],
            "downside_ret5_threshold": constants["downside_ret5_threshold"],
            "stabilization_rule": constants["stabilization_rule"],
            "money_repair_rule": constants["money_repair_rule"],
            "weekly_observation_cadence": constants["weekly_observation_cadence"],
            "vol_rank_cross_section_min_count": constants["vol_rank_cross_section_min_count"],
            "episode_merge_gap_trading_days": constants["episode_merge_gap_trading_days"],
            "horizons": HORIZON_LABELS,
            "primary_horizon": "H10",
        },
        "baseline": {
            "baseline_unit": BASELINE_UNIT,
            "baseline_scope": "weekly date-aligned paired nonselected downside high-vol universe",
            "avg_money20_floor_cny": constants["avg_money20_floor_cny"],
            "downside_ret5_threshold": constants["downside_ret5_threshold"],
            "realized_vol10_rank_pct_threshold": constants["realized_vol10_rank_pct_threshold"],
            "min_paired_nonselected_executable_constituents": constants["paired_downside_baseline_min_complete_constituents_per_dh"],
            "baseline_status": [
                "comparable",
                "blocked_insufficient_baseline_constituents",
                "not_applicable_no_primary_complete_event",
            ],
        },
    }


def formula_hashes(config: dict[str, Any]) -> dict[str, str]:
    spec = formula_spec(config)
    return {
        PRIMARY_UNIT: r01.canonical_hash(spec["primary"]),
        BASELINE_UNIT: r01.canonical_hash(spec["baseline"]),
    }


def build_input_audits(config: dict[str, Any], paths: r01.Paths) -> None:
    rows = []
    for role, raw_path in [
        ("qlib_provider_uri", config["data_sources"]["qlib_provider_uri"]),
        ("pit_universe_path", config["data_sources"]["pit_universe_path"]),
        ("pit_qlib_instrument_universe_path", config["data_sources"]["pit_qlib_instrument_universe_path"]),
        ("pit_industry_path", config["data_sources"]["pit_industry_path"]),
        ("trading_calendar_path", config["data_sources"]["trading_calendar_path"]),
        ("qlib_instrument_path", config["data_sources"]["qlib_instrument_path"]),
        ("requirement_path", config["requirement_path"]),
        ("config_path", paths.config_path),
    ]:
        path = r01.topic_path(raw_path)
        rows.append(
            {
                "artifact_role": role,
                "artifact_path": r01.relpath(path),
                "required": True,
                "exists": path.exists(),
                "sha256": r01.file_hash(path) if path.exists() else "",
                "row_count": r01.count_rows(path) if path.exists() else 0,
                "status": "present" if path.exists() else "missing",
            }
        )
    r01.write_csv(pd.DataFrame(rows), paths.reports_dir / "r03_artifact_authority.csv")

    universe = r01.load_universe(config)
    industry = r01.load_industry(config)
    calendar = r01.load_calendar(config)
    audit = pd.DataFrame(
        [
            {
                "source": "pit_universe",
                "row_count": len(universe),
                "instrument_count": universe["instrument_id"].nunique(),
                "min_date": universe["trade_date"].min(),
                "max_date": universe["trade_date"].max(),
                "status": "passed" if not universe.empty else "failed",
            },
            {
                "source": "pit_industry",
                "row_count": len(industry),
                "instrument_count": industry["instrument_id"].nunique(),
                "min_date": industry["trade_date"].min(),
                "max_date": industry["trade_date"].max(),
                "status": "passed" if not industry.empty else "failed",
            },
            {
                "source": "trading_calendar",
                "row_count": len(calendar),
                "instrument_count": 0,
                "min_date": calendar.min(),
                "max_date": calendar.max(),
                "status": "passed" if len(calendar) else "failed",
            },
        ]
    )
    r01.write_csv(audit, paths.reports_dir / "r03_input_data_audit.csv")


def weekly_observation_dates(config: dict[str, Any]) -> set[pd.Timestamp]:
    calendar = r01.load_calendar(config)
    start = pd.Timestamp(config["split"]["train_start"])
    end = pd.Timestamp(config["split"]["robustness_end"])
    dates = pd.DatetimeIndex([pd.Timestamp(d) for d in calendar if start <= pd.Timestamp(d) <= end])
    if dates.empty:
        return set()
    frame = pd.DataFrame({"trade_date": dates})
    iso = frame["trade_date"].dt.isocalendar()
    frame["iso_year"] = iso["year"].astype(int)
    frame["iso_week"] = iso["week"].astype(int)
    weekly = frame.groupby(["iso_year", "iso_week"], as_index=False)["trade_date"].max()
    return set(pd.to_datetime(weekly["trade_date"]).dt.normalize())


def ret5_bucket(value: Any) -> str:
    if not finite(value):
        return "unknown"
    x = float(value)
    if x <= -0.15:
        return "ret5_le_neg_150"
    if x <= -0.10:
        return "ret5_neg_150_neg_100"
    if x <= -0.05:
        return "ret5_neg_100_neg_050"
    return "ret5_gt_neg_050"


def rank_bucket(value: Any) -> str:
    if not finite(value):
        return "unknown"
    x = float(value)
    if x < 0.80:
        return "below_080"
    if x < 0.85:
        return "bucket_080_085"
    if x < 0.90:
        return "bucket_085_090"
    if x < 0.95:
        return "bucket_090_095"
    return "bucket_095_100"


def stabilization_bucket(value: Any) -> str:
    if not finite(value):
        return "unknown"
    x = float(value)
    if x <= 0:
        return "stabilization_le_000"
    if x <= 0.01:
        return "stabilization_000_001"
    if x <= 0.03:
        return "stabilization_001_003"
    return "stabilization_gt_003"


def money_repair_bucket(value: Any) -> str:
    if not finite(value):
        return "unknown"
    x = float(value)
    if x < 0.50:
        return "money_repair_lt_050"
    if x < 1.0:
        return "money_repair_050_100"
    if x < 1.5:
        return "money_repair_100_150"
    if x < 3.0:
        return "money_repair_150_300"
    return "money_repair_ge_300"


def build_feature_panel(config: dict[str, Any], paths: r01.Paths) -> pd.DataFrame:
    feature, _ = r01.build_feature_panel(config, paths)
    for extra_report in [
        "r01_provider_field_audit.csv",
        "r01_formula_input_coverage_audit.csv",
        "r01_feature_asof_audit.csv",
        "r01_market_state_beta_bucket_audit.csv",
        "r01_beta_bucket_boundary_audit.csv",
    ]:
        (paths.reports_dir / extra_report).unlink(missing_ok=True)
    (paths.cache_dir / "r01_daily_feature_panel.parquet").unlink(missing_ok=True)
    constants = config["frozen_formula_constants"]
    feature = feature.sort_values(["instrument_id", "trade_date"]).reset_index(drop=True)
    grouped = feature.groupby("instrument_id", group_keys=False)
    feature["ret5"] = grouped["close"].transform(lambda s: s / s.shift(int(constants["ret5_window_trading_days"])) - 1.0)
    feature["daily_close_return"] = grouped["close"].pct_change()
    feature["realized_vol10"] = grouped["daily_close_return"].transform(
        lambda s: s.rolling(int(constants["realized_vol10_window_trading_days"]), min_periods=int(constants["realized_vol10_window_trading_days"])).std(ddof=int(constants["realized_vol10_ddof"]))
    )
    feature["avg_money20_D"] = feature["avg_money20_asof"]
    feature["money_ma20_prev_D"] = feature["money_ma20_prev"]
    feature["stabilization_return_at_D"] = feature["close"] / feature["prev_close"] - 1.0
    feature["money_repair_ratio_at_D"] = feature["money"] / feature["money_ma20_prev_D"]
    feature["weekly_observation_date"] = feature["trade_date"].isin(weekly_observation_dates(config))
    feature["rank_pct_realized_vol10"] = np.nan
    feature["vol_rank_cross_section_count"] = 0
    feature["vol_rank_cross_section_status"] = ""
    feature["raw_primary_eligible_pre_collapse"] = False

    floor = float(constants["avg_money20_floor_cny"])
    min_count = int(constants["vol_rank_cross_section_min_count"])
    vol_threshold = float(constants["realized_vol10_rank_pct_threshold"])
    ret5_threshold = float(constants["downside_ret5_threshold"])
    audit_rows = []
    weekly = feature.loc[feature["weekly_observation_date"] & feature["split"].isin(SPLITS)]
    for date, group in weekly.groupby("trade_date", sort=True):
        rank_mask = (
            group["pit_universe_member"]
            & (group["avg_money20_D"] >= floor)
            & (group["close"] > 0)
            & (group["prev_close"] > 0)
            & np.isfinite(group["ret5"])
            & np.isfinite(group["realized_vol10"])
            & np.isfinite(group["money_ma20_prev_D"])
            & (group["money"] > 0)
            & (group["volume"] > 0)
        )
        rank_count = int(rank_mask.sum())
        status = "vol_rank_cross_section_ok" if rank_count >= min_count else "blocked_insufficient_vol_rank_cross_section"
        rank_values = group.loc[rank_mask, "realized_vol10"]
        if rank_count:
            ranks = rank_values.rank(method="average", ascending=True) / rank_count
            feature.loc[ranks.index, "rank_pct_realized_vol10"] = ranks
        feature.loc[group.index, "vol_rank_cross_section_count"] = rank_count
        feature.loc[group.index, "vol_rank_cross_section_status"] = status
        eligible_mask = (
            rank_mask
            & (rank_count >= min_count)
            & (group["ret5"] <= ret5_threshold)
            & ((feature.loc[group.index, "rank_pct_realized_vol10"]) >= vol_threshold)
            & (group["close"] > group["prev_close"])
            & (group["money"] >= group["money_ma20_prev_D"])
        )
        feature.loc[group.index, "raw_primary_eligible_pre_collapse"] = eligible_mask.to_numpy()
        audit_rows.append(
            {
                "weekly_observation_date": pd.Timestamp(date),
                "split": split_for_date(config, date),
                "vol_rank_cross_section_count": rank_count,
                "eligible_signal_count": int(eligible_mask.sum()),
                "vol_rank_cross_section_status": status,
            }
        )
    feature["rank_pct_realized_vol10_bucket_at_D"] = feature["rank_pct_realized_vol10"].map(rank_bucket)
    feature["ret5_value_bucket_at_D"] = feature["ret5"].map(ret5_bucket)
    feature["stabilization_return_bucket_at_D"] = feature["stabilization_return_at_D"].map(stabilization_bucket)
    feature["money_repair_ratio_bucket_at_D"] = feature["money_repair_ratio_at_D"].map(money_repair_bucket)

    r01.write_parquet(feature, paths.cache_dir / "r03_daily_feature_panel.parquet")
    r01.write_csv(pd.DataFrame(audit_rows), paths.reports_dir / "r03_vol_rank_cross_section_audit.csv")

    provider_audit = pd.DataFrame(
        [
            {
                "field": field,
                "row_count": len(feature),
                "non_null_count": int(feature[field].notna().sum()) if field in feature else 0,
                "missing_count": int(feature[field].isna().sum()) if field in feature else len(feature),
                "status": "present" if field in feature else "missing",
            }
            for field in ["open", "high", "low", "close", "volume", "money", "factor"]
        ]
    )
    r01.write_csv(provider_audit, paths.reports_dir / "r03_provider_field_audit.csv")
    coverage_fields = [
        "ret5",
        "realized_vol10",
        "avg_money20_D",
        "money_ma20_prev_D",
        "stabilization_return_at_D",
        "money_repair_ratio_at_D",
        "rank_pct_realized_vol10",
        "raw_primary_eligible_pre_collapse",
    ]
    coverage = [
        {
            "feature_name": column,
            "row_count": len(feature),
            "non_null_count": int(feature[column].notna().sum()),
            "weekly_non_null_count": int(feature.loc[feature["weekly_observation_date"], column].notna().sum()),
            "status": "present",
        }
        for column in coverage_fields
    ]
    r01.write_csv(pd.DataFrame(coverage), paths.reports_dir / "r03_formula_input_coverage_audit.csv")
    return feature


def build_unit_registry(config: dict[str, Any], paths: r01.Paths) -> None:
    hashes = formula_hashes(config)
    registry = pd.DataFrame(
        [
            {
                "canonical_unit_id": PRIMARY_UNIT,
                "unit_role": "primary downside volatility shock rebound exposure unit",
                "final_decision_authority": "sole R03 continue/no-continue decision unit",
                "horizons": "H5,H10,H20",
                "entry_rule": "first_executable_next_open",
                "exit_rule": "natural_exit_execution_date",
                "formula_hash": hashes[PRIMARY_UNIT],
                "formula_constants_hash": r01.canonical_hash(config["frozen_formula_constants"]),
                "status": "frozen",
            },
            {
                "canonical_unit_id": BASELINE_UNIT,
                "unit_role": "audit-only date-aligned paired nonselected downside baseline",
                "final_decision_authority": "downgrade guard only; cannot create positive decision",
                "horizons": "H5,H10,H20",
                "entry_rule": "first_executable_next_open",
                "exit_rule": "natural_exit_execution_date",
                "formula_hash": hashes[BASELINE_UNIT],
                "formula_constants_hash": r01.canonical_hash(config["frozen_formula_constants"]),
                "status": "frozen",
            },
        ]
    )
    r01.write_csv(registry, paths.reports_dir / "r03_canonical_unit_registry.csv")

    rows = []
    for unit in CANONICAL_UNITS:
        for name, value in config["frozen_formula_constants"].items():
            rows.append(
                {
                    "canonical_unit_id": unit,
                    "source_requirement_section": "R03 §7",
                    "formula_name": unit,
                    "frozen_constant_name": name,
                    "frozen_constant_value": value,
                    "formula_text_hash": hashes[unit],
                    "formula_constants_hash": r01.canonical_hash(config["frozen_formula_constants"]),
                    "implementation_hash": hashes[unit],
                    "status": "frozen",
                }
            )
    r01.write_csv(pd.DataFrame(rows), paths.reports_dir / "r03_formula_freeze_audit.csv")


def build_primary_event_panel(config: dict[str, Any], paths: r01.Paths, feature: pd.DataFrame) -> pd.DataFrame:
    constants = config["frozen_formula_constants"]
    hashes = formula_hashes(config)
    calendar_pos = r01.trading_day_pos(r01.load_calendar(config))
    gap = int(constants["episode_merge_gap_trading_days"])
    eligible = feature["raw_primary_eligible_pre_collapse"].astype(bool)
    hits = feature.loc[eligible].sort_values(["instrument_id", "trade_date"]).copy()
    rows = []
    audit_rows = []
    for instrument, group in hits.groupby("instrument_id", sort=True):
        last_pos: int | None = None
        episode_no = 0
        raw_count = 0
        kept_count = 0
        duplicate_count = 0
        for record in group.itertuples(index=False):
            raw_count += 1
            date = pd.Timestamp(record.trade_date)
            pos = calendar_pos.get(date)
            if pos is None:
                continue
            if last_pos is None or pos - last_pos > gap:
                episode_no += 1
                kept_count += 1
                event_key = f"{PRIMARY_UNIT}_{instrument}_{date.date()}"
                rows.append(
                    {
                        "canonical_unit_id": PRIMARY_UNIT,
                        "unit_role": "primary downside volatility shock rebound exposure unit",
                        "instrument_id": instrument,
                        "signal_date": date,
                        "episode_id": f"{instrument}_{date.date()}_DVSR_{episode_no}",
                        "episode_start_signal_date": date,
                        "event_key": event_key,
                        "split": record.split,
                        "detector_id": "R03_DOWNSIDE_VOLATILITY_SHOCK_REBOUND_V0",
                        "detector_formula_hash": hashes[PRIMARY_UNIT],
                        "formula_hash": hashes[PRIMARY_UNIT],
                        "formula_input_row_hash": r01.canonical_hash({"instrument_id": instrument, "signal_date": str(date.date()), "unit": PRIMARY_UNIT}),
                        "source_requirement_section": "R03 §7.1",
                        "event_collapse_window_trading_days": gap,
                        "event_status": "event_generated",
                        "ret5": record.ret5,
                        "realized_vol10": record.realized_vol10,
                        "daily_close_return": record.daily_close_return,
                        "prev_close": record.prev_close,
                        "avg_money20_D": record.avg_money20_D,
                        "money_ma20_prev_D": record.money_ma20_prev_D,
                        "stabilization_return_at_D": record.stabilization_return_at_D,
                        "money_repair_ratio_at_D": record.money_repair_ratio_at_D,
                        "rank_pct_realized_vol10": record.rank_pct_realized_vol10,
                        "vol_rank_cross_section_count": record.vol_rank_cross_section_count,
                        "rank_pct_realized_vol10_bucket_at_D": record.rank_pct_realized_vol10_bucket_at_D,
                        "ret5_value_bucket_at_D": record.ret5_value_bucket_at_D,
                        "stabilization_return_bucket_at_D": record.stabilization_return_bucket_at_D,
                        "money_repair_ratio_bucket_at_D": record.money_repair_ratio_bucket_at_D,
                        "raw_primary_eligible_pre_collapse": True,
                        "industry_id": record.industry_id,
                        "industry_name": record.industry_name,
                        "liquidity_quintile": record.liquidity_quintile,
                        "market_state": record.market_state,
                        "beta_bucket": record.beta_bucket,
                    }
                )
            else:
                duplicate_count += 1
            last_pos = pos
        audit_rows.append(
            {
                "canonical_unit_id": PRIMARY_UNIT,
                "instrument_id": instrument,
                "raw_formula_hit_count": raw_count,
                "post_collapse_event_count": kept_count,
                "dropped_duplicate_episode_member_count": duplicate_count,
                "blocked_formula_row_count": 0,
            }
        )
    event = pd.DataFrame(rows)
    if event.empty:
        event = pd.DataFrame(
            columns=[
                "canonical_unit_id",
                "unit_role",
                "instrument_id",
                "signal_date",
                "episode_id",
                "episode_start_signal_date",
                "event_key",
                "split",
                "detector_id",
                "formula_hash",
                "event_status",
            ]
        )
    event = event.sort_values(["instrument_id", "signal_date"]).reset_index(drop=True)
    r01.write_parquet(event, paths.cache_dir / "r03_primary_event_panel.parquet")

    audit = pd.DataFrame(audit_rows)
    if audit.empty:
        audit = pd.DataFrame(columns=["canonical_unit_id", "instrument_id", "raw_formula_hit_count", "post_collapse_event_count", "dropped_duplicate_episode_member_count", "blocked_formula_row_count"])
    aggregate = audit.groupby("canonical_unit_id", as_index=False).sum(numeric_only=True) if not audit.empty else audit
    r01.write_csv(aggregate, paths.reports_dir / "r03_event_generation_audit.csv")
    return event


def execute_events(config: dict[str, Any], feature: pd.DataFrame, event: pd.DataFrame) -> pd.DataFrame:
    calendar = r01.load_calendar(config)
    lookup = r01.make_feature_lookup(feature)
    max_entry_lag = int(config["execution"]["max_entry_execution_lag_trading_days"])
    max_exit_lag = int(config["execution"]["max_exit_execution_lag_trading_days"])
    buy_cost = float(config["execution"]["buy_cost_bps"])
    sell_cost = float(config["execution"]["sell_cost_bps"])
    round_trip = float(config["execution"]["round_trip_cost_bps"])
    rows: list[dict[str, Any]] = []
    for ev in event.itertuples(index=False):
        for horizon in HORIZONS:
            row = {
                "canonical_unit_id": ev.canonical_unit_id,
                "unit_role": getattr(ev, "unit_role", ""),
                "instrument_id": ev.instrument_id,
                "event_key": ev.event_key,
                "signal_date": pd.Timestamp(ev.signal_date),
                "horizon": f"H{horizon}",
                "split": ev.split,
                "entry_execution_date": pd.NaT,
                "entry_price": np.nan,
                "natural_exit_target_date": pd.NaT,
                "natural_exit_signal_date": pd.NaT,
                "natural_exit_execution_date": pd.NaT,
                "natural_exit_price": np.nan,
                "fast_fail_enabled": False,
                "fast_fail_drawdown": np.nan,
                "fast_fail_signal_date": pd.NaT,
                "exit_execution_date": pd.NaT,
                "exit_price": np.nan,
                "buy_cost_bps": buy_cost,
                "sell_cost_bps": sell_cost,
                "round_trip_cost_bps": round_trip,
                "gross_return": np.nan,
                "net_return": np.nan,
                "execution_status": "",
                "blocked_reason": "",
                "entry_lag_trading_days": np.nan,
                "exit_lag_trading_days": np.nan,
            }
            for attr in [
                "ret5",
                "realized_vol10",
                "daily_close_return",
                "prev_close",
                "avg_money20_D",
                "money_ma20_prev_D",
                "stabilization_return_at_D",
                "money_repair_ratio_at_D",
                "rank_pct_realized_vol10",
                "vol_rank_cross_section_count",
                "rank_pct_realized_vol10_bucket_at_D",
                "ret5_value_bucket_at_D",
                "stabilization_return_bucket_at_D",
                "money_repair_ratio_bucket_at_D",
                "raw_primary_eligible_pre_collapse",
                "industry_id",
                "industry_name",
                "liquidity_quintile",
                "market_state",
                "beta_bucket",
                "is_broad_liquid_baseline",
                "is_paired_nonselected_downside_baseline",
                "raw_primary_eligible_pre_collapse_on_date",
            ]:
                if hasattr(ev, attr):
                    row[attr] = getattr(ev, attr)
            entry = r01.first_executable_open(config, calendar, lookup, ev.instrument_id, pd.Timestamp(ev.signal_date), ev.split, "entry", max_entry_lag)
            row["entry_lag_trading_days"] = entry["lag"]
            if entry["blocked_reason"]:
                reason = entry["blocked_reason"]
                row["execution_status"] = f"blocked_{reason}"
                row["blocked_reason"] = reason
                rows.append(row)
                continue
            row["entry_execution_date"] = entry["date"]
            row["entry_price"] = entry["price"]
            target = r01.add_trading_days(calendar, row["entry_execution_date"], horizon)
            row["natural_exit_target_date"] = target
            if pd.isna(target):
                row["execution_status"] = "blocked_insufficient_forward_trading_days"
                row["blocked_reason"] = "insufficient_forward_trading_days"
                rows.append(row)
                continue
            if split_for_date(config, target) != ev.split:
                row["execution_status"] = "blocked_split_boundary"
                row["blocked_reason"] = "split_boundary"
                rows.append(row)
                continue
            natural_signal = r01.prev_trading_day(calendar, target)
            row["natural_exit_signal_date"] = natural_signal
            exit_exec = r01.first_executable_open(config, calendar, lookup, ev.instrument_id, natural_signal, ev.split, "exit", max_exit_lag)
            row["exit_lag_trading_days"] = exit_exec["lag"]
            if exit_exec["blocked_reason"]:
                reason = exit_exec["blocked_reason"]
                row["execution_status"] = f"blocked_{reason}"
                row["blocked_reason"] = reason
                rows.append(row)
                continue
            row["exit_execution_date"] = exit_exec["date"]
            row["exit_price"] = exit_exec["price"]
            row["natural_exit_execution_date"] = target
            natural_info = lookup.get((ev.instrument_id, target), {})
            row["natural_exit_price"] = natural_info.get("open", np.nan)
            row["gross_return"] = row["exit_price"] / row["entry_price"] - 1.0
            row["net_return"] = row["exit_price"] * (1.0 - sell_cost / 10000.0) / (row["entry_price"] * (1.0 + buy_cost / 10000.0)) - 1.0
            row["execution_status"] = "complete_executable"
            rows.append(row)
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(
        columns=[
            "canonical_unit_id",
            "unit_role",
            "instrument_id",
            "event_key",
            "signal_date",
            "horizon",
            "split",
            "entry_execution_date",
            "entry_price",
            "natural_exit_target_date",
            "natural_exit_signal_date",
            "natural_exit_execution_date",
            "natural_exit_price",
            "exit_execution_date",
            "exit_price",
            "buy_cost_bps",
            "sell_cost_bps",
            "round_trip_cost_bps",
            "gross_return",
            "net_return",
            "execution_status",
            "blocked_reason",
            "entry_lag_trading_days",
            "exit_lag_trading_days",
        ]
    )


def write_execution_audits(paths: r01.Paths, execution: pd.DataFrame) -> None:
    block = (
        execution.loc[execution["execution_status"].ne("complete_executable")]
        .groupby(["canonical_unit_id", "horizon", "split", "blocked_reason"], dropna=False)
        .size()
        .reset_index(name="blocked_count")
    )
    denom = execution.groupby(["canonical_unit_id", "horizon", "split"], dropna=False).size().reset_index(name="signal_event_count")
    complete = execution.loc[execution["execution_status"].eq("complete_executable")].groupby(["canonical_unit_id", "horizon", "split"], dropna=False).size().reset_index(name="complete_event_count")
    denom = denom.merge(complete, on=["canonical_unit_id", "horizon", "split"], how="left").fillna({"complete_event_count": 0})
    denom["blocked_event_count"] = denom["signal_event_count"] - denom["complete_event_count"]
    denom["complete_event_share"] = denom["complete_event_count"] / denom["signal_event_count"]
    if not block.empty:
        block = block.merge(denom[["canonical_unit_id", "horizon", "split", "signal_event_count"]], on=["canonical_unit_id", "horizon", "split"], how="left")
        block["blocked_share"] = block["blocked_count"] / block["signal_event_count"]
    else:
        block = pd.DataFrame(columns=["canonical_unit_id", "horizon", "split", "blocked_reason", "blocked_count", "signal_event_count", "blocked_share"])
    r01.write_csv(block, paths.reports_dir / "r03_execution_block_audit.csv")
    r01.write_csv(denom, paths.reports_dir / "r03_denominator_audit.csv")


def build_execution_panel(config: dict[str, Any], paths: r01.Paths, feature: pd.DataFrame, event: pd.DataFrame) -> pd.DataFrame:
    execution = execute_events(config, feature, event)
    r01.write_parquet(execution, paths.cache_dir / "r03_execution_event_panel.parquet")
    write_execution_audits(paths, execution)
    return execution


def build_baseline_constituent_panel(config: dict[str, Any], paths: r01.Paths, feature: pd.DataFrame, primary_event: pd.DataFrame) -> pd.DataFrame:
    constants = config["frozen_formula_constants"]
    floor = float(constants["avg_money20_floor_cny"])
    ret5_threshold = float(constants["downside_ret5_threshold"])
    vol_threshold = float(constants["realized_vol10_rank_pct_threshold"])
    hashes = formula_hashes(config)
    if primary_event.empty:
        empty = pd.DataFrame()
        r01.write_parquet(empty, paths.cache_dir / "r03_baseline_constituent_panel.parquet")
        return empty
    signal_dates = sorted(pd.to_datetime(primary_event["signal_date"]).dt.normalize().unique())
    rows = []
    base = feature.loc[
        feature["trade_date"].isin(signal_dates)
        & feature["pit_universe_member"]
        & (feature["avg_money20_D"] >= floor)
        & (feature["close"] > 0)
        & (feature["prev_close"] > 0)
        & (feature["money"] > 0)
        & (feature["volume"] > 0)
        & np.isfinite(feature["ret5"])
        & np.isfinite(feature["realized_vol10"])
        & np.isfinite(feature["rank_pct_realized_vol10"])
    ].copy()
    for record in base.itertuples(index=False):
        date = pd.Timestamp(record.trade_date)
        raw_primary = bool(record.raw_primary_eligible_pre_collapse)
        paired_downside = bool(
            record.ret5 <= ret5_threshold
            and record.rank_pct_realized_vol10 >= vol_threshold
            and record.vol_rank_cross_section_status == "vol_rank_cross_section_ok"
            and not raw_primary
        )
        rows.append(
            {
                "canonical_unit_id": BASELINE_UNIT,
                "unit_role": "audit-only date-aligned paired nonselected downside baseline",
                "instrument_id": record.instrument_id,
                "signal_date": date,
                "event_key": f"{BASELINE_UNIT}_{record.instrument_id}_{date.date()}",
                "split": record.split,
                "formula_hash": hashes[BASELINE_UNIT],
                "source_requirement_section": "R03 §7.2",
                "is_broad_liquid_baseline": True,
                "is_paired_nonselected_downside_baseline": paired_downside,
                "raw_primary_eligible_pre_collapse_on_date": raw_primary,
                "ret5": record.ret5,
                "realized_vol10": record.realized_vol10,
                "daily_close_return": record.daily_close_return,
                "prev_close": record.prev_close,
                "avg_money20_D": record.avg_money20_D,
                "money_ma20_prev_D": record.money_ma20_prev_D,
                "stabilization_return_at_D": record.stabilization_return_at_D,
                "money_repair_ratio_at_D": record.money_repair_ratio_at_D,
                "rank_pct_realized_vol10": record.rank_pct_realized_vol10,
                "vol_rank_cross_section_count": record.vol_rank_cross_section_count,
                "rank_pct_realized_vol10_bucket_at_D": record.rank_pct_realized_vol10_bucket_at_D,
                "ret5_value_bucket_at_D": record.ret5_value_bucket_at_D,
                "stabilization_return_bucket_at_D": record.stabilization_return_bucket_at_D,
                "money_repair_ratio_bucket_at_D": record.money_repair_ratio_bucket_at_D,
                "raw_primary_eligible_pre_collapse": raw_primary,
                "industry_id": record.industry_id,
                "industry_name": record.industry_name,
                "liquidity_quintile": record.liquidity_quintile,
                "market_state": record.market_state,
                "beta_bucket": record.beta_bucket,
            }
        )
    baseline_event = pd.DataFrame(rows)
    baseline_execution = execute_events(config, feature, baseline_event)
    r01.write_parquet(baseline_execution, paths.cache_dir / "r03_baseline_constituent_panel.parquet")
    return baseline_execution


def build_index_open_lookup(config: dict[str, Any]) -> dict[pd.Timestamp, float]:
    provider = r01.load_provider_panel(config)
    index_id = config["data_sources"]["index_instrument"].upper()
    index = provider.loc[provider["instrument_id"].eq(index_id), ["trade_date", "open"]].dropna()
    return {pd.Timestamp(row.trade_date): float(row.open) for row in index.itertuples(index=False)}


def build_comparator_panel(config: dict[str, Any], paths: r01.Paths, feature: pd.DataFrame, execution: pd.DataFrame) -> pd.DataFrame:
    feature_by_date = r01.build_feature_by_date(feature)
    index_open = build_index_open_lookup(config)
    pair_cache: dict[tuple[pd.Timestamp, pd.Timestamp], pd.DataFrame] = {}
    complete = execution.loc[execution["execution_status"].eq("complete_executable")].copy()
    rows: list[dict[str, Any]] = []
    for record in complete.itertuples(index=False):
        entry_date = pd.Timestamp(record.entry_execution_date)
        exit_date = pd.Timestamp(record.exit_execution_date)
        signal_date = pd.Timestamp(record.signal_date)
        pair_key = (entry_date, exit_date)
        if pair_key not in pair_cache:
            pair_cache[pair_key] = r01.executable_pair_returns(config, entry_date, exit_date, feature_by_date, float(record.buy_cost_bps), float(record.sell_cost_bps))
        candidates = pair_cache[pair_key]
        signal_features = feature_by_date.get(signal_date, pd.DataFrame())
        base = candidates.loc[candidates["instrument_id"].ne(record.instrument_id)].copy()
        base = base.merge(signal_features[["instrument_id", "industry_id", "liquidity_quintile"]], on="instrument_id", how="left") if not signal_features.empty else base
        event_feat = signal_features.loc[signal_features["instrument_id"].eq(record.instrument_id)].head(1) if not signal_features.empty else pd.DataFrame()
        event_industry = event_feat.iloc[0]["industry_id"] if not event_feat.empty else "UNKNOWN"
        event_liq = event_feat.iloc[0]["liquidity_quintile"] if not event_feat.empty else ""
        same_industry = base.loc[base["industry_id"].eq(event_industry)] if "industry_id" in base else pd.DataFrame()
        same_liquidity = base.loc[base["liquidity_quintile"].eq(event_liq)] if "liquidity_quintile" in base else pd.DataFrame()
        same_both = base.loc[base["industry_id"].eq(event_industry) & base["liquidity_quintile"].eq(event_liq)] if {"industry_id", "liquidity_quintile"}.issubset(base.columns) else pd.DataFrame()
        if len(same_both) >= 30:
            scope_name, scope = "same_industry_same_liquidity", same_both
        elif len(same_industry) >= 30:
            scope_name, scope = "same_industry_only", same_industry
        elif len(same_liquidity) >= 30:
            scope_name, scope = "same_liquidity_only", same_liquidity
        else:
            scope_name, scope = "same_day_pit_universe", base
        if base.empty or scope.empty:
            status = "blocked_missing_comparator_price"
        elif scope_name == "same_day_pit_universe" and len(scope) < 100:
            status = "blocked_insufficient_comparator"
        else:
            status = "comparable"
        scope_mean = safe_mean(scope["candidate_net_return"]) if not scope.empty else np.nan
        scope_median = float(scope["candidate_net_return"].median()) if not scope.empty else np.nan
        same_day_mean = safe_mean(base["candidate_net_return"]) if not base.empty else np.nan
        industry_mean = safe_mean(same_industry["candidate_net_return"]) if not same_industry.empty else np.nan
        liquidity_mean = safe_mean(same_liquidity["candidate_net_return"]) if not same_liquidity.empty else np.nan
        idx_entry = index_open.get(entry_date, np.nan)
        idx_exit = index_open.get(exit_date, np.nan)
        if finite(idx_entry) and finite(idx_exit) and float(idx_entry) > 0:
            idx_return = float(idx_exit) * (1.0 - float(record.sell_cost_bps) / 10000.0) / (float(idx_entry) * (1.0 + float(record.buy_cost_bps) / 10000.0)) - 1.0
        else:
            idx_return = np.nan
        rows.append(
            {
                "canonical_unit_id": record.canonical_unit_id,
                "event_key": record.event_key,
                "horizon": record.horizon,
                "split": record.split,
                "instrument_id": record.instrument_id,
                "signal_date": signal_date,
                "entry_execution_date": entry_date,
                "exit_execution_date": exit_date,
                "candidate_scope_0_count": len(base),
                "same_industry_same_liquidity_count": len(same_both),
                "same_industry_only_count": len(same_industry),
                "same_liquidity_only_count": len(same_liquidity),
                "same_day_pit_universe_count": len(base),
                "primary_comparator_scope": scope_name,
                "matched_comparator_count": len(scope),
                "matched_comparator_net_return": scope_mean,
                "matched_comparator_net_return_median": scope_median,
                "matched_delta_return": record.net_return - scope_mean if finite(scope_mean) else np.nan,
                "matched_delta_return_vs_comparator_median": record.net_return - scope_median if finite(scope_median) else np.nan,
                "matched_comparator_status": status,
                "same_day_universe_delta_return": record.net_return - same_day_mean if finite(same_day_mean) else np.nan,
                "industry_only_delta_return": record.net_return - industry_mean if finite(industry_mean) else np.nan,
                "liquidity_only_delta_return": record.net_return - liquidity_mean if finite(liquidity_mean) else np.nan,
                "SH000300_net_return": idx_return,
                "SH000300_delta_return": record.net_return - idx_return if finite(idx_return) else np.nan,
                "fallback_comparator_used": scope_name == "same_day_pit_universe",
            }
        )
    comparator = pd.DataFrame(rows)
    if comparator.empty:
        comparator = pd.DataFrame(columns=["canonical_unit_id", "event_key", "horizon", "split", "instrument_id", "matched_comparator_status"])
    r01.write_parquet(comparator, paths.cache_dir / "r03_matched_comparator_panel.parquet")
    write_comparator_audits(paths, comparator)
    return comparator


def write_comparator_audits(paths: r01.Paths, comparator: pd.DataFrame) -> None:
    scope = comparator.groupby(["canonical_unit_id", "horizon", "split", "primary_comparator_scope"], dropna=False).size().reset_index(name="event_count") if not comparator.empty else pd.DataFrame()
    denom = comparator.groupby(["canonical_unit_id", "horizon", "split", "matched_comparator_status"], dropna=False).size().reset_index(name="event_count") if not comparator.empty else pd.DataFrame()
    fallback = comparator.groupby(["canonical_unit_id", "horizon", "split"], dropna=False)["fallback_comparator_used"].mean().reset_index(name="fallback_comparator_share") if not comparator.empty else pd.DataFrame()
    if not fallback.empty:
        fallback["weak_comparator_quality"] = fallback["fallback_comparator_share"] > 0.30
    r01.write_csv(scope, paths.reports_dir / "r03_comparator_scope_audit.csv")
    r01.write_csv(denom, paths.reports_dir / "r03_relative_denominator_audit.csv")
    r01.write_csv(fallback, paths.reports_dir / "r03_comparator_fallback_quality_audit.csv")


def top_n_share(df: pd.DataFrame, column: str, n: int) -> float:
    return r01.top_n_share(df, column, n)


def contribution_share(df: pd.DataFrame, key: str, value_col: str, n: int = 1) -> float:
    return r01.contribution_share(df, key, value_col, n)


def build_baseline_date_comparison(
    config: dict[str, Any],
    paths: r01.Paths,
    primary_event: pd.DataFrame,
    execution: pd.DataFrame,
    baseline: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    min_count = int(config["frozen_formula_constants"]["paired_downside_baseline_min_complete_constituents_per_dh"])
    generated_dates = sorted(pd.to_datetime(primary_event["signal_date"]).dt.normalize().unique()) if not primary_event.empty else []
    for horizon in HORIZON_LABELS:
        for date in generated_dates:
            date = pd.Timestamp(date)
            event_slice = primary_event.loc[pd.to_datetime(primary_event["signal_date"]).dt.normalize().eq(date)]
            split = str(event_slice.iloc[0]["split"]) if not event_slice.empty else ""
            primary_complete = execution.loc[
                execution["horizon"].eq(horizon)
                & pd.to_datetime(execution["signal_date"]).dt.normalize().eq(date)
                & execution["execution_status"].eq("complete_executable")
            ]
            baseline_date = baseline.loc[
                baseline["horizon"].eq(horizon)
                & pd.to_datetime(baseline["signal_date"]).dt.normalize().eq(date)
            ] if not baseline.empty else pd.DataFrame()
            broad_complete = baseline_date.loc[
                baseline_date.get("is_broad_liquid_baseline", pd.Series(False, index=baseline_date.index)).astype(bool)
                & baseline_date["execution_status"].eq("complete_executable")
            ] if not baseline_date.empty else pd.DataFrame()
            paired_complete = baseline_date.loc[
                baseline_date.get("is_paired_nonselected_downside_baseline", pd.Series(False, index=baseline_date.index)).astype(bool)
                & baseline_date["execution_status"].eq("complete_executable")
            ] if not baseline_date.empty else pd.DataFrame()
            primary_decision = len(primary_complete) > 0
            baseline_count = len(paired_complete)
            if not primary_decision:
                status = "not_applicable_no_primary_complete_event"
            elif baseline_count >= min_count:
                status = "comparable"
            else:
                status = "blocked_insufficient_baseline_constituents"
            primary_mean = safe_mean(primary_complete["net_return"])
            paired_mean = safe_mean(paired_complete["net_return"])
            broad_mean = safe_mean(broad_complete["net_return"])
            rows.append(
                {
                    "canonical_unit_id": PRIMARY_UNIT,
                    "horizon": horizon,
                    "split": split,
                    "weekly_observation_date": date,
                    "primary_decision_observation_date": primary_decision,
                    "primary_complete_event_count": len(primary_complete),
                    "primary_date_equal_weight_return": primary_mean,
                    "broad_liquid_baseline_executable_constituent_count": len(broad_complete),
                    "broad_liquid_baseline_date_equal_weight_return": broad_mean,
                    "baseline_executable_constituent_count": baseline_count,
                    "baseline_comparison_status": status,
                    "baseline_date_equal_weight_return": paired_mean,
                    "selection_lift_vs_baseline": primary_mean - paired_mean if finite(primary_mean) and finite(paired_mean) else np.nan,
                    "primary_date_loss": bool(finite(primary_mean) and primary_mean < 0),
                    "baseline_date_loss": bool(finite(paired_mean) and paired_mean < 0),
                    "broad_liquid_baseline_date_loss": bool(finite(broad_mean) and broad_mean < 0),
                }
            )
    comparison = pd.DataFrame(rows)
    r01.write_csv(comparison, paths.reports_dir / "r03_baseline_date_comparison.csv")
    return comparison


def date_level_rows(joined: pd.DataFrame) -> pd.DataFrame:
    rows = []
    complete_all = joined.loc[joined["execution_status"].eq("complete_executable")].copy()
    for (unit, horizon, split, date), group in complete_all.groupby(["canonical_unit_id", "horizon", "split", "signal_date"], dropna=False):
        comparable = group.loc[group["matched_comparator_status"].eq("comparable")]
        rows.append(
            {
                "canonical_unit_id": unit,
                "horizon": horizon,
                "split": split,
                "weekly_observation_date": pd.Timestamp(date),
                "calendar_year": pd.Timestamp(date).year if pd.notna(date) else 0,
                "complete_event_count": len(group),
                "date_equal_weight_net_return": safe_mean(group["net_return"]),
                "date_equal_weight_matched_delta_return": safe_mean(comparable["matched_delta_return"]),
                "positive_net_date": bool(safe_mean(group["net_return"]) > 0) if len(group) else False,
                "positive_matched_delta_date": bool(safe_mean(comparable["matched_delta_return"]) > 0) if len(comparable) else False,
            }
        )
    return pd.DataFrame(rows)


def build_year_summary(joined: pd.DataFrame, date_rows: pd.DataFrame, baseline_date: pd.DataFrame) -> pd.DataFrame:
    rows = []
    joined = joined.copy()
    joined["calendar_year"] = pd.to_datetime(joined["signal_date"]).dt.year
    for (unit, horizon, split, year), group in joined.groupby(["canonical_unit_id", "horizon", "split", "calendar_year"], dropna=False):
        complete = group.loc[group["execution_status"].eq("complete_executable")]
        if complete.empty:
            continue
        comparable = complete.loc[complete["matched_comparator_status"].eq("comparable")]
        drows = date_rows.loc[
            date_rows["canonical_unit_id"].eq(unit)
            & date_rows["horizon"].eq(horizon)
            & date_rows["split"].eq(split)
            & date_rows["calendar_year"].eq(year)
        ]
        brows = baseline_date.loc[
            baseline_date["horizon"].eq(horizon)
            & baseline_date["split"].eq(split)
            & pd.to_datetime(baseline_date["weekly_observation_date"]).dt.year.eq(year)
            & baseline_date["baseline_comparison_status"].eq("comparable")
        ] if not baseline_date.empty else pd.DataFrame()
        rows.append(
            {
                "canonical_unit_id": unit,
                "horizon": horizon,
                "split": split,
                "calendar_year": int(year) if pd.notna(year) else 0,
                "signal_event_count": len(group),
                "complete_event_count": len(complete),
                "complete_event_share": safe_share(len(complete), len(group)),
                "mean_net_return": safe_mean(complete["net_return"]),
                "median_net_return": float(complete["net_return"].median()) if len(complete) else np.nan,
                "p10_net_return": safe_quantile(complete["net_return"], 0.10),
                "loss_rate": safe_mean(complete["net_return"] < 0),
                "relative_comparable_event_share": safe_share(len(comparable), len(complete)),
                "mean_matched_delta_return": safe_mean(comparable["matched_delta_return"]),
                "median_matched_delta_return": float(comparable["matched_delta_return"].median()) if len(comparable) else np.nan,
                "p10_matched_delta_return": safe_quantile(comparable["matched_delta_return"], 0.10),
                "matched_loss_rate_delta": safe_mean(comparable["net_return"] < 0) - safe_mean(comparable["matched_comparator_net_return"] < 0) if len(comparable) else np.nan,
                "same_day_universe_delta_mean": safe_mean(comparable["same_day_universe_delta_return"]),
                "industry_only_delta_mean": safe_mean(comparable["industry_only_delta_return"]),
                "liquidity_only_delta_mean": safe_mean(comparable["liquidity_only_delta_return"]),
                "SH000300_delta_mean": safe_mean(comparable["SH000300_delta_return"]),
                "fallback_comparator_share": safe_mean(complete["primary_comparator_scope"].eq("same_day_pit_universe")) if len(complete) else 0.0,
                "decision_observation_date_count": len(drows),
                "date_weighted_mean_net_return": safe_mean(drows["date_equal_weight_net_return"]),
                "date_weighted_mean_matched_delta_return": safe_mean(drows["date_equal_weight_matched_delta_return"]),
                "baseline_comparable_observation_date_count": len(brows),
                "selection_lift_vs_baseline_mean": safe_mean(brows["selection_lift_vs_baseline"]),
                "year_gate_status": "complete" if len(complete) else "empty",
            }
        )
    return pd.DataFrame(rows)


def multi_comparator_stable(row: pd.Series, years: pd.DataFrame) -> bool:
    deltas = [
        row.get("mean_matched_delta_return", np.nan),
        row.get("same_day_universe_delta_mean", np.nan),
        row.get("industry_only_delta_mean", np.nan),
        row.get("liquidity_only_delta_mean", np.nan),
    ]
    positive_count = sum(finite(x) and float(x) > 0 for x in deltas)
    year_ok = True
    if years.empty:
        year_ok = False
    for _, year in years.iterrows():
        y_deltas = [
            year.get("mean_matched_delta_return", np.nan),
            year.get("same_day_universe_delta_mean", np.nan),
            year.get("industry_only_delta_mean", np.nan),
            year.get("liquidity_only_delta_mean", np.nan),
        ]
        if sum(finite(x) and float(x) >= -0.0025 for x in y_deltas) < 2:
            year_ok = False
    sh_only = positive_count == 0 and finite(row.get("SH000300_delta_mean", np.nan)) and float(row["SH000300_delta_mean"]) > 0
    return bool(bool_value(row.get("relative_positive", False)) and positive_count >= 3 and year_ok and not sh_only)


def compute_summary_rows(
    config: dict[str, Any],
    paths: r01.Paths,
    primary_event: pd.DataFrame,
    execution: pd.DataFrame,
    comparator: pd.DataFrame,
    baseline_date: pd.DataFrame,
    rank_audit: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    joined = execution.merge(comparator, on=["canonical_unit_id", "event_key", "horizon", "split", "instrument_id"], how="left", suffixes=("", "_comparator"))
    date_rows = date_level_rows(joined)
    year_summary = build_year_summary(joined, date_rows, baseline_date)
    constants = config["frozen_formula_constants"]
    min_baseline_dates = int(constants["baseline_lift_min_comparable_observation_date_count"])
    min_year_baseline_dates = int(constants["baseline_lift_min_year_comparable_observation_date_count"])
    rows = []
    for horizon in HORIZON_LABELS:
        for split in SPLITS:
            group = joined.loc[joined["horizon"].eq(horizon) & joined["split"].eq(split)]
            complete = group.loc[group["execution_status"].eq("complete_executable")]
            comparable = complete.loc[complete["matched_comparator_status"].eq("comparable")]
            years = year_summary.loc[year_summary["horizon"].eq(horizon) & year_summary["split"].eq(split)]
            nonempty_years = years.loc[years["complete_event_count"] > 0]
            year_count = int(len(nonempty_years))
            min_year = int(nonempty_years["complete_event_count"].min()) if len(nonempty_years) else 0
            drows = date_rows.loc[date_rows["horizon"].eq(horizon) & date_rows["split"].eq(split)]
            decision_count = int(len(drows))
            date_counts_by_year = drows.groupby("calendar_year").size() if not drows.empty else pd.Series(dtype=int)
            min_year_decision = int(date_counts_by_year.min()) if len(date_counts_by_year) else 0
            signal_count = len(group)
            complete_count = len(complete)
            fallback_share = safe_mean(complete["primary_comparator_scope"].eq("same_day_pit_universe")) if complete_count else 0.0
            weak_comparator_quality = fallback_share > 0.30
            event_sample_gate = complete_count >= 300 and safe_share(complete_count, signal_count) >= 0.95 and year_count == 2 and min_year >= 75
            date_sample_gate = decision_count >= 40 and min_year_decision >= 15
            sample_gate = event_sample_gate and date_sample_gate
            if sample_gate:
                sample_status = "sample_pass"
            elif event_sample_gate and not date_sample_gate:
                sample_status = "blocked_insufficient_date_independence_sample"
            elif complete_count >= 150:
                sample_status = "sample_limited_lead"
            else:
                sample_status = "blocked_insufficient_sample"
            top1_obs = top_n_share(complete, "signal_date", 1)
            top5_obs = top_n_share(complete, "signal_date", 5)
            concentration_gate = (
                top_n_share(complete, "instrument_id", 1) <= 0.05
                and top_n_share(complete, "instrument_id", 5) <= 0.20
                and top_n_share(complete, "industry_id", 1) <= 0.35
                and top_n_share(complete, "entry_execution_date", 1) <= 0.08
                and fallback_share <= 0.30
                and top1_obs <= 0.08
                and top5_obs <= 0.30
                and contribution_share(complete, "signal_date", "net_return", 1) <= 0.20
            )
            each_year_abs = bool((nonempty_years["mean_net_return"] >= -0.0025).all()) if year_count == 2 else False
            each_year_rel = bool((nonempty_years["mean_matched_delta_return"] >= -0.0025).all()) if year_count == 2 else False
            each_year_date_abs = bool((nonempty_years["date_weighted_mean_net_return"] >= -0.0025).all()) if year_count == 2 else False
            each_year_date_rel = bool((nonempty_years["date_weighted_mean_matched_delta_return"] >= -0.0025).all()) if year_count == 2 else False
            mean_net = safe_mean(complete["net_return"])
            median_net = float(complete["net_return"].median()) if complete_count else np.nan
            p10_net = safe_quantile(complete["net_return"], 0.10)
            loss_rate = safe_mean(complete["net_return"] < 0) if complete_count else np.nan
            mean_delta = safe_mean(comparable["matched_delta_return"])
            median_delta = float(comparable["matched_delta_return"].median()) if len(comparable) else np.nan
            p10_delta = safe_quantile(comparable["matched_delta_return"], 0.10)
            matched_loss_delta = safe_mean(comparable["net_return"] < 0) - safe_mean(comparable["matched_comparator_net_return"] < 0) if len(comparable) else np.nan
            date_weighted_net = safe_mean(drows["date_equal_weight_net_return"])
            date_weighted_delta = safe_mean(drows["date_equal_weight_matched_delta_return"])
            date_independence_gate = bool(
                split == "validation"
                and decision_count >= 40
                and min_year_decision >= 15
                and top1_obs <= 0.08
                and top5_obs <= 0.30
                and date_weighted_net > 0
                and date_weighted_delta > 0
                and each_year_date_abs
                and each_year_date_rel
                and safe_mean(drows["date_equal_weight_net_return"] > 0) >= 0.50
                and safe_mean(drows["date_equal_weight_matched_delta_return"] > 0) >= 0.50
            )
            absolute_positive = bool(
                split == "validation"
                and mean_net > 0
                and median_net >= -0.0025
                and p10_net >= -0.0800
                and loss_rate <= 0.55
                and each_year_abs
            )
            relative_positive = bool(
                split == "validation"
                and safe_share(len(comparable), complete_count) >= 0.95
                and safe_share(int(complete["matched_comparator_status"].eq("blocked_insufficient_comparator").sum()), complete_count) <= 0.05
                and fallback_share <= 0.30
                and mean_delta > 0
                and each_year_rel
                and sum(
                    [
                        finite(median_delta) and median_delta >= 0,
                        finite(p10_delta) and p10_delta >= 0,
                        finite(matched_loss_delta) and matched_loss_delta <= 0,
                    ]
                )
                >= 2
                and not weak_comparator_quality
            )
            brows = baseline_date.loc[baseline_date["horizon"].eq(horizon) & baseline_date["split"].eq(split)] if not baseline_date.empty else pd.DataFrame()
            comparable_brows = brows.loc[brows["baseline_comparison_status"].eq("comparable")] if not brows.empty else pd.DataFrame()
            baseline_count = len(comparable_brows)
            baseline_by_year = comparable_brows.assign(calendar_year=pd.to_datetime(comparable_brows["weekly_observation_date"]).dt.year).groupby("calendar_year").size() if len(comparable_brows) else pd.Series(dtype=int)
            min_year_baseline = int(baseline_by_year.min()) if len(baseline_by_year) else 0
            baseline_year_mean = comparable_brows.assign(calendar_year=pd.to_datetime(comparable_brows["weekly_observation_date"]).dt.year).groupby("calendar_year")["selection_lift_vs_baseline"].mean() if len(comparable_brows) else pd.Series(dtype=float)
            baseline_evaluable = baseline_count >= min_baseline_dates and min_year_baseline >= min_year_baseline_dates
            selection_lift_mean = safe_mean(comparable_brows["selection_lift_vs_baseline"])
            selection_lift_median = float(comparable_brows["selection_lift_vs_baseline"].median()) if len(comparable_brows) else np.nan
            selection_lift_p10 = safe_quantile(comparable_brows["selection_lift_vs_baseline"], 0.10)
            selection_lift_loss_delta = safe_mean(comparable_brows["primary_date_loss"]) - safe_mean(comparable_brows["baseline_date_loss"]) if len(comparable_brows) else np.nan
            baseline_year_ok = bool((baseline_year_mean >= -0.0025).all()) if len(baseline_year_mean) else False
            baseline_shape_ok = (
                sum(
                    [
                        finite(selection_lift_median) and selection_lift_median >= 0,
                        finite(selection_lift_p10) and selection_lift_p10 >= 0,
                        finite(selection_lift_loss_delta) and selection_lift_loss_delta <= 0,
                    ]
                )
                >= 2
            )
            baseline_lift_gate = bool(baseline_evaluable and split == "validation" and selection_lift_mean > 0 and baseline_year_ok and baseline_shape_ok)
            rank_dates = rank_audit.loc[rank_audit["split"].eq(split)] if not rank_audit.empty else pd.DataFrame()
            event_dates = pd.to_datetime(group["signal_date"]).dt.normalize().dropna().unique() if not group.empty else []
            rank_for_events = rank_audit.loc[pd.to_datetime(rank_audit.get("weekly_observation_date", pd.Series(dtype=object))).dt.normalize().isin(event_dates)] if not rank_audit.empty and len(event_dates) else pd.DataFrame()
            baseline_counts = brows["baseline_executable_constituent_count"] if not brows.empty and "baseline_executable_constituent_count" in brows else pd.Series(dtype=float)
            row = {
                "canonical_unit_id": PRIMARY_UNIT,
                "unit_role": "primary downside volatility shock rebound exposure unit",
                "horizon": horizon,
                "split": split,
                "weekly_observation_date_count": int(len(rank_dates)),
                "decision_observation_date_count": decision_count,
                "min_year_decision_observation_date_count": min_year_decision,
                "events_per_observation_date_mean": safe_mean(drows["complete_event_count"]),
                "events_per_observation_date_median": float(drows["complete_event_count"].median()) if len(drows) else np.nan,
                "events_per_observation_date_p95": safe_quantile(drows["complete_event_count"], 0.95),
                "unique_instrument_count": int(complete["instrument_id"].nunique()) if complete_count else 0,
                "mean_avg_money20_at_D": safe_mean(complete["avg_money20_D"]),
                "mean_ret5_at_D": safe_mean(complete["ret5"]),
                "median_ret5_at_D": float(complete["ret5"].median()) if complete_count else np.nan,
                "mean_realized_vol10_at_D": safe_mean(complete["realized_vol10"]),
                "mean_realized_vol10_rank_pct_at_D": safe_mean(complete["rank_pct_realized_vol10"]),
                "mean_stabilization_return_at_D": safe_mean(complete["stabilization_return_at_D"]),
                "mean_money_repair_ratio_at_D": safe_mean(complete["money_repair_ratio_at_D"]),
                "share_of_event_dates_with_zero_eligible_instruments": safe_mean(rank_dates["eligible_signal_count"].eq(0)) if len(rank_dates) else 0.0,
                "date_weighted_mean_net_return": date_weighted_net,
                "date_weighted_median_net_return": float(drows["date_equal_weight_net_return"].median()) if len(drows) else np.nan,
                "date_weighted_mean_matched_delta_return": date_weighted_delta,
                "positive_observation_date_share_net": safe_mean(drows["date_equal_weight_net_return"] > 0) if len(drows) else 0.0,
                "positive_observation_date_share_matched_delta": safe_mean(drows["date_equal_weight_matched_delta_return"] > 0) if len(drows) else 0.0,
                "top1_observation_date_event_share": top1_obs,
                "top5_observation_date_event_share": top5_obs,
                "top1_observation_date_profit_contribution_share": contribution_share(complete, "signal_date", "net_return", 1),
                "vol_rank_cross_section_count_min": int(rank_for_events["vol_rank_cross_section_count"].min()) if len(rank_for_events) else 0,
                "vol_rank_cross_section_count_median": float(rank_for_events["vol_rank_cross_section_count"].median()) if len(rank_for_events) else np.nan,
                "signal_event_count": signal_count,
                "entry_executable_count": int(group["entry_execution_date"].notna().sum()) if not group.empty else 0,
                "complete_event_count": complete_count,
                "blocked_event_count": signal_count - complete_count,
                "complete_event_share": safe_share(complete_count, signal_count),
                "mean_gross_return": safe_mean(complete["gross_return"]),
                "mean_net_return": mean_net,
                "median_net_return": median_net,
                "p10_net_return": p10_net,
                "p25_net_return": safe_quantile(complete["net_return"], 0.25),
                "p75_net_return": safe_quantile(complete["net_return"], 0.75),
                "p90_net_return": safe_quantile(complete["net_return"], 0.90),
                "loss_rate": loss_rate,
                "relative_comparable_event_share": safe_share(len(comparable), complete_count),
                "blocked_insufficient_comparator_count": int(complete["matched_comparator_status"].eq("blocked_insufficient_comparator").sum()) if complete_count else 0,
                "fallback_comparator_share": fallback_share,
                "mean_matched_delta_return": mean_delta,
                "median_matched_delta_return": median_delta,
                "p10_matched_delta_return": p10_delta,
                "matched_loss_rate_delta": matched_loss_delta,
                "matched_comparator_count_mean": safe_mean(complete["matched_comparator_count"]),
                "same_day_universe_delta_mean": safe_mean(comparable["same_day_universe_delta_return"]),
                "industry_only_delta_mean": safe_mean(comparable["industry_only_delta_return"]),
                "liquidity_only_delta_mean": safe_mean(comparable["liquidity_only_delta_return"]),
                "SH000300_delta_mean": safe_mean(comparable["SH000300_delta_return"]),
                "top1_instrument_event_share": top_n_share(complete, "instrument_id", 1),
                "top5_instrument_event_share": top_n_share(complete, "instrument_id", 5),
                "top1_industry_event_share": top_n_share(complete, "industry_id", 1),
                "top5_industry_event_share": top_n_share(complete, "industry_id", 5),
                "top1_entry_date_event_share": top_n_share(complete, "entry_execution_date", 1),
                "year_count": year_count,
                "min_year_complete_event_count": min_year,
                "sample_status": sample_status,
                "sample_gate_pass": sample_gate,
                "concentration_gate_pass": concentration_gate,
                "date_independence_gate": date_independence_gate,
                "absolute_positive": absolute_positive,
                "relative_positive": relative_positive,
                "weak_comparator_quality": weak_comparator_quality,
                "baseline_date_weighted_mean_net_return": safe_mean(comparable_brows["baseline_date_equal_weight_return"]),
                "baseline_comparable_observation_date_count": baseline_count,
                "min_year_baseline_comparable_observation_date_count": min_year_baseline,
                "baseline_lift_evaluable": baseline_evaluable,
                "baseline_executable_constituent_count_min": int(baseline_counts.min()) if len(baseline_counts) else 0,
                "baseline_executable_constituent_count_p10": safe_quantile(baseline_counts, 0.10),
                "baseline_executable_constituent_count_median": float(baseline_counts.median()) if len(baseline_counts) else np.nan,
                "baseline_executable_constituent_count_mean": safe_mean(baseline_counts),
                "selection_lift_vs_baseline_mean": selection_lift_mean,
                "selection_lift_vs_baseline_median": selection_lift_median,
                "selection_lift_vs_baseline_p10": selection_lift_p10,
                "selection_lift_loss_rate_delta": selection_lift_loss_delta,
                "broad_liquid_baseline_date_weighted_mean_net_return": safe_mean(brows["broad_liquid_baseline_date_equal_weight_return"]) if len(brows) else np.nan,
                "baseline_lift_gate": baseline_lift_gate,
                "horizon_pass": sample_gate and concentration_gate and date_independence_gate and absolute_positive and relative_positive,
                "strongly_negative": complete_count >= 150 and mean_net < -0.0025 and mean_delta < -0.0025,
                "adjacent_horizon_shape_status": "not_applicable",
                "multi_comparator_relative_stable": False,
                "robustness_confirmed": False,
                "robustness_baseline_lift_evaluable": False,
                "robustness_selection_lift_vs_baseline_mean": np.nan,
            }
            rows.append(row)
    summary = pd.DataFrame(rows)
    for idx, row in summary.iterrows():
        if row["horizon"] in {"H5", "H20"} and row["split"] == "validation":
            adjacent_evaluable = (
                int(row["complete_event_count"]) >= 150
                and float(row["complete_event_share"]) >= 0.90
                and finite(row["mean_net_return"])
                and finite(row["mean_matched_delta_return"])
            )
            if not adjacent_evaluable:
                summary.at[idx, "adjacent_horizon_shape_status"] = "adjacent_horizon_not_evaluable"
            elif bool_value(row["strongly_negative"]):
                summary.at[idx, "adjacent_horizon_shape_status"] = "strongly_negative"
            else:
                summary.at[idx, "adjacent_horizon_shape_status"] = "adjacent_horizon_clean"
    for idx, row in summary.iterrows():
        if row["split"] == "validation":
            years = year_summary.loc[year_summary["horizon"].eq(row["horizon"]) & year_summary["split"].eq("validation")]
            summary.at[idx, "multi_comparator_relative_stable"] = multi_comparator_stable(row, years)
            robust = r03_robustness_criteria(summary, year_summary, row["horizon"])
            summary.at[idx, "robustness_confirmed"] = robust["robustness_confirmed"]
            summary.at[idx, "robustness_baseline_lift_evaluable"] = robust["robustness_baseline_lift_evaluable"]
            summary.at[idx, "robustness_selection_lift_vs_baseline_mean"] = robust["robustness_selection_lift_vs_baseline_mean"]

    r01.write_csv(year_summary, paths.reports_dir / "r03_event_summary_by_unit_horizon_year.csv")
    r01.write_csv(summary, paths.reports_dir / "r03_event_summary_by_unit_horizon_split.csv")
    write_gate_audits(paths, summary)
    write_decompositions(paths, joined)
    return summary, year_summary


def r03_robustness_criteria(summary: pd.DataFrame, year_summary: pd.DataFrame, horizon: str) -> dict[str, Any]:
    row = summary.loc[summary["horizon"].eq(horizon) & summary["split"].eq("robustness")]
    if row.empty:
        return {"robustness_confirmed": False, "robustness_baseline_lift_evaluable": False, "robustness_selection_lift_vs_baseline_mean": np.nan}
    r = row.iloc[0]
    years = year_summary.loc[year_summary["horizon"].eq(horizon) & year_summary["split"].eq("robustness")]
    nonempty = years.loc[years["complete_event_count"] > 0]
    each_abs = bool((nonempty["mean_net_return"] >= -0.0050).all()) if int(r["year_count"]) == 2 else False
    each_rel = bool((nonempty["mean_matched_delta_return"] >= -0.0050).all()) if int(r["year_count"]) == 2 else False
    baseline_eval = bool_value(r.get("baseline_lift_evaluable", False))
    selection_lift_mean = r.get("selection_lift_vs_baseline_mean", np.nan)
    confirmed = bool(
        int(r["complete_event_count"]) >= 300
        and float(r["complete_event_share"]) >= 0.95
        and int(r["year_count"]) == 2
        and int(r["min_year_complete_event_count"]) >= 75
        and int(r["decision_observation_date_count"]) >= 40
        and int(r["min_year_decision_observation_date_count"]) >= 15
        and float(r["relative_comparable_event_share"]) >= 0.95
        and safe_share(float(r["blocked_insufficient_comparator_count"]), float(r["complete_event_count"])) <= 0.05
        and float(r["mean_net_return"]) >= -0.0025
        and float(r["median_net_return"]) >= -0.0050
        and float(r["p10_net_return"]) >= -0.0900
        and float(r["loss_rate"]) <= 0.58
        and float(r["mean_matched_delta_return"]) >= -0.0025
        and each_abs
        and each_rel
        and float(r["top1_instrument_event_share"]) <= 0.05
        and float(r["top5_instrument_event_share"]) <= 0.20
        and float(r["top1_industry_event_share"]) <= 0.35
        and float(r["top1_observation_date_event_share"]) <= 0.08
        and float(r["top5_observation_date_event_share"]) <= 0.30
        and float(r["fallback_comparator_share"]) <= 0.30
        and baseline_eval
        and finite(selection_lift_mean)
        and float(selection_lift_mean) >= -0.0025
    )
    return {
        "robustness_confirmed": confirmed,
        "robustness_baseline_lift_evaluable": baseline_eval,
        "robustness_selection_lift_vs_baseline_mean": selection_lift_mean,
    }


def write_gate_audits(paths: r01.Paths, summary: pd.DataFrame) -> None:
    r01.write_csv(summary[["canonical_unit_id", "horizon", "split", "complete_event_count", "complete_event_share", "year_count", "min_year_complete_event_count", "decision_observation_date_count", "min_year_decision_observation_date_count", "sample_status", "sample_gate_pass"]], paths.reports_dir / "r03_sample_gate_audit.csv")
    r01.write_csv(summary[["canonical_unit_id", "horizon", "split", "top1_instrument_event_share", "top5_instrument_event_share", "top1_industry_event_share", "top1_entry_date_event_share", "fallback_comparator_share", "top1_observation_date_event_share", "top5_observation_date_event_share", "top1_observation_date_profit_contribution_share", "concentration_gate_pass"]], paths.reports_dir / "r03_concentration_gate_audit.csv")
    r01.write_csv(summary[["canonical_unit_id", "horizon", "split", "mean_net_return", "median_net_return", "p10_net_return", "loss_rate", "absolute_positive"]], paths.reports_dir / "r03_absolute_gate_audit.csv")
    r01.write_csv(summary[["canonical_unit_id", "horizon", "split", "relative_comparable_event_share", "blocked_insufficient_comparator_count", "fallback_comparator_share", "mean_matched_delta_return", "median_matched_delta_return", "p10_matched_delta_return", "matched_loss_rate_delta", "weak_comparator_quality", "relative_positive"]], paths.reports_dir / "r03_relative_gate_audit.csv")
    r01.write_csv(summary[["canonical_unit_id", "horizon", "split", "decision_observation_date_count", "min_year_decision_observation_date_count", "date_weighted_mean_net_return", "date_weighted_mean_matched_delta_return", "positive_observation_date_share_net", "positive_observation_date_share_matched_delta", "top1_observation_date_event_share", "top5_observation_date_event_share", "date_independence_gate"]], paths.reports_dir / "r03_date_independence_audit.csv")
    r01.write_csv(summary[["canonical_unit_id", "horizon", "split", "baseline_comparable_observation_date_count", "min_year_baseline_comparable_observation_date_count", "baseline_lift_evaluable", "baseline_executable_constituent_count_min", "baseline_executable_constituent_count_p10", "baseline_executable_constituent_count_median", "baseline_executable_constituent_count_mean", "selection_lift_vs_baseline_mean", "selection_lift_vs_baseline_median", "selection_lift_vs_baseline_p10", "selection_lift_loss_rate_delta", "broad_liquid_baseline_date_weighted_mean_net_return", "baseline_lift_gate"]], paths.reports_dir / "r03_baseline_lift_audit.csv")
    r01.write_csv(summary[["canonical_unit_id", "horizon", "split", "robustness_confirmed", "robustness_baseline_lift_evaluable", "robustness_selection_lift_vs_baseline_mean"]], paths.reports_dir / "r03_robustness_confirmation_audit.csv")
    r01.write_csv(summary[["canonical_unit_id", "horizon", "split", "horizon_pass", "baseline_lift_gate", "strongly_negative", "adjacent_horizon_shape_status"]], paths.reports_dir / "r03_horizon_shape_audit.csv")
    r01.write_csv(summary[["canonical_unit_id", "horizon", "split", "mean_matched_delta_return", "same_day_universe_delta_mean", "industry_only_delta_mean", "liquidity_only_delta_mean", "SH000300_delta_mean", "relative_positive", "multi_comparator_relative_stable"]], paths.reports_dir / "r03_multi_comparator_relative_audit.csv")


def write_decompositions(paths: r01.Paths, joined: pd.DataFrame) -> None:
    complete = joined.loc[joined["execution_status"].eq("complete_executable")].copy()
    regime_beta = decomposition_rows(complete, ["market_state", "beta_bucket", "industry_id", "liquidity_quintile"])
    shock_state = decomposition_rows(complete, ["ret5_value_bucket_at_D", "rank_pct_realized_vol10_bucket_at_D", "stabilization_return_bucket_at_D", "money_repair_ratio_bucket_at_D"])
    r01.write_csv(regime_beta, paths.reports_dir / "r03_regime_beta_decomposition.csv")
    r01.write_csv(shock_state, paths.reports_dir / "r03_shock_state_decomposition.csv")


def decomposition_rows(df: pd.DataFrame, axes: list[str]) -> pd.DataFrame:
    rows = []
    for axis in axes:
        if axis not in df:
            continue
        for (horizon, split, value), group in df.groupby(["horizon", "split", axis], dropna=False):
            comparable = group.loc[group["matched_comparator_status"].eq("comparable")]
            parent = df.loc[df["horizon"].eq(horizon) & df["split"].eq(split)]
            rows.append(
                {
                    "canonical_unit_id": PRIMARY_UNIT,
                    "horizon": horizon,
                    "split": split,
                    "decomposition_axis": axis,
                    "decomposition_value": value if pd.notna(value) else "UNKNOWN",
                    "complete_event_count": len(group),
                    "mean_net_return": safe_mean(group["net_return"]),
                    "median_net_return": float(group["net_return"].median()) if len(group) else np.nan,
                    "p10_net_return": safe_quantile(group["net_return"], 0.10),
                    "loss_rate": safe_mean(group["net_return"] < 0),
                    "relative_comparable_event_share": safe_share(len(comparable), len(group)),
                    "mean_matched_delta_return": safe_mean(comparable["matched_delta_return"]),
                    "median_matched_delta_return": float(comparable["matched_delta_return"].median()) if len(comparable) else np.nan,
                    "p10_matched_delta_return": safe_quantile(comparable["matched_delta_return"], 0.10),
                    "matched_loss_rate_delta": safe_mean(comparable["net_return"] < 0) - safe_mean(comparable["matched_comparator_net_return"] < 0) if len(comparable) else np.nan,
                    "event_share": safe_share(len(group), len(parent)),
                    "net_return_contribution_share": contribution_share(group, axis, "net_return", 1),
                    "matched_delta_contribution_share": contribution_share(comparable, axis, "matched_delta_return", 1),
                }
            )
    return pd.DataFrame(rows)


def build_summaries(
    config: dict[str, Any],
    paths: r01.Paths,
    primary_event: pd.DataFrame,
    execution: pd.DataFrame,
    comparator: pd.DataFrame,
    baseline: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    baseline_date = build_baseline_date_comparison(config, paths, primary_event, execution, baseline)
    rank_audit = pd.read_csv(paths.reports_dir / "r03_vol_rank_cross_section_audit.csv", parse_dates=["weekly_observation_date"])
    summary, year_summary = compute_summary_rows(config, paths, primary_event, execution, comparator, baseline_date, rank_audit)
    return summary, year_summary, baseline_date


def build_right_tail(config: dict[str, Any], paths: r01.Paths, feature: pd.DataFrame, execution: pd.DataFrame) -> pd.DataFrame:
    calendar = r01.load_calendar(config)
    pos_map = r01.trading_day_pos(calendar)
    feature_lookup = r01.make_feature_lookup(feature)
    complete = execution.loc[execution["execution_status"].eq("complete_executable")].copy()
    pivot = complete.pivot_table(index=["canonical_unit_id", "event_key", "instrument_id", "split", "entry_execution_date", "entry_price"], columns="horizon", values="net_return", aggfunc="first").reset_index() if not complete.empty else pd.DataFrame()
    rows = []
    constants = config["frozen_formula_constants"]
    for record in pivot.itertuples(index=False):
        entry_date = pd.Timestamp(record.entry_execution_date)
        entry_price = float(record.entry_price)
        start_pos = pos_map.get(entry_date)
        status = "blocked_missing_forward_path"
        path_status = "blocked_missing_forward_path"
        max_gain = np.nan
        first20 = pd.NaT
        first50 = pd.NaT
        first20_offset = np.nan
        first50_offset = np.nan
        post_h20 = np.nan
        if start_pos is not None:
            end_pos = start_pos + int(constants["right_tail_horizon_trading_days"])
            if end_pos >= len(calendar):
                path_status = "censored_provider_end"
                status = "censored_not_evaluable"
            else:
                end_date = pd.Timestamp(calendar[end_pos])
                if split_for_date(config, end_date) == record.split:
                    path_status = "complete_same_split_120d"
                elif split_for_date(config, end_date) == "provider_tail":
                    path_status = "censored_provider_end"
                else:
                    path_status = "complete_cross_split_120d_readonly"
                dates = [pd.Timestamp(calendar[idx]) for idx in range(start_pos, end_pos + 1)]
                path_rows = []
                for idx, date in enumerate(dates):
                    info = feature_lookup.get((record.instrument_id, date))
                    if info is not None and finite(info.get("close")):
                        path_rows.append((date, idx, float(info["close"]) / entry_price - 1.0))
                if path_rows and path_status in {"complete_same_split_120d", "complete_cross_split_120d_readonly"}:
                    gains = pd.DataFrame(path_rows, columns=["date", "offset", "gain"])
                    max_gain = float(gains["gain"].max())
                    hit20 = gains.loc[gains["gain"] >= float(constants["right_tail_plus20_threshold"])]
                    hit50 = gains.loc[gains["gain"] >= float(constants["right_tail_plus50_threshold"])]
                    if not hit20.empty:
                        first20 = pd.Timestamp(hit20.iloc[0]["date"])
                        first20_offset = int(hit20.iloc[0]["offset"])
                    if not hit50.empty:
                        first50 = pd.Timestamp(hit50.iloc[0]["date"])
                        first50_offset = int(hit50.iloc[0]["offset"])
                    post = gains.loc[gains["offset"] > 20, "gain"]
                    post_h20 = float(post.max()) if len(post) else np.nan
                    if not hit50.empty:
                        status = "hit_plus50"
                    elif not hit20.empty:
                        status = "hit_plus20_only"
                    else:
                        status = "no_hit_complete"
                elif path_status.startswith("censored"):
                    status = "censored_not_evaluable"
        rows.append(
            {
                "canonical_unit_id": record.canonical_unit_id,
                "event_key": record.event_key,
                "instrument_id": record.instrument_id,
                "split": record.split,
                "entry_execution_date": entry_date,
                "entry_price": entry_price,
                "max_gain_120d": max_gain,
                "first_plus20_hit_date": first20,
                "first_plus20_hit_offset": first20_offset,
                "first_plus50_hit_date": first50,
                "first_plus50_hit_offset": first50_offset,
                "H5_net_return": getattr(record, "H5", np.nan),
                "H10_net_return": getattr(record, "H10", np.nan),
                "H20_net_return": getattr(record, "H20", np.nan),
                "post_H20_max_gain_to_H120": post_h20,
                "right_tail_status": status,
                "right_tail_path_status": path_status,
            }
        )
    panel = pd.DataFrame(rows)
    r01.write_parquet(panel, paths.cache_dir / "r03_right_tail_diagnostic_panel.parquet")
    readout = panel.groupby(["canonical_unit_id", "split", "right_tail_path_status", "right_tail_status"], dropna=False).size().reset_index(name="event_count") if not panel.empty else pd.DataFrame()
    censor = panel.groupby(["canonical_unit_id", "split", "right_tail_path_status"], dropna=False).size().reset_index(name="event_count") if not panel.empty else pd.DataFrame()
    r01.write_csv(readout, paths.reports_dir / "r03_right_tail_readout.csv")
    r01.write_csv(censor, paths.reports_dir / "r03_right_tail_censoring_audit.csv")
    return panel


def summary_row(summary: pd.DataFrame, horizon: str, split: str = "validation") -> pd.Series | None:
    row = summary.loc[summary["canonical_unit_id"].eq(PRIMARY_UNIT) & summary["horizon"].eq(horizon) & summary["split"].eq(split)]
    if row.empty:
        return None
    return row.iloc[0]


def h10_validated_pass(summary: pd.DataFrame) -> bool:
    row = summary_row(summary, "H10")
    return bool(
        row is not None
        and bool_value(row["sample_gate_pass"])
        and bool_value(row["concentration_gate_pass"])
        and bool_value(row["date_independence_gate"])
        and bool_value(row["absolute_positive"])
        and bool_value(row["relative_positive"])
    )


def stock_selection_supported(summary: pd.DataFrame, horizon: str = "H10") -> bool:
    row = summary_row(summary, horizon)
    return bool(row is not None and h10_validated_pass(summary) and bool_value(row["baseline_lift_gate"]))


def adjacent_status(summary: pd.DataFrame) -> str:
    h5 = summary_row(summary, "H5")
    h20 = summary_row(summary, "H20")
    rows = [r for r in [h5, h20] if r is not None]
    if any(bool_value(r["strongly_negative"]) for r in rows):
        return "adjacent_horizon_strongly_negative"
    if any(str(r["adjacent_horizon_shape_status"]) == "adjacent_horizon_not_evaluable" for r in rows):
        return "adjacent_horizon_not_evaluable"
    return "adjacent_horizon_clean"


def adjacent_clean(summary: pd.DataFrame) -> bool:
    return adjacent_status(summary) == "adjacent_horizon_clean"


def robustness_confirmed(summary: pd.DataFrame) -> bool:
    row = summary_row(summary, "H10")
    return bool(row is not None and bool_value(row["robustness_confirmed"]))


def baseline_not_evaluable_validation_lead(summary: pd.DataFrame) -> bool:
    row = summary_row(summary, "H10")
    return bool(row is not None and h10_validated_pass(summary) and not bool_value(row["baseline_lift_evaluable"]))


def relative_only_audit_supported(summary: pd.DataFrame) -> bool:
    row = summary_row(summary, "H10")
    return bool(
        row is not None
        and bool_value(row["sample_gate_pass"])
        and bool_value(row["concentration_gate_pass"])
        and bool_value(row["date_independence_gate"])
        and bool_value(row["relative_positive"])
        and bool_value(row["multi_comparator_relative_stable"])
        and bool_value(row["baseline_lift_gate"])
        and not bool_value(row["absolute_positive"])
    )


def relative_only_baseline_not_evaluable(summary: pd.DataFrame) -> bool:
    row = summary_row(summary, "H10")
    return bool(
        row is not None
        and bool_value(row["sample_gate_pass"])
        and bool_value(row["concentration_gate_pass"])
        and bool_value(row["date_independence_gate"])
        and bool_value(row["relative_positive"])
        and bool_value(row["multi_comparator_relative_stable"])
        and not bool_value(row["baseline_lift_evaluable"])
        and not bool_value(row["absolute_positive"])
    )


def absolute_only_baseline_not_evaluable(summary: pd.DataFrame) -> bool:
    row = summary_row(summary, "H10")
    return bool(
        row is not None
        and bool_value(row["sample_gate_pass"])
        and bool_value(row["concentration_gate_pass"])
        and bool_value(row["date_independence_gate"])
        and bool_value(row["absolute_positive"])
        and not bool_value(row["relative_positive"])
        and not bool_value(row["baseline_lift_evaluable"])
    )


def absolute_only_beta_or_market_rebound(summary: pd.DataFrame) -> bool:
    row = summary_row(summary, "H10")
    return bool(
        row is not None
        and bool_value(row["sample_gate_pass"])
        and bool_value(row["concentration_gate_pass"])
        and bool_value(row["date_independence_gate"])
        and bool_value(row["absolute_positive"])
        and not bool_value(row["relative_positive"])
        and bool_value(row["baseline_lift_evaluable"])
        and not bool_value(row["baseline_lift_gate"])
    )


def absolute_only_baseline_lift_no_relative_pass(summary: pd.DataFrame) -> bool:
    row = summary_row(summary, "H10")
    return bool(
        row is not None
        and bool_value(row["sample_gate_pass"])
        and bool_value(row["concentration_gate_pass"])
        and bool_value(row["date_independence_gate"])
        and bool_value(row["absolute_positive"])
        and not bool_value(row["relative_positive"])
        and bool_value(row["baseline_lift_gate"])
    )


def sample_limited_return_lead(summary: pd.DataFrame) -> bool:
    row = summary_row(summary, "H10")
    return bool(
        row is not None
        and str(row["sample_status"]) == "sample_limited_lead"
        and bool_value(row["concentration_gate_pass"])
        and bool_value(row["date_independence_gate"])
        and bool_value(row["absolute_positive"])
        and bool_value(row["relative_positive"])
    )


def horizon_specific_lead(summary: pd.DataFrame) -> bool:
    h10 = summary_row(summary, "H10")
    h10_pass = bool(h10 is not None and bool_value(h10["horizon_pass"]))
    if h10_pass:
        return False
    for horizon in ["H5", "H20"]:
        row = summary_row(summary, horizon)
        if row is not None and bool_value(row["horizon_pass"]) and bool_value(row["baseline_lift_gate"]):
            return True
    return False


def quadrant(row: pd.Series | None) -> str:
    if row is None:
        return "missing"
    return f"absolute_{str(bool_value(row['absolute_positive'])).lower()}__relative_{str(bool_value(row['relative_positive'])).lower()}"


def allowed_next(decision: str) -> tuple[str, str]:
    mapping = {
        "r03_downside_volatility_shock_rebound_supported_continue_research": (
            "R04 controlled discovery or holding diagnostic requirement",
            "portfolio allocator; hedged strategy; live trading; production approval",
        ),
        "r03_relative_rebound_edge_only_hedged_or_regime_audit_required": (
            "hedged / relative feasibility audit only",
            "long-only pass; market-neutral backtest; production strategy",
        ),
        "r03_downside_beta_or_market_rebound_only_no_selection_pass": (
            "downside basket beta / market rebound attribution",
            "stock-selection edge claim",
        ),
        "r03_absolute_rebound_only_baseline_lift_no_relative_pass": (
            "abs-only conflict lead disclosure",
            "continue research; matched-relative edge claim",
        ),
        "r03_baseline_not_evaluable_validation_lead": (
            "baseline comparability repair or explanation",
            "beta interpretation; search",
        ),
        "r03_unstable_validation_only_lead": (
            "validation / robustness drift explanation",
            "search",
        ),
        "r03_unstable_horizon_shape_no_search_allowed": (
            "horizon instability explanation",
            "single-horizon promotion",
        ),
        "r03_adjacent_horizon_not_evaluable_validation_lead": (
            "adjacent horizon evaluability review",
            "H10-only search",
        ),
        "r03_horizon_specific_lead_only_no_search_allowed": (
            "horizon-specific explanation",
            "best-horizon search",
        ),
        "r03_sample_limited_primary_lead_only": (
            "event-source / execution-blocking / weekly-cadence review",
            "threshold loosening for sample",
        ),
        "r03_no_downside_rebound_support": (
            "pause R03 mainline or define a genuinely new exposure mainline",
            "grid expansion; ret5/volatility rank/stabilization/money repair tuning",
        ),
        "r03_blocked_data_or_execution_contract": (
            "fix R01/E01 data or execution contract",
            "economic conclusion",
        ),
    }
    return mapping.get(decision, ("", ""))


def final_row(base: dict[str, Any], rule: str, decision: str, reason: str) -> dict[str, Any]:
    allowed, blocked = allowed_next(decision)
    out = dict(base)
    out.update(
        {
            "priority_rule_id": rule,
            "final_decision": decision,
            "allowed_next_requirement": allowed,
            "blocked_next_requirements": blocked,
            "decision_reason": reason,
        }
    )
    return out


def all_priority_matches(summary: pd.DataFrame, contract_ok: bool = True) -> list[dict[str, Any]]:
    h10 = summary_row(summary, "H10")
    h5 = summary_row(summary, "H5")
    h20 = summary_row(summary, "H20")
    base = {
        "h10_validated_pass": h10_validated_pass(summary),
        "stock_selection_supported": stock_selection_supported(summary),
        "robustness_confirmed": robustness_confirmed(summary),
        "adjacent_horizon_status": adjacent_status(summary),
        "baseline_lift_evaluable_H10": bool_value(h10["baseline_lift_evaluable"]) if h10 is not None else False,
        "baseline_lift_gate_H10": bool_value(h10["baseline_lift_gate"]) if h10 is not None else False,
        "absolute_positive_H10": bool_value(h10["absolute_positive"]) if h10 is not None else False,
        "relative_positive_H10": bool_value(h10["relative_positive"]) if h10 is not None else False,
        "horizon_pass_H5": bool_value(h5["horizon_pass"]) if h5 is not None else False,
        "horizon_pass_H20": bool_value(h20["horizon_pass"]) if h20 is not None else False,
        "matched_rule_id": "",
        "baseline_not_evaluable_origin": "",
    }
    rule_defs = [
        ("rule_01_blocked_data_or_execution_contract", not contract_ok, "r03_blocked_data_or_execution_contract", "Required data, split, execution, cost, or canonical unit authority is missing."),
        ("rule_02_downside_volatility_shock_rebound_supported", stock_selection_supported(summary) and robustness_confirmed(summary) and adjacent_clean(summary), "r03_downside_volatility_shock_rebound_supported_continue_research", "Primary downside-volatility shock rebound unit passed H10, baseline lift, robustness, and adjacent horizon checks."),
        ("rule_03_baseline_not_evaluable_validation_lead", baseline_not_evaluable_validation_lead(summary), "r03_baseline_not_evaluable_validation_lead", "Primary validation passed but date-aligned baseline was not evaluable."),
        ("rule_04_downside_beta_or_market_rebound_only", h10_validated_pass(summary) and h10 is not None and bool_value(h10["baseline_lift_evaluable"]) and not bool_value(h10["baseline_lift_gate"]), "r03_downside_beta_or_market_rebound_only_no_selection_pass", "Primary validation passed but did not stably beat same-week paired nonselected downside baseline."),
        ("rule_05_unstable_validation_only_lead", stock_selection_supported(summary) and not robustness_confirmed(summary), "r03_unstable_validation_only_lead", "Validation stock-selection support did not confirm in robustness."),
        ("rule_06_unstable_horizon_shape", stock_selection_supported(summary) and robustness_confirmed(summary) and adjacent_status(summary) == "adjacent_horizon_strongly_negative", "r03_unstable_horizon_shape_no_search_allowed", "H10 support was contradicted by a strongly negative adjacent horizon."),
        ("rule_07_adjacent_horizon_not_evaluable", stock_selection_supported(summary) and robustness_confirmed(summary) and adjacent_status(summary) == "adjacent_horizon_not_evaluable", "r03_adjacent_horizon_not_evaluable_validation_lead", "H10 support had an adjacent horizon that was not evaluable."),
        ("rule_08_relative_rebound_edge_only", relative_only_audit_supported(summary), "r03_relative_rebound_edge_only_hedged_or_regime_audit_required", "Relative rebound edge exists without absolute long-only deployability, is stable across comparators, and beats the paired downside baseline."),
        ("rule_09_relative_only_baseline_not_evaluable", relative_only_baseline_not_evaluable(summary), "r03_baseline_not_evaluable_validation_lead", "Relative-only rebound lead exists but paired downside baseline was not evaluable."),
        ("rule_10_absolute_only_baseline_not_evaluable", absolute_only_baseline_not_evaluable(summary), "r03_baseline_not_evaluable_validation_lead", "Absolute-only rebound lead exists but paired downside baseline was not evaluable."),
        ("rule_11_absolute_only_beta_or_market_rebound", absolute_only_beta_or_market_rebound(summary), "r03_downside_beta_or_market_rebound_only_no_selection_pass", "Absolute rebound exists without matched residual edge and without paired downside baseline lift."),
        ("rule_12_absolute_rebound_only_baseline_lift_no_relative_pass", absolute_only_baseline_lift_no_relative_pass(summary), "r03_absolute_rebound_only_baseline_lift_no_relative_pass", "Absolute rebound and paired baseline lift exist, but matched-relative support failed."),
        ("rule_13_horizon_specific_lead_only", horizon_specific_lead(summary), "r03_horizon_specific_lead_only_no_search_allowed", "Only H5 or H20 passed while H10 did not."),
        ("rule_14_sample_limited_primary_lead_only", sample_limited_return_lead(summary) and h10 is not None and bool_value(h10["baseline_lift_gate"]), "r03_sample_limited_primary_lead_only", "Primary unit is a sample-limited lead only."),
        ("rule_15_no_downside_rebound_support", True, "r03_no_downside_rebound_support", "No R03 rule supplied downside volatility shock rebound support."),
    ]
    rows = []
    selected_seen = False
    for idx, (rule, matched, decision, reason) in enumerate(rule_defs, start=1):
        selected = bool(matched and not selected_seen)
        if selected:
            selected_seen = True
        row = {
            "priority_order": idx,
            "priority_rule_id": rule,
            "would_match": bool(matched),
            "selected": selected,
            "candidate_final_decision": decision,
            "decision_reason": reason,
        }
        row.update(base)
        if decision == "r03_baseline_not_evaluable_validation_lead" and bool(matched):
            row["matched_rule_id"] = rule
            if rule == "rule_03_baseline_not_evaluable_validation_lead":
                row["baseline_not_evaluable_origin"] = "h10_validated_pass"
            elif rule == "rule_09_relative_only_baseline_not_evaluable":
                row["baseline_not_evaluable_origin"] = "rel_only"
            elif rule == "rule_10_absolute_only_baseline_not_evaluable":
                row["baseline_not_evaluable_origin"] = "abs_only"
        rows.append(row)
    return rows


def replay_final_decision(summary: pd.DataFrame, contract_ok: bool = True) -> dict[str, Any]:
    h10 = summary_row(summary, "H10")
    base = {
        "requirement_id": REQUIREMENT_ID,
        "primary_unit_h10_quadrant": quadrant(h10),
        "primary_unit_robustness_confirmed": robustness_confirmed(summary),
        "primary_unit_adjacent_horizon_status": adjacent_status(summary),
        "created_at": r01.now_iso(),
    }
    matches = all_priority_matches(summary, contract_ok)
    selected = next(row for row in matches if row["selected"])
    return final_row(base, selected["priority_rule_id"], selected["candidate_final_decision"], selected["decision_reason"])


def build_final_decision(paths: r01.Paths, summary: pd.DataFrame) -> pd.DataFrame:
    final = pd.DataFrame([replay_final_decision(summary, contract_ok=True)])
    inputs = pd.DataFrame(all_priority_matches(summary, contract_ok=True))
    r01.write_csv(final, paths.reports_dir / "r03_final_decision.csv")
    r01.write_csv(inputs, paths.reports_dir / "r03_final_decision_inputs.csv")
    r01.write_csv(final, paths.reports_dir / "r03_final_decision_replay_audit.csv")
    return final


def fmt_pct(value: Any) -> str:
    if not finite(value):
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def fmt_num(value: Any, digits: int = 4) -> str:
    if not finite(value):
        return "n/a"
    return f"{float(value):.{digits}f}"


def write_final_report(paths: r01.Paths, validation: dict[str, Any] | None, summary: pd.DataFrame, final: pd.DataFrame) -> None:
    final_row = final.iloc[0].to_dict()
    hrows = {h: summary_row(summary, h) for h in HORIZON_LABELS}
    h10 = hrows["H10"]
    robust = summary_row(summary, "H10", "robustness")
    lines = [
        "# EP5 R03 Final Report",
        "",
        "## 1. 边界声明",
        "",
        "R03 did not perform alpha search.",
        "R03 did not tune ret5, realized_vol10, volatility rank, stabilization, money floor, horizon, or collapse.",
        "R03 did not reuse R02 descriptive buckets as candidate rules.",
        "R03 did not use big-winner labels for pass/fail.",
        "R03 did not tune thresholds after validation.",
        "R03 did not approve a production strategy.",
        "R03 did not run a hedged or market-neutral backtest.",
        "R03 did not let the audit-only downside baseline create a positive decision.",
        "",
        "## 2. 最终结论",
        "",
        f"- final_decision: `{final_row.get('final_decision', '')}`",
        f"- priority_rule: `{final_row.get('priority_rule_id', '')}`",
        f"- H10 quadrant: `{final_row.get('primary_unit_h10_quadrant', '')}`",
        f"- allowed_next_requirement: {final_row.get('allowed_next_requirement', '')}",
        f"- blocked_next_requirements: {final_row.get('blocked_next_requirements', '')}",
        f"- reason: {final_row.get('decision_reason', '')}",
    ]
    if h10 is not None:
        lines.extend(
            [
                "",
                "## 3. H10 主判定数据",
                "",
                "| metric | value |",
                "|:--|--:|",
                f"| complete_event_count | {int(h10['complete_event_count'])} |",
                f"| complete_event_share | {fmt_pct(h10['complete_event_share'])} |",
                f"| decision_observation_date_count | {int(h10['decision_observation_date_count'])} |",
                f"| mean_ret5_at_D | {fmt_pct(h10['mean_ret5_at_D'])} |",
                f"| mean_realized_vol10_at_D | {fmt_pct(h10['mean_realized_vol10_at_D'])} |",
                f"| mean_realized_vol10_rank_pct_at_D | {fmt_pct(h10['mean_realized_vol10_rank_pct_at_D'])} |",
                f"| mean_stabilization_return_at_D | {fmt_pct(h10['mean_stabilization_return_at_D'])} |",
                f"| mean_money_repair_ratio_at_D | {fmt_num(h10['mean_money_repair_ratio_at_D'])} |",
                f"| mean_net_return | {fmt_pct(h10['mean_net_return'])} |",
                f"| median_net_return | {fmt_pct(h10['median_net_return'])} |",
                f"| p10_net_return | {fmt_pct(h10['p10_net_return'])} |",
                f"| loss_rate | {fmt_pct(h10['loss_rate'])} |",
                f"| mean_matched_delta_return | {fmt_pct(h10['mean_matched_delta_return'])} |",
                f"| median_matched_delta_return | {fmt_pct(h10['median_matched_delta_return'])} |",
                f"| p10_matched_delta_return | {fmt_pct(h10['p10_matched_delta_return'])} |",
                f"| matched_loss_rate_delta | {fmt_pct(h10['matched_loss_rate_delta'])} |",
                f"| date_weighted_mean_net_return | {fmt_pct(h10['date_weighted_mean_net_return'])} |",
                f"| date_weighted_mean_matched_delta_return | {fmt_pct(h10['date_weighted_mean_matched_delta_return'])} |",
                f"| fallback_comparator_share | {fmt_pct(h10['fallback_comparator_share'])} |",
                f"| sample_gate_pass | `{bool_value(h10['sample_gate_pass'])}` |",
                f"| concentration_gate_pass | `{bool_value(h10['concentration_gate_pass'])}` |",
                f"| date_independence_gate | `{bool_value(h10['date_independence_gate'])}` |",
                f"| absolute_positive | `{bool_value(h10['absolute_positive'])}` |",
                f"| relative_positive | `{bool_value(h10['relative_positive'])}` |",
            ]
        )
        lines.extend(
            [
                "",
                "## 4. 7.1 vs 7.2 Baseline",
                "",
                "| metric | H10 validation |",
                "|:--|--:|",
                f"| baseline_lift_evaluable | `{bool_value(h10['baseline_lift_evaluable'])}` |",
                f"| baseline_lift_gate | `{bool_value(h10['baseline_lift_gate'])}` |",
                f"| baseline_comparable_observation_date_count | {int(h10['baseline_comparable_observation_date_count'])} |",
                f"| min_year_baseline_comparable_observation_date_count | {int(h10['min_year_baseline_comparable_observation_date_count'])} |",
                f"| baseline_executable_constituent_count_min | {int(h10['baseline_executable_constituent_count_min'])} |",
                f"| baseline_executable_constituent_count_p10 | {fmt_num(h10['baseline_executable_constituent_count_p10'])} |",
                f"| baseline_executable_constituent_count_median | {fmt_num(h10['baseline_executable_constituent_count_median'])} |",
                f"| baseline_executable_constituent_count_mean | {fmt_num(h10['baseline_executable_constituent_count_mean'])} |",
                f"| baseline_date_weighted_mean_net_return | {fmt_pct(h10['baseline_date_weighted_mean_net_return'])} |",
                f"| broad_liquid_baseline_date_weighted_mean_net_return | {fmt_pct(h10['broad_liquid_baseline_date_weighted_mean_net_return'])} |",
                f"| selection_lift_vs_baseline_mean | {fmt_pct(h10['selection_lift_vs_baseline_mean'])} |",
                f"| selection_lift_vs_baseline_median | {fmt_pct(h10['selection_lift_vs_baseline_median'])} |",
                f"| selection_lift_vs_baseline_p10 | {fmt_pct(h10['selection_lift_vs_baseline_p10'])} |",
                f"| selection_lift_loss_rate_delta | {fmt_pct(h10['selection_lift_loss_rate_delta'])} |",
            ]
        )
    lines.extend(["", "## 5. Horizon Shape", "", "| horizon | abs | rel | date_gate | baseline_lift | horizon_pass | strongly_negative |"])
    lines.append("|:--|:--:|:--:|:--:|:--:|:--:|:--:|")
    for horizon, row in hrows.items():
        if row is None:
            continue
        lines.append(
            f"| {horizon} | `{bool_value(row['absolute_positive'])}` | `{bool_value(row['relative_positive'])}` | `{bool_value(row['date_independence_gate'])}` | `{bool_value(row['baseline_lift_gate'])}` | `{bool_value(row['horizon_pass'])}` | `{bool_value(row['strongly_negative'])}` |"
        )
    lines.extend(["", "## 6. Robustness", ""])
    if robust is not None:
        lines.extend(
            [
                f"- robustness H10 complete events: `{int(robust['complete_event_count'])}`",
                f"- robustness H10 mean net: `{fmt_pct(robust['mean_net_return'])}`",
                f"- robustness H10 mean matched delta: `{fmt_pct(robust['mean_matched_delta_return'])}`",
                f"- robustness baseline evaluable: `{bool_value(h10['robustness_baseline_lift_evaluable']) if h10 is not None else False}`",
                f"- robustness selection lift mean: `{fmt_pct(h10['robustness_selection_lift_vs_baseline_mean']) if h10 is not None else 'n/a'}`",
                f"- robustness_confirmed: `{bool_value(h10['robustness_confirmed']) if h10 is not None else False}`",
            ]
        )
    lines.extend(
        [
            "",
            "## 7. 问题回答",
            "",
            f"1. H10 四象限为 `{final_row.get('primary_unit_h10_quadrant', '')}`。",
            "2. 结果是否为 edge 由 final_decision 决定；baseline 不可单独创造 positive decision。",
            "3. 年度方向一致性见 `r03_event_summary_by_unit_horizon_year.csv`。",
            "4. Robustness 只确认 validation，不救回 validation failure。",
            "5. Matched comparator fallback 已进入 relative gate 和 weak comparator guard。",
            "6. instrument / industry / entry-date / observation-date concentration 已进入 concentration gate。",
            "7. date-weighted return 和 observation-date concentration 已进入 date_independence_gate。",
            "8. downside baseline 使用同周 paired nonselected downside high-vol basket；broad liquid baseline 只作市场整体反弹 readout。",
            "9. H5 / H20 只作为 shape audit，不能替代 H10。",
            "10. Big-winner / right-tail 只在 `r03_right_tail_readout.csv` 中作为 post-entry diagnostic。",
            "11. 7.1 vs 7.2 的 baseline lift 已由 `r03_baseline_date_comparison.csv` 和 `r03_baseline_lift_audit.csv` 提供 authority。",
            "12. shock-state decomposition 仅为描述性 readout，不能升级为新规则。",
            "13. relative-only 必须同时通过 `multi_comparator_relative_stable` 和 `baseline_lift_gate`，不能只靠 SH000300。",
            f"14. 下一步允许 `{final_row.get('allowed_next_requirement', '')}`；禁止 `{final_row.get('blocked_next_requirements', '')}`。",
        ]
    )
    if validation is not None:
        lines.extend(
            [
                "",
                "## 8. Validator",
                "",
                f"- validation_status: `{validation['validation_status']}`",
                f"- passed gates: `{validation['passed_gate_count']}` / `{validation['gate_count']}`",
            ]
        )
    (paths.reports_dir / "r03_final_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_artifact_hashes(paths: r01.Paths) -> None:
    rows = []
    for name in CACHE_FILES:
        path = paths.cache_dir / name
        rows.append({"artifact_path": r01.relpath(path), "artifact_type": "cache", "exists": path.exists(), "sha256": r01.file_hash(path)})
    for name in [*RUNNER_REPORTS, *VALIDATOR_REPORTS]:
        path = paths.reports_dir / name
        rows.append({"artifact_path": r01.relpath(path), "artifact_type": "report", "exists": path.exists(), "sha256": r01.file_hash(path)})
    for name in ["r03_run_manifest.json", "r03_validation.json"]:
        path = paths.manifests_dir / name
        rows.append({"artifact_path": r01.relpath(path), "artifact_type": "manifest", "exists": path.exists(), "sha256": r01.file_hash(path)})
    r01.write_json({"created_at": r01.now_iso(), "artifacts": rows}, paths.manifests_dir / "r03_artifact_hashes.json")


def run_pipeline(config_path: str | Path = DEFAULT_CONFIG) -> None:
    config, paths = load_config(config_path)
    build_input_audits(config, paths)
    feature = build_feature_panel(config, paths)
    build_unit_registry(config, paths)
    primary_event = build_primary_event_panel(config, paths, feature)
    execution = build_execution_panel(config, paths, feature, primary_event)
    baseline = build_baseline_constituent_panel(config, paths, feature, primary_event)
    comparator = build_comparator_panel(config, paths, feature, execution)
    summary, _, _ = build_summaries(config, paths, primary_event, execution, comparator, baseline)
    build_right_tail(config, paths, feature, execution)
    final = build_final_decision(paths, summary)
    write_final_report(paths, None, summary, final)
    r01.write_json(
        {
            "requirement_id": REQUIREMENT_ID,
            "plan_id": PLAN_ID,
            "config_path": r01.relpath(paths.config_path),
            "output_root": r01.relpath(paths.output_root),
            "created_at": r01.now_iso(),
            "git_commit": r01.git_commit_hash(),
            "final_decision": final.iloc[0]["final_decision"],
        },
        paths.manifests_dir / "r03_run_manifest.json",
    )
    write_artifact_hashes(paths)


def required_output_paths(paths: r01.Paths) -> list[Path]:
    return [paths.cache_dir / name for name in CACHE_FILES] + [paths.reports_dir / name for name in RUNNER_REPORTS] + [paths.manifests_dir / name for name in RUNNER_MANIFESTS]


def validate_outputs(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths = load_config(config_path)
    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"check_name": name, "status": "passed" if condition else "failed", "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    check("requirement_id", config.get("requirement_id") == REQUIREMENT_ID, str(config.get("requirement_id")))
    check("plan_id", config.get("plan_id") == PLAN_ID, str(config.get("plan_id")))
    check("canonical_units", config.get("canonical_units") == CANONICAL_UNITS, str(config.get("canonical_units")))
    check("horizons", config.get("execution", {}).get("horizons") == HORIZONS, str(config.get("execution", {}).get("horizons")))
    check("primary_horizon", config.get("execution", {}).get("primary_horizon") == 10, str(config.get("execution", {}).get("primary_horizon")))
    local_paths = [str(config["data_sources"][key]) for key in ["qlib_provider_uri", "pit_universe_path", "pit_qlib_instrument_universe_path", "pit_industry_path", "trading_calendar_path", "qlib_instrument_path"]]
    check("local_pit_inputs_only", all(not value.startswith(("http://", "https://")) for value in local_paths) and "pit" in config["data_sources"]["qlib_provider_uri"], ";".join(local_paths))
    check("costs", config["execution"]["buy_cost_bps"] == 30 and config["execution"]["sell_cost_bps"] == 80 and config["execution"]["round_trip_cost_bps"] == 110, "")
    check("execution_lag_and_limit", config["execution"]["max_entry_execution_lag_trading_days"] == 5 and config["execution"]["max_exit_execution_lag_trading_days"] == 5 and float(config["execution"]["mainboard_limit_inference_pct"]) == 0.095, "")
    constants = config["frozen_formula_constants"]
    expected_constants = {
        "ret5_window_trading_days": 5,
        "realized_vol10_window_trading_days": 10,
        "realized_vol10_ddof": 0,
        "realized_vol10_rank_pct_threshold": 0.80,
        "avg_money20_window_trading_days": 20,
        "avg_money20_floor_cny": 50000000,
        "money_ma20_prev_window_trading_days": 20,
        "downside_ret5_threshold": -0.05,
        "stabilization_rule": "close_D_strictly_gt_close_D_minus_1",
        "money_repair_rule": "money_D_gte_money_ma20_prev_D",
        "weekly_observation_cadence": "iso_week_last_trading_day",
        "vol_rank_cross_section_min_count": 100,
        "episode_merge_gap_trading_days": 20,
        "paired_downside_baseline_min_complete_constituents_per_dh": 30,
        "baseline_lift_min_comparable_observation_date_count": 40,
        "baseline_lift_min_year_comparable_observation_date_count": 15,
    }
    for key, expected in expected_constants.items():
        check(f"constant_{key}", constants.get(key) == expected, str(constants.get(key)))
    for key, value in config.get("guardrails", {}).items():
        check(f"guardrail_{key}", value is False, str(value))

    missing = [r01.relpath(path) for path in required_output_paths(paths) if not path.exists()]
    check("all_required_outputs_exist", not missing, "; ".join(missing[:10]))
    if missing:
        return write_validation(paths, checks, failures, "blocked_missing_required_artifact", "")

    feature = pd.read_parquet(paths.cache_dir / "r03_daily_feature_panel.parquet")
    primary_event = pd.read_parquet(paths.cache_dir / "r03_primary_event_panel.parquet")
    execution = pd.read_parquet(paths.cache_dir / "r03_execution_event_panel.parquet")
    comparator = pd.read_parquet(paths.cache_dir / "r03_matched_comparator_panel.parquet")
    baseline = pd.read_parquet(paths.cache_dir / "r03_baseline_constituent_panel.parquet")
    right_tail = pd.read_parquet(paths.cache_dir / "r03_right_tail_diagnostic_panel.parquet")
    summary = pd.read_csv(paths.reports_dir / "r03_event_summary_by_unit_horizon_split.csv")
    baseline_date = pd.read_csv(paths.reports_dir / "r03_baseline_date_comparison.csv")
    final = pd.read_csv(paths.reports_dir / "r03_final_decision.csv")
    final_inputs = pd.read_csv(paths.reports_dir / "r03_final_decision_inputs.csv")

    check("feature_required_columns", {"ret5", "realized_vol10", "rank_pct_realized_vol10", "stabilization_return_at_D", "money_repair_ratio_at_D", "raw_primary_eligible_pre_collapse"}.issubset(feature.columns), "")
    check("realized_vol10_ddof_configured", int(constants["realized_vol10_ddof"]) == 0, "")
    check("vol_rank_average_rank_bounds", bool(feature["rank_pct_realized_vol10"].dropna().between(0, 1).all()), "")
    check("only_one_primary_decision_unit", set(primary_event.get("canonical_unit_id", pd.Series(dtype=object)).dropna().unique()) <= {PRIMARY_UNIT}, "")
    check("baseline_unit_not_primary_event", BASELINE_UNIT not in set(primary_event.get("canonical_unit_id", pd.Series(dtype=object)).dropna().unique()), "")
    check("execution_horizons_exact", set(execution.get("horizon", pd.Series(dtype=object)).dropna().unique()) == set(HORIZON_LABELS), "")
    check("blocked_reason_unprefixed", set(execution.loc[execution["blocked_reason"].notna() & execution["blocked_reason"].ne(""), "blocked_reason"]).issubset(set(BLOCKED_REASONS)), "")
    check("complete_rows_have_empty_blocked_reason", bool(execution.loc[execution["execution_status"].eq("complete_executable"), "blocked_reason"].fillna("").eq("").all()), "")
    check("comparator_status_values", set(comparator.get("matched_comparator_status", pd.Series(dtype=object)).dropna().unique()).issubset({"comparable", "blocked_insufficient_comparator", "blocked_missing_comparator_price"}), "")
    if not primary_event.empty:
        primary_conditions = (
            primary_event["ret5"].le(float(constants["downside_ret5_threshold"]))
            & primary_event["rank_pct_realized_vol10"].ge(float(constants["realized_vol10_rank_pct_threshold"]))
            & primary_event["stabilization_return_at_D"].gt(0)
            & primary_event["money_repair_ratio_at_D"].ge(1.0)
            & primary_event["raw_primary_eligible_pre_collapse"].astype(bool)
        )
        check("primary_eligibility_formula", bool(primary_conditions.all()), "")
    if not primary_event.empty:
        calendar_pos = r01.trading_day_pos(r01.load_calendar(config))
        collapse_ok = True
        for _, group in primary_event.sort_values(["instrument_id", "signal_date"]).groupby("instrument_id"):
            positions = [calendar_pos.get(pd.Timestamp(value)) for value in group["signal_date"]]
            positions = [value for value in positions if value is not None]
            if any(b - a <= 20 for a, b in zip(positions, positions[1:])):
                collapse_ok = False
                break
        check("episode_collapse_20d_first_signal", collapse_ok, "")
    if not baseline.empty and "is_paired_nonselected_downside_baseline" in baseline:
        paired = baseline.loc[baseline["is_paired_nonselected_downside_baseline"].astype(bool)]
        check("paired_baseline_excludes_raw_primary", bool((~paired.get("raw_primary_eligible_pre_collapse_on_date", pd.Series(False, index=paired.index)).astype(bool)).all()), "")
    status_set = set(baseline_date.get("baseline_comparison_status", pd.Series(dtype=object)).dropna().unique())
    check("baseline_status_exhaustive_enum", status_set.issubset({"comparable", "blocked_insufficient_baseline_constituents", "not_applicable_no_primary_complete_event"}), str(status_set))
    comparable_rows = baseline_date.loc[baseline_date["baseline_comparison_status"].eq("comparable")]
    check("baseline_comparable_count_threshold", bool((comparable_rows["baseline_executable_constituent_count"] >= 30).all()) if not comparable_rows.empty else True, "")
    blocked_rows = baseline_date.loc[baseline_date["baseline_comparison_status"].eq("blocked_insufficient_baseline_constituents")]
    check("baseline_blocked_count_threshold", bool((blocked_rows["baseline_executable_constituent_count"] < 30).all()) if not blocked_rows.empty else True, "")
    check("baseline_lift_uses_paired_not_broad", "broad_liquid_baseline_date_equal_weight_return" in baseline_date.columns and "baseline_date_equal_weight_return" in baseline_date.columns, "")
    check("baseline_count_distribution_reported", {"baseline_executable_constituent_count_min", "baseline_executable_constituent_count_p10", "baseline_executable_constituent_count_median", "baseline_executable_constituent_count_mean"}.issubset(summary.columns), "")
    check("baseline_cannot_create_positive_decision", final.iloc[0]["final_decision"] in FINAL_DECISIONS and BASELINE_UNIT not in ",".join(final.astype(str).iloc[0].tolist()), "")
    required_summary_cols = {"sample_gate_pass", "date_independence_gate", "baseline_lift_gate", "baseline_lift_evaluable", "multi_comparator_relative_stable", "sample_status"}
    check("summary_required_gate_columns", required_summary_cols.issubset(summary.columns), ",".join(sorted(required_summary_cols - set(summary.columns))))
    sample_status_values = set(summary["sample_status"].dropna().astype(str).unique()) if "sample_status" in summary else set()
    check("sample_status_enum_includes_date_block", sample_status_values.issubset({"sample_pass", "blocked_insufficient_date_independence_sample", "sample_limited_lead", "blocked_insufficient_sample"}), str(sample_status_values))
    h10 = summary_row(summary, "H10")
    if final.iloc[0]["final_decision"] == "r03_downside_volatility_shock_rebound_supported_continue_research" and h10 is not None:
        check("continue_requires_date_gate", bool_value(h10["date_independence_gate"]), "")
        check("continue_requires_baseline_lift", bool_value(h10["baseline_lift_gate"]), "")
    if h10 is not None and h10_validated_pass(summary) and not bool_value(h10["baseline_lift_evaluable"]):
        check("baseline_not_evaluable_not_beta", final.iloc[0]["final_decision"] == "r03_baseline_not_evaluable_validation_lead", str(final.iloc[0]["final_decision"]))
    if final.iloc[0]["final_decision"] == "r03_relative_rebound_edge_only_hedged_or_regime_audit_required" and h10 is not None:
        check("relative_only_requires_multi_comparator", bool_value(h10["multi_comparator_relative_stable"]), "")
        check("relative_only_requires_baseline_lift", bool_value(h10["baseline_lift_gate"]), "")
    if h10 is not None and relative_only_baseline_not_evaluable(summary):
        check("rel_only_baseline_not_evaluable_maps_to_baseline_lead", final.iloc[0]["final_decision"] == "r03_baseline_not_evaluable_validation_lead", str(final.iloc[0]["final_decision"]))
    if h10 is not None and bool_value(h10["absolute_positive"]) and not bool_value(h10["relative_positive"]):
        decision = str(final.iloc[0]["final_decision"])
        allowed_abs_only = {"r03_baseline_not_evaluable_validation_lead", "r03_downside_beta_or_market_rebound_only_no_selection_pass", "r03_absolute_rebound_only_baseline_lift_no_relative_pass", "r03_horizon_specific_lead_only_no_search_allowed", "r03_sample_limited_primary_lead_only", "r03_no_downside_rebound_support"}
        check("abs_rel_minus_three_way_baseline_guard", decision in allowed_abs_only, decision)
    if final.iloc[0]["final_decision"] == "r03_baseline_not_evaluable_validation_lead":
        selected_mask = final_inputs["selected"].map(bool_value) if "selected" in final_inputs else pd.Series(False, index=final_inputs.index)
        selected_baseline_rows = final_inputs.loc[final_inputs["candidate_final_decision"].eq("r03_baseline_not_evaluable_validation_lead") & selected_mask]
        origins = set(selected_baseline_rows.get("baseline_not_evaluable_origin", pd.Series(dtype=object)).dropna().astype(str))
        check("baseline_not_evaluable_origin_present", bool(origins & {"h10_validated_pass", "rel_only", "abs_only"}), str(origins))
    if h10 is not None and bool_value(h10["robustness_confirmed"]):
        check("robustness_requires_baseline_eval", bool_value(h10["robustness_baseline_lift_evaluable"]), "")
        check("robustness_requires_selection_lift_floor", finite(h10["robustness_selection_lift_vs_baseline_mean"]) and float(h10["robustness_selection_lift_vs_baseline_mean"]) >= -0.0025, "")
    forbidden_final_cols = {"right_tail_status", "right_tail_path_status", "decomposition_axis", "decomposition_value"}
    check("final_inputs_no_right_tail_or_decomposition_filter", forbidden_final_cols.isdisjoint(final_inputs.columns), ",".join(sorted(forbidden_final_cols & set(final_inputs.columns))))
    check("final_decision_enum", final.iloc[0]["final_decision"] in FINAL_DECISIONS, str(final.iloc[0]["final_decision"]))
    check("priority_rule_enum", final.iloc[0]["priority_rule_id"] in PRIORITY_RULES, str(final.iloc[0].get("priority_rule_id")))
    replay = replay_final_decision(summary, contract_ok=True)
    replay_match = final.iloc[0]["final_decision"] == replay["final_decision"] and final.iloc[0]["priority_rule_id"] == replay["priority_rule_id"]
    check("final_decision_replay", replay_match, f"observed={final.iloc[0]['final_decision']} replay={replay['final_decision']}")
    check("would_have_matched_rules_reported", set(final_inputs["priority_rule_id"]) == set(PRIORITY_RULES), "")
    check("priority_rule_count_15", len(final_inputs["priority_rule_id"].drop_duplicates()) == 15, str(len(final_inputs["priority_rule_id"].drop_duplicates())))
    check("right_tail_enums", set(right_tail.get("right_tail_path_status", pd.Series(dtype=object)).dropna().unique()).issubset(set(RIGHT_TAIL_PATH_STATUSES)) and set(right_tail.get("right_tail_status", pd.Series(dtype=object)).dropna().unique()).issubset(set(RIGHT_TAIL_STATUSES)), "")
    check("no_r02_bucket_selection_gates", {"rank_pct_ret20", "ret20_value_bucket_at_D", "rank_pct_ret20_bucket_at_D"}.isdisjoint(set(feature.columns) | set(primary_event.columns)), "")
    year_summary = pd.read_csv(paths.reports_dir / "r03_event_summary_by_unit_horizon_year.csv")
    check("empty_calendar_year_rows_excluded", bool((year_summary["complete_event_count"] > 0).all()) if not year_summary.empty else True, "")
    report_text = (paths.reports_dir / "r03_final_report.md").read_text(encoding="utf-8") if (paths.reports_dir / "r03_final_report.md").exists() else ""
    for statement in [
        "R03 did not tune ret5, realized_vol10, volatility rank, stabilization, money floor, horizon, or collapse.",
        "R03 did not reuse R02 descriptive buckets as candidate rules.",
        "R03 did not use big-winner labels for pass/fail.",
        "R03 did not tune thresholds after validation.",
        "R03 did not approve a production strategy.",
        "R03 did not run a hedged or market-neutral backtest.",
        "R03 did not let the audit-only downside baseline create a positive decision.",
    ]:
        check(f"report_boundary_statement_{len(checks)}", statement in report_text, statement)

    validation_status = "passed" if not failures else "failed"
    return write_validation(paths, checks, failures, validation_status, final.iloc[0]["final_decision"], summary=summary, final=final, replay=replay)


def write_validation(
    paths: r01.Paths,
    checks: list[dict[str, Any]],
    failures: list[str],
    validation_status: str,
    final_decision: str,
    summary: pd.DataFrame | None = None,
    final: pd.DataFrame | None = None,
    replay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = pd.DataFrame(checks)
    r01.write_csv(gate, paths.reports_dir / "r03_validation_gate_audit.csv")
    r01.write_csv(gate[["check_name", "status", "detail"]], paths.reports_dir / "r03_schema_validation_audit.csv")
    replay_df = pd.DataFrame([replay or {"final_decision": final_decision, "priority_rule_id": ""}])
    r01.write_csv(replay_df, paths.reports_dir / "r03_final_decision_replay_audit.csv")
    payload = {
        "validation_status": validation_status,
        "requirement_id": REQUIREMENT_ID,
        "plan_id": PLAN_ID,
        "config_path": r01.relpath(paths.config_path),
        "output_root": r01.relpath(paths.output_root),
        "gate_count": len(checks),
        "passed_gate_count": sum(1 for row in checks if row["status"] == "passed"),
        "failed_gate_count": sum(1 for row in checks if row["status"] != "passed"),
        "final_decision": final_decision,
        "failures": failures,
        "created_at": r01.now_iso(),
    }
    r01.write_json(payload, paths.manifests_dir / "r03_validation.json")
    if summary is not None and final is not None:
        write_final_report(paths, payload, summary, final)
    write_artifact_hashes(paths)
    return payload
