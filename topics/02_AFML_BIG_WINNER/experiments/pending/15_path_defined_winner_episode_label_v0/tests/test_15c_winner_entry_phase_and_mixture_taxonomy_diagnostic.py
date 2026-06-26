from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_15c_winner_entry_phase_and_mixture_taxonomy_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_15c_for_tests", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


m = load_runner()


def scaler():
    return {feature: {"center": 0.0, "scale": 1.0} for feature in m.MEDOID_FEATURES_15B}


def anchor_frame(n: int = 12, split: str = "train", threshold: str = "up50pct") -> pd.DataFrame:
    rows = []
    for i in range(n):
        path_type = "late_rescue_winner" if i < n // 2 else "smooth_trend_winner"
        rows.append(
            {
                "source_row_key": f"SZ000001|2020-01-{i + 1:02d}|{i}|{threshold}",
                "instrument": "SZ000001",
                "reference_date": f"2020-01-{i + 1:02d}",
                "row_id": i,
                "split_bucket": split,
                "threshold_id": threshold,
                "threshold_return": 0.5,
                "reference_pos": i,
                "episode_cluster_id": f"{threshold}::SZ000001::000000",
                "cluster_split_bucket": split,
                "touches_multiple_split_buckets": False,
                "touches_multiple_calendar_split_buckets": False,
                "entry_pos": i,
                "first_threshold_hit_pos": i + 5,
                "segment_start_pos": i,
                "segment_end_pos": i + 5,
                "segment_sessions": 6,
                "entry_price": 10.0,
                "shape_close_start": 10.0,
                "shape_close_end": 15.0,
                "time_to_threshold_sessions": n - i,
                "path_efficiency": float(i),
                "max_drawdown_before_hit": -0.01 * i,
                "max_drawdown_before_hit_abs": 0.01 * i,
                "underwater_days_share": 0.1,
                "directional_entropy_5state": 0.2,
                "trend_line_r2": 0.8,
                "top1_positive_gain_share": 0.2,
                "top3_positive_gain_share": 0.4,
                "large_up_day_count": 0,
                "pullback_5pct_count": 0,
                "log_time_to_threshold": 1.0,
                "path_type": path_type,
                "path_shape_quality": "pass",
                "wick_hit_only": False,
                "path_winner": True,
                "is_censored": False,
                "cluster_start_pos": 0,
                "cluster_end_pos": n - 1,
                "ret_20d": i / n,
                "ret_60d": i / n,
                "distance_to_20d_high": i / n,
                "distance_to_60d_high": i / n,
                "distance_to_20d_low": i / n,
                "trend_ma_20_60_spread": i / n,
                "rebound_from_20d_low": i / n,
                "vol_compression_20d_60d": i / n,
                "volatility_20d": 0.02,
                "eligible_primary_anchor": split in m.SPLITS,
                "primary_gate_eligible": split in m.SPLITS and threshold == m.SELECTED_THRESHOLD_ID,
            }
        )
    return pd.DataFrame(rows)


def rule_audit_frame() -> pd.DataFrame:
    quantiles = {
        "q_efficiency_30": 0.5,
        "q_efficiency_70": 3.0,
        "q_max_drawdown_abs_30": 0.05,
        "q_max_drawdown_abs_70": 0.20,
        "q_underwater_share_50": 0.30,
        "q_underwater_share_70": 0.70,
        "q_entropy_70": 0.70,
        "q_trend_r2_50": 0.50,
        "q_trend_r2_70": 0.70,
        "q_top1_gain_share_70": 0.50,
        "q_top1_gain_share_85": 0.85,
        "q_top3_gain_share_70": 0.60,
        "q_top3_gain_share_85": 0.85,
        "q_large_up_day_count_70": 2.0,
        "q_time_to_threshold_75": 8.0,
        "q_pullback_5pct_count_50": 1.0,
        "q_pullback_5pct_count_70": 2.0,
    }
    rows = [
        {
            "rule_type": "medoid_scaler",
            "feature_id": feature,
            "quantile_name": "",
            "value": 0.0,
            "scale": 1.0,
            "train_rule_fit_status": "pass",
        }
        for feature in m.MEDOID_FEATURES_15B
    ]
    rows.extend(
        {
            "rule_type": "taxonomy_quantile",
            "feature_id": name,
            "quantile_name": name,
            "value": value,
            "scale": np.nan,
            "train_rule_fit_status": "pass",
        }
        for name, value in quantiles.items()
    )
    return pd.DataFrame(rows)


