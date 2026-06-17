from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = EXPERIMENT_DIR / "src"

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import run_11c_two_stage_observed_state_policy_replay as replay  # noqa: E402


def _config() -> dict:
    return {
        "scope": {
            "reference_slice": {
                "model_id": "regularized_logistic_false_repair_20d_l2_v1",
                "ablation_id": "full",
                "capacity_id": "keep_9000",
                "threshold_id": "keep_9000",
                "population_id": "10A__same_instrument_cooldown_10d",
                "denominator_id": "post_dedup_risk_on_r_core",
            }
        },
        "parameters": {
            "exit_contract_id": "common_exit_120d_with_risk_stop_v1",
            "trial_size_grid": [0.00, 0.10, 0.25],
            "upgrade_size_grid": [0.50, 1.00],
            "capacity_slots": [20, 50, 100],
            "primary_capacity_slots": 50,
        },
    }


def test_10c_blocked_manifest_uses_keep_9000_reference_slice_not_input_blocked() -> None:
    manifest = {
        "selected_capacity_id": None,
        "selected_threshold_id": None,
        "selected_cascade_status": "blocked",
    }

    spec = replay.select_10c_slice_mode(manifest, _config())

    assert spec["tenc_slice_mode"] == "keep_9000_reference_slice"
    assert spec["capacity_id"] == "keep_9000"
    assert spec["threshold_id"] == "keep_9000"
    assert spec["tenc_slice_selected_flag"] is False


def test_10c_supported_manifest_uses_selected_gate() -> None:
    manifest = {
        "selected_model_id": "m",
        "selected_capacity_id": "cap",
        "selected_threshold_id": "thr",
        "selected_population_id": "pop",
        "selected_denominator_id": "den",
        "selected_cascade_status": "supported",
        "selected_operating_point": {"ablation_id": "full"},
    }

    spec = replay.select_10c_slice_mode(manifest, _config())

    assert spec["tenc_slice_mode"] == "selected_gate"
    assert spec["capacity_id"] == "cap"
    assert spec["threshold_id"] == "thr"


def test_lane_construction_uses_10b_deployed_and_10c_reference_flags() -> None:
    frame = pd.DataFrame(
        {
            "tenb_rejected_flag": [False, False, True],
            "tenc_ref_rejected_flag": [False, True, True],
        }
    )

    out = replay.construct_lanes(frame)

    assert out["lane_id"].tolist() == [
        "lane_A_10C_ref_kept",
        "lane_B_10C_ref_rejected",
        "out_of_lane_10B_rejected",
    ]
    assert out["deployed_baseline_kept_flag"].tolist() == [True, True, False]


def test_sizing_grid_defines_upgrade_as_target_total_not_incremental() -> None:
    params = replay.Params.from_config(_config())

    grid = replay.valid_sizing_grid(params)
    combo = grid.loc[grid["trial_size"].eq(0.25) & grid["upgrade_size"].eq(1.00)].iloc[0]

    assert combo["valid_grid_flag"] is True or bool(combo["valid_grid_flag"])
    assert combo["upgrade_size_semantics"] == "target_total_position_size"
    assert combo["example_incremental_upgrade_order_size"] == 0.75


def test_trial_zero_b3_registry_marks_wait_confirm_equivalence() -> None:
    params = replay.Params.from_config(_config())
    registry = replay.build_arm_registry(params, ["S0_return_damage_basic"])

    trial_zero = registry.loc[
        registry["arm_id"].eq("B3_trial_then_upgrade_K3")
        & registry["trial_size"].eq(0.0)
        & registry["upgrade_size"].eq(1.0)
    ]

    assert not trial_zero.empty
    assert trial_zero["trial_zero_wait_confirm_equivalence_flag"].all()
    assert trial_zero["trial_zero_wait_confirm_equivalence_expected_flag"].all()


