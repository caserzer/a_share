from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    EXPERIMENT_ROOT
    / "src/run_20b_p4_d8_d10_sector_crowding_cost_stoploss_sensitivity.py"
)
CONFIG_PATH = (
    EXPERIMENT_ROOT
    / "configs/config_20b_p4_d8_d10_sector_crowding_cost_stoploss_sensitivity.yaml"
)
SPEC = importlib.util.spec_from_file_location("portsens_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def test_frozen_config_identity_authority_and_unknown_key_fail_closed() -> None:
    config, path = runner.load_config(CONFIG_PATH)
    assert path == CONFIG_PATH
    assert config["authorization"] == {
        "requirement_generation_authorized": True,
        "requirement_execution_authorized": True,
        "implementation_authorized": True,
        "historical_outcome_execution_authorized": True,
        "portfolio_replay_authorized": True,
        "deployment_authorized": False,
    }
    assert (
        config["board_concentration"]["reference_universe_dependency"]
        == "retrospective_full_sample_universe_dependency"
    )
    runner.require_historical_authority(config)
    changed = copy.deepcopy(config)
    changed["population"]["unregistered_override"] = True
    with pytest.raises(runner.ContractError, match="config keys differ"):
        runner.validate_config(changed)


def test_cli_frozen_output_override_gate_creates_no_scratch_or_output(
    tmp_path: Path,
) -> None:
    config, _ = runner.load_config(CONFIG_PATH)
    forbidden_output = tmp_path / "override-output"
    frozen_scratch = runner.resolved_paths(config)["replay_a_scratch_root"]
    scratch_before = (
        sorted(
            (
                path.relative_to(frozen_scratch).as_posix(),
                path.stat().st_size,
                path.stat().st_mtime_ns,
            )
            for path in frozen_scratch.rglob("*")
            if path.is_file()
        )
        if frozen_scratch.exists()
        else None
    )
    assert not forbidden_output.exists()
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--config",
            str(CONFIG_PATH),
            "--output-root",
            str(forbidden_output),
            "--replay-id",
            "replay_a",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert completed.returncode == 2
    stderr = json.loads(completed.stderr)
    assert stderr["decision_state"] == "20B_P4_PORTSENS_launch_blocked"
    assert stderr["publication_state"] == "NO_PUBLISHED_BUNDLE"
    assert not forbidden_output.exists()
    scratch_after = (
        sorted(
            (
                path.relative_to(frozen_scratch).as_posix(),
                path.stat().st_size,
                path.stat().st_mtime_ns,
            )
            for path in frozen_scratch.rglob("*")
            if path.is_file()
        )
        if frozen_scratch.exists()
        else None
    )
    assert scratch_after == scratch_before


def test_policy_cost_and_comparison_registries_are_exact() -> None:
    policies = runner.build_policy_arm_registry()
    costs = runner.build_cost_scenario_registry()
    comparisons = runner.build_paired_comparison_registry()
    assert len(policies) == 2 * 3 * 3 * 5 == 90
    assert policies["policy_id"].nunique() == 90
    assert set(policies["bucket_id"]) == {8, 9, 10}
    assert set(costs["cost_scenario_id"]) == set(runner.COST_IDS)
    assert len(costs) == 6
    assert len(comparisons) == 284
    assert comparisons["comparison_id"].is_unique
    assert comparisons["only_one_dimension_changed"].all()
    primary = comparisons[comparisons["primary_OFAT"]]
    assert len(primary) == 14
    assert set(primary["changed_dimension"]) == {
        "bucket_id",
        "sector_tilt_lambda",
        "stop_threshold",
        "cost_scenario_id",
    }


def _board_fixture() -> tuple[list[str], pd.DataFrame]:
    reference = [f"SZ{i:06d}" for i in range(1, 17)]
    rows: list[dict[str, str]] = []
    for board, members in {
        "A": range(1, 11),
        "B_DUPLICATE": range(1, 11),
        "C": range(6, 16),
        "SMALL": range(1, 4),
    }.items():
        rows.extend(
            {"board_ts_code": board, "con_code": f"{item:06d}.SZ"} for item in members
        )
    return reference, pd.DataFrame(rows)


def test_board_dictionary_fractional_duplicate_and_no_board_semantics() -> None:
    reference, source = _board_fixture()
    registry, membership, audit = runner.build_board_dictionary(reference, source, 10)
    retained = set(registry.loc[registry["retained"], "retained_board_id"])
    assert retained == {"A", "C", runner.NO_BOARD}
    assert not registry.loc[
        registry["source_board_ts_code"].eq("B_DUPLICATE"), "retained"
    ].item()
    assert not registry.loc[
        registry["source_board_ts_code"].eq("SMALL"), "minimum_member_pass"
    ].item()
    sums = membership.groupby("instrument_id")["membership_weight"].sum()
    np.testing.assert_allclose(sums, 1.0, rtol=0.0, atol=1e-12)
    overlap = membership[
        membership["instrument_id"].isin([f"SZ{i:06d}" for i in range(6, 11)])
    ]
    assert set(overlap["membership_weight"]) == {0.5}
    no_board = membership[membership["instrument_id"].eq("SZ000016")]
    assert no_board[["retained_board_id", "membership_weight"]].iloc[0].tolist() == [
        runner.NO_BOARD,
        1.0,
    ]
    assert (
        audit.iloc[0]["board_reference_universe_dependency"]
        == "retrospective_full_sample_universe_dependency"
    )
    assert not bool(audit.iloc[0]["historical_PIT_industry_claim_allowed"])


def test_overrepresentation_percentiles_and_no_board_neutral_score() -> None:
    reference, source = _board_fixture()
    _, membership, _ = runner.build_board_dictionary(reference, source, 10)
    assignment = pd.DataFrame(
        {
            "scored_model_id": "S0_SELECTED_FULL",
            "decision_date": pd.Timestamp("2025-01-31"),
            "instrument_id": reference,
            "bucket_id": [8] * 5 + [9] * 5 + [10] * 6,
        }
    )
    board, scores = runner.compute_overrepresentation(assignment, membership)
    assert list(board.columns) == runner.BOARD_OVERREP_COLUMNS
    no_board = board[board["retained_board_id"].eq(runner.NO_BOARD)]
    assert (no_board["board_overrepresentation_pct"] == 0.5).all()
    assert not no_board["percentile_evaluable"].any()
    real = board[board["retained_board_id"].ne(runner.NO_BOARD)]
    assert real["board_overrepresentation_pct"].between(0.0, 1.0).all()
    neutral = scores[scores["instrument_id"].eq("SZ000016")]
    assert neutral["stock_concentration_tilt_score"].item() == 0.5


def _target_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    assignment_rows: list[dict[str, object]] = []
    score_rows: list[dict[str, object]] = []
    for model in runner.MODEL_IDS:
        for bucket in runner.BUCKET_IDS:
            for index in range(20):
                instrument = f"SZ{bucket}{index:05d}"
                key = {
                    "scored_model_id": model,
                    "decision_date": pd.Timestamp("2025-01-31"),
                    "bucket_id": bucket,
                    "instrument_id": instrument,
                }
                assignment_rows.append({**key, "nominal_bucket_n": 20})
                score_rows.append(
                    {
                        **key,
                        "stock_concentration_tilt_score": index / 19.0,
                        "board_membership_n": 1,
                    }
                )
    return pd.DataFrame(assignment_rows), pd.DataFrame(score_rows)


def test_target_weights_equal_weight_monotonic_cap_and_exclusive_buckets() -> None:
    assignment, scores = _target_fixture()
    targets = runner.build_target_weights(assignment, scores, "a" * 64, "b" * 64)
    assert targets["policy_id"].nunique() == 90
    sums = targets.groupby(["policy_id", "decision_date"])["target_weight"].sum()
    np.testing.assert_allclose(sums, 1.0, rtol=0.0, atol=1e-12)
    assert targets["target_weight"].max() <= 0.10 + 1e-15
    equal = targets[targets["policy_id"].eq("S0_SELECTED_FULL__D8__L000__STOPNONE")]
    assert np.array_equal(equal["target_weight"].to_numpy(), np.full(20, 0.05))
    tilted = targets[
        targets["policy_id"].eq("S0_SELECTED_FULL__D8__L100__STOPNONE")
    ].sort_values("stock_concentration_tilt_score")
    assert tilted["target_weight"].is_monotonic_increasing
    for policy_id, group in targets.groupby("policy_id"):
        encoded_bucket = int(policy_id.split("__D", 1)[1].split("__", 1)[0])
        assert set(group["bucket_id"]) == {encoded_bucket}


def test_target_turnover_uses_union_and_first_zero_vector() -> None:
    targets = pd.DataFrame(
        [
            {
                "policy_id": "P",
                "decision_date": "2025-01-31",
                "instrument_id": "A",
                "target_weight": 0.5,
            },
            {
                "policy_id": "P",
                "decision_date": "2025-01-31",
                "instrument_id": "B",
                "target_weight": 0.5,
            },
            {
                "policy_id": "P",
                "decision_date": "2025-02-28",
                "instrument_id": "B",
                "target_weight": 0.5,
            },
            {
                "policy_id": "P",
                "decision_date": "2025-02-28",
                "instrument_id": "C",
                "target_weight": 0.5,
            },
        ]
    )
    turnover = runner.target_turnover_series(targets)
    np.testing.assert_allclose(turnover["target_one_way_turnover"], [0.5, 0.5])


def test_cost_basis_stop_mapping_fill_domain_and_overshoot_inputs() -> None:
    assert runner.update_cost_basis(100, 10.0, 100, 12.0) == 11.0
    assert runner.update_cost_basis(200, 11.0, 0, 9.0) == 11.0
    raw = {"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0}
    qfq = {"open": 5.0, "high": 5.5, "low": 4.5, "close": 5.0}
    mapped = runner.map_intraday_stop(4.754, raw, qfq, 0.01)
    assert mapped.factor == 0.5
    assert mapped.raw_trigger_tick == 9.5
    assert mapped.qfq_fill == 4.75
    assert mapped.mapping_pass
    outside = runner.map_intraday_stop(4.0, raw, qfq, 0.01)
    assert outside.raw_trigger_tick == 8.0
    assert not outside.fill_domain_pass
    bad_qfq = {**qfq, "close": 5.2}
    spread = runner.map_intraday_stop(4.75, raw, bad_qfq, 0.01)
    assert spread.warning
    assert not spread.factor_mapping_pass
    assert (
        runner.preserve_pending_stop_reason(
            "stop:SPELL__STOP0001", "limit_down_blocked"
        )
        == "stop:SPELL__STOP0001"
    )
    assert (
        runner.preserve_pending_stop_reason("", "limit_down_blocked")
        == "limit_down_blocked"
    )


def test_stateful_stop_latch_survives_limit_down_and_fills_next_open() -> None:
    config, _ = runner.load_config(CONFIG_PATH)
    config = copy.deepcopy(config)
    config["population"]["ledger_end_date"] = "2025-08-03"
    instrument = "SZ000001"
    calendar = pd.DatetimeIndex(
        pd.to_datetime(["2025-07-31", "2025-08-01", "2025-08-02", "2025-08-03"])
    )
    prices = {
        "2025-07-31": (10.0, 10.0, 10.0, 10.0, 10.0),
        "2025-08-01": (10.0, 10.0, 10.0, 10.0, 10.0),
        "2025-08-02": (9.0, 9.0, 9.0, 9.0, 10.0),
        "2025-08-03": (8.5, 8.7, 8.4, 8.6, 9.0),
    }
    market_rows = []
    for date, (open_, high, low, close, previous) in prices.items():
        market_rows.append(
            {
                "trade_date": pd.Timestamp(date),
                "instrument_id": instrument,
                "raw_open": open_,
                "raw_high": high,
                "raw_low": low,
                "raw_close": close,
                "qfq_open": open_,
                "qfq_high": high,
                "qfq_low": low,
                "qfq_close": close,
                "raw_qfq_factor": 1.0,
                "relative_ratio_spread": 0.0,
                "mapping_warning": False,
                "factor_mapping_pass": True,
                "previous_raw_close": previous,
            }
        )
    market = pd.DataFrame(market_rows).set_index(["trade_date", "instrument_id"])
    context = pd.DataFrame(
        [
            {
                "trade_date": date,
                "instrument_id": instrument,
                "is_listed": True,
                "is_suspended": False,
                "no_limit_flag": False,
                "daily_limit_up_rate": 0.10,
                "daily_limit_down_rate": 0.10,
                "tick_size": 0.01,
                "minimum_buy_order_shares": 100,
                "buy_order_increment_shares": 100,
                "transfer_fee_buy_bps": 0.0,
                "transfer_fee_sell_bps": 0.0,
            }
            for date in calendar
        ]
    ).set_index(["trade_date", "instrument_id"])
    targets = pd.DataFrame(
        [
            {
                "policy_id": "S0_SELECTED_FULL__D10__L000__STOP10",
                "decision_date": pd.Timestamp("2025-07-31"),
                "instrument_id": instrument,
                "target_weight": 1.0,
                "stock_concentration_tilt_score": 0.5,
            }
        ]
    )
    simulation = runner.simulate_policy(
        {
            "policy_id": "S0_SELECTED_FULL__D10__L000__STOP10",
            "stop_threshold": 0.10,
        },
        targets,
        calendar,
        market,
        context,
        config,
    )
    stop = simulation["stop_events"].iloc[0]
    assert stop["trigger_date"] == pd.Timestamp("2025-08-02")
    assert stop["fill_date"] == pd.Timestamp("2025-08-03")
    assert stop["fill_status"] == "filled_after_delay"
    assert stop["trigger_to_fill_delay_sessions"] == 1
    execution = simulation["execution"]
    blocked = execution[
        execution["trade_date"].eq(pd.Timestamp("2025-08-02"))
        & execution["event_type"].eq("stop_trigger")
    ].iloc[0]
    assert blocked["fill_status"] == "blocked_unfilled"
    assert blocked["blocking_reason"] == "limit_down_blocked"
    assert simulation["final_positions"] == {}


def test_cost_components_break_even_and_fixed_fill_shadows() -> None:
    buy = runner.order_costs("buy", 1_000.0, 5.0, 0.2)
    sell = runner.order_costs("sell", 1_000.0, 5.0, 0.2)
    assert buy["commission_cny"] == 5.0
    assert buy["stamp_tax_cny"] == 0.0
    assert sell["stamp_tax_cny"] == 0.5
    root, status = runner.break_even_bisection(
        11_000_000.0, 10_000_000.0, 0.0, 10_000_000.0
    )
    assert status == "root_found"
    assert root == pytest.approx(1000.0, abs=1e-6)
    undefined, undefined_status = runner.break_even_bisection(
        11_000_000.0, 10_000_000.0, 0.0, 0.0
    )
    assert np.isnan(undefined)
    assert undefined_status == "undefined_no_turnover"

    config, _ = runner.load_config(CONFIG_PATH)
    reference_cost = runner.order_costs("buy", 1_000.0, 5.0, 0.0)
    simulation = {
        "cost_events": pd.DataFrame(
            [
                {
                    "policy_id": "P",
                    "trade_date": pd.Timestamp("2025-01-02"),
                    "event_sequence": 1,
                    "instrument_id": "SZ000001",
                    "side": "buy",
                    "executed_shares": 100.0,
                    "executed_notional": 1_000.0,
                    "transfer_fee_bps": 0.0,
                }
            ]
        ),
        "reference_daily": pd.DataFrame(
            [
                {
                    "policy_id": "P",
                    "trade_date": pd.Timestamp("2025-01-02"),
                    "reference_net_cash": 9_000.0
                    - reference_cost["total_event_cost_cny"],
                    "reference_cost_cumulative": reference_cost["total_event_cost_cny"],
                    "marked_position_value": 1_000.0,
                    "reference_net_NAV": 10_000.0
                    - reference_cost["total_event_cost_cny"],
                    "locked_capital_weight": 0.0,
                }
            ]
        ),
    }
    cost, nav = runner.build_cost_shadows(simulation, config)
    assert len(cost) == 6
    assert nav["cost_scenario_id"].nunique() == 6
    gross = nav[nav["cost_scenario_id"].eq("GROSS")].iloc[0]
    reference = nav[nav["cost_scenario_id"].eq("SLIP005")].iloc[0]
    assert gross["scenario_cost_liability"] == 0.0
    assert (
        reference["scenario_NAV"]
        == simulation["reference_daily"].iloc[0]["reference_net_NAV"]
    )


def test_chinext_st_rule_is_exactly_registered_at_twenty_percent() -> None:
    config, _ = runner.load_config(CONFIG_PATH)
    rules = pd.read_csv(runner.resolved_paths(config)["MARKET_RULE_REGISTRY_FILE"])
    matched = runner.match_market_rule(
        rules,
        exchange="SZ",
        board_bucket="chinext",
        is_st=True,
        trade_date=pd.Timestamp("2025-04-24"),
        listing_session=2049,
    )
    assert matched["rule_id"] == "chinext_st_after_reform_post_transfer_cut"
    assert matched["daily_limit_up_rate"] == pytest.approx(0.20)
    assert matched["daily_limit_down_rate"] == pytest.approx(0.20)


def test_bootstrap_is_frozen_pcg64_circular_and_complete_calendar_only() -> None:
    values = np.arange(21, dtype=float) / 100.0
    first = runner.circular_moving_block_bootstrap(
        values, np.random.Generator(np.random.PCG64(20260716)), repetitions=20
    )
    second = runner.circular_moving_block_bootstrap(
        values, np.random.Generator(np.random.PCG64(20260716)), repetitions=20
    )
    np.testing.assert_array_equal(first, second)
    with pytest.raises(runner.ContractError, match="21 finite"):
        runner.circular_moving_block_bootstrap(
            values[:-1], np.random.Generator(np.random.PCG64(20260716)), repetitions=1
        )


def test_concentration_excludes_no_board_from_hhi_and_reports_coverage() -> None:
    membership = pd.DataFrame(
        [
            {"instrument_id": "A", "retained_board_id": "X", "membership_weight": 1.0},
            {
                "instrument_id": "B",
                "retained_board_id": runner.NO_BOARD,
                "membership_weight": 1.0,
            },
        ]
    )
    metrics = runner.concentration_metrics(
        {"A": 0.6, "B": 0.4}, membership, {"A": 1.0, "B": 0.5}
    )
    assert metrics["board_HHI"] == 1.0
    assert metrics["top1_board_weight"] == 1.0
    assert metrics["no_board_position_weight"] == 0.4
    assert metrics["classified_board_coverage_ratio"] == 0.6
    assert metrics["effective_holdings"] == pytest.approx(1 / (0.6**2 + 0.4**2))


def test_profile_file_sets_seal_no_self_hash_and_determinism(tmp_path: Path) -> None:
    config, _ = runner.load_config(CONFIG_PATH)
    runner.validate_profile_contract(config["output_contract"])
    p0 = runner.profile_file_set(config, "P0_PREFLIGHT_BLOCKED")
    assert p0 == set(config["output_contract"]["artifact_groups"]["G0_FINAL_AUDIT"])
    assert len(runner.profile_file_set(config, "P5_SENSITIVITY_MATERIALIZED")) == 30

    build = tmp_path / "candidate.building"
    output = tmp_path / "sealed"
    runner.write_yaml(
        build / "preflight/resolved_config.yaml", runner.resolved_config_payload(config)
    )
    runner.write_json(build / "preflight/contract_snapshot.json", {"test": True})
    runner.write_csv(
        build / "preflight/input_integrity_audit.csv",
        pd.DataFrame(columns=runner.INPUT_AUDIT_COLUMNS),
        runner.INPUT_AUDIT_COLUMNS,
    )
    runner.write_csv(
        build / "stage_failure_audit.csv",
        pd.DataFrame(columns=runner.STAGE_AUDIT_COLUMNS),
        runner.STAGE_AUDIT_COLUMNS,
    )
    runner.write_csv(
        build / runner.DECISION_NAME,
        runner.decision_frame("P0_PREFLIGHT_BLOCKED", "preflight", "synthetic"),
        runner.DECISION_COLUMNS,
    )
    (build / runner.REPORT_NAME).write_text("synthetic\n", encoding="utf-8")
    bundle_hash = runner.seal_candidate(
        build,
        output,
        config,
        "P0_PREFLIGHT_BLOCKED",
        "20B_P4_PORTSENS_preflight_blocked",
        "preflight",
    )
    registry = json.loads((output / runner.HASHES_NAME).read_text(encoding="utf-8"))
    assert runner.HASHES_NAME not in registry
    assert runner.MANIFEST_NAME in registry
    assert bundle_hash == runner.verify_candidate_seal(
        output, config, "P0_PREFLIGHT_BLOCKED"
    )

    replay_a = tmp_path / "replay_a"
    replay_b = tmp_path / "replay_b"
    for root in (replay_a, replay_b):
        for relative in runner.CORE_PATHS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(relative.encode("utf-8"))
    comparison, hashes, matches = runner.compare_replays(replay_a, replay_b)
    assert matches
    assert comparison["hash_match"].all()
    assert list(hashes) == runner.CORE_PATHS
    (replay_b / runner.CORE_PATHS[0]).write_bytes(b"drift")
    _, _, matches_after_drift = runner.compare_replays(replay_a, replay_b)
    assert not matches_after_drift
