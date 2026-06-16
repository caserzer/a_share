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

import run_11a0_regime_pit_availability_audit as audit  # noqa: E402


def test_allowed_buckets_do_not_create_missing_regime() -> None:
    assert audit.normalize_bucket("risk_on") == "risk_on"
    assert audit.normalize_bucket("risk_off") == "risk_off"
    assert audit.normalize_bucket("transition") == "transition"
    assert audit.normalize_bucket("") == ""
    assert audit.normalize_bucket("missing") == ""
    assert audit.normalize_bucket("unknown") == ""


def test_analysis_event_regime_never_uses_10a_fallback() -> None:
    frame = pd.DataFrame(
        {
            "event_regime_bucket": ["", ""],
            "market_regime_bucket": ["risk_off", ""],
            "event_regime_bucket_09a": ["risk_on", ""],
            "event_regime_bucket_10a": ["risk_on", "risk_on"],
        }
    )
    result = audit.coalesce_valid_series(
        [
            frame["event_regime_bucket"],
            frame["market_regime_bucket"],
            frame["event_regime_bucket_09a"],
        ]
    )

    assert result.tolist() == ["risk_off", ""]


def test_daily_regime_series_mode_and_date_level_stability() -> None:
    panel = pd.DataFrame(
        {
            "date": [
                "2024-01-01",
                "2024-01-01",
                "2024-01-02",
                "2024-01-02",
                "2024-01-03",
                "2024-01-03",
                "2024-01-04",
                "2024-01-04",
                "2024-01-05",
                "2024-01-05",
                "2024-01-06",
                "2024-01-06",
            ],
            "market_regime_bucket": [
                "risk_on",
                "risk_on",
                "risk_on",
                "risk_off",
                "risk_on",
                "risk_on",
                "risk_off",
                "risk_off",
                "risk_off",
                "risk_off",
                "risk_off",
                "risk_off",
            ],
        }
    )

    daily = audit.build_daily_regime_series(panel, daily_conflict_rate_cap=0.51)

    assert daily.loc[daily["date"].eq("2024-01-02"), "daily_regime_bucket"].iloc[0] == "risk_off"
    assert daily.loc[daily["date"].eq("2024-01-02"), "daily_regime_conflict_rate"].iloc[0] == 0.5
    assert bool(daily.loc[daily["date"].eq("2024-01-01"), "date_flip_any_5d_flag"].iloc[0])
    assert daily.loc[daily["date"].eq("2024-01-01"), "regime_age_sessions_t0"].iloc[0] == 1
    assert daily.loc[daily["date"].eq("2024-01-04"), "regime_age_sessions_t0"].iloc[0] == 1


def test_event_weighted_metrics_are_diagnostic_not_gate_basis() -> None:
    dates = pd.date_range("2024-01-01", periods=30, freq="B").strftime("%Y-%m-%d").tolist()
    regimes = ["risk_on"] * 10 + ["risk_off"] * 20
    panel = pd.DataFrame(
        {
            "date": [date for date in dates for _ in range(2)],
            "market_regime_bucket": [regime for regime in regimes for _ in range(2)],
        }
    )
    daily = audit.build_daily_regime_series(panel)
    canonical = pd.DataFrame(
        [
            {
                "event_id": f"e{i}",
                "canonical_event_id": f"c{i}",
                "instrument": "SH600000",
                "event_t0_date": dates[0] if i < 20 else dates[15],
                "event_split": "train",
                "event_regime_bucket": "risk_on" if i < 20 else "risk_off",
                "market_regime_bucket": "risk_on" if i < 20 else "risk_off",
                "event_regime_gating": "ungated",
                "trade_open_date": dates[1],
                "event_t0_confirmation_time": "t0_close_next_open_executable",
            }
            for i in range(25)
        ]
    )
    scored, _, failures = audit.build_event_scored(canonical, pd.DataFrame(columns=["canonical_event_id"]), daily, audit.Thresholds())
    date_level = audit.summarize_date_level_stability(daily)
    event_weighted = audit.summarize_event_weighted_stability(scored)

    assert failures == []
    assert set(date_level["population_scope"]) == {"date_level_unweighted"}
    assert set(event_weighted["population_scope"]) == {"08_canonical_event_weighted"}
    assert "event_n" in event_weighted.columns
    assert "date_n" in date_level.columns


