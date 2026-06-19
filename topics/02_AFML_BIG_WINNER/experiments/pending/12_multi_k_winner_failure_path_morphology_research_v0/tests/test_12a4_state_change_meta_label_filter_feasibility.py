from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a4_state_change_meta_label_filter_feasibility.py"
TABLE_DIR = (
    EXPERIMENT_DIR
    / "outputs"
    / "publishable"
    / "tables"
    / "12A4_state_change_meta_label_filter_feasibility"
)
LOCAL_MATRIX = (
    EXPERIMENT_DIR
    / "outputs"
    / "local_cache"
    / "12A4_state_change_meta_label_filter_feasibility"
    / "meta_label_event_feature_matrix.parquet"
)
MANIFEST_PATH = (
    EXPERIMENT_DIR
    / "outputs"
    / "manifests"
    / "12A4_state_change_meta_label_filter_feasibility_manifest.json"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a4_meta_label", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_entropy_normalization_uses_declared_state_count_not_nonempty_states():
    runner = load_runner()

    assert runner.entropy_from_states(["up"] * 20, 3) == 0.0
    value = runner.entropy_from_states(["up", "down"] * 10, 3)

    assert 0.0 < value < 1.0


def test_volume_acceleration_features_use_only_prior_window():
    runner = load_runner()
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=80).strftime("%Y-%m-%d"),
            "open": [10.0] * 80,
            "high": [10.5] * 80,
            "low": [9.5] * 80,
            "close": [10.0 + i * 0.01 for i in range(80)],
            "volume": [1000.0 + i * 10 for i in range(80)],
            "money": [10000.0 + i * 100 for i in range(80)],
            "turnover_rate": [0.01 + i * 0.0001 for i in range(80)],
        }
    )
    changed_future = daily.copy()
    changed_future.loc[61:, "volume"] = 9999999.0

    a = runner.build_single_daily_features(daily, 60)
    b = runner.build_single_daily_features(changed_future, 60)

    assert a["log_volume_accel_5d"] == b["log_volume_accel_5d"]
    assert a["volume_slope_accel_5_15d"] == b["volume_slope_accel_5_15d"]


def test_validation_threshold_health_forces_train_cv_when_unhealthy():
    runner = load_runner()
    config = runner.load_yaml(EXPERIMENT_DIR / "configs" / "config_12a4_state_change_meta_label_filter_feasibility.yaml")
    rows = []
    rows.extend({"event_split": "train", "target_low_to_high_inside": i < 602} for i in range(8303))
    rows.extend({"event_split": "validation", "target_low_to_high_inside": i < 43} for i in range(2151))
    frame = pd.DataFrame(rows)

    health = runner.build_validation_health(frame, config).iloc[0]

    assert health["validation_threshold_health_pass"] is False or health["validation_threshold_health_pass"] == False
    assert health["threshold_selection_source"] == "train_internal_cv"


def test_12a3_decision_gate_requires_label_parity():
    runner = load_runner()
    decision = pd.DataFrame(
        [
            {
                "decision_state": "12A3_state_change_backbone_partial_feature_source",
                "partial_feature_source_gate_pass": True,
                "label_recompute_gate_pass": True,
                "min_label_recompute_parity_match_rate": 1.0,
            }
        ]
    )
    parity = pd.DataFrame(
        [
            {
                "label_id": "failure_10_label",
                "parity_status": "pass",
                "parity_match_rate": 1.0,
                "min_required_match_rate": 0.995,
            }
        ]
    )

    ok, reason = runner.check_12a3_gate(decision, parity)
    assert ok
    bad = decision.copy()
    bad.loc[0, "label_recompute_gate_pass"] = False
    ok, reason = runner.check_12a3_gate(bad, parity)
    assert not ok
    assert "label_recompute_gate_pass" in reason


