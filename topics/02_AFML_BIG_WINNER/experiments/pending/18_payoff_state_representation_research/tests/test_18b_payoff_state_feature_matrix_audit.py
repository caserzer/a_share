from __future__ import annotations

import functools
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/18_payoff_state_representation_research"
SCRIPT = EXP / "src/run_18b_payoff_state_feature_matrix_audit.py"
CONFIG = EXP / "configs/config_18b_payoff_state_feature_matrix_audit.yaml"

REQUIRED_SCHEMAS = {
    "feature_family_coverage": {
        "feature_family_id",
        "feature_family_name",
        "expected_feature_n",
        "observed_raw_feature_n",
        "observed_model_ready_feature_n",
        "pit_available_status",
        "t0_available_status",
        "primary_allowed",
        "feature_family_coverage_gate",
        "blocking_reason",
    },
    "train_only_preprocessing_audit": {
        "feature_name",
        "feature_family_id",
        "preprocessing_id",
        "fit_split",
        "fit_row_n",
        "imputer",
        "train_median",
        "train_iqr",
        "scale_value",
        "zero_iqr_flag",
        "preprocessing_uses_target_columns",
        "preprocessing_uses_robustness_rows",
        "preprocessing_uses_validation_rows",
        "split_local_imputation_used",
        "split_local_scaling_used",
        "train_only_preprocessing_gate",
        "blocking_reason",
    },
    "split_drift_feature_readout": {
        "feature_name",
        "feature_family_id",
        "comparison_split",
        "train_mean",
        "comparison_mean",
        "standardized_mean_diff",
        "train_missing_rate",
        "comparison_missing_rate",
        "missing_rate_diff",
        "split_drift_flag",
        "split_drift_readout_gate",
        "notes",
    },
    "forbidden_feature_audit": {
        "forbidden_column_family",
        "forbidden_column_pattern",
        "column_name",
        "present_in_matrix",
        "marked_model_ready_feature",
        "forbidden_feature_gate",
        "blocking_reason",
    },
    "search_accounting_audit": {
        "search_family",
        "phase_id",
        "no_model_training",
        "no_model_refit",
        "no_feature_selection",
        "no_target_correlation_feature_selection",
        "no_robustness_feature_selection",
        "no_validation_feature_selection",
        "no_separability_metric_computed",
        "no_rank_ic_computed",
        "no_binary_metric_used_as_primary_gate",
        "no_entry_policy_authorized",
        "no_exit_policy_authorized",
        "no_holding_policy_authorized",
        "no_portfolio_backtest_authorized",
        "no_model_deployment_authorized",
        "no_production_signal_authorized",
        "no_live_trading_authorized",
        "delayed_features_used_in_primary_model",
        "search_accounting_gate",
        "blocking_reason",
    },
}


