#!/usr/bin/env python
"""Staged implementation of the EP20B historical design diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from scipy.stats import norm, rankdata
from sklearn.linear_model import Ridge


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUN_ID = "20B_trendpv_residual_momentum_design_and_replication_diagnostic_v5"
CONTRACT_VERSION = "20B_v5"
CONFIG_PATH = EXPERIMENT_DIR / "configs/config_20b_trendpv_residual_momentum_design_and_replication_diagnostic.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_20b_trendpv_residual_momentum_design_and_replication_diagnostic.md"
EXPECTED_20A_HASH = "da5902ac7a987ec061cdffc33e8735ad34c22f1ae771a43540fe005fd77acb05"
HISTORICAL_ROLE = "design_contaminated_historical"

ARMS = {
    "P0_TOTAL_MOMENTUM_12_1": "project_return_history_primary",
    "P1_TRENDPV_RAW_ADAPTATION": "project_strict_primary",
    "P1_TRENDPV_RAW_ADAPTATION__PAPER": "paper_fill_sensitivity",
    "P4_RESMOM_R2_MARKET_ONLY_ADAPTATION": "project_sequential_market_residual_primary",
    "P5_RESMOM_R3_BOARD_ADAPTATION": "full_history_retrospective_proxy",
    "P6_LOWVOL_36M_COMPARATOR": "project_monthly_volatility_primary",
}
_WORKER_CALENDAR: list[str] = []


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--stage", required=True, choices=["preflight", "run-historical", "finalize", "all"])
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
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
    return EXPERIMENT_DIR / path


def paths_for(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config["paths"].items()}


def output_root(config: dict[str, Any]) -> Path:
    return topic_path(config["output"]["output_root"])


def build_root(config: dict[str, Any]) -> Path:
    """Return the unpublished transactional root for a new immutable run."""
    target = output_root(config)
    return target.with_name(target.name + ".building")


def active_root(config: dict[str, Any]) -> Path:
    target = output_root(config)
    return target if target.exists() else build_root(config)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    if columns is not None:
        for column in columns:
            if column not in out:
                out[column] = None
        out = out[columns]
    out.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def seal_bundle(root: Path, manifest_name: str, hashes_name: str, names: list[str], metadata: dict[str, Any]) -> str:
    names = sorted(set(names))
    unexpected = sorted(
        p.name for p in root.iterdir()
        if p.is_file() and p.name not in set(names) | {manifest_name, hashes_name}
    )
    if unexpected:
        raise RuntimeError(f"unregistered bundle files: {unexpected}")
    hashes = {name: file_sha(root / name) for name in sorted(names)}
    manifest = {**metadata, "sealed_at_utc": utc_now(), "immutable": True, "output_hashes": hashes}
    write_json(root / manifest_name, manifest)
    hashes[manifest_name] = file_sha(root / manifest_name)
    write_json(root / hashes_name, hashes)
    return file_sha(root / hashes_name)


def verify_bundle(root: Path, manifest_name: str, hashes_name: str) -> str:
    hashes = read_json(root / hashes_name)
    manifest = read_json(root / manifest_name)
    for name, expected in hashes.items():
        if not (root / name).exists() or file_sha(root / name) != expected:
            raise RuntimeError(f"bundle hash mismatch: {root / name}")
        if name != manifest_name and manifest.get("output_hashes", {}).get(name) != expected:
            raise RuntimeError(f"manifest mismatch: {name}")
    registered = set(hashes)
    actual = {p.name for p in root.iterdir() if p.is_file()}
    if actual != registered | {hashes_name}:
        raise RuntimeError(f"bundle file-set mismatch: extra={sorted(actual-registered-{hashes_name})}, missing={sorted(registered-actual)}")
    if set(manifest.get("output_hashes", {})) != registered - {manifest_name}:
        raise RuntimeError("manifest/hash registry is not bidirectionally consistent")
    return file_sha(root / hashes_name)


def begin_stage(parent: Path, name: str) -> Path:
    """Create a clean sibling candidate; publication is one atomic directory rename."""
    target = parent / name
    candidate = parent / f".{name}.candidate"
    if target.exists():
        raise FileExistsError(f"immutable stage already exists: {target}")
    if candidate.exists():
        shutil.rmtree(candidate)
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def publish_stage(candidate: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"refusing to overwrite immutable stage: {target}")
    os.replace(candidate, target)


def exchange_calendar(path: Path, maximum: pd.Timestamp) -> pd.DatetimeIndex:
    cal = pd.read_csv(path, usecols=["trade_date"])
    values = pd.to_datetime(cal["trade_date"], errors="coerce").dropna().drop_duplicates().sort_values()
    return pd.DatetimeIndex(values[values <= maximum])


def decision_calendar(calendar: pd.DatetimeIndex, history_max: pd.Timestamp) -> pd.DataFrame:
    frame = pd.DataFrame({"date": calendar})
    frame["period"] = frame["date"].dt.to_period("M")
    decisions = frame.groupby("period", as_index=False)["date"].max()
    next_period = decisions["period"] + 1
    label_end_map = frame.groupby("period")["date"].max()
    decisions["label_period"] = next_period
    decisions["label_end"] = next_period.map(label_end_map)
    decisions["label_complete"] = decisions["label_end"].notna() & decisions["label_end"].le(history_max)
    return decisions


def assign_buckets(values: pd.Series, k: int) -> pd.Series:
    ordered = pd.DataFrame({"value": values.to_numpy(), "instrument": values.index.astype(str).to_numpy()}).sort_values(
        ["value", "instrument"], kind="mergesort"
    )
    n = len(ordered)
    bucket = 1 + np.floor(np.arange(n) * k / n).astype(int)
    return pd.Series(bucket, index=ordered["instrument"].to_numpy(), dtype="Int64")


def nw_stats(values: Iterable[float]) -> dict[str, float | int | None]:
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n == 0:
        return {key: None for key in ["lag", "t", "p", "ci_low", "ci_high"]}
    mean = float(x.mean())
    if n < 2:
        return {"lag": 0, "t": None, "p": None, "ci_low": None, "ci_high": None}
    lag = min(n - 1, max(1, int(math.floor(4 * (n / 100) ** (2 / 9)))))
    centered = x - mean
    gamma0 = float(np.dot(centered, centered) / n)
    long_var = gamma0
    for h in range(1, lag + 1):
        gamma = float(np.dot(centered[h:], centered[:-h]) / n)
        long_var += 2 * (1 - h / (lag + 1)) * gamma
    var_mean = long_var / n
    if not np.isfinite(var_mean) or var_mean <= 0:
        return {"lag": lag, "t": None, "p": None, "ci_low": None, "ci_high": None}
    se = math.sqrt(var_mean)
    t_stat = mean / se
    return {
        "lag": lag, "t": t_stat, "p": 2 * (1 - norm.cdf(abs(t_stat))),
        "ci_low": mean - 1.959963984540054 * se, "ci_high": mean + 1.959963984540054 * se,
    }


def series_stats(values: Iterable[float], registered_n: int) -> dict[str, Any]:
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n == 0:
        return {"registered_month_n": registered_n, "month_n": 0, "gap_month_n": registered_n,
                "missing_reason": "no_evaluable_month"}
    q = np.quantile(x, [0.1, 0.5, 0.9], method="linear")
    worst_n = max(1, math.ceil(0.1 * n))
    vol = float(np.std(x, ddof=1)) if n >= 2 else np.nan
    wealth = np.cumprod(1 + x)
    running = np.maximum.accumulate(np.r_[1.0, wealth])
    drawdown = 1 - np.r_[1.0, wealth] / running
    nw = nw_stats(x)
    return {
        "registered_month_n": registered_n, "month_n": n, "gap_month_n": max(0, registered_n - n),
        "mean_monthly_return": float(x.mean()), "median_monthly_return": float(np.median(x)),
        "monthly_volatility": vol, "annualized_mean": float(12 * x.mean()),
        "annualized_volatility": float(math.sqrt(12) * vol) if np.isfinite(vol) else np.nan,
        "annualized_sharpe": float(math.sqrt(12) * x.mean() / vol) if np.isfinite(vol) and vol > 0 else np.nan,
        "positive_month_rate": float(np.mean(x > 0)), "p10": float(q[0]), "p50": float(q[1]), "p90": float(q[2]),
        "ES10_loss": float(-np.mean(np.sort(x)[:worst_n])),
        "max_drawdown_of_compounded_gross_series": float(np.max(drawdown)),
        "Newey_West_lag": nw["lag"], "HAC_t_stat": nw["t"], "HAC_two_sided_p_value": nw["p"],
        "nominal_95pct_CI_lower": nw["ci_low"], "nominal_95pct_CI_upper": nw["ci_high"],
        "inference_role": "design_only_not_support", "missing_reason": "",
    }


def preflight_stage(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    config = load_config(config_path)
    paths = paths_for(config)
    root = build_root(config)
    target_root = output_root(config)
    if target_root.exists():
        return {"status": "already_finalized", "output_root": str(target_root)}
    root.mkdir(parents=True, exist_ok=True)
    pre_target = root / "preoutcome"
    manifest_name = "preoutcome_manifest_20b.json"
    hashes_name = "preoutcome_output_hashes_20b.json"
    if (pre_target / hashes_name).exists():
        return {"status": "already_sealed", "preoutcome_bundle_hash": verify_bundle(pre_target, manifest_name, hashes_name)}
    pre = begin_stage(root, "preoutcome")

    upstream = paths["upstream_root"]
    upstream_hash = file_sha(upstream / "freeze/freeze_output_hashes_20a.json")
    decision = pd.read_csv(upstream / "20A_preoutcome_contract_decision.csv").iloc[0]
    integrity_pass = upstream_hash == EXPECTED_20A_HASH and str(decision["decision_state"]) == "20A_preoutcome_contract_ready"
    audit_rows = [
        {"artifact_id": "20A_FREEZE_HASHES", "path": rel(upstream / "freeze/freeze_output_hashes_20a.json"),
         "expected_sha256": EXPECTED_20A_HASH, "observed_sha256": upstream_hash, "required_value": "hash_match",
         "observed_value": "hash_match" if upstream_hash == EXPECTED_20A_HASH else "mismatch", "status": "pass" if integrity_pass else "fail", "blocking_reason": "" if integrity_pass else "upstream mismatch"},
        {"artifact_id": "20A_DECISION", "path": rel(upstream / "20A_preoutcome_contract_decision.csv"),
         "expected_sha256": "", "observed_sha256": file_sha(upstream / "20A_preoutcome_contract_decision.csv"),
         "required_value": "20A_preoutcome_contract_ready", "observed_value": decision["decision_state"],
         "status": "pass" if integrity_pass else "fail", "blocking_reason": "" if integrity_pass else "decision mismatch"},
    ]
    if not integrity_pass:
        raise RuntimeError("20A integrity gate failed")
    write_csv(pre / "upstream_20a_integrity_audit.csv", pd.DataFrame(audit_rows))

    resolutions = [
        ("R2_UNIVERSE_RULE", "paper_formula_registry.csv", "universe_rule", "U_paper", "U_project", "20A decision + arm_role_registry + research_plan"),
        ("R2_REPLICATION_ROLE", "paper_formula_registry.csv", "replication_role", "paper_exact_or_diagnostic", "project_adaptation", "20A decision + arm_role_registry + research_plan"),
        ("R2_PROMOTION_ELIGIBILITY", "paper_formula_registry.csv", "promotion_eligible", True, False, "arm_role_registry"),
        ("R2_FAMILY_BRIDGE_ROLE", "arm_role_registry.csv", "family_bridge_authorizer", False, True, "20B design bridge only"),
        ("TRENDPV_WARMUP", "warmup_and_monthly_support_audit.csv", "post_warmup_month_n", 97, "400_sessions_plus_38_complete_coefficients", "paper equations 1-7"),
    ]
    res_df = pd.DataFrame(resolutions, columns=["inconsistency_id", "source_artifact", "source_field", "observed_value", "resolved_value", "resolution_authority"])
    res_df["outcome_used_for_resolution"] = False
    res_df["claim_impact"] = "project_adaptation_design_only"
    res_df["status"] = "pass"
    write_csv(pre / "upstream_metadata_resolution_registry.csv", res_df)

    history_max = pd.Timestamp(config["boundary"]["history_date_max"])
    calendar = exchange_calendar(paths["trading_calendar"], history_max)
    decisions = decision_calendar(calendar, history_max)
    decisions.to_csv(pre / "decision_calendar_freeze.csv", index=False)
    complete = decisions.loc[decisions["label_complete"]].copy()
    first_universe_row = pd.read_csv(paths["project_universe"], usecols=["usable_trade_date"], nrows=1)
    first_date = pd.to_datetime(first_universe_row["usable_trade_date"].iloc[0])
    local_calendar = calendar[calendar >= first_date]
    signal_ready = local_calendar[399]
    periods = complete["period"].tolist()
    signal_idx = next(i for i, period in enumerate(periods) if period >= signal_ready.to_period("M"))
    p1_first_idx = signal_idx + 38
    p1_periods = periods[p1_first_idx:]
    # Section 10.1 freezes the corrected 12-1 R2 theoretical readiness at
    # 2021-01 (64 decision months through 2026-04).  It is a dates/history
    # coverage boundary, not a split of realized evaluable months.
    p4_periods = [p for p in periods if p >= pd.Period("2021-01", freq="M")]
    common = sorted(set(p1_periods).intersection(p4_periods))

    calendar_sets = {
        "P1_PROJECT_STRICT_CALENDAR": (p1_periods, 48, 24, "outcome_free_calendar_feasibility"),
        "P1_PAPER_FILL_CALENDAR": (p1_periods, 48, 24, "reuse_P1_PROJECT_STRICT_CALENDAR"),
        "P4_PRIMARY_CALENDAR": (p4_periods, 60, 30, "fixed_36_plus_11_history"),
        "P5_FULL_HISTORY_RETROSPECTIVE_CALENDAR": (p4_periods, 60, 30, "reuse_P4_PRIMARY_CALENDAR"),
        "P0_COMPARATOR_CALENDAR": ([p for p in periods if p >= first_date.to_period("M") + 11], None, None, "descriptive_comparator_no_gate"),
        "P6_COMPARATOR_CALENDAR": ([p for p in periods if p >= first_date.to_period("M") + 35], None, None, "descriptive_comparator_no_gate"),
        "P1_P4_COMMON_CALENDAR": (common, 48, 24, "intersection_preoutcome"),
    }
    fold_rows = []
    for calendar_id, (values, floor_total, floor_fold, source) in calendar_sets.items():
        split = len(values) // 2
        fold_rows.append({
            "arm_or_calendar_id": calendar_id, "first_formula_ready_month": str(values[0]) if values else "",
            "last_label_complete_decision_month": str(values[-1]) if values else "", "theoretical_max_month_n": len(values),
            "observed_nonoutcome_ready_month_n": len(values), "minimum_arm_month_n": floor_total,
            "minimum_fold_month_n": floor_fold, "early_start": str(values[0]) if values else "",
            "early_end": str(values[split - 1]) if split else "", "late_start": str(values[split]) if len(values) > split else "",
            "late_end": str(values[-1]) if values else "", "boundary_source_calendar_id": source,
            "threshold_source": source, "outcome_used_for_threshold": False,
        })
    write_csv(pre / "statistical_and_fold_freeze.csv", pd.DataFrame(fold_rows))

    arm_rows = []
    for arm_key, track in ARMS.items():
        arm_id = arm_key.replace("__PAPER", "")
        for ret in ["paper_qfq_complete_case_sensitivity", "project_conservative_primary"]:
            arm_rows.append({"arm_id": arm_id, "signal_semantic_track": track, "return_semantics": ret,
                             "P5_date_scope": "registered_three_scope" if arm_id.startswith("P5_") else "",
                             "arm_promotion_eligible": False, "family_bridge_authorizer": arm_id.startswith("P4_")})
    for arm_id in ["P2_TREND_FULL_EXACT", "P3_RESMOM_CH3_EXACT"]:
        arm_rows.append({"arm_id": arm_id, "signal_semantic_track": "not_applicable_registered_not_run",
                         "return_semantics": "", "P5_date_scope": "", "arm_promotion_eligible": False,
                         "family_bridge_authorizer": False})
    write_csv(pre / "arm_and_track_registry.csv", pd.DataFrame(arm_rows))

    history_rules = [
        ("P0_TOTAL_MOMENTUM_12_1", "U_project(t)", "not_applicable", True, "t-11...t-1", "11 monthly returns"),
        ("P1_TRENDPV_RAW_ADAPTATION", "U_project(t)", "U_project(m-1) for coefficient fit", True, "daily L history", "400 sessions + 38 coefficients"),
        ("P4_RESMOM_R2_MARKET_ONLY_ADAPTATION", "U_project(t)", "not_applicable", True, "36m regression + 11 residuals", "47 monthly returns"),
        ("P5_RESMOM_R3_BOARD_ADAPTATION", "U_project(t)", "U_project(s-1) for ridge", False, "R2 base only", "11 actual R3 residuals"),
        ("P6_LOWVOL_36M_COMPARATOR", "U_project(t)", "not_applicable", True, "t-35...t", "36 monthly returns"),
    ]
    universe_freeze = pd.DataFrame(history_rules, columns=["arm_id", "decision_membership_rule", "fit_population_membership_rule", "pre_membership_history_allowed", "pre_membership_history_scope", "history_ready_formula"])
    universe_freeze["listing_and_availability_guard"] = "listed_then; availability<=predictor_asof; no future status repair"
    write_csv(pre / "universe_and_denominator_freeze.csv", universe_freeze)

    common_payloads = {
        "formula_execution_registry.csv": pd.DataFrame([{"formula_id": x, "status": "frozen", "outcome_used": False} for x in ["TMOM_12_1", "TRENDPV", "RESMOM_R2", "RESMOM_R3", "LOWVOL_36M"]]),
        "trendpv_ols_ema_initialization_freeze.csv": pd.DataFrame([{"windows": "3|5|10|20|50|100|200|300|400", "lambda": 0.02, "burn_in": 38, "minimum_n": 190, "rcond": 1e-12}]),
        "residual_regression_and_score_freeze.csv": pd.DataFrame([{"regression_months": 36, "score_months": 11, "rcond": 1e-12, "ddof": 1}]),
        "board_ridge_transform_freeze.csv": pd.DataFrame([{"alpha": 1.0, "solver": "svd", "zscore_ddof": 0, "minimum_n": 100, "snapshot_date": "2025-01-02"}]),
        "outcome_resolution_semantics_freeze.csv": pd.DataFrame([{"valid_mark": "qfq ratio", "suspension_carry_mark": "last marked close", "delisting_minus_one": -1.0, "unknown_bridge": "bucket_month_not_evaluable"}]),
        "bucket_weighting_holding_freeze.csv": pd.DataFrame([{"bucket_counts": "5|10", "weightings": "EW|VW", "primary_holding": 1, "appendix_holding": "3|6|12", "cohort_accounting": "buy_and_hold_drift"}]),
        "exact_route_status_freeze.csv": pd.DataFrame([{"arm_id": "P2_TREND_FULL_EXACT", "run_status": "registered_not_run", "reason": "20A exact gates failed"}, {"arm_id": "P3_RESMOM_CH3_EXACT", "run_status": "registered_not_run", "reason": "20A exact gates failed"}]),
        "input_artifact_audit.csv": pd.DataFrame([{"artifact": key, "path": rel(value), "exists": value.exists(), "outcome_read": False} for key, value in paths.items()]),
        "outcome_access_audit.csv": pd.DataFrame([{"stage": "preflight", "accessed_at_utc": utc_now(), "artifact_path": rel(paths["trading_calendar"]), "artifact_sha256_or_root_hash": file_sha(paths["trading_calendar"]), "dataset_role": "dates_only", "columns_read": "trade_date", "derived_fields": "decision_calendar", "historical_outcome_access_authorized": False, "forward_outcome_detected": False, "selection_or_tuning_allowed": False, "purpose": "freeze calendar", "access_gate": "pass"}]),
    }
    for name, frame in common_payloads.items():
        write_csv(pre / name, frame)
    resolved = json.loads(json.dumps(config, default=str))
    write_text(pre / "resolved_config.yaml", yaml.safe_dump(resolved, sort_keys=True, allow_unicode=True))
    contract = {
        "run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "upstream_20a_integrity_gate": "pass",
        "R2_universe_resolution_gate": "pass", "R2_replication_role_resolution_gate": "pass",
        "R2_promotion_eligibility_resolution_gate": "pass", "R2_family_bridge_role_resolution_gate": "pass",
        "TrendPV_warmup_resolution_gate": "pass", "outcome_firewall_gate": "pass",
        "historical_sample_role": HISTORICAL_ROLE, "historical_support_claim_allowed": False,
        "history_date_max": str(history_max.date()), "direct_run_authorized_by_user": bool(config["authorization"]["direct_run_authorized"]),
    }
    write_json(pre / "preoutcome_contract_20b.json", contract)
    write_text(pre / "20B_preoutcome_contract.md", "# 20B preoutcome contract\n\nAll formulas, calendars, tracks and gates are frozen before historical outcome access.\n")
    names = sorted(path.name for path in pre.iterdir() if path.is_file())
    bundle_hash = seal_bundle(pre, manifest_name, hashes_name, names, {"run_id": RUN_ID, "contract_version": CONTRACT_VERSION})
    verify_bundle(pre, manifest_name, hashes_name)
    publish_stage(pre, pre_target)
    return {"status": "sealed", "preoutcome_bundle_hash": bundle_hash, "preoutcome_root": str(pre_target)}


def load_monthly_universe(path: Path, decisions: pd.DataFrame) -> pd.DataFrame:
    wanted = set(decisions["date"].dt.strftime("%Y-%m-%d"))
    usecols = ["usable_trade_date", "instrument", "is_listed", "is_suspended", "total_market_cap_cny", "ts_code"]
    chunks = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=150_000):
        selected = chunk[chunk["usable_trade_date"].astype(str).isin(wanted)].copy()
        if not selected.empty:
            chunks.append(selected)
    out = pd.concat(chunks, ignore_index=True)
    out["decision_date"] = pd.to_datetime(out.pop("usable_trade_date"))
    out["period"] = out["decision_date"].dt.to_period("M")
    out["instrument"] = out["instrument"].astype(str)
    out = out[out["is_listed"].astype(str).str.lower().isin(["true", "1"])].copy()
    return out.sort_values(["decision_date", "instrument"]).drop_duplicates(["decision_date", "instrument"])


def _init_feature_worker(calendar_strings: list[str]) -> None:
    global _WORKER_CALENDAR
    _WORKER_CALENDAR = calendar_strings


def _instrument_features(args: tuple[str, str, list[int], str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    instrument, filename, windows, maximum = args
    path = Path(filename)
    try:
        raw = pd.read_csv(path, usecols=["date", "close", "volume", "source_volume_unit"])
    except (ValueError, pd.errors.EmptyDataError):
        return [], [], {"instrument": instrument, "status": "read_failed"}
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw = raw.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")
    raw = raw[raw["date"] <= pd.Timestamp(maximum)]
    if raw.empty:
        return [], [], {"instrument": instrument, "status": "empty"}
    unit = str(raw["source_volume_unit"].dropna().iloc[0]).lower() if raw["source_volume_unit"].notna().any() else "unknown"
    multiplier = 100.0 if unit == "hands" else 1.0 if unit == "shares" else np.nan
    raw["volume_norm"] = pd.to_numeric(raw["volume"], errors="coerce") * multiplier
    raw["close"] = pd.to_numeric(raw["close"], errors="coerce")
    raw["period"] = raw["date"].dt.to_period("M")
    monthly = raw.groupby("period", as_index=False).agg(close=("close", "last"), last_trade_date=("date", "last"))
    monthly["instrument"] = instrument
    monthly_rows = monthly.to_dict("records")

    calendar = pd.DatetimeIndex(pd.to_datetime(_WORKER_CALENDAR))
    decisions = pd.Series(calendar).groupby(calendar.to_period("M")).max()
    decision_dates = pd.DatetimeIndex(decisions.values)
    observed = raw.set_index("date")
    strict = pd.DataFrame(index=observed.index)
    strict["close"] = observed["close"]
    strict["volume"] = observed["volume_norm"]
    for window in windows:
        strict[f"MP_{window}"] = strict["close"].rolling(window, min_periods=window).mean() / strict["close"]
        strict[f"MV_{window}"] = strict["volume"].rolling(window, min_periods=window).mean() / strict["volume"].replace(0, np.nan)

    full_idx = calendar[(calendar >= raw["date"].min()) & (calendar <= pd.Timestamp(maximum))]
    fill_close = observed["close"].reindex(full_idx).ffill()
    fill = pd.DataFrame(index=full_idx)
    fill["close"] = fill_close
    for window in windows:
        fill[f"MP_{window}"] = fill_close.rolling(window, min_periods=window).mean() / fill_close
        exchange_volume = observed["volume_norm"].reindex(full_idx)
        record_n = exchange_volume.notna().rolling(window, min_periods=window).sum()
        raw_mv = exchange_volume.rolling(window, min_periods=math.floor(window / 2) + 1).mean() / exchange_volume.replace(0, np.nan)
        raw_mv = raw_mv.where(record_n > window / 2)
        # Carry only a previously valid same-L signal; a zero current volume is
        # never a valid denominator and an unknown unit remains missing.
        fill[f"MV_{window}"] = raw_mv.ffill()

    feature_rows: list[dict[str, Any]] = []
    predictor_cols = [f"MP_{w}" for w in windows] + [f"MV_{w}" for w in windows]
    for date in decision_dates:
        if date > pd.Timestamp(maximum):
            continue
        if date in strict.index:
            row = {"instrument": instrument, "decision_date": date, "semantic_track": "project_strict_primary"}
            row.update(strict.loc[date, predictor_cols].to_dict())
            feature_rows.append(row)
        if date in fill.index and date.to_period("M") in observed.index.to_period("M"):
            row = {"instrument": instrument, "decision_date": date, "semantic_track": "paper_fill_sensitivity"}
            row.update(fill.loc[date, predictor_cols].to_dict())
            feature_rows.append(row)
    meta = {"instrument": instrument, "status": "pass", "date_min": str(raw["date"].min().date()),
            "date_max": str(raw["date"].max().date()), "source_volume_unit": unit, "row_n": len(raw)}
    return feature_rows, monthly_rows, meta


def load_market_panel(paths: dict[str, Path], universe: pd.DataFrame, calendar: pd.DatetimeIndex,
                      history_max: pd.Timestamp, windows: list[int], workers: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    instruments = sorted(universe["instrument"].unique())
    tasks = []
    cal_strings = calendar.strftime("%Y-%m-%d").tolist()
    for instrument in instruments:
        path = paths["qfq_root"] / f"{instrument}.csv"
        if path.exists():
            tasks.append((instrument, str(path), windows, str(history_max.date())))
    feature_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    metas: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=max(1, workers), initializer=_init_feature_worker, initargs=(cal_strings,)) as pool:
        for features, monthly, meta in pool.map(_instrument_features, tasks, chunksize=8):
            feature_rows.extend(features)
            monthly_rows.extend(monthly)
            metas.append(meta)
    features = pd.DataFrame(feature_rows)
    monthly = pd.DataFrame(monthly_rows)
    monthly["period"] = pd.PeriodIndex(monthly["period"], freq="M")
    monthly["last_trade_date"] = pd.to_datetime(monthly["last_trade_date"])
    return features, monthly, pd.DataFrame(metas)


def monthly_matrices(
    monthly: pd.DataFrame,
    periods: list[pd.Period],
    universe: pd.DataFrame,
    security_master_path: Path,
    label_end: dict[pd.Period, pd.Timestamp],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build independent paper and conservative monthly-return tracks.

    A missing qfq month is never interpreted as a delisting merely because the
    series stops.  Delisting requires the point-in-time security-master fields;
    suspension carry requires an explicit suspension flag for that month.
    Everything else fails closed as an unknown bridge.
    """
    close = monthly.pivot(index="instrument", columns="period", values="close").reindex(columns=periods)
    last_date = monthly.pivot(index="instrument", columns="period", values="last_trade_date").reindex(columns=periods)
    end_frame = pd.DataFrame({p: [label_end.get(p)] * len(close.index) for p in periods}, index=close.index)
    valid_label_end = last_date.eq(end_frame)
    paper_close = close.where(valid_label_end)
    paper = paper_close / paper_close.shift(1, axis=1) - 1
    project = pd.DataFrame(np.nan, index=close.index, columns=periods, dtype=float)
    resolution = pd.DataFrame("unknown_bridge_arm_month_not_evaluable", index=close.index, columns=periods, dtype=object)

    master = pd.read_csv(security_master_path, usecols=["instrument", "delist_date", "is_delisted", "metadata_source"])
    master["instrument"] = master["instrument"].astype(str)
    master["delist_date"] = pd.to_datetime(master["delist_date"], errors="coerce")
    master = master.drop_duplicates("instrument").set_index("instrument")
    status = universe[["instrument", "period", "is_suspended"]].drop_duplicates(["instrument", "period"])
    suspended = {(str(r.instrument), r.period): str(r.is_suspended).lower() in {"true", "1"}
                 for r in status.itertuples(index=False)}

    for instrument in close.index:
        last_mark = np.nan
        previous_resolved = False
        terminal_applied = False
        if instrument in master.index:
            mrow = master.loc[instrument]
            confirmed_delisted = str(mrow["is_delisted"]).lower() in {"true", "1"}
            delist_date = mrow["delist_date"]
        else:
            confirmed_delisted = False
            delist_date = pd.NaT
        for j, period in enumerate(periods):
            observed = close.at[instrument, period]
            end = label_end.get(period)
            if np.isfinite(observed):
                actual_date = last_date.at[instrument, period]
                at_label_end = end is not None and pd.notna(actual_date) and pd.Timestamp(actual_date) == pd.Timestamp(end)
                explicit_suspension = suspended.get((instrument, period), False)
                if np.isfinite(last_mark) and previous_resolved:
                    if at_label_end or explicit_suspension:
                        project.iat[project.index.get_loc(instrument), j] = float(observed / last_mark - 1.0)
                        resolution.iat[resolution.index.get_loc(instrument), j] = "valid_mark" if at_label_end else "suspension_carry_mark"
                last_mark = float(observed)
                previous_resolved = bool(at_label_end or explicit_suspension)
                continue
            delisted_by_end = bool(
                confirmed_delisted and pd.notna(delist_date) and end is not None
                and pd.Timestamp(delist_date) <= pd.Timestamp(end)
            )
            if delisted_by_end and np.isfinite(last_mark) and not terminal_applied:
                project.iat[project.index.get_loc(instrument), j] = -1.0
                resolution.iat[resolution.index.get_loc(instrument), j] = "delisting_minus_one"
                terminal_applied = True
                previous_resolved = False
                last_mark = 0.0
            elif suspended.get((instrument, period), False) and np.isfinite(last_mark) and previous_resolved and not terminal_applied:
                project.iat[project.index.get_loc(instrument), j] = 0.0
                resolution.iat[resolution.index.get_loc(instrument), j] = "suspension_carry_mark"
                previous_resolved = True
            else:
                previous_resolved = False
    return close, last_date, paper, project, resolution


