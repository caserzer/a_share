#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r03a_probability_survival_step_feasibility_v1.yaml"
REPORT_FILES = {
    "input": "r03a_input_readiness_audit.csv",
    "t0": "r03a_t0_episode_prior.csv",
    "survival": "r03a_survival_same_grain_lift.csv",
    "grid": "r03a_candidate_grid_train_selection.csv",
    "baseline": "r03a_baseline_comparison.csv",
    "readonly": "r03a_validation_robustness_readonly.csv",
    "bundle_context": "r03a_descriptive_bundle_context_prior.csv",
    "fresh": "r03a_fresh_evidence_descriptive_audit.csv",
    "null": "r03a_null_result_audit.csv",
    "report": "r03a_probability_survival_step_feasibility_report.md",
}
MIN_PROB_COLS = {
    "label_denominator_count",
    "P_good",
    "P_bad",
    "P_neutral",
    "P_good_lower",
    "P_good_upper",
    "P_bad_lower",
    "P_bad_upper",
    "credible_interval_width_good",
    "credible_interval_width_bad",
}
BUCKET_SCHEMA_COLS = MIN_PROB_COLS | {
    "good_count",
    "bad_count",
    "neutral_count",
    "sample_sufficiency_status",
    "split_stability_status",
    "prior_source",
    "fallback_level",
}
EPISODE_COLS = {
    "seed_episode_id",
    "instrument_id",
    "seed_trade_date",
    "seed_entry_date",
    "seed_entry_price",
    "seed_same_day_bundle_key",
    "seed_same_day_family_count",
    "seed_family_set",
    "seed_type",
    "seed_primary_family_id",
    "split",
    "year",
    "label",
    "censored_or_invalid_reason",
    "good_path_flag",
    "bad_path_flag",
    "neutral_path_flag",
    "first_minus5_offset",
    "hit_plus10_before_minus5",
    "path_quality_flag",
    "max_drawdown_120d",
    "max_gain_120d",
    "close_return_t20",
    "close_return_t60",
    "close_return_t120",
    "train_inner_cv_fold_id",
    "selected_candidate_id",
    "candidate_scope_id",
    "baseline_3_scope_id",
    "episode_in_selected_seed_scope",
    "episode_survived_selected_checkpoint",
    "episode_probability_bucket_key",
    "episode_probability_score",
    "candidate_episode_included",
    "baseline_3_same_scope_episode_included",
}
GRID_REQUIRED = {
    "candidate_id",
    "candidate_scope_id",
    "baseline_3_scope_id",
    "seed_scope_id",
    "seed_scope_type",
    "survival_checkpoint",
    "probe_label",
    "survival_step_label",
    "probability_gate_threshold",
    "fallback_grain",
    "episode_probability_score_formula",
    "train_scoring_mode",
    "train_inner_cv_fold_count",
    "train_grid_total_candidate_count",
    "train_eligible_candidate_count_after_gate",
    "train_grid_multiplicity_status",
    "train_distinct_probability_bucket_count",
    "degenerate_probability_gate_status",
    "credible_interval_level",
    "r03a_gate_status",
    "fallback_grain_status",
    "fallback_grain_disallowed_reason",
    "train_oof_label_denominator",
    "train_oof_P_good",
    "train_oof_P_bad",
    "train_oof_P_neutral",
    "train_oof_P_good_lower",
    "train_oof_P_good_upper",
    "train_oof_P_bad_lower",
    "train_oof_P_bad_upper",
    "train_oof_credible_interval_width_good",
    "train_oof_credible_interval_width_bad",
    "train_oof_prob_feasibility_score",
    "train_oof_prob_edge_vs_baseline_3",
    "train_oof_bad_edge_ci_halfwidth_proxy",
    "train_oof_good_edge_ci_halfwidth_proxy",
    "train_oof_candidate_eligibility_threshold_smaller_than_ci_halfwidth",
    "train_candidate_split_pass",
    "selection_metric",
    "selection_metric_value",
    "tie_breaker_tuple",
    "selection_rank",
    "selected_in_train",
    "selection_reason",
}


