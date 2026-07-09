from __future__ import annotations

import functools
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight"
SCRIPT = EXP / "src/run_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.py"
CONFIG = EXP / "configs/config_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_19b2_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def run_outputs():
    return r.run(CONFIG)


def read_output(key: str) -> pd.DataFrame:
    return pd.read_csv(run_outputs()[key])


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "pass"})


def test_19b2_inputs_and_upstream_hashes_are_closed():
    outputs = run_outputs()
    for key in r.REQUIRED_OUTPUT_KEYS:
        assert key in outputs
        assert outputs[key].exists()
        assert outputs[key].stat().st_size > 0

    input_audit = read_output("input_artifact_audit")
    assert set(input_audit["artifact_id"]) == set(r.REQUIRED_INPUT_KEYS)
    assert input_audit["input_artifact_gate"].eq("pass").all()
    verified_inputs = input_audit.loc[input_audit["expected_hash"].fillna("").ne("")]
    assert bool_series(verified_inputs["hash_verified"]).all()

    upstream = read_output("upstream_contract_audit")
    assert upstream["contract_gate"].eq("pass").all()
    paths = r.resolve_input_paths(r.load_config(CONFIG))
    with paths["nineteen_b_output_hashes"].open("r", encoding="utf-8") as handle:
        b_hashes = json.load(handle)
    with paths["nineteen_b1_output_hashes"].open("r", encoding="utf-8") as handle:
        b1_hashes = json.load(handle)
    assert set(b_hashes) == set(r.UPSTREAM_HASH_PATH_MAPS["19B"])
    assert set(b1_hashes) == set(r.UPSTREAM_HASH_PATH_MAPS["19B1"])
    assert len(upstream.loc[upstream["upstream_scope"].eq("19B_hash")]) == len(b_hashes)
    assert len(upstream.loc[upstream["upstream_scope"].eq("19B1_hash")]) == len(b1_hashes)
    required_facts = {
        "robustness_candidate_manifest_gate",
        "outcome_boundary_gate",
        "robustness_candidate_manifest_frozen_before_label_readout",
        "label_read_before_manifest_freeze",
        "max_ep19_terminal_state_if_no_residual_pass",
        "primary_feature_separability_gate",
        "stability_gate",
        "max_ep19_terminal_state",
    }
    assert required_facts.issubset(set(upstream["required_fact"]))


def test_19b2_primary_scope_and_outcome_groups_match_19b1():
    join = read_output("primary_row_join_audit").iloc[0]
    assert join["primary_row_join_gate"] == "pass"
    assert int(join["expected_candidate_n_from_19b_metric"]) == 1552
    assert int(join["observed_candidate_n_from_mfe_mae_joint"]) == 1552
    assert int(join["observed_candidate_n_after_manifest_join"]) == 1552
    assert int(join["duplicate_join_key_n"]) == 0
    assert int(join["missing_in_candidate_manifest_n"]) == 0

    decision = read_output("entry_universe_19b2_decision").iloc[0]
    assert int(decision["candidate_n"]) == 1552
    assert int(decision["instrument_n"]) == 524
    assert int(decision["right_clean_n"]) == 290
    assert int(decision["left_bad_n"]) == 614
    assert int(decision["both_n"]) == 145
    assert int(decision["neither_n"]) == 503

    score = read_output("b2_suppressor_score_panel")
    assert score["outcome_group"].value_counts().to_dict() == {
        "left_bad": 614,
        "neither": 503,
        "right_clean": 290,
        "both": 145,
    }