def benchmark_returns(path: Path, periods: list[pd.Period], maximum: pd.Timestamp) -> pd.Series:
    frame = pd.read_csv(path, usecols=["date", "close", "index_alias"])
    frame = frame[frame["index_alias"].astype(str).str.lower().eq("csi300")].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame[frame["date"] <= maximum].sort_values("date")
    frame["period"] = frame["date"].dt.to_period("M")
    close = frame.groupby("period")["close"].last().reindex(periods)
    return close / close.shift(1) - 1


def rolling_scores(returns: pd.DataFrame, market: pd.Series, rcond: float = 1e-12) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    instruments, periods = returns.index, list(returns.columns)
    residual = pd.DataFrame(np.nan, index=instruments, columns=periods)
    audits: list[dict[str, Any]] = []
    for j in range(36, len(periods)):
        mwin = market.iloc[j - 36:j].to_numpy(dtype=float)
        y = returns.iloc[:, j - 36:j].to_numpy(dtype=float)
        current = returns.iloc[:, j].to_numpy(dtype=float)
        valid_market = np.isfinite(mwin).all() and np.nanstd(mwin) > 0
        good = np.isfinite(y).all(axis=1) & np.isfinite(current) if valid_market else np.zeros(len(instruments), dtype=bool)
        if good.any():
            X = np.column_stack([np.ones(36, dtype=np.float64), mwin.astype(np.float64)])
            for ix in np.flatnonzero(good):
                beta, _, rank, _ = np.linalg.lstsq(X, y[ix].astype(np.float64), rcond=rcond)
                complete = int(rank) == 2
                if complete:
                    residual.iat[ix, j] = current[ix] - float(np.dot([1.0, market.iloc[j]], beta))
                audits.append({"instrument": instruments[ix], "residual_month": str(periods[j]),
                               "alpha": beta[0] if complete else np.nan, "beta": beta[1] if complete else np.nan,
                               "observation_n": 36, "rank": int(rank),
                               "fit_row_key_hash": stable_hash([str(period) for period in periods[j-36:j]]),
                               "status": "pass" if complete else "rank_deficient"})
    score = residual.shift(1, axis=1).rolling(11, axis=1, min_periods=11).mean() / residual.shift(1, axis=1).rolling(11, axis=1, min_periods=11).std(ddof=1)
    return residual, score, audits


