from __future__ import annotations

import functools
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight"
SCRIPT = EXP / "src/run_19b1_t0_left_right_tail_separability_readout.py"
CONFIG = EXP / "configs/config_19b1_t0_left_right_tail_separability_readout.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_19b1_test_module", SCRIPT)
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


def test_19b1_contract_inputs_and_upstream_hashes_are_closed():
    outputs = run_outputs()
    for key in r.REQUIRED_OUTPUT_KEYS:
        assert key in outputs
        assert outputs[key].exists()
        assert outputs[key].stat().st_size > 0

    input_audit = read_output("input_artifact_audit")
    assert "output_root" not in set(input_audit["artifact_id"])
    assert input_audit["input_artifact_gate"].eq("pass").all()
    verified = input_audit.loc[input_audit["artifact_id"].isin(r.B_HASH_KEY_MAP)]
    assert verified["hash_verified"].astype(bool).all()

    upstream = read_output("upstream_contract_audit")
    assert set(upstream["upstream_scope"]).issubset({"19A", "19B0", "19B", "19B_boundary", "19B_hash"})
    assert upstream["contract_gate"].eq("pass").all()
    with r.resolve_input_paths(r.load_config(CONFIG))["nineteen_b_output_hashes"].open("r", encoding="utf-8") as handle:
        nineteen_b_hashes = json.load(handle)
    assert len(upstream.loc[upstream["upstream_scope"].eq("19B_hash")]) == len(nineteen_b_hashes)


def test_19b1_primary_scope_and_outcome_groups_are_exact():
    join = read_output("t0_feature_join_audit").iloc[0]
    assert join["primary_row_join_gate"] == "pass"
    assert int(join["expected_candidate_n_from_19b_metric"]) == 1552
    assert int(join["observed_candidate_n_from_mfe_mae_joint"]) == 1552
    assert int(join["observed_candidate_n_after_manifest_join"]) == 1552
    assert int(join["duplicate_join_key_n"]) == 0
    assert int(join["missing_in_candidate_manifest_n"]) == 0

    outcome = read_output("outcome_left_right_overlap_readout").iloc[0]
    assert int(outcome["candidate_n"]) == 1552
    assert int(outcome["instrument_n"]) == 524
    assert int(outcome["right_clean_n"]) == 290
    assert int(outcome["left_bad_n"]) == 614
    assert int(outcome["both_n"]) == 145
    assert int(outcome["neither_n"]) == 503
    assert outcome["outcome_overlap_gate"] == "pass"


def test_19b1_feature_contract_blocks_forbidden_inputs():
    source = read_output("t0_feature_source_audit")
    assert set(source["feature_name"]) == set(r.PRIMARY_FEATURE_WHITELIST)
    assert source["pit_safe_flag"].astype(bool).all()
    assert source["primary_whitelist_flag"].astype(bool).all()
    assert not source["exploratory_only_flag"].astype(bool).any()
    assert set(source["feature_signal_group"]) <= set(r.FEATURE_SIGNAL_GROUPS)

    matrix_manifest = read_output("t0_feature_matrix_manifest").iloc[0]
    assert int(matrix_manifest["forbidden_column_n"]) == 0
    assert int(matrix_manifest["forbidden_label_column_n"]) == 0
    assert matrix_manifest["feature_matrix_gate"] == "pass"
    assert matrix_manifest["primary_whitelist_hash"] == r.stable_hash_payload(r.PRIMARY_FEATURE_WHITELIST)
    config = r.load_config(CONFIG)
    paths = r.resolve_input_paths(config)
    matrix, _ = r.build_primary_matrix(config, paths, r.load_feature_panel(config, paths))
    feature_matrix = r.build_feature_only_matrix(matrix)
    forbidden = [
        col
        for col in feature_matrix.columns
        if col in r.FORBIDDEN_NAMES or col.startswith(r.FORBIDDEN_PREFIXES) or "validation" in col
    ]
    assert forbidden == []
    assert matrix_manifest["feature_matrix_hash"] == r.frame_hash(feature_matrix, list(feature_matrix.columns))

    univariate = read_output("t0_univariate_feature_separability_readout")
    assert set(univariate["feature_name"]) == set(r.PRIMARY_FEATURE_WHITELIST)
    assert {
        "feature_auc_raw_left_bad_positive",
        "feature_auc_oriented_left_bad_vs_right_clean",
        "direction_for_left_bad",
        "bh_fdr_adjusted_p",
        "bonferroni_sidak_adjusted_p",
        "separability_pass",
    }.issubset(univariate.columns)
    assert univariate["feature_support_gate"].isin({"pass", "fail"}).all()


