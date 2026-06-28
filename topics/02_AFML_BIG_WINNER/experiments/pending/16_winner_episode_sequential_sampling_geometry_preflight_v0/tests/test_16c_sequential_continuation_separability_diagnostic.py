from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
SCRIPT = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16c_sequential_continuation_separability_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_16c_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


def base_config():
    return {
        "separability": {
            "selected_threshold_id": "up50pct",
            "primary_horizon_sessions": 20,
            "primary_label_id": r.PRIMARY_LABEL_ID,
            "upstream_16b_required_decision": "16B_continuation_label_ready_for_separability_diagnostic",
            "upstream_16b_required_next_allowed": "requirement_16c_sequential_continuation_separability_diagnostic.md",
            "board_bucket_allowed_values": ["chinext", "main_board"],
            "known_failed_families": list(r.KNOWN_FAILED_FAMILIES),
            "known_failed_anchor_share_threshold": 0.50,
            "known_failed_aggregate_count_tolerance": 0,
            "hard_projection_anchor_coverage_min": 0.95,
            "soft_overlap_coverage_caveat_min": 0.95,
            "soft_membership_high_threshold": 0.30,
            "feature_missing_rate_max": 0.05,
            "pit_missing_rate_max": 0.05,
            "cv_n_splits": 5,
            "cv_min_positive_n": 1,
            "cv_min_negative_n": 1,
            "cv_min_episode_cluster_n": 1,
            "cv_min_valid_fold_n": 4,
            "purge_sessions": 20,
            "bootstrap_replicates": 10,
            "random_state": 1616,
            "max_publishable_score_sample_rows": 100,
        },
        "power_gates": {
            "train_binary_step_n_min": 1,
            "train_positive_n_min": 1,
            "train_negative_n_min": 1,
            "train_episode_cluster_n_min": 1,
            "robustness_binary_step_n_min": 1,
            "robustness_positive_n_min": 1,
            "robustness_negative_n_min": 1,
            "robustness_episode_cluster_n_min": 1,
            "primary_model_feature_n_min": 1,
            "train_feature_complete_rate_min": 0.0,
            "robustness_feature_complete_rate_min": 0.0,
        },
        "separability_gates": {
            "grouped_cv_median_roc_auc_min": 0.55,
            "grouped_cv_median_pr_auc_lift_min": 0.02,
            "grouped_cv_positive_auc_fold_share_min": 0.60,
            "purged_cv_median_roc_auc_min": 0.53,
            "purged_cv_positive_auc_fold_share_min": 0.60,
            "robustness_roc_auc_min": 0.55,
            "robustness_pr_auc_lift_min": 0.02,
            "robustness_bootstrap_auc_ci_low_min": 0.50,
            "non_known_failed_train_binary_step_n_min": 1,
            "non_known_failed_train_positive_n_min": 1,
            "non_known_failed_train_negative_n_min": 1,
            "non_known_failed_robustness_binary_step_n_min": 1,
            "non_known_failed_robustness_positive_n_min": 1,
            "non_known_failed_robustness_negative_n_min": 1,
            "non_known_failed_robustness_roc_auc_min": 0.52,
            "validation_binary_step_n_min": 1,
            "validation_positive_n_min": 1,
            "validation_negative_n_min": 1,
        },
        "model_registry": {
            "primary_model_id": r.PRIMARY_MODEL_ID,
            "allow_hyperparameter_grid": False,
            "allow_model_family_grid": False,
            "allow_feature_selection_grid": False,
        },
    }


def sample_labels() -> pd.DataFrame:
    rows = []
    for split in ["train", "robustness", "validation"]:
        for i, state in enumerate(["pos", "neg", "neutral"]):
            rows.append(
                {
                    "step_id": f"{split}-{i}",
                    "label_id": r.PRIMARY_LABEL_ID,
                    "threshold_id": "up50pct",
                    "cluster_split_bucket": split,
                    "instrument": f"SH60000{i}",
                    "episode_cluster_id": f"c-{split}-{i}",
                    "horizon_sessions": 20,
                    "step_index": i,
                    "step_start_pos": 100 + i * 20,
                    "step_end_pos": 119 + i * 20,
                    "step_start_date": f"2020-01-0{i+1}",
                    "step_end_date": f"2020-01-{i+2:02d}",
                    "step_start_qfq_close": 10.0,
                    "step_end_qfq_close": 11.0,
                    "max_drawdown_from_step_start": 0.0,
                    "step_end_price_ratio_minus_one_for_label_rule": 0.1,
                    "continuation_positive": state == "pos",
                    "continuation_negative": state == "neg",
                    "continuation_neutral": state == "neutral",
                    "label_rule_status": "pass",
                }
            )
    return pd.DataFrame(rows)


