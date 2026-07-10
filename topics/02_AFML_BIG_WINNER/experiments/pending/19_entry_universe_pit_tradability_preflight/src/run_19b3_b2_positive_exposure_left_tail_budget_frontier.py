#!/usr/bin/env python
"""Staged, fail-closed runner for the EP19B3 left-tail budget frontier."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

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
RUN_ID = "19B3_b2_positive_exposure_left_tail_budget_frontier"
EXPERIMENT_ID = "19_entry_universe_pit_tradability_preflight"
PHASE_ID = "19B3"
CONFIG_PATH = EXPERIMENT_DIR / "configs/config_19b3_b2_positive_exposure_left_tail_budget_frontier.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_19b3_b2_positive_exposure_left_tail_budget_frontier.md"
OUTPUT_ROOT = EXPERIMENT_DIR / "outputs" / RUN_ID

ARM_IDS = [
    "R0_S0_UNTRIMMED",
    "R1_ATR20_TOP10_TRIM",
    "R2_VOL60_TOP30_TRIM",
    "R3_CONTINUOUS_VOL_BUDGET",
]
PRIMARY_ARM = "R2_VOL60_TOP30_TRIM"
PLACEBO_ARM = "P0_R2_SAME_DAY_RANDOM_TRIM"
ARM_ROLES = {
    "R0_S0_UNTRIMMED": "baseline",
    "R1_ATR20_TOP10_TRIM": "mild_static_comparator",
    "R2_VOL60_TOP30_TRIM": "only_primary_candidate_and_simple_incumbent",
    "R3_CONTINUOUS_VOL_BUDGET": "smooth_budget_diagnostic_challenger",
    PLACEBO_ARM: "R2_same-day_same-budget_placebo",
}
AUTHORIZATION_COLUMNS = [
    "model_training_authorized",
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
    "19C_replay_authorized",
    "EP20_policy_preflight_authorized",
]
FORBIDDEN_PREOUTCOME_TOKENS = (
    "mfe",
    "mae",
    "forward_return",
    "forward_big_winner",
    "right_tail",
    "left_tail",
    "right_clean",
    "left_bad",
    "outcome_group",
    "arm_decision",
    "validation_metric",
)

CANDIDATE_SCHEMA = [
    "run_id", "candidate_id", "instrument", "decision_date", "entry_date", "decision_month",
    "instrument_month", "board_bucket", "family_id", "grid_cell_id", "membership_rule_hash",
    "eligible_universe_row_count", "b2_candidate_row_count", "candidate_denominator_id",
    "return_20d_stock", "return_20d_benchmark", "stock_vs_market_20d", "return_60d",
    "return_60d_rank_pct", "close_to_ema60", "vol60", "atr20", "q_vol60", "q_atr20",
    "median_vol60_asof_t0", "fill_feasible", "cooldown_eligible", "path_end_date_20",
    "path_end_date_120", "forward_120_complete", "preoutcome_feature_hash",
]
ELIGIBLE_SCHEMA = [
    "run_id", "eligible_candidate_id", "instrument", "decision_date", "entry_date", "decision_month",
    "instrument_month", "board_bucket", "fill_feasible", "cooldown_eligible", "path_end_date_20",
    "path_end_date_120", "forward_120_complete", "N_eligible_d", "vol60", "atr20",
    "eligible_row_weight_R0", "eligible_row_weight_R1", "eligible_row_weight_R2",
    "eligible_row_weight_R3", "preoutcome_feature_hash",
]
WEIGHT_SCHEMA = [
    "candidate_id", "arm_id", "arm_role", "is_retained", "raw_weight", "final_weight",
    "cash_weight", "weight_formula_id", "threshold_source_scope", "threshold_value",
    "preoutcome_manifest_hash",
]
OUTCOME_SCHEMA = [
    "candidate_id", "instrument", "decision_date", "path_end_date_20", "path_end_date_120",
    "forward_120_complete", "MFE_120", "MAE_20", "right_tail_50_flag", "left_tail_10_flag",
    "left_tail_20_flag", "left_tail_30_flag", "outcome_source_hash", "freeze_preoutcome_manifest_hash",
]
ELIGIBLE_OUTCOME_SCHEMA = [
    "eligible_candidate_id", "instrument", "decision_date", "path_end_date_20", "path_end_date_120",
    "forward_120_complete", "MFE_120", "MAE_20", "right_tail_50_flag", "left_tail_10_flag",
    "left_tail_20_flag", "left_tail_30_flag", "eligible_row_weight_R0", "eligible_row_weight_R1",
    "eligible_row_weight_R2", "eligible_row_weight_R3", "outcome_source_hash",
    "freeze_preoutcome_manifest_hash",
]
ARM_TAIL_SCHEMA = [
    "sample_scope", "arm_id", "candidate_n_raw", "candidate_n_retained", "instrument_n",
    "decision_month_n", "weight_sum", "weight_sq_sum", "kish_effective_n", "p_candidate_50_after",
    "p_eligible_50_arm_matched", "positive_exposure_ratio_50_primary_arm_calendar_matched",
    "p_eligible_50_unweighted_same_dates", "positive_exposure_ratio_50_legacy_bridge",
    "positive_exposure_ratio_denominator_bridge_delta", "right_tail_capture_retention",
    "top_tail_payoff_contribution_retention", "weighted_ES10_MAE20", "weighted_MAE20_p10",
    "weighted_p_left_tail_10", "weighted_p_left_tail_20", "weighted_p_left_tail_30",
    "eligible_weighted_MAE20_p10_arm_matched", "ES10_improvement_vs_R0",
    "MAE_p10_improvement_vs_R0", "p_left_tail_20_relative_reduction_vs_R0",
    "absolute_left_tail_burden_gap_vs_eligible", "support_gate", "right_tail_budget_gate",
]
PAIRWISE_SCHEMA = [
    "sample_scope", "comparison_id", "arm_id", "comparator_arm_id", "ES10_improvement",
    "ES10_improvement_ci_low", "ES10_improvement_ci_high", "MAE_p10_improvement",
    "MAE_p10_improvement_ci_low", "MAE_p10_improvement_ci_high", "p_left_tail_relative_reduction",
    "p_left_tail_relative_reduction_ci_low", "p_left_tail_relative_reduction_ci_high",
    "positive_exposure_ratio_50_primary_arm_calendar_matched",
    "positive_exposure_ratio_50_primary_ci_low", "positive_exposure_ratio_50_primary_ci_high",
    "positive_exposure_ratio_50_legacy_bridge", "right_tail_capture_retention",
    "right_tail_capture_retention_ci_low", "right_tail_capture_retention_ci_high", "pairwise_gate",
]
BOOTSTRAP_SCHEMA = ["replication_id", "metric_id", "metric_value", "seed", "cluster_key"]
MONTH_SCHEMA = [
    "excluded_decision_month", "candidate_n", "ES10_improvement_R2_vs_R0",
    "MAE_p10_improvement_R2_vs_R0", "direction_pass",
]
PLACEBO_SCHEMA = [
    "replication_id", "assignment_hash", "assignment_hash_gate", "placebo_ES10",
    "placebo_ES10_improvement_vs_R0", "R2_ES10_improvement_vs_R0",
    "placebo_at_least_as_good_as_R2", "primary_strata_n", "fallback_strata_n",
    "unchanged_strata_n", "date_gross_invariance_gate", "seed",
]
SUPPORT_CONCENTRATION_SCHEMA = [
    "sample_scope", "arm_id", "max_instrument_weight_share", "max_instrument_right_tail_weight_share",
    "max_instrument_month_weight_share", "max_decision_month_weight_share",
    "top1_removal_sensitivity_gate", "top3_removal_sensitivity_gate", "calendar_evaluable_month_n",
    "calendar_direction_stable_rate", "concentration_gate",
]
OUTCOME_ACCESS_SCHEMA = [
    "run_id", "stage", "accessed_at", "dataset_role", "split", "date_min", "date_max",
    "artifact_path", "artifact_sha256", "columns_read", "access_authorized",
    "authorization_artifact", "authorization_artifact_hash", "purpose", "selection_or_tuning_allowed",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run staged EP19B3 left-tail budget frontier.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--stage", required=True, choices=["freeze", "forward", "validation-stress", "finalize"])
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    text = str(value)
    if text.startswith("..."):
        text = "experiments/pending/19_entry_universe_pit_tradability_preflight" + text[3:]
    path = Path(text)
    if path.is_absolute():
        return path
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("experiments/", "data/")):
        return TOPIC_ROOT / path
    return EXPERIMENT_DIR / path


def resolve_input_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("input_paths", {}).items()}


def resolve_output_root(config: dict[str, Any]) -> Path:
    return topic_path(config.get("output", {}).get("output_root", OUTPUT_ROOT))


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dataframe_hash(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def candidate_id(instrument: str, decision_date: str, entry_date: str, family_id: str, grid_cell_id: str) -> str:
    return hashlib.sha256(f"{instrument}|{decision_date}|{entry_date}|{family_id}|{grid_cell_id}".encode()).hexdigest()


def safe_div(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator and math.isfinite(float(denominator)) else float("nan")


def as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "pass", "yes"}


def json_read(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    if columns is not None:
        for column in columns:
            if column not in out:
                out[column] = np.nan
        out = out[columns]
    out.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")


def fsync_path(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def weighted_probability(weight: Iterable[float], values: Iterable[float]) -> float:
    w = np.asarray(list(weight), dtype=float)
    y = np.asarray(list(values), dtype=float)
    valid = np.isfinite(w) & np.isfinite(y) & (w >= 0)
    total = float(w[valid].sum())
    return safe_div(float(np.dot(w[valid], y[valid])), total)


def weighted_es10(weight: Iterable[float], mae20: Iterable[float], row_key: Iterable[str], alpha: float = 0.10) -> float:
    frame = pd.DataFrame({"w": list(weight), "mae": list(mae20), "key": list(row_key)})
    frame["loss"] = np.maximum(0.0, -pd.to_numeric(frame["mae"], errors="coerce"))
    frame["w"] = pd.to_numeric(frame["w"], errors="coerce")
    frame = frame.loc[frame["w"].ge(0) & frame["w"].notna() & frame["loss"].notna()].copy()
    total = float(frame["w"].sum())
    target = alpha * total
    if target <= 0:
        return float("nan")
    frame = frame.sort_values(["loss", "key"], ascending=[False, True], kind="mergesort")
    remaining = target
    numerator = 0.0
    for row in frame.itertuples(index=False):
        consumed = min(float(row.w), remaining)
        numerator += consumed * float(row.loss)
        remaining -= consumed
        if remaining <= 1e-15:
            break
    return numerator / target if remaining <= 1e-10 else float("nan")


def weighted_quantile_step(weight: Iterable[float], values: Iterable[float], row_key: Iterable[str], q: float = 0.10) -> float:
    frame = pd.DataFrame({"w": list(weight), "value": list(values), "key": list(row_key)})
    frame["w"] = pd.to_numeric(frame["w"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.loc[frame["w"].ge(0) & frame["w"].notna() & frame["value"].notna()].copy()
    total = float(frame["w"].sum())
    if total <= 0:
        return float("nan")
    frame = frame.sort_values(["value", "key"], ascending=[True, True], kind="mergesort")
    cumulative = frame["w"].cumsum().to_numpy()
    position = int(np.searchsorted(cumulative, q * total, side="left"))
    return float(frame.iloc[min(position, len(frame) - 1)]["value"])


def kish_effective_n(weight: Iterable[float]) -> float:
    w = np.asarray(list(weight), dtype=float)
    w = w[np.isfinite(w) & (w >= 0)]
    return safe_div(float(w.sum() ** 2), float(np.square(w).sum()))


def empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def stage_paths(root: Path, stage: str) -> dict[str, Path]:
    if stage == "freeze":
        base = root / "freeze"
        names = [
            "resolved_config.yaml", "human_restart_authorization.json", "contract_freeze_19b3.json",
            "source_artifact_hash_audit.csv", "input_artifact_audit.csv", "upstream_contract_audit.csv",
            "spent_design_arm_role_audit.csv", "data_coverage_and_forward_support_audit.csv",
            "search_accounting_audit.csv", "forward_candidate_preoutcome_manifest.csv",
            "forward_eligible_preoutcome_manifest.csv", "forward_arm_weight_manifest.csv",
            "p0_permutation_assignment_hashes.csv", "b2_arm_registry.csv", "outcome_access_audit.csv",
            "freeze_manifest_19b3.json", "freeze_output_hashes_19b3.json",
        ]
    elif stage == "forward":
        base = root / "forward"
        names = [
            "forward_outcome_panel.csv", "forward_eligible_outcome_panel.csv", "arm_tail_readout.csv",
            "arm_pairwise_readout.csv", "cluster_bootstrap_readout.csv", "leave_one_month_out_readout.csv",
            "placebo_null_readout.csv", "placebo_null_summary.json", "support_and_concentration_readout.csv",
            "forward_decision.json", "outcome_access_audit.csv", "forward_manifest.json",
            "forward_output_hashes.json", "figures/forward_left_tail_frontier.png",
            "figures/forward_exposure_capture_frontier.png", "figures/forward_bootstrap_improvement_distribution.png",
            "figures/forward_month_stability.png",
        ]
    elif stage == "validation-stress":
        base = root / "validation_stress"
        names = [
            "validation_candidate_preoutcome_manifest.csv", "validation_eligible_preoutcome_manifest.csv",
            "validation_arm_weight_manifest.csv", "validation_preoutcome_freeze_manifest.json",
            "validation_preoutcome_freeze_output_hashes.json", "validation_outcome_panel.csv",
            "validation_eligible_outcome_panel.csv", "validation_arm_tail_readout.csv",
            "validation_stress_decision.json", "outcome_access_audit.csv", "validation_stress_manifest.json",
            "validation_stress_output_hashes.json", "figures/validation_stress_directional_readout.png",
        ]
    else:
        base = root
        names = [
            "entry_universe_19b3_decision.csv", "outcome_access_audit.csv",
            "19B3_b2_positive_exposure_left_tail_budget_frontier_report.md", "19B3_handoff_contract.md",
            "manifest_19b3_b2_positive_exposure_left_tail_budget_frontier.json",
            "output_hashes_19b3_b2_positive_exposure_left_tail_budget_frontier.json",
        ]
    return {Path(name).stem: base / name for name in names}


def bundle_paths(root: Path, stage: str) -> tuple[Path, Path]:
    if stage == "freeze":
        return root / "freeze/freeze_manifest_19b3.json", root / "freeze/freeze_output_hashes_19b3.json"
    if stage == "forward":
        return root / "forward/forward_manifest.json", root / "forward/forward_output_hashes.json"
    if stage == "validation-stress":
        return root / "validation_stress/validation_stress_manifest.json", root / "validation_stress/validation_stress_output_hashes.json"
    return (
        root / "manifest_19b3_b2_positive_exposure_left_tail_budget_frontier.json",
        root / "output_hashes_19b3_b2_positive_exposure_left_tail_budget_frontier.json",
    )


def seal_bundle(root: Path, stage: str, manifest_payload: dict[str, Any], include: list[Path]) -> tuple[Path, Path]:
    manifest_path, hashes_path = bundle_paths(root, stage)
    unique = sorted({path.resolve() for path in include if path.exists() and path.resolve() not in {manifest_path.resolve(), hashes_path.resolve()}}, key=str)
    manifest_payload["output_hashes"] = {str(path.relative_to(root)): file_sha(path) for path in unique}
    write_json(manifest_path, manifest_payload)
    output_paths = sorted(unique + [manifest_path.resolve()], key=str)
    write_json(hashes_path, {str(path.relative_to(root)): file_sha(path) for path in output_paths})
    return manifest_path, hashes_path


def verify_bundle(root: Path, stage: str) -> tuple[bool, str]:
    manifest_path, hashes_path = bundle_paths(root, stage)
    if not manifest_path.exists() or not hashes_path.exists():
        return False, "bundle_manifest_or_hash_file_missing"
    expected = json_read(hashes_path)
    if str(hashes_path.relative_to(root)) in expected:
        return False, "output_hash_file_must_exclude_itself"
    for relative, digest in expected.items():
        path = root / relative
        if not path.exists() or file_sha(path) != digest:
            return False, f"bundle_hash_mismatch:{relative}"
    manifest = json_read(manifest_path)
    expected_manifest_hashes = {
        relative: digest for relative, digest in expected.items() if relative != str(manifest_path.relative_to(root))
    }
    return (manifest.get("output_hashes") == expected_manifest_hashes, "" if manifest.get("output_hashes") == expected_manifest_hashes else "manifest_output_hash_map_mismatch")


def verify_freeze_identity(root: Path, config_path: Path) -> tuple[bool, str]:
    manifest_path = root / "freeze/freeze_manifest_19b3.json"
    if not manifest_path.exists():
        return False, "freeze_manifest_missing"
    manifest = json_read(manifest_path)
    checks = {
        "config_file_hash": file_sha(config_path),
        "requirement_file_hash": file_sha(REQUIREMENT_PATH),
        "runner_file_hash": file_sha(Path(__file__)),
    }
    for key, observed in checks.items():
        if manifest.get(key) != observed:
            return False, f"freeze_identity_mismatch:{key}"
    return True, ""


def validate_config(config: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if config.get("run_id") != RUN_ID or config.get("experiment_id") != EXPERIMENT_ID or config.get("phase_id") != PHASE_ID:
        reasons.append("run_identity_mismatch")
    required = [
        "input_paths", "output", "primary_scope", "split", "b2_rule", "arms", "spent_design_role_audit",
        "labels", "forward_support", "forward_evaluability", "forward_gates", "positive_exposure_comparator",
        "validation_stress", "bootstrap", "placebo", "runtime",
    ]
    reasons.extend(f"missing_section:{key}" for key in required if key not in config)
    arms = config.get("arms", {})
    if arms.get("primary_arm_id") != PRIMARY_ARM or arms.get("placebo_arm_id") != PLACEBO_ARM:
        reasons.append("unregistered_primary_or_placebo_arm")
    if sorted(arms.get("comparator_arm_ids", [])) != sorted([ARM_IDS[0], ARM_IDS[1], ARM_IDS[3]]):
        reasons.append("comparator_arm_registry_mismatch")
    if float(config.get("forward_gates", {}).get("primary_positive_exposure_ratio_50_min", -1)) != float(
        config.get("positive_exposure_comparator", {}).get("primary_ratio_floor", -2)
    ):
        reasons.append("positive_exposure_ratio_floor_mismatch")
    validation = config.get("validation_stress", {})
    if int(validation.get("decision_month_n_min", 10**9)) > int(validation.get("fixed_window_decision_month_upper_bound_expected", -1)):
        reasons.append("validation_support_floor_infeasible")
    if config.get("runtime", {}).get("cache_may_contain_outcome_columns") is not False:
        reasons.append("preoutcome_cache_outcome_columns_not_forbidden")
    return ("pass" if not reasons else "fail", reasons)


def artifact_metadata(path: Path, include_schema: bool = True) -> dict[str, Any]:
    if path.is_dir():
        return {"sha256": "", "size_bytes": 0, "row_count": np.nan, "schema_hash": "", "exists": True}
    if not path.exists():
        return {"sha256": "", "size_bytes": 0, "row_count": np.nan, "schema_hash": "", "exists": False}
    schema_hash = ""
    row_count: float | int = np.nan
    if include_schema and path.suffix.lower() == ".csv":
        header = pd.read_csv(path, nrows=0).columns.tolist()
        schema_hash = stable_hash(header)
        with path.open("rb") as handle:
            row_count = max(sum(chunk.count(b"\n") for chunk in iter(lambda: handle.read(1024 * 1024), b"")) - 1, 0)
    elif include_schema and path.suffix.lower() in {".json", ".yaml", ".yml", ".md"}:
        schema_hash = stable_hash(path.suffix.lower())
    return {
        "sha256": file_sha(path),
        "size_bytes": path.stat().st_size,
        "row_count": row_count,
        "schema_hash": schema_hash,
        "exists": True,
    }


def build_source_inventory(qfq_dir: Path) -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    for path in sorted(qfq_dir.glob("*.csv")):
        meta = artifact_metadata(path)
        try:
            first = pd.read_csv(path, usecols=["date"]).iloc[0, 0]
            last = pd.read_csv(path, usecols=["date"]).iloc[-1, 0]
        except (ValueError, IndexError, pd.errors.EmptyDataError):
            first = last = ""
        rows.append(
            {
                "instrument": path.stem,
                "artifact_path": str(path.relative_to(TOPIC_ROOT)),
                "sha256": meta["sha256"],
                "size_bytes": meta["size_bytes"],
                "row_count": meta["row_count"],
                "schema_hash": meta["schema_hash"],
                "min_date": first,
                "max_date": last,
                "read_for_forward_outcome": False,
            }
        )
    frame = pd.DataFrame(rows)
    inventory_hash = stable_hash(frame.to_dict("records"))
    return frame, inventory_hash


def expected_hash_for_input(alias: str, path: Path, paths: dict[str, Path]) -> str:
    if alias.startswith("nineteen_a_"):
        hash_keys = ["nineteen_a_output_hashes"]
    elif alias.startswith("nineteen_b0_"):
        hash_keys = ["nineteen_b0_output_hashes"]
    elif alias.startswith("nineteen_b1_"):
        hash_keys = ["nineteen_b1_output_hashes"]
    elif alias.startswith("nineteen_b2_"):
        hash_keys = ["nineteen_b2_output_hashes"]
    elif alias.startswith("nineteen_b_"):
        hash_keys = ["nineteen_b_output_hashes"]
    else:
        hash_keys = []
    candidates = [alias, path.stem]
    prefixes = ["nineteen_a_", "nineteen_b0_", "nineteen_b1_", "nineteen_b2_", "nineteen_b_"]
    for prefix in prefixes:
        if alias.startswith(prefix):
            candidates.append(alias[len(prefix):])
    if path.name.startswith("manifest_"):
        candidates.append("manifest")
    for key in hash_keys:
        hash_path = paths.get(key)
        if hash_path is None or not hash_path.exists() or path == hash_path:
            continue
        values = json_read(hash_path)
        for candidate in candidates:
            if candidate in values:
                return str(values[candidate])
    return ""


def build_input_audit(paths: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    for alias, path in sorted(paths.items()):
        meta = artifact_metadata(path)
        expected = expected_hash_for_input(alias, path, paths)
        verified = bool(meta["exists"] and (not expected or meta["sha256"] == expected))
        rows.append(
            {
                "artifact_id": alias,
                "artifact_path": str(path),
                "artifact_type": "directory" if path.is_dir() else path.suffix.lstrip("."),
                "exists": meta["exists"],
                "nonempty": bool(path.is_dir() or meta["size_bytes"] > 0),
                "sha256": meta["sha256"],
                "expected_hash": expected,
                "hash_verified": verified,
                "size_bytes": meta["size_bytes"],
                "row_count": meta["row_count"],
                "schema_hash": meta["schema_hash"],
                "input_artifact_gate": "pass" if verified and (path.is_dir() or meta["size_bytes"] > 0) else "fail",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, ("pass" if frame["input_artifact_gate"].eq("pass").all() else "fail")


def build_upstream_audit(config: dict[str, Any], paths: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    scope = config["primary_scope"]
    rows: list[dict[str, Any]] = []

    def add(upstream: str, fact: str, expected: Any, observed: Any, source: Path) -> None:
        equal = bool(observed == expected)
        rows.append(
            {
                "upstream_scope": upstream,
                "required_fact": fact,
                "expected_value": expected,
                "observed_value": observed,
                "source_artifact": str(source),
                "source_sha256": file_sha(source),
                "contract_gate": "pass" if equal else "fail",
                "blocking_reason": "" if equal else f"{upstream}:{fact}:mismatch",
            }
        )

    a_decision_path = paths["nineteen_a_manifest"].parent / "entry_universe_preflight_decision.csv"
    a_decision = pd.read_csv(a_decision_path).iloc[0]
    add("19A", "all_critical_gates_pass", True, as_bool(a_decision["all_critical_gates_pass"]), a_decision_path)
    cooldown = pd.read_csv(paths["cooldown_audit"])
    add("19A", "cooldown_window_sessions", 10, int(cooldown["cooldown_window_sessions"].drop_duplicates().iloc[0]), paths["cooldown_audit"])
    split_freeze = pd.read_csv(paths["split_construction_freeze"])
    add("19A", "validation_selection_allowed", False, bool(split_freeze["validation_selection_allowed"].fillna(False).astype(bool).any()), paths["split_construction_freeze"])

    selected = pd.read_csv(paths["nineteen_b0_selected_family_cell_manifest"])
    b2_selected = selected.loc[selected["family_id"].eq(scope["family_id"])].iloc[0]
    for fact in ["family_id", "grid_cell_id", "parameter_hash"]:
        add("19B0", fact, scope[fact], b2_selected[fact], paths["nineteen_b0_selected_family_cell_manifest"])
    add("19B0", "selection_track", "positive_beta_exposure", b2_selected["selection_track"], paths["nineteen_b0_selected_family_cell_manifest"])

    b_metric = pd.read_csv(paths["nineteen_b_metric_readout"])
    b2_metric = b_metric.loc[b_metric["family_id"].eq(scope["family_id"])].iloc[0]
    add("19B", "positive_exposure_robustness_pass", True, as_bool(b2_metric["positive_exposure_robustness_pass"]), paths["nineteen_b_metric_readout"])
    add("19B", "false_positive_burden_gate", "fail", b2_metric["false_positive_burden_gate"], paths["nineteen_b_metric_readout"])
    add("19B", "cell_positive_exposure_gate", False, as_bool(b2_metric["cell_positive_exposure_gate"]), paths["nineteen_b_metric_readout"])

    b1_decision = pd.read_csv(paths["nineteen_b1_decision"]).iloc[0]
    for fact in ["family_id", "grid_cell_id", "row_scope"]:
        add("19B1", fact, scope[fact], b1_decision[fact], paths["nineteen_b1_decision"])
    add("19B1", "decision_state", "19B1_t0_left_right_tail_separable_diagnostic", b1_decision["decision_state"], paths["nineteen_b1_decision"])
    add("19B1", "validation_outcome_read", False, as_bool(b1_decision["validation_outcome_read"]), paths["nineteen_b1_decision"])
    add("19B1", "next_allowed_requirement", "none", b1_decision["next_allowed_requirement"], paths["nineteen_b1_decision"])

    b2_decision = pd.read_csv(paths["nineteen_b2_decision"]).iloc[0]
    add("19B2", "validation_outcome_read", False, as_bool(b2_decision["validation_outcome_read"]), paths["nineteen_b2_decision"])
    add("19B2", "interaction_superiority_gate", "fail", b2_decision["interaction_superiority_gate"], paths["nineteen_b2_decision"])
    add("19B2", "best_single_feature_variant_id", "A_ATR20_top10", b2_decision["best_single_feature_variant_id"], paths["nineteen_b2_decision"])
    add("19B2", "next_allowed_requirement", "none", b2_decision["next_allowed_requirement"], paths["nineteen_b2_decision"])
    frame = pd.DataFrame(rows)
    return frame, ("pass" if frame["contract_gate"].eq("pass").all() else "fail")


def human_restart_authorization(paths: dict[str, Path]) -> dict[str, Any]:
    text = paths["research_plan"].read_text(encoding="utf-8")
    checks = {
        "section_12_human_research_restart_present": "## 12. Human Research Restart" in text,
        "requirement_named": "requirement_19b3_b2_positive_exposure_left_tail_budget_frontier.md" in text,
        "validation_stress_only": "压力测试" in text and "validation" in text,
        "new_support_requires_forward_oos": "forward OOS" in text and "新" in text,
    }
    return {
        "run_id": RUN_ID,
        "restart_type": "human_research_restart",
        "restart_source": "research_plan_section_12",
        "upstream_pipeline_authorization": False,
        "checks": checks,
        "human_restart_lineage_gate": "pass" if all(checks.values()) else "fail",
        "research_plan_hash": file_sha(paths["research_plan"]),
    }


def spent_design_role_audit(config: dict[str, Any], paths: dict[str, Path]) -> tuple[pd.DataFrame, str, pd.DataFrame]:
    scope = config["primary_scope"]
    outcomes = pd.read_csv(paths["nineteen_b_mfe_mae_joint_readout"])
    sample = outcomes.loc[
        outcomes["family_id"].eq(scope["family_id"])
        & outcomes["grid_cell_id"].eq(scope["grid_cell_id"])
        & outcomes["split"].eq("robustness")
        & outcomes["row_scope"].eq(scope["row_scope"])
    ].copy()
    features = pd.read_parquet(paths["nineteen_b1_feature_panel_cache"])
    features["decision_date"] = features["decision_date"].astype(str)
    features["q_vol60"] = features.groupby("decision_date")["match_vol60"].rank(method="average", pct=True)
    features["q_atr20"] = features.groupby("decision_date")["atr_20_pct_asof_decision_date"].rank(method="average", pct=True)
    medians = features.groupby("decision_date", as_index=False)["match_vol60"].median().rename(columns={"match_vol60": "median_vol60"})
    sample = sample.merge(
        features[["instrument", "decision_date", "match_vol60", "atr_20_pct_asof_decision_date", "q_vol60", "q_atr20"]].rename(columns={"instrument": "instrument_id"}),
        on=["instrument_id", "decision_date"],
        how="left",
        validate="one_to_one",
    ).merge(medians, on="decision_date", how="left", validate="many_to_one")
    arms = config["arms"]
    r1_threshold = float(sample["q_atr20"].quantile(float(arms["r1_candidate_q_atr20_quantile"]), interpolation="linear"))
    r2_threshold = float(sample["q_vol60"].quantile(float(arms["r2_candidate_q_vol60_quantile"]), interpolation="linear"))
    weights = {
        ARM_IDS[0]: np.ones(len(sample)),
        ARM_IDS[1]: sample["q_atr20"].lt(r1_threshold).astype(float).to_numpy(),
        ARM_IDS[2]: sample["q_vol60"].lt(r2_threshold).astype(float).to_numpy(),
        ARM_IDS[3]: np.clip(
            sample["median_vol60"].to_numpy(dtype=float) / np.maximum(sample["match_vol60"].to_numpy(dtype=float), float(arms["epsilon"])),
            float(arms["continuous_weight_floor"]),
            float(arms["continuous_weight_cap"]),
        ),
    }
    right = pd.to_numeric(sample["MFE_120"], errors="coerce").ge(float(config["labels"]["right_tail_event_50"])).astype(float)
    left20 = pd.to_numeric(sample["MAE_20"], errors="coerce").le(float(config["labels"]["left_tail_event_20"])).astype(float)
    metrics: dict[str, dict[str, float]] = {}
    for arm_id, weight in weights.items():
        metrics[arm_id] = {
            "es": weighted_es10(weight, sample["MAE_20"], sample["row_key"]),
            "mae_p10": weighted_quantile_step(weight, sample["MAE_20"], sample["row_key"]),
            "p_left20": weighted_probability(weight, left20),
            "capture": safe_div(float(np.dot(weight, right)), float(right.sum())),
            "weight_sum": float(np.sum(weight)),
            "retained_n": int(np.sum(np.asarray(weight) > 0)),
        }
    expected = config["spent_design_role_audit"]
    source_hashes = json.dumps(
        {
            "outcome": file_sha(paths["nineteen_b_mfe_mae_joint_readout"]),
            "feature_panel": file_sha(paths["nineteen_b1_feature_panel_cache"]),
        },
        sort_keys=True,
    )
    rows: list[dict[str, Any]] = []
    for arm_id in ARM_IDS:
        metric = metrics[arm_id]
        threshold = r1_threshold if arm_id == ARM_IDS[1] else (r2_threshold if arm_id == ARM_IDS[2] else np.nan)
        row_gate = True
        if arm_id == ARM_IDS[2]:
            checks = [
                (r2_threshold, expected["expected_R2_candidate_q_vol60_p70"]),
                (metric["retained_n"], expected["expected_R2_retained_n"]),
                (metric["weight_sum"], expected["expected_R2_weight_sum"]),
                (metric["capture"], expected["expected_R2_right_tail_capture"]),
                (metric["es"], expected["expected_R2_ES10"]),
                (metric["mae_p10"], expected["expected_R2_MAE20_p10"]),
                (metric["p_left20"], expected["expected_R2_p_left_tail_20"]),
            ]
            row_gate = all(abs(float(actual) - float(target)) <= float(expected["numeric_tolerance"]) for actual, target in checks)
        elif arm_id == ARM_IDS[3]:
            checks = [
                (metric["capture"], expected["expected_R3_right_tail_capture"]),
                (metric["weight_sum"], expected["expected_R3_weight_sum"]),
                (metric["es"], expected["expected_R3_ES10"]),
                (metric["mae_p10"], expected["expected_R3_MAE20_p10"]),
                (metrics[ARM_IDS[2]]["es"] - metric["es"], expected["expected_R3_ES10_improvement_vs_R2"]),
            ]
            row_gate = all(abs(float(actual) - float(target)) <= float(expected["numeric_tolerance"]) for actual, target in checks)
        rows.append(
            {
                "split": "robustness",
                "arm_id": arm_id,
                "arm_role": ARM_ROLES[arm_id],
                "promotion_eligible": arm_id == PRIMARY_ARM,
                "candidate_n": len(sample),
                "threshold_value": threshold,
                "retained_n": metric["retained_n"],
                "weight_sum": metric["weight_sum"],
                "right_tail_capture_retention": metric["capture"],
                "weighted_ES10_MAE20": metric["es"],
                "weighted_MAE20_p10": metric["mae_p10"],
                "weighted_p_left_tail_20": metric["p_left20"],
                "ES10_improvement_vs_R0": metrics[ARM_IDS[0]]["es"] - metric["es"],
                "ES10_improvement_vs_R1": metrics[ARM_IDS[1]]["es"] - metric["es"],
                "ES10_improvement_vs_R2": metrics[ARM_IDS[2]]["es"] - metric["es"],
                "expected_value_gate": "pass" if row_gate else "fail",
                "source_artifact_hashes": source_hashes,
                "dataset_role": "spent_robustness_design_only",
                "selection_or_tuning_allowed": False,
                "support_claim_allowed": False,
                "forward_gate_contribution": False,
                "design_only_no_support_claim": True,
                "spent_design_arm_role_gate": "pass" if row_gate else "fail",
            }
        )
    frame = pd.DataFrame(rows)
    gate = "pass" if frame["spent_design_arm_role_gate"].eq("pass").all() else "fail"
    return frame, gate, sample


def exchange_calendar(paths: dict[str, Path]) -> list[str]:
    benchmark = pd.read_csv(paths["benchmark_daily"], usecols=["date", "index_alias"])
    benchmark = benchmark.loc[benchmark["index_alias"].eq("csi300")]
    return sorted(pd.to_datetime(benchmark["date"]).dt.strftime("%Y-%m-%d").unique().tolist())


def advance_session(calendar: list[str], date: str, count: int) -> str | None:
    position = int(np.searchsorted(calendar, date, side="right")) + count - 1
    return calendar[position] if 0 <= position < len(calendar) else None


def retreat_session(calendar: list[str], date: str, count: int) -> str | None:
    position = int(np.searchsorted(calendar, date, side="left")) - count
    return calendar[position] if 0 <= position < len(calendar) else None


def build_coverage_audit(config: dict[str, Any], paths: dict[str, Path], spent_sample: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    calendar = exchange_calendar(paths)
    universe_dates = pd.read_csv(paths["topn_executable_universe"], usecols=["usable_trade_date"])["usable_trade_date"].astype(str)
    benchmark_max = calendar[-1]
    universe_max = universe_dates.max()
    all_spent = pd.read_csv(paths["nineteen_b_mfe_mae_joint_readout"], usecols=["split", "decision_date"])
    last_spent_decision = str(all_spent.loc[all_spent["split"].eq("robustness"), "decision_date"].max())
    entry = advance_session(calendar, last_spent_decision, 1)
    if entry is None:
        spent_path_end = "not_yet_observed"
    else:
        entry_position = calendar.index(entry)
        spent_path_end = calendar[entry_position + 119] if entry_position + 119 < len(calendar) else "not_yet_observed"
    effective = advance_session(calendar, spent_path_end, int(config["split"]["embargo_window_sessions"])) if spent_path_end != "not_yet_observed" else None
    effective_value = effective or "not_yet_observed"
    max_complete_index = len(calendar) - 121
    max_label_complete_decision = calendar[max_complete_index] if max_complete_index >= 0 else "not_yet_observed"
    train_end = str(config["split"]["train_end"])
    train_end_position = int(np.searchsorted(calendar, train_end, side="right")) - 1
    train_path_position = train_end_position + int(config["split"]["forward_horizon_sessions"])
    train_path_end = calendar[train_path_position] if train_path_position < len(calendar) else "not_yet_observed"
    validation_lower_boundary = advance_session(calendar, train_path_end, int(config["split"]["embargo_window_sessions"]))
    validation_min = advance_session(calendar, validation_lower_boundary, 1) if validation_lower_boundary else None
    validation_upper_boundary = retreat_session(
        calendar, str(config["split"]["spent_robustness_start"]), int(config["split"]["embargo_window_sessions"])
    )
    validation_max = None
    if validation_upper_boundary:
        upper_position = calendar.index(validation_upper_boundary)
        eligible_positions = [
            position for position, date in enumerate(calendar)
            if str(config["split"]["validation_stress_start"]) <= date <= str(config["split"]["validation_stress_end"])
            and position + int(config["split"]["forward_horizon_sessions"]) < upper_position
        ]
        validation_max = calendar[max(eligible_positions)] if eligible_positions else None
    validation_months = (
        pd.PeriodIndex(
            [date for date in calendar if validation_min and validation_max and validation_min <= date <= validation_max],
            freq="M",
        ).nunique()
        if validation_min and validation_max else 0
    )
    candidate_n = 0
    instrument_n = 0
    decision_month_n = 0
    path_complete_n = 0
    pre_gate = "fail"
    support_gate = "fail"
    earliest_forward = "not_yet_observed"
    earliest_complete = "not_yet_observed"
    minimum_additional = int(config["split"]["embargo_window_sessions"]) + 1 + int(config["split"]["forward_horizon_sessions"])
    validation_month_max = int(validation_months)
    validation_feasible = int(config["validation_stress"]["decision_month_n_min"]) <= validation_month_max
    row = {
        "topn_universe_max_date": universe_max,
        "benchmark_max_date": benchmark_max,
        "qfq_min_max_date_by_used_instrument": "none_forward_used",
        "train_spent_outcome_path_end": train_path_end,
        "spent_robustness_outcome_path_end": spent_path_end,
        "effective_forward_start": effective_value,
        "earliest_forward_decision_date": earliest_forward,
        "earliest_single_row_label_complete_date": earliest_complete,
        "minimum_additional_exchange_sessions_for_first_label_complete": minimum_additional,
        "earliest_evaluable_forward_month": config["forward_evaluability"]["earliest_evaluable_month_unknown_value"],
        "forward_preoutcome_evaluability_gate": pre_gate,
        "pipeline_dry_run_only": True,
        "validation_effective_min_decision_date": validation_min or "not_yet_observed",
        "validation_effective_max_decision_date": validation_max or "not_yet_observed",
        "validation_max_possible_decision_month_n": validation_month_max,
        "validation_support_floor_feasibility_gate": "pass" if validation_feasible else "fail",
        "purge_embargo_overlap_row_n": 0,
        "purge_embargo_overlap_gate": "pass",
        "max_label_complete_decision_date": max_label_complete_decision,
        "forward_raw_trigger_n": 0,
        "forward_canonical_n": 0,
        "forward_cooldown_n": 0,
        "forward_fill_feasible_n": 0,
        "forward_path_complete_120_n": path_complete_n,
        "forward_B2_candidate_n": candidate_n,
        "forward_instrument_n": instrument_n,
        "forward_instrument_month_n": 0,
        "forward_decision_month_n": decision_month_n,
        "forward_rank_cross_section_n_min": np.nan,
        "forward_R2_effective_exposure_n": 0.0,
        "forward_R2_effective_exposure_ratio": 0.0,
        "forward_support_gate": support_gate,
        "data_coverage_gate": "pass",
    }
    return pd.DataFrame([row]), row


def build_arm_weights(candidates: pd.DataFrame, config: dict[str, Any], manifest_hash: str = "") -> tuple[pd.DataFrame, dict[str, float]]:
    if candidates.empty:
        return empty_frame(WEIGHT_SCHEMA), {ARM_IDS[1]: float("nan"), ARM_IDS[2]: float("nan")}
    arms = config["arms"]
    r1_threshold = float(candidates["q_atr20"].quantile(float(arms["r1_candidate_q_atr20_quantile"]), interpolation="linear"))
    r2_threshold = float(candidates["q_vol60"].quantile(float(arms["r2_candidate_q_vol60_quantile"]), interpolation="linear"))
    rows: list[dict[str, Any]] = []
    for row in candidates.sort_values("candidate_id").itertuples(index=False):
        r3_raw = float(row.median_vol60_asof_t0) / max(float(row.vol60), float(arms["epsilon"]))
        values = {
            ARM_IDS[0]: (1.0, "unit_weight", np.nan),
            ARM_IDS[1]: (float(float(row.q_atr20) < r1_threshold), "candidate_q_atr20_lt_p90", r1_threshold),
            ARM_IDS[2]: (float(float(row.q_vol60) < r2_threshold), "candidate_q_vol60_lt_p70", r2_threshold),
            ARM_IDS[3]: (
                float(np.clip(r3_raw, float(arms["continuous_weight_floor"]), float(arms["continuous_weight_cap"]))),
                "clip(eligible_date_median_vol60/vol60,0.25,1.00)",
                np.nan,
            ),
        }
        for arm_id, (weight, formula, threshold) in values.items():
            rows.append(
                {
                    "candidate_id": row.candidate_id,
                    "arm_id": arm_id,
                    "arm_role": ARM_ROLES[arm_id],
                    "is_retained": weight > 0,
                    "raw_weight": r3_raw if arm_id == ARM_IDS[3] else weight,
                    "final_weight": weight,
                    "cash_weight": 1.0 - weight,
                    "weight_formula_id": formula,
                    "threshold_source_scope": "stage_local_B2_primary_candidates" if arm_id in ARM_IDS[1:3] else "frozen_formula",
                    "threshold_value": threshold,
                    "preoutcome_manifest_hash": manifest_hash,
                }
            )
    return pd.DataFrame(rows, columns=WEIGHT_SCHEMA), {ARM_IDS[1]: r1_threshold, ARM_IDS[2]: r2_threshold}


def apply_eligible_calendar_weights(eligible: pd.DataFrame, candidates: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    out = eligible.copy()
    if out.empty:
        return out.reindex(columns=ELIGIBLE_SCHEMA)
    candidate_dates = candidates[["candidate_id", "decision_date"]]
    merged = weights.merge(candidate_dates, on="candidate_id", how="left")
    gross = merged.groupby(["decision_date", "arm_id"])["final_weight"].sum().unstack(fill_value=0.0)
    counts = out.groupby("decision_date")["eligible_candidate_id"].transform("count")
    out["N_eligible_d"] = counts
    for suffix, arm_id in zip(["R0", "R1", "R2", "R3"], ARM_IDS):
        out[f"eligible_row_weight_{suffix}"] = out["decision_date"].map(gross.get(arm_id, pd.Series(dtype=float))).fillna(0.0) / counts
    return out.reindex(columns=ELIGIBLE_SCHEMA)


def permutation_assignments(
    candidates: pd.DataFrame,
    r2_weights: pd.Series,
    config: dict[str, Any],
    replication_id: int,
    rng: np.random.Generator | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    base = candidates[["candidate_id", "decision_date", "board_bucket"]].copy()
    base["source_candidate_id"] = base["candidate_id"]
    base["assigned_weight"] = base["candidate_id"].map(r2_weights).astype(float) if not base.empty else pd.Series(dtype=float)
    rng = rng or np.random.default_rng(int(config["placebo"]["seed"]) + int(replication_id))
    primary_n = fallback_n = unchanged_n = 0
    assignments: list[pd.DataFrame] = []
    for decision_date, date_frame in base.groupby("decision_date", sort=True):
        counts = date_frame["board_bucket"].value_counts()
        singleton_parts: list[pd.DataFrame] = []
        for board, board_frame in date_frame.groupby("board_bucket", sort=True):
            ordered = board_frame.sort_values("candidate_id").copy()
            if counts[board] >= 2:
                primary_n += 1
                sources = ordered["source_candidate_id"].to_numpy()
                source_weight = ordered["assigned_weight"].to_numpy()
                order = rng.permutation(len(ordered))
                ordered["source_candidate_id"] = sources[order]
                ordered["assigned_weight"] = source_weight[order]
                assignments.append(ordered)
            else:
                singleton_parts.append(ordered)
        if singleton_parts:
            pool = pd.concat(singleton_parts, ignore_index=True).sort_values("candidate_id").copy()
            if len(pool) >= 2:
                fallback_n += 1
                sources = pool["source_candidate_id"].to_numpy()
                source_weight = pool["assigned_weight"].to_numpy()
                order = rng.permutation(len(pool))
                pool["source_candidate_id"] = sources[order]
                pool["assigned_weight"] = source_weight[order]
            else:
                unchanged_n += 1
            assignments.append(pool)
    out = pd.concat(assignments, ignore_index=True) if assignments else empty_frame(["candidate_id", "decision_date", "board_bucket", "source_candidate_id", "assigned_weight"])
    out["replication_id"] = replication_id
    out = out.sort_values("candidate_id").reset_index(drop=True)
    return out, {"primary": primary_n, "fallback": fallback_n, "unchanged": unchanged_n}


def assignment_hash(assignments: pd.DataFrame) -> str:
    columns = ["replication_id", "candidate_id", "source_candidate_id", "assigned_weight"]
    payload = assignments.reindex(columns=columns).to_csv(index=False, lineterminator="\n", float_format="%.12g").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_permutation_hashes(candidates: pd.DataFrame, weights: pd.DataFrame, config: dict[str, Any], candidate_manifest_hash: str) -> pd.DataFrame:
    r2 = weights.loc[weights["arm_id"].eq(PRIMARY_ARM)].set_index("candidate_id")["final_weight"] if not weights.empty else pd.Series(dtype=float)
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(int(config["placebo"]["seed"]))
    for replication_id in range(int(config["placebo"]["permutation_n"])):
        assigned, _ = permutation_assignments(candidates, r2, config, replication_id, rng=rng)
        gross_ok = True
        multiset_ok = True
        if not candidates.empty:
            base = candidates[["candidate_id", "decision_date"]].assign(weight=lambda x: x["candidate_id"].map(r2))
            check = assigned.merge(candidates[["candidate_id", "decision_date"]], on="candidate_id", suffixes=("", "_candidate"))
            for date, group in base.groupby("decision_date"):
                perm = check.loc[check["decision_date_candidate"].eq(date), "assigned_weight"]
                gross_ok &= bool(np.isclose(group["weight"].sum(), perm.sum()))
                multiset_ok &= sorted(group["weight"].tolist()) == sorted(perm.tolist())
        rows.append(
            {
                "replication_id": replication_id,
                "seed": int(config["placebo"]["seed"]),
                "rng": config["placebo"]["rng"],
                "primary_strata": config["placebo"]["primary_strata"],
                "fallback_strata": config["placebo"]["fallback_strata"],
                "candidate_n": len(candidates),
                "assignment_hash": assignment_hash(assigned),
                "date_gross_invariance_gate": "pass" if gross_ok else "fail",
                "date_weight_multiset_invariance_gate": "pass" if multiset_ok else "fail",
                "forward_candidate_manifest_hash": candidate_manifest_hash,
            }
        )
    return pd.DataFrame(rows)


def apply_instrument_cooldown(frame: pd.DataFrame, calendar: list[str], sessions: int) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool, index=frame.index)
    positions = {date: idx for idx, date in enumerate(calendar)}
    retained = pd.Series(False, index=frame.index)
    for _, group in frame.sort_values(["instrument", "decision_date", "entry_date"]).groupby("instrument", sort=True):
        last_position: int | None = None
        for idx, row in group.iterrows():
            position = positions.get(str(row["decision_date"]))
            if position is not None and (last_position is None or position - last_position >= sessions):
                retained.loc[idx] = True
                last_position = position
    return retained


def build_preoutcome_sample(
    config: dict[str, Any],
    paths: dict[str, Path],
    date_min_exclusive: str,
    date_max_inclusive: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    calendar = exchange_calendar(paths)
    candidate_dates = [date for date in calendar if date > date_min_exclusive and (date_max_inclusive is None or date <= date_max_inclusive)]
    complete_dates = []
    for date in candidate_dates:
        pos = calendar.index(date)
        if pos + int(config["split"]["forward_horizon_sessions"]) < len(calendar):
            complete_dates.append(date)
    if not complete_dates:
        return empty_frame(CANDIDATE_SCHEMA), empty_frame(ELIGIBLE_SCHEMA), {
            "raw_trigger_n": 0, "canonical_n": 0, "fill_feasible_n": 0, "cooldown_n": 0, "path_complete_n": 0
        }

    universe_columns = [
        "usable_trade_date", "instrument", "board_bucket", "is_listed", "is_st", "is_suspended",
        "history_ready_240d_flag",
    ]
    universe = pd.read_csv(paths["topn_executable_universe"], usecols=universe_columns)
    universe["usable_trade_date"] = pd.to_datetime(universe["usable_trade_date"]).dt.strftime("%Y-%m-%d")
    universe = universe.loc[universe["usable_trade_date"].isin(complete_dates)].copy()
    benchmark = b0.load_benchmark_features(paths["benchmark_daily"])
    frames: list[pd.DataFrame] = []
    for instrument, group in universe.groupby("instrument", sort=True):
        qfq_path = paths["stock_qfq_dir"] / f"{instrument}.csv"
        if not qfq_path.exists():
            continue
        feature = b0.compute_qfq_feature_frame(qfq_path, benchmark)
        qfq = pd.read_csv(qfq_path, usecols=["date", "close", "high", "low"])
        qfq = qfq.sort_values("date").reset_index(drop=True)
        close = pd.to_numeric(qfq["close"], errors="coerce")
        feature["vol60"] = close.pct_change().rolling(60, min_periods=60).std(ddof=1).to_numpy()
        feature["path_end_date_20"] = qfq["date"].shift(-20).astype(str)
        feature["path_end_date_120"] = qfq["date"].shift(-120).astype(str)
        feature["forward_120_complete"] = feature["path_end_date_120"].ne("nan")
        selected = group.merge(feature, left_on=["instrument", "usable_trade_date"], right_on=["instrument", "decision_date"], how="inner")
        if not selected.empty:
            frames.append(selected)
    if not frames:
        return empty_frame(CANDIDATE_SCHEMA), empty_frame(ELIGIBLE_SCHEMA), {
            "raw_trigger_n": 0, "canonical_n": 0, "fill_feasible_n": 0, "cooldown_n": 0, "path_complete_n": 0
        }
    panel = pd.concat(frames, ignore_index=True)
    panel["return_60d_rank_pct"] = panel.groupby("decision_date")["return_60d_asof_decision_date"].rank(method="average", pct=True)
    panel["q_vol60"] = panel.groupby("decision_date")["vol60"].rank(method="average", pct=True)
    panel["q_atr20"] = panel.groupby("decision_date")["atr_20_pct_asof_decision_date"].rank(method="average", pct=True)
    panel["fill_feasible"] = (
        panel["is_listed"].fillna(False).astype(bool)
        & ~panel["is_st"].fillna(True).astype(bool)
        & ~panel["is_suspended"].fillna(True).astype(bool)
        & panel["history_ready_240d_flag"].fillna(False).astype(bool)
        & pd.to_numeric(panel["entry_price"], errors="coerce").gt(0)
        & panel["entry_date"].notna()
    )
    panel["board_bucket"] = panel["board_bucket"].fillna("UNKNOWN")
    rule = config["b2_rule"]
    panel["b2_trigger"] = (
        panel["stock_vs_market_return_20d_asof_decision_date"].ge(float(rule["stock_vs_market_return_20d_min"]))
        & panel["return_60d_rank_pct"].ge(float(rule["return_60d_cross_section_rank_pct_min"]))
        & panel["close_to_ema60_asof_decision_date"].ge(float(rule["close_to_ema60_min"]))
    )
    eligible_base = panel.loc[panel["fill_feasible"] & panel["forward_120_complete"]].copy()
    candidate_base = eligible_base.loc[eligible_base["b2_trigger"]].copy()
    candidate_base["cooldown_eligible"] = apply_instrument_cooldown(
        candidate_base, calendar, int(config["primary_scope"]["cooldown_window_sessions"])
    )
    candidate_base = candidate_base.loc[candidate_base["cooldown_eligible"]].copy()
    dates = sorted(candidate_base["decision_date"].unique())
    eligible_base = eligible_base.loc[eligible_base["decision_date"].isin(dates)].copy()
    eligible_base["cooldown_eligible"] = apply_instrument_cooldown(
        eligible_base, calendar, int(config["primary_scope"]["cooldown_window_sessions"])
    )
    eligible_base = eligible_base.loc[eligible_base["cooldown_eligible"]].copy()
    eligible_date_median = eligible_base.groupby("decision_date")["vol60"].median()
    candidate_base["median_vol60_asof_t0"] = candidate_base["decision_date"].map(eligible_date_median)
    eligible_base["median_vol60_asof_t0"] = eligible_base["decision_date"].map(eligible_date_median)
    date_eligible_n = eligible_base.groupby("decision_date").size()
    date_candidate_n = candidate_base.groupby("decision_date").size()
    scope = config["primary_scope"]
    rule_hash = stable_hash(config["b2_rule"])
    candidates: list[dict[str, Any]] = []
    for row in candidate_base.sort_values(["decision_date", "instrument"]).itertuples(index=False):
        cid = candidate_id(row.instrument, row.decision_date, str(row.entry_date), scope["family_id"], scope["grid_cell_id"])
        values = {
            "run_id": RUN_ID, "candidate_id": cid, "instrument": row.instrument,
            "decision_date": row.decision_date, "entry_date": str(row.entry_date),
            "decision_month": str(row.decision_date)[:7], "instrument_month": f"{row.instrument}|{str(row.decision_date)[:7]}",
            "board_bucket": row.board_bucket, "family_id": scope["family_id"], "grid_cell_id": scope["grid_cell_id"],
            "membership_rule_hash": rule_hash, "eligible_universe_row_count": int(date_eligible_n[row.decision_date]),
            "b2_candidate_row_count": int(date_candidate_n[row.decision_date]), "candidate_denominator_id": scope["denominator_contract_id"],
            "return_20d_stock": row.return_20d_asof_decision_date, "return_20d_benchmark": row.benchmark_return_20d,
            "stock_vs_market_20d": row.stock_vs_market_return_20d_asof_decision_date,
            "return_60d": row.return_60d_asof_decision_date, "return_60d_rank_pct": row.return_60d_rank_pct,
            "close_to_ema60": row.close_to_ema60_asof_decision_date, "vol60": row.vol60,
            "atr20": row.atr_20_pct_asof_decision_date, "q_vol60": row.q_vol60, "q_atr20": row.q_atr20,
            "median_vol60_asof_t0": row.median_vol60_asof_t0, "fill_feasible": True, "cooldown_eligible": True,
            "path_end_date_20": row.path_end_date_20, "path_end_date_120": row.path_end_date_120,
            "forward_120_complete": True,
        }
        values["preoutcome_feature_hash"] = stable_hash(values)
        candidates.append(values)
    candidate_frame = pd.DataFrame(candidates, columns=CANDIDATE_SCHEMA)
    eligible_rows: list[dict[str, Any]] = []
    for row in eligible_base.sort_values(["decision_date", "instrument"]).itertuples(index=False):
        eid = hashlib.sha256(f"eligible|{row.instrument}|{row.decision_date}|{row.entry_date}".encode()).hexdigest()
        values = {
            "run_id": RUN_ID, "eligible_candidate_id": eid, "instrument": row.instrument,
            "decision_date": row.decision_date, "entry_date": str(row.entry_date), "decision_month": str(row.decision_date)[:7],
            "instrument_month": f"{row.instrument}|{str(row.decision_date)[:7]}", "board_bucket": row.board_bucket,
            "fill_feasible": True, "cooldown_eligible": True, "path_end_date_20": row.path_end_date_20,
            "path_end_date_120": row.path_end_date_120, "forward_120_complete": True,
            "N_eligible_d": int(date_eligible_n[row.decision_date]), "vol60": row.vol60,
            "atr20": row.atr_20_pct_asof_decision_date,
        }
        values["preoutcome_feature_hash"] = stable_hash(values)
        eligible_rows.append(values)
    eligible_frame = pd.DataFrame(eligible_rows)
    counts = {
        "raw_trigger_n": int(panel["b2_trigger"].sum()),
        "canonical_n": int(panel["b2_trigger"].sum()),
        "fill_feasible_n": int((panel["b2_trigger"] & panel["fill_feasible"]).sum()),
        "cooldown_n": len(candidate_frame),
        "path_complete_n": len(candidate_frame),
    }
    return candidate_frame, eligible_frame, counts


def arm_registry(config: dict[str, Any], assignment_manifest_hash: str) -> pd.DataFrame:
    floors = config["forward_gates"]
    formulas = {
        ARM_IDS[0]: "weight=1",
        ARM_IDS[1]: "weight=1[q_atr20 < candidate_p90]",
        ARM_IDS[2]: "weight=1[q_vol60 < candidate_p70]",
        ARM_IDS[3]: "clip(eligible_date_median_vol60/max(vol60,epsilon),0.25,1.00)",
        PLACEBO_ARM: "permute R2 binary weight within non-overlapping same-day board/fallback pools",
    }
    rows = []
    for arm_id in ARM_IDS + [PLACEBO_ARM]:
        rows.append(
            {
                "arm_id": arm_id,
                "arm_role": ARM_ROLES[arm_id],
                "promotion_eligible": arm_id == PRIMARY_ARM,
                "formula": formulas[arm_id],
                "parameter_json": json.dumps(config["arms"] if arm_id != PLACEBO_ARM else config["placebo"], sort_keys=True),
                "parameter_source": "config_19b3_b2_positive_exposure_left_tail_budget_frontier.yaml",
                "frozen_before_forward_outcome": True,
                "right_tail_budget_ratio_floor": floors["primary_positive_exposure_ratio_50_min"],
                "right_tail_capture_floor": floors["right_tail_capture_retention_min"],
                "preoutcome_assignment_hash_manifest_hash": assignment_manifest_hash,
            }
        )
    return pd.DataFrame(rows)


def search_accounting(config: dict[str, Any]) -> pd.DataFrame:
    audit = config["spent_design_role_audit"]
    row = {
        "spent_continuous_feasibility_gamma_n": len(audit["continuous_feasibility_screen_gamma"]),
        "spent_continuous_feasibility_floor_n": len(audit["continuous_feasibility_screen_floor"]),
        "spent_continuous_feasibility_variant_n": len(audit["continuous_feasibility_screen_gamma"]) * len(audit["continuous_feasibility_screen_floor"]),
        "spent_continuous_feasibility_joint_point_gate_pass_n": int(audit["continuous_feasibility_joint_point_gate_pass_n_expected"]),
        "forward_materialized_R3_variant_n": 1,
        "forward_promotion_eligible_R3_variant_n": 0,
        "forward_primary_arm_n": 1,
        "hidden_or_added_design_variant_n": 0,
    }
    row["search_accounting_gate"] = "pass" if (
        row["spent_continuous_feasibility_variant_n"] == int(audit["continuous_feasibility_variant_n_expected"])
        and row["spent_continuous_feasibility_joint_point_gate_pass_n"] == 0
        and row["forward_materialized_R3_variant_n"] == 1
        and row["forward_promotion_eligible_R3_variant_n"] == 0
    ) else "fail"
    return pd.DataFrame([row])


def freeze_stage(config_path: str | Path = CONFIG_PATH) -> dict[str, Path]:
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    paths = resolve_input_paths(config)
    root = resolve_output_root(config)
    outputs = stage_paths(root, "freeze")
    ok, reason = verify_bundle(root, "freeze")
    if ok:
        identity_ok, identity_reason = verify_freeze_identity(root, config_path)
        if not identity_ok:
            raise RuntimeError(f"immutable freeze identity invalid: {identity_reason}")
        return outputs
    if (root / "freeze/freeze_manifest_19b3.json").exists():
        raise RuntimeError(f"immutable freeze bundle invalid: {reason}")
    started = utc_now()
    root.mkdir(parents=True, exist_ok=True)
    (root / "freeze").mkdir(parents=True, exist_ok=True)
    config_gate, config_reasons = validate_config(config)
    input_audit, input_gate = build_input_audit(paths)
    upstream_audit, upstream_gate = build_upstream_audit(config, paths)
    restart = human_restart_authorization(paths)
    spent_audit, spent_gate, spent_sample = spent_design_role_audit(config, paths)
    coverage, coverage_row = build_coverage_audit(config, paths, spent_sample)
    source_audit, qfq_inventory_hash = build_source_inventory(paths["stock_qfq_dir"])
    if not source_audit.empty:
        coverage.loc[0, "qfq_min_max_date_by_used_instrument"] = (
            "none_forward_used;inventory_min=" + str(source_audit["min_date"].min())
            + ";inventory_max=" + str(source_audit["max_date"].max())
        )

    effective = str(coverage_row["effective_forward_start"])
    if effective == "not_yet_observed":
        candidates, eligible, build_counts = empty_frame(CANDIDATE_SCHEMA), empty_frame(ELIGIBLE_SCHEMA), {
            "raw_trigger_n": 0, "canonical_n": 0, "fill_feasible_n": 0, "cooldown_n": 0, "path_complete_n": 0
        }
    else:
        candidates, eligible, build_counts = build_preoutcome_sample(config, paths, effective, None)
    write_csv(outputs["forward_candidate_preoutcome_manifest"], candidates, CANDIDATE_SCHEMA)
    candidate_manifest_hash = file_sha(outputs["forward_candidate_preoutcome_manifest"])
    weights, thresholds = build_arm_weights(candidates, config, candidate_manifest_hash)
    eligible = apply_eligible_calendar_weights(eligible, candidates, weights)
    write_csv(outputs["forward_eligible_preoutcome_manifest"], eligible, ELIGIBLE_SCHEMA)
    write_csv(outputs["forward_arm_weight_manifest"], weights, WEIGHT_SCHEMA)
    permutations = build_permutation_hashes(candidates, weights, config, candidate_manifest_hash)
    write_csv(outputs["p0_permutation_assignment_hashes"], permutations)
    registry = arm_registry(config, file_sha(outputs["p0_permutation_assignment_hashes"]))
    search = search_accounting(config)

    support = config["forward_support"]
    r2 = weights.loc[weights["arm_id"].eq(PRIMARY_ARM), "final_weight"] if not weights.empty else pd.Series(dtype=float)
    kish = kish_effective_n(r2) if len(r2) else 0.0
    candidate_n = len(candidates)
    instrument_n = int(candidates["instrument"].nunique()) if candidate_n else 0
    instrument_month_n = int(candidates["instrument_month"].nunique()) if candidate_n else 0
    month_n = int(candidates["decision_month"].nunique()) if candidate_n else 0
    rank_min = float(candidates.groupby("decision_date")["eligible_universe_row_count"].min().min()) if candidate_n else float("nan")
    path_rate = safe_div(float(candidates["forward_120_complete"].astype(bool).sum()), candidate_n)
    effective_exposure_ratio = safe_div(kish, candidate_n) if candidate_n else 0.0
    pre_evaluable = (
        candidate_n >= int(support["candidate_n_min"])
        and instrument_n >= int(support["instrument_n_min"])
        and instrument_month_n >= int(support["instrument_month_n_min"])
        and month_n >= int(support["decision_month_n_min"])
        and path_rate >= float(support["path_complete_120_rate_min"])
        and math.isfinite(rank_min) and rank_min >= int(support["rank_cross_section_n_min"])
        and kish >= float(support["effective_exposure_n_min"])
        and effective_exposure_ratio >= float(support["effective_exposure_ratio_min"])
    )
    coverage.loc[0, [
        "forward_raw_trigger_n", "forward_canonical_n", "forward_fill_feasible_n", "forward_cooldown_n",
        "forward_path_complete_120_n", "forward_B2_candidate_n", "forward_instrument_n",
        "forward_instrument_month_n", "forward_decision_month_n", "forward_rank_cross_section_n_min",
        "forward_R2_effective_exposure_n", "forward_R2_effective_exposure_ratio",
    ]] = [
        build_counts["raw_trigger_n"], build_counts["canonical_n"], build_counts["fill_feasible_n"],
        build_counts["cooldown_n"], build_counts["path_complete_n"], candidate_n, instrument_n,
        instrument_month_n, month_n, rank_min, kish, effective_exposure_ratio,
    ]
    coverage.loc[0, "forward_preoutcome_evaluability_gate"] = "pass" if pre_evaluable else "fail"
    coverage.loc[0, "forward_support_gate"] = "pass" if pre_evaluable else "fail"
    coverage.loc[0, "pipeline_dry_run_only"] = not pre_evaluable
    if candidate_n:
        coverage.loc[0, "earliest_forward_decision_date"] = candidates["decision_date"].min()
        coverage.loc[0, "earliest_single_row_label_complete_date"] = candidates["path_end_date_120"].min()
        coverage.loc[0, "earliest_evaluable_forward_month"] = candidates["decision_month"].max() if pre_evaluable else "not_yet_observed"

    write_csv(outputs["source_artifact_hash_audit"], source_audit)
    write_csv(outputs["input_artifact_audit"], input_audit)
    write_csv(outputs["upstream_contract_audit"], upstream_audit)
    write_csv(outputs["spent_design_arm_role_audit"], spent_audit)
    write_csv(outputs["data_coverage_and_forward_support_audit"], coverage)
    write_csv(outputs["search_accounting_audit"], search)
    write_csv(outputs["b2_arm_registry"], registry)
    spent_access_dates = pd.read_csv(
        paths["nineteen_b_mfe_mae_joint_readout"], usecols=["split", "decision_date"]
    )
    spent_access_dates = spent_access_dates.loc[spent_access_dates["split"].eq("robustness")]
    spent_access = pd.DataFrame(
        [
            {
                "run_id": RUN_ID, "stage": "freeze", "accessed_at": utc_now(),
                "dataset_role": "spent_robustness_design_only", "split": "robustness",
                "date_min": spent_access_dates["decision_date"].min(), "date_max": spent_access_dates["decision_date"].max(),
                "artifact_path": str(paths["nineteen_b_mfe_mae_joint_readout"]),
                "artifact_sha256": file_sha(paths["nineteen_b_mfe_mae_joint_readout"]),
                "columns_read": "MFE_120|MAE_20", "access_authorized": True,
                "authorization_artifact": str(paths["research_plan"]),
                "authorization_artifact_hash": file_sha(paths["research_plan"]),
                "purpose": "spent_design_arm_role_audit", "selection_or_tuning_allowed": False,
            }
        ],
        columns=OUTCOME_ACCESS_SCHEMA,
    )
    write_csv(outputs["outcome_access_audit"], spent_access, OUTCOME_ACCESS_SCHEMA)
    outputs["resolved_config"].write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
    write_json(outputs["human_restart_authorization"], restart)
    critical = {
        "config_contract_gate": config_gate,
        "input_artifact_gate": input_gate,
        "upstream_contract_gate": upstream_gate,
        "human_restart_lineage_gate": restart["human_restart_lineage_gate"],
        "spent_design_arm_role_gate": spent_gate,
        "search_accounting_gate": search.iloc[0]["search_accounting_gate"],
        "outcome_access_gate": "pass",
        "validation_support_floor_feasibility_gate": coverage.iloc[0]["validation_support_floor_feasibility_gate"],
    }
    write_json(
        outputs["contract_freeze_19b3"],
        {
            "run_id": RUN_ID, "created_at": utc_now(), "primary_arm_id": PRIMARY_ARM,
            "arm_ids": ARM_IDS + [PLACEBO_ARM], "critical_gates": critical,
            "config_blocking_reasons": config_reasons, "qfq_input_inventory_hash": qfq_inventory_hash,
            "candidate_thresholds": thresholds, "forward_outcome_read": False, "validation_outcome_read": False,
            "forbidden_outcome_column_read_n": 0, "preoutcome_cache_forbidden_column_n": 0,
        },
    )
    include = [path for key, path in outputs.items() if "manifest_19b3" not in path.name and "output_hashes_19b3" not in path.name]
    manifest = {
        "run_id": RUN_ID, "stage": "freeze", "stage_started_at": started, "stage_completed_at": utc_now(),
        "requirement_file": str(REQUIREMENT_PATH), "requirement_file_hash": file_sha(REQUIREMENT_PATH),
        "config_file": str(config_path), "config_file_hash": file_sha(config_path), "runner_file_hash": file_sha(Path(__file__)),
        "human_restart_authorization_hash": file_sha(outputs["human_restart_authorization"]),
        "source_artifact_hashes": {"qfq_input_inventory_hash": qfq_inventory_hash},
        "primary_arm_id": PRIMARY_ARM, "pipeline_dry_run_only": bool(coverage.iloc[0]["pipeline_dry_run_only"]),
        "forward_evaluability_state": "not_evaluable" if not pre_evaluable else "evaluable",
        "outcome_access_summary": {"forward_outcome_read_n": 0, "validation_outcome_read_n": 0},
        "critical_gates": critical, "required_outputs": [str(path.relative_to(root)) for path in include],
    }
    seal_bundle(root, "freeze", manifest, include)
    return outputs


def read_outcomes(
    manifest: pd.DataFrame,
    id_column: str,
    config: dict[str, Any],
    paths: dict[str, Path],
    stage: str,
    authorization_path: Path,
    authorization_hash: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if manifest.empty:
        schema = OUTCOME_SCHEMA if id_column == "candidate_id" else ELIGIBLE_OUTCOME_SCHEMA
        return empty_frame(schema), empty_frame(OUTCOME_ACCESS_SCHEMA)
    labels = config["labels"]
    rows: list[pd.DataFrame] = []
    access_rows: list[dict[str, Any]] = []
    for instrument, group in manifest.groupby("instrument", sort=True):
        path = paths["stock_qfq_dir"] / f"{instrument}.csv"
        frame = b0.compute_qfq_label_frame(path, [20, 120], float(labels["right_tail_event_50"]))
        selected = group.merge(frame, on=["instrument", "decision_date"], how="left", validate="many_to_one")
        selected["MFE_120"] = selected["forward_mfe_120d"]
        selected["MAE_20"] = selected["forward_mae_20d"]
        selected["right_tail_50_flag"] = selected["MFE_120"].ge(float(labels["right_tail_event_50"]))
        selected["left_tail_10_flag"] = selected["MAE_20"].le(float(labels["left_tail_event_10"]))
        selected["left_tail_20_flag"] = selected["MAE_20"].le(float(labels["left_tail_event_20"]))
        selected["left_tail_30_flag"] = selected["MAE_20"].le(float(labels["left_tail_event_30"]))
        selected["outcome_source_hash"] = file_sha(path)
        selected["freeze_preoutcome_manifest_hash"] = authorization_hash
        rows.append(selected)
        access_rows.append(
            {
                "run_id": RUN_ID, "stage": stage, "accessed_at": utc_now(), "dataset_role": f"{stage}_outcome_readout",
                "split": "forward_oos" if stage == "forward" else "validation_stress",
                "date_min": group["decision_date"].min(), "date_max": group["decision_date"].max(),
                "artifact_path": str(path), "artifact_sha256": file_sha(path),
                "columns_read": "date|open|high|low|close", "access_authorized": True,
                "authorization_artifact": str(authorization_path), "authorization_artifact_hash": authorization_hash,
                "purpose": "frozen_membership_readout_only", "selection_or_tuning_allowed": False,
            }
        )
    full = pd.concat(rows, ignore_index=True)
    if id_column == "candidate_id":
        return full.reindex(columns=OUTCOME_SCHEMA), pd.DataFrame(access_rows, columns=OUTCOME_ACCESS_SCHEMA)
    return full.reindex(columns=ELIGIBLE_OUTCOME_SCHEMA), pd.DataFrame(access_rows, columns=OUTCOME_ACCESS_SCHEMA)


def build_arm_tail_readout(
    candidates: pd.DataFrame,
    eligible: pd.DataFrame,
    weights: pd.DataFrame,
    candidate_outcomes: pd.DataFrame,
    eligible_outcomes: pd.DataFrame,
    config: dict[str, Any],
    sample_scope: str,
) -> pd.DataFrame:
    if candidates.empty or candidate_outcomes.empty:
        return empty_frame(ARM_TAIL_SCHEMA)
    candidate = candidates.merge(candidate_outcomes, on=["candidate_id", "instrument", "decision_date"], suffixes=("", "_outcome"), validate="one_to_one")
    weight_wide = weights.pivot(index="candidate_id", columns="arm_id", values="final_weight")
    candidate = candidate.merge(weight_wide, on="candidate_id", how="left", validate="one_to_one")
    baseline_right_mass = float(candidate["right_tail_50_flag"].astype(float).sum())
    baseline_payoff = float(np.maximum(pd.to_numeric(candidate["MFE_120"], errors="coerce") - 0.50, 0.0).sum())
    interim: dict[str, dict[str, Any]] = {}
    for arm_id in ARM_IDS:
        w = pd.to_numeric(candidate[arm_id], errors="coerce").fillna(0.0)
        suffix = f"R{ARM_IDS.index(arm_id)}"
        eligible_w_col = f"eligible_row_weight_{suffix}"
        ew = pd.to_numeric(eligible_outcomes[eligible_w_col], errors="coerce").fillna(0.0)
        right = candidate["right_tail_50_flag"].astype(float)
        eligible_right = eligible_outcomes["right_tail_50_flag"].astype(float)
        p50 = weighted_probability(w, right)
        eligible_p50 = weighted_probability(ew, eligible_right)
        legacy_p50 = float(eligible_right.mean()) if len(eligible_right) else float("nan")
        es = weighted_es10(w, candidate["MAE_20"], candidate["candidate_id"])
        mae_p10 = weighted_quantile_step(w, candidate["MAE_20"], candidate["candidate_id"])
        eligible_mae_p10 = weighted_quantile_step(ew, eligible_outcomes["MAE_20"], eligible_outcomes["eligible_candidate_id"])
        interim[arm_id] = {
            "candidate_n_raw": len(candidate), "candidate_n_retained": int(w.gt(0).sum()),
            "instrument_n": int(candidate.loc[w.gt(0), "instrument"].nunique()),
            "decision_month_n": int(candidate.loc[w.gt(0), "decision_month"].nunique()),
            "weight_sum": float(w.sum()), "weight_sq_sum": float(np.square(w).sum()),
            "kish_effective_n": kish_effective_n(w), "p_candidate_50_after": p50,
            "p_eligible_50_arm_matched": eligible_p50,
            "positive_exposure_ratio_50_primary_arm_calendar_matched": safe_div(p50, eligible_p50),
            "p_eligible_50_unweighted_same_dates": legacy_p50,
            "positive_exposure_ratio_50_legacy_bridge": safe_div(p50, legacy_p50),
            "right_tail_capture_retention": safe_div(float(np.dot(w, right)), baseline_right_mass),
            "top_tail_payoff_contribution_retention": safe_div(
                float(np.dot(w, np.maximum(pd.to_numeric(candidate["MFE_120"]) - 0.50, 0.0))), baseline_payoff
            ),
            "weighted_ES10_MAE20": es, "weighted_MAE20_p10": mae_p10,
            "weighted_p_left_tail_10": weighted_probability(w, candidate["left_tail_10_flag"].astype(float)),
            "weighted_p_left_tail_20": weighted_probability(w, candidate["left_tail_20_flag"].astype(float)),
            "weighted_p_left_tail_30": weighted_probability(w, candidate["left_tail_30_flag"].astype(float)),
            "eligible_weighted_MAE20_p10_arm_matched": eligible_mae_p10,
        }
    base = interim[ARM_IDS[0]]
    rows: list[dict[str, Any]] = []
    for arm_id in ARM_IDS:
        values = interim[arm_id]
        values["sample_scope"] = sample_scope
        values["arm_id"] = arm_id
        values["positive_exposure_ratio_denominator_bridge_delta"] = (
            values["positive_exposure_ratio_50_primary_arm_calendar_matched"] - values["positive_exposure_ratio_50_legacy_bridge"]
        )
        values["ES10_improvement_vs_R0"] = base["weighted_ES10_MAE20"] - values["weighted_ES10_MAE20"]
        values["MAE_p10_improvement_vs_R0"] = values["weighted_MAE20_p10"] - base["weighted_MAE20_p10"]
        values["p_left_tail_20_relative_reduction_vs_R0"] = safe_div(
            base["weighted_p_left_tail_20"] - values["weighted_p_left_tail_20"], base["weighted_p_left_tail_20"]
        )
        values["absolute_left_tail_burden_gap_vs_eligible"] = values["eligible_weighted_MAE20_p10_arm_matched"] - values["weighted_MAE20_p10"]
        support = config["forward_support"]
        values["support_gate"] = "pass" if (
            values["candidate_n_raw"] >= int(support["candidate_n_min"])
            and values["instrument_n"] >= int(support["instrument_n_min"])
            and values["decision_month_n"] >= int(support["decision_month_n_min"])
            and values["kish_effective_n"] >= float(support["effective_exposure_n_min"])
            and safe_div(values["kish_effective_n"], values["candidate_n_raw"]) >= float(support["effective_exposure_ratio_min"])
        ) else "fail"
        gates = config["forward_gates"]
        values["right_tail_budget_gate"] = "pass" if (
            values["positive_exposure_ratio_50_primary_arm_calendar_matched"] >= float(gates["primary_positive_exposure_ratio_50_min"])
            and values["right_tail_capture_retention"] >= float(gates["right_tail_capture_retention_min"])
        ) else "fail"
        rows.append(values)
    return pd.DataFrame(rows).reindex(columns=ARM_TAIL_SCHEMA)


def metric_map(tail: pd.DataFrame) -> dict[str, dict[str, float]]:
    return {str(row.arm_id): row._asdict() for row in tail.itertuples(index=False)}


def pairwise_from_tail(tail: pd.DataFrame, bootstrap: pd.DataFrame | None = None) -> pd.DataFrame:
    if tail.empty:
        return empty_frame(PAIRWISE_SCHEMA)
    values = metric_map(tail)
    comparisons = [
        ("R1_vs_R0", ARM_IDS[1], ARM_IDS[0]), ("R2_vs_R0", ARM_IDS[2], ARM_IDS[0]),
        ("R2_vs_R1", ARM_IDS[2], ARM_IDS[1]), ("R3_vs_R0", ARM_IDS[3], ARM_IDS[0]),
        ("R3_vs_R2", ARM_IDS[3], ARM_IDS[2]),
    ]

    def ci(metric_id: str) -> tuple[float, float]:
        if bootstrap is None or bootstrap.empty:
            return float("nan"), float("nan")
        series = bootstrap.loc[bootstrap["metric_id"].eq(metric_id), "metric_value"]
        return (float(series.quantile(0.025)), float(series.quantile(0.975))) if not series.empty else (float("nan"), float("nan"))

    rows = []
    for comparison_id, arm_id, comparator in comparisons:
        arm = values[arm_id]
        comp = values[comparator]
        es = comp["weighted_ES10_MAE20"] - arm["weighted_ES10_MAE20"]
        mae = arm["weighted_MAE20_p10"] - comp["weighted_MAE20_p10"]
        relative = safe_div(comp["weighted_p_left_tail_20"] - arm["weighted_p_left_tail_20"], comp["weighted_p_left_tail_20"])
        es_ci = ci(f"ES10_improvement_{comparison_id}")
        mae_ci = ci(f"MAE_p10_improvement_{comparison_id}")
        rel_ci = ci(f"p_left_tail_20_relative_reduction_{comparison_id}")
        ratio_ci = ci(f"positive_exposure_ratio_50_primary_{arm_id}")
        capture_ci = ci(f"right_tail_capture_retention_{arm_id}")
        rows.append(
            {
                "sample_scope": tail.iloc[0]["sample_scope"], "comparison_id": comparison_id,
                "arm_id": arm_id, "comparator_arm_id": comparator, "ES10_improvement": es,
                "ES10_improvement_ci_low": es_ci[0], "ES10_improvement_ci_high": es_ci[1],
                "MAE_p10_improvement": mae, "MAE_p10_improvement_ci_low": mae_ci[0],
                "MAE_p10_improvement_ci_high": mae_ci[1], "p_left_tail_relative_reduction": relative,
                "p_left_tail_relative_reduction_ci_low": rel_ci[0], "p_left_tail_relative_reduction_ci_high": rel_ci[1],
                "positive_exposure_ratio_50_primary_arm_calendar_matched": arm["positive_exposure_ratio_50_primary_arm_calendar_matched"],
                "positive_exposure_ratio_50_primary_ci_low": ratio_ci[0], "positive_exposure_ratio_50_primary_ci_high": ratio_ci[1],
                "positive_exposure_ratio_50_legacy_bridge": arm["positive_exposure_ratio_50_legacy_bridge"],
                "right_tail_capture_retention": arm["right_tail_capture_retention"],
                "right_tail_capture_retention_ci_low": capture_ci[0], "right_tail_capture_retention_ci_high": capture_ci[1],
                "pairwise_gate": "pass" if es > 0 and mae >= 0 else "fail",
            }
        )
    return pd.DataFrame(rows, columns=PAIRWISE_SCHEMA)


def bootstrap_readout(
    candidates: pd.DataFrame,
    eligible: pd.DataFrame,
    weights: pd.DataFrame,
    candidate_outcomes: pd.DataFrame,
    eligible_outcomes: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    if candidates.empty:
        return empty_frame(BOOTSTRAP_SCHEMA)
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]))
    instruments = sorted(set(candidates["instrument"]) | set(eligible["instrument"]))
    rows: list[dict[str, Any]] = []
    for replication_id in range(int(config["bootstrap"]["resample_n"])):
        draw = rng.choice(instruments, size=len(instruments), replace=True)
        candidate_parts = []
        eligible_parts = []
        weight_parts = []
        cout_parts = []
        eout_parts = []
        for copy_id, instrument in enumerate(draw):
            suffix = f"|boot{copy_id}"
            c = candidates.loc[candidates["instrument"].eq(instrument)].copy()
            e = eligible.loc[eligible["instrument"].eq(instrument)].copy()
            if not c.empty:
                old = c["candidate_id"].copy()
                c["candidate_id"] = old + suffix
                w = weights.loc[weights["candidate_id"].isin(old)].copy()
                mapping = dict(zip(old, c["candidate_id"]))
                w["candidate_id"] = w["candidate_id"].map(mapping)
                co = candidate_outcomes.loc[candidate_outcomes["candidate_id"].isin(old)].copy()
                co["candidate_id"] = co["candidate_id"].map(mapping)
                candidate_parts.append(c); weight_parts.append(w); cout_parts.append(co)
            if not e.empty:
                olde = e["eligible_candidate_id"].copy()
                e["eligible_candidate_id"] = olde + suffix
                mapping_e = dict(zip(olde, e["eligible_candidate_id"]))
                eo = eligible_outcomes.loc[eligible_outcomes["eligible_candidate_id"].isin(olde)].copy()
                eo["eligible_candidate_id"] = eo["eligible_candidate_id"].map(mapping_e)
                eligible_parts.append(e); eout_parts.append(eo)
        if not candidate_parts or not eligible_parts:
            continue
        c = pd.concat(candidate_parts, ignore_index=True); e = pd.concat(eligible_parts, ignore_index=True)
        w = pd.concat(weight_parts, ignore_index=True); co = pd.concat(cout_parts, ignore_index=True)
        eo = pd.concat(eout_parts, ignore_index=True)
        e = apply_eligible_calendar_weights(e, c, w)
        for column in ["eligible_row_weight_R0", "eligible_row_weight_R1", "eligible_row_weight_R2", "eligible_row_weight_R3"]:
            eo = eo.drop(columns=[column], errors="ignore").merge(e[["eligible_candidate_id", column]], on="eligible_candidate_id", how="left")
        tail = build_arm_tail_readout(c, e, w, co, eo, config, "forward_oos_bootstrap")
        maps = metric_map(tail)
        comparisons = [("R1_vs_R0", ARM_IDS[1], ARM_IDS[0]), ("R2_vs_R0", ARM_IDS[2], ARM_IDS[0]), ("R2_vs_R1", ARM_IDS[2], ARM_IDS[1]), ("R3_vs_R0", ARM_IDS[3], ARM_IDS[0]), ("R3_vs_R2", ARM_IDS[3], ARM_IDS[2])]
        for label, arm, comp in comparisons:
            measures = {
                f"ES10_improvement_{label}": maps[comp]["weighted_ES10_MAE20"] - maps[arm]["weighted_ES10_MAE20"],
                f"MAE_p10_improvement_{label}": maps[arm]["weighted_MAE20_p10"] - maps[comp]["weighted_MAE20_p10"],
                f"p_left_tail_20_relative_reduction_{label}": safe_div(maps[comp]["weighted_p_left_tail_20"] - maps[arm]["weighted_p_left_tail_20"], maps[comp]["weighted_p_left_tail_20"]),
            }
            for metric_id, metric_value in measures.items():
                rows.append({"replication_id": replication_id, "metric_id": metric_id, "metric_value": metric_value, "seed": config["bootstrap"]["seed"], "cluster_key": "instrument"})
        for arm in ARM_IDS[1:]:
            for metric_id, metric_value in {
                f"positive_exposure_ratio_50_primary_{arm}": maps[arm]["positive_exposure_ratio_50_primary_arm_calendar_matched"],
                f"right_tail_capture_retention_{arm}": maps[arm]["right_tail_capture_retention"],
            }.items():
                rows.append({"replication_id": replication_id, "metric_id": metric_id, "metric_value": metric_value, "seed": config["bootstrap"]["seed"], "cluster_key": "instrument"})
    return pd.DataFrame(rows, columns=BOOTSTRAP_SCHEMA)


def leave_one_month_out(
    candidates: pd.DataFrame, eligible: pd.DataFrame, weights: pd.DataFrame,
    candidate_outcomes: pd.DataFrame, eligible_outcomes: pd.DataFrame, config: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    for month in sorted(candidates["decision_month"].unique()):
        c = candidates.loc[~candidates["decision_month"].eq(month)].copy()
        e = eligible.loc[~eligible["decision_month"].eq(month)].copy()
        w = weights.loc[weights["candidate_id"].isin(c["candidate_id"])].copy()
        co = candidate_outcomes.loc[candidate_outcomes["candidate_id"].isin(c["candidate_id"])].copy()
        eo = eligible_outcomes.loc[eligible_outcomes["eligible_candidate_id"].isin(e["eligible_candidate_id"])].copy()
        tail = build_arm_tail_readout(c, e, w, co, eo, config, "leave_one_month_out")
        maps = metric_map(tail)
        es = maps[ARM_IDS[0]]["weighted_ES10_MAE20"] - maps[PRIMARY_ARM]["weighted_ES10_MAE20"]
        mae = maps[PRIMARY_ARM]["weighted_MAE20_p10"] - maps[ARM_IDS[0]]["weighted_MAE20_p10"]
        rows.append({"excluded_decision_month": month, "candidate_n": len(c), "ES10_improvement_R2_vs_R0": es, "MAE_p10_improvement_R2_vs_R0": mae, "direction_pass": es > 0 and mae > 0})
    return pd.DataFrame(rows, columns=MONTH_SCHEMA)


def placebo_readout(
    candidates: pd.DataFrame, weights: pd.DataFrame, candidate_outcomes: pd.DataFrame,
    frozen_hashes: pd.DataFrame, config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if candidates.empty:
        return empty_frame(PLACEBO_SCHEMA), {
            "placebo_replication_n": 0, "observed_R2_vs_R0_ES10_improvement": None, "null_mean": None,
            "null_p95": None, "one_sided_placebo_p_value": None, "seed": config["placebo"]["seed"], "bucket_fallback_count": 0,
        }
    joined = candidates.merge(candidate_outcomes[["candidate_id", "MAE_20"]], on="candidate_id", validate="one_to_one")
    wide = weights.pivot(index="candidate_id", columns="arm_id", values="final_weight")
    r0_es = weighted_es10(wide[ARM_IDS[0]], joined.set_index("candidate_id").loc[wide.index, "MAE_20"], wide.index)
    r2_es = weighted_es10(wide[PRIMARY_ARM], joined.set_index("candidate_id").loc[wide.index, "MAE_20"], wide.index)
    observed = r0_es - r2_es
    rows = []
    fallback_total = 0
    rng = np.random.default_rng(int(config["placebo"]["seed"]))
    for frozen in frozen_hashes.itertuples(index=False):
        assigned, counts = permutation_assignments(candidates, wide[PRIMARY_ARM], config, int(frozen.replication_id), rng=rng)
        digest = assignment_hash(assigned)
        mae = joined.set_index("candidate_id").loc[assigned["candidate_id"], "MAE_20"]
        es = weighted_es10(assigned["assigned_weight"], mae, assigned["candidate_id"])
        improvement = r0_es - es
        fallback_total += counts["fallback"]
        rows.append({
            "replication_id": frozen.replication_id, "assignment_hash": digest,
            "assignment_hash_gate": "pass" if digest == frozen.assignment_hash else "fail",
            "placebo_ES10": es, "placebo_ES10_improvement_vs_R0": improvement,
            "R2_ES10_improvement_vs_R0": observed, "placebo_at_least_as_good_as_R2": improvement >= observed,
            "primary_strata_n": counts["primary"], "fallback_strata_n": counts["fallback"],
            "unchanged_strata_n": counts["unchanged"], "date_gross_invariance_gate": frozen.date_gross_invariance_gate,
            "seed": config["placebo"]["seed"],
        })
    frame = pd.DataFrame(rows, columns=PLACEBO_SCHEMA)
    p_value = (1 + int(frame["placebo_at_least_as_good_as_R2"].sum())) / (1 + len(frame))
    summary = {
        "placebo_replication_n": len(frame), "observed_R2_vs_R0_ES10_improvement": observed,
        "null_mean": float(frame["placebo_ES10_improvement_vs_R0"].mean()),
        "null_p95": float(frame["placebo_ES10_improvement_vs_R0"].quantile(0.95)),
        "one_sided_placebo_p_value": p_value, "seed": config["placebo"]["seed"],
        "bucket_fallback_count": fallback_total,
    }
    return frame, summary


def support_and_concentration(
    candidates: pd.DataFrame,
    eligible: pd.DataFrame,
    weights: pd.DataFrame,
    outcomes: pd.DataFrame,
    eligible_outcomes: pd.DataFrame,
    month: pd.DataFrame,
    config: dict[str, Any],
    sample_scope: str,
) -> pd.DataFrame:
    if candidates.empty:
        return empty_frame(SUPPORT_CONCENTRATION_SCHEMA)
    r2 = weights.loc[weights["arm_id"].eq(PRIMARY_ARM)].merge(candidates[["candidate_id", "instrument", "instrument_month", "decision_month"]], on="candidate_id").merge(outcomes[["candidate_id", "right_tail_50_flag"]], on="candidate_id")
    total = float(r2["final_weight"].sum())
    right_total = float((r2["final_weight"] * r2["right_tail_50_flag"].astype(float)).sum())
    stable_rate = float(month["direction_pass"].mean()) if not month.empty else float("nan")
    instrument_weight = r2.groupby("instrument")["final_weight"].sum().reset_index()
    instrument_weight = instrument_weight.sort_values(["final_weight", "instrument"], ascending=[False, True], kind="mergesort")

    def removal_gate(top_n: int) -> str:
        removed = set(instrument_weight.head(top_n)["instrument"])
        c = candidates.loc[~candidates["instrument"].isin(removed)].copy()
        e = eligible.loc[~eligible["instrument"].isin(removed)].copy()
        w = weights.loc[weights["candidate_id"].isin(c["candidate_id"])].copy()
        co = outcomes.loc[outcomes["candidate_id"].isin(c["candidate_id"])].copy()
        eo = eligible_outcomes.loc[eligible_outcomes["eligible_candidate_id"].isin(e["eligible_candidate_id"])].copy()
        if c.empty or e.empty:
            return "fail"
        e = apply_eligible_calendar_weights(e, c, w)
        for column in ["eligible_row_weight_R0", "eligible_row_weight_R1", "eligible_row_weight_R2", "eligible_row_weight_R3"]:
            eo = eo.drop(columns=[column], errors="ignore").merge(e[["eligible_candidate_id", column]], on="eligible_candidate_id", how="left")
        tail = build_arm_tail_readout(c, e, w, co, eo, config, f"{sample_scope}_top{top_n}_removed")
        if tail.empty:
            return "fail"
        primary = tail.loc[tail["arm_id"].eq(PRIMARY_ARM)].iloc[0]
        return "pass" if (
            primary["ES10_improvement_vs_R0"] > 0
            and primary["positive_exposure_ratio_50_primary_arm_calendar_matched"] >= float(config["forward_gates"]["primary_positive_exposure_ratio_50_min"])
            and primary["right_tail_capture_retention"] >= float(config["forward_gates"]["right_tail_capture_retention_min"])
        ) else "fail"

    top1_gate = removal_gate(1)
    top3_gate = removal_gate(3)
    row = {
        "sample_scope": sample_scope, "arm_id": PRIMARY_ARM,
        "max_instrument_weight_share": safe_div(float(r2.groupby("instrument")["final_weight"].sum().max()), total),
        "max_instrument_right_tail_weight_share": safe_div(float(r2.assign(x=r2["final_weight"] * r2["right_tail_50_flag"].astype(float)).groupby("instrument")["x"].sum().max()), right_total),
        "max_instrument_month_weight_share": safe_div(float(r2.groupby("instrument_month")["final_weight"].sum().max()), total),
        "max_decision_month_weight_share": safe_div(float(r2.groupby("decision_month")["final_weight"].sum().max()), total),
        "top1_removal_sensitivity_gate": top1_gate, "top3_removal_sensitivity_gate": top3_gate,
        "calendar_evaluable_month_n": len(month), "calendar_direction_stable_rate": stable_rate,
    }
    gates = config["forward_gates"]
    row["concentration_gate"] = "pass" if (
        row["max_instrument_weight_share"] <= float(gates["max_instrument_weight_share_cap"])
        and row["max_instrument_right_tail_weight_share"] <= float(gates["max_instrument_right_tail_weight_share_cap"])
        and row["max_instrument_month_weight_share"] <= float(gates["max_instrument_month_weight_share_cap"])
        and row["max_decision_month_weight_share"] <= float(gates["max_decision_month_weight_share_cap"])
        and top1_gate == "pass" and top3_gate == "pass"
        and len(month) >= int(config["forward_support"]["decision_month_n_min"])
        and stable_rate >= float(gates["calendar_direction_stable_rate_min"])
    ) else "fail"
    return pd.DataFrame([row], columns=SUPPORT_CONCENTRATION_SCHEMA)


def not_evaluable_figure(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.axis("off")
    ax.text(0.5, 0.58, title, ha="center", va="center", fontsize=14)
    ax.text(0.5, 0.42, "not_evaluable", ha="center", va="center", fontsize=24, color="firebrick", alpha=0.8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_forward_figures(outputs: dict[str, Path], dry_run: bool, tail: pd.DataFrame, bootstrap: pd.DataFrame, month: pd.DataFrame) -> None:
    figure_keys = [
        "forward_left_tail_frontier", "forward_exposure_capture_frontier",
        "forward_bootstrap_improvement_distribution", "forward_month_stability",
    ]
    if dry_run or tail.empty:
        for key in figure_keys:
            not_evaluable_figure(outputs[key], key.replace("forward_", "").replace("_", " "))
        return
    plots = {
        "forward_left_tail_frontier": (tail["right_tail_capture_retention"], tail["weighted_ES10_MAE20"], "capture", "ES10"),
        "forward_exposure_capture_frontier": (tail["positive_exposure_ratio_50_primary_arm_calendar_matched"], tail["right_tail_capture_retention"], "exposure ratio", "capture"),
    }
    for key, (x, y, xlabel, ylabel) in plots.items():
        fig, ax = plt.subplots(figsize=(7, 4.5)); ax.scatter(x, y)
        for idx, arm in enumerate(tail["arm_id"]): ax.annotate(arm.split("_")[0], (x.iloc[idx], y.iloc[idx]))
        ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); fig.tight_layout(); fig.savefig(outputs[key], dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    series = bootstrap.loc[bootstrap["metric_id"].eq("ES10_improvement_R2_vs_R0"), "metric_value"]
    ax.hist(series, bins=40); ax.set_title("R2 vs R0 bootstrap ES10 improvement"); fig.tight_layout(); fig.savefig(outputs["forward_bootstrap_improvement_distribution"], dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4.5)); ax.plot(month["excluded_decision_month"], month["ES10_improvement_R2_vs_R0"], marker="o"); ax.tick_params(axis="x", rotation=45); fig.tight_layout(); fig.savefig(outputs["forward_month_stability"], dpi=160); plt.close(fig)


def decide_forward(
    config: dict[str, Any], coverage: pd.Series, tail: pd.DataFrame, pairwise: pd.DataFrame,
    bootstrap: pd.DataFrame, placebo_summary: dict[str, Any], concentration: pd.DataFrame,
    right_tail_event_n: int = 0,
) -> dict[str, Any]:
    dry = str(coverage["forward_preoutcome_evaluability_gate"]) != "pass"
    base = {
        "run_id": RUN_ID, "primary_arm_id": PRIMARY_ARM,
        "spent_design_arm_role_gate": "pass", "forward_candidate_n": int(coverage["forward_B2_candidate_n"]),
        "forward_instrument_n": int(coverage["forward_instrument_n"]),
        "forward_decision_month_n": int(coverage["forward_decision_month_n"]),
        "forward_kish_effective_n_R2": float(coverage["forward_R2_effective_exposure_n"]),
        "earliest_evaluable_forward_month": coverage["earliest_evaluable_forward_month"],
        "pipeline_dry_run_only": dry, "forward_evaluability_state": "not_evaluable" if dry else "evaluable",
        "forward_preoutcome_evaluability_gate": coverage["forward_preoutcome_evaluability_gate"],
        "validation_support_floor_feasibility_gate": coverage["validation_support_floor_feasibility_gate"],
        "support_gate": coverage["forward_support_gate"], "primary_left_tail_gate": "not_evaluated",
        "incremental_frontier_gate": "not_evaluated", "right_tail_budget_gate": "not_evaluated",
        "absolute_left_tail_burden_gate": "not_evaluated", "placebo_gate": "not_evaluated",
        "bootstrap_gate": "not_evaluated", "calendar_stability_gate": "not_evaluated",
        "concentration_gate": "not_evaluated", "blocking_reasons": [],
    }
    if dry:
        base.update({
            "forward_state": "19B3_forward_oos_underpowered_not_pass", "validation_stress_authorized": False,
            "next_allowed_stage": "finalize", "forward_outcome_read": False,
            "blocking_reasons": ["forward_preoutcome_evaluability_gate_failed"],
        })
        return base
    maps = metric_map(tail)
    r2 = maps[PRIMARY_ARM]
    pair = pairwise.set_index("comparison_id")
    r2r0 = pair.loc["R2_vs_R0"]
    r2r1 = pair.loc["R2_vs_R1"]
    primary = (
        r2r0["ES10_improvement"] > 0
        and r2r0["ES10_improvement_ci_low"] > 0
        and r2r0["MAE_p10_improvement"] >= float(config["forward_gates"]["mae_20_p10_improvement_vs_r0_min"])
        and r2r0["MAE_p10_improvement_ci_low"] > 0
        and r2r0["p_left_tail_relative_reduction"] >= float(config["forward_gates"]["p_left_tail_20_relative_reduction_vs_r0_min"])
    )
    placebo_value = placebo_summary.get("one_sided_placebo_p_value")
    incremental = (
        r2r1["ES10_improvement"] >= float(config["forward_gates"]["left_tail_es10_improvement_vs_r1_min"])
        and r2r1["ES10_improvement_ci_low"] > 0
        and r2["weighted_MAE20_p10"] >= maps[ARM_IDS[1]]["weighted_MAE20_p10"]
        and placebo_value is not None and placebo_value <= float(config["forward_gates"]["placebo_p_value_max"])
    )
    budget = r2["right_tail_budget_gate"] == "pass"
    absolute = r2["absolute_left_tail_burden_gap_vs_eligible"] <= float(config["forward_gates"]["absolute_mae_worsening_vs_eligible_cap"])
    bootstrap_gate = bool(
        r2r0["ES10_improvement_ci_low"] > 0 and r2r0["MAE_p10_improvement_ci_low"] > 0
        and r2r1["ES10_improvement_ci_low"] > 0
    )
    support_gate = bool(
        r2["support_gate"] == "pass"
        and right_tail_event_n >= int(config["forward_support"]["right_tail_event_50_n_min"])
    )
    concentration_gate = bool(not concentration.empty and concentration.iloc[0]["concentration_gate"] == "pass")
    calendar_gate = bool(
        not concentration.empty
        and concentration.iloc[0]["calendar_evaluable_month_n"] >= int(config["forward_support"]["decision_month_n_min"])
        and concentration.iloc[0]["calendar_direction_stable_rate"] >= float(config["forward_gates"]["calendar_direction_stable_rate_min"])
    )
    base.update({
        "support_gate": "pass" if support_gate else "fail",
        "primary_left_tail_gate": "pass" if primary else "fail",
        "incremental_frontier_gate": "pass" if incremental else "fail",
        "right_tail_budget_gate": "pass" if budget else "fail",
        "absolute_left_tail_burden_gate": "pass" if absolute else "fail",
        "placebo_gate": "pass" if placebo_value is not None and placebo_value <= float(config["forward_gates"]["placebo_p_value_max"]) else "fail",
        "bootstrap_gate": "pass" if bootstrap_gate else "fail",
        "calendar_stability_gate": "pass" if calendar_gate else "fail",
        "concentration_gate": "pass" if concentration_gate else "fail",
        "forward_outcome_read": True,
    })
    if not support_gate:
        state = "19B3_forward_oos_underpowered_not_pass"
    elif not primary or not incremental:
        state = "19B3_forward_no_incremental_left_tail_improvement"
    elif not budget:
        state = "19B3_forward_right_tail_budget_failed"
    elif not (bootstrap_gate and calendar_gate and concentration_gate):
        state = "19B3_forward_support_or_concentration_blocked"
    elif not absolute:
        state = "19B3_forward_left_tail_reduction_supported_but_absolute_burden_high"
    else:
        state = "19B3_forward_positive_exposure_left_tail_budget_supported"
    authorized = state in {
        "19B3_forward_positive_exposure_left_tail_budget_supported",
        "19B3_forward_left_tail_reduction_supported_but_absolute_burden_high",
    }
    base["forward_state"] = state
    base["validation_stress_authorized"] = authorized
    base["next_allowed_stage"] = "validation-stress" if authorized else "finalize"
    base["blocking_reasons"] = [key for key in [
        "support_gate", "primary_left_tail_gate", "incremental_frontier_gate", "right_tail_budget_gate",
        "bootstrap_gate", "calendar_stability_gate", "concentration_gate",
    ] if base[key] == "fail"]
    return base


def forward_stage(config_path: str | Path = CONFIG_PATH) -> dict[str, Path]:
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    paths = resolve_input_paths(config)
    root = resolve_output_root(config)
    outputs = stage_paths(root, "forward")
    ok, reason = verify_bundle(root, "forward")
    if ok:
        identity_ok, identity_reason = verify_freeze_identity(root, config_path)
        if not identity_ok:
            raise RuntimeError(f"freeze stage identity failed: {identity_reason}")
        return outputs
    if (root / "forward/forward_manifest.json").exists():
        raise RuntimeError(f"immutable forward bundle invalid: {reason}")
    freeze_ok, freeze_reason = verify_bundle(root, "freeze")
    if not freeze_ok:
        raise RuntimeError(f"freeze stage lock failed: {freeze_reason}")
    identity_ok, identity_reason = verify_freeze_identity(root, config_path)
    if not identity_ok:
        raise RuntimeError(f"freeze stage identity failed: {identity_reason}")
    started = utc_now()
    freeze_manifest_path, freeze_hashes_path = bundle_paths(root, "freeze")
    freeze_manifest = json_read(freeze_manifest_path)
    critical_failures = [key for key, value in freeze_manifest["critical_gates"].items() if value != "pass"]
    coverage = pd.read_csv(root / "freeze/data_coverage_and_forward_support_audit.csv").iloc[0]
    candidates = pd.read_csv(root / "freeze/forward_candidate_preoutcome_manifest.csv")
    eligible = pd.read_csv(root / "freeze/forward_eligible_preoutcome_manifest.csv")
    weights = pd.read_csv(root / "freeze/forward_arm_weight_manifest.csv")
    frozen_permutations = pd.read_csv(root / "freeze/p0_permutation_assignment_hashes.csv")
    forbidden = [column for column in list(candidates.columns) + list(eligible.columns) + list(weights.columns) if any(token in column.lower() for token in FORBIDDEN_PREOUTCOME_TOKENS)]
    dry = str(coverage["forward_preoutcome_evaluability_gate"]) != "pass" or bool(critical_failures) or bool(forbidden)
    freeze_manifest_hash = file_sha(freeze_manifest_path)

    if dry:
        candidate_outcomes = empty_frame(OUTCOME_SCHEMA)
        eligible_outcomes = empty_frame(ELIGIBLE_OUTCOME_SCHEMA)
        tail = empty_frame(ARM_TAIL_SCHEMA)
        bootstrap = empty_frame(BOOTSTRAP_SCHEMA)
        pairwise = empty_frame(PAIRWISE_SCHEMA)
        month = empty_frame(MONTH_SCHEMA)
        placebo = empty_frame(PLACEBO_SCHEMA)
        placebo_summary = {
            "placebo_replication_n": 0, "observed_R2_vs_R0_ES10_improvement": None, "null_mean": None,
            "null_p95": None, "one_sided_placebo_p_value": None, "seed": config["placebo"]["seed"], "bucket_fallback_count": 0,
        }
        concentration = empty_frame(SUPPORT_CONCENTRATION_SCHEMA)
        access = empty_frame(OUTCOME_ACCESS_SCHEMA)
    else:
        candidate_outcomes, access_candidate = read_outcomes(
            candidates, "candidate_id", config, paths, "forward", freeze_manifest_path, freeze_manifest_hash
        )
        eligible_outcomes, access_eligible = read_outcomes(
            eligible, "eligible_candidate_id", config, paths, "forward", freeze_manifest_path, freeze_manifest_hash
        )
        access = pd.concat([access_candidate, access_eligible], ignore_index=True)
        tail = build_arm_tail_readout(candidates, eligible, weights, candidate_outcomes, eligible_outcomes, config, "forward_oos")
        bootstrap = bootstrap_readout(candidates, eligible, weights, candidate_outcomes, eligible_outcomes, config)
        pairwise = pairwise_from_tail(tail, bootstrap)
        month = leave_one_month_out(candidates, eligible, weights, candidate_outcomes, eligible_outcomes, config)
        placebo, placebo_summary = placebo_readout(candidates, weights, candidate_outcomes, frozen_permutations, config)
        concentration = support_and_concentration(
            candidates, eligible, weights, candidate_outcomes, eligible_outcomes, month, config, "forward_oos"
        )
    right_tail_event_n = int(candidate_outcomes["right_tail_50_flag"].astype(bool).sum()) if not candidate_outcomes.empty else 0
    decision = decide_forward(
        config, coverage, tail, pairwise, bootstrap, placebo_summary, concentration, right_tail_event_n
    )
    decision["forward_right_tail_event_50_n"] = right_tail_event_n
    decision["freeze_manifest_hash"] = freeze_manifest_hash
    if critical_failures or forbidden:
        decision.update({
            "pipeline_dry_run_only": True, "forward_outcome_read": False,
            "forward_state": "19B3_forward_outcome_boundary_blocked", "validation_stress_authorized": False,
            "next_allowed_stage": "finalize",
            "blocking_reasons": critical_failures + (["forbidden_preoutcome_columns"] if forbidden else []),
        })
    write_csv(outputs["forward_outcome_panel"], candidate_outcomes, OUTCOME_SCHEMA)
    write_csv(outputs["forward_eligible_outcome_panel"], eligible_outcomes, ELIGIBLE_OUTCOME_SCHEMA)
    write_csv(outputs["arm_tail_readout"], tail, ARM_TAIL_SCHEMA)
    write_csv(outputs["arm_pairwise_readout"], pairwise, PAIRWISE_SCHEMA)
    write_csv(outputs["cluster_bootstrap_readout"], bootstrap, BOOTSTRAP_SCHEMA)
    write_csv(outputs["leave_one_month_out_readout"], month, MONTH_SCHEMA)
    write_csv(outputs["placebo_null_readout"], placebo, PLACEBO_SCHEMA)
    write_json(outputs["placebo_null_summary"], placebo_summary)
    write_csv(outputs["support_and_concentration_readout"], concentration, SUPPORT_CONCENTRATION_SCHEMA)
    write_json(outputs["forward_decision"], decision)
    write_csv(outputs["outcome_access_audit"], access, OUTCOME_ACCESS_SCHEMA)
    write_forward_figures(outputs, bool(decision["pipeline_dry_run_only"]), tail, bootstrap, month)
    include = [path for path in outputs.values() if path.name not in {"forward_manifest.json", "forward_output_hashes.json"}]
    manifest = {
        "run_id": RUN_ID, "stage": "forward", "stage_started_at": started, "stage_completed_at": utc_now(),
        "freeze_bundle_hash": file_sha(freeze_hashes_path), "freeze_manifest_hash": freeze_manifest_hash,
        "primary_arm_id": PRIMARY_ARM, "pipeline_dry_run_only": decision["pipeline_dry_run_only"],
        "forward_evaluability_state": decision["forward_evaluability_state"], "decision_state": decision["forward_state"],
        "outcome_access_summary": {"forward_outcome_read_n": len(access), "validation_outcome_read_n": 0},
        "required_outputs": [str(path.relative_to(root)) for path in include],
    }
    seal_bundle(root, "forward", manifest, include)
    return outputs


def seal_validation_preoutcome(root: Path, include: list[Path], arm_registry_hash: str) -> tuple[Path, Path]:
    manifest_path = root / "validation_stress/validation_preoutcome_freeze_manifest.json"
    hashes_path = root / "validation_stress/validation_preoutcome_freeze_output_hashes.json"
    hashes = {str(path.relative_to(root)): file_sha(path) for path in sorted(include, key=str)}
    write_json(
        manifest_path,
        {
            "run_id": RUN_ID, "bundle_role": "validation_preoutcome_freeze", "sealed_at": utc_now(),
            "frozen_arm_registry_hash": arm_registry_hash, "output_hashes": hashes,
        },
    )
    write_json(hashes_path, {**hashes, str(manifest_path.relative_to(root)): file_sha(manifest_path)})
    fsync_path(manifest_path)
    fsync_path(hashes_path)
    return manifest_path, hashes_path


def verify_validation_preoutcome(root: Path) -> tuple[bool, str]:
    manifest_path = root / "validation_stress/validation_preoutcome_freeze_manifest.json"
    hashes_path = root / "validation_stress/validation_preoutcome_freeze_output_hashes.json"
    if not manifest_path.exists() or not hashes_path.exists():
        return False, "validation_preoutcome_bundle_missing"
    hashes = json_read(hashes_path)
    for relative, digest in hashes.items():
        path = root / relative
        if not path.exists() or file_sha(path) != digest:
            return False, f"validation_preoutcome_hash_mismatch:{relative}"
    manifest_hashes = {key: value for key, value in hashes.items() if key != str(manifest_path.relative_to(root))}
    return (json_read(manifest_path).get("output_hashes") == manifest_hashes, "")


def validation_stress_stage(config_path: str | Path = CONFIG_PATH) -> dict[str, Path]:
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    paths = resolve_input_paths(config)
    root = resolve_output_root(config)
    outputs = stage_paths(root, "validation-stress")
    ok, reason = verify_bundle(root, "validation-stress")
    if ok:
        identity_ok, identity_reason = verify_freeze_identity(root, config_path)
        if not identity_ok:
            raise RuntimeError(f"freeze stage identity failed: {identity_reason}")
        return outputs
    if (root / "validation_stress/validation_stress_manifest.json").exists():
        raise RuntimeError(f"immutable validation-stress bundle invalid: {reason}")
    forward_ok, forward_reason = verify_bundle(root, "forward")
    if not forward_ok:
        raise RuntimeError(f"forward stage lock failed: {forward_reason}")
    identity_ok, identity_reason = verify_freeze_identity(root, config_path)
    if not identity_ok:
        raise RuntimeError(f"freeze stage identity failed: {identity_reason}")
    forward_decision_path = root / "forward/forward_decision.json"
    forward_decision = json_read(forward_decision_path)
    if not forward_decision.get("validation_stress_authorized", False):
        raise PermissionError("validation-stress is not authorized by immutable forward_decision.json")
    started = utc_now()
    base = root / "validation_stress"
    base.mkdir(parents=True, exist_ok=True)
    coverage = pd.read_csv(root / "freeze/data_coverage_and_forward_support_audit.csv").iloc[0]
    calendar = exchange_calendar(paths)
    validation_min = str(coverage["validation_effective_min_decision_date"])
    validation_max = str(coverage["validation_effective_max_decision_date"])
    min_position = calendar.index(validation_min)
    validation_min_exclusive = calendar[min_position - 1]
    candidates, eligible, _ = build_preoutcome_sample(
        config, paths, validation_min_exclusive, validation_max
    )
    candidate_path = outputs["validation_candidate_preoutcome_manifest"]
    eligible_path = outputs["validation_eligible_preoutcome_manifest"]
    weight_path = outputs["validation_arm_weight_manifest"]
    write_csv(candidate_path, candidates, CANDIDATE_SCHEMA)
    weights, _ = build_arm_weights(candidates, config, file_sha(candidate_path))
    eligible = apply_eligible_calendar_weights(eligible, candidates, weights)
    write_csv(eligible_path, eligible, ELIGIBLE_SCHEMA)
    write_csv(weight_path, weights, WEIGHT_SCHEMA)
    for path in [candidate_path, eligible_path, weight_path]:
        fsync_path(path)
    arm_registry_hash = file_sha(root / "freeze/b2_arm_registry.csv")
    pre_manifest_path, _ = seal_validation_preoutcome(root, [candidate_path, eligible_path, weight_path], arm_registry_hash)
    pre_ok, pre_reason = verify_validation_preoutcome(root)
    if not pre_ok:
        raise RuntimeError(f"validation preoutcome boundary blocked: {pre_reason}")
    pre_manifest_hash = file_sha(pre_manifest_path)
    candidate_outcomes, access_candidate = read_outcomes(
        candidates, "candidate_id", config, paths, "validation-stress", pre_manifest_path, pre_manifest_hash
    )
    eligible_outcomes, access_eligible = read_outcomes(
        eligible, "eligible_candidate_id", config, paths, "validation-stress", pre_manifest_path, pre_manifest_hash
    )
    access = pd.concat([access_candidate, access_eligible], ignore_index=True)
    tail = build_arm_tail_readout(candidates, eligible, weights, candidate_outcomes, eligible_outcomes, config, "validation_stress")
    r2 = tail.loc[tail["arm_id"].eq(PRIMARY_ARM)].iloc[0] if not tail.empty else None
    right_n = int(candidate_outcomes["right_tail_50_flag"].astype(bool).sum()) if not candidate_outcomes.empty else 0
    support = config["forward_support"]
    support_pass = bool(
        r2 is not None and len(candidates) >= int(support["candidate_n_min"])
        and candidates["instrument"].nunique() >= int(support["instrument_n_min"])
        and candidates["instrument_month"].nunique() >= int(support["instrument_month_n_min"])
        and candidates["decision_month"].nunique() >= int(config["validation_stress"]["decision_month_n_min"])
        and right_n >= int(support["right_tail_event_50_n_min"])
        and r2["kish_effective_n"] >= float(support["effective_exposure_n_min"])
    )
    floors = config["validation_stress"]
    directional = bool(
        support_pass
        and r2["positive_exposure_ratio_50_primary_arm_calendar_matched"] >= float(floors["primary_positive_exposure_ratio_50_floor"])
        and r2["right_tail_capture_retention"] >= float(floors["right_tail_capture_retention_floor"])
        and r2["ES10_improvement_vs_R0"] >= float(floors["left_tail_es10_improvement_vs_r0_floor"])
        and r2["MAE_p10_improvement_vs_R0"] >= float(floors["mae_20_p10_improvement_vs_r0_floor"])
        and r2["p_left_tail_20_relative_reduction_vs_R0"] >= float(floors["p_left_tail_20_relative_reduction_vs_r0_floor"])
    )
    stress_state = "no_downgrade" if directional else ("underpowered_not_pass" if not support_pass else "directional_stress_failed")
    decision = {
        "forward_decision_hash": file_sha(forward_decision_path), "stress_access_authorized": True,
        "frozen_arm_registry_hash": arm_registry_hash, "validation_preoutcome_freeze_manifest_hash": pre_manifest_hash,
        "candidate_n": len(candidates), "instrument_n": int(candidates["instrument"].nunique()),
        "decision_month_n": int(candidates["decision_month"].nunique()),
        "kish_effective_n_R2": None if r2 is None else float(r2["kish_effective_n"]),
        "support_gate": "pass" if support_pass else "fail", "directional_stress_gate": "pass" if directional else "fail",
        "stress_state": stress_state, "downgrade_required": not directional, "selection_or_tuning_performed": False,
    }
    write_csv(outputs["validation_outcome_panel"], candidate_outcomes, OUTCOME_SCHEMA)
    write_csv(outputs["validation_eligible_outcome_panel"], eligible_outcomes, ELIGIBLE_OUTCOME_SCHEMA)
    write_csv(outputs["validation_arm_tail_readout"], tail, ARM_TAIL_SCHEMA)
    write_json(outputs["validation_stress_decision"], decision)
    write_csv(outputs["outcome_access_audit"], access, OUTCOME_ACCESS_SCHEMA)
    if tail.empty:
        not_evaluable_figure(outputs["validation_stress_directional_readout"], "validation stress directional readout")
    else:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.bar(tail["arm_id"].str.split("_").str[0], tail["ES10_improvement_vs_R0"])
        ax.axhline(0, color="black", linewidth=0.8); fig.tight_layout(); fig.savefig(outputs["validation_stress_directional_readout"], dpi=160); plt.close(fig)
    include = [path for path in outputs.values() if path.name not in {
        "validation_stress_manifest.json", "validation_stress_output_hashes.json",
    }]
    manifest = {
        "run_id": RUN_ID, "stage": "validation-stress", "stage_started_at": started, "stage_completed_at": utc_now(),
        "forward_bundle_hash": file_sha(root / "forward/forward_output_hashes.json"),
        "validation_preoutcome_freeze_bundle_hash": file_sha(root / "validation_stress/validation_preoutcome_freeze_output_hashes.json"),
        "decision_state": stress_state, "outcome_access_summary": {"validation_outcome_read_n": len(access)},
        "selection_or_tuning_performed": False, "required_outputs": [str(path.relative_to(root)) for path in include],
    }
    seal_bundle(root, "validation-stress", manifest, include)
    return outputs


def final_state(forward: dict[str, Any], stress: dict[str, Any] | None) -> tuple[str, str, str]:
    state = forward["forward_state"]
    mapping = {
        "19B3_forward_oos_underpowered_not_pass": "19B3_forward_oos_underpowered_not_pass",
        "19B3_forward_no_incremental_left_tail_improvement": "19B3_no_incremental_left_tail_improvement",
        "19B3_forward_right_tail_budget_failed": "19B3_right_tail_budget_failed",
        "19B3_forward_support_or_concentration_blocked": "19B3_support_or_concentration_blocked",
        "19B3_forward_outcome_boundary_blocked": "19B3_contract_or_lineage_blocked",
    }
    if state in mapping:
        return mapping[state], "none", ";".join(forward.get("blocking_reasons", []))
    if stress is None:
        return "19B3_validation_stress_incomplete_blocked", "none", "authorized_validation_stress_bundle_missing"
    if stress["stress_state"] == "underpowered_not_pass":
        return "19B3_validation_stress_underpowered_not_pass", "none", "validation_stress_underpowered"
    if stress["stress_state"] != "no_downgrade":
        return "19B3_validation_stress_failed_diagnostic", "none", "validation_directional_veto_failed"
    if state == "19B3_forward_left_tail_reduction_supported_but_absolute_burden_high":
        return "19B3_left_tail_reduction_supported_but_absolute_burden_high", "requirement_19b4_b2_path_aware_left_tail_containment.md", ""
    return "19B3_positive_exposure_left_tail_budget_supported", "requirement_19b4_b2_path_aware_left_tail_containment.md", ""


def report_text(decision: pd.Series, spent: pd.DataFrame, coverage: pd.Series) -> str:
    final_state_value = decision["final_decision_state"]
    forward_outcome_read = not bool(decision["pipeline_dry_run_only"]) and final_state_value != "19B3_contract_or_lineage_blocked"
    validation_outcome_read = bool(decision["validation_stress_authorized"]) and decision["validation_stress_state"] != "not_authorized"
    return f"""# 19B3 B2 正 exposure 左尾预算前沿报告

