from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
SCRIPT = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17b_oracle_ladder_replay.py"
CONFIG = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic/configs/config_17b_oracle_ladder_replay.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_17b_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


def load_config():
    return r.load_config(CONFIG)


def minimal_row(frame_return: float, drawdown: float = -0.2, label: str = "negative") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "forward_return_h20": frame_return,
                "realized_h20_payoff": frame_return,
                "signed_max_drawdown_h20": drawdown,
                "label_class": label,
            }
        ]
    )


def pass_frame(column: str) -> pd.DataFrame:
    return pd.DataFrame([{column: "pass"}])


def decision_summary_rows(values: dict[str, tuple[float, float]]) -> pd.DataFrame:
    rows = []
    for variant, (trimmed, mean) in values.items():
        rows.append(
            {
                "oracle_id": variant.split("_")[0],
                "oracle_variant_id": variant,
                "split_bucket": "robustness",
                "cost_bps": 50,
                "q_defend": 0.0,
                "trimmed_mean_incremental_return": trimmed,
                "mean_incremental_return": mean,
                "ladder_metric_gate": "pass",
            }
        )
    return pd.DataFrame(rows)


def test_17a_ready_decision_is_required_but_not_sufficient():
    cfg = load_config()
    audit = r.build_input_gate_audit(cfg, r.resolve_paths(cfg))
    assert set(audit["gate_status"]) == {"pass"}
    assert "seventeen_a_decision" in set(audit["artifact_key"])
    assert "upstream_16e_utility_panel" in set(audit["artifact_key"])


def test_17a_independent_contract_validation_covers_machine_gate_artifacts():
    cfg = load_config()
    validation = r.build_17a_contract_validation_audit(cfg, r.resolve_paths(cfg))
    assert set(validation["validation_status"]) == {"pass"}
    artifact_keys = set(validation["artifact_key"])
    assert {
        "seventeen_a_action_semantics_audit",
        "seventeen_a_replay_price_path_audit",
        "seventeen_a_delayed_materialization_audit",
        "seventeen_a_input_artifact_audit",
        "seventeen_a_replay_engine_manifest",
        "seventeen_a_input_artifact_manifest",
    }.issubset(artifact_keys)


def test_denominator_counts_match_17a_binding_for_labelable_and_binary_oracles():
    cfg = load_config()
    panel = r.read_table(r.resolve_paths(cfg)["upstream_16e_utility_panel"])
    assert len(panel) == cfg["source_panel"]["expected_raw_rows"]
    base = r.load_primary_base_panel(cfg, panel)
    assert len(base) == cfg["source_panel"]["expected_primary_rows"]
    assert base.duplicated(list(r.PRIMARY_ROW_KEY)).sum() == 0
    assert base["cluster_split_bucket"].value_counts().to_dict()["robustness"] == 2496


def test_o2_drawdown_threshold_uses_signed_negative_drawdown_not_abs_field():
    spec = {"rule": "drawdown_threshold", "drawdown_threshold": -0.10}
    rows = pd.concat(
        [
            minimal_row(-0.01, drawdown=-0.20),
            minimal_row(-0.01, drawdown=-0.05),
        ],
        ignore_index=True,
    )
    actions = r.action_for_spec(spec, rows, q_defend=0.0, cost_bps=50)
    assert actions.tolist() == ["defend", "continue"]


def test_o5_partial_defend_recomputes_action_by_variant_not_full_defend_set():
    spec = {"rule": "perfect_utility"}
    row = minimal_row(-0.008)
    full_defend_action = r.action_for_spec(spec, row, q_defend=0.0, cost_bps=50)[0]
    partial_defend_action = r.action_for_spec(spec, row, q_defend=0.5, cost_bps=50)[0]
    assert full_defend_action == "defend"
    assert partial_defend_action == "continue"


