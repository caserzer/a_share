from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a6_c0_local_survival_episode_audit.py"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / "12A6_c0_local_survival_episode_audit"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "manifests" / "12A6_c0_local_survival_episode_audit_manifest.json"
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "c0_local_survival_episode_audit_report.md"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a6_survival", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeStockDailyCache:
    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.frames = frames

    def get(self, instrument: str) -> pd.DataFrame | None:
        return self.frames.get(str(instrument))


def table(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLE_DIR / f"{name}.csv", low_memory=False)


def test_first_hit_same_bar_uses_lower_first_priority():
    runner = load_runner()

    assert runner.classify_first_hit(3, None) == ("upper_first", False)
    assert runner.classify_first_hit(None, 4) == ("lower_first", False)
    assert runner.classify_first_hit(None, None) == ("neutral", False)
    assert runner.classify_first_hit(2, 2) == ("lower_first", True)
    assert runner.classify_first_hit(2, 1) == ("lower_first", False)
    assert runner.classify_first_hit(1, 2) == ("upper_first", False)


def test_pit_membership_lookup_streams_and_flags_non_executable_rows(tmp_path):
    runner = load_runner()
    path = tmp_path / "pit.csv"
    pd.DataFrame(
        [
            {"usable_trade_date": "2020-01-02", "instrument": "AAA", "is_listed": True, "is_st": False, "is_suspended": False},
            {"usable_trade_date": "2020-01-02", "instrument": "BBB", "is_listed": True, "is_st": True, "is_suspended": False},
            {"usable_trade_date": "2020-01-03", "instrument": "AAA", "is_listed": True, "is_st": False, "is_suspended": False},
        ]
    ).to_csv(path, index=False)

    lookup = runner.load_pit_membership_lookup(path, {"AAA", "BBB", "CCC"}, {"2020-01-02"}, chunksize=1)

    assert lookup[("AAA", "2020-01-02")] == "pass"
    assert lookup[("BBB", "2020-01-02")] == "st"
    assert ("CCC", "2020-01-02") not in lookup
    assert ("AAA", "2020-01-03") not in lookup


def test_entry_audit_blocks_missing_membership_and_missing_trade_open_price():
    runner = load_runner()
    universe = pd.DataFrame(
        [
            {"instrument": "AAA", "trade_open_date": "2020-01-02", "trade_open_pos": 0, "trade_open_price": 10.0, "trade_open_pit_status": "pass"},
            {"instrument": "BBB", "trade_open_date": "2020-01-02", "trade_open_pos": 0, "trade_open_price": 11.0, "trade_open_pit_status": "pass"},
            {"instrument": "CCC", "trade_open_date": "2020-01-02", "trade_open_pos": 0, "trade_open_price": 12.0, "trade_open_pit_status": "pass"},
        ]
    )
    stock_cache = FakeStockDailyCache(
        {
            "AAA": pd.DataFrame({"date": ["2020-01-02", "2020-01-03"], "open": [10.0, 10.5]}),
            "BBB": pd.DataFrame({"date": ["2020-01-02", "2020-01-03"], "open": [pd.NA, 11.5]}),
            "CCC": pd.DataFrame({"date": ["2020-01-02", "2020-01-03"], "open": [12.0, 12.5]}),
        }
    )

    out, audit = runner.attach_entry_audit(
        universe,
        stock_cache,
        20,
        {("AAA", "2020-01-02"): "pass", ("BBB", "2020-01-02"): "pass"},
    )
    all_row = audit.loc[audit["entry_status"].eq("all")].iloc[0]
    membership_row = audit.loc[audit["entry_status"].eq("pit_membership_missing_or_not_executable")].iloc[0]

    assert list(out["entry_status"]) == ["ok", "missing_trade_open_price", "pit_membership_missing_or_not_executable"]
    assert not bool(all_row["entry_parity_gate_pass"])
    assert int(all_row["entry_blocked_n"]) == 2
    assert int(all_row["pit_membership_missing_n"]) == 1
    assert int(membership_row["entry_blocked_n"]) == 1


