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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r03b_signal_sequence_big_winner_path_diagnostic_v1.yaml"
REPORTS = [
    "r03b_input_readiness_audit.csv",
    "r03b_input_reconciliation_audit.csv",
    "r03b_seed_episode_label_summary.csv",
    "r03b_checkpoint_fresh_count_summary.csv",
    "r03b_kth_fresh_summary.csv",
    "r03b_sequence_pattern_summary.csv",
    "r03b_offset_hazard_summary.csv",
    "r03b_survival_bias_audit.csv",
    "r03b_same_offset_multi_family_audit.csv",
    "r03b_same_family_repeat_audit.csv",
    "r03b_big_winner_label_audit.csv",
    "r03b_sequence_big_winner_path_final_report.md",
]
CACHE = [
    "r03b_seed_episode_panel.parquet",
    "r03b_signal_timeline_panel.parquet",
    "r03b_sequence_step_panel.parquet",
    "r03b_checkpoint_state_panel.parquet",
    "r03b_offset_hazard_panel.parquet",
]
POSTERIOR_COLS = {
    "split",
    "year",
    "conditioning_state",
    "conditioning_key",
    "seed_episode_count",
    "big_winner_label_denominator",
    "big_winner_count_close_anchor",
    "big_winner_rate_close_anchor",
    "big_winner_rate_close_anchor_lower",
    "big_winner_rate_close_anchor_upper",
    "path_label_denominator",
    "good_count",
    "bad_count",
    "neutral_count",
    "P_good",
    "P_bad",
    "P_neutral",
    "P_good_lower",
    "P_good_upper",
    "P_bad_lower",
    "P_bad_upper",
    "censored_or_invalid_count",
    "failed_before_condition_count",
    "sample_sufficiency_status",
}
FORBIDDEN_REPORT_TOKENS = [
    "passed signal",
    "validated entry",
    "production gate",
    "add position",
    "buy signal",
    "1R sizing",
]


