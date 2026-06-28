from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_16a_sequential_sampling_geometry_preflight.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_16a_for_tests", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


m = load_runner()


def config() -> dict:
    return {
        "sampling_geometry": {
            "selected_threshold_id": "up50pct",
            "threshold_sensitivity_grid": ["up50pct", "up100pct", "up150pct"],
            "horizon_grid_sessions": [5, 8, 13, 15, 20],
            "primary_horizon_sessions": 20,
            "startup_authorization_basis": m.AUTHORIZATION_BASIS,
            "manual_research_plan_override": True,
            "threshold_selection_source": "inherited_from_15A_lowest_pre_registered_material_censoring_threshold",
            "eligible_split_buckets": ["train", "validation", "robustness"],
            "stability_gate_split_buckets": ["train", "robustness"],
            "stress_test_split_buckets": ["validation"],
            "sufficient_episode_clusters_min": 200,
            "split_stability_episode_clusters_min": 100,
            "anchor_overcount_ratio_min": 1.5,
            "effective_sample_size_min": 200,
            "effective_to_anchor_ratio_abs_range_max": 0.20,
        }
    }


def member(**overrides: object) -> dict:
    base = {
        "instrument": "S1",
        "reference_date": "2020-01-01",
        "row_id": 1,
        "threshold_id": "up50pct",
        "split_bucket": "train",
        "entry_pos": 10,
        "time_to_threshold_sessions": 9,
        "path_winner": True,
        "is_censored": False,
        "available_forward_sessions": 100,
        "episode_threshold_pos": 19,
        "episode_cluster_id": "up50pct::S1::000000",
        "cluster_start_pos": 10,
        "cluster_end_pos": 39,
        "cluster_split_bucket": "train",
        "touches_multiple_split_buckets": False,
        "touches_multiple_calendar_split_buckets": False,
        "episode_cluster_status": "pass",
    }
    base.update(overrides)
    base["source_row_key"] = (
        f"{base['instrument']}|{base['reference_date']}|{base['row_id']}|{base['threshold_id']}"
    )
    return base


def membership(rows: list[dict[str, object]] | None = None) -> pd.DataFrame:
    return pd.DataFrame(rows or [member()])


def price15a(status: str = "pass") -> pd.DataFrame:
    return pd.DataFrame({"instrument": ["S1", "S2"], "qfq_row_n": [100, 100], "price_path_status": [status, status]})


def price15b(status: str = "pass") -> pd.DataFrame:
    return pd.DataFrame({"instrument": ["S1", "S2"], "qfq_row_n": [100, 100], "price_path_status": [status, status]})


def intervals_for_steps() -> pd.DataFrame:
    price = m.build_price_path_completeness_audit(membership(), price15a(), price15b())
    return m.build_episode_interval_panel(membership(), price, config())


def pass_gates() -> dict[str, str]:
    return {
        "input_artifact": "pass",
        "upstream_lineage": "pass",
        "price_path_completeness": "pass",
        "cluster_interval_adapter": "pass",
        "cluster_interval_rebuild": "pass",
        "episode_cluster_non_overlap": "pass",
        "geometry_consistency": "pass",
        "search_accounting": "pass",
    }


