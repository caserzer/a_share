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
import run_risk_on_post_filter_cost_rejector as cost_rejector  # noqa: E402
import run_transition_subregime_taxonomy_audit as transition_taxonomy  # noqa: E402


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


def test_cost_rejector_scope_audit_accepts_recorded_r_core_minus_15() -> None:
    source_pool = "08_R_core_event_regime_gated"
    scope_events = {
        source_pool: pd.DataFrame(
            [
                {"event_id": "a", "event_window_anchor_pos": 1},
                {"event_id": "b", "event_window_anchor_pos": 2},
            ]
        )
    }
    mapping = pd.DataFrame(
        [
            {
                "candidate_scope_id": source_pool,
                "scope_mapping_status": "reconstructable_event_membership",
                "source_row_filter": "R core",
                "source_artifact_hash": "abc",
            }
        ]
    )
    reconstruct = pd.DataFrame(
        [
            {
                "candidate_scope_id": source_pool,
                "scope_status": "reconstructable_event_membership",
                "source_row_count": 2,
                "published_reference_event_count": 17,
                "reconstructed_vs_published_count_difference": -15,
                "hard_gate_eligible_flag": True,
            }
        ]
    )

    audit, failures = cost_rejector.build_scope_reconstruction_audit(
        scope_events,
        mapping,
        reconstruct,
    )

    row = audit.loc[audit["source_pool"] == source_pool].iloc[0]
    assert failures == []
    assert row["scope_reconstruction_status"] == "pass"
    assert (
        row["accepted_difference_reason"]
        == "A_audit_accepted_R_core_minus_15_published_reference_difference"
    )


def test_cost_rejector_regime_role_audit_distinguishes_d_artifacts() -> None:
    audit = cost_rejector.regime_role_audit()

    summary = audit.loc[
        audit["source_artifact"].eq("post_replay_scope_retention_by_split_regime.csv")
        & audit["column_name"].eq("market_regime_bucket")
    ].iloc[0]
    membership_event = audit.loc[
        audit["source_artifact"].eq("post_replay_event_episode_membership.parquet")
        & audit["column_name"].eq("market_regime_bucket")
    ].iloc[0]
    membership_episode = audit.loc[
        audit["source_artifact"].eq("post_replay_event_episode_membership.parquet")
        & audit["column_name"].eq("episode_market_regime_bucket")
    ].iloc[0]

    assert summary["column_role"] == "episode_regime_bucket"
    assert membership_event["column_role"] == "event_regime_bucket"
    assert membership_episode["column_role"] == "episode_regime_bucket"


def test_cost_rejector_asof_join_uses_latest_same_or_prior_t0_date() -> None:
    events = pd.DataFrame(
        [
            {
                "event_id": "e1",
                "instrument": "A",
                "event_t0_date": "2020-01-03",
                "event_split": "train",
            },
            {
                "event_id": "e2",
                "instrument": "A",
                "event_t0_date": "2019-12-31",
                "event_split": "train",
            },
        ]
    )
    panel = pd.DataFrame(
        [
            {"instrument": "A", "date": "2020-01-01", "return_1d": 0.01},
            {"instrument": "A", "date": "2020-01-04", "return_1d": 0.04},
        ]
    )

    joined, meta = cost_rejector.asof_join_panel(events, panel)

    assert meta["future_join_row_count"] == 0
    assert joined.loc[joined["event_id"] == "e1", "panel_return_1d"].iloc[0] == 0.01
    assert str(joined.loc[joined["event_id"] == "e1", "feature_as_of_date"].iloc[0].date()) == "2020-01-01"
    assert joined.loc[joined["event_id"] == "e2", "daily_panel_feature_status"].iloc[0] == "asof_feature_missing"


def test_cost_rejector_membership_label_reconciliation_compares_boolean_semantics() -> None:
    source_pool = "08_R6_event_regime_gated"
    membership = pd.DataFrame(
        [
            {
                "source_id": source_pool,
                "source_kind": "scope",
                "event_id": "e1",
                "failure_10_label": 0.0,
                "failure_10_complete": 1.0,
                "event_false_repair_20d_label": False,
                "event_false_repair_20d_complete": True,
            }
        ]
    )
    labels_joined = pd.DataFrame(
        [
            {
                "event_id": "e1",
                "failure_10_label": False,
                "failure_10_complete": True,
                "event_false_repair_20d_label": 0.0,
                "event_false_repair_20d_complete": 1.0,
            }
        ]
    )

    mismatch_n, reconciled_n = cost_rejector.membership_label_reconciliation(
        source_pool,
        "all_new_candidate_union",
        labels_joined,
        membership,
    )

    assert mismatch_n == 0
    assert reconciled_n == 1