def test_parse_10a_key_and_coverage_flags_slice_power() -> None:
    event_scored = pd.DataFrame(
        {
            "canonical_event_id": ["c1", "c2"],
            "instrument": ["SH600000", "SH600001"],
            "event_t0_date": ["2024-01-01", "2024-01-02"],
            "event_split": ["train", "validation"],
            "analysis_event_regime_bucket": ["risk_on", "risk_on"],
        }
    )
    bindings = pd.DataFrame(
        {
            "population_id": ["10A__same_instrument_cooldown_10d", "10A__same_instrument_cooldown_10d"],
            "rule_arm_id": ["same_instrument_cooldown_10d", "same_instrument_cooldown_10d"],
            "denominator_id": ["post_dedup_risk_on_r_core", "post_dedup_risk_on_r_core"],
            "admission_status": ["admitted", "admitted"],
            "readout_only_flag": [False, False],
            "input_event_key": ["a|b|d|c1", "a|b|d|c2"],
            "feature_matrix_join_key": ["a|b|d|c1", "a|b|d|c2"],
            "instrument": ["SH600000", "SH600001"],
            "event_t0_date": ["2024-01-01", "2024-01-02"],
            "split": ["train", "validation"],
            "source_family_id": ["f", "f"],
            "event_regime_bucket": ["risk_on", "risk_on"],
        }
    )
    config = {
        "scope": {
            "ten_a_population_id": "10A__same_instrument_cooldown_10d",
            "ten_a_rule_arm_id": "same_instrument_cooldown_10d",
            "ten_a_denominator_id": "post_dedup_risk_on_r_core",
            "ten_a_admission_status": "admitted",
            "ten_a_readout_only_flag": False,
            "downstream_required_regimes": ["risk_on"],
        }
    }
    thresholds = audit.Thresholds(ten_a_event_n_min=1, ten_a_split_event_n_min=0)

    coverage, power, flag = audit.build_10a_coverage(bindings, event_scored, config, thresholds)

    assert coverage["ten_a_key_parse_success_rate"].iloc[0] == 1.0
    assert coverage["ten_a_to_08_match_rate"].iloc[0] == 1.0
    assert bool(power.loc[power["analysis_event_regime_bucket"].eq("risk_on"), "ten_a_slice_power_flag"].iloc[0])
    assert flag is True


def test_downstream_usage_downgrades_matched_axis_when_10a_power_fails() -> None:
    usage = audit.build_downstream_usage_decision(audit.FINAL_STABLE, ten_a_slice_power_flag=False)
    matched = usage.loc[usage["usage_target"].eq("11A1_matched_base_axis")].iloc[0]

    assert bool(matched["allowed_flag"]) is False
    assert matched["usage_scope"] == "diagnostic_only"
    assert matched["stability_gate_basis"] == "date_level_unweighted"


def test_final_status_precedence() -> None:
    assert audit.choose_final_status(["missing"], [], [], []) == audit.FINAL_BLOCKED
    assert audit.choose_final_status([], ["pit"], [], []) == audit.FINAL_INCOMPLETE
    assert audit.choose_final_status([], [], ["power"], []) == audit.FINAL_INCOMPLETE
    assert audit.choose_final_status([], [], [], ["flip"]) == audit.FINAL_UNSTABLE
    assert audit.choose_final_status([], [], [], []) == audit.FINAL_STABLE


def test_event_regime_gating_readout_skips_missing_optional_instances() -> None:
    scored = pd.DataFrame(
        {
            "event_split": ["train", "train", "validation"],
            "analysis_event_regime_bucket": ["risk_on", "risk_on", "risk_off"],
            "event_regime_gating": ["ungated", "event_regime_gated", "ungated"],
        }
    )

    readout = audit.build_event_regime_gating_readout(scored, None)

    all_row = readout.loc[readout["view"].eq("all")].iloc[0]
    assert all_row["gated_event_count"] == 1
    assert all_row["event_instance_reconciliation_status"] == "event_instance_gating_reconciliation_skipped"
