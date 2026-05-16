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
from run_r03c_price_aware_kth_fresh_family_set_pooling_diagnostic import (  # noqa: E402
    ALL_SPLITS,
    FAMILY_ORDER,
    PATH_LABELS,
    _boolish,
    _build_clean_steps,
    _family_list,
    _presence_signature,
)


DEFAULT_CONFIG = EP4_DIR / "configs" / "r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1.yaml"
REPORTS = [
    "r03c_input_readiness_audit.csv",
    "r03c_price_reconciliation_audit.csv",
    "r03c_wait_price_movement_summary.csv",
    "r03c_fresh_count_price_conditioned_summary.csv",
    "r03c_kth_offset_price_summary.csv",
    "r03c_grouping_explanatory_power_comparison.csv",
    "r03c_family_set_pooling_summary.csv",
    "r03c_family_set_split_stability_audit.csv",
    "r03c_seed_vs_fresh_anchor_outcome_audit.csv",
    "r03c_survival_price_bias_audit.csv",
    "r03c_price_aware_pooling_final_report.md",
    "r03c_price_aware_pooling_validation_audit.csv",
]
CACHE = [
    "r03c_fresh_step_price_panel.parquet",
    "r03c_checkpoint_price_state_panel.parquet",
    "r03c_family_set_pooling_panel.parquet",
]
MANIFESTS = [
    "r03c_price_aware_kth_fresh_family_set_pooling_manifest.json",
    "r03c_price_aware_kth_fresh_family_set_pooling_validation.json",
]
VALIDATION_AUDIT_COLS = {
    "check_id",
    "check_category",
    "status",
    "severity",
    "failure_reason",
    "affected_rows",
    "artifact_path",
}
FRESH_REQUIRED = {
    "seed_episode_id",
    "instrument_id",
    "split",
    "seed_trade_date",
    "seed_family_set",
    "seed_same_day_family_count",
    "seed_entry_date",
    "seed_entry_price",
    "step_signal_date",
    "step_offset",
    "kth_fresh_step_index_raw",
    "kth_fresh_step_bucket",
    "kth_fresh_offset_bucket",
    "added_family_set",
    "added_family_count",
    "cumulative_distinct_family_set_after_step",
    "cumulative_distinct_family_count_after_step",
    "is_same_offset_multi_family_step",
    "fresh_signal_close_price",
    "wait_return_to_fresh_signal_close",
    "fresh_entry_date",
    "fresh_entry_price",
    "fresh_entry_valid",
    "fresh_path_complete_120d",
    "fresh_complete_h120_close_anchor_flag",
    "fresh_big_winner_forward_h120_close_anchor",
    "fresh_forward_close_peak_h120_return_from_signal_close",
    "wait_return_to_fresh_entry",
    "wait_return_bucket",
    "fresh_path_label",
    "wait_cost_to_remaining_max_gain_ratio",
}
CHECKPOINT_REQUIRED = {
    "seed_episode_id",
    "instrument_id",
    "split",
    "checkpoint",
    "checkpoint_offset",
    "checkpoint_state",
    "at_risk_at_checkpoint",
    "fresh_distinct_family_count_before_or_at_checkpoint",
    "fresh_distinct_family_count_bucket",
    "kth_fresh_reached_before_or_at_checkpoint",
    "fresh_family_set_before_or_at_checkpoint",
    "cumulative_family_set_before_or_at_checkpoint",
    "latest_clean_fresh_step_offset_before_or_at_checkpoint",
    "latest_clean_fresh_kth_fresh_step_bucket_before_or_at_checkpoint",
    "latest_clean_fresh_kth_fresh_offset_bucket_before_or_at_checkpoint",
    "latest_clean_fresh_entry_date_before_or_at_checkpoint",
    "latest_clean_fresh_entry_price_before_or_at_checkpoint",
    "wait_return_to_latest_fresh_entry_before_or_at_checkpoint",
    "wait_return_bucket_before_or_at_checkpoint",
}
POOLING_REQUIRED = {
    "seed_episode_id",
    "instrument_id",
    "split",
    "pooling_level",
    "pooling_key",
    "pooling_key_family_count",
    "kth_fresh_step_bucket",
    "kth_fresh_offset_bucket",
    "wait_return_bucket",
    "added_family_set",
    "cumulative_distinct_family_set_after_step",
}
SUMMARY_REQUIRED = {
    "split",
    "seed_anchor_big_winner_denominator",
    "seed_anchor_big_winner_count",
    "seed_anchor_big_winner_rate",
    "seed_path_denominator",
    "seed_P_good",
    "seed_P_bad",
    "wait_return_to_fresh_entry_p25",
    "wait_return_to_fresh_entry_p50",
    "wait_return_to_fresh_entry_p75",
    "pct_wait_up_gt_5pct",
    "pct_wait_up_gt_10pct",
    "pct_wait_up_gt_20pct",
    "sample_sufficiency_status",
}
ALLOWED_POOLING_LEVELS = {
    "fresh_added_family_set",
    "cumulative_family_set_after_step",
    "family_presence_signature",
}
ALLOWED_GROUPING_SCHEMES = {
    "checkpoint_fresh_count",
    "checkpoint_latest_kth_offset",
    "checkpoint_latest_kth_offset_wait_bucket",
    "kth_offset",
    "kth_offset_wait_bucket",
    "family_set_pooling",
    "family_set_pooling_wait_bucket",
}
ALLOWED_OUTCOMES = {
    "seed_anchor_big_winner",
    "seed_path_good_bad",
    "fresh_anchor_big_winner",
    "fresh_path_good_bad",
}
FORBIDDEN_REPORT_TOKENS = [
    "production signal已验证",
    "entry rule已验证",
    "position size已验证",
    "R03 risk-budget allocation已验证",
]