def test_o5_action_selection_proof_recomputes_formula_per_variant():
    rows = []
    for q_defend, action in [(0.0, "defend"), (0.5, "continue")]:
        rows.append(
            {
                "step_id": "s1",
                "label_id": "l1",
                "threshold_id": "t1",
                "instrument": "000001",
                "episode_cluster_id": "c1",
                "horizon_sessions": 20,
                "step_index": 1,
                "step_start_date": "2020-01-01",
                "step_end_date": "2020-02-01",
                "cluster_split_bucket": "robustness",
                "oracle_id": "O5",
                "cost_bps": 50,
                "q_defend": q_defend,
                "forward_return_h20": -0.008,
                "oracle_action": action,
            }
        )
    proof = r.build_o5_action_selection_proof(pd.DataFrame(rows))
    assert set(proof["formula_recompute_gate"]) == {"pass"}
    partial = proof.loc[proof["q_defend"].eq(0.5)].iloc[0]
    assert partial["nonreference_full_defend_reuse_gate"] == "pass"
    assert bool(partial["action_set_equal_to_full_defend_reference"]) is False


def test_oracle_variant_ids_are_unique_and_manifested():
    cfg = load_config()
    thresholds = pd.DataFrame(
        [
            {
                "threshold_id": "high_upside_top30_stress",
                "oracle_variant_id": "O4_high_upside_top30_stress",
                "train_absolute_payoff_cutoff": 0.1,
            }
        ]
    )
    specs = r.oracle_specs(cfg, thresholds)
    variant_ids = [spec["oracle_variant_id"] for spec in specs]
    assert len(variant_ids) == len(set(variant_ids))
    assert {"O1_negative_primary", "O2_dd_10pct_primary", "O4_label_positive_primary", "O5_perfect_utility_primary"}.issubset(
        set(variant_ids)
    )


def test_17b_ready_gate_requires_25bps_mean_materiality_floor():
    cfg = load_config()
    summary = decision_summary_rows(
        {
            "O1_negative_primary": (0.0, 0.0),
            "O2_dd_10pct_primary": (0.0, 0.0),
            "O4_label_positive_primary": (0.0, 0.0),
            "O5_perfect_utility_primary": (0.001, 0.001),
        }
    )
    decision = r.build_decision(
        cfg,
        "pass",
        "",
        pass_frame("row_replay_gate"),
        summary,
        pass_frame("six_cell_gate"),
        pass_frame("frontier_gate"),
        pass_frame("neutral_stress_gate"),
        pass_frame("threshold_freeze_gate"),
        r.build_search_accounting_audit(),
        pd.Series({"o6_status_for_17b": "appendix_only_nonblocking"}),
    )
    assert decision.iloc[0]["decision_state"] == r.DECISION_NO_VALUE


def test_nonprimary_cost_or_stress_variant_cannot_rescue_ready_decision():
    cfg = load_config()
    summary = decision_summary_rows(
        {
            "O1_negative_primary": (0.0, 0.0),
            "O2_dd_10pct_primary": (0.0, 0.0),
            "O4_label_positive_primary": (0.0, 0.0),
            "O5_perfect_utility_primary": (0.0, 0.0),
        }
    )
    summary = pd.concat(
        [
            summary,
            pd.DataFrame(
                [
                    {
                        "oracle_id": "O4",
                        "oracle_variant_id": "O4_high_upside_top10_stress",
                        "split_bucket": "robustness",
                        "cost_bps": 0,
                        "q_defend": 0.5,
                        "trimmed_mean_incremental_return": 0.5,
                        "mean_incremental_return": 0.5,
                        "ladder_metric_gate": "pass",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    decision = r.build_decision(
        cfg,
        "pass",
        "",
        pass_frame("row_replay_gate"),
        summary,
        pass_frame("six_cell_gate"),
        pass_frame("frontier_gate"),
        pass_frame("neutral_stress_gate"),
        pass_frame("threshold_freeze_gate"),
        r.build_search_accounting_audit(),
        pd.Series({"o6_status_for_17b": "appendix_only_nonblocking"}),
    )
    assert decision.iloc[0]["decision_state"] == r.DECISION_NO_VALUE


def test_canonical_field_mapping_reconciles_continue_return_and_qfq_return():
    mapping = r.canonical_field_mapping()
    assert mapping["forward_return_h20"]["source"] == "continue_return_h20"
    assert mapping["signed_max_drawdown_h20"]["source"] == "continue_max_drawdown_h20"
    assert "never used for O2" in mapping["drawdown_avoided_abs"]["rule"]


def test_no_validation_or_robustness_selection_flags_are_true():
    search = r.build_search_accounting_audit().iloc[0]
    assert search["search_accounting_gate"] == "pass"
    assert bool(search["no_validation_selection"]) is True
    assert bool(search["no_robustness_tuning"]) is True
    assert bool(search["no_live_trading_authorized"]) is True