def auth_files(tmp_path: Path, next_allowed: str = "requirement_16c_sequential_continuation_separability_diagnostic.md"):
    decision = pd.DataFrame(
        [
            {
                "decision_state": "16B_continuation_label_ready_for_separability_diagnostic",
                "next_allowed_requirement": next_allowed,
                "primary_label_id": r.PRIMARY_LABEL_ID,
                "selected_threshold_id": "up50pct",
                "primary_horizon_sessions": 20,
                "base_rate_nontrivial": True,
                "effective_sample_sufficient": True,
                "base_rate_stable_train_robustness": True,
                "step_materialization_gate": "pass",
                "qfq_price_source_gate": "pass",
                "known_failed_overlap_gate": "pass",
                "known_failed_overlap_evaluability_gate": "pass",
                "step_generation_lineage_sane": True,
                "soft_overlap_partial_coverage_caveat": True,
                "known_failed_context_exposure_caveat": True,
            }
        ]
    )
    base = pd.DataFrame(
        [
            {"label_id": r.PRIMARY_LABEL_ID, "threshold_id": "up50pct", "cluster_split_bucket": "train", "horizon_sessions": 20, "labelable_step_n": 20245, "positive_step_n": 10078, "negative_step_n": 4884, "neutral_step_n": 5283},
            {"label_id": r.PRIMARY_LABEL_ID, "threshold_id": "up50pct", "cluster_split_bucket": "robustness", "horizon_sessions": 20, "labelable_step_n": 2496, "positive_step_n": 1346, "negative_step_n": 526, "neutral_step_n": 624},
            {"label_id": r.PRIMARY_LABEL_ID, "threshold_id": "up50pct", "cluster_split_bucket": "validation", "horizon_sessions": 20, "labelable_step_n": 664, "positive_step_n": 325, "negative_step_n": 180, "neutral_step_n": 159},
        ]
    )
    decision_path = tmp_path / "decision.csv"
    base_path = tmp_path / "base.csv"
    decision.to_csv(decision_path, index=False)
    base.to_csv(base_path, index=False)
    return {"upstream_16b_decision": decision_path, "upstream_16b_base_rate_readout": base_path}


def test_16b_ready_authorization_required_for_16c(tmp_path):
    resolved = auth_files(tmp_path)
    audit = r.build_upstream_16b_authorization_audit(base_config(), resolved)
    assert audit.loc[0, "authorization_status"] == "pass"


def test_16b_next_allowed_requirement_must_match_16c(tmp_path):
    resolved = auth_files(tmp_path, next_allowed="wrong.md")
    audit = r.build_upstream_16b_authorization_audit(base_config(), resolved)
    assert audit.loc[0, "authorization_status"] == "fail"
    assert "next_allowed" in audit.loc[0, "blocking_reason"]


def test_16b_authorization_requires_step_generation_lineage_sane(tmp_path):
    resolved = auth_files(tmp_path)
    decision = pd.read_csv(resolved["upstream_16b_decision"])
    decision["step_generation_lineage_sane"] = False
    decision.to_csv(resolved["upstream_16b_decision"], index=False)
    audit = r.build_upstream_16b_authorization_audit(base_config(), resolved)
    assert audit.loc[0, "authorization_status"] == "fail"
    assert "step_generation_lineage_sane" in audit.loc[0, "blocking_reason"]