def test_trial_zero_b3_ledger_equals_b2_wait_confirm_for_same_target() -> None:
    dates = pd.date_range("2024-01-02", periods=130, freq="D").strftime("%Y-%m-%d")
    bars = pd.DataFrame(
        {
            "date": dates,
            "open": [10.0] * 130,
            "high": [10.2] * 130,
            "low": [9.9] * 130,
            "close": [10.1] * 130,
            "volume": [100.0] * 130,
            "money": [1000.0] * 130,
        }
    )
    bars["prev_close"] = bars["close"].shift(1)
    bars["range_pct"] = bars["high"] / bars["low"] - 1.0

    class DummyPriceCache:
        instrument_source = {"000001": "unit_test"}

        def load(self, instrument: str) -> pd.DataFrame:
            return bars

    row = pd.Series(
        {
            "policy_row_id": "r1",
            "sample_id": "s1",
            "selected_target_id": "t",
            "denominator_id": "d",
            "input_event_key": "e",
            "instrument": "000001",
            "event_t0_date": dates[0],
            "split": "train",
            "lane_id": "lane_A_10C_ref_kept",
            "winner_120_bool": False,
            "big_failure_proxy_bool": False,
            "fast_fail_10_bool": False,
            "false_repair_20_bool": False,
            "binding_canonical_event_id": "c1",
            "state_positive_S0_return_damage_basic": True,
        }
    )
    b2 = pd.Series(
        {
            "arm_id": "B2_wait_confirm_K3",
            "arm_variant_id": "B2_wait_confirm_K3__S0_return_damage_basic__target_1.00",
            "state_id": "S0_return_damage_basic",
            "trial_size": 0.0,
            "upgrade_size": 1.0,
        }
    )
    b3 = pd.Series(
        {
            "arm_id": "B3_trial_then_upgrade_K3",
            "arm_variant_id": "B3_trial_then_upgrade_K3__S0_return_damage_basic__trial_0.00__target_1.00",
            "state_id": "S0_return_damage_basic",
            "trial_size": 0.0,
            "upgrade_size": 1.0,
        }
    )

    out_b2 = replay.replay_row(row, b2, DummyPriceCache(), {"000001": "main_board"}, replay.Params())
    out_b3 = replay.replay_row(row, b3, DummyPriceCache(), {"000001": "main_board"}, replay.Params())

    for field in ["first_entry_date", "exit_date", "gross_pnl_full_notional", "exposure_days_full", "risk_stop_anchor_price"]:
        assert out_b2[field] == out_b3[field]


def test_weighted_average_cost_basis_recomputed_after_upgrade() -> None:
    anchor = replay.weighted_average_cost_after_upgrade(
        trial_size=0.25,
        trial_price=10.0,
        upgrade_order_size=0.75,
        upgrade_price=12.0,
    )

    expected = 1.0 / (0.25 / 10.0 + 0.75 / 12.0)
    assert abs(anchor - expected) < 1e-12


def test_observed_state_registry_forbids_label_overlap_primary_features() -> None:
    registry = replay.observed_state_feature_registry()
    forbidden = registry.loc[registry["feature_id"].astype(str).str.contains("winner_120|selected_fast_fail|forward_return", regex=True)]

    assert not forbidden.empty
    assert not forbidden["primary_policy_allowed_flag"].any()


def test_state_formulas_do_not_use_forbidden_features() -> None:
    states = replay.observed_state_definition_registry()

    assert not states["formula"].map(replay.formula_uses_forbidden_features).any()


def test_apply_state_definitions_uses_only_k3_observable_columns() -> None:
    matrix = pd.DataFrame(
        {
            "ep_ret_t0_to_K": [0.01, -0.01],
            "ep_max_drawdown_to_K": [-0.02, -0.02],
            "ep_close_vs_t0_close": [0.01, 0.02],
            "ep_breach_t0_low_through_K_flag": [False, False],
            "ep_close_above_t0_high_at_K_flag": [True, False],
            "ep_money_ratio_3d_vs_20d": [1.2, 2.0],
            "entry_t0p4_executable_flag": [True, True],
        }
    )

    out = replay.apply_state_definitions(matrix)

    assert out["state_positive_S0_return_damage_basic"].tolist() == [True, False]
    assert out["state_positive_S1_reclaim_damage"].tolist() == [True, True]
    assert out["state_positive_S2_return_reclaim_liquidity"].tolist() == [True, False]


def test_validation_low_power_makes_validation_ci_readout_only() -> None:
    params = replay.Params()
    base = pd.DataFrame(
        {
            "split": ["validation"] * 20,
            "winner_120_bool": [True] * 16 + [False] * 4,
            "state_positive_S0_return_damage_basic": [True] * 20,
        }
    )

    assert replay.validation_low_power("B2_wait_confirm_K3__S0_return_damage_basic__target_1.00", base, params)


