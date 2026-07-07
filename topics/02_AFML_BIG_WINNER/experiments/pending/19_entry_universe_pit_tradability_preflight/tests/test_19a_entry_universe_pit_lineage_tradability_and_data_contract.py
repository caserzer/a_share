from __future__ import annotations

import functools
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight"
SCRIPT = EXP / "src/run_19a_entry_universe_pit_lineage_tradability_and_data_contract.py"
CONFIG = EXP / "configs/config_19a_entry_universe_pit_lineage_tradability_and_data_contract.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_19a_test_module", SCRIPT)
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


def test_19a_input_artifacts_and_18f_upstream_closure_are_ready():
    cfg, paths = config_and_paths()
    audit = r.build_input_artifact_audit(cfg, paths)
    assert audit["input_artifact_gate"].eq("pass").all()
    assert audit["exists"].eq(True).all()

    upstream, gate = r.build_upstream_closure_audit(paths)
    assert gate == "pass"
    observed = dict(zip(upstream["required_fact"], upstream["observed_value"], strict=False))
    assert observed["decision_state"] == "18F_utility_bridge_not_supported"
    assert observed["next_allowed_requirement"] == "none"
    assert str(observed["policy_training_authorized"]).lower() == "false"
    assert str(observed["policy_replay_authorized"]).lower() == "false"
    assert str(observed["deployment_authorized"]).lower() == "false"
    assert observed["learned_utility_support_gate"] == "fail"
    for fact in [
        "entry_policy_authorized",
        "exit_policy_authorized",
        "holding_policy_authorized",
        "portfolio_backtest_authorized",
        "model_deployment_authorized",
        "production_signal_authorized",
        "live_trading_authorized",
    ]:
        assert str(observed[fact]).lower() == "false"


def test_19a_primary_candidate_materialization_applies_cooldown_and_support_gates():
    cfg, paths = config_and_paths()
    panel = r.load_primary_candidate_panel(cfg, paths)
    density = r.build_candidate_density_and_overlap_audit(panel)
    censoring = r.build_censoring_treatment_freeze(cfg, panel)
    ess = r.build_effective_sample_size_readout(cfg, panel)

    expected = {
        "train": (7328, 5254, 5116, 5116, 803),
        "robustness": (3687, 2640, 2638, 2635, 551),
        "validation": (4146, 2902, 2901, 2901, 602),
    }
    for split, values in expected.items():
        row = density.loc[density["split"].eq(split)].iloc[0]
        assert (
            int(row["raw_trigger_rows"]),
            int(row["cooldown_entry_rows"]),
            int(row["fill_feasible_candidate_rows"]),
            int(row["primary_enrichment_denominator_rows"]),
            int(row["instrument_n"]),
        ) == values

    support_gate, blocking = r.build_sample_support_gate(cfg, density, censoring, ess)
    assert support_gate == "pass"
    assert blocking == ""
    assert ess["effective_sample_size_gate"].eq("pass").all()
    assert censoring["censoring_treatment_gate"].eq("pass").all()

    tradability = r.build_tradability_field_availability_audit(panel)
    assert tradability["field_availability_gate"].isin(["pass", "pass_nonblocking"]).all()
    entry_day_amount = tradability.loc[tradability["field_id"].eq("entry_day_amount_cny")].iloc[0]
    assert entry_day_amount["availability_status"] == "unavailable_not_used_in_primary_19a_adapter"
    assert bool(entry_day_amount["unavailable_field_recorded"]) is True