def load_config(config_path: Path) -> dict[str, Any]:
    with topic_path(config_path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _check(condition: bool, check_id: str, detail: Any, rows: list[dict[str, Any]]) -> None:
    rows.append({"check_id": check_id, "status": "passed" if condition else "failed", "detail": str(detail)})


def _require_columns(df: pd.DataFrame, columns: set[str], check_id: str, rows: list[dict[str, Any]]) -> None:
    missing = sorted(columns - set(df.columns))
    _check(not missing, check_id, missing, rows)


def _prob_sum_ok(df: pd.DataFrame) -> bool:
    den = pd.to_numeric(df["label_denominator_count"], errors="coerce").fillna(0)
    sums = (
        pd.to_numeric(df["P_good"], errors="coerce")
        + pd.to_numeric(df["P_bad"], errors="coerce")
        + pd.to_numeric(df["P_neutral"], errors="coerce")
    )
    return bool(((den <= 0) | (sums.sub(1.0).abs() < 1e-8)).all())


def validate(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r03a_probability_survival_step_feasibility_manifest.json"
    rows: list[dict[str, Any]] = []

    for key, name in REPORT_FILES.items():
        _check((reports_dir / name).exists(), f"required_output_exists_{key}", relpath(reports_dir / name), rows)
    episode_path = cache_dir / "r03a_episode_first_trigger_panel.parquet"
    _check(episode_path.exists(), "episode_panel_exists", relpath(episode_path), rows)
    _check(manifest_path.exists(), "manifest_exists", relpath(manifest_path), rows)
    if not manifest_path.exists():
        result = {"validation_status": "failed", "failed_checks": ["manifest_exists"]}
        write_json(result, manifests_dir / "r03a_probability_survival_step_feasibility_validation.json")
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dfs = {
        key: pd.read_csv(reports_dir / name, low_memory=False)
        for key, name in REPORT_FILES.items()
        if name.endswith(".csv") and (reports_dir / name).exists()
    }
    episode = pd.read_parquet(episode_path) if episode_path.exists() else pd.DataFrame()

    _check(manifest.get("risk_budget_status") == "probability_only_ev_r_blocked", "risk_budget_status_blocked", manifest.get("risk_budget_status"), rows)
    _check(manifest.get("background_denominator_status") == "blocked_missing_denominator", "background_denominator_blocked", "", rows)
    _check(manifest.get("split_stability_status") == "partial_only", "split_stability_status_partial_only", manifest.get("split_stability_status"), rows)
    _check(manifest.get("episode_grain") == "episode_first_trigger", "episode_grain_episode_first_trigger", manifest.get("episode_grain"), rows)
    _check(manifest.get("label_priority_order") == ["censored_or_invalid", "bad_path", "good_path", "neutral_path"], "label_priority_bad_before_good", manifest.get("label_priority_order"), rows)
    _check(manifest.get("alpha_source") == "Jeffreys_prior", "alpha_source_jeffreys", manifest.get("alpha_source"), rows)
    _check(abs(float(manifest.get("credible_interval_level", 0)) - 0.90) < 1e-12, "credible_interval_level_090", manifest.get("credible_interval_level"), rows)
    _check(manifest.get("credible_interval_method") == "scipy_beta_marginal_quantile", "credible_interval_method_recorded", manifest.get("credible_interval_method"), rows)
    _check(float(manifest.get("credible_interval_tolerance", 0)) == 1.0e-12, "credible_interval_tolerance_recorded", manifest.get("credible_interval_tolerance"), rows)
    _check("train_empirical_fallback_prior" not in json.dumps(manifest), "forbidden_empirical_prior_absent", "", rows)
    _check(manifest.get("train_scoring_mode") == "train_inner_cv_out_of_fold", "train_scoring_mode_oof", manifest.get("train_scoring_mode"), rows)
    _check(int(manifest.get("train_inner_cv_fold_count", 0)) == 5, "train_inner_cv_fold_count_recorded", manifest.get("train_inner_cv_fold_count"), rows)
    _check(manifest.get("episode_construction_hash_mode") in {"preferred_rule_hash", "upstream_manifest_and_episode_audit_fallback"}, "episode_hash_mode_allowed", manifest.get("episode_construction_hash_mode"), rows)
    if manifest.get("episode_construction_hash_mode") == "upstream_manifest_and_episode_audit_fallback":
        _check(bool(manifest.get("upstream_path_query_manifest_hash")), "fallback_manifest_hash_present", "", rows)
        _check(bool(manifest.get("upstream_path_query_validation_hash")), "fallback_validation_hash_present", "", rows)
        _check(bool(manifest.get("upstream_episode_audit_file_hashes")), "fallback_episode_audit_hashes_present", "", rows)
    _check(len(manifest.get("frozen_family_universe", [])) == 7, "frozen_family_count_7", len(manifest.get("frozen_family_universe", [])), rows)
    _check(not manifest.get("fresh_evidence_gate_allowed"), "fresh_gate_forbidden", manifest.get("fresh_evidence_gate_allowed"), rows)
    _check(not manifest.get("bundle_context_primary_gate_allowed"), "bundle_context_primary_gate_forbidden", manifest.get("bundle_context_primary_gate_allowed"), rows)

    _require_columns(episode, EPISODE_COLS, "episode_required_columns_present", rows)
    if not episode.empty:
        multi = episode["seed_same_day_family_count"].astype(int).gt(1)
        _check(
            episode.loc[multi, "seed_primary_family_id"].astype(str).eq("multi_family_bundle").all(),
            "multi_family_primary_literal",
            "",
            rows,
        )
        dup = episode.duplicated(["instrument_id", "seed_trade_date"])
        _check(not dup.any(), "same_day_multiple_families_single_risk_unit", int(dup.sum()), rows)

    t0 = dfs.get("t0", pd.DataFrame())
    _require_columns(t0, BUCKET_SCHEMA_COLS, "t0_full_bucket_schema_present", rows)
    if not t0.empty and MIN_PROB_COLS.issubset(t0.columns):
        _check(_prob_sum_ok(t0), "t0_probabilities_sum_to_one", "", rows)
        _check(
            np.allclose(
                pd.to_numeric(t0["credible_interval_width_good"], errors="coerce"),
                pd.to_numeric(t0["P_good_upper"], errors="coerce") - pd.to_numeric(t0["P_good_lower"], errors="coerce"),
                equal_nan=True,
            ),
            "t0_ci_width_good_consistent",
            "",
            rows,
        )

    survival = dfs.get("survival", pd.DataFrame())
    survival_required = {
        "checkpoint",
        "survival_lift_grain",
        "seed_primary_family_id_or_all",
        "pre_checkpoint_episode_count",
        "survivor_episode_count",
        "non_survivor_episode_count",
        "survivor_rate",
        "survivor_label_denominator_count",
        "survivor_P_good",
        "survivor_P_bad",
        "survivor_P_neutral",
        "survivor_P_good_lower",
        "survivor_P_good_upper",
        "survivor_P_bad_lower",
        "survivor_P_bad_upper",
        "survivor_credible_interval_width_good",
        "survivor_credible_interval_width_bad",
        "non_survivor_label_denominator_count",
        "non_survivor_P_good",
        "non_survivor_P_bad",
        "non_survivor_P_neutral",
        "non_survivor_P_good_lower",
        "non_survivor_P_good_upper",
        "non_survivor_P_bad_lower",
        "non_survivor_P_bad_upper",
        "non_survivor_credible_interval_width_good",
        "non_survivor_credible_interval_width_bad",
        "survival_lift_good_vs_t0_same_grain",
        "survival_lift_bad_vs_t0_same_grain",
        "split_stability_status",
    }
    _require_columns(survival, survival_required, "survival_required_columns_present", rows)
    if not survival.empty:
        _check({"T+3", "T+5", "T+10"}.issubset(set(survival["checkpoint"].astype(str))), "survival_checkpoints_present", "", rows)

    grid = dfs.get("grid", pd.DataFrame())
    _require_columns(grid, GRID_REQUIRED, "grid_required_columns_present", rows)
    if not grid.empty:
        _check(grid["episode_probability_score_formula"].astype(str).eq("P_good_lower - P_bad_upper").all(), "score_formula_fixed", "", rows)
        _check(grid["train_scoring_mode"].astype(str).eq("train_inner_cv_out_of_fold").all(), "grid_train_scoring_oof", "", rows)
        _check(pd.to_numeric(grid["credible_interval_level"], errors="coerce").eq(0.90).all(), "grid_ci_level_fixed", "", rows)
        configured_thresholds = {float(x) for x in config["probability_gate_threshold_grid"]}
        _check(set(pd.to_numeric(grid["probability_gate_threshold"], errors="coerce").dropna()).issubset(configured_thresholds), "threshold_grid_fixed", "", rows)
        _check(not grid["seed_scope_id"].astype(str).str.contains("same_day_bundle_key|context_bucket_id").any(), "no_bundle_context_seed_scope", "", rows)
        _check(not grid["fallback_grain"].astype(str).eq("fresh_evidence_status").any(), "fresh_not_fallback_grain", "", rows)
        _check(
            set(grid["r03a_gate_status"].astype(str)).issubset({"sufficient_and_stable"}),
            "grid_rows_only_sufficient_and_stable",
            sorted(grid["r03a_gate_status"].astype(str).unique()),
            rows,
        )
        _check(
            bool(manifest.get("fallback_grain_evaluation_status", {}).get("same_day_bundle_key_and_context_bucket_require_bucket_level_sufficient_and_stable")),
            "fallback_bundle_context_requires_stable_buckets",
            manifest.get("fallback_grain_evaluation_status"),
            rows,
        )
        selected_count = int(grid["selected_in_train"].astype(str).str.lower().isin({"true", "1"}).sum())
        _check(selected_count <= 1, "at_most_one_selected_candidate", selected_count, rows)
        _check(
            int(manifest.get("train_grid_total_candidate_count", 0)) <= int(manifest.get("max_train_grid_total_candidate_count", 0)),
            "grid_total_within_cap",
            manifest.get("train_grid_total_candidate_count"),
            rows,
        )
        if int(manifest.get("train_eligible_candidate_count_after_gate", 0)) > int(manifest.get("max_train_eligible_candidate_count_after_gate", 0)):
            _check(selected_count == 0, "excessive_eligible_blocks_selection", selected_count, rows)

    baseline = dfs.get("baseline", pd.DataFrame())
    baseline_required = MIN_PROB_COLS | {
        "scenario_id",
        "comparison_role",
        "candidate_scope_id",
        "baseline_3_scope_id",
        "split",
        "year",
        "selected_checkpoint",
        "proxy_exposure_schedule_label",
        "risk_budget_status",
        "exposure_label_is_validated_size",
        "path_metric_denominator_policy",
        "seed_episode_count",
        "censored_or_invalid_count",
        "censored_or_invalid_rate",
        "max_drawdown_120d_p50",
        "max_drawdown_120d_p10",
        "max_drawdown_120d_p75",
        "max_drawdown_120d_p90",
        "drawdown_loss_120d_p90",
        "drawdown_severity_120d_p90",
        "max_gain_120d_p50",
        "max_gain_120d_p75",
        "max_gain_120d_p90",
        "close_return_t20_p50",
        "close_return_t60_p50",
        "close_return_t120_p50",
        "upside_capture_proxy",
        "upside_capture_ratio_vs_baseline3",
        "early_failure_rate",
        "candidate_split_pass",
        "comparison_vs_baseline_3_status",
    }
    _require_columns(baseline, baseline_required, "baseline_required_columns_present", rows)
    if not baseline.empty:
        required_scenarios = {
            "baseline_1_t0_full_entry",
            "baseline_2_t0_probe_only",
            "baseline_3_probe_survival_step_up",
            "candidate_probability_survival_step",
        }
        _check(required_scenarios.issubset(set(baseline["scenario_id"].astype(str))), "baseline_required_scenarios_present", "", rows)
        _check(not any(col for col in baseline.columns if "EV_R" in col or "expected_R" in col), "baseline_no_ev_r_fields", "", rows)
        _check(
            set(baseline["path_metric_denominator_policy"].astype(str)).issubset(
                {
                    "episode_first_trigger_label_denominator",
                    "episode_first_trigger_survivor_label_denominator",
                    "episode_first_trigger_candidate_included_label_denominator",
                }
            ),
            "baseline_denominator_policy_enum",
            "",
            rows,
        )
        _check(baseline["risk_budget_status"].astype(str).eq("probability_only_ev_r_blocked").all(), "baseline_risk_budget_blocked", "", rows)
        _check(~baseline["exposure_label_is_validated_size"].astype(str).str.lower().isin({"true", "1"}).any(), "exposure_not_validated_size", "", rows)
        b1 = baseline.loc[baseline["scenario_id"].eq("baseline_1_t0_full_entry")].sort_values(["split", "year"]).reset_index(drop=True)
        b2 = baseline.loc[baseline["scenario_id"].eq("baseline_2_t0_probe_only")].sort_values(["split", "year"]).reset_index(drop=True)
        metric_cols = [
            "seed_episode_count",
            "censored_or_invalid_count",
            "label_denominator_count",
            "P_good",
            "P_bad",
            "P_neutral",
            "max_gain_120d_p75",
            "drawdown_severity_120d_p90",
        ]
        eq = True
        for col in metric_cols:
            eq = eq and np.allclose(
                pd.to_numeric(b1[col], errors="coerce").fillna(999999.0),
                pd.to_numeric(b2[col], errors="coerce").fillna(999999.0),
                atol=1e-12,
                rtol=0,
            )
        _check(eq, "baseline_1_2_path_metrics_equivalent", "", rows)

    readonly = dfs.get("readonly", pd.DataFrame())
    if not readonly.empty:
        row = readonly.iloc[0]
        _check(row.get("validation_episode_probability_score_source") == "full_train_frozen_posterior", "validation_score_source_literal", row.get("validation_episode_probability_score_source"), rows)
        _check(row.get("validation_probability_evaluation_source") == "actual_validation_labels_after_frozen_inclusion", "validation_eval_source_literal", row.get("validation_probability_evaluation_source"), rows)
        _check(row.get("robustness_episode_probability_score_source") == "full_train_frozen_posterior", "robustness_score_source_literal", row.get("robustness_episode_probability_score_source"), rows)
        _check(row.get("robustness_probability_evaluation_source") == "actual_robustness_labels_after_frozen_inclusion", "robustness_eval_source_literal", row.get("robustness_probability_evaluation_source"), rows)
        _check(not bool(row.get("threshold_changed_after_train")), "threshold_not_changed", row.get("threshold_changed_after_train"), rows)
        _check(not bool(row.get("checkpoint_changed_after_train")), "checkpoint_not_changed", row.get("checkpoint_changed_after_train"), rows)
        _check(not bool(row.get("bucket_changed_after_train")), "bucket_not_changed", row.get("bucket_changed_after_train"), rows)

    bundle_context = dfs.get("bundle_context", pd.DataFrame())
    _require_columns(
        bundle_context,
        MIN_PROB_COLS
        | {
            "primary_gate_allowed",
            "reason_if_not_allowed",
            "fallback_level",
            "fallback_grain_allowed",
            "sample_sufficiency_status",
            "split_stability_status",
            "upstream_sample_sufficiency_status",
            "upstream_stability_status",
            "r03a_stability_status",
            "r03a_gate_status",
            "used_by_candidate",
        },
        "bundle_context_required_columns_present",
        rows,
    )
    if not bundle_context.empty:
        _check(~bundle_context["primary_gate_allowed"].astype(str).str.lower().isin({"true", "1"}).any(), "bundle_context_not_primary_gate", "", rows)

    fresh = dfs.get("fresh", pd.DataFrame())
    _require_columns(
        fresh,
        MIN_PROB_COLS
        | {
            "fresh_evidence_status",
            "fresh_offset_bucket",
            "fresh_family_id_first",
            "survival_checkpoint_conditioning",
            "same_survival_checkpoint_conditioning_status",
            "fresh_before_observable_failure_rate",
            "fresh_without_prior_observable_failure_rate",
            "split_stability_status",
            "gate_use_allowed",
            "reason_if_not_allowed",
        },
        "fresh_required_columns_present",
        rows,
    )
    if not fresh.empty:
        _check(~fresh["gate_use_allowed"].astype(str).str.lower().isin({"true", "1"}).any(), "fresh_gate_use_false", "", rows)

    null = dfs.get("null", pd.DataFrame())
    required_nulls = {
        "candidate_not_better_than_baseline_3_on_P_bad",
        "candidate_loses_too_much_upside_capture_vs_baseline_3",
        "candidate_only_wins_in_train",
        "candidate_depends_on_sparse_bucket",
        "candidate_depends_on_fresh_evidence_gate",
        "candidate_requires_ev_r_sizing",
        "baseline_1_2_path_metric_mismatch",
        "candidate_compared_to_global_baseline3",
        "multi_family_seed_component_selected_as_primary",
        "upstream_enum_not_normalized",
        "candidate_inclusion_formula_missing",
        "credible_interval_level_not_fixed",
        "drawdown_severity_uses_raw_p90_wrong_tail",
        "denominator_gate_not_applied",
        "candidate_train_scoring_used_in_sample_posterior",
        "candidate_grid_multiplicity_excessive",
        "candidate_eligibility_threshold_smaller_than_ci_halfwidth",
        "candidate_degenerate_probability_gate",
        "episode_construction_rule_hash_mismatch",
    }
    _check(required_nulls.issubset(set(null.get("null_condition", pd.Series(dtype=str)).astype(str))), "null_required_conditions_present", "", rows)

    report_text = (reports_dir / REPORT_FILES["report"]).read_text(encoding="utf-8") if (reports_dir / REPORT_FILES["report"]).exists() else ""
    forbidden = [
        "production-ready",
        "buy signal",
        "sell signal",
        "validated 1R allocation",
        "expected R positive",
        "EV_R passed",
        "fresh evidence gate validated",
        "portfolio-ready",
    ]
    _check(not any(token.lower() in report_text.lower() for token in forbidden), "report_forbidden_language_absent", "", rows)
    _check("Final decision:" in report_text and str(manifest.get("final_decision")) in report_text, "report_final_decision_present", manifest.get("final_decision"), rows)

    allowed_final = {
        "r03a_probability_feasibility_passed",
        "r03a_survival_step_baseline_sufficient_no_incremental_posterior_edge",
        "blocked_no_stable_candidate_bucket",
        "blocked_grid_multiplicity_excessive",
        "blocked_missing_required_input",
        "failed_validation_or_robustness",
        "invalid_requirement_violation",
    }
    _check(manifest.get("final_decision") in allowed_final, "final_decision_allowed", manifest.get("final_decision"), rows)
    if manifest.get("final_decision") == "r03a_probability_feasibility_passed" and not readonly.empty:
        row = readonly.iloc[0]
        _check(bool(row.get("validation_candidate_pass")) and bool(row.get("robustness_candidate_pass")), "pass_requires_validation_and_robustness", "", rows)

    audit = pd.DataFrame(rows)
    audit_path = reports_dir / "r03a_probability_survival_step_feasibility_validation_audit.csv"
    audit.to_csv(audit_path, index=False)
    failed = audit.loc[audit["status"].eq("failed"), "check_id"].tolist()
    result = {
        "validation_status": "passed" if not failed else "failed",
        "failed_checks": failed,
        "audit_path": relpath(audit_path),
    }
    manifest["validation_status"] = result["validation_status"]
    write_json(manifest, manifest_path)
    write_json(result, manifests_dir / "r03a_probability_survival_step_feasibility_validation.json")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate EP4 R03a probability-only survival-step feasibility artifacts.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    result = validate(Path(args.config))
    return 0 if result["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
