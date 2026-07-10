from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml


RUNNER_PATH = Path(__file__).resolve().parents[1] / "src/run_20a_paper_lineage_data_and_replication_contract.py"
SPEC = importlib.util.spec_from_file_location("run_20a", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_identity_objective_and_paths_are_repository_relative() -> None:
    config = runner.load_config()
    assert config["run_id"] == runner.RUN_ID
    assert config["experiment_id"] == "20_ohlcv_positive_beta_exposure_research"
    assert config["objective"]["primary_objective"] == "deployable_positive_beta"
    assert config["objective"]["incremental_alpha_required"] is False
    assert config["objective"]["historical_support_claim_allowed"] is False
    assert all(not Path(value).is_absolute() for value in config["paths"].values())
    assert "19_entry_universe" not in config["paths"]["research_plan"]


def test_forbidden_column_scanner_is_case_insensitive_and_nested() -> None:
    columns = [
        "instrument", "prefix_MFE_120_adjusted", "FUTURE_RETURN_20", "my_winner_flag",
        "strategy_PnL_net", "candidate_hit_flag", "derived_label_v2",
    ]
    found = runner.forbid_outcome_columns(columns)
    assert found == columns[1:]
    assert runner.forbid_outcome_columns(["date", "close", "total_market_cap_cny"]) == []


def test_formula_registry_freezes_positive_beta_adaptations() -> None:
    config = runner.load_config()
    manifest = pd.DataFrame({
        "source_id": [source["source_id"] for source in config["paper_sources"]],
        "sha256": ["a" * 64] * len(config["paper_sources"]),
    })
    formulas = runner.build_formula_draft(config, manifest)
    assert set(formulas.columns) == set(runner.FORMULA_COLUMNS)
    assert formulas["formula_gate"].eq("pending_human_review").all()
    r3 = formulas.loc[formulas["formula_id"] == "RESMOM_R3_BOARD_ADAPTATION"].iloc[0]
    assert "R2 market residual first" in r3["formula_text"]
    assert "lagged log market cap" in r3["formula_text"]
    assert "static 2025 board multi-hot" in r3["formula_text"]
    assert "alpha=1.0" in r3["formula_text"]
    assert "subtract market constant" not in r3["formula_text"].lower()
    trend = formulas.loc[formulas["formula_id"] == "TRENDPV_MONTHLY_CS_REG"].iloc[0]
    assert "lambda=0.02" in trend["formula_text"]


def test_primary_family_is_two_and_board_fallback_is_preoutcome() -> None:
    r3 = runner.fixed_arm_registry("C3_RESMOM_R3_BOARD_ADAPTATION")
    r2 = runner.fixed_arm_registry("C3A_RESMOM_R2_MARKET_ONLY")
    assert r3["arm_role"].eq("primary").sum() == 2
    assert r2["arm_role"].eq("primary").sum() == 2
    assert set(r3.loc[r3["arm_role"] == "primary", "arm_id"]) == {
        "C2_TRENDPV_RAW_ADAPTATION", "C3_RESMOM_R3_BOARD_ADAPTATION",
    }
    assert set(r2.loc[r2["arm_role"] == "primary", "arm_id"]) == {
        "C2_TRENDPV_RAW_ADAPTATION", "C3A_RESMOM_R2_MARKET_ONLY",
    }
    assert r3.groupby("arm_id")["portfolio_ledger_id"].nunique().max() == 1
    assert r3["accounting_mode"].eq("continuous_no_injection_stateful_NAV").all()


def test_mde_is_126_complete_decision_months() -> None:
    grid = runner.compute_mde_grid(runner.load_config())
    primary = grid.loc[(grid["effect_monthly"] == 0.02) & (grid["monthly_volatility"] == 0.08)].iloc[0]
    assert primary["n_required"] == 126
    assert primary["evidence_unit"] == "distinct_complete_decision_month"
    assert not bool(primary["serial_independence_claim"])
    assert set(grid["effect_monthly"]) == {0.01, 0.02, 0.03}
    assert set(grid["monthly_volatility"]) == {0.05, 0.08, 0.12}


def test_instrument_normalization_is_fail_closed() -> None:
    assert runner.normalize_instrument("600000.SH") == "SH600000"
    assert runner.normalize_instrument("000001.SZ") == "SZ000001"
    assert runner.normalize_instrument("BJ430047") == "BJ430047"
    assert runner.normalize_instrument("bad") == ""


def test_paper_source_allowlist_is_explicit() -> None:
    config = runner.load_config()
    assert len(config["paper_sources"]) >= 10
    for source in config["paper_sources"]:
        hostname = runner.urlparse(source["url"]).hostname
        assert hostname in source["allowed_domains"]
        assert source["expected_content"] in {"pdf", "html"}
        assert source["core"] is True


def test_freeze_is_blocked_before_market_read_without_human_authorization(tmp_path: Path) -> None:
    config = runner.load_config()
    config["paths"]["paper_cache_root"] = str(tmp_path / "missing_paper_cache")
    config["output"]["output_root"] = str(tmp_path / "blocked_output")
    config_path = tmp_path / "blocked_config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(PermissionError, match="paper formula"):
        runner.freeze_stage(config_path)


def test_b2_preoutcome_lineage_uses_only_five_allowlisted_artifacts() -> None:
    config = runner.load_config()
    paths = runner.resolve_paths(config)
    access: list[dict[str, object]] = []
    audit, status = runner.build_b2_lineage(paths, access)
    assert status == "pass"
    assert len(access) == 5
    assert set(row["dataset_role"] for row in access) == {"EP19_preoutcome_rule"}
    assert not audit["check_id"].str.contains("MFE|MAE|return", case=False, regex=True).any()
    assert audit.loc[audit["check_id"] == "EP19_effect_size_transfer_allowed", "frozen_value"].iloc[0] in {False, "False"}


def test_sealed_bundle_detects_mutation(tmp_path: Path) -> None:
    (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
    digest = runner.seal_bundle(tmp_path, "manifest.json", "hashes.json", ["a.csv"], {"run_id": "fixture"})
    assert len(digest) == 64
    runner.verify_bundle(tmp_path, "manifest.json", "hashes.json", ["a.csv"])
    (tmp_path / "a.csv").write_text("x\n2\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="hash mismatch"):
        runner.verify_bundle(tmp_path, "manifest.json", "hashes.json", ["a.csv"])


def test_human_authorization_hashes_and_full_review_are_required(tmp_path: Path) -> None:
    config = runner.load_config()
    cache = tmp_path / "papers"
    cache.mkdir()
    manifest = pd.DataFrame([{
        "source_id": "s1", "allowlist_gate": "pass", "content_validation_gate": "pass",
    }])
    formulas = runner.build_formula_draft(config, pd.DataFrame({
        "source_id": [source["source_id"] for source in config["paper_sources"]],
        "sha256": ["a" * 64] * len(config["paper_sources"]),
    }))
    formulas["formula_gate"] = "pass"
    manifest.to_csv(cache / "source_acquisition_manifest.csv", index=False)
    formulas.to_csv(cache / "paper_formula_registry_draft.csv", index=False)
    auth = {
        "authorization_granted": True, "all_implementation_choices_resolved": True,
        "reviewer": "fixture", "reviewed_at": "2026-07-10T00:00:00Z",
        "source_acquisition_manifest_sha256": runner.file_sha(cache / "source_acquisition_manifest.csv"),
        "formula_registry_draft_sha256": runner.file_sha(cache / "paper_formula_registry_draft.csv"),
        "reviewed_source_ids": ["s1"], "reviewed_formula_ids": list(formulas["formula_id"]),
    }
    (cache / "formula_review_authorization.json").write_text(json.dumps(auth), encoding="utf-8")
    config["paths"]["paper_cache_root"] = str(cache)
    returned_manifest, returned_formulas, _ = runner.validate_formula_authorization(config)
    assert len(returned_manifest) == 1
    assert returned_formulas["formula_gate"].eq("pass").all()
    auth["formula_registry_draft_sha256"] = "0" * 64
    (cache / "formula_review_authorization.json").write_text(json.dumps(auth), encoding="utf-8")
    with pytest.raises(PermissionError, match="hash_mismatch"):
        runner.validate_formula_authorization(config)


def test_isolated_fixture_runs_freeze_and_finalize_without_outcome_access(tmp_path: Path) -> None:
    config = runner.load_config()
    cache = tmp_path / "papers"
    cache.mkdir()
    source_rows = []
    for source in config["paper_sources"]:
        source_rows.append({
            "source_id": source["source_id"], "requested_url": source["url"], "resolved_url": source["url"],
            "resolved_domain": source["allowed_domains"][0], "content_role": "fixture_full_text",
            "http_status": 200, "content_type": "application/pdf", "local_path": "fixture",
            "byte_size": 20000, "sha256": "a" * 64, "acquired_at_utc": "2026-07-10T00:00:00Z",
            "allowlist_gate": "pass", "content_validation_gate": "pass", "acquisition_error": "",
        })
    source_manifest = pd.DataFrame(source_rows)[runner.SOURCE_COLUMNS]
    formulas = runner.build_formula_draft(config, source_manifest)
    formulas["formula_gate"] = "pass"
    source_manifest.to_csv(cache / "source_acquisition_manifest.csv", index=False)
    formulas.to_csv(cache / "paper_formula_registry_draft.csv", index=False)
    auth = {
        "authorization_type": "paper_formula_registry_human_review", "reviewed_at": "2026-07-10T00:00:00Z",
        "reviewer": "fixture-reviewer", "source_acquisition_manifest_sha256": runner.file_sha(cache / "source_acquisition_manifest.csv"),
        "reviewed_source_ids": list(source_manifest["source_id"]), "reviewed_formula_ids": list(formulas["formula_id"]),
        "formula_registry_draft_sha256": runner.file_sha(cache / "paper_formula_registry_draft.csv"),
        "all_implementation_choices_resolved": True, "authorization_granted": True,
    }
    (cache / "formula_review_authorization.json").write_text(json.dumps(auth), encoding="utf-8")

    data_root = tmp_path / "data"
    qfq_root = data_root / "qfq"
    qfq_root.mkdir(parents=True)
    months = pd.date_range("2017-01-31", periods=108, freq="ME")
    instruments = ["SH600000", "SZ000001"]
    universe_rows = []
    for date in months:
        for instrument in instruments:
            universe_rows.append({
                "usable_trade_date": date.date().isoformat(), "instrument": instrument,
                "membership_date": (date - pd.Timedelta(days=1)).date().isoformat(),
                "available_time": f"{(date - pd.Timedelta(days=1)).date().isoformat()} close",
                "board_bucket": "main_board", "is_listed": True, "is_st": False, "is_suspended": False,
                "total_market_cap_cny": 10_000_000_000, "market_cap_source": "fixture",
                "source_asof_date": (date - pd.Timedelta(days=1)).date().isoformat(),
                "history_ready_240d_flag": True,
            })
    universe_path = data_root / "universe.csv"
    pd.DataFrame(universe_rows).to_csv(universe_path, index=False)
    qfq_columns = ["date", "open", "high", "low", "close", "volume", "money", "turnover_rate", "instrument", "source_function", "source_volume_unit", "source_turnover_unit"]
    for instrument in instruments:
        pd.DataFrame([["2017-01-31", 10, 11, 9, 10, 1000, 10000, 1.0, instrument, "fixture", "shares", "percent"]], columns=qfq_columns).to_csv(qfq_root / f"{instrument}.csv", index=False)
    benchmark_path = data_root / "benchmark.csv"
    pd.DataFrame([{
        "date": date.date().isoformat(), "trade_date": date.date().isoformat(), "index_alias": "csi300",
        "instrument": "SH000300", "close": 3000 + index, "source_function": "fixture", "source_volume_unit": "shares",
    } for index, date in enumerate(months)]).to_csv(benchmark_path, index=False)
    calendar_path = data_root / "calendar.csv"
    pd.DataFrame({"trade_date": [date.date().isoformat() for date in months]}).to_csv(calendar_path, index=False)
    security_path = data_root / "security.csv"
    pd.DataFrame({"instrument": instruments, "board_bucket": ["main_board", "main_board"]}).to_csv(security_path, index=False)
    sh_history = data_root / "sh_history"
    sh_history.mkdir()
    pd.DataFrame({"instrument": ["SH600000"]}).to_csv(sh_history / "SH600000.csv", index=False)
    market_path = data_root / "market_rules.csv"
    market = pd.read_csv(runner.resolve_paths(config)["market_rule_registry"])
    market["human_verified"] = True
    market.to_csv(market_path, index=False)

    config["paths"].update({
        "project_universe": str(universe_path), "qfq_root": str(qfq_root), "raw_ohlcv_root": str(qfq_root),
        "benchmark": str(benchmark_path), "trading_calendar": str(calendar_path), "security_master": str(security_path),
        "sh_name_history_root": str(sh_history), "paper_cache_root": str(cache), "market_rule_registry": str(market_path),
    })
    config["output"]["output_root"] = str(tmp_path / "output")
    config["project_contract"].update({
        "project_universe_unique_instrument_min": 2, "project_monthly_eligible_median_min": 2,
        "project_monthly_eligible_p10_min": 2, "qfq_file_n_min": 2, "qfq_overlap_rate_min": 1.0,
        "board_overlap_rate_min": 0.0, "board_column_n_min": 0,
    })
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    frozen = runner.freeze_stage(config_path)
    assert frozen["status"] == "sealed"
    finalized = runner.finalize_stage(config_path)
    assert finalized["status"] == "finalized"
    decision = pd.read_csv(tmp_path / "output/20A_preoutcome_contract_decision.csv").iloc[0]
    assert decision["decision_state"] == "20A_preoutcome_contract_ready"
    assert decision["project_adaptation_reachable"] in {True, "True"}
    assert decision["exact_replication_reachable"] in {False, "False"}
    assert decision["next_requirement_execution_authorized"] in {False, "False"}
    access = pd.read_csv(tmp_path / "output/freeze/outcome_access_audit.csv")
    assert access["outcome_columns_detected"].fillna("").eq("").all()
    assert not access["selection_or_tuning_allowed"].map(runner.bool_value).any()
    runner.verify_bundle(
        tmp_path / "output/freeze", "freeze_manifest_20a.json", "freeze_output_hashes_20a.json",
        runner.FREEZE_ARTIFACT_NAMES,
    )
