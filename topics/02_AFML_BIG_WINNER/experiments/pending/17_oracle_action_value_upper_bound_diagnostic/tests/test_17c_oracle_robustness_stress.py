from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
SCRIPT = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17c_oracle_robustness_stress.py"
CONFIG = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic/configs/config_17c_oracle_robustness_stress.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_17c_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


def load_config():
    return r.load_config(CONFIG)


def row(
    i: int,
    variant: str = "O5_perfect_utility_primary",
    split: str = "robustness",
    inc: float = 0.01,
    instrument: str | None = None,
    episode: str | None = None,
    month: str = "2020-01-01",
    action: str = "defend",
    label: str = "negative",
) -> dict:
    return {
        "step_id": f"s{i}",
        "label_id": "l1",
        "threshold_id": "t1",
        "instrument": instrument or f"SH600{i % 10:03d}",
        "episode_cluster_id": episode or f"c{i % 10}",
        "horizon_sessions": 20,
        "step_index": i,
        "step_start_date": month,
        "step_end_date": "2020-02-01",
        "cluster_split_bucket": split,
        "split_bucket": split,
        "label_class": label,
        "forward_return_h20": -0.02,
        "realized_h20_payoff": -0.02,
        "signed_max_drawdown_h20": -0.1,
        "drawdown_abs_for_reporting": 0.1,
        "oracle_id": variant.split("_")[0],
        "oracle_variant_id": variant,
        "primary_variant": True,
        "cost_bps": 50,
        "q_defend": 0.0,
        "oracle_action": action,
        "incremental_net_return": inc,
    }


def test_17b_ready_decision_required_for_17c():
    cfg = load_config()
    audit = r.build_input_gate_audit(cfg, r.resolve_paths(cfg))
    contract = r.build_17b_contract_validation_audit(cfg, r.resolve_paths(cfg))
    assert set(audit["gate_status"]) == {"pass"}
    assert set(contract["validation_status"]) == {"pass"}
    assert "seventeen_b_row_level_panel" in set(audit["artifact_key"])


def test_input_gate_emits_named_panel_canonicalization_checks():
    cfg = load_config()
    audit = r.build_input_gate_audit(cfg, r.resolve_paths(cfg))
    checks = audit.loc[audit["audit_row_type"].astype(str).eq("canonicalization_check")]
    assert {
        "cluster_split_bucket_present",
        "canonical_split_bucket_created",
        "split_bucket_conflict_count",
        "signed_max_drawdown_h20_present",
        "drawdown_abs_for_reporting_present",
        "drawdown_avoided_abs_not_required",
    }.issubset(set(checks["input_check_id"]))
    assert checks["gate_status"].astype(str).eq("pass").all()


def test_17b_contract_validation_covers_manifest_hashes_and_ladder_reconciliation():
    cfg = load_config()
    contract = r.build_17b_contract_validation_audit(cfg, r.resolve_paths(cfg))
    checks = set(contract["validation_check_id"].astype(str))
    assert "output_hash_ladder_summary" in checks
    assert "row_count_ladder_summary" in checks
    assert "primary_ladder_summary_rows_present" in checks
    assert any(check.startswith("primary_ladder_summary_reconcile:") for check in checks)
    assert {"seventeen_b_manifest", "seventeen_b_ladder_summary"}.issubset(set(contract["artifact_key"]))
    assert contract["validation_status"].astype(str).eq("pass").all()


def test_17c_canonicalizes_cluster_split_bucket_to_split_bucket():
    frame = pd.DataFrame([row(1)]).drop(columns=["split_bucket"])
    out = r.canonicalize_panel(frame)
    assert out["split_bucket"].tolist() == ["robustness"]


def test_17c_rejects_conflicting_split_bucket_aliases():
    frame = pd.DataFrame([row(1)])
    frame["split_bucket"] = "train"
    try:
        r.canonicalize_panel(frame)
    except ValueError as exc:
        assert "split_bucket conflicts" in str(exc)
    else:
        raise AssertionError("conflicting split aliases must fail")


