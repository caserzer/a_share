#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
CODE_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", CODE_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from pipeline import (  # noqa: E402
    BuildInputs,
    build_active_listing_counts,
    build_all_outputs,
    build_candidate_panel,
    decision_from_gates,
    file_sha256,
    git_revision,
    load_metadata,
    load_sz_name_changes,
    load_trade_calendar,
    next_trade_date_map,
    write_csv,
    write_manifest,
    write_qlib_intervals,
    write_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the PIT top-N 400/100 universe from cached PIT inputs."
    )
    parser.add_argument(
        "--config",
        default=str(EXPERIMENT_ROOT / "config.yaml"),
        help="Experiment config YAML.",
    )
    parser.add_argument(
        "--mode",
        choices=["validate-config", "full"],
        default="full",
        help="Validate config or run the full offline universe build.",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping in {path}")
    return value


def topic_path(relative: str) -> Path:
    return (PROJECT_ROOT / relative).resolve()


def validate_config(config: dict[str, Any]) -> None:
    required = {
        "experiment",
        "date_range",
        "universe",
        "paths",
        "processed_outputs",
        "outputs",
        "validation",
    }
    missing = required.difference(config)
    if missing:
        raise ValueError(f"config missing sections: {sorted(missing)}")
    quotas = config["universe"]["quotas"]
    if quotas["main_board"] != 400 or quotas["chinext"] != 100:
        raise ValueError("top-N quotas must remain main_board=400 and chinext=100")
    if config["universe"]["candidate_panel_source"] != "full_board_candidate_panel":
        raise ValueError("candidate_panel_source must be full_board_candidate_panel")
    if config["universe"]["minimum_history_sessions"] != 240:
        raise ValueError("minimum_history_sessions must remain 240")


def build_paths(config: dict[str, Any]) -> tuple[dict[str, Path], dict[str, Path], dict[str, Path]]:
    input_keys = {
        "upstream_01_config_yaml",
        "upstream_01_run_manifest_json",
        "upstream_01_source_coverage_audit_csv",
        "upstream_01_market_cap_source_audit_csv",
        "upstream_01_daily_universe_counts_csv",
        "trading_calendar_csv",
        "instrument_metadata_csv",
        "sz_name_change_csv",
        "fixed_cap_membership_csv",
        "fixed_cap_executable_csv",
    }
    input_paths = {
        key: topic_path(config["paths"][key])
        for key in input_keys
        if key in config["paths"]
    }
    data_paths = {
        "raw_daily_dir": topic_path(config["paths"]["raw_daily_dir"]),
        "market_cap_dir": topic_path(config["paths"]["market_cap_dir"]),
        "status_dir": topic_path(config["paths"]["status_dir"]),
        "sh_name_history_dir": topic_path(config["paths"]["sh_name_history_dir"]),
        "processed_universe_dir": topic_path(config["paths"]["processed_universe_dir"]),
    }
    output_paths = {
        "processed_membership_daily": topic_path(
            config["processed_outputs"]["membership_daily_csv"]
        ),
        "processed_executable_daily": topic_path(
            config["processed_outputs"]["executable_daily_csv"]
        ),
        "processed_intervals": topic_path(config["processed_outputs"]["interval_csv"]),
        "processed_qlib_instruments": topic_path(
            config["processed_outputs"]["qlib_instrument_file"]
        ),
        "daily_universe_counts": topic_path(
            config["outputs"]["publishable_tables_dir"]
        )
        / "daily_universe_counts.csv",
        "board_bucket_counts": topic_path(config["outputs"]["publishable_tables_dir"])
        / "board_bucket_counts.csv",
        "yearly_universe_summary": topic_path(
            config["outputs"]["publishable_tables_dir"]
        )
        / "yearly_universe_summary.csv",
        "quota_fill_audit": topic_path(config["outputs"]["publishable_tables_dir"])
        / "quota_fill_audit.csv",
        "rank_cutoff_audit": topic_path(config["outputs"]["publishable_tables_dir"])
        / "rank_cutoff_audit.csv",
        "status_exclusion_audit": topic_path(
            config["outputs"]["publishable_tables_dir"]
        )
        / "status_exclusion_audit.csv",
        "history_coverage_audit": topic_path(
            config["outputs"]["publishable_tables_dir"]
        )
        / "history_coverage_audit.csv",
        "fixed_cap_overlap_audit": topic_path(
            config["outputs"]["publishable_tables_dir"]
        )
        / "fixed_cap_overlap_audit.csv",
        "topn_only_vs_fixed_cap_only_audit": topic_path(
            config["outputs"]["publishable_tables_dir"]
        )
        / "topn_only_vs_fixed_cap_only_audit.csv",
        "data_source_coverage_audit": topic_path(
            config["outputs"]["publishable_tables_dir"]
        )
        / "data_source_coverage_audit.csv",
        "report": topic_path(config["outputs"]["publishable_reports_dir"])
        / "pit_topn_400_100_universe_report.md",
        "run_manifest": topic_path(config["outputs"]["manifests_dir"])
        / "run_manifest.json",
    }
    return input_paths, data_paths, output_paths


def run_full(config: dict[str, Any], config_path: Path) -> int:
    input_paths, data_paths, output_paths = build_paths(config)
    for key, path in input_paths.items():
        if key != "sz_name_change_csv" and not path.exists():
            raise FileNotFoundError(f"missing required input {key}: {path}")

    calendar = load_trade_calendar(
        input_paths["trading_calendar_csv"],
        config["date_range"]["requested_start_date"],
        config["date_range"]["requested_end_date"],
    )
    next_trade_date = next_trade_date_map(calendar)
    metadata = load_metadata(input_paths["instrument_metadata_csv"])
    active_listing_counts = build_active_listing_counts(metadata, calendar)
    sz_changes = load_sz_name_changes(input_paths["sz_name_change_csv"])
    candidate, source_audit, source_gap_count, active_source_gap_count = build_candidate_panel(
        metadata=metadata,
        calendar=calendar,
        next_trade_date=next_trade_date,
        raw_daily_dir=data_paths["raw_daily_dir"],
        market_cap_dir=data_paths["market_cap_dir"],
        sh_name_history_dir=data_paths["sh_name_history_dir"],
        sz_changes_by_code=sz_changes,
        candidate_source=config["universe"]["candidate_panel_source"],
        membership_rule_version=config["universe"]["membership_rule_version"],
    )
    fixed_cap_membership = pd.read_csv(input_paths["fixed_cap_membership_csv"], dtype="string")
    build_inputs = BuildInputs(
        candidate=candidate,
        source_audit=source_audit,
        active_listing_counts=active_listing_counts,
        calendar=calendar,
        next_trade_date=next_trade_date,
        source_gap_count=source_gap_count,
        active_source_gap_count=active_source_gap_count,
    )
    result = build_all_outputs(
        build_inputs=build_inputs,
        fixed_cap_membership=fixed_cap_membership,
        quotas=config["universe"]["quotas"],
        minimum_history_sessions=config["universe"]["minimum_history_sessions"],
        rank_rule_version=config["universe"]["rank_rule_version"],
        validation=config["validation"],
    )
    decision = decision_from_gates(result.gate_summary)

    write_csv(result.membership, output_paths["processed_membership_daily"])
    write_csv(result.executable, output_paths["processed_executable_daily"])
    write_csv(result.intervals, output_paths["processed_intervals"])
    write_qlib_intervals(result.intervals, output_paths["processed_qlib_instruments"])
    write_csv(result.daily_counts, output_paths["daily_universe_counts"])
    write_csv(result.board_counts, output_paths["board_bucket_counts"])
    write_csv(result.yearly_summary, output_paths["yearly_universe_summary"])
    write_csv(result.quota_fill_audit, output_paths["quota_fill_audit"])
    write_csv(result.rank_cutoff_audit, output_paths["rank_cutoff_audit"])
    write_csv(result.status_exclusion_audit, output_paths["status_exclusion_audit"])
    write_csv(result.history_coverage_audit, output_paths["history_coverage_audit"])
    write_csv(result.fixed_cap_overlap_audit, output_paths["fixed_cap_overlap_audit"])
    write_csv(
        result.topn_only_vs_fixed_cap_only_audit,
        output_paths["topn_only_vs_fixed_cap_only_audit"],
    )
    write_csv(source_audit, output_paths["data_source_coverage_audit"])

    input_hashes = {
        key: file_sha256(path) if path.is_file() else None
        for key, path in input_paths.items()
    }
    upstream_manifest_hash = input_hashes.get("upstream_01_run_manifest_json")
    upstream_git_revision = None
    if input_paths["upstream_01_run_manifest_json"].is_file():
        try:
            upstream_manifest = json.loads(
                input_paths["upstream_01_run_manifest_json"].read_text(encoding="utf-8")
            )
            upstream_git_revision = upstream_manifest.get("git_revision")
        except (OSError, json.JSONDecodeError):
            upstream_git_revision = None
    write_report(
        path=output_paths["report"],
        decision=decision,
        result=result,
        source_audit=source_audit,
        input_hashes=input_hashes,
        upstream_manifest_hash=upstream_manifest_hash,
    )
    write_manifest(
        manifest_path=output_paths["run_manifest"],
        config_path=config_path,
        config=config,
        project_root=PROJECT_ROOT,
        decision=decision,
        input_paths=input_paths,
        output_paths=output_paths,
        upstream_01_manifest_hash=upstream_manifest_hash,
        upstream_01_git_revision=upstream_git_revision or git_revision(PROJECT_ROOT),
        gate_summary=result.gate_summary,
    )
    print(
        "decision="
        f"{decision} membership_rows={len(result.membership)} "
        f"active_source_gaps={active_source_gap_count}"
    )
    return 0 if decision == "topn_universe_supported" else 2


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_yaml(config_path)
    validate_config(config)
    if args.mode == "validate-config":
        print("config validation passed")
        return 0
    return run_full(config, config_path)


if __name__ == "__main__":
    raise SystemExit(main())
