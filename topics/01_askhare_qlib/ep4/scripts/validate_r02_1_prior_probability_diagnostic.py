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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r02_1_prior_probability_diagnostic_v1.yaml"
REPORT_FILES = {
    "global": "r02_1_global_action_time_prior.csv",
    "single": "r02_1_single_family_prior.csv",
    "bundle": "r02_1_same_day_bundle_prior.csv",
    "count": "r02_1_same_day_family_count_prior.csv",
    "fallback": "r02_1_bucket_fallback_audit.csv",
    "context": "r02_1_context_bucket_prior.csv",
    "survival": "r02_1_survival_checkpoint_prior.csv",
    "fresh": "r02_1_fresh_evidence_prior.csv",
    "fresh_offsets": "r02_1_fresh_evidence_offset_distribution.csv",
    "split": "r02_1_split_stability_diagnostics.csv",
    "readiness": "r02_1_r03_input_readiness.csv",
    "ev_audit": "r02_1_ev_r_input_audit.csv",
    "report": "r02_1_prior_probability_diagnostic_report.md",
}

EXPECTED_FROZEN_FAMILIES = [
    {
        "family_id": "momentum_rps",
        "signal_id": "single_momentum_rps",
        "condition_group_id": "momentum_rps__and3__68b32373ce93",
        "condition_text": "roc5_r02 >= 0.05 AND rps5_r02 >= 0.8 AND rps10_r02 >= 0.5",
    },
    {
        "family_id": "oscillator",
        "signal_id": "single_oscillator",
        "condition_group_id": "oscillator__and4__95dbd99ae828",
        "condition_text": "kdj_k5_r02 >= 60 AND cci5_r02 >= 100 AND kdj_k10_r02 >= 55 AND cci10_r02 >= 150",
    },
    {
        "family_id": "price_trend",
        "signal_id": "single_price_trend",
        "condition_group_id": "price_trend__and3__6030760ed19f",
        "condition_text": "close_over_ma5_r02 >= 0.03 AND ema_slope5_r02 >= 0.0 AND close_over_ma10_r02 >= 0.03",
    },
    {
        "family_id": "pullback_drawdown",
        "signal_id": "single_pullback_drawdown",
        "condition_group_id": "pullback_drawdown__and3__11795aa42e45",
        "condition_text": "pullback_depth5_r02 >= -0.05 AND rebound_from_low5_r02 >= 0.05 AND days_since_high10_r02 <= 5",
    },
    {
        "family_id": "range_breakout",
        "signal_id": "single_range_breakout",
        "condition_group_id": "range_breakout__and3__00e51295d9c3",
        "condition_text": "range_position5_r02 >= 0.9 AND new_high_flag10_r02 == 1.0 AND range_position10_r02 >= 0.7",
    },
    {
        "family_id": "volatility_band",
        "signal_id": "single_volatility_band",
        "condition_group_id": "volatility_band__and4__ef9c875dde10",
        "condition_text": "boll_pct_b5_r02 >= 0.8 AND boll_width5_r02 >= 1.0 AND boll_width10_r02 >= 1.0 AND price_channel_position10_r02 >= 0.8",
    },
    {
        "family_id": "volume_money",
        "signal_id": "single_volume_money",
        "condition_group_id": "volume_money__and4__4eb7a99e922f",
        "condition_text": "volume_ratio5_r02 >= 1.5 AND money_zscore5_r02 >= 2.0 AND money_price_coherence5_r02 == 1.0 AND money_price_coherence10_r02 == 1.0",
    },
]