def test_19b2_pre_outcome_rank_panel_is_pit_and_score_formula_recomputes():
    pre = read_output("b2_pre_outcome_rank_panel")
    forbidden = set(r.FORBIDDEN_NAMES)
    forbidden |= {col for col in pre.columns if any(col.startswith(prefix) for prefix in r.FORBIDDEN_PREFIXES)}
    assert forbidden.isdisjoint(pre.columns)
    assert pre["rank_scope"].eq("executable_universe_same_decision_date").all()
    assert pre["rank_source_gate"].eq("pass").all()
    assert pre["feature_pit_gate"].eq("pass").all()
    assert pre["rank_cross_section_n"].min() >= 30

    hash_cols = [col for col in r.CSV_SCHEMAS["b2_pre_outcome_rank_panel"] if col != "pre_outcome_rank_panel_hash"]
    expected_hash = r.frame_hash(pre, hash_cols)
    assert pre["pre_outcome_rank_panel_hash"].nunique() == 1
    assert pre["pre_outcome_rank_panel_hash"].iloc[0] == expected_hash

    score = read_output("b2_suppressor_score_panel")
    assert score["pre_outcome_rank_panel_hash"].nunique() == 1
    assert score["pre_outcome_rank_panel_hash"].iloc[0] == expected_hash
    assert np.allclose(score["vol_block"], score[["q_vol60", "q_atr20"]].max(axis=1))
    assert np.allclose(score["extension_block"], score[["q_ret60", "q_ema60_dist"]].max(axis=1))
    assert np.allclose(score["tail_risk_score"], score["vol_block"] * score["extension_block"])
    assert np.allclose(score["basis_risk_score"], score["q_ema60_dist"] * score[["q_atr20", "q_vol60"]].max(axis=1))
    assert np.allclose(score["vol_expansion_rank_spread"], score["q_atr20"] - score["q_vol60"])
    assert np.allclose(score["atr20_over_vol60"], score["atr_20_pct_asof_decision_date"] / np.maximum(score["match_vol60"], 1e-12))
    candidate_rank_sources = {
        "candidate_vol_block_rank_pct": "vol_block",
        "candidate_extension_block_rank_pct": "extension_block",
        "candidate_q_atr20_rank_pct": "q_atr20",
        "candidate_q_ema60_dist_rank_pct": "q_ema60_dist",
        "candidate_q_vol60_rank_pct": "q_vol60",
        "candidate_q_ret60_rank_pct": "q_ret60",
    }
    for out_col, source_col in candidate_rank_sources.items():
        assert np.allclose(score[out_col], score[source_col].rank(pct=True, method="average", ascending=True))


def test_19b2_variant_grid_and_logical_interactions_are_pre_registered():
    grid = read_output("suppressor_variant_grid")
    expected = pd.DataFrame(r.EXPECTED_VARIANT_GRID)
    assert list(grid["variant_id"]) == list(expected["variant_id"])
    assert list(grid["suppressor_family"]) == list(expected["suppressor_family"])
    assert list(grid["score_name"]) == list(expected["score_name"])
    assert list(grid["threshold_type"]) == list(expected["threshold_type"])
    assert list(grid["logical_condition"]) == list(expected["logical_condition"])
    assert bool_series(grid["pre_registered_flag"]).all()
    assert len(grid) == 30

    b_group = grid.loc[grid["variant_id"].str.startswith("B_")]
    assert not b_group["logical_condition"].str.contains("vol_block >=|extension_block >=|q_atr20 >=|q_vol60 >=", regex=True).any()
    assert b_group["logical_condition"].str.contains("candidate_").all()
    extras = grid.loc[~grid["variant_id"].isin(expected["variant_id"])]
    assert extras.empty or bool_series(extras["exploratory_only"]).all()


def test_19b2_ablation_metrics_and_interaction_gate_are_consistent():
    ablation = read_output("suppressor_ablation_readout")
    score = read_output("b2_suppressor_score_panel")
    assert np.allclose(ablation["fast_fail_rate_after"], ablation["left_tail_event_10_n_after"] / ablation["candidate_n_after"])
    assert np.allclose(
        ablation["MAE_20_p10_improvement_vs_S0"],
        ablation["MAE_20_p10_after"] - ablation["S0_candidate_MAE_20_p10"],
    )
    assert np.isclose(
        ablation.loc[ablation["variant_id"].eq("S0"), "S0_candidate_MAE_20_p10"].iloc[0],
        score["MAE_20"].quantile(0.10),
    )
    assert ablation["both_n_before"].eq(145).all()
    assert not bool_series(ablation.loc[ablation["suppressor_family"].eq("single_feature"), "primary_success_eligible"]).any()
    assert ablation.loc[ablation["suppressor_family"].eq("single_feature"), "primary_success_gate"].eq("fail").all()

    budget = read_output("suppressor_budget_comparison_readout")
    decision = read_output("entry_universe_19b2_decision").iloc[0]
    gate_should_pass = budget["interaction_superiority_component_gate"].eq("pass").any()
    assert decision["interaction_superiority_gate"] == ("pass" if gate_should_pass else "fail")
    if decision["interaction_superiority_gate"] == "fail":
        best_budget = budget.loc[budget["primary_variant_id"].eq(decision["best_variant_id"])].iloc[0]
        assert best_budget["efficiency_lift_pct"] < 0.10 or best_budget["efficiency_lift_pct_ci_low"] < 0