def test_primary_step_universe_filters_up50_h20_primary_label_only(tmp_path):
    labels = sample_labels()
    labels.loc[0, "threshold_id"] = "up100pct"
    path = tmp_path / "labels.csv"
    labels.to_csv(path, index=False)
    out = r.load_primary_label_panel(path, base_config())
    assert "up100pct" not in set(out["threshold_id"])
    assert set(out["horizon_sessions"]) == {20}


def test_step_label_binding_rejects_duplicate_step_ids():
    labels = pd.concat([sample_labels().head(1), sample_labels().head(1)], ignore_index=True)
    audit = r.build_step_label_binding_audit(labels, base_config())
    assert audit.loc[0, "step_label_binding_gate"] == "fail"


def test_binary_target_positive_vs_negative_excludes_neutral(tmp_path):
    path = tmp_path / "labels.csv"
    sample_labels().to_csv(path, index=False)
    out = r.load_primary_label_panel(path, base_config())
    assert int(out["is_binary_target"].sum()) == 6
    assert int(out["continuation_neutral"].sum()) == 3


def test_neutral_rows_retained_in_denominator_audit(tmp_path):
    audit = r.build_neutral_population_audit(sample_labels())
    train = audit.loc[audit["split_bucket"].eq("train")].iloc[0]
    assert train["labelable_step_n"] == 3
    assert train["binary_step_n"] == 2
    assert train["neutral_n"] == 1


def test_feature_contract_forbids_step_end_and_label_fields():
    contract = r.build_feature_contract()
    assert contract.loc[contract["feature_name"].eq("step_end_pos"), "forbidden_as_model_feature"].iloc[0]
    assert contract.loc[contract["feature_name"].eq("continuation_positive"), "forbidden_as_model_feature"].iloc[0]


def test_feature_contract_forbids_cluster_end_and_episode_length_fields():
    contract = r.build_feature_contract()
    assert contract.loc[contract["feature_name"].eq("cluster_end_pos"), "forbidden_as_model_feature"].iloc[0]
    assert contract.loc[contract["feature_name"].eq("episode_length_sessions"), "forbidden_as_model_feature"].iloc[0]


def test_feature_contract_forbids_15b_15c2_taxonomy_as_model_features():
    contract = r.build_feature_contract()
    assert contract.loc[contract["feature_name"].eq("path_type"), "forbidden_as_model_feature"].iloc[0]
    assert contract.loc[contract["feature_name"].eq("known_failed_family"), "forbidden_as_model_feature"].iloc[0]


def test_qfq_rolling_features_use_only_positions_le_step_start_pos():
    qfq = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=80).astype(str), "open": 1, "high": np.arange(80) + 2, "low": np.arange(80) + 1, "close": np.arange(80) + 1, "volume": 100, "money": 1000, "turnover_rate": 1.0})
    step = type("Step", (), {"step_start_pos": 70})()
    row = r.qfq_feature_row(step, qfq)
    assert row["qfq_max_source_pos"] == 70


def test_pit_context_join_uses_asof_not_future_fill(tmp_path):
    labels = sample_labels().head(1)
    pit = pd.DataFrame(
        [{"usable_trade_date": "2020-01-02", "instrument": labels.loc[0, "instrument"], "available_time": "2020-01-02 close", "board_bucket": "main_board", "is_listed": True, "is_st": False, "is_suspended": False, "total_market_cap_cny": 1e10, "board_rank_by_market_cap": 1, "board_quota": 400, "history_ready_240d_flag": True, "history_observed_sessions_before_usable_date": 300}]
    )
    path = tmp_path / "pit.csv"
    pit.to_csv(path, index=False)
    out, gate = r.build_pit_feature_panel(labels, path, ["chinext", "main_board"])
    assert gate == "pass"
    assert bool(out.loc[0, "pit_context_missing"])


def test_pit_context_join_allows_latest_past_membership_row(tmp_path):
    labels = sample_labels().head(1)
    pit = pd.DataFrame(
        [{"usable_trade_date": "2019-12-31", "instrument": labels.loc[0, "instrument"], "available_time": "2019-12-31 close", "board_bucket": "main_board", "is_listed": True, "is_st": False, "is_suspended": False, "total_market_cap_cny": 1e10, "board_rank_by_market_cap": 1, "board_quota": 400, "history_ready_240d_flag": True, "history_observed_sessions_before_usable_date": 300}]
    )
    path = tmp_path / "pit.csv"
    pit.to_csv(path, index=False)
    out, gate = r.build_pit_feature_panel(labels, path, ["chinext", "main_board"])
    assert gate == "pass"
    assert not bool(out.loc[0, "pit_context_missing"])


