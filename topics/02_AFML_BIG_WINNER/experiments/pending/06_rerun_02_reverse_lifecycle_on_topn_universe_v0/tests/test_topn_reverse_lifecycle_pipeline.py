from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
CODE_DIR = EXPERIMENT_ROOT / "code"
SPEC = importlib.util.spec_from_file_location(
    "topn_reverse_lifecycle_pipeline", CODE_DIR / "pipeline.py"
)
assert SPEC is not None and SPEC.loader is not None
pipeline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pipeline
SPEC.loader.exec_module(pipeline)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_accepts_current_05_available_source_topn_proxy_state() -> None:
    config = load_yaml(EXPERIMENT_ROOT / "config.yaml")

    status = pipeline.validate_topn_inputs(config, PROJECT_ROOT)

    assert status.universe_precision_status == "available_source_topn_candidate_gap"
    assert status.topn_universe_input_accepted
    assert not status.exact_topn_supported
    assert status.topn_candidate_gap_accepted
    assert status.active_source_gap_count == 229
    assert status.missing_active_source_instrument_count == 229
    assert status.missing_active_source_audit_count_reconciled
    assert status.validation_failures == ["active_source_gaps"]


def test_rule_invariant_audit_allows_only_universe_and_precision_difference() -> None:
    config = load_yaml(EXPERIMENT_ROOT / "config.yaml")
    upstream_02_config = load_yaml(
        PROJECT_ROOT
        / "experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/config.yaml"
    )
    status = pipeline.validate_topn_inputs(config, PROJECT_ROOT)

    audit = pipeline.build_rule_invariant_audit(config, upstream_02_config, status)

    blocking_fail = audit.loc[
        (audit["status"] == "fail") & audit["blocking"].astype(bool)
    ]
    allowed = set(audit.loc[audit["allowed_difference"], "rule_name"])
    assert blocking_fail.empty
    assert allowed == {"target_universe_input", "universe_precision_status"}
    assert pipeline.invariant_audit_passed(audit)


def test_02_runner_keeps_legacy_pipeline_module_available_for_runtime_imports() -> None:
    old_pipeline = sys.modules.get("pipeline")

    legacy_runner = pipeline.load_02_runner(PROJECT_ROOT)

    assert hasattr(legacy_runner, "_pipeline_module")
    assert str(legacy_runner._pipeline_module.__file__).endswith(
        "02_big_winner_reverse_lifecycle_profile_v0/code/pipeline.py"
    )
    assert sys.modules.get("pipeline") is old_pipeline


def test_denominator_outputs_derive_year_and_leave_duration_denominator_empty() -> None:
    denominator = pd.DataFrame(
        {
            "evaluated_flag": [True, True, False],
            "year": [2024, 2024, 2025],
            "split": ["train", "train", "validation"],
            "board_bucket": ["main_board", "chinext", "main_board"],
            "market_regime_bucket": ["risk_on", "risk_off", "risk_on"],
        }
    )
    winners = pd.DataFrame(
        {
            "episode_low_date": ["2024-01-02", "2024-01-03"],
            "split": ["train", "train"],
            "board_bucket": ["main_board", "chinext"],
            "market_regime_bucket": ["risk_on", "risk_off"],
            "duration_bucket": ["fast", "medium"],
        }
    )

    outputs = pipeline.build_denominator_outputs(denominator, winners)

    yearly = outputs["topn_episode_rate_by_year"]
    row_2024 = yearly.loc[yearly["year"] == 2024].iloc[0]
    assert row_2024["episode_count"] == 2
    assert row_2024["instrument_days"] == 2
    assert row_2024["episodes_per_100_universe_years"] == pytest.approx(
        2 / (2 / 252) * 100
    )

    duration = outputs["topn_episode_count_summary"].loc[
        outputs["topn_episode_count_summary"]["scope"] == "duration_bucket"
    ]
    assert set(duration["denominator_scope"]) == {
        "not_applicable_duration_episode_attribute"
    }
    assert duration["universe_years_252"].isna().all()


def test_topn_decision_mapping_is_prefixed_and_has_no_generic_sample_blocked() -> None:
    assert (
        pipeline.topn_decision_from_semantic(
            "reverse_lifecycle_profile_validation_sample_blocked", True
        )
        == "topn_reverse_lifecycle_profile_validation_sample_blocked"
    )
    assert (
        pipeline.topn_decision_from_semantic(
            "reverse_lifecycle_profile_validation_sample_blocked", False
        )
        == "topn_reverse_lifecycle_invariant_replay_blocked"
    )
    assert "topn_reverse_lifecycle_sample_blocked" not in set(
        pipeline.DECISION_MAP.values()
    )


