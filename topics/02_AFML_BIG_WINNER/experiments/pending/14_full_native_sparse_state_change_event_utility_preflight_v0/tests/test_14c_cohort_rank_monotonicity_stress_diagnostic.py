from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_14c_cohort_rank_monotonicity_stress_diagnostic.py"
REQ_PATH = EXPERIMENT_DIR / "requirement_14c_cohort_rank_monotonicity_stress_diagnostic.md"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_14c_cohort_rank_monotonicity_stress_diagnostic", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def primary_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "family_id": ["F4"] * 4,
            "parameter_set_id": ["ret60_jump3"] * 4,
            "raw_event_arm_id": ["F4_board_relative_strength_rank_jump__ret60_jump3"] * 4,
            "event_id": ["e1", "e1", "e2", "e2"],
            "row_id": ["r1", "r1", "r2", "r2"],
            "instrument": ["S1", "S1", "S1", "S1"],
            "reference_date": ["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-02"],
            "split_bucket": ["train"] * 4,
            "board_bucket": ["main"] * 4,
            "calendar_year": [2020] * 4,
            "instrument_year": ["S1_2020"] * 4,
            "reference_date_rank": [1, 1, 2, 2],
            "event_intensity_score": [0.8, 0.8, 0.7, 0.7],
            "entry_date": ["2020-01-02"] * 4,
            "entry_price": [10.0] * 4,
            "upper_first": [True, True, False, False],
            "lower_first": [False, False, True, True],
            "same_bar_conflict": [False] * 4,
            "winner": [True, True, False, False],
            "fast_fail": [False, False, True, True],
            "upper_barrier_return": [0.1] * 4,
            "lower_barrier_return": [-0.05] * 4,
            "terminal_return_20d": [0.04, 0.04, -0.02, -0.02],
            "max_high_return": [0.12] * 4,
            "min_low_return": [-0.02] * 4,
            "path_utility_component_0bps": [0.1, 0.1, -0.05, -0.05],
            "path_utility_component_50bps": [0.095, 0.095, -0.055, -0.055],
            "path_utility_component_100bps": [0.09, 0.09, -0.06, -0.06],
            "cohort_finite_n": [100] * 4,
            "cohort_percentile_rank": [0.9, 0.9, 0.1, 0.1],
            "cohort_rank_status": ["pass"] * 4,
            "cohort_arm_id": ["C3"] * 4,
            "rank_cutoff_id": ["top10pct", "top20pct", "top10pct", "top20pct"],
            "selected_event_flag": [True] * 4,
            "skipped_event_flag": [False] * 4,
        }
    )


def test_rank_cutoff_canonicalization_prefers_top20_and_detects_mismatch():
    runner = load_runner()
    panel = primary_rows()
    canonical, audit, status = runner.canonicalize_rank_cutoffs(panel)

    assert status == "pass"
    assert canonical["canonical_rank_cutoff_source"].tolist() == ["top20pct", "top20pct"]
    assert audit["duplicate_consistency_status"].eq("pass").all()

    drifted = panel.copy()
    drifted.loc[0, "winner"] = False
    _canonical, audit, status = runner.canonicalize_rank_cutoffs(drifted)

    assert status == "fail"
    winner_row = audit.loc[audit["invariant_field"].eq("winner")].iloc[0]
    assert winner_row["mismatch_group_n"] == 1


def test_feature_enrichment_derives_bucket_and_fails_overlap_conflict():
    runner = load_runner()
    canonical, _audit, _status = runner.canonicalize_rank_cutoffs(primary_rows())
    feature = pd.DataFrame(
        {
            "row_id": ["r1", "r2"],
            "instrument": ["S1", "S1"],
            "reference_date": ["2020-01-01", "2020-01-02"],
            "market_regime_bucket": ["risk_on", "risk_off"],
            "volatility_20d_decile": [2, 8],
            "liquidity_metric_decile": [5, 9],
            "board_bucket": ["main", "main"],
            "calendar_year": [2020, 2020],
            "calendar_month": [1, 1],
            "split": ["train", "train"],
            "split_bucket": ["train", "train"],
        }
    )

    enriched, audit, status = runner.enrich_features(canonical, feature)

    assert status == "pass"
    assert enriched["volatility_bucket"].tolist() == ["low", "high"]
    assert enriched["liquidity_bucket"].tolist() == ["mid", "high"]
    assert audit["split_field_source"].eq("split_bucket").all()

    conflict = feature.copy()
    conflict.loc[0, "board_bucket"] = "other"
    _enriched, audit, status = runner.enrich_features(canonical, conflict)

    assert status == "fail"
    assert audit.loc[audit["overlap_field"].eq("board_bucket"), "feature_conflict_n"].iloc[0] == 1