def test_primary_selection_does_not_rank_by_raw_expected_r_first():
    runner = load_runner()
    rows = pd.DataFrame(
        [
            {
                "scope_id": "all_c0",
                "split": "train",
                "upper_barrier_pct": 0.10,
                "lower_barrier_pct": -0.06,
                "horizon_sessions": 20,
                "complete_executable_event_n": 1000,
                "upper_first_rate": 0.12,
                "lower_first_rate": 0.20,
                "true_survivor_killed_by_lower_rate": 0.10,
                "expected_r_multiple_proxy": 4.0,
                "time_penalized_expected_r_proxy": 1.0,
                "median_time_to_upper_sessions": 5,
            },
            {
                "scope_id": "all_c0",
                "split": "train",
                "upper_barrier_pct": 0.20,
                "lower_barrier_pct": -0.15,
                "horizon_sessions": 20,
                "complete_executable_event_n": 1000,
                "upper_first_rate": 0.18,
                "lower_first_rate": 0.22,
                "true_survivor_killed_by_lower_rate": 0.10,
                "expected_r_multiple_proxy": 1.0,
                "time_penalized_expected_r_proxy": 0.5,
                "median_time_to_upper_sessions": 6,
            },
        ]
    )
    rows["selection_eligible_flag"] = True

    selected, status = runner.select_primary_candidate(rows)

    assert status == "pass"
    assert selected["upper_barrier_pct"] == 0.20
    assert selected["expected_r_multiple_proxy"] == 1.0


def test_selection_eligibility_only_all_c0_train_and_family_diagnostic_only():
    runner = load_runner()
    thresholds = runner.load_yaml(EXPERIMENT_DIR / "configs" / "config_12a6_c0_local_survival_episode_audit.yaml")["thresholds"]
    base = {
        "upper_barrier_pct": 0.2,
        "lower_barrier_pct": -0.1,
        "horizon_sessions": 60,
        "event_n": 1000,
        "complete_executable_event_n": 1000,
        "upper_first_rate": 0.2,
        "lower_first_rate": 0.2,
        "true_survivor_killed_by_lower_rate": 0.1,
        "expected_r_multiple_proxy": 0.5,
        "median_time_to_upper_sessions": 20,
    }
    frame = pd.DataFrame(
        [
            {"scope_id": "all_c0", "split": "train", **base},
            {"scope_id": "all_c0", "split": "robustness", **base},
            {"scope_id": "primary_family_B4", "split": "train", **base},
        ]
    )

    out = runner.assign_selection_flags(frame, thresholds)

    assert out.loc[0, "selection_eligible_flag"]
    assert not out.loc[1, "selection_eligible_flag"]
    assert not out.loc[2, "selection_eligible_flag"]
    assert out.loc[2, "diagnostic_only_flag"]


def test_decision_uses_train_selected_threshold_and_robustness_cannot_reselect():
    runner = load_runner()
    thresholds = runner.load_yaml(EXPERIMENT_DIR / "configs" / "config_12a6_c0_local_survival_episode_audit.yaml")["thresholds"]
    base = {
        "scope_id": "all_c0",
        "lower_barrier_pct": -0.10,
        "horizon_sessions": 60,
        "event_n": 1000,
        "complete_executable_event_n": 1000,
        "lower_first_rate": 0.20,
        "true_survivor_killed_by_lower_rate": 0.10,
        "expected_r_multiple_proxy": 0.50,
        "time_penalized_expected_r_proxy": 0.15,
        "median_time_to_upper_sessions": 20,
        "selection_eligible_flag": False,
    }
    frontier = pd.DataFrame(
        [
            {**base, "split": "train", "upper_barrier_pct": 0.20, "upper_first_rate": 0.20, "selection_eligible_flag": True},
            {**base, "split": "train", "upper_barrier_pct": 0.30, "upper_first_rate": 0.19, "selection_eligible_flag": True},
            {**base, "split": "robustness", "upper_barrier_pct": 0.20, "upper_first_rate": 0.16},
            {**base, "split": "robustness", "upper_barrier_pct": 0.30, "upper_first_rate": 0.60},
        ]
    )

    decision, candidate = runner.evaluate_threshold_decision(
        frontier,
        pd.DataFrame(),
        pd.DataFrame([{"entry_parity_gate_pass": True}]),
        True,
        thresholds,
        [60],
    )

    assert float(candidate["upper_barrier_pct"]) == 0.20
    assert float(decision.iloc[0]["selected_upper_barrier_pct"]) == 0.20
    assert float(decision.iloc[0]["strong_upper_barrier_pct"]) == 0.30


