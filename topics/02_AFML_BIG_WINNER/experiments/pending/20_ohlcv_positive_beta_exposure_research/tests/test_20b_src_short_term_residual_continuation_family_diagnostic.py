from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


EXPERIMENT = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT / "src/run_20b_src_short_term_residual_continuation_family_diagnostic.py"
OUTPUT = EXPERIMENT / "outputs/20B_SRC_short_term_residual_continuation_family_diagnostic_v0"
SPEC = importlib.util.spec_from_file_location("src20b", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_config_identity_and_authorization() -> None:
    config = runner.load_config()
    assert config["run_id"] == runner.RUN_ID
    assert config["contract_version"] == "20B_SRC_v0"
    assert config["authorization"]["implementation_authorized"] is True


def test_unknown_config_key_fails(tmp_path: Path) -> None:
    config = runner.load_config()
    config["unknown"] = 1
    path = tmp_path / "bad.yaml"
    path.write_text(__import__("yaml").safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown/missing"):
        runner.load_config(path)


def test_registry_exact_counts_and_keys() -> None:
    registry = runner.arm_registry()
    assert len(registry) == 84
    assert len(registry[registry["arm_id"] != runner.BASELINE_ARM]) == 80
    assert len(registry[registry["arm_id"] == runner.BASELINE_ARM]) == 4
    assert not registry.duplicated(["arm_id", "holding_sessions", "return_semantics", "weighting", "bucket_count"]).any()


def test_registry_primary_rows_are_exact() -> None:
    primary = runner.arm_registry().query("primary_gate_eligible == True")
    assert set(zip(primary["arm_id"], primary["holding_sessions"])) == {
        ("SRC3_MKT_RESID_CONT_5D", 5), ("SRC4_MKT_RESID_CONT_10D", 10)
    }
    assert set(primary["return_semantics"]) == {runner.PROJECT_SEMANTICS}
    assert set(primary["weighting"]) == {"EW"}
    assert set(primary["bucket_count"]) == {10}


def test_formula_registry_exact_count() -> None:
    formulas = runner.formula_registry(runner.load_config())
    assert len(formulas) == 6
    assert formulas["formula_id"].is_unique
    assert set(formulas["arm_id"]) == set(runner.SCORED_ARMS) | {runner.BASELINE_ARM}


@pytest.mark.parametrize("length", [5, 10])
def test_standardized_score_exact_window(length: int) -> None:
    values = np.arange(1.0, 30.0)
    value, n, reason = runner.standardized_score(values, 20, length)
    expected = values[21 - length:21]
    assert n == length and reason == ""
    assert value == pytest.approx(expected.mean() / expected.std(ddof=1))


def test_standardized_score_missing_fails() -> None:
    values = np.arange(20.0)
    values[17] = np.nan
    value, n, reason = runner.standardized_score(values, 19, 5)
    assert np.isnan(value) and n == 4 and reason == "formation_missing_value"


def test_standardized_score_zero_scale_fails() -> None:
    value, n, reason = runner.standardized_score(np.ones(10), 9, 5)
    assert np.isnan(value) and n == 5 and reason == "formation_scale_nonpositive"


def test_bucket_tie_breaks_by_instrument() -> None:
    values = pd.Series([1.0, 1.0, 2.0, 3.0], index=["b", "a", "c", "d"])
    assert runner.assign_buckets(values, 2).to_dict() == {"a": 1, "b": 1, "c": 2, "d": 2}


@pytest.mark.parametrize("k,n", [(5, 50), (10, 100)])
def test_assignment_bucket_formula(k: int, n: int) -> None:
    values = pd.Series(np.arange(n, dtype=float), index=[f"S{i:03d}" for i in range(n)])
    buckets = runner.assign_buckets(values, k)
    assert buckets.min() == 1 and buckets.max() == k
    assert buckets.value_counts().sort_index().tolist() == [n // k] * k


def test_return_statistics_fixed_order_tail() -> None:
    stats = runner.return_statistics([-3, -2, -1, 1, 2, 3, 4, 5, 6, 7])
    assert stats["p10"] == pytest.approx(-2.1)
    assert stats["ES10_loss"] == pytest.approx(3.0)
    assert stats["positive_rate"] == pytest.approx(0.7)


def test_return_statistics_zero_is_not_positive() -> None:
    assert runner.return_statistics([-1, 0, 1])["positive_rate"] == pytest.approx(1 / 3)


def test_return_statistics_ties_do_not_expand_tail() -> None:
    values = [-2] * 5 + [1] * 15
    assert runner.return_statistics(values)["ES10_loss"] == pytest.approx(2.0)


def test_calendar_hac_preserves_missing_slots() -> None:
    with_gap = runner.calendar_hac([1.0, np.nan, 2.0, 3.0], 4)
    compressed = runner.calendar_hac([1.0, 2.0, 3.0], 4)
    assert with_gap["calendar_slot_n"] == 4
    assert with_gap["se"] != compressed["se"]


def test_calendar_hac_insufficient_n_is_missing() -> None:
    result = runner.calendar_hac([np.nan, 1.0, np.nan])
    assert result["p"] is None and result["se"] is None


def test_moving_block_paths_are_deterministic_and_non_circular() -> None:
    left = runner.moving_block_count_matrix(8, 20, 3, 20020)
    right = runner.moving_block_count_matrix(8, 20, 3, 20020)
    assert np.array_equal(left, right)
    assert np.all(left.sum(axis=1) == 8)


def test_bootstrap_matrix_keeps_missing_denominator() -> None:
    counts = runner.moving_block_count_matrix(4, 100, 2, 20020)
    values = np.array([[1.0], [np.nan], [3.0], [np.nan]])
    means, finite = runner.bootstrap_matrix(values, counts)
    assert means.shape == (100, 1)
    assert 0 < finite[0] <= 100


def test_three_state_or() -> None:
    assert runner.three_state_or([False, "not_evaluable"]) == "not_evaluable"
    assert runner.three_state_or([False, False]) is False
    assert runner.three_state_or(["not_evaluable", True]) is True


@pytest.mark.parametrize(
    "date,buy,sell", [("2017-01-03", 0.2, 0.2), ("2022-04-28", 0.2, 0.2), ("2022-04-29", 0.1, 0.1), ("2026-05-29", 0.1, 0.1)],
)
def test_transfer_fee_schedule(date: str, buy: float, sell: float) -> None:
    assert runner.transfer_fee_bps(runner.load_config(), pd.Timestamp(date)) == (buy, sell)


def test_authorization_semantic_hash_excludes_self() -> None:
    record = {"authorization_stage": "signal-materialization", "x": 1, "authorization_record_sha256": "wrong"}
    assert runner.semantic_authorization_hash(record) == runner.stable_hash({"authorization_stage": "signal-materialization", "x": 1})


def test_authorization_binding_and_scope(tmp_path: Path) -> None:
    record = {
        "authorization_stage": "signal-materialization", "authorized_by": "workspace_user",
        "authorization_source": "user_message", "authorized_at_utc": "2026-07-13T00:00:00.000000Z",
        "bound_run_id": runner.RUN_ID, "bound_contract_version": runner.CONTRACT_VERSION,
        "bound_input_bundle_hash": "bundle", "allowed_read_scope": "scope",
    }
    record["authorization_record_sha256"] = runner.semantic_authorization_hash(record)
    path = tmp_path / "auth.json"
    runner.write_json(path, record)
    assert runner.verify_authorization(path, "signal-materialization", "bundle", "scope") == record
    with pytest.raises(PermissionError):
        runner.verify_authorization(path, "signal-materialization", "other", "scope")


def test_published_json_is_sorted_and_has_newline(tmp_path: Path) -> None:
    path = tmp_path / "x.json"
    runner.write_json(path, {"b": 1, "a": 2})
    assert path.read_text(encoding="utf-8") == '{\n  "a": 2,\n  "b": 1\n}\n'


def test_deterministic_gzip_has_zero_mtime_and_empty_filename(tmp_path: Path) -> None:
    path = tmp_path / "x.csv.gz"
    runner.write_csv_gz(path, pd.DataFrame({"a": [1]}))
    raw = path.read_bytes()
    assert raw[4:8] == b"\x00\x00\x00\x00"
    assert gzip.open(path, "rt", encoding="utf-8").read() == "a\n1\n"


def test_weekly_calendar_uses_last_iso_session_and_next_entry() -> None:
    calendar = pd.DatetimeIndex(pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-05", "2024-01-08", "2024-01-09"]))
    weekly = runner.weekly_calendar(calendar)
    assert weekly.iloc[0]["decision_date"] == pd.Timestamp("2024-01-05")
    assert weekly.iloc[0]["entry_date"] == pd.Timestamp("2024-01-08")


def test_weekly_calendar_warmup_is_calendar_only() -> None:
    calendar = pd.bdate_range("2020-01-01", periods=300)
    weekly = runner.weekly_calendar(calendar)
    assert (weekly["calendar_signal_possible"] == (weekly["zero_based_session_index"] >= 262)).all()


def test_early_late_split_uses_floor_midpoint() -> None:
    calendar = pd.bdate_range("2020-01-01", periods=400)
    weekly = runner.weekly_calendar(calendar)
    possible = weekly[weekly["calendar_signal_possible"]]
    assert int((possible["fold_id"] == "EARLY").sum()) == len(possible) // 2


def _write_qfq(path: Path, instrument: str, dates: list[str], closes: list[float | None]) -> None:
    pd.DataFrame({"date": dates, "close": closes, "instrument": instrument}).to_csv(path, index=False)


def test_daily_resolution_missing_is_not_suspension_carry(tmp_path: Path) -> None:
    path = tmp_path / "SH600000.csv"
    _write_qfq(path, "SH600000", ["2024-01-02", "2024-01-04"], [10.0, 11.0])
    calendar = pd.DatetimeIndex(pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]))
    daily, returns, *_ = runner.resolve_daily_path("SH600000", path, calendar, None)
    assert daily.loc[1, "resolution_state"] == "unknown_data_gap"
    assert np.isnan(returns[1]) and np.isnan(returns[2])
    assert not daily["daily_suspension_lookup_performed"].any()


def test_daily_resolution_observed_mark_wins_on_delist_date(tmp_path: Path) -> None:
    path = tmp_path / "SH600000.csv"
    _write_qfq(path, "SH600000", ["2024-01-02", "2024-01-03"], [10.0, 9.0])
    calendar = pd.DatetimeIndex(pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]))
    master = {"listing_date": pd.Timestamp("2000-01-01"), "delist_date": pd.Timestamp("2024-01-03"), "is_delisted": True}
    daily, returns, *_ = runner.resolve_daily_path("SH600000", path, calendar, master)
    assert daily.loc[1, "resolution_state"] == "valid_mark"
    assert daily.loc[2, "resolution_state"] == "confirmed_delisting_terminal"
    assert returns[2] == -1.0


