#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from afml_big_winner.config import stable_hash
from afml_big_winner.manifest import git_revision

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
CODE_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", CODE_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from pipeline import (  # noqa: E402
    TopNReverseLifecycleBlocked,
    add_denominator_context,
    build_baseline_comparison,
    build_denominator_outputs,
    build_replay_config,
    build_rule_invariant_audit,
    collect_output_paths,
    invariant_audit_passed,
    load_02_runner,
    load_json,
    load_topn_denominator,
    patch_02_runner_for_topn,
    topic_path,
    topn_decision_from_semantic,
    validate_topn_inputs,
    write_csv,
    write_report,
    write_topn_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rerun 02 reverse lifecycle on the PIT Top-N 400/100 universe."
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
        help="Validate config or run the full experiment.",
    )
    parser.add_argument(
        "--max-instruments",
        type=int,
        default=None,
        help="Optional smoke-run cap. Full publishable runs should omit this.",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping in {path}")
    return value


def validate_config(config: dict[str, Any], project_root: Path) -> None:
    required = {
        "experiment",
        "upstream",
        "paths",
        "upstream_02_publishable_tables",
        "outputs",
        "episode_extraction",
        "splits",
        "alignment",
        "matching",
        "dominance",
        "industry",
    }
    missing = required.difference(config)
    if missing:
        raise ValueError(f"config missing sections: {sorted(missing)}")
    for key in [
        "executable_universe_csv",
        "membership_universe_csv",
        "benchmark_daily_csv",
        "upstream_02_run_manifest_json",
        "upstream_05_run_manifest_json",
        "upstream_05_data_source_coverage_audit_csv",
    ]:
        path = topic_path(project_root, config["paths"][key])
        if not path.exists():
            raise FileNotFoundError(f"missing config path {key}: {path}")
    for key, value in config["upstream_02_publishable_tables"].items():
        path = topic_path(project_root, value)
        if not path.is_file():
            raise FileNotFoundError(f"missing 02 comparison table {key}: {path}")
    if int(config["episode_extraction"]["prior_lookback_sessions"]) != 250:
        raise ValueError("06 must preserve the 02 250-session lookback")
    if int(config["episode_extraction"]["forward_horizon_sessions"]) != 120:
        raise ValueError("06 must preserve the 02 120-session forward horizon")
    if float(config["episode_extraction"]["big_winner_mfe_threshold"]) != 0.50:
        raise ValueError("06 must preserve the 02 +50% MFE threshold")


def run_pipeline(
    config: dict[str, Any], *, config_path: Path, max_instruments: int | None = None
) -> dict[str, Any]:
    validate_config(config, PROJECT_ROOT)
    legacy_runner = load_02_runner(PROJECT_ROOT)
    topn_status = validate_topn_inputs(config, PROJECT_ROOT)
    patch_02_runner_for_topn(legacy_runner)

    replay_config = build_replay_config(config)
    old_pipeline = sys.modules.get("pipeline")
    sys.modules["pipeline"] = legacy_runner._pipeline_module
    try:
        replay_result = legacy_runner.run_pipeline(
            replay_config, config_path=config_path, max_instruments=max_instruments
        )
    finally:
        if old_pipeline is None:
            sys.modules.pop("pipeline", None)
        else:
            sys.modules["pipeline"] = old_pipeline
    replay_manifest_path = topic_path(PROJECT_ROOT, config["outputs"]["manifests_dir"]) / (
        "run_manifest.json"
    )
    replay_manifest = load_json(replay_manifest_path)
    semantic_decision = str(replay_manifest.get("decision", replay_result["decision"]))
    gate_summary = dict(replay_manifest.get("gate_summary", {}))

    table_dir = topic_path(PROJECT_ROOT, config["outputs"]["publishable_tables_dir"])
    topn_winners_path = table_dir / "topn_big_winner_episode_reference_summary.csv"
    topn_match_stats_path = table_dir / "topn_winner_vs_matched_control_stats.csv"
    topn_winners = pd.read_csv(topn_winners_path) if topn_winners_path.is_file() else pd.DataFrame()
    topn_match_stats = (
        pd.read_csv(topn_match_stats_path)
        if topn_match_stats_path.is_file()
        else pd.DataFrame()
    )

    denominator = load_topn_denominator(
        config, PROJECT_ROOT, topn_status=topn_status
    )
    denominator, split_config = add_denominator_context(
        denominator, config, PROJECT_ROOT, legacy_runner
    )
    denominator_outputs = build_denominator_outputs(denominator, topn_winners)
    write_denominator_outputs(denominator_outputs, table_dir)

    upstream_02_config = load_yaml(topic_path(PROJECT_ROOT, config["paths"]["upstream_02_config_yaml"]))
    invariant_audit = build_rule_invariant_audit(config, upstream_02_config, topn_status)
    invariant_path = table_dir / "topn_02_rule_invariant_audit.csv"
    write_csv(invariant_audit, invariant_path)
    invariant_ok = invariant_audit_passed(invariant_audit)

    topn_decision = topn_decision_from_semantic(semantic_decision, invariant_ok)
    if not invariant_ok:
        gate_summary.setdefault("blocked_reasons", [])
        if "02_rule_invariant_replay_failed" not in gate_summary["blocked_reasons"]:
            gate_summary["blocked_reasons"].append("02_rule_invariant_replay_failed")

    gate_summary.update(
        {
            "decision": topn_decision,
            "semantic_02_decision": semantic_decision,
            "universe_precision_status": topn_status.universe_precision_status,
            "topn_universe_input_accepted": topn_status.topn_universe_input_accepted,
            "exact_topn_supported": topn_status.exact_topn_supported,
            "topn_candidate_gap_accepted": topn_status.topn_candidate_gap_accepted,
            "active_source_gap_count": topn_status.active_source_gap_count,
            "source_gap_count": topn_status.source_gap_count,
            "missing_active_source_instrument_count": topn_status.missing_active_source_instrument_count,
            "missing_active_source_audit_count_reconciled": topn_status.missing_active_source_audit_count_reconciled,
            "inherited_02_rule_invariant_status": "pass"
            if invariant_ok
            else "blocked",
            "raw_topn_instrument_days": int(
                denominator_outputs["topn_denominator_summary"].iloc[0][
                    "raw_topn_instrument_days"
                ]
            ),
            "evaluated_instrument_days": int(
                denominator_outputs["topn_denominator_summary"].iloc[0][
                    "evaluated_instrument_days"
                ]
            ),
            "instrument_days": int(
                denominator_outputs["topn_denominator_summary"].iloc[0][
                    "instrument_days"
                ]
            ),
            "universe_years_252": float(
                denominator_outputs["topn_denominator_summary"].iloc[0][
                    "universe_years_252"
                ]
            ),
            "episodes_per_100_universe_years": float(
                denominator_outputs["topn_denominator_summary"].iloc[0][
                    "episodes_per_100_universe_years"
                ]
            ),
        }
    )

    topn_data_source_audit = pd.read_csv(
        topic_path(
            PROJECT_ROOT, config["paths"]["upstream_05_data_source_coverage_audit_csv"]
        )
    )
    write_csv(topn_data_source_audit, table_dir / "topn_data_source_coverage_audit.csv")

    baseline_comparison = build_baseline_comparison(
        config,
        PROJECT_ROOT,
        topn_winners,
        topn_match_stats,
        denominator_outputs["topn_denominator_summary"],
        topn_decision,
    )
    write_csv(
        baseline_comparison,
        table_dir / "topn_vs_fixed_cap_episode_rate_comparison.csv",
    )

    report_path = write_report(
        config=config,
        project_root=PROJECT_ROOT,
        topn_status=topn_status,
        decision=topn_decision,
        semantic_02_decision=semantic_decision,
        gate_summary=gate_summary,
        denominator_summary=denominator_outputs["topn_denominator_summary"],
        episode_summary=denominator_outputs["topn_episode_count_summary"],
        baseline_comparison=baseline_comparison,
        invariant_audit=invariant_audit,
    )

    output_paths = collect_output_paths(config, PROJECT_ROOT)
    output_paths["publishable.reports.topn_reverse_lifecycle_profile_report"] = report_path
    manifest_path = write_topn_manifest(
        config=config,
        config_path=config_path,
        project_root=PROJECT_ROOT,
        topn_status=topn_status,
        topn_decision=topn_decision,
        semantic_02_decision=semantic_decision,
        gate_summary=gate_summary,
        split_config=split_config,
        output_paths=output_paths,
    )
    return {
        "decision": topn_decision,
        "manifest_path": str(manifest_path),
        "report_path": str(report_path),
    }


def write_denominator_outputs(outputs: dict[str, pd.DataFrame], table_dir: Path) -> None:
    name_to_file = {
        "topn_denominator_summary": "topn_denominator_summary.csv",
        "topn_yearly_denominator_summary": "topn_yearly_denominator_summary.csv",
        "topn_split_denominator_summary": "topn_split_denominator_summary.csv",
        "topn_episode_count_summary": "topn_episode_count_summary.csv",
        "topn_episode_rate_by_year": "topn_episode_rate_by_year.csv",
        "topn_episode_rate_by_split": "topn_episode_rate_by_split.csv",
        "topn_episode_rate_by_board": "topn_episode_rate_by_board.csv",
        "topn_episode_rate_by_regime": "topn_episode_rate_by_regime.csv",
    }
    for key, filename in name_to_file.items():
        if key in outputs:
            write_csv(outputs[key], table_dir / filename)


def write_blocked_artifacts(
    config: dict[str, Any],
    config_path: Path,
    exc: TopNReverseLifecycleBlocked,
) -> dict[str, Any]:
    report_dir = topic_path(PROJECT_ROOT, config["outputs"]["publishable_reports_dir"])
    manifest_dir = topic_path(PROJECT_ROOT, config["outputs"]["manifests_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "topn_reverse_lifecycle_profile_report.md"
    manifest_path = manifest_dir / "run_manifest.json"
    report_path.write_text(
        "\n".join(
            [
                "# PIT Top-N Reverse Lifecycle Profile Report",
                "",
                f"Final decision: `{exc.decision}`",
                "",
                f"Blocked reason: {exc}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest = {
        "experiment_name": config.get("experiment", {}).get("name", ""),
        "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        "source_git_revision": git_revision(PROJECT_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "decision": exc.decision,
        "gate_summary": {"blocked_reasons": [str(exc)]},
        "output_paths": {
            "publishable.reports.topn_reverse_lifecycle_profile_report": str(report_path)
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return {
        "decision": exc.decision,
        "manifest_path": str(manifest_path),
        "report_path": str(report_path),
    }


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_yaml(config_path)
    if args.mode == "validate-config":
        validate_config(config, PROJECT_ROOT)
        validate_topn_inputs(config, PROJECT_ROOT)
        print("config_valid=true")
        return 0
    try:
        result = run_pipeline(
            config, config_path=config_path, max_instruments=args.max_instruments
        )
    except TopNReverseLifecycleBlocked as exc:
        result = write_blocked_artifacts(config, config_path, exc)
    print(f"decision={result['decision']}")
    print(f"manifest={result['manifest_path']}")
    print(f"report={result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
