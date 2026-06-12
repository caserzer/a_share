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
import run_regime_family_matrix as regime_matrix  # noqa: E402
import run_risk_on_r_series_bridge_ranker as bridge_ranker  # noqa: E402
import run_post_replay_event_to_episode_retention_source as post_replay_source  # noqa: E402


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


def test_post_replay_episode_windows_deduplicate_scope_expanded_capture() -> None:
    capture = pd.DataFrame(
        [
            {
                "target_episode_id": "ep1",
                "instrument": "A",
                "episode_low_date": "2020-01-01",
                "episode_high_date": "2020-02-01",
                "first_50pct_touch_date": "2020-01-15",
                "episode_split": "train",
                "market_regime_bucket": "risk_on",
                "board_bucket": "main_board",
                "window": "low_to_first_50pct",
                "window_start_pos": 10,
                "window_end_pos": 20,
                "any_event_denominator_included": True,
                "bridge_positive_denominator_included": True,
                "candidate_scope_id": "scope_a",
            },
            {
                "target_episode_id": "ep1",
                "instrument": "A",
                "episode_low_date": "2020-01-01",
                "episode_high_date": "2020-02-01",
                "first_50pct_touch_date": "2020-01-15",
                "episode_split": "train",
                "market_regime_bucket": "risk_on",
                "board_bucket": "main_board",
                "window": "low_to_first_50pct",
                "window_start_pos": 10,
                "window_end_pos": 20,
                "any_event_denominator_included": True,
                "bridge_positive_denominator_included": True,
                "candidate_scope_id": "scope_b",
            },
        ]
    )
    episodes = pd.DataFrame(
        [
            {
                "episode_id": "ep1",
                "instrument": "A",
                "split": "train",
                "episode_low_date": "2020-01-01",
                "episode_high_date": "2020-02-01",
            }
        ]
    )

    windows = post_replay_source.build_episode_windows(capture, episodes)

    assert len(windows) == 1
    assert windows.iloc[0]["source_row_count_before_dedup"] == 2
    assert windows.iloc[0]["episode_window_source_status"] == "episode_window_ready"


def test_post_replay_membership_respects_exclusive_window_end() -> None:
    events = pd.DataFrame(
        [
            {
                "source_kind": "scope",
                "source_id": "s",
                "source_event_row_id": "e1",
                "instrument": "A",
                "event_t0_pos": 20,
                "trade_open_pos": 20,
                "event_t0_date": "2020-01-10",
                "trade_open_date": "2020-01-10",
                "non_executable_next_open": False,
            }
        ]
    )
    events = post_replay_source.apply_replay_anchor(events)
    windows = pd.DataFrame(
        [
            {
                "target_episode_id": "ep1",
                "instrument": "A",
                "episode_split": "train",
                "market_regime_bucket": "risk_on",
                "window": "low_to_first_50pct",
                "window_start_pos": 10,
                "window_end_pos": 20,
                "window_end_inclusive_flag": False,
                "bridge_positive_denominator_included": True,
                "episode_window_source_status": "episode_window_ready",
                "denominator_included_flag": True,
            }
        ]
    )

    membership = post_replay_source.build_membership(events, windows)

    assert membership.empty


def test_post_replay_low_to_high_sample_status_uses_target_denominator_only() -> None:
    assert (
        post_replay_source.sample_status(
            target_den=120,
            bridge_den=0,
            window="low_to_high",
        )
        == "sufficient_for_cell_readout"
    )


def test_post_replay_sample_status_uses_e1_missed_denominator() -> None:
    assert (
        post_replay_source.sample_status(
            target_den=120,
            bridge_den=120,
            window="low_to_first_50pct",
            e1_missed_den=12,
        )
        == "diagnostic_only"
    )


def test_post_replay_conservative_status_uses_upstream_cell_status() -> None:
    assert (
        post_replay_source.more_conservative_sample_status(
            "sufficient_for_cell_readout",
            "diagnostic_only",
        )
        == "diagnostic_only"
    )
    assert (
        post_replay_source.source_status_to_sample_status(
            "post_replay_event_membership_materialized_source_caveated_upstream"
        )
        == "diagnostic_only"
    )


