from __future__ import annotations

import functools
import importlib.util
import json
import math
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/18_payoff_state_representation_research"
SCRIPT = EXP / "src/run_18c_payoff_state_separability_diagnostic.py"
CONFIG = EXP / "configs/config_18c_payoff_state_separability_diagnostic.yaml"

REQUIRED_SCHEMAS = {
    "matrix_contract": {
        "check_id",
        "expected_value",
        "observed_value",
        "matrix_contract_replay_gate",
        "blocking_reason",
    },
    "registry": {
        "model_id",
        "model_family",
        "model_role",
        "target_column",
        "feature_column_n",
        "fit_split",
        "hyperparameters",
        "used_for_primary_decision",
        "binary_metric_used_as_primary_gate",
        "training_uses_robustness_rows",
        "training_uses_validation_rows",
        "model_registry_gate",
        "blocking_reason",
    },
    "coefficients": {
        "model_id",
        "feature_name",
        "feature_family_id",
        "coefficient",
        "feature_train_std",
        "standardized_coefficient",
        "abs_coefficient_rank",
        "standardized_abs_coefficient_rank",
        "train_fit_row_n",
        "coefficient_source",
    },
    "oos": {
        "split_bucket",
        "model_id",
        "target_id",
        "row_n",
        "episode_cluster_n",
        "rank_ic_spearman",
        "continue_advantage_rank_ic_spearman",
        "continue_advantage_replay_abs_diff",
        "coarse_rank_ic_vs_16x_external_delta",
        "rank_ic_status",
    },
    "baseline": {
        "comparison_id",
        "split_bucket",
        "model_id",
        "baseline_id",
        "metric_id",
        "model_denominator_type",
        "baseline_denominator_type",
        "baseline_role",
        "model_value",
        "baseline_value",
        "delta_vs_baseline",
        "required_delta",
        "hard_gate_used",
        "comparison_status",
    },
    "binary": {
        "split_bucket",
        "model_id",
        "target_column",
        "denominator_type",
        "row_n",
        "positive_n",
        "negative_n",
        "neutral_n",
        "roc_auc",
        "average_precision",
        "split_unconditional_positive_rate",
        "precision_lift",
        "binary_metric_used_as_primary_gate",
        "binary_sanity_status",
    },
}


