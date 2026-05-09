#!/usr/bin/env python3
"""Validate EP2 Requirement 01 label and baseline freeze contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PRIMARY_LABEL_ID = "confirm_h10_u10_d06_conservative_fail"
REJECTED_ORIGINAL_LABEL_ID = "confirm_h10_u12_d06_conservative_fail"
FROZEN_BASELINE_ID = "probe_with_simple_stop"
EXPECTED_CONFIG_HASH = "02c64d1c90fb2344247f732e7935738bae17542f67442db3758ddcc0f4c6f492"
EXPECTED_LAUNCH_DETECTOR_CONFIG_HASH = "ecf4d97efb4239181765a50b1fd161af4b93d7f5e298cbce5bb276aeda4e10d0"
EXPECTED_POOL_ROWS = 5605
EXPECTED_EPISODE_COUNT = 2464
EXPECTED_FREEZE_CANDIDATE_COUNT = 30


@dataclass(frozen=True)
class Paths:
    project_root: Path
    baseline_root: Path
    output_root: Path

    @property
    def baseline_outputs(self) -> Path:
        return self.baseline_root / "outputs"

    @property
    def cache_dir(self) -> Path:
        return self.baseline_outputs / "cache"

    @property
    def reports_dir(self) -> Path:
        return self.baseline_outputs / "reports"

    @property
    def manifests_dir(self) -> Path:
        return self.baseline_outputs / "manifests"

    @property
    def output_reports_dir(self) -> Path:
        return self.output_root / "reports"

    @property
    def output_manifests_dir(self) -> Path:
        return self.output_root / "manifests"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate EP2 Requirement 01 freeze contract.")
    parser.add_argument("--project-root", default=".", help="Project root for topics/01_askhare_qlib.")
    parser.add_argument(
        "--baseline-root",
        default="ep2/engineering_baseline",
        help="EP2 engineering baseline root relative to project root.",
    )
    parser.add_argument(
        "--output-root",
        default="ep2/outputs/requirement_01_label_and_baseline_freeze",
        help="Requirement 01 output root relative to project root.",
    )
    return parser.parse_args()


def stable_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def gate_row(gate_name: str, passed: bool, observed: Any, expected: Any, detail: str = "") -> dict[str, Any]:
    return {
        "gate_name": gate_name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
        "detail": detail,
    }


def load_inputs(paths: Paths) -> dict[str, Any]:
    return {
        "config": yaml.safe_load((paths.baseline_root / "config.yaml").read_text(encoding="utf-8")),
        "engineering_manifest": read_json(paths.manifests_dir / "ep2_engineering_baseline_manifest.json"),
        "pool_manifest": read_json(paths.manifests_dir / "ep2_pool_freeze_manifest.json"),
        "authority": pd.read_csv(paths.reports_dir / "ep2_required_artifact_authority.csv"),
        "pit_audit": pd.read_csv(paths.reports_dir / "ep2_pit_input_audit.csv"),
        "feature_audit": pd.read_csv(paths.reports_dir / "ep2_feature_asof_audit.csv"),
        "threshold_audit": pd.read_csv(paths.reports_dir / "ep2_threshold_config_consistency_audit.csv"),
        "label_freeze": pd.read_csv(paths.reports_dir / "ep2_label_freeze_candidate.csv"),
        "label_sweep": pd.read_csv(paths.reports_dir / "ep2_label_sweep_grid.csv"),
        "baseline_results": pd.read_csv(paths.reports_dir / "ep2_no_model_baseline_results.csv"),
        "baseline_gates": pd.read_csv(paths.reports_dir / "ep2_no_model_baseline_gate.csv"),
    }


def validate_authority(paths: Paths, data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gates: list[dict[str, Any]] = []
    authority_rows: list[dict[str, Any]] = []
    authority = data["authority"]

    missing = []
    for row in authority.itertuples(index=False):
        artifact_path = paths.project_root / str(row.artifact_path)
        exists = artifact_path.exists()
        missing.append(not exists)
        authority_rows.append(
            {
                "artifact_name": row.artifact_name,
                "artifact_path": row.artifact_path,
                "required_for_requirement": bool(row.required_for_requirement),
                "exists": exists,
                "recorded_content_hash": row.content_hash,
                "current_content_hash": stable_file_hash(artifact_path) if exists and artifact_path.is_file() else "",
            }
        )

    gates.append(gate_row("required_artifacts_exist", not any(missing), int((~pd.Series(missing)).sum()), len(authority)))
    return gates, authority_rows


def validate_manifest_and_audits(paths: Paths, data: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = data["engineering_manifest"]
    pool_manifest = data["pool_manifest"]
    pit = data["pit_audit"]
    feature = data["feature_audit"]
    threshold = data["threshold_audit"]

    gates = [
        gate_row("engineering_manifest_passed", manifest.get("validation_status") == "passed", manifest.get("validation_status"), "passed"),
        gate_row(
            "engineering_manifest_artifact_count",
            manifest.get("required_artifact_count") == manifest.get("existing_required_artifact_count") == 20,
            f"{manifest.get('existing_required_artifact_count')}/{manifest.get('required_artifact_count')}",
            "20/20",
        ),
        gate_row("config_hash_frozen", manifest.get("config_hash") == EXPECTED_CONFIG_HASH, manifest.get("config_hash"), EXPECTED_CONFIG_HASH),
        gate_row(
            "launch_detector_config_hash_frozen",
            manifest.get("launch_detector_config_hash") == EXPECTED_LAUNCH_DETECTOR_CONFIG_HASH,
            manifest.get("launch_detector_config_hash"),
            EXPECTED_LAUNCH_DETECTOR_CONFIG_HASH,
        ),
        gate_row("pool_row_count_frozen", pool_manifest.get("row_count") == EXPECTED_POOL_ROWS, pool_manifest.get("row_count"), EXPECTED_POOL_ROWS),
        gate_row(
            "episode_count_frozen",
            pool_manifest.get("episode_count") == EXPECTED_EPISODE_COUNT,
            pool_manifest.get("episode_count"),
            EXPECTED_EPISODE_COUNT,
        ),
        gate_row("pit_inputs_pass", bool(pit[["exists", "date_coverage_pass", "instrument_join_pass"]].astype(bool).all().all()), "all", "all true"),
        gate_row(
            "feature_asof_pass",
            (not feature["uses_execution_date_intraday"].astype(bool).any()) and int(feature["violation_count"].sum()) == 0,
            f"uses_execution_date_intraday_any={feature['uses_execution_date_intraday'].astype(bool).any()}, violations={int(feature['violation_count'].sum())}",
            "false, 0",
        ),
        gate_row("threshold_config_consistent", bool(threshold["is_consistent"].astype(bool).all()), "all", "all true"),
    ]
    gates.extend(validate_authority(paths, data)[0])
    return gates


def parse_label_id(label_id: str) -> dict[str, Any]:
    # Expected shape: confirm_h10_u10_d06_conservative_fail
    parts = label_id.split("_")
    return {
        "horizon": int(parts[1][1:]),
        "upside": int(parts[2][1:]) / 100.0,
        "drawdown": int(parts[3][1:]) / 100.0,
        "same_day_policy": "_".join(parts[4:]),
    }


def validate_label_freeze(data: dict[str, Any]) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    config = data["config"]
    freeze = data["label_freeze"].copy()
    sweep = data["label_sweep"].copy()
    parsed = pd.DataFrame([parse_label_id(label_id) for label_id in sweep["label_id"]])
    sweep = pd.concat([sweep.drop(columns=[c for c in parsed.columns if c in sweep.columns], errors="ignore"), parsed], axis=1)
    labels = freeze.merge(sweep, on="label_id", how="left", suffixes=("_freeze", ""))

    primary_h = int(config["schedule_defaults"]["primary_H"])
    primary_drawdown = float(config["schedule_defaults"]["canonical_fast_fail_drawdown"])
    candidates = labels.loc[
        labels["frozen_for_ep2_2"].astype(bool)
        & labels["same_day_policy"].eq("conservative_fail")
        & labels["horizon"].eq(primary_h)
        & labels["drawdown"].round(8).eq(round(primary_drawdown, 8))
        & labels["candidate_positive_rate"].ge(0.20)
        & labels["episode_any_positive_rate"].le(0.50)
    ].sort_values(["upside", "label_id"])

    selected_label = candidates["label_id"].iloc[0] if not candidates.empty else ""
    primary_row = labels.loc[labels["label_id"].eq(PRIMARY_LABEL_ID)]
    rejected_row = labels.loc[labels["label_id"].eq(REJECTED_ORIGINAL_LABEL_ID)]
    sensitivity_count = int(freeze["frozen_for_ep2_2"].astype(bool).sum())

    gates = [
        gate_row("primary_label_tie_breaker_selects_frozen_label", selected_label == PRIMARY_LABEL_ID, selected_label, PRIMARY_LABEL_ID),
        gate_row("primary_label_exists", not primary_row.empty, len(primary_row), 1),
        gate_row(
            "primary_label_all_freeze_gates_pass",
            bool(
                not primary_row.empty
                and primary_row[
                    [
                        "passed_candidate_base_rate_gate",
                        "passed_episode_base_rate_gate",
                        "passed_ambiguity_gate",
                        "passed_concentration_gate",
                        "frozen_for_ep2_2",
                    ]
                ]
                .astype(bool)
                .all(axis=None)
            ),
            "all true" if not primary_row.empty else "missing",
            "all true",
        ),
        gate_row("sensitivity_label_count_frozen", sensitivity_count == EXPECTED_FREEZE_CANDIDATE_COUNT, sensitivity_count, EXPECTED_FREEZE_CANDIDATE_COUNT),
        gate_row(
            "original_10d_12pct_6pct_candidate_rejected",
            bool(
                not rejected_row.empty
                and not bool(rejected_row["frozen_for_ep2_2"].iloc[0])
                and "candidate_base_rate_out_of_range" in str(rejected_row["selection_reason"].iloc[0])
            ),
            rejected_row["selection_reason"].iloc[0] if not rejected_row.empty else "missing",
            "candidate_base_rate_out_of_range and frozen_for_ep2_2=false",
        ),
    ]

    audit_columns = [
        "label_id",
        "selection_scope",
        "selection_reason",
        "frozen_for_ep2_2",
        "horizon",
        "upside",
        "drawdown",
        "same_day_policy",
        "candidate_positive_rate",
        "episode_any_positive_rate",
        "episode_first_valid_positive_rate",
        "episode_weighted_positive_rate",
        "top1_instrument_year_positive_share",
        "same_day_ambiguity_rate",
    ]
    audit = labels.loc[labels["label_id"].isin([PRIMARY_LABEL_ID, REJECTED_ORIGINAL_LABEL_ID]) | labels["frozen_for_ep2_2"].astype(bool), audit_columns]
    return gates, audit.sort_values(["frozen_for_ep2_2", "label_id"], ascending=[False, True])


def validate_baseline_freeze(data: dict[str, Any]) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    results = data["baseline_results"].copy()
    gates = data["baseline_gates"].copy()
    pass_by_schedule = gates.groupby("schedule_id")["passed"].apply(lambda series: bool(series.astype(bool).all())).sort_index()
    all_pass_schedules = pass_by_schedule[pass_by_schedule].index.tolist()
    baseline_row = results.loc[results["schedule_id"].eq(FROZEN_BASELINE_ID)]
    frozen_gates = gates.loc[gates["schedule_id"].eq(FROZEN_BASELINE_ID)]

    random_diff_row = frozen_gates.loc[frozen_gates["gate_name"].eq("after_cost_lift_vs_random")]
    random_diff_value = float(random_diff_row["gate_value"].iloc[0]) if not random_diff_row.empty else float("nan")

    gate_rows = [
        gate_row("only_probe_with_simple_stop_passes_all_gates", all_pass_schedules == [FROZEN_BASELINE_ID], ";".join(all_pass_schedules), FROZEN_BASELINE_ID),
        gate_row("frozen_baseline_result_exists", not baseline_row.empty, len(baseline_row), 1),
        gate_row("frozen_baseline_gate_count", len(frozen_gates) == 8, len(frozen_gates), 8),
        gate_row("frozen_baseline_all_gates_pass", bool(not frozen_gates.empty and frozen_gates["passed"].astype(bool).all()), "all true", "all true"),
        gate_row(
            "random_gate_interpreted_as_mean_diff",
            random_diff_value > 0,
            random_diff_value,
            "> 0 mean_after_cost_diff_vs_random",
            "source gate_name remains after_cost_lift_vs_random for backward compatibility",
        ),
    ]

    comparison_fields = [
        "schedule_id",
        "episode_with_any_exposure_count",
        "probe_rate",
        "fast_fail_exit_rate",
        "mean_after_cost_return",
        "median_after_cost_return",
        "big_winner_capture_rate",
        "missed_gain_to_exposure_median",
        "turnover_proxy",
        "top1_instrument_year_exposure_share",
        "top5_instrument_exposure_share",
    ]
    baseline_audit = results[comparison_fields].merge(
        pass_by_schedule.rename("all_gates_passed").reset_index(),
        on="schedule_id",
        how="left",
    )
    return gate_rows, baseline_audit


def build_summary(gates: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(gates)
    passed = bool(df["passed"].all()) if not df.empty else False
    return pd.DataFrame(
        [
            {
                "requirement_id": "requirement_01_label_and_baseline_freeze",
                "validation_status": "passed" if passed else "failed",
                "gate_count": len(df),
                "passed_gate_count": int(df["passed"].sum()) if not df.empty else 0,
                "failed_gate_count": int((~df["passed"]).sum()) if not df.empty else 0,
                "primary_label_id": PRIMARY_LABEL_ID,
                "frozen_baseline_id": FROZEN_BASELINE_ID,
            }
        ]
    )


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    paths = Paths(
        project_root=project_root,
        baseline_root=(project_root / args.baseline_root).resolve(),
        output_root=(project_root / args.output_root).resolve(),
    )
    paths.output_reports_dir.mkdir(parents=True, exist_ok=True)
    paths.output_manifests_dir.mkdir(parents=True, exist_ok=True)

    data = load_inputs(paths)

    gates: list[dict[str, Any]] = []
    gates.extend(validate_manifest_and_audits(paths, data))
    _, authority_rows = validate_authority(paths, data)
    label_gates, label_audit = validate_label_freeze(data)
    baseline_gates, baseline_audit = validate_baseline_freeze(data)
    gates.extend(label_gates)
    gates.extend(baseline_gates)

    gate_audit = pd.DataFrame(gates)
    summary = build_summary(gates)

    write_csv(gate_audit, paths.output_reports_dir / "requirement_01_gate_audit.csv")
    write_csv(summary, paths.output_reports_dir / "requirement_01_freeze_summary.csv")
    write_csv(pd.DataFrame(authority_rows), paths.output_reports_dir / "requirement_01_artifact_authority_check.csv")
    write_csv(label_audit, paths.output_reports_dir / "requirement_01_primary_label_audit.csv")
    write_csv(baseline_audit, paths.output_reports_dir / "requirement_01_baseline_freeze_audit.csv")

    manifest = {
        "requirement_id": "requirement_01_label_and_baseline_freeze",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_status": summary["validation_status"].iloc[0],
        "primary_label_id": PRIMARY_LABEL_ID,
        "frozen_baseline_id": FROZEN_BASELINE_ID,
        "source_engineering_manifest": str((paths.manifests_dir / "ep2_engineering_baseline_manifest.json").relative_to(paths.project_root)),
        "source_config_hash": data["engineering_manifest"].get("config_hash"),
        "source_launch_detector_config_hash": data["engineering_manifest"].get("launch_detector_config_hash"),
        "output_reports": sorted(path.name for path in paths.output_reports_dir.glob("*.csv")),
    }
    write_json(manifest, paths.output_manifests_dir / "requirement_01_freeze_manifest.json")

    if summary["validation_status"].iloc[0] != "passed":
        failed = gate_audit.loc[~gate_audit["passed"].astype(bool), ["gate_name", "observed", "expected", "detail"]]
        raise SystemExit("Requirement 01 freeze validation failed:\n" + failed.to_string(index=False))

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