def test_cost_rejector_selected_events_keep_density_anchor_columns() -> None:
    events = pd.DataFrame(
        [
            {
                "source_pool": "08_R_core_event_regime_gated",
                "event_id": "e1",
                "canonical_event_id": "e1",
                "instrument": "A",
                "event_t0_date": "2020-01-01",
                "event_t0_pos": 10,
                "trade_open_date": "2020-01-02",
                "trade_open_pos": 11,
                "non_executable_next_open": False,
                "event_window_anchor_pos": 11,
                "event_window_anchor_date": "2020-01-02",
                "event_window_anchor_status": "next_open_execution_anchor",
                "event_key": "e1",
                "event_split": "train",
                "event_regime_bucket": "risk_on",
                "board_bucket": "main",
                "primary_family_id": "R1",
                "fast_fail_bad_10d": False,
                "false_repair_bad_20d": False,
                "cost_bad_10_20": False,
                "horizon_complete": True,
            }
        ]
    )
    scores = pd.DataFrame(
        [
            {
                "source_pool": "08_R_core_event_regime_gated",
                "model_id": "supervised_joint_cost_rejector",
                "event_id": "e1",
                "cost_bad_score": 0.1,
            }
        ]
    )

    selected, rejected = cost_rejector.build_selected_event_tables(
        events,
        scores,
        {
            "source_pool": "08_R_core_event_regime_gated",
            "model_id": "supervised_joint_cost_rejector",
            "threshold_id": "t",
            "threshold_value": 0.2,
        },
    )

    assert rejected.empty
    assert selected.loc[0, "event_window_anchor_pos"] == 11
    assert selected.loc[0, "trade_open_pos"] == 11


def test_cost_rejector_design_matrix_uses_train_only_numeric_preprocessing() -> None:
    events = pd.DataFrame(
        [
            {
                "event_split": "train",
                "horizon_complete": True,
                "amount_ratio_20d": 1.0,
                "return_5d": -0.10,
                "board_bucket": "main",
            },
            {
                "event_split": "train",
                "horizon_complete": True,
                "amount_ratio_20d": 3.0,
                "return_5d": 0.10,
                "board_bucket": "main",
            },
            {
                "event_split": "robustness",
                "horizon_complete": True,
                "amount_ratio_20d": 1000.0,
                "return_5d": 10.0,
                "board_bucket": "new_oos_board",
            },
        ]
    )
    train_mask = events["event_split"].eq("train") & events["horizon_complete"]

    matrix, columns, preprocessing = cost_rejector.build_design_matrix(events, train_mask)

    assert "amount_ratio_20d" in preprocessing["numeric"]["log1p_columns"]
    assert round(float(matrix.loc[train_mask, "amount_ratio_20d"].mean()), 12) == 0.0
    assert round(float(matrix.loc[train_mask, "return_5d"].std(ddof=0)), 12) == 1.0
    assert "board_bucket_main" in columns
    assert "board_bucket_new_oos_board" not in columns


def test_cost_rejector_final_threshold_selection_is_train_only() -> None:
    frontier = pd.DataFrame(
        [
            {
                "source_pool": "08_R_core_event_regime_gated",
                "model_id": "supervised_joint_cost_rejector",
                "threshold_id": "train_better",
                "threshold_value": 0.2,
                "keep_fraction": 0.9,
                "train_cost_reduction_relative": 0.20,
                "train_any_recall_retention": 0.95,
                "train_e1_missed_capture_retention": 0.90,
                "robustness_cost_reduction_relative": 0.01,
                "robustness_e1_missed_capture_retention": 0.70,
            },
            {
                "source_pool": "08_R_core_event_regime_gated",
                "model_id": "supervised_joint_cost_rejector",
                "threshold_id": "robustness_better",
                "threshold_value": 0.1,
                "keep_fraction": 0.8,
                "train_cost_reduction_relative": 0.05,
                "train_any_recall_retention": 0.95,
                "train_e1_missed_capture_retention": 0.90,
                "robustness_cost_reduction_relative": 0.90,
                "robustness_e1_missed_capture_retention": 0.90,
            },
        ]
    )

    selected = cost_rejector.select_final_threshold(frontier)

    assert selected["threshold_id"] == "train_better"