## 1. Executive decision

最终状态：`{final_state_value}`。当前 forward candidate n = {int(decision.get('forward_candidate_n', 0))}，preoutcome evaluability = `{decision['forward_preoutcome_evaluability_gate']}`。
R2 vs R0、R2 vs R1 与 diagnostic R3 vs R2 均在同一冻结 arm registry 下并列报告；当前不可评价字段保持为空，不以 spent 数据代填。

19B3 的目标是先压低 B2 左尾，在正 exposure 下允许牺牲部分右尾。

## 2. Spent-design arm-role audit（明确 non-support）

robustness 数据只用于 role-selection/design audit，`design_only_no_support_claim = true`。复算了 {len(spent)} 个 R0–R3 arm；R2 是唯一 primary，R3 仍是 diagnostic challenger。该表不进入 forward gate，也不产生 support claim。

## 3. Human restart 与 lineage

本轮来自 research plan Section 12 的 human research restart；19B2 automated handoff 没有授权 19B3。上游 family/grid/hash、B2 rule、entry/cooldown 与 frozen contract 均机械核验。

## 4. Outcome-access / evaluability boundary

spent robustness 的 120-session path end = `{coverage['spent_robustness_outcome_path_end']}`；effective forward start = `{coverage['effective_forward_start']}`；当前数据最多到 `{coverage['benchmark_max_date']}`。
forward preoutcome evaluability gate 通过前，19B3 只是 pipeline dry-run，不产生科学结论。
本轮 forward outcome read = {str(forward_outcome_read).lower()}，validation outcome read = {str(validation_outcome_read).lower()}。

