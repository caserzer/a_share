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

import run_11b_archetype_protected_retention_readout as ret  # noqa: E402


def _config() -> dict:
    return {
        "scope": {
            "reference_slice": {
                "model_id": "regularized_logistic_false_repair_20d_l2_v1",
                "ablation_id": "full",
                "capacity_id": "keep_9000",
                "threshold_id": "keep_9000",
                "population_id": "10A__same_instrument_cooldown_10d",
                "denominator_id": "post_dedup_risk_on_r_core",
            }
        },
        "parameters": ret.CONFIG_PARAM_DEFAULTS.copy(),
    }


def _base_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sample_id": ["s1", "s2", "s3", "s4"],
            "selected_target_id": ["t"] * 4,
            "denominator_id": ["d"] * 4,
            "input_event_key": ["e1", "e2", "e3", "e4"],
            "instrument": ["A", "A", "B", "C"],
            "event_t0_date": ["2024-01-02"] * 4,
            "split": ["train", "train", "train", "train"],
            "binding_canonical_event_id": ["c1", "c2", "c3", "c4"],
            "winner_120": [True, True, False, False],
            "horizon_complete_120d": [True, False, True, True],
            "final_sample_weight": [1.0, 1.0, 1.0, 1.0],
        }
    )


def test_slice_mode_defaults_to_keep_9000_reference_when_10c_manifest_blocked() -> None:
    manifest = {
        "selected_capacity_id": None,
        "selected_threshold_id": None,
        "selected_cascade_status": "blocked",
    }

    out = ret.select_rejector_slice_mode(manifest, _config())

    assert out["rejector_slice_mode"] == "keep_9000_reference_slice"
    assert out["capacity_id"] == "keep_9000"
    assert out["threshold_id"] == "keep_9000"


def test_slice_mode_uses_selected_gate_only_when_manifest_supported() -> None:
    manifest = {
        "selected_model_id": "m",
        "selected_ablation_id": "a",
        "selected_capacity_id": "cap",
        "selected_threshold_id": "thr",
        "selected_population_id": "pop",
        "selected_denominator_id": "den",
        "selected_cascade_status": "supported",
    }

    out = ret.select_rejector_slice_mode(manifest, _config())

    assert out["rejector_slice_mode"] == "selected_gate"
    assert out["capacity_id"] == "cap"
    assert out["threshold_id"] == "thr"


def test_filter_rejector_slice_requires_full_slice_field_group() -> None:
    scores = pd.DataFrame(
        {
            "model_id": ["m", "m"],
            "ablation_id": ["full", "full"],
            "capacity_id": ["keep_9000", "keep_8000"],
            "threshold_id": ["keep_9000", "keep_8000"],
            "population_id": ["pop", "pop"],
            "denominator_id": ["den", "den"],
            "sample_id": ["s1", "s2"],
            "selected_target_id": ["t", "t"],
            "input_event_key": ["e1", "e2"],
        }
    )
    spec = {
        "rejector_slice_mode": "keep_9000_reference_slice",
        "model_id": "m",
        "ablation_id": "full",
        "capacity_id": "keep_9000",
        "threshold_id": "keep_9000",
        "population_id": "pop",
        "denominator_id": "den",
    }

    out = ret.filter_rejector_slice(scores, spec)

    assert len(out) == 1
    assert out.iloc[0]["sample_id"] == "s1"


