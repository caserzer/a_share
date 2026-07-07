from __future__ import annotations

import functools
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight"
SCRIPT = EXP / "src/run_19b0_fast_rule_grid_enrichment_scan.py"
CONFIG = EXP / "configs/config_19b0_fast_rule_grid_enrichment_scan.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_19b0_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def config_and_paths():
    cfg = r.load_config(CONFIG)
    return cfg, r.resolve_paths(cfg)


@functools.lru_cache(maxsize=1)
def run_outputs():
    return r.run(CONFIG)


def read_output(key: str) -> pd.DataFrame:
    return pd.read_csv(run_outputs()[key])


def test_19b0_upstream_19a_and_train_only_boundary_are_enforced():
    cfg, paths = config_and_paths()
    input_audit = r.build_input_artifact_audit(cfg, paths)
    assert input_audit["input_artifact_gate"].eq("pass").all()

    upstream, gate, row = r.build_upstream_19a_contract_audit(paths)
    assert gate == "pass"
    assert row["decision_state"] == "19A_entry_universe_contract_ready"
    assert row["next_allowed_requirement"] == "requirement_19b0_fast_rule_grid_enrichment_scan.md"
    assert upstream["fact_gate"].eq("pass").all()
    assert upstream["required_fact"].str.startswith("manifest_hash_match:").any()

    boundary = read_output("train_only_boundary_audit").iloc[0]
    assert bool(boundary["non_train_outcome_columns_loaded"]) is False
    assert int(boundary["non_train_outcome_row_n"]) == 0
    assert int(boundary["robustness_label_value_access_n"]) == 0
    assert int(boundary["validation_label_value_access_n"]) == 0
    assert bool(boundary["selection_uses_train_only"]) is True
    assert boundary["boundary_gate"] == "pass"


def test_19b0_label_anchor_rebuild_uses_executable_next_open_not_ep07_ready_made_label():
    label_map = read_output("label_source_map")
    assert label_map["selected_anchor_type"].eq("executable_next_open_anchored").all()
    assert label_map["ready_made_label_allowed_for_primary"].eq(False).all()
    assert label_map["ready_made_label_allowed_for_diagnostic"].eq(True).all()
    expected_label_fields = {
        f"{label}_{horizon}d"
        for horizon in (20, 30, 60, 120)
        for label in ("forward_mfe", "forward_mae", "forward_return", "forward_big_winner", "path_complete")
    }
    assert expected_label_fields.issubset(set(label_map["label_field"]))

    audit = read_output("label_anchor_rebuild_audit").iloc[0]
    assert audit["row_scope"] == "ep07_train_candidate_rows"
    assert float(audit["trade_open_price_positive_rate"]) == 1.0
    assert bool(audit["ready_made_label_used_for_primary"]) is False
    assert bool(audit["ready_made_label_used_for_selection"]) is False

    metric = read_output("train_cell_metric_readout")
    if not metric.empty:
        assert metric["label_anchor_type"].eq("executable_next_open_anchored").all()


def test_19b0_matching_features_and_baseline_arms_are_explicit():
    matching = read_output("matching_feature_source_map")
    assert set(matching["matching_key"]) >= {
        "decision_month",
        "market_cap_bucket_asof_decision_date",
        "rolling_20d_amount_bucket_asof_decision_date",
        "rolling_60d_volatility_bucket_asof_decision_date",
        "recent_20d_return_bucket_asof_decision_date",
        "instrument_or_industry_bucket_if_supported",
    }
    assert matching["ep07_direct_field_allowed_for_matching"].eq(False).all()
    assert matching["frozen_before_baseline_materialization"].eq(True).all()

    metric = read_output("train_cell_metric_readout")
    if not metric.empty:
        observed = set(metric["baseline_family"])
        assert observed == set(r.BASELINE_FAMILIES)
        counts = metric.groupby(["family_id", "grid_cell_id"])["baseline_family"].nunique()
        assert counts.eq(3).all()
        assert "forward_big_winner_100d_rate" not in metric.columns
        assert "p_matched_50" not in metric.columns

    quality = read_output("baseline_matching_quality_audit")
    materialization = read_output("baseline_materialization_audit")
    if not quality.empty:
        assert quality["unmatched_candidate_rate"].lt(1.0).any()
        assert r.any_cell_with_all_baseline_gate_pass(materialization, "baseline_materialization_gate")
        decision = read_output("entry_universe_19b0_decision").iloc[0]
        expected_gate = "pass" if r.any_cell_with_all_baseline_gate_pass(quality, "baseline_matching_quality_gate") else "fail"
        assert decision["baseline_matching_quality_gate"] == expected_gate


def test_19b0_grid_and_denominator_outputs_include_ep07_identity_cell_and_source_maps():
    grid = read_output("grid_cell_manifest")
    ep07 = grid.loc[grid["grid_cell_id"].eq("EP07_identity_cell")]
    assert len(ep07) == 1
    assert "19A_family_search_accounting_manifest" in ep07.iloc[0]["source_contract"]
    assert "19A_grid_search_manifest" not in ep07.iloc[0]["source_contract"]

    features = read_output("simple_rule_feature_source_map")
    assert "early_no_false_repair_10d_asof_decision_date" in set(features["feature_field"])
    early = features.loc[features["feature_field"].eq("early_no_false_repair_10d_asof_decision_date")].iloc[0]
    assert early["source_type"] == "ep07_direct_only"

    denominator = read_output("candidate_cell_denominator_audit")
    ep07_den = denominator.loc[denominator["ep07_identity_cell_flag"].eq(True)].iloc[0]
    assert ep07_den["grid_cell_id"] == "EP07_identity_cell"
    assert int(ep07_den["source_candidate_train_n"]) == 7328
    assert int(ep07_den["entry_anchor_available_n"]) > 0


def test_19b0_decision_manifest_and_policy_authorization():
    decision = read_output("entry_universe_19b0_decision").iloc[0]
    assert decision["decision_state"] in {
        "19B0_candidate_family_eligible_for_19B",
        "19B0_candidate_family_train_diagnostic",
        "19B0_no_candidate_family_passed",
        "19B0_baseline_materialization_blocked",
    }
    failed_gates = [gate for gate in r.CRITICAL_GATES if decision[gate] != "pass"]
    if decision["decision_state"] == "19B0_baseline_materialization_blocked":
        assert failed_gates == ["baseline_matching_quality_gate"]
        assert decision["blocking_reason"] == "baseline_matching_quality_gate"
    else:
        assert failed_gates == []
    for column in r.POLICY_AUTH_COLUMNS:
        assert bool(decision[column]) is False
    assert bool(decision["validation_outcome_read"]) is False
    assert bool(decision["robustness_outcome_used_for_selection"]) is False

    outputs = run_outputs()
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
    assert "executable_next_open_anchored" in report
    assert "不授权模型" in report