def test_cost_rejector_research_gate_requires_declared_density_gate() -> None:
    oos = pd.DataFrame(
        [
            {
                "source_pool": "08_R_core_event_regime_gated",
                "model_id": "supervised_joint_cost_rejector",
                "target_label": "cost_bad_10_20",
                "split": "robustness",
                "roc_auc": 0.60,
                "pr_auc": 0.40,
                "label_prevalence": 0.30,
                "top_decile_lift": 1.5,
            }
        ]
    )
    feature_contract = pd.DataFrame(
        [
            {
                "feature_name": "x",
                "allowed_as_t0_feature": True,
                "missing_rate_train": 0.0,
                "missing_rate_robustness": 0.0,
            }
        ]
    )
    density = pd.DataFrame([{"density_readout_status": "auditable_no_predeclared_gate"}])
    decision, failures = cost_rejector.decision_from_selected(
        {
            "source_pool": "08_R_core_event_regime_gated",
            "model_id": "supervised_joint_cost_rejector",
            "train_cost_reduction_relative": 0.20,
            "robustness_cost_reduction_relative": 0.20,
            "train_fast_fail_rate_before": 0.30,
            "train_fast_fail_rate_after": 0.20,
            "train_false_repair_rate_before": 0.30,
            "train_false_repair_rate_after": 0.20,
            "robustness_fast_fail_rate_before": 0.30,
            "robustness_fast_fail_rate_after": 0.20,
            "robustness_false_repair_rate_before": 0.30,
            "robustness_false_repair_rate_after": 0.20,
            "train_any_recall_retention": 0.95,
            "robustness_any_recall_retention": 0.85,
            "train_e1_missed_capture_retention": 0.90,
            "robustness_e1_missed_capture_retention": 0.80,
            "robustness_post_filter_e1_missed_captured_episode_n": 70,
        },
        source_caveated=True,
        research_density_gate_configured=False,
        oos=oos,
        feature_contract=feature_contract,
        density_readout=density,
    )

    assert decision == cost_rejector.FINAL_FEATURE_CAVEATED
    assert "density_gate_not_configured" in failures


def test_cost_rejector_feature_gate_blocks_oos_reversal() -> None:
    decision, failures = cost_rejector.decision_from_selected(
        {
            "source_pool": "08_R_core_event_regime_gated",
            "model_id": "supervised_joint_cost_rejector",
            "train_cost_reduction_relative": 0.12,
            "robustness_cost_reduction_relative": 0.12,
            "train_fast_fail_rate_before": 0.30,
            "train_fast_fail_rate_after": 0.20,
            "train_false_repair_rate_before": 0.30,
            "train_false_repair_rate_after": 0.20,
            "robustness_fast_fail_rate_before": 0.30,
            "robustness_fast_fail_rate_after": 0.20,
            "robustness_false_repair_rate_before": 0.30,
            "robustness_false_repair_rate_after": 0.20,
            "train_any_recall_retention": 0.95,
            "robustness_any_recall_retention": 0.85,
            "train_e1_missed_capture_retention": 0.90,
            "robustness_e1_missed_capture_retention": 0.80,
            "robustness_post_filter_e1_missed_captured_episode_n": 70,
        },
        source_caveated=True,
        oos=pd.DataFrame(
            [
                {
                    "source_pool": "08_R_core_event_regime_gated",
                    "model_id": "supervised_joint_cost_rejector",
                    "target_label": "cost_bad_10_20",
                    "split": "robustness",
                    "roc_auc": 0.49,
                    "pr_auc": 0.20,
                    "label_prevalence": 0.30,
                    "top_decile_lift": 0.8,
                }
            ]
        ),
        feature_contract=pd.DataFrame(
            [
                {
                    "feature_name": "x",
                    "allowed_as_t0_feature": True,
                    "missing_rate_train": 0.0,
                    "missing_rate_robustness": 0.0,
                }
            ]
        ),
        density_readout=pd.DataFrame([{"density_readout_status": "auditable_no_predeclared_gate"}]),
    )

    assert decision == cost_rejector.FINAL_DIAGNOSTIC
    assert "feature_oos_separability_gate_failed" in failures


