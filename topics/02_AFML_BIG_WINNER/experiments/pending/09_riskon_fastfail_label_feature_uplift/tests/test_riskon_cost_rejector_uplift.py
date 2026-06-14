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

import run_riskon_cost_rejector_uplift as uplift  # noqa: E402


def test_target_component_contract_freezes_09a_fields_and_weight_horizons() -> None:
    contract = uplift.target_component_contract()

    assert set(contract["target_component"]) == {
        "fast_fail_only_10d",
        "false_repair_20d_component",
        "hybrid_cost_bad_10_20",
    }
    mapping = contract.set_index("target_component").to_dict("index")
    assert mapping["fast_fail_only_10d"]["binding_field"] == "selected_fast_fail_10_label"
    assert mapping["fast_fail_only_10d"]["weight_horizon_id"] == "fast_fail_10d"
    assert mapping["hybrid_cost_bad_10_20"]["binding_field"] == "selected_cost_bad_10_20_target"
    assert mapping["hybrid_cost_bad_10_20"]["weight_horizon_id"] == "cost_bad_10_20_20d"
    assert contract["selected_target_id"].eq(uplift.SUPPORTED_TARGET_ID).all()


def test_feature_sets_keep_fs0_baseline_and_overlap_ablations_separate() -> None:
    contract = pd.DataFrame(
        [
            {
                "feature_id": "return_10d",
                "feature_family": "FS0_baseline_h_features",
                "label_mechanism_overlap_type": "none",
                "stationary_hygiene_method": "train_z",
                "fracdiff_status": "not_applied",
            },
            {
                "feature_id": "close_to_high_120",
                "feature_family": "FS0_baseline_h_features",
                "label_mechanism_overlap_type": "related",
                "stationary_hygiene_method": "train_z",
                "fracdiff_status": "not_applied",
            },
            {
                "feature_id": "close_to_ema20",
                "feature_family": "FS2_basis_path_quality",
                "label_mechanism_overlap_type": "related",
                "stationary_hygiene_method": "train_z",
                "fracdiff_status": "not_applied",
            },
            {
                "feature_id": "log_close_fracdiff_d04",
                "feature_family": "FS0_baseline_h_features",
                "label_mechanism_overlap_type": "none",
                "stationary_hygiene_method": "selected_fracdiff_log_close_d04",
                "fracdiff_status": "applied_d_0.4",
            },
        ]
    )
    feature_sets = uplift.build_feature_sets(
        contract,
        [
            "return_10d",
            "close_to_high_120",
            "close_to_ema20",
            "log_close_fracdiff_d04",
        ],
    )

    assert feature_sets["baseline_fs0"] == [
        "return_10d",
        "close_to_high_120",
        "log_close_fracdiff_d04",
    ]
    assert "close_to_ema20" not in feature_sets["drop_fs2_related_subset_only"]
    assert "close_to_high_120" not in feature_sets["drop_direct_related_overlap"]
    assert "log_close_fracdiff_d04" not in feature_sets["drop_fs0_rolling_fracdiff_hygiene"]
    assert "return_10d" in feature_sets["drop_fs0_rolling_fracdiff_hygiene"]
    assert "close_to_ema20" in feature_sets["drop_fs0_rolling_fracdiff_hygiene"]
    assert feature_sets["family_representative_features_only"] == ["return_10d", "close_to_ema20"]


def test_forbidden_feature_audit_blocks_label_columns() -> None:
    status, forbidden_count, audit = uplift.forbidden_feature_audit(
        ["return_10d", "selected_fast_fail_10_label", "future_high"]
    )

    assert status == "blocked"
    assert forbidden_count == 2
    blocked = audit.loc[audit["forbidden_feature_flag"], "feature_id"].tolist()
    assert blocked == ["selected_fast_fail_10_label", "future_high"]


def test_component_bucket_is_mutually_exclusive() -> None:
    frame = pd.DataFrame(
        {
            "selected_fast_fail_10_label": [1, 0, 1, 0],
            "frozen_false_repair_20d_label": [0, 1, 1, 0],
        }
    )

    assert uplift.component_bucket(frame).tolist() == [
        "fast_fail_only",
        "false_repair_only",
        "both",
        "neither",
    ]


