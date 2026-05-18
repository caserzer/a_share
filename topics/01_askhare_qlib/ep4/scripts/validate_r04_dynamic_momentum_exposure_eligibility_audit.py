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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r04_dynamic_momentum_exposure_eligibility_audit_v1.yaml"
SPLITS = {"train", "validation", "robustness"}
SUCCESS_RACES = {"upside_first", "upside_only_complete"}
FAILURE_RACES = {"downside_first", "downside_only_complete", "neither_hit_complete"}
AMBIGUOUS_RACES = {"same_offset", "censored_incomplete"}
MARKET_BUCKETS = {
    "post_drawdown_rebound_hypothesis",
    "panic_high_vol",
    "normal_uptrend",
    "normal_range",
    "downtrend_low_breadth",
    "missing_market_regime",
}
INDUSTRY_BUCKETS = {
    "missing_industry",
    "thin_industry",
    "industry_rebound_from_drawdown",
    "industry_leading",
    "industry_lagging",
    "industry_neutral",
}
FINAL_DECISIONS = {
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_spec_sheet_invalid",
    "blocked_background_path_label_validation_failed",
    "blocked_matching_background_comparator_invalid",
    "r04_v1_exposure_eligibility_audit_complete_descriptive_only",
    "stop_exposure_eligibility_route_no_oos_lift",
    "proceed_to_r04_v2_volume_volatility_spec_only",
    "proceed_to_r04b_hold_exit_only",
}
RPS_INCLUSION = {
    "included",
    "excluded_invalid_episode_entry",
    "excluded_incomplete_120d_path",
    "excluded_cross_split",
    "excluded_out_of_scope_split",
    "excluded_duplicate_episode",
    "excluded_missing_required_field",
}
BACKGROUND_INCLUSION = {
    "included",
    "excluded_not_pit_executable",
    "excluded_suspended_or_dirty_bar",
    "excluded_nonpositive_close",
    "excluded_out_of_scope_split",
    "excluded_invalid_next_open",
    "excluded_incomplete_120d_path",
    "excluded_cross_split",
    "excluded_missing_required_field",
}
REPORTS = [
    "r04_input_readiness_audit.csv",
    "r04_spec_sheet_frozen.csv",
    "r04_feature_dictionary.csv",
    "r04_candidate_funnel_audit.csv",
    "r04_raw_vs_episode_audit.csv",
    "r04_background_denominator_audit.csv",
    "r04_background_path_label_reconciliation_audit.csv",
    "r04_industry_membership_join_audit.csv",
    "r04_market_regime_bucket_summary.csv",
    "r04_industry_regime_bucket_summary.csv",
    "r04_post_drawdown_rebound_audit.csv",
    "r04_nested_baseline_ablation_summary.csv",
    "r04_negative_ablation_summary.csv",
    "r04_matching_background_comparator_audit.csv",
    "r04_outcome_hierarchy_summary.csv",
    "r04_denominator_shrink_audit.csv",
    "r04_denominator_sufficiency_audit.csv",
    "r04_race_ambiguity_audit.csv",
    "r04_split_stability_audit.csv",
    "r04_year_industry_concentration_audit.csv",
    "r04_kill_criteria_audit.csv",
    "r04_dynamic_momentum_exposure_eligibility_final_report.md",
]
CACHE = [
    "r04_rps_candidate_action_panel.parquet",
    "r04_raw_action_time_audit_panel.parquet",
    "r04_background_action_time_panel.parquet",
    "r04_market_regime_panel.parquet",
    "r04_industry_regime_panel.parquet",
    "r04_candidate_regime_join_panel.parquet",
    "r04_ablation_membership_panel.parquet",
]
MANIFESTS = ["r04_dynamic_momentum_exposure_eligibility_manifest.json"]


