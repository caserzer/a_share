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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r03e_family_signal_bad_shape_filter_diagnostic_v1.yaml"
REPORTS = [
    "r03e_input_readiness_audit.csv",
    "r03e_bad_shape_component_definition_audit.csv",
    "r03e_bad_shape_component_summary.csv",
    "r03e_bad_score_bucket_summary.csv",
    "r03e_bad_score_threshold_tradeoff.csv",
    "r03e_filtered_outcome_summary.csv",
    "r03e_component_overlap_audit.csv",
    "r03e_survival_and_timing_bias_audit.csv",
    "r03e_split_stability_audit.csv",
    "r03e_family_signal_bad_shape_filter_final_report.md",
    "r03e_family_signal_bad_shape_filter_validation_audit.csv",
]
CACHE = [
    "r03e_family_signal_event_panel.parquet",
    "r03e_ohlcv_shape_window_panel.parquet",
    "r03e_bad_shape_feature_panel.parquet",
    "r03e_bad_shape_filter_panel.parquet",
]
MANIFESTS = [
    "r03e_family_signal_bad_shape_filter_manifest.json",
    "r03e_family_signal_bad_shape_filter_validation.json",
]
FINAL_DECISIONS = {
    "badshape_filter_supported",
    "badshape_filter_reduces_bad_path_but_costs_winners",
    "badshape_filter_no_incremental_edge",
    "insufficient_denominator",
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_validation_failed",
}
EVENT_SCOPES = {"r02_signal_episode_start", "r03_seed_family_event", "r03_clean_fresh_family_event"}
PATH_LABELS = {"good_path", "neutral_path", "bad_path"}
BAD_ITEMS = [
    "bad_item_01_ret20_lt0",
    "bad_item_02_close_below_ma20",
    "bad_item_03_ma20_slope_negative",
    "bad_item_04_recent5_low_below_prior15_low",
    "bad_item_05_down_volume_gt_up_volume",
    "bad_item_06_max_down_abs_gt_max_up",
    "bad_item_07_atr_rank_up_ret20_low",
    "bad_item_08_upper_shadow_count_ge3",
    "bad_item_09_volume_down_day_ge2",
    "bad_item_10_failed_breakout_3d",
]