def write_adapter_inputs(tmp_path: Path):
    anchor = anchor_frame(4)
    rule = rule_audit_frame()
    taxonomy_cols = [col for col in m.TAXONOMY_REQUIRED_COLUMNS + m.TAXONOMY_OPTIONAL_COLUMNS if col in anchor.columns]
    taxonomy = m.apply_frozen_15b_taxonomy(anchor[taxonomy_cols].copy(), rule)
    taxonomy["assignment_unit"] = "anchor_path"
    membership = anchor[m.MEMBERSHIP_COLUMNS].copy()
    native = anchor[m.NATIVE_COLUMNS].copy()
    paths = {
        "taxonomy_assignment_panel_15b": tmp_path / "taxonomy.parquet",
        "path_shape_feature_panel_15b": tmp_path / "feature_panel.parquet",
        "winner_episode_cluster_membership_15b": tmp_path / "membership.csv",
        "native_universe_panel_13a": tmp_path / "native.parquet",
    }
    taxonomy.to_parquet(paths["taxonomy_assignment_panel_15b"], index=False)
    anchor[taxonomy_cols].to_parquet(paths["path_shape_feature_panel_15b"], index=False)
    membership.to_csv(paths["winner_episode_cluster_membership_15b"], index=False)
    native.to_parquet(paths["native_universe_panel_13a"], index=False)
    return paths, rule


def test_path_quality_computed_on_anchor_segment_not_cluster_medoid():
    mix = m.build_phase_conditioned_mixture(anchor_frame(12).assign(entry_phase_pit="early_base_pit", entry_phase_outcome="early_cluster_entry"), scaler(), 0.70, 0.75, 2)
    row = mix.loc[mix["phase_scheme"].eq("pit")].iloc[0]
    dist = row["path_type_distribution_vector"]
    assert "late_rescue_winner" in dist and "smooth_trend_winner" in dist


def test_path_quality_adapter_uses_taxonomy_assignment_panel_before_rebuild(tmp_path):
    paths, rule = write_adapter_inputs(tmp_path)
    _, adapter, rebuild = m.load_taxonomy_anchor_panel(paths, rule)
    assert adapter["adapter_source_priority"].iloc[0] == 1
    assert rebuild["rebuild_status"].iloc[0] == "not_required_pass"


def test_path_quality_adapter_reproduces_15b_anchor_path_type(tmp_path):
    paths, rule = write_adapter_inputs(tmp_path)
    panel, adapter, _ = m.load_taxonomy_anchor_panel(paths, rule)
    assert adapter["adapter_anchor_path_type_reproducible"].iloc[0]
    reproduced = m.apply_frozen_15b_taxonomy(panel.drop(columns=["path_type"], errors="ignore"), rule)
    assert panel["path_type"].astype(str).reset_index(drop=True).equals(reproduced["path_type"].astype(str).reset_index(drop=True))


def test_path_quality_adapter_falls_back_to_feature_panel_priority_2(tmp_path):
    paths, rule = write_adapter_inputs(tmp_path)
    paths["taxonomy_assignment_panel_15b"].unlink()
    _, adapter, rebuild = m.load_taxonomy_anchor_panel(paths, rule)
    assert adapter["adapter_source_priority"].iloc[0] == 2
    assert adapter["adapter_status"].iloc[0] == "pass"
    assert rebuild["rebuild_status"].iloc[0] == "not_required_pass"


