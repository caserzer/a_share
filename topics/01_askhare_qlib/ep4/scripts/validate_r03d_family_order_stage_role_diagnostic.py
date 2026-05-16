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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r03d_family_order_stage_role_diagnostic_v1.yaml"
REPORTS = [
    "r03d_input_readiness_audit.csv",
    "r03d_family_position_summary.csv",
    "r03d_stage_role_summary.csv",
    "r03d_next_family_given_prefix_summary.csv",
    "r03d_pair_order_asymmetry_summary.csv",
    "r03d_last_added_family_price_conditioned_summary.csv",
    "r03d_order_explanatory_power_comparison.csv",
    "r03d_order_split_stability_audit.csv",
    "r03d_denominator_and_survival_audit.csv",
    "r03d_family_order_stage_role_final_report.md",
    "r03d_family_order_stage_role_validation_audit.csv",
]
CACHE = [
    "r03d_family_order_step_panel.parquet",
    "r03d_order_transition_candidate_panel.parquet",
    "r03d_pair_order_panel.parquet",
    "r03d_stage_role_panel.parquet",
]
MANIFESTS = [
    "r03d_family_order_stage_role_manifest.json",
    "r03d_family_order_stage_role_validation.json",
]
FINAL_DECISIONS = {
    "supported_order_incremental_edge",
    "stage_role_only_no_order_increment",
    "price_state_proxy_only",
    "insufficient_denominator",
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_validation_failed",
}
COMPONENT_STATES = {"supported", "no_increment", "price_state_proxy", "insufficient_denominator"}
PRICE_BUCKETS = {
    "seed_anchor",
    "not_observed",
    "down_or_flat",
    "up_0_5pct",
    "up_5_10pct",
    "up_10_20pct",
    "up_gt_20pct",
    "missing_or_invalid",
}


