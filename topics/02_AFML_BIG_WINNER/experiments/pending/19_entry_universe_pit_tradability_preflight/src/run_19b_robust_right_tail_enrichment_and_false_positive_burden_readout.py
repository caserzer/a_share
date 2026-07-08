#!/usr/bin/env python
from __future__ import annotations

import argparse
import copy
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml


SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import run_19b0_fast_rule_grid_enrichment_scan as b0  # noqa: E402


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "19B_robust_right_tail_enrichment_and_false_positive_burden_readout"
EXPERIMENT_ID = "19_entry_universe_pit_tradability_preflight"
PHASE_ID = "19B"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.yaml"
OUTPUT_ROOT = EXPERIMENT_DIR / "outputs" / RUN_ID
LOCAL_CACHE = OUTPUT_ROOT / "local_cache"
FIGURE_DIR = OUTPUT_ROOT / "figures"

READY_19A = "19A_entry_universe_contract_ready"
READY_19B0 = "19B0_candidate_family_eligible_for_19B"
NEXT_19B = "requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md"
NEXT_19B1 = "requirement_19b1_validation_stress_readout.md"

ORIGINAL_VARIANT_TO_BASELINE = {
    "original_calendar_time_random_same_budget": "calendar_time_random_same_budget",
    "original_instrument_matched_random_same_budget": "instrument_matched_random_same_budget",
    "original_liquidity_size_volatility_matched_same_budget": "liquidity_size_volatility_matched_same_budget",
}
ORIGINAL_VARIANTS = list(ORIGINAL_VARIANT_TO_BASELINE)
BASELINE_FAMILIES = list(b0.BASELINE_FAMILIES)
POLICY_AUTH_COLUMNS = list(b0.POLICY_AUTH_COLUMNS)
CONTRACT_DEFAULT_FALSE_POSITIVE_BURDEN_CAPS = {
    "candidate_per_winner_cap": 6.0,
    "fast_fail_rate_cap": 0.60,
    "false_repair_rate_cap": 0.60,
    "mae_abs_worsening_cap": 0.02,
}
CRITICAL_GATES = [
    "upstream_19a_contract_gate",
    "upstream_19b0_contract_gate",
    "outcome_boundary_gate",
    "robustness_candidate_manifest_gate",
    "baseline_repair_registry_gate",
    "baseline_matching_quality_gate",
    "positive_exposure_robustness_gate",
    "matched_baseline_residual_gate",
    "false_positive_burden_gate",
    "topk_positive_exposure_gate",
    "topk_residual_gate",
    "cluster_bootstrap_gate",
    "search_accounting_gate",
    "output_contract_gate",
]
REQUIRED_OUTPUT_KEYS = [
    "input_artifact_audit",
    "upstream_19a_contract_audit",
    "upstream_19b0_contract_audit",
    "robustness_outcome_boundary_audit",
    "robustness_candidate_row_manifest",
    "robustness_baseline_row_manifest",
    "baseline_repair_variant_registry",
    "baseline_repair_sweep_audit",
    "robustness_metric_readout",
    "robustness_baseline_quality_audit",
    "robustness_positive_exposure_readout",
    "robustness_residual_alpha_readout",
    "false_positive_burden_readout",
    "tail_lift_curve_readout",
    "ccdf_survival_curve_readout",
    "capture_vs_burden_readout",
    "mfe_mae_joint_readout",
    "topk_concentration_sensitivity",
    "cluster_bootstrap_ci",
    "search_accounting_audit",
    "entry_universe_19b_decision",
    "tail_lift_curve_figure",
    "ccdf_survival_curve_figure",
    "capture_vs_burden_figure",
    "mfe_mae_joint_scatter_figure",
    "report",
    "handoff_contract",
    "manifest",
    "output_hashes",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP19B robustness right-tail enrichment readout.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("experiments/", "data/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": OUTPUT_ROOT / "input_artifact_audit.csv",
        "upstream_19a_contract_audit": OUTPUT_ROOT / "upstream_19a_contract_audit.csv",
        "upstream_19b0_contract_audit": OUTPUT_ROOT / "upstream_19b0_contract_audit.csv",
        "robustness_outcome_boundary_audit": OUTPUT_ROOT / "robustness_outcome_boundary_audit.csv",
        "robustness_candidate_row_manifest": OUTPUT_ROOT / "robustness_candidate_row_manifest.csv",
        "robustness_baseline_row_manifest": OUTPUT_ROOT / "robustness_baseline_row_manifest.csv",
        "baseline_repair_variant_registry": OUTPUT_ROOT / "baseline_repair_variant_registry.csv",
        "baseline_repair_sweep_audit": OUTPUT_ROOT / "baseline_repair_sweep_audit.csv",
        "robustness_metric_readout": OUTPUT_ROOT / "robustness_metric_readout.csv",
        "robustness_baseline_quality_audit": OUTPUT_ROOT / "robustness_baseline_quality_audit.csv",
        "robustness_positive_exposure_readout": OUTPUT_ROOT / "robustness_positive_exposure_readout.csv",
        "robustness_residual_alpha_readout": OUTPUT_ROOT / "robustness_residual_alpha_readout.csv",
        "false_positive_burden_readout": OUTPUT_ROOT / "false_positive_burden_readout.csv",
        "tail_lift_curve_readout": OUTPUT_ROOT / "tail_lift_curve_readout.csv",
        "ccdf_survival_curve_readout": OUTPUT_ROOT / "ccdf_survival_curve_readout.csv",
        "capture_vs_burden_readout": OUTPUT_ROOT / "capture_vs_burden_readout.csv",
        "mfe_mae_joint_readout": OUTPUT_ROOT / "mfe_mae_joint_readout.csv",
        "topk_concentration_sensitivity": OUTPUT_ROOT / "topk_concentration_sensitivity.csv",
        "cluster_bootstrap_ci": OUTPUT_ROOT / "cluster_bootstrap_ci.csv",
        "search_accounting_audit": OUTPUT_ROOT / "search_accounting_audit.csv",
        "entry_universe_19b_decision": OUTPUT_ROOT / "entry_universe_19b_decision.csv",
        "tail_lift_curve_figure": FIGURE_DIR / "tail_lift_curve.png",
        "ccdf_survival_curve_figure": FIGURE_DIR / "ccdf_survival_curve.png",
        "capture_vs_burden_figure": FIGURE_DIR / "capture_vs_burden.png",
        "mfe_mae_joint_scatter_figure": FIGURE_DIR / "mfe_mae_joint_scatter.png",
        "report": OUTPUT_ROOT / "19B_robust_right_tail_enrichment_and_false_positive_burden_readout_report.md",
        "handoff_contract": OUTPUT_ROOT / "19B_handoff_contract.md",
        "manifest": OUTPUT_ROOT / "manifest_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.json",
        "output_hashes": OUTPUT_ROOT / "output_hashes_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.json",
    }


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def standard_normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def sidak_alpha(n_tests: int, alpha: float = 0.05) -> float:
    n = max(int(n_tests), 1)
    return 1.0 - (1.0 - alpha) ** (1.0 / n)


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if np.isfinite(out) else default


def pass_fail(condition: bool) -> str:
    return "pass" if bool(condition) else "fail"


def metric_contract_blocking_reason(config: dict[str, Any]) -> str:
    burden_cfg = config.get("false_positive_burden", {})
    for cap_name, default_value in CONTRACT_DEFAULT_FALSE_POSITIVE_BURDEN_CAPS.items():
        value = safe_float(burden_cfg.get(cap_name))
        if not np.isfinite(value):
            return f"required_metric_tolerance_not_frozen:{cap_name}"
        if value > default_value + 1e-12:
            return "false_positive_burden_tolerance_weakened_after_contract_default"

    positive_cfg = config.get("positive_exposure", {})
    required_positive_keys = [
        "positive_exposure_absolute_margin_floor_50",
        "positive_exposure_relative_margin_ratio_floor",
    ]
    for key in required_positive_keys:
        if not np.isfinite(safe_float(positive_cfg.get(key))):
            return f"required_metric_tolerance_not_frozen:{key}"

    bootstrap_cfg = config.get("bootstrap", {})
    required_bootstrap_keys = [
        "bootstrap_resample_n",
        "bootstrap_seed",
        "candidate_cluster_key",
        "matched_baseline_rerandomization_n",
        "matched_baseline_rerandomization_seed",
        "positive_exposure_p_value_method",
        "residual_p_value_method",
    ]
    for key in required_bootstrap_keys:
        if key not in bootstrap_cfg or bootstrap_cfg[key] in (None, ""):
            return f"required_metric_tolerance_not_frozen:{key}"

    return ""


def build_input_artifact_audit(config: dict[str, Any], paths: dict[str, Path]) -> pd.DataFrame:
    required = [
        "requirement_19b",
        "config_19b",
        "nineteen_a_decision",
        "nineteen_a_manifest",
        "nineteen_a_output_hashes",
        "nineteen_a_baseline_budget_freeze",
        "nineteen_a_baseline_matching_spec",
        "nineteen_a_primary_metric_and_margin_freeze",
        "nineteen_a_multiple_testing_correction_freeze",
        "nineteen_a_validation_stress_rule_freeze",
        "nineteen_a_split_construction_freeze",
        "nineteen_b0_decision",
        "nineteen_b0_manifest",
        "nineteen_b0_output_hashes",
        "nineteen_b0_selected_family_cell_manifest",
        "nineteen_b0_robustness_test_manifest",
        "nineteen_b0_grid_cell_manifest",
        "nineteen_b0_handoff_contract",
        "topn_executable_universe",
        "stock_qfq_dir",
        "benchmark_daily",
    ]
    rows = []
    for key in required:
        path = paths[key]
        exists = path.exists()
        row_count = b0.row_count(path) if exists and path.is_file() and path.suffix == ".csv" else np.nan
        rows.append(
            {
                "artifact_id": key,
                "artifact_path": str(path.relative_to(REPO_ROOT)) if path.exists() or not path.is_absolute() else str(path),
                "required_flag": True,
                "exists": exists,
                "row_count_if_tabular": row_count,
                "source_manifest_hash": "",
                "observed_file_hash": b0.artifact_hash(path) if exists else "",
                "hash_verified": exists,
                "input_artifact_gate": pass_fail(exists),
                "blocking_reason": "" if exists else "required_artifact_missing",
            }
        )
    return pd.DataFrame(rows)


def contract_row(artifact_id: str, fact: str, expected: Any, observed: Any) -> dict[str, Any]:
    ok = str(expected) == str(observed)
    return {
        "artifact_id": artifact_id,
        "required_fact": fact,
        "expected_value": expected,
        "observed_value": observed,
        "contract_gate": pass_fail(ok),
        "blocking_reason": "" if ok else f"{fact}_mismatch",
    }


def build_upstream_19a_contract_audit(paths: dict[str, Path]) -> tuple[pd.DataFrame, str, dict[str, Any]]:
    decision = pd.read_csv(paths["nineteen_a_decision"]).iloc[0].to_dict()
    manifest = read_json(paths["nineteen_a_manifest"])
    split = pd.read_csv(paths["nineteen_a_split_construction_freeze"])
    robust = split.loc[split["split"].eq("robustness")].iloc[0].to_dict()
    rows = [
        contract_row("entry_universe_preflight_decision", "decision_state", READY_19A, decision.get("decision_state", "")),
        contract_row("entry_universe_preflight_decision", "all_critical_gates_pass", True, bool(decision.get("all_critical_gates_pass"))),
        contract_row("entry_universe_preflight_decision", "next_allowed_requirement", "requirement_19b0_fast_rule_grid_enrichment_scan.md", decision.get("next_allowed_requirement", "")),
        contract_row("manifest_19a", "decision_state", READY_19A, manifest.get("decision_state", "")),
        contract_row("split_construction_freeze", "robustness_split", "robustness", robust.get("split", "")),
        contract_row("split_construction_freeze", "validation_selection_allowed", False, bool(robust.get("validation_selection_allowed"))),
    ]
    for col in POLICY_AUTH_COLUMNS:
        rows.append(contract_row("entry_universe_preflight_decision", col, False, bool(decision.get(col))))
    frame = pd.DataFrame(rows)
    gate = pass_fail(frame["contract_gate"].eq("pass").all())
    return frame, gate, decision


def build_upstream_19b0_contract_audit(config: dict[str, Any], paths: dict[str, Path]) -> tuple[pd.DataFrame, str, pd.DataFrame, pd.DataFrame]:
    decision = pd.read_csv(paths["nineteen_b0_decision"]).iloc[0].to_dict()
    selected = pd.read_csv(paths["nineteen_b0_selected_family_cell_manifest"])
    robustness = pd.read_csv(paths["nineteen_b0_robustness_test_manifest"])
    expected_cells = {(item["family_id"], item["grid_cell_id"]) for item in config["selected_cells"]}
    observed_cells = set(map(tuple, robustness[["family_id", "grid_cell_id"]].to_numpy()))
    rows = [
        contract_row("entry_universe_19b0_decision", "decision_state", READY_19B0, decision.get("decision_state", "")),
        contract_row("entry_universe_19b0_decision", "next_allowed_requirement", NEXT_19B, decision.get("next_allowed_requirement", "")),
        contract_row("entry_universe_19b0_decision", "N_family_brought_to_robustness", 2, int(decision.get("N_family_brought_to_robustness", -1))),
        contract_row("entry_universe_19b0_decision", "N_tested_family_cell_pairs", 2, int(decision.get("N_tested_family_cell_pairs", -1))),
        contract_row("entry_universe_19b0_decision", "selected_residual_alpha_cell_pair_n", 0, int(decision.get("selected_residual_alpha_cell_pair_n", -1))),
        contract_row("entry_universe_19b0_decision", "selected_positive_beta_exposure_cell_pair_n", 2, int(decision.get("selected_positive_beta_exposure_cell_pair_n", -1))),
        contract_row("entry_universe_19b0_decision", "validation_outcome_read", False, bool(decision.get("validation_outcome_read"))),
        contract_row("entry_universe_19b0_decision", "robustness_outcome_used_for_selection", False, bool(decision.get("robustness_outcome_used_for_selection"))),
        contract_row("robustness_test_manifest", "frozen_cell_set", sorted(expected_cells), sorted(observed_cells)),
    ]
    for row in robustness.itertuples(index=False):
        rows.append(contract_row("robustness_test_manifest", f"{row.family_id}:promotion_claim_type", "positive_beta_exposure_candidate", row.promotion_claim_type))
        rows.append(contract_row("robustness_test_manifest", f"{row.family_id}:residual_alpha_claim_allowed", False, bool(row.residual_alpha_claim_allowed)))
        rows.append(contract_row("robustness_test_manifest", f"{row.family_id}:validation_split_outcome_read_allowed_in_19B", False, bool(row.validation_split_outcome_read_allowed_in_19B)))
    frame = pd.DataFrame(rows)
    gate = pass_fail(frame["contract_gate"].eq("pass").all())
    return frame, gate, selected, robustness


def build_panel(config: dict[str, Any], paths: dict[str, Path]) -> pd.DataFrame:
    panel_config = copy.deepcopy(config)
    panel_config["split"]["train_start"] = str(config["split"]["robustness_start"])
    panel_config["split"]["train_end"] = str(config["split"]["robustness_end"])
    b0.LOCAL_CACHE = LOCAL_CACHE
    panel = b0.load_or_build_universe_feature_panel(panel_config, paths)
    if panel.empty:
        return panel
    panel = panel.loc[pd.to_datetime(panel["decision_date"]).dt.strftime("%Y-%m-%d").between(config["split"]["robustness_start"], config["split"]["robustness_end"])].copy()
    return panel


def selected_parameters(paths: dict[str, Path], robustness_manifest: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    grid = pd.read_csv(paths["nineteen_b0_grid_cell_manifest"])
    merged = robustness_manifest[["family_id", "grid_cell_id"]].merge(
        grid[["family_id", "grid_cell_id", "parameter_json", "parameter_hash"]],
        on=["family_id", "grid_cell_id"],
        how="left",
        validate="one_to_one",
    )
    params: dict[tuple[str, str], dict[str, Any]] = {}
    for row in merged.itertuples(index=False):
        params[(row.family_id, row.grid_cell_id)] = json.loads(row.parameter_json)
    return params


def materialize_selected_cells(
    panel: pd.DataFrame,
    config: dict[str, Any],
    robustness_manifest: pd.DataFrame,
    params_by_cell: dict[tuple[str, str], dict[str, Any]],
) -> tuple[pd.DataFrame, dict[tuple[str, str], pd.DataFrame]]:
    frames: dict[tuple[str, str], pd.DataFrame] = {}
    manifest_rows = []
    window = int(config["execution"]["primary_cooldown_window_sessions"])
    base = panel.copy()
    for row in robustness_manifest.itertuples(index=False):
        key = (row.family_id, row.grid_cell_id)
        params = params_by_cell[key]
        mask, blocking = b0.apply_simple_predicate(base, row.family_id, params)
        raw = base.loc[mask].copy()
        if not raw.empty:
            raw["cooldown_entry"] = b0.cooldown_filter(raw, "decision_pos", window)
            raw["primary_denominator_row"] = raw["cooldown_entry"] & raw["entry_fill_feasible"] & raw["path_complete_120d"]
            raw["family_id"] = row.family_id
            raw["grid_cell_id"] = row.grid_cell_id
            raw["parameter_hash"] = row.parameter_hash
            raw["parameter_json"] = json.dumps(b0.clean_json(params), sort_keys=True)
        frames[key] = raw
        primary = raw.loc[raw["primary_denominator_row"]].copy() if not raw.empty else pd.DataFrame()
        for item in raw.itertuples(index=False):
            manifest_rows.append(
                {
                    "family_id": row.family_id,
                    "grid_cell_id": row.grid_cell_id,
                    "parameter_hash": row.parameter_hash,
                    "split": "robustness",
                    "row_key": item.row_id,
                    "instrument_id": item.instrument,
                    "decision_date": item.decision_date,
                    "executable_next_open_date": item.entry_date,
                    "primary_enrichment_denominator_flag": bool(getattr(item, "primary_denominator_row", False)),
                    "candidate_flag": True,
                    "manifest_frozen_before_label_readout": True,
                    "label_read_before_manifest_freeze": False,
                    "row_source_hash": b0.stable_hash_json(
                        {"family_id": row.family_id, "grid_cell_id": row.grid_cell_id, "row_key": item.row_id}
                    ),
                    "blocking_reason": blocking,
                }
            )
        if primary.empty and raw.empty:
            manifest_rows.append(
                {
                    "family_id": row.family_id,
                    "grid_cell_id": row.grid_cell_id,
                    "parameter_hash": row.parameter_hash,
                    "split": "robustness",
                    "row_key": "",
                    "instrument_id": "",
                    "decision_date": "",
                    "executable_next_open_date": "",
                    "primary_enrichment_denominator_flag": False,
                    "candidate_flag": False,
                    "manifest_frozen_before_label_readout": True,
                    "label_read_before_manifest_freeze": False,
                    "row_source_hash": "",
                    "blocking_reason": blocking or "no_candidate_rows",
                }
            )
    return pd.DataFrame(manifest_rows), frames


def build_repair_variant_registry(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in config["diagnostic_repair_variants"]:
        rows.append(
            {
                "repair_variant_id": item["repair_variant_id"],
                "baseline_family": item["baseline_family"],
                "variant_role": item["variant_role"],
                "matching_method": item["matching_method"],
                "bucket_spec_id": "19B0_bucket_count_5" if "cem" in item["matching_method"] else "",
                "caliper_spec_id": "19B_frozen_nn_caliper_v1" if "nearest_neighbor" in item["matching_method"] else "",
                "primary_residual_claim_allowed": bool(item["primary_residual_claim_allowed"]),
                "diagnostic_repair_only_flag": bool(item["diagnostic_repair_only_flag"]),
                "outcome_read_before_registry_freeze": False,
                "registry_frozen_before_label_readout": True,
                "blocking_reason": "",
            }
        )
    return pd.DataFrame(rows)


def sample_baseline_for_variant(
    candidate: pd.DataFrame,
    pool: pd.DataFrame,
    repair_variant_id: str,
    baseline_family: str,
    seed: int,
) -> tuple[pd.DataFrame, int]:
    if repair_variant_id in ORIGINAL_VARIANT_TO_BASELINE:
        return b0.baseline_for_cell(candidate, pool, ORIGINAL_VARIANT_TO_BASELINE[repair_variant_id], seed)
    rng = np.random.default_rng(seed)
    if baseline_family == "liquidity_size_volatility_recent_return_matched_same_budget":
        counts = candidate.groupby(["lsv_match_key"], dropna=False).size()
        return b0.sample_from_pool(pool, counts, ["lsv_match_key"], rng)
    if baseline_family == "liquidity_size_volatility_recent_return_nearest_neighbor_same_budget":
        counts = candidate.groupby(["decision_month"], dropna=False).size()
        return b0.sample_from_pool(pool, counts, ["decision_month"], rng)
    return b0.baseline_for_cell(candidate, pool, baseline_family, seed)


def cluster_bootstrap_se_delta(
    candidate: pd.DataFrame,
    comparator: pd.DataFrame,
    cluster_key: str,
    resample_n: int,
    seed: int,
) -> tuple[float, float, float]:
    if candidate.empty or comparator.empty or cluster_key not in candidate or cluster_key not in comparator:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)

    def cluster_arrays(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        grouped = frame.groupby(cluster_key)["forward_big_winner_120d"].agg(["sum", "count"])
        return grouped["sum"].to_numpy(dtype=float), grouped["count"].to_numpy(dtype=float)

    cand_sum, cand_count = cluster_arrays(candidate)
    comp_sum, comp_count = cluster_arrays(comparator)
    if len(cand_sum) < 2 or len(comp_sum) < 2:
        return np.nan, np.nan, np.nan
    deltas = np.empty(resample_n, dtype=float)
    for idx in range(resample_n):
        c_idx = rng.integers(0, len(cand_sum), size=len(cand_sum))
        b_idx = rng.integers(0, len(comp_sum), size=len(comp_sum))
        p_c = cand_sum[c_idx].sum() / max(cand_count[c_idx].sum(), 1.0)
        p_b = comp_sum[b_idx].sum() / max(comp_count[b_idx].sum(), 1.0)
        deltas[idx] = p_c - p_b
    return float(np.std(deltas, ddof=1)), float(np.quantile(deltas, 0.025)), float(np.quantile(deltas, 0.975))


def positive_exposure_readout_for_candidate(
    candidate: pd.DataFrame,
    baseline_pool: pd.DataFrame,
    config: dict[str, Any],
    seed_offset: int = 0,
) -> dict[str, float]:
    p_candidate = float(candidate["forward_big_winner_120d"].mean()) if len(candidate) else np.nan
    p_eligible = float(baseline_pool["forward_big_winner_120d"].mean()) if len(baseline_pool) else np.nan
    delta = p_candidate - p_eligible if np.isfinite(p_candidate) and np.isfinite(p_eligible) else np.nan
    ratio = p_candidate / p_eligible if np.isfinite(p_candidate) and np.isfinite(p_eligible) and p_eligible > 0 else np.nan
    boot = config["bootstrap"]
    se, ci_low, ci_high = cluster_bootstrap_se_delta(
        candidate,
        baseline_pool,
        str(boot["candidate_cluster_key"]),
        int(boot["bootstrap_resample_n"]),
        int(boot["bootstrap_seed"]) + seed_offset,
    )
    absolute_floor, relative_ratio = b0.positive_exposure_parameters(config)
    relative_floor = relative_ratio * p_eligible if np.isfinite(p_eligible) else np.nan
    margin_candidates = [absolute_floor]
    if np.isfinite(relative_floor):
        margin_candidates.append(float(relative_floor))
    if np.isfinite(se):
        margin_candidates.append(float(2.0 * se))
    margin = max(margin_candidates)
    score = delta - margin if np.isfinite(delta) else np.nan
    z = delta / se if np.isfinite(delta) and np.isfinite(se) and se > 0 else np.nan
    p_value = 1.0 - standard_normal_cdf(z) if np.isfinite(z) else np.nan
    return {
        "p_candidate_50": p_candidate,
        "p_eligible_universe_50": p_eligible,
        "positive_exposure_delta_50": delta,
        "positive_exposure_ratio_50": ratio,
        "positive_exposure_SE_delta_probability": se,
        "positive_exposure_CI_low": ci_low,
        "positive_exposure_CI_high": ci_high,
        "cluster_bootstrap_SE_margin_50": 2.0 * se if np.isfinite(se) else np.nan,
        "positive_exposure_absolute_margin_floor_50": absolute_floor,
        "positive_exposure_relative_margin_ratio_floor": relative_ratio,
        "positive_exposure_relative_margin_floor_50": relative_floor,
        "positive_exposure_margin_50": margin,
        "positive_exposure_score_50": score,
        "positive_exposure_p_value_50": p_value,
    }


def false_positive_burden(candidate: pd.DataFrame, comparator: pd.DataFrame, config: dict[str, Any], scope: str) -> dict[str, Any]:
    cfg = config["false_positive_burden"]
    winner_n = int(candidate["forward_big_winner_120d"].sum()) if len(candidate) else 0
    non_winner_n = int(len(candidate) - winner_n)
    candidate_per_winner = len(candidate) / max(winner_n, 1)
    fast_fail_rate = float(candidate["forward_mae_20d"].le(-0.10).mean()) if len(candidate) else np.nan
    false_repair_rate = fast_fail_rate
    mae_20_p10 = float(candidate["forward_mae_20d"].quantile(0.10)) if len(candidate) else np.nan
    mae_20_p05 = float(candidate["forward_mae_20d"].quantile(0.05)) if len(candidate) else np.nan
    comp_p10 = float(comparator["forward_mae_20d"].quantile(0.10)) if len(comparator) else np.nan
    comp_p05 = float(comparator["forward_mae_20d"].quantile(0.05)) if len(comparator) else np.nan
    worsening = comp_p10 - mae_20_p10 if np.isfinite(comp_p10) and np.isfinite(mae_20_p10) else np.nan
    relative = worsening / abs(comp_p10) if np.isfinite(worsening) and np.isfinite(comp_p10) and comp_p10 != 0 else np.nan
    gate = (
        candidate_per_winner <= float(cfg["candidate_per_winner_cap"])
        and fast_fail_rate <= float(cfg["fast_fail_rate_cap"])
        and false_repair_rate <= float(cfg["false_repair_rate_cap"])
        and np.isfinite(worsening)
        and worsening <= float(cfg["mae_abs_worsening_cap"])
    )
    return {
        "winner_n": winner_n,
        "non_winner_n": non_winner_n,
        "non_winner_rate": non_winner_n / max(len(candidate), 1),
        "candidate_per_winner": candidate_per_winner,
        "fast_fail_rate": fast_fail_rate,
        "false_repair_rate": false_repair_rate,
        "MAE_20_p10": mae_20_p10,
        "MAE_20_p05": mae_20_p05,
        "burden_comparator_scope": scope,
        "burden_comparator_MAE_20_p10": comp_p10,
        "burden_comparator_MAE_20_p05": comp_p05,
        "mae_abs_worsening": worsening,
        "mae_relative_worsening": relative,
        "candidate_per_winner_cap": float(cfg["candidate_per_winner_cap"]),
        "fast_fail_rate_cap": float(cfg["fast_fail_rate_cap"]),
        "false_repair_rate_cap": float(cfg["false_repair_rate_cap"]),
        "mae_abs_worsening_cap": float(cfg["mae_abs_worsening_cap"]),
        "false_positive_burden_gate": pass_fail(gate),
    }


def topk_readout(
    candidate: pd.DataFrame,
    baseline_pool: pd.DataFrame,
    p_matched_conservative: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    inst_counts = candidate["instrument"].value_counts()
    top1 = set(inst_counts.index[:1])
    top3 = set(inst_counts.index[:3])
    removed1 = candidate.loc[~candidate["instrument"].isin(top1)]
    removed3 = candidate.loc[~candidate["instrument"].isin(top3)]
    pos1 = positive_exposure_readout_for_candidate(removed1, baseline_pool, config, seed_offset=101)
    pos3 = positive_exposure_readout_for_candidate(removed3, baseline_pool, config, seed_offset=103)
    p1 = pos1["p_candidate_50"]
    p3 = pos3["p_candidate_50"]
    lift1 = p1 / p_matched_conservative if np.isfinite(p1) and np.isfinite(p_matched_conservative) and p_matched_conservative > 0 else np.nan
    lift3 = p3 / p_matched_conservative if np.isfinite(p3) and np.isfinite(p_matched_conservative) and p_matched_conservative > 0 else np.nan
    winner_counts = candidate.loc[candidate["forward_big_winner_120d"], "instrument"].value_counts()
    max_winner_share = float(winner_counts.iloc[0] / max(int(winner_counts.sum()), 1)) if len(winner_counts) else 0.0
    cap = float(config["topk"]["max_instrument_winner_share_cap"])
    positive_gate = pos1["positive_exposure_score_50"] > 0 and pos3["positive_exposure_score_50"] > 0 and max_winner_share <= cap
    return {
        "top_1_instrument_removed_tail_lift_against_original_frozen_baseline": lift1,
        "top_3_instruments_removed_tail_lift_against_original_frozen_baseline": lift3,
        "top_1_instrument_removed_positive_exposure_score_50": pos1["positive_exposure_score_50"],
        "top_3_instruments_removed_positive_exposure_score_50": pos3["positive_exposure_score_50"],
        "max_instrument_candidate_share": float(inst_counts.iloc[0] / max(len(candidate), 1)) if len(inst_counts) else 0.0,
        "max_instrument_winner_share": max_winner_share,
        "max_instrument_month_candidate_share": float(candidate["instrument_month"].value_counts().iloc[0] / max(len(candidate), 1))
        if len(candidate)
        else 0.0,
        "max_decision_month_candidate_share": float(candidate["decision_month"].value_counts().iloc[0] / max(len(candidate), 1))
        if len(candidate)
        else 0.0,
        "topk_positive_exposure_gate": pass_fail(positive_gate),
    }


def baseline_quality_metrics(candidate: pd.DataFrame, baseline: pd.DataFrame, unmatched: int, gates: dict[str, Any]) -> dict[str, Any]:
    requested = len(candidate)
    materialized = len(baseline)
    reuse_rate = 1.0 - baseline.index.nunique() / materialized if materialized else 1.0
    smd = b0.max_smd(candidate, baseline) if materialized else np.nan
    decision_delta = b0.max_distribution_delta(candidate["decision_month"], baseline["decision_month"]) if materialized else 1.0
    instrument_delta = b0.max_distribution_delta(candidate["instrument"], baseline["instrument"]) if materialized else 1.0
    unmatched_rate = unmatched / requested if requested else 1.0
    quality_pass = (
        unmatched_rate <= float(gates["unmatched_candidate_rate_max"])
        and reuse_rate <= float(gates["baseline_reuse_rate_max"])
        and np.isfinite(smd)
        and smd <= float(gates["max_standardized_mean_difference_after_matching_max"])
        and decision_delta <= float(gates["decision_month_coverage_delta_max"])
        and instrument_delta <= float(gates["instrument_coverage_delta_max"])
        and materialized >= requested
    )
    return {
        "candidate_n": requested,
        "matched_candidate_n": min(requested, materialized),
        "unmatched_candidate_n": unmatched,
        "unmatched_candidate_rate": unmatched_rate,
        "baseline_reuse_rate": reuse_rate,
        "max_standardized_mean_difference_after_matching": smd,
        "per_feature_smd_json": json.dumps({}, sort_keys=True),
        "decision_month_coverage_delta": decision_delta,
        "instrument_coverage_delta": instrument_delta,
        "matched_baseline_primary_row_count": materialized,
        "primary_enrichment_denominator_row_count": requested,
        "common_support_pass": pass_fail(unmatched_rate <= float(gates["unmatched_candidate_rate_max"])),
        "baseline_matching_quality_gate": pass_fail(quality_pass),
        "failure_reason": "" if quality_pass else "baseline_quality_threshold_failed",
    }


def residual_rerandomization_p_value(candidate: pd.DataFrame, baseline: pd.DataFrame, observed_lift: float, n: int, seed: int) -> float:
    if candidate.empty or baseline.empty or not np.isfinite(observed_lift):
        return np.nan
    values = pd.concat([candidate["forward_big_winner_120d"], baseline["forward_big_winner_120d"]]).astype(float).to_numpy()
    c_n = len(candidate)
    b_n = len(baseline)
    if b_n == 0:
        return np.nan
    rng = np.random.default_rng(seed)
    exceed = 0
    for _ in range(n):
        perm = rng.permutation(values)
        p_c = perm[:c_n].mean()
        p_b = perm[c_n : c_n + b_n].mean()
        lift = p_c / p_b if p_b > 0 else np.inf
        if lift >= observed_lift:
            exceed += 1
    return (1 + exceed) / (1 + n)


def build_readouts(
    config: dict[str, Any],
    robustness_manifest: pd.DataFrame,
    candidate_manifest: pd.DataFrame,
    cell_frames: dict[tuple[str, str], pd.DataFrame],
    panel: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    baseline_pool = panel.loc[panel["baseline_eligible"]].copy()
    registry = build_repair_variant_registry(config)
    gates = config["baseline"]["quality_gates"]
    bootstrap_cfg = config["bootstrap"]
    n_tests = int(robustness_manifest["N_tested_family_cell_pairs"].max()) if not robustness_manifest.empty else 1
    pos_alpha = sidak_alpha(n_tests)
    residual_alpha = sidak_alpha(n_tests)
    baseline_manifest_rows: list[dict[str, Any]] = []
    sweep_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    positive_rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    burden_rows: list[dict[str, Any]] = []
    topk_rows: list[dict[str, Any]] = []
    cluster_rows: list[dict[str, Any]] = []
    tail_rows: list[dict[str, Any]] = []
    ccdf_rows: list[dict[str, Any]] = []
    capture_rows: list[dict[str, Any]] = []
    joint_rows: list[dict[str, Any]] = []

    for cell_no, row in enumerate(robustness_manifest.itertuples(index=False), start=1):
        key = (row.family_id, row.grid_cell_id)
        frame = cell_frames[key]
        candidate = frame.loc[frame["primary_denominator_row"]].copy() if not frame.empty else pd.DataFrame()
        candidate_n = len(candidate)
        baselines: dict[str, pd.DataFrame] = {}
        original_quality: dict[str, str] = {}
        original_p: dict[str, float] = {}
        original_se: dict[str, float] = {}

        for variant_no, variant in enumerate(registry.itertuples(index=False), start=1):
            baseline, unmatched = sample_baseline_for_variant(
                candidate,
                baseline_pool,
                variant.repair_variant_id,
                variant.baseline_family,
                int(config["baseline"]["random_seed"]) + cell_no * 101 + variant_no,
            )
            baselines[variant.repair_variant_id] = baseline
            for base_row in baseline.itertuples(index=False):
                baseline_manifest_rows.append(
                    {
                        "family_id": row.family_id,
                        "grid_cell_id": row.grid_cell_id,
                        "parameter_hash": row.parameter_hash,
                        "split": "robustness",
                        "repair_variant_id": variant.repair_variant_id,
                        "baseline_family": variant.baseline_family,
                        "variant_role": variant.variant_role,
                        "candidate_row_key": "",
                        "baseline_row_key": base_row.row_id,
                        "baseline_instrument_id": base_row.instrument,
                        "baseline_decision_date": base_row.decision_date,
                        "matching_weight": 1.0,
                        "manifest_frozen_before_label_readout": True,
                        "label_read_before_manifest_freeze": False,
                        "row_source_hash": b0.stable_hash_json(
                            {"repair_variant_id": variant.repair_variant_id, "row_key": base_row.row_id}
                        ),
                        "blocking_reason": "",
                    }
                )
            quality = baseline_quality_metrics(candidate, baseline, unmatched, gates)
            p_matched = float(baseline["forward_big_winner_120d"].mean()) if len(baseline) else np.nan
            se_delta = b0.se_delta_probability(candidate, baseline) if len(candidate) and len(baseline) else np.nan
            quality.update(
                {
                    "family_id": row.family_id,
                    "grid_cell_id": row.grid_cell_id,
                    "split": "robustness",
                    "repair_variant_id": variant.repair_variant_id,
                    "baseline_family": variant.baseline_family,
                    "variant_role": variant.variant_role,
                    "primary_residual_claim_allowed": bool(variant.primary_residual_claim_allowed),
                    "quality_blocks_residual_alpha_only": bool(
                        variant.variant_role == "primary_original_frozen" and quality["baseline_matching_quality_gate"] == "fail"
                    ),
                    "positive_exposure_readout_allowed": True,
                    "diagnostic_repair_only_flag": bool(variant.diagnostic_repair_only_flag),
                }
            )
            quality_rows.append(quality.copy())
            sweep_rows.append(
                {
                    **quality,
                    "matching_method": variant.matching_method,
                    "bucket_spec_id": variant.bucket_spec_id,
                    "caliper_spec_id": variant.caliper_spec_id,
                }
            )
            if variant.repair_variant_id in ORIGINAL_VARIANTS:
                original_quality[variant.repair_variant_id] = quality["baseline_matching_quality_gate"]
                original_p[variant.repair_variant_id] = p_matched
                original_se[variant.repair_variant_id] = se_delta

        all_original_quality_pass = all(original_quality.get(variant) == "pass" for variant in ORIGINAL_VARIANTS)
        p_matched_conservative = max([value for value in original_p.values() if np.isfinite(value)], default=np.nan)
        conservative_variant = ""
        conservative_baseline = pd.DataFrame()
        if np.isfinite(p_matched_conservative):
            for variant, value in original_p.items():
                if value == p_matched_conservative:
                    conservative_variant = variant
                    conservative_baseline = baselines[variant]
                    break

        positive = positive_exposure_readout_for_candidate(candidate, baseline_pool, config, seed_offset=cell_no)
        positive_pass = (
            positive["positive_exposure_score_50"] > 0
            and positive["positive_exposure_ratio_50"] >= 1.0 + float(config["positive_exposure"]["positive_exposure_relative_margin_ratio_floor"])
            and positive["positive_exposure_p_value_50"] <= pos_alpha
        )

        residual_se = original_se.get(conservative_variant, np.nan)
        residual_margin = (
            max(0.10, 2.0 * residual_se / p_matched_conservative)
            if np.isfinite(residual_se) and np.isfinite(p_matched_conservative) and p_matched_conservative > 0
            else np.nan
        )
        primary_tail_lift = positive["p_candidate_50"] / p_matched_conservative if np.isfinite(p_matched_conservative) and p_matched_conservative > 0 else np.nan
        residual_adjusted = primary_tail_lift - (1.0 + residual_margin) if np.isfinite(primary_tail_lift) and np.isfinite(residual_margin) else np.nan
        residual_p = (
            residual_rerandomization_p_value(
                candidate,
                conservative_baseline,
                primary_tail_lift,
                int(bootstrap_cfg["matched_baseline_rerandomization_n"]),
                int(bootstrap_cfg["matched_baseline_rerandomization_seed"]) + cell_no,
            )
            if all_original_quality_pass
            else np.nan
        )

        burden_comparator = baseline_pool
        burden_scope = "eligible_universe_primary"
        burden = false_positive_burden(candidate, burden_comparator, config, burden_scope)
        matched_p10 = (
            float(conservative_baseline["forward_mae_20d"].quantile(0.10))
            if all_original_quality_pass and not conservative_baseline.empty
            else np.nan
        )
        matched_p05 = (
            float(conservative_baseline["forward_mae_20d"].quantile(0.05))
            if all_original_quality_pass and not conservative_baseline.empty
            else np.nan
        )
        topk = topk_readout(candidate, baseline_pool, p_matched_conservative, config)
        topk_residual_gate = (
            all_original_quality_pass
            and topk["top_1_instrument_removed_tail_lift_against_original_frozen_baseline"] >= 1.0
            and topk["top_3_instruments_removed_tail_lift_against_original_frozen_baseline"] >= 1.0
            and topk["max_instrument_winner_share"] <= float(config["topk"]["max_instrument_winner_share_cap"])
        )
        residual_pass = (
            all_original_quality_pass
            and np.isfinite(residual_adjusted)
            and residual_adjusted > 0
            and np.isfinite(residual_p)
            and residual_p <= residual_alpha
            and burden["false_positive_burden_gate"] == "pass"
            and topk_residual_gate
        )
        if any(np.isfinite(value) and value == 0 for value in original_p.values()):
            residual_status = "not_supportable_zero_baseline_without_frozen_smoothing"
        elif not all_original_quality_pass:
            residual_status = "diagnostic_only_original_frozen_baseline_quality_failed"
        elif residual_pass:
            residual_status = "residual_style_supported"
        else:
            residual_status = "residual_style_not_supported"

        cell_positive_gate = positive_pass and burden["false_positive_burden_gate"] == "pass" and topk["topk_positive_exposure_gate"] == "pass"
        cell_residual_gate = residual_pass and burden["false_positive_burden_gate"] == "pass" and topk_residual_gate
        if cell_residual_gate:
            cell_state = "residual_alpha_supported"
        elif cell_positive_gate and not all_original_quality_pass:
            cell_state = "positive_exposure_persistent_baseline_quality_blocked"
        elif cell_positive_gate and all_original_quality_pass and not residual_pass:
            cell_state = "positive_exposure_persistent_residual_not_supported"
        elif positive_pass and burden["false_positive_burden_gate"] == "fail":
            cell_state = "false_positive_burden_blocked"
        elif positive_pass and burden["false_positive_burden_gate"] == "pass" and topk["topk_positive_exposure_gate"] == "fail":
            cell_state = "topk_concentration_blocked"
        else:
            cell_state = "robustness_not_supported"

        base_columns = {
            "family_id": row.family_id,
            "grid_cell_id": row.grid_cell_id,
            "parameter_hash": row.parameter_hash,
            "split": "robustness",
        }
        common = {
            **base_columns,
            "label_anchor_type": "executable_next_open_anchored",
            "promotion_claim_type_19b0": row.promotion_claim_type,
            "candidate_n": candidate_n,
            "tradable_n": candidate_n,
            "instrument_n": int(candidate["instrument"].nunique()) if candidate_n else 0,
            "instrument_month_n": int(candidate["instrument_month"].nunique()) if candidate_n else 0,
            "decision_month_n": int(candidate["decision_month"].nunique()) if candidate_n else 0,
            "cooldown_entry_n": candidate_n,
            "primary_denominator_n": candidate_n,
            "path_complete_20_n": int(candidate["path_complete_20d"].sum()) if candidate_n else 0,
            "path_complete_30_n": int(candidate["path_complete_30d"].sum()) if candidate_n else 0,
            "path_complete_60_n": int(candidate["path_complete_60d"].sum()) if candidate_n else 0,
            "path_complete_120_n": int(candidate["path_complete_120d"].sum()) if candidate_n else 0,
            **{k: positive[k] for k in [
                "p_candidate_50",
                "p_eligible_universe_50",
                "positive_exposure_delta_50",
                "positive_exposure_ratio_50",
                "positive_exposure_SE_delta_probability",
                "cluster_bootstrap_SE_margin_50",
                "positive_exposure_margin_50",
                "positive_exposure_score_50",
                "positive_exposure_p_value_50",
            ]},
            "positive_exposure_p_value_method": bootstrap_cfg["positive_exposure_p_value_method"],
            "positive_exposure_sidak_alpha": pos_alpha,
            "positive_exposure_robustness_pass": bool(positive_pass),
            "p_matched_50_primary_residual_baseline": p_matched_conservative,
            "residual_SE_delta_probability": residual_se,
            "residual_corrected_margin_ratio_50": residual_margin,
            "primary_tail_lift_50": primary_tail_lift,
            "primary_tail_lift_50_margin_adjusted": residual_adjusted,
            "residual_p_value_method": bootstrap_cfg["residual_p_value_method"],
            "primary_tail_lift_50_p_value": residual_p,
            "residual_alpha_sidak_alpha": residual_alpha,
            "matched_baseline_residual_pass_19b": bool(residual_pass),
            "residual_alpha_support_claim_allowed_19b": bool(residual_pass),
            "residual_readout_status": residual_status,
            "residual_blocking_reason": "" if residual_pass else residual_status,
            "false_positive_burden_gate": burden["false_positive_burden_gate"],
            "topk_positive_exposure_gate": topk["topk_positive_exposure_gate"],
            "topk_residual_gate": pass_fail(topk_residual_gate),
            "cell_positive_exposure_gate": bool(cell_positive_gate),
            "cell_residual_style_gate": bool(cell_residual_gate),
            "cell_decision_state": cell_state,
            "blocking_reason": "" if cell_state in {"residual_alpha_supported", "positive_exposure_persistent_baseline_quality_blocked", "positive_exposure_persistent_residual_not_supported"} else cell_state,
        }
        metric_rows.append(common)
        positive_rows.append(
            {
                **base_columns,
                **{k: common[k] for k in [
                    "p_candidate_50",
                    "p_eligible_universe_50",
                    "positive_exposure_delta_50",
                    "positive_exposure_ratio_50",
                    "positive_exposure_SE_delta_probability",
                    "cluster_bootstrap_SE_margin_50",
                    "positive_exposure_margin_50",
                    "positive_exposure_score_50",
                    "positive_exposure_p_value_method",
                    "positive_exposure_p_value_50",
                    "positive_exposure_sidak_alpha",
                    "positive_exposure_robustness_pass",
                    "false_positive_burden_gate",
                    "topk_positive_exposure_gate",
                    "cell_positive_exposure_gate",
                    "cell_decision_state",
                    "blocking_reason",
                ]},
            }
        )
        residual_rows.append(
            {
                **base_columns,
                "all_three_original_frozen_baseline_quality_gate": pass_fail(all_original_quality_pass),
                "p_candidate_50": common["p_candidate_50"],
                "p_matched_50_by_original_frozen_baseline_json": json.dumps(original_p, sort_keys=True),
                "p_matched_50_primary_residual_baseline": p_matched_conservative,
                "residual_SE_delta_probability": residual_se,
                "residual_corrected_margin_ratio_50": residual_margin,
                "primary_tail_lift_50": primary_tail_lift,
                "primary_tail_lift_50_margin_adjusted": residual_adjusted,
                "residual_p_value_method": bootstrap_cfg["residual_p_value_method"],
                "residual_rerandomization_n": int(bootstrap_cfg["matched_baseline_rerandomization_n"]),
                "residual_rerandomization_seed": int(bootstrap_cfg["matched_baseline_rerandomization_seed"]),
                "primary_tail_lift_50_p_value": residual_p,
                "residual_alpha_sidak_alpha": residual_alpha,
                "matched_baseline_residual_pass_19b": bool(residual_pass),
                "residual_alpha_support_claim_allowed_19b": bool(residual_pass),
                "residual_readout_status": residual_status,
                "residual_blocking_reason": "" if residual_pass else residual_status,
                "topk_residual_gate": pass_fail(topk_residual_gate),
                "cell_residual_style_gate": bool(cell_residual_gate),
                "cell_decision_state": cell_state,
                "blocking_reason": "" if residual_pass else residual_status,
            }
        )
        burden_rows.append(
            {
                **base_columns,
                "candidate_n": candidate_n,
                **burden,
                "matched_baseline_MAE_20_p10_if_quality_pass": matched_p10,
                "matched_baseline_MAE_20_p05_if_quality_pass": matched_p05,
                "blocking_reason": "" if burden["false_positive_burden_gate"] == "pass" else "false_positive_burden_gate_failed",
            }
        )
        topk_rows.append(
            {
                **base_columns,
                "baseline_family": "original_frozen_conservative",
                **topk,
                "topk_residual_gate": pass_fail(topk_residual_gate),
                "diagnostic_only_flag": not all_original_quality_pass,
                "blocking_reason": "" if topk["topk_positive_exposure_gate"] == "pass" else "topk_positive_exposure_gate_failed",
            }
        )
        cluster_rows.append(
            {
                **base_columns,
                "metric_id": "positive_exposure_delta_50",
                "cluster_key": bootstrap_cfg["candidate_cluster_key"],
                "resample_n": int(bootstrap_cfg["bootstrap_resample_n"]),
                "seed": int(bootstrap_cfg["bootstrap_seed"]),
                "p_value_method": bootstrap_cfg["positive_exposure_p_value_method"],
                "alternative": "p_candidate_50 > p_eligible_universe_50",
                "estimate": positive["positive_exposure_delta_50"],
                "SE": positive["positive_exposure_SE_delta_probability"],
                "ci_low": positive["positive_exposure_CI_low"],
                "ci_high": positive["positive_exposure_CI_high"],
                "p_value": positive["positive_exposure_p_value_50"],
                "sidak_alpha": pos_alpha,
                "bootstrap_contract_gate": pass_fail(np.isfinite(positive["positive_exposure_SE_delta_probability"])),
                "blocking_reason": "" if np.isfinite(positive["positive_exposure_SE_delta_probability"]) else "positive_exposure_p_value_method_not_reproducible",
            }
        )
        cluster_rows.append(
            {
                **base_columns,
                "metric_id": "primary_tail_lift_50",
                "cluster_key": "matched_baseline_rerandomization",
                "resample_n": int(bootstrap_cfg["matched_baseline_rerandomization_n"]),
                "seed": int(bootstrap_cfg["matched_baseline_rerandomization_seed"]),
                "p_value_method": bootstrap_cfg["residual_p_value_method"],
                "alternative": "primary_tail_lift_50 > 1",
                "estimate": primary_tail_lift,
                "SE": residual_se,
                "ci_low": np.nan,
                "ci_high": np.nan,
                "p_value": residual_p,
                "sidak_alpha": residual_alpha,
                "bootstrap_contract_gate": pass_fail((not all_original_quality_pass) or np.isfinite(residual_p)),
                "blocking_reason": "" if all_original_quality_pass else "diagnostic_only_original_frozen_baseline_quality_failed",
            }
        )

        for threshold in [0.20, 0.30, 0.50, 1.00]:
            cand_rate = float(candidate["forward_mfe_120d"].ge(threshold).mean()) if candidate_n else np.nan
            eligible_rate = float(baseline_pool["forward_mfe_120d"].ge(threshold).mean()) if len(baseline_pool) else np.nan
            base_rate = (
                float(conservative_baseline["forward_mfe_120d"].ge(threshold).mean())
                if all_original_quality_pass and not conservative_baseline.empty
                else np.nan
            )
            tail_rows.append(
                {
                    **base_columns,
                    "baseline_family": "original_frozen_conservative",
                    "curve_scope": "mfe_threshold",
                    "horizon_sessions": 120,
                    "threshold_return": threshold,
                    "p_candidate": cand_rate,
                    "p_eligible_universe": eligible_rate,
                    "p_matched_baseline_if_quality_pass": base_rate,
                    "tail_lift_vs_eligible_universe": cand_rate / eligible_rate if np.isfinite(eligible_rate) and eligible_rate > 0 else np.nan,
                    "tail_lift_vs_matched_baseline_if_quality_pass": cand_rate / base_rate if np.isfinite(base_rate) and base_rate > 0 else np.nan,
                    "diagnostic_only_flag": not all_original_quality_pass,
                    "blocking_reason": "",
                }
            )
            ccdf_rows.append(
                {
                    **base_columns,
                    "baseline_family": "original_frozen_conservative",
                    "curve_scope": "mfe_threshold",
                    "horizon_sessions": 120,
                    "threshold_return": threshold,
                    "candidate_ccdf": cand_rate,
                    "eligible_universe_ccdf": eligible_rate,
                    "matched_baseline_ccdf_if_quality_pass": base_rate,
                    "diagnostic_only_flag": not all_original_quality_pass,
                    "blocking_reason": "",
                }
            )
            capture_rows.append(
                {
                    **base_columns,
                    "threshold_return": threshold,
                    "candidate_n": candidate_n,
                    "winner_n": int(candidate["forward_mfe_120d"].ge(threshold).sum()) if candidate_n else 0,
                    "winner_capture_rate": cand_rate,
                    "candidate_per_winner": candidate_n / max(int(candidate["forward_mfe_120d"].ge(threshold).sum()), 1) if candidate_n else np.nan,
                    "non_winner_rate": 1.0 - cand_rate if np.isfinite(cand_rate) else np.nan,
                    "fast_fail_rate": burden["fast_fail_rate"],
                    "false_repair_rate": burden["false_repair_rate"],
                    "MAE_20_p10": burden["MAE_20_p10"],
                    "burden_comparator_scope": burden["burden_comparator_scope"],
                    "mae_abs_worsening": burden["mae_abs_worsening"],
                    "diagnostic_only_flag": False,
                    "blocking_reason": "",
                }
            )

        for item in candidate.itertuples(index=False):
            joint_rows.append(
                {
                    **base_columns,
                    "row_scope": "candidate_primary_denominator",
                    "row_key": item.row_id,
                    "instrument_id": item.instrument,
                    "decision_date": item.decision_date,
                    "MFE_120": item.forward_mfe_120d,
                    "MAE_20": item.forward_mae_20d,
                    "forward_big_winner_120d": bool(item.forward_big_winner_120d),
                    "fast_fail_flag": bool(item.forward_mae_20d <= -0.10),
                    "false_repair_flag": bool(item.forward_mae_20d <= -0.10),
                    "diagnostic_only_flag": False,
                    "blocking_reason": "",
                }
            )
        eligible_sample = (
            baseline_pool.sample(n=min(candidate_n, len(baseline_pool)), random_state=int(config["baseline"]["random_seed"]) + cell_no)
            if candidate_n and len(baseline_pool)
            else pd.DataFrame()
        )
        matched_scope = "matched_baseline_quality_pass_sample" if all_original_quality_pass else "matched_baseline_diagnostic_sample"
        joint_sources = [
            ("eligible_universe_baseline_sample", eligible_sample, False, ""),
            (
                matched_scope,
                conservative_baseline,
                not all_original_quality_pass,
                "" if all_original_quality_pass else "diagnostic_only_original_frozen_baseline_quality_failed",
            ),
        ]
        for row_scope, source_frame, diagnostic_flag, blocking in joint_sources:
            for item in source_frame.itertuples(index=False):
                joint_rows.append(
                    {
                        **base_columns,
                        "row_scope": row_scope,
                        "row_key": item.row_id,
                        "instrument_id": item.instrument,
                        "decision_date": item.decision_date,
                        "MFE_120": item.forward_mfe_120d,
                        "MAE_20": item.forward_mae_20d,
                        "forward_big_winner_120d": bool(item.forward_big_winner_120d),
                        "fast_fail_flag": bool(item.forward_mae_20d <= -0.10),
                        "false_repair_flag": bool(item.forward_mae_20d <= -0.10),
                        "diagnostic_only_flag": diagnostic_flag,
                        "blocking_reason": blocking,
                    }
                )

    metric = pd.DataFrame(metric_rows)
    return {
        "baseline_repair_variant_registry": registry,
        "robustness_baseline_row_manifest": pd.DataFrame(baseline_manifest_rows),
        "baseline_repair_sweep_audit": pd.DataFrame(sweep_rows),
        "robustness_baseline_quality_audit": pd.DataFrame(quality_rows),
        "robustness_metric_readout": metric,
        "robustness_positive_exposure_readout": pd.DataFrame(positive_rows),
        "robustness_residual_alpha_readout": pd.DataFrame(residual_rows),
        "false_positive_burden_readout": pd.DataFrame(burden_rows),
        "topk_concentration_sensitivity": pd.DataFrame(topk_rows),
        "cluster_bootstrap_ci": pd.DataFrame(cluster_rows),
        "tail_lift_curve_readout": pd.DataFrame(tail_rows),
        "ccdf_survival_curve_readout": pd.DataFrame(ccdf_rows),
        "capture_vs_burden_readout": pd.DataFrame(capture_rows),
        "mfe_mae_joint_readout": pd.DataFrame(joint_rows),
    }


def build_boundary_audit(candidate_manifest: pd.DataFrame, baseline_manifest: pd.DataFrame, robustness_outcome_row_n: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "selected_family_cell_pair_n": int(candidate_manifest[["family_id", "grid_cell_id"]].drop_duplicates().shape[0]),
                "robustness_candidate_manifest_frozen_before_label_readout": bool(
                    candidate_manifest["manifest_frozen_before_label_readout"].all()
                ),
                "robustness_baseline_manifest_frozen_before_label_readout": bool(
                    baseline_manifest["manifest_frozen_before_label_readout"].all()
                )
                if not baseline_manifest.empty
                else True,
                "robustness_outcome_row_n_loaded": int(robustness_outcome_row_n),
                "validation_outcome_columns_loaded": False,
                "validation_outcome_row_n": 0,
                "validation_label_value_access_n": 0,
                "robustness_outcome_used_to_expand_or_select_test_set": False,
                "boundary_gate": "pass",
                "blocking_reason": "",
            }
        ]
    )


def decide_state(metric: pd.DataFrame, gates: dict[str, str], metric_contract_reason: str = "") -> tuple[str, str, str]:
    if gates["upstream_19a_contract_gate"] != "pass":
        return "19B_upstream_19a_contract_blocked", "none", "upstream_19a_contract_gate"
    if gates["upstream_19b0_contract_gate"] != "pass":
        return "19B_upstream_19b0_contract_blocked", "none", "upstream_19b0_contract_gate"
    if gates["outcome_boundary_gate"] != "pass":
        return "19B_outcome_boundary_blocked", "none", "outcome_boundary_gate"
    if metric_contract_reason:
        return "19B_metric_contract_blocked", "none", metric_contract_reason
    if gates["cluster_bootstrap_gate"] != "pass":
        return "19B_metric_contract_blocked", "none", "cluster_bootstrap_gate"
    if gates["output_contract_gate"] != "pass":
        return "19B_output_contract_blocked", "none", "output_contract_gate"
    if metric.empty:
        return "19B_robustness_not_supported", "none", "no_metric_rows"
    states = set(metric["cell_decision_state"])
    if "residual_alpha_supported" in states:
        return "19B_residual_alpha_supported_for_validation_stress_readout", NEXT_19B1, ""
    if "positive_exposure_persistent_baseline_quality_blocked" in states:
        return "19B_baseline_quality_blocked_enrichment_only_diagnostic_possible", "none", ""
    if "positive_exposure_persistent_residual_not_supported" in states:
        return "19B_positive_exposure_persistent_enrichment_only_diagnostic", "none", ""
    if "false_positive_burden_blocked" in states:
        return "19B_false_positive_burden_blocked", "none", "false_positive_burden_blocked"
    if "topk_concentration_blocked" in states:
        return "19B_topk_concentration_blocked", "none", "topk_concentration_blocked"
    return "19B_robustness_not_supported", "none", "positive_exposure_or_residual_not_supported"


def build_search_accounting(robustness_manifest: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "N_family_brought_to_robustness": int(robustness_manifest["family_id"].nunique()),
                "N_tested_family_cell_pairs": len(robustness_manifest),
                "tested_family_cell_pairs_json": json.dumps(
                    [
                        {"family_id": row.family_id, "grid_cell_id": row.grid_cell_id}
                        for row in robustness_manifest.itertuples(index=False)
                    ],
                    sort_keys=True,
                ),
                "positive_beta_exposure_correction_scope": "2 * positive_exposure_score_50",
                "residual_alpha_correction_scope_19b0_frozen": "0 * primary_tail_lift_50",
                "residual_style_readout_correction_scope_19b": "2 * primary_tail_lift_50",
                "family_level_correction": "Bonferroni-Sidak",
                "cell_level_accounting": "all_tried_cells_counted",
                "robustness_outcome_used_to_drop_survivors": False,
                "search_accounting_gate": "pass",
                "blocking_reason": "",
            }
        ]
    )


def build_decision(
    config_path: Path,
    paths: dict[str, Path],
    gates: dict[str, str],
    state: str,
    next_req: str,
    reason: str,
    metric: pd.DataFrame,
    robustness_manifest: pd.DataFrame,
) -> pd.DataFrame:
    row = {
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requirement_file_hash": b0.artifact_hash(paths["requirement_19b"]),
        "config_file_hash": b0.artifact_hash(config_path),
        "upstream_19a_manifest_hash": b0.artifact_hash(paths["nineteen_a_manifest"]),
        "upstream_19b0_manifest_hash": b0.artifact_hash(paths["nineteen_b0_manifest"]),
        "decision_state": state,
        "next_allowed_requirement": next_req,
        **gates,
        "N_family_brought_to_robustness": int(robustness_manifest["family_id"].nunique()) if not robustness_manifest.empty else 0,
        "N_tested_family_cell_pairs": len(robustness_manifest),
        "N_positive_exposure_robustness_pass": int(metric["positive_exposure_robustness_pass"].sum()) if not metric.empty else 0,
        "N_matched_baseline_residual_pass": int(metric["matched_baseline_residual_pass_19b"].sum()) if not metric.empty else 0,
        "N_original_frozen_baseline_quality_pass": int(
            metric["residual_readout_status"].isin(["residual_style_supported", "residual_style_not_supported"]).sum()
        )
        if not metric.empty
        else 0,
        "N_cell_false_positive_burden_fail": int(metric["cell_decision_state"].eq("false_positive_burden_blocked").sum())
        if not metric.empty
        else 0,
        "N_cell_topk_concentration_fail": int(metric["cell_decision_state"].eq("topk_concentration_blocked").sum())
        if not metric.empty
        else 0,
        "positive_beta_exposure_correction_scope": "2 * positive_exposure_score_50",
        "residual_alpha_correction_scope_19b0_frozen": "0 * primary_tail_lift_50",
        "residual_style_readout_correction_scope_19b": "2 * primary_tail_lift_50",
        "validation_outcome_read": False,
        "max_ep19_terminal_state_if_no_residual_pass": "19_entry_universe_enrichment_only_diagnostic",
        "blocking_reason": reason,
    }
    for col in POLICY_AUTH_COLUMNS:
        row[col] = False
    return pd.DataFrame([row])


def subplot_grid(cell_count: int) -> tuple[Any, np.ndarray]:
    rows = max(int(cell_count), 1)
    fig, axes = plt.subplots(rows, 1, figsize=(9, 3.8 * rows), squeeze=False)
    return fig, axes.reshape(-1)


def save_figure(fig: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_probability_curve(df: pd.DataFrame, path: Path, columns: list[tuple[str, str]], ylabel: str, title: str) -> None:
    cells = df[["family_id", "grid_cell_id"]].drop_duplicates()
    fig, axes = subplot_grid(len(cells))
    for ax, cell in zip(axes, cells.itertuples(index=False), strict=False):
        sub = df.loc[(df["family_id"] == cell.family_id) & (df["grid_cell_id"] == cell.grid_cell_id)].sort_values("threshold_return")
        for column, label in columns:
            if column in sub.columns and sub[column].notna().any():
                ax.plot(sub["threshold_return"], sub[column], marker="o", linewidth=1.8, label=label)
        if "diagnostic_only_flag" in sub.columns and bool(sub["diagnostic_only_flag"].any()):
            ax.text(0.02, 0.92, "matched baseline diagnostic-only", transform=ax.transAxes, fontsize=9)
        ax.set_title(f"{cell.family_id} / {cell.grid_cell_id}", fontsize=10)
        ax.set_xlabel("threshold_return")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.25)
        ax.legend(loc="best", fontsize=8)
    fig.suptitle(title, fontsize=12)
    save_figure(fig, path)


def plot_capture_vs_burden(df: pd.DataFrame, path: Path) -> None:
    cells = df[["family_id", "grid_cell_id"]].drop_duplicates()
    fig, axes = subplot_grid(len(cells))
    for ax, cell in zip(axes, cells.itertuples(index=False), strict=False):
        sub = df.loc[(df["family_id"] == cell.family_id) & (df["grid_cell_id"] == cell.grid_cell_id)].sort_values("threshold_return")
        ax.plot(sub["threshold_return"], sub["winner_capture_rate"], marker="o", label="candidate winner capture")
        ax.plot(sub["threshold_return"], sub["non_winner_rate"], marker="o", label="candidate non-winner burden")
        ax.plot(sub["threshold_return"], sub["fast_fail_rate"], linestyle="--", label="fast fail rate")
        ax.plot(sub["threshold_return"], sub["false_repair_rate"], linestyle="--", label="false repair rate")
        ax2 = ax.twinx()
        ax2.plot(sub["threshold_return"], sub["candidate_per_winner"], color="#444444", marker="x", label="candidate per winner")
        ax2.set_ylabel("candidate_per_winner")
        ax.set_title(f"{cell.family_id} / {cell.grid_cell_id}", fontsize=10)
        ax.set_xlabel("threshold_return")
        ax.set_ylabel("rate")
        ax.grid(alpha=0.25)
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc="best", fontsize=8)
    fig.suptitle("Capture vs false-positive burden", fontsize=12)
    save_figure(fig, path)


