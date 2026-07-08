from __future__ import annotations

import functools
import importlib.util
import json
import re
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight"
SCRIPT = EXP / "src/run_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.py"
CONFIG = EXP / "configs/config_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.yaml"
REQUIREMENT = EXP / "requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_19b_test_module", SCRIPT)
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


def required_csv_outputs_from_requirement() -> set[str]:
    text = REQUIREMENT.read_text(encoding="utf-8")
    block = text.split("机器可读输出：", 1)[1].split("叙述输出：", 1)[0]
    return {line.strip() for line in block.splitlines() if line.strip().endswith(".csv")}


def schema_csvs_from_requirement() -> set[str]:
    text = REQUIREMENT.read_text(encoding="utf-8")
    names = set()
    for line in text.splitlines():
        if line.startswith("### 15.") and ".csv`" in line:
            names.add(line.split("`", 2)[1])
    return names


def required_figure_outputs_from_requirement() -> set[str]:
    text = REQUIREMENT.read_text(encoding="utf-8")
    block = text.split("图表输出：", 1)[1].split("manifest 输出：", 1)[0]
    return {line.strip() for line in block.splitlines() if line.strip().endswith(".png")}


def required_columns_for_csv(csv_name: str) -> list[str]:
    text = REQUIREMENT.read_text(encoding="utf-8")
    pattern = rf"### 15\.\d+ `{re.escape(csv_name)}`.*?```text\n(.*?)\n```"
    match = re.search(pattern, text, flags=re.S)
    assert match is not None
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


def test_19b_upstream_and_outcome_boundary_are_fail_closed():
    input_audit = read_output("input_artifact_audit")
    assert input_audit["input_artifact_gate"].eq("pass").all()

    upstream_19a = read_output("upstream_19a_contract_audit")
    upstream_19b0 = read_output("upstream_19b0_contract_audit")
    assert upstream_19a["contract_gate"].eq("pass").all()
    assert upstream_19b0["contract_gate"].eq("pass").all()

    boundary = read_output("robustness_outcome_boundary_audit").iloc[0]
    assert bool(boundary["robustness_candidate_manifest_frozen_before_label_readout"]) is True
    assert bool(boundary["robustness_baseline_manifest_frozen_before_label_readout"]) is True
    assert bool(boundary["validation_outcome_columns_loaded"]) is False
    assert int(boundary["validation_outcome_row_n"]) == 0
    assert int(boundary["validation_label_value_access_n"]) == 0
    assert bool(boundary["robustness_outcome_used_to_expand_or_select_test_set"]) is False
    assert boundary["boundary_gate"] == "pass"

    candidate_manifest = read_output("robustness_candidate_row_manifest")
    forbidden = [col for col in candidate_manifest.columns if col.startswith("forward_") or col.startswith("validation_")]
    assert forbidden == []


def test_19b_selected_cells_and_claim_scopes_are_preserved():
    metric = read_output("robustness_metric_readout")
    observed = set(map(tuple, metric[["family_id", "grid_cell_id"]].drop_duplicates().to_numpy()))
    assert observed == {
        ("B2_relative_strength_breakout", "B2-relative-strength-breakout__182b3d0f30f5"),
        ("B5_recent_high_close_plus_amount_expansion", "B5-recent-high-close-plus-amount-expansion__25d72c708fc1"),
    }
    assert metric["promotion_claim_type_19b0"].eq("positive_beta_exposure_candidate").all()
    assert "residual_alpha_candidate" not in set(metric["promotion_claim_type_19b0"])

    decision = read_output("entry_universe_19b_decision").iloc[0]
    assert decision["positive_beta_exposure_correction_scope"] == "2 * positive_exposure_score_50"
    assert decision["residual_alpha_correction_scope_19b0_frozen"] == "0 * primary_tail_lift_50"
    assert decision["residual_style_readout_correction_scope_19b"] == "2 * primary_tail_lift_50"
    for column in r.POLICY_AUTH_COLUMNS:
        assert bool(decision[column]) is False
    assert bool(decision["validation_outcome_read"]) is False