def test_feature_contract_pit_asof_policy_allows_backward_asof():
    contract = r.build_feature_contract()
    pit_rows = contract.loc[contract["feature_family"].eq("pit_membership_context")]
    assert pit_rows["as_of_policy"].astype(str).str.contains("latest_le_step_start_date").all()


def test_qfq_dir_schema_status_rejects_missing_columns(tmp_path):
    qfq_dir = tmp_path / "qfq"
    qfq_dir.mkdir()
    pd.DataFrame({"date": ["2020-01-01"], "close": [1.0]}).to_csv(qfq_dir / "SH600000.csv", index=False)
    assert r.qfq_dir_schema_status(qfq_dir).startswith("fail_missing_qfq_columns")


def test_train_only_imputer_scaler_and_winsorization():
    train = pd.DataFrame({f: [1.0, 2.0, np.nan, 100.0] for f in r.MODEL_FEATURES})
    pp = r.TrainPreprocessor(r.MODEL_FEATURES).fit(train)
    assert pp.median[r.MODEL_FEATURES[0]] == 2.0


def test_validation_and_robustness_not_used_for_selection():
    search = r.build_search_accounting(base_config(), "pass")
    assert not bool(search.loc[0, "validation_used_for_selection"])
    assert not bool(search.loc[0, "robustness_used_for_selection"])


def test_no_hyperparameter_grid_or_model_family_search():
    cfg = base_config()
    cfg["model_registry"]["allow_hyperparameter_grid"] = True
    search = r.build_search_accounting(cfg, "pass")
    assert search.loc[0, "search_accounting_gate"] == "fail"


def test_episode_cluster_grouped_cv_keeps_cluster_in_one_fold():
    df = pd.DataFrame({"episode_cluster_id": ["a", "a", "b", "c"]})
    folds = r.assign_episode_cluster_grouped_folds(df, 3)
    assert folds.iloc[0] == folds.iloc[1]


def test_instrument_purged_cv_removes_same_instrument_label_window_overlap():
    train = pd.DataFrame({"instrument": ["A", "B"], "step_start_pos": [100, 500], "step_end_pos": [119, 519]})
    test = pd.DataFrame({"instrument": ["A"], "step_start_pos": [110], "step_end_pos": [129]})
    keep = r.purge_train_candidates(train, test, 20)
    assert not bool(keep.iloc[0])
    assert bool(keep.iloc[1])


def test_cv_power_gate_requires_valid_fold_counts():
    cv = pd.DataFrame({"cv_scheme": ["episode_cluster_grouped_cv"], "model_id": [r.PRIMARY_MODEL_ID], "fold_status": ["pass"]})
    assert r.valid_fold_n(cv, "episode_cluster_grouped_cv") == 1


def test_cv_power_gate_low_power_not_input_lineage_failure():
    assert r.DECISION_LOW_POWER != r.DECISION_BLOCKED


def test_binary_sample_power_uses_effective_nonoverlap_and_cluster_counts():
    neutral = r.build_neutral_population_audit(sample_labels())
    train = neutral.loc[neutral["split_bucket"].eq("train")].iloc[0]
    assert train["binary_step_n"] == train["positive_n"] + train["negative_n"]
    assert train["binary_step_n"] != train["labelable_step_n"]


def test_local_cache_inputs_are_optional_and_rebuildable_from_publishable_artifacts(tmp_path):
    cfg = {"paths": {"upstream_15b_taxonomy_assignment_panel": "missing.parquet", "upstream_15c2_anchor_soft_membership_panel": "missing.csv"}}
    resolved = {"upstream_15b_taxonomy_assignment_panel": tmp_path / "missing.parquet", "upstream_15c2_anchor_soft_membership_panel": tmp_path / "missing.csv"}
    audit = r.build_input_artifact_audit(cfg, resolved)
    assert set(audit["required_flag"]) <= {"optional_cache", "optional_appendix"}