def test_topk_removed_mean_uses_original_denominator():
    cfg = load_config()
    frame = pd.DataFrame(
        [
            row(1, inc=0.10, instrument="SH600001"),
            row(2, inc=-0.01, instrument="SH600002"),
            row(3, inc=-0.01, instrument="SH600003"),
        ]
    )
    rows = pd.DataFrame(r.topk_rows_for_group(r.canonicalize_panel(frame), cfg))
    top1 = rows.loc[rows["removal_family"].eq("remove_top_1_instrument")].iloc[0]
    assert np.isclose(top1["remaining_mean_incremental_return"], (-0.02) / 3.0)
    assert top1["remaining_step_n"] == 2


def test_topk_removal_uses_positive_contribution_groups_not_abs_losses():
    cfg = load_config()
    frame = pd.DataFrame(
        [
            row(1, inc=0.04, instrument="SH600001"),
            row(2, inc=-0.50, instrument="SH600002"),
            row(3, inc=0.01, instrument="SH600003"),
        ]
    )
    rows = pd.DataFrame(r.topk_rows_for_group(r.canonicalize_panel(frame), cfg))
    top1 = rows.loc[rows["removal_family"].eq("remove_top_1_instrument")].iloc[0]
    assert top1["top_removed_group_keys"] == "SH600001"


def test_bootstrap_rejects_row_independent_resampling():
    cfg = load_config()
    frame = pd.DataFrame([row(i, episode=f"c{i}", instrument=f"SH600{i:03d}", month=f"2020-{(i % 6) + 1:02d}-01") for i in range(30)])
    rows = pd.DataFrame(r.bootstrap_rows_for_group(r.canonicalize_panel(frame), cfg))
    assert "row_independent" not in set(rows["bootstrap_family"])


def test_bootstrap_is_deterministic_for_frozen_random_seed():
    cfg = load_config()
    frame = pd.DataFrame([row(i, episode=f"c{i}", instrument=f"SH600{i:03d}", month=f"2020-{(i % 6) + 1:02d}-01") for i in range(30)])
    first = pd.DataFrame(r.bootstrap_rows_for_group(r.canonicalize_panel(frame), cfg))
    second = pd.DataFrame(r.bootstrap_rows_for_group(r.canonicalize_panel(frame), cfg))
    assert np.allclose(first["ci_low"], second["ci_low"])
    assert first["random_seed"].tolist() == second["random_seed"].tolist()


def test_calendar_quarter_bootstrap_is_readout_only_when_under_min_clusters():
    cfg = load_config()
    frame = pd.DataFrame([row(i, episode=f"c{i}", instrument=f"SH600{i:03d}", month=f"2020-{(i % 12) + 1:02d}-01") for i in range(30)])
    rows = pd.DataFrame(r.bootstrap_rows_for_group(r.canonicalize_panel(frame), cfg))
    q = rows.loc[rows["bootstrap_family"].eq("calendar_quarter")].iloc[0]
    assert q["bootstrap_primary_role"] == "readout_only"
    assert q["bootstrap_family_status"] == "readout_only_insufficient_clusters"
    assert q["bootstrap_gate"] == "readout_only"


def test_matched_base_derives_calendar_and_board_buckets_without_split_leakage():
    cfg = load_config()
    rows = []
    for i in range(80):
        month = f"2020-{(i % 8) + 1:02d}-01"
        inst = "SZ300001" if i % 2 else "SH600001"
        rows.append(row(i, inc=0.01, instrument=inst, episode=f"c{i}", month=month))
    matched = pd.DataFrame(r.matched_rows_for_group(r.canonicalize_panel(pd.DataFrame(rows)), cfg))
    assert {"calendar_month", "calendar_quarter", "instrument_board_bucket"}.issubset(set(matched["matched_family"]))
    assert {"chinext", "sh_main"}.issubset(set(matched["matched_bucket"]))