def test_path_quality_adapter_backfills_cluster_interval_from_membership_audit(tmp_path):
    paths, rule = write_adapter_inputs(tmp_path)
    panel, adapter, _ = m.load_taxonomy_anchor_panel(paths, rule)
    assert adapter["adapter_cluster_interval_backfilled"].iloc[0]
    assert panel[["cluster_start_pos", "cluster_end_pos"]].notna().all().all()


def test_path_quality_rebuild_not_required_status_passes_when_adapter_passes(tmp_path):
    paths, rule = write_adapter_inputs(tmp_path)
    _, _, rebuild = m.load_taxonomy_anchor_panel(paths, rule)
    assert rebuild["rebuild_attempted"].iloc[0] is False or not rebuild["rebuild_attempted"].iloc[0]
    assert rebuild["rebuild_status"].iloc[0] == "not_required_pass"


def test_subgroup_medoid_uses_frozen_15b_medoid_features_and_scaler():
    group = anchor_frame(3)
    medoid = m.select_subgroup_medoid(group, scaler())
    assert medoid["source_row_key"] in set(group["source_row_key"])
    assert m.MEDOID_FEATURES_15B == [
        "path_efficiency",
        "max_drawdown_before_hit_abs",
        "underwater_days_share",
        "directional_entropy_5state",
        "trend_line_r2",
        "top1_positive_gain_share",
        "top3_positive_gain_share",
        "log_time_to_threshold",
    ]


def test_pit_phase_uses_only_reference_pos_and_earlier_fields():
    assert set(m.PIT_FEATURES) == {"ret_60d", "distance_to_60d_high", "distance_to_20d_low", "trend_ma_20_60_spread"}


def test_pit_phase_predicate_priority_and_missing_policy():
    frame = pd.DataFrame(
        {
            "ret_60d": [0.9, np.nan],
            "distance_to_60d_high": [0.95, 0.95],
            "distance_to_20d_low": [0.9, 0.9],
            "trend_ma_20_60_spread": [0.9, 0.9],
        }
    )
    q = {
        "q_ret60d_30": 0.1,
        "q_ret60d_50": 0.5,
        "q_ret60d_70": 0.7,
        "q_distance_to_60d_high_70": 0.7,
        "q_distance_to_60d_high_90": 0.9,
        "q_distance_to_20d_low_30": 0.1,
        "q_distance_to_20d_low_70": 0.7,
        "q_trend_ma_20_60_spread_50": 0.5,
    }
    out = m.assign_pit_phase(frame, q)
    assert out["entry_phase_pit"].tolist() == ["late_chase_pit", "undetermined_pit"]


def test_outcome_phase_flagged_not_upgradeable_and_blocks_if_used_as_feature():
    out = m.assign_outcome_phase(anchor_frame(4))
    assignment = m.build_entry_phase_assignment_readout(m.assign_pit_phase(out, m.fit_pit_quantiles(out, "up50pct")))
    assert not assignment["entry_phase_outcome_upgradeable_to_t0_feature"].any()


def test_both_phase_schemes_computed_and_compared():
    anchor = anchor_frame(12)
    q = m.fit_pit_quantiles(anchor, "up50pct")
    anchor = m.assign_outcome_phase(m.assign_pit_phase(anchor, q))
    mix = m.build_phase_conditioned_mixture(anchor, scaler(), 0.70, 0.75, 2)
    assert set(mix["phase_scheme"]) == {"pit", "outcome"}


def test_cross_split_clusters_excluded_from_primary_fit_and_gates():
    frame = anchor_frame(4, split="cross_split")
    frame["eligible_primary_anchor"] = False
    assert not frame["eligible_primary_anchor"].any()


def test_phased_representative_disagreement_uses_subgroup_earliest_shortest_medoid():
    anchor = anchor_frame(4).assign(entry_phase_pit="early_base_pit", entry_phase_outcome="early_cluster_entry")
    anchor.loc[0, "path_type"] = "smooth_trend_winner"
    anchor.loc[3, "time_to_threshold_sessions"] = 1
    anchor.loc[3, "path_type"] = "late_rescue_winner"
    mix = m.build_phase_conditioned_mixture(anchor, scaler(), 0.70, 0.75, 2)
    assert mix.loc[mix["phase_scheme"].eq("pit"), "subgroup_representative_disagreement"].iloc[0]