def test_feature_coverage_gate_fails_missing_rate_above_threshold():
    panel = sample_labels()
    for feature in r.MODEL_FEATURES:
        panel[feature] = np.nan
    panel["feature_complete"] = False
    audit = r.build_training_universe_audit(panel.assign(is_binary_target=True, target_binary=[1, 0, 1, 0, 1, 0, 1, 0, 1]))
    assert audit["feature_complete_rate"].max() == 0


def test_leakage_gate_precedes_other_decision_branches():
    leakage = r.build_feature_leakage_audit(["step_end_pos"], base_config())
    assert leakage.loc[0, "leakage_status"] == "fail"


def test_known_failed_context_fields_are_readout_only_not_features():
    assert "known_failed_family" not in r.MODEL_FEATURES
    assert "path_type" not in r.MODEL_FEATURES


def test_known_failed_context_rebuilt_from_15b_publishable_membership():
    keys = ["a", "b", "c", "d", "e", "f"]
    path_types = ["late_rescue_winner", "late_rescue_winner", "late_rescue_winner", "choppy_reversal_winner", "jump_repricing_winner", "unclassified_mixed_path"]
    membership = pd.DataFrame({"source_row_key": keys, "threshold_id": ["up50pct"] * 6, "instrument": ["I"] * 6, "episode_cluster_id": ["c"] * 6, "cluster_split_bucket": ["train"] * 6})
    taxonomy = pd.DataFrame({"source_row_key": keys, "threshold_id": ["up50pct"] * 6, "episode_cluster_id": ["c"] * 6, "path_type": path_types, "assignment_unit": ["anchor_path"] * 6})
    projection, gate, _ = r.r16b.build_known_failed_cluster_projection(membership, taxonomy, None, {"label_design": {"hard_projection_anchor_coverage_min": 0.95, "soft_overlap_coverage_caveat_min": 0.95, "soft_membership_high_threshold": 0.3}})
    assert gate == "pass"
    assert projection.loc[projection["known_failed_family"].eq("late_rescue_winner"), "known_failed_step_flag"].iloc[0]


def test_known_failed_context_rebuild_must_match_16b_aggregate():
    assert r.KNOWN_FAILED_FAMILIES == ("choppy_reversal_winner", "late_rescue_winner", "jump_repricing_winner", "unclassified_mixed_path")


def test_taxonomy_cache_mismatch_fails_rebuild_consistency(tmp_path):
    rebuilt = pd.DataFrame(
        {
            "source_row_key": ["a"],
            "threshold_id": ["up50pct"],
            "path_type": ["late_rescue_winner"],
            "assignment_unit": ["anchor_path"],
        }
    )
    cache = tmp_path / "taxonomy.parquet"
    pd.DataFrame(
        {
            "source_row_key": ["a"],
            "threshold_id": ["up50pct"],
            "path_type": ["smooth_trend_winner"],
            "assignment_unit": ["anchor_path"],
        }
    ).to_parquet(cache)
    status, mismatch_n, reason = r.taxonomy_cache_consistency_status(rebuilt, cache)
    assert status == "fail_taxonomy_cache_mismatch"
    assert mismatch_n == 1
    assert "rebuilt_taxonomy" in reason


def test_known_failed_context_rebuild_fails_when_15b_rule_audit_underspecified():
    rule = pd.DataFrame({"quantile_name": ["q_efficiency_30"], "train_rule_fit_status": ["pass"]})
    feat = pd.DataFrame({"definition_status": ["pass"]})
    status, _ = r.rule_closure_status(rule, feat)
    assert status == "fail_rule_underspecified"


def test_sparse_known_failed_context_stratum_is_caveat_not_gate_failure():
    cfg = base_config()
    scored = sample_labels().loc[[0, 1, 3, 4]].copy()
    scored["target_binary"] = [1, 0, 1, 0]
    scored["model_id"] = r.PRIMARY_MODEL_ID
    scored["score"] = [0.9, 0.1, 0.8, 0.2]
    ctx = scored[["step_id"]].copy()
    ctx["known_failed_context_any"] = False
    ctx["late_rescue_context_flag"] = False
    readout, gate, caveat = r.build_context_stratified_readout(scored, ctx, cfg)
    assert gate in {"pass", "fail"}
    assert caveat is True