def test_decision_state_mapping_for_input_no_candidate_and_hard_robustness_failure():
    runner = load_runner()
    thresholds = runner.load_yaml(EXPERIMENT_DIR / "configs" / "config_12a6_c0_local_survival_episode_audit.yaml")["thresholds"]
    base = {
        "scope_id": "all_c0",
        "upper_barrier_pct": 0.20,
        "lower_barrier_pct": -0.10,
        "horizon_sessions": 60,
        "event_n": 1000,
        "complete_executable_event_n": 1000,
        "upper_first_rate": 0.20,
        "lower_first_rate": 0.20,
        "true_survivor_killed_by_lower_rate": 0.10,
        "expected_r_multiple_proxy": 0.50,
        "time_penalized_expected_r_proxy": 0.15,
        "median_time_to_upper_sessions": 20,
    }
    frontier = pd.DataFrame(
        [
            {**base, "split": "train", "selection_eligible_flag": True},
            {**base, "split": "robustness", "upper_first_rate": 0.01, "selection_eligible_flag": False},
        ]
    )
    entry_pass = pd.DataFrame([{"entry_parity_gate_pass": True}])

    blocked, _ = runner.evaluate_threshold_decision(frontier, pd.DataFrame(), entry_pass, False, thresholds, [60])
    assert blocked.iloc[0]["decision_state"] == "12A6_blocked_input_or_pit_failure"

    no_candidate_frontier = frontier.assign(selection_eligible_flag=False)
    no_candidate, _ = runner.evaluate_threshold_decision(no_candidate_frontier, pd.DataFrame(), entry_pass, True, thresholds, [60])
    assert no_candidate.iloc[0]["decision_state"] == "12A6_no_stable_survival_threshold"

    hard, _ = runner.evaluate_threshold_decision(frontier, pd.DataFrame(), entry_pass, True, thresholds, [60])
    assert hard.iloc[0]["decision_state"] == "12A6_no_stable_survival_threshold"
    assert bool(hard.iloc[0]["hard_robustness_failure"])


def test_horizon_plateau_uses_longest_horizon_complete_fixed_cohort():
    runner = load_runner()
    universe = pd.DataFrame(
        {
            "event_ordinal": [0, 1],
            "event_split": ["train", "train"],
            "board_bucket": ["main_board", "main_board"],
            "market_regime_bucket": ["risk_on", "risk_on"],
            "primary_family_id": ["B1", "B1"],
            "entry_status": ["ok", "ok"],
            "max_complete_horizon_sessions": [20, 10],
        }
    )
    path = pd.DataFrame(
        [
            {
                "event_ordinal": event,
                "horizon_sessions": horizon,
                "upper_barrier_pct": 0.1,
                "lower_barrier_pct": -0.1,
                "first_hit_status": status,
                "same_bar_conflict_flag": False,
                "time_to_upper_sessions": 5 if status == "upper_first" else pd.NA,
                "time_to_lower_sessions": pd.NA,
                "upper_touch_possible_flag": status == "upper_first",
                "true_survivor_killed_by_lower_flag": False,
                "exit_return_proxy": 0.1 if status == "upper_first" else pd.NA,
                "r_multiple_proxy": 1.0 if status == "upper_first" else pd.NA,
                "mfe_h": 0.2 if status == "upper_first" else pd.NA,
                "mae_h": -0.02 if status == "upper_first" else pd.NA,
                "close_return_h": 0.05 if status == "upper_first" else pd.NA,
                "horizon_complete": complete,
                "entry_blocked": False,
                "pre_success_mae": -0.02 if status == "upper_first" else pd.NA,
            }
            for event, horizon, complete, status in [
                (0, 10, True, "upper_first"),
                (1, 10, True, "upper_first"),
                (0, 20, True, "upper_first"),
                (1, 20, False, "censored"),
            ]
        ]
    )
    thresholds = runner.load_yaml(EXPERIMENT_DIR / "configs" / "config_12a6_c0_local_survival_episode_audit.yaml")["thresholds"]
    frontier = runner.build_grid_frontier(path, universe, thresholds)
    curve = runner.build_time_to_hit_curve(frontier, path, universe, [10, 20], 0.03)
    row = curve.loc[
        curve["scope_id"].eq("all_c0")
        & curve["split"].eq("train")
        & curve["horizon_sessions"].eq(10)
    ].iloc[0]

    assert int(row["complete_executable_event_n"]) == 2
    assert int(row["plateau_cohort_event_n"]) == 1
    assert row["plateau_upper_first_rate"] == 1.0


