from __future__ import annotations

import functools
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/18_payoff_state_representation_research"
SCRIPT = EXP / "src/run_18a_payoff_state_contract_preflight.py"
CONFIG = EXP / "configs/config_18a_payoff_state_contract_preflight.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_18a_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def context():
    cfg = r.load_config(CONFIG)
    resolved = r.resolve_paths(cfg)
    target_panel, lineage_hash = r.load_target_panel(cfg, resolved)
    tables = r.load_support_tables(resolved)
    input_audit = r.build_input_artifact_audit(cfg, resolved, target_panel)
    return cfg, resolved, target_panel, lineage_hash, tables, input_audit


def test_18a_input_audit_uses_single_publishable_full_panel_source():
    cfg, _, target_panel, _, _, input_audit = context()
    primary = input_audit.loc[input_audit["artifact_role"].eq("full_row_level_target_source")]
    assert len(primary) == 1
    row = primary.iloc[0]
    assert row["source_kind"] == "publishable_full_panel"
    assert row["row_key_coverage"] == "labelable_full"
    assert row["row_key_reconciliation_gate"] == "pass"
    assert len(target_panel) == cfg["expected"]["total_labelable_step_n"]
    assert target_panel["step_id"].nunique() == len(target_panel)
    assert r.input_artifact_gate(input_audit) == "pass"


def test_18a_denominator_reconciliation_preserves_neutral_rows():
    cfg, _, target_panel, _, _, _ = context()
    denominator, gate = r.build_target_denominator_reconciliation(cfg, target_panel)
    assert gate == "pass"
    robustness = denominator.loc[denominator["split_bucket"].eq("robustness")].iloc[0]
    assert int(robustness["labelable_step_n"]) == 2496
    assert int(robustness["binary_step_n"]) == 1872
    assert int(robustness["neutral_step_n"]) == 624

    neutral, neutral_gate = r.build_neutral_preservation_audit(target_panel)
    assert neutral_gate == "pass"
    assert neutral["neutral_preserved_in_labelable_full"].all()
    assert not neutral["neutral_reclassified_as_positive_or_negative"].any()


def test_18a_oracle_reference_map_keeps_o4_binary_denominator_diagnostic_only():
    cfg, _, _, _, tables, _ = context()
    oracle_map, gate = r.build_oracle_reference_denominator_map(cfg, tables)
    assert gate == "pass"
    o5 = oracle_map.loc[oracle_map["oracle_reference_id"].eq("O5_perfect_utility_primary")].iloc[0]
    o4 = oracle_map.loc[oracle_map["oracle_reference_id"].eq("O4_label_positive_primary")].iloc[0]
    mixed = oracle_map.loc[oracle_map["oracle_reference_id"].eq("17D_mixed_o5_vs_best_label_path_gap")].iloc[0]
    assert o5["source_denominator_type"] == "labelable_full"
    assert bool(o5["direct_comparison_allowed"]) is True
    assert o4["source_denominator_type"] == "binary_primary"
    assert bool(o4["direct_comparison_allowed"]) is False
    assert mixed["source_denominator_type"] == "mixed_diagnostic_only"
    assert mixed["allowed_bridge_denominator"] == "none"


def test_18a_o5_identity_replays_full_labelable_denominator_and_blocks_mismatch():
    cfg, _, target_panel, _, tables, _ = context()
    replay, gate = r.build_o5_incremental_definition_replay(cfg, tables, target_panel)
    assert gate == "pass"
    robustness = replay.loc[replay["split_bucket"].eq("robustness")].iloc[0]
    assert int(robustness["observed_step_n"]) == 2496
    assert int(robustness["defended_step_n"]) == 1056
    assert abs(float(robustness["aggregate_o5_incremental_replay"]) - 0.0294674283651707) <= 1e-12
    assert float(robustness["max_abs_diff"]) <= 1e-9
    assert int(robustness["formula_mismatch_n"]) == 0

    broken = {key: value.copy() for key, value in tables.items()}
    mask = (
        broken["seventeen_b_ladder_summary"]["oracle_variant_id"].eq("O5_perfect_utility_primary")
        & broken["seventeen_b_ladder_summary"]["split_bucket"].eq("robustness")
        & broken["seventeen_b_ladder_summary"]["cost_bps"].eq(50)
    )
    broken["seventeen_b_ladder_summary"].loc[mask, "mean_incremental_return"] = 0.0
    _, broken_gate = r.build_o5_incremental_definition_replay(cfg, broken, target_panel)
    assert broken_gate == "fail"


def test_18a_payoff_cutoffs_are_train_frozen_absolute_values():
    cfg, _, _, lineage_hash, tables, _ = context()
    cutoffs, gate = r.build_payoff_cutoff_freeze(cfg, tables, lineage_hash)
    assert gate == "pass"
    observed = dict(zip(cutoffs["threshold_id"], cutoffs["train_absolute_payoff_cutoff"], strict=False))
    assert abs(observed["high_upside_top30_stress"] - 0.0596330275229357) <= 1e-12
    assert abs(observed["high_upside_top20_stress"] - 0.1012285086722715) <= 1e-12
    assert abs(observed["high_upside_top10_stress"] - 0.1721071844362347) <= 1e-12
    assert not cutoffs["split_local_recompute_used"].any()
    assert cutoffs["y_payoff_lineage_hash"].nunique() == 1


