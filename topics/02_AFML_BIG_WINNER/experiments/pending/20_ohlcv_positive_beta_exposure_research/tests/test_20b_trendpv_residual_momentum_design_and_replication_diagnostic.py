from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


RUNNER = Path(__file__).resolve().parents[1] / "src/run_20b_trendpv_residual_momentum_design_and_replication_diagnostic.py"
BASE = RUNNER.parents[1]
OUTPUT_V5 = BASE / "outputs/20B_trendpv_residual_momentum_design_and_replication_diagnostic_v5"
SPEC = importlib.util.spec_from_file_location("ep20b_runner", RUNNER)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(runner)


def test_bucket_assignment_exact_and_tie_break() -> None:
    values = pd.Series([1.0] * 10, index=[f"S{i:02d}" for i in range(10)][::-1])
    result = runner.assign_buckets(values, 5)
    assert result.sort_index().tolist() == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


def test_newey_west_is_finite() -> None:
    result = runner.nw_stats([0.01, 0.02, -0.01, 0.03, 0.0] * 10)
    assert result["lag"] >= 1
    assert np.isfinite(result["t"])
    assert 0 <= result["p"] <= 1


def test_series_stats_es_and_drawdown() -> None:
    result = runner.series_stats([-0.2, 0.1, 0.05, -0.1, 0.02], 6)
    assert result["ES10_loss"] == 0.2
    assert result["month_n"] == 5
    assert result["gap_month_n"] == 1
    assert result["max_drawdown_of_compounded_gross_series"] > 0


def test_decision_calendar_requires_complete_label() -> None:
    cal = pd.date_range("2026-01-01", "2026-03-31", freq="B")
    frame = runner.decision_calendar(cal, pd.Timestamp("2026-02-28"))
    assert frame.loc[frame["period"] == pd.Period("2026-01"), "label_complete"].iloc[0]
    assert not frame.loc[frame["period"] == pd.Period("2026-02"), "label_complete"].iloc[0]


def test_config_freezes_direct_authorization_and_boundaries() -> None:
    config = runner.load_config()
    assert config["authorization"]["direct_run_authorized"] is True
    assert config["boundary"]["history_date_max"] == "2026-05-29"
    assert config["trendpv"]["windows"] == [3, 5, 10, 20, 50, 100, 200, 300, 400]


def test_required_semantic_tracks_are_unique() -> None:
    assert runner.ARMS["P4_RESMOM_R2_MARKET_ONLY_ADAPTATION"] == "project_sequential_market_residual_primary"
    assert runner.ARMS["P5_RESMOM_R3_BOARD_ADAPTATION"] == "full_history_retrospective_proxy"


def test_expected_upstream_hash_is_frozen() -> None:
    assert runner.EXPECTED_20A_HASH == "da5902ac7a987ec061cdffc33e8735ad34c22f1ae771a43540fe005fd77acb05"


def test_contract_version_is_upgraded_after_superseded_runs() -> None:
    assert runner.CONTRACT_VERSION == "20B_v5"
    assert runner.RUN_ID.endswith("_v5")


def test_r2_uses_exact_lstsq_and_prior_36_months() -> None:
    periods = list(pd.period_range("2020-01", periods=38, freq="M"))
    market = pd.Series(np.linspace(-0.1, 0.1, 38), index=periods)
    stock = pd.DataFrame([0.02 + 1.5 * market.to_numpy()], index=["X"], columns=periods)
    residual, score, audit = runner.rolling_scores(stock, market)
    row = pd.DataFrame(audit).iloc[0]
    assert row["rank"] == 2 and row["observation_n"] == 36
    assert abs(row["alpha"] - 0.02) < 1e-12
    assert abs(row["beta"] - 1.5) < 1e-12
    assert abs(residual.at["X", periods[36]]) < 1e-12
    assert score.notna().sum().sum() == 0