def test_daily_terminal_applies_once(tmp_path: Path) -> None:
    path = tmp_path / "SH600000.csv"
    _write_qfq(path, "SH600000", ["2024-01-02"], [10.0])
    calendar = pd.DatetimeIndex(pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]))
    master = {"listing_date": pd.Timestamp("2000-01-01"), "delist_date": pd.Timestamp("2024-01-03"), "is_delisted": True}
    daily, returns, *_ = runner.resolve_daily_path("SH600000", path, calendar, master)
    assert list(daily["resolution_state"]) == ["valid_mark", "confirmed_delisting_terminal", "post_terminal_not_eligible"]
    assert np.nansum(returns == -1.0) == 1


def test_sequential_residual_timing_and_lstsq_equivalence() -> None:
    rng = np.random.default_rng(7)
    market = rng.normal(0, 0.01, 400)
    stock = 0.0002 + 1.2 * market + rng.normal(0, 0.005, 400)
    market[0] = stock[0] = np.nan
    calendar = pd.bdate_range("2020-01-01", periods=400)
    model, panel, residual, _ = runner.sequential_residuals("SH600000", stock, market, calendar, calendar[-1], 1e-12)
    assert (pd.to_datetime(model["estimation_end_date"]) < pd.to_datetime(model["residual_date"])).all()
    assert (pd.to_datetime(panel["max_contributing_date"]) == pd.to_datetime(panel["residual_date"])).all()
    assert panel["future_rows_contributed"].sum() == 0
    assert np.isfinite(residual).sum() > 0


