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

import run_feature_foundation_ablation as foundation  # noqa: E402


def test_selected_target_binding_coverage_flags_missing_usable_target() -> None:
    selected = pd.DataFrame(
        [
            {
                "selected_target_id": "target_a",
                "selected_fast_fail_label_id": "label_a",
                "selection_status": "selected",
                "usable_for_09C_supported_gate": True,
            },
            {
                "selected_target_id": "target_b",
                "selected_fast_fail_label_id": "label_b",
                "selection_status": "selected",
                "usable_for_09C_supported_gate": True,
            },
        ]
    )
    binding = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "target_a",
                "denominator_id": foundation.RISK_ON_R_CORE_DENOM,
            }
        ]
    )

    coverage = foundation.build_selected_target_binding_coverage(selected, binding)
    status, upstream_status, supported, missing = foundation.selected_target_binding_status(
        coverage
    )

    assert status == "partial"
    assert upstream_status == "upstream_contract_conflict"
    assert supported == ["target_a"]
    assert missing == ["target_b"]
    assert coverage.loc[
        coverage["selected_target_id"].eq("target_b"), "upstream_contract_conflict_flag"
    ].iloc[0]


def test_sample_key_uniqueness_allows_sample_id_reuse_across_denominators() -> None:
    binding = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "target_a",
                "denominator_id": foundation.RISK_ON_R_CORE_DENOM,
            },
            {
                "sample_id": "s1",
                "selected_target_id": "target_a",
                "denominator_id": foundation.RISK_ON_R6_DENOM,
            },
        ]
    )

    audit = foundation.build_sample_key_uniqueness_audit(binding)

    assert audit.loc[audit["denominator_id"].eq("all"), "sample_id_unique_n"].iloc[0] == 1
    assert audit.loc[audit["denominator_id"].eq("all"), "sample_key_unique_n"].iloc[0] == 2
    assert audit["sample_key_uniqueness_status"].eq("pass").all()


def test_sample_uniqueness_audit_reports_missing_target_and_horizon_slices() -> None:
    coverage = pd.DataFrame(
        [
            {
                "selected_target_id": "target_a",
                "selected_target_binding_coverage_status": "complete",
            },
            {
                "selected_target_id": "target_b",
                "selected_target_binding_coverage_status": "missing_binding",
            },
        ]
    )
    binding = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "target_a",
                "denominator_id": foundation.RISK_ON_R_CORE_DENOM,
            },
            {
                "sample_id": "s1",
                "selected_target_id": "target_a",
                "denominator_id": foundation.RISK_ON_R6_DENOM,
            },
            {
                "sample_id": "s2",
                "selected_target_id": "target_a",
                "denominator_id": foundation.RISK_OFF_E1_READONLY_DENOM,
            },
        ]
    )

    audit = foundation.build_sample_uniqueness_audit(
        coverage, binding, blocked_by_upstream_conflict=True
    )

    missing = audit.loc[audit["selected_target_id"].eq("target_b")]
    assert missing["weight_status"].tolist() == ["target_binding_missing"]
    target_a = audit.loc[audit["selected_target_id"].eq("target_a")]
    assert set(target_a["weight_horizon_id"]) == {
        foundation.FAST_FAIL_WEIGHT,
        foundation.HYBRID_WEIGHT,
    }
    assert target_a.groupby("denominator_id")["weight_horizon_id"].nunique().to_dict() == {
        foundation.RISK_OFF_E1_READONLY_DENOM: 2,
        foundation.RISK_ON_R_CORE_DENOM: 2,
        foundation.RISK_ON_R6_DENOM: 2,
    }
    assert (
        target_a.loc[
            target_a["denominator_id"].eq(foundation.RISK_ON_R6_DENOM), "scope_usage"
        ]
        .eq("readout_only")
        .all()
    )
    assert (
        target_a.loc[
            target_a["denominator_id"].eq(foundation.RISK_OFF_E1_READONLY_DENOM),
            "scope_usage",
        ]
        .eq("not_09B_scope_readonly")
        .all()
    )
    assert (
        target_a.loc[
            target_a["denominator_id"].eq(foundation.RISK_OFF_E1_READONLY_DENOM),
            "weight_status",
        ]
        .eq("not_09B_scope_readonly")
        .all()
    )


def test_manifest_hash_audit_detects_match_and_mismatch(tmp_path: Path) -> None:
    outputs = {}
    hashes = {}
    for output_id in [
        "selected_label_contract",
        "selected_label_event_bindings",
        "source_pool_reconstruction_audit",
        "fast_fail_label_contract",
        "cost_target_bridge",
        "label_mechanism_contract",
    ]:
        path = tmp_path / f"{output_id}.txt"
        path.write_text(f"{output_id}\n", encoding="utf-8")
        outputs[output_id] = str(path)
        hashes[output_id] = foundation.file_sha256(path)
    hashes["cost_target_bridge"] = "bad_hash"

    audit = foundation.build_09a_manifest_hash_audit(
        {"outputs": outputs, "output_hashes": hashes}
    )

    assert audit.loc[
        audit["output_id"].eq("selected_label_contract"), "status"
    ].iloc[0] == "pass"
    assert audit.loc[audit["output_id"].eq("cost_target_bridge"), "status"].iloc[0] == (
        "hash_mismatch"
    )


