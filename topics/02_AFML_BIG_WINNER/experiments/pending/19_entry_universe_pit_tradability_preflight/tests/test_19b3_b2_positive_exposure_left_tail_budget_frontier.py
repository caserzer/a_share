from __future__ import annotations

import functools
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight"
SCRIPT = EXP / "src/run_19b3_b2_positive_exposure_left_tail_budget_frontier.py"
CONFIG = EXP / "configs/config_19b3_b2_positive_exposure_left_tail_budget_frontier.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_19b3_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def run_outputs():
    r.freeze_stage(CONFIG)
    r.forward_stage(CONFIG)
    return r.finalize_stage(CONFIG)


def output_root() -> Path:
    return r.resolve_output_root(r.load_config(CONFIG))


def test_config_human_restart_and_upstream_contract_are_closed():
    run_outputs()
    root = output_root()
    config = r.load_config(CONFIG)
    gate, reasons = r.validate_config(config)
    assert gate == "pass"
    assert reasons == []
    assert config["arms"]["primary_arm_id"] == r.PRIMARY_ARM
    assert config["positive_exposure_comparator"]["primary_ratio_floor"] == config["forward_gates"]["primary_positive_exposure_ratio_50_min"]

    restart = json.loads((root / "freeze/human_restart_authorization.json").read_text())
    assert restart["restart_type"] == "human_research_restart"
    assert restart["restart_source"] == "research_plan_section_12"
    assert restart["upstream_pipeline_authorization"] is False
    assert restart["human_restart_lineage_gate"] == "pass"
    assert all(restart["checks"].values())

    upstream = pd.read_csv(root / "freeze/upstream_contract_audit.csv")
    assert upstream["contract_gate"].eq("pass").all()
    for fact in [
        "all_critical_gates_pass", "cooldown_window_sessions", "selection_track",
        "positive_exposure_robustness_pass", "interaction_superiority_gate",
        "best_single_feature_variant_id",
    ]:
        assert fact in set(upstream["required_fact"])


def test_spent_design_role_audit_reproduces_frozen_r2_and_r3_values():
    run_outputs()
    audit = pd.read_csv(output_root() / "freeze/spent_design_arm_role_audit.csv").set_index("arm_id")
    config = r.load_config(CONFIG)["spent_design_role_audit"]
    r2 = audit.loc[r.PRIMARY_ARM]
    r3 = audit.loc[r.ARM_IDS[3]]
    assert r2["promotion_eligible"]
    assert not r3["promotion_eligible"]
    assert np.isclose(r2["threshold_value"], config["expected_R2_candidate_q_vol60_p70"], atol=1e-9)
    assert int(r2["retained_n"]) == config["expected_R2_retained_n"]
    assert np.isclose(r2["right_tail_capture_retention"], config["expected_R2_right_tail_capture"], atol=1e-9)
    assert np.isclose(r2["weighted_ES10_MAE20"], config["expected_R2_ES10"], atol=1e-9)
    assert np.isclose(r2["weighted_MAE20_p10"], config["expected_R2_MAE20_p10"], atol=1e-9)
    assert np.isclose(r3["right_tail_capture_retention"], config["expected_R3_right_tail_capture"], atol=1e-9)
    assert np.isclose(r3["weighted_ES10_MAE20"], config["expected_R3_ES10"], atol=1e-9)
    assert np.isclose(r3["ES10_improvement_vs_R2"], config["expected_R3_ES10_improvement_vs_R2"], atol=1e-9)
    assert audit["dataset_role"].eq("spent_robustness_design_only").all()
    assert (~audit["selection_or_tuning_allowed"].astype(bool)).all()
    assert (~audit["support_claim_allowed"].astype(bool)).all()
    assert (~audit["forward_gate_contribution"].astype(bool)).all()
    assert audit["spent_design_arm_role_gate"].eq("pass").all()