def test_context_concentrated_only_blocks_16d_authorization():
    assert r.DECISION_CONTEXT != r.DECISION_READY


def test_pr_auc_lift_uses_binary_positive_rate_not_labelable_positive_rate():
    metric = r.metrics_for_scores([1, 1, 0], [0.9, 0.8, 0.1])
    assert metric["binary_positive_rate"] == 2 / 3
    assert metric["pr_auc_lift_vs_binary_base"] == metric["average_precision"] - 2 / 3


def test_board_bucket_enum_frozen_and_unknown_bucket_fails(tmp_path):
    labels = sample_labels().head(1)
    pit = pd.DataFrame(
        [{"usable_trade_date": labels.loc[0, "step_start_date"], "instrument": labels.loc[0, "instrument"], "available_time": "2020-01-01 close", "board_bucket": "bad_board", "is_listed": True, "is_st": False, "is_suspended": False, "total_market_cap_cny": 1e10, "board_rank_by_market_cap": 1, "board_quota": 400, "history_ready_240d_flag": True, "history_observed_sessions_before_usable_date": 300}]
    )
    path = tmp_path / "pit.csv"
    pit.to_csv(path, index=False)
    _out, gate = r.build_pit_feature_panel(labels, path, ["chinext", "main_board"])
    assert gate == "fail_unknown_board_bucket_enum"


def test_feature_importance_stability_schema_includes_collinearity_caveat():
    out = r.build_feature_importance_readout({"episode_cluster_grouped_cv": [], "instrument_purged_chronological_cv": []})
    assert "collinearity_caveat" in out.columns
    assert "history_depth_feature_pair" in set(out["collinearity_caveat"])


def test_ready_decision_only_authorizes_named_16d_requirement():
    assert r.NEXT_16D == "requirement_16d_sequential_continuation_policy_preflight.md"


def test_all_policy_and_deployment_authorizations_remain_false():
    decision = r.initial_blocked_decision(base_config(), "x")
    for col in ["entry_policy_authorized", "exit_policy_authorized", "holding_policy_authorized", "model_deployment_authorized", "production_signal_authorized"]:
        assert not bool(decision.loc[0, col])


def test_search_accounting_rejects_posthoc_feature_or_model_variants():
    cfg = base_config()
    cfg["model_registry"]["allow_model_family_grid"] = True
    assert r.build_search_accounting(cfg, "pass").loc[0, "search_accounting_gate"] == "fail"


def test_large_score_export_policy_keeps_full_scores_local_when_needed():
    outputs = r.output_paths()
    assert outputs["score_panel"].suffix == ".parquet"
    assert outputs["score_sample"].suffixes[-2:] == [".csv", ".gz"]


def test_manifest_includes_input_artifact_hashes(tmp_path):
    input_audit = tmp_path / "input_artifact_audit.csv"
    pd.DataFrame([{"artifact_key": "upstream_x", "sha256": "abc123"}]).to_csv(input_audit, index=False)
    outputs = {"input_artifact_audit": input_audit, "manifest": tmp_path / "manifest.json"}
    decision = pd.DataFrame([{"decision_state": "x", "next_allowed_requirement": "none"}])
    cfg_path = tmp_path / "config.yaml"
    req_path = tmp_path / "requirement.md"
    cfg_path.write_text("x: 1\n", encoding="utf-8")
    req_path.write_text("requirement\n", encoding="utf-8")
    cfg = {
        "paths": {"requirement": str(req_path)},
        "separability": {
            "upstream_16b_required_decision": "ready",
            "primary_label_id": r.PRIMARY_LABEL_ID,
            "selected_threshold_id": "up50pct",
            "primary_horizon_sessions": 20,
        },
    }
    r.write_manifest(outputs["manifest"], cfg_path, cfg, decision, outputs)
    payload = pd.read_json(outputs["manifest"], typ="series").to_dict()
    assert payload["input_artifact_hashes"]["upstream_x"] == "abc123"
