from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a5a_badside_decoupling_feasibility_probe.py"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a5a_badside_decoupling_feasibility_probe.yaml"
CONFIG_12A4_PATH = EXPERIMENT_DIR / "configs" / "config_12a4_state_change_meta_label_filter_feasibility.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / "12A5A_badside_decoupling_feasibility_probe"
TABLE_12A4_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / "12A4_state_change_meta_label_filter_feasibility"
LOCAL_MATRIX = EXPERIMENT_DIR / "outputs" / "local_cache" / "12A4_state_change_meta_label_filter_feasibility" / "meta_label_event_feature_matrix.parquet"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "manifests" / "12A5A_badside_decoupling_feasibility_probe_manifest.json"
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "badside_decoupling_feasibility_probe_report.md"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a5a_badside", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def table(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLE_DIR / f"{name}.csv", low_memory=False)


def test_required_inputs_exist_and_schema():
    audit = table("input_artifact_audit")

    assert not audit.empty
    assert audit["exists"].astype(bool).all()
    assert audit["read_status"].astype(str).eq("pass").all()
    assert not audit["schema_status"].astype(str).str.startswith("missing_columns").any()


def test_event_feature_join_uses_meta_event_id_and_scope_c0_risk_on_only():
    join = table("event_feature_join_audit")
    universe = pd.read_csv(TABLE_12A4_DIR / "meta_label_event_universe.csv.gz", low_memory=False)
    primary = universe.loc[
        universe["source_arm_is_c0"].astype(bool)
        & universe["market_regime_bucket"].astype(str).eq("risk_on")
    ]

    assert join["event_feature_join_gate_pass"].astype(bool).all()
    assert join["primary_universe_row_count"].nunique() == 1
    assert int(join["primary_universe_row_count"].iloc[0]) == len(primary)
    assert int(join["duplicate_meta_event_id_n"].sum()) == 0


def test_feature_dictionary_allowed_columns_match_feature_matrix():
    runner = load_runner()
    dictionary = pd.read_csv(TABLE_12A4_DIR / "meta_label_feature_dictionary.csv")
    matrix = pd.read_parquet(LOCAL_MATRIX)
    allowed = runner.allowed_feature_columns(dictionary, matrix)
    join = table("event_feature_join_audit")

    assert allowed
    assert set(allowed).issubset(matrix.columns)
    assert join["feature_dictionary_parity_gate_pass"].astype(bool).all()


def test_12a4_partial_or_stronger_decision_gate_required():
    decision_12a4 = pd.read_csv(TABLE_12A4_DIR / "meta_label_decision.csv").iloc[0]
    decision = table("badside_decoupling_decision").iloc[0]

    assert decision_12a4["decision_state"] in {
        "12A4_meta_label_partial_feature_source",
        "12A4_meta_label_supported",
        "12A4_nonlinear_candidate_requires_12A5_validation",
    }
    assert decision_12a4["threshold_selection_source"] == "train_internal_cv"
    assert bool(decision["upstream_12a4_gate_pass"])


def test_bucket_reconstruction_uses_train_frozen_cutoffs_not_robustness_quantile():
    matrix = pd.read_parquet(LOCAL_MATRIX)
    train_threshold = matrix.loc[matrix["event_split"].eq("train"), "same_day_c0_event_count_all"].quantile(0.20)
    robustness_threshold = matrix.loc[matrix["event_split"].eq("robustness"), "same_day_c0_event_count_all"].quantile(0.20)
    recon = table("bucket_reconstruction_audit")
    row = recon.loc[recon["pool_id"].eq("density_only_top20") & recon["split"].eq("robustness")].iloc[0]

    assert row["score_direction"] == "lower_is_selected"
    assert row["train_reference_top20_threshold"] == train_threshold
    assert row["train_reference_top20_threshold"] != robustness_threshold