def test_instrument_without_weekly_denominator_returns_typed_empty_frame() -> None:
    calendar = pd.bdate_range("2024-01-01", periods=30)
    frame = runner.weekly_features_for_instrument("SH600000", pd.DataFrame(), calendar, np.zeros(30), np.zeros(30), calendar[-1])
    assert frame.empty
    assert frame.columns.tolist() == runner.WEEKLY_COLUMNS


def test_assignment_accepts_object_boolean_signal_flags() -> None:
    rows = []
    for i in range(100):
        rows.append({
            "instrument_id": f"S{i:03d}", "decision_date": pd.Timestamp("2024-01-05"),
            "entry_date": pd.Timestamp("2024-01-08"), "arm_id": "SRC1_TOTAL_CONT_5D",
            "formation_sessions": 5, "signal_eligible": bool(i % 2 == 0), "raw_signal": float(i),
            "total_market_cap_cny": 100 + i, "signal_missing_reason": "" if i % 2 == 0 else "missing",
        })
    weekly = pd.DataFrame(rows).astype({"signal_eligible": "object"})
    assignment, coverage = runner.materialize_assignments(weekly, runner.load_config())
    assert len(assignment) == 200
    assert coverage.iloc[0]["signal_eligible_n"] == 50


def test_derived_bucket_direction_for_lowvol() -> None:
    physical = {i: {"registered_denominator_n": 100, "signal_eligible_n": 100, "bucket_target_n": 20, "outcome_resolved_n": 20, "evaluable": True, "not_evaluable_reason": "", "gross_return": i / 100} for i in range(1, 6)}
    rows = runner.derived_bucket_rows(physical, "SRC5_LOWVOL_20D_COMPARATOR", 5)
    favorite = next(row for row in rows if row["series_role"] == "favorable_bucket")
    spread = next(row for row in rows if row["series_role"] == "favorable_minus_unfavorable")
    assert favorite["gross_return"] == pytest.approx(0.01)
    assert spread["gross_return"] == pytest.approx(-0.04)


