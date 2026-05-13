#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP4_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r02_family_precision_forward_return_stats_v1.yaml"
REQUIRED_CACHE = [
    "r02_family_action_time_panel.parquet",
    "r02_family_background_prior_panel.parquet",
]
REQUIRED_REPORTS = [
    "r02_family_frozen_condition_audit.csv",
    "r02_family_precision_summary.csv",
    "r02_family_precision_by_split.csv",
    "r02_family_precision_by_year.csv",
    "r02_family_forward_return_stats.csv",
    "r02_family_forward_return_stats_by_split.csv",
    "r02_family_episode_precision_summary.csv",
    "r02_family_episode_forward_return_stats.csv",
    "r02_family_signal_overlap_matrix.csv",
    "r02_family_signal_redundancy_long.csv",
    "r02_family_signal_phi_correlation_matrix.csv",
    "r02_family_signal_jaccard_matrix.csv",
    "r02_family_signal_incremental_precision.csv",
    "r02_family_top4_independence_selection_audit.csv",
    "r02_family_top4_combined_precision.csv",
    "r02_family_missingness_audit.csv",
    "r02_family_background_prior_audit.csv",
    "r02_family_decision_gate_audit.csv",
    "r02_family_precision_forward_return_final_report.md",
]


def load_config(config_path: Path) -> dict[str, Any]:
    with topic_path(config_path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _check(condition: bool, check_id: str, detail: str, rows: list[dict[str, Any]]) -> None:
    rows.append({"check_id": check_id, "status": "passed" if condition else "failed", "detail": detail})


def validate(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    output_root = topic_path(config["output_root"])
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r02_family_precision_forward_return_stats_manifest.json"
    rows: list[dict[str, Any]] = []

    for name in REQUIRED_CACHE:
        _check((cache_dir / name).exists(), f"cache_exists_{name}", relpath(cache_dir / name), rows)
    for name in REQUIRED_REPORTS:
        _check((reports_dir / name).exists(), f"report_exists_{name}", relpath(reports_dir / name), rows)
    _check(manifest_path.exists(), "manifest_exists", relpath(manifest_path), rows)
    if not manifest_path.exists():
        result = {"validation_status": "failed", "failed_checks": ["manifest_exists"]}
        write_json(result, manifests_dir / "r02_family_precision_forward_return_stats_validation.json")
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _check(manifest.get("frozen_condition_group_count") == 7, "frozen_condition_group_count_7", str(manifest.get("frozen_condition_group_count")), rows)
    _check(manifest.get("bootstrap_resample_unit") == "instrument_year", "bootstrap_resample_unit_instrument_year", str(manifest.get("bootstrap_resample_unit")), rows)
    _check(int(manifest.get("bootstrap_iterations", 0)) == int(config["bootstrap"]["iterations"]), "bootstrap_iterations_match_config", str(manifest.get("bootstrap_iterations")), rows)
    _check(manifest.get("upstream_parallel_result_hash") is not None, "upstream_parallel_result_hash_recorded", str(manifest.get("upstream_parallel_result_hash")), rows)
    _check(manifest.get("decision_grain") in {"stock_day", "episode"}, "decision_grain_allowed", str(manifest.get("decision_grain")), rows)

    action = pd.read_parquet(cache_dir / "r02_family_action_time_panel.parquet")
    background = pd.read_parquet(cache_dir / "r02_family_background_prior_panel.parquet")
    precision = pd.read_csv(reports_dir / "r02_family_precision_summary.csv")
    precision_year = pd.read_csv(reports_dir / "r02_family_precision_by_year.csv")
    returns = pd.read_csv(reports_dir / "r02_family_forward_return_stats.csv")
    decision = pd.read_csv(reports_dir / "r02_family_decision_gate_audit.csv")
    frozen = pd.read_csv(reports_dir / "r02_family_frozen_condition_audit.csv")
    missing = pd.read_csv(reports_dir / "r02_family_missingness_audit.csv")
    redundancy = pd.read_csv(reports_dir / "r02_family_signal_redundancy_long.csv")
    phi = pd.read_csv(reports_dir / "r02_family_signal_phi_correlation_matrix.csv")
    jaccard = pd.read_csv(reports_dir / "r02_family_signal_jaccard_matrix.csv")
    incremental = pd.read_csv(reports_dir / "r02_family_signal_incremental_precision.csv")
    top4_audit = pd.read_csv(reports_dir / "r02_family_top4_independence_selection_audit.csv")
    top4_combined = pd.read_csv(reports_dir / "r02_family_top4_combined_precision.csv")

    expected_ids = {item["condition_group_id"] for item in config["frozen_conditions"]}
    _check(set(action["condition_group_id"].unique()) == expected_ids, "action_panel_has_exact_frozen_conditions", str(len(action["condition_group_id"].unique())), rows)
    _check(set(frozen["condition_group_id"]) == expected_ids, "frozen_audit_has_exact_conditions", str(len(frozen)), rows)
    _check(action["signal_occurs"].isin([True, False]).all(), "signal_occurs_boolean", "", rows)
    _check((~action["signal_occurs"].astype(bool)).any(), "action_panel_retains_non_signal_rows", str((~action["signal_occurs"].astype(bool)).sum()), rows)
    _check((action.loc[~action["feature_complete_flag"].astype(bool), "signal_occurs"].astype(bool).sum() == 0), "feature_incomplete_never_signals", "", rows)

    non_signal = action.loc[~action["signal_occurs"].astype(bool)]
    _check(non_signal["signal_episode_id"].isna().all(), "non_signal_episode_id_null", "", rows)
    _check(non_signal["episode_signal_date"].isna().all(), "non_signal_episode_signal_date_null", "", rows)
    _check(non_signal["episode_occurrence_price_t"].isna().all(), "non_signal_episode_occurrence_price_null", "", rows)
    _check(non_signal["episode_entry_price_t"].isna().all(), "non_signal_episode_entry_price_null", "", rows)
    episode_start = action.loc[action["is_episode_start"].astype(bool)]
    _check(episode_start["signal_occurs"].astype(bool).all(), "episode_start_only_signal_rows", "", rows)
    _check(episode_start["signal_episode_id"].notna().all(), "episode_start_has_episode_id", "", rows)
    _check(episode_start["episode_signal_date"].notna().all(), "episode_start_has_episode_signal_date", "", rows)

    feature_matched = background.loc[background["background_denominator_role"].eq("feature_matched")]
    _check((~feature_matched["signal_occurs"].astype(bool)).any(), "feature_matched_background_includes_non_signal_rows", str((~feature_matched["signal_occurs"].astype(bool)).sum()), rows)
    _check(feature_matched["feature_complete_flag"].astype(bool).all(), "feature_matched_background_feature_complete", "", rows)

    required_precision_cols = {
        "background_prior_global_h120_close_anchor",
        "background_prior_feature_matched_h120_close_anchor",
        "precision_lift_feature_matched_h120_close_anchor",
        "bootstrap_precision_lift_ci90_lower",
        "bootstrap_precision_lift_ci90_upper",
    }
    _check(required_precision_cols.issubset(set(precision.columns)), "precision_columns_present", str(sorted(required_precision_cols - set(precision.columns))), rows)
    _check(precision.loc[precision["split"].isin(["validation", "robustness"]), "bootstrap_precision_lift_ci90_lower"].notna().all(), "bootstrap_ci_present_for_oos_splits", "", rows)
    _check("year" in precision_year.columns, "precision_by_year_has_year_column", "", rows)
    _check(pd.to_numeric(precision_year["year"], errors="coerce").notna().all(), "precision_by_year_numeric_years", str(precision_year["year"].drop_duplicates().head().tolist()), rows)
    _check(precision_year["year"].nunique() > 1, "precision_by_year_multiple_years", str(precision_year["year"].nunique()), rows)
    _check(set(returns["horizon"].astype(int).unique()) == set(int(v) for v in config["horizons"]), "return_horizons_match_config", str(sorted(returns["horizon"].unique().tolist())), rows)
    _check("signal_count_gate_pass" in decision.columns, "decision_signal_count_gate_present", "", rows)
    _check(not missing.empty, "missingness_audit_nonempty", str(len(missing)), rows)

    expected_families = {item["family_id"] for item in config["frozen_conditions"]}
    _check(len(redundancy) == len(expected_families) * len(expected_families), "redundancy_long_has_family_square", str(len(redundancy)), rows)
    _check({"family_a", "family_b", "phi_correlation", "jaccard_overlap", "phi_null_reason"}.issubset(redundancy.columns), "redundancy_required_columns_present", "", rows)
    _check(set(phi["family_a"]) == expected_families, "phi_matrix_rows_match_families", str(sorted(phi["family_a"].astype(str).tolist())), rows)
    _check(set(jaccard["family_a"]) == expected_families, "jaccard_matrix_rows_match_families", str(sorted(jaccard["family_a"].astype(str).tolist())), rows)
    _check(set(expected_families).issubset(set(phi.columns)), "phi_matrix_columns_match_families", str(phi.columns.tolist()), rows)
    _check(set(expected_families).issubset(set(jaccard.columns)), "jaccard_matrix_columns_match_families", str(jaccard.columns.tolist()), rows)
    _check(
        {"base_family", "added_family", "base_and_added_precision_h120_close_anchor", "signal_retention_base_and_added_vs_base"}.issubset(
            incremental.columns
        ),
        "incremental_required_columns_present",
        "",
        rows,
    )
    _check(set(incremental["split"].astype(str).unique()) == set(["train", "validation", "robustness", "all"]), "incremental_has_all_splits", str(sorted(incremental["split"].unique().tolist())), rows)
    _check(len(top4_audit) == 35, "top4_audit_has_c7_4_rows", str(len(top4_audit)), rows)
    _check(set(top4_audit["selection_rank"].astype(int)) == set(range(1, 36)), "top4_audit_ranks_1_to_35", str(top4_audit["selection_rank"].head().tolist()), rows)
    selected_manifest = manifest.get("top4_independent_family_set", [])
    selected_audit = str(top4_audit.sort_values("selection_rank").iloc[0]["selected_family_set"]).split("|") if not top4_audit.empty else []
    _check(sorted(selected_manifest) == sorted(selected_audit) and len(selected_manifest) == 4, "top4_manifest_matches_rank1_audit", str(selected_manifest), rows)
    _check(set(top4_combined["split"].astype(str).unique()) == set(["train", "validation", "robustness", "all"]), "top4_combined_has_all_splits", str(sorted(top4_combined["split"].unique().tolist())), rows)
    _check((top4_combined["selected_family_set"].nunique() == 1), "top4_combined_uses_single_selected_set", str(top4_combined["selected_family_set"].unique().tolist()), rows)
    _check(top4_combined["sample_sufficiency_status"].isin(["fragile_low_sample", "sufficient_for_diagnostic"]).all(), "top4_sample_sufficiency_status_allowed", "", rows)
    _check(manifest.get("top4_independence_selection_rule") is not None, "manifest_top4_selection_rule_recorded", str(manifest.get("top4_independence_selection_rule")), rows)
    _check(manifest.get("top4_combined_signal_count") is not None, "manifest_top4_combined_signal_count_recorded", str(manifest.get("top4_combined_signal_count")), rows)

    report_text = (reports_dir / "r02_family_precision_forward_return_final_report.md").read_text(encoding="utf-8")
    _check("same-day executable" not in report_text.lower(), "report_no_same_day_executable_claim", "", rows)
    _check("feature-matched background prior" in report_text, "report_mentions_feature_matched_prior", "", rows)
    _check("Final decision" in report_text, "report_has_final_decision", "", rows)
    _check("Signal Redundancy Diagnostics" in report_text, "report_has_signal_redundancy_section", "", rows)
    _check("Top-4 Independent Combined Precision" in report_text, "report_has_top4_combined_section", "", rows)
    _check("not a new production condition" not in report_text.lower(), "report_avoids_english_new_production_claim_token", "", rows)
    _check("不构成新信号" in report_text or "不是当日可执行入场信号" in report_text, "report_marks_combined_diagnostic_only", "", rows)

    audit = pd.DataFrame(rows)
    audit_path = reports_dir / "r02_family_precision_forward_return_validation_audit.csv"
    audit.to_csv(audit_path, index=False)
    failed = audit.loc[audit["status"].eq("failed"), "check_id"].tolist()
    result = {
        "validation_status": "passed" if not failed else "failed",
        "failed_checks": failed,
        "audit_path": relpath(audit_path),
    }
    write_json(result, manifests_dir / "r02_family_precision_forward_return_stats_validation.json")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate EP4 R02 family precision and forward-return artifacts.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    result = validate(Path(args.config))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