def test_deterministic_pool_recomputes_train_quantile_threshold_no_published_threshold_dependency():
    recon = table("bucket_reconstruction_audit")
    deterministic = recon.loc[recon["pool_id"].isin(["density_only_top20", "freshness_only_top20", "r_core_interaction_top20"])]

    assert deterministic["reconstruction_method"].eq("deterministic_score_from_feature_matrix").all()
    assert deterministic["train_quantile"].notna().all()
    assert deterministic["train_reference_top20_threshold"].notna().all()


def test_bucket_reconstruction_crosschecks_published_event_n_not_nominal_20pct():
    recon = table("bucket_reconstruction_audit")
    density = recon.loc[recon["pool_id"].eq("density_only_top20") & recon["split"].eq("robustness")].iloc[0]

    assert bool(density["event_n_match"])
    assert bool(density["inside_n_match"])
    assert int(density["reconstructed_event_n"]) == int(density["published_event_n"])
    assert int(density["reconstructed_event_n"]) != int(density["nominal_top20_event_n"])
    assert int(density["tie_expansion_n"]) > 0


def test_badside_count_is_not_hard_gate_when_upstream_only_publishes_rate():
    recon = table("bucket_reconstruction_audit")
    deterministic = recon.loc[recon["pool_id"].eq("density_only_top20")]

    assert not deterministic["bad_side_n_hard_gate_applied"].astype(bool).any()
    assert deterministic["published_bad_side_n"].isna().all()
    assert deterministic["published_bad_side_n_derived"].notna().all()


def test_shallow_tree_fallback_records_pool_badside_difficulty_change():
    decision = table("badside_decoupling_decision").iloc[0]
    recon = table("bucket_reconstruction_audit")
    shallow = recon.loc[recon["pool_id"].eq("shallow_tree_top20") & recon["split"].eq("robustness")].iloc[0]

    if shallow["reconstruction_status"] != "ok":
        assert bool(decision["primary_pool_is_fallback"])
        assert decision["fallback_from_pool_id"] == "shallow_tree_top20"
        assert decision["fallback_to_pool_id"] == "density_only_top20"
        assert decision["fallback_from_pool_bad_side_rate"] > decision["fallback_to_pool_bad_side_rate"]


def test_fallback_primary_pool_cannot_set_supported_decision_state():
    decision = table("badside_decoupling_decision").iloc[0]

    if bool(decision["primary_pool_is_fallback"]):
        assert decision["decision_state"] != "12A5A_badside_decoupling_supported"
        assert not bool(decision["supported_gate_pass"])


def test_lightgbm_pool_skips_cleanly_when_dependency_or_upstream_status_unavailable():
    recon = table("bucket_reconstruction_audit")
    lightgbm = recon.loc[recon["pool_id"].eq("lightgbm_top20")]

    assert not lightgbm.empty
    assert not lightgbm["reconstruction_status"].eq("ok").all()
    assert "lightgbm_top20" in set(lightgbm["pool_id"])


def test_badside_composition_excludes_incomplete_horizon():
    runner = load_runner()
    frame = pd.DataFrame(
        {
            "meta_event_id": ["a", "b", "c"],
            "event_split": ["robustness"] * 3,
            "target_low_to_high_inside": [False, False, False],
            "target_low_to_high_episode_id_first": [None, None, None],
            "fast_fail_10d_label": [True, True, False],
            "false_repair_20d_label": [False, True, True],
            "bad_side_10_20_label": [True, True, True],
            "winner_120_label": [False, False, False],
            "label_10d_complete": [True, True, True],
            "label_20d_complete": [True, True, False],
            "label_120d_complete": [True, True, True],
        }
    )
    runner.add_derived_labels(frame)
    baseline = pd.DataFrame([{"source_arm_id": runner.PRIMARY_SOURCE_ARM, "split": "robustness", "low_to_high_precision": 0.1, "eligible_episode_n": 10}])
    comp = runner.build_composition(frame, {"p": pd.Series(True, index=frame.index)}, baseline)
    row = comp.loc[comp["pool_id"].eq("p") & comp["split"].eq("robustness")].iloc[0]

    assert int(row["bad_side_n"]) == 2
    assert int(row["fast_fail_n"]) == 2
    assert int(row["false_repair_n"]) == 1