REQUIRED_COLUMNS = {
    "survival": {
        "checkpoint",
        "survival_definition_version",
        "pre_checkpoint_row_count",
        "survivor_count",
        "survivor_rate",
        "survivor_label_denominator_count",
        "survivor_P_good",
        "survivor_P_bad",
        "survivor_P_neutral",
        "survivor_EV_R_diagnostic",
        "non_survivor_count",
        "non_survivor_label_denominator_count",
        "non_survivor_P_good",
        "non_survivor_P_bad",
        "non_survivor_P_neutral",
        "non_survivor_EV_R_diagnostic",
        "survival_lift_good_vs_pre_checkpoint",
        "survival_lift_bad_vs_pre_checkpoint",
        "sample_sufficiency_status",
    },
    "fresh_offsets": {
        "seed_episode_id",
        "instrument_id",
        "seed_trade_date",
        "seed_split",
        "seed_same_day_bundle_key",
        "seed_same_day_family_count",
        "seed_label",
        "fresh_family_id",
        "fresh_signal_date",
        "fresh_offset",
        "fresh_offset_bucket",
        "seed_failure_offset",
        "seed_failure_offset_bucket",
        "fresh_vs_observable_failure_state",
        "fresh_evidence_status",
        "seed_pre_fresh_state",
        "survival_checkpoint_state",
        "posterior_denominator_policy",
    },
}


