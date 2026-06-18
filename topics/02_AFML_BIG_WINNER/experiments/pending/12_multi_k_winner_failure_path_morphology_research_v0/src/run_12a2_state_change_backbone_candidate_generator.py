#!/usr/bin/env python
from __future__ import annotations

import argparse
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


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
TOPIC_SRC_DIR = TOPIC_ROOT / "src"

if str(TOPIC_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(TOPIC_SRC_DIR))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402


RUN_ID = "12A2_state_change_backbone_candidate_generator"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"
FORMULA_VERSION = "12A2_state_change_formula_v1"
CANONICALIZER_ID = "C0_first_trigger_density_discipline_v1"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a2_state_change_backbone_candidate_generator.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_12a2_state_change_backbone_candidate_generator.md"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
RAW_R_CORE_ARM = "08_R_core_event_regime_gated_raw"
E1_SCOPE_08 = "07_e1_only"
SUPPORTED_FIRST_TRIGGER_STATUSES = {"first_after_reset", "first_observed_in_sample"}
FORBIDDEN_FEATURES = {
    "episode_id",
    "episode_low_date",
    "episode_high_date",
    "first_50pct_date",
    "mfe_120",
    "mfe_120d_frozen",
    "mae_10d",
    "failure_10",
    "false_repair_20d_label",
    "winner_120",
    "class_big_winner",
    "class_big_failure_proxy_nonwinner",
    "future_return",
    "forward_high",
    "forward_low",
    "post_t0",
    "label",
}


@dataclass(frozen=True)
class VariantSpec:
    family_id: str
    variant_id: str
    family_variant_id: str
    family_role: str
    input_series: str
    required_input_columns: tuple[str, ...]
    lookback_window: str
    lag_policy: str
    formula_text: str
    threshold_grid: dict[str, Any]
    reset_rule_text: str
    cooldown_sessions: int
    event_t0_confirmation_time: str
    execution_anchor_policy: str
    pit_status: str
    family_input_status: str
    blocked_reason: str
    allowed_for_primary_canonical_flag: bool
    priority: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A2 state-change backbone candidate generator.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    parser.add_argument("--max-instruments", type=int, default=None)
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith("outputs/"):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        frame.to_parquet(path, index=False)
    elif suffixes.endswith(".csv.gz"):
        frame.to_csv(
            path,
            index=False,
            compression={"method": "gzip", "compresslevel": 9, "mtime": 1},
        )
    else:
        frame.to_csv(path, index=False)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    return pd.read_csv(path, low_memory=False, **kwargs)


def path_sha(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator is None or pd.isna(denominator) or float(denominator) == 0:
        return np.nan
    return float(numerator) / float(denominator)


def safe_num(value: Any, default: float = np.nan) -> float:
    if value is None or pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def date_text(value: Any) -> str:
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d")


def json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def split_for_date(value: Any, config: dict[str, Any]) -> str:
    text = date_text(value)
    splits = config["splits"]
    if splits["train_start"] <= text <= splits["train_end"]:
        return "train"
    if splits["validation_start"] <= text <= splits["validation_end"]:
        return "validation"
    if text >= splits["robustness_start"]:
        return "robustness"
    return "outside_split"


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "instances": TABLE_DIR / "state_change_candidate_event_instances.csv.gz",
        "canonical": TABLE_DIR / "state_change_candidate_event_canonical.csv.gz",
        "formula_spec": TABLE_DIR / "state_change_family_formula_spec.csv",
        "canonicalization_spec": TABLE_DIR / "state_change_canonicalization_spec.csv",
        "feature_pit_audit": TABLE_DIR / "state_change_feature_pit_audit.csv",
        "density_audit": TABLE_DIR / "state_change_density_audit.csv",
        "overlap_diagnostic": TABLE_DIR / "state_change_family_overlap_diagnostic.csv",
        "decision": TABLE_DIR / "state_change_generation_decision.csv",
        "report": REPORT_DIR / "state_change_candidate_generation_report.md",
        "manifest": MANIFEST_DIR / "12A2_state_change_backbone_candidate_generator_manifest.json",
    }


def build_variant_specs(config: dict[str, Any]) -> list[VariantSpec]:
    cooldown = int(config["canonicalization"]["family_level_cooldown_sessions"])
    priority = config["canonicalization"]["priority_order"]

    def spec(
        family_id: str,
        variant_id: str,
        input_series: str,
        required: tuple[str, ...],
        lookback: str,
        formula: str,
        thresholds: dict[str, Any],
        reset: str,
        *,
        role: str = "primary_candidate",
        status: str = "runnable_existing_data",
        blocked: str = "",
        allowed: bool = True,
    ) -> VariantSpec:
        return VariantSpec(
            family_id=family_id,
            variant_id=variant_id,
            family_variant_id=f"{family_id}_{variant_id}",
            family_role=role,
            input_series=input_series,
            required_input_columns=required,
            lookback_window=lookback,
            lag_policy="same-day close features; executable at next open",
            formula_text=formula,
            threshold_grid=thresholds,
            reset_rule_text=reset,
            cooldown_sessions=cooldown,
            event_t0_confirmation_time="t0_close",
            execution_anchor_policy="next_open",
            pit_status="pit_safe_same_day_close",
            family_input_status=status,
            blocked_reason=blocked,
            allowed_for_primary_canonical_flag=allowed,
            priority=int(priority.get(family_id, 99)),
        )

    rows = [
        spec(
            "B1",
            "B1a_residual_cusum_20d",
            "stock beta-adjusted residual returns vs all-A",
            ("residual_cusum_20d", "residual_cusum_20d_lagmax", "residual_ret_5d", "close_to_ema60"),
            "20/60 sessions",
            "residual_cusum_20d >= 0.08 AND residual_cusum_20d_lagmax < 0.08 AND residual_ret_5d >= 0.02 AND close_to_ema60 >= -0.02",
            {"residual_cusum_20d_min": 0.08, "residual_ret_5d_min": 0.02, "close_to_ema60_min": -0.02},
            "residual_cusum_20d <= 0 OR close_to_ema60 < -0.05",
        ),
        spec(
            "B1",
            "B1b_strict_residual_cusum_20d",
            "stock beta-adjusted residual returns vs all-A",
            ("residual_cusum_20d", "residual_cusum_20d_lagmax", "residual_ret_5d", "close_to_ema60"),
            "20/60 sessions",
            "residual_cusum_20d >= 0.10 AND residual_cusum_20d_lagmax < 0.10 AND residual_ret_5d >= 0.03 AND close_to_ema60 >= 0.00",
            {"residual_cusum_20d_min": 0.10, "residual_ret_5d_min": 0.03, "close_to_ema60_min": 0.00},
            "residual_cusum_20d <= 0 OR close_to_ema60 < -0.05",
        ),
        spec(
            "B1",
            "B1c_stock_vs_board",
            "stock vs PIT board residual returns",
            ("stock_vs_board_cusum_20d", "stock_vs_board_cusum_20d_lagmax", "residual_ret_5d", "close_to_ema60"),
            "20 sessions",
            "stock_vs_board_cusum_20d >= 0.08 AND stock_vs_board_cusum_20d_lagmax < 0.08 AND residual_ret_5d >= 0.02 AND close_to_ema60 >= -0.02",
            {"stock_vs_board_cusum_20d_min": 0.08, "residual_ret_5d_min": 0.02, "close_to_ema60_min": -0.02},
            "stock_vs_board_cusum_20d <= 0 OR close_to_ema60 < -0.05",
        ),
        spec(
            "B1",
            "B1d_board_vs_market_context",
            "PIT board vs all-A residual returns",
            ("board_relative_cusum_20d", "board_relative_cusum_20d_lagmax", "stock_vs_board_20d", "residual_ret_5d"),
            "20 sessions",
            "board_relative_cusum_20d >= 0.06 AND board_relative_cusum_20d_lagmax < 0.06 AND stock_vs_board_20d >= 0 AND residual_ret_5d >= 0.015",
            {"board_relative_cusum_20d_min": 0.06, "stock_vs_board_20d_min": 0.0, "residual_ret_5d_min": 0.015},
            "board_relative_cusum_20d < 0 OR stock_vs_board_20d < -0.03 OR close_to_ema60 < -0.05",
        ),
        spec(
            "B2",
            "B2a_compression_to_expansion",
            "ATR/range compression to directional expansion",
            ("atr_pct_rank_60d_lag1", "range_compression_ratio_10_60_lag1", "range_pct", "range_pct_mean_20d_lag1", "amount_ratio_20d", "close_position_in_range", "return_5d"),
            "20/60 sessions",
            "compression_flag AND range expansion with amount, close-location, and ret_5d confirmation",
            {"atr_pct_rank_60d_max": 0.35, "range_compression_ratio_max": 0.75, "expansion_multiple": 1.20, "amount_ratio_20d_min": 1.15, "return_5d_min": 0.02, "close_position_in_range_min": 0.65},
            "atr_pct_rank_60d > 0.70 OR close_to_ema20 < -0.03",
        ),
        spec(
            "B2",
            "B2b_strict_compression_to_expansion",
            "ATR/range compression to directional expansion",
            ("atr_pct_rank_60d_lag1", "range_compression_ratio_10_60_lag1", "range_pct", "range_pct_mean_20d_lag1", "amount_ratio_20d", "close_position_in_range", "return_5d"),
            "20/60 sessions",
            "looser ATR compression but stricter expansion and amount confirmation",
            {"atr_pct_rank_60d_max": 0.45, "range_compression_ratio_max": 0.75, "expansion_multiple": 1.35, "amount_ratio_20d_min": 1.30, "return_5d_min": 0.02, "close_position_in_range_min": 0.65},
            "atr_pct_rank_60d > 0.70 OR close_to_ema20 < -0.03",
        ),
        spec(
            "B2",
            "B2c_entropy_directional_expansion",
            "direction entropy and residual expansion",
            ("direction_entropy_20d_lag1", "return_5d", "residual_ret_5d", "amount_ratio_20d", "close_position_in_range"),
            "20 sessions",
            "direction_entropy_20d_lag1 <= 0.85 AND return_5d/residual_ret_5d/amount/close-position expansion",
            {"direction_entropy_20d_max": 0.85, "return_5d_min": 0.035, "residual_ret_5d_min": 0.02, "amount_ratio_20d_min": 1.10, "close_position_in_range_min": 0.65},
            "direction_entropy_20d > 0.95 OR close_to_ema20 < -0.03",
        ),
        spec(
            "B3",
            "B3a_ema60_low_reclaim",
            "EMA60 low-reclaim repair",
            ("prior_below_ema60_days_20", "ema60_reclaim_today", "distance_from_low_60", "near_high_60", "return_5d", "stock_vs_board_20d", "close_position_in_range"),
            "20/60 sessions",
            "ema60_reclaim_today AND low_repair_context AND confirmation",
            {"prior_below_ema60_days_20_min": 10, "distance_from_low_60_min": 0.08, "near_high_60_max": 0.95, "return_5d_min": 0.03, "stock_vs_board_20d_min": -0.02, "close_position_in_range_min": 0.60},
            "close_to_ema60 < -0.03",
        ),
        spec(
            "B3",
            "B3b_strict_ema60_low_reclaim",
            "EMA60 low-reclaim repair",
            ("prior_below_ema60_days_20", "ema60_reclaim_today", "distance_from_low_60", "near_high_60", "return_5d", "stock_vs_board_20d", "close_position_in_range"),
            "20/60 sessions",
            "strict ema60_reclaim_today AND low_repair_context AND confirmation",
            {"prior_below_ema60_days_20_min": 15, "distance_from_low_60_min": 0.12, "near_high_60_max": 0.95, "return_5d_min": 0.04, "stock_vs_board_20d_min": -0.02, "close_position_in_range_min": 0.60},
            "close_to_ema60 < -0.03",
        ),
        spec(
            "B4",
            "B4a_board_regime_turn",
            "Top-N board/all-A regime context",
            ("market_return_20d", "all_a_drawdown_60d", "board_relative_cusum_20d", "board_return_20d", "residual_ret_5d", "stock_vs_board_20d"),
            "20/60 sessions",
            "market_turn AND board_turn AND stock_participation",
            {"board_relative_cusum_20d_min": 0.04, "residual_ret_5d_min": 0.015},
            "all_a_drawdown_60d < -0.15 OR board_relative_cusum_20d < 0",
        ),
        spec(
            "B4",
            "B4b_strict_board_regime_turn",
            "Top-N board/all-A regime context",
            ("market_return_20d", "all_a_drawdown_60d", "board_relative_cusum_20d", "board_return_20d", "residual_ret_5d", "stock_vs_board_20d"),
            "20/60 sessions",
            "strict market_turn AND board_turn AND stock_participation",
            {"board_relative_cusum_20d_min": 0.06, "residual_ret_5d_min": 0.020},
            "all_a_drawdown_60d < -0.15 OR board_relative_cusum_20d < 0",
        ),
        spec("B4_industry_breadth_context", "blocked_missing_pit_industry_classification", "PIT industry breadth", ("pit_industry_code",), "20 sessions", "blocked: B4 industry breadth context unavailable", {"industry_up_share_z_min": 1.0}, "not_applicable", role="blocked_state_change_dimension", status="blocked_missing_pit_industry_classification", blocked="missing_pit_industry_classification", allowed=False),
        spec("R4_industry_breadth_expansion", "blocked_missing_pit_industry_classification", "PIT industry breadth", ("pit_industry_code",), "20 sessions", "blocked: PIT industry breadth expansion unavailable", {"industry_up_share_z_min": 1.0}, "not_applicable", role="blocked_state_change_dimension", status="blocked_missing_pit_industry_classification", blocked="missing_pit_industry_classification", allowed=False),
        spec("T1_stock_vs_industry_CUSUM_break", "blocked_missing_pit_industry_classification", "PIT industry residual", ("pit_industry_code",), "20 sessions", "blocked: stock-vs-industry CUSUM unavailable", {"cusum_20d_min": 0.10}, "not_applicable", role="blocked_state_change_dimension", status="blocked_missing_pit_industry_classification", blocked="missing_pit_industry_classification", allowed=False),
        spec("T2_industry_vs_market_CUSUM_break", "blocked_missing_pit_industry_classification", "PIT industry residual", ("pit_industry_code",), "20 sessions", "blocked: industry-vs-market CUSUM unavailable", {"cusum_20d_min": 0.08}, "not_applicable", role="blocked_state_change_dimension", status="blocked_missing_pit_industry_classification", blocked="missing_pit_industry_classification", allowed=False),
        spec(
            "B5",
            "B5a_amount_regime_shift",
            "money/amount expansion",
            ("amount_ratio_20d", "amount_ratio_60d", "return_5d", "residual_ret_5d", "close_position_in_range"),
            "20/60 sessions",
            "volume_regime_shift AND positive_price_confirmation",
            {"amount_ratio_20d_min": 1.80, "amount_ratio_60d_min": 1.30, "return_5d_min": 0.035, "residual_ret_5d_min": 0.015, "close_position_in_range_min": 0.60},
            "amount_ratio_20d < 1.00 OR close_to_ema20 < -0.03",
        ),
        spec(
            "B5",
            "B5b_strict_amount_regime_shift",
            "money/amount expansion",
            ("amount_ratio_20d", "amount_ratio_60d", "return_5d", "residual_ret_5d", "close_position_in_range"),
            "20/60 sessions",
            "strict amount expansion with lower short-return but higher volume and location confirmation",
            {"amount_ratio_20d_min": 2.20, "amount_ratio_60d_min": 1.50, "return_5d_min": 0.025, "residual_ret_5d_min": 0.010, "close_position_in_range_min": 0.65},
            "amount_ratio_20d < 1.00 OR close_to_ema20 < -0.03",
        ),
        spec(
            "B6",
            "B6a_first_leadership_rank_entry",
            "cross-sectional momentum rank jump",
            ("momentum_percentile_20d_lag20", "momentum_percentile_20d", "momentum_rank_jump_20d", "residual_ret_5d", "close_to_ema60"),
            "20 sessions",
            "rank_entry AND quality_confirmation",
            {"lag_momentum_percentile_20d_max": 0.50, "momentum_percentile_20d_min": 0.80, "momentum_rank_jump_20d_min": 0.25, "residual_ret_5d_min": 0.015, "close_to_ema60_min": -0.02},
            "momentum_percentile_20d < 0.55 OR close_to_ema60 < -0.05",
        ),
        spec(
            "B6",
            "B6b_strict_first_leadership_rank_entry",
            "cross-sectional momentum rank jump",
            ("momentum_percentile_20d_lag20", "momentum_percentile_20d", "momentum_rank_jump_20d", "residual_ret_5d", "close_to_ema60"),
            "20 sessions",
            "strict rank_entry AND quality_confirmation",
            {"lag_momentum_percentile_20d_max": 0.40, "momentum_percentile_20d_min": 0.85, "momentum_rank_jump_20d_min": 0.30, "residual_ret_5d_min": 0.020, "close_to_ema60_min": 0.00},
            "momentum_percentile_20d < 0.55 OR close_to_ema60 < -0.05",
        ),
        spec("B7", "B7a_high_base_breakout_diagnostic", "near-high breakout", ("near_high_60", "amount_ratio_20d", "close_position_in_range", "residual_ret_5d"), "60 sessions", "near_high_60 >= 0.96 AND amount_ratio_20d >= 1.50 AND close_position_in_range >= 0.65 AND residual_ret_5d >= 0.02", {"near_high_60_min": 0.96, "amount_ratio_20d_min": 1.50, "close_position_in_range_min": 0.65, "residual_ret_5d_min": 0.02}, "near_high_60 < 0.90 OR close_to_ema20 < -0.03", role="diagnostic_only", status="diagnostic_only", allowed=False),
        spec("B8", "B8a_sustained_trend_state", "EMA60 sustained trend", ("above_ema60_days_20", "close_to_ema60", "return_20d", "stock_vs_market_5d"), "20/60 sessions", "first confirmation of sustained trend state", {"above_ema60_days_20_min": 10, "close_to_ema60_min": 0.03, "return_20d_min": 0.08, "stock_vs_market_5d_min": 0.0}, "above_ema60_days_20 < 5 OR close_to_ema60 < -0.02"),
        spec("B8", "B8b_strict_sustained_trend_state", "EMA60 sustained trend", ("above_ema60_days_20", "close_to_ema60", "return_20d", "stock_vs_market_5d"), "20/60 sessions", "strict first confirmation of sustained trend state", {"above_ema60_days_20_min": 15, "close_to_ema60_min": 0.05, "return_20d_min": 0.10, "stock_vs_market_5d_min": 0.01}, "above_ema60_days_20 < 5 OR close_to_ema60 < -0.02"),
    ]
    return rows