def test_source_pool_reconstruction_requires_r_core_and_r6_pass() -> None:
    source = pd.DataFrame(
        [
            {
                "source_pool_id": foundation.R_CORE_SCOPE,
                "status": "pass",
                "hard_gate_eligible_flag": True,
            },
            {
                "source_pool_id": foundation.R6_SCOPE,
                "status": "pass",
                "hard_gate_eligible_flag": True,
            },
            {
                "source_pool_id": "risk_off_e1_horizon_complete_readonly",
                "status": "pass",
                "hard_gate_eligible_flag": False,
            },
        ]
    )

    audit = foundation.build_source_pool_reconstruction_audit(source)

    assert foundation.source_pool_reconstruction_status(audit) == "pass"
    assert audit.loc[
        audit["source_pool_id"].eq(foundation.R_CORE_SCOPE), "scope_usage"
    ].iloc[0] == "supported_training"
    assert audit.loc[audit["source_pool_id"].eq(foundation.R6_SCOPE), "scope_usage"].iloc[
        0
    ] == "readout_only"
    assert (
        foundation.source_pool_reconstruction_status(source.iloc[[0]].copy())
        == "missing_required_scope"
    )


def test_industry_pit_unavailable_blocks_industry_features_but_allows_board_fallback() -> None:
    industry = pd.DataFrame(
        [
            {
                "feature_domain": "industry",
                "pit_available_flag": False,
                "coverage_rate": 0.0,
                "effective_date_policy": "not_available",
                "notes": "No PIT industry classification artifact.",
            },
            {
                "feature_domain": "style_proxy_board",
                "pit_available_flag": True,
                "coverage_rate": 1.0,
                "effective_date_policy": "source_membership_date close",
                "notes": "Board bucket fallback.",
            },
        ]
    )
    capability = pd.DataFrame(
        [
            {
                "family_id": "R4_industry_breadth_expansion",
                "data_dependency": "PIT industry classification",
            }
        ]
    )

    audit = foundation.build_industry_board_pit_membership_audit(industry, capability)

    assert (
        audit.loc[audit["feature_domain"].eq("industry"), "feature_policy"].iloc[0]
        == "block_industry_features"
    )
    assert (
        audit.loc[audit["feature_domain"].eq("style_proxy_board"), "feature_policy"].iloc[0]
        == "board_fallback_not_industry"
    )


def test_feature_definitions_include_fs0_and_stationary_hygiene_features() -> None:
    families = {item["feature_family"] for item in foundation.FEATURE_DEFINITIONS}
    methods = {item.get("stationary_hygiene_method", "") for item in foundation.FEATURE_DEFINITIONS}
    fracdiff_features = [
        item["feature_id"]
        for item in foundation.FEATURE_DEFINITIONS
        if item.get("fracdiff_status", "not_applied") != "not_applied"
    ]

    assert "FS0_baseline_h_features" in families
    assert "rolling_z_score_60d" in methods
    assert "rolling_percentile_60d" in methods
    assert "atr_normalization" in methods
    assert "sigma_normalization" in methods
    assert fracdiff_features == ["log_close_fracdiff_d04"]


def test_output_paths_include_single_feature_importance() -> None:
    outputs = foundation.output_paths()

    assert "single_feature_importance" in outputs
    assert outputs["single_feature_importance"].name == "single_feature_importance.csv"


def test_fast_fail_10d_active_interval_uses_touch_when_triggered() -> None:
    t1, status = foundation.trading_session_t1(
        "2024-01-02", "2024-01-05", True, 3, calendar=None
    )

    assert t1 == "2024-01-05"
    assert status == "complete"


def test_fast_fail_10d_active_interval_rejects_bad_touch_offset() -> None:
    t1, status = foundation.trading_session_t1(
        "2024-01-02", "2024-01-05", True, 12, calendar=None
    )

    assert t1 == ""
    assert status == "not_evaluable_10d"


def test_sample_uniqueness_weights_keep_10d_and_20d_horizons_separate() -> None:
    calendar = list(pd.date_range("2024-01-02", periods=25, freq="B"))
    binding = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "target_a",
                "denominator_id": foundation.RISK_ON_R_CORE_DENOM,
                "canonical_event_id": "e1",
                "instrument": "SH600000",
                "event_t0_date": "2024-01-01",
                "trade_time": "2024-01-02",
                "label_t1_date": "2024-01-29",
                "selected_fast_fail_10_label": False,
                "selected_fast_fail_touch_date": "",
                "selected_fast_fail_touch_offset_sessions": -1,
                "censoring_status": "complete",
            }
        ]
    )

    weights = foundation.build_sample_uniqueness_weights(binding, calendar, ["target_a"])

    fast = weights.loc[weights["weight_horizon_id"].eq(foundation.FAST_FAIL_WEIGHT)].iloc[0]
    hybrid = weights.loc[weights["weight_horizon_id"].eq(foundation.HYBRID_WEIGHT)].iloc[0]
    assert fast["active_interval_end"] == "2024-01-15"
    assert hybrid["active_interval_end"] == "2024-01-29"
    assert fast["weight_status"] == "complete"
    assert hybrid["weight_status"] == "complete"


def test_weighted_auc_handles_null_boolean_labels() -> None:
    auc = foundation.weighted_auc(
        pd.Series([True, None, False, True]),
        pd.Series([0.9, 0.2, 0.1, 0.8]).to_numpy(),
    )

    assert auc == 1.0