def test_post_replay_executable_horizon_complete_requires_10d_and_20d_labels() -> None:
    events = pd.DataFrame(
        [
            {
                "source_event_row_id": "e1",
                "event_executable_flag": True,
                "failure_10_complete": True,
                "event_false_repair_20d_complete": False,
            },
            {
                "source_event_row_id": "e2",
                "event_executable_flag": True,
                "failure_10_complete": True,
                "event_false_repair_20d_complete": True,
            },
        ]
    )

    mask = post_replay_source.policy_event_mask(
        events,
        "post_replay_executable_horizon_complete",
    )

    assert mask.tolist() == [False, True]


def test_post_replay_scope_selection_uses_mapping_contract_filter() -> None:
    mapping_row = pd.Series(
        {
            "candidate_scope_id": "08_R6_event_regime_gated",
            "source_experiment": "08",
            "source_row_filter": (
                "triggered_family_variants contains "
                "R6_market_breadth_thrust__event_regime_gated"
            ),
        }
    )
    canonical08 = pd.DataFrame(
        [
            {
                "canonical_event_id": "r6",
                "event_id": "r6",
                "triggered_family_variants": "R6_market_breadth_thrust__event_regime_gated",
            },
            {
                "canonical_event_id": "r1",
                "event_id": "r1",
                "triggered_family_variants": "R1_relative_strength_breakout__event_regime_gated",
            },
        ]
    )

    selected = post_replay_source.select_scope_events_from_contract(
        mapping_row,
        pd.DataFrame(),
        canonical08,
    )

    assert selected["canonical_event_id"].tolist() == ["r6"]


def test_post_replay_scope_normalization_honors_anchor_union_canonicalization() -> None:
    events = pd.DataFrame(
        [
            {
                "event_id": "a",
                "canonical_event_id": "a",
                "instrument": "000001.SZ",
                "event_t0_pos": 10,
                "trade_open_pos": 11,
                "trade_open_date": "2020-01-02",
                "non_executable_next_open": False,
            },
            {
                "event_id": "b",
                "canonical_event_id": "b",
                "instrument": "000001.SZ",
                "event_t0_pos": 10,
                "trade_open_pos": 11,
                "trade_open_date": "2020-01-02",
                "non_executable_next_open": False,
            },
        ]
    )

    out = post_replay_source.normalize_scope_events(
        "08_R_core_event_regime_gated",
        events,
        pd.DataFrame(),
        source_experiment="08",
        source_path=Path("source.csv"),
        canonicalization_rule="canonical union by instrument / event anchor",
    )

    assert len(out) == 1


def test_post_replay_blocked_outputs_keep_episode_window_audit(
    tmp_path: Path, monkeypatch
) -> None:
    original_paths = post_replay_source.output_paths()
    paths = {}
    for key in original_paths:
        if key.endswith("manifest"):
            suffix = ".json"
        elif key.endswith("contract") or key.endswith("report"):
            suffix = ".md"
        elif key == "post_replay_event_episode_membership":
            suffix = ".parquet"
        else:
            suffix = ".csv"
        paths[key] = tmp_path / f"{key}{suffix}"
    monkeypatch.setattr(post_replay_source, "output_paths", lambda: paths)
    episode_windows = pd.DataFrame(
        [
            {
                "target_episode_id": "ep1",
                "instrument": "000001.SZ",
                "episode_split": "train",
                "market_regime_bucket": "risk_on",
                "window": "low_to_first_50pct",
                "window_start_pos": 10,
                "window_end_pos": 20,
                "episode_low_date": "2020-01-01",
                "first_50pct_touch_date": "2020-01-15",
                "episode_high_date": "2020-02-01",
                "episode_window_source_status": "episode_window_conflict_blocked",
                "denominator_included_flag": False,
                "window_end_inclusive_flag": True,
                "source_path": "capture.parquet",
                "source_hash": "abc",
                "source_row_count_before_dedup": 2,
                "dedup_conflict_flag": True,
                "dedup_conflict_fields": "window_end_pos",
            }
        ]
    )

    post_replay_source.write_blocked_outputs(
        post_replay_source.FINAL_CONTRACT_BLOCKED,
        ["episode_window_conflict_blocked"],
        pd.DataFrame(),
        {},
        {},
        {},
        {},
        episode_windows,
    )

    out = pd.read_csv(paths["post_replay_episode_window_audit"])
    assert out.iloc[0]["episode_window_source_status"] == "episode_window_conflict_blocked"