def test_18a_feature_inventory_marks_delayed_and_external_nonprimary():
    _, _, _, _, tables, _ = context()
    inventory, gate = r.build_feature_source_inventory(tables)
    assert gate == "pass"
    assert inventory.loc[inventory["feature_family_id"].isin(["F1", "F2", "F3", "F4", "F5"]), "primary_allowed"].all()
    f6 = inventory.loc[inventory["feature_family_id"].eq("F6")].iloc[0]
    f7 = inventory.loc[inventory["feature_family_id"].eq("F7")].iloc[0]
    assert bool(f6["primary_allowed"]) is False
    assert bool(f6["appendix_only"]) is True
    assert bool(f7["primary_allowed"]) is False
    assert f7["pit_available_status"] == "unavailable"


def test_18a_leakage_forbidden_columns_are_not_primary_allowed():
    cfg, _, _, _, tables, _ = context()
    leakage, gate = r.build_leakage_forbidden_column_audit(cfg, tables)
    assert gate == "pass"
    assert not leakage["found_in_primary_feature_source"].any()
    assert not leakage["primary_feature_allowed"].any()
    assert leakage["leakage_forbidden_column_gate"].eq("pass").all()


def test_18a_final_decision_ready_and_no_policy_authorization():
    cfg, _, target_panel, lineage_hash, tables, input_audit = context()
    upstream, upstream_gate = r.build_upstream_authorization_audit(cfg, tables)
    denominator, denom_gate = r.build_target_denominator_reconciliation(cfg, target_panel)
    neutral, neutral_gate = r.build_neutral_preservation_audit(target_panel)
    oracle_map, oracle_gate = r.build_oracle_reference_denominator_map(cfg, tables)
    o5_replay, o5_gate = r.build_o5_incremental_definition_replay(cfg, tables, target_panel)
    cutoffs, cutoff_gate = r.build_payoff_cutoff_freeze(cfg, tables, lineage_hash)
    target_registry, target_gate = r.build_target_definition_registry(lineage_hash)
    path_risk, path_gate = r.build_path_risk_target_audit(target_panel)
    feature_inventory, feature_gate = r.build_feature_source_inventory(tables)
    leakage, leakage_gate = r.build_leakage_forbidden_column_audit(cfg, tables)
    search, search_gate = r.build_search_accounting_audit()

    assert upstream["authorization_status"].eq("pass").all()
    assert denominator["denominator_reconciliation_gate"].eq("pass").all()
    assert neutral["neutral_preservation_gate"].eq("pass").all()
    assert oracle_map["oracle_reference_denominator_gate"].eq("pass").all()
    assert o5_replay["o5_incremental_definition_replay_gate"].eq("pass").all()
    assert cutoffs["train_frozen_cutoff_gate"].eq("pass").all()
    assert target_registry["target_lineage_gate"].eq("pass").all()
    assert path_risk["path_risk_sign_convention_gate"].eq("pass").all()
    assert feature_inventory.loc[feature_inventory["primary_allowed"], "pit_available_status"].eq("pass").all()
    assert leakage["leakage_forbidden_column_gate"].eq("pass").all()
    assert search["search_accounting_gate"].eq("pass").all()

    gates = {
        "upstream_authorization_gate": upstream_gate,
        "input_artifact_gate": r.input_artifact_gate(input_audit),
        "denominator_reconciliation_gate": denom_gate,
        "target_lineage_gate": target_gate,
        "oracle_reference_denominator_gate": oracle_gate,
        "o5_incremental_definition_replay_gate": o5_gate,
        "train_frozen_cutoff_gate": cutoff_gate,
        "neutral_preservation_gate": neutral_gate,
        "path_risk_sign_convention_gate": path_gate,
        "feature_source_pit_gate": feature_gate,
        "leakage_forbidden_column_gate": leakage_gate,
        "search_accounting_gate": search_gate,
    }
    decision = r.build_decision_row(gates).iloc[0]
    assert decision["decision_state"] == "18A_payoff_state_contract_ready"
    assert decision["next_allowed_requirement"] == "requirement_18b_payoff_state_feature_matrix_audit.md"
    for col in r.AUTH_FALSE_COLUMNS:
        assert bool(decision[col]) is False


def test_18a_manifest_hashes_are_synced_without_regenerating_outputs():
    manifest_path = EXP / "outputs/manifests/18A_payoff_state_contract_preflight_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    decision_path = EXP / "outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_state_contract_decision.csv"
    report_path = EXP / "outputs/publishable/reports/payoff_state_contract_preflight_report.md"
    assert manifest["decision_state"] == "18A_payoff_state_contract_ready"
    assert manifest["next_allowed_requirement"] == "requirement_18b_payoff_state_feature_matrix_audit.md"
    assert manifest["output_hashes"]["decision"] == r.file_sha(decision_path)
    assert manifest["output_hashes"]["report"] == r.file_sha(report_path)
