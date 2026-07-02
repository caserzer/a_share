from __future__ import annotations

import functools
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/18_payoff_state_representation_research"
SCRIPT = EXP / "src/run_18e_payoff_state_feature_matrix_refresh.py"
CONFIG = EXP / "configs/config_18e_payoff_state_feature_matrix_refresh.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_18e_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def context():
    return r.run(CONFIG, mode="full")


def load_config():
    with CONFIG.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_config_declares_single_money_flow_source_priority_and_windows():
    config = load_config()
    assert config["money_flow_proxy_params"]["amount_column_priority"] == ["money", "amount", "turnover_value", "volume_times_close"]
    assert config["money_flow_proxy_params"]["close_column_priority"] == ["close", "qfq_close"]
    assert config["expected"]["refresh_primary_raw_feature_n"] == 26
    assert "m2_money_flow_reversal_accel_5v20" in config["expected"]["primary_refresh_feature_ids"]


def test_runner_does_not_train_score_or_walk_arbitrary_sources():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "sklearn" not in source
    assert "def rank_ic" not in source
    assert "rank_ic(" not in source
    assert "fit(" not in source
    assert "predict(" not in source
    assert ".rglob(" not in source
    assert "os.walk" not in source


def test_check_inputs_records_required_sources_and_qfq_schema():
    result = r.run(CONFIG, mode="check-inputs")
    audit = result["input_artifact_audit"]
    assert result["input_artifact_gate"] == "pass"
    assert audit.loc[audit["artifact_key"].eq("stock_daily_qfq_dir"), "schema_status"].iloc[0] == "pass"
    assert audit.loc[audit["artifact_key"].eq("eighteen_b_matrix"), "observed_row_n"].iloc[0] == 23405


def test_full_run_emits_positive_18e_handoff_decision():
    result = context()
    decision = result["decision"].iloc[0]
    assert decision["decision_state"] == "18E_payoff_state_feature_matrix_refresh_supported"
    assert decision["next_allowed_requirement"] == "requirement_18c_payoff_state_separability_diagnostic.md"
    assert decision["next_allowed_requirement_scope"] == "refreshed_matrix_rerun"
    assert bool(decision["all_hard_gates_pass"])
    for gate, status in result["gates"].items():
        assert status == "pass", gate
    for col in r.AUTH_FALSE_COLUMNS:
        assert not bool(decision[col])


def test_candidate_replay_exactly_classifies_18d_universe_and_m2_uses_extended_control():
    replay = context()["replay"]
    assert len(replay) == 41
    assert replay["replay_status"].eq("pass").all()
    assert replay["expected_18e_role"].value_counts().to_dict() == {
        "primary_refresh": 26,
        "appendix_only": 14,
        "deferred": 1,
    }
    primary = replay.loc[replay["expected_18e_role"].eq("primary_refresh")]
    m2 = primary.loc[primary["candidate_family_id"].eq("M2")]
    assert not m2.empty
    assert set(m2["observed_residualization_control_set_id"]) == {r.M2_EXT_RESIDUALIZATION_ID}
    blocked = replay.set_index("candidate_feature_id")
    assert blocked.loc["m5_lifecycle_progress_to_t0", "observed_blocking_reason"] == "full_episode_boundary_after_t0"
    assert blocked.loc["m5_bars_since_reclaim", "observed_blocking_reason"] == "candidate_finite_rate_below_floor"


def test_refreshed_matrix_preserves_18b_rows_targets_and_adds_49_model_features():
    result = context()
    config = load_config()
    matrix = result["matrix"]
    schema = result["schema"]
    assert len(matrix) == 23405
    assert int(schema["primary_raw_feature"].sum()) == 49
    assert int(schema["primary_model_feature"].sum()) == 49
    assert set(config["target_columns"]).issubset(matrix.columns)
    assert matrix["label_class"].astype(str).eq("neutral").sum() == 6066
    assert result["binding"]["target_binding_gate"].iloc[0] == "pass"


def test_existing_18b_model_ready_columns_are_preserved_byte_for_byte():
    result = context()
    old = pd.read_parquet(EXP / "outputs/local_cache/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix.parquet")
    new = result["matrix"]
    for col in ["mr_ret_5d", "mr_turnover_rate_20d_zscore", "mr_volatility_20d", "mr_tradability_status_ok"]:
        pd.testing.assert_series_equal(old[col], new[col], check_names=False)