def test_pre_success_mae_distribution_counts_survivors_killed_by_lower_barrier():
    runner = load_runner()
    universe = pd.DataFrame(
        {
            "event_ordinal": [0, 1],
            "event_split": ["train", "train"],
            "board_bucket": ["main_board", "main_board"],
            "market_regime_bucket": ["risk_on", "risk_on"],
            "primary_family_id": ["B1", "B1"],
        }
    )
    upper_touch = pd.DataFrame(
        [
            {
                "event_ordinal": 0,
                "upper_barrier_pct": 0.10,
                "horizon_sessions": 10,
                "entry_blocked": False,
                "horizon_complete": True,
                "upper_touch_possible_flag": True,
                "pre_success_mae": -0.02,
            },
            {
                "event_ordinal": 1,
                "upper_barrier_pct": 0.10,
                "horizon_sessions": 10,
                "entry_blocked": False,
                "horizon_complete": True,
                "upper_touch_possible_flag": True,
                "pre_success_mae": -0.06,
            },
        ]
    )
    path = pd.DataFrame(
        [
            {
                "event_ordinal": 0,
                "upper_barrier_pct": 0.10,
                "lower_barrier_pct": -0.05,
                "horizon_sessions": 10,
                "entry_blocked": False,
                "horizon_complete": True,
                "first_hit_status": "upper_first",
                "time_to_upper_sessions": 5,
                "time_to_lower_sessions": pd.NA,
                "r_multiple_proxy": 1.0,
                "exit_return_proxy": 0.10,
                "upper_touch_possible_flag": True,
                "true_survivor_killed_by_lower_flag": False,
            },
            {
                "event_ordinal": 1,
                "upper_barrier_pct": 0.10,
                "lower_barrier_pct": -0.05,
                "horizon_sessions": 10,
                "entry_blocked": False,
                "horizon_complete": True,
                "first_hit_status": "lower_first",
                "time_to_upper_sessions": pd.NA,
                "time_to_lower_sessions": 3,
                "r_multiple_proxy": -1.0,
                "exit_return_proxy": -0.05,
                "upper_touch_possible_flag": True,
                "true_survivor_killed_by_lower_flag": True,
            },
        ]
    )

    out = runner.build_pre_success_mae_distribution(upper_touch, path, universe, [-0.05])
    row = out.loc[out["scope_id"].eq("all_c0") & out["split"].eq("train")].iloc[0]

    assert int(row["upper_first_n"]) == 2
    assert row["pre_success_mae_p50"] == pytest.approx(-0.04)
    assert row["survivor_killed_by_lower_minus_05_rate"] == pytest.approx(0.5)


def test_enrichment_headline_uses_risk_on_baseline_not_all_c0():
    runner = load_runner()
    universe = pd.DataFrame(
        {
            "event_ordinal": [0, 1, 2],
            "event_split": ["train", "train", "train"],
            "market_regime_bucket": ["risk_on", "risk_on", "risk_off"],
            "overlap_06_low_to_high": [True, False, True],
            "overlap_06_pre120_to_high": [True, False, True],
            "overlap_11a2_pre120_to_high": [False, False, False],
            "overlap_12a4_risk_on_sanity_winner_120": [False, False, False],
        }
    )
    selected = pd.DataFrame(
        {
            "event_ordinal": [0, 1, 2],
            "complete_executable": [True, True, True],
            "upper_first_flag": [True, True, True],
        }
    )

    out = runner.build_enrichment_crosstab(universe, selected, "candidate")
    headline = out.loc[
        out["overlap_source"].eq("06_registry")
        & out["overlap_window"].eq("pre120_to_high")
        & out["scope_id"].eq("regime_risk_on")
        & out["split"].eq("train")
    ].iloc[0]
    all_c0 = out.loc[
        out["overlap_source"].eq("06_registry")
        & out["overlap_window"].eq("pre120_to_high")
        & out["scope_id"].eq("all_c0")
        & out["split"].eq("train")
    ].iloc[0]

    assert bool(headline["headline_enrichment_flag"])
    assert int(headline["baseline_event_n"]) == 2
    assert not bool(all_c0["headline_enrichment_flag"])
    assert int(all_c0["baseline_event_n"]) == 3