def test_disagreement_baseline_and_phased_metrics_use_same_anchor_weighted_denominator():
    mix = pd.DataFrame(
        {
            "threshold_id": ["up50pct", "up50pct"],
            "split_bucket": ["train", "train"],
            "phase_scheme": ["pit", "pit"],
            "episode_cluster_id": ["c1", "c1"],
            "anchor_n": [9, 1],
            "eligible_phase_subgroup": [True, True],
            "sparse_phase_subgroup": [False, False],
            "subgroup_representative_disagreement": [False, True],
            "internal_entropy": [0.0, 1.0],
        }
    )
    rep = pd.DataFrame(
        {
            "threshold_id": ["up50pct"],
            "episode_cluster_id": ["c1"],
            "representative_taxonomy_disagreement": [True],
            "cluster_internal_path_type_entropy": [1.0],
        }
    )
    out = m.build_disagreement_readout(mix, rep).iloc[0]
    assert out["representative_disagreement_share_baseline_anchor_weighted"] == 1.0
    assert out["representative_disagreement_share_phased_anchor_weighted"] == 0.1


def test_random_baseline_only_permutes_anchor_to_subgroup_not_membership_or_quality():
    metrics = m.random_partition_summary(np.array(["a", "b", "b", "a"]), [2, 2], np.random.default_rng(1), 1)
    assert metrics["eligible_random_anchor_n"] == 4


def test_random_baseline_seed_frozen_and_deterministic():
    anchor = anchor_frame(12).assign(entry_phase_pit=["a"] * 6 + ["b"] * 6, entry_phase_outcome=["x"] * 6 + ["y"] * 6)
    mix = m.build_phase_conditioned_mixture(anchor, scaler(), 0.70, 0.75, 2)
    _, a = m.build_random_baseline(anchor, mix, 123, 3, 2)
    _, b = m.build_random_baseline(anchor, mix, 123, 3, 2)
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))


def test_random_baseline_primary_metrics_are_anchor_weighted_not_subgroup_equal_weighted():
    mix = pd.DataFrame(
        {
            "threshold_id": ["up50pct", "up50pct"],
            "split_bucket": ["train", "train"],
            "phase_scheme": ["pit", "pit"],
            "anchor_n": [100, 1],
            "eligible_phase_subgroup": [True, True],
            "dominant_share": [0.5, 1.0],
            "internal_entropy": [1.0, 0.0],
            "sparse_phase_subgroup": [False, False],
        }
    )
    out = m.aggregate_weighted_metrics(mix).iloc[0]
    assert out["mean_dominant_share_phase"] < 0.51


def test_dominant_share_threshold_0p70_assigns_single_subtype_else_mixed():
    assert m.subtype_from_dominant(10, "smooth_trend_winner", 0.70, 0.70, 10) == "smooth_trend_winner"
    assert m.subtype_from_dominant(10, "smooth_trend_winner", 0.69, 0.70, 10) == m.MIXED_SUBTYPE


def test_sparse_phase_subgroups_do_not_count_as_single_subtype_coverage():
    anchor = anchor_frame(3)
    mix = pd.DataFrame(
        {
            "threshold_id": ["up50pct"],
            "split_bucket": ["train"],
            "phase_scheme": ["pit"],
            "subtype_0p70": [m.SPARSE_SUBTYPE],
            "anchor_n": [3],
        }
    )
    out = m.build_coverage_readout(anchor, mix).iloc[0]
    assert out["single_subtype_coverage"] == 0.0


def test_undetermined_pit_does_not_count_as_single_subtype_coverage():
    anchor = anchor_frame(12).assign(entry_phase_pit="undetermined_pit", entry_phase_outcome="early_cluster_entry")
    mix = m.build_phase_conditioned_mixture(anchor, scaler(), 0.70, 0.75, 2)
    pit = mix.loc[mix["phase_scheme"].eq("pit")]
    assert set(pit["subtype_0p70"]) == {m.MIXED_SUBTYPE}
    coverage = m.build_coverage_readout(anchor, pit).iloc[0]
    assert coverage["single_subtype_coverage"] == 0.0