def test_badside_composition_overlap_counted_once():
    comp = table("badside_composition_decomposition")
    row = comp.loc[comp["pool_id"].eq("density_only_top20") & comp["split"].eq("robustness")].iloc[0]

    assert int(row["bad_side_n"]) == int(row["fast_fail_only_n"] + row["false_repair_only_n"] + row["both_n"])
    assert int(row["both_n"]) <= min(int(row["fast_fail_n"]), int(row["false_repair_n"]))


def test_fast_fail_dominant_blocks_supported_and_partial():
    runner = load_runner()
    config = runner.load_yaml(CONFIG_PATH)
    baseline = pd.DataFrame([{"source_arm_id": runner.PRIMARY_SOURCE_ARM, "split": "robustness", "low_to_high_precision": 0.08, "eligible_episode_n": 100}])
    reconstruction = pd.DataFrame([{"pool_id": "shallow_tree_top20", "split": "robustness", "reconstruction_status": "ok"}])
    label = pd.DataFrame([{"pool_id": "shallow_tree_top20", "split": "robustness", "label_completeness_gate_pass": True}])
    composition = pd.DataFrame(
        [
            {
                "pool_id": "shallow_tree_top20",
                "split": "robustness",
                "dominant_component": "fast_fail_dominant",
                "fast_fail_only_share_of_bad": 0.60,
                "bad_side_rate": 0.40,
            }
        ]
    )
    univariate = pd.DataFrame([{"pool_id": "shallow_tree_top20", "split": "robustness", "separability_positive_class": "clean_winner_event", "abs_auc_minus_0p5": 0.20}])
    low = pd.DataFrame([{"pool_id": "shallow_tree_top20", "separability_positive_class": "clean_winner_event", "auc": 0.70, "auc_ci_low": 0.60, "clean_winner_n": 40}])
    work = pd.DataFrame(
        [
            {
                "pool_id": "shallow_tree_top20",
                "label_policy": "bad_side_vs_clean_winner",
                "workpoint_allowed_for_decision_gate": True,
                "train_cv_candidate_gate_pass": True,
                "train_class_sufficiency_gate_pass": True,
                "retained_precision": 0.13,
                "bad_side_reduction_abs": 0.06,
                "retained_bad_side_rate": 0.30,
                "retained_event_n": 600,
                "retained_episode_recall_low_to_high": 0.40,
                "precision_delta_vs_pool": 0.01,
            }
        ]
    )
    decision = runner.evaluate_decision(True, True, True, True, reconstruction, label, composition, univariate, low, pd.DataFrame(), work, baseline, config).iloc[0]

    assert decision["decision_state"] == "12A5A_no_decoupling_stop_keep_feature_source"
    assert not bool(decision["supported_gate_pass"])
    assert not bool(decision["partial_gate_pass"])


def test_clean_winner_requires_low_to_high_winner120_and_not_badside():
    runner = load_runner()
    frame = pd.DataFrame(
        {
            "target_low_to_high_inside": [True, True, False, True],
            "winner_120_label": [True, True, True, False],
            "bad_side_10_20_label": [False, True, False, False],
            "fast_fail_10d_label": [False, True, False, False],
            "false_repair_20d_label": [False, False, False, False],
            "label_10d_complete": [True] * 4,
            "label_20d_complete": [True] * 4,
            "label_120d_complete": [True] * 4,
        }
    )
    runner.add_derived_labels(frame)

    assert frame["clean_winner_event"].tolist() == [True, False, False, False]


def test_separability_requires_clean_winner_n_at_least_30_else_insufficient_positive():
    low = table("badside_separability_lowcapacity")
    sparse = low.loc[(low["separability_positive_class"].eq("clean_winner_event")) & (low["clean_winner_n"].lt(30))]

    if not sparse.empty:
        assert sparse["separability_status"].eq("insufficient_positive").all()