def load_runner():
    spec = importlib.util.spec_from_file_location("run_18c_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def context():
    return r.run(CONFIG, mode="full")


def test_18c_publishable_tables_include_requirement_minimum_schemas():
    result = context()
    for table_name, required_columns in REQUIRED_SCHEMAS.items():
        assert required_columns.issubset(set(result[table_name].columns)), table_name


def test_18c_input_handoff_and_matrix_contract_replay_pass_with_explicit_identity_keys():
    result = context()
    input_audit = result["input_artifact_audit"]
    assert result["input_artifact_gate"] == "pass"
    assert input_audit["read_status"].eq("pass").all()
    assert input_audit["schema_status"].eq("pass").all()
    assert input_audit["cache_key_reconciliation_gate"].eq("pass").all()

    xref = input_audit.loc[input_audit["artifact_key"].eq("sixteen_x_reference_values")].iloc[0]
    assert xref["artifact_role"] == "sixteen_x_external_context_integrity"
    assert xref["cache_hash_validated"] == "exact_match"
    assert xref["cache_key_reconciliation_gate"] == "pass"

    upstream = result["upstream"]
    assert upstream["upstream_18b_contract_gate"].eq("pass").all()

    contract = result["matrix_contract"]
    assert contract["matrix_contract_replay_gate"].eq("pass").all()
    observed = dict(zip(contract["check_id"], contract["observed_value"], strict=False))
    assert int(observed["matrix_row_n"]) == 23405
    assert int(observed["train_row_n"]) == 20245
    assert int(observed["robustness_row_n"]) == 2496
    assert int(observed["validation_row_n"]) == 664
    assert observed["identity_key_columns"] == "step_id|label_id"
    assert int(observed["identity_key_duplicate_n"]) == 0
    assert observed["full_lineage_key_columns"] == (
        "step_id|label_id|threshold_id|horizon_sessions|instrument|"
        "episode_cluster_id|step_index|step_start_date|step_end_date"
    )
    assert int(observed["full_lineage_key_duplicate_n"]) == 0
    assert observed["target_lineage_hash_y_payoff_h20"] == "602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3"
    assert observed["target_lineage_hash_continue_advantage"] == "602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3"
    assert observed["target_lineage_hash_payoff_ordinal_state"] == "602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3"
    assert observed["target_lineage_gate_y_payoff_h20"] == "pass"
    assert observed["target_denominator_reconciliation_gate"] == "pass|pass|pass"
    assert observed["target_denominator_labelable_replay"] == "train:20245|robustness:2496|validation:664"
    assert observed["target_denominator_neutral_replay"] == "train:5283|robustness:624|validation:159"
    assert observed["neutral_preservation_gate"] == "pass|pass|pass"
    assert bool(observed["neutral_reclassified_as_positive_or_negative"]) is False
    assert float(observed["continue_advantage_affine_replay_max_abs_diff"]) <= 1e-12
    cutoff_replay = observed["train_frozen_payoff_cutoff_value_replay"]
    assert abs(cutoff_replay["high_upside_top30_stress"] - 0.0596330275229357) <= 1e-12
    assert abs(cutoff_replay["high_upside_top20_stress"] - 0.1012285086722715) <= 1e-12
    assert abs(cutoff_replay["high_upside_top10_stress"] - 0.1721071844362347) <= 1e-12
    assert observed["train_frozen_payoff_cutoff_lineage_hash"] == "602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3"
    assert bool(observed["split_local_payoff_cutoff_recompute_used"]) is False
    assert observed["train_frozen_payoff_cutoff_gate"] == "pass|pass|pass"

    matrix = result["matrix"]
    mapping = r.load_config(CONFIG)["ordinal_mapping"]
    assert sorted(matrix["payoff_ordinal_state_int"].dropna().unique().tolist()) == [0, 1, 2, 3]
    assert set(matrix["payoff_ordinal_state"].unique()) == set(mapping)


def test_18c_model_registry_and_standardized_coefficient_removal_are_predeclared():
    result = context()
    registry = result["registry"]
    assert int(registry["used_for_primary_decision"].sum()) == 1
    primary = registry.loc[registry["used_for_primary_decision"].astype(bool)].iloc[0]
    assert primary["model_id"] == "ridge_payoff_rank_h20_v1"
    assert primary["fit_split"] == "train"
    assert int(primary["feature_column_n"]) == 23
    assert not registry["training_uses_robustness_rows"].astype(bool).any()
    assert not registry["training_uses_validation_rows"].astype(bool).any()

    x16 = registry.loc[registry["model_id"].eq("16x_payoff_rank_probe_v1")].iloc[0]
    assert x16["model_role"] == "external_coarse_context_only"
    assert x16["fit_split"] == "external"
    assert bool(x16["used_for_primary_decision"]) is False

    coefficients = result["coefficients"]
    primary_coef = coefficients.loc[coefficients["model_id"].eq("ridge_payoff_rank_h20_v1")].copy()
    assert len(primary_coef) == 23
    assert sorted(primary_coef["standardized_abs_coefficient_rank"].tolist()) == list(range(1, 24))
    recomputed = primary_coef["coefficient"] * primary_coef["feature_train_std"]
    assert (recomputed - primary_coef["standardized_coefficient"]).abs().max() <= 1e-12

    ordered = primary_coef.sort_values("standardized_abs_coefficient_rank")["feature_name"].tolist()
    sensitivity = result["sensitivity"]
    for k in (1, 3, 5):
        row = sensitivity.loc[
            sensitivity["split_bucket"].eq("robustness")
            & sensitivity["sensitivity_id"].eq(f"top{k}_abs_coefficient_removed")
        ].iloc[0]
        assert row["removed_feature_names"].split("|") == ordered[:k]


def test_18c_primary_metrics_fail_closed_on_rank_and_same_denominator_baseline():
    result = context()
    oos = result["oos"]
    primary = oos.loc[oos["model_id"].eq("ridge_payoff_rank_h20_v1") & oos["split_bucket"].eq("robustness")].iloc[0]
    assert int(primary["row_n"]) == 2496
    assert int(primary["episode_cluster_n"]) == 204
    assert math.isclose(float(primary["rank_ic_spearman"]), 0.06439789586667599, rel_tol=0.0, abs_tol=1e-12)
    assert float(primary["continue_advantage_replay_abs_diff"]) <= 1e-12
    assert primary["rank_ic_status"] == "fail"

    deciles = result["deciles"]
    mono = deciles.loc[deciles["model_id"].eq("ridge_payoff_rank_h20_v1") & deciles["split_bucket"].eq("robustness")].iloc[0]
    assert float(mono["decile_payoff_monotonicity_spearman"]) >= 0.60
    assert float(mono["top3_minus_bottom3_payoff_gap"]) > 0
    assert bool(mono["split_local_score_cutoff_recompute_used"]) is False

    bucket = result["bucket"].loc[result["bucket"]["split_bucket"].eq("robustness")]
    assert (bucket["bucket_lift"] > 1.0).all()
    assert not bucket["split_local_score_cutoff_recompute_used"].astype(bool).any()

    bootstrap = result["bootstrap"].iloc[0]
    assert int(bootstrap["valid_bootstrap_resample_n"]) == 2000
    assert float(bootstrap["cluster_bootstrap_rank_ic_ci_low"]) > 0

    decision = result["decision"].iloc[0]
    assert decision["decision_state"] == "18C_payoff_state_signal_weak_or_nonmonotone"
    assert decision["next_allowed_requirement"] == "none"
    assert bool(decision["all_hard_gates_pass"]) is False
    assert decision["rank_ic_support_gate"] == "fail"
    assert decision["baseline_improvement_gate"] == "fail"
    assert decision["monotonicity_support_gate"] == "pass"
    assert decision["bucket_lift_gate"] == "pass"
    assert decision["bootstrap_ci_gate"] == "pass"
    assert decision["risk_only_gate"] == "pass"


def test_18c_16x_is_external_context_only_not_baseline_gate():
    result = context()
    baseline = result["baseline"]
    vol = baseline.loc[baseline["comparison_id"].eq("payoff_rank_ic_vs_volatility20d")].iloc[0]
    assert bool(vol["hard_gate_used"]) is True
    assert vol["baseline_denominator_type"] == "labelable_full"
    assert float(vol["delta_vs_baseline"]) < float(vol["required_delta"])
    assert vol["comparison_status"] == "diagnostic_only"

    x16 = baseline.loc[baseline["baseline_id"].eq("16x_payoff_rank_probe_v1")]
    assert len(x16) == 3
    assert x16["baseline_role"].eq("external_coarse_context_only").all()
    assert x16["model_denominator_type"].eq("labelable_full").all()
    assert x16["baseline_denominator_type"].eq("winner_episode_probe_rows_only").all()
    assert not x16["hard_gate_used"].astype(bool).any()
    assert x16["comparison_status"].eq("external_context_only").all()


def test_18c_binary_sanity_search_accounting_and_report_boundaries():
    result = context()
    binary = result["binary"]
    assert not binary["binary_metric_used_as_primary_gate"].astype(bool).any()
    x16c = binary.loc[binary["model_id"].eq("16c_ridge_logistic_bar_state_v1")]
    assert len(x16c) == 3
    assert x16c["denominator_type"].eq("binary_primary").all()
    assert x16c["binary_sanity_status"].eq("external_16c_appendix_only").all()

    search = result["search"].iloc[0]
    assert search["search_accounting_gate"] == "pass"
    for col in [
        "no_feature_selection_from_target_correlation",
        "no_feature_selection_from_robustness",
        "no_feature_selection_from_validation",
        "no_model_family_selection_from_robustness",
        "no_model_family_selection_from_validation",
        "no_threshold_tuning_on_robustness",
        "no_threshold_tuning_on_validation",
        "no_split_local_payoff_cutoff_recompute",
        "no_split_local_score_threshold_recompute_for_gate",
        "binary_metric_not_primary_gate",
        "validation_stress_readout_only",
    ]:
        assert bool(search[col]) is True

    cfg = r.load_config(CONFIG)
    assert cfg["expected"]["binary_blocked_classification_min_roc_auc"] == 0.55
    assert cfg["expected"]["binary_blocked_classification_min_precision_lift"] == 0.02

    decision = result["decision"].iloc[0]
    for col in r.AUTH_FALSE_COLUMNS:
        assert bool(decision[col]) is False

    report = (EXP / "outputs/publishable/reports/payoff_state_separability_diagnostic_report.md").read_text(encoding="utf-8")
    assert "16C binary continuation results are appendix-only and are not primary payoff-state gates." in report
    assert "continue_advantage is an affine replay of y_payoff_h20 and is not independent evidence." in report
    assert "Only 18C_payoff_state_separability_supported may authorize 18D." in report
    assert "step_id\\|label_id\\|threshold_id" in report


def test_18c_manifests_hashes_figures_and_score_panel_are_synced():
    context()
    outputs = r.output_paths()
    manifest = json.loads(outputs["manifest"].read_text(encoding="utf-8"))
    score_manifest = json.loads(outputs["score_panel_manifest"].read_text(encoding="utf-8"))

    assert manifest["decision_state"] == "18C_payoff_state_signal_weak_or_nonmonotone"
    assert manifest["next_allowed_requirement"] == "none"
    assert manifest["all_hard_gates_pass"] is False
    assert manifest["report_sha256"] == r.file_sha(outputs["report"])
    assert manifest["score_panel_sha256"] == r.file_sha(outputs["score_panel"])
    assert manifest["publishable_table_sha256_by_name"]["decision"] == r.file_sha(outputs["decision"])
    for col in r.AUTH_FALSE_COLUMNS:
        assert manifest[col] is False

    score = pd.read_parquet(outputs["score_panel"])
    assert len(score) == 23405
    assert score_manifest["row_count"] == 23405
    assert score_manifest["split_counts"] == {"robustness": 2496, "train": 20245, "validation": 664}
    assert score_manifest["identity_key_columns"] == ["step_id", "label_id"]
    assert "score_ridge_payoff_rank_h20_v1" in score_manifest["score_columns"]
    for figure_key in ("decile_curve", "score_surface"):
        assert outputs[figure_key].exists()
        assert outputs[figure_key].stat().st_size > 0
