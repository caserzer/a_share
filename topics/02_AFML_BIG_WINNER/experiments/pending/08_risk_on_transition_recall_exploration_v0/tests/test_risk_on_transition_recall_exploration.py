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

import pipeline  # noqa: E402
import run_risk_on_r_series_density_compression_patch as rseries_patch  # noqa: E402
import run_density_fast_fail_audit as density_audit  # noqa: E402


def test_e1_only_replay_uses_triggered_channel_membership() -> None:
    canonical = pd.DataFrame(
        [
            {
                "event_id": "a",
                "instrument": "000001.SZ",
                "event_t0_date": "2020-01-01",
                "triggered_channels": "E1_early_ema60_repair;E2_money_vwap_repair_confirmation",
                "market_regime_bucket": "risk_on",
            },
            {
                "event_id": "b",
                "instrument": "000001.SZ",
                "event_t0_date": "2020-01-02",
                "triggered_channels": "E6_continuation_discriminator",
                "market_regime_bucket": "risk_on",
            },
        ]
    )
    instances = pd.DataFrame()

    e1 = pipeline.rebuild_e1_only_from_07(canonical, instances)

    assert e1["event_id"].tolist() == ["a"]
    assert e1.iloc[0]["family_id"] == pipeline.CHANNEL_E1


def test_density_audit_uses_execution_anchor_for_executable_rows() -> None:
    events = pd.DataFrame(
        [
            {
                "event_id": "a",
                "event_t0_pos": 10,
                "event_t0_date": "2020-01-10",
                "trade_open_pos": 11,
                "trade_open_date": "2020-01-13",
                "non_executable_next_open": False,
            },
            {
                "event_id": "b",
                "event_t0_pos": 20,
                "event_t0_date": "2020-01-24",
                "trade_open_pos": pd.NA,
                "trade_open_date": pd.NA,
                "non_executable_next_open": True,
            },
        ]
    )

    out = density_audit.with_event_window_anchor(events)

    assert out.loc[0, "event_window_anchor_pos"] == 11
    assert out.loc[0, "event_window_anchor_status"] == "next_open_execution_anchor"
    assert out.loc[1, "event_window_anchor_pos"] == 20
    assert out.loc[1, "event_window_anchor_status"] == "non_executable_t0_fallback"


def test_density_audit_rolling_count_is_same_instrument_only() -> None:
    events = pd.DataFrame(
        [
            {"instrument": "A", "event_key": "a1", "event_window_anchor_pos": 1},
            {"instrument": "A", "event_key": "a2", "event_window_anchor_pos": 5},
            {"instrument": "B", "event_key": "b1", "event_window_anchor_pos": 3},
        ]
    )

    counts = density_audit.rolling_window_counts(events, 10)

    assert counts.tolist() == [2, 1, 1]


def test_density_audit_uniqueness_is_same_instrument_only() -> None:
    events = pd.DataFrame(
        [
            {"instrument": "A", "event_key": "a1", "event_window_anchor_pos": 1},
            {"instrument": "A", "event_key": "a2", "event_window_anchor_pos": 5},
            {"instrument": "B", "event_key": "b1", "event_window_anchor_pos": 1},
        ]
    )

    uniqueness = density_audit.event_uniqueness(events, horizon=10)

    assert round(float(uniqueness.iloc[0]), 4) == round((4 + 7 * 0.5) / 11, 4)
    assert float(uniqueness.iloc[2]) == 1.0


def test_density_audit_selected_union_uses_selected_t4_t7_variants() -> None:
    canonical_08 = pd.DataFrame(
        [
            {
                "event_id": "t4",
                "triggered_family_variants": "T4_entropy_compression_then_directional_expansion__event_regime_gated",
                "recommended_union_included": True,
            },
            {
                "event_id": "broad",
                "triggered_family_variants": "R6_market_breadth_thrust__ungated",
                "recommended_union_included": True,
            },
            {
                "event_id": "t7",
                "triggered_family_variants": "T7_board_relative_strength_break__event_regime_gated",
                "recommended_union_included": False,
            },
        ]
    )
    spec = next(
        s
        for s in density_audit.build_scope_specs()
        if s.candidate_scope_id == "08_selected_T4_T7_union"
    )

    selected = density_audit.select_scope_events(spec, pd.DataFrame(), canonical_08)

    assert selected["event_id"].tolist() == ["t4", "t7"]