def _load_config(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _check(condition: bool, check_id: str, detail: Any, rows: list[dict[str, Any]]) -> None:
    rows.append({"check_id": check_id, "status": "passed" if condition else "failed", "detail": str(detail)})


def _require_columns(df: pd.DataFrame, cols: set[str], check_id: str, rows: list[dict[str, Any]]) -> None:
    missing = sorted(cols - set(df.columns))
    _check(not missing, check_id, missing, rows)


def _prob_sum_ok(df: pd.DataFrame) -> bool:
    den = pd.to_numeric(df["path_label_denominator"], errors="coerce").fillna(0)
    sums = (
        pd.to_numeric(df["P_good"], errors="coerce")
        + pd.to_numeric(df["P_bad"], errors="coerce")
        + pd.to_numeric(df["P_neutral"], errors="coerce")
    )
    return bool(((den <= 0) | (sums.sub(1.0).abs() < 1e-8)).all())


def validate(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    output_root = topic_path(Path(config["output_root"]))
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r03b_signal_sequence_big_winner_path_manifest.json"
    rows: list[dict[str, Any]] = []

    for name in REPORTS:
        _check((reports_dir / name).exists(), f"required_report_exists_{name}", relpath(reports_dir / name), rows)
    for name in CACHE:
        _check((cache_dir / name).exists(), f"required_cache_exists_{name}", relpath(cache_dir / name), rows)
    _check(manifest_path.exists(), "manifest_exists", relpath(manifest_path), rows)

    if not manifest_path.exists():
        result = {"validation_status": "failed", "failed_checks": ["manifest_exists"]}
        write_json(result, manifests_dir / "r03b_signal_sequence_big_winner_path_validation.json")
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _check(
        manifest.get("final_decision") == "descriptive_sequence_diagnostic_complete",
        "final_decision_complete",
        manifest.get("final_decision"),
        rows,
    )
    _check(manifest.get("episode_grain") == "deterministic_episode_first_trigger", "episode_grain_recorded", manifest.get("episode_grain"), rows)
    _check(len(manifest.get("condition_group_dictionary", {})) == 7, "condition_dictionary_size_7", manifest.get("condition_group_dictionary"), rows)
    _check(abs(float(manifest.get("credible_interval_level", 0)) - 0.90) < 1e-12, "credible_interval_90", manifest.get("credible_interval_level"), rows)

    dfs = {}
    for name in REPORTS:
        if name.endswith(".csv") and (reports_dir / name).exists():
            dfs[name] = pd.read_csv(reports_dir / name, low_memory=False)
    cache = {}
    for name in CACHE:
        if (cache_dir / name).exists():
            cache[name] = pd.read_parquet(cache_dir / name)

    readiness = dfs.get("r03b_input_readiness_audit.csv", pd.DataFrame())
    _require_columns(readiness, {"artifact_role", "artifact_path", "exists", "validation_status", "readiness_status", "failure_reason"}, "readiness_schema", rows)
    if not readiness.empty:
        _check(readiness["exists"].astype(bool).all(), "all_required_inputs_exist", readiness.loc[~readiness["exists"].astype(bool), "artifact_path"].tolist(), rows)
        _check(readiness["readiness_status"].eq("ready").all(), "all_required_inputs_ready", readiness.loc[~readiness["readiness_status"].eq("ready"), "artifact_path"].tolist(), rows)

    recon = dfs.get("r03b_input_reconciliation_audit.csv", pd.DataFrame())
    _require_columns(recon, {"family_id", "condition_group_id", "path_signal_count", "precision_signal_occurs_count", "matched_signal_count", "path_only_count", "precision_only_count", "reconciliation_status"}, "reconciliation_schema", rows)
    if not recon.empty:
        _check(recon["reconciliation_status"].eq("passed").all(), "input_reconciliation_passed", recon.to_dict("records"), rows)
        _check((pd.to_numeric(recon["path_only_count"], errors="coerce").fillna(0) == 0).all(), "no_path_only_occurrences", "", rows)
        _check((pd.to_numeric(recon["precision_only_count"], errors="coerce").fillna(0) == 0).all(), "no_precision_only_occurrences", "", rows)

    seeds = cache.get("r03b_seed_episode_panel.parquet", pd.DataFrame())
    timeline = cache.get("r03b_signal_timeline_panel.parquet", pd.DataFrame())
    step = cache.get("r03b_sequence_step_panel.parquet", pd.DataFrame())
    checkpoint = cache.get("r03b_checkpoint_state_panel.parquet", pd.DataFrame())
    _require_columns(
        seeds,
        {"seed_episode_id", "instrument_id", "seed_trade_date", "seed_family_set", "split", "label", "complete_h120_close_anchor_flag", "big_winner_forward_h120_close_anchor", "observable_failure_offset"},
        "seed_schema",
        rows,
    )
    if not seeds.empty:
        _check(not seeds["seed_episode_id"].duplicated().any(), "seed_episode_id_unique", int(seeds["seed_episode_id"].duplicated().sum()), rows)
        _check(seeds["label"].isin(["good_path", "bad_path", "neutral_path", "censored_or_invalid"]).all(), "path_labels_allowed", seeds["label"].value_counts().to_dict(), rows)
        _check(set(seeds["split"].unique()).issubset({"train", "validation", "robustness"}), "seed_splits_allowed", sorted(seeds["split"].unique()), rows)

    if not timeline.empty:
        t12 = timeline["offset_from_seed"].isin([1, 2]) & timeline["included_in_primary_fresh_count"].astype(bool)
        _check(not t12.any(), "t1_t2_not_primary_fresh", int(t12.sum()), rows)
    if not step.empty:
        _check(
            not step.loc[step["step_status"].eq("ambiguous_same_offset"), "included_in_primary_fresh_count"].astype(bool).any(),
            "ambiguous_not_primary_fresh",
            "",
            rows,
        )
        _check(
            not step.loc[step["step_status"].eq("after_observable_failure"), "included_in_primary_fresh_count"].astype(bool).any(),
            "after_failure_not_primary_fresh",
            "",
            rows,
        )

    if not checkpoint.empty:
        _require_columns(
            checkpoint,
            {"seed_episode_id", "checkpoint", "fresh_distinct_family_count_before_or_at_checkpoint", "fresh_distinct_family_count_bucket", "at_risk_at_checkpoint", "checkpoint_state"},
            "checkpoint_schema",
            rows,
        )
        _check(checkpoint["fresh_distinct_family_count_bucket"].isin(["0", "1", "2", "3plus"]).all(), "fresh_count_buckets_allowed", checkpoint["fresh_distinct_family_count_bucket"].value_counts().to_dict(), rows)

    for name in [
        "r03b_seed_episode_label_summary.csv",
        "r03b_checkpoint_fresh_count_summary.csv",
        "r03b_kth_fresh_summary.csv",
        "r03b_sequence_pattern_summary.csv",
    ]:
        df = dfs.get(name, pd.DataFrame())
        _require_columns(df, POSTERIOR_COLS, f"{name}_posterior_schema", rows)
        if not df.empty and POSTERIOR_COLS.issubset(df.columns):
            _check(_prob_sum_ok(df), f"{name}_path_probabilities_sum_to_one", "", rows)
            _check(df["sample_sufficiency_status"].isin(["sufficient", "thin_report_only", "too_sparse_report_only", "unusable"]).all(), f"{name}_sample_status_allowed", df["sample_sufficiency_status"].value_counts().to_dict(), rows)

    kth = dfs.get("r03b_kth_fresh_summary.csv", pd.DataFrame())
    if not kth.empty:
        _check("kth_fresh_status=not_reached" in set(kth["conditioning_state"].astype(str)) or kth["conditioning_state"].astype(str).str.contains("kth_fresh_status=not_reached").any(), "kth_not_reached_retained", "", rows)

    pattern = dfs.get("r03b_sequence_pattern_summary.csv", pd.DataFrame())
    if not pattern.empty:
        _check(not pattern["conditioning_state"].astype(str).str.contains("checkpoint=T\\+3").any() or pattern["conditioning_state"].astype(str).str.contains("checkpoint=T\\+3").any(), "pattern_summary_readable", len(pattern), rows)

    hazard = dfs.get("r03b_offset_hazard_summary.csv", pd.DataFrame())
    _require_columns(hazard, {"split", "offset", "fresh_family_id", "kth_fresh_step_index", "at_risk_episode_count", "fresh_event_count", "fresh_hazard_rate", "failed_before_offset_count", "censored_before_offset_count"}, "hazard_schema", rows)

    report_path = reports_dir / "r03b_sequence_big_winner_path_final_report.md"
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
        _check("Final decision: `descriptive_sequence_diagnostic_complete`" in text, "report_final_decision_present", "", rows)
        _check("P_good / P_bad 不得解读为 P(big winner | signal)" in text, "report_path_bigwinner_warning_present", "", rows)
        for token in FORBIDDEN_REPORT_TOKENS:
            _check(token not in text, f"forbidden_report_token_absent_{token.replace(' ', '_')}", token, rows)

    audit = pd.DataFrame(rows)
    audit_path = reports_dir / "r03b_signal_sequence_big_winner_path_validation_audit.csv"
    audit.to_csv(audit_path, index=False)
    failed = audit.loc[audit["status"].eq("failed"), "check_id"].tolist()
    result = {
        "validation_status": "passed" if not failed else "failed",
        "failed_checks": failed,
        "audit_path": relpath(audit_path),
    }
    write_json(result, manifests_dir / "r03b_signal_sequence_big_winner_path_validation.json")
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    validate(args.config)


if __name__ == "__main__":
    main()