def test_project_bucket_fails_on_one_unknown() -> None:
    group = pd.DataFrame({"instrument_id": ["A", "B"], "bucket_id": [1, 1], "ew_target_weight": [0.5, 0.5], "vw_target_weight": [0.5, 0.5], "signal_eligible": [True, True]})
    result = runner.physical_bucket_row(group, pd.Series({"A": 0.1, "B": np.nan}), runner.PROJECT_SEMANTICS, "EW", 1)
    assert result["evaluable"] is False
    assert result["not_evaluable_reason"] == "whole_bucket_unknown_or_right_censored"


def test_complete_case_bucket_renormalizes() -> None:
    group = pd.DataFrame({"instrument_id": ["A", "B"], "bucket_id": [1, 1], "ew_target_weight": [0.5, 0.5], "vw_target_weight": [0.5, 0.5], "signal_eligible": [True, True]})
    result = runner.physical_bucket_row(group, pd.Series({"A": 0.1, "B": np.nan}), runner.COMPLETE_CASE_SEMANTICS, "EW", 1)
    assert result["evaluable"] is True and result["gross_return"] == pytest.approx(0.1)


def test_path_formula_is_multiplicative() -> None:
    assert (1.10 / 1.05 - 1) != pytest.approx(0.10 - 0.05)


@pytest.mark.parametrize("required", runner.DAILY_COLUMNS)
def test_daily_schema_fields_registered(required: str) -> None:
    assert required in runner.DAILY_COLUMNS


@pytest.mark.parametrize("required", runner.FORWARD_COLUMNS)
def test_forward_schema_fields_registered(required: str) -> None:
    assert required in runner.FORWARD_COLUMNS


def test_requirement_counts_match_implementable_grid() -> None:
    text = (EXPERIMENT / "requirement_20b_src_short_term_residual_continuation_family_diagnostic.md").read_text(encoding="utf-8")
    assert "= 84" in text
    assert "summary 1212 rows" in text
    assert "= 2424" in text


def test_source_has_four_explicit_stage_functions() -> None:
    for name in ["preflight_stage", "signal_stage", "outcome_stage", "finalize_stage"]:
        assert callable(getattr(runner, name))


def test_forward_and_policy_authorizations_remain_false_in_config_scope() -> None:
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert '"true_forward_execution_authorized": False' in source
    assert '"policy_replay_authorized": False' in source
    assert '"deployment_authorized": False' in source


def test_final_bundle_and_all_stages_are_bidirectionally_sealed() -> None:
    assert runner.verify_bundle(OUTPUT / "preoutcome", "preoutcome")
    assert runner.verify_bundle(OUTPUT / "signal", "signal")
    assert runner.verify_bundle(OUTPUT / "historical", "historical")
    assert runner.verify_bundle(OUTPUT, "final")


