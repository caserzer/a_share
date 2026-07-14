from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


EXPERIMENT = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT / "src/run_20b_p4_learned_monotonic_return_ranking_diagnostic.py"
CONFIG_PATH = EXPERIMENT / "configs/config_20b_p4_learned_monotonic_return_ranking_diagnostic.yaml"
OUTPUT = EXPERIMENT / "outputs/20B_P4_learned_monotonic_return_ranking_diagnostic_v1"
SPEC = importlib.util.spec_from_file_location("p4_mlrank", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_frozen_config_identity_features_and_scope() -> None:
    config, root = runner.load_config(CONFIG_PATH)
    assert root == EXPERIMENT
    assert config["identity"]["run_id"] == runner.RUN_ID
    assert config["features"]["ordered_feature_ids"] == runner.FEATURES
    assert config["research_scope"] == {
        "multi_factor_model_allowed": True,
        "P4_single_factor_repair_claim_allowed": False,
    }
    assert config["execution"]["authority_record_required"] is False


def test_hash_null_is_deterministic_and_instrument_specific() -> None:
    date = pd.Timestamp("2025-01-31")
    assert runner.hash_null_score(date, "SH600000") == runner.hash_null_score(date, "SH600000")
    assert runner.hash_null_score(date, "SH600000") != runner.hash_null_score(date, "SH600001")
    assert 0 <= runner.hash_null_score(date, "SH600000") <= 1


def test_decile_formula_and_tie_break() -> None:
    frame = pd.DataFrame({
        "scored_model_id": ["X"] * 20,
        "decision_date": [pd.Timestamp("2025-01-31")] * 20,
        "instrument_id": [f"I{x:02d}" for x in reversed(range(20))],
        "model_score": [1.0] * 20,
    })
    result = runner.assign_deciles(frame).sort_values("model_score_rank")
    assert result["instrument_id"].tolist() == [f"I{x:02d}" for x in range(20)]
    assert result.groupby("bucket_id").size().tolist() == [2] * 10
    assert result.iloc[0]["bucket_id"] == 1
    assert result.iloc[-1]["bucket_id"] == 10


def test_equal_return_values_keep_equal_rank_target() -> None:
    frame = pd.DataFrame({
        "decision_date": [pd.Timestamp("2025-01-31")] * 250,
        "instrument_id": [f"I{x:03d}" for x in range(250)],
        "project_resolved_next_month_return": np.repeat(np.arange(125), 2),
        "outcome_resolution": [runner.VALID_MARK] * 250,
    })
    result = runner._add_rank_labels(frame, 250)
    assert result.loc[0, "y_rank_pct"] == pytest.approx(result.loc[1, "y_rank_pct"])
    assert result["y_relevance"].between(0, 9).all()


def test_unknown_label_is_retained_without_rank() -> None:
    frame = pd.DataFrame({
        "decision_date": [pd.Timestamp("2025-01-31")] * 251,
        "instrument_id": [f"I{x:03d}" for x in range(251)],
        "project_resolved_next_month_return": list(np.arange(250, dtype=float)) + [np.nan],
        "outcome_resolution": [runner.VALID_MARK] * 250 + [runner.UNKNOWN],
    })
    result = runner._add_rank_labels(frame, 250)
    unknown = result.iloc[-1]
    assert not unknown["label_known"]
    assert np.isnan(unknown["y_rank_pct"])
    assert np.isnan(unknown["y_relevance"])


def test_common_month_shift_does_not_change_monotonic_metrics() -> None:
    rows = []
    rank_rows = []
    for month_idx, date in enumerate(pd.to_datetime(["2025-01-31", "2025-02-28"])):
        for bucket in range(1, 11):
            rows.append({
                "scored_model_id": "X", "model_family_id": "F", "fit_id": "fit",
                "split": "validation", "decision_date": date, "label_month": "x",
                "return_semantics": runner.RETURN_PRIMARY, "bucket_id": bucket,
                "centered_bucket_return": bucket / 100.0, "month_evaluable": True,
            })
        rank_rows.append({"scored_model_id": "X", "decision_date": date,
                          "security_rank_ic": 0.1 + month_idx})
    base = runner.monotonicity_metrics(pd.DataFrame(rows), pd.DataFrame(rank_rows), "validation").iloc[0]
    shifted = pd.DataFrame(rows)
    shifted["centered_bucket_return"] += np.repeat([0.25, -0.40], 10)
    shifted["centered_bucket_return"] -= shifted.groupby("decision_date")["centered_bucket_return"].transform("mean")
    again = runner.monotonicity_metrics(shifted, pd.DataFrame(rank_rows), "validation").iloc[0]
    assert base["aggregate_bucket_mean_spearman"] == pytest.approx(again["aggregate_bucket_mean_spearman"])
    assert base["adjacent_order_rate"] == pytest.approx(again["adjacent_order_rate"])


def test_hac_uses_frozen_lag_and_returns_finite_result() -> None:
    stat, p_value = runner.hac_mean([0.01, 0.02, -0.01, 0.03, 0.02], lag=3)
    assert np.isfinite(stat)
    assert 0 <= p_value <= 1


def test_stage_registry_does_not_hash_itself(tmp_path: Path) -> None:
    stage = tmp_path / "preflight"
    stage.mkdir(parents=True)
    (stage / "payload.txt").write_text("x\n", encoding="utf-8")
    bundle = runner.seal_stage(tmp_path, "preflight", "preflight_manifest.json", "preflight_output_hashes.json")
    registry = json.loads((stage / "preflight_output_hashes.json").read_text(encoding="utf-8"))
    assert "preflight_output_hashes.json" not in registry
    assert "preflight_manifest.json" in registry
    assert bundle == runner.sha256_file(stage / "preflight_output_hashes.json")
    assert runner.verify_stage(tmp_path, "preflight", "preflight_manifest.json", "preflight_output_hashes.json")


def test_output_bundle_hashes_and_required_inventory_when_materialized() -> None:
    if not OUTPUT.exists():
        pytest.skip("full output has not been materialized")
    registry = json.loads((OUTPUT / runner.HASHES_NAME).read_text(encoding="utf-8"))
    assert runner.HASHES_NAME not in registry
    for relative, expected in registry.items():
        assert runner.sha256_file(OUTPUT / relative) == expected
    required = [
        "materialized/feature_panel.parquet",
        "selection/candidate_selection.csv",
        "models/model_artifact_registry.csv",
        "scores/robustness_model_score_panel.parquet",
        "historical/monotonicity_readout.csv",
        "determinism/determinism_comparison.csv",
        runner.DECISION_NAME, runner.REPORT_NAME, runner.MANIFEST_NAME,
    ]
    assert all((OUTPUT / relative).is_file() for relative in required)