def test_density_audit_r_core_union_deduplicates_instrument_anchor(tmp_path: Path) -> None:
    spec = next(
        s
        for s in density_audit.build_scope_specs()
        if s.candidate_scope_id == "08_R_core_event_regime_gated"
    )
    events = pd.DataFrame(
        [
            {
                "event_id": "r1",
                "canonical_event_id": "r1",
                "instrument": "A",
                "event_t0_pos": 9,
                "trade_open_pos": 10,
                "event_t0_date": "2020-01-09",
                "trade_open_date": "2020-01-10",
                "non_executable_next_open": False,
            },
            {
                "event_id": "r2",
                "canonical_event_id": "r2",
                "instrument": "A",
                "event_t0_pos": 9,
                "trade_open_pos": 10,
                "event_t0_date": "2020-01-09",
                "trade_open_date": "2020-01-10",
                "non_executable_next_open": False,
            },
            {
                "event_id": "r3",
                "canonical_event_id": "r3",
                "instrument": "A",
                "event_t0_pos": 19,
                "trade_open_pos": 20,
                "event_t0_date": "2020-01-19",
                "trade_open_date": "2020-01-20",
                "non_executable_next_open": False,
            },
        ]
    )

    out = density_audit.normalise_scope_events(events, spec, source_path=tmp_path / "events.csv")

    assert len(out) == 2
    assert out[["instrument", "event_window_anchor_pos"]].drop_duplicates().shape[0] == 2