def test_separability_gate_requires_auc_point_and_ci_lower_bound():
    decision = table("badside_decoupling_decision").iloc[0]

    assert decision["best_lowcapacity_auc"] < 0.60 or decision["best_lowcapacity_auc_ci_low"] < 0.55
    assert not bool(decision["separable"])


def test_separability_only_on_label_complete_subset():
    runner = load_runner()
    frame = pd.DataFrame(
        {
            "target_low_to_high_inside": [True, True],
            "winner_120_label": [True, True],
            "bad_side_10_20_label": [False, False],
            "fast_fail_10d_label": [False, False],
            "false_repair_20d_label": [False, False],
            "label_10d_complete": [True, True],
            "label_20d_complete": [True, True],
            "label_120d_complete": [True, False],
        }
    )
    runner.add_derived_labels(frame)

    assert frame["clean_winner_event"].tolist() == [True, False]


def test_separability_features_are_allowed_pit_only_no_label_columns():
    uni = table("badside_separability_univariate")
    forbidden = ["target_", "label_", "winner_", "fast_fail_", "false_repair_", "bad_side_", "inside_window", "score"]

    assert {"clean_winner_event", "clean_capture_event"}.issubset(set(uni["separability_positive_class"]))
    assert not any(any(pattern in str(name) for pattern in forbidden) for name in uni["feature_name"].unique())


def test_primary_rejector_fit_uses_badside_vs_clean_winner_not_all_nonbad():
    work = table("badside_decoupling_workpoint")
    decision = table("badside_decoupling_decision").iloc[0]

    assert decision["workpoint_label_policy"] == "bad_side_vs_clean_winner"
    assert not work.loc[work["label_policy"].eq("bad_side_vs_all_non_bad"), "workpoint_allowed_for_decision_gate"].astype(bool).any()


def test_primary_rejector_requires_train_class_sufficiency():
    decision = table("badside_decoupling_decision").iloc[0]
    training = table("badside_rejector_training_audit")
    row = training.loc[
        training["pool_id"].eq(decision["primary_decision_pool_id"])
        & training["rejector_id"].eq(decision["primary_rejector_id"])
        & training["label_policy"].eq("bad_side_vs_clean_winner")
    ].iloc[0]

    assert bool(row["train_class_sufficiency_gate_pass"])
    assert int(row["train_clean_winner_n"]) >= 30
    assert int(row["train_bad_side_n"]) >= 100
    assert int(row["cv_fold_min_clean_winner_n"]) >= 8
    assert int(row["cv_fold_min_bad_side_n"]) >= 30


def test_rejector_does_not_use_score_or_label_as_feature():
    runner = load_runner()
    dictionary = pd.read_csv(TABLE_12A4_DIR / "meta_label_feature_dictionary.csv")
    matrix = pd.read_parquet(LOCAL_MATRIX)
    allowed = runner.allowed_feature_columns(dictionary, matrix)

    assert allowed
    assert not any(runner.has_forbidden_pattern(name) for name in allowed)


def test_reject_score_higher_is_worse_and_rejects_high_score_tail():
    runner = load_runner()
    frame = pd.DataFrame({"meta_event_id": [f"e{i}" for i in range(10)]})
    score = pd.Series(range(10), index=frame.index)

    retained = runner.apply_reject_fraction(frame, score, 0.2)

    assert len(retained) == 8
    assert {"e8", "e9"}.isdisjoint(set(retained["meta_event_id"]))


def test_rejector_thresholds_are_train_cv_only_validation_is_readout():
    work = table("badside_decoupling_workpoint")

    assert work["chosen_reject_fraction_source"].eq("train_internal_cv").all()
    assert work["selection_split"].eq("train_internal_cv").all()
    assert work["eval_split"].eq("robustness").all()