def test_19a_tushare_theme_contract_blocks_pre2025_matching_and_quarantines_akshare():
    _, paths = config_and_paths()
    theme = r.build_theme_snapshot_status(paths)
    pre_2025 = theme.loc[theme["classification_year"].lt(2025)]
    assert not pre_2025.empty
    assert pre_2025["snapshot_policy"].eq("pre_2025_backfilled_from_2025_snapshot").all()
    assert pre_2025["pre_2025_backfill_flag"].eq(True).all()
    assert pre_2025["historical_pit_membership_evidence_flag"].eq(False).all()

    baseline_spec = r.build_baseline_matching_spec(r.load_config(CONFIG))
    industry_key = baseline_spec.loc[
        baseline_spec["matching_key"].eq("instrument_or_industry_bucket_if_supported")
    ].iloc[0]
    assert bool(industry_key["primary_matching_allowed"]) is False
    assert industry_key["forbidden_snapshot_policy"] == "pre_2025_backfilled_from_2025_snapshot"
    assert bool(industry_key["akshare_board_full_dump_forbidden_as_matching_key"]) is True

    quarantine = r.build_board_source_quarantine_audit(paths).iloc[0]
    assert quarantine["quarantine_status"] == "quarantined_out_of_contract"
    assert bool(quarantine["feature_use_detected_flag"]) is False
    assert bool(quarantine["matching_use_detected_flag"]) is False
    assert bool(quarantine["candidate_source_use_detected_flag"]) is False
    assert int(quarantine["file_n"]) > 0


def test_19a_decision_ready_and_no_policy_authorization():
    decision = read_output("entry_universe_preflight_decision").iloc[0]
    assert decision["decision_state"] == "19A_entry_universe_contract_ready"
    assert decision["next_allowed_requirement"] == "requirement_19b0_fast_rule_grid_enrichment_scan.md"
    assert isinstance(decision["requirement_file_hash"], str) and len(decision["requirement_file_hash"]) == 64
    assert isinstance(decision["config_file_hash"], str) and len(decision["config_file_hash"]) == 64
    assert bool(decision["all_critical_gates_pass"]) is True
    for gate in r.CRITICAL_GATES:
        assert decision[gate] == "pass"
    for column in r.POLICY_AUTH_COLUMNS:
        assert bool(decision[column]) is False

    forward = read_output("forward_outcome_label_freeze")
    required_fields = {
        "forward_big_winner_20d",
        "forward_big_winner_60d",
        "forward_big_winner_120d",
        "path_complete_flag",
        "path_complete_20d",
        "path_complete_60d",
        "path_complete_120d",
        "censoring_status",
        "last_available_forward_session",
        "label_readout_only_flag",
    }
    assert required_fields.issubset(set(forward["field_name"]))
    assert forward["label_readout_only_flag"].eq(True).all()

    baseline_quality = read_output("baseline_matching_quality_audit")
    assert baseline_quality["baseline_materialized_in_19a"].eq(False).all()
    assert baseline_quality["quality_status"].eq("frozen_pending_19B0_baseline_materialization").all()

    correction = read_output("multiple_testing_correction_freeze")
    assert "status" in correction.columns
    assert correction["status"].eq("frozen_pending_19B0_train_selection").all()


def test_19a_manifest_hashes_are_synced_and_exclude_self_referential_outputs():
    outputs = run_outputs()
    with outputs["output_hashes"].open("r", encoding="utf-8") as handle:
        output_hashes = json.load(handle)
    with outputs["manifest"].open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    assert manifest["decision_state"] == "19A_entry_universe_contract_ready"
    assert len(manifest["requirement_file_hash"]) == 64
    assert len(manifest["config_file_hash"]) == 64
    assert manifest["output_hashes"] == output_hashes
    assert "manifest" not in output_hashes
    assert "output_hashes" not in output_hashes
    assert output_hashes == r.build_output_hashes(r.output_paths())
    assert set(r.REQUIRED_OUTPUT_KEYS) == set(r.output_paths())

    report = outputs["report"].read_text(encoding="utf-8")
    for heading in [
        "## 1. Upstream Closure",
        "## 2. Candidate Row Schema and Lineage",
        "## 3. Execution and Fill Feasibility",
        "## 4. Canonicalization and Cooldown",
        "## 5. Forward Label and Censoring",
        "## 6. Split Freeze",
        "## 7. TuShare DC Concept-Board Contract",
        "## 8. AkShare Quarantine",
        "## 9. Industry / Board / Theme Support",
        "## 10. Baseline Budget and Matching",
        "## 11. Grid Search and Multiplicity",
        "## 12. Minimum Sample and Effective Sample",
        "## 13. Final Decision",
    ]:
        assert heading in report
