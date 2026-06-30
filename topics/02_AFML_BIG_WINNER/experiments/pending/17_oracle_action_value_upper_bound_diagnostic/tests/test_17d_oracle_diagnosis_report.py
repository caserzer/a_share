from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic"
SCRIPT = EXP / "src/run_17d_oracle_diagnosis_report.py"
CONFIG = EXP / "configs/config_17d_oracle_diagnosis_report.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_17d_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


def load_context():
    cfg = r.load_config(CONFIG)
    resolved = r.resolve_paths(cfg)
    inputs = r.build_input_gate_audit(cfg, resolved)
    contract = r.build_contract_validation_audit(cfg, resolved)
    tables = r.load_inputs(resolved)
    return cfg, resolved, inputs, contract, tables


def test_17d_requires_17c_ready_handoff():
    _, _, _, contract, _ = load_context()
    handoff = contract.loc[contract["validation_check_id"].astype(str).str.startswith("17c_decision_handoff_values")]
    assert not handoff.empty
    assert handoff["validation_status"].astype(str).eq("pass").all()
    assert "17c_decision_handoff_values:decision_state" in set(handoff["validation_check_id"])


def test_17d_contract_validation_audit_blocks_on_stale_hash():
    cfg, _, inputs, contract, tables = load_context()
    broken = contract.copy()
    first_hash = broken["validation_check_id"].astype(str).str.endswith("_sha256")
    broken.loc[first_hash.idxmax(), "validation_status"] = "fail"
    gates = r.compute_gates(cfg, tables, inputs, broken)
    decision = r.build_decision_row(gates).iloc[0]
    assert decision["contract_validation_gate"] == "fail"
    assert decision["final_decision_state"] == "oracle_lineage_or_denominator_blocked"


def test_17d_o5_upper_bound_gate_uses_topk_bootstrap_and_materiality():
    cfg, _, inputs, contract, tables = load_context()
    gates = r.compute_gates(cfg, tables, inputs, contract)
    assert gates["o5_upper_bound_gate"] == "pass"
    assert gates["primary_o5_mean_incremental_return"] >= cfg["materiality"]["materiality_mean_floor"]


def test_17d_payoff_preservation_requires_variant_specific_high_upside_topk_bootstrap():
    cfg, _, _, _, tables = load_context()
    payoff, gate = r.build_upside_preservation_diagnosis(cfg, tables)
    assert gate == "pass"
    high = payoff.loc[payoff["oracle_variant_id"].astype(str).str.contains("O4_high_upside")]
    assert len(high) == 3
    top10 = high.loc[high["oracle_variant_id"].eq("O4_high_upside_top10_stress")].iloc[0]
    assert top10["topk_gate"] == "fail"
    assert bool(top10["overdefense_flag"]) is True
    assert high.loc[high["oracle_variant_id"].eq("O4_high_upside_top20_stress"), "bootstrap_gate"].iloc[0] == "pass"


def test_17d_o4_label_positive_uses_explicit_threshold_id_convention():
    cfg, _, _, _, tables = load_context()
    payoff, _ = r.build_upside_preservation_diagnosis(cfg, tables)
    row = payoff.loc[payoff["oracle_variant_id"].eq("O4_label_positive_primary")].iloc[0]
    assert row["threshold_id"] == "label_positive_primary"
    assert pd.isna(row["train_quantile"])


def test_17d_o2_threshold_decay_is_readout_not_tuning():
    cfg, _, _, _, tables = load_context()
    path, gate = r.build_path_risk_threshold_diagnosis(cfg, tables)
    assert gate == "pass"
    assert {"O2_dd_08pct_stress", "O2_dd_10pct_primary", "O2_dd_20pct_stress"}.issubset(set(path["oracle_variant_id"]))
    assert "threshold_value_decay_vs_08pct" in path.columns


def test_17d_delayed_support_requires_validation_dominance_not_robustness_only():
    cfg, _, _, _, tables = load_context()
    timing, gate, candidate = r.build_timing_sensitivity_diagnosis(cfg, tables)
    assert gate == "fail"
    assert candidate is True
    validation = timing.loc[timing["split_bucket"].eq("validation")].iloc[0]
    assert validation["best_delayed_retention_ratio_vs_o5_t0"] < cfg["materiality"]["delayed_retention_floor"]


def test_17d_current_feature_gap_requires_16e_six_cell_reconciliation_pass():
    _, _, _, _, tables = load_context()
    bridge, gate, _ = r.build_learned_model_gap_bridge(tables)
    assert gate == "pass"
    assert "16e_six_cell_reconciliation_consistent" in set(bridge["feature_gap_component"])

    broken = {key: value.copy() for key, value in tables.items()}
    primary_idx = broken["sixteen_e_six_cell_reconciliation"].loc[
        broken["sixteen_e_six_cell_reconciliation"]["cost_bps"].eq(50)
    ].index[0]
    broken["sixteen_e_six_cell_reconciliation"].loc[primary_idx, "six_cell_reconciliation_status"] = "fail"
    _, broken_gate, _ = r.build_learned_model_gap_bridge(broken)
    assert broken_gate == "fail"


def test_17d_final_decision_emits_single_label():
    cfg, _, inputs, contract, tables = load_context()
    gates = r.compute_gates(cfg, tables, inputs, contract)
    decision = r.build_decision_row(gates).iloc[0]
    assert decision["final_decision_state"] == "oracle_payoff_state_research_allowed"
    assert decision["recommended_next_requirement"] == "requirement_18_payoff_state_representation_research.md"
    assert int(decision["selected_priority_rank"]) == 6


def test_17d_no_policy_authorization_flags_are_true():
    cfg, _, inputs, contract, tables = load_context()
    decision = r.build_decision_row(r.compute_gates(cfg, tables, inputs, contract)).iloc[0]
    for col in r.AUTH_FALSE_COLUMNS:
        assert bool(decision[col]) is False


def test_17d_report_hash_is_synced_in_manifest():
    manifest_path = EXP / "outputs/manifests/17D_oracle_diagnosis_report_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = EXP / "outputs/publishable/reports/ep17_oracle_action_value_diagnostic_report.md"
    assert manifest["output_hashes"]["report"] == r.file_sha(report)
    assert manifest["final_decision_state"] == "oracle_payoff_state_research_allowed"