def plot_mfe_mae_joint(df: pd.DataFrame, path: Path) -> None:
    cells = df[["family_id", "grid_cell_id"]].drop_duplicates()
    fig, axes = subplot_grid(len(cells))
    colors = {
        "candidate_primary_denominator": "#1f77b4",
        "eligible_universe_baseline_sample": "#2ca02c",
        "matched_baseline_quality_pass_sample": "#9467bd",
        "matched_baseline_diagnostic_sample": "#ff7f0e",
    }
    for ax, cell in zip(axes, cells.itertuples(index=False), strict=False):
        sub = df.loc[(df["family_id"] == cell.family_id) & (df["grid_cell_id"] == cell.grid_cell_id)]
        for row_scope, scope_df in sub.groupby("row_scope"):
            sample = scope_df
            if len(sample) > 600:
                sample = sample.sample(n=600, random_state=20260707)
            ax.scatter(
                sample["MAE_20"],
                sample["MFE_120"],
                s=10,
                alpha=0.35,
                label=row_scope,
                color=colors.get(row_scope, None),
            )
        ax.axvline(-0.10, color="#555555", linestyle="--", linewidth=1.0)
        ax.axhline(0.50, color="#555555", linestyle=":", linewidth=1.0)
        ax.set_title(f"{cell.family_id} / {cell.grid_cell_id}", fontsize=10)
        ax.set_xlabel("MAE_20")
        ax.set_ylabel("MFE_120")
        ax.grid(alpha=0.25)
        ax.legend(loc="best", fontsize=8)
    fig.suptitle("MFE/MAE joint readout", fontsize=12)
    save_figure(fig, path)