def test_19b_outputs_have_requirement_schemas_and_expected_columns():
    outputs = run_outputs()
    missing_schema = required_csv_outputs_from_requirement() - schema_csvs_from_requirement()
    assert missing_schema == set()
    for key in r.REQUIRED_OUTPUT_KEYS:
        assert key in outputs
        assert outputs[key].exists()
        assert outputs[key].stat().st_size > 0

    for csv_name in required_csv_outputs_from_requirement():
        actual_columns = set(pd.read_csv(r.OUTPUT_ROOT / csv_name, nrows=0).columns)
        missing_columns = set(required_columns_for_csv(csv_name)) - actual_columns
        assert missing_columns == set(), csv_name

    report = outputs["report"].read_text(encoding="utf-8")
    for figure_name in required_figure_outputs_from_requirement():
        figure_path = r.OUTPUT_ROOT / figure_name
        assert figure_path.exists()
        assert figure_path.stat().st_size > 0
        assert figure_name in report

    metric = read_output("robustness_metric_readout")
    assert {
        "positive_exposure_p_value_method",
        "residual_alpha_support_claim_allowed_19b",
        "residual_readout_status",
        "residual_blocking_reason",
        "cell_decision_state",
    }.issubset(metric.columns)
    assert metric["positive_exposure_p_value_method"].eq(
        "cluster_bootstrap_se_normal_approx_one_sided_candidate_vs_eligible_universe"
    ).all()

    topk = read_output("topk_concentration_sensitivity")
    assert {
        "top_1_instrument_removed_tail_lift_against_original_frozen_baseline",
        "top_3_instruments_removed_tail_lift_against_original_frozen_baseline",
    }.issubset(topk.columns)


def test_19b_diagnostic_repairs_do_not_create_residual_claims():
    registry = read_output("baseline_repair_variant_registry")
    diagnostic = registry.loc[registry["diagnostic_repair_only_flag"].astype(bool)]
    assert not diagnostic.empty
    assert diagnostic["primary_residual_claim_allowed"].eq(False).all()

    sweep = read_output("baseline_repair_sweep_audit")
    diagnostic_sweep = sweep.loc[sweep["diagnostic_repair_only_flag"].astype(bool)]
    assert not diagnostic_sweep.empty
    assert diagnostic_sweep["primary_residual_claim_allowed"].eq(False).all()
    metric = read_output("robustness_metric_readout")
    if metric["matched_baseline_residual_pass_19b"].any():
        residual = read_output("robustness_residual_alpha_readout")
        assert residual["residual_alpha_support_claim_allowed_19b"].eq(residual["matched_baseline_residual_pass_19b"]).all()


def test_19b_metric_contract_blocks_weakened_false_positive_burden_caps():
    config = r.load_config(CONFIG)
    config["false_positive_burden"]["candidate_per_winner_cap"] = 6.01
    reason = r.metric_contract_blocking_reason(config)
    assert reason == "false_positive_burden_tolerance_weakened_after_contract_default"

    gates = {gate: "pass" for gate in r.CRITICAL_GATES}
    metric = pd.DataFrame([{"cell_decision_state": "positive_exposure_persistent_residual_not_supported"}])
    state, next_req, blocking_reason = r.decide_state(metric, gates, reason)
    assert state == "19B_metric_contract_blocked"
    assert next_req == "none"
    assert blocking_reason == "false_positive_burden_tolerance_weakened_after_contract_default"


def test_19b_manifest_hashes_report_and_decision_are_consistent():
    outputs = run_outputs()
    decision = read_output("entry_universe_19b_decision").iloc[0]
    assert decision["decision_state"] in {
        "19B_residual_alpha_supported_for_validation_stress_readout",
        "19B_baseline_quality_blocked_enrichment_only_diagnostic_possible",
        "19B_positive_exposure_persistent_enrichment_only_diagnostic",
        "19B_robustness_not_supported",
        "19B_false_positive_burden_blocked",
        "19B_topk_concentration_blocked",
        "19B_upstream_19a_contract_blocked",
        "19B_upstream_19b0_contract_blocked",
        "19B_outcome_boundary_blocked",
        "19B_metric_contract_blocked",
        "19B_output_contract_blocked",
    }
    with outputs["output_hashes"].open("r", encoding="utf-8") as handle:
        output_hashes = json.load(handle)
    with outputs["manifest"].open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    assert manifest["decision_state"] == decision["decision_state"]
    assert manifest["output_hashes"] == output_hashes
    assert output_hashes == r.build_output_hashes(r.output_paths())
    assert "manifest" not in output_hashes
    assert "output_hashes" not in output_hashes

    report = outputs["report"].read_text(encoding="utf-8")
    assert "validation outcome read: `false`" in report
    assert "positive exposure persistence 不是 independent alpha" in report
    assert "19B 不授权 19C replay" in report