def test_blocked_gate_triggers_on_failed_input_gate():
    runner = load_runner()
    config = runner.load_yaml(EXPERIMENT_DIR / "configs" / "config_12a4_state_change_meta_label_filter_feasibility.yaml")
    baselines = pd.DataFrame(
        [
            {
                "source_arm_id": "C0_state_change",
                "split": "robustness",
                "low_to_high_precision": 0.08,
                "bad_side_10_20_rate": 0.2,
            },
            {
                "source_arm_id": "R_core",
                "split": "robustness",
                "low_to_high_precision": 0.07,
                "bad_side_10_20_rate": 0.2,
            },
        ]
    )
    validation = pd.DataFrame(
        [{"validation_threshold_health_pass": False, "threshold_selection_source": "train_internal_cv"}]
    )
    dictionary = pd.DataFrame([{"feature_name": "x", "allowed_for_primary_model": True}])

    decision, _ = runner.evaluate_decision(
        pd.DataFrame(),
        pd.DataFrame(),
        baselines,
        pd.DataFrame(),
        validation,
        dictionary,
        config,
        input_gate_pass=False,
    )

    assert decision.iloc[0]["decision_state"] == "12A4_blocked_input_or_pit_failure"


def test_required_outputs_exist_and_schema_after_full_run():
    required = {
        "input_artifact_audit.csv": {"artifact_id", "read_status", "schema_status", "sha256"},
        "regime_scope_exclusion_audit.csv": {"source_arm_id", "market_regime_bucket", "excluded_event_n"},
        "split_time_boundary_audit.csv": {"feature_group", "eval_split", "split_time_boundary_gate_pass"},
        "meta_label_event_universe.csv.gz": {"meta_event_id", "source_arm_id", "market_regime_bucket", "event_split"},
        "meta_label_event_targets.csv.gz": {"meta_event_id", "target_low_to_high_inside", "bad_side_10_20_label"},
        "meta_label_feature_dictionary.csv": {"feature_name", "feature_group", "allowed_for_primary_model", "pit_status"},
        "meta_label_feature_pit_audit.csv": {"feature_name", "pit_status", "coverage_rate"},
        "risk_on_r_core_baseline.csv": {"source_arm_id", "split", "regime_scope", "event_n", "low_to_high_event_precision"},
        "validation_threshold_health.csv": {"validation_threshold_health_pass", "threshold_selection_source"},
        "meta_label_score_bucket_frontier.csv": {"model_id", "split", "bucket_id", "low_to_high_precision"},
        "supported_gate_feasibility_selfcheck.csv": {"gate_name", "binding_implied_precision", "is_binding_constraint"},
        "lightgbm_challenger_score_bucket_frontier.csv": {"lightgbm_challenger_status"},
        "lightgbm_challenger_model_card.csv": {"model_id", "lightgbm_challenger_status", "allowed_for_supported_gate"},
        "meta_label_decision.csv": {"decision_state", "supported_gate_pass", "partial_feature_source_gate_pass"},
    }
    for file_name, columns in required.items():
        path = TABLE_DIR / file_name
        assert path.exists(), file_name
        frame = pd.read_csv(path, nrows=5, low_memory=False)
        assert columns.issubset(frame.columns), file_name
    assert LOCAL_MATRIX.exists()


def test_primary_universe_contains_only_risk_on_events():
    universe = pd.read_csv(TABLE_DIR / "meta_label_event_universe.csv.gz", low_memory=False)

    assert set(universe["market_regime_bucket"].dropna().astype(str)) == {"risk_on"}
    c0 = universe.loc[universe["source_arm_id"].eq("C0_state_change")]
    assert not c0.empty
    assert set(c0["source_arm_role"]) == {"primary_decision_population"}
    required_readout = {
        "source_event_id",
        "source_arm_is_c0",
        "source_arm_is_r_core",
        "readout_c0_intersect_r_core_same_day",
        "readout_c0_without_prior_r_core_5_sessions",
        "readout_r_core_without_prior_c0_5_sessions",
        "readout_c0_after_prior_r_core_5_sessions",
        "readout_r_core_after_prior_c0_5_sessions",
    }
    assert required_readout.issubset(universe.columns)
    assert bool(c0["source_arm_is_c0"].all())
    r_core = universe.loc[universe["source_arm_id"].eq("R_core")]
    assert not r_core.empty
    assert bool(r_core["source_arm_is_r_core"].all())