def load_config(config_path: Path) -> dict[str, Any]:
    with topic_path(config_path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _check(condition: bool, check_id: str, detail: str, rows: list[dict[str, Any]]) -> None:
    rows.append({"check_id": check_id, "status": "passed" if condition else "failed", "detail": str(detail)})


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _require_columns(df: pd.DataFrame, columns: set[str], check_id: str, rows: list[dict[str, Any]]) -> None:
    missing = sorted(columns - set(df.columns))
    _check(not missing, check_id, missing, rows)


def validate(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r02_1_prior_probability_diagnostic_manifest.json"
    rows: list[dict[str, Any]] = []

    for key, name in REPORT_FILES.items():
        _check((reports_dir / name).exists(), f"required_output_exists_{key}", relpath(reports_dir / name), rows)
    _check(manifest_path.exists(), "manifest_exists", relpath(manifest_path), rows)
    if not manifest_path.exists():
        result = {"validation_status": "failed", "failed_checks": ["manifest_exists"]}
        write_json(result, manifests_dir / "r02_1_prior_probability_diagnostic_validation.json")
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_families = sorted(item["family_id"] for item in EXPECTED_FROZEN_FAMILIES)
    configured = sorted(config["frozen_families"], key=lambda item: item["family_id"])
    expected_config = sorted(EXPECTED_FROZEN_FAMILIES, key=lambda item: item["family_id"])
    _check(configured == expected_config, "config_frozen_families_match_requirement", configured, rows)
    upstream_config_path = config.get("upstream_path_query", {}).get("config")
    if upstream_config_path:
        with topic_path(Path(upstream_config_path)).open("r", encoding="utf-8") as file:
            upstream_config = yaml.safe_load(file) or {}
        upstream = pd.DataFrame(upstream_config.get("single_signals", []))
        frozen = pd.DataFrame(EXPECTED_FROZEN_FAMILIES)
        merged = frozen.merge(upstream, on=["family_id", "signal_id", "condition_group_id"], how="left", suffixes=("", "_upstream"))
        upstream_ok = not merged.empty and merged["condition_text_upstream"].notna().all()
        if upstream_ok:
            upstream_ok = merged["condition_text"].astype(str).eq(merged["condition_text_upstream"].astype(str)).all()
        _check(upstream_ok, "upstream_frozen_formulas_match_requirement", "", rows)
    _check(sorted(manifest.get("frozen_family_ids", [])) == expected_families, "frozen_family_ids_match_config", manifest.get("frozen_family_ids"), rows)
    _check(manifest.get("label_definition_version") == "r02_1_good_bad_neutral_v1", "label_definition_version_recorded", manifest.get("label_definition_version"), rows)
    _check(manifest.get("entry_anchor") == "first_executable_next_open_after_signal_date", "entry_anchor_matches_r02", manifest.get("entry_anchor"), rows)

    dfs = {key: _read(reports_dir / name) for key, name in REPORT_FILES.items() if name.endswith(".csv") and (reports_dir / name).exists()}
    posterior_tables = ["single", "bundle", "count", "context", "fresh"]
    for key in posterior_tables:
        df = dfs.get(key, pd.DataFrame())
        _check(not df.empty, f"{key}_posterior_nonempty", len(df), rows)
        if {"P_good", "P_bad", "P_neutral", "label_denominator_count"}.issubset(df.columns):
            den = pd.to_numeric(df["label_denominator_count"], errors="coerce").fillna(0)
            sums = pd.to_numeric(df["P_good"], errors="coerce") + pd.to_numeric(df["P_bad"], errors="coerce") + pd.to_numeric(df["P_neutral"], errors="coerce")
            ok = ((den <= 0) | (sums.sub(1.0).abs() < 1e-8)).all()
            _check(ok, f"{key}_probabilities_sum_to_one", "", rows)

    single = dfs.get("single", pd.DataFrame())
    if not single.empty:
        _check(set(single["family_id"].astype(str)) == set(expected_families), "single_prior_has_exact_families", sorted(single["family_id"].astype(str).unique()), rows)
    global_prior = dfs.get("global", pd.DataFrame())
    _check(
        "unavailable_background_path_not_materialized" in set(global_prior.get("global_prior_status", pd.Series(dtype=str)).astype(str)),
        "global_prior_unavailable_status_recorded",
        "",
        rows,
    )
    ev_audit = dfs.get("ev_audit", pd.DataFrame())
    _check({"signal_day_low", "prior_10d_low", "prior_20d_low"}.issubset(set(ev_audit.get("field_name", []))), "ev_audit_required_fields_present", "", rows)
    _check("missing" in set(ev_audit.get("availability_status", pd.Series(dtype=str)).astype(str)), "ev_audit_records_missing_inputs", "", rows)

    fresh = dfs.get("fresh", pd.DataFrame())
    fresh_offsets = dfs.get("fresh_offsets", pd.DataFrame())
    survival = dfs.get("survival", pd.DataFrame())
    split = dfs.get("split", pd.DataFrame())
    _require_columns(survival, REQUIRED_COLUMNS["survival"], "survival_required_columns_present", rows)
    if not survival.empty:
        _check({"T+3", "T+5", "T+10"}.issubset(set(survival["checkpoint"].astype(str))), "survival_required_checkpoints_present", sorted(survival["checkpoint"].astype(str).unique()), rows)
        expected_non = pd.to_numeric(survival["pre_checkpoint_row_count"], errors="coerce") - pd.to_numeric(survival["survivor_count"], errors="coerce")
        actual_non = pd.to_numeric(survival["non_survivor_count"], errors="coerce")
        _check(expected_non.eq(actual_non).all(), "survival_non_survivor_count_consistent", "", rows)
    _require_columns(fresh_offsets, REQUIRED_COLUMNS["fresh_offsets"], "fresh_offset_required_columns_present", rows)
    _check("seed_label" not in fresh.columns, "fresh_prior_does_not_group_by_seed_label", "", rows)
    required_status = {
        "found_within_t3_t30",
        "none_within_t3_t30",
        "seed_failed_before_t3",
        "seed_failed_before_fresh",
        "ambiguous_same_offset",
        "censored_before_t30",
    }
    _check(set(fresh_offsets.get("fresh_evidence_status", pd.Series(dtype=str)).astype(str)).issubset(required_status), "fresh_offset_status_allowed", "", rows)
    if not fresh_offsets.empty:
        found_mask = fresh_offsets["fresh_evidence_status"].isin(["found_within_t3_t30", "ambiguous_same_offset"])
        numeric_offsets = pd.to_numeric(fresh_offsets.loc[found_mask, "fresh_offset"], errors="coerce")
        _check(numeric_offsets.notna().all() and numeric_offsets.between(3, 30).all(), "found_fresh_offsets_numeric_3_30", "", rows)
        none_mask = fresh_offsets["fresh_evidence_status"].isin(["none_within_t3_t30", "seed_failed_before_t3", "seed_failed_before_fresh"])
        _check(
            fresh_offsets.loc[none_mask, "fresh_signal_date"].astype(str).eq("none").all()
            and fresh_offsets.loc[none_mask, "fresh_offset"].astype(str).eq("none").all(),
            "none_and_seed_failed_fresh_sentinels",
            "",
            rows,
        )
        _check(
            fresh_offsets.loc[none_mask, "fresh_family_id"].astype(str).eq("none").all()
            and fresh_offsets.loc[none_mask, "fresh_offset_bucket"].astype(str).eq("none").all(),
            "none_and_seed_failed_fresh_family_bucket_sentinels",
            "",
            rows,
        )
        _check(
            fresh_offsets.loc[fresh_offsets["fresh_evidence_status"].eq("seed_failed_before_t3"), "seed_pre_fresh_state"].astype(str).eq("failed_before_t3").all()
            and fresh_offsets.loc[fresh_offsets["fresh_evidence_status"].eq("seed_failed_before_fresh"), "seed_pre_fresh_state"].astype(str).eq("failed_before_fresh").all(),
            "seed_failed_pre_fresh_state_matches_status",
            "",
            rows,
        )
        censored_mask = fresh_offsets["fresh_evidence_status"].eq("censored_before_t30")
        _check(
            fresh_offsets.loc[censored_mask, "fresh_signal_date"].astype(str).eq("censored").all()
            and fresh_offsets.loc[censored_mask, "fresh_offset"].astype(str).eq("censored").all()
            and fresh_offsets.loc[censored_mask, "fresh_family_id"].astype(str).eq("censored").all()
            and fresh_offsets.loc[censored_mask, "fresh_offset_bucket"].astype(str).eq("censored").all(),
            "censored_fresh_sentinels",
            "",
            rows,
        )
        no_seed_family_reuse = True
        for row in fresh_offsets.loc[found_mask, ["seed_same_day_bundle_key", "fresh_family_id"]].itertuples(index=False):
            no_seed_family_reuse = no_seed_family_reuse and str(row.fresh_family_id) not in set(str(row.seed_same_day_bundle_key).split("|"))
        _check(no_seed_family_reuse, "fresh_family_not_in_seed_bundle", "", rows)
        _check("none_within_t3_t30" in set(fresh_offsets["fresh_evidence_status"].astype(str)), "fresh_offsets_include_no_fresh_rows", "", rows)
        ambiguous = fresh_offsets["fresh_evidence_status"].eq("ambiguous_same_offset")
        _check(fresh_offsets.loc[ambiguous, "posterior_denominator_policy"].astype(str).eq("audit_only_exclude").all(), "ambiguous_offsets_audit_only", "", rows)
        if not fresh.empty and "fresh_evidence_status" in fresh.columns:
            ambiguous_prior = fresh["fresh_evidence_status"].eq("ambiguous_same_offset")
            _check(
                pd.to_numeric(fresh.loc[ambiguous_prior, "label_denominator_count"], errors="coerce").fillna(0).eq(0).all(),
                "ambiguous_prior_excluded_from_denominator",
                "",
                rows,
            )
        _check(
            not {"fresh_before_bad_path_flag", "fresh_before_bad_path_rate", "fresh_before_observable_failure_flag"}.intersection(fresh_offsets.columns),
            "deprecated_fresh_fields_absent",
            "",
            rows,
        )
        _check("fresh_vs_observable_failure_state" in fresh_offsets.columns, "fresh_vs_observable_failure_state_present", "", rows)

    readiness = dfs.get("readiness", pd.DataFrame())
    allowed_readiness = {
        "ready",
        "limited_use_coarser_bucket",
        "blocked_missing_denominator",
        "blocked_sparse_bucket",
        "blocked_unstable_split",
        "blocked_missing_ev_r",
        "blocked_missing_fresh_evidence",
    }
    readiness_cols = [c for c in readiness.columns if c.endswith("_ready")]
    for col in readiness_cols:
        _check(set(readiness[col].astype(str)).issubset(allowed_readiness), f"readiness_values_allowed_{col}", sorted(readiness[col].astype(str).unique()), rows)
    _check("blocked_missing_ev_r" in set(readiness.get("ev_r_ready", pd.Series(dtype=str)).astype(str)), "ev_r_ready_blocked_when_missing", "", rows)
    _check("blocked_missing_denominator" in set(readiness.get("global_prior_ready", pd.Series(dtype=str)).astype(str)), "global_prior_ready_blocked_when_missing", "", rows)
    _check("blocked_missing_ev_r" in set(readiness.get("primary_blocker", pd.Series(dtype=str)).astype(str)), "ev_r_primary_blocker_when_missing", "", rows)
    allowed_grains = {"same_day_bundle_context", "same_day_family_count_context", "single_family_context", "global_prior_only", "not_ready"}
    allowed_windows = {"build_window_t30_supported", "build_window_needs_retest", "blocked_missing_fresh_distribution", "blocked_missing_survival_prior", "not_ready"}
    _check(set(readiness.get("recommended_r03_bucket_grain", pd.Series(dtype=str)).astype(str)).issubset(allowed_grains), "recommended_r03_bucket_grain_allowed", "", rows)
    _check(set(readiness.get("recommended_build_window_status", pd.Series(dtype=str)).astype(str)).issubset(allowed_windows), "recommended_build_window_status_allowed", "", rows)
    if not split.empty:
        required_groupings = {
            "single_family_prior",
            "same_day_bundle_prior",
            "same_day_family_count_prior",
            "context_bucket_prior",
            "survival_checkpoint_prior",
            "fresh_evidence_prior",
        }
        allowed_stability = {"stable_enough_for_requirement_input", "unstable_do_not_freeze", "insufficient_sample", "missing_split"}
        _check(required_groupings.issubset(set(split["grouping_type"].astype(str))), "split_stability_required_groupings_present", "", rows)
        _check(set(split["stability_status"].astype(str)).issubset(allowed_stability), "split_stability_status_allowed", "", rows)
        single_split = split.loc[split["grouping_type"].eq("single_family_prior")]
        _check(len(single_split) <= len(EXPECTED_FROZEN_FAMILIES), "single_family_split_stability_not_grouped_by_row_count", len(single_split), rows)

    report_text = (reports_dir / REPORT_FILES["report"]).read_text(encoding="utf-8") if (reports_dir / REPORT_FILES["report"]).exists() else ""
    _check("not an entry strategy" in report_text, "report_boundary_language_present", "", rows)
    required_report_sections = [
        "## Bundle Sparsity And Fallback",
        "## Context Bucket Availability",
        "## Survival Checkpoints",
        "## Fresh Evidence Offset Distribution",
        "## Fresh Evidence Posterior",
        "## T+30 Plausibility",
        "## Split Stability",
        "## R03 Readiness",
    ]
    _check(all(section in report_text for section in required_report_sections), "report_required_sections_present", "", rows)
    forbidden = ["buy ", "sell ", "trading recommendation", "production signal"]
    _check(not any(token in report_text.lower() for token in forbidden), "report_no_trading_recommendation_language", "", rows)

    audit = pd.DataFrame(rows)
    audit_path = reports_dir / "r02_1_prior_probability_diagnostic_validation_audit.csv"
    audit.to_csv(audit_path, index=False)
    failed = audit.loc[audit["status"].eq("failed"), "check_id"].tolist()
    result = {
        "validation_status": "passed" if not failed else "failed",
        "failed_checks": failed,
        "audit_path": relpath(audit_path),
    }
    manifest["validation_status"] = result["validation_status"]
    write_json(manifest, manifest_path)
    write_json(result, manifests_dir / "r02_1_prior_probability_diagnostic_validation.json")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate EP4 R02.1 prior probability diagnostic artifacts.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    result = validate(Path(args.config))
    return 0 if result["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