def decision_frames(
    *,
    train_clusters: int = 250,
    validation_clusters: int = 150,
    robustness_clusters: int = 150,
    overcount_ratio: float = 2.0,
    effective_train: float = 250.0,
    ratios: tuple[float, float, float] = (0.30, 0.35, 0.40),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sampling = pd.DataFrame(
        [
            {
                "threshold_id": "up50pct",
                "cluster_split_bucket": split,
                "anchor_n": 1000,
                "episode_cluster_n": clusters,
                "nonoverlap_step_n_at_primary_horizon": 500,
                "full_horizon_nonoverlap_step_n_at_primary_horizon": 400,
                "partial_tail_step_n_at_primary_horizon": 100,
            }
            for split, clusters in [
                ("train", train_clusters),
                ("validation", validation_clusters),
                ("robustness", robustness_clusters),
            ]
        ]
    )
    over = pd.DataFrame(
        [
            {
                "threshold_id": "up50pct",
                "cluster_split_bucket": "train",
                "horizon_sessions": 20,
                "anchor_overcount_ratio_anchor_weighted": overcount_ratio,
            }
        ]
    )
    effective = pd.DataFrame(
        [
            {
                "threshold_id": "up50pct",
                "cluster_split_bucket": split,
                "horizon_sessions": 20,
                "episode_cluster_n": clusters,
                "anchor_n": 1000,
                "step_n_overlap": 1000,
                "average_uniqueness": 0.1,
                "average_uniqueness_nonoverlap": 1.0,
                "full_horizon_nonoverlap_step_n": 400,
                "effective_sample_size_overlap": 100.0,
                "effective_sample_size_nonoverlap": eff,
                "effective_sample_size_episode_cluster_blocked": clusters,
                "partial_tail_step_n": 0,
                "effective_to_anchor_ratio": ratio,
                "time_block_to_anchor_ratio": ratio,
                "episode_cluster_to_anchor_ratio": clusters / 1000,
                "effective_sample_status": "pass",
            }
            for (split, clusters, eff, ratio) in [
                ("train", train_clusters, effective_train, ratios[0]),
                ("validation", validation_clusters, 250.0, ratios[1]),
                ("robustness", robustness_clusters, 250.0, ratios[2]),
            ]
        ]
    )
    horizon = pd.DataFrame(
        [
            {
                "threshold_id": "up50pct",
                "cluster_split_bucket": "train",
                "horizon_sessions": 20,
                "full_horizon_nonoverlap_step_n": 400,
                "median_episode_length_sessions": 25,
            }
        ]
    )
    return sampling, over, effective, horizon


def make_decision(**kwargs: object) -> pd.DataFrame:
    sampling, over, effective, horizon = decision_frames(**kwargs)
    return m.build_sampling_geometry_decision(config(), pass_gates(), sampling, over, effective, horizon)


def test_cluster_interval_adapter_uses_membership_audit_for_path_winner_and_censored():
    frame = membership(
        [
            member(row_id=1, path_winner=True, is_censored=False),
            member(row_id=2, reference_date="2020-01-02", path_winner=True, is_censored=True, episode_cluster_id="up50pct::S1::000001", cluster_start_pos=50, cluster_end_pos=70),
            member(row_id=3, reference_date="2020-01-03", path_winner=False, is_censored=False, episode_cluster_id="up50pct::S1::000002", cluster_start_pos=80, cluster_end_pos=90),
        ]
    )
    price = m.build_price_path_completeness_audit(frame, price15a(), price15b())
    intervals = m.build_episode_interval_panel(frame, price, config())
    eligible = intervals.loc[intervals["eligible_episode_cluster"]]
    assert len(eligible) == 1
    assert int(eligible.iloc[0]["anchor_n"]) == 1


def test_cluster_interval_adapter_uses_episode_threshold_pos_as_anchor_hit_pos():
    frame = membership([member(reference_pos=99, entry_pos=10, time_to_threshold_sessions=9, episode_threshold_pos=19)])
    audit = m.build_cluster_interval_adapter_audit(frame, Path("membership.csv"))
    row = audit.iloc[0]
    assert row["anchor_entry_pos_source_field"] == "entry_pos"
    assert int(row["hit_pos_relation_mismatch_n"]) == 0
    assert row["adapter_status"] == "pass"


def test_cluster_interval_adapter_fails_when_interval_inconsistent_with_entry_hit_pos():
    frame = membership([member(cluster_end_pos=15)])
    audit = m.build_cluster_interval_adapter_audit(frame, Path("membership.csv"))
    assert audit.iloc[0]["adapter_status"] == "fail"
    assert int(audit.iloc[0]["entry_hit_interval_violation_n"]) == 1


def test_cluster_interval_adapter_reports_hit_pos_relation_and_interval_violation_counts():
    frame = membership(
        [
            member(row_id=1, time_to_threshold_sessions=8, episode_threshold_pos=19),
            member(row_id=2, reference_date="2020-01-02", entry_pos=5, episode_threshold_pos=10, time_to_threshold_sessions=5, cluster_start_pos=6, cluster_end_pos=20, episode_cluster_id="up50pct::S1::000001"),
        ]
    )
    audit = m.build_cluster_interval_adapter_audit(frame, Path("membership.csv"))
    row = audit.iloc[0]
    assert int(row["hit_pos_relation_mismatch_n"]) == 1
    assert int(row["entry_pos_interval_violation_n"]) == 1
    assert row["adapter_status"] == "fail"


def test_cluster_rebuild_uses_15a_path_defined_label_panel_and_15b_section_6_2_rule(tmp_path):
    label_path = tmp_path / "path_defined_label_panel.parquet"
    pd.DataFrame(
        [
            member(row_id=1, entry_pos=10, episode_threshold_pos=20),
            member(row_id=2, reference_date="2020-01-02", entry_pos=18, episode_threshold_pos=25),
            member(row_id=3, reference_date="2020-01-03", entry_pos=40, episode_threshold_pos=50),
        ]
    ).to_parquet(label_path, index=False)
    config_path = tmp_path / "config.yaml"
    config_path.write_text("x: 1\n", encoding="utf-8")
    resolved = {
        "upstream_15b_winner_episode_cluster_cache": tmp_path / "missing.parquet",
        "upstream_15a_path_defined_label_cache": label_path,
        "upstream_15b_config": config_path,
    }
    audit = m.build_cluster_interval_rebuild_audit(resolved)
    row = audit.iloc[0]
    assert row["rebuild_rule_authority"] == "upstream_requirement_15b_section_6_2"
    assert int(row["rebuilt_episode_cluster_n"]) == 2
    assert row["rebuild_status"] == "pass"


def test_cluster_rebuild_not_required_when_cache_schema_passes(tmp_path):
    cache_path = tmp_path / "winner_episode_cluster_panel.parquet"
    pd.DataFrame(
        {
            "threshold_id": ["up50pct"],
            "instrument": ["S1"],
            "episode_cluster_id": ["up50pct::S1::000000"],
            "cluster_start_pos": [10],
            "cluster_end_pos": [20],
        }
    ).to_parquet(cache_path, index=False)
    config_path = tmp_path / "config.yaml"
    config_path.write_text("x: 1\n", encoding="utf-8")
    resolved = {
        "upstream_15b_winner_episode_cluster_cache": cache_path,
        "upstream_15a_path_defined_label_cache": tmp_path / "missing.parquet",
        "upstream_15b_config": config_path,
    }
    audit = m.build_cluster_interval_rebuild_audit(resolved)
    assert audit.iloc[0]["rebuild_status"] == "not_required_pass"


def test_price_path_audit_required_and_fail_closed_when_missing_or_nonpass():
    audit = m.build_price_path_completeness_audit(membership(), price15a("fail"), price15b())
    assert set(audit["price_path_status"]) == {"fail"}
    missing_qfq = m.build_price_path_completeness_audit(membership(), price15a(), pd.DataFrame({"instrument": ["S2"], "qfq_row_n": [100], "price_path_status": ["pass"]}))
    assert set(missing_qfq["price_path_status"]) == {"fail"}


def test_episode_interval_within_price_path_observable_range():
    audit = m.build_price_path_completeness_audit(membership(), price15a(), price15b())
    row = audit.iloc[0]
    assert row["price_path_status"] == "pass"
    assert int(row["cluster_end_out_of_bounds_n"]) == 0


def test_cluster_end_beyond_anchor_available_forward_sessions_fails_closed():
    frame = membership([member(entry_pos=10, cluster_end_pos=80, available_forward_sessions=20)])
    audit = m.build_price_path_completeness_audit(frame, price15a(), price15b())
    assert audit.iloc[0]["price_path_status"] == "fail"
    assert int(audit.iloc[0]["cluster_end_beyond_anchor_available_forward_sessions_n"]) == 1


def test_eligible_excludes_cross_split_and_censored():
    frame = membership(
        [
            member(row_id=1),
            member(row_id=2, reference_date="2020-01-02", is_censored=True, episode_cluster_id="up50pct::S1::000001", cluster_start_pos=50, cluster_end_pos=70),
            member(row_id=3, reference_date="2020-01-03", cluster_split_bucket="cross_split", touches_multiple_split_buckets=True, episode_cluster_id="up50pct::S1::000002", cluster_start_pos=80, cluster_end_pos=90),
        ]
    )
    price = m.build_price_path_completeness_audit(frame, price15a(), price15b())
    intervals = m.build_episode_interval_panel(frame, price, config())
    assert int(intervals["eligible_episode_cluster"].sum()) == 1


def test_eligible_requires_split_overlap_flags_false():
    frame = membership([member(touches_multiple_calendar_split_buckets=True)])
    price = m.build_price_path_completeness_audit(frame, price15a(), price15b())
    intervals = m.build_episode_interval_panel(frame, price, config())
    assert not bool(intervals.iloc[0]["eligible_episode_cluster"])


def test_horizon_grid_frozen_at_5_8_13_15_20():
    search = m.build_search_accounting_audit(config())
    assert search.iloc[0]["horizon_grid_sessions"] == "5;8;13;15;20"
    assert search.iloc[0]["search_accounting_status"] == "pass"


def test_nonoverlapping_step_count_matches_ceil_episode_length_over_horizon():
    steps = m.build_step_geometry_panel(intervals_for_steps(), [20])
    assert int(steps.iloc[0]["step_n_nonoverlap"]) == 2


def test_full_horizon_labelable_step_count_uses_floor_episode_length_over_horizon():
    steps = m.build_step_geometry_panel(intervals_for_steps(), [20])
    assert int(steps.iloc[0]["full_horizon_nonoverlap_step_n"]) == 1


def test_overlapping_step_count_matches_episode_length_minus_horizon_plus_one():
    steps = m.build_step_geometry_panel(intervals_for_steps(), [20])
    assert int(steps.iloc[0]["step_n_overlap"]) == 11


def test_partial_tail_step_flagged_not_dropped_silently():
    steps = m.build_step_geometry_panel(intervals_for_steps(), [20])
    assert int(steps.iloc[0]["partial_tail_step_n"]) == 1


def test_anchor_overcount_ratio_uses_nonoverlap_step_denominator():
    steps = pd.DataFrame(
        {
            "threshold_id": ["up50pct"],
            "cluster_split_bucket": ["train"],
            "horizon_sessions": [20],
            "episode_cluster_id": ["c1"],
            "anchor_n": [10],
            "step_n_nonoverlap": [2],
            "labelable_step_n_for_future_16B": [1],
        }
    )
    out = m.build_anchor_overcount_readout(steps)
    assert float(out.iloc[0]["anchor_overcount_ratio_median"]) == 5.0


def test_anchor_to_labelable_step_ratio_uses_full_horizon_denominator():
    steps = pd.DataFrame(
        {
            "threshold_id": ["up50pct"],
            "cluster_split_bucket": ["train"],
            "horizon_sessions": [20],
            "episode_cluster_id": ["c1"],
            "anchor_n": [10],
            "step_n_nonoverlap": [2],
            "labelable_step_n_for_future_16B": [1],
        }
    )
    out = m.build_anchor_overcount_readout(steps)
    assert float(out.iloc[0]["anchor_to_labelable_step_ratio_anchor_weighted"]) == 10.0


def test_anchor_weighted_overcount_ratio_uses_sum_anchor_over_sum_step():
    steps = pd.DataFrame(
        {
            "threshold_id": ["up50pct", "up50pct"],
            "cluster_split_bucket": ["train", "train"],
            "horizon_sessions": [20, 20],
            "episode_cluster_id": ["c1", "c2"],
            "anchor_n": [10, 2],
            "step_n_nonoverlap": [2, 2],
            "labelable_step_n_for_future_16B": [1, 1],
        }
    )
    out = m.build_anchor_overcount_readout(steps)
    assert float(out.iloc[0]["anchor_overcount_ratio_anchor_weighted"]) == 3.0


def test_effective_sample_readout_contains_full_horizon_fields_for_gate():
    steps = m.build_step_geometry_panel(intervals_for_steps(), [20])
    out = m.build_effective_sample_size_readout(steps)
    assert "full_horizon_nonoverlap_step_n" in out.columns
    assert "effective_sample_size_nonoverlap" in out.columns


def test_effective_sample_readout_compares_episode_cluster_blocked_and_time_block():
    steps = m.build_step_geometry_panel(intervals_for_steps(), [20])
    out = m.build_effective_sample_size_readout(steps)
    row = out.iloc[0]
    assert float(row["effective_sample_size_episode_cluster_blocked"]) == 1.0
    assert float(row["time_block_to_anchor_ratio"]) == float(row["effective_to_anchor_ratio"])


def test_decision_records_validation_and_robustness_cluster_counts_for_stability_gate():
    decision = make_decision(validation_clusters=101, robustness_clusters=102)
    row = decision.iloc[0]
    assert int(row["episode_cluster_n_validation"]) == 101
    assert int(row["episode_cluster_n_robustness"]) == 102


def test_average_uniqueness_in_zero_one_and_concurrency_within_instrument_only():
    frame = membership(
        [
            member(row_id=1, instrument="S1", episode_cluster_id="up50pct::S1::000000", cluster_start_pos=0, cluster_end_pos=19, entry_pos=0, episode_threshold_pos=4),
            member(row_id=2, instrument="S2", episode_cluster_id="up50pct::S2::000000", cluster_start_pos=0, cluster_end_pos=19, entry_pos=0, episode_threshold_pos=4),
        ]
    )
    price = m.build_price_path_completeness_audit(frame, price15a(), price15b())
    intervals = m.build_episode_interval_panel(frame, price, config())
    steps = m.build_step_geometry_panel(intervals, [5])
    out = m.build_effective_sample_size_readout(steps)
    avg = float(out.iloc[0]["average_uniqueness"])
    assert 0 < avg <= 1
    assert round(float(out.iloc[0]["effective_sample_size_overlap"]), 6) == 8.0


def test_effective_sample_size_never_exceeds_step_count():
    steps = m.build_step_geometry_panel(intervals_for_steps(), [5])
    out = m.build_effective_sample_size_readout(steps)
    row = out.iloc[0]
    assert float(row["effective_sample_size_overlap"]) <= float(row["step_n_overlap"])


def test_same_threshold_instrument_episode_overlap_fails_closed():
    intervals = pd.DataFrame(
        [
            {"threshold_id": "up50pct", "cluster_split_bucket": "train", "instrument": "S1", "episode_cluster_id": "c1", "cluster_start_pos": 10, "cluster_end_pos": 30},
            {"threshold_id": "up50pct", "cluster_split_bucket": "train", "instrument": "S1", "episode_cluster_id": "c2", "cluster_start_pos": 25, "cluster_end_pos": 40},
        ]
    )
    audit = m.build_episode_cluster_non_overlap_audit(intervals)
    assert audit.iloc[0]["concurrency_status"] == "fail_same_threshold_overlap"


def test_same_threshold_instrument_cross_split_episode_overlap_fails_closed():
    intervals = pd.DataFrame(
        [
            {"threshold_id": "up50pct", "cluster_split_bucket": "train", "instrument": "S1", "episode_cluster_id": "c1", "cluster_start_pos": 10, "cluster_end_pos": 30},
            {"threshold_id": "up50pct", "cluster_split_bucket": "validation", "instrument": "S1", "episode_cluster_id": "c2", "cluster_start_pos": 25, "cluster_end_pos": 40},
        ]
    )
    audit = m.build_episode_cluster_non_overlap_audit(intervals)
    global_row = audit.loc[audit["cluster_split_bucket"].eq("all_cluster_split_buckets")].iloc[0]
    split_rows = audit.loc[~audit["cluster_split_bucket"].eq("all_cluster_split_buckets")]
    assert global_row["concurrency_status"] == "fail_same_threshold_overlap"
    assert int(global_row["same_threshold_instrument_overlap_pair_n"]) == 1
    assert set(split_rows["concurrency_status"]) == {"pass_no_same_threshold_overlap"}


def test_forward_return_not_computed_anywhere():
    search = m.build_search_accounting_audit(config())
    steps = m.build_step_geometry_panel(intervals_for_steps(), [20])
    assert not bool(search.iloc[0]["forward_return_computed"])
    assert not any("return" in col for col in steps.columns)


def test_threshold_sensitivity_does_not_change_primary_decision():
    sampling, over, effective, horizon = decision_frames()
    extra = pd.DataFrame(
        [
            {
                **effective.iloc[0].to_dict(),
                "threshold_id": "up100pct",
                "effective_sample_status": "fail",
                "effective_to_anchor_ratio": 99.0,
            }
        ]
    )
    decision = m.build_sampling_geometry_decision(
        config(), pass_gates(), sampling, over, pd.concat([effective, extra], ignore_index=True), horizon
    )
    assert decision.iloc[0]["decision_state"] == m.DECISION_READY


def test_primary_horizon_frozen_at_20_and_5_8_13_15_are_sensitivity_only():
    search = m.build_search_accounting_audit(config())
    assert int(search.iloc[0]["primary_horizon_sessions"]) == 20
    assert search.iloc[0]["horizon_grid_sessions"] == "5;8;13;15;20"


def test_sparse_validation_split_is_stress_readout_and_does_not_block_stability():
    decision = make_decision(validation_clusters=45)
    row = decision.iloc[0]
    assert row["decision_state"] == m.DECISION_READY
    assert bool(row["split_stability_evaluable"])
    assert int(row["episode_cluster_n_validation"]) == 45
    assert row["stability_gate_split_buckets"] == "train;robustness"
    assert bool(row["validation_stress_test_readout_only"])
    assert "validation=45" not in str(row["stability_not_evaluable_reason"])


def test_sparse_robustness_split_makes_stability_not_evaluable_not_unstable():
    decision = make_decision(robustness_clusters=45)
    row = decision.iloc[0]
    assert row["decision_state"] == "16A_sampling_geometry_inconclusive_too_sparse"
    assert not bool(row["split_stability_evaluable"])
    assert "robustness=45" in row["stability_not_evaluable_reason"]


def test_geometry_stable_requires_effective_to_anchor_ratio_absolute_range_within_0p20():
    decision = make_decision(ratios=(0.10, 0.35, 0.40))
    row = decision.iloc[0]
    assert row["decision_state"] == "16A_sampling_geometry_unstable_across_splits"
    assert not bool(row["geometry_stable_across_splits"])


def test_primary_horizon_longer_than_median_episode_length_reported_as_expected_sparsity():
    sampling, over, effective, horizon = decision_frames()
    decision = m.build_sampling_geometry_decision(config(), pass_gates(), sampling, over, effective, horizon)
    horizon.loc[0, "median_episode_length_sessions"] = 10
    report = m.render_report(
        decision,
        sampling,
        horizon,
        effective,
        pd.DataFrame(
            {
                "threshold_id": ["up50pct"],
                "cluster_split_bucket": ["train"],
                "instrument_n": [1],
                "episode_cluster_n": [1],
                "same_threshold_instrument_overlap_pair_n": [0],
                "max_same_threshold_instrument_concurrency": [1],
                "concurrency_status": ["pass_no_same_threshold_overlap"],
            }
        ),
        pd.DataFrame(),
    )
    assert "预期结果" in report


def test_hard_fail_gate_sources_exist_and_fail_closed_when_missing():
    gates = m.hard_gate_status(
        "fail",
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert set(gates.values()) == {"fail"}


def test_geometry_consistency_gate_rejects_impossible_values():
    bad = pd.DataFrame(
        {
            "average_uniqueness": [1.2],
            "average_uniqueness_nonoverlap": [1.0],
            "effective_sample_size_overlap": [11],
            "step_n_overlap": [10],
            "effective_sample_size_nonoverlap": [5],
            "full_horizon_nonoverlap_step_n": [4],
        }
    )
    assert m.validate_effective_sample_readout(bad).iloc[0] == "fail"


def test_decision_map_handles_overcount_not_demonstrated_without_confirmed_wording():
    decision = make_decision(overcount_ratio=1.1)
    row = decision.iloc[0]
    assert row["decision_state"] == "16A_sampling_geometry_overcount_not_demonstrated"
    assert not bool(row["anchor_overcount_demonstrated"])


def test_search_accounting_records_startup_authorization_override():
    search = m.build_search_accounting_audit(config())
    row = search.iloc[0]
    assert row["startup_authorization_basis"] == m.AUTHORIZATION_BASIS
    assert bool(row["manual_research_plan_override"])
    assert row["validation_usage"] == "stress_test_readout_only"
    assert row["search_accounting_status"] == "pass"


def test_search_accounting_fails_when_frozen_source_field_drifts():
    cfg = config()
    cfg["sampling_geometry"]["threshold_selection_source"] = "validation_selected"
    search = m.build_search_accounting_audit(cfg)
    assert search.iloc[0]["search_accounting_status"] == "fail"


def test_decision_map_never_authorizes_sequential_label_or_entry_or_separability():
    decision = make_decision()
    row = decision.iloc[0]
    assert not bool(row["sequential_label_authorized"])
    assert not bool(row["entry_policy_authorized"])
    assert not bool(row["separability_search_authorized"])


def test_ready_decision_only_authorizes_16b_design_not_entry():
    decision = make_decision()
    row = decision.iloc[0]
    assert row["decision_state"] == m.DECISION_READY
    assert row["next_allowed_requirement"] == m.NEXT_16B
    assert not bool(row["entry_policy_authorized"])
    assert not bool(row["sequential_label_authorized"])