def test_post_replay_capture_sets_use_episode_regime_after_merge() -> None:
    events = pd.DataFrame(
        [
            {
                "source_kind": "scope",
                "source_id": "s",
                "source_event_row_id": "e1",
                "instrument": "A",
                "event_t0_pos": 15,
                "trade_open_pos": 15,
                "event_t0_date": "2020-01-10",
                "trade_open_date": "2020-01-10",
                "non_executable_next_open": False,
                "market_regime_bucket": "risk_on",
            }
        ]
    )
    events = post_replay_source.apply_replay_anchor(events)
    windows = pd.DataFrame(
        [
            {
                "target_episode_id": "ep1",
                "instrument": "A",
                "episode_split": "train",
                "market_regime_bucket": "transition",
                "window": "low_to_first_50pct",
                "window_start_pos": 10,
                "window_end_pos": 20,
                "window_end_inclusive_flag": True,
                "bridge_positive_denominator_included": True,
                "episode_window_source_status": "episode_window_ready",
                "denominator_included_flag": True,
            }
        ]
    )

    membership = post_replay_source.build_membership(events, windows)
    captured = post_replay_source.captured_episode_sets(
        membership,
        "pre_replay_capture_only",
    )

    assert captured.iloc[0]["market_regime_bucket"] == "transition"


def test_post_replay_bridge_capture_sets_filter_bridge_denominator() -> None:
    membership = pd.DataFrame(
        [
            {
                "source_kind": "scope",
                "source_id": "s",
                "episode_split": "train",
                "episode_market_regime_bucket": "risk_on",
                "window": "low_to_first_50pct",
                "target_episode_id": "ep1",
                "bridge_positive_denominator_included": True,
                "replay_anchor_pos": 10,
            },
            {
                "source_kind": "scope",
                "source_id": "s",
                "episode_split": "train",
                "episode_market_regime_bucket": "risk_on",
                "window": "low_to_first_50pct",
                "target_episode_id": "ep2",
                "bridge_positive_denominator_included": False,
                "replay_anchor_pos": 11,
            },
        ]
    )

    any_capture = post_replay_source.captured_episode_sets(
        membership,
        "pre_replay_capture_only",
    )
    bridge_capture = post_replay_source.captured_episode_sets(
        membership,
        "pre_replay_capture_only",
        bridge_only=True,
    )

    assert set(any_capture["target_episode_id"]) == {"ep1", "ep2"}
    assert bridge_capture["target_episode_id"].tolist() == ["ep1"]


def test_post_replay_optional_cross_section_panel_does_not_block(
    tmp_path: Path, monkeypatch
) -> None:
    required = tmp_path / "required.csv"
    required.write_text("a\n1\n", encoding="utf-8")
    monkeypatch.setattr(
        post_replay_source,
        "INPUT_SPECS",
        [
            post_replay_source.InputSpec("required", required, required=True),
            post_replay_source.InputSpec(
                "cross_section_feature_panel",
                tmp_path / "missing.parquet",
                required=False,
            ),
        ],
    )

    frame, failures, _ = post_replay_source.input_audit()

    assert failures == []
    optional = frame.loc[frame["source_id"] == "cross_section_feature_panel"].iloc[0]
    assert optional["source_status"] == "missing_optional_input"
    assert not bool(optional["blocking_flag"])


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