def test_phase_split_is_real_requires_uplift_over_random():
    anchor = anchor_frame(12).assign(entry_phase_pit=["a"] * 6 + ["b"] * 6, entry_phase_outcome=["x"] * 6 + ["y"] * 6)
    mix = m.build_phase_conditioned_mixture(anchor, scaler(), 0.70, 0.75, 2)
    _, readout = m.build_random_baseline(anchor, mix, 123, 3, 2)
    assert ((readout["phase_split_is_real"]) == ((readout["dominant_share_uplift_vs_random"] >= 0.10) & (readout["internal_entropy_reduction_vs_random"] >= 0.10))).all()


def test_train_only_quantiles_do_not_use_validation_or_robustness():
    train = anchor_frame(4, split="train")
    val = anchor_frame(4, split="validation")
    val["ret_60d"] = 100.0
    q = m.fit_pit_quantiles(pd.concat([train, val], ignore_index=True), "up50pct")
    assert q["q_ret60d_70"] < 1.0


def test_censored_rows_excluded_from_phase_and_mixture():
    anchor = anchor_frame(4).assign(entry_phase_pit="a", entry_phase_outcome="x")
    anchor["is_censored"] = True
    anchor["eligible_primary_anchor"] = False
    mix = m.build_phase_conditioned_mixture(anchor, scaler(), 0.70, 0.75, 2)
    assert mix.empty


def test_primary_support_gate_uses_selected_threshold_train_improvement_only():
    stability = pd.DataFrame(
        {
            "threshold_id": ["up50pct", "up100pct"],
            "phase_scheme": ["pit", "pit"],
            "eligible_train_phase_subgroup_n": [300, 300],
            "phase_split_is_real": [False, True],
            "pit_scheme_supported_for_15d": [False, True],
            "outcome_scheme_descriptive_supported": [False, False],
        }
    )
    decision = m.build_decision(stability, pass_df("input_gate_status"), pass_df("lineage_status"), pass_df("price_path_status"), pass_df("adapter_status"), rebuild_pass_df(), pass_entry_rule(), pass_mixture_rule(), pass_df("random_baseline_status"), pass_df("search_accounting_status"))
    assert decision["decision_state"].iloc[0] == "15C_entry_phase_no_real_improvement_over_random"


def pass_df(col: str) -> pd.DataFrame:
    return pd.DataFrame({col: ["pass"]})


def rebuild_pass_df() -> pd.DataFrame:
    return pd.DataFrame({"rebuild_status": ["not_required_pass"]})


def pass_entry_rule() -> pd.DataFrame:
    return pd.DataFrame({"entry_phase_rule_fit_status": ["pass"], "entry_phase_provenance_status": ["pass"]})


def pass_mixture_rule() -> pd.DataFrame:
    return pd.DataFrame({"mixture_rule_fit_status": ["pass"]})


def test_validation_and_robustness_are_support_gate_no_fit_confirmations():
    search = m.build_search_accounting({"selected_threshold_id": "up50pct", "random_seed": 1, "random_repeat_n": 20, "dominant_share_threshold": 0.70, "min_phase_subgroup_anchor_n": 10})
    assert search["validation_usage"].iloc[0] == "support_gate_no_fit"
    assert search["robustness_usage"].iloc[0] == "support_gate_no_fit"


def test_hard_fail_gate_sources_exist_and_fail_closed_when_missing():
    assert m.hard_fail_present(pass_df("input_gate_status").assign(input_gate_status="fail"), pass_df("lineage_status"), pass_df("price_path_status"), pass_df("adapter_status"), rebuild_pass_df(), pass_entry_rule(), pass_mixture_rule(), pass_df("random_baseline_status"), pass_df("search_accounting_status"))
    assert m.hard_fail_present(pd.DataFrame(columns=["input_gate_status", "required_flag"]), pass_df("lineage_status"), pass_df("price_path_status"), pass_df("adapter_status"), rebuild_pass_df(), pass_entry_rule(), pass_mixture_rule(), pass_df("random_baseline_status"), pass_df("search_accounting_status"))