def _load_config(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _to_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _add(
    rows: list[dict[str, Any]],
    check_name: str,
    condition: bool,
    severity: str,
    details: str = "",
    artifact_path: str = "",
) -> None:
    rows.append(
        {
            "check_name": check_name,
            "status": "passed" if condition else "failed",
            "severity": severity,
            "details": "" if condition else details,
            "artifact_path": artifact_path,
        }
    )


def _status(rows: list[dict[str, Any]]) -> str:
    audit = pd.DataFrame(rows)
    failed = audit["status"].eq("failed") & audit["severity"].isin(["error", "fatal"])
    return "failed" if bool(failed.any()) else "passed"


def _require_columns(rows: list[dict[str, Any]], df: pd.DataFrame, cols: set[str], check_name: str, path: Path) -> None:
    missing = sorted(cols - set(df.columns))
    _add(rows, check_name, not missing, "error", f"missing columns: {missing}", relpath(path))


def _primary_success_expected(status: Any) -> Any:
    text = str(status)
    if text in SUCCESS_RACES:
        return True
    if text in FAILURE_RACES:
        return False
    return pd.NA


def _id_hash(parts: list[Any]) -> str:
    import hashlib

    return hashlib.sha256("|".join("" if pd.isna(part) else str(part) for part in parts).encode("utf-8")).hexdigest()


def validate(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    output_root = topic_path(Path(config["output_root"]))
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r04_dynamic_momentum_exposure_eligibility_manifest.json"
    validation_path = manifests_dir / "r04_dynamic_momentum_exposure_eligibility_validation.json"
    audit_path = reports_dir / "r04_dynamic_momentum_exposure_eligibility_validation_audit.csv"
    rows: list[dict[str, Any]] = []

    for name in REPORTS:
        _add(rows, f"required_report_exists_{name}", (reports_dir / name).exists(), "fatal", "required report missing", relpath(reports_dir / name))
    for name in CACHE:
        _add(rows, f"required_cache_exists_{name}", (cache_dir / name).exists(), "fatal", "required cache missing", relpath(cache_dir / name))
    for name in MANIFESTS:
        _add(rows, f"required_manifest_exists_{name}", (manifests_dir / name).exists(), "fatal", "required manifest missing", relpath(manifests_dir / name))

    if not manifest_path.exists():
        reports_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(audit_path, index=False)
        result = {"validation_status": "failed", "failed_checks": ["manifest_missing"], "audit_path": relpath(audit_path)}
        write_json(result, validation_path)
        return result

    manifest = _read_json(manifest_path)
    final_decision = manifest.get("final_decision")
    _add(rows, "final_decision_allowed", final_decision in FINAL_DECISIONS, "error", f"invalid final_decision={final_decision}", relpath(manifest_path))
    upstream_status = _read_json(Path(config["upstream_path_query"]["validation"])).get("validation_status")
    _add(rows, "upstream_path_query_validation_passed", upstream_status == "passed", "fatal", f"upstream validation_status={upstream_status}")

    paths = {
        "candidate": cache_dir / "r04_rps_candidate_action_panel.parquet",
        "raw": cache_dir / "r04_raw_action_time_audit_panel.parquet",
        "background": cache_dir / "r04_background_action_time_panel.parquet",
        "market": cache_dir / "r04_market_regime_panel.parquet",
        "industry": cache_dir / "r04_industry_regime_panel.parquet",
        "join": cache_dir / "r04_candidate_regime_join_panel.parquet",
        "ablation": cache_dir / "r04_ablation_membership_panel.parquet",
        "spec": reports_dir / "r04_spec_sheet_frozen.csv",
        "reconciliation": reports_dir / "r04_background_path_label_reconciliation_audit.csv",
        "outcome": reports_dir / "r04_outcome_hierarchy_summary.csv",
        "nested": reports_dir / "r04_nested_baseline_ablation_summary.csv",
        "negative": reports_dir / "r04_negative_ablation_summary.csv",
        "kill": reports_dir / "r04_kill_criteria_audit.csv",
        "report": reports_dir / "r04_dynamic_momentum_exposure_eligibility_final_report.md",
    }
    if all(path.exists() for path in paths.values()):
        candidate = pd.read_parquet(paths["candidate"])
        raw = pd.read_parquet(paths["raw"])
        background = pd.read_parquet(paths["background"])
        market = pd.read_parquet(paths["market"])
        industry = pd.read_parquet(paths["industry"])
        joined = pd.read_parquet(paths["join"])
        ablation = pd.read_parquet(paths["ablation"])
        spec = pd.read_csv(paths["spec"])
        reconciliation = pd.read_csv(paths["reconciliation"])
        outcome = pd.read_csv(paths["outcome"])
        nested = pd.read_csv(paths["nested"])
        negative = pd.read_csv(paths["negative"])
        kill = pd.read_csv(paths["kill"])
        report_text = paths["report"].read_text(encoding="utf-8")

        _require_columns(
            rows,
            candidate,
            {
                "r04_candidate_event_id",
                "signal_id",
                "family_id",
                "episode_id",
                "instrument_id",
                "episode_start_signal_date",
                "entry_execution_date",
                "episode_entry_valid",
                "path_complete_120d",
                "r04_inclusion_status",
                "race_plus10_minus5_status",
                "primary_success_flag",
                "metric_denominator_eligible_flag",
            },
            "candidate_required_columns",
            paths["candidate"],
        )
        _require_columns(
            rows,
            raw,
            {"raw_action_time_event_id", "signal_id", "instrument_id", "signal_date", "entry_date", "entry_valid", "episode_id", "raw_is_episode_first_trigger"},
            "raw_required_columns",
            paths["raw"],
        )
        _require_columns(
            rows,
            background,
            {
                "background_event_id",
                "instrument_id",
                "background_signal_date",
                "background_entry_date",
                "background_entry_valid",
                "background_inclusion_status",
                "background_race_plus10_minus5_status",
                "background_primary_success_flag",
                "background_metric_denominator_eligible_flag",
            },
            "background_required_columns",
            paths["background"],
        )
        _require_columns(
            rows,
            joined,
            {
                "r04_candidate_event_id",
                "background_event_id",
                "raw_action_time_event_id",
                "denominator_scope",
                "instrument_id",
                "signal_date",
                "background_signal_date",
                "anchor_signal_date",
                "market_regime_bucket",
                "industry_regime_bucket",
                "primary_success_flag",
                "metric_denominator_eligible_flag",
            },
            "join_required_columns",
            paths["join"],
        )

        _add(rows, "spec_sheet_formula_hash_present", "formula_hash" in spec.columns and spec["formula_hash"].notna().all() and spec["formula_hash"].astype(str).ne("").all(), "error", "spec formula_hash missing", relpath(paths["spec"]))
        declared_buckets = set(spec["bucket_name"].dropna().astype(str)) if "bucket_name" in spec.columns else set()
        actual_market_buckets = set(market["market_regime_bucket"].dropna().astype(str)) | set(joined["market_regime_bucket"].dropna().astype(str))
        actual_industry_buckets = set(industry["industry_regime_bucket"].dropna().astype(str)) | set(joined["industry_regime_bucket"].dropna().astype(str))
        _add(rows, "actual_market_buckets_declared", actual_market_buckets <= declared_buckets, "error", f"undeclared market buckets: {sorted(actual_market_buckets - declared_buckets)}", relpath(paths["spec"]))
        _add(rows, "actual_industry_buckets_declared", actual_industry_buckets <= declared_buckets, "error", f"undeclared industry buckets: {sorted(actual_industry_buckets - declared_buckets)}", relpath(paths["spec"]))
        _add(rows, "single_momentum_rps_only", set(candidate["signal_id"].dropna().astype(str)) == {config["candidate"]["signal_id"]}, "error", "candidate signal_id drift", relpath(paths["candidate"]))
        _add(rows, "episode_id_unique", not candidate["episode_id"].duplicated().any(), "error", "candidate episode_id duplicated", relpath(paths["candidate"]))
        _add(rows, "candidate_ids_unique", not candidate["r04_candidate_event_id"].duplicated().any(), "error", "candidate ids duplicated", relpath(paths["candidate"]))
        _add(rows, "raw_ids_unique", not raw["raw_action_time_event_id"].duplicated().any(), "error", "raw ids duplicated", relpath(paths["raw"]))
        _add(rows, "background_ids_unique", not background["background_event_id"].duplicated().any(), "error", "background ids duplicated", relpath(paths["background"]))

        raw_id_sample = raw.head(100)
        raw_id_ok = all(
            row.raw_action_time_event_id == _id_hash(["r04_raw", row.signal_id, row.instrument_id, str(pd.to_datetime(row.signal_date).date())])
            for row in raw_id_sample.itertuples(index=False)
        )
        bg_id_sample = background.head(100)
        bg_id_ok = all(
            row.background_event_id == _id_hash(["r04_background", row.instrument_id, str(pd.to_datetime(row.background_signal_date).date())])
            for row in bg_id_sample.itertuples(index=False)
        )
        _add(rows, "raw_id_hash_sample_matches", raw_id_ok, "error", "raw_action_time_event_id hash mismatch", relpath(paths["raw"]))
        _add(rows, "background_id_hash_sample_matches", bg_id_ok, "error", "background_event_id hash mismatch", relpath(paths["background"]))

        rps_statuses = set(candidate["r04_inclusion_status"].dropna().astype(str))
        bg_statuses = set(background["background_inclusion_status"].dropna().astype(str))
        _add(rows, "candidate_inclusion_status_allowed", rps_statuses <= RPS_INCLUSION, "error", f"bad statuses: {sorted(rps_statuses - RPS_INCLUSION)}", relpath(paths["candidate"]))
        _add(rows, "background_inclusion_status_allowed", bg_statuses <= BACKGROUND_INCLUSION, "error", f"bad statuses: {sorted(bg_statuses - BACKGROUND_INCLUSION)}", relpath(paths["background"]))

        included = candidate["r04_inclusion_status"].eq("included")
        included_ok = _to_bool_series(candidate.loc[included, "episode_entry_valid"]).all() and _to_bool_series(candidate.loc[included, "path_complete_120d"]).all()
        _add(rows, "rps_headline_included_valid_complete", bool(included_ok), "error", "included RPS rows must be valid and path-complete", relpath(paths["candidate"]))
        bg_included = background["background_inclusion_status"].eq("included")
        bg_included_ok = _to_bool_series(background.loc[bg_included, "background_entry_valid"]).all() and _to_bool_series(background.loc[bg_included, "background_path_complete_120d"]).all()
        _add(rows, "background_headline_included_valid_complete", bool(bg_included_ok), "error", "included background rows must be next-open valid and path-complete", relpath(paths["background"]))

        expected = candidate["race_plus10_minus5_status"].map(_primary_success_expected)
        success_ok = True
        for actual, exp in zip(candidate["primary_success_flag"], expected, strict=False):
            if pd.isna(exp):
                if not pd.isna(actual):
                    success_ok = False
                    break
            elif bool(actual) != bool(exp):
                success_ok = False
                break
        _add(rows, "primary_success_consistent_with_race", success_ok, "error", "candidate primary_success_flag not derived mechanically", relpath(paths["candidate"]))
        ambiguous = candidate["race_plus10_minus5_status"].isin(AMBIGUOUS_RACES)
        _add(rows, "ambiguous_race_success_null", candidate.loc[ambiguous, "primary_success_flag"].isna().all(), "error", "ambiguous races must not be success/failure", relpath(paths["candidate"]))

        recon_ok = int(reconciliation["total_mismatch_count"].sum()) == 0
        _add(rows, "background_path_reconciliation_zero_mismatch", recon_ok, "error", "total_mismatch_count must be zero", relpath(paths["reconciliation"]))
        _add(rows, "background_headline_denominator_exists", int(bg_included.sum()) > 0, "error", "background headline denominator is empty", relpath(paths["background"]))

        scopes = set(joined["denominator_scope"].dropna().astype(str))
        _add(rows, "join_scopes_complete", {"rps_episode_primary", "background_action_time", "raw_action_time_audit"} <= scopes, "error", f"missing scopes: {sorted({'rps_episode_primary', 'background_action_time', 'raw_action_time_audit'} - scopes)}", relpath(paths["join"]))
        rps_join = joined["denominator_scope"].eq("rps_episode_primary")
        bg_join = joined["denominator_scope"].eq("background_action_time")
        raw_join = joined["denominator_scope"].eq("raw_action_time_audit")
        nullability_ok = (
            joined.loc[rps_join, "r04_candidate_event_id"].notna().all()
            and joined.loc[rps_join, "background_event_id"].isna().all()
            and joined.loc[bg_join, "background_event_id"].notna().all()
            and joined.loc[bg_join, "r04_candidate_event_id"].isna().all()
            and joined.loc[raw_join, "raw_action_time_event_id"].notna().all()
            and joined.loc[raw_join, "r04_candidate_event_id"].isna().all()
        )
        _add(rows, "mixed_scope_id_nullability", bool(nullability_ok), "error", "join panel id nullability violates scope semantics", relpath(paths["join"]))

        rank_cols_ok = True
        for frame, cols in [(joined, ["stock_rps_60d"]), (industry, ["industry_rps_60d"])]:
            for col in cols:
                values = pd.to_numeric(frame[col], errors="coerce").dropna()
                if len(values) and not values.between(0, 1).all():
                    rank_cols_ok = False
        _add(rows, "rank_features_within_unit_interval", rank_cols_ok, "error", "RPS rank outside [0,1]", relpath(paths["join"]))

        required_ablation = {"mask_A_all_rps", "mask_B_market_constructive_no_default_rebound_penalty", "mask_C_industry_leadership", "background_all"}
        _add(rows, "ablation_membership_core_masks_exist", required_ablation <= set(ablation["ablation_id"].dropna().astype(str)), "error", "missing core ablation masks", relpath(paths["ablation"]))
        _add(rows, "nested_baseline_exists", {"baseline_A_rps_only", "baseline_B_market_bucket", "baseline_C_market_industry_bucket"} <= set(nested["summary_id"].dropna().astype(str)), "error", "nested baselines missing", relpath(paths["nested"]))
        _add(rows, "negative_ablation_exists", {"full_background_component", "rps_market_only", "rps_industry_only", "rps_market_industry"} <= set(negative["summary_id"].dropna().astype(str)), "error", "negative ablations missing", relpath(paths["negative"]))
        _add(rows, "denominator_sufficiency_present", "denominator_sufficiency_status" in outcome.columns and outcome["denominator_sufficiency_status"].notna().all(), "error", "outcome missing denominator sufficiency", relpath(paths["outcome"]))
        _add(rows, "kill_criteria_exists", len(kill) > 0, "error", "kill criteria audit empty", relpath(paths["kill"]))

        if final_decision == "proceed_to_r04_v2_volume_volatility_spec_only":
            oos_c = outcome[outcome["ablation_id"].eq("mask_C_industry_leadership") & outcome["split"].isin(["validation", "robustness"])]
            proceed_ok = len(oos_c) == 2 and oos_c["denominator_sufficiency_status"].eq("sufficient").all() and oos_c["matching_background_status"].eq("sufficient").all()
            _add(rows, "proceed_decision_requires_oos_sufficiency", proceed_ok, "error", "proceed decision without OOS sufficiency", relpath(paths["outcome"]))
        _add(rows, "all_split_not_proceed_driver", final_decision != "proceed_to_r04_v2_volume_volatility_spec_only" or "all" in set(outcome["split"]), "warning", "all split is descriptive only", relpath(paths["outcome"]))
        _add(rows, "ev_r_out_of_scope_in_report", "ev_r_status = out_of_scope_for_r04_v1" in report_text, "error", "final report missing EV_R out-of-scope marker", relpath(paths["report"]))
        _add(rows, "no_production_gate_marker", "No production gate" in report_text or "not a production gate" in report_text, "error", "final report missing no-production-gate statement", relpath(paths["report"]))
        _add(rows, "post_drawdown_rebound_reported", "post_drawdown_rebound_hypothesis" in report_text and "not default bad gates" in report_text, "error", "rebound bucket must be reported as hypothesis", relpath(paths["report"]))

    reports_dir.mkdir(parents=True, exist_ok=True)
    audit = pd.DataFrame(rows)
    audit.to_csv(audit_path, index=False)
    failed_checks = audit.loc[audit["status"].eq("failed") & audit["severity"].isin(["error", "fatal"]), "check_name"].tolist()
    result = {
        "validation_status": _status(rows),
        "failed_checks": failed_checks,
        "audit_path": relpath(audit_path),
        "manifest_path": relpath(manifest_path),
        "final_decision": manifest.get("final_decision"),
        "check_count": int(len(rows)),
    }
    write_json(result, validation_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    result = validate(Path(args.config))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