def _load_config(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


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


def _status(rows: list[dict[str, Any]]) -> str:
    df = pd.DataFrame(rows)
    if df.empty:
        return "passed"
    failed = df["status"].eq("failed") & df["severity"].isin(["error", "fatal"])
    return "failed" if bool(failed.any()) else "passed"


def _require_columns(rows: list[dict[str, Any]], df: pd.DataFrame, cols: set[str], check_id: str, artifact_path: Path) -> None:
    missing = sorted(cols - set(df.columns))
    _add(rows, check_id, "schema", not missing, "error", f"missing columns: {missing}", len(missing), relpath(artifact_path))


def validate(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    output_root = topic_path(Path(config["output_root"]))
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r03e_family_signal_bad_shape_filter_manifest.json"
    validation_path = manifests_dir / "r03e_family_signal_bad_shape_filter_validation.json"
    audit_path = reports_dir / "r03e_family_signal_bad_shape_filter_validation_audit.csv"
    rows: list[dict[str, Any]] = []

    for name in REPORTS:
        if name == "r03e_family_signal_bad_shape_filter_validation_audit.csv":
            continue
        _add(rows, f"required_report_exists_{name}", "existence", (reports_dir / name).exists(), "fatal", "required report missing", 1, relpath(reports_dir / name))
    for name in CACHE:
        _add(rows, f"required_cache_exists_{name}", "existence", (cache_dir / name).exists(), "fatal", "required cache missing", 1, relpath(cache_dir / name))
    for name in MANIFESTS:
        if name == "r03e_family_signal_bad_shape_filter_validation.json":
            continue
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

    for group in ["upstream_precision", "upstream_path_query", "upstream_r03b", "upstream_r03c"]:
        validation_status = _read_json(Path(config[group]["validation"])).get("validation_status")
        _add(rows, f"{group}_validation_passed", "upstream", validation_status == "passed", "fatal", f"{group} validation not passed", 1)

    event_path = cache_dir / "r03e_family_signal_event_panel.parquet"
    feature_path = cache_dir / "r03e_bad_shape_feature_panel.parquet"
    filter_path = cache_dir / "r03e_bad_shape_filter_panel.parquet"
    window_path = cache_dir / "r03e_ohlcv_shape_window_panel.parquet"
    outcome_path = reports_dir / "r03e_filtered_outcome_summary.csv"
    threshold_path = reports_dir / "r03e_bad_score_threshold_tradeoff.csv"
    component_def_path = reports_dir / "r03e_bad_shape_component_definition_audit.csv"

    if all(path.exists() for path in [event_path, feature_path, filter_path, window_path, outcome_path, threshold_path]):
        events = pd.read_parquet(event_path)
        features = pd.read_parquet(feature_path)
        panel = pd.read_parquet(filter_path)
        window = pd.read_parquet(window_path)
        outcome = pd.read_csv(outcome_path)
        threshold = pd.read_csv(threshold_path)
        component_def = pd.read_csv(component_def_path)

        _require_columns(
            rows,
            events,
            {
                "family_signal_event_id",
                "event_scope",
                "event_stage",
                "instrument_id",
                "signal_date",
                "family_id",
                "condition_group_id",
                "t0_entry_date",
                "same_date_family_count",
                "dedup_weight",
            },
            "event_panel_required_columns",
            event_path,
        )
        _require_columns(
            rows,
            features,
            {
                "family_signal_event_id",
                "shape_eval_date",
                "shape_core_window_complete_flag",
                "bad_score_complete_flag",
                "bad_score_v1",
                "bad_score_bucket",
                "pass_primary_badshape_filter",
                "drop_primary_badshape_filter",
                "filter_entry_date",
                "filter_path_complete_120d",
                "filter_path_label",
                *BAD_ITEMS,
            },
            "feature_panel_required_columns",
            feature_path,
        )
        _require_columns(
            rows,
            outcome,
            {
                "split",
                "event_scope",
                "event_stage",
                "family_group",
                "family_id",
                "outcome_anchor",
                "filter_policy",
                "delta_p_bad_vs_parent",
                "delta_p_good_vs_parent",
                "delta_p_good_minus_p_bad_vs_parent",
                "delta_big_winner_rate_vs_parent",
            },
            "outcome_summary_required_columns",
            outcome_path,
        )
        _add(
            rows,
            "event_scopes_complete",
            "lineage",
            set(events["event_scope"].dropna().unique()) >= EVENT_SCOPES,
            "error",
            f"missing event scopes: {sorted(EVENT_SCOPES - set(events['event_scope'].dropna().unique()))}",
            1,
            relpath(event_path),
        )
        _add(
            rows,
            "event_ids_unique",
            "schema",
            not events["family_signal_event_id"].duplicated().any(),
            "error",
            "family_signal_event_id not unique",
            int(events["family_signal_event_id"].duplicated().sum()),
            relpath(event_path),
        )
        _add(
            rows,
            "feature_ids_match_events",
            "lineage",
            set(features["family_signal_event_id"]) == set(events["family_signal_event_id"]),
            "error",
            "feature panel ids do not match event panel ids",
            abs(len(set(features["family_signal_event_id"])) - len(set(events["family_signal_event_id"]))),
            relpath(feature_path),
        )
        complete = features["bad_score_complete_flag"].astype(bool)
        calc_score = features.loc[complete, BAD_ITEMS].astype(bool).sum(axis=1)
        score_diff = calc_score.ne(features.loc[complete, "bad_score_v1"].astype(int))
        _add(
            rows,
            "bad_score_sum_consistent",
            "badscore",
            not bool(score_diff.any()),
            "error",
            "bad_score_v1 does not equal sum of 10 item flags",
            int(score_diff.sum()),
            relpath(feature_path),
        )
        incomplete = ~features["bad_score_complete_flag"].astype(bool)
        invalid_incomplete = features.loc[incomplete, "bad_score_v1"].notna() | features.loc[incomplete, "pass_primary_badshape_filter"].notna() | features.loc[incomplete, "drop_primary_badshape_filter"].notna()
        _add(
            rows,
            "bad_score_incomplete_null_policy",
            "badscore",
            not bool(invalid_incomplete.any()),
            "error",
            "incomplete BadScore rows must have null score/pass/drop",
            int(invalid_incomplete.sum()),
            relpath(feature_path),
        )
        core = window[window["is_shape_core_window_20d"].astype(bool)]
        expected_start = int(config["shape"].get("write_window_offsets", {}).get("start", -252))
        expected_end = int(config["shape"].get("write_window_offsets", {}).get("end", 131))
        _add(
            rows,
            "window_materialized_offset_range",
            "window",
            int(window["relative_offset"].min()) <= expected_start and int(window["relative_offset"].max()) >= expected_end,
            "error",
            f"window offsets must cover {expected_start}..{expected_end}",
            1,
            relpath(window_path),
        )
        _add(
            rows,
            "window_excludes_t0_from_core",
            "window",
            not bool(core["relative_offset"].eq(0).any()),
            "error",
            "relative_offset=0 appears in shape_core_window_20d",
            int(core["relative_offset"].eq(0).sum()),
            relpath(window_path),
        )
        complete_feature_ids = set(features.loc[features["shape_core_window_complete_flag"].astype(bool), "family_signal_event_id"])
        core_counts = core[core["family_signal_event_id"].isin(complete_feature_ids)].groupby("family_signal_event_id")["relative_offset"].nunique()
        bad_core_counts = core_counts[core_counts != 20]
        _add(
            rows,
            "complete_shape_core_has_20_bars",
            "window",
            bad_core_counts.empty,
            "error",
            "complete shape-core rows must have exactly 20 core offsets",
            len(bad_core_counts),
            relpath(window_path),
        )
        _add(
            rows,
            "component_definition_has_all_10_components",
            "schema",
            set(component_def["component_id"]) == {item.replace("bad_item_", "") for item in []} or len(component_def) == 10,
            "error",
            "component definition audit must contain 10 components",
            abs(len(component_def) - 10),
            relpath(component_def_path),
        )
        primary = config["primary_decision"]
        primary_rows = outcome[
            (outcome["event_scope"] == primary["event_scope"])
            & (outcome["event_stage"] == primary["event_stage"])
            & (outcome["family_group"] == primary["family_group"])
            & (outcome["family_id"] == "ALL")
            & (outcome["outcome_anchor"] == primary["outcome_anchor"])
            & (outcome["filter_policy"].isin([primary["parent_policy"], primary["filter_policy"]]))
            & (outcome["split"].isin(["validation", "robustness"]))
        ]
        _add(
            rows,
            "primary_parent_and_filter_rows_exist",
            "decision",
            len(primary_rows) == 4,
            "error",
            "primary validation/robustness parent and filter rows must exist",
            abs(len(primary_rows) - 4),
            relpath(outcome_path),
        )
        delta_cols = [
            "delta_p_bad_vs_parent",
            "delta_p_good_vs_parent",
            "delta_p_good_minus_p_bad_vs_parent",
            "delta_big_winner_rate_vs_parent",
        ]
        _add(
            rows,
            "outcome_delta_columns_split_not_single_delta",
            "schema",
            set(delta_cols).issubset(outcome.columns),
            "error",
            "outcome summary missing required split delta columns",
            1,
            relpath(outcome_path),
        )
        parent_rows = threshold[threshold["filter_policy"].eq(primary["parent_policy"])]
        _add(
            rows,
            "parent_policy_uses_baseline1",
            "denominator",
            parent_rows["denominator_policy"].eq("baseline_1").all() if not parent_rows.empty else False,
            "error",
            "parent policy denominator must be baseline_1",
            int((~parent_rows["denominator_policy"].eq("baseline_1")).sum()) if not parent_rows.empty else 1,
            relpath(threshold_path),
        )
        path_labels = set(panel["filter_path_label"].dropna().astype(str).unique())
        _add(
            rows,
            "filter_path_label_allowed_or_incomplete",
            "schema",
            path_labels <= (PATH_LABELS | {"invalid_or_incomplete"}),
            "error",
            f"unexpected filter path labels: {sorted(path_labels - (PATH_LABELS | {'invalid_or_incomplete'}))}",
            1,
            relpath(filter_path),
        )

    reports_dir.mkdir(parents=True, exist_ok=True)
    audit = pd.DataFrame(rows)
    audit.to_csv(audit_path, index=False)
    failed_checks = audit.loc[audit["status"].eq("failed") & audit["severity"].isin(["error", "fatal"]), "check_id"].tolist()
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