def test_matched_base_pass_share_is_equal_bucket_weighted_by_family():
    cfg = load_config()
    rows = []
    for i in range(200):
        month = f"2020-{(i % 8) + 1:02d}-01"
        rows.append(row(i, inc=0.01 if i % 8 != 0 else -0.01, episode=f"c{i}", month=month))
    matched = pd.DataFrame(r.matched_rows_for_group(r.canonicalize_panel(pd.DataFrame(rows)), cfg))
    fam = matched.loc[matched["matched_family"].eq("calendar_month")].drop_duplicates("matched_family").iloc[0]
    assert fam["family_pass_share_weighting"] == "equal_bucket_weight"
    assert 0 <= fam["family_pass_share"] <= 1


def test_regime_matched_readout_requires_pit_audit_or_marks_provisional():
    cfg = load_config()
    frame = pd.DataFrame([row(i) for i in range(25)])
    matched = pd.DataFrame(r.matched_rows_for_group(r.canonicalize_panel(frame), cfg))
    regime = matched.loc[matched["matched_family"].eq("market_regime_bucket")].iloc[0]
    assert regime["matched_family_status"] == "not_evaluable_nonblocking"
    assert bool(regime["matched_gate_in_primary_decision"]) is False


def test_known_failed_context_missing_is_not_evaluable_nonblocking():
    cfg = load_config()
    frame = pd.DataFrame([row(i) for i in range(25)])
    matched = pd.DataFrame(r.matched_rows_for_group(r.canonicalize_panel(frame), cfg))
    known = matched.loc[matched["matched_family"].eq("known_failed_context_bucket")].iloc[0]
    assert known["bucket_gate"] == "not_evaluable_nonblocking"


def test_o7_delayed_semantics_use_original_h20_endpoint():
    source = row(1)
    source.update({"forward_return_h20": 0.10, "split_bucket": "robustness"})
    delayed = r.delayed_base_row(
        pd.Series(source),
        k=3,
        cost=50,
        q_defend=0.0,
        action="defend_at_t0_plus_k",
        policy=0.02,
        inc=-0.08,
        prefix=0.025,
        remaining=0.07,
        missing_t0=0,
        missing_end=0,
        status="pass",
    )
    assert delayed["step_end_date"] == source["step_end_date"]
    assert delayed["restart_h20_at_t0_plus_k"] is False


def test_o7_delayed_gap_vs_o5_is_diagnostic_not_support_gate():
    cfg = load_config()
    primary = pd.DataFrame(
        [
            {
                "oracle_id": "O5",
                "oracle_variant_id": "O5_perfect_utility_primary",
                "split_bucket": "robustness",
                "mean_incremental_return": 0.05,
            }
        ]
    )
    delayed_rows = []
    for i in range(30):
        delayed_rows.append(
            {
                **row(i, inc=0.01, month=f"2020-{(i % 6) + 1:02d}-01"),
                "oracle_id": "O7",
                "oracle_variant_id": "O7_delayed_k3_diagnostic",
                "delay_k_sessions": 3,
                "materialization_status": "pass",
                "missing_t0_plus_k_price_n": 0,
                "missing_original_h20_endpoint_n": 0,
                "restart_h20_at_t0_plus_k": False,
                "partial_tail_fill_used": False,
            }
        )
    curve = r.delayed_curve_rows(r.canonicalize_panel(pd.DataFrame(delayed_rows)), primary, cfg)
    assert "delayed_mean_improvement_vs_o5_t0" not in curve.columns
    assert "delayed_mean_gap_vs_o5_t0" in curve.columns
    assert curve.iloc[0]["delayed_mean_gap_vs_o5_t0"] < 0