def test_primary_coverage_status_is_deterministic_for_early_train_drops():
    runner = load_runner()
    primary = pd.DataFrame(
        {
            "raw_event_arm_id": ["arm"] * 5,
            "cohort_arm_id": ["C3"] * 5,
            "split_bucket": ["train"] * 5,
            "calendar_year": [2018, 2018, 2018, 2019, 2019],
            "cohort_rank_status": ["insufficient_cohort", "insufficient_cohort", "pass", "pass", "pass"],
            "cohort_percentile_rank": [np.nan, np.nan, 0.5, 0.4, 0.7],
        }
    )
    finite = primary.loc[primary["cohort_rank_status"].eq("pass")].copy()
    cfg = {"coverage_audit": {"early_history_drop_share_threshold": 0.80}}

    audit, summary = runner.primary_coverage_audit(primary, finite, cfg)

    early = audit.loc[audit["calendar_year"].eq(2018)].iloc[0]
    assert early["coverage_audit_status"] == "train_early_history_concentration"
    assert early["earliest_train_year_drop_share"] == 1.0
    assert summary.iloc[0]["dropped_insufficient_cohort_n"] == 2


def test_badside_gate_requires_bootstrap_ci_not_crossing_zero():
    runner = load_runner()
    primary_ic = pd.DataFrame(
        {
            "split_bucket": ["train", "validation", "robustness"],
            "rank_ic_fast_fail": [-0.01, -0.05, -0.02],
            "rank_ic_utility_50bps": [0.0, -0.01, 0.0],
            "rank_ic_winner": [0.0, 0.0, 0.0],
        }
    )
    bucket = pd.DataFrame(
        {
            "split_bucket": ["train", "validation", "robustness"],
            "top_bottom_fast_fail_delta": [-0.01, -0.04, -0.01],
            "top_bottom_lower_first_delta": [-0.01, -0.01, -0.01],
            "top_bottom_utility_delta_50bps": [0.0, -0.01, 0.0],
            "top_bottom_winner_delta": [0.0, 0.0, 0.0],
        }
    )
    bootstrap = pd.DataFrame(
        {
            "split_bucket": ["validation"],
            "bootstrap_status": ["pass"],
            "rank_ic_fast_fail_ci_high": [0.01],
        }
    )

    gates = runner.monotonicity_gates(primary_ic, bucket, bootstrap, {"stress_gates": {}})
    assert gates["stress_badside_monotonicity_gate_status"] == "fail"

    bootstrap.loc[0, "rank_ic_fast_fail_ci_high"] = -0.001
    gates = runner.monotonicity_gates(primary_ic, bucket, bootstrap, {"stress_gates": {}})
    assert gates["stress_badside_monotonicity_gate_status"] == "pass"


def test_decision_precedence_blocks_defense_when_only_utility_passes():
    runner = load_runner()
    decision = runner.build_decision(
        "pass",
        {
            "selected_raw_event_arm_id": "arm",
            "selected_cohort_arm_id": "C3",
            "selected_rank_cutoff_id": "top20pct",
            "primary_cost_tier_bps": 50,
            "decision_prerequisite_status": "pass",
        },
        "pass",
        {
            "stress_badside_monotonicity_gate_status": "fail",
            "stress_utility_monotonicity_gate_status": "pass",
            "stress_winner_monotonicity_gate_status": "fail",
        },
        "localized_or_weak",
        "pass",
        {},
    )

    row = decision.iloc[0]
    assert row["decision_state"] == "14C_probability_or_utility_monotonic_partial_no_defense_support"
    assert row["next_allowed_requirement"] == "none"
    assert row["secondary_allowed_discussion"] == "requirement_14e_event_uniqueness_redesign_preflight.md"


def test_required_publishable_tables_all_have_schema_sections():
    runner = load_runner()
    text = REQ_PATH.read_text()
    required_block = re.search(r"Required publishable tables:\n\n```text\n(.*?)\n```", text, re.S).group(1)
    required = [line.strip() for line in required_block.splitlines() if line.strip()]
    headings = re.findall(r"### 11\.\d+ `([^`]+)`", text)

    assert sorted(required) == sorted(headings)
    assert sorted(runner.PUBLISHABLE_TABLE_KEYS) == sorted(path[:-4] for path in required)