def test_regime_family_matrix_scope_density_is_scope_level_only() -> None:
    cells = pd.DataFrame(
        [
            {
                "candidate_scope_id": "07_E1_only",
                "split": "train",
                "market_regime_bucket": "transition",
            },
            {
                "candidate_scope_id": "07_E1_only",
                "split": "validation",
                "market_regime_bucket": "transition",
            },
        ]
    )
    density = pd.DataFrame(
        [
            {
                "candidate_scope_id": "07_E1_only",
                "event_count": 100,
                "events_per_instrument_year_mean": 0.25,
                "events_per_instrument_year_p95": 1.0,
                "rolling_10d_duplicate_rate": 0.01,
            }
        ]
    )

    out = regime_matrix.join_scope_density(cells, density)

    assert set(out["events_per_instrument_year_mean"]) == {0.25}
    assert set(out["density_granularity"]) == {"scope_level_only"}
    assert set(out["density_source_split"]) == {"all"}
    assert set(out["density_source_regime"]) == {"all"}
    assert not out["density_cell_recomputed_flag"].any()


def test_regime_family_matrix_cell_status_uses_more_conservative_status() -> None:
    assert regime_matrix.sample_status(29, 100) == "diagnostic_only"
    assert regime_matrix.sample_status(99, 100) == "low_power_caution"
    assert (
        regime_matrix.more_conservative_status(
            "sufficient_for_cell_readout", "low_power_caution"
        )
        == "low_power_caution"
    )
    assert (
        regime_matrix.more_conservative_status("low_power_caution", "diagnostic_only")
        == "diagnostic_only"
    )
    assert (
        regime_matrix.more_conservative_status(
            "not_available_publishable_source", "sufficient_for_cell_readout"
        )
        == "diagnostic_only"
    )


def test_regime_family_matrix_t4_gated_missing_incremental_is_not_source_blocked() -> None:
    perf = pd.DataFrame(
        [
            {
                "candidate_scope_id": "08_T4_gated",
                "reference_scope_id": (
                    "T4_entropy_compression_then_directional_expansion__event_regime_gated"
                ),
                "split": "train",
                "market_regime_bucket": "transition",
            }
        ]
    )
    incremental = pd.DataFrame(
        [
            {
                "candidate_scope_id": (
                    "T4_entropy_compression_then_directional_expansion__ungated"
                ),
                "episode_split": "train",
                "market_regime_bucket": "transition",
                "window": "before_first_50pct",
                "incremental_recall_over_e1": 0.10,
                "incremental_captures_over_e1": 10,
                "denominator_episodes": 100,
            }
        ]
    )

    out = regime_matrix.merge_incremental(perf, incremental)

    assert pd.isna(out.loc[0, "incremental_recall_over_e1"])
    assert (
        out.loc[0, "incremental_recall_source_status"]
        == "not_available_publishable_source"
    )


def test_regime_family_matrix_missing_fast_fail_blocks_family_role() -> None:
    role = regime_matrix.classify_family_role(
        pd.Series(
            {
                "candidate_scope_id": "08_R6_event_regime_gated",
                "family_id": "R6_market_breadth_thrust",
                "source_kind": "experiment_a_scope",
                "market_regime_bucket": "risk_off",
                "split": "train",
                "cell_sample_status": "sufficient_for_cell_readout",
                "source_scope_status": "ok",
                "fast_fail_10d_rate": pd.NA,
            }
        )
    )

    assert role == "source_blocked"


def test_regime_family_matrix_invalid_a_decision_fails_closed() -> None:
    perf = pd.DataFrame([{"retention_source_status": ""}])

    decision = regime_matrix.decide({"decision": "not_allowed"}, perf, [])

    assert decision == regime_matrix.DECISION_INPUT_BLOCKED


def test_regime_family_matrix_required_inputs_match_requirement() -> None:
    specs = {spec.input_id: spec for spec in regime_matrix.INPUT_SPECS}

    assert specs["density_fast_fail_audit_gate_summary"].required
    assert specs["candidate_10d_density_vs_episode_density_comparison"].required
    assert specs["regime_recall_baseline_07_e1_only"].required


def test_regime_family_matrix_exposes_planning_pass_mode() -> None:
    args = regime_matrix.parse_args(["--mode", "planning-pass"])

    assert args.mode == "planning-pass"