def test_reject_join_uses_composite_key_not_instrument_date() -> None:
    frame = pd.DataFrame(
        {
            "sample_id": ["s1", "s2"],
            "selected_target_id": ["t", "t"],
            "denominator_id": ["d", "d"],
            "input_event_key": ["event_a", "event_b"],
            "instrument": ["AAA", "AAA"],
            "event_t0_date": ["2024-01-02", "2024-01-02"],
            "split": ["train", "train"],
        }
    )
    reject = pd.DataFrame(
        {
            "sample_id": ["s1", "s2"],
            "selected_target_id": ["t", "t"],
            "denominator_id": ["d", "d"],
            "input_event_key": ["event_a", "event_b"],
            "instrument": ["AAA", "AAA"],
            "event_t0_date": ["2024-01-02", "2024-01-02"],
            "split": ["train", "train"],
            "candidate_rejected_flag": [True, False],
        }
    )

    out, mismatch = ret.attach_reject_decision(frame, reject)

    assert ret.REJECT_JOIN_KEY == ["sample_id", "selected_target_id", "denominator_id", "input_event_key"]
    assert "instrument" not in ret.REJECT_JOIN_KEY
    assert "event_t0_date" not in ret.REJECT_JOIN_KEY
    assert out["rejected_flag"].tolist() == [True, False]
    assert out["retained_flag"].tolist() == [False, True]
    assert sum(mismatch.values()) == 0


def test_reject_decision_fallback_reconstructs_from_rank_and_reject_fraction() -> None:
    scores = pd.DataFrame(
        {
            "split": ["train"] * 5,
            "candidate_rank": [1, 2, 3, 4, 5],
            "reject_fraction": [0.4] * 5,
        }
    )

    out, derivation, hit_rate = ret.materialize_reject_decision(scores)

    assert derivation == "reject_flag_reconstructed_from_rank_reject_fraction"
    assert hit_rate == 1.0
    assert out["reject_decision_flag"].tolist() == [True, True, False, False, False]
    assert out["reject_flag_reconstructed_from_threshold"].all()


def test_unresolved_class_is_counted_but_excluded_from_retention_ratio() -> None:
    frame = _base_frame()
    reject = frame[ret.REJECT_JOIN_KEY + ["instrument", "event_t0_date", "split"]].copy()
    reject["candidate_rejected_flag"] = [False, True, False, True]
    joined, _ = ret.attach_reject_decision(frame, reject)
    joined = ret.add_subgroup_flags(joined)

    winner = ret.retention_for_mask(joined, joined["winner_120_protected_flag"])
    unresolved = ret.retention_for_mask(joined, joined["class_unresolved_flag"])

    assert joined["class_unresolved_flag"].sum() == 1
    assert winner["eligible_n"] == 1
    assert winner["retention_rate"] == 1.0
    assert unresolved["eligible_n"] == 0
    assert unresolved["unresolved_excluded_n"] == 1


def test_missing_winner_label_is_not_silently_treated_as_nonwinner() -> None:
    frame = pd.DataFrame(
        {
            "instrument": ["A"],
            "horizon_complete_120d": [True],
            "final_sample_weight": [1.0],
        }
    )

    out = ret.add_subgroup_flags(frame)

    assert not out["winner_120_protected_flag"].iloc[0]
    assert not out["nonwinner_reference_flag"].iloc[0]
    assert not out["winner_120_label_available_flag"].iloc[0]


def test_split_gate_power_floor_and_validation_guard() -> None:
    params = ret.Params()
    train_low_power = pd.Series(
        {
            "split": "train",
            "winner_n": 59,
            "unique_winner_instrument_n": 40,
            "relative_retention_ci_low_p05": 0.95,
            "relative_retention_ci_high_p95": 1.05,
        }
    )
    train_supported = pd.Series(
        {
            "split": "train",
            "winner_n": 60,
            "unique_winner_instrument_n": 30,
            "relative_retention_ci_low_p05": 0.91,
            "relative_retention_ci_high_p95": 1.03,
        }
    )
    validation_low_power = pd.Series(
        {
            "split": "validation",
            "winner_n": 16,
            "nonwinner_n": 800,
            "unique_winner_instrument_n": 15,
            "unique_nonwinner_instrument_n": 300,
            "relative_retention_ci_low_p05": 0.10,
            "relative_retention_ci_high_p95": 0.20,
        }
    )

    assert ret.split_retention_status(train_low_power, params) == "retention_underpowered"
    assert ret.split_retention_status(train_supported, params) == "non_discriminatory"
    assert ret.split_retention_status(validation_low_power, params) == "validation_low_power"