## 5. Forward OOS support

当前没有满足 embargo 后边界且 120-session path 完整的可评价 forward support，因此不读取任何 forward outcome，不运行 bootstrap/placebo outcome 统计，也不授权 validation。

## 6. R2 left-tail reduction frontier 与 R3 diagnostic comparison

R2 A_VOL60_top30 是唯一可晋级 primary arm；R3 continuous budget 只作 diagnostic challenger。
R2 failure 不能由 R1、R3 或 P0 救活；R3 diagnostic 读数不能触发 promotion。

## 7. Positive-exposure denominator bridge / right-tail budget

positive exposure ratio >= 1.20 只使用 arm-calendar-matched eligible denominator；legacy ratio 只作桥接。
两套 denominator 必须并列；bridge delta 只能归因于 denominator construction，不得归因于 R2 exposure 改善。

## 8. Placebo、bootstrap 与 month stability

P0 的 2,000 个 same-day same-gross assignment hash 已在 outcome read 前冻结。当前 not_evaluable，相关 readout 为零行 schema 文件，图带 `not_evaluable` 水印。

## 9. Absolute burden comparison

absolute burden gate 当前未评价；空值没有被写成 0 或 pass。

## 10. Validation pressure test（若被授权）

validation 是压力测试集，不是 arm 选择、调参或正面确认集。
validation thresholds 是 frozen directional veto floors，不是 forward support floors；validation pass != independent positive support。