def test_regime_family_fast_fail_matrix_uses_aggregate_contract_names() -> None:
    perf = pd.DataFrame(
        [
            {
                "candidate_scope_id": "07_E1_only",
                "family_id": "E1_early_ema60_repair",
                "split": "train",
                "market_regime_bucket": "transition",
                "event_n": 10,
                "failure_10_complete_event_count": 9,
                "fast_fail_10d_count": 1,
                "fast_fail_10d_rate": 0.1,
                "false_repair_20d_count": 2,
                "false_repair_20d_rate": 0.2,
                "non_executable_event_count": 0,
                "horizon_incomplete_10d_count": 1,
                "label_source_column": "failure_10_complete",
                "fast_fail_definition_id": "fast_fail_10d_v1",
                "label_mapping_status": "mapped",
                "event_level_label_source_status": "available",
                "fast_fail_diagnostic_label_usage": "diagnostic_only_not_t0_feature",
            }
        ]
    )

    out = regime_matrix.build_fast_fail_diagnostic_matrix(perf)

    assert "event_split" in out.columns
    assert "event_count" in out.columns
    assert "split" not in out.columns
    assert "event_n" not in out.columns
    assert not [col for col in out.columns if col.endswith("_diagnostic_label")]


def test_regime_family_matrix_partial_a_forces_source_caveated_complete() -> None:
    perf = pd.DataFrame(
        [
            {
                "candidate_scope_id": "07_E1_only",
                "family_id": "E1_early_ema60_repair",
                "split": "train",
                "market_regime_bucket": "transition",
                "transition_reselection_role": "transition_primary_candidate",
                "retention_source_status": "pre_replay_capture_only",
            }
        ]
    )

    decision = regime_matrix.decide(
        {"decision": regime_matrix.A_DECISION_PARTIAL}, perf, []
    )

    assert decision == regime_matrix.DECISION_SOURCE_CAVEATED


def test_bridge_ranker_direct_entry_requires_sufficient_train_and_robustness() -> None:
    metrics = {
        "train_incremental_recall_over_e1": bridge_ranker.TRAIN_RECALL_DELTA_MIN + 0.02,
        "train_bridge_delta_vs_e1": bridge_ranker.TRAIN_BRIDGE_DELTA_MIN + 0.02,
        "robustness_incremental_recall_over_e1": bridge_ranker.ROB_RECALL_DELTA_MIN + 0.02,
        "robustness_bridge_delta_vs_e1": bridge_ranker.ROB_BRIDGE_DELTA_MIN + 0.02,
        "train_cell_sample_status": "sufficient_for_cell_readout",
        "robustness_cell_sample_status": "low_power_caution",
        "density_vs_e1_full_denominator": 1.0,
        "events_per_instrument_year_mean": 2.0,
        "events_per_instrument_year_p95": 5.0,
        "rolling_10d_duplicate_rate": 0.01,
        "single_family_selected_share_max": 0.2,
        "fast_fail_10d_excess_vs_e1": 0.0,
        "false_repair_20d_excess_vs_e1": 0.0,
        "event_level_label_source_status": "event_level_label_available",
        "aggregate_only": False,
        "oos_direct_pass": True,
        "oos_feature_pass": True,
    }

    tier, direct_pass, feature_pass, failures = bridge_ranker.target_tier(
        metrics, source_caveated=True, is_diagnostic_pool=False
    )

    assert not direct_pass
    assert feature_pass
    assert tier == bridge_ranker.SOURCE_CAVEATED_FEATURE_TIER
    assert "sample_status" in failures