def test_forward_evaluability_fails_before_any_outcome_read():
    run_outputs()
    root = output_root()
    coverage = pd.read_csv(root / "freeze/data_coverage_and_forward_support_audit.csv").iloc[0]
    assert coverage["topn_universe_max_date"] == "2026-05-29"
    assert coverage["benchmark_max_date"] == "2026-05-29"
    assert coverage["spent_robustness_outcome_path_end"] == "2026-05-29"
    assert coverage["train_spent_outcome_path_end"] == "2022-07-05"
    assert coverage["effective_forward_start"] == "not_yet_observed"
    assert int(coverage["minimum_additional_exchange_sessions_for_first_label_complete"]) == 141
    assert int(coverage["forward_B2_candidate_n"]) == 0
    assert coverage["forward_preoutcome_evaluability_gate"] == "fail"
    assert bool(coverage["pipeline_dry_run_only"])
    assert coverage["validation_support_floor_feasibility_gate"] == "pass"
    assert int(coverage["validation_max_possible_decision_month_n"]) == 11
    assert int(coverage["purge_embargo_overlap_row_n"]) == 0

    forward = json.loads((root / "forward/forward_decision.json").read_text())
    assert forward["forward_state"] == "19B3_forward_oos_underpowered_not_pass"
    assert forward["pipeline_dry_run_only"] is True
    assert forward["forward_outcome_read"] is False
    assert forward["validation_stress_authorized"] is False
    assert forward["next_allowed_stage"] == "finalize"
    assert pd.read_csv(root / "forward/outcome_access_audit.csv").empty
    final_access = pd.read_csv(root / "outcome_access_audit.csv")
    assert len(final_access) == 1
    assert final_access.iloc[0]["dataset_role"] == "spent_robustness_design_only"
    assert final_access.iloc[0]["purpose"] == "spent_design_arm_role_audit"
    assert not bool(final_access.iloc[0]["selection_or_tuning_allowed"])
    assert not (root / "validation_stress").exists()