def _monthly_fixture(tmp_path: Path, *, delisted: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, Path, dict]:
    periods = list(pd.period_range("2025-01", periods=4, freq="M"))
    monthly = pd.DataFrame({
        "instrument": ["X", "X", "X"], "period": [periods[0], periods[2], periods[3]],
        "close": [10.0, 11.0, 12.0],
        "last_trade_date": pd.to_datetime(["2025-01-31", "2025-03-31", "2025-04-30"]),
    })
    universe = pd.DataFrame({"instrument": ["X"] * 4, "period": periods,
                             "is_suspended": [False, True, False, False]})
    master = tmp_path / "master.csv"
    pd.DataFrame([{"instrument": "X", "delist_date": "2025-02-15" if delisted else "",
                   "is_delisted": delisted, "metadata_source": "unit"}]).to_csv(master, index=False)
    ends = {p: pd.Timestamp(f"{p}-01") + pd.offsets.MonthEnd(0) for p in periods}
    return monthly, universe, master, ends


def test_project_suspension_carry_and_resumption(tmp_path: Path) -> None:
    monthly, universe, master, ends = _monthly_fixture(tmp_path)
    _, _, paper, project, resolution = runner.monthly_matrices(monthly, list(ends), universe, master, ends)
    assert project.at["X", pd.Period("2025-02")] == 0.0
    assert resolution.at["X", pd.Period("2025-02")] == "suspension_carry_mark"
    assert project.at["X", pd.Period("2025-03")] == pytest.approx(0.1)
    assert np.isnan(paper.at["X", pd.Period("2025-03")])


def test_confirmed_delisting_is_minus_one_once(tmp_path: Path) -> None:
    monthly, universe, master, ends = _monthly_fixture(tmp_path, delisted=True)
    _, _, _, project, resolution = runner.monthly_matrices(monthly.iloc[:1], list(ends), universe, master, ends)
    assert project.at["X", pd.Period("2025-02")] == -1.0
    assert resolution.at["X", pd.Period("2025-02")] == "delisting_minus_one"
    assert np.isnan(project.at["X", pd.Period("2025-03")])


def test_unconfirmed_series_end_is_unknown_not_delisting(tmp_path: Path) -> None:
    monthly, universe, master, ends = _monthly_fixture(tmp_path)
    universe["is_suspended"] = False
    _, _, _, project, resolution = runner.monthly_matrices(monthly.iloc[:1], list(ends), universe, master, ends)
    assert np.isnan(project.at["X", pd.Period("2025-02")])
    assert resolution.at["X", pd.Period("2025-02")] == "unknown_bridge_arm_month_not_evaluable"


def test_partial_month_without_suspension_is_unknown_and_breaks_next_ratio(tmp_path: Path) -> None:
    monthly, universe, master, ends = _monthly_fixture(tmp_path)
    monthly.loc[monthly["period"].eq(pd.Period("2025-03")), "last_trade_date"] = pd.Timestamp("2025-03-20")
    _, _, paper, project, resolution = runner.monthly_matrices(monthly, list(ends), universe, master, ends)
    assert np.isnan(paper.at["X", pd.Period("2025-03")])
    assert np.isnan(project.at["X", pd.Period("2025-03")])
    assert resolution.at["X", pd.Period("2025-03")] == "unknown_bridge_arm_month_not_evaluable"
    assert np.isnan(project.at["X", pd.Period("2025-04")])


def test_outcome_for_keeps_return_semantics_separate() -> None:
    cols = pd.period_range("2025-01", periods=2, freq="M")
    paper = pd.DataFrame([[np.nan, 0.2]], index=["X"], columns=cols)
    project = pd.DataFrame([[np.nan, 0.0]], index=["X"], columns=cols)
    resolution = pd.DataFrame([["unknown", "suspension_carry_mark"]], index=["X"], columns=cols)
    result = runner.outcome_for("X", cols[0], paper, project, resolution)
    assert result == (0.2, 0.0, "suspension_carry_mark")


def test_board_matrix_drops_exact_duplicate_columns(tmp_path: Path) -> None:
    board = tmp_path / "board.csv"
    pd.DataFrame({"board_ts_code": ["A", "A", "B", "B"],
                  "con_code": ["600000.SH", "600001.SH", "600000.SH", "600001.SH"]}).to_csv(board, index=False)
    matrix = runner.board_matrix(board, pd.Index(["SH600000", "SH600001"]), 1)
    assert list(matrix.columns) == ["A"]
    assert matrix.attrs["duplicate_columns_dropped"] == "B"


def test_series_stats_preserves_registered_gap_count() -> None:
    result = runner.series_stats([0.1, -0.1], 10)
    assert result["registered_month_n"] == 10
    assert result["gap_month_n"] == 8