def build_formula_spec(specs: list[VariantSpec]) -> pd.DataFrame:
    rows = []
    for spec in specs:
        forbidden = sorted(FORBIDDEN_FEATURES.intersection(spec.required_input_columns))
        rows.append(
            {
                "family_id": spec.family_id,
                "variant_id": spec.variant_id,
                "family_variant_id": spec.family_variant_id,
                "family_role": spec.family_role,
                "input_series": spec.input_series,
                "required_input_columns": ";".join(spec.required_input_columns),
                "lookback_window": spec.lookback_window,
                "lag_policy": spec.lag_policy,
                "formula_text": spec.formula_text,
                "threshold_grid_json": json_compact(spec.threshold_grid),
                "reset_rule_text": spec.reset_rule_text,
                "cooldown_sessions": spec.cooldown_sessions,
                "event_t0_confirmation_time": spec.event_t0_confirmation_time,
                "execution_anchor_policy": spec.execution_anchor_policy,
                "pit_status": spec.pit_status,
                "family_input_status": spec.family_input_status,
                "blocked_reason": spec.blocked_reason,
                "forbidden_feature_scan_status": "blocked" if forbidden else "pass",
                "allowed_for_primary_canonical_flag": spec.allowed_for_primary_canonical_flag,
            }
        )
    return pd.DataFrame(rows)


def build_canonicalization_spec(config: dict[str, Any], specs: list[VariantSpec]) -> pd.DataFrame:
    priority = {
        spec.family_id: spec.priority
        for spec in sorted(specs, key=lambda item: (item.priority, item.family_id))
        if spec.family_input_status != "blocked_missing_pit_industry_classification"
    }
    rows = [
        {
            "canonicalizer_id": CANONICALIZER_ID,
            "component_id": "C0_priority_order",
            "component_role": "same_day_primary_selection",
            "input_family_scope": "B1/B2/B3/B4/B5/B6/B7/B8",
            "priority_order_json": json_compact(priority),
            "family_level_cooldown_sessions": int(config["canonicalization"]["family_level_cooldown_sessions"]),
            "union_level_cooldown_sessions": int(config["canonicalization"]["union_level_cooldown_sessions"]),
            "first_trigger_supported_statuses_json": json_compact(config["canonicalization"]["supported_first_trigger_statuses"]),
            "cooldown_reentry_policy": "raw_audit_only",
            "same_day_collision_policy": "lowest_priority_number_wins",
            "union_cooldown_policy": "same_instrument_union_cooldown_blocks_primary",
            "allowed_primary_filter": "family_input_status=runnable_existing_data AND allowed_for_primary_canonical_flag=true",
            "diagnostic_family_policy": "raw_and_diagnostics_only",
            "non_executable_policy": "raw_audit_only",
            "pit_blocked_policy": "raw_audit_only",
            "rule_text": "B1 priority 10, B3 20, B2 30, B4 40, B5 50, B6 60, B8 70, B7 diagnostic 90.",
        },
        {
            "canonicalizer_id": CANONICALIZER_ID,
            "component_id": "C0_family_level_first_trigger",
            "component_role": "family_state_machine",
            "input_family_scope": "family_variant_id",
            "priority_order_json": "{}",
            "family_level_cooldown_sessions": int(config["canonicalization"]["family_level_cooldown_sessions"]),
            "union_level_cooldown_sessions": int(config["canonicalization"]["union_level_cooldown_sessions"]),
            "first_trigger_supported_statuses_json": json_compact(config["canonicalization"]["supported_first_trigger_statuses"]),
            "cooldown_reentry_policy": "cooldown_reentry_without_reset excluded from primary denominator",
            "same_day_collision_policy": "",
            "union_cooldown_policy": "",
            "allowed_primary_filter": "",
            "diagnostic_family_policy": "",
            "non_executable_policy": "",
            "pit_blocked_policy": "",
            "rule_text": "reset re-arms; first observed and first after reset are supported; cooldown-only reentry is audit-only.",
        },
        {
            "canonicalizer_id": CANONICALIZER_ID,
            "component_id": "C0_same_day_collision",
            "component_role": "collapse_same_instrument_same_day",
            "input_family_scope": "instrument,event_t0_date",
            "priority_order_json": json_compact(priority),
            "family_level_cooldown_sessions": int(config["canonicalization"]["family_level_cooldown_sessions"]),
            "union_level_cooldown_sessions": int(config["canonicalization"]["union_level_cooldown_sessions"]),
            "first_trigger_supported_statuses_json": json_compact(config["canonicalization"]["supported_first_trigger_statuses"]),
            "cooldown_reentry_policy": "",
            "same_day_collision_policy": "keep primary priority min and record all triggered variants",
            "union_cooldown_policy": "",
            "allowed_primary_filter": "allowed_for_primary_canonical_flag=true",
            "diagnostic_family_policy": "exclude diagnostic family from primary selection",
            "non_executable_policy": "",
            "pit_blocked_policy": "",
            "rule_text": "Same-day primary event is deterministic by priority then family_variant_id.",
        },
        {
            "canonicalizer_id": CANONICALIZER_ID,
            "component_id": "C0_union_level_cooldown",
            "component_role": "union_density_control",
            "input_family_scope": "instrument",
            "priority_order_json": "{}",
            "family_level_cooldown_sessions": int(config["canonicalization"]["family_level_cooldown_sessions"]),
            "union_level_cooldown_sessions": int(config["canonicalization"]["union_level_cooldown_sessions"]),
            "first_trigger_supported_statuses_json": json_compact(config["canonicalization"]["supported_first_trigger_statuses"]),
            "cooldown_reentry_policy": "",
            "same_day_collision_policy": "",
            "union_cooldown_policy": "block primary if previous canonical event is within 10 sessions",
            "allowed_primary_filter": "",
            "diagnostic_family_policy": "",
            "non_executable_policy": "",
            "pit_blocked_policy": "",
            "rule_text": "Union cooldown is applied after same-day family collision grouping.",
        },
        {
            "canonicalizer_id": CANONICALIZER_ID,
            "component_id": "C0_primary_denominator_filter",
            "component_role": "supported_canonical_denominator",
            "input_family_scope": "raw event instances",
            "priority_order_json": "{}",
            "family_level_cooldown_sessions": int(config["canonicalization"]["family_level_cooldown_sessions"]),
            "union_level_cooldown_sessions": int(config["canonicalization"]["union_level_cooldown_sessions"]),
            "first_trigger_supported_statuses_json": json_compact(config["canonicalization"]["supported_first_trigger_statuses"]),
            "cooldown_reentry_policy": "exclude",
            "same_day_collision_policy": "",
            "union_cooldown_policy": "pass only",
            "allowed_primary_filter": "family_input_status=runnable_existing_data AND allowed_for_primary_canonical_flag=true AND family_cooldown_status=pass AND union_cooldown_status=pass AND first_trigger_status in supported AND PIT pass AND next-open executable",
            "diagnostic_family_policy": "exclude",
            "non_executable_policy": "exclude from canonical output",
            "pit_blocked_policy": "exclude from canonical output",
            "rule_text": "This row freezes the supported denominator used by state_change_candidate_event_canonical.csv.gz.",
        },
        {
            "canonicalizer_id": CANONICALIZER_ID,
            "component_id": "C0_diagnostic_family_policy",
            "component_role": "diagnostic_family_handling",
            "input_family_scope": "B7 and blocked industry dimensions",
            "priority_order_json": "{}",
            "family_level_cooldown_sessions": int(config["canonicalization"]["family_level_cooldown_sessions"]),
            "union_level_cooldown_sessions": int(config["canonicalization"]["union_level_cooldown_sessions"]),
            "first_trigger_supported_statuses_json": json_compact(config["canonicalization"]["supported_first_trigger_statuses"]),
            "cooldown_reentry_policy": "",
            "same_day_collision_policy": "",
            "union_cooldown_policy": "",
            "allowed_primary_filter": "allowed_for_primary_canonical_flag=false",
            "diagnostic_family_policy": "raw density/readout only",
            "non_executable_policy": "",
            "pit_blocked_policy": "blocked dimensions have formula-spec rows only",
            "rule_text": "B7 and PIT-industry blocked rows cannot satisfy runnable_family_n or become primary canonical events.",
        },
    ]
    for row in rows:
        row["rule_hash"] = stable_hash(row)
    return pd.DataFrame(rows)


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    executable_columns = (
        "usable_trade_date",
        "instrument",
        "source_membership_date",
        "membership_date",
        "available_time",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
        "raw_unadjusted_close",
        "total_market_cap_cny",
        "history_ready_240d_flag",
        "history_observed_sessions_before_usable_date",
    )
    membership_columns = (
        "membership_date",
        "usable_trade_date",
        "instrument",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
        "raw_unadjusted_close",
        "total_market_cap_cny",
        "history_ready_240d_flag",
        "history_observed_sessions_before_usable_date",
    )
    specs = [
        ("config", Path(config.get("_config_path", CONFIG_PATH)), True, ()),
        ("requirement", REQUIREMENT_PATH, True, ()),
        ("r_core_demote_or_keep_decision", topic_path(config["paths"]["r_core_demote_or_keep_decision"]), True, ("decision", "population_bridge_status", "next_allowed_requirement")),
        ("source_08_config", topic_path(config["paths"]["source_08_config"]), True, ()),
        ("source_08_feature_panel", topic_path(config["paths"]["source_08_feature_panel"]), True, ("date", "instrument", "market_regime_bucket")),
        ("pit_executable_daily", topic_path(config["paths"]["pit_executable_daily"]), True, executable_columns),
        ("pit_membership_daily", topic_path(config["paths"]["pit_membership_daily"]), True, membership_columns),
        ("stock_daily_csv_dir", topic_path(config["paths"]["stock_daily_csv_dir"]), True, ()),
        ("benchmark_daily_csv", topic_path(config["paths"]["benchmark_daily_csv"]), True, ("trade_date", "index_alias", "open", "high", "low", "close", "volume", "money")),
        ("episode_target_registry_06", topic_path(config["paths"]["episode_target_registry_06"]), True, ("episode_id", "instrument", "episode_low_date", "episode_high_date", "split")),
        ("r_core_density_badside_tradeoff", topic_path(config["paths"]["r_core_density_badside_tradeoff"]), True, ("arm_id", "split", "events_per_instrument_year_mean")),
        ("r_core_arm_event_registry", topic_path(config["paths"]["r_core_arm_event_registry"]), True, ("arm_id", "instrument", "event_signal_date", "event_execution_date", "event_split")),
        ("manifest_12a0_12a1", topic_path(config["paths"]["manifest_12a0_12a1"]), True, ()),
        ("candidate_family_density_summary_08", topic_path(config["paths"]["candidate_family_density_summary_08"]), True, ("candidate_scope_id", "density_by_split")),
    ]
    rows = []
    for artifact_id, path, required, expected_columns in specs:
        exists = path.exists()
        read_status = "missing"
        row_count: int | float = np.nan
        columns: list[str] = []
        if exists and path.is_dir():
            read_status = "readable_directory"
            row_count = len(list(path.glob("*.csv")))
        elif exists:
            try:
                if "".join(path.suffixes).endswith((".csv", ".csv.gz")):
                    frame = pd.read_csv(path, nrows=1000, low_memory=False)
                    row_count = np.nan
                else:
                    frame = read_table(path)
                    row_count = len(frame)
                read_status = "readable_tabular"
                columns = frame.columns.astype(str).tolist()
            except Exception:
                try:
                    path.read_text(encoding="utf-8")
                    read_status = "readable_text"
                except Exception:
                    read_status = "read_error"
        missing_columns = [column for column in expected_columns if column not in columns]
        block_reason = ""
        if required and not exists:
            block_reason = "missing_required_artifact"
        elif missing_columns and read_status == "readable_tabular":
            block_reason = "missing_required_columns:" + ";".join(missing_columns)
        rows.append(
            {
                "artifact_id": artifact_id,
                "artifact_role": "required" if required else "optional",
                "required_for_final_decision_flag": required,
                "required_for_comparison_flag": artifact_id in {"r_core_density_badside_tradeoff", "candidate_family_density_summary_08"},
                "relative_path": str(path.relative_to(REPO_ROOT)) if str(path).startswith(str(REPO_ROOT)) else str(path),
                "resolved_absolute_path": str(path),
                "exists_flag": exists,
                "read_status": read_status,
                "row_count": row_count,
                "column_count": len(columns) if columns else np.nan,
                "sha256": path_sha(path) if exists and path.is_file() else "",
                "source_manifest_path": "",
                "source_manifest_hash": "",
                "expected_columns": ";".join(expected_columns),
                "actual_columns_hash": stable_hash(columns) if columns else "",
                "diagnostic_hash_reference_status": "not_applicable",
                "diagnostic_reconciliation_status": "not_checked",
                "block_reason": block_reason,
            }
        )
    return pd.DataFrame(rows)