def test_density_audit_input_audit_flags_schema_incompatible(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "events.csv"
    pd.DataFrame({"event_id": ["a"]}).to_csv(source, index=False)
    monkeypatch.setattr(density_audit, "REQUIRED_INPUTS", {"bad_events": source})
    monkeypatch.setattr(density_audit, "OPTIONAL_INPUTS", {})
    monkeypatch.setattr(
        density_audit,
        "REQUIRED_INPUT_COLUMNS",
        {"bad_events": ["event_id", "instrument"]},
    )

    frame, failures = density_audit.input_audit()

    assert frame.iloc[0]["status"] == "schema_incompatible_required_input"
    assert frame.iloc[0]["missing_required_columns"] == "instrument"
    assert failures == ["schema_incompatible_required_input:bad_events:missing_columns=instrument"]


def test_density_audit_pre_replay_capture_rows_use_partial_replay_id() -> None:
    spec = next(
        s for s in density_audit.build_scope_specs() if s.candidate_scope_id == "07_E1_only"
    )
    capture = pd.DataFrame(
        [
            {
                "candidate_scope_id": "07_e1_only",
                "window": density_audit.BEFORE_FIRST_50,
                "target_episode_id": "ep1",
                "episode_split": "train",
                "market_regime_bucket": "risk_on",
                "any_event_denominator_included": True,
                "bridge_positive_denominator_included": True,
                "any_event_captured": True,
                "bridge_positive_captured": False,
            }
        ]
    )

    out = density_audit.retention_rows_from_capture(capture, {"07_E1_only": spec})

    assert set(out["retention_replay_id"]) == {"pre_replay_capture_only"}
    assert not out["replay_uses_future_label"].any()
    assert out["post_replay_any_recall"].isna().all()


def test_incremental_recall_uses_same_denominator_percentage_points() -> None:
    baseline = pd.DataFrame(
        [
            {
                "target_episode_id": "ep1",
                "episode_split": "train",
                "market_regime_bucket": "risk_on",
                "window": "before_first_50pct",
                "any_event_captured": True,
                "bridge_positive_denominator_included": True,
                "bridge_positive_captured": False,
            },
            {
                "target_episode_id": "ep2",
                "episode_split": "train",
                "market_regime_bucket": "risk_on",
                "window": "before_first_50pct",
                "any_event_captured": False,
                "bridge_positive_denominator_included": True,
                "bridge_positive_captured": False,
            },
        ]
    )
    candidate = baseline.copy()
    candidate.loc[candidate["target_episode_id"] == "ep2", "any_event_captured"] = True
    capture_map = {"candidate": candidate}
    meta = {
        "candidate": pipeline.scope_metadata(
            "candidate", pipeline.FAMILY_VARIANT_SCOPE, "R1", "ungated", "runnable_existing_data", "relative_strength_cluster"
        )
    }

    out = pipeline.build_incremental_recall(capture_map, meta, baseline, baseline)
    row = out.loc[
        (out["episode_split"] == "train")
        & (out["market_regime_bucket"] == "risk_on")
        & (out["window"] == "before_first_50pct")
    ].iloc[0]

    assert row["denominator_episodes"] == 2
    assert row["incremental_captures_over_e1"] == 1
    assert row["incremental_recall_over_e1"] == 0.5


def test_gated_density_reports_full_and_eligible_denominators() -> None:
    events = pd.DataFrame(
        [
            {
                "event_id": "e1",
                "instrument": "000001.SZ",
                "event_t0_date": "2020-01-01",
            },
            {
                "event_id": "e2",
                "instrument": "000002.SZ",
                "event_t0_date": "2020-01-01",
            },
        ]
    )
    denominator = pd.DataFrame(
        [{"evaluated_instrument_days": 2520, "universe_years_252": 10.0}]
    )
    panel = pd.DataFrame(
        {
            "market_regime_bucket": ["risk_on"] * 252 + ["risk_off"] * 252,
        }
    )
    meta = {
        "fam__event_regime_gated": pipeline.scope_metadata(
            "fam__event_regime_gated",
            pipeline.FAMILY_VARIANT_SCOPE,
            "fam",
            "event_regime_gated",
            "runnable_existing_data",
            "cluster",
        )
    }

    density, denom = pipeline.build_density_tables(
        {"fam__event_regime_gated": events},
        meta,
        denominator,
        panel,
        e1_events=pd.DataFrame(
            [
                {
                    "event_id": "base",
                    "instrument": "000001.SZ",
                    "event_t0_date": "2020-01-01",
                    "event_regime_bucket": "risk_on",
                }
            ]
        ),
    )
    row = density.iloc[0]

    assert row["density_full_denominator"] == 0.2
    assert row["density_eligible_gated_denominator"] == 2.0
    assert row["density_vs_same_gated_denominator"] == 2.0
    assert denom.iloc[0]["headline_density_uses"] == "density_full_denominator"


def test_selection_keeps_one_variant_per_family() -> None:
    incremental = pd.DataFrame(
        [
            {
                "candidate_scope_id": "fam__ungated",
                "candidate_scope_type": pipeline.FAMILY_VARIANT_SCOPE,
                "family_id": "fam",
                "variant_id": "ungated",
                "family_input_status": "runnable_existing_data",
                "episode_split": "train",
                "market_regime_bucket": "risk_on",
                "window": "before_first_50pct",
                "incremental_recall_over_e1": 0.02,
                "incremental_captures_over_e1": 2,
            },
            {
                "candidate_scope_id": "fam__event_regime_gated",
                "candidate_scope_type": pipeline.FAMILY_VARIANT_SCOPE,
                "family_id": "fam",
                "variant_id": "event_regime_gated",
                "family_input_status": "runnable_existing_data",
                "episode_split": "train",
                "market_regime_bucket": "risk_on",
                "window": "before_first_50pct",
                "incremental_recall_over_e1": 0.02,
                "incremental_captures_over_e1": 2,
            },
        ]
    )
    density = pd.DataFrame(
        [
            {
                "candidate_scope_id": "fam__ungated",
                "density_vs_e1_full_denominator": 0.4,
                "density_full_denominator": 1.0,
            },
            {
                "candidate_scope_id": "fam__event_regime_gated",
                "density_vs_e1_full_denominator": 0.2,
                "density_full_denominator": 0.5,
            },
        ]
    )
    config = {
        "selection": {
            "focus_episode_regimes": ["risk_on", "transition"],
            "focus_window": "before_first_50pct",
            "eligible_statuses": ["runnable_existing_data"],
            "train_selection_min_incremental_recall": 0.005,
            "train_selection_max_density_vs_e1": 0.5,
            "max_selected_variants": 6,
        }
    }

    selected = pipeline.select_candidate_variants(incremental, density, config)

    assert selected == ["fam__event_regime_gated"]


def test_decision_downgrades_when_bridge_gate_fails() -> None:
    config = {
        "gates": {
            "min_incremental_recall_pct_points_robustness": 0.08,
            "min_incremental_recall_pct_points_strong": 0.12,
            "min_train_robustness_missed_capture_count": 30,
            "min_earlier_capture_count": 30,
            "max_candidate_union_canonical_events_per_instrument_year_mean": 2.75,
            "max_candidate_union_canonical_events_per_instrument_year_p95": 5.0,
            "max_candidate_family_canonical_events_per_instrument_year_mean": 1.25,
            "max_candidate_family_canonical_events_per_instrument_year_p95": 3.0,
            "max_new_family_density_share": 0.35,
            "density_drag_incremental_recall_threshold": 0.02,
            "density_drag_density_share_threshold": 0.20,
            "min_next_open_executable_rate": 0.95,
            "min_event_precision_label_complete_rate": 0.70,
            "max_bridge_recall_shortfall_pct_points": 0.02,
            "max_bridge_exclusion_rate_excess_pct_points": 0.02,
            "max_single_board_event_share": 1.0,
        }
    }
    input_status = pipeline.InputStatus("pass", "", "pass", "pass", "pass", "2025-01-01", "pass", True)
    incremental = pd.DataFrame(
        [
            {
                "candidate_scope_id": "selected_candidate_union",
                "episode_split": "robustness",
                "market_regime_bucket": "risk_on",
                "window": "before_first_50pct",
                "incremental_recall_over_e1": 0.09,
                "incremental_captures_over_e1": 9,
            },
            {
                "candidate_scope_id": "selected_candidate_union",
                "episode_split": "validation",
                "market_regime_bucket": "risk_on",
                "window": "before_first_50pct",
                "incremental_recall_over_e1": 0.01,
                "incremental_captures_over_e1": 1,
            },
        ]
    )
    density = pd.DataFrame(
        [
            {
                "candidate_scope_id": "selected_candidate_union",
                "event_count": 10,
                "density_full_denominator": 1.0,
                "events_per_instrument_year_p95": 1.0,
            },
            {
                "candidate_scope_id": pipeline.E1_SCOPE,
                "event_count": 20,
                "density_full_denominator": 2.0,
                "events_per_instrument_year_p95": 2.0,
            },
            {
                "candidate_scope_id": "fam__event_regime_gated",
                "candidate_scope_type": pipeline.FAMILY_VARIANT_SCOPE,
                "event_count": 4,
                "density_full_denominator": 0.4,
                "events_per_instrument_year_p95": 1.0,
                "density_share_of_selected_union": 0.2,
                "density_drag_flag": False,
            },
        ]
    )
    label_quality = pd.DataFrame(
        [
            {
                "candidate_scope_id": "selected_candidate_union",
                "event_split": "robustness",
                "event_regime_bucket": "risk_on",
                "board_bucket": "main",
                "event_count": 10,
                "next_open_executable_rate": 1.0,
                "label_completeness_rate": 1.0,
            }
        ]
    )
    bridge_recall = pd.DataFrame(
        [
            {
                "candidate_scope_id": "selected_candidate_union",
                "episode_split": "robustness",
                "market_regime_bucket": "risk_on",
                "board_bucket": "all",
                "window": "before_first_50pct",
                "recall": 0.10,
            },
            {
                "candidate_scope_id": pipeline.E1_SCOPE,
                "episode_split": "robustness",
                "market_regime_bucket": "risk_on",
                "board_bucket": "all",
                "window": "before_first_50pct",
                "recall": 0.50,
            },
        ]
    )
    bridge_exclusion = pd.DataFrame(
        [
            {
                "candidate_scope_id": "selected_candidate_union",
                "episode_split": "robustness",
                "market_regime_bucket": "risk_on",
                "window": "before_first_50pct",
                "bridge_excluded_rate": 0.0,
            },
            {
                "candidate_scope_id": pipeline.E1_SCOPE,
                "episode_split": "robustness",
                "market_regime_bucket": "risk_on",
                "window": "before_first_50pct",
                "bridge_excluded_rate": 0.0,
            },
        ]
    )

    decision, summary = pipeline.decide(
        input_status,
        ["fam__event_regime_gated"],
        incremental,
        density,
        label_quality,
        bridge_recall,
        bridge_exclusion,
        pd.DataFrame(),
        pd.DataFrame(),
        config,
    )

    assert decision == pipeline.DECISION_DIAGNOSTIC_ONLY
    assert "bridge_gate" in summary["gate_failures"]


def test_manifest_metadata_records_row_count_and_schema(tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    frame = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    pipeline.write_dataframe(path, frame)

    metadata = pipeline.build_artifact_metadata({"table": path}, {"table": frame})

    assert metadata["table"]["row_count"] == 2
    assert [column["name"] for column in metadata["table"]["column_schema"]] == ["a", "b"]


def test_blocked_industry_family_and_fallback_have_independent_ids() -> None:
    config = {
        "candidate_families": {
            "T2_industry_vs_market_CUSUM_break": {
                "status": "family_data_blocked",
                "data_dependency": "PIT industry classification",
                "priority": 1,
            },
            "T7_board_relative_strength_break": {
                "status": "fallback_variant",
                "data_dependency": "PIT board bucket fallback",
                "priority": 2,
                "is_fallback_of": "T2_industry_vs_market_CUSUM_break",
            },
        }
    }
    instances = pd.DataFrame(
        [{"family_id": "T7_board_relative_strength_break", "event_id": "x"}]
    )

    summary = pipeline.build_run_capability_summary(config, instances)
    blocked = summary.loc[summary["family_id"] == "T2_industry_vs_market_CUSUM_break"].iloc[0]
    fallback = summary.loc[summary["family_id"] == "T7_board_relative_strength_break"].iloc[0]

    assert blocked["family_input_status"] == "family_data_blocked"
    assert not bool(blocked["executed_flag"])
    assert fallback["is_fallback_of"] == "T2_industry_vs_market_CUSUM_break"
    assert bool(fallback["executed_flag"])


def test_validation_risk_on_sample_small_gate_value_is_config_driven() -> None:
    config = {"gates": {"validation_risk_on_sample_small_denominator": 30}}

    assert 22 < config["gates"]["validation_risk_on_sample_small_denominator"]


def test_risk_on_r_series_patch_alignment_gate_passes() -> None:
    ok, failures = rseries_patch.check_requirement_alignment()

    assert ok, failures
    assert rseries_patch.SOURCE_VARIANT_POLICY == "event_regime_gated_first"
    assert rseries_patch.UNSCORED_CANONICAL_POLICY == "retain_and_audit"
    assert rseries_patch.ROBUSTNESS_BRIDGE_DELTA_MIN == 0.05


def test_risk_on_r_series_r2_only_canonical_event_is_retained_and_audited() -> None:
    events = pd.DataFrame(
        [
            {
                "event_id": "r2_event_1",
                "instrument": "000001.SZ",
                "event_t0_date": "2020-01-01",
                "event_t0_pos": 100,
                "event_family_priority": 2,
                "family_id": rseries_patch.R2_FAMILY,
                "variant_id": "event_regime_gated",
                "family_variant_id": f"{rseries_patch.R2_FAMILY}__event_regime_gated",
                "per_family_variant_score": pd.NA,
                "score_rank_eligible_flag": False,
            }
        ]
    )

    canonical = rseries_patch.canonicalize_scored(events, "market_day_top_percentile__top10pct")

    assert len(canonical) == 1
    row = canonical.iloc[0]
    assert bool(row["unscored_canonical_event_flag"])
    assert not bool(row["score_rank_eligible_flag"])
    assert row["unscored_canonical_policy"] == "retain_and_audit"
    assert row["compression_reason"] == "unscored_canonical_retained"


def test_risk_on_r_series_score_spec_uses_available_panel_columns_and_r2_is_non_scored() -> None:
    feature_panel = pd.DataFrame(columns=["date", "instrument", *rseries_patch.AVAILABLE_SCORE_SOURCE_COLUMNS])

    score_spec = rseries_patch.build_score_spec(feature_panel, "source_hash", "requirement_hash")

    r2 = score_spec.loc[score_spec["family_id"] == rseries_patch.R2_FAMILY].iloc[0]
    assert r2["score_availability_status"] == "core_semantic_score_unavailable"
    assert not bool(r2["proxy_score_used"])
    assert bool(r2["recompute_required_flag"])

    r8 = score_spec.loc[score_spec["family_id"] == "R8_persistent_distance_above_ema"]
    assert not r8.empty
    assert set(r8["source_column_presence_status"]) == {"present"}
    assert r8["proxy_score_used"].fillna(False).astype(bool).all()


def test_risk_on_r_series_missing_score_features_are_attached_from_t0_panel() -> None:
    instances = pd.DataFrame(
        [
            {
                "event_id": "r8_event_1",
                "instrument": "000001.SZ",
                "event_t0_date": "2020-01-02",
                "family_id": "R8_persistent_distance_above_ema",
                "variant_id": "event_regime_gated",
                "return_60d": 0.10,
                "close_to_high_60": 0.95,
            }
        ]
    )
    feature_panel = pd.DataFrame(
        [
            {
                "instrument": "000001.SZ",
                "date": "2020-01-02",
                "momentum_percentile_20d": 0.70,
                "momentum_percentile_20d_lag20": 0.55,
                "momentum_percentile_60d": 0.80,
            }
        ]
    )

    attached = rseries_patch.attach_missing_score_features(instances, feature_panel)

    assert attached.loc[0, "momentum_percentile_60d"] == 0.80
    assert attached.loc[0, "return_60d"] == 0.10