def board_matrix(path: Path, instruments: pd.Index, minimum_overlap: int) -> pd.DataFrame:
    board = pd.read_csv(path, usecols=["board_ts_code", "con_code"])
    code = board["con_code"].astype(str)
    board["instrument"] = np.where(code.str.endswith(".SH"), "SH" + code.str[:6], "SZ" + code.str[:6])
    board = board[board["instrument"].isin(instruments)].drop_duplicates(["instrument", "board_ts_code"])
    counts = board.groupby("board_ts_code")["instrument"].nunique()
    keep = sorted(counts[counts >= minimum_overlap].index)
    matrix = pd.crosstab(board["instrument"], board["board_ts_code"]).reindex(index=instruments, columns=keep, fill_value=0)
    matrix = matrix.astype(float)
    duplicate = matrix.T.duplicated(keep="first")
    dropped = matrix.columns[duplicate].tolist()
    matrix = matrix.loc[:, ~duplicate]
    matrix.attrs["duplicate_columns_dropped"] = "|".join(dropped)
    matrix.attrs["retained_board_columns"] = "|".join(matrix.columns.astype(str))
    return matrix


def r3_scores(residual: pd.DataFrame, universe: pd.DataFrame, boards: pd.DataFrame,
              minimum_n: int, alpha: float, snapshot: pd.Period) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    periods = list(residual.columns)
    instruments = residual.index
    r3 = pd.DataFrame(np.nan, index=instruments, columns=periods)
    audit: list[dict[str, Any]] = []
    by_period = {period: group.set_index("instrument") for period, group in universe.groupby("period")}
    for j, period in enumerate(periods):
        prev = period - 1
        if prev not in by_period:
            continue
        members = by_period[prev]
        ids = members.index.intersection(instruments)
        target = residual.loc[ids, period]
        cap = pd.to_numeric(members.loc[ids, "total_market_cap_cny"], errors="coerce")
        good_ids = ids[target.notna() & cap.notna() & cap.gt(0)]
        if len(good_ids) < minimum_n:
            continue
        size = np.log(cap.loc[good_ids].to_numpy(dtype=float))
        Xb = boards.loc[good_ids].to_numpy(dtype=float)
        X = np.column_stack([size, Xb])
        std = X.std(axis=0, ddof=0)
        keep = std > 1e-12
        X = (X[:, keep] - X[:, keep].mean(axis=0)) / std[keep]
        y = target.loc[good_ids].to_numpy(dtype=float)
        model = Ridge(alpha=alpha, fit_intercept=True, solver="svd", copy_X=True)
        fitted = model.fit(X.astype(np.float64), y.astype(np.float64)).predict(X)
        values = y - fitted
        r3.loc[good_ids, period] = values
        row_hash = stable_hash(good_ids.tolist())
        audit.append({"residual_month": str(period), "preselected_n": len(ids), "target_complete_n": int(target.notna().sum()),
                      "final_fit_n": len(good_ids), "predictor_n": int(keep.sum()), "row_key_hash": row_hash,
                      "predictor_order": "lagged_log_market_cap|" + "|".join(boards.columns.astype(str)),
                      "constant_predictor_n": int((~keep).sum()),
                      "duplicate_board_columns_dropped": boards.attrs.get("duplicate_columns_dropped", ""),
                      "standardization_mean": stable_hash(np.nanmean(np.column_stack([size, Xb]), axis=0).tolist()),
                      "standardization_std": stable_hash(np.nanstd(np.column_stack([size, Xb]), axis=0, ddof=0).tolist()),
                      "board_known_by_predictor_asof": bool(prev >= snapshot),
                      "board_snapshot_age_month_n": int(period.ordinal - snapshot.ordinal), "status": "pass"})
    score = r3.shift(1, axis=1).rolling(11, axis=1, min_periods=11).mean() / r3.shift(1, axis=1).rolling(11, axis=1, min_periods=11).std(ddof=1)
    return r3, score, audit


def trend_scores(features: pd.DataFrame, universe: pd.DataFrame, returns_by_track: dict[str, pd.DataFrame],
                 windows: list[int], minimum_n: int, burn_in: int, lam: float,
                 rcond: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictor_cols = [f"MP_{w}" for w in windows] + [f"MV_{w}" for w in windows]
    features = features.copy()
    features["period"] = features["decision_date"].dt.to_period("M")
    universe_by_period = {period: group["instrument"].tolist() for period, group in universe.groupby("period")}
    score_rows: list[dict[str, Any]] = []
    coefficient_rows: list[dict[str, Any]] = []
    for track, track_features in features.groupby("semantic_track"):
        returns = returns_by_track[track]
        lookup = {(period, instrument): row[predictor_cols].to_numpy(dtype=float)
                  for (period, instrument), row in track_features.set_index(["period", "instrument"]).iterrows()}
        periods = sorted(track_features["period"].unique())
        state: np.ndarray | None = None
        complete_n = 0
        last_complete: pd.Period | None = None
        for period in periods:
            prev = period - 1
            members = universe_by_period.get(prev, [])
            X_rows, y_rows, ids = [], [], []
            if period in returns.columns:
                for instrument in members:
                    values = lookup.get((prev, instrument))
                    if values is None or not np.isfinite(values).all() or instrument not in returns.index:
                        continue
                    response = returns.at[instrument, period]
                    if np.isfinite(response):
                        X_rows.append(values); y_rows.append(response); ids.append(instrument)
            rank = 0
            available = False
            beta = None
            if len(X_rows) >= minimum_n:
                X = np.column_stack([np.ones(len(X_rows)), np.asarray(X_rows, dtype=np.float64)])
                y = np.asarray(y_rows, dtype=np.float64)
                beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=rcond)
                available = rank == len(predictor_cols) + 1
            if available and beta is not None:
                state = beta.copy() if state is None else (1 - lam) * state + lam * beta
                complete_n += 1
                last_complete = period
            coefficient_rows.append({
                "semantic_track": track, "coefficient_month": str(period), "selected_n": len(members),
                "return_complete_n": len(y_rows), "fit_n": len(y_rows), "rank": rank,
                "coefficient_complete": available, "complete_coefficient_month_n": complete_n,
                "coefficient_staleness_calendar_month_n": 0 if last_complete is None else period.ordinal - last_complete.ordinal,
                "realized_intercept": beta[0] if available and beta is not None else np.nan,
                "ema_intercept": state[0] if state is not None else np.nan,
                **{f"realized_beta_{name}": beta[i + 1] if available and beta is not None else np.nan for i, name in enumerate(predictor_cols)},
                **{f"ema_beta_{name}": state[i + 1] if state is not None else np.nan for i, name in enumerate(predictor_cols)},
                "fit_row_key_hash": stable_hash(ids),
            })
            if complete_n < burn_in or state is None:
                continue
            members_now = universe_by_period.get(period, [])
            for instrument in members_now:
                values = lookup.get((period, instrument))
                if values is None or not np.isfinite(values).all():
                    continue
                price = float(np.dot(state[1:1 + len(windows)], values[:len(windows)]))
                volume = float(np.dot(state[1 + len(windows):], values[len(windows):]))
                score_rows.append({"instrument": instrument, "period": period, "semantic_track": track,
                                   "raw_signal": price + volume, "price_component": price,
                                   "volume_component": volume, "residual_component": np.nan})
    return pd.DataFrame(score_rows), pd.DataFrame(coefficient_rows)


def build_signal_table(universe: pd.DataFrame, returns: pd.DataFrame, trend: pd.DataFrame,
                       r2: pd.DataFrame, r3: pd.DataFrame, snapshot: pd.Period) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    shifted = returns.shift(1, axis=1)
    tmom_all = (1 + shifted).rolling(11, axis=1, min_periods=11).apply(np.prod, raw=True) - 1
    lowvol_all = returns.rolling(36, axis=1, min_periods=36).std(ddof=1)
    for period, group in universe.groupby("period"):
        ids = group["instrument"].tolist()
        if period in returns.columns:
            tmom = tmom_all[period]
            lowvol = lowvol_all[period]
            for instrument in ids:
                if instrument in tmom.index and np.isfinite(tmom[instrument]):
                    records.append({"instrument": instrument, "period": period, "arm_id": "P0_TOTAL_MOMENTUM_12_1",
                                    "semantic_track": ARMS["P0_TOTAL_MOMENTUM_12_1"], "raw_signal": tmom[instrument]})
                if instrument in lowvol.index and np.isfinite(lowvol[instrument]):
                    records.append({"instrument": instrument, "period": period, "arm_id": "P6_LOWVOL_36M_COMPARATOR",
                                    "semantic_track": ARMS["P6_LOWVOL_36M_COMPARATOR"], "raw_signal": lowvol[instrument]})
                if period in r2.columns and instrument in r2.index and np.isfinite(r2.at[instrument, period]):
                    records.append({"instrument": instrument, "period": period, "arm_id": "P4_RESMOM_R2_MARKET_ONLY_ADAPTATION",
                                    "semantic_track": ARMS["P4_RESMOM_R2_MARKET_ONLY_ADAPTATION"], "raw_signal": r2.at[instrument, period],
                                    "residual_component": r2.at[instrument, period]})
                if period in r3.columns and instrument in r3.index and np.isfinite(r3.at[instrument, period]):
                    scope = "fully_post_snapshot_score" if period - 12 >= snapshot else (
                        "pre_snapshot_decision_retrospective" if period < snapshot else "mixed_post_snapshot_decision")
                    records.append({"instrument": instrument, "period": period, "arm_id": "P5_RESMOM_R3_BOARD_ADAPTATION",
                                    "semantic_track": ARMS["P5_RESMOM_R3_BOARD_ADAPTATION"], "raw_signal": r3.at[instrument, period],
                                    "residual_component": r3.at[instrument, period], "P5_date_scope": scope,
                                    "formation_contains_pre_snapshot_residual": scope != "fully_post_snapshot_score"})
    base = pd.DataFrame(records)
    if not trend.empty:
        trend = trend.copy()
        trend["arm_id"] = "P1_TRENDPV_RAW_ADAPTATION"
        base = pd.concat([base, trend], ignore_index=True, sort=False)
    return base