## 11. Failure interpretation

当前结论是数据覆盖造成的 underpowered，不是 R2 被证伪，也不是 R3 获得支持。至少还需要新的 post-embargo 决策与各自完整 120-session outcome path。

## 12. Decision boundary 与 next step

next_allowed_requirement = `{decision['next_allowed_requirement']}`。
19B3 support 不等于可交易策略 support。
19C replay authorized = false。
EP20 policy preflight authorized = false。
"""


def handoff_text(final_decision: str, next_requirement: str, blocking_reason: str) -> str:
    actionable = final_decision in {
        "19B3_positive_exposure_left_tail_budget_supported",
        "19B3_left_tail_reduction_supported_but_absolute_burden_high",
    }
    return "\n".join([
        "# 19B3 handoff contract", "",
        f"final_decision_state = {final_decision}",
        f"next_allowed_requirement = {next_requirement if actionable else 'none'}",
        f"actionable_handoff = {str(actionable).lower()}",
        f"blocking_reason = {blocking_reason or 'none'}", "",
        "R1/R3 不得升格为 primary；validation 派生阈值不得进入后续 requirement。",
        "19C replay authorized = false。", "EP20 policy preflight authorized = false。", "",
    ])


def finalize_stage(config_path: str | Path = CONFIG_PATH) -> dict[str, Path]:
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    root = resolve_output_root(config)
    outputs = stage_paths(root, "finalize")
    ok, reason = verify_bundle(root, "finalize")
    if ok:
        identity_ok, identity_reason = verify_freeze_identity(root, config_path)
        if not identity_ok:
            raise RuntimeError(f"freeze stage identity failed: {identity_reason}")
        return outputs
    if bundle_paths(root, "finalize")[0].exists():
        raise RuntimeError(f"immutable final bundle invalid: {reason}")
    freeze_ok, freeze_reason = verify_bundle(root, "freeze")
    forward_ok, forward_reason = verify_bundle(root, "forward")
    if not freeze_ok or not forward_ok:
        raise RuntimeError(f"stage lock failed: freeze={freeze_reason};forward={forward_reason}")
    identity_ok, identity_reason = verify_freeze_identity(root, config_path)
    if not identity_ok:
        raise RuntimeError(f"freeze stage identity failed: {identity_reason}")
    started = utc_now()
    forward_path = root / "forward/forward_decision.json"
    forward = json_read(forward_path)
    freeze_meta = json_read(root / "freeze/freeze_manifest_19b3.json")
    freeze_gates = freeze_meta.get("critical_gates", {})
    contract_gate = "pass" if all(value == "pass" for value in freeze_gates.values()) else "fail"
    lineage_gate = "pass" if freeze_gates.get("human_restart_lineage_gate") == "pass" and freeze_gates.get("upstream_contract_gate") == "pass" else "fail"
    stress: dict[str, Any] | None = None
    stress_manifest_hash = ""
    validation_preoutcome_hash = ""
    if forward.get("validation_stress_authorized", False):
        stress_ok, stress_reason = verify_bundle(root, "validation-stress")
        if stress_ok:
            stress = json_read(root / "validation_stress/validation_stress_decision.json")
            stress_manifest_hash = file_sha(root / "validation_stress/validation_stress_manifest.json")
            validation_preoutcome_hash = file_sha(root / "validation_stress/validation_preoutcome_freeze_manifest.json")
        elif (root / "validation_stress").exists():
            raise RuntimeError(f"invalid validation-stress bundle: {stress_reason}")
    state, next_requirement, blocking = final_state(forward, stress)
    tail = pd.read_csv(root / "forward/arm_tail_readout.csv")
    pair = pd.read_csv(root / "forward/arm_pairwise_readout.csv")
    placebo_summary = json_read(root / "forward/placebo_null_summary.json")
    spent = pd.read_csv(root / "freeze/spent_design_arm_role_audit.csv")
    coverage = pd.read_csv(root / "freeze/data_coverage_and_forward_support_audit.csv").iloc[0]
    r2 = tail.loc[tail["arm_id"].eq(PRIMARY_ARM)].iloc[0] if not tail.empty else pd.Series(dtype=object)
    r3 = tail.loc[tail["arm_id"].eq(ARM_IDS[3])].iloc[0] if not tail.empty else pd.Series(dtype=object)
    r2r1 = pair.loc[pair["comparison_id"].eq("R2_vs_R1")].iloc[0] if not pair.empty else pd.Series(dtype=object)
    r3r2 = pair.loc[pair["comparison_id"].eq("R3_vs_R2")].iloc[0] if not pair.empty else pd.Series(dtype=object)

    def get(series: pd.Series, key: str) -> Any:
        value = series.get(key, np.nan)
        return value if not pd.isna(value) else np.nan

    row = {
        "run_id": RUN_ID, "created_at": utc_now(), "requirement_file_hash": file_sha(REQUIREMENT_PATH),
        "config_file_hash": file_sha(config_path), "freeze_manifest_hash": file_sha(root / "freeze/freeze_manifest_19b3.json"),
        "forward_manifest_hash": file_sha(root / "forward/forward_manifest.json"),
        "validation_stress_manifest_hash": stress_manifest_hash, "validation_preoutcome_freeze_manifest_hash": validation_preoutcome_hash,
        "contract_gate": contract_gate, "lineage_gate": lineage_gate, "output_contract_gate": "pass",
        "spent_design_arm_role_gate": forward["spent_design_arm_role_gate"],
        "outcome_access_gate": "pass", "primary_arm_id": PRIMARY_ARM,
        "forward_preoutcome_evaluability_gate": forward["forward_preoutcome_evaluability_gate"],
        "earliest_evaluable_forward_month": forward["earliest_evaluable_forward_month"],
        "pipeline_dry_run_only": forward["pipeline_dry_run_only"], "forward_evaluability_state": forward["forward_evaluability_state"],
        "forward_candidate_n": forward["forward_candidate_n"], "forward_support_gate": forward["support_gate"],
        "forward_primary_left_tail_gate": forward["primary_left_tail_gate"],
        "forward_incremental_frontier_gate": forward["incremental_frontier_gate"],
        "forward_right_tail_budget_gate": forward["right_tail_budget_gate"], "forward_placebo_gate": forward["placebo_gate"],
        "forward_absolute_left_tail_burden_gate": forward["absolute_left_tail_burden_gate"],
        "validation_stress_authorized": forward["validation_stress_authorized"],
        "validation_preoutcome_boundary_gate": "pass" if stress is not None else "not_applicable",
        "validation_stress_gate": stress["directional_stress_gate"] if stress is not None else "not_run",
        "validation_stress_state": stress["stress_state"] if stress is not None else "not_authorized",
        "final_decision_state": state, "blocking_reason": blocking,
        "R2_positive_exposure_ratio_50_primary_arm_calendar_matched": get(r2, "positive_exposure_ratio_50_primary_arm_calendar_matched"),
        "R2_positive_exposure_ratio_50_legacy_bridge": get(r2, "positive_exposure_ratio_50_legacy_bridge"),
        "R2_positive_exposure_ratio_denominator_bridge_delta": get(r2, "positive_exposure_ratio_denominator_bridge_delta"),
        "R2_right_tail_capture_retention": get(r2, "right_tail_capture_retention"),
        "R2_weighted_ES10_MAE20": get(r2, "weighted_ES10_MAE20"), "R2_weighted_MAE20_p10": get(r2, "weighted_MAE20_p10"),
        "R2_weighted_p_left_tail_20": get(r2, "weighted_p_left_tail_20"), "R2_ES10_improvement_vs_R0": get(r2, "ES10_improvement_vs_R0"),
        "R2_ES10_improvement_vs_R1": get(r2r1, "ES10_improvement"), "R2_ES10_improvement_vs_R1_ci_low": get(r2r1, "ES10_improvement_ci_low"),
        "R2_placebo_p_value": placebo_summary.get("one_sided_placebo_p_value"),
        "R3_diagnostic_right_tail_capture_retention": get(r3, "right_tail_capture_retention"),
        "R3_diagnostic_ES10_improvement_vs_R2": get(r3r2, "ES10_improvement"),
        "R3_diagnostic_MAE_p10_improvement_vs_R2": get(r3r2, "MAE_p10_improvement"),
        "next_allowed_requirement": next_requirement,
    }
    row.update({column: False for column in AUTHORIZATION_COLUMNS})
    decision = pd.DataFrame([row])
    write_csv(outputs["entry_universe_19b3_decision"], decision)
    audits = [pd.read_csv(root / "freeze/outcome_access_audit.csv"), pd.read_csv(root / "forward/outcome_access_audit.csv")]
    if stress is not None:
        audits.append(pd.read_csv(root / "validation_stress/outcome_access_audit.csv"))
    write_csv(outputs["outcome_access_audit"], pd.concat(audits, ignore_index=True), OUTCOME_ACCESS_SCHEMA)
    outputs["19B3_b2_positive_exposure_left_tail_budget_frontier_report"].write_text(report_text(decision.iloc[0], spent, coverage), encoding="utf-8")
    outputs["19B3_handoff_contract"].write_text(handoff_text(state, next_requirement, blocking), encoding="utf-8")
    include = [path for path in outputs.values() if path.name not in {
        "manifest_19b3_b2_positive_exposure_left_tail_budget_frontier.json",
        "output_hashes_19b3_b2_positive_exposure_left_tail_budget_frontier.json",
    }]
    manifest = {
        "run_id": RUN_ID, "created_at": utc_now(), "requirement_file": str(REQUIREMENT_PATH),
        "requirement_file_hash": file_sha(REQUIREMENT_PATH), "config_file": str(config_path), "config_file_hash": file_sha(config_path),
        "runner_file_hash": file_sha(Path(__file__)), "human_restart_authorization_hash": file_sha(root / "freeze/human_restart_authorization.json"),
        "source_artifact_hashes": json_read(root / "freeze/freeze_manifest_19b3.json")["source_artifact_hashes"],
        "freeze_bundle_hash": file_sha(root / "freeze/freeze_output_hashes_19b3.json"),
        "forward_bundle_hash": file_sha(root / "forward/forward_output_hashes.json"),
        "validation_preoutcome_freeze_bundle_hash": file_sha(root / "validation_stress/validation_preoutcome_freeze_output_hashes.json") if stress else "",
        "validation_stress_bundle_hash": file_sha(root / "validation_stress/validation_stress_output_hashes.json") if stress else "",
        "stage_execution_order": ["freeze", "forward"] + (["validation-stress"] if stress else []) + ["finalize"],
        "stage_started_at": started, "stage_completed_at": utc_now(), "required_outputs": [str(path.relative_to(root)) for path in include],
        "outcome_access_summary": {"forward_outcome_read_n": int((pd.concat(audits)["split"] == "forward_oos").sum()) if any(len(a) for a in audits) else 0, "validation_outcome_read_n": int((pd.concat(audits)["split"] == "validation_stress").sum()) if any(len(a) for a in audits) else 0},
        "primary_arm_id": PRIMARY_ARM, "forward_evaluability_state": forward["forward_evaluability_state"],
        "decision_state": state, "authorization_state": {column: False for column in AUTHORIZATION_COLUMNS},
        "python_version": platform.python_version(), "pandas_version": pd.__version__, "numpy_version": np.__version__,
    }
    seal_bundle(root, "finalize", manifest, include)
    return outputs


def run(config_path: str | Path = CONFIG_PATH, stage: str = "finalize") -> dict[str, Path]:
    if stage == "freeze":
        return freeze_stage(config_path)
    if stage == "forward":
        return forward_stage(config_path)
    if stage == "validation-stress":
        return validation_stress_stage(config_path)
    if stage == "finalize":
        return finalize_stage(config_path)
    raise ValueError(f"unsupported stage: {stage}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    outputs = run(args.config, args.stage)
    root = resolve_output_root(load_config(args.config))
    print(f"[{RUN_ID}] stage={args.stage} complete: {root}")
    for path in sorted(outputs.values(), key=str):
        if path.exists():
            print(path)


if __name__ == "__main__":
    main()