def test_config_declares_required_exit_contract() -> None:
    config = replay.load_yaml(replay.CONFIG_PATH)

    assert config["parameters"]["exit_contract_id"] == "common_exit_120d_with_risk_stop_v1"
    assert replay.Params.from_config(config).exit_contract_id == "common_exit_120d_with_risk_stop_v1"


def test_artifact_metadata_records_row_count_and_schema_for_cache(tmp_path: Path) -> None:
    path = tmp_path / "cache.parquet"
    pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).to_parquet(path, index=False)

    meta = replay.artifact_metadata(path)

    assert meta["row_count"] == 2
    assert meta["sha256"]
    assert {field["name"] for field in meta["schema"]} == {"a", "b"}


def test_bootstrap_uses_distinct_resamples_across_iterations() -> None:
    rows = []
    pnl_by_inst = {"A": 0.04, "B": -0.02, "C": 0.01, "D": -0.01}
    exp_by_inst = {"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0}
    for split in ["train", "validation", "robustness"]:
        for inst, pnl in pnl_by_inst.items():
            exposure = exp_by_inst[inst]
            rows.append(
                {
                    "arm_variant_id": "B2_wait_confirm_K3__S0_return_damage_basic__target_1.00",
                    "arm_id": "B2_wait_confirm_K3",
                    "split": split,
                    "capacity_slots": 50,
                    "instrument": inst,
                    "portfolio_accepted_flag": True,
                    "gross_pnl_full_notional": pnl,
                    "buy_notional_full": 0.0,
                    "sell_notional_full": 0.0,
                    "turnover_notional_full": 0.0,
                    "portfolio_notional_scale": 1.0,
                    "exposure_days_full": exposure,
                }
            )
            rows.append(
                {
                    "arm_variant_id": "B0_deployed_baseline__full",
                    "arm_id": "B0_deployed_baseline",
                    "split": split,
                    "capacity_slots": 50,
                    "instrument": inst,
                    "portfolio_accepted_flag": True,
                    "gross_pnl_full_notional": 0.0,
                    "buy_notional_full": 0.0,
                    "sell_notional_full": 0.0,
                    "turnover_notional_full": 0.0,
                    "portfolio_notional_scale": 1.0,
                    "exposure_days_full": exposure,
                }
            )
    ledger = pd.DataFrame(rows)
    params = replay.Params(bootstrap_n=200)

    ci, samples = replay.build_bootstrap_ci(
        ledger,
        "B2_wait_confirm_K3__S0_return_damage_basic__target_1.00",
        params,
    )

    assert ci["sample_unique_metric_n"].min() > 1
    assert samples.groupby("split")["net_ev_per_exposure_day_lift_vs_B0"].nunique().min() > 1


def test_11b_statistics_incomplete_ceiling_precedes_positive_status() -> None:
    final_status, reasons = replay.final_status_decision(
        replay.FINAL_SUPPORTED,
        ["11B_statistics_incomplete:risk_on_pre_pit_retention_recon_diff_gt_ceiling"],
        "B2_wait_confirm_K3__S0_return_damage_basic__target_1.00",
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        True,
    )

    assert final_status == replay.FINAL_INCOMPLETE
    assert "11B_statistics_incomplete:risk_on_pre_pit_retention_recon_diff_gt_ceiling" in reasons


def test_limit_locked_proxy_fails_closed_for_buy_and_sell() -> None:
    bars = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "open": [10.0, 10.96, 9.90],
            "high": [10.1, 10.96, 9.90],
            "low": [9.9, 10.96, 9.90],
            "close": [10.0, 10.96, 9.90],
            "volume": [100.0, 100.0, 100.0],
            "money": [1000.0, 1000.0, 1000.0],
            "prev_close": [None, 10.0, 10.96],
        }
    )

    buy_ok, buy_reason, _, _ = replay.action_fill_status(bars, 1, "buy", "main_board")
    sell_ok, sell_reason, _, _ = replay.action_fill_status(bars, 2, "sell", "main_board")

    assert not buy_ok
    assert buy_reason == "buy_unfilled_limit_up_locked"
    assert not sell_ok
    assert sell_reason == "sell_unfilled_limit_down_locked"
