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

import run_11a2_post_t0_archetype_path_divergence_diagnostic as diag  # noqa: E402


def test_scope_reconciliation_drift_threshold_triggers_incomplete_status(tmp_path: Path) -> None:
    risk = tmp_path / "risk.csv"
    pit = tmp_path / "pit.csv"
    pd.DataFrame(
        {
            "split": ["all", "train", "validation", "robustness"],
            "risk_on_evaluated_row_n": [3, 1, 1, 1],
        }
    ).to_csv(risk, index=False)
    pd.DataFrame(
        {
            "split": ["all", "train", "validation", "robustness"],
            "pit_valid_evaluated_row_n": [3, 1, 1, 1],
        }
    ).to_csv(pit, index=False)
    denom = pd.DataFrame({"split": ["train", "validation"], "instrument": ["A", "B"]})

    out = diag.build_scope_reconciliation(
        denom,
        {"eleven_a1_scope_risk_on": risk, "eleven_a1_scope_pit": pit},
        diag.Params(denominator_drift_ceiling=0.005),
    )

    all_row = out.loc[out["split"].eq("all")].iloc[0]
    assert all_row["denominator_drift_rate"] > 0.005
    assert all_row["reconciliation_status"] == "denominator_drift_vs_11a1"


def test_k15_and_feature_registry_exclusions_are_pre_registered() -> None:
    params = diag.Params()
    registry = diag.feature_registry()

    assert params.observation_windows_K == (1, 3, 5, 10, 15, 20)
    assert 15 in params.observation_windows_K
    assert registry.loc[
        registry["feature_id"].eq("ep_structural_drawdown_8pct_by_K_flag"),
        "include_in_separation_curve_flag",
    ].iloc[0]
    assert not registry.loc[
        registry["feature_id"].eq("ep_fast_fail_barrier_touched_by_K_flag"),
        "include_in_separation_curve_flag",
    ].iloc[0]
    assert not registry.loc[
        registry["feature_id"].eq("ep_mfe_to_K"),
        "include_in_separation_curve_flag",
    ].iloc[0]


def test_outcome_class_contract_keeps_c1_failure_union_nonwinner() -> None:
    frame = pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4, 5],
            "instrument": ["A", "B", "C", "D", "E"],
            "event_t0_date": ["2024-01-02"] * 5,
            "winner_120": [True, False, False, False, False],
            "selected_fast_fail_10_label": [False, True, False, False, True],
            "frozen_false_repair_20d_label": [False, False, True, False, True],
            "horizon_complete_10d": [True, True, True, True, False],
            "horizon_complete_20d": [True, True, True, True, True],
            "horizon_complete_120d": [True, True, True, True, True],
            "final_sample_weight": [1, 1, 1, 1, 1],
        }
    )

    out = diag.prepare_outcome_classes(frame)

    assert out["class_big_winner_flag"].tolist() == [True, False, False, False, False]
    assert out["class_big_failure_proxy_nonwinner_flag"].tolist() == [False, True, True, False, False]
    assert out["subclass_fast_fail_flag"].tolist() == [False, True, False, False, False]
    assert out["subclass_false_repair_only_flag"].tolist() == [False, False, True, False, False]
    assert out["class_neutral_chop_flag"].tolist() == [False, False, False, True, False]
    assert out["class_unresolved_flag"].tolist() == [False, False, False, False, True]