def load_upstream_12a1_gate(config: dict[str, Any]) -> dict[str, Any]:
    path = topic_path(config["paths"]["r_core_demote_or_keep_decision"])
    decision = pd.read_csv(path)
    if decision.empty:
        return {
            "input_gate_pass": False,
            "upstream_12a1_decision": "",
            "upstream_population_bridge_status": "",
            "upstream_next_allowed_requirement": "",
            "handoff_conflict_flag": False,
            "upstream_block_reason": "upstream_12a1_decision_empty",
        }
    record = decision.iloc[0].to_dict()
    upstream_decision = str(record.get("decision", ""))
    population_bridge_status = str(record.get("population_bridge_status", ""))
    next_allowed = str(record.get("next_allowed_requirement", ""))
    allowed_decisions = {
        "12A1_r_core_recall_benchmark_only",
        "12A1_r_core_feature_source_only",
        "12A1_r_core_backbone_supported",
    }
    if upstream_decision == "12A1_r_core_population_blocked":
        reason = "upstream_12a1_population_blocked"
    elif upstream_decision not in allowed_decisions:
        reason = "upstream_12a1_decision_not_allowed"
    elif population_bridge_status != "pass":
        reason = "upstream_12a1_population_bridge_not_pass"
    else:
        reason = ""
    handoff_conflict = bool(
        next_allowed
        and next_allowed
        not in {
            "stop_no_valid_backbone_for_morphology",
            "requirement_12a2_state_change_backbone_candidate_generator.md",
        }
    )
    return {
        "input_gate_pass": reason == "",
        "upstream_12a1_decision": upstream_decision,
        "upstream_population_bridge_status": population_bridge_status,
        "upstream_next_allowed_requirement": next_allowed,
        "handoff_conflict_flag": handoff_conflict,
        "upstream_block_reason": reason,
    }


def binary_entropy_from_share(share: float) -> float:
    if pd.isna(share):
        return np.nan
    if share <= 0.0 or share >= 1.0:
        return 0.0
    return float(-(share * math.log2(share) + (1.0 - share) * math.log2(1.0 - share)))


def rolling_last_rank(values: np.ndarray) -> float:
    if len(values) == 0 or np.isnan(values[-1]):
        return np.nan
    clean = values[~np.isnan(values)]
    if len(clean) == 0:
        return np.nan
    return float((clean <= values[-1]).sum()) / float(len(clean))