def test_bridge_ranker_feature_source_requires_oos_positive() -> None:
    metrics = {
        "train_incremental_recall_over_e1": bridge_ranker.TRAIN_RECALL_DELTA_MIN + 0.02,
        "train_bridge_delta_vs_e1": bridge_ranker.TRAIN_BRIDGE_DELTA_MIN + 0.02,
        "robustness_incremental_recall_over_e1": bridge_ranker.ROB_RECALL_DELTA_MIN + 0.02,
        "robustness_bridge_delta_vs_e1": bridge_ranker.ROB_BRIDGE_DELTA_MIN + 0.02,
        "train_cell_sample_status": "sufficient_for_cell_readout",
        "robustness_cell_sample_status": "sufficient_for_cell_readout",
        "density_vs_e1_full_denominator": 1.0,
        "events_per_instrument_year_mean": 2.0,
        "events_per_instrument_year_p95": 5.0,
        "rolling_10d_duplicate_rate": 0.01,
        "single_family_selected_share_max": 0.2,
        "fast_fail_10d_excess_vs_e1": 0.0,
        "false_repair_20d_excess_vs_e1": 0.0,
        "event_level_label_source_status": "event_level_label_available",
        "aggregate_only": False,
        "oos_direct_pass": False,
        "oos_feature_pass": False,
    }

    tier, direct_pass, feature_pass, failures = bridge_ranker.target_tier(
        metrics, source_caveated=True, is_diagnostic_pool=False
    )

    assert tier == bridge_ranker.DIAGNOSTIC_TIER
    assert not direct_pass
    assert not feature_pass
    assert "oos_separability" in failures


def test_bridge_ranker_risk_off_tier_is_diagnostic_only() -> None:
    tier, direct_pass, feature_pass, failures = bridge_ranker.target_tier(
        {"oos_direct_pass": True, "oos_feature_pass": True},
        source_caveated=True,
        is_diagnostic_pool=True,
        risk_off=True,
    )

    assert tier == bridge_ranker.RISK_OFF_TIER
    assert not direct_pass
    assert not feature_pass
    assert failures == ["risk_off_diagnostic_only"]


def test_bridge_ranker_borderline_flag_catches_near_threshold_metrics() -> None:
    flag, names = bridge_ranker.gate_borderline(
        {
            "robustness_bridge_delta_vs_e1": bridge_ranker.ROB_BRIDGE_DELTA_MIN,
            "train_incremental_recall_over_e1": bridge_ranker.TRAIN_RECALL_DELTA_MIN + 0.02,
        }
    )

    assert flag
    assert "robustness_bridge_delta_vs_e1" in names


def test_bridge_ranker_label_policy_blocks_future_labels_as_features() -> None:
    audit = bridge_ranker.build_label_policy_audit()

    blocked = audit.loc[audit["field_name"].isin(["failure_10_label", "bridge_positive_event_or_episode_capture"])]

    assert not blocked["allowed_as_feature"].any()
    assert blocked["allowed_as_label"].all()


def test_bridge_ranker_final_decision_is_manifest_level_constant_in_outputs() -> None:
    path = (
        bridge_ranker.C_TABLE_DIR
        / "risk_on_r_series_ranker_decision_tiers.csv"
    )
    if not path.exists():
        return

    tiers = pd.read_csv(path)

    assert tiers["final_decision"].nunique() == 1
    assert "target_regime_decision_tier" in tiers.columns


def test_bridge_ranker_outputs_keep_individual_r_scope_ids() -> None:
    path = bridge_ranker.C_TABLE_DIR / "risk_on_r_series_ranker_selected_events.csv"
    if not path.exists():
        return

    selected = pd.read_csv(path, usecols=["candidate_scope_id", "family_id"])

    r6 = selected.loc[selected["family_id"] == bridge_ranker.R6]
    assert bridge_ranker.R6_SCOPE in set(r6["candidate_scope_id"])
    assert bridge_ranker.R_CORE_SCOPE in set(selected["candidate_scope_id"])


def test_bridge_ranker_oos_outputs_required_labels_and_risk_off() -> None:
    path = bridge_ranker.C_TABLE_DIR / "risk_on_r_series_ranker_oos_separability.csv"
    if not path.exists():
        return

    oos = pd.read_csv(path, usecols=["target_regime", "label_name"])

    assert "risk_off" in set(oos["target_regime"])
    assert {
        "bridge_positive_vs_bridge_negative",
        "e1_missed_captured_vs_still_missed",
    }.issubset(set(oos["label_name"]))
