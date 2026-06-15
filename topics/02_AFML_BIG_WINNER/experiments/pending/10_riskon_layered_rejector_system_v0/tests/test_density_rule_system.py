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

import run_density_rule_system as density  # noqa: E402


def test_scope_treatment_maps_denominator_and_split_aliases() -> None:
    binding = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "t",
                "canonical_event_id": "c1",
                "denominator_id": density.R_CORE_INPUT_DENOM,
                "event_split": "train",
                "event_regime_bucket": "risk_on",
                "source_pool_id": density.R_CORE_SCOPE,
            },
            {
                "sample_id": "s2",
                "selected_target_id": "t",
                "canonical_event_id": "c2",
                "denominator_id": density.E1_READONLY_INPUT_DENOM,
                "event_split": "train",
                "event_regime_bucket": "risk_off",
                "source_pool_id": density.E1_SCOPE,
            },
        ]
    )

    scoped = density.scope_treatment(binding)
    exclusion = density.build_input_scope_exclusion_audit(scoped)

    assert scoped.loc[0, "input_denominator_id"] == density.R_CORE_INPUT_DENOM
    assert scoped.loc[0, "denominator_id"] == density.R_CORE_INPUT_DENOM
    assert scoped.loc[0, "output_denominator_id"] == density.R_CORE_OUTPUT_DENOM
    assert scoped.loc[0, "split"] == "train"
    assert exclusion.loc[0, "exclusion_reason"] == "excluded_riskoff_e1_readonly"
    assert not bool(exclusion.loc[0, "feature_matrix_join_attempted_flag"])


def test_feature_join_rejects_event_split_mismatch() -> None:
    base = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "t",
                "input_denominator_id": density.R_CORE_INPUT_DENOM,
                "canonical_event_id": "c1",
                "split": "train",
            }
        ]
    )
    feature = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "t",
                "denominator_id": density.R_CORE_INPUT_DENOM,
                "canonical_event_id": "c1",
                "event_split": "validation",
                "close_to_ema60": 1.0,
            }
        ]
    )

    _, failures = density.validate_and_join_features(base, feature, ["close_to_ema60"])

    assert failures == ["feature_matrix_event_split_mismatch:1"]


def test_same_instrument_cooldown_suppresses_with_representative_binding() -> None:
    base = pd.DataFrame(
        [
            {
                "split": "train",
                "denominator_id": density.R_CORE_OUTPUT_DENOM,
                "instrument": "000001",
                "raw_event_status": "executable",
                "event_window_anchor_pos": 10,
                "event_t0_date": "2025-01-01",
                "sample_id": "s1",
                "input_event_key": "s1|t|d|c1",
            },
            {
                "split": "train",
                "denominator_id": density.R_CORE_OUTPUT_DENOM,
                "instrument": "000001",
                "raw_event_status": "executable",
                "event_window_anchor_pos": 15,
                "event_t0_date": "2025-01-08",
                "sample_id": "s2",
                "input_event_key": "s2|t|d|c2",
            },
            {
                "split": "train",
                "denominator_id": density.R_CORE_OUTPUT_DENOM,
                "instrument": "000001",
                "raw_event_status": "non_executable_audit_only",
                "event_window_anchor_pos": 16,
                "event_t0_date": "2025-01-09",
                "sample_id": "s3",
                "input_event_key": "s3|t|d|c3",
            },
        ]
    )
    arm = density.RuleArm(
        rule_arm_id="same_instrument_cooldown_10d",
        rule_arm_type="same_instrument_cooldown",
        window_sessions=10,
        cap=1,
        required_field=None,
    )

    out = density.materialize_arm(base, arm, "materialized")

    assert out.loc[0, "admission_status"] == "admitted"
    assert out.loc[1, "admission_status"] == "suppressed_by_density_rule"
    assert out.loc[1, "admitted_event_id"] == "s1|t|d|c1"
    assert out.loc[1, "suppressed_by_sample_id"] == "s1"
    assert out.loc[2, "admission_status"] == "non_executable_audit_only"
    assert out.loc[2, "suppression_reason"] == "non_executable_next_open"


def test_e1_rollup_and_feature_contract_status() -> None:
    assert (
        density.aggregate_e1_status(
            pd.Series(
                [
                    "episode_level_proxy_from_08_membership",
                    "no_episode_membership_for_event",
                ]
            )
        )
        == "mixed_non_blocking"
    )
    assert (
        density.aggregate_e1_status(
            pd.Series(["episode_membership_proxy_input_blocked", "no_episode_membership_for_event"])
        )
        == "episode_membership_proxy_input_blocked"
    )

    contract = pd.DataFrame(
        [
            {"feature_id": "close_to_ema60", "allowed_for_09C_flag": True},
            {"feature_id": "ema60_slope_20d", "allowed_for_09C_flag": True},
        ]
    )
    bindings = pd.DataFrame({"close_to_ema60": [1.0], "ema60_slope_20d": [0.1]})

    assert (
        density.feature_contract_status(
            contract, ["close_to_ema60", "ema60_slope_20d"], bindings
        )
        == "pass"
    )
    assert (
        density.feature_contract_status(contract, ["close_to_ema60", "missing_feature"], bindings)
        == "input_blocked"
    )