def test_o7_delayed_o5_reference_is_split_specific_from_row_panel():
    cfg = load_config()
    delayed_rows = []
    reference_rows = []
    refs = {"train": 0.04, "robustness": 0.05, "validation": 0.06}
    i = 0
    for split, ref in refs.items():
        for j in range(30):
            month = f"2020-{(j % 10) + 1:02d}-01"
            instrument = "SH600001" if j % 2 else "SZ300001"
            delayed_rows.append(
                {
                    **row(i, split=split, inc=0.01, instrument=instrument, episode=f"{split}_c{j}", month=month),
                    "oracle_id": "O7",
                    "oracle_variant_id": "O7_delayed_k3_diagnostic",
                    "delay_k_sessions": 3,
                    "materialization_status": "pass",
                    "missing_t0_plus_k_price_n": 0,
                    "missing_original_h20_endpoint_n": 0,
                    "restart_h20_at_t0_plus_k": False,
                    "partial_tail_fill_used": False,
                }
            )
            reference_rows.append(
                row(
                    i,
                    variant="O5_perfect_utility_primary",
                    split=split,
                    inc=ref,
                    instrument=instrument,
                    episode=f"{split}_c{j}",
                    month=month,
                )
            )
            i += 1
    curve = r.delayed_curve_rows(
        r.canonicalize_panel(pd.DataFrame(delayed_rows)),
        r.canonicalize_panel(pd.DataFrame(reference_rows)),
        cfg,
    )
    assert not curve["o5_t0_mean_incremental_return"].isna().any()
    observed = curve.drop_duplicates("split_bucket").set_index("split_bucket")["o5_t0_mean_incremental_return"].to_dict()
    for split, expected in refs.items():
        assert np.isclose(observed[split], expected)


def test_o7_rejects_restart_h20_at_t0_plus_k():
    source = row(1)
    delayed = r.delayed_base_row(pd.Series(source), 3, 50, 0.0, "", np.nan, np.nan, np.nan, np.nan, 0, 1, "missing_original_h20_endpoint")
    assert delayed["missing_original_h20_endpoint_n"] == 1
    assert delayed["partial_tail_fill_used"] is False


def test_o7_missing_t0_plus_k_price_blocks_delayed_curve():
    source = row(1)
    delayed = r.delayed_missing_row(pd.Series(source), 10, 50, 0.0, "missing_t0_plus_k_price")
    assert delayed["missing_t0_plus_k_price_n"] == 1
    assert delayed["materialization_status"] == "missing_t0_plus_k_price"


def test_capacity_sort_key_uses_drawdown_abs_for_reporting_not_missing_drawdown_avoided_abs():
    cfg = load_config()
    assert cfg["capacity"]["capacity_selection_sort_key"] == "drawdown_abs_for_reporting_desc"


def test_capacity_appendix_only_does_not_emit_execution_capacity_blocked():
    cfg = load_config()
    frame = pd.DataFrame([row(i, variant="O5_perfect_utility_primary") for i in range(10)])
    capacity_audit = pd.DataFrame([{"capacity_reconstruction_gate": "appendix_only", "o6_status_for_17b": "appendix_only_nonblocking"}])
    capacity, _ = r.build_capacity_constraint(r.canonicalize_panel(frame), capacity_audit, cfg)
    assert set(capacity["capacity_constraint_gate"]) == {"not_evaluable_nonblocking"}
    assert not capacity["o6_primary_decision_allowed"].astype(bool).any()


def test_capacity_evaluable_failure_can_emit_execution_capacity_blocked():
    cfg = load_config()
    input_audit = pd.DataFrame([{"gate_status": "pass", "artifact_key": "x"}])
    contract = pd.DataFrame([{"validation_status": "pass"}])
    primary = pd.DataFrame(
        [
            {
                "oracle_id": "O5",
                "oracle_variant_id": "O5_perfect_utility_primary",
                "primary_support_gate": "pass",
                "topk_gate": "pass",
                "bootstrap_gate": "pass",
                "matched_base_gate": "pass",
                "materiality_gate": "pass",
                "mean_incremental_return": 0.03,
                "trimmed_mean_incremental_return": 0.03,
            }
        ]
    )
    delay = pd.DataFrame([{"delayed_curve_gate": "pass", "delayed_decision_diagnostic_flag": False}])
    capacity = pd.DataFrame(
        [
            {
                "split_bucket": "robustness",
                "capacity_status": "evaluable",
                "capacity_reconstruction_gate": "pass",
                "capacity_constraint_gate": "fail",
            }
        ]
    )
    search = pd.DataFrame([{"search_accounting_gate": "pass"}])
    decision = r.build_decision(cfg, input_audit, contract, primary, delay, capacity, search).iloc[0]
    assert decision["decision_state"] == r.DECISION_CAPACITY_BLOCKED