def load_benchmark_returns(path: Path) -> pd.DataFrame:
    benchmark = pd.read_csv(path)
    all_a = benchmark.loc[benchmark["index_alias"].astype(str).eq("all_a")].copy()
    all_a["date"] = pd.to_datetime(all_a["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    all_a = all_a.sort_values("date")
    close = pd.to_numeric(all_a["close"], errors="coerce")
    all_a["all_a_close"] = close
    all_a["all_a_drawdown_60d"] = close / close.rolling(60, min_periods=40).max() - 1.0
    for horizon in (1, 5, 10, 20, 60):
        all_a[f"market_return_{horizon}d"] = close / close.shift(horizon) - 1.0
    return all_a[
        [
            "date",
            "all_a_close",
            "all_a_drawdown_60d",
            "market_return_1d",
            "market_return_5d",
            "market_return_10d",
            "market_return_20d",
            "market_return_60d",
        ]
    ]


def load_executable_dates(path: Path) -> dict[str, set[str]]:
    frame = pd.read_csv(path, usecols=["instrument", "usable_trade_date"], low_memory=False)
    frame["instrument"] = frame["instrument"].astype(str)
    frame["usable_trade_date"] = pd.to_datetime(frame["usable_trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    frame = frame.dropna(subset=["instrument", "usable_trade_date"]).drop_duplicates()
    return {
        instrument: set(group["usable_trade_date"].astype(str).tolist())
        for instrument, group in frame.groupby("instrument", sort=False)
    }


def enrich_instrument_daily(
    instrument: str,
    stock_path: Path,
    panel_i: pd.DataFrame,
    benchmark_returns: pd.DataFrame,
) -> pd.DataFrame:
    daily = pd.read_csv(stock_path)
    daily["date"] = pd.to_datetime(daily["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    daily = daily.sort_values("date").reset_index(drop=True)
    for column in ["open", "high", "low", "close", "volume", "money", "turnover_rate"]:
        daily[column] = pd.to_numeric(daily.get(column), errors="coerce")
    close = daily["close"]
    high = daily["high"]
    low = daily["low"]
    open_ = daily["open"]
    for horizon in (1, 5, 10, 20, 60):
        daily[f"return_{horizon}d"] = close / close.shift(horizon) - 1.0
    daily["ema20"] = close.ewm(span=20, min_periods=15, adjust=False).mean()
    daily["ema60"] = close.ewm(span=60, min_periods=40, adjust=False).mean()
    daily["close_to_ema20"] = close / daily["ema20"] - 1.0
    daily["close_to_ema60"] = close / daily["ema60"] - 1.0
    daily["rolling_high_60"] = high.rolling(60, min_periods=40).max()
    daily["rolling_high_120"] = high.rolling(120, min_periods=80).max()
    daily["rolling_low_60"] = low.rolling(60, min_periods=40).min()
    daily["close_to_high_60"] = close / daily["rolling_high_60"]
    daily["close_to_high_120"] = close / daily["rolling_high_120"]
    daily["near_high_60"] = daily["close_to_high_60"]
    daily["distance_from_low_60"] = close / daily["rolling_low_60"] - 1.0
    high20 = high.rolling(20, min_periods=15).max()
    low20 = low.rolling(20, min_periods=15).min()
    range20 = high20 - low20
    daily["range_width_20d"] = range20 / close
    daily["range_width_ratio_20d_60d"] = daily["range_width_20d"] / daily["range_width_20d"].rolling(60, min_periods=40).median()
    daily["range_compression_recent_5d"] = daily["range_width_ratio_20d_60d"].rolling(5, min_periods=3).min()
    daily["close_position_in_range"] = (close - low20) / range20.replace(0.0, np.nan)
    daily["intraday_range_pct"] = (high - low) / close
    daily["range_pct"] = daily["intraday_range_pct"]
    daily["range_pct_mean_10d_lag1"] = daily["range_pct"].rolling(10, min_periods=7).mean().shift(1)
    daily["range_pct_mean_20d_lag1"] = daily["range_pct"].rolling(20, min_periods=15).mean().shift(1)
    daily["range_pct_mean_60d_lag1"] = daily["range_pct"].rolling(60, min_periods=40).mean().shift(1)
    daily["range_compression_ratio_10_60_lag1"] = daily["range_pct_mean_10d_lag1"] / daily["range_pct_mean_60d_lag1"]
    daily["upper_shadow_pct"] = (high - np.maximum(open_, close)) / close
    prev_close = close.shift(1)
    true_range = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    daily["atr_20_pct"] = true_range.rolling(20, min_periods=15).mean() / close
    daily["atr_pct_rank_60d"] = daily["atr_20_pct"].rolling(60, min_periods=20).apply(rolling_last_rank, raw=True)
    daily["atr_pct_rank_60d_lag1"] = daily["atr_pct_rank_60d"].shift(1)
    money = daily["money"].replace(0.0, np.nan)
    turnover = daily["turnover_rate"].replace(0.0, np.nan)
    daily["amount_ratio_20d"] = money / money.rolling(20, min_periods=10).median()
    daily["amount_ratio_60d"] = money / money.rolling(60, min_periods=30).median()
    daily["turnover_ratio_20d"] = turnover / turnover.rolling(20, min_periods=10).median()
    daily["turnover_ratio_60d"] = turnover / turnover.rolling(60, min_periods=30).median()
    pos_share = daily["return_1d"].gt(0).rolling(20, min_periods=15).mean()
    daily["direction_entropy_20d"] = pos_share.map(binary_entropy_from_share)
    daily["direction_entropy_20d_lag1"] = daily["direction_entropy_20d"].shift(1)
    daily = daily.merge(benchmark_returns, on="date", how="left")
    cov_60 = daily["return_1d"].rolling(60, min_periods=40).cov(daily["market_return_1d"]).shift(1)
    var_60 = daily["market_return_1d"].rolling(60, min_periods=40).var().shift(1)
    daily["beta_60"] = (cov_60 / var_60.replace(0.0, np.nan)).clip(-1.0, 3.0)
    daily["residual_ret_1d"] = daily["return_1d"] - daily["beta_60"] * daily["market_return_1d"]
    daily["residual_ret_5d"] = daily["residual_ret_1d"].rolling(5, min_periods=3).sum()
    daily["residual_cusum_20d"] = daily["residual_ret_1d"].rolling(20, min_periods=15).sum()
    daily["residual_cusum_20d_lagmax"] = daily["residual_cusum_20d"].shift(1).rolling(20, min_periods=10).max()
    for horizon in (1, 5, 10, 20, 60):
        daily[f"stock_vs_market_{horizon}d"] = daily[f"return_{horizon}d"] - daily[f"market_return_{horizon}d"]
    daily["relative_cusum_10d"] = daily["stock_vs_market_1d"].rolling(10, min_periods=7).sum()
    daily["relative_cusum_20d"] = daily["stock_vs_market_1d"].rolling(20, min_periods=15).sum()
    above = daily["close_to_ema60"].gt(0)
    run_id = (~above).cumsum()
    daily["ema60_positive_run"] = above.groupby(run_id).cumcount() + 1
    daily.loc[~above, "ema60_positive_run"] = 0
    daily["above_ema60_flag"] = above.astype(int)
    daily["above_ema60_days_20"] = daily["above_ema60_flag"].rolling(20, min_periods=20).sum()

    panel_cols = [
        "date",
        "board_bucket",
        "market_regime_bucket",
        "total_market_cap_cny",
        "history_observed_sessions_before_usable_date",
        "momentum_percentile_20d",
        "momentum_percentile_60d",
        "momentum_percentile_20d_lag20",
        "evaluated_member_count",
        "universe_up_share",
        "universe_new_high_60_share",
        "universe_equal_weight_return_x",
        "universe_up_share_z",
        "universe_up_share_change_5d",
        "board_equal_weight_return",
        "board_relative_1d",
        "board_relative_cusum_20d",
        "board_return_20d",
        "stock_vs_board_20d",
    ]
    panel_available = [column for column in panel_cols if column in panel_i.columns]
    daily = daily.merge(panel_i[panel_available].drop_duplicates("date"), on="date", how="left")
    daily["board_relative_cusum_20d_lagmax"] = daily["board_relative_cusum_20d"].shift(1).rolling(20, min_periods=10).max()
    daily["stock_vs_board_1d"] = daily["return_1d"] - daily["board_equal_weight_return"]
    daily["stock_vs_board_cusum_20d"] = daily["stock_vs_board_1d"].rolling(20, min_periods=15).sum()
    daily["stock_vs_board_cusum_20d_lagmax"] = daily["stock_vs_board_cusum_20d"].shift(1).rolling(20, min_periods=10).max()
    daily["momentum_rank_jump_20d"] = daily["momentum_percentile_20d"] - daily["momentum_percentile_20d_lag20"]
    daily["prior_below_ema60_days_20"] = close.shift(1).lt(daily["ema60"].shift(1)).rolling(20, min_periods=20).sum()
    daily["ema60_reclaim_today"] = close.ge(daily["ema60"]) & close.shift(1).lt(daily["ema60"].shift(1))
    daily["instrument"] = instrument
    daily["event_t0_pos"] = np.arange(len(daily))
    return daily.replace([np.inf, -np.inf], np.nan)


def value_at(daily: pd.DataFrame, pos: int, column: str, default: float = np.nan) -> float:
    if column not in daily.columns:
        return default
    return safe_num(daily.at[pos, column], default)


def prior_value(daily: pd.DataFrame, pos: int, column: str, default: float = np.nan) -> float:
    if pos <= 0:
        return default
    return value_at(daily, pos - 1, column, default)


def crossed_up(current: float, prior: float, threshold: float) -> bool:
    return pd.notna(current) and current >= threshold and (pd.isna(prior) or prior < threshold)


def reset_for_family(daily: pd.DataFrame, pos: int, spec: VariantSpec) -> bool:
    family = spec.family_id
    if family == "B1":
        if "stock_vs_board" in spec.variant_id:
            return value_at(daily, pos, "stock_vs_board_cusum_20d") <= 0.0 or value_at(daily, pos, "close_to_ema60") < -0.05
        if "board_vs_market" in spec.variant_id:
            return (
                value_at(daily, pos, "board_relative_cusum_20d") < 0.0
                or value_at(daily, pos, "stock_vs_board_20d") < -0.03
                or value_at(daily, pos, "close_to_ema60") < -0.05
            )
        return value_at(daily, pos, "residual_cusum_20d") <= 0.0 or value_at(daily, pos, "close_to_ema60") < -0.05
    if family == "B2":
        if "entropy" in spec.variant_id:
            return value_at(daily, pos, "direction_entropy_20d") > 0.95 or value_at(daily, pos, "close_to_ema20") < -0.03
        return value_at(daily, pos, "atr_pct_rank_60d") > 0.70 or value_at(daily, pos, "close_to_ema20") < -0.03
    if family == "B3":
        return value_at(daily, pos, "close_to_ema60") < -0.03
    if family == "B4":
        return value_at(daily, pos, "all_a_drawdown_60d") < -0.15 or value_at(daily, pos, "board_relative_cusum_20d") < 0.0
    if family == "B5":
        return value_at(daily, pos, "amount_ratio_20d") < 1.0 or value_at(daily, pos, "close_to_ema20") < -0.03
    if family == "B6":
        return value_at(daily, pos, "momentum_percentile_20d") < 0.55 or value_at(daily, pos, "close_to_ema60") < -0.05
    if family == "B7":
        return value_at(daily, pos, "near_high_60") < 0.90 or value_at(daily, pos, "close_to_ema20") < -0.03
    if family == "B8":
        return value_at(daily, pos, "above_ema60_days_20") < 5 or value_at(daily, pos, "close_to_ema60") < -0.02
    return False


def evaluate_variant(
    daily: pd.DataFrame,
    pos: int,
    spec: VariantSpec,
    tracker: dict[str, Any],
) -> tuple[bool, str, dict[str, Any], str]:
    t = spec.threshold_grid
    family = spec.family_id
    origin = "threshold_state_change"
    status = "trigger_evaluated"
    values = {
        "close": value_at(daily, pos, "close"),
        "close_to_ema20": value_at(daily, pos, "close_to_ema20"),
        "close_to_ema60": value_at(daily, pos, "close_to_ema60"),
        "return_5d": value_at(daily, pos, "return_5d"),
        "return_10d": value_at(daily, pos, "return_10d"),
        "return_20d": value_at(daily, pos, "return_20d"),
        "market_return_20d": value_at(daily, pos, "market_return_20d"),
        "all_a_drawdown_60d": value_at(daily, pos, "all_a_drawdown_60d"),
        "residual_ret_5d": value_at(daily, pos, "residual_ret_5d"),
        "residual_cusum_20d": value_at(daily, pos, "residual_cusum_20d"),
        "residual_cusum_20d_lagmax": value_at(daily, pos, "residual_cusum_20d_lagmax"),
        "stock_vs_market_5d": value_at(daily, pos, "stock_vs_market_5d"),
        "stock_vs_market_10d": value_at(daily, pos, "stock_vs_market_10d"),
        "stock_vs_market_20d": value_at(daily, pos, "stock_vs_market_20d"),
        "relative_cusum_10d": value_at(daily, pos, "relative_cusum_10d"),
        "relative_cusum_20d": value_at(daily, pos, "relative_cusum_20d"),
        "stock_vs_board_20d": value_at(daily, pos, "stock_vs_board_20d"),
        "stock_vs_board_cusum_20d": value_at(daily, pos, "stock_vs_board_cusum_20d"),
        "stock_vs_board_cusum_20d_lagmax": value_at(daily, pos, "stock_vs_board_cusum_20d_lagmax"),
        "board_relative_cusum_20d": value_at(daily, pos, "board_relative_cusum_20d"),
        "board_relative_cusum_20d_lagmax": value_at(daily, pos, "board_relative_cusum_20d_lagmax"),
        "board_return_20d": value_at(daily, pos, "board_return_20d"),
        "range_width_ratio_20d_60d": value_at(daily, pos, "range_width_ratio_20d_60d"),
        "range_compression_recent_5d": value_at(daily, pos, "range_compression_recent_5d"),
        "range_pct": value_at(daily, pos, "range_pct"),
        "range_pct_mean_20d_lag1": value_at(daily, pos, "range_pct_mean_20d_lag1"),
        "range_compression_ratio_10_60_lag1": value_at(daily, pos, "range_compression_ratio_10_60_lag1"),
        "direction_entropy_20d": value_at(daily, pos, "direction_entropy_20d"),
        "direction_entropy_20d_lag1": value_at(daily, pos, "direction_entropy_20d_lag1"),
        "atr_pct_rank_60d": value_at(daily, pos, "atr_pct_rank_60d"),
        "atr_pct_rank_60d_lag1": value_at(daily, pos, "atr_pct_rank_60d_lag1"),
        "amount_ratio_20d": value_at(daily, pos, "amount_ratio_20d"),
        "amount_ratio_60d": value_at(daily, pos, "amount_ratio_60d"),
        "turnover_ratio_20d": value_at(daily, pos, "turnover_ratio_20d"),
        "close_position_in_range": value_at(daily, pos, "close_position_in_range"),
        "close_to_high_60": value_at(daily, pos, "close_to_high_60"),
        "near_high_60": value_at(daily, pos, "near_high_60"),
        "distance_from_low_60": value_at(daily, pos, "distance_from_low_60"),
        "prior_below_ema60_days_20": value_at(daily, pos, "prior_below_ema60_days_20"),
        "ema60_reclaim_today": bool(daily.at[pos, "ema60_reclaim_today"]) if "ema60_reclaim_today" in daily.columns and pd.notna(daily.at[pos, "ema60_reclaim_today"]) else False,
        "momentum_percentile_20d": value_at(daily, pos, "momentum_percentile_20d"),
        "momentum_percentile_60d": value_at(daily, pos, "momentum_percentile_60d"),
        "momentum_percentile_20d_lag20": value_at(daily, pos, "momentum_percentile_20d_lag20"),
        "momentum_rank_jump_20d": value_at(daily, pos, "momentum_rank_jump_20d"),
        "universe_up_share_z": value_at(daily, pos, "universe_up_share_z"),
        "universe_up_share_change_5d": value_at(daily, pos, "universe_up_share_change_5d"),
        "above_ema60_days_20": value_at(daily, pos, "above_ema60_days_20"),
    }
    if family == "B1" and spec.variant_id == "B1a_residual_cusum_20d":
        threshold = float(t["residual_cusum_20d_min"])
        trigger = (
            values["residual_cusum_20d"] >= threshold
            and values["residual_cusum_20d_lagmax"] < threshold
            and values["residual_ret_5d"] >= float(t["residual_ret_5d_min"])
            and values["close_to_ema60"] >= float(t["close_to_ema60_min"])
        )
    elif family == "B1" and spec.variant_id == "B1b_strict_residual_cusum_20d":
        threshold = float(t["residual_cusum_20d_min"])
        trigger = (
            values["residual_cusum_20d"] >= threshold
            and values["residual_cusum_20d_lagmax"] < threshold
            and values["residual_ret_5d"] >= float(t["residual_ret_5d_min"])
            and values["close_to_ema60"] >= float(t["close_to_ema60_min"])
        )
    elif family == "B1" and spec.variant_id == "B1c_stock_vs_board":
        threshold = float(t["stock_vs_board_cusum_20d_min"])
        trigger = (
            values["stock_vs_board_cusum_20d"] >= threshold
            and values["stock_vs_board_cusum_20d_lagmax"] < threshold
            and values["residual_ret_5d"] >= float(t["residual_ret_5d_min"])
            and values["close_to_ema60"] >= float(t["close_to_ema60_min"])
        )
    elif family == "B1" and spec.variant_id == "B1d_board_vs_market_context":
        threshold = float(t["board_relative_cusum_20d_min"])
        trigger = (
            values["board_relative_cusum_20d"] >= threshold
            and values["board_relative_cusum_20d_lagmax"] < threshold
            and values["stock_vs_board_20d"] >= float(t["stock_vs_board_20d_min"])
            and values["residual_ret_5d"] >= float(t["residual_ret_5d_min"])
        )
    elif family == "B2" and spec.variant_id in {"B2a_compression_to_expansion", "B2b_strict_compression_to_expansion"}:
        compression = (
            values["atr_pct_rank_60d_lag1"] <= float(t["atr_pct_rank_60d_max"])
            and values["range_compression_ratio_10_60_lag1"] <= float(t["range_compression_ratio_max"])
        )
        expansion = (
            values["range_pct"] >= values["range_pct_mean_20d_lag1"] * float(t["expansion_multiple"])
            and values["amount_ratio_20d"] >= float(t["amount_ratio_20d_min"])
            and values["close_position_in_range"] >= float(t["close_position_in_range_min"])
            and values["return_5d"] >= float(t["return_5d_min"])
        )
        trigger = compression and expansion
    elif family == "B2" and spec.variant_id == "B2c_entropy_directional_expansion":
        trigger = (
            values["direction_entropy_20d_lag1"] <= float(t["direction_entropy_20d_max"])
            and values["return_5d"] >= float(t["return_5d_min"])
            and values["residual_ret_5d"] >= float(t["residual_ret_5d_min"])
            and values["amount_ratio_20d"] >= float(t["amount_ratio_20d_min"])
            and values["close_position_in_range"] >= float(t["close_position_in_range_min"])
        )
    elif family == "B3" and spec.variant_id in {"B3a_ema60_low_reclaim", "B3b_strict_ema60_low_reclaim"}:
        low_repair_context = values["distance_from_low_60"] >= float(t["distance_from_low_60_min"]) and values["near_high_60"] <= float(t["near_high_60_max"])
        confirmation = (
            values["prior_below_ema60_days_20"] >= float(t["prior_below_ema60_days_20_min"])
            and values["return_5d"] >= float(t["return_5d_min"])
            and values["stock_vs_board_20d"] >= float(t["stock_vs_board_20d_min"])
            and values["close_position_in_range"] >= float(t["close_position_in_range_min"])
        )
        trigger = values["ema60_reclaim_today"] and low_repair_context and confirmation
    elif family == "B4" and spec.variant_id in {"B4a_board_regime_turn", "B4b_strict_board_regime_turn"}:
        market_turn = values["market_return_20d"] >= 0.0 and values["all_a_drawdown_60d"] >= -0.10
        board_turn = values["board_relative_cusum_20d"] >= float(t["board_relative_cusum_20d_min"]) and values["board_return_20d"] >= 0.0
        stock_participation = values["residual_ret_5d"] >= float(t["residual_ret_5d_min"]) and values["stock_vs_board_20d"] >= 0.0
        trigger = market_turn and board_turn and stock_participation
    elif family == "B5" and spec.variant_id == "B5a_amount_regime_shift":
        trigger = (
            values["amount_ratio_20d"] >= float(t["amount_ratio_20d_min"])
            and values["amount_ratio_60d"] >= float(t["amount_ratio_60d_min"])
            and values["return_5d"] >= float(t["return_5d_min"])
            and values["residual_ret_5d"] >= float(t["residual_ret_5d_min"])
            and values["close_position_in_range"] >= float(t["close_position_in_range_min"])
        )
    elif family == "B5" and spec.variant_id == "B5b_strict_amount_regime_shift":
        trigger = (
            values["amount_ratio_20d"] >= float(t["amount_ratio_20d_min"])
            and values["amount_ratio_60d"] >= float(t["amount_ratio_60d_min"])
            and values["return_5d"] >= float(t["return_5d_min"])
            and values["residual_ret_5d"] >= float(t["residual_ret_5d_min"])
            and values["close_position_in_range"] >= float(t["close_position_in_range_min"])
        )
    elif family == "B6" and spec.variant_id in {"B6a_first_leadership_rank_entry", "B6b_strict_first_leadership_rank_entry"}:
        rank_entry = (
            values["momentum_percentile_20d_lag20"] <= float(t["lag_momentum_percentile_20d_max"])
            and values["momentum_percentile_20d"] >= float(t["momentum_percentile_20d_min"])
            and values["momentum_rank_jump_20d"] >= float(t["momentum_rank_jump_20d_min"])
        )
        quality_confirmation = values["residual_ret_5d"] >= float(t["residual_ret_5d_min"]) and values["close_to_ema60"] >= float(t["close_to_ema60_min"])
        trigger = rank_entry and quality_confirmation
    elif family == "B7":
        trigger = (
            values["near_high_60"] >= float(t["near_high_60_min"])
            and values["amount_ratio_20d"] >= float(t["amount_ratio_20d_min"])
            and values["close_position_in_range"] >= float(t["close_position_in_range_min"])
            and values["residual_ret_5d"] >= float(t["residual_ret_5d_min"])
        )
        origin = "diagnostic_high_base_breakout"
    elif family == "B8":
        required = [values["above_ema60_days_20"], values["close_to_ema60"], values["return_20d"], values["stock_vs_market_5d"]]
        lookback_complete = all(pd.notna(value) for value in required)
        current_state = lookback_complete and values["above_ema60_days_20"] >= float(t["above_ema60_days_20_min"]) and values["close_to_ema60"] >= float(t["close_to_ema60_min"]) and values["return_20d"] >= float(t["return_20d_min"]) and values["stock_vs_market_5d"] >= float(t["stock_vs_market_5d_min"])
        previous_state = tracker.get("b8_previous_evaluated_state")
        if not lookback_complete:
            trigger = False
            origin = "missing_required_lookback"
            status = "blocked_missing_b8_prior_state"
        elif current_state and previous_state is None:
            trigger = True
            origin = "first_observed_sustained_state"
        elif current_state and previous_state is False:
            trigger = True
            origin = "false_to_true_sustained_state"
        else:
            trigger = False
            origin = "state_already_true_or_false"
        if lookback_complete:
            tracker["b8_previous_evaluated_state"] = bool(current_state)
    else:
        trigger = False
    values["threshold_grid"] = spec.threshold_grid
    return bool(trigger), origin, values, status


def make_event_row(
    daily: pd.DataFrame,
    pos: int,
    spec: VariantSpec,
    config: dict[str, Any],
    executable_dates: set[str],
    trigger_origin: str,
    trigger_values: dict[str, Any],
    reset_before_event: bool,
    first_trigger_status: str,
    family_cooldown_status: str,
    raw_event_status: str,
) -> dict[str, Any]:
    instrument = str(daily.at[pos, "instrument"])
    event_date = str(daily.at[pos, "date"])
    trade_pos = pos + 1 if pos + 1 < len(daily) else -1
    trade_date = str(daily.at[trade_pos, "date"]) if trade_pos >= 0 else ""
    trade_price = value_at(daily, trade_pos, "open") if trade_pos >= 0 else np.nan
    trade_open_pit_status = "pass" if trade_date in executable_dates else "blocked_missing_next_open_executable_universe"
    non_executable = trade_pos < 0 or pd.isna(trade_price) or trade_open_pit_status != "pass"
    non_executable_reason = "" if not non_executable else ("missing_next_open_price" if trade_pos < 0 or pd.isna(trade_price) else trade_open_pit_status)
    event_id = stable_hash([RUN_ID, spec.family_variant_id, instrument, event_date, int(pos), trade_date, FORMULA_VERSION])
    trigger_payload = {
        column: trigger_values.get(column)
        for column in spec.required_input_columns
        if column in trigger_values
    }
    trigger_payload["threshold_grid"] = spec.threshold_grid
    trigger_payload["family_trigger_origin"] = trigger_origin
    feature_snapshot_hash = stable_hash({k: v for k, v in trigger_payload.items() if k != "threshold_grid"})
    return {
        "event_instance_id": event_id,
        "family_id": spec.family_id,
        "variant_id": spec.variant_id,
        "family_variant_id": spec.family_variant_id,
        "instrument": instrument,
        "event_t0_date": event_date,
        "event_t0_pos": int(pos),
        "event_signal_time": "t0_close",
        "trade_open_date": trade_date,
        "trade_open_pos": int(trade_pos) if trade_pos >= 0 else np.nan,
        "trade_open_price": trade_price,
        "non_executable_next_open": bool(non_executable),
        "non_executable_reason": non_executable_reason,
        "event_split": split_for_date(event_date, config),
        "board_bucket": str(daily.at[pos, "board_bucket"]) if "board_bucket" in daily and pd.notna(daily.at[pos, "board_bucket"]) else "",
        "market_regime_bucket": str(daily.at[pos, "market_regime_bucket"]) if "market_regime_bucket" in daily and pd.notna(daily.at[pos, "market_regime_bucket"]) else "missing_insufficient_lookback",
        "total_market_cap_cny": value_at(daily, pos, "total_market_cap_cny"),
        "history_ready_240d_flag": value_at(daily, pos, "history_observed_sessions_before_usable_date", 0.0) >= 240,
        "feature_snapshot_hash": feature_snapshot_hash,
        "trigger_values_json": json_compact(trigger_payload),
        "family_trigger_origin": trigger_origin,
        "reset_state_before_event": bool(reset_before_event),
        "first_trigger_status": first_trigger_status,
        "family_cooldown_status": family_cooldown_status,
        "union_cooldown_status": "not_evaluated",
        "raw_event_status": raw_event_status,
        "pit_status": "pass",
        "event_t0_pit_status": "pass",
        "trade_open_pit_status": trade_open_pit_status,
        "candidate_generation_status": "raw_trigger_generated",
        "family_input_status": spec.family_input_status,
        "allowed_for_primary_canonical_flag": spec.allowed_for_primary_canonical_flag,
        "canonical_priority": spec.priority,
        "formula_version": FORMULA_VERSION,
    }


def generate_events_for_instrument(
    instrument: str,
    daily: pd.DataFrame,
    config: dict[str, Any],
    specs: list[VariantSpec],
    executable_dates: set[str],
) -> pd.DataFrame:
    runnable_specs = [
        spec
        for spec in specs
        if spec.family_input_status in {"runnable_existing_data", "diagnostic_only"}
    ]
    member_positions = daily.index[daily["market_regime_bucket"].notna()].tolist()
    if not member_positions:
        return pd.DataFrame()
    trackers = {
        spec.family_variant_id: {"armed_state": True, "last_family_kept_pos": None}
        for spec in runnable_specs
    }
    rows: list[dict[str, Any]] = []
    for pos in member_positions:
        event_date = str(daily.at[pos, "date"])
        if split_for_date(event_date, config) == "outside_split":
            continue
        for spec in runnable_specs:
            tracker = trackers[spec.family_variant_id]
            reset_before_event = reset_for_family(daily, pos, spec)
            if reset_before_event:
                tracker["armed_state"] = True
            trigger, origin, values, eval_status = evaluate_variant(daily, pos, spec, tracker)
            if not trigger:
                continue
            last_pos = tracker.get("last_family_kept_pos")
            if last_pos is None:
                first_status = "first_observed_in_sample"
                cooldown_status = "pass"
            elif tracker.get("armed_state", False):
                first_status = "first_after_reset"
                cooldown_status = "pass"
            elif int(pos) - int(last_pos) >= int(spec.cooldown_sessions):
                first_status = "cooldown_reentry_without_reset"
                cooldown_status = "pass"
            else:
                first_status = "cooldown_blocked_without_reset"
                cooldown_status = "blocked"
            if cooldown_status == "pass":
                tracker["last_family_kept_pos"] = int(pos)
                tracker["armed_state"] = False
            raw_status = eval_status if eval_status.startswith("blocked_") else "triggered"
            rows.append(
                make_event_row(
                    daily,
                    pos,
                    spec,
                    config,
                    executable_dates,
                    origin,
                    values,
                    reset_before_event,
                    first_status,
                    cooldown_status,
                    raw_status,
                )
            )
    return pd.DataFrame(rows)


def canonicalize_events(
    instances: pd.DataFrame,
    config: dict[str, Any],
    canonicalization_spec_hash: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if instances.empty:
        return pd.DataFrame(), instances
    out = instances.copy()
    primary_mask = (
        out["family_input_status"].astype(str).eq("runnable_existing_data")
        & out["allowed_for_primary_canonical_flag"].astype(bool)
        & out["family_cooldown_status"].astype(str).eq("pass")
        & out["first_trigger_status"].astype(str).isin(SUPPORTED_FIRST_TRIGGER_STATUSES)
        & out["event_t0_pit_status"].astype(str).eq("pass")
        & out["market_regime_bucket"].astype(str).ne("missing_insufficient_lookback")
        & ~out["non_executable_next_open"].astype(bool)
        & out["trade_open_pit_status"].astype(str).eq("pass")
    )
    out.loc[~primary_mask, "union_cooldown_status"] = "not_primary_eligible"
    eligible = out.loc[primary_mask].sort_values(
        ["instrument", "event_t0_pos", "event_t0_date", "canonical_priority", "family_variant_id"]
    )
    rows: list[dict[str, Any]] = []
    for instrument, group_i in eligible.groupby("instrument", sort=True):
        last_union_pos: int | None = None
        for (_, event_date), group in group_i.groupby(["event_t0_pos", "event_t0_date"], sort=True):
            pos = int(group["event_t0_pos"].iloc[0])
            if last_union_pos is not None and pos - last_union_pos < int(config["canonicalization"]["union_level_cooldown_sessions"]):
                out.loc[group.index, "union_cooldown_status"] = "blocked"
                continue
            out.loc[group.index, "union_cooldown_status"] = "pass"
            ordered = group.sort_values(["canonical_priority", "family_variant_id", "event_instance_id"], kind="stable")
            primary = ordered.iloc[0]
            variants = list(dict.fromkeys(ordered["family_variant_id"].astype(str).tolist()))
            families = list(dict.fromkeys(ordered["family_id"].astype(str).tolist()))
            canonical_event_id = stable_hash(
                [
                    RUN_ID,
                    instrument,
                    event_date,
                    pos,
                    primary["family_id"],
                    variants,
                    FORMULA_VERSION,
                    canonicalization_spec_hash,
                ]
            )
            rows.append(
                {
                    "canonical_event_id": canonical_event_id,
                    "primary_event_instance_id": primary["event_instance_id"],
                    "primary_family_id": primary["family_id"],
                    "primary_variant_id": primary["variant_id"],
                    "instrument": instrument,
                    "event_t0_date": event_date,
                    "event_t0_pos": pos,
                    "event_signal_time": primary["event_signal_time"],
                    "trade_open_date": primary["trade_open_date"],
                    "trade_open_pos": primary["trade_open_pos"],
                    "trade_open_price": primary["trade_open_price"],
                    "event_split": primary["event_split"],
                    "board_bucket": primary["board_bucket"],
                    "market_regime_bucket": primary["market_regime_bucket"],
                    "triggered_family_variants": ";".join(variants),
                    "triggered_family_count": len(families),
                    "first_trigger_status": primary["first_trigger_status"],
                    "canonicalization_rule": CANONICALIZER_ID,
                    "canonical_priority": primary["canonical_priority"],
                    "event_window_anchor_date": primary["event_t0_date"],
                    "event_window_anchor_pos": primary["event_t0_pos"],
                    "event_window_anchor_status": "event_t0_close_anchor",
                    "non_executable_next_open": bool(primary["non_executable_next_open"]),
                    "event_t0_pit_status": primary["event_t0_pit_status"],
                    "trade_open_pit_status": primary["trade_open_pit_status"],
                    "raw_instance_count_collapsed": int(len(ordered)),
                    "feature_snapshot_hash": primary["feature_snapshot_hash"],
                    "source_formula_hash": stable_hash(FORMULA_VERSION),
                    "canonicalization_spec_hash": canonicalization_spec_hash,
                    "primary_family_trigger_origin": primary["family_trigger_origin"],
                    "candidate_generation_status": "supported_canonical_event",
                }
            )
            last_union_pos = pos
    return pd.DataFrame(rows), out


def rolling_duplicate_rate(events: pd.DataFrame, window: int) -> float:
    if events.empty:
        return np.nan
    duplicate = 0
    total = 0
    for _, group in events.sort_values(["instrument", "event_t0_pos"]).groupby("instrument"):
        diffs = pd.to_numeric(group["event_t0_pos"], errors="coerce").diff()
        duplicate += int(diffs.le(window).sum())
        total += int(len(group))
    return safe_rate(duplicate, total)


def adjacent_gap_median(events: pd.DataFrame) -> float:
    gaps: list[float] = []
    for _, group in events.sort_values(["instrument", "event_t0_pos"]).groupby("instrument"):
        gaps.extend(pd.to_numeric(group["event_t0_pos"], errors="coerce").diff().dropna().tolist())
    return float(np.median(gaps)) if gaps else np.nan


def split_subset(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "all":
        return frame
    return frame.loc[frame["event_split"].astype(str).eq(split)].copy()


def e1_reference_by_split(density_08: pd.DataFrame, split: str) -> tuple[float, int | float]:
    row = density_08.loc[density_08["candidate_scope_id"].astype(str).eq(E1_SCOPE_08)]
    if row.empty:
        return np.nan, np.nan
    record = row.iloc[0]
    if split == "all":
        return float(record["events_per_instrument_year_mean"]), int(record["event_count"])
    try:
        payload = json.loads(str(record["density_by_split"]))
        item = payload.get(split, {})
        return float(item.get("events_per_instrument_year", np.nan)), int(item.get("event_count", 0))
    except Exception:
        return np.nan, np.nan


def r_core_reference_by_split(r_core_density: pd.DataFrame, split: str) -> tuple[float, int | float, float]:
    row = r_core_density.loc[
        r_core_density["arm_id"].astype(str).eq(RAW_R_CORE_ARM)
        & r_core_density["split"].astype(str).eq(split)
    ]
    if row.empty:
        return np.nan, np.nan, np.nan
    record = row.iloc[0]
    return (
        float(record["events_per_instrument_year_mean"]),
        int(record["event_n"]),
        float(record["denominator_instrument_years"]),
    )


def build_density_audit(
    canonical: pd.DataFrame,
    instances: pd.DataFrame,
    r_core_density: pd.DataFrame,
    density_08: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    primary_eligible = instances.loc[
        instances["family_input_status"].astype(str).eq("runnable_existing_data")
        & instances["allowed_for_primary_canonical_flag"].astype(bool)
        & instances["family_cooldown_status"].astype(str).eq("pass")
    ].copy()
    supported_first = primary_eligible.loc[
        primary_eligible["first_trigger_status"].astype(str).isin(SUPPORTED_FIRST_TRIGGER_STATUSES)
    ]
    for split in SPLITS:
        events = split_subset(canonical, split)
        raw_split = split_subset(primary_eligible, split)
        supported_split = split_subset(supported_first, split)
        r_core_mean, r_core_n, denom = r_core_reference_by_split(r_core_density, split)
        e1_mean, e1_n = e1_reference_by_split(density_08, split)
        if pd.isna(denom):
            denom = float(r_core_density["denominator_instrument_years"].dropna().iloc[0])
        counts = events.groupby("instrument").size() if not events.empty else pd.Series(dtype=float)
        avg_years_per_inst = safe_rate(denom, max(1, int(events["instrument"].nunique()) if not events.empty else 1))
        p95 = float((counts / avg_years_per_inst).quantile(0.95)) if len(counts) else 0.0
        event_n = int(len(events))
        epiy = safe_rate(event_n, denom)
        rows.append(
            {
                "candidate_scope_id": "12A2_primary_canonical_union",
                "split": split,
                "event_n": event_n,
                "unique_instrument_n": int(events["instrument"].nunique()) if not events.empty else 0,
                "unique_event_day_n": int(events["event_t0_date"].nunique()) if not events.empty else 0,
                "density_basis_id": "08_full_evaluated_universe_years_252",
                "denominator_source_id": "12A1_r_core_density_badside_tradeoff",
                "denominator_instrument_years": denom,
                "events_per_instrument_year_mean": epiy,
                "events_per_instrument_year_p95": p95,
                "density_vs_08_r_core": safe_rate(epiy, r_core_mean),
                "density_vs_07_E1_only": safe_rate(epiy, e1_mean),
                "r_core_reference_event_n": r_core_n,
                "r_core_reference_events_per_instrument_year_mean": r_core_mean,
                "e1_reference_event_n": e1_n,
                "e1_reference_events_per_instrument_year_mean": e1_mean,
                "rolling_10d_duplicate_rate": rolling_duplicate_rate(events, 10),
                "rolling_20d_duplicate_rate": rolling_duplicate_rate(events, 20),
                "adjacent_gap_median": adjacent_gap_median(events),
                "top_instrument_event_share": safe_rate(int(counts.max()) if len(counts) else 0, event_n),
                "top_board_event_share": safe_rate(int(events["board_bucket"].value_counts().max()) if not events.empty else 0, event_n),
                "non_executable_event_rate": safe_rate(int(raw_split["non_executable_next_open"].astype(bool).sum()) if not raw_split.empty else 0, len(raw_split)),
                "first_trigger_supported_rate": safe_rate(len(supported_split), len(raw_split)),
                "density_status": "ok",
            }
        )
    return pd.DataFrame(rows)


def build_feature_pit_audit(config: dict[str, Any], panel: pd.DataFrame, specs: list[VariantSpec]) -> pd.DataFrame:
    stock_cols = ["open", "high", "low", "close", "money", "turnover_rate"]
    panel_cols = panel.columns.astype(str).tolist()
    rows = [
        {
            "input_source_id": "stock_daily_qfq_panel",
            "input_source_path": str(topic_path(config["paths"]["stock_daily_csv_dir"]).relative_to(REPO_ROOT)),
            "required_columns": ";".join(stock_cols),
            "lookback_sessions": 120,
            "lag_policy": "t0 close only; next-open execution",
            "available_at_t0_close_flag": True,
            "uses_future_return_flag": False,
            "uses_episode_label_flag": False,
            "uses_label_touch_coordinate_flag": False,
            "missing_value_policy": "missing disables trigger",
            "raw_row_count": np.nan,
            "usable_row_count": np.nan,
            "missing_row_rate": np.nan,
            "blocked_row_count": 0,
            "blocked_reason": "",
            "pit_audit_status": "pass",
        },
        {
            "input_source_id": "pit_membership_daily",
            "input_source_path": str(topic_path(config["paths"]["pit_membership_daily"]).relative_to(REPO_ROOT)),
            "required_columns": "membership_date;usable_trade_date;instrument;board_bucket;history_ready_240d_flag;history_observed_sessions_before_usable_date",
            "lookback_sessions": 240,
            "lag_policy": "event_t0 PIT membership and same-day board snapshot",
            "available_at_t0_close_flag": True,
            "uses_future_return_flag": False,
            "uses_episode_label_flag": False,
            "uses_label_touch_coordinate_flag": False,
            "missing_value_policy": "missing membership disables event_t0 eligibility",
            "raw_row_count": np.nan,
            "usable_row_count": np.nan,
            "missing_row_rate": np.nan,
            "blocked_row_count": 0,
            "blocked_reason": "",
            "pit_audit_status": "pass",
        },
        {
            "input_source_id": "pit_executable_daily",
            "input_source_path": str(topic_path(config["paths"]["pit_executable_daily"]).relative_to(REPO_ROOT)),
            "required_columns": "usable_trade_date;instrument;source_membership_date;membership_date;available_time;board_bucket",
            "lookback_sessions": 1,
            "lag_policy": "trade_open eligibility only; not a substitute for event_t0 membership",
            "available_at_t0_close_flag": True,
            "uses_future_return_flag": False,
            "uses_episode_label_flag": False,
            "uses_label_touch_coordinate_flag": False,
            "missing_value_policy": "missing next-open executable row marks raw event non-executable",
            "raw_row_count": np.nan,
            "usable_row_count": np.nan,
            "missing_row_rate": np.nan,
            "blocked_row_count": 0,
            "blocked_reason": "",
            "pit_audit_status": "pass",
        },
        {
            "input_source_id": "08_cross_section_feature_panel",
            "input_source_path": str(topic_path(config["paths"]["source_08_feature_panel"]).relative_to(REPO_ROOT)),
            "required_columns": "date;instrument;market_regime_bucket;board_bucket;momentum_percentile_20d",
            "lookback_sessions": 60,
            "lag_policy": "same-date close feature from frozen 08 panel",
            "available_at_t0_close_flag": True,
            "uses_future_return_flag": False,
            "uses_episode_label_flag": False,
            "uses_label_touch_coordinate_flag": False,
            "missing_value_policy": "missing cross-section feature disables dependent trigger",
            "raw_row_count": int(len(panel)),
            "usable_row_count": int(panel[["date", "instrument"]].dropna().drop_duplicates().shape[0]),
            "missing_row_rate": 0.0 if panel_cols else 1.0,
            "blocked_row_count": 0,
            "blocked_reason": "",
            "pit_audit_status": "pass",
        },
        {
            "input_source_id": "pit_industry_classification",
            "input_source_path": "",
            "required_columns": "pit_industry_code",
            "lookback_sessions": 20,
            "lag_policy": "not available",
            "available_at_t0_close_flag": False,
            "uses_future_return_flag": False,
            "uses_episode_label_flag": False,
            "uses_label_touch_coordinate_flag": False,
            "missing_value_policy": "blocks industry dimensions B4_industry/R4/T1/T2",
            "raw_row_count": 0,
            "usable_row_count": 0,
            "missing_row_rate": 1.0,
            "blocked_row_count": 4,
            "blocked_reason": "blocked_missing_pit_industry_classification",
            "pit_audit_status": "blocked_missing_source",
        },
    ]
    forbidden_hits = []
    for spec in specs:
        forbidden_hits.extend(sorted(FORBIDDEN_FEATURES.intersection(spec.required_input_columns)))
    if forbidden_hits:
        rows.append(
            {
                "input_source_id": "forbidden_feature_scan",
                "input_source_path": "state_change_family_formula_spec.csv",
                "required_columns": ";".join(sorted(set(forbidden_hits))),
                "lookback_sessions": 0,
                "lag_policy": "blocked",
                "available_at_t0_close_flag": False,
                "uses_future_return_flag": True,
                "uses_episode_label_flag": True,
                "uses_label_touch_coordinate_flag": True,
                "missing_value_policy": "not_applicable",
                "raw_row_count": len(specs),
                "usable_row_count": 0,
                "missing_row_rate": np.nan,
                "blocked_row_count": len(forbidden_hits),
                "blocked_reason": "forbidden_future_or_label_feature_detected",
                "pit_audit_status": "blocked_future_or_label_leakage",
            }
        )
    return pd.DataFrame(rows)


def episode_matches(events: pd.DataFrame, episodes: pd.DataFrame, date_pos_lookup: dict[str, dict[str, int]]) -> tuple[set[str], list[float]]:
    if events.empty or episodes.empty:
        return set(), []
    covered: set[str] = set()
    offsets: list[float] = []
    ep_by_inst = {inst: group.copy() for inst, group in episodes.groupby("instrument")}
    for row in events.to_dict("records"):
        instrument = str(row["instrument"])
        eps = ep_by_inst.get(instrument)
        if eps is None or eps.empty:
            continue
        event_date = str(row["event_t0_date"])
        event_dt = pd.to_datetime(event_date, errors="coerce")
        candidates = eps.loc[
            (pd.to_datetime(eps["pre120_calendar_start_date"], errors="coerce") <= event_dt)
            & (event_dt <= pd.to_datetime(eps["episode_high_date"], errors="coerce"))
        ]
        for ep in candidates.to_dict("records"):
            ep_id = str(ep["episode_id"])
            covered.add(ep_id)
            lookup = date_pos_lookup.get(instrument, {})
            event_pos = lookup.get(event_date)
            low_pos = lookup.get(str(ep["episode_low_date"]))
            if event_pos is not None and low_pos is not None:
                offsets.append(float(event_pos - low_pos))
            else:
                offsets.append(float((event_dt - pd.to_datetime(ep["episode_low_date"])).days))
    return covered, offsets


def overlap_row(
    scope_id: str,
    family_id: str,
    overlap_family_id: str,
    split: str,
    raw_events: pd.DataFrame,
    canonical: pd.DataFrame,
    episodes: pd.DataFrame,
    date_pos_lookup: dict[str, dict[str, int]],
) -> dict[str, Any]:
    raw_split = split_subset(raw_events, split)
    canonical_split = split_subset(canonical, split)
    fam_raw = raw_split.loc[raw_split["family_id"].astype(str).eq(family_id)].copy()
    fam_can = canonical_split.loc[canonical_split["primary_family_id"].astype(str).eq(family_id)].copy()
    if overlap_family_id == "B1_or_B3":
        overlap_raw = raw_split.loc[raw_split["family_id"].astype(str).isin(["B1", "B3"])].copy()
        overlap_can = canonical_split.loc[canonical_split["primary_family_id"].astype(str).isin(["B1", "B3"])].copy()
    else:
        overlap_raw = raw_split.loc[raw_split["family_id"].astype(str).eq(overlap_family_id)].copy()
        overlap_can = canonical_split.loc[canonical_split["primary_family_id"].astype(str).eq(overlap_family_id)].copy()
    fam_keys_raw = set(zip(fam_raw["instrument"].astype(str), fam_raw["event_t0_date"].astype(str)))
    overlap_keys_raw = set(zip(overlap_raw["instrument"].astype(str), overlap_raw["event_t0_date"].astype(str)))
    fam_keys_can = set(zip(fam_can["instrument"].astype(str), fam_can["event_t0_date"].astype(str)))
    overlap_keys_can = set(zip(overlap_can["instrument"].astype(str), overlap_can["event_t0_date"].astype(str)))
    same_day_keys = fam_keys_raw & overlap_keys_raw
    covered, offsets = episode_matches(fam_can, episodes if split == "all" else episodes.loc[episodes["split"].astype(str).eq(split)], date_pos_lookup)
    _, overlap_offsets = episode_matches(overlap_can, episodes if split == "all" else episodes.loc[episodes["split"].astype(str).eq(split)], date_pos_lookup)
    total_episodes = len(episodes if split == "all" else episodes.loc[episodes["split"].astype(str).eq(split)])
    if not canonical_split.empty and same_day_keys:
        canonical_keys = list(zip(canonical_split["instrument"].astype(str), canonical_split["event_t0_date"].astype(str)))
        same_day_primary = canonical_split.loc[[key in same_day_keys for key in canonical_keys]].copy()
    else:
        same_day_primary = pd.DataFrame()
    primary_choice = same_day_primary["primary_family_id"].astype(str).value_counts() if not same_day_primary.empty else pd.Series(dtype=int)
    return {
        "diagnostic_scope_id": scope_id,
        "family_id": family_id,
        "overlap_family_id": overlap_family_id,
        "split": split,
        "raw_event_n": int(len(fam_raw)),
        "canonical_event_n": int(len(fam_can)),
        "family_only_raw_event_n": int(len(fam_keys_raw - overlap_keys_raw)),
        "family_only_canonical_event_n": int(len(fam_keys_can - overlap_keys_can)),
        "overlap_raw_event_n": int(len(fam_keys_raw & overlap_keys_raw)),
        "overlap_canonical_event_n": int(len(fam_keys_can & overlap_keys_can)),
        "same_instrument_same_day_overlap_n": int(len(same_day_keys)),
        "same_day_primary_choice_b1_event_n": int(primary_choice.get("B1", 0)),
        "same_day_primary_choice_b3_event_n": int(primary_choice.get("B3", 0)),
        "covered_06_episode_n": int(len(covered)),
        "missed_06_episode_n": int(max(0, total_episodes - len(covered))),
        "median_trading_days_from_episode_low": float(np.median(offsets)) if offsets else np.nan,
        "p25_trading_days_from_episode_low": float(np.percentile(offsets, 25)) if offsets else np.nan,
        "p75_trading_days_from_episode_low": float(np.percentile(offsets, 75)) if offsets else np.nan,
        "overlap_family_median_trading_days_from_episode_low": float(np.median(overlap_offsets)) if overlap_offsets else np.nan,
        "overlap_family_p25_trading_days_from_episode_low": float(np.percentile(overlap_offsets, 25)) if overlap_offsets else np.nan,
        "overlap_family_p75_trading_days_from_episode_low": float(np.percentile(overlap_offsets, 75)) if overlap_offsets else np.nan,
        "diagnostic_status": "ok",
        "diagnostic_reason": "",
    }


def build_overlap_diagnostic(
    instances: pd.DataFrame,
    canonical: pd.DataFrame,
    episodes: pd.DataFrame,
    date_pos_lookup: dict[str, dict[str, int]],
) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        rows.append(overlap_row("B8_vs_B1", "B8", "B1", split, instances, canonical, episodes, date_pos_lookup))
        rows.append(overlap_row("B8_vs_B3", "B8", "B3", split, instances, canonical, episodes, date_pos_lookup))
        rows.append(overlap_row("B8_vs_B1_or_B3", "B8", "B1_or_B3", split, instances, canonical, episodes, date_pos_lookup))
        rows.append(overlap_row("B1_vs_B3_same_day_collision", "B1", "B3", split, instances, canonical, episodes, date_pos_lookup))
    return pd.DataFrame(rows)


def build_decision(
    formula_spec: pd.DataFrame,
    instances: pd.DataFrame,
    canonical: pd.DataFrame,
    density: pd.DataFrame,
    feature_audit: pd.DataFrame,
    config: dict[str, Any],
    upstream_gate: dict[str, Any] | None = None,
) -> pd.DataFrame:
    upstream_gate = upstream_gate or {
        "input_gate_pass": True,
        "upstream_12a1_decision": "",
        "upstream_population_bridge_status": "",
        "upstream_next_allowed_requirement": "",
        "handoff_conflict_flag": False,
        "upstream_block_reason": "",
    }
    gates = config["quality_gates"]
    runnable_family_n = int(
        formula_spec.loc[
            formula_spec["family_input_status"].eq("runnable_existing_data")
            & formula_spec["allowed_for_primary_canonical_flag"].astype(bool),
            "family_id",
        ].nunique()
    )
    diagnostic_family_n = int(formula_spec.loc[formula_spec["family_input_status"].eq("diagnostic_only"), "family_id"].nunique())
    blocked_family_n = int(formula_spec.loc[formula_spec["family_input_status"].astype(str).str.startswith("blocked_"), "family_id"].nunique())
    primary_n = int(len(canonical))
    raw_n = int(len(instances))
    runnable_raw_n = int(instances["family_input_status"].astype(str).eq("runnable_existing_data").sum()) if not instances.empty else 0
    supported_raw = instances.loc[
        instances["family_input_status"].astype(str).eq("runnable_existing_data")
        & instances["allowed_for_primary_canonical_flag"].astype(bool)
        & instances["family_cooldown_status"].astype(str).eq("pass")
        & instances["union_cooldown_status"].astype(str).eq("pass")
        & instances["first_trigger_status"].astype(str).isin(SUPPORTED_FIRST_TRIGGER_STATUSES)
        & instances["event_t0_pit_status"].astype(str).eq("pass")
        & instances["market_regime_bucket"].astype(str).ne("missing_insufficient_lookback")
    ].copy()
    executable_supported = supported_raw.loc[
        ~supported_raw["non_executable_next_open"].astype(bool)
        & supported_raw["trade_open_pit_status"].astype(str).eq("pass")
    ]
    next_open_rate = safe_rate(len(executable_supported), len(supported_raw))
    forbidden_pass = not feature_audit["pit_audit_status"].astype(str).eq("blocked_future_or_label_leakage").any()
    density_required_splits = {"all", "train", "robustness"}
    density_failures: list[str] = []
    for split in sorted(density_required_splits):
        row = density.loc[density["split"].astype(str).eq(split)]
        if row.empty:
            density_failures.append(f"{split}:missing_density_row")
            continue
        record = row.iloc[0]
        split_gate = (
            safe_num(record.get("density_vs_08_r_core")) <= float(gates["max_density_vs_08_r_core"])
            and safe_num(record.get("rolling_10d_duplicate_rate")) <= float(gates["max_rolling_10d_duplicate_rate"])
            and safe_num(record.get("top_board_event_share")) <= float(gates["max_top_board_event_share"])
            and safe_num(record.get("first_trigger_supported_rate")) >= float(gates["min_first_trigger_supported_rate"])
        )
        if not split_gate:
            density_failures.append(split)
    density_gate = not density_failures
    nonempty_gate = primary_n > 0 and runnable_family_n >= int(gates["min_runnable_family_n"])
    train_gate = len(canonical.loc[canonical["event_split"].eq("train")]) > 0 if not canonical.empty else False
    robust_gate = len(canonical.loc[canonical["event_split"].eq("robustness")]) > 0 if not canonical.empty else False
    next_open_gate = bool(pd.notna(next_open_rate) and next_open_rate >= float(gates["min_next_open_executable_rate"]))
    if not bool(upstream_gate.get("input_gate_pass", False)):
        decision = "12A2_state_change_candidate_generation_blocked"
        reason = str(upstream_gate.get("upstream_block_reason") or "input_gate_failed")
    elif not forbidden_pass:
        decision = "12A2_state_change_candidate_generation_blocked"
        reason = "forbidden_future_or_label_feature_detected"
    elif not nonempty_gate:
        decision = "12A2_state_change_candidate_generation_empty"
        reason = "primary canonical event_n is zero or runnable_family_n below floor"
    elif not train_gate or not robust_gate:
        decision = "12A2_state_change_candidate_generation_blocked"
        reason = "train_or_robustness_presence_gate_failed"
    elif not next_open_gate:
        decision = "12A2_state_change_candidate_generation_blocked"
        reason = "next_open_executable_rate_below_floor"
    elif not density_gate:
        decision = "12A2_state_change_candidate_generation_supported_with_density_caveat"
        reason = "density_hygiene_gate_failed:" + ";".join(density_failures)
    else:
        decision = "12A2_state_change_candidate_generation_supported"
        reason = "all 12A2 candidate-generation gates passed"
    next_allowed = (
        "requirement_12a3_episode_precision_recall_frontier.md"
        if decision
        in {
            "12A2_state_change_candidate_generation_supported",
            "12A2_state_change_candidate_generation_supported_with_density_caveat",
        }
        else ""
    )
    return pd.DataFrame(
        [
            {
                "decision": decision,
                "decision_reason": reason,
                "input_gate_pass": bool(upstream_gate.get("input_gate_pass", False)),
                "upstream_12a1_decision": str(upstream_gate.get("upstream_12a1_decision", "")),
                "upstream_population_bridge_status": str(upstream_gate.get("upstream_population_bridge_status", "")),
                "upstream_next_allowed_requirement": str(upstream_gate.get("upstream_next_allowed_requirement", "")),
                "pit_feature_gate_pass": True,
                "forbidden_feature_gate_pass": forbidden_pass,
                "candidate_nonempty_gate_pass": nonempty_gate,
                "train_candidate_presence_gate_pass": train_gate,
                "robustness_candidate_presence_gate_pass": robust_gate,
                "next_open_executable_gate_pass": next_open_gate,
                "density_hygiene_gate_pass": density_gate,
                "primary_canonical_event_n": primary_n,
                "raw_instance_event_n": raw_n,
                "runnable_raw_instance_event_n": runnable_raw_n,
                "supported_raw_instance_event_n": int(len(supported_raw)),
                "next_open_executable_event_n": int(len(executable_supported)),
                "next_open_executable_rate": next_open_rate,
                "runnable_family_n": runnable_family_n,
                "diagnostic_family_n": diagnostic_family_n,
                "blocked_family_n": blocked_family_n,
                "density_hygiene_failure_splits": ";".join(density_failures),
                "handoff_conflict_flag": bool(upstream_gate.get("handoff_conflict_flag", False)),
                "block_reason": "" if next_allowed else reason,
                "next_allowed_requirement": next_allowed,
            }
        ]
    )


def build_report(
    decision: pd.DataFrame,
    formula_spec: pd.DataFrame,
    instances: pd.DataFrame,
    canonical: pd.DataFrame,
    density: pd.DataFrame,
    overlap: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    all_density = density.loc[density["split"].eq("all")].iloc[0] if not density.empty else pd.Series(dtype=object)
    formula_family_status = (
        formula_spec.groupby(["family_id", "family_input_status"], dropna=False)
        .size()
        .reset_index(name="variant_n")
        .sort_values(["family_input_status", "family_id"])
    )
    if not instances.empty:
        family_split = (
            instances.groupby(["family_id", "family_input_status", "event_split"], dropna=False)
            .agg(
                raw_event_n=("event_instance_id", "count"),
                executable_rate=("non_executable_next_open", lambda value: 1.0 - float(value.astype(bool).mean())),
            )
            .reset_index()
            .sort_values(["family_id", "event_split"])
        )
    else:
        family_split = pd.DataFrame(columns=["family_id", "family_input_status", "event_split", "raw_event_n", "executable_rate"])
    if not canonical.empty:
        canonical_counts = (
            canonical.groupby(["primary_family_id", "event_split"], dropna=False)
            .size()
            .reset_index(name="canonical_event_n")
            .sort_values(["primary_family_id", "event_split"])
        )
    else:
        canonical_counts = pd.DataFrame(columns=["primary_family_id", "event_split", "canonical_event_n"])
    b8_origins = (
        instances.loc[instances["family_id"].eq("B8"), "family_trigger_origin"].value_counts().to_dict()
        if not instances.empty
        else {}
    )
    b8_split = family_split.loc[family_split["family_id"].eq("B8")].copy()
    b8_canonical_n = int(canonical.loc[canonical["primary_family_id"].eq("B8")].shape[0]) if not canonical.empty else 0
    b8_density = safe_rate(b8_canonical_n, safe_num(all_density.get("denominator_instrument_years"))) if not density.empty else np.nan
    b1_b3 = overlap.loc[overlap["diagnostic_scope_id"].eq("B1_vs_B3_same_day_collision") & overlap["split"].eq("all")]
    b8_gap = overlap.loc[overlap["diagnostic_scope_id"].eq("B8_vs_B1_or_B3") & overlap["split"].eq("all")]
    if not b1_b3.empty:
        b1_row = b1_b3.iloc[0]
        b1_median = safe_num(b1_row.get("median_trading_days_from_episode_low"))
        b3_median = safe_num(b1_row.get("overlap_family_median_trading_days_from_episode_low"))
        if pd.notna(b1_median) and pd.notna(b3_median):
            if b1_median > b3_median:
                b1_b3_conclusion = "B1 primary 的 episode_low lag 中位数晚于 B3，需要在 12A3 验证 C0 priority 是否牺牲 timing。"
            elif b1_median < b3_median:
                b1_b3_conclusion = "B1 primary 的 episode_low lag 中位数早于 B3，当前 priority 没有显示更晚的中位数问题。"
            else:
                b1_b3_conclusion = "B1 与 B3 的 episode_low lag 中位数相同，priority 影响需要看分位数和 recall frontier。"
        else:
            b1_b3_conclusion = "B1/B3 timing 分布样本不足，12A3 需要继续诊断。"
    else:
        b1_b3_conclusion = "没有 B1/B3 同日碰撞诊断行。"
    lines = [
        "# 12A2 State-change Backbone Candidate Generator Report",
        "",
        "## 结论",
        "",
        f"- decision: `{d['decision']}`",
        f"- decision_reason: `{d['decision_reason']}`",
        f"- upstream_12a1_decision: `{d.get('upstream_12a1_decision', '')}`",
        f"- upstream_population_bridge_status: `{d.get('upstream_population_bridge_status', '')}`",
        f"- upstream_next_allowed_requirement: `{d.get('upstream_next_allowed_requirement', '')}`",
        f"- handoff_conflict_flag: `{d['handoff_conflict_flag']}`",
        f"- next_allowed_requirement: `{d['next_allowed_requirement']}`",
        f"- primary canonical event_n: {int(d['primary_canonical_event_n'])}",
        f"- raw instance event_n: {int(d['raw_instance_event_n'])}",
        f"- runnable_family_n / diagnostic_family_n / blocked_family_n: {int(d['runnable_family_n'])} / {int(d['diagnostic_family_n'])} / {int(d['blocked_family_n'])}",
        "",
        "12A2 只生成 PIT-safe state-change candidates，并不证明 episode recall / precision；12A3 才做 episode frontier。",
        "R-core 在本阶段继续作为 recall benchmark only，不作为 backbone primary contract。",
        "",
        "## 密度和执行",
        "",
        f"- density_vs_08_r_core: {safe_num(all_density.get('density_vs_08_r_core')):.4f}",
        f"- density_vs_07_E1_only: {safe_num(all_density.get('density_vs_07_E1_only')):.4f}",
        f"- rolling_10d_duplicate_rate: {safe_num(all_density.get('rolling_10d_duplicate_rate')):.4f}",
        f"- top_board_event_share: {safe_num(all_density.get('top_board_event_share')):.4f}",
        f"- density_hygiene_gate_pass: `{d['density_hygiene_gate_pass']}`",
        f"- density_hygiene_failure_splits: `{d.get('density_hygiene_failure_splits', '')}`",
        f"- next_open_executable_rate: {safe_num(d['next_open_executable_rate']):.4f}",
        "",
        density.to_markdown(index=False) if not density.empty else "无 density audit。",
        "",
        "## Family 状态",
        "",
        formula_family_status.to_markdown(index=False),
        "",
        "## 每个 family 的事件数、split 分布和 executable rate",
        "",
        family_split.to_markdown(index=False) if not family_split.empty else "无 raw family events。",
        "",
        "## Canonical primary 分布",
        "",
        canonical_counts.to_markdown(index=False) if not canonical_counts.empty else "无 canonical events。",
        "",
        "## 被 PIT 行业数据 block 的维度",
        "",
        "- `B4_industry_breadth_context`",
        "- `R4_industry_breadth_expansion`",
        "- `T1_stock_vs_industry_CUSUM_break`",
        "- `T2_industry_vs_market_CUSUM_break`",
        "",
        "## B1 vs B3 同日碰撞",
        "",
        b1_b3.to_markdown(index=False) if not b1_b3.empty else "无 B1/B3 同日碰撞诊断行。",
        "",
        b1_b3_conclusion,
        "",
        "## B8 sustained trend state confirmation",
        "",
        f"- B8 primary canonical event_n: {b8_canonical_n}",
        f"- B8 primary density: {b8_density:.4f}" if pd.notna(b8_density) else "- B8 primary density: nan",
        f"- B8 trigger origin 分布: `{json_compact(b8_origins)}`",
        "",
        b8_split.to_markdown(index=False) if not b8_split.empty else "无 B8 raw event split 分布。",
        "",
        b8_gap.to_markdown(index=False) if not b8_gap.empty else "无 B8 overlap 诊断行。",
        "",
        "B8 用于识别“无穿越但趋势在位”的持续趋势态缺口；它进入 primary 只是候选生成结论，是否提高 winner episode recall 由 12A3 评估。",
        "",
        "## PIT / leakage audit",
        "",
        "所有 runnable family 使用 t0 close 可得字段；未使用 future return、episode label 或 label-derived touch coordinate。",
    ]
    return "\n".join(lines)


def build_date_pos_lookup(daily_by_instrument: dict[str, pd.DataFrame]) -> dict[str, dict[str, int]]:
    return {
        instrument: dict(zip(frame["date"].astype(str), frame["event_t0_pos"].astype(int)))
        for instrument, frame in daily_by_instrument.items()
    }


def run(config_path: Path, mode: str = "full", max_instruments: int | None = None) -> dict[str, Path]:
    config = load_yaml(config_path)
    config["_config_path"] = str(config_path)
    out_paths = output_paths()
    input_audit = build_input_artifact_audit(config)
    outputs: dict[str, Path] = {"input_artifact_audit": write_df(out_paths["input_artifact_audit"], input_audit)}
    if mode == "check-inputs":
        return outputs
    blocked_inputs = input_audit.loc[
        input_audit["required_for_final_decision_flag"].astype(bool)
        & input_audit["block_reason"].astype(str).ne("")
    ]
    if not blocked_inputs.empty:
        raise RuntimeError("required input blocked: " + ";".join(blocked_inputs["artifact_id"].astype(str)))
    upstream_gate = load_upstream_12a1_gate(config)

    specs = build_variant_specs(config)
    formula_spec = build_formula_spec(specs)
    canonicalization_spec = build_canonicalization_spec(config, specs)
    canonicalization_spec_hash = stable_hash(canonicalization_spec.to_dict(orient="records"))
    feature_panel_path = topic_path(config["paths"]["source_08_feature_panel"])
    panel = pd.read_parquet(feature_panel_path)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    panel["instrument"] = panel["instrument"].astype(str)
    if max_instruments is None:
        max_instruments = config.get("runtime", {}).get("max_instruments")
    instruments = sorted(panel["instrument"].dropna().unique().tolist())
    if max_instruments:
        instruments = instruments[: int(max_instruments)]
    panel = panel.loc[panel["instrument"].isin(instruments)].copy()
    benchmark_returns = load_benchmark_returns(topic_path(config["paths"]["benchmark_daily_csv"]))
    executable_dates_by_instrument = load_executable_dates(topic_path(config["paths"]["pit_executable_daily"]))
    stock_dir = topic_path(config["paths"]["stock_daily_csv_dir"])
    daily_by_instrument: dict[str, pd.DataFrame] = {}
    instance_parts: list[pd.DataFrame] = []
    progress_every = int(config.get("runtime", {}).get("progress_every_instruments", 100))
    for idx, instrument in enumerate(instruments, start=1):
        stock_path = stock_dir / f"{instrument}.csv"
        if not stock_path.exists():
            continue
        panel_i = panel.loc[panel["instrument"].eq(instrument)].copy()
        daily = enrich_instrument_daily(instrument, stock_path, panel_i, benchmark_returns)
        daily_by_instrument[instrument] = daily
        events = generate_events_for_instrument(
            instrument,
            daily,
            config,
            specs,
            executable_dates_by_instrument.get(instrument, set()),
        )
        if not events.empty:
            instance_parts.append(events)
        if progress_every and (idx == 1 or idx == len(instruments) or idx % progress_every == 0):
            print(f"[12A2] processed {idx}/{len(instruments)} instruments", flush=True)
    instances = pd.concat(instance_parts, ignore_index=True) if instance_parts else pd.DataFrame()
    canonical, instances = canonicalize_events(instances, config, canonicalization_spec_hash)
    r_core_density = pd.read_csv(topic_path(config["paths"]["r_core_density_badside_tradeoff"]))
    density_08 = pd.read_csv(topic_path(config["paths"]["candidate_family_density_summary_08"]))
    density = build_density_audit(canonical, instances, r_core_density, density_08)
    feature_audit = build_feature_pit_audit(config, panel, specs)
    episodes = pd.read_csv(topic_path(config["paths"]["episode_target_registry_06"]))
    overlap = build_overlap_diagnostic(instances, canonical, episodes, build_date_pos_lookup(daily_by_instrument))
    decision = build_decision(formula_spec, instances, canonical, density, feature_audit, config, upstream_gate)
    report = build_report(decision, formula_spec, instances, canonical, density, overlap)

    for key, frame in [
        ("instances", instances),
        ("canonical", canonical),
        ("formula_spec", formula_spec),
        ("canonicalization_spec", canonicalization_spec),
        ("feature_pit_audit", feature_audit),
        ("density_audit", density),
        ("overlap_diagnostic", overlap),
        ("decision", decision),
    ]:
        outputs[key] = write_df(out_paths[key], frame)
    outputs["report"] = write_text(out_paths["report"], report)
    manifest_artifacts = {**outputs, "manifest": out_paths["manifest"]}
    manifest_payload = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "legacy_directory_id": LEGACY_DIRECTORY_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_revision(REPO_ROOT),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "config_hash": stable_hash(config),
        "input_artifacts": input_audit.to_dict(orient="records"),
        "upstream_12a1_gate": upstream_gate,
        "output_artifacts": {key: str(path) for key, path in manifest_artifacts.items()},
        "output_hashes": {key: path_sha(path) for key, path in outputs.items()},
        "decision": str(decision.iloc[0]["decision"]),
        "decision_reason": str(decision.iloc[0]["decision_reason"]),
        "forbidden_feature_scan_hash": stable_hash(formula_spec[["family_variant_id", "forbidden_feature_scan_status"]].to_dict(orient="records")),
        "formula_spec_hash": stable_hash(formula_spec.to_dict(orient="records")),
        "canonicalization_spec_hash": canonicalization_spec_hash,
    }
    outputs["manifest"] = write_json(out_paths["manifest"], manifest_payload)
    return outputs


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    outputs = run(Path(args.config), mode=args.mode, max_instruments=args.max_instruments)
    for key, path in outputs.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
