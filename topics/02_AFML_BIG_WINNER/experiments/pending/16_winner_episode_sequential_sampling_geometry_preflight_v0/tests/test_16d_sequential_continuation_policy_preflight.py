from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
SCRIPT = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16d_sequential_continuation_policy_preflight.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_16d_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


def base_config():
    return {
        "paths": {},
        "policy": {
            "selected_threshold_id": "up50pct",
            "primary_horizon_sessions": 20,
            "primary_label_id": r.PRIMARY_LABEL_ID,
            "primary_model_id": r.PRIMARY_MODEL_ID,
            "primary_policy_id": "defense_bottom_30pct_continuation_score_v1",
            "defense_quantiles": [0.30],
            "primary_defense_quantile": 0.30,
            "next_allowed_requirement": "requirement_16e_sequential_continuation_utility_diagnostic.md",
        },
        "power_gates": {
            "train_binary_step_n_min": 1,
            "train_negative_n_min": 1,
            "train_positive_n_min": 1,
            "train_episode_cluster_n_min": 1,
            "train_defended_binary_step_n_min": 1,
            "train_defended_negative_n_min": 1,
            "robustness_binary_step_n_min": 1,
            "robustness_negative_n_min": 1,
            "robustness_positive_n_min": 1,
            "robustness_episode_cluster_n_min": 1,
            "robustness_defended_binary_step_n_min": 1,
            "robustness_defended_negative_n_min": 1,
            "validation_binary_step_n_min": 1,
            "validation_defended_binary_step_n_min": 1,
        },
        "usefulness_gates": {
            "train_defense_negative_capture_rate_min": 0.01,
            "robustness_defense_negative_capture_rate_min": 0.01,
            "train_defense_precision_lift_vs_binary_negative_base_min": 0.01,
            "robustness_defense_precision_lift_vs_binary_negative_base_min": 0.01,
            "train_positive_sacrifice_rate_max": 1.0,
            "robustness_positive_sacrifice_rate_max": 1.0,
            "train_continue_negative_leakage_rate_max": 1.0,
            "robustness_continue_negative_leakage_rate_max": 1.0,
        },
        "context_gates": {
            "non_known_failed_train_binary_step_n_min": 1,
            "non_known_failed_train_negative_n_min": 1,
            "non_known_failed_train_defended_negative_n_min": 1,
            "non_known_failed_train_defense_precision_lift_min": 0.01,
            "non_known_failed_robustness_binary_step_n_min": 1,
            "non_known_failed_robustness_negative_n_min": 1,
            "non_known_failed_robustness_defended_negative_n_min": 1,
            "non_known_failed_robustness_defense_precision_lift_min": 0.01,
        },
    }


def scored_rows() -> pd.DataFrame:
    rows = []
    specs = [
        ("train", "pos", 0.90),
        ("train", "pos", 0.80),
        ("train", "neg", 0.10),
        ("train", "neg", 0.20),
        ("train", "neutral", -100.0),
        ("robustness", "pos", 0.85),
        ("robustness", "neg", 0.15),
        ("validation", "pos", 0.75),
        ("validation", "neg", 0.25),
    ]
    for i, (split, label, score) in enumerate(specs):
        rows.append(
            {
                "step_id": f"{split}-{i}",
                "label_id": r.PRIMARY_LABEL_ID,
                "threshold_id": "up50pct",
                "cluster_split_bucket": split,
                "instrument": "SH600000",
                "episode_cluster_id": f"{split}-cluster-{i}",
                "horizon_sessions": 20,
                "step_index": i,
                "step_start_pos": i * 20,
                "step_end_pos": i * 20 + 19,
                "step_start_date": "2020-01-01",
                "step_end_date": "2020-01-28",
                "continuation_positive": label == "pos",
                "continuation_negative": label == "neg",
                "continuation_neutral": label == "neutral",
                "target_binary": 1.0 if label == "pos" else 0.0 if label == "neg" else np.nan,
                "is_binary_target": label != "neutral",
                "model_id": r.PRIMARY_MODEL_ID,
                "score": score,
            }
        )
    return pd.DataFrame(rows)


