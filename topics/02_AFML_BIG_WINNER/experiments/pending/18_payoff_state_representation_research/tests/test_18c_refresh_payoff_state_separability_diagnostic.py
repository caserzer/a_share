from __future__ import annotations

import functools
import importlib.util
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/18_payoff_state_representation_research"
SCRIPT = EXP / "src/run_18c_refresh_payoff_state_separability_diagnostic.py"
CONFIG = EXP / "configs/config_18c_refresh_payoff_state_separability_diagnostic.yaml"
REQ = EXP / "requirement_18c_refresh_payoff_state_separability_diagnostic.md"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_18c_refresh_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def context():
    return r.run(CONFIG, mode="full")


def test_18c_refresh_fails_closed_when_18e_local_cache_matrix_is_missing():
    result = context()
    decision = result["decision"].iloc[0]
    input_audit = result["input_artifact_audit"]

    matrix_row = input_audit.loc[input_audit["artifact_key"].eq("eighteen_e_refreshed_matrix")].iloc[0]
    if matrix_row["read_status"] == "missing":
        assert decision["decision_state"] == "18C_refresh_upstream_18e_contract_blocked"
        assert decision["next_allowed_requirement"] == "none"
        assert "missing_local_cache_refreshed_matrix" in matrix_row["blocking_reason"]
        assert "rerun_18e_full_to_regenerate" in matrix_row["blocking_reason"]
    else:
        assert matrix_row["cache_hash_validated"] == "exact_match"

    for col in r.AUTH_FALSE_COLUMNS:
        assert bool(decision[col]) is False


def test_18c_refresh_uses_distinct_output_namespace_and_does_not_overwrite_initial_18c():
    context()
    outputs = r.output_paths()
    assert "18C_refresh_payoff_state_separability_diagnostic" in str(outputs["decision"])
    assert outputs["report"].name == "payoff_state_separability_refresh_report.md"
    assert outputs["manifest"].name == "18C_refresh_payoff_state_separability_diagnostic_manifest.json"
    assert outputs["decision"].exists()
    assert outputs["input_artifact_audit"].exists()
    assert outputs["upstream_18e_handoff_audit"].exists()
    assert outputs["decile_curve"].stat().st_size > 0
    assert outputs["score_surface"].stat().st_size > 0


def test_18c_refresh_family_removal_sensitivity_schema_is_explicit():
    result = context()
    family = result["family_removal_sensitivity"]
    required = {
        "sensitivity_id",
        "split_bucket",
        "model_id",
        "removal_type",
        "removed_feature_family_id",
        "removed_feature_n",
        "removed_feature_names",
        "base_rank_ic_spearman",
        "sensitivity_rank_ic_spearman",
        "rank_ic_retention_rate",
        "family_role",
        "refresh_family_flag",
        "risk_only_focus_flag",
        "sensitivity_status",
        "blocking_reason",
    }
    assert required.issubset(set(family.columns))

    requirement_text = REQ.read_text(encoding="utf-8")
    assert "### 9.2 `family_removal_sensitivity.csv`" in requirement_text
    assert "family_M1_removed" in requirement_text
    assert "family_M5_removed" in requirement_text


def test_18c_refresh_uses_actual_18e_handoff_schemas_not_old_aliases():
    config = r.load_config(CONFIG)
    lineage = r.required_columns_for_key(config, "eighteen_e_lineage_audit")
    binding = r.required_columns_for_key(config, "eighteen_e_target_binding_audit")
    pit = r.required_columns_for_key(config, "eighteen_e_pit_availability_audit")
    assert {"candidate_family_id", "candidate_feature_id", "lineage_before_correlation_gate"}.issubset(lineage)
    assert {"refreshed_matrix_row_n", "refreshed_identity_key_n", "target_binding_gate"}.issubset(binding)
    assert {"candidate_family_id", "candidate_feature_id", "t0_available_status"}.issubset(pit)
    assert "feature_lineage_gate" not in lineage
    assert "bound_matrix_row_n" not in binding
    assert "pit_t0_availability_gate" not in pit


def test_18c_refresh_score_panel_and_search_accounting_contracts_are_explicit():
    result = context()
    outputs = r.output_paths()
    score = pd.read_parquet(outputs["score_panel"])
    assert set(r.SCORE_PANEL_COLUMNS).issubset(set(score.columns))
    assert "run_id" in result["search_accounting"].columns
    assert "scope_id" in result["search_accounting"].columns
    assert result["search_accounting"].iloc[0]["run_id"] == r.RUN_ID
    assert result["search_accounting"].iloc[0]["scope_id"] == "refreshed_matrix_rerun"


def test_18c_refresh_positive_decision_routes_to_18f_when_all_gates_pass():
    config = r.prepared_model_config(r.load_config(CONFIG), r.resolve_paths(r.load_config(CONFIG)))
    gates = {gate: "pass" for gate in r.HARD_GATES}
    oos = pd.DataFrame(
        [
            {
                "split_bucket": "robustness",
                "model_id": r.PRIMARY_MODEL_ID,
                "row_n": 2496,
                "episode_cluster_n": 204,
                "rank_ic_spearman": 0.10,
                "continue_advantage_replay_abs_diff": 0.0,
            },
            {
                "split_bucket": "validation",
                "model_id": r.PRIMARY_MODEL_ID,
                "row_n": 664,
                "episode_cluster_n": 41,
                "rank_ic_spearman": 0.09,
                "continue_advantage_replay_abs_diff": 0.0,
            },
        ]
    )
    deciles = pd.DataFrame(
        [
            {
                "split_bucket": "robustness",
                "model_id": r.PRIMARY_MODEL_ID,
                "decile_payoff_monotonicity_spearman": 0.70,
                "top3_minus_bottom3_payoff_gap": 0.01,
            }
        ]
    )
    bucket = pd.DataFrame([{"split_bucket": "robustness", "bucket_lift": 1.1}])
    bootstrap = pd.DataFrame([{"cluster_bootstrap_rank_ic_ci_low": 0.01}])
    baseline = pd.DataFrame([{"comparison_id": "payoff_rank_ic_vs_volatility20d", "delta_vs_baseline": 0.006}])
    family = pd.DataFrame([{"split_bucket": "robustness", "sensitivity_id": "family_F4_removed", "rank_ic_retention_rate": 0.7}])
    binary = pd.DataFrame([{"split_bucket": "robustness", "roc_auc": 0.50, "precision_lift": 0.0}])
    decision = r.build_refreshed_decision(config, gates, oos, deciles, bucket, bootstrap, baseline, family, binary, "scored").iloc[0]
    assert decision["decision_state"] == "18C_payoff_state_separability_supported"
    assert decision["next_allowed_requirement"] == "requirement_18f_payoff_state_oracle_gap_bridge.md"
    assert decision["next_allowed_requirement_scope"] == "refreshed_matrix_oracle_gap_bridge"