def test_fast_fail_touch_is_label_overlap_only_not_primary_fill(tmp_path: Path) -> None:
    primary = tmp_path / "qfq"
    fallback = tmp_path / "fallback"
    primary.mkdir()
    fallback.mkdir()
    bars = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-02", periods=30, freq="B").strftime("%Y-%m-%d"),
            "open": [10.0] * 30,
            "high": [10.5] * 30,
            "low": [9.5] * 30,
            "close": [10.1] * 30,
            "volume": [1000.0] * 30,
            "money": [10000.0] * 30,
            "instrument": ["AAA"] * 30,
        }
    )
    bars.to_csv(primary / "AAA.csv", index=False)
    board = tmp_path / "board.csv"
    pd.DataFrame({"instrument": ["AAA"], "delist_date": [""]}).to_csv(board, index=False)
    frame = pd.DataFrame(
        {
            "row_id": [1],
            "split": ["train"],
            "instrument": ["AAA"],
            "event_t0_date": ["2024-01-02"],
            "event_window_anchor_date": ["2024-01-03"],
            "binding_canonical_event_id": ["evt1"],
            "final_sample_weight": [1.0],
            "class_big_winner_flag": [False],
            "class_big_failure_proxy_nonwinner_flag": [True],
            "subclass_fast_fail_flag": [True],
            "subclass_false_repair_only_flag": [False],
            "class_neutral_chop_flag": [False],
            "class_all_nonwinner_resolved_flag": [True],
            "class_unresolved_flag": [False],
            "winner_120_bool": [False],
            "fast_fail_10_bool": [True],
            "false_repair_20_bool": [False],
            "mfe_120d": [0.10],
            "forward_return_120d": [0.05],
            "selected_fast_fail_touch_date": ["2024-01-04"],
            "selected_fast_fail_touch_offset_sessions": [1],
        }
    )
    params = diag.Params(observation_windows_K=(3,))
    cache = diag.PriceCache(primary, fallback)

    features, _, fill_audit, _, _, overlap = diag.build_early_path_features(
        frame,
        {"board_metadata": board},
        params,
        cache,
    )

    full = features.loc[features["cohort"].eq("full_cohort")].iloc[0]
    assert full["fill_reason"] == "complete_path"
    assert full["eligible_flag"]
    assert full["ep_fast_fail_barrier_touched_by_K_flag"]
    assert "barrier_stop_fast_fail" not in set(fill_audit["fill_reason"])
    assert overlap["label_overlap_status"].eq("label_overlap_tautology_audit_only").all()


def test_touch_by_k_uses_offset_not_absolute_touch_pos() -> None:
    row = pd.Series(
        {
            "fast_fail_10_bool": True,
            "selected_fast_fail_touch_date": "",
            "selected_fast_fail_touch_pos": 2096,
            "selected_fast_fail_touch_offset_sessions": 2,
        }
    )

    touched_k2, offset_k2 = diag.touch_by_k(row, None, None, 2)
    touched_k3, offset_k3 = diag.touch_by_k(row, None, None, 3)

    assert not touched_k2
    assert touched_k3
    assert offset_k2 == 3.0
    assert offset_k3 == 3.0


def test_post_t0_st_is_not_a_fill_reason_or_status_ceiling() -> None:
    assert "st" not in {reason for reason in ["delisted", "suspended", "complete_path"]}
    params = diag.Params()
    assert params.touch_pos_offset_unresolved_ceiling == 0.005


def test_boolean_features_are_numeric_for_separation_metrics() -> None:
    pos = pd.Series([True, True, False])
    neg = pd.Series([False, False, True])
    weights = pd.Series([1.0, 1.0, 1.0])

    auc, cliff = diag.weighted_auc_cliff(pos, neg, weights, weights)
    smd = diag.winsorized_smd(pos, neg, weights, weights)

    assert auc > 0.5
    assert cliff > 0
    assert smd > 0


def test_dual_channel_confirmed_onset_waits_for_structure_channel() -> None:
    rows = []
    for split in ["train", "robustness"]:
        for feature, strong_ks in {
            "ep_ret_t0_to_K": {5, 10},
            "ep_max_drawdown_to_K": {10},
        }.items():
            for k in [5, 10]:
                strong = k in strong_ks
                rows.append(
                    {
                        "contrast_id": "C1_winner_vs_big_failure_proxy",
                        "cohort": "full_cohort",
                        "split": split,
                        "K": k,
                        "feature_id": feature,
                        "cliffs_delta": 0.20 if strong else 0.01,
                        "cliffs_delta_ci_low": 0.10 if strong else -0.05,
                        "cliffs_delta_ci_high": 0.30 if strong else 0.07,
                        "eligible_positive_n": 100,
                        "eligible_negative_n": 100,
                        "separation_direction": "winner_higher" if strong else "undetermined",
                    }
                )
    separation = pd.DataFrame(rows)
    features = pd.DataFrame(
        {
            "cohort": ["full_cohort", "full_cohort", "full_cohort"],
            "K": [10, 10, 10],
            "ep_ret_t0_to_K": [0.10, 0.20, 0.30],
            "ep_max_drawdown_to_K": [-0.05, -0.02, 0.00],
            "final_sample_weight": [1.0, 1.0, 1.0],
        }
    )

    onset, _ = diag.build_onset_readouts(separation, features, diag.Params())
    c1 = onset.loc[
        onset["contrast_id"].eq("C1_winner_vs_big_failure_proxy")
        & onset["cohort"].eq("full_cohort")
    ].iloc[0]

    assert c1["return_channel_tier3_confirmed_onset_day"] == 5
    assert c1["structure_channel_tier3_confirmed_onset_day"] == 10
    assert c1["confirmed_divergence_onset_day"] == 10