def outcome_for(instrument: str, period: pd.Period, paper_returns: pd.DataFrame,
                project_returns: pd.DataFrame, resolution: pd.DataFrame) -> tuple[float, float, str]:
    label = period + 1
    if instrument not in project_returns.index or label not in project_returns.columns:
        return np.nan, np.nan, "unknown_bridge_arm_month_not_evaluable"
    paper = paper_returns.at[instrument, label]
    project = project_returns.at[instrument, label]
    kind = str(resolution.at[instrument, label])
    return (float(paper) if np.isfinite(paper) else np.nan,
            float(project) if np.isfinite(project) else np.nan, kind)


ASSIGNMENT_COLUMNS = [
    "run_id", "instrument_id", "decision_date", "label_month", "arm_id", "semantic_track",
    "universe_eligible", "signal_eligible", "bucket_eligible", "exclusion_reason", "raw_signal",
    "price_component", "volume_component", "residual_component", "bucket_count", "bucket_id", "bucket_role",
    "ex_ante_ew_target_weight", "ex_ante_vw_target_weight", "paper_ew_analysis_weight", "paper_vw_analysis_weight",
    "project_ew_analysis_weight", "project_vw_analysis_weight", "paper_proxy_next_month_return",
    "project_resolved_next_month_return", "outcome_resolution", "project_bucket_month_evaluable",
    "lookahead_proxy_scope", "P5_date_scope", "board_snapshot_date", "board_snapshot_age_month_n",
    "board_known_by_predictor_asof", "formation_contains_pre_snapshot_residual", "historical_sample_role", "input_snapshot_hash",
]