def test_final_decision_uses_source_caveated_variant_for_research_pass() -> None:
    selection = {
        "selected_model_id": "m1",
        "selected_threshold_id": "keep_0800",
        "selection_status": "train_gate_pass",
    }
    frontier = pd.DataFrame(
        [
                {
                    "model_id": "m1",
                    "model_family": "regularized_logistic_or_elastic_net",
                    "ablation_id": "full",
                    "calibration_id": "none",
                    "threshold_id": "keep_0800",
                    "denominator_id": uplift.R_CORE_DENOM,
                    "split": "train",
                "rejected_fraction": 0.20,
                "relative_cost_reduction": 0.20,
                "any_recall_retention": 0.91,
            },
                {
                    "model_id": "m1",
                    "model_family": "regularized_logistic_or_elastic_net",
                    "ablation_id": "full",
                    "calibration_id": "none",
                    "threshold_id": "keep_0800",
                    "denominator_id": uplift.R_CORE_DENOM,
                    "split": "validation",
                "rejected_fraction": 0.21,
                "relative_cost_reduction": 0.02,
                "any_recall_retention": 0.86,
            },
                {
                    "model_id": "m1",
                    "model_family": "regularized_logistic_or_elastic_net",
                    "ablation_id": "full",
                    "calibration_id": "none",
                    "threshold_id": "keep_0800",
                    "denominator_id": uplift.R_CORE_DENOM,
                    "split": "robustness",
                "rejected_fraction": 0.22,
                "relative_cost_reduction": 0.01,
                "any_recall_retention": 0.84,
            },
        ]
    )
    contribution = pd.DataFrame(
        [
            {
                "model_id": "m1",
                "threshold_id": "keep_0800",
                "denominator_id": uplift.R_CORE_DENOM,
                "split": "train",
                "fast_fail_attributed_cost_reduction_share": 0.20,
            }
        ]
    )
    density = pd.DataFrame([{"status": "pass", "cap_usage_ratio": 0.5}])
    separability = pd.DataFrame(
        [
                {
                    "model_id": "m1",
                    "model_family": "regularized_logistic_or_elastic_net",
                    "ablation_id": "full",
                    "calibration_id": "none",
                    "train_target_component": "fast_fail_only_10d",
                    "denominator_id": uplift.R_CORE_DENOM,
                "split": "robustness",
                "roc_auc": 0.61,
            }
        ]
    )

    decision, gate = uplift.final_decision(
        selection,
        frontier,
        contribution,
        density,
        separability,
        source_caveated=True,
        config={"cost_rejector": {"research_entry_gate": {}}},
    )

    assert decision == uplift.DECISION_RESEARCH_CAVEATED
    assert gate["spread_gate_pass"] is True


def test_final_decision_forces_diagnostic_when_oos_spread_exceeds_limit() -> None:
    selection = {
        "selected_model_id": "m1",
        "selected_threshold_id": "keep_0800",
        "selection_status": "train_gate_pass",
    }
    frontier = pd.DataFrame(
        [
            {
                "model_id": "m1",
                "model_family": "regularized_logistic_or_elastic_net",
                "ablation_id": "full",
                "calibration_id": "none",
                "threshold_id": "keep_0800",
                "denominator_id": uplift.R_CORE_DENOM,
                "split": "train",
                "rejected_fraction": 0.10,
                "relative_cost_reduction": 0.20,
                "any_recall_retention": 0.91,
            },
            {
                "model_id": "m1",
                "model_family": "regularized_logistic_or_elastic_net",
                "ablation_id": "full",
                "calibration_id": "none",
                "threshold_id": "keep_0800",
                "denominator_id": uplift.R_CORE_DENOM,
                "split": "robustness",
                "rejected_fraction": 0.30,
                "relative_cost_reduction": 0.05,
                "any_recall_retention": 0.86,
            },
        ]
    )
    contribution = pd.DataFrame(
        [
            {
                "model_id": "m1",
                "threshold_id": "keep_0800",
                "denominator_id": uplift.R_CORE_DENOM,
                "split": "train",
                "fast_fail_attributed_cost_reduction_share": 0.20,
            }
        ]
    )
    density = pd.DataFrame([{"status": "pass", "cap_usage_ratio": 0.5}])
    separability = pd.DataFrame(
        [
            {
                "model_id": "m1",
                "model_family": "regularized_logistic_or_elastic_net",
                "ablation_id": "full",
                "calibration_id": "none",
                "train_target_component": "fast_fail_only_10d",
                "denominator_id": uplift.R_CORE_DENOM,
                "split": "robustness",
                "roc_auc": 0.70,
            },
            {
                "model_id": "m1",
                "model_family": "regularized_logistic_or_elastic_net",
                "ablation_id": "full",
                "calibration_id": "none",
                "train_target_component": "hybrid_cost_bad_10_20",
                "denominator_id": uplift.R_CORE_DENOM,
                "split": "robustness",
                "roc_auc": 0.70,
            },
        ]
    )

    decision, gate = uplift.final_decision(
        selection,
        frontier,
        contribution,
        density,
        separability,
        source_caveated=True,
        config={
            "cost_rejector": {
                "oos_positive_rate_spread_force_diagnostic_threshold": 0.15,
                "research_entry_gate": {},
            }
        },
    )

    assert gate["spread_gate_pass"] is False
    assert decision == uplift.DECISION_DIAGNOSTIC


def test_metric_input_frame_drops_zero_weight_only_for_r_core_train() -> None:
    frame = pd.DataFrame(
        {
            "denominator_id": [uplift.R_CORE_DENOM, uplift.R_CORE_DENOM],
            "event_split": ["train", "train"],
            "final_sample_weight": [1.0, 0.0],
            "score": [0.1, 0.9],
            "selected_cost_bad_10_20_target": [0, 1],
        }
    )

    train_frame = uplift.metric_input_frame(frame, uplift.R_CORE_DENOM, "train")
    robust_frame = uplift.metric_input_frame(frame, uplift.R_CORE_DENOM, "robustness")

    assert len(train_frame) == 1
    assert len(robust_frame) == 2


def test_riskoff_readonly_control_reports_09a_binding_input_count() -> None:
    data = pd.DataFrame({"denominator_id": [uplift.R_CORE_DENOM]})
    binding = pd.DataFrame(
        {
            "denominator_id": [
                uplift.R_CORE_DENOM,
                uplift.RISK_OFF_READONLY_DENOM,
                uplift.RISK_OFF_READONLY_DENOM,
            ]
        }
    )
    contract = pd.DataFrame({"feature_id": ["return_10d"]})

    control, coverage = uplift.build_riskoff_tables(data, binding, contract)

    assert control["riskoff_input_event_n"].iloc[0] == 2
    assert control["scored_event_n"].iloc[0] == 0
    assert coverage["status"].iloc[0] == "riskoff_feature_matrix_not_materialized"