def load_runner():
    spec = importlib.util.spec_from_file_location("run_18b_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def context():
    return r.run(CONFIG, mode="full")


def test_18b_input_audit_validates_local_cache_and_target_source():
    result = context()
    input_audit = result["input_artifact_audit"]
    primary = input_audit.loc[input_audit["artifact_role"].eq("primary_row_level_feature_source")]
    assert len(primary) == 1
    row = primary.iloc[0]
    assert row["source_kind"] == "validated_local_cache"
    assert row["cache_hash_manifest_status"] in {"exact_match", "not_available_nonblocking"}
    assert row["cache_schema_validated"] is True
    assert row["cache_key_reconciliation_gate"] == "pass"
    assert int(row["observed_feature_row_n"]) == 23405
    assert int(row["observed_matrix_identity_key_n"]) == 23405

    target = input_audit.loc[input_audit["artifact_role"].eq("primary_row_level_target_source")].iloc[0]
    assert target["cache_key_reconciliation_gate"] == "pass"
    assert int(target["observed_matrix_identity_key_n"]) == 23405
    assert r.input_artifact_gate(input_audit) == "pass"


def test_18b_target_binding_uses_identity_key_not_split_join():
    result = context()
    binding = result["feature_target_binding_audit"].iloc[0]
    assert int(binding["feature_row_n"]) == 23405
    assert int(binding["target_filter_row_n"]) == 23405
    assert int(binding["bound_matrix_row_n"]) == 23405
    assert bool(binding["identity_key_join_used"]) is True
    assert bool(binding["split_join_key_used"]) is False
    assert int(binding["split_mismatch_n"]) == 0
    assert int(binding["feature_missing_split_n"]) == 0
    assert int(binding["target_missing_split_n"]) == 0
    assert bool(binding["split_counts_match_18a"]) is True
    assert binding["split_allowed_values_gate"] == "pass"
    assert int(binding["neutral_step_n_robustness"]) == 624
    assert binding["feature_target_binding_gate"] == "pass"


def test_18b_publishable_tables_include_requirement_minimum_schemas():
    result = context()
    for table_name, required_columns in REQUIRED_SCHEMAS.items():
        observed = set(result[table_name].columns)
        assert required_columns.issubset(observed), table_name


def test_18b_matrix_schema_has_exact_primary_feature_contract():
    result = context()
    schema = result["schema"]
    matrix = result["matrix"]
    features = r.primary_features(r.load_config(CONFIG))
    model_ready = [r.model_ready_name(r.load_config(CONFIG), feature) for feature in features]

    assert len(matrix) == 23405
    assert matrix.shape[1] == 75
    assert set(schema.loc[schema["raw_feature"], "column_name"]) == set(features)
    assert set(schema.loc[schema["model_ready_feature"], "column_name"]) == set(model_ready)
    assert int(schema["raw_feature"].sum()) == 23
    assert int(schema["model_ready_feature"].sum()) == 23
    assert schema["feature_matrix_schema_gate"].eq("pass").all()
    assert not schema.loc[
        schema["column_role"].isin(["row_key", "split_metadata", "target", "diagnostic_metadata"]),
        "model_ready_feature",
    ].any()


def test_18b_missingness_and_row_completeness_pass_without_row_drops():
    result = context()
    missingness = result["feature_missingness_audit"]
    complete = result["matrix_row_completeness_audit"]
    assert len(missingness) == 23 * 3
    assert missingness["feature_complete_rate_gate"].eq("pass").all()
    assert missingness["finite_rate"].min() >= 0.99
    total = complete.loc[complete["split_bucket"].eq("total")].iloc[0]
    assert int(total["row_complete_n"]) == 23405
    assert float(total["matrix_row_complete_rate"]) >= 0.99
    assert not complete["row_drop_used_to_improve_complete_rate"].any()


def test_18b_preprocessing_is_train_only_and_keeps_binary_no_scale():
    result = context()
    preprocessing = result["train_only_preprocessing_audit"]
    assert len(preprocessing) == 23
    assert preprocessing["train_only_preprocessing_gate"].eq("pass").all()
    assert preprocessing["fit_split"].eq("train").all()
    assert preprocessing["fit_row_n"].eq(20245).all()
    assert not preprocessing["preprocessing_uses_target_columns"].any()
    assert not preprocessing["preprocessing_uses_robustness_rows"].any()
    assert not preprocessing["preprocessing_uses_validation_rows"].any()

    binary = preprocessing.loc[preprocessing["feature_name"].isin(["board_bucket_chinext", "board_bucket_main_board", "tradability_status_ok"])]
    assert binary["center"].eq(0.0).all()
    assert binary["scale"].eq(1.0).all()
    assert binary["scale_value"].eq(1.0).all()
    assert preprocessing["train_median"].notna().all()
    assert preprocessing["train_iqr"].notna().all()


def test_18b_lineage_covers_inventory_approved_pit_context_aliases():
    result = context()
    lineage = result["feature_lineage_audit"]
    assert len(lineage) == 23
    assert lineage["feature_lineage_gate"].eq("pass").all()
    assert (lineage["max_source_pos_minus_step_start_pos"] <= 0).all()
    assert (lineage["max_source_date_minus_step_start_date"] <= 0).all()
    board_rank = lineage.loc[lineage["feature_name"].eq("board_rank_by_market_cap")].iloc[0]
    tradability = lineage.loc[lineage["feature_name"].eq("tradability_status_ok")].iloc[0]
    assert board_rank["source_artifact"] == "pit_topn_400_100_executable_daily"
    assert tradability["source_artifact"] == "pit_topn_400_100_executable_daily"
    assert board_rank["source_lineage_status_16c"] == "pass"
    assert tradability["source_leakage_status_16c"] == "pass"


def test_18b_decision_ready_and_no_policy_or_model_authorization():
    result = context()
    decision = result["decision"].iloc[0]
    assert decision["decision_state"] == "18B_payoff_state_feature_matrix_ready"
    assert decision["next_allowed_requirement"] == "requirement_18c_payoff_state_separability_diagnostic.md"
    for gate in r.HARD_GATES:
        assert decision[gate] == "pass"
    for col in r.AUTH_FALSE_COLUMNS:
        assert bool(decision[col]) is False

    search = result["search_accounting_audit"].iloc[0]
    assert bool(search["no_model_training"]) is True
    assert bool(search["no_target_correlation_feature_selection"]) is True
    assert bool(search["no_robustness_feature_selection"]) is True
    assert bool(search["no_validation_feature_selection"]) is True
    assert bool(search["no_separability_metric_computed"]) is True
    assert bool(search["no_binary_metric_used_as_primary_gate"]) is True
    assert bool(search["no_policy_utility_computed"]) is True


def test_18b_manifest_hashes_are_synced_with_outputs():
    context()
    manifest_path = EXP / "outputs/manifests/18B_payoff_state_feature_matrix_audit_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    decision_path = EXP / "outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_decision.csv"
    report_path = EXP / "outputs/publishable/reports/payoff_state_feature_matrix_audit_report.md"
    matrix_path = EXP / "outputs/local_cache/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix.parquet"
    assert manifest["decision_state"] == "18B_payoff_state_feature_matrix_ready"
    assert manifest["next_allowed_requirement"] == "requirement_18c_payoff_state_separability_diagnostic.md"
    assert manifest["row_counts"]["matrix"] == 23405
    assert manifest["output_hashes"]["decision"] == r.file_sha(decision_path)
    assert manifest["output_hashes"]["report"] == r.file_sha(report_path)
    assert manifest["output_hashes"]["matrix"] == r.file_sha(matrix_path)

    matrix_manifest = json.loads((EXP / "outputs/manifests/payoff_state_feature_matrix_manifest.json").read_text(encoding="utf-8"))
    assert matrix_manifest["matrix_row_n"] == 23405
    assert len(matrix_manifest["primary_raw_features"]) == 23
    assert len(matrix_manifest["primary_model_ready_features"]) == 23