def _load_config(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


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


def _family_list(value: Any) -> list[str]:
    if pd.isna(value):
        return []
    text = str(value)
    if not text or text == "none":
        return []
    return [part for part in text.split("|") if part and part != "none"]


def _require_columns(rows: list[dict[str, Any]], df: pd.DataFrame, cols: set[str], check_id: str, artifact_path: Path) -> None:
    missing = sorted(cols - set(df.columns))
    _add(rows, check_id, "schema", not missing, "error", f"missing columns: {missing}", len(missing), relpath(artifact_path))


def _status(rows: list[dict[str, Any]]) -> str:
    df = pd.DataFrame(rows)
    if df.empty:
        return "passed"
    failed = df["status"].eq("failed") & df["severity"].isin(["error", "fatal"])
    return "failed" if bool(failed.any()) else "passed"


def validate(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    output_root = topic_path(Path(config["output_root"]))
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r03d_family_order_stage_role_manifest.json"
    validation_path = manifests_dir / "r03d_family_order_stage_role_validation.json"
    audit_path = reports_dir / "r03d_family_order_stage_role_validation_audit.csv"
    rows: list[dict[str, Any]] = []

    for name in REPORTS:
        _add(rows, f"required_report_exists_{name}", "existence", (reports_dir / name).exists(), "fatal", "required report missing", 1, relpath(reports_dir / name))
    for name in CACHE:
        _add(rows, f"required_cache_exists_{name}", "existence", (cache_dir / name).exists(), "fatal", "required cache missing", 1, relpath(cache_dir / name))
    for name in MANIFESTS:
        _add(rows, f"required_manifest_exists_{name}", "existence", (manifests_dir / name).exists(), "fatal", "required manifest missing", 1, relpath(manifests_dir / name))

    if not manifest_path.exists():
        reports_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(audit_path, index=False)
        result = {"validation_status": "failed", "failed_checks": ["manifest_missing"], "audit_path": relpath(audit_path)}
        write_json(result, validation_path)
        return result

    manifest = _read_json(manifest_path)
    final_decision = manifest.get("final_decision")
    _add(rows, "final_decision_allowed", "manifest", final_decision in FINAL_DECISIONS, "error", f"invalid final_decision={final_decision}", 1, relpath(manifest_path))
    components = manifest.get("decision_components", {})
    expected_components = {"prefix_order_incremental", "pair_order_incremental", "last_added_family_incremental"}
    _add(
        rows,
        "decision_components_complete",
        "manifest",
        set(components) == expected_components and all(v in COMPONENT_STATES for v in components.values()),
        "error",
        "decision_components missing or invalid",
        1,
        relpath(manifest_path),
    )
    _add(
        rows,
        "supported_decision_requires_order_component",
        "manifest",
        final_decision != "supported_order_incremental_edge"
        or components.get("prefix_order_incremental") == "supported"
        or components.get("pair_order_incremental") == "supported",
        "error",
        "supported_order_incremental_edge requires prefix or pair component",
        1,
        relpath(manifest_path),
    )

    upstream_r03b_validation = _read_json(topic_path(Path(config["upstream_r03b"]["validation"]))).get("validation_status")
    upstream_r03c_validation = _read_json(topic_path(Path(config["upstream_r03c"]["validation"]))).get("validation_status")
    _add(rows, "upstream_r03b_validation_passed", "upstream", upstream_r03b_validation == "passed", "fatal", "R03b validation not passed", 1)
    _add(rows, "upstream_r03c_validation_passed", "upstream", upstream_r03c_validation == "passed", "fatal", "R03c validation not passed", 1)

    seed_path = topic_path(Path(config["upstream_r03b"]["seed_episode_panel"]))
    r03c_fresh_path = topic_path(Path(config["upstream_r03c"]["fresh_step_price_panel"]))
    seeds = pd.read_parquet(seed_path)
    r03c_fresh = pd.read_parquet(r03c_fresh_path)
    order_step = pd.read_parquet(cache_dir / "r03d_family_order_step_panel.parquet") if (cache_dir / "r03d_family_order_step_panel.parquet").exists() else pd.DataFrame()
    transition = pd.read_parquet(cache_dir / "r03d_order_transition_candidate_panel.parquet") if (cache_dir / "r03d_order_transition_candidate_panel.parquet").exists() else pd.DataFrame()
    pair = pd.read_parquet(cache_dir / "r03d_pair_order_panel.parquet") if (cache_dir / "r03d_pair_order_panel.parquet").exists() else pd.DataFrame()
    stage = pd.read_parquet(cache_dir / "r03d_stage_role_panel.parquet") if (cache_dir / "r03d_stage_role_panel.parquet").exists() else pd.DataFrame()

    _add(rows, "seed_episode_count_matches_r03b", "lineage", len(seeds) * len(config["family_universe"]) == len(stage), "error", "stage_role_panel row count mismatch", abs(len(seeds) * len(config["family_universe"]) - len(stage)), relpath(cache_dir / "r03d_stage_role_panel.parquet"))
    _add(rows, "fresh_step_count_matches_r03c", "lineage", len(order_step) == len(r03c_fresh), "error", "fresh step row count mismatch", abs(len(order_step) - len(r03c_fresh)), relpath(cache_dir / "r03d_family_order_step_panel.parquet"))

    family_universe = set(config["family_universe"])
    unknown: set[str] = set()
    for df, cols in [
        (order_step, ["seed_family_set", "added_family_set", "family_presence_signature_after_step"]),
        (transition, ["prefix_family_set", "candidate_next_family", "next_step_added_family_set"]),
        (pair, ["family_a", "family_b", "unordered_pair_key"]),
        (stage, ["family"]),
    ]:
        for col in cols:
            if col not in df.columns:
                continue
            for value in df[col].dropna().astype(str).unique():
                if col in {"candidate_next_family", "family", "family_a", "family_b"}:
                    if value not in family_universe:
                        unknown.add(value)
                else:
                    for family in _family_list(value):
                        if family not in family_universe:
                            unknown.add(family)
    _add(rows, "family_universe_known", "schema", not unknown, "error", f"unknown family tokens={sorted(unknown)}", len(unknown))

    _require_columns(
        rows,
        order_step,
        {
            "seed_complete_h120_close_anchor_flag",
            "fresh_complete_h120_close_anchor_flag",
            "family_presence_signature_before_step",
            "family_presence_signature_after_step",
            "last_added_family_set",
        },
        "order_step_required_columns",
        cache_dir / "r03d_family_order_step_panel.parquet",
    )
    _require_columns(
        rows,
        transition,
        {
            "candidate_weight",
            "candidate_occurs_at_next_step",
            "next_step_fresh_complete_h120_close_anchor_flag",
            "candidate_fresh_complete_h120_close_anchor_flag",
            "candidate_fresh_anchor_big_winner",
            "candidate_fresh_path_label",
        },
        "transition_required_columns",
        cache_dir / "r03d_order_transition_candidate_panel.parquet",
    )
    _require_columns(
        rows,
        pair,
        {
            "seed_complete_h120_close_anchor_flag",
            "pair_completion_fresh_complete_h120_close_anchor_flag",
            "pair_order_key",
            "pair_completion_wait_return_bucket",
        },
        "pair_required_columns",
        cache_dir / "r03d_pair_order_panel.parquet",
    )
    _require_columns(
        rows,
        stage,
        {
            "seed_complete_h120_close_anchor_flag",
            "fresh_complete_h120_close_anchor_flag_if_observed_as_fresh",
            "first_observed_stage",
            "first_observed_price_state_bucket",
        },
        "stage_required_columns",
        cache_dir / "r03d_stage_role_panel.parquet",
    )

    if not transition.empty and {"seed_episode_id", "prefix_step_index", "candidate_weight"}.issubset(transition.columns):
        weight_sums = transition.groupby(["seed_episode_id", "prefix_step_index"])["candidate_weight"].sum()
        bad_weights = int((weight_sums.sub(1).abs() > 1e-9).sum())
        _add(rows, "candidate_weight_sums_to_one", "denominator", bad_weights == 0, "error", "candidate weights do not sum to one", bad_weights, relpath(cache_dir / "r03d_order_transition_candidate_panel.parquet"))
        false_rows = transition.loc[~transition["candidate_occurs_at_next_step"].astype(bool)]
        bad_false = 0
        for col in ["candidate_fresh_complete_h120_close_anchor_flag", "candidate_fresh_anchor_big_winner", "candidate_fresh_path_label"]:
            if col in false_rows.columns:
                bad_false += int(false_rows[col].notna().sum())
        _add(rows, "false_candidate_fresh_fields_null", "schema", bad_false == 0, "error", "false candidate rows have candidate_fresh fields", bad_false, relpath(cache_dir / "r03d_order_transition_candidate_panel.parquet"))
        _add(
            rows,
            "transition_contains_false_rows",
            "denominator",
            bool((~transition["candidate_occurs_at_next_step"].astype(bool)).any()),
            "error",
            "transition candidate panel lacks false rows",
            1,
            relpath(cache_dir / "r03d_order_transition_candidate_panel.parquet"),
        )

    if "first_observed_stage" in stage.columns:
        not_observed = int(stage["first_observed_stage"].eq("not_observed").sum())
        observed = int(len(stage) - not_observed)
        expected_not_observed = len(seeds) * len(config["family_universe"]) - observed
        _add(rows, "not_observed_rows_preserved", "denominator", not_observed == expected_not_observed, "error", "not_observed row count mismatch", abs(not_observed - expected_not_observed), relpath(cache_dir / "r03d_stage_role_panel.parquet"))

    price_bad = set()
    for df, col in [(order_step, "price_state_bucket"), (transition, "price_state_bucket"), (stage, "first_observed_price_state_bucket")]:
        if col in df.columns:
            price_bad.update(set(df[col].dropna().astype(str).unique()) - PRICE_BUCKETS)
    _add(rows, "price_state_bucket_allowed", "schema", not price_bad, "error", f"invalid price buckets={sorted(price_bad)}", len(price_bad))

    comparison_path = reports_dir / "r03d_order_explanatory_power_comparison.csv"
    if comparison_path.exists():
        comparison = pd.read_csv(comparison_path)
        _require_columns(
            rows,
            comparison,
            {
                "split",
                "grouping_scheme",
                "row_grain",
                "outcome",
                "bucket_count",
                "sufficient_bucket_count",
                "sufficient_bucket_ratio",
                "parent_grouping_scheme",
                "weighted_abs_lift_vs_parent",
                "weighted_signed_lift_vs_parent",
                "interpretability_status",
            },
            "comparison_required_columns",
            comparison_path,
        )
        required_schemes = {
            "ordered_prefix",
            "price_state_plus_ordered_prefix",
            "pair_order",
            "pair_wait_state_plus_order",
            "kth_offset_price_state_plus_last_added_family",
        }
        missing_schemes = required_schemes - set(comparison.get("grouping_scheme", pd.Series(dtype=str)).dropna().astype(str).unique())
        _add(rows, "comparison_required_schemes_present", "schema", not missing_schemes, "error", f"missing schemes={sorted(missing_schemes)}", len(missing_schemes), relpath(comparison_path))

    report_path = reports_dir / "r03d_family_order_stage_role_final_report.md"
    if report_path.exists():
        report = report_path.read_text(encoding="utf-8")
        forbidden = ["production signal已验证", "entry rule已验证", "position size已验证"]
        found = [token for token in forbidden if token in report]
        _add(rows, "report_boundary_language", "report", not found, "error", f"forbidden report tokens={found}", len(found), relpath(report_path))
        for token in ["prefix_order_incremental", "pair_order_incremental", "last_added_family_incremental"]:
            _add(rows, f"report_mentions_{token}", "report", token in report, "error", f"report missing {token}", 1, relpath(report_path))

    reports_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(audit_path, index=False)
    failed = [row["check_id"] for row in rows if row["status"] == "failed" and row["severity"] in {"error", "fatal"}]
    result = {
        "validation_status": "failed" if failed else "passed",
        "final_decision": final_decision,
        "failed_checks": failed,
        "audit_path": relpath(audit_path),
    }
    write_json(result, validation_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate EP4 R03d family order stage-role diagnostic")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    result = validate(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