def test_workpoint_train_cv_candidate_guard_enforced():
    config = load_runner().load_yaml(CONFIG_PATH)
    work = table("badside_decoupling_workpoint")
    candidates = work.loc[work["train_cv_candidate_gate_pass"].astype(bool)]

    assert not candidates.empty
    assert candidates["train_cv_retained_event_n"].ge(int(config["thresholds"]["train_cv_min_retained_event_n"])).all()
    assert candidates["train_cv_retained_precision"].ge(float(config["thresholds"]["train_cv_min_precision_floor"])).all()


def test_workpoint_is_selected_by_train_cv_and_robustness_is_readout_only():
    decision = table("badside_decoupling_decision").iloc[0]

    assert decision["workpoint_chosen_reject_fraction_source"] == "train_internal_cv"
    assert decision["workpoint_selection_split"] == "train_internal_cv"
    assert decision["workpoint_eval_split"] == "robustness"


def test_lightgbm_rejector_cannot_set_supported_decision_state():
    work = table("badside_decoupling_workpoint")
    lightgbm = work.loc[work["rejector_id"].eq("lightgbm_rejector_depth_3")]
    decision = table("badside_decoupling_decision").iloc[0]

    assert not lightgbm.empty
    assert not lightgbm["workpoint_allowed_for_decision_gate"].astype(bool).any()
    assert decision["primary_rejector_id"] != "lightgbm_rejector_depth_3"


def test_decision_state_in_allowed_set_and_precedence():
    runner = load_runner()
    decision = table("badside_decoupling_decision").iloc[0]

    assert decision["decision_state"] in {
        "12A5A_badside_decoupling_supported",
        "12A5A_badside_decoupling_partial",
        "12A5A_no_decoupling_stop_keep_feature_source",
        "12A5A_blocked_input_or_pit_failure",
    }
    empty_reconstruction = pd.DataFrame(columns=["pool_id", "split", "reconstruction_status"])
    empty_label = pd.DataFrame(columns=["pool_id", "split", "label_completeness_gate_pass"])
    empty_composition = pd.DataFrame(columns=["pool_id", "split", "dominant_component", "fast_fail_only_share_of_bad", "bad_side_rate"])
    empty_univariate = pd.DataFrame(columns=["pool_id", "split", "separability_positive_class", "abs_auc_minus_0p5"])
    empty_low = pd.DataFrame(columns=["pool_id", "separability_positive_class", "auc", "auc_ci_low", "clean_winner_n"])
    empty_work = pd.DataFrame(columns=["pool_id", "label_policy", "workpoint_allowed_for_decision_gate"])
    empty_baseline = pd.DataFrame(columns=["source_arm_id", "split", "low_to_high_precision", "eligible_episode_n"])
    blocked = runner.evaluate_decision(
        False,
        True,
        True,
        True,
        empty_reconstruction,
        empty_label,
        empty_composition,
        empty_univariate,
        empty_low,
        pd.DataFrame(),
        empty_work,
        empty_baseline,
        runner.load_yaml(CONFIG_PATH),
    ).iloc[0]
    assert blocked["decision_state"] == "12A5A_blocked_input_or_pit_failure"


def test_required_outputs_and_manifest_hashes():
    runner = load_runner()
    required = {
        "input_artifact_audit.csv",
        "event_feature_join_audit.csv",
        "bucket_reconstruction_audit.csv",
        "label_completeness_audit.csv",
        "badside_composition_decomposition.csv",
        "badside_separability_univariate.csv",
        "badside_separability_lowcapacity.csv",
        "badside_rejector_training_audit.csv",
        "badside_rejector_frontier.csv",
        "badside_decoupling_workpoint.csv",
        "badside_decoupling_decision.csv",
    }
    for name in required:
        assert (TABLE_DIR / name).exists(), name
    assert REPORT_PATH.exists()
    assert MANIFEST_PATH.exists()

    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["final_decision"] == table("badside_decoupling_decision").iloc[0]["decision_state"]
    for key, meta in manifest["outputs"].items():
        path = Path(meta["path"])
        assert path.exists(), key
        assert meta["sha256"] == runner.path_sha(path)