def action_rows() -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            {"step_id": "a", "policy_id": "p", "cluster_split_bucket": "train", "episode_cluster_id": "c1", "continuation_positive": True, "continuation_negative": False, "continuation_neutral": False, "is_binary_target": True, "candidate_action": "defend_next_h20", "score": 0.1},
            {"step_id": "b", "policy_id": "p", "cluster_split_bucket": "train", "episode_cluster_id": "c2", "continuation_positive": True, "continuation_negative": False, "continuation_neutral": False, "is_binary_target": True, "candidate_action": "continue_next_h20", "score": 0.9},
            {"step_id": "c", "policy_id": "p", "cluster_split_bucket": "train", "episode_cluster_id": "c3", "continuation_positive": False, "continuation_negative": True, "continuation_neutral": False, "is_binary_target": True, "candidate_action": "defend_next_h20", "score": 0.2},
            {"step_id": "d", "policy_id": "p", "cluster_split_bucket": "train", "episode_cluster_id": "c4", "continuation_positive": False, "continuation_negative": True, "continuation_neutral": False, "is_binary_target": True, "candidate_action": "defend_next_h20", "score": 0.3},
            {"step_id": "e", "policy_id": "p", "cluster_split_bucket": "train", "episode_cluster_id": "c5", "continuation_positive": False, "continuation_negative": False, "continuation_neutral": True, "is_binary_target": False, "candidate_action": "defend_next_h20", "score": 0.4},
        ]
    )
    for col in ["known_failed_context_any", "late_rescue_context"]:
        frame[col] = False
    frame["non_known_failed_context"] = True
    frame["non_late_rescue_context"] = True
    return frame


def test_threshold_fit_population_is_train_binary_primary_model_rows():
    frame = scored_rows()
    fit = r.train_binary_primary_model_score_rows(frame)
    assert len(fit) == 4
    assert fit["cluster_split_bucket"].eq("train").all()
    assert not fit["continuation_neutral"].any()


def test_threshold_fit_excludes_neutral_rows_before_policy_freeze():
    frame = scored_rows()
    audit = r.build_policy_threshold_freeze_audit(frame, base_config())
    threshold = audit.loc[0, "threshold_value"]
    assert np.isclose(threshold, pd.Series([0.90, 0.80, 0.10, 0.20]).quantile(0.30))
    assert audit.loc[0, "neutral_rows_excluded_from_fit"]


def test_policy_action_tie_goes_to_defend():
    frame = scored_rows().head(1).copy()
    frame["score"] = 0.5
    thresholds = pd.DataFrame([{"policy_id": "p", "threshold_quantile": 0.30, "threshold_value": 0.5}])
    actions = r.apply_policy_actions(frame, thresholds)
    assert actions.loc[0, "candidate_action"] == "defend_next_h20"


def test_parquet_count_rows_uses_actual_row_count(tmp_path):
    path = tmp_path / "panel.parquet"
    pd.DataFrame({"x": [1, 2, 3]}).to_parquet(path, index=False)
    assert r.count_rows(path) == 3


def test_policy_confusion_formulae_exact():
    metrics = r.confusion_metrics(action_rows())
    assert metrics["binary_step_n"] == 4
    assert metrics["positive_n"] == 2
    assert metrics["negative_n"] == 2
    assert metrics["defended_binary_step_n"] == 3
    assert metrics["defended_negative_n"] == 2
    assert metrics["positive_sacrifice_rate"] == 0.5
    assert np.isclose(metrics["defense_precision"], 2 / 3)
    assert np.isclose(metrics["defense_precision_lift_vs_binary_negative_base"], 2 / 3 - 0.5)
    assert metrics["continue_negative_leakage_rate"] == 0.0


def test_neutral_rows_are_not_mapped_to_negative():
    audit = r.build_neutral_policy_handling_audit(action_rows(), {"policy": {"primary_policy_id": "p"}})
    assert audit.loc[0, "neutral_step_n"] == 1
    assert audit.loc[0, "neutral_mapped_to_negative_n"] == 0
    assert audit.loc[0, "neutral_handling_gate"] == "pass"


def test_policy_action_binding_rejects_duplicate_keys():
    panel = pd.concat([action_rows(), action_rows().head(1)], ignore_index=True)
    audit = r.build_policy_action_binding_audit(panel, {"policy": {"primary_policy_id": "p", "primary_label_id": r.PRIMARY_LABEL_ID, "selected_threshold_id": "up50pct", "primary_horizon_sessions": 20}})
    assert audit.loc[0, "policy_action_binding_gate"] == "fail"


def test_context_stratified_policy_requires_row_level_context_flags():
    panel = action_rows()
    readout = r.build_policy_context_stratified_readout(panel, {**base_config(), "policy": {"primary_policy_id": "p"}, "context_gates": base_config()["context_gates"]})
    row = readout.loc[readout["context_stratum"].eq("non_known_failed_context")].iloc[0]
    assert row["binary_step_n"] == 4
    assert row["context_independence_status"] == "pass"