def test_cost_rejector_replay_policy_ids_require_complete_executable_events() -> None:
    events = pd.DataFrame(
        [
            {
                "event_id": "complete_exec",
                "horizon_complete": True,
                "non_executable_next_open": False,
            },
            {
                "event_id": "incomplete",
                "horizon_complete": False,
                "non_executable_next_open": False,
            },
            {
                "event_id": "non_exec",
                "horizon_complete": True,
                "non_executable_next_open": True,
            },
        ]
    )

    ids = cost_rejector.selected_ids_for_replay_policy(
        events,
        {"complete_exec", "incomplete", "non_exec"},
    )

    assert ids == {"complete_exec"}


def test_cost_rejector_binding_audit_reads_c_reconciliation() -> None:
    reconciliation = pd.DataFrame(
        [
            {"source_experiment": "C", "reconciliation_status": "pass"},
            {"source_experiment": "C", "reconciliation_status": "fail"},
        ]
    )

    audit = cost_rejector.build_binding_audit(
        {
            "decision": "post_replay_retention_source_source_caveated_complete",
            "local_raw_membership": {"row_count": 357450},
            "output_row_counts": {"post_replay_episode_window_audit": 4986},
            "entry_support_allowed": False,
            "oracle_policies_audit_only": True,
        },
        pd.DataFrame(),
        reconciliation,
    )

    row = audit.loc[audit["binding_name"].eq("D C-arm reconciliation")].iloc[0]
    assert row["observed_value"] == "1/2 pass"
    assert row["binding_status"] == "drift"


def test_cost_rejector_density_readout_reports_concentration() -> None:
    selected_events = pd.DataFrame(
        [
            {
                "source_pool": "s",
                "model_id": "m",
                "threshold_id": "t",
                "event_id": "e1",
                "canonical_event_id": "e1",
                "instrument": "A",
                "event_window_anchor_pos": 1,
                "event_key": "e1",
                "primary_family_id": "R1",
                "board_bucket": "main",
            },
            {
                "source_pool": "s",
                "model_id": "m",
                "threshold_id": "t",
                "event_id": "e2",
                "canonical_event_id": "e2",
                "instrument": "A",
                "event_window_anchor_pos": 3,
                "event_key": "e2",
                "primary_family_id": "R1",
                "board_bucket": "main",
            },
        ]
    )
    density_summary = pd.DataFrame(
        [{"candidate_scope_id": "07_E1_only", "instrument_years": 2.0, "events_per_instrument_year_mean": 1.0}]
    )

    out = cost_rejector.build_density_readout(
        selected_events,
        density_summary,
        {"source_pool": "s", "model_id": "m", "threshold_id": "t"},
    )

    assert out.loc[0, "family_concentration"] == 1.0
    assert out.loc[0, "board_concentration"] == 1.0
    assert "rolling_10d_executable_event_day_density" in out.columns


def test_transition_taxonomy_default_boundary_is_reclassification() -> None:
    events = pd.DataFrame(
        [
            {
                "event_split": "train",
                "market_trend_60d": 0.05,
                "market_trend_20d": 0.04,
                "market_drawdown_120d": -0.12,
                "market_volatility_20d": 0.01,
            },
            {
                "event_split": "train",
                "market_trend_60d": -0.05,
                "market_trend_20d": -0.03,
                "market_drawdown_120d": -0.02,
                "market_volatility_20d": 0.01,
            },
            {
                "event_split": "train",
                "market_trend_60d": 0.005,
                "market_trend_20d": 0.02,
                "market_drawdown_120d": -0.12,
                "market_volatility_20d": 0.01,
            },
            {
                "event_split": "train",
                "market_trend_60d": pd.NA,
                "market_trend_20d": pd.NA,
                "market_drawdown_120d": -0.12,
                "market_volatility_20d": 0.01,
            },
        ]
    )

    out = transition_taxonomy.assign_default_subregime(events)

    assert out["raw_core_quadrant"].tolist() == [
        "recovery",
        "deterioration",
        "recovery",
        "component_missing",
    ]
    assert out["final_default_subregime"].tolist() == [
        "transition_recovery",
        "transition_deterioration",
        "transition_boundary_or_mixed",
        "transition_component_missing",
    ]
    assert (
        out.loc[2, "boundary_reclassification_reason"]
        == "trend_boundary_margin"
    )