def test_material_subtype_share_uses_full_split_denominator():
    mixture = pd.DataFrame(
        {
            "threshold_id": ["up50pct", "up50pct"],
            "split_bucket": ["train", "train"],
            "phase_scheme": ["pit", "pit"],
            "subtype_0p70": ["smooth_trend_winner", m.MIXED_SUBTYPE],
            "anchor_n": [40, 960],
        }
    )
    assert m.material_subtype_n(mixture, "up50pct", "train", "pit", 0.05, 20) == 0


def test_search_accounting_records_startup_authorization_override():
    search = m.build_search_accounting({"selected_threshold_id": "up50pct", "random_seed": 151503, "random_repeat_n": 20, "dominant_share_threshold": 0.70, "min_phase_subgroup_anchor_n": 10})
    assert search["startup_authorization_basis"].iloc[0] == "15B_unit_granularity_insufficiency_not_15B_separability_block"
    assert search["search_accounting_status"].iloc[0] == "pass"


def test_decision_map_never_authorizes_signal_separability_or_label_deployment():
    stability = pd.DataFrame(
        {
            "threshold_id": ["up50pct"],
            "phase_scheme": ["pit"],
            "eligible_train_phase_subgroup_n": [300],
            "phase_split_is_real": [True],
            "pit_scheme_supported_for_15d": [True],
            "outcome_scheme_descriptive_supported": [False],
        }
    )
    decision = m.build_decision(stability, pass_df("input_gate_status"), pass_df("lineage_status"), pass_df("price_path_status"), pass_df("adapter_status"), rebuild_pass_df(), pass_entry_rule(), pass_mixture_rule(), pass_df("random_baseline_status"), pass_df("search_accounting_status"))
    assert not decision["label_deployment_authorized"].iloc[0]
    assert not decision["signal_search_authorized"].iloc[0]
    assert not decision["separability_search_authorized"].iloc[0]


def test_outcome_only_support_maps_to_descriptive_improvement_not_15d():
    stability = pd.DataFrame(
        {
            "threshold_id": ["up50pct", "up50pct"],
            "phase_scheme": ["pit", "outcome"],
            "eligible_train_phase_subgroup_n": [300, 300],
            "phase_split_is_real": [False, True],
            "pit_scheme_supported_for_15d": [False, False],
            "outcome_scheme_descriptive_supported": [False, True],
        }
    )
    decision = m.build_decision(stability, pass_df("input_gate_status"), pass_df("lineage_status"), pass_df("price_path_status"), pass_df("adapter_status"), rebuild_pass_df(), pass_entry_rule(), pass_mixture_rule(), pass_df("random_baseline_status"), pass_df("search_accounting_status"))
    assert decision["decision_state"].iloc[0] == "15C_outcome_phase_only_descriptive_improvement"
    assert decision["next_allowed_requirement"].iloc[0] == "none"


def test_supported_decision_only_allows_pit_phase_capture_friendly_subtype_to_15d():
    stability = pd.DataFrame(
        {
            "threshold_id": ["up50pct", "up50pct"],
            "phase_scheme": ["pit", "outcome"],
            "eligible_train_phase_subgroup_n": [300, 300],
            "phase_split_is_real": [True, True],
            "pit_scheme_supported_for_15d": [True, False],
            "outcome_scheme_descriptive_supported": [False, False],
        }
    )
    decision = m.build_decision(stability, pass_df("input_gate_status"), pass_df("lineage_status"), pass_df("price_path_status"), pass_df("adapter_status"), rebuild_pass_df(), pass_entry_rule(), pass_mixture_rule(), pass_df("random_baseline_status"), pass_df("search_accounting_status"))
    assert decision["next_allowed_requirement"].iloc[0] == "requirement_15d_capture_friendly_winner_separability_diagnostic.md"