def test_late_stage_feature_policy_status_is_computed_from_required_feature_coverage():
    runner = load_runner()
    good = pd.DataFrame({col: [0.01] for col in runner.LATE_STAGE_NUMERIC_FEATURE_COLUMNS})
    missing = good.drop(columns=[runner.LATE_STAGE_NUMERIC_FEATURE_COLUMNS[0]])
    all_nan = pd.DataFrame({col: [pd.NA] for col in runner.LATE_STAGE_NUMERIC_FEATURE_COLUMNS})

    assert runner.late_stage_feature_policy_status(good) == "pass"
    assert runner.late_stage_feature_policy_status(missing) == "diagnostic_not_comparable"
    assert runner.late_stage_feature_policy_status(all_nan) == "diagnostic_not_comparable"


def test_required_outputs_exist_and_schema_after_full_run():
    required = {
        "input_artifact_audit.csv": {"artifact_id", "read_status", "schema_status", "sha256"},
        "c0_survival_event_universe.csv.gz": {
            "survival_event_id",
            "canonical_event_id",
            "source_scope_id",
            "trade_open_pit_membership_status",
            "entry_status",
        },
        "c0_forward_path_distribution.csv": {"scope_id", "split", "horizon_sessions", "mfe_p50", "mae_p50"},
        "c0_triple_barrier_grid_frontier.csv": {
            "scope_id",
            "split",
            "upper_barrier_pct",
            "lower_barrier_pct",
            "selection_eligible_flag",
            "diagnostic_only_flag",
            "time_penalized_expected_r_proxy",
        },
        "c0_pre_success_mae_distribution.csv": {"scope_id", "upper_barrier_pct", "survivor_killed_by_lower_minus_15_rate"},
        "c0_time_to_hit_curve.csv": {"plateau_cohort_event_n", "plateau_upper_first_rate", "horizon_plateau_flag"},
        "c0_threshold_candidate_decision.csv": {"decision_state", "selected_candidate_status", "selected_train_time_penalized_expected_r_proxy"},
        "c0_bigwinner_enrichment_crosstab.csv": {"registry_scope_id", "baseline_scope_id", "headline_enrichment_flag", "diagnostic_only_flag"},
        "c0_late_stage_failure_diagnostics.csv": {"late_stage_bucket", "late_stage_feature_policy_status"},
        "c0_entry_executability_audit.csv": {
            "entry_status",
            "pit_membership_missing_n",
            "pit_membership_file_missing_n",
            "pit_membership_not_executable_n",
            "entry_blocked_n",
            "entry_parity_gate_pass",
        },
        "c0_same_bar_conflict_audit.csv": {"same_bar_conflict_n", "conflict_counted_as"},
        "c0_overlap_density_audit.csv": {"same_instrument_prior_c0_10d_rate", "overlap_with_other_c0_survival_window_mean"},
    }
    for file_name, columns in required.items():
        path = TABLE_DIR / file_name
        assert path.exists(), file_name
        frame = pd.read_csv(path, nrows=5, low_memory=False)
        assert columns.issubset(frame.columns), file_name
    assert MANIFEST_PATH.exists()
    assert REPORT_PATH.exists()


def test_publishable_family_slices_exclude_b7_and_family_rows_are_diagnostic_only():
    frontier = table("c0_triple_barrier_grid_frontier")
    family_rows = frontier.loc[frontier["scope_id"].astype(str).str.startswith("primary_family_")]

    assert "primary_family_B7" not in set(frontier["scope_id"].astype(str))
    assert set(family_rows["scope_id"].unique()) == {
        "primary_family_B1",
        "primary_family_B2",
        "primary_family_B3",
        "primary_family_B4",
        "primary_family_B5",
        "primary_family_B6",
        "primary_family_B8",
    }
    assert not family_rows["selection_eligible_flag"].astype(bool).any()
    assert family_rows["diagnostic_only_flag"].astype(bool).all()


def test_publishable_enrichment_headline_rows_are_risk_on_scope():
    enrichment = table("c0_bigwinner_enrichment_crosstab")
    headline = enrichment.loc[enrichment["headline_enrichment_flag"].astype(bool)]

    assert not headline.empty
    assert set(headline["registry_scope_id"].astype(str)) == {"regime_risk_on"}
    assert set(headline["baseline_scope_id"].astype(str)) == {"regime_risk_on"}
    assert not headline["scope_id"].eq("all_c0").any()