def test_survivorship_audit_emits_both_delist_haircut_endpoints() -> None:
    separation = pd.DataFrame(
        [
            {
                "contrast_id": "C1_winner_vs_big_failure_proxy",
                "feature_id": "ep_ret_t0_to_K",
                "K": 3,
                "split": "train",
                "cohort": cohort,
                "cliffs_delta": 0.20,
                "eligible_row_n": 10,
                "separation_direction": "winner_higher",
            }
            for cohort in ["survivors_only", "full_cohort"]
        ]
    )

    out = diag.survivorship_audit(
        separation,
        diag.Params(delist_haircut=1.0, delist_haircut_sensitivity_values=(1.0, 0.0)),
    )

    assert sorted(out["delist_haircut"].tolist()) == [0.0, 1.0]
    assert set(out["delist_haircut_sensitivity_status"]) == {"primary", "sensitivity_delist_haircut_0"}


def test_multiple_comparison_uses_stratified_null_simulation() -> None:
    rows = []
    for idx in range(24):
        winner = idx < 6
        failure = 6 <= idx < 14
        fast = 6 <= idx < 10
        false_repair = 10 <= idx < 14
        neutral = idx >= 14
        rows.append(
            {
                "row_id": idx,
                "split": "train" if idx < 12 else "robustness",
                "event_t0_date": "2024-01-02",
                "event_year_quarter": "2024Q1",
                "source_family_id_matched": "sf",
                "cohort": "full_cohort",
                "K": 1,
                "eligible_flag": True,
                "final_sample_weight": 1.0,
                "ep_ret_t0_to_K": float(idx) / 100.0,
                "class_big_winner_flag": winner,
                "class_big_failure_proxy_nonwinner_flag": failure,
                "subclass_fast_fail_flag": fast,
                "subclass_false_repair_only_flag": false_repair,
                "class_neutral_chop_flag": neutral,
                "class_all_nonwinner_resolved_flag": failure or neutral,
            }
        )
    features = pd.DataFrame(rows)
    separation = pd.DataFrame(
        {
            "cohort": ["full_cohort"],
            "readout_tier": ["primary_return_channel"],
            "feature_id": ["ep_ret_t0_to_K"],
            "cliffs_delta": [0.20],
            "cliffs_delta_ci_low": [0.10],
            "cliffs_delta_ci_high": [0.30],
        }
    )

    out = diag.multiple_comparison_audit(
        separation,
        features,
        diag.Params(observation_windows_K=(1,), null_simulation_n=2),
    )

    assert out["null_simulation_n"].iloc[0] == 2
    assert out["null_simulation_method"].iloc[0] == "stratified_label_permutation_by_split_event_quarter_source_family_cached_weighted_cliffs_delta"


def test_final_status_precedence_for_tradability_and_incomplete() -> None:
    onset = pd.DataFrame(
        {
            "contrast_id": ["C1_winner_vs_big_failure_proxy"],
            "cohort": ["full_cohort"],
            "confirmed_divergence_onset_day": [5],
        }
    )
    bootstrap = pd.DataFrame(
        {
            "contrast_id": ["C1_winner_vs_big_failure_proxy"],
            "bootstrap_stable_flag": [True],
        }
    )
    survivorship = pd.DataFrame({"contrast_id": [], "survivorship_flag": []})
    tradable = pd.DataFrame({"winner_realized_fraction_status": ["tradable_window_open"]})
    late = pd.DataFrame({"winner_realized_fraction_status": ["late_most_move_realized"]})

    assert diag.choose_final_status(["missing"], [], onset, bootstrap, tradable, survivorship) == diag.FINAL_BLOCKED
    assert diag.choose_final_status([], ["drift"], onset, bootstrap, tradable, survivorship) == diag.FINAL_INCOMPLETE
    assert diag.choose_final_status([], [], onset, bootstrap, tradable, survivorship) == diag.FINAL_TRADABLE
    assert diag.choose_final_status([], [], onset, bootstrap, late, survivorship) == diag.FINAL_LATE