def test_19b2_decision_manifest_and_report_boundaries_are_closed():
    outputs = run_outputs()
    decision = read_output("entry_universe_19b2_decision").iloc[0]
    for gate in [
        "config_contract_gate",
        "input_artifact_gate",
        "upstream_19a_contract_gate",
        "upstream_19b0_contract_gate",
        "upstream_19b_contract_gate",
        "upstream_19b1_contract_gate",
        "sample_support_gate",
        "primary_row_join_gate",
        "feature_pit_gate",
        "rank_source_gate",
        "score_contract_gate",
        "variant_grid_gate",
        "ablation_metric_gate",
        "policy_authorization_gate",
        "output_contract_gate",
    ]:
        assert decision[gate] == "pass"

    assert decision["decision_state"] in {
        "19B2_high_vol_extension_suppressor_ablation_supported_diagnostic",
        "19B2_suppressor_improves_burden_but_not_interaction_supported_diagnostic",
        "19B2_no_suppressor_pareto_improvement_diagnostic",
        "19B2_config_contract_blocked",
        "19B2_input_artifact_blocked",
        "19B2_upstream_19b_contract_blocked",
        "19B2_upstream_19b1_contract_blocked",
        "19B2_sample_support_blocked",
        "19B2_primary_row_join_blocked",
        "19B2_feature_pit_contract_blocked",
        "19B2_rank_source_blocked",
        "19B2_score_contract_blocked",
        "19B2_variant_grid_blocked",
        "19B2_output_contract_blocked",
    }
    for column in r.POLICY_AUTH_COLUMNS:
        assert bool(decision[column]) is False
    assert bool(decision["validation_outcome_read"]) is False
    assert decision["next_allowed_requirement"] == "none"
    assert decision["max_ep19_terminal_state"] == "19_entry_universe_enrichment_only_diagnostic"

    with outputs["manifest"].open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    with outputs["output_hashes"].open("r", encoding="utf-8") as handle:
        output_hashes = json.load(handle)
    assert manifest["decision_state"] == decision["decision_state"]
    assert manifest["output_hashes"] == r.build_output_hashes(r.output_paths(r.resolve_output_root(r.load_config(CONFIG))), include_manifest=False)
    assert output_hashes == r.build_output_hashes(r.output_paths(r.resolve_output_root(r.load_config(CONFIG))), include_manifest=True)
    assert "manifest" not in manifest["output_hashes"]
    assert "manifest" in output_hashes
    assert "output_hashes" not in output_hashes

    report = outputs["report"].read_text(encoding="utf-8")
    for phrase in [
        "19B2 是 diagnostic-only suppressor ablation。",
        "T0 suppressor ablation 不等于 alpha support。",
        "validation outcome read = false。",
        "19C replay authorized = false。",
        "EP20 policy preflight authorized = false。",
        "任何 delayed confirmation、entry timing 或 left-tail rejector model 都必须作为新的 pre-registered requirement。",
        "当前结果不能简化写成 “B2 bad”。",
        "interaction score 没有同时以点估计和 bootstrap CI 优于 single-feature",
        "both 被单独输出",
    ]:
        assert phrase in report
    assert r.output_contract_pass(outputs, report, outputs["handoff_contract"].read_text(encoding="utf-8"))