def test_overall_gate_precedence() -> None:
    assert ret.overall_gate({"train": "retention_underpowered", "robustness": "retention_underpowered"}) == "inconclusive_underpowered"
    assert ret.overall_gate({"train": "non_discriminatory", "robustness": "retention_underpowered"}) == "inconclusive_mixed_power"
    assert ret.overall_gate({"train": "ambiguous", "robustness": "retention_underpowered"}) == "ambiguous"
    assert ret.overall_gate({"train": "discriminatory", "robustness": "non_discriminatory"}) == "discriminatory"


def test_bootstrap_retention_outputs_primary_probabilities() -> None:
    rows = []
    for i in range(80):
        rows.append(
            {
                "sample_id": f"w{i}",
                "selected_target_id": "t",
                "denominator_id": "d",
                "input_event_key": f"ew{i}",
                "instrument": f"I{i % 20}",
                "event_t0_date": "2024-01-02",
                "split": "train",
                "binding_canonical_event_id": f"cw{i}",
                "winner_120": True,
                "horizon_complete_120d": True,
                "final_sample_weight": 1.0,
                "reject_decision_available_flag": True,
                "retained_flag": i % 10 != 0,
                "rejected_flag": i % 10 == 0,
            }
        )
    for i in range(160):
        rows.append(
            {
                "sample_id": f"n{i}",
                "selected_target_id": "t",
                "denominator_id": "d",
                "input_event_key": f"en{i}",
                "instrument": f"J{i % 40}",
                "event_t0_date": "2024-01-02",
                "split": "train",
                "binding_canonical_event_id": f"cn{i}",
                "winner_120": False,
                "horizon_complete_120d": True,
                "final_sample_weight": 1.0,
                "reject_decision_available_flag": True,
                "retained_flag": i % 5 != 0,
                "rejected_flag": i % 5 == 0,
            }
        )
    frame = ret.add_subgroup_flags(pd.DataFrame(rows))

    summary, raw = ret.bootstrap_retention(frame, ret.Params(bootstrap_n=25, bootstrap_seed=1))

    train_instrument = summary.loc[summary["split"].eq("train") & summary["block_level"].eq("instrument")].iloc[0]
    assert len(raw) == 100
    assert 0.0 <= train_instrument["prob_relative_retention_lt_floor"] <= 1.0
    assert 0.0 <= train_instrument["prob_relative_retention_ge_1"] <= 1.0


def test_config_contract_requires_all_preregistered_defaults() -> None:
    audit = ret.validate_config_contract(_config())

    assert audit["present_flag"].all()
    assert audit.loc[audit["config_key"].eq("relative_retention_floor"), "configured_value"].iloc[0] == 0.90
    assert audit["config_contract_status"].eq("ok").all()


def test_multiple_comparison_actual_significant_cells_use_ci_flag() -> None:
    frame = pd.DataFrame(
        {
            "split": ["train", "train", "robustness", "robustness"],
            "instrument": ["A", "B", "C", "D"],
            "horizon_complete_120d_bool": [True] * 4,
            "reject_decision_available_flag": [True] * 4,
            "retained_flag": [True, False, True, False],
            "winner_shakeout_seed_flag": [True, False, True, False],
            "winner_volatile_chop_seed_flag": [False] * 4,
            "winner_gap_event_seed_flag": [False] * 4,
            "nonwinner_reference_flag": [False, True, False, True],
            "class_unresolved_flag": [False] * 4,
            "final_sample_weight": [1.0] * 4,
        }
    )
    seed_readout = pd.DataFrame(
        {
            "split": ["train", "robustness"],
            "subgroup_status": ["ok", "ok"],
            "ci_below_floor_flag": [True, False],
        }
    )

    audit = ret.build_subgroup_multiple_comparison_audit(
        frame,
        seed_readout,
        ret.Params(multiple_comparison_null_n=5, multiple_comparison_null_seed=1),
    )

    assert audit["significant_cells_n"].iloc[0] == 1
