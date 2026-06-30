from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
SCRIPT = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17a_oracle_replay_contract_preflight.py"
CONFIG = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic/configs/config_17a_oracle_replay_contract_preflight.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_17a_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


def load_config():
    return r.load_config(CONFIG)


def test_topic_main_unsolved_problem_is_narrative_not_hard_gate():
    cfg = load_config()
    upstream = r.build_upstream_closure_audit(cfg, r.resolve_paths(cfg))
    topic = upstream.loc[upstream["source_phase_id"].eq("topic_conclusion")].iloc[0]
    assert topic["required_state_status"] == "pass"
    assert topic["main_unsolved_problem_readout_status"] == "prose_or_research_plan_only"


def test_oracle_denominator_binding_keeps_binary_and_labelable_separate():
    cfg = load_config()
    binding = r.build_oracle_denominator_binding(cfg, "appendix_only")
    o1 = binding.loc[binding["oracle_id"].eq("O1")].iloc[0]
    o5 = binding.loc[binding["oracle_id"].eq("O5")].iloc[0]
    o6 = binding.loc[binding["oracle_id"].eq("O6")].iloc[0]
    assert o1["primary_denominator_type"] == "binary_primary"
    assert o1["expected_primary_row_count_train"] == 14962
    assert o1["expected_primary_row_count_validation"] == 505
    assert o5["primary_denominator_type"] == "labelable_full"
    assert o5["expected_primary_row_count_train"] == 20245
    assert bool(o6["skip_is_blocking"]) is False


def test_capacity_appendix_only_does_not_block_ready_decision():
    cfg = load_config()
    one = pd.DataFrame([{"required_state_status": "pass"}])
    decision = r.build_decision(
        cfg,
        "pass",
        one,
        pd.DataFrame([{"denominator_reconciliation_gate": "pass"}]),
        pd.DataFrame([{"binding_status": "pass"}]),
        pd.DataFrame([{"action_semantics_gate": "pass"}]),
        pd.DataFrame([{"delayed_materialization_gate": "pass"}]),
        pd.DataFrame(
            [
                {
                    "capacity_reconstruction_gate": "appendix_only",
                    "o6_status_for_17b": "appendix_only_nonblocking",
                }
            ]
        ),
        pd.DataFrame([{"price_path_replay_gate": "pass"}]),
        pd.DataFrame([{"learned_score_reference_gate": "pass"}]),
        pd.DataFrame([{"sanity_status": "pass"}]),
        pd.DataFrame([{"six_cell_sanity_gate": "pass"}]),
        pd.DataFrame([{"search_accounting_gate": "pass"}]),
    )
    row = decision.iloc[0]
    assert row["decision_state"] == r.DECISION_READY
    assert row["o6_status_for_17b"] == "appendix_only_nonblocking"


def test_16d_validation_stress_reference_replays_without_selection():
    cfg = load_config()
    resolved = r.resolve_paths(cfg)
    learned = r.build_learned_score_reference_replay_audit(
        cfg,
        r.read_table(resolved["upstream_16d_policy_confusion_readout"]),
        r.read_table(resolved["upstream_16d_policy_threshold_freeze_audit"]),
    )
    validation = learned.loc[learned["split_bucket"].eq("validation")].iloc[0]
    assert validation["observed_binary_step_n"] == 505
    assert validation["observed_defended_binary_step_n"] == 158
    assert validation["observed_defended_negative_n"] == 81
    assert validation["learned_score_reference_gate"] == "pass"


def test_output_paths_include_three_manifest_outputs():
    outputs = r.output_paths()
    assert outputs["manifest"].name == "17A_oracle_replay_contract_preflight_manifest.json"
    assert outputs["replay_engine_manifest"].name == "oracle_replay_engine_manifest.json"
    assert outputs["input_artifact_manifest"].name == "input_artifact_manifest.json"


def test_search_accounting_has_no_trading_authorization():
    search = r.build_search_accounting_audit(load_config()).iloc[0]
    assert search["search_accounting_gate"] == "pass"
    assert bool(search["no_model_refit"]) is True
    assert bool(search["no_validation_selection"]) is True
    assert bool(search["no_oracle_value_interpretation"]) is True