def test_o5_failure_after_topk_or_bootstrap_emits_no_action_value():
    cfg = load_config()
    input_audit = pd.DataFrame([{"gate_status": "pass", "artifact_key": "x"}])
    contract = pd.DataFrame([{"validation_status": "pass"}])
    primary = pd.DataFrame(
        [
            {
                "oracle_id": "O5",
                "oracle_variant_id": "O5_perfect_utility_primary",
                "primary_support_gate": "fail",
                "topk_gate": "fail",
                "bootstrap_gate": "pass",
                "matched_base_gate": "pass",
                "materiality_gate": "pass",
                "mean_incremental_return": 0.03,
                "trimmed_mean_incremental_return": 0.03,
            }
        ]
    )
    delay = pd.DataFrame([{"delayed_curve_gate": "pass", "delayed_decision_diagnostic_flag": False}])
    capacity = pd.DataFrame([{"split_bucket": "robustness", "capacity_status": "appendix_only_nonblocking", "capacity_reconstruction_gate": "appendix_only", "capacity_constraint_gate": "not_evaluable_nonblocking"}])
    search = pd.DataFrame([{"search_accounting_gate": "pass"}])
    decision = r.build_decision(cfg, input_audit, contract, primary, delay, capacity, search).iloc[0]
    assert decision["decision_state"] == r.DECISION_NO_VALUE


def test_o5_pass_with_o1_o2_o4_pass_emits_ready_for_diagnosis():
    cfg = load_config()
    input_audit = pd.DataFrame([{"gate_status": "pass", "artifact_key": "x"}])
    contract = pd.DataFrame([{"validation_status": "pass"}])
    rows = []
    for variant in ["O1_negative_primary", "O5_perfect_utility_primary"]:
        rows.append(
            {
                "oracle_id": variant.split("_")[0],
                "oracle_variant_id": variant,
                "primary_support_gate": "pass",
                "topk_gate": "pass",
                "bootstrap_gate": "pass",
                "matched_base_gate": "pass",
                "materiality_gate": "pass",
                "mean_incremental_return": 0.03,
                "trimmed_mean_incremental_return": 0.03,
            }
        )
    delay = pd.DataFrame([{"delayed_curve_gate": "pass", "delayed_decision_diagnostic_flag": False}])
    capacity = pd.DataFrame([{"split_bucket": "robustness", "capacity_status": "appendix_only_nonblocking", "capacity_reconstruction_gate": "appendix_only", "capacity_constraint_gate": "not_evaluable_nonblocking"}])
    search = pd.DataFrame([{"search_accounting_gate": "pass"}])
    decision = r.build_decision(cfg, input_audit, contract, pd.DataFrame(rows), delay, capacity, search).iloc[0]
    assert decision["decision_state"] == r.DECISION_READY
    assert decision["label_or_path_oracle_support_gate"] == "pass"


def test_no_policy_authorization_flags_are_true():
    cfg = load_config()
    input_audit = pd.DataFrame([{"gate_status": "pass", "artifact_key": "x"}])
    contract = pd.DataFrame([{"validation_status": "pass"}])
    primary = pd.DataFrame(
        [
            {
                "oracle_id": "O5",
                "oracle_variant_id": "O5_perfect_utility_primary",
                "primary_support_gate": "pass",
                "topk_gate": "pass",
                "bootstrap_gate": "pass",
                "matched_base_gate": "pass",
                "materiality_gate": "pass",
                "mean_incremental_return": 0.03,
                "trimmed_mean_incremental_return": 0.03,
            }
        ]
    )
    delay = pd.DataFrame([{"delayed_curve_gate": "pass", "delayed_decision_diagnostic_flag": False}])
    capacity = pd.DataFrame([{"split_bucket": "robustness", "capacity_status": "appendix_only_nonblocking", "capacity_reconstruction_gate": "appendix_only", "capacity_constraint_gate": "not_evaluable_nonblocking"}])
    search = pd.DataFrame([{"search_accounting_gate": "pass"}])
    decision = r.build_decision(cfg, input_audit, contract, primary, delay, capacity, search).iloc[0]
    for col in r.AUTH_FALSE_COLUMNS:
        assert bool(decision[col]) is False
