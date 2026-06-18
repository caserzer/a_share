from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


RUNNER_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "run_12a2_state_change_backbone_candidate_generator.py"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a2_state_change", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_b8_first_observed_requires_complete_lookback_and_records_origin():
    runner = load_runner()
    config = runner.load_yaml(runner.CONFIG_PATH)
    spec = next(
        item
        for item in runner.build_variant_specs(config)
        if item.family_variant_id == "B8_B8a_sustained_trend_state"
    )
    daily = pd.DataFrame(
        {
            "close": [10.0, 11.0],
            "close_to_ema60": [0.04, 0.04],
            "return_20d": [0.09, 0.09],
            "stock_vs_market_5d": [0.01, 0.01],
            "above_ema60_days_20": [float("nan"), 12.0],
        }
    )
    tracker: dict[str, object] = {}

    trigger0, origin0, _, status0 = runner.evaluate_variant(daily, 0, spec, tracker)
    trigger1, origin1, _, status1 = runner.evaluate_variant(daily, 1, spec, tracker)

    assert trigger0 is False
    assert origin0 == "missing_required_lookback"
    assert status0 == "blocked_missing_b8_prior_state"
    assert trigger1 is True
    assert origin1 == "first_observed_sustained_state"
    assert status1 == "trigger_evaluated"


def test_canonicalize_excludes_diagnostic_family_from_primary():
    runner = load_runner()
    config = runner.load_yaml(runner.CONFIG_PATH)
    base = {
        "instrument": "A",
        "event_t0_date": "2020-01-02",
        "event_t0_pos": 10,
        "event_signal_time": "t0_close",
        "trade_open_date": "2020-01-03",
        "trade_open_pos": 11,
        "trade_open_price": 10.5,
        "event_split": "train",
        "board_bucket": "main_board",
        "market_regime_bucket": "risk_on",
        "first_trigger_status": "first_observed_in_sample",
        "family_cooldown_status": "pass",
        "union_cooldown_status": "not_evaluated",
        "non_executable_next_open": False,
        "event_t0_pit_status": "pass",
        "trade_open_pit_status": "pass",
        "feature_snapshot_hash": "h",
        "family_trigger_origin": "unit_test",
    }
    rows = [
        {
            **base,
            "event_instance_id": "b7",
            "family_id": "B7",
            "variant_id": "B7a",
            "family_variant_id": "B7_B7a",
            "family_input_status": "diagnostic_only",
            "allowed_for_primary_canonical_flag": False,
            "canonical_priority": 1,
        },
        {
            **base,
            "event_instance_id": "b3",
            "family_id": "B3",
            "variant_id": "B3a",
            "family_variant_id": "B3_B3a",
            "family_input_status": "runnable_existing_data",
            "allowed_for_primary_canonical_flag": True,
            "canonical_priority": 20,
        },
    ]

    canonical, instances = runner.canonicalize_events(
        pd.DataFrame(rows),
        config,
        canonicalization_spec_hash="hash",
    )

    assert canonical["primary_family_id"].tolist() == ["B3"]
    assert instances.loc[instances["event_instance_id"].eq("b7"), "union_cooldown_status"].iloc[0] == "not_primary_eligible"


def test_formula_spec_lists_blocked_industry_context_and_dimensions():
    runner = load_runner()
    config = runner.load_yaml(runner.CONFIG_PATH)
    formula = runner.build_formula_spec(runner.build_variant_specs(config))
    blocked = formula.loc[
        formula["family_input_status"].eq("blocked_missing_pit_industry_classification"),
        "family_id",
    ].tolist()

    assert blocked == [
        "B4_industry_breadth_context",
        "R4_industry_breadth_expansion",
        "T1_stock_vs_industry_CUSUM_break",
        "T2_industry_vs_market_CUSUM_break",
    ]


def minimal_decision_frames(runner):
    config = runner.load_yaml(runner.CONFIG_PATH)
    formula = runner.build_formula_spec(runner.build_variant_specs(config))
    instances = pd.DataFrame(
        [
            {
                "family_input_status": "runnable_existing_data",
                "allowed_for_primary_canonical_flag": True,
                "family_cooldown_status": "pass",
                "union_cooldown_status": "pass",
                "first_trigger_status": "first_observed_in_sample",
                "event_t0_pit_status": "pass",
                "market_regime_bucket": "risk_on",
                "non_executable_next_open": False,
                "trade_open_pit_status": "pass",
            },
            {
                "family_input_status": "runnable_existing_data",
                "allowed_for_primary_canonical_flag": True,
                "family_cooldown_status": "pass",
                "union_cooldown_status": "blocked",
                "first_trigger_status": "first_observed_in_sample",
                "event_t0_pit_status": "pass",
                "market_regime_bucket": "risk_on",
                "non_executable_next_open": False,
                "trade_open_pit_status": "pass",
            },
        ]
    )
    canonical = pd.DataFrame({"event_split": ["train", "robustness"]})
    density = pd.DataFrame(
        {
            "split": ["all", "train", "validation", "robustness"],
            "density_vs_08_r_core": [1.0, 1.0, 99.0, 1.0],
            "rolling_10d_duplicate_rate": [0.1, 0.1, 0.1, 0.1],
            "top_board_event_share": [0.5, 0.5, 0.5, 0.5],
            "first_trigger_supported_rate": [0.8, 0.8, 0.8, 0.8],
        }
    )
    feature_audit = pd.DataFrame({"pit_audit_status": ["pass"]})
    return config, formula, instances, canonical, density, feature_audit


def test_decision_supported_raw_denominator_requires_union_pass():
    runner = load_runner()
    config, formula, instances, canonical, density, feature_audit = minimal_decision_frames(runner)

    decision = runner.build_decision(formula, instances, canonical, density, feature_audit, config).iloc[0]

    assert decision["decision"] == "12A2_state_change_candidate_generation_supported"
    assert decision["supported_raw_instance_event_n"] == 1
    assert decision["next_open_executable_event_n"] == 1


def test_density_failure_is_supported_caveat_not_blocker():
    runner = load_runner()
    config, formula, instances, canonical, density, feature_audit = minimal_decision_frames(runner)
    density.loc[density["split"].eq("train"), "density_vs_08_r_core"] = 1.30

    decision = runner.build_decision(formula, instances, canonical, density, feature_audit, config).iloc[0]

    assert decision["decision"] == "12A2_state_change_candidate_generation_supported_with_density_caveat"
    assert decision["block_reason"] == ""
    assert decision["next_allowed_requirement"] == "requirement_12a3_episode_precision_recall_frontier.md"