def test_19b1_multivariate_probe_is_skipped_and_never_authorizes_policy():
    multi = read_output("t0_multivariate_diagnostic_separability_readout").iloc[0]
    assert bool(multi["multivariate_enabled"]) is False
    assert multi["diagnostic_method"] == "skipped_by_config"
    assert multi["diagnostic_status"] == "skipped"
    assert multi["multivariate_diagnostic_skipped_reason"] == (
        "multivariate_probe_disabled_by_pre_frozen_config_to_avoid_model_training_ambiguity"
    )
    assert bool(multi["model_artifact_written"]) is False
    assert bool(multi["threshold_rule_written"]) is False
    assert bool(multi["policy_training_flag"]) is False
    assert bool(multi["model_training_authorized"]) is False

    decision = read_output("entry_universe_19b1_decision").iloc[0]
    for column in r.POLICY_AUTH_COLUMNS:
        assert bool(decision[column]) is False
    assert bool(decision["validation_outcome_read"]) is False
    assert decision["next_allowed_requirement"] == "none"
    assert decision["max_ep19_terminal_state"] == "19_entry_universe_enrichment_only_diagnostic"


def test_19b1_decision_and_hash_manifests_are_consistent():
    outputs = run_outputs()
    decision = read_output("entry_universe_19b1_decision").iloc[0]
    assert decision["decision_state"] in {
        "19B1_t0_left_right_tail_separable_diagnostic",
        "19B1_t0_left_right_tail_not_separable_diagnostic",
        "19B1_config_contract_blocked",
        "19B1_input_artifact_blocked",
        "19B1_sample_support_blocked",
        "19B1_t0_feature_pit_contract_blocked",
        "19B1_upstream_contract_blocked",
        "19B1_upstream_19b_contract_blocked",
        "19B1_output_contract_blocked",
    }
    for gate in [
        "config_contract_gate",
        "input_artifact_gate",
        "upstream_19a_contract_gate",
        "upstream_19b0_contract_gate",
        "upstream_19b_contract_gate",
        "sample_support_gate",
        "primary_row_join_gate",
        "outcome_overlap_gate",
        "t0_feature_pit_gate",
        "policy_authorization_gate",
        "output_contract_gate",
    ]:
        assert decision[gate] == "pass"

    with outputs["manifest"].open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    with outputs["output_hashes"].open("r", encoding="utf-8") as handle:
        output_hashes = json.load(handle)
    assert manifest["decision_state"] == decision["decision_state"]
    assert manifest["output_hashes"] == r.build_output_hashes(r.output_paths(r.OUTPUT_ROOT), include_manifest=False)
    assert output_hashes == r.build_output_hashes(r.output_paths(r.OUTPUT_ROOT), include_manifest=True)
    assert "output_hashes" not in output_hashes
    assert "manifest" in output_hashes
    assert set(manifest["required_outputs"]) == set(r.REQUIRED_OUTPUT_KEYS)
    assert r.output_contract_pass(outputs, outputs["report"].read_text(encoding="utf-8"), outputs["handoff_contract"].read_text(encoding="utf-8"))

    report = outputs["report"].read_text(encoding="utf-8")
    assert "19B1 是 diagnostic-only" in report
    assert "validation outcome read = false" in report
    assert "T0 separability 不等于 alpha support" in report
    assert "19C replay authorized = false" in report
    assert "任何后续 left-tail suppressor 必须作为新的 pre-registered requirement" in report