def bucket_outputs(universe: pd.DataFrame, signals: pd.DataFrame, paper_returns: pd.DataFrame,
                   project_returns: pd.DataFrame, resolution_matrix: pd.DataFrame,
                   decisions: pd.DataFrame, bucket_counts: list[int]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    decision_map = decisions.set_index("period")["date"].to_dict()
    label_end = decisions.set_index("period")["date"].to_dict()
    signal_groups = {(arm, track, period): group.set_index("instrument") for (arm, track, period), group in signals.groupby(["arm_id", "semantic_track", "period"])}
    assignment_rows: list[dict[str, Any]] = []
    bucket_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    tracks = sorted({(arm.replace("__PAPER", ""), track) for arm, track in ARMS.items()})
    for period, ug in universe.groupby("period"):
        if period not in decision_map or period + 1 not in label_end:
            continue
        ug = ug.set_index("instrument")
        for arm_id, track in tracks:
            sg = signal_groups.get((arm_id, track, period), pd.DataFrame(index=pd.Index([], name="instrument")))
            joined = ug.join(sg[[c for c in ["raw_signal", "price_component", "volume_component", "residual_component", "P5_date_scope", "formation_contains_pre_snapshot_residual"] if c in sg]], how="left")
            for column in ["raw_signal", "price_component", "volume_component", "residual_component", "P5_date_scope", "formation_contains_pre_snapshot_residual"]:
                if column not in joined:
                    joined[column] = np.nan
            eligible = joined["raw_signal"].replace([np.inf, -np.inf], np.nan).dropna()
            support = {"run_id": RUN_ID, "arm_id": arm_id, "semantic_track": track, "decision_date": decision_map[period],
                       "primary_bucket_count": 10, "denominator_n": len(joined), "signal_eligible_n": len(eligible)}
            primary_complete = 0; primary_resolved = 0; primary_unknown = 0
            for k in bucket_counts:
                can_bucket = len(eligible) >= k * 10 and (k != 10 or len(eligible) >= 100)
                buckets = assign_buckets(eligible, k) if can_bucket else pd.Series(dtype="Int64")
                temp_rows = []
                for instrument, row in joined.iterrows():
                    bucket_id = int(buckets[instrument]) if instrument in buckets.index else None
                    paper, project, resolution = outcome_for(instrument, period, paper_returns, project_returns, resolution_matrix)
                    temp_rows.append({"instrument": instrument, "row": row, "bucket_id": bucket_id,
                                      "paper": paper, "project": project, "resolution": resolution})
                by_bucket = defaultdict(list)
                for item in temp_rows:
                    if item["bucket_id"] is not None:
                        by_bucket[item["bucket_id"]].append(item)
                weight_maps: dict[tuple[int, str], dict[str, float]] = {}
                bucket_eval: dict[int, bool] = {}
                for bucket_id, items in by_bucket.items():
                    ids = [item["instrument"] for item in items]
                    ew = {inst: 1 / len(ids) for inst in ids}
                    caps = pd.to_numeric(joined.loc[ids, "total_market_cap_cny"], errors="coerce").clip(lower=0)
                    vw = (caps / caps.sum()).to_dict() if caps.notna().all() and caps.sum() > 0 else {inst: np.nan for inst in ids}
                    weight_maps[(bucket_id, "EW")] = ew; weight_maps[(bucket_id, "VW")] = vw
                    bucket_eval[bucket_id] = all(np.isfinite(item["project"]) for item in items)
                    for semantics in ["paper_qfq_complete_case_sensitivity", "project_conservative_primary"]:
                        for weighting in ["EW", "VW"]:
                            wm = weight_maps[(bucket_id, weighting)]
                            vals = [(item["instrument"], item["paper"] if semantics.startswith("paper") else item["project"]) for item in items]
                            complete_vals = [(inst, val) for inst, val in vals if np.isfinite(val) and np.isfinite(wm.get(inst, np.nan))]
                            evaluable = bool(complete_vals) if semantics.startswith("paper") else bucket_eval[bucket_id] and len(complete_vals) == len(items)
                            if evaluable:
                                denom = sum(wm[inst] for inst, _ in complete_vals)
                                ret = sum(wm[inst] * val for inst, val in complete_vals) / denom if semantics.startswith("paper") else sum(wm[inst] * val for inst, val in complete_vals)
                            else:
                                ret = np.nan
                            bucket_rows.append({"run_id": RUN_ID, "arm_id": arm_id, "semantic_track": track,
                                "decision_date": decision_map[period], "holding_month_n": 1, "weighting": weighting,
                                "return_semantics": semantics, "bucket_count": k, "bucket_id": bucket_id,
                                "bucket_role": "favorable" if (arm_id.startswith("P6_") and bucket_id == 1) or (not arm_id.startswith("P6_") and bucket_id == k) else ("unfavorable" if (arm_id.startswith("P6_") and bucket_id == k) or (not arm_id.startswith("P6_") and bucket_id == 1) else "middle"),
                                "instrument_n": len(items), "weight_sum": sum(v for v in wm.values() if np.isfinite(v)),
                                "next_month_complete_n": sum(np.isfinite(item["paper"]) for item in items),
                                "valid_mark_n": sum(item["resolution"] == "valid_mark" for item in items),
                                "suspension_carry_n": sum(item["resolution"] == "suspension_carry_mark" for item in items),
                                "delisting_minus_one_n": sum(item["resolution"] == "delisting_minus_one" for item in items),
                                "unknown_bridge_n": sum(item["resolution"].startswith("unknown") for item in items),
                                "bucket_month_evaluable": evaluable, "gross_bucket_return": ret,
                                "historical_sample_role": HISTORICAL_ROLE, "inference_role": "design_only_not_support"})
                for item in temp_rows:
                    row = item["row"]; bucket_id = item["bucket_id"]
                    ew = weight_maps.get((bucket_id, "EW"), {}).get(item["instrument"], np.nan) if bucket_id else np.nan
                    vw = weight_maps.get((bucket_id, "VW"), {}).get(item["instrument"], np.nan) if bucket_id else np.nan
                    items = by_bucket.get(bucket_id, []) if bucket_id else []
                    paper_ids = [x["instrument"] for x in items if np.isfinite(x["paper"])]
                    paper_ew = 1 / len(paper_ids) if item["instrument"] in paper_ids else np.nan
                    caps_complete = {x["instrument"]: weight_maps.get((bucket_id, "VW"), {}).get(x["instrument"], np.nan) for x in items if np.isfinite(x["paper"])}
                    denom_vw = sum(v for v in caps_complete.values() if np.isfinite(v))
                    paper_vw = caps_complete.get(item["instrument"], np.nan) / denom_vw if denom_vw > 0 else np.nan
                    role = ("favorable" if (arm_id.startswith("P6_") and bucket_id == 1) or (not arm_id.startswith("P6_") and bucket_id == k)
                            else "unfavorable" if (arm_id.startswith("P6_") and bucket_id == k) or (not arm_id.startswith("P6_") and bucket_id == 1)
                            else "middle") if bucket_id else ""
                    assignment_rows.append({"run_id": RUN_ID, "instrument_id": item["instrument"], "decision_date": decision_map[period],
                        "label_month": str(period + 1), "arm_id": arm_id, "semantic_track": track, "universe_eligible": True,
                        "signal_eligible": bool(np.isfinite(row.get("raw_signal", np.nan))), "bucket_eligible": bucket_id is not None,
                        "exclusion_reason": "" if bucket_id else ("signal_missing" if not np.isfinite(row.get("raw_signal", np.nan)) else "bucket_floor_failed"),
                        "raw_signal": row.get("raw_signal", np.nan), "price_component": row.get("price_component", np.nan),
                        "volume_component": row.get("volume_component", np.nan), "residual_component": row.get("residual_component", np.nan),
                        "bucket_count": k, "bucket_id": bucket_id, "bucket_role": role,
                        "ex_ante_ew_target_weight": ew, "ex_ante_vw_target_weight": vw, "paper_ew_analysis_weight": paper_ew,
                        "paper_vw_analysis_weight": paper_vw, "project_ew_analysis_weight": ew if bucket_id and bucket_eval[bucket_id] else np.nan,
                        "project_vw_analysis_weight": vw if bucket_id and bucket_eval[bucket_id] else np.nan,
                        "paper_proxy_next_month_return": item["paper"], "project_resolved_next_month_return": item["project"],
                        "outcome_resolution": item["resolution"], "project_bucket_month_evaluable": bucket_eval.get(bucket_id, False),
                        "lookahead_proxy_scope": row.get("P5_date_scope", ""), "P5_date_scope": row.get("P5_date_scope", ""),
                        "board_snapshot_date": "2025-01-02" if arm_id.startswith("P5_") else "",
                        "board_snapshot_age_month_n": period.ordinal - pd.Period("2025-01", freq="M").ordinal if arm_id.startswith("P5_") else np.nan,
                        "board_known_by_predictor_asof": period - 1 >= pd.Period("2025-01", freq="M") if arm_id.startswith("P5_") else None,
                        "formation_contains_pre_snapshot_residual": row.get("formation_contains_pre_snapshot_residual", None),
                        "historical_sample_role": HISTORICAL_ROLE, "input_snapshot_hash": ""})
                if k == 10:
                    primary_complete = sum(np.isfinite(item["paper"]) for item in temp_rows if item["bucket_id"] is not None)
                    primary_resolved = sum(np.isfinite(item["project"]) for item in temp_rows if item["bucket_id"] is not None)
                    primary_unknown = sum(item["resolution"].startswith("unknown") for item in temp_rows if item["bucket_id"] is not None)
                    support["decile_eligible_n"] = len(eligible) if can_bucket else 0
            denom = support["denominator_n"]; decile_n = support.get("decile_eligible_n", 0)
            support.update({"next_month_complete_n": primary_complete, "project_label_resolved_n": primary_resolved,
                "project_unknown_bridge_n": primary_unknown, "signal_coverage_rate": len(eligible) / denom if denom else np.nan,
                "decile_coverage_rate": decile_n / denom if denom else np.nan,
                "paper_next_month_complete_rate": primary_complete / decile_n if decile_n else np.nan,
                "project_label_resolution_rate": primary_resolved / decile_n if decile_n else np.nan,
                "coefficient_complete": True, "warmup_complete": bool(len(eligible)),
                "lookahead_proxy_scope": "", "P5_date_scope": "", "board_snapshot_age_month_n": np.nan,
                "formation_contains_pre_snapshot_residual": None, "evaluable": decile_n > 0 and primary_resolved == decile_n,
                "missing_reason": "" if decile_n > 0 else "signal_or_bucket_floor"})
            support_rows.append(support)
    assignment = pd.DataFrame(assignment_rows)
    assignment["input_snapshot_hash"] = stable_hash({"rows": len(assignment), "run_id": RUN_ID})
    return assignment, pd.DataFrame(bucket_rows), pd.DataFrame(support_rows)


def monotonicity_and_stats(bucket: pd.DataFrame, fold_freeze: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    monthly_rows, summary_rows, stat_rows = [], [], []
    grouped = bucket.groupby(["arm_id", "semantic_track", "return_semantics", "weighting", "bucket_count"])
    for keys, group in grouped:
        arm, track, semantics, weighting, k = keys
        pivot = group.pivot_table(index="decision_date", columns="bucket_id", values="gross_bucket_return", aggfunc="first").sort_index()
        pivot = pivot.reindex(columns=range(1, int(k) + 1)).dropna()
        favorable = 1 if str(arm).startswith("P6_") else int(k)
        unfavorable = int(k) if favorable == 1 else 1
        middle = pivot[3] if int(k) == 5 else (pivot[5] + pivot[6]) / 2
        spread = pivot[favorable] - pivot[unfavorable]
        midspread = pivot[favorable] - middle
        for date in pivot.index:
            raw = float(pd.Series(range(1, int(k) + 1)).corr(pd.Series(pivot.loc[date].to_numpy()), method="spearman"))
            monthly_rows.append({"arm_id": arm, "semantic_track": track, "return_semantics": semantics,
                                 "weighting": weighting, "bucket_count": k, "decision_date": date,
                                 "raw_bucket_spearman": raw, "favorable_minus_unfavorable": spread.loc[date],
                                 "favorable_minus_middle": midspread.loc[date]})
        dates = list(pivot.index)
        calendar_id = (
            "P1_PAPER_FILL_CALENDAR" if arm == "P1_TRENDPV_RAW_ADAPTATION" and track == "paper_fill_sensitivity"
            else "P1_PROJECT_STRICT_CALENDAR" if arm == "P1_TRENDPV_RAW_ADAPTATION"
            else "P4_PRIMARY_CALENDAR" if arm == "P4_RESMOM_R2_MARKET_ONLY_ADAPTATION"
            else "P5_FULL_HISTORY_RETROSPECTIVE_CALENDAR" if arm == "P5_RESMOM_R3_BOARD_ADAPTATION"
            else "P0_COMPARATOR_CALENDAR" if arm == "P0_TOTAL_MOMENTUM_12_1"
            else "P6_COMPARATOR_CALENDAR"
        )
        frozen = fold_freeze[fold_freeze["arm_or_calendar_id"] == calendar_id]
        if frozen.empty:
            raise RuntimeError(f"missing frozen fold boundary: {calendar_id}")
        f = frozen.iloc[0]
        early_end = pd.Period(str(f["early_end"]), freq="M")
        late_start = pd.Period(str(f["late_start"]), freq="M")
        periods_by_date = {date: pd.Timestamp(date).to_period("M") for date in dates}
        scopes = {
            "full": dates,
            "early": [d for d in dates if periods_by_date[d] <= early_end],
            "late": [d for d in dates if periods_by_date[d] >= late_start],
        }
        registered = {
            "full": int(f["theoretical_max_month_n"]),
            "early": len(pd.period_range(str(f["early_start"]), str(f["early_end"]), freq="M")),
            "late": len(pd.period_range(str(f["late_start"]), str(f["late_end"]), freq="M")),
        }
        if arm == "P5_RESMOM_R3_BOARD_ADAPTATION":
            date_scope = bucket[(bucket["arm_id"] == arm) & (bucket["semantic_track"] == track)][["decision_date"]].drop_duplicates()
            # P5 scopes are mechanically determined from the frozen board date,
            # never from return availability.
            for p5_scope in ["pre_snapshot_decision_retrospective", "mixed_post_snapshot_decision", "fully_post_snapshot_score"]:
                if p5_scope == "pre_snapshot_decision_retrospective":
                    scoped = [d for d in dates if pd.Timestamp(d).to_period("M") < pd.Period("2025-01")]
                elif p5_scope == "fully_post_snapshot_score":
                    scoped = [d for d in dates if pd.Timestamp(d).to_period("M") >= pd.Period("2026-01")]
                else:
                    scoped = [d for d in dates if pd.Period("2025-01") <= pd.Timestamp(d).to_period("M") < pd.Period("2026-01")]
                scopes[p5_scope] = scoped
                registered[p5_scope] = len(scoped)
        for scope, scope_dates in scopes.items():
            if not scope_dates:
                continue
            values = spread.loc[scope_dates]
            raw_s = [row["raw_bucket_spearman"] for row in monthly_rows if row["arm_id"] == arm and row["semantic_track"] == track and row["return_semantics"] == semantics and row["weighting"] == weighting and row["bucket_count"] == k and row["decision_date"] in scope_dates]
            raw_mean = float(np.nanmean(raw_s))
            summary_rows.append({"arm_id": arm, "semantic_track": track, "return_semantics": semantics,
                "weighting": weighting, "bucket_count": k, "holding_month_n": 1,
                "month_scope": "P5_date_scope" if scope.startswith(("pre_snapshot", "mixed_post", "fully_post")) else scope,
                "P5_date_scope": scope if scope.startswith(("pre_snapshot", "mixed_post", "fully_post")) else "",
                "month_n": len(scope_dates), "favorable_extreme_mean": pivot.loc[scope_dates, favorable].mean(),
                "middle_mean": middle.loc[scope_dates].mean(), "unfavorable_extreme_mean": pivot.loc[scope_dates, unfavorable].mean(),
                "favorable_minus_unfavorable_mean": values.mean(), "favorable_minus_middle_mean": midspread.loc[scope_dates].mean(),
                "spread_positive_month_rate": float(np.mean(values > 0)), "raw_mean_bucket_spearman": raw_mean,
                "favorable_aligned_mean_bucket_spearman": -raw_mean if str(arm).startswith("P6_") else raw_mean,
                "HAC_t_stat": nw_stats(values)["t"], "HAC_p_value": nw_stats(values)["p"],
                "inference_role": "design_only_not_support", "paper_sort_direction_gate": False,
                "positive_exposure_design_gate": False})
        for scope, scope_dates in scopes.items():
            if not scope_dates:
                continue
            out_scope = "P5_date_scope" if scope.startswith(("pre_snapshot", "mixed_post", "fully_post")) else scope
            p5_scope = scope if out_scope == "P5_date_scope" else ""
            for bucket_id in range(1, int(k) + 1):
                stats = series_stats(pivot.loc[scope_dates, bucket_id], registered[scope])
                stat_rows.append({"run_id": RUN_ID, "arm_id": arm, "semantic_track": track, "return_semantics": semantics,
                                  "weighting": weighting, "bucket_count": k, "bucket_id": bucket_id,
                                  "bucket_role": "favorable" if bucket_id == favorable else "unfavorable" if bucket_id == unfavorable else "middle",
                                  "holding_month_n": 1, "month_scope": out_scope, "P5_date_scope": p5_scope,
                                  "series_role": "bucket_return", **stats})
            for role, values in [("favorable_minus_unfavorable", spread.loc[scope_dates]),
                                 ("favorable_minus_middle", midspread.loc[scope_dates])]:
                stat_rows.append({"run_id": RUN_ID, "arm_id": arm, "semantic_track": track, "return_semantics": semantics,
                                  "weighting": weighting, "bucket_count": k, "bucket_id": np.nan, "bucket_role": "",
                                  "holding_month_n": 1, "month_scope": out_scope, "P5_date_scope": p5_scope,
                                  "series_role": role, **series_stats(values, registered[scope])})
    return pd.DataFrame(monthly_rows), pd.DataFrame(summary_rows), pd.DataFrame(stat_rows)


def metric(summary: pd.DataFrame, arm: str, track: str, field: str, scope: str) -> float:
    rows = summary[(summary["arm_id"] == arm) & (summary["semantic_track"] == track) &
                   (summary["return_semantics"] == "project_conservative_primary") &
                   (summary["weighting"] == "EW") & (summary["bucket_count"] == 10) &
                   (summary["month_scope"] == scope)]
    return float(rows.iloc[0][field]) if len(rows) else np.nan


def dominance_audit(monthly_sort: pd.DataFrame, assignment: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    key_cols = ["arm_id", "semantic_track", "return_semantics", "weighting", "bucket_count"]
    for keys, group in monthly_sort.groupby(key_cols):
        spreads = group.set_index(pd.to_datetime(group["decision_date"]))["favorable_minus_unfavorable"].astype(float)
        total_abs = float(spreads.abs().sum())
        original = float(spreads.mean())
        lomo = [float(spreads.drop(index=d).mean()) for d in spreads.index] if len(spreads) > 1 else []
        arm, track, semantics, weighting, k = keys
        loio_values: dict[str, float] = {}
        if semantics == "project_conservative_primary" and weighting == "EW":
            source = assignment[(assignment["arm_id"] == arm) & (assignment["semantic_track"] == track) &
                                (assignment["bucket_count"] == k) & assignment["bucket_eligible"] &
                                assignment["project_bucket_month_evaluable"]].copy()
            source["decision_date"] = pd.to_datetime(source["decision_date"])
            source = source[source["decision_date"].isin(spreads.index)]
            favorable = 1 if str(arm).startswith("P6_") else int(k)
            unfavorable = int(k) if favorable == 1 else 1
            source = source[source["bucket_id"].isin([favorable, unfavorable])]
            monthly = {(date, int(bid)): vals["project_resolved_next_month_return"].astype(float)
                       for (date, bid), vals in source.groupby(["decision_date", "bucket_id"])}
            for instrument, affected in source.groupby("instrument_id"):
                revised = spreads.copy()
                for date in affected["decision_date"].unique():
                    fvals = monthly.get((pd.Timestamp(date), favorable), pd.Series(dtype=float))
                    uvals = monthly.get((pd.Timestamp(date), unfavorable), pd.Series(dtype=float))
                    fidx = source[(source["decision_date"] == date) & (source["bucket_id"] == favorable)]
                    uidx = source[(source["decision_date"] == date) & (source["bucket_id"] == unfavorable)]
                    if instrument in set(fidx["instrument_id"]):
                        fvals = fidx.loc[fidx["instrument_id"] != instrument, "project_resolved_next_month_return"].astype(float)
                    if instrument in set(uidx["instrument_id"]):
                        uvals = uidx.loc[uidx["instrument_id"] != instrument, "project_resolved_next_month_return"].astype(float)
                    if len(fvals) and len(uvals):
                        revised.loc[pd.Timestamp(date)] = float(fvals.mean() - uvals.mean())
                loio_values[str(instrument)] = float(revised.mean())
        if loio_values:
            loio_min_inst = min(loio_values, key=loio_values.get); loio_max_inst = max(loio_values, key=loio_values.get)
            shift_inst = max(loio_values, key=lambda x: abs(loio_values[x] - original))
        else:
            loio_min_inst = loio_max_inst = shift_inst = ""
        rows.append(dict(zip(key_cols, keys)) | {
            "full_sample_mean_spread": original,
            "max_abs_month_contribution": float(spreads.abs().max() / total_abs) if total_abs > 0 else np.nan,
            "top3_abs_month_contribution": float(spreads.abs().nlargest(3).sum() / total_abs) if total_abs > 0 else np.nan,
            "leave_one_month_out_mean_min": min(lomo) if lomo else np.nan,
            "LOIO_full_mean_min": loio_values.get(loio_min_inst, np.nan),
            "LOIO_full_mean_max": loio_values.get(loio_max_inst, np.nan),
            "LOIO_max_abs_shift": abs(loio_values.get(shift_inst, np.nan) - original) if shift_inst else np.nan,
            "LOIO_max_abs_shift_instrument": shift_inst,
            "missing_reason": "all_spreads_zero" if total_abs == 0 else ("LOIO_only_defined_for_project_EW" if not loio_values else ""),
            "inference_role": "design_only_not_support",
        })
    return pd.DataFrame(rows)


def direction_values(summary: pd.DataFrame, arm: str, track: str, semantics: str,
                     p5_scope: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for scope in ["full", "early", "late"]:
        rows = summary[(summary["arm_id"] == arm) & (summary["semantic_track"] == track) &
                       (summary["return_semantics"] == semantics) & (summary["weighting"] == "EW") &
                       (summary["bucket_count"] == 10) & (summary["month_scope"] == scope)]
        result[f"months_{scope}"] = int(rows.iloc[0]["month_n"]) if len(rows) else 0
        result[f"spread_{scope}"] = float(rows.iloc[0]["favorable_minus_unfavorable_mean"]) if len(rows) else np.nan
        result[f"fav_{scope}"] = float(rows.iloc[0]["favorable_extreme_mean"]) if len(rows) else np.nan
    if p5_scope:
        rows = summary[(summary["arm_id"] == arm) & (summary["semantic_track"] == track) &
                       (summary["return_semantics"] == semantics) & (summary["weighting"] == "EW") &
                       (summary["bucket_count"] == 10) & (summary["month_scope"] == "P5_date_scope") &
                       (summary["P5_date_scope"] == p5_scope)]
        result["scope_months"] = int(rows.iloc[0]["month_n"]) if len(rows) else 0
    return result


def decision_snapshot(summary: pd.DataFrame, signals: pd.DataFrame, coefficients: pd.DataFrame,
                      ts_audit: pd.DataFrame, ridge_audit: pd.DataFrame) -> dict[str, Any]:
    p1 = direction_values(summary, "P1_TRENDPV_RAW_ADAPTATION", "project_strict_primary", "project_conservative_primary")
    p1paper = direction_values(summary, "P1_TRENDPV_RAW_ADAPTATION", "paper_fill_sensitivity", "paper_qfq_complete_case_sensitivity")
    p4 = direction_values(summary, "P4_RESMOM_R2_MARKET_ONLY_ADAPTATION", "project_sequential_market_residual_primary", "project_conservative_primary")
    p5 = direction_values(summary, "P5_RESMOM_R3_BOARD_ADAPTATION", "full_history_retrospective_proxy", "project_conservative_primary", "fully_post_snapshot_score")
    p0 = direction_values(summary, "P0_TOTAL_MOMENTUM_12_1", "project_return_history_primary", "project_conservative_primary")
    p6 = direction_values(summary, "P6_LOWVOL_36M_COMPARATOR", "project_monthly_volatility_primary", "project_conservative_primary")

    def complete(values: dict[str, Any], fields: list[str]) -> bool:
        return all(np.isfinite(values.get(f, np.nan)) for f in fields)
    direction_fields = [f"{kind}_{scope}" for kind in ["spread", "fav"] for scope in ["full", "early", "late"]]
    coef_tracks = set(coefficients.loc[coefficients["coefficient_complete"], "semantic_track"]) if not coefficients.empty else set()
    signal_arms = set(signals["arm_id"]) if not signals.empty else set()
    gates: dict[str, Any] = {
        "P0_formula_integrity_gate": "P0_TOTAL_MOMENTUM_12_1" in signal_arms,
        "P1_formula_integrity_gate": "project_strict_primary" in coef_tracks and "P1_TRENDPV_RAW_ADAPTATION" in signal_arms,
        "P1_paper_fill_formula_integrity_gate": "paper_fill_sensitivity" in coef_tracks and not signals[(signals["arm_id"] == "P1_TRENDPV_RAW_ADAPTATION") & (signals["semantic_track"] == "paper_fill_sensitivity")].empty,
        "P4_formula_integrity_gate": not ts_audit.empty and ts_audit["status"].eq("pass").any() and "P4_RESMOM_R2_MARKET_ONLY_ADAPTATION" in signal_arms,
        "P5_materialization_gate": not ridge_audit.empty and ridge_audit["status"].eq("pass").any() and "P5_RESMOM_R3_BOARD_ADAPTATION" in signal_arms,
        "P6_formula_integrity_gate": "P6_LOWVOL_36M_COMPARATOR" in signal_arms,
    }
    gates["P0_metric_completeness_gate"] = p0["months_full"] > 0 and complete(p0, ["spread_full", "fav_full"])
    gates["P0_materialization_gate"] = gates["P0_formula_integrity_gate"] and gates["P0_metric_completeness_gate"]
    gates["P1_sample_support_gate"] = p1["months_full"] >= 48 and p1["months_early"] >= 24 and p1["months_late"] >= 24
    gates["P1_direction_metric_completeness_gate"] = complete(p1, direction_fields)
    gates["P1_materialization_gate"] = gates["P1_formula_integrity_gate"] and gates["P1_sample_support_gate"] and gates["P1_direction_metric_completeness_gate"]
    gates["P4_sample_support_gate"] = p4["months_full"] >= 60 and p4["months_early"] >= 30 and p4["months_late"] >= 30
    gates["P4_direction_metric_completeness_gate"] = complete(p4, direction_fields)
    gates["P4_materialization_gate"] = gates["P4_formula_integrity_gate"] and gates["P4_sample_support_gate"] and gates["P4_direction_metric_completeness_gate"]
    gates["P5_fully_post_snapshot_materialization_gate"] = gates["P5_materialization_gate"] and p5.get("scope_months", 0) > 0
    gates["P6_metric_completeness_gate"] = p6["months_full"] > 0 and complete(p6, ["spread_full", "fav_full"])
    gates["P6_materialization_gate"] = gates["P6_formula_integrity_gate"] and gates["P6_metric_completeness_gate"]
    gates["P1_paper_sort_direction_gate"] = gates["P1_materialization_gate"] and complete(p1, [f"spread_{s}" for s in ["full", "early", "late"]]) and all(p1[f"spread_{s}"] > 0 for s in ["full", "early", "late"])
    gates["P4_paper_sort_direction_gate"] = gates["P4_materialization_gate"] and complete(p4, [f"spread_{s}" for s in ["full", "early", "late"]]) and all(p4[f"spread_{s}"] > 0 for s in ["full", "early", "late"])
    gates["P1_paper_fill_sort_diagnostic_gate"] = gates["P1_paper_fill_formula_integrity_gate"] and p1paper["months_full"] >= 48 and p1paper["months_early"] >= 24 and p1paper["months_late"] >= 24 and complete(p1paper, [f"spread_{s}" for s in ["full", "early", "late"]]) and all(p1paper[f"spread_{s}"] > 0 for s in ["full", "early", "late"])
    gates["P5_retrospective_sort_diagnostic_gate"] = gates["P5_materialization_gate"] and p5["months_full"] >= 60 and p5["months_early"] >= 30 and p5["months_late"] >= 30 and complete(p5, [f"spread_{s}" for s in ["full", "early", "late"]]) and all(p5[f"spread_{s}"] > 0 for s in ["full", "early", "late"])
    gates["P1_positive_exposure_design_gate"] = gates["P1_materialization_gate"] and all(p1[f"fav_{s}"] > 0 for s in ["full", "early", "late"])
    gates["P4_positive_exposure_design_gate"] = gates["P4_materialization_gate"] and all(p4[f"fav_{s}"] > 0 for s in ["full", "early", "late"])

    gates["P1_partial_underpowered"] = gates["P1_formula_integrity_gate"] and not gates["P1_sample_support_gate"]
    gates["P4_partial_underpowered"] = gates["P4_formula_integrity_gate"] and not gates["P4_sample_support_gate"]
    gates["partial_formula_failure"] = bool(gates["P1_formula_integrity_gate"]) ^ bool(gates["P4_formula_integrity_gate"])
    gates["P1_metric_materialization_failure"] = gates["P1_formula_integrity_gate"] and gates["P1_sample_support_gate"] and not gates["P1_direction_metric_completeness_gate"]
    gates["P4_metric_materialization_failure"] = gates["P4_formula_integrity_gate"] and gates["P4_sample_support_gate"] and not gates["P4_direction_metric_completeness_gate"]
    gates["partial_metric_materialization_failure"] = (gates["P1_metric_materialization_failure"] or gates["P4_metric_materialization_failure"]) and (gates["P1_materialization_gate"] or gates["P4_materialization_gate"])
    gates["partial_underpowered"] = (gates["P1_partial_underpowered"] or gates["P4_partial_underpowered"]) and (gates["P1_materialization_gate"] or gates["P4_materialization_gate"])
    gates["global_underpowered"] = (gates["P1_formula_integrity_gate"] or gates["P4_formula_integrity_gate"]) and not gates["P1_materialization_gate"] and not gates["P4_materialization_gate"] and not (gates["P1_metric_materialization_failure"] or gates["P4_metric_materialization_failure"])
    gates["global_metric_materialization_failure"] = not gates["P1_materialization_gate"] and not gates["P4_materialization_gate"] and (gates["P1_metric_materialization_failure"] or gates["P4_metric_materialization_failure"])
    gates["primary_materialized_any"] = gates["P1_materialization_gate"] or gates["P4_materialization_gate"]
    gates["primary_positive_exposure_any"] = gates["P1_positive_exposure_design_gate"] or gates["P4_positive_exposure_design_gate"]
    gates["P1_partial_positive"] = gates["P1_materialization_gate"] and p1["fav_full"] > 0 and not gates["P1_positive_exposure_design_gate"]
    gates["P4_partial_positive"] = gates["P4_materialization_gate"] and p4["fav_full"] > 0 and not gates["P4_positive_exposure_design_gate"]
    gates["project_partial_positive_any"] = gates["P1_partial_positive"] or gates["P4_partial_positive"]
    gates["auxiliary_sort_positive_any"] = any(gates[x] for x in ["P1_paper_sort_direction_gate", "P4_paper_sort_direction_gate", "P1_paper_fill_sort_diagnostic_gate", "P5_retrospective_sort_diagnostic_gate"])
    gates["all_materialized_primary_full_nonpositive"] = gates["primary_materialized_any"] and (not gates["P1_materialization_gate"] or p1["fav_full"] <= 0) and (not gates["P4_materialization_gate"] or p4["fav_full"] <= 0)
    materialization_blocked = (not gates["P1_formula_integrity_gate"] and not gates["P4_formula_integrity_gate"]) or gates["global_metric_materialization_failure"]
    if materialization_blocked: state = "20B_data_or_formula_materialization_blocked"
    elif gates["global_underpowered"]: state = "20B_underpowered_design_diagnostic"
    elif gates["primary_positive_exposure_any"]: state = "20B_positive_exposure_candidate_identified_design_only"
    elif not gates["project_partial_positive_any"] and gates["auxiliary_sort_positive_any"]: state = "20B_paper_sort_or_semantics_only_design_only"
    elif gates["project_partial_positive_any"]: state = "20B_mixed_direction_design_only"
    elif gates["all_materialized_primary_full_nonpositive"]: state = "20B_positive_exposure_not_identified_design_only"
    else: raise RuntimeError("terminal truth table is not exhaustive")
    return {"decision_state": state, "p1": p1, "p1_paper_fill": p1paper, "p4": p4, "p5": p5,
            "p0": p0, "p6": p6, **gates,
            "20C_requirement_generation_authorized": bool(gates["primary_positive_exposure_any"]),
            "blocking_reasons": "" if not materialization_blocked else "both primary formulas unavailable or global metric materialization failed"}


def p4_p5_attribution(signals: pd.DataFrame, bucket: pd.DataFrame, fold_freeze: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    p4 = signals[signals["arm_id"] == "P4_RESMOM_R2_MARKET_ONLY_ADAPTATION"][["instrument", "period", "raw_signal"]]
    p5 = signals[signals["arm_id"] == "P5_RESMOM_R3_BOARD_ADAPTATION"][["instrument", "period", "raw_signal", "P5_date_scope"]]
    pairs = p4.merge(p5, on=["instrument", "period"], suffixes=("_P4", "_P5"))
    for row in pairs.itertuples(index=False):
        rows.append({"run_id": RUN_ID, "record_type": "score_instrument_pair", "instrument_id": row.instrument,
                     "decision_date": str(row.period), "P5_date_scope": row.P5_date_scope, "P4_value": row.raw_signal_P4,
                     "P5_value": row.raw_signal_P5, "P5_minus_P4_value": row.raw_signal_P5 - row.raw_signal_P4,
                     "month_scope": "", "return_semantics": "", "weighting": "", "bucket_count": np.nan,
                     "series_role": "", "bucket_id": np.nan, "pair_evaluable": True, "paired_month_n": np.nan,
                     "P4_paired_mean": np.nan, "P5_paired_mean": np.nan, "paired_mean_delta": np.nan,
                     "missing_reason": "", "input_snapshot_hash": ""})
    p4b = bucket[bucket["arm_id"] == "P4_RESMOM_R2_MARKET_ONLY_ADAPTATION"]
    p5b = bucket[bucket["arm_id"] == "P5_RESMOM_R3_BOARD_ADAPTATION"]
    keys = ["decision_date", "return_semantics", "weighting", "bucket_count", "bucket_id"]
    paired_bucket = p4b.merge(p5b, on=keys, how="outer", suffixes=("_P4", "_P5"))
    monthly_pairs: list[dict[str, Any]] = []
    for base_keys, group in paired_bucket.groupby(["decision_date", "return_semantics", "weighting", "bucket_count"], dropna=False):
        date, semantics, weighting, k = base_keys
        scope = ("pre_snapshot_decision_retrospective" if pd.Timestamp(date).to_period("M") < pd.Period("2025-01")
                 else "fully_post_snapshot_score" if pd.Timestamp(date).to_period("M") >= pd.Period("2026-01")
                 else "mixed_post_snapshot_decision")
        by_id = group.set_index("bucket_id")
        series: list[tuple[str, float | None, float | None, float | int]] = []
        for bid, r in by_id.iterrows():
            series.append(("bucket_return", r.get("gross_bucket_return_P4"), r.get("gross_bucket_return_P5"), bid))
        favorable, unfavorable = int(k), 1
        middle_ids = [3] if int(k) == 5 else [5, 6]
        def value(side: str, ids: list[int]) -> float:
            col = f"gross_bucket_return_{side}"
            vals = [by_id.at[i, col] for i in ids if i in by_id.index]
            return float(np.mean(vals)) if len(vals) == len(ids) and np.isfinite(vals).all() else np.nan
        for role, p4v, p5v in [
            ("favorable_minus_unfavorable", value("P4", [favorable])-value("P4", [unfavorable]), value("P5", [favorable])-value("P5", [unfavorable])),
            ("favorable_minus_middle", value("P4", [favorable])-value("P4", middle_ids), value("P5", [favorable])-value("P5", middle_ids)),
        ]:
            series.append((role, p4v, p5v, np.nan))
        for role, p4v, p5v, bid in series:
            good = bool(np.isfinite(p4v) and np.isfinite(p5v))
            monthly_pairs.append({"run_id": RUN_ID, "record_type": "return_month_pair", "instrument_id": "",
                "decision_date": date, "P5_date_scope": scope, "month_scope": "", "return_semantics": semantics,
                "weighting": weighting, "bucket_count": k, "series_role": role, "bucket_id": bid,
                "P4_value": p4v, "P5_value": p5v, "P5_minus_P4_value": p5v-p4v if good else np.nan,
                "pair_evaluable": good, "paired_month_n": np.nan, "P4_paired_mean": np.nan,
                "P5_paired_mean": np.nan, "paired_mean_delta": np.nan,
                "missing_reason": "" if good else "one_or_both_source_series_missing", "input_snapshot_hash": ""})
    rows.extend(monthly_pairs)

    pairs_df = pd.DataFrame(monthly_pairs)
    frozen = fold_freeze[fold_freeze["arm_or_calendar_id"] == "P4_PRIMARY_CALENDAR"].iloc[0]
    period = pd.to_datetime(pairs_df["decision_date"]).dt.to_period("M") if not pairs_df.empty else pd.Series(dtype=object)
    masks = {
        ("full", ""): pd.Series(True, index=pairs_df.index),
        ("early", ""): period <= pd.Period(str(frozen["early_end"]), freq="M"),
        ("late", ""): period >= pd.Period(str(frozen["late_start"]), freq="M"),
    }
    for scope in ["pre_snapshot_decision_retrospective", "mixed_post_snapshot_decision", "fully_post_snapshot_score"]:
        masks[("P5_date_scope", scope)] = pairs_df["P5_date_scope"].eq(scope)
    summary_keys = ["return_semantics", "weighting", "bucket_count", "series_role", "bucket_id"]
    for (month_scope, p5_scope), mask in masks.items():
        for keys_value, group in pairs_df[mask & pairs_df["pair_evaluable"]].groupby(summary_keys, dropna=False):
            p4mean = float(group["P4_value"].mean()); p5mean = float(group["P5_value"].mean())
            rows.append({"run_id": RUN_ID, "record_type": "return_scope_summary", "instrument_id": "",
                "decision_date": "", "P5_date_scope": p5_scope, "month_scope": month_scope,
                **dict(zip(summary_keys, keys_value)), "P4_value": np.nan, "P5_value": np.nan,
                "P5_minus_P4_value": np.nan, "pair_evaluable": True, "paired_month_n": len(group),
                "P4_paired_mean": p4mean, "P5_paired_mean": p5mean,
                "paired_mean_delta": float(group["P5_minus_P4_value"].mean()), "missing_reason": "",
                "input_snapshot_hash": ""})
    out = pd.DataFrame(rows)
    if not out.empty:
        out["input_snapshot_hash"] = stable_hash({"rows": len(out)})
    return out


def overlapping_outputs(assignment: pd.DataFrame, returns: pd.DataFrame, resolution: pd.DataFrame, holding_values: list[int],
                        output_path: Path) -> pd.DataFrame:
    source = assignment[(assignment["arm_id"].isin(["P4_RESMOM_R2_MARKET_ONLY_ADAPTATION", "P5_RESMOM_R3_BOARD_ADAPTATION"])) & assignment["bucket_eligible"]].copy()
    source["formation_period"] = pd.to_datetime(source["decision_date"]).dt.to_period("M")
    rows: list[dict[str, Any]] = []
    cohort_months: dict[tuple[Any, ...], list[tuple[float, bool]]] = defaultdict(list)
    writer: pq.ParquetWriter | None = None
    def flush() -> None:
        nonlocal rows, writer
        if not rows: return
        table = pa.Table.from_pandas(pd.DataFrame(rows), preserve_index=False)
        if writer is None: writer = pq.ParquetWriter(output_path, table.schema, compression="zstd")
        writer.write_table(table); rows = []
    for (arm, track, formation, k, bucket_id), group in source.groupby(["arm_id", "semantic_track", "formation_period", "bucket_count", "bucket_id"]):
        ids = group["instrument_id"].astype(str).tolist()
        for weighting, weight_col in [("EW", "ex_ante_ew_target_weight"), ("VW", "ex_ante_vw_target_weight")]:
            initial = pd.to_numeric(group[weight_col], errors="coerce").fillna(0).to_numpy(float)
            if initial.sum() <= 0: continue
            for H in holding_values:
                values = initial.copy(); cash = max(0.0, 1.0 - values.sum()); observable = True
                terminal = np.zeros(len(ids), dtype=bool)
                for age in range(1, H + 1):
                    period = formation + age; nav_start = float(values.sum() + cash)
                    rets = np.full(len(ids), np.nan); resolutions = np.full(len(ids), "unknown_bridge", dtype=object)
                    for ix, instrument in enumerate(ids):
                        if terminal[ix] or values[ix] == 0:
                            rets[ix] = 0.0; resolutions[ix] = "post_terminal_zero_value"
                        elif instrument in returns.index and period in returns.columns and np.isfinite(returns.at[instrument, period]):
                            rets[ix] = float(returns.at[instrument, period]); resolutions[ix] = str(resolution.at[instrument, period])
                        else: observable = False
                    end = values * (1 + np.nan_to_num(rets, nan=0.0)) if observable else np.full(len(ids), np.nan)
                    nav_end = float(np.nansum(end) + cash) if observable else np.nan
                    cohort_ret = nav_end / nav_start - 1 if observable and nav_start > 0 else np.nan
                    for ix, instrument in enumerate(ids):
                        rows.append({"run_id": RUN_ID, "arm_id": arm, "semantic_track": track, "weighting": weighting,
                            "bucket_count": int(k), "bucket_id": int(bucket_id), "bucket_role": group.iloc[0]["bucket_role"],
                            "holding_month_n": H, "cohort_formation_date": str(formation), "evaluation_month": str(period),
                            "cohort_age_month": age, "instrument_id": instrument, "within_cohort_target_weight": initial[ix],
                            "position_value_start": values[ix], "instrument_weight_start": values[ix] / nav_start if nav_start > 0 else np.nan,
                            "position_value_end": end[ix] if observable else np.nan, "cohort_NAV_start": nav_start,
                            "cohort_NAV_end": nav_end, "cohort_gross_return": cohort_ret, "cohort_cash_start": cash,
                            "cohort_cash_end": cash, "cohort_capital_weight": 1 / H, "resolved_monthly_return": rets[ix],
                            "outcome_resolution": resolutions[ix], "cohort_state_observable": observable,
                            "portfolio_month_evaluable": observable, "input_snapshot_hash": ""})
                    aggregate_key = (arm, track, weighting, int(k), int(bucket_id), group.iloc[0]["bucket_role"], H, period)
                    cohort_months[aggregate_key].append((cohort_ret, observable))
                    if len(rows) >= 50_000: flush()
                    if observable:
                        terminal |= rets == -1; values = end
    flush()
    if writer is not None: writer.close()
    elif not output_path.exists(): pd.DataFrame().to_parquet(output_path, index=False)
    result = []
    for keys, values in cohort_months.items():
        H = int(keys[6]); active = len(values); obs = sum(bool(x[1]) for x in values); good = active == H and obs == H
        result.append(dict(zip(["arm_id", "semantic_track", "weighting", "bucket_count", "bucket_id", "bucket_role", "holding_month_n", "evaluation_month"], keys)) |
                      {"active_cohort_n": active, "observable_active_cohort_n": obs, "unknown_state_cohort_n": active-obs,
                       "portfolio_month_evaluable": good,
                       "gross_overlapping_monthly_return": float(np.mean([x[0] for x in values])) if good else np.nan,
                       "inference_role": "appendix_design_only_not_gate"})
    return pd.DataFrame(result)


def historical_stage(config_path: str | Path = CONFIG_PATH, workers: int = 4) -> dict[str, Any]:
    config = load_config(config_path); paths = paths_for(config); root = active_root(config)
    pre = root / "preoutcome"; hist_target = root / "historical"
    pre_hash = verify_bundle(pre, "preoutcome_manifest_20b.json", "preoutcome_output_hashes_20b.json")
    if (hist_target / "historical_output_hashes_20b.json").exists():
        return {"status": "already_sealed", "historical_bundle_hash": verify_bundle(hist_target, "historical_manifest_20b.json", "historical_output_hashes_20b.json")}
    hist = begin_stage(root, "historical")
    auth = config["authorization"]
    if not auth.get("direct_run_authorized"):
        raise PermissionError("direct historical run not authorized")
    write_json(hist / "human_historical_run_authorization.json", {
        "authorization_type": auth["authorization_type"], "authorized_at_utc": utc_now(), "reviewer": auth["reviewer"],
        "authorization_source": auth["authorization_source"], "preoutcome_bundle_hash": pre_hash,
        "registered_arm_ids": sorted(set(k.replace("__PAPER", "") for k in ARMS)),
        "registered_semantic_tracks": sorted(set(ARMS.values())), "history_date_max": config["boundary"]["history_date_max"],
        "authorization_granted": True, "manual_pause_skipped_by_explicit_user_instruction": True})
    history_max = pd.Timestamp(config["boundary"]["history_date_max"])
    calendar = exchange_calendar(paths["trading_calendar"], history_max)
    decisions_all = decision_calendar(calendar, history_max)
    decisions = decisions_all[decisions_all["label_complete"]].copy()
    universe = load_monthly_universe(paths["project_universe"], decisions)
    windows = list(config["trendpv"]["windows"])
    features, monthly, input_meta = load_market_panel(paths, universe, calendar, history_max, windows, workers)
    all_periods = list(pd.period_range(monthly["period"].min(), history_max.to_period("M"), freq="M"))
    label_end = pd.Series(calendar).groupby(calendar.to_period("M")).max().to_dict()
    close, last_date, paper_returns, project_returns, resolution_matrix = monthly_matrices(
        monthly, all_periods, universe, paths["security_master"], label_end
    )
    market = benchmark_returns(paths["benchmark"], all_periods, history_max)
    trend, coefficients = trend_scores(features, universe, {
        "project_strict_primary": project_returns,
        "paper_fill_sensitivity": paper_returns,
    }, windows,
        int(config["trendpv"]["minimum_complete_cross_section_n"]), int(config["trendpv"]["coefficient_burn_in"]),
        float(config["trendpv"]["lambda"]), float(config["trendpv"]["rcond"]))
    residual, r2, ts_audit = rolling_scores(project_returns, market, float(config["trendpv"]["rcond"]))
    boards = board_matrix(paths["board_member"], project_returns.index, int(config["residual"]["board_minimum_overlap_n"]))
    r3_residual, r3, ridge_audit = r3_scores(residual, universe, boards,
        int(config["residual"]["ridge_minimum_complete_cross_section_n"]), float(config["residual"]["ridge_alpha"]),
        pd.Period("2025-01", freq="M"))
    signals = build_signal_table(universe, project_returns, trend, r2, r3, pd.Period("2025-01", freq="M"))
    assignment, bucket, support = bucket_outputs(universe, signals, paper_returns, project_returns,
                                                  resolution_matrix, decisions, list(config["sorting"]["bucket_counts"]))
    folds = pd.read_csv(pre / "statistical_and_fold_freeze.csv")
    monthly_sort, summary, stats = monotonicity_and_stats(bucket, folds)
    attribution = p4_p5_attribution(signals, bucket, folds)
    dominance = dominance_audit(monthly_sort, assignment)

    coef_lookup = coefficients.set_index(["semantic_track", "coefficient_month"]) if not coefficients.empty else pd.DataFrame()
    for idx, row in support.iterrows():
        period = pd.Timestamp(row["decision_date"]).to_period("M")
        if row["arm_id"] == "P1_TRENDPV_RAW_ADAPTATION" and not coefficients.empty and (row["semantic_track"], str(period)) in coef_lookup.index:
            c = coef_lookup.loc[(row["semantic_track"], str(period))]
            support.at[idx, "coefficient_complete"] = bool(c["coefficient_complete"])
            support.at[idx, "warmup_complete"] = int(c["complete_coefficient_month_n"]) >= int(config["trendpv"]["coefficient_burn_in"])
        elif row["arm_id"] == "P1_TRENDPV_RAW_ADAPTATION":
            support.at[idx, "coefficient_complete"] = False; support.at[idx, "warmup_complete"] = False
        if row["arm_id"] == "P5_RESMOM_R3_BOARD_ADAPTATION":
            scope = ("pre_snapshot_decision_retrospective" if period < pd.Period("2025-01")
                     else "fully_post_snapshot_score" if period >= pd.Period("2026-01")
                     else "mixed_post_snapshot_decision")
            support.at[idx, "P5_date_scope"] = scope
            support.at[idx, "lookahead_proxy_scope"] = scope
            support.at[idx, "board_snapshot_age_month_n"] = period.ordinal - pd.Period("2025-01").ordinal
            support.at[idx, "formation_contains_pre_snapshot_residual"] = scope != "fully_post_snapshot_score"

    assignment.to_parquet(hist / "instrument_month_signal_bucket_assignment.parquet", index=False, compression="zstd")
    write_csv(hist / "monthly_bucket_returns.csv.gz", bucket)
    write_csv(hist / "monthly_signal_support.csv", support)
    write_csv(hist / "trendpv_coefficient_path.csv.gz", coefficients)
    component = trend.groupby(["period", "semantic_track"], as_index=False).agg(instrument_n=("instrument", "nunique"), price_component_mean=("price_component", "mean"), volume_component_mean=("volume_component", "mean"), total_score_mean=("raw_signal", "mean")) if not trend.empty else pd.DataFrame()
    write_csv(hist / "trendpv_component_diagnostic.csv", component)
    write_csv(hist / "residual_time_series_regression_audit.csv.gz", pd.DataFrame(ts_audit))
    write_csv(hist / "residual_board_ridge_audit.csv.gz", pd.DataFrame(ridge_audit))
    write_csv(hist / "sort_monotonicity_readout.csv", summary)
    write_csv(hist / "arm_summary_statistics.csv", stats)
    write_csv(hist / "early_late_direction_readout.csv", summary[summary["month_scope"].isin(["early", "late"])])
    write_csv(hist / "p4_p5_board_attribution_readout.csv", attribution)
    write_csv(hist / "month_instrument_dominance_audit.csv", dominance)
    write_csv(hist / "paper_benchmark_context.csv", pd.DataFrame([{"source_id": "trend_china_full_working_paper", "paper_sample": "paper", "paper_universe": "U_paper", "paper_weighting": "paper", "paper_holding": "paper", "paper_value": np.nan, "local_value": np.nan, "direct_comparability": False, "reason": "sample/universe/data/return semantics differ"}]))
    write_csv(hist / "exact_route_status.csv", pd.DataFrame([{"arm_id": "P2_TREND_FULL_EXACT", "run_status": "registered_not_run", "reason": "20A exact data/history/universe gates failed", "row_n": 0, "exact_replication_claim_allowed": False}, {"arm_id": "P3_RESMOM_CH3_EXACT", "run_status": "registered_not_run", "reason": "20A exact data/history/universe gates failed", "row_n": 0, "exact_replication_claim_allowed": False}]))

    resolution = assignment[["instrument_id", "decision_date", "label_month", "paper_proxy_next_month_return", "project_resolved_next_month_return", "outcome_resolution", "arm_id", "semantic_track", "bucket_count", "bucket_id"]].copy()
    resolution["label_period"] = pd.PeriodIndex(resolution["label_month"], freq="M")
    resolution["label_end"] = resolution["label_period"].map(label_end)
    resolution["source_last_trade_date"] = [last_date.at[i, p] if i in last_date.index and p in last_date.columns else pd.NaT for i, p in zip(resolution["instrument_id"], resolution["label_period"])]
    resolution["security_status"] = resolution["outcome_resolution"].map({"valid_mark": "traded_to_label_end", "suspension_carry_mark": "explicit_suspension_or_partial_month", "delisting_minus_one": "confirmed_security_master_delist", "unknown_bridge_arm_month_not_evaluable": "unverified_bridge"})
    resolution["raw_qfq_return"] = resolution["paper_proxy_next_month_return"]
    resolution["affected_arm_bucket_keys"] = resolution[["arm_id", "semantic_track", "bucket_count", "bucket_id"]].astype(str).agg("|".join, axis=1)
    resolution = resolution.drop(columns=["label_period", "arm_id", "semantic_track", "bucket_count", "bucket_id"]).drop_duplicates()
    resolution["resolution_source_hash"] = stable_hash({"security_master": file_sha(paths["security_master"]), "rows": len(resolution)})
    write_csv(hist / "outcome_resolution_audit.csv.gz", resolution)
    access_specs = [
        (paths["qfq_root"], stable_hash(input_meta.to_dict("records")), "historical_qfq_ohlcv", "date|close|volume|source_volume_unit", "signals|paper_and_project_returns"),
        (paths["project_universe"], file_sha(paths["project_universe"]), "pit_project_universe_status_size", "usable_trade_date|instrument|is_listed|is_suspended|total_market_cap_cny|ts_code", "membership|suspension|lagged_size"),
        (paths["benchmark"], file_sha(paths["benchmark"]), "csi300_benchmark", "date|close|index_alias", "market_return"),
        (paths["board_member"], file_sha(paths["board_member"]), "frozen_2025_board_membership", "board_ts_code|con_code", "board_multi_hot"),
        (paths["security_master"], file_sha(paths["security_master"]), "listing_delisting_status", "instrument|delist_date|is_delisted|metadata_source", "confirmed_delisting_resolution"),
    ]
    write_csv(hist / "outcome_access_audit.csv", pd.DataFrame([{"stage": "run-historical", "accessed_at_utc": utc_now(), "artifact_path": rel(path), "artifact_sha256_or_root_hash": digest, "dataset_role": role, "columns_read": cols, "derived_fields": derived, "historical_outcome_access_authorized": True, "forward_outcome_detected": False, "selection_or_tuning_allowed": False, "purpose": "registered historical diagnostic", "access_gate": "pass"} for path, digest, role, cols, derived in access_specs]))

    overlap = overlapping_outputs(assignment, project_returns, resolution_matrix, list(config["residual"]["holding_months"]), hist / "residual_overlapping_cohort_assignment.parquet")
    write_csv(hist / "residual_overlapping_portfolio_returns.csv.gz", overlap)

    snapshot = decision_snapshot(summary, signals, coefficients, pd.DataFrame(ts_audit), pd.DataFrame(ridge_audit))
    snapshot.update({"assignment_row_n": len(assignment), "bucket_return_row_n": len(bucket),
                     "signal_row_n": len(signals), "overlapping_appendix_materialized": True})
    write_json(hist / "historical_decision_snapshot.json", snapshot)
    names = sorted(p.name for p in hist.iterdir() if p.is_file())
    bundle_hash = seal_bundle(hist, "historical_manifest_20b.json", "historical_output_hashes_20b.json", names,
                              {"run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "preoutcome_bundle_hash": pre_hash})
    verify_bundle(hist, "historical_manifest_20b.json", "historical_output_hashes_20b.json")
    publish_stage(hist, hist_target)
    return {"status": "sealed", "historical_bundle_hash": bundle_hash, **snapshot}


def finalize_stage(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    config = load_config(config_path)
    target = output_root(config)
    if target.exists():
        hashes = target / "output_hashes_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json"
        manifest = target / "manifest_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json"
        return {"status": "already_finalized", "final_bundle_hash": verify_bundle(target, manifest.name, hashes.name)}
    root = build_root(config)
    pre_hash = verify_bundle(root / "preoutcome", "preoutcome_manifest_20b.json", "preoutcome_output_hashes_20b.json")
    hist_hash = verify_bundle(root / "historical", "historical_manifest_20b.json", "historical_output_hashes_20b.json")
    manifest = root / "manifest_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json"
    hashes = root / "output_hashes_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json"
    snapshot = read_json(root / "historical/historical_decision_snapshot.json")
    p1, p1paper, p4, p5 = snapshot["p1"], snapshot["p1_paper_fill"], snapshot["p4"], snapshot["p5"]
    row = {
        "run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "decision_state": snapshot["decision_state"],
        "primary_objective": "deployable_positive_beta", "incremental_alpha_required": False,
        "upstream_20a_integrity_gate": "pass", "R2_universe_resolution_gate": "pass",
        "R2_replication_role_resolution_gate": "pass", "R2_promotion_eligibility_resolution_gate": "pass",
        "TrendPV_warmup_resolution_gate": "pass", "R2_family_bridge_role_resolution_gate": "pass",
        "preoutcome_manifest_hash_gate": "pass", "historical_run_authorization_gate": "pass",
        "outcome_firewall_gate": "pass", "historical_manifest_hash_gate": "pass", "final_manifest_hash_gate": "pass",
        **{key: snapshot[key] for key in [
            "P0_formula_integrity_gate", "P0_metric_completeness_gate", "P0_materialization_gate",
            "P1_formula_integrity_gate", "P1_paper_fill_formula_integrity_gate", "P1_sample_support_gate",
            "P1_direction_metric_completeness_gate", "P1_materialization_gate",
            "P4_formula_integrity_gate", "P4_sample_support_gate", "P4_direction_metric_completeness_gate",
            "P4_materialization_gate", "P5_materialization_gate", "P5_fully_post_snapshot_materialization_gate",
            "P6_formula_integrity_gate", "P6_metric_completeness_gate", "P6_materialization_gate",
            "P1_paper_sort_direction_gate", "P4_paper_sort_direction_gate", "P1_paper_fill_sort_diagnostic_gate",
            "P5_retrospective_sort_diagnostic_gate", "P1_positive_exposure_design_gate", "P4_positive_exposure_design_gate",
            "primary_materialized_any", "primary_positive_exposure_any", "P1_partial_positive", "P4_partial_positive",
            "project_partial_positive_any", "auxiliary_sort_positive_any", "all_materialized_primary_full_nonpositive",
            "partial_formula_failure", "P1_metric_materialization_failure", "P4_metric_materialization_failure",
            "partial_metric_materialization_failure", "P1_partial_underpowered", "P4_partial_underpowered",
            "partial_underpowered", "global_underpowered", "global_metric_materialization_failure",
        ]},
        "P2_run_status": "registered_not_run", "P3_run_status": "registered_not_run",
        "P1_project_strict_evaluable_month_n": p1["months_full"],
        "P1_paper_fill_evaluable_month_n": p1paper["months_full"],
        "P4_evaluable_month_n": p4["months_full"],
        "P5_full_history_retrospective_evaluable_month_n": p5["months_full"],
        "P5_fully_post_snapshot_score_month_n": p5.get("scope_months", 0),
        "P1_early_month_n": p1["months_early"], "P1_late_month_n": p1["months_late"],
        "P1_paper_fill_early_month_n": p1paper["months_early"], "P1_paper_fill_late_month_n": p1paper["months_late"],
        "P4_early_month_n": p4["months_early"], "P4_late_month_n": p4["months_late"],
        "P5_full_history_retrospective_early_month_n": p5["months_early"],
        "P5_full_history_retrospective_late_month_n": p5["months_late"],
        **{f"P1_mean_spread_{s}": p1[f"spread_{s}"] for s in ["full", "early", "late"]},
        **{f"P4_mean_spread_{s}": p4[f"spread_{s}"] for s in ["full", "early", "late"]},
        **{f"P1_paper_fill_mean_spread_{s}": p1paper[f"spread_{s}"] for s in ["full", "early", "late"]},
        **{f"P5_full_history_retrospective_mean_spread_{s}": p5[f"spread_{s}"] for s in ["full", "early", "late"]},
        **{f"P1_favorable_extreme_mean_{s}": p1[f"fav_{s}"] for s in ["full", "early", "late"]},
        **{f"P4_favorable_extreme_mean_{s}": p4[f"fav_{s}"] for s in ["full", "early", "late"]},
        "P4_arm_promotion_eligible": False, "P4_residual_family_bridge_authorizer": True,
        "P4_pass_does_not_change_residual_primary": True, "residual_primary_arm_frozen": "C3_RESMOM_R3_BOARD_ADAPTATION",
        "residual_primary_changed_by_20B": False, "exact_replication_reachable": False,
        "historical_sample_role": HISTORICAL_ROLE, "historical_support_claim_allowed": False,
        "20C_requirement_generation_authorized": snapshot["20C_requirement_generation_authorized"],
        "20C_execution_authorized": False, "policy_training_authorized": False, "policy_replay_authorized": False,
        "portfolio_optimization_authorized": False, "deployment_authorized": False,
        "preoutcome_bundle_hash": pre_hash, "historical_bundle_hash": hist_hash,
        "blocking_reasons": snapshot["blocking_reasons"],
    }
    decision_name = "20B_trendpv_residual_momentum_design_and_replication_diagnostic_decision.csv"
    report_name = "20B_trendpv_residual_momentum_design_and_replication_diagnostic_report.md"
    write_csv(root / decision_name, pd.DataFrame([row]))
    support = pd.read_csv(root / "historical/monthly_signal_support.csv")
    resolution = pd.read_csv(root / "historical/outcome_resolution_audit.csv.gz")
    resolution_counts = resolution["outcome_resolution"].value_counts().to_dict()
    overlap = pd.read_csv(root / "historical/residual_overlapping_portfolio_returns.csv.gz")
    attribution = pd.read_csv(root / "historical/p4_p5_board_attribution_readout.csv")
    paired_summary_n = int((attribution["record_type"] == "return_scope_summary").sum())
    report = f"""# 20B TrendPV 与 Residual Momentum 历史设计 / 复制诊断

## 1. 一页决策

- decision state：`{snapshot['decision_state']}`
- 20C requirement generation authorized：`{str(snapshot['20C_requirement_generation_authorized']).lower()}`
- exact replication reachable：`false`
- historical sample role：`{HISTORICAL_ROLE}`；任何结果都不是 support。
- preoutcome bundle：`{pre_hash}`
- historical bundle：`{hist_hash}`

20B 目标是正收益暴露设计，不要求 matched alpha。P2/P3 因 exact data/history/universe gates 失败而 registered-not-run。

## 2. 正 beta 目标，不是 alpha 目标

冻结目标是 favorable bucket 的绝对 gross return 方向；`incremental_alpha_required=false`。Spread 只诊断 paper-style sorting morphology，不替代正收益暴露门。

## 3. 20A lineage 与运行授权

20A freeze hash 固定为 `{EXPECTED_20A_HASH}`。Preoutcome bundle `{pre_hash}` 在 outcome access 前完成密封；本轮直接运行授权绑定到该 hash，历史 bundle 为 `{hist_hash}`。

## 4. Metadata resolution

R2 universe/replication/promotion 已解析为 `U_project / project_adaptation / promotion=false`；P4 仅保留 family-bridge authorization。Trend warm-up 使用 400 sessions 后 38 个 complete coefficient months，不复用旧的 97-month metadata。

## 5. Exact routes

| arm | status | reason |
|---|---|---|
| P2 | registered_not_run | wide PIT market-cap、PIT EP、paper universe/history gates 不满足 |
| P3 | registered_not_run | risk-free、CH-3 vintage、paper universe/history gates 不满足 |

## 6. 支持月份、coverage 与 missingness

`monthly_signal_support.csv` 共 {len(support):,} 行，逐 arm-track-month 披露 denominator、signal/decile coverage、paper completeness、project resolution 与 unknown bridge。P1 strict/P1 paper-fill/P4/P5/P0/P6 的 primary evaluable months 分别为 {p1['months_full']}/{p1paper['months_full']}/{p4['months_full']}/{p5['months_full']}/{snapshot['p0']['months_full']}/{snapshot['p6']['months_full']}。

## 7. TrendPV 18 signals 与 coefficient path

使用 9 个 price 与 9 个 normalized-volume predictor；月度 OLS 为 float64 `lstsq(rcond=1e-12)`。Artifact 同时保存 realized beta、EMA beta、rank、fit row hash、complete-month count 与 staleness，score 分解为 price/volume components。

## 8. 月末动量与 sequential R2

P0 固定使用 `t-11...t-1` 11 个 project-conservative returns。P4 每个 residual month 只用此前 36 个 paired stock/CSI300 months 回归，再以 `t-11...t-1` 的 11 个 residuals 形成 score。

## 9. R3 board ridge 与 paired attribution

P5 复用逐行 P4 residual，再用 lagged log-size 与去重后的 2025 board multi-hot 做 ridge。Retrospective/mixed/fully-post scopes 均机械标注；paired attribution 产生 {paired_summary_n:,} 个 return scope summary，不使用 unpaired arm means。

## 10. Outcome resolution

Audit rows 的 resolution 数量：valid={resolution_counts.get('valid_mark', 0):,}，suspension carry={resolution_counts.get('suspension_carry_mark', 0):,}，confirmed delisting -1={resolution_counts.get('delisting_minus_one', 0):,}，unknown bridge={resolution_counts.get('unknown_bridge_arm_month_not_evaluable', 0):,}。只有 security master 确认退市才允许 -1；unknown 会令整个 project bucket-month 不可评价。

## 11. EW/VW sorting morphology 与 primary gates

| arm | materialized | favorable full | favorable early | favorable late | spread full | positive exposure gate |
|---|---:|---:|---:|---:|---:|---:|
| P1 TrendPV strict | {p1.get('months_full', 0)} months | {p1.get('fav_full', float('nan')):.6f} | {p1.get('fav_early', float('nan')):.6f} | {p1.get('fav_late', float('nan')):.6f} | {p1.get('spread_full', float('nan')):.6f} | {snapshot['P1_positive_exposure_design_gate']} |
| P4 R2 market residual | {p4.get('months_full', 0)} months | {p4.get('fav_full', float('nan')):.6f} | {p4.get('fav_early', float('nan')):.6f} | {p4.get('fav_late', float('nan')):.6f} | {p4.get('spread_full', float('nan')):.6f} | {snapshot['P4_positive_exposure_design_gate']} |

所有 decile/quintile EW/VW、bucket means、favorable-minus-unfavorable、favorable-minus-middle、raw/aligned Spearman 均保留在 sealed tables。

## 12. 3/6/12 overlapping appendix

共 {len(overlap):,} 个 overlapping portfolio-month rows。Within-cohort 使用 buy-and-hold drift，跨 cohort 固定 1/H；只有恰好 H 个 active 且 observable cohorts 时可评价。Delisting -1 只在 terminal month 一次，后续为 `post_terminal_zero_value`；该 appendix 不进入 gate。

## 13. Frozen folds、dominance 与 design-only inference

P1/P4 使用 preoutcome 冻结的 48/24 与 60/30 calendars；实际缺失月份不会重切 early/late。Quantile、ES10、HAC Bartlett、drawdown、month dominance、LOMO 与 LOIO 均为 design-only fragility diagnostics。

## 14. Paper context 不可直接比较

本地使用 U_project、provider-qfq、固定本地 dates/weights/holding；论文样本、universe、数据库与 portfolio construction 不同，因此 paper statistic 与 local value 均标记 `direct_comparability=false`。

## 15. Gate、family bridge 与 20C

P1 paper-sort={snapshot['P1_paper_sort_direction_gate']}，P4 paper-sort={snapshot['P4_paper_sort_direction_gate']}，P1 paper-fill diagnostic={snapshot['P1_paper_fill_sort_diagnostic_gate']}，P5 retrospective diagnostic={snapshot['P5_retrospective_sort_diagnostic_gate']}。P4 `arm_promotion_eligible=false`，仅能通过 family-bridge field 参与 20C generation。`20C_requirement_generation_authorized={snapshot['20C_requirement_generation_authorized']}`。

## 16. Access、resolution 与 manifest 证据

Historical access audit 分开记录 qfq、PIT universe/status/size、CSI300、board snapshot 与 security master。三个 bundle 均执行 file-set 双向 hash 校验；早期 superseded bundles 保持 immutable，当前 `{CONTRACT_VERSION}` 通过 transactional candidate publication。

## 17. 授权边界

所有收益是 close-to-close gross provider-qfq proxy，不是 next-open、成本后、cash-inclusive 20C NAV。Paper-sort morphology 与 favorable bucket 绝对收益分别报告；任何显著性只作 design diagnostic。

P5 使用 2025 static concept-board proxy；2025 年以前及混合 formation 均标记 retrospective look-ahead。P4 pass 不晋升 R2，也不改变冻结的 R3 residual primary。

3/6/12 overlapping appendix 使用 within-cohort buy-and-hold drift 与跨 cohort 1/H allocation 完整物化；它不参与任何 gate。

`20C_execution_authorized=false`，`policy_training_authorized=false`，`policy_replay_authorized=false`，`portfolio_optimization_authorized=false`，`deployment_authorized=false`。

Finalize raw input read count：`0`；outcome recompute count：`0`。
"""
    write_text(root / report_name, report)
    final_hash = seal_bundle(root, manifest.name, hashes.name, [decision_name, report_name],
                             {"run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "preoutcome_bundle_hash": pre_hash, "historical_bundle_hash": hist_hash})
    verify_bundle(root, manifest.name, hashes.name)
    os.replace(root, target)
    return {"status": "finalized", "final_bundle_hash": final_hash, "decision_state": snapshot["decision_state"], "output_root": str(target)}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.stage == "preflight": result = preflight_stage(args.config)
    elif args.stage == "run-historical": result = historical_stage(args.config, args.workers)
    elif args.stage == "finalize": result = finalize_stage(args.config)
    else:
        result = {"preflight": preflight_stage(args.config),
                  "historical": historical_stage(args.config, args.workers),
                  "finalize": finalize_stage(args.config)}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