@pytest.mark.parametrize("value,expected", [(0.0, False), (-0.01, False), (0.01, True)])
def test_positive_hurdle_is_strictly_greater_than_zero(value: float, expected: bool) -> None:
    assert (value > 0) is expected


def test_seal_verification_is_bidirectional(tmp_path: Path) -> None:
    (tmp_path / "x.txt").write_text("x", encoding="utf-8")
    runner.seal_bundle(tmp_path, "manifest.json", "hashes.json", ["x.txt"], {"run_id": "t"})
    runner.verify_bundle(tmp_path, "manifest.json", "hashes.json")
    (tmp_path / "extra.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(RuntimeError, match="file-set mismatch"):
        runner.verify_bundle(tmp_path, "manifest.json", "hashes.json")


def test_publish_stage_refuses_overwrite(tmp_path: Path) -> None:
    candidate = tmp_path / ".candidate"; candidate.mkdir()
    target = tmp_path / "target"; target.mkdir()
    with pytest.raises(FileExistsError):
        runner.publish_stage(candidate, target)


def test_p5_scope_boundary_uses_all_eleven_residual_months() -> None:
    snapshot = pd.Period("2025-01", freq="M")
    assert pd.Period("2025-12", freq="M") - 12 < snapshot
    assert pd.Period("2026-01", freq="M") - 12 >= snapshot


@pytest.mark.parametrize("arm,expected", [
    ("P0_TOTAL_MOMENTUM_12_1", "project_return_history_primary"),
    ("P1_TRENDPV_RAW_ADAPTATION", "project_strict_primary"),
    ("P4_RESMOM_R2_MARKET_ONLY_ADAPTATION", "project_sequential_market_residual_primary"),
    ("P5_RESMOM_R3_BOARD_ADAPTATION", "full_history_retrospective_proxy"),
    ("P6_LOWVOL_36M_COMPARATOR", "project_monthly_volatility_primary"),
])
def test_registered_track_exact_mapping(arm: str, expected: str) -> None:
    assert runner.ARMS[arm] == expected


def test_v5_all_three_bundles_are_bidirectionally_sealed() -> None:
    assert runner.verify_bundle(OUTPUT_V5 / "preoutcome", "preoutcome_manifest_20b.json", "preoutcome_output_hashes_20b.json")
    assert runner.verify_bundle(OUTPUT_V5 / "historical", "historical_manifest_20b.json", "historical_output_hashes_20b.json")
    assert runner.verify_bundle(OUTPUT_V5, "manifest_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json", "output_hashes_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json")


def test_v5_frozen_calendars_are_55_and_64_not_recuts() -> None:
    folds = pd.read_csv(OUTPUT_V5 / "preoutcome/statistical_and_fold_freeze.csv").set_index("arm_or_calendar_id")
    assert folds.at["P1_PROJECT_STRICT_CALENDAR", "theoretical_max_month_n"] == 55
    assert folds.at["P4_PRIMARY_CALENDAR", "theoretical_max_month_n"] == 64
    assert folds.at["P4_PRIMARY_CALENDAR", "early_end"] == "2023-08"
    assert folds.at["P4_PRIMARY_CALENDAR", "late_start"] == "2023-09"
    assert not folds["outcome_used_for_threshold"].astype(bool).any()


def test_v5_trend_path_has_realized_and_ema_for_all_18_predictors() -> None:
    coef = pd.read_csv(OUTPUT_V5 / "historical/trendpv_coefficient_path.csv.gz", nrows=1)
    assert len([c for c in coef if c.startswith("realized_beta_")]) == 18
    assert len([c for c in coef if c.startswith("ema_beta_")]) == 18


def test_v5_exact_routes_are_registered_not_run() -> None:
    exact = pd.read_csv(OUTPUT_V5 / "historical/exact_route_status.csv")
    assert set(exact["arm_id"]) == {"P2_TREND_FULL_EXACT", "P3_RESMOM_CH3_EXACT"}
    assert exact["run_status"].eq("registered_not_run").all()
    assert exact["row_n"].eq(0).all()
    assert not exact["exact_replication_claim_allowed"].astype(bool).any()


def test_v5_outcome_resolution_fails_closed_without_fake_carry() -> None:
    audit = pd.read_csv(OUTPUT_V5 / "historical/outcome_resolution_audit.csv.gz")
    assert set(audit["outcome_resolution"]) <= {"valid_mark", "suspension_carry_mark", "delisting_minus_one", "unknown_bridge_arm_month_not_evaluable"}
    assert audit["outcome_resolution"].eq("unknown_bridge_arm_month_not_evaluable").any()
    assert not audit["outcome_resolution"].eq("suspension_carry_mark").any()


def test_v5_p4_p5_attribution_has_pairs_spreads_and_frozen_summaries() -> None:
    audit = pd.read_csv(OUTPUT_V5 / "historical/p4_p5_board_attribution_readout.csv")
    assert set(audit["record_type"]) == {"score_instrument_pair", "return_month_pair", "return_scope_summary"}
    pairs = audit[audit["record_type"].eq("return_month_pair") & audit["pair_evaluable"]]
    assert {"bucket_return", "favorable_minus_unfavorable", "favorable_minus_middle"} <= set(pairs["series_role"])
    assert np.allclose(pairs["P5_minus_P4_value"], pairs["P5_value"] - pairs["P4_value"])
    summaries = audit[audit["record_type"].eq("return_scope_summary")]
    assert {"full", "early", "late", "P5_date_scope"} <= set(summaries["month_scope"])


def test_v5_overlapping_terminal_loss_never_repeats() -> None:
    cohort = pd.read_parquet(OUTPUT_V5 / "historical/residual_overlapping_cohort_assignment.parquet",
                             columns=["arm_id", "holding_month_n", "cohort_formation_date", "bucket_count", "bucket_id", "weighting", "instrument_id", "outcome_resolution"])
    keys = ["arm_id", "holding_month_n", "cohort_formation_date", "bucket_count", "bucket_id", "weighting", "instrument_id"]
    terminal_n = cohort["outcome_resolution"].eq("delisting_minus_one").groupby([cohort[c] for c in keys]).sum()
    assert terminal_n.le(1).all()


@pytest.mark.parametrize("column", [
    "20C_execution_authorized", "policy_training_authorized", "policy_replay_authorized",
    "portfolio_optimization_authorized", "deployment_authorized", "historical_support_claim_allowed",
    "residual_primary_changed_by_20B", "exact_replication_reachable",
])
def test_v5_hard_false_authorizations(column: str) -> None:
    decision = pd.read_csv(OUTPUT_V5 / "20B_trendpv_residual_momentum_design_and_replication_diagnostic_decision.csv").iloc[0]
    assert bool(decision[column]) is False


def test_v5_decision_schema_exactly_matches_requirement() -> None:
    requirement = (BASE / "requirement_20b_trendpv_residual_momentum_design_and_replication_diagnostic.md").read_text(encoding="utf-8")
    section = requirement.split("### 15.8 Decision schema", 1)[1]
    required = {x.strip() for x in re.search(r"```text\n(.*?)\n```", section, re.S).group(1).splitlines() if x.strip()}
    columns = set(pd.read_csv(OUTPUT_V5 / "20B_trendpv_residual_momentum_design_and_replication_diagnostic_decision.csv", nrows=0).columns)
    assert columns == required


def test_v5_terminal_truth_and_report_contract() -> None:
    snapshot = json.loads((OUTPUT_V5 / "historical/historical_decision_snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["decision_state"] == "20B_underpowered_design_diagnostic"
    assert snapshot["global_underpowered"] is True
    assert snapshot["P1_materialization_gate"] is False and snapshot["P4_materialization_gate"] is False
    report = (OUTPUT_V5 / "20B_trendpv_residual_momentum_design_and_replication_diagnostic_report.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^## \d+\.", report, re.M)) == 17
    for phrase in ["local replication passed", "OOS confirmed", "positive beta supported", "alpha discovered", "deployable strategy"]:
        assert phrase.lower() not in report.lower()


def test_v5_outcome_access_roles_are_complete_and_not_tuning() -> None:
    access = pd.read_csv(OUTPUT_V5 / "historical/outcome_access_audit.csv")
    assert {"historical_qfq_ohlcv", "pit_project_universe_status_size", "csi300_benchmark", "frozen_2025_board_membership", "listing_delisting_status"} == set(access["dataset_role"])
    assert access["historical_outcome_access_authorized"].astype(bool).all()
    assert not access["selection_or_tuning_allowed"].astype(bool).any()
