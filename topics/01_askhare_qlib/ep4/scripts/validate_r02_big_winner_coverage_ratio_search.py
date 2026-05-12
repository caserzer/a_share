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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r02_big_winner_coverage_ratio_search_v1.yaml"
REQUIRED_CACHE = [
    "r02_big_winner_reference_events.parquet",
    "r02_winner_t0_t30_profile_panel.parquet",
    "r02_eligible_day_density_panel.parquet",
]
REQUIRED_REPORTS = [
    "r02_big_winner_coverage_atomic_condition_dictionary.csv",
    "r02_big_winner_coverage_candidate_dictionary.csv",
    "r02_big_winner_coverage_all.csv",
    "r02_big_winner_coverage_ge85.csv",
    "r02_big_winner_coverage_top_by_family.csv",
    "r02_big_winner_coverage_lowest_density_ge85.csv",
    "r02_big_winner_coverage_rejected.csv",
    "r02_big_winner_coverage_uncovered_events.csv",
    "r02_big_winner_coverage_market_context_decomposition.csv",
    "r02_big_winner_coverage_final_report.md",
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
    manifest_path = manifests_dir / "r02_big_winner_coverage_manifest.json"
    rows: list[dict[str, Any]] = []

    for name in REQUIRED_CACHE:
        _check((cache_dir / name).exists(), f"cache_exists_{name}", relpath(cache_dir / name), rows)
    for name in REQUIRED_REPORTS:
        _check((reports_dir / name).exists(), f"report_exists_{name}", relpath(reports_dir / name), rows)
    _check(manifest_path.exists(), "manifest_exists", relpath(manifest_path), rows)
    if not manifest_path.exists():
        result = {"validation_status": "failed", "failed_checks": ["manifest_exists"]}
        write_json(result, manifests_dir / "r02_big_winner_coverage_validation.json")
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _check(manifest.get("reference_event_count") == 845, "reference_event_count_845", str(manifest.get("reference_event_count")), rows)
    _check(manifest.get("parallel_enabled") is True, "parallel_enabled_true", str(manifest.get("parallel_enabled")), rows)
    _check(manifest.get("configured_max_workers") == 12, "configured_max_workers_12", str(manifest.get("configured_max_workers")), rows)
    _check(manifest.get("deterministic_merge") is True, "deterministic_merge_true", str(manifest.get("deterministic_merge")), rows)
    _check(manifest.get("failed_chunk_count") == 0, "failed_chunk_count_zero", str(manifest.get("failed_chunk_count")), rows)
    _check(manifest.get("parallel_result_hash") == manifest.get("single_pass_audit_hash"), "parallel_hash_matches_single_pass", str(manifest.get("parallel_result_hash")), rows)
    _check(manifest.get("full_sample_descriptive_only") is True, "full_sample_descriptive_only", str(manifest.get("full_sample_descriptive_only")), rows)
    _check(manifest.get("uses_market_context_filter") is False, "no_market_context_filter", str(manifest.get("uses_market_context_filter")), rows)

    atomic = pd.read_csv(reports_dir / "r02_big_winner_coverage_atomic_condition_dictionary.csv")
    candidates = pd.read_csv(reports_dir / "r02_big_winner_coverage_candidate_dictionary.csv")
    all_results = pd.read_csv(reports_dir / "r02_big_winner_coverage_all.csv")
    ge85 = pd.read_csv(reports_dir / "r02_big_winner_coverage_ge85.csv")
    reference = pd.read_parquet(cache_dir / "r02_big_winner_reference_events.parquet")
    profile = pd.read_parquet(cache_dir / "r02_winner_t0_t30_profile_panel.parquet")
    density = pd.read_parquet(cache_dir / "r02_eligible_day_density_panel.parquet")

    allowed_windows = set(int(v) for v in config["search"]["allowed_windows"])
    _check(set(atomic["window"].astype(int)).issubset(allowed_windows), "atomic_windows_allowed", str(sorted(atomic["window"].unique().tolist())), rows)
    _check(atomic["formula_hash"].notna().all(), "atomic_formula_hash_present", str(len(atomic)), rows)
    _check(set(candidates["n_terms"].astype(int)).issubset({3, 4}), "candidate_terms_3_or_4", str(sorted(candidates["n_terms"].unique().tolist())), rows)
    _check(candidates["uses_market_context_filter"].astype(str).str.lower().isin(["false", "0"]).all(), "candidate_no_market_context_filter", "", rows)
    family_ok = True
    atomic_family = atomic.set_index("atomic_condition_id")["family_id"].to_dict()
    for row in candidates.itertuples(index=False):
        families = {atomic_family.get(atom_id) for atom_id in str(row.atomic_condition_ids).split("|")}
        if len(families) != 1 or None in families:
            family_ok = False
            break
    _check(family_ok, "candidate_single_family_only", "", rows)
    _check(len(all_results) == len(candidates), "all_results_matches_candidate_count", f"{len(all_results)} vs {len(candidates)}", rows)
    _check(set(candidates["condition_group_id"]).issubset(set(all_results["condition_group_id"])), "every_candidate_has_result", "", rows)
    _check((ge85["coverage_t0_t30"] >= float(config["coverage"]["min_coverage_t0_t30"])).all() if not ge85.empty else True, "ge85_only_ge85", str(len(ge85)), rows)
    _check(len(reference) == 845, "reference_cache_count_845", str(len(reference)), rows)
    _check(profile["offset_day"].between(0, 30).all(), "profile_offset_t0_t30", str(profile["offset_day"].min()) + ":" + str(profile["offset_day"].max()), rows)
    _check("is_r01_pit_executable_eligible" in density.columns, "density_panel_has_eligibility", "", rows)

    report_text = (reports_dir / "r02_big_winner_coverage_final_report.md").read_text(encoding="utf-8")
    forbidden = ["go_to_r03", "R03-ready", "holdout-validated"]
    _check(not any(term in report_text for term in forbidden), "report_no_promotion_language", "", rows)
    _check("not holdout validation" in report_text or "不是 holdout validation" in report_text, "report_states_not_holdout", "", rows)

    audit = pd.DataFrame(rows)
    audit_path = reports_dir / "r02_big_winner_coverage_validation_audit.csv"
    audit.to_csv(audit_path, index=False)
    failed = audit.loc[audit["status"].eq("failed"), "check_id"].tolist()
    result = {
        "validation_status": "passed" if not failed else "failed",
        "failed_checks": failed,
        "audit_path": relpath(audit_path),
    }
    write_json(result, manifests_dir / "r02_big_winner_coverage_validation.json")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate EP4 R02 big-winner coverage ratio search artifacts.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    result = validate(Path(args.config))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