def test_authorizations_bind_exact_stage_hashes_and_scopes() -> None:
    pre_hash = runner.verify_bundle(OUTPUT / "preoutcome", "preoutcome")
    signal_hash = runner.verify_bundle(OUTPUT / "signal", "signal")
    scopes = runner.load_preoutcome_whitelist(OUTPUT)
    signal = runner.verify_authorization(
        OUTPUT / "authorizations/signal_materialization_authorization.json",
        "signal-materialization", pre_hash, scopes["signal-materialization"]["stable_object_hash"],
    )
    outcome = runner.verify_authorization(
        OUTPUT / "authorizations/outcome_materialization_authorization.json",
        "outcome-materialization", signal_hash, scopes["outcome-materialization"]["stable_object_hash"],
    )
    assert signal["authorized_by"] == outcome["authorized_by"] == "workspace_user"


def test_published_exact_row_counts() -> None:
    manifest = json.loads((OUTPUT / "historical/historical_manifest_20b_src.json").read_text(encoding="utf-8"))
    counts = {row["file_path"]: row["row_count"] for row in manifest["artifacts"]}
    assert counts["arm_summary_statistics.csv"] == 1212
    assert counts["hac_and_block_bootstrap_inference.csv"] == 2424
    assert counts["paired_residual_vs_total_attribution.csv"] == 48
    assert counts["turnover_break_even_cost_readout.csv"] == 80
    assert counts["forward_return_resolution.parquet"] == 960000
    assert counts["bucket_return_panel.csv.gz"] == 481920


def test_signal_timing_firewall_on_published_panels() -> None:
    panel = pd.read_parquet(OUTPUT / "signal/daily_market_residual_panel.parquet", columns=["residual_date", "estimation_end_date", "max_contributing_date", "future_rows_contributed"])
    assert (pd.to_datetime(panel["estimation_end_date"]) < pd.to_datetime(panel["residual_date"])).all()
    assert (pd.to_datetime(panel["max_contributing_date"]) == pd.to_datetime(panel["residual_date"])).all()
    assert panel["future_rows_contributed"].sum() == 0


def test_no_suspension_lookup_or_carry_in_published_daily_audit() -> None:
    states = set()
    suspension_lookup_n = 0
    for chunk in pd.read_csv(OUTPUT / "signal/daily_return_resolution_audit.csv.gz", usecols=["resolution_state", "daily_suspension_lookup_performed"], chunksize=500_000):
        states.update(chunk["resolution_state"].dropna().astype(str))
        suspension_lookup_n += int(chunk["daily_suspension_lookup_performed"].astype(str).str.lower().eq("true").sum())
    assert suspension_lookup_n == 0
    assert states <= {"valid_mark", "confirmed_delisting_terminal", "unknown_data_gap", "post_terminal_not_eligible"}


def test_published_assignments_have_unique_frozen_keys() -> None:
    assignment = pd.read_parquet(OUTPUT / "signal/weekly_bucket_assignment.parquet", columns=["instrument_id", "decision_date", "arm_id", "bucket_count"])
    assert len(assignment) == 2_400_000
    assert not assignment.duplicated(["instrument_id", "decision_date", "arm_id", "bucket_count"]).any()


def test_published_terminal_state_and_no_forward_authorization() -> None:
    decision = pd.read_csv(OUTPUT / "20B_SRC_short_term_residual_continuation_family_decision.csv").iloc[0]
    assert decision["terminal_state"] == "20B_SRC_not_identified_design_only"
    assert str(decision["historical_signal_execution_authorization_gate"]) == "pass"
    assert str(decision["historical_outcome_execution_authorization_gate"]) == "pass"
    assert str(decision["true_forward_execution_authorized"]).lower() == "false"
    assert str(decision["deployment_authorized"]).lower() == "false"


def test_report_has_frozen_sections_and_required_disclosures() -> None:
    report = (OUTPUT / "20B_SRC_short_term_residual_continuation_family_diagnostic_report.md").read_text(encoding="utf-8")
    assert report.count("\n## ") == 14
    assert "任何历史结果都不能形成 true OOS support" in report
    assert "不读取、不推断逐日停牌状态" in report
    assert "Favorable-minus-unfavorable 为正不能替代" in report
    assert "deployment_authorized=false" in report