def test_regime_exclusion_audit_records_r_core_transition_exclusion():
    audit = pd.read_csv(TABLE_DIR / "regime_scope_exclusion_audit.csv")
    excluded = audit.loc[
        audit["source_arm_id"].eq("R_core")
        & audit["market_regime_bucket"].eq("transition")
        & audit["exclusion_reason"].eq("r_core_non_risk_on_scope")
    ]
    assert not excluded.empty
    assert int(excluded["excluded_event_n"].sum()) > 0


def test_feature_dictionary_blocks_forbidden_primary_features():
    dictionary = pd.read_csv(TABLE_DIR / "meta_label_feature_dictionary.csv")
    allowed = dictionary.loc[dictionary["allowed_for_primary_model"].astype(bool), "feature_name"].astype(str)
    forbidden = [
        "episode_low",
        "episode_high",
        "future",
        "target_",
        "label_",
        "winner_",
        "fast_fail_",
        "false_repair_",
        "bad_side_",
        "inside_window",
    ]

    assert not any(any(pattern in name for pattern in forbidden) for name in allowed)


def test_feature_dictionary_covers_required_source_and_r_core_interaction_features():
    dictionary = pd.read_csv(TABLE_DIR / "meta_label_feature_dictionary.csv")
    features = set(dictionary["feature_name"].astype(str))
    required = {
        "source_arm_is_c0",
        "source_arm_is_r_core",
        "has_r_core_same_day_at_t0_close",
        "has_prior_r_core_within_5_sessions",
        "sessions_since_nearest_prior_r_core_event",
        "c0_after_prior_r_core_within_5_sessions",
        "r_core_active_same_risk_on_scope",
    }
    assert required.issubset(features)
    blocked = dictionary.loc[dictionary["feature_name"].isin(["source_arm_is_c0", "source_arm_is_r_core"])]
    assert not blocked["allowed_for_primary_model"].astype(bool).any()


def test_volume_acceleration_audit_records_train_frozen_winsorization():
    audit = pd.read_csv(TABLE_DIR / "volume_acceleration_feature_audit.csv")
    with_cutoffs = audit.loc[
        audit["feature_name"].astype(str).str.contains("volume|turnover", regex=True)
        & audit["split"].eq("all")
        & audit["winsorization_lower_cutoff"].notna()
        & audit["winsorization_upper_cutoff"].notna()
    ]
    assert not with_cutoffs.empty


def test_r_core_baseline_exists_by_split_and_validation_fallback():
    baseline = pd.read_csv(TABLE_DIR / "risk_on_r_core_baseline.csv")
    rcore_splits = set(baseline.loc[baseline["source_arm_id"].eq("R_core"), "split"])
    health = pd.read_csv(TABLE_DIR / "validation_threshold_health.csv").iloc[0]

    assert {"all", "train", "validation", "robustness"}.issubset(rcore_splits)
    assert set(baseline["regime_scope"].astype(str)) == {"risk_on"}
    assert bool(health["validation_threshold_health_pass"]) is False
    assert health["threshold_selection_source"] == "train_internal_cv"


def test_lightgbm_challenger_cannot_set_supported_decision_state():
    card = pd.read_csv(TABLE_DIR / "lightgbm_challenger_model_card.csv")
    decision = pd.read_csv(TABLE_DIR / "meta_label_decision.csv").iloc[0]

    assert not bool(card["allowed_for_supported_gate"].iloc[0])
    if decision["decision_state"] == "12A4_meta_label_supported":
        assert decision["supporting_model_family"] != "lightgbm_challenger_diagnostic_only"


def test_manifest_hashes_match_generated_outputs():
    runner = load_runner()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    decision_path = TABLE_DIR / "meta_label_decision.csv"
    report_path = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "state_change_meta_label_filter_decision_report.md"

    assert manifest["final_decision"] in {
        "12A4_meta_label_supported",
        "12A4_meta_label_partial_feature_source",
        "12A4_meta_label_diagnostic_only",
        "12A4_nonlinear_candidate_requires_12A5_validation",
        "12A4_no_meta_label_uplift",
        "12A4_blocked_input_or_pit_failure",
    }
    assert manifest["outputs"]["decision"]["sha256"] == runner.path_sha(decision_path)
    assert manifest["outputs"]["report"]["sha256"] == runner.path_sha(report_path)