def _load_config(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _add(
    rows: list[dict[str, Any]],
    check_id: str,
    category: str,
    condition: bool,
    severity: str,
    failure_reason: str = "",
    affected_rows: int = 0,
    artifact_path: str = "",
) -> None:
    rows.append(
        {
            "check_id": check_id,
            "check_category": category,
            "status": "passed" if condition else "failed",
            "severity": severity,
            "failure_reason": "" if condition else failure_reason,
            "affected_rows": 0 if condition else int(affected_rows),
            "artifact_path": artifact_path,
        }
    )


def _require_columns(rows: list[dict[str, Any]], df: pd.DataFrame, cols: set[str], check_id: str, artifact_path: Path) -> None:
    missing = sorted(cols - set(df.columns))
    _add(rows, check_id, "schema", not missing, "error", f"missing columns: {missing}", len(missing), relpath(artifact_path))


def _status(rows: list[dict[str, Any]]) -> str:
    df = pd.DataFrame(rows)
    if df.empty:
        return "passed"
    failed = df["status"].eq("failed") & df["severity"].isin(["error", "fatal"])
    return "failed" if bool(failed.any()) else "passed"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _clean_r03b_count(config: dict[str, Any]) -> int:
    seeds = pd.read_parquet(topic_path(Path(config["upstream_r03b"]["seed_episode_panel"])))
    step = pd.read_parquet(topic_path(Path(config["upstream_r03b"]["sequence_step_panel"])))
    for col in ["seed_trade_date", "seed_entry_date"]:
        if col in seeds.columns:
            seeds[col] = pd.to_datetime(seeds[col], errors="coerce")
    if "step_signal_date" in step.columns:
        step["step_signal_date"] = pd.to_datetime(step["step_signal_date"], errors="coerce")
    return int(len(_build_clean_steps(seeds, step, config)))


def validate(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    output_root = topic_path(Path(config["output_root"]))
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r03c_price_aware_kth_fresh_family_set_pooling_manifest.json"
    validation_path = manifests_dir / "r03c_price_aware_kth_fresh_family_set_pooling_validation.json"
    audit_path = reports_dir / "r03c_price_aware_pooling_validation_audit.csv"
    rows: list[dict[str, Any]] = []

    for name in REPORTS:
        _add(rows, f"required_report_exists_{name}", "existence", (reports_dir / name).exists(), "fatal", "required report missing", 1, relpath(reports_dir / name))
    for name in CACHE:
        _add(rows, f"required_cache_exists_{name}", "existence", (cache_dir / name).exists(), "fatal", "required cache missing", 1, relpath(cache_dir / name))
    for name in MANIFESTS:
        _add(rows, f"required_manifest_exists_{name}", "existence", (manifests_dir / name).exists(), "fatal", "required manifest missing", 1, relpath(manifests_dir / name))

    if not manifest_path.exists():
        result = {"validation_status": "failed", "failed_checks": ["manifest_missing"], "audit_path": relpath(audit_path)}
        pd.DataFrame(rows).to_csv(audit_path, index=False)
        write_json(result, validation_path)
        return result

    manifest = _read_json(manifest_path)
    _add(
        rows,
        "final_decision_complete",
        "manifest",
        manifest.get("final_decision") == "descriptive_price_aware_pooling_diagnostic_complete",
        "fatal",
        f"unexpected final_decision: {manifest.get('final_decision')}",
        1,
        relpath(manifest_path),
    )
    _add(rows, "diagnostic_status_descriptive_only", "manifest", manifest.get("diagnostic_status") == "descriptive_only", "error", "diagnostic status must be descriptive_only", 1, relpath(manifest_path))

    dfs: dict[str, pd.DataFrame] = {}
    for name in REPORTS:
        path = reports_dir / name
        if name.endswith(".csv") and path.exists():
            dfs[name] = pd.read_csv(path, low_memory=False)
    cache: dict[str, pd.DataFrame] = {}
    for name in CACHE:
        path = cache_dir / name
        if path.exists():
            cache[name] = pd.read_parquet(path)

    fresh = cache.get("r03c_fresh_step_price_panel.parquet", pd.DataFrame())
    checkpoint = cache.get("r03c_checkpoint_price_state_panel.parquet", pd.DataFrame())
    pooling = cache.get("r03c_family_set_pooling_panel.parquet", pd.DataFrame())
    _require_columns(rows, fresh, FRESH_REQUIRED, "fresh_step_price_panel_schema", cache_dir / "r03c_fresh_step_price_panel.parquet")
    _require_columns(rows, checkpoint, CHECKPOINT_REQUIRED, "checkpoint_price_state_panel_schema", cache_dir / "r03c_checkpoint_price_state_panel.parquet")
    _require_columns(rows, pooling, POOLING_REQUIRED, "family_set_pooling_panel_schema", cache_dir / "r03c_family_set_pooling_panel.parquet")

    if not fresh.empty and FRESH_REQUIRED.issubset(fresh.columns):
        _add(rows, "fresh_step_count_matches_manifest", "denominator", len(fresh) == int(manifest.get("clean_primary_fresh_step_count", -1)), "fatal", "fresh row count mismatch manifest", abs(len(fresh) - int(manifest.get("clean_primary_fresh_step_count", -1))), relpath(cache_dir / "r03c_fresh_step_price_panel.parquet"))
        expected_clean_count = _clean_r03b_count(config)
        _add(rows, "fresh_step_count_matches_r03b_clean_derivation", "membership", len(fresh) == expected_clean_count, "fatal", "fresh panel does not match R03b clean primary fresh derivation", abs(len(fresh) - expected_clean_count), relpath(cache_dir / "r03c_fresh_step_price_panel.parquet"))
        ordered = fresh.sort_values(["seed_episode_id", "step_offset", "step_signal_date", "added_family_set"]).copy()
        ordered["expected_kth"] = ordered.groupby("seed_episode_id").cumcount() + 1
        _add(rows, "kth_fresh_index_rederived_from_clean_steps", "membership", (ordered["kth_fresh_step_index_raw"].astype(int) == ordered["expected_kth"].astype(int)).all(), "fatal", "kth_fresh_step_index_raw mismatch", int((ordered["kth_fresh_step_index_raw"].astype(int) != ordered["expected_kth"].astype(int)).sum()), relpath(cache_dir / "r03c_fresh_step_price_panel.parquet"))
        _add(rows, "fresh_panel_no_no_fresh_bucket", "price_bucket", not fresh["wait_return_bucket"].astype(str).eq("no_fresh").any(), "error", "no_fresh appeared in fresh-step wait bucket", int(fresh["wait_return_bucket"].astype(str).eq("no_fresh").sum()), relpath(cache_dir / "r03c_fresh_step_price_panel.parquet"))
        allowed_wait = {"down_or_flat", "up_0_5pct", "up_5_10pct", "up_10_20pct", "up_gt_20pct", "missing_or_invalid"}
        _add(rows, "fresh_wait_buckets_allowed", "price_bucket", set(fresh["wait_return_bucket"].dropna().astype(str)).issubset(allowed_wait), "error", "unexpected wait bucket", 1, relpath(cache_dir / "r03c_fresh_step_price_panel.parquet"))
        _add(rows, "fresh_path_labels_allowed", "outcome", set(fresh["fresh_path_label"].dropna().astype(str)).issubset(set(PATH_LABELS + ["censored_or_invalid"])), "error", "unexpected fresh path label", 1, relpath(cache_dir / "r03c_fresh_step_price_panel.parquet"))

    if not checkpoint.empty and CHECKPOINT_REQUIRED.issubset(checkpoint.columns):
        no_fresh = checkpoint["wait_return_bucket_before_or_at_checkpoint"].astype(str).eq("no_fresh")
        _add(rows, "checkpoint_no_fresh_rows_retained", "checkpoint", bool(no_fresh.any()), "error", "no_fresh checkpoint rows missing", 1, relpath(cache_dir / "r03c_checkpoint_price_state_panel.parquet"))
        _add(rows, "checkpoint_latest_fields_no_fresh_filled", "checkpoint", checkpoint.loc[no_fresh, "latest_clean_fresh_kth_fresh_step_bucket_before_or_at_checkpoint"].astype(str).eq("no_fresh").all(), "error", "no_fresh kth bucket not filled", int(no_fresh.sum()), relpath(cache_dir / "r03c_checkpoint_price_state_panel.parquet"))
        latest_offset = pd.to_numeric(checkpoint["latest_clean_fresh_step_offset_before_or_at_checkpoint"], errors="coerce")
        chk_offset = pd.to_numeric(checkpoint["checkpoint_offset"], errors="coerce")
        future = latest_offset.notna() & (latest_offset > chk_offset)
        _add(rows, "checkpoint_does_not_use_future_fresh_step", "leakage", not bool(future.any()), "fatal", "latest fresh offset after checkpoint", int(future.sum()), relpath(cache_dir / "r03c_checkpoint_price_state_panel.parquet"))

    if not pooling.empty and POOLING_REQUIRED.issubset(pooling.columns):
        levels = set(pooling["pooling_level"].dropna().astype(str))
        _add(rows, "pooling_levels_allowed", "pooling", levels == ALLOWED_POOLING_LEVELS, "error", f"unexpected pooling levels: {sorted(levels)}", 1, relpath(cache_dir / "r03c_family_set_pooling_panel.parquet"))
        presence = pooling.loc[pooling["pooling_level"].eq("family_presence_signature")].copy()
        if not presence.empty:
            expected = presence["cumulative_distinct_family_set_after_step"].map(_presence_signature)
            _add(rows, "family_presence_signature_from_cumulative_set", "pooling", presence["pooling_key"].astype(str).eq(expected.astype(str)).all(), "fatal", "family_presence_signature not based on cumulative family set", int((~presence["pooling_key"].astype(str).eq(expected.astype(str))).sum()), relpath(cache_dir / "r03c_family_set_pooling_panel.parquet"))
        expected_rows = len(fresh) * 3 if not fresh.empty else 0
        _add(rows, "pooling_row_count_three_levels_per_fresh_step", "pooling", len(pooling) == expected_rows, "error", "pooling row count must equal fresh steps x 3", abs(len(pooling) - expected_rows), relpath(cache_dir / "r03c_family_set_pooling_panel.parquet"))

    for df_name in [
        "r03c_fresh_count_price_conditioned_summary.csv",
        "r03c_kth_offset_price_summary.csv",
        "r03c_family_set_pooling_summary.csv",
        "r03c_seed_vs_fresh_anchor_outcome_audit.csv",
    ]:
        df = dfs.get(df_name, pd.DataFrame())
        _require_columns(rows, df, SUMMARY_REQUIRED & set(df.columns) if df_name.endswith("audit.csv") else SUMMARY_REQUIRED, f"{df_name}_headline_schema", reports_dir / df_name)
        if not df.empty and "split" in df.columns:
            _add(rows, f"{df_name}_has_all_splits", "split", set(ALL_SPLITS).issubset(set(df["split"].astype(str))), "error", "summary missing required splits", 1, relpath(reports_dir / df_name))
        if not df.empty and "sample_sufficiency_status" in df.columns:
            allowed_status = {"sufficient", "thin_report_only", "too_sparse_report_only", "unusable"}
            _add(rows, f"{df_name}_sample_status_allowed", "schema", set(df["sample_sufficiency_status"].dropna().astype(str)).issubset(allowed_status), "error", "unexpected sample_sufficiency_status", 1, relpath(reports_dir / df_name))

    recon = dfs.get("r03c_price_reconciliation_audit.csv", pd.DataFrame())
    if not recon.empty:
        _add(rows, "price_reconciliation_all_passed", "reconciliation", recon["reconciliation_status"].astype(str).eq("passed").all(), "fatal", "reconciliation failures present", int(recon["reconciliation_status"].astype(str).ne("passed").sum()), relpath(reports_dir / "r03c_price_reconciliation_audit.csv"))

    explanatory = dfs.get("r03c_grouping_explanatory_power_comparison.csv", pd.DataFrame())
    if not explanatory.empty:
        _add(rows, "grouping_schemes_allowed", "explanatory_power", set(explanatory["grouping_scheme"].dropna().astype(str)).issubset(ALLOWED_GROUPING_SCHEMES), "error", "unexpected grouping scheme", 1, relpath(reports_dir / "r03c_grouping_explanatory_power_comparison.csv"))
        _add(rows, "outcome_families_allowed", "explanatory_power", set(explanatory["outcome_family"].dropna().astype(str)).issubset(ALLOWED_OUTCOMES), "error", "unexpected outcome family", 1, relpath(reports_dir / "r03c_grouping_explanatory_power_comparison.csv"))
        _add(rows, "wait_ratio_not_lift_input", "explanatory_power", not any("wait_cost_to_remaining_max_gain_ratio" in col for col in explanatory.columns), "fatal", "wait_cost_to_remaining_max_gain_ratio used in explanatory power table", 1, relpath(reports_dir / "r03c_grouping_explanatory_power_comparison.csv"))

    survival = dfs.get("r03c_survival_price_bias_audit.csv", pd.DataFrame())
    if not survival.empty:
        r03b_seeds = pd.read_parquet(topic_path(Path(config["upstream_r03b"]["seed_episode_panel"])))
        expected = {"all": len(r03b_seeds)}
        expected.update(r03b_seeds["split"].value_counts().to_dict())
        observed = dict(zip(survival["split"].astype(str), survival["seed_episode_count"].astype(int)))
        _add(rows, "survival_seed_counts_match_r03b", "survival_bias", all(int(observed.get(k, -1)) == int(v) for k, v in expected.items()), "fatal", "survival seed counts do not match R03b seed panel", 1, relpath(reports_dir / "r03c_survival_price_bias_audit.csv"))

    all_columns = list(fresh.columns) + list(checkpoint.columns) + list(pooling.columns)
    _add(rows, "family_role_set_absent_all_outputs", "schema", not any("family_role_set" in str(col) for col in all_columns), "fatal", "family_role_set appears in R03c V1 output", 1, relpath(output_root))

    report_path = reports_dir / "r03c_price_aware_pooling_final_report.md"
    report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    required_phrases = [
        "本诊断明确区分 seed-anchor big-winner、fresh-anchor big-winner 和 path labels",
        "P_good / P_bad 不得解读为 P(big winner | signal)",
        "fresh-anchor outcome 不能替代 seed-anchor outcome",
        "不同 row grain 的 explanatory-power lift 不得直接比较",
        "本实验不产出 production signal",
        "本实验不产出 entry rule",
        "本实验不产出 position size",
        "本实验不产出 R03 risk-budget allocation",
        "不同 price anchor",
    ]
    missing_phrases = [phrase for phrase in required_phrases if phrase not in report]
    _add(rows, "final_report_required_warnings_present", "report", not missing_phrases, "error", f"missing report phrases: {missing_phrases}", len(missing_phrases), relpath(report_path))
    forbidden = [token for token in FORBIDDEN_REPORT_TOKENS if token in report]
    _add(rows, "final_report_no_production_claims", "report", not forbidden, "error", f"forbidden report tokens: {forbidden}", len(forbidden), relpath(report_path))

    _add(rows, "validation_audit_schema", "validation", True, "info", "", 0, relpath(audit_path))
    audit = pd.DataFrame(rows)
    if not VALIDATION_AUDIT_COLS.issubset(audit.columns):
        for col in VALIDATION_AUDIT_COLS - set(audit.columns):
            audit[col] = np.nan
    audit = audit[["check_id", "check_category", "status", "severity", "failure_reason", "affected_rows", "artifact_path"]]
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(audit_path, index=False)

    validation_status = _status(rows)
    result = {
        "validation_status": validation_status,
        "final_decision": manifest.get("final_decision"),
        "failed_checks": audit.loc[audit["status"].eq("failed"), "check_id"].tolist(),
        "audit_path": relpath(audit_path),
    }
    write_json(result, validation_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    result = validate(args.config)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
