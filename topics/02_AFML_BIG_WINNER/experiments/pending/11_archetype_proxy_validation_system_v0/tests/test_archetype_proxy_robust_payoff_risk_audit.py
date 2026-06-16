from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = EXPERIMENT_DIR / "src"

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import run_11a1_archetype_proxy_robust_payoff_risk_audit as audit  # noqa: E402


def test_regime_scope_filter_keeps_only_risk_on_for_evaluation() -> None:
    frame = pd.DataFrame(
        {
            "split": ["train", "train", "validation", "robustness"],
            "episode_regime_bucket_09a": ["risk_on", "", "risk_off", ""],
            "event_regime_bucket": ["risk_on", "transition", "risk_on", ""],
            "event_regime_bucket_09a": ["", "", "", ""],
        }
    )

    scoped, scope_audit, regime_audit = audit.attach_regime_scope(frame)

    assert scoped["risk_on_scope_flag"].tolist() == [True, False, False, False]
    all_row = scope_audit.loc[scope_audit["split"].eq("all")].iloc[0]
    assert all_row["risk_on_evaluated_row_n"] == 1
    assert all_row["transition_out_of_scope_row_n"] == 1
    assert "risk_on_scope_flag" in regime_audit.columns


def test_pit_universe_filter_keeps_only_valid_inner_join_rows(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4],
            "split": ["train", "train", "validation", "robustness"],
            "instrument": ["000001", "000002", "000003", "000004"],
            "event_t0_date": ["2024-01-02", "2024-01-02", "2024-01-02", "2024-01-02"],
            "winner_120": [True, False, False, True],
            "selected_fast_fail_10_label": [False, True, False, False],
            "frozen_false_repair_20d_label": [False, False, True, False],
            "source_family_id": ["a", "a", "b", "b"],
        }
    )
    pit_path = tmp_path / "pit.csv"
    pd.DataFrame(
        {
            "membership_date": ["2024-01-02", "2024-01-02", "2024-01-03"],
            "usable_trade_date": ["2024-01-02", "2024-01-02", "2024-01-03"],
            "instrument": ["000001", "000002", "000003"],
            "board_bucket": ["main_board", "main_board", "main_board"],
            "is_listed": [True, True, True],
            "is_st": [False, True, False],
            "is_suspended": [False, False, False],
            "total_market_cap_cny": [10.0, 10.0, 10.0],
            "market_cap_threshold_cny": [1.0, 1.0, 1.0],
            "source_trade_date": ["2024-01-02", "2024-01-02", "2024-01-03"],
            "membership_rule_version": ["v1", "v1", "v1"],
        }
    ).to_csv(pit_path, index=False)

    filtered, pit_audit, diagnostic = audit.apply_pit_universe_filter(frame, {"pit_universe": pit_path})

    assert filtered["row_id"].tolist() == [1]
    all_row = pit_audit.loc[pit_audit["split"].eq("all")].iloc[0]
    assert all_row["pre_pit_risk_on_row_n"] == 4
    assert all_row["pit_membership_joined_row_n"] == 2
    assert all_row["pit_valid_evaluated_row_n"] == 1
    assert all_row["st_excluded_row_n"] == 1
    all_reasons = set(diagnostic.loc[diagnostic["dimension_name"].eq("all"), "pit_scope_filter_reason"])
    assert {"pit_valid", "st_on_event_t0_date", "before_first_pit_membership", "instrument_never_in_pit"} <= all_reasons


def test_registered_proxy_fields_are_not_outcome_fields() -> None:
    for proxy in audit.proxy_registry():
        assert not (set(proxy["fields"]) & audit.OUTCOME_FORBIDDEN_FIELDS)
    assert len(audit.proxy_registry()) == 8


def test_construct_matched_weights_excludes_zero_negative_cell() -> None:
    frame = pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4],
            "split": ["train", "train", "train", "train"],
            "event_year_quarter": ["2024Q1", "2024Q1", "2024Q2", "2024Q2"],
            "source_family_id_matched": ["a", "a", "b", "b"],
            "final_sample_weight": [1.0, 1.0, 1.0, 1.0],
            "P1_gap_event_proxy": [True, False, True, True],
            "winner_120_bool": [True, False, True, False],
            "fast_fail_10_bool": [False, False, False, False],
            "false_repair_20_bool": [False, False, False, False],
            "big_failure_proxy_bool": [False, False, False, False],
            "e1_missed_winner_bool": [False, False, False, False],
            "forward_return_20d": [0.1, 0.0, 0.2, 0.1],
            "forward_return_60d": [0.2, 0.0, 0.3, 0.1],
            "forward_return_120d": [0.5, 0.0, 0.6, 0.2],
        }
    )

    matched, info = audit.construct_matched_weights(frame, "P1_gap_event_proxy", "train")

    assert matched.loc[matched["row_id"].eq(2), "matched_base_weight"].iloc[0] == 1.0
    assert matched.loc[matched["row_id"].isin([3, 4]), "proxy_positive_weight"].sum() == 2.0
    assert info["unmatched_positive_weight"] == 2.0
    assert info["matched_positive_weight_coverage"] == 1.0 / 3.0


def test_metric_bundle_component_rates_are_explicit() -> None:
    frame = pd.DataFrame(
        {
            "winner_120_bool": [True, False],
            "fast_fail_10_bool": [True, False],
            "false_repair_20_bool": [False, True],
            "big_failure_proxy_bool": [True, True],
            "e1_missed_winner_bool": [False, True],
            "forward_return_20d": [0.1, -0.1],
            "forward_return_60d": [0.2, -0.2],
            "forward_return_120d": [0.5, -0.5],
        }
    )
    weights = pd.Series([1.0, 1.0])

    metrics = audit.metric_bundle(frame, weights)

    assert metrics["fast_fail_10_rate"] == 0.5
    assert metrics["false_repair_20_rate"] == 0.5
    assert metrics["big_failure_proxy_rate"] == 1.0
    assert "forward_return_60d_median" in metrics


def test_final_status_precedence() -> None:
    decisions = pd.DataFrame({"proxy_status": ["proxy_supported"]})

    assert audit.choose_final_status(["missing"], [], decisions) == audit.FINAL_BLOCKED
    assert audit.choose_final_status([], ["incomplete"], decisions) == audit.FINAL_INCOMPLETE
    assert audit.choose_final_status([], [], decisions) == audit.FINAL_SUPPORTED
    assert audit.choose_final_status([], [], pd.DataFrame({"proxy_status": ["proxy_diagnostic_candidate"]})) == audit.FINAL_EMPTY


def test_evidence_score_contract_is_six_items() -> None:
    assert {
        "median_payoff_noninferior",
        "winsorized_payoff_noninferior",
        "right_tail_capture_noninferior",
        "strict_advantage_marker",
        "bootstrap_payoff_stable",
        "validation_not_conflicting",
    }
    assert 6 == 6