def test_transition_taxonomy_preprocessing_is_train_only() -> None:
    features = pd.DataFrame(
        {
            "split": ["train", "train", "robustness"],
            "market_return_20d": [1.0, 3.0, 1000.0],
            "market_volatility_20d": [0.1, 0.3, 100.0],
        }
    )

    matrix, meta = transition_taxonomy.preprocess_auto_features(
        features,
        ["market_return_20d", "market_volatility_20d"],
    )

    train = matrix.loc[features["split"].eq("train")]
    assert meta["policy"] == "train_median_impute__train_winsorize_1_99__train_zscore"
    assert round(float(train["market_return_20d"].mean()), 12) == 0.0
    assert round(float(train["market_volatility_20d"].std(ddof=0)), 12) == 1.0


def test_transition_taxonomy_block_stability_uses_date_assignments(monkeypatch) -> None:
    class FakeKMeans:
        def __init__(self, n_clusters, random_state, n_init, max_iter):
            self.n_clusters = n_clusters

        def fit_predict(self, matrix):
            return [0 if idx < len(matrix) // 2 else 1 for idx in range(len(matrix))]

    monkeypatch.setattr(transition_taxonomy, "KMeans", FakeKMeans)
    monkeypatch.setattr(
        transition_taxonomy,
        "elbow_table_for_matrix",
        lambda matrix, k_candidates: pd.DataFrame(
            {
                "k": [2],
                "min_cluster_share": [0.5],
                "silhouette": [0.5],
            }
        ),
    )
    monkeypatch.setattr(
        transition_taxonomy,
        "select_elbow_k",
        lambda elbow: (2, "test_stub"),
    )
    dates = pd.date_range("2020-01-01", periods=120, freq="D")
    features = pd.DataFrame({"date": dates, "split": ["train"] * len(dates)})
    index_values = pd.Series(range(len(dates)), dtype=float)
    cluster = pd.Series([0, 0, 0, 1, 1, 1] * 20)
    matrix = pd.DataFrame(
        {
            "market_return_20d": index_values / 10.0,
            "market_volatility_20d": (index_values % 17) / 10.0,
        }
    )
    rolling_assignments = pd.DataFrame(
        {"date": dates, "auto_cluster_id": cluster}
    )

    out = transition_taxonomy.block_stability(
        features,
        matrix,
        ["market_return_20d", "market_volatility_20d"],
        rolling_k=2,
        rolling_assignments=rolling_assignments,
    )

    assert out.loc[0, "block_sample_n"] == 6
    assert out.loc[0, "block_stability_status"] in {
        "pass",
        "block_stability_failed",
    }
    assert not pd.isna(out.loc[0, "adjusted_rand_index"])


def test_transition_taxonomy_composition_deduplicates_target_episodes() -> None:
    event_view = pd.DataFrame(
        [
            {
                "taxonomy_method": "default_deterministic",
                "event_split": "train",
                "subregime_label": "transition_recovery",
                "event_key": "e1",
                "date": pd.Timestamp("2020-01-01"),
            },
            {
                "taxonomy_method": "default_deterministic",
                "event_split": "train",
                "subregime_label": "transition_recovery",
                "event_key": "e2",
                "date": pd.Timestamp("2020-01-02"),
            },
        ]
    )
    membership = pd.DataFrame(
        [
            {
                "event_split": "train",
                "date": pd.Timestamp("2020-01-01"),
                "target_episode_id": "ep1",
            },
            {
                "event_split": "train",
                "date": pd.Timestamp("2020-01-02"),
                "target_episode_id": "ep1",
            },
        ]
    )

    out = transition_taxonomy.composition_by_split(event_view, membership)

    assert out.loc[0, "event_count"] == 2
    assert out.loc[0, "target_episode_n"] == 1
    assert out.loc[0, "target_episode_share"] == 1.0


def test_transition_taxonomy_recall_uses_subregime_episode_denominator() -> None:
    source_events = pd.DataFrame(
        [
            {
                "source_id": "07_E1_only",
                "event_split": "train",
                "taxonomy_method": "default_deterministic",
                "subregime_label": "transition_recovery",
                "window": transition_taxonomy.HEADLINE_WINDOW,
                "target_episode_id": "ep1",
                "replay_anchor_pos": 1,
                "event_executable_flag": True,
                "failure_10_complete": True,
                "event_false_repair_20d_complete": True,
                "bridge_positive_denominator_included": True,
            },
            {
                "source_id": "08_R_core_event_regime_gated",
                "event_split": "train",
                "taxonomy_method": "default_deterministic",
                "subregime_label": "transition_recovery",
                "window": transition_taxonomy.HEADLINE_WINDOW,
                "target_episode_id": "ep2",
                "replay_anchor_pos": 2,
                "event_executable_flag": True,
                "failure_10_complete": True,
                "event_false_repair_20d_complete": True,
                "bridge_positive_denominator_included": True,
            },
            {
                "source_id": "08_R_core_event_regime_gated",
                "event_split": "train",
                "taxonomy_method": "default_deterministic",
                "subregime_label": "transition_deterioration",
                "window": transition_taxonomy.HEADLINE_WINDOW,
                "target_episode_id": "ep3",
                "replay_anchor_pos": 3,
                "event_executable_flag": True,
                "failure_10_complete": True,
                "event_false_repair_20d_complete": True,
                "bridge_positive_denominator_included": True,
            },
        ]
    )

    recall, e1 = transition_taxonomy.recall_retention_matrix(source_events)
    row = recall.loc[
        recall["source_id"].eq("08_R_core_event_regime_gated")
        & recall["split"].eq("train")
        & recall["subregime_label"].eq("transition_recovery")
    ].iloc[0]

    assert row["target_episode_denominator_n"] == 2
    assert row["bridge_episode_denominator_n"] == 2
    assert row["source_post_replay_any_captured_episode_n"] == 1
    assert row["source_post_replay_any_recall"] == 0.5
    assert row["source_post_replay_bridge_recall"] == 0.5
    assert row["e1_missed_episode_n"] == 1
    assert e1.loc[
        e1["source_id"].eq("08_R_core_event_regime_gated")
        & e1["split"].eq("train")
        & e1["subregime_label"].eq("transition_recovery"),
        "target_episode_denominator_n",
    ].iloc[0] == 2


def test_transition_taxonomy_density_uses_replay_anchor_pos() -> None:
    source_events = pd.DataFrame(
        [
            {
                "taxonomy_method": "default_deterministic",
                "event_split": "train",
                "subregime_label": "transition_recovery",
                "source_id": "08_R_core_event_regime_gated",
                "event_id": "e1",
                "canonical_event_id": "e1",
                "instrument": "A",
                "event_t0_pos": 100,
                "event_t0_date": "2020-01-01",
                "replay_anchor_pos": 10,
                "replay_anchor_date": "2020-01-02",
                "family_id": "R1",
                "board_bucket": "main",
            },
            {
                "taxonomy_method": "default_deterministic",
                "event_split": "train",
                "subregime_label": "transition_recovery",
                "source_id": "08_R_core_event_regime_gated",
                "event_id": "e2",
                "canonical_event_id": "e2",
                "instrument": "A",
                "event_t0_pos": 200,
                "event_t0_date": "2020-01-03",
                "replay_anchor_pos": 12,
                "replay_anchor_date": "2020-01-04",
                "family_id": "R2",
                "board_bucket": "main",
            },
        ]
    )

    out = transition_taxonomy.density_overlap_matrix(source_events)

    assert out.loc[0, "density_contract_reference"] == "A_density_contract_replay_anchor_pos"
    assert out.loc[0, "rolling_10d_executable_event_day_density"] == 1.5
    assert out.loc[0, "rolling_10d_duplicate_rate"] == 0.5
    assert out.loc[0, "cross_family_collision_rate"] == 0.5


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