def test_fast_02_monkey_patches_match_original_small_sample() -> None:
    legacy_runner = pipeline.load_02_runner(PROJECT_ROOT)
    legacy_pipeline = legacy_runner._pipeline_module
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=80, freq="D").strftime(
                "%Y-%m-%d"
            ),
            "close": [10.0] * 80,
            "low": [9.0] * 80,
            "high": [11.0] * 80,
            "ema60": [9.5] * 80,
            "close_to_ema20": [0.01] * 80,
            "close_to_ema60": [0.02] * 80,
            "ema20_slope_20d": [0.001] * 80,
            "ema60_slope_20d": [0.001] * 80,
            "return_5d": [0.03] * 80,
            "return_20d": [0.04] * 80,
            "return_60d": [0.05] * 80,
            "drawdown_from_60d_high": [-0.10] * 80,
            "distance_to_120d_high": [-0.05] * 80,
            "amount_ratio_20d": [1.1] * 80,
            "amount_ratio_60d": [1.0] * 80,
            "turnover_ratio_20d": [1.2] * 80,
            "derived_daily_vwap_available": [True] * 80,
            "derived_daily_vwap_price_basis": ["qfq"] * 80,
            "derived_daily_vwap_missing_reason": ["not_missing"] * 80,
            "qfq_adjustment_factor_available": [True] * 80,
            "close_to_derived_daily_vwap": [0.01] * 80,
            "open_to_derived_daily_vwap": [0.01] * 80,
            "vwap_deviation_20d_z": [0.2] * 80,
            "vwap_reclaim_flag": [1.0] * 80,
            "intraday_range_pct": [0.03] * 80,
            "close_position_in_range": [0.7] * 80,
            "upper_shadow_pct": [0.02] * 80,
            "gap_open_pct": [0.01] * 80,
            "gap_fade_flag": [0.0] * 80,
            "atr_20_pct": [0.04] * 80,
            "stock_vs_market_20d": [0.06] * 80,
            "market_regime_bucket": ["risk_on"] * 80,
        }
    )
    daily.loc[10, "close_to_ema20"] = pd.NA
    entities = pd.DataFrame(
        {
            "entity_id": ["winner_1", "control_1"],
            "instrument": ["SH600000", "SH600000"],
            "group": ["winner", "control"],
            "axis_date": ["2024-01-20", "2024-01-21"],
            "split": ["train", "train"],
            "duration_bucket": ["fast", "fast"],
            "market_regime_bucket": ["risk_on", "risk_on"],
            "control_is_near_winner": [False, True],
            "control_is_false_repair": [False, False],
        }
    )
    daily_by_instrument = {"SH600000": daily}

    original_panel = legacy_pipeline.build_aligned_panel(
        entities,
        daily_by_instrument,
        entity_id_col="entity_id",
        axis_date_col="axis_date",
        group_col="group",
        shared_axis="shared_axis_low",
        relative_start=-1,
        relative_end=1,
    )
    fast_panel = pipeline.make_fast_aligned_panel_builder(legacy_pipeline)(
        entities,
        daily_by_instrument,
        entity_id_col="entity_id",
        axis_date_col="axis_date",
        group_col="group",
        shared_axis="shared_axis_low",
        relative_start=-1,
        relative_end=1,
    )
    pd.testing.assert_frame_equal(original_panel, fast_panel, check_dtype=False)

    original_sequence = legacy_pipeline.evaluate_sequences_for_entities(
        entities,
        daily_by_instrument,
        entity_id_col="entity_id",
        axis_date_col="axis_date",
        group_col="group",
        horizon_sessions=30,
    )
    fast_sequence = pipeline.make_fast_sequence_evaluator(legacy_pipeline)(
        entities,
        daily_by_instrument,
        entity_id_col="entity_id",
        axis_date_col="axis_date",
        group_col="group",
        horizon_sessions=30,
    )
    pd.testing.assert_frame_equal(original_sequence, fast_sequence, check_dtype=False)

    thresholds = {
        "min_feature_non_missing_coverage_for_claim": 0.0,
        "standardized_mean_difference_gate": 0.25,
        "lift_gate": 1.25,
        "absolute_rate_difference_gate": 0.05,
    }
    original_dominance = legacy_pipeline.summarize_continuous_dominance(
        original_panel,
        shared_axis="shared_axis_low",
        relative_days=[0],
        thresholds=thresholds,
    )
    fast_dominance = pipeline.make_fast_continuous_dominance_summarizer(
        legacy_pipeline
    )(
        fast_panel,
        shared_axis="shared_axis_low",
        relative_days=[0],
        thresholds=thresholds,
    )
    pd.testing.assert_frame_equal(
        original_dominance,
        fast_dominance,
        check_dtype=False,
        rtol=1e-12,
        atol=1e-12,
    )