def test_refresh_features_clear_finite_rate_floor_without_row_drops():
    result = context()
    config = load_config()
    missing = result["missingness"]
    refresh_total = missing.loc[
        missing["split_bucket"].eq("total")
        & missing["feature_name"].isin(config["expected"]["primary_refresh_feature_ids"])
    ]
    assert len(refresh_total) == 26
    assert refresh_total["finite_rate"].min() >= 0.80
    assert result["row_complete"]["row_drop_used_to_improve_complete_rate"].eq(False).all()
    assert result["row_complete"]["neutral_rows_dropped"].eq(False).all()


def test_lineage_and_pit_audits_keep_primary_features_t0_available():
    result = context()
    config = load_config()
    lineage = result["lineage"]
    pit = result["pit"]
    refresh_lineage = lineage.loc[lineage["feature_id"].isin(config["expected"]["primary_refresh_feature_ids"])]
    assert len(refresh_lineage) == 26
    assert refresh_lineage["pit_valid_status"].eq("pass").all()
    assert refresh_lineage["t0_available_status"].eq("pass").all()
    assert refresh_lineage["source_pos_max_minus_step_start_pos"].le(0).all()
    assert not refresh_lineage["uses_future_h20_path"].astype(bool).any()
    assert not refresh_lineage["uses_step_end_outcome"].astype(bool).any()
    assert pit.loc[pit["feature_id"].isin(config["expected"]["primary_refresh_feature_ids"]), "candidate_appendix_only"].eq(False).all()


def test_train_only_preprocessing_covers_all_49_features_and_model_ready_is_finite():
    result = context()
    config = load_config()
    pre = result["preprocessing"]
    matrix = result["matrix"]
    assert len(pre) == 49
    assert set(pre["fit_split"]) == {"train"}
    assert not pre["preprocessing_uses_target_columns"].astype(bool).any()
    assert not pre["preprocessing_uses_robustness_rows"].astype(bool).any()
    assert not pre["preprocessing_uses_validation_rows"].astype(bool).any()
    assert not pre["split_local_imputation_used"].astype(bool).any()
    assert not pre["split_local_scaling_used"].astype(bool).any()
    model_ready = [r.model_ready_name(config, f) for f in r.primary_raw_features(config)]
    assert np.isfinite(matrix[model_ready].to_numpy(dtype=float)).all()


def test_formula_registry_and_money_flow_helpers_fix_reviewed_ambiguities():
    result = context()
    formula = result["formula"].set_index("feature_id")
    assert "reversal_rate(trailing_5" in formula.loc["m2_money_flow_reversal_accel_5v20", "formula_text"]
    assert "j=4..19" in formula.loc["m2_flow_price_divergence_persistence_20", "formula_text"]
    assert "mixed low/close drawdown proxy" in formula.loc["m1_episode_drawdown_pre_t0", "formula_text"]
    window = pd.DataFrame(
        {
            "close": [10.0, 11.0, 10.5, 10.7, 10.2],
            "amount_proxy": [100.0, 100.0, 100.0, 100.0, 100.0],
        }
    )
    stats = r.money_flow_stats(window, 1e-12, 5)
    assert np.isfinite(stats["reversal_rate"])
    assert stats["reversal_rate"] > 0


def test_source_audit_records_qfq_coverage_and_amount_proxy_source():
    source = context()["source_audit"]
    assert source["qfq_instrument_path_coverage_rate"].iloc[0] >= 0.95
    assert source["qfq_matrix_row_path_coverage_rate"].iloc[0] >= 0.95
    assert set(source["amount_proxy_source"]) == {"money"}
    assert source["refreshed_feature_source_gate"].eq("pass").all()


def test_forbidden_feature_and_search_accounting_boundaries_hold():
    result = context()
    schema = result["schema"].set_index("column_name")
    assert schema.loc["label_class", "target_column"]
    assert schema.loc["label_class", "forbidden_as_model_feature"]
    assert not schema.loc["label_class", "primary_model_feature"]
    assert result["forbidden"]["forbidden_feature_gate"].eq("pass").all()
    search = result["search"].iloc[0]
    assert search["search_accounting_gate"] == "pass"
    assert bool(search["no_model_training"])
    assert bool(search["no_scoring"])
    assert bool(search["delayed_features_not_primary"])
    assert bool(search["m4_not_primary"])
