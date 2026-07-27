from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


EP23 = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((EP23 / "config.yaml").read_text(encoding="utf-8"))


def load_preflight_module():
    path = EP23 / "src/run_23a_rdagent_pit_preflight.py"
    spec = importlib.util.spec_from_file_location("ep23_preflight", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_baseline_module():
    path = EP23 / "src/run_23b_alpha20_lgbm_baseline.py"
    spec = importlib.util.spec_from_file_location("ep23_baseline", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_execution_bridge_module():
    path = EP23 / "src/run_23f_pit_execution_big_winner_bridge.py"
    spec = importlib.util.spec_from_file_location("ep23_execution_bridge", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_alpha20_contract_has_exactly_twenty_unique_factors():
    assert len(CONFIG["alpha20"]) == 20
    assert len(set(CONFIG["alpha20"])) == 20


def test_split_order_and_historical_evidence_ceiling():
    split = CONFIG["split"]
    assert split["train"][1] < split["validation"][0]
    assert split["validation"][1] < split["historical_test"][0]
    assert split["evidence_class"] == (
        "design_contaminated_historical_real_market_evidence"
    )


def test_paper_and_executable_labels_are_separate():
    labels = CONFIG["labels"]
    assert labels["paper_proxy"]["expression"] != labels["executable_bridge"][
        "expression"
    ]
    assert labels["paper_proxy"]["semantics"] == "close_t1_to_close_t2"
    assert labels["executable_bridge"]["semantics"] == (
        "next_open_t1_to_next_open_t2"
    )


def test_normalize_feature_frame_produces_expected_index():
    module = load_preflight_module()
    index = pd.MultiIndex.from_tuples(
        [("SH600000", pd.Timestamp("2024-01-02"))],
        names=["instrument", "datetime"],
    )
    frame = pd.DataFrame({"x": [1.0]}, index=index)
    normalized = module.normalize_feature_frame(frame)
    assert normalized.index.names == ["datetime", "instrument"]


def test_research_plan_refuses_exact_replication_claim():
    text = (EP23 / "research_plan.md").read_text(encoding="utf-8")
    assert "paper_protocol_grounded_pit_universe_project_adaptation" in text
    assert "exact_replication" in text
    assert "ready_for_agent_loop=true" in text


def test_cross_sectional_zscore_is_per_date():
    module = load_baseline_module()
    index = pd.MultiIndex.from_product(
        [
            [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")],
            ["A", "B", "C"],
        ],
        names=["datetime", "instrument"],
    )
    values = pd.Series([1.0, 2.0, 3.0, 10.0, 20.0, 30.0], index=index)
    result = module.cross_sectional_zscore(values)
    grouped = result.groupby(level="datetime")
    assert grouped.mean().abs().max() < 1e-12
    assert (grouped.std(ddof=0) - 1.0).abs().max() < 1e-12


def test_topk_dropout_costs_initial_purchase_and_retention():
    module = load_baseline_module()
    index = pd.MultiIndex.from_product(
        [
            [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")],
            ["A", "B", "C"],
        ],
        names=["datetime", "instrument"],
    )
    frame = pd.DataFrame(
        {
            "prediction": [3.0, 2.0, 1.0, 3.0, 2.0, 1.0],
            "label": [0.03, 0.02, 0.01, 0.04, 0.02, 0.01],
        },
        index=index,
    )
    result = module.topk_dropout_returns(
        frame,
        prediction_column="prediction",
        label_column="label",
        topk=2,
        n_drop=1,
        buy_cost=0.0005,
        sell_cost=0.0015,
    )
    assert result.iloc[0]["buy_fraction"] == 1.0
    assert result.iloc[0]["sell_fraction"] == 0.0
    assert result.iloc[1]["holdings"] == 2


def test_execution_bridge_seed_selection_is_validation_only():
    bridge = CONFIG["execution_bridge"]
    assert bridge["primary_seed_selection_metric"] == "validation_paper_proxy_ic"
    assert bridge["primary_seed_selection_rule"] == (
        "max_metric_then_smallest_seed"
    )
    assert bridge["primary_topk"] == 50
    assert bridge["sensitivity_topk"] == 30


def test_execution_bridge_rounding_and_statutory_costs():
    module = load_execution_bridge_module()
    assert module.round_half_up_to_tick(10.005, 0.01) == 10.01
    costs = module.order_costs(
        "sell",
        100_000.0,
        0.1,
        CONFIG["execution_bridge"],
    )
    assert np.isclose(costs["commission_cny"], 25.0)
    assert np.isclose(costs["stamp_tax_cny"], 50.0)
    assert np.isclose(costs["transfer_fee_cny"], 1.0)
    assert np.isclose(costs["slippage_cny"], 50.0)
    assert np.isclose(costs["total_cost_cny"], 126.0)


def test_23f_output_keeps_failed_utility_gate_if_materialized():
    output = EP23 / "outputs/23F_pit_execution_big_winner_bridge"
    if not output.is_dir():
        return
    gates = pd.read_csv(output / "gate_audit.csv")
    values = (
        gates.set_index("gate")["passed"].astype(str).str.lower().eq("true")
    )
    assert values["executable_no_sign_reversal_gate"]
    assert values["five_seed_executable_direction_gate"]
    assert not values["right_tail_enrichment_gate"]
    manifest = yaml.safe_load((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["deployment_authorized"] is False
    assert manifest["decision"] == "model_branch_only_supported"