def test_context_gate_blocks_context_concentrated_policy():
    cfg = base_config()
    panel = action_rows()
    panel["known_failed_context_any"] = True
    panel["non_known_failed_context"] = False
    readout = r.build_policy_context_stratified_readout(panel, {**cfg, "policy": {"primary_policy_id": "p"}})
    row = readout.loc[readout["context_stratum"].eq("non_known_failed_context")].iloc[0]
    assert row["binary_step_n"] == 0
    assert row["context_independence_status"] == "fail"


def test_score_orientation_gate_uses_auc_and_bottom30_defense_lift(tmp_path):
    frame = scored_rows().loc[lambda x: x["is_binary_target"]].copy()
    oos_rows = []
    for split, sub in frame.groupby("cluster_split_bucket"):
        metrics = r.r16c.metrics_for_scores(sub["target_binary"], sub["score"])
        oos_rows.append({"split_bucket": split, "model_id": r.PRIMARY_MODEL_ID, "binary_step_n": len(sub), "positive_n": int(sub["target_binary"].eq(1).sum()), "negative_n": int(sub["target_binary"].eq(0).sum()), **metrics})
    oos_path = tmp_path / "oos.csv"
    pd.DataFrame(oos_rows).to_csv(oos_path, index=False)
    contract_path = tmp_path / "contract.csv"
    pd.DataFrame({"feature_name": ["x"]}).to_csv(contract_path, index=False)
    cache_path = tmp_path / "score.parquet"
    frame[["step_id", "model_id", "score"]].to_parquet(cache_path, index=False)
    resolved = {
        "upstream_16c_oos_readout": oos_path,
        "upstream_16c_t0_feature_contract": contract_path,
        "upstream_16c_score_panel": cache_path,
    }
    cfg = base_config()
    thresholds = r.build_policy_threshold_freeze_audit(scored_rows(), cfg)
    actions = r.apply_policy_actions(scored_rows(), thresholds)
    confusion = r.build_policy_confusion_readout(actions)
    audit = r.build_score_rebuild_lineage_audit(scored_rows(), "hash", cfg, resolved, thresholds, confusion)
    assert audit.loc[0, "score_orientation_gate"] == "pass"
    assert audit.loc[0, "score_rebuild_lineage_gate"] == "pass"


def test_decision_map_lineage_failure():
    cfg = base_config()
    panel = pd.concat([action_rows().assign(policy_id="defense_bottom_30pct_continuation_score_v1", cluster_split_bucket="train"), action_rows().assign(policy_id="defense_bottom_30pct_continuation_score_v1", cluster_split_bucket="robustness")], ignore_index=True)
    confusion = r.build_policy_confusion_readout(panel)
    context = r.build_policy_context_stratified_readout(panel, cfg)
    gates = {
        "input_artifact_gate": "fail",
        "upstream_16c_authorization_gate": "pass",
        "upstream_16b_label_rebuild_gate": "pass",
        "score_rebuild_lineage_gate": "pass",
        "feature_contract_replay_gate": "pass",
        "score_orientation_gate": "pass",
        "threshold_freeze_gate": "pass",
        "neutral_handling_gate": "pass",
        "policy_action_binding_gate": "pass",
        "known_failed_context_rebuild_gate": "pass",
        "search_accounting_gate": "pass",
    }
    decision = r.build_decision(cfg, gates, confusion, context, panel, pd.DataFrame([{}]))
    assert decision.loc[0, "decision_state"] == r.DECISION_LINEAGE


def test_ready_decision_only_allows_16e_requirement():
    cfg = base_config()
    train = action_rows().assign(policy_id="defense_bottom_30pct_continuation_score_v1", cluster_split_bucket="train")
    rob = action_rows().assign(policy_id="defense_bottom_30pct_continuation_score_v1", cluster_split_bucket="robustness")
    panel = pd.concat([train, rob], ignore_index=True)
    confusion = r.build_policy_confusion_readout(panel)
    context = r.build_policy_context_stratified_readout(panel, cfg)
    gates = {name: "pass" for name in [
        "input_artifact_gate",
        "upstream_16c_authorization_gate",
        "upstream_16b_label_rebuild_gate",
        "score_rebuild_lineage_gate",
        "feature_contract_replay_gate",
        "score_orientation_gate",
        "threshold_freeze_gate",
        "neutral_handling_gate",
        "policy_action_binding_gate",
        "known_failed_context_rebuild_gate",
        "search_accounting_gate",
    ]}
    decision = r.build_decision(cfg, gates, confusion, context, panel, pd.DataFrame([{}]))
    assert decision.loc[0, "decision_state"] == r.DECISION_READY
    assert decision.loc[0, "next_allowed_requirement"] == "requirement_16e_sequential_continuation_utility_diagnostic.md"
    assert not decision.loc[0, "entry_policy_authorized"]
    assert not decision.loc[0, "return_backtest_authorized"]