def test_freeze_manifests_are_preoutcome_only_and_p0_is_frozen():
    run_outputs()
    root = output_root()
    candidate = pd.read_csv(root / "freeze/forward_candidate_preoutcome_manifest.csv")
    eligible = pd.read_csv(root / "freeze/forward_eligible_preoutcome_manifest.csv")
    weights = pd.read_csv(root / "freeze/forward_arm_weight_manifest.csv")
    forbidden = ("mfe", "mae", "right_tail", "left_tail", "outcome_group", "arm_decision", "validation_metric")
    for frame in [candidate, eligible, weights]:
        assert not [column for column in frame.columns if any(token in column.lower() for token in forbidden)]
    assert candidate.empty and eligible.empty and weights.empty

    p0 = pd.read_csv(root / "freeze/p0_permutation_assignment_hashes.csv")
    assert len(p0) == 2000
    assert p0["assignment_hash"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert p0["date_gross_invariance_gate"].eq("pass").all()
    assert p0["date_weight_multiset_invariance_gate"].eq("pass").all()
    registry = pd.read_csv(root / "freeze/b2_arm_registry.csv")
    assert list(registry["arm_id"]) == r.ARM_IDS + [r.PLACEBO_ARM]
    assert registry["promotion_eligible"].sum() == 1
    assert registry.loc[registry["promotion_eligible"], "arm_id"].iloc[0] == r.PRIMARY_ARM


def test_weighted_es10_uses_fractional_boundary_mass_and_step_quantile():
    weights = [0.04, 0.10, 0.86]
    mae = [-0.50, -0.30, -0.05]
    keys = ["a", "b", "c"]
    # Tail mass is 0.10: all 0.04 from a and 0.06 from b.
    expected = (0.04 * 0.50 + 0.06 * 0.30) / 0.10
    assert np.isclose(r.weighted_es10(weights, mae, keys), expected)
    # Cumulative weight first reaches 10% at b.
    assert r.weighted_quantile_step(weights, mae, keys) == -0.30


def test_r3_weight_and_cash_are_not_rescaled_and_p0_preserves_date_budget():
    config = r.load_config(CONFIG)
    candidates = pd.DataFrame(
        [
            {"candidate_id": "a", "decision_date": "2027-01-04", "board_bucket": "main", "q_atr20": 0.1, "q_vol60": 0.1, "median_vol60_asof_t0": 0.02, "vol60": 0.01},
            {"candidate_id": "b", "decision_date": "2027-01-04", "board_bucket": "main", "q_atr20": 0.5, "q_vol60": 0.5, "median_vol60_asof_t0": 0.02, "vol60": 0.04},
            {"candidate_id": "c", "decision_date": "2027-01-04", "board_bucket": "star", "q_atr20": 0.9, "q_vol60": 0.9, "median_vol60_asof_t0": 0.02, "vol60": 0.20},
            {"candidate_id": "d", "decision_date": "2027-01-04", "board_bucket": "chinext", "q_atr20": 0.7, "q_vol60": 0.7, "median_vol60_asof_t0": 0.02, "vol60": 0.08},
        ]
    )
    weights, _ = r.build_arm_weights(candidates, config, "manifest-hash")
    r3 = weights.loc[weights["arm_id"].eq(r.ARM_IDS[3])].set_index("candidate_id")
    assert np.isclose(r3.loc["a", "final_weight"], 1.0)
    assert np.isclose(r3.loc["b", "final_weight"], 0.5)
    assert np.isclose(r3.loc["c", "final_weight"], 0.25)
    assert np.isclose(r3.loc["d", "final_weight"], 0.25)
    assert np.allclose(r3["cash_weight"], 1.0 - r3["final_weight"])
    assert not np.isclose(r3["final_weight"].sum(), len(r3))

    r2 = weights.loc[weights["arm_id"].eq(r.PRIMARY_ARM)].set_index("candidate_id")["final_weight"]
    assigned, counts = r.permutation_assignments(candidates, r2, config, 0)
    assert counts["primary"] == 1
    assert counts["fallback"] == 1
    assert assigned["candidate_id"].nunique() == len(candidates)
    assert np.isclose(assigned["assigned_weight"].sum(), r2.sum())
    assert sorted(assigned["assigned_weight"].tolist()) == sorted(r2.tolist())


def test_dry_run_outputs_have_frozen_schema_watermarks_and_no_validation_access():
    run_outputs()
    root = output_root()
    schemas = {
        "forward_outcome_panel.csv": r.OUTCOME_SCHEMA,
        "forward_eligible_outcome_panel.csv": r.ELIGIBLE_OUTCOME_SCHEMA,
        "arm_tail_readout.csv": r.ARM_TAIL_SCHEMA,
        "arm_pairwise_readout.csv": r.PAIRWISE_SCHEMA,
        "cluster_bootstrap_readout.csv": r.BOOTSTRAP_SCHEMA,
        "leave_one_month_out_readout.csv": r.MONTH_SCHEMA,
        "placebo_null_readout.csv": r.PLACEBO_SCHEMA,
        "support_and_concentration_readout.csv": r.SUPPORT_CONCENTRATION_SCHEMA,
    }
    for name, schema in schemas.items():
        frame = pd.read_csv(root / "forward" / name)
        assert frame.empty
        assert list(frame.columns) == schema
    for name in [
        "forward_left_tail_frontier.png", "forward_exposure_capture_frontier.png",
        "forward_bootstrap_improvement_distribution.png", "forward_month_stability.png",
    ]:
        path = root / "forward/figures" / name
        assert path.exists() and path.stat().st_size > 1000
    with pytest.raises(PermissionError):
        r.validation_stress_stage(CONFIG)
    assert not (root / "validation_stress").exists()


def test_stage_and_final_hash_bundles_are_bidirectionally_consistent():
    run_outputs()
    root = output_root()
    for stage in ["freeze", "forward", "finalize"]:
        ok, reason = r.verify_bundle(root, stage)
        assert ok, reason
        manifest_path, hashes_path = r.bundle_paths(root, stage)
        manifest = json.loads(manifest_path.read_text())
        hashes = json.loads(hashes_path.read_text())
        assert str(hashes_path.relative_to(root)) not in hashes
        assert hashes[str(manifest_path.relative_to(root))] == r.file_sha(manifest_path)
        assert manifest["output_hashes"] == {key: value for key, value in hashes.items() if key != str(manifest_path.relative_to(root))}


def test_final_decision_report_and_authorization_boundary_are_closed():
    outputs = run_outputs()
    decision = pd.read_csv(outputs["entry_universe_19b3_decision"]).iloc[0]
    assert decision["final_decision_state"] == "19B3_forward_oos_underpowered_not_pass"
    assert decision["next_allowed_requirement"] == "none"
    assert decision["primary_arm_id"] == r.PRIMARY_ARM
    assert bool(decision["pipeline_dry_run_only"])
    for column in r.AUTHORIZATION_COLUMNS:
        assert not bool(decision[column])
    report = outputs["19B3_b2_positive_exposure_left_tail_budget_frontier_report"].read_text(encoding="utf-8")
    for phrase in [
        "19B3 的目标是先压低 B2 左尾，在正 exposure 下允许牺牲部分右尾。",
        "validation 是压力测试集，不是 arm 选择、调参或正面确认集。",
        "R2 A_VOL60_top30 是唯一可晋级 primary arm；R3 continuous budget 只作 diagnostic challenger。",
        "positive exposure ratio >= 1.20 只使用 arm-calendar-matched eligible denominator；legacy ratio 只作桥接。",
        "forward preoutcome evaluability gate 通过前，19B3 只是 pipeline dry-run，不产生科学结论。",
        "19B3 support 不等于可交易策略 support。",
        "19C replay authorized = false。",
        "EP20 policy preflight authorized = false。",
    ]:
        assert phrase in report
    handoff = outputs["19B3_handoff_contract"].read_text(encoding="utf-8")
    assert "next_allowed_requirement = none" in handoff
    assert "actionable_handoff = false" in handoff