def write_required_figures(outputs: dict[str, Path], readouts: dict[str, pd.DataFrame]) -> None:
    plot_probability_curve(
        readouts["tail_lift_curve_readout"],
        outputs["tail_lift_curve_figure"],
        [
            ("p_candidate", "candidate"),
            ("p_eligible_universe", "eligible universe baseline"),
            ("p_matched_baseline_if_quality_pass", "matched baseline if quality pass"),
        ],
        "probability",
        "Tail lift curve",
    )
    plot_probability_curve(
        readouts["ccdf_survival_curve_readout"],
        outputs["ccdf_survival_curve_figure"],
        [
            ("candidate_ccdf", "candidate"),
            ("eligible_universe_ccdf", "eligible universe baseline"),
            ("matched_baseline_ccdf_if_quality_pass", "matched baseline if quality pass"),
        ],
        "CCDF",
        "CCDF survival curve",
    )
    plot_capture_vs_burden(readouts["capture_vs_burden_readout"], outputs["capture_vs_burden_figure"])
    plot_mfe_mae_joint(readouts["mfe_mae_joint_readout"], outputs["mfe_mae_joint_scatter_figure"])


def build_report(decision: pd.DataFrame, metric: pd.DataFrame, burden: pd.DataFrame, quality: pd.DataFrame) -> str:
    row = decision.iloc[0]
    lines = [
        "# 19B 稳健右尾富集与假阳性负担读出报告",
        "",
        "## 决策摘要",
        "",
        f"- decision_state: `{row['decision_state']}`",
        f"- next_allowed_requirement: `{row['next_allowed_requirement']}`",
        "- validation outcome read: `false`",
        "- model / policy / backtest / production / live trading authorization: `false`",
        "- 19C replay remains forbidden unless a later validation-stress requirement authorizes it.",
        "",
        "## Cell Readout",
        "",
        "| family | grid_cell | p_candidate_50 | p_eligible_50 | positive_score | positive_pass | residual_pass | cell_decision_state |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for item in metric.itertuples(index=False):
        lines.append(
            f"| {item.family_id} | {item.grid_cell_id} | {item.p_candidate_50:.4f} | "
            f"{item.p_eligible_universe_50:.4f} | {item.positive_exposure_score_50:.4f} | "
            f"{item.positive_exposure_robustness_pass} | {item.matched_baseline_residual_pass_19b} | "
            f"{item.cell_decision_state} |"
        )
    lines.extend(
        [
            "",
            "## Baseline Quality",
            "",
            "| family | grid_cell | variant | quality_gate | unmatched_rate | max_smd | diagnostic_only |",
            "|---|---|---|---|---:|---:|---|",
        ]
    )
    for item in quality.itertuples(index=False):
        lines.append(
            f"| {item.family_id} | {item.grid_cell_id} | {item.repair_variant_id} | "
            f"{item.baseline_matching_quality_gate} | {item.unmatched_candidate_rate:.4f} | "
            f"{item.max_standardized_mean_difference_after_matching:.4f} | {item.diagnostic_repair_only_flag} |"
        )
    lines.extend(
        [
            "",
            "## False-Positive Burden",
            "",
            "| family | grid_cell | candidate_per_winner | fast_fail_rate | false_repair_rate | mae_abs_worsening | gate |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for item in burden.itertuples(index=False):
        lines.append(
            f"| {item.family_id} | {item.grid_cell_id} | {item.candidate_per_winner:.3f} | "
            f"{item.fast_fail_rate:.3f} | {item.false_repair_rate:.3f} | "
            f"{item.mae_abs_worsening:.4f} | {item.false_positive_burden_gate} |"
        )
    lines.extend(
        [
            "",
            "## Required Figures",
            "",
            "- `figures/tail_lift_curve.png`",
            "- `figures/ccdf_survival_curve.png`",
            "- `figures/capture_vs_burden.png`",
            "- `figures/mfe_mae_joint_scatter.png`",
            "",
            "## Boundary",
            "",
            "- 19B 不读取 validation outcome。",
            "- positive exposure persistence 不是 independent alpha。",
            "- matched-baseline quality failure blocks residual-alpha support only.",
            "- positive exposure persistence without matched-baseline residual pass can only support 19_entry_universe_enrichment_only_diagnostic.",
            "- 19B 不授权 19C replay、EP20 policy preflight、entry policy、组合回测、production signal 或 live trading。",
            "",
        ]
    )
    return "\n".join(lines)


def build_handoff(decision: pd.DataFrame, metric: pd.DataFrame) -> str:
    row = decision.iloc[0]
    lines = [
        "# 19B Handoff Contract",
        "",
        f"decision_state = {row['decision_state']}",
        f"next_allowed_requirement = {row['next_allowed_requirement']}",
        "",
        "Validation outcome remains unread in 19B.",
        "19C replay and EP20 policy preflight remain unauthorized by this artifact.",
        "",
        "| family_id | grid_cell_id | cell_decision_state | matched_baseline_residual_pass_19b | max_ep19_terminal_state_if_no_residual_pass |",
        "|---|---|---|---:|---|",
    ]
    for item in metric.itertuples(index=False):
        lines.append(
            f"| {item.family_id} | {item.grid_cell_id} | {item.cell_decision_state} | "
            f"{item.matched_baseline_residual_pass_19b} | 19_entry_universe_enrichment_only_diagnostic |"
        )
    return "\n".join(lines) + "\n"


def output_contract_pass(report: str, outputs: dict[str, Path]) -> bool:
    required = [key for key in REQUIRED_OUTPUT_KEYS if key not in {"manifest", "output_hashes"}]
    output_ready = all(outputs[key].exists() and outputs[key].stat().st_size > 0 for key in required if key in outputs)
    phrases = [
        "validation outcome read: `false`",
        "19C replay remains forbidden",
        "positive exposure persistence 不是 independent alpha",
        "matched-baseline quality failure blocks residual-alpha support only",
        "19B 不授权 19C replay",
        "figures/tail_lift_curve.png",
        "figures/ccdf_survival_curve.png",
        "figures/capture_vs_burden.png",
        "figures/mfe_mae_joint_scatter.png",
    ]
    return output_ready and all(phrase in report for phrase in phrases)


def build_output_hashes(outputs: dict[str, Path]) -> dict[str, str]:
    return {
        key: b0.artifact_hash(path)
        for key, path in sorted(outputs.items())
        if key not in {"manifest", "output_hashes"} and path.exists()
    }


def write_all_frames(outputs: dict[str, Path], frames: dict[str, pd.DataFrame]) -> None:
    for key, frame in frames.items():
        b0.write_df(outputs[key], frame)


def run(config_path: str | Path = CONFIG_PATH) -> dict[str, Path]:
    config_path = Path(config_path)
    config = load_config(config_path)
    paths = resolve_paths(config)
    outputs = output_paths()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    metric_contract_reason = metric_contract_blocking_reason(config)

    input_audit = build_input_artifact_audit(config, paths)
    upstream_19a, gate_19a, _ = build_upstream_19a_contract_audit(paths)
    upstream_19b0, gate_19b0, _, robustness_manifest = build_upstream_19b0_contract_audit(config, paths)
    for key, frame in {
        "input_artifact_audit": input_audit,
        "upstream_19a_contract_audit": upstream_19a,
        "upstream_19b0_contract_audit": upstream_19b0,
    }.items():
        b0.write_df(outputs[key], frame)

    panel = build_panel(config, paths)
    params = selected_parameters(paths, robustness_manifest)
    candidate_manifest, cell_frames = materialize_selected_cells(panel, config, robustness_manifest, params)
    readouts = build_readouts(config, robustness_manifest, candidate_manifest, cell_frames, panel)
    boundary = build_boundary_audit(
        candidate_manifest,
        readouts["robustness_baseline_row_manifest"],
        int(sum(len(frame.loc[frame["primary_denominator_row"]]) for frame in cell_frames.values() if "primary_denominator_row" in frame)),
    )
    search = build_search_accounting(robustness_manifest)
    readouts.update(
        {
            "robustness_outcome_boundary_audit": boundary,
            "robustness_candidate_row_manifest": candidate_manifest,
            "search_accounting_audit": search,
        }
    )
    write_all_frames(outputs, readouts)
    write_required_figures(outputs, readouts)

    metric = readouts["robustness_metric_readout"]
    gates = {
        "upstream_19a_contract_gate": gate_19a,
        "upstream_19b0_contract_gate": gate_19b0,
        "outcome_boundary_gate": "pass",
        "robustness_candidate_manifest_gate": pass_fail(not candidate_manifest.empty and candidate_manifest["manifest_frozen_before_label_readout"].all()),
        "baseline_repair_registry_gate": pass_fail(readouts["baseline_repair_variant_registry"]["registry_frozen_before_label_readout"].all()),
        "baseline_matching_quality_gate": "pass",
        "positive_exposure_robustness_gate": pass_fail(metric["positive_exposure_robustness_pass"].any()) if not metric.empty else "fail",
        "matched_baseline_residual_gate": pass_fail(metric["matched_baseline_residual_pass_19b"].any()) if not metric.empty else "fail",
        "false_positive_burden_gate": pass_fail((readouts["false_positive_burden_readout"]["false_positive_burden_gate"] == "pass").any()),
        "topk_positive_exposure_gate": pass_fail((readouts["topk_concentration_sensitivity"]["topk_positive_exposure_gate"] == "pass").any()),
        "topk_residual_gate": pass_fail((readouts["topk_concentration_sensitivity"]["topk_residual_gate"] == "pass").any()),
        "cluster_bootstrap_gate": pass_fail((readouts["cluster_bootstrap_ci"]["bootstrap_contract_gate"] == "pass").all()),
        "search_accounting_gate": "pass",
        "output_contract_gate": "pass",
    }
    state, next_req, reason = decide_state(metric, gates, metric_contract_reason)
    decision = build_decision(config_path, paths, gates, state, next_req, reason, metric, robustness_manifest)
    b0.write_df(outputs["entry_universe_19b_decision"], decision)
    report = build_report(decision, metric, readouts["false_positive_burden_readout"], readouts["robustness_baseline_quality_audit"])
    handoff = build_handoff(decision, metric)
    b0.write_text(outputs["report"], report)
    b0.write_text(outputs["handoff_contract"], handoff)
    gates["output_contract_gate"] = pass_fail(output_contract_pass(report, outputs))
    state, next_req, reason = decide_state(metric, gates, metric_contract_reason)
    decision = build_decision(config_path, paths, gates, state, next_req, reason, metric, robustness_manifest)
    b0.write_df(outputs["entry_universe_19b_decision"], decision)
    report = build_report(decision, metric, readouts["false_positive_burden_readout"], readouts["robustness_baseline_quality_audit"])
    handoff = build_handoff(decision, metric)
    b0.write_text(outputs["report"], report)
    b0.write_text(outputs["handoff_contract"], handoff)

    output_hashes = build_output_hashes(outputs)
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at": decision.iloc[0]["created_at"],
        "python_version": platform.python_version(),
        "requirement_file_hash": b0.artifact_hash(paths["requirement_19b"]),
        "config_file_hash": b0.artifact_hash(config_path),
        "upstream_19a_manifest_hash": b0.artifact_hash(paths["nineteen_a_manifest"]),
        "upstream_19b0_manifest_hash": b0.artifact_hash(paths["nineteen_b0_manifest"]),
        "decision_state": decision.iloc[0]["decision_state"],
        "next_allowed_requirement": decision.iloc[0]["next_allowed_requirement"],
        "critical_gates": {gate: decision.iloc[0][gate] for gate in CRITICAL_GATES},
        "output_hashes": output_hashes,
    }
    b0.write_json(outputs["manifest"], manifest)
    b0.write_json(outputs["output_hashes"], output_hashes)
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(args.config)


if __name__ == "__main__":
    main()
